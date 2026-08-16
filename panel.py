"""
LG 360 CAM - Görüntü Ayarları Paneli
======================================
webcam.sh kurulumu bitirdikten sonra çalışır. Kameranın OSC oturumunu VE
/dev/video9'a akan ffmpeg sürecini bu script yönetir; tarayıcıda kaydırma
çubuklu bir panel + canlı MJPEG önizleme sunar.

Kararlılık notu: ffmpeg'i, kamera sürekli aynı UDP akışını gönderirken
"ortasından" yeniden başlatmak (yeni bir H264 anahtar kare gelene kadar)
bazen hiç senkronize olamayıp kilitleniyordu. Bunu önlemek için her ayar
değişikliğinde ÖNCE kameranın kendi yayınını (_stopPreview/_startPreview)
yeniden başlatıyoruz — böylece yerel ffmpeg her zaman akışın en başından,
temiz bir anahtar kareyle başlıyor. Hızlı ardışık değişiklikler (kaydırma
çubuğunu sürüklerken) tek bir yeniden başlatmada birleştirilir (debounce).

Düşük gecikme önceliklidir: nobuffer/low_delay/fast bayrakları hep aynı.
Ses bu hatta hiç taşınmıyor (v4l2 çıkışı zaten görüntü-only), dolayısıyla
ses/görüntü kayması oluşmaz.
"""

import subprocess
import threading
import time

import cv2
from flask import Flask, Response, jsonify, request

from camera_api import LG360CamAPI
from config import Config

app = Flask(__name__)

VIDEO_DEVICE = "/dev/video9"
UDP_SOURCE = "udp://@:1234?reuse=1&fifo_size=1000000&overrun_nonfatal=1"
DEBOUNCE = 0.5           # saniye — art arda gelen değişiklikleri birleştirir
RESTART_COOLDOWN = 4.0   # saniye — bir restart'ın senkronize olması için gereken asgari süre;
                         # bu süre dolmadan yeni bir restart tetiklenmez (art arda kesilmeyi önler)

api = LG360CamAPI()
_ffmpeg_proc = None
_restart_timer = None
_son_restart_zamani = 0.0
_lock = threading.Lock()

CROP_PRESETS = {
    "zoom": {"boyut": (480, 480), "etiket": "Yakın (Zoom)"},
    "normal": {"boyut": (640, 480), "etiket": "Normal"},
    "wide": {"boyut": (1024, 768), "etiket": "Geniş (Balıkgözüne Yakın)"},
}
CAMERA_RESOLUTIONS = {
    "1024x512": {"boyut": (1024, 512), "etiket": "1024x512 (hızlı)"},
    "640x320": {"boyut": (640, 320), "etiket": "640x320 (en hızlı)"},
    "1280x640": {"boyut": (1280, 640), "etiket": "1280x640"},
    "1280x768": {"boyut": (1280, 768), "etiket": "1280x768 (varsayılan)"},
}

SLIDERS = {
    "brightness": ("STREAM_BRIGHTNESS", 0, 100),
    "contrast": ("STREAM_CONTRAST", 0, 100),
    "saturation": ("STREAM_SATURATION", 0, 100),
    "sharpness": ("STREAM_SHARPNESS", 0, 100),
    "denoise": ("STREAM_DENOISE", 0, 10),
    "gamma": ("STREAM_GAMMA", 50, 200),
}


def _build_filter_chain() -> str:
    cw, ch = CROP_PRESETS.get(Config.STREAM_LENS_ANGLE, CROP_PRESETS["normal"])["boyut"]

    brightness = (Config.STREAM_BRIGHTNESS - 50) / 50.0
    contrast = Config.STREAM_CONTRAST / 50.0
    saturation = Config.STREAM_SATURATION / 50.0
    gamma = Config.STREAM_GAMMA / 100.0

    filters = [
        f"crop={cw}:{ch}",
        f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}"
        f":saturation={saturation:.3f}:gamma={gamma:.3f}",
    ]

    sharp_amount = (Config.STREAM_SHARPNESS - 50) / 25.0
    if abs(sharp_amount) > 0.01:
        filters.append(f"unsharp=5:5:{sharp_amount:.3f}:5:5:0.0")

    if Config.STREAM_DENOISE > 0:
        d = Config.STREAM_DENOISE
        filters.append(f"hqdn3d={d*2}:{d*1.5}:{d*2}:{d*1.5}")

    return ",".join(filters)


def _start_ffmpeg():
    global _ffmpeg_proc
    cmd = [
        "ffmpeg", "-v", "warning",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-flags2", "fast",
        "-i", UDP_SOURCE,
        "-threads", "1",
        "-vf", _build_filter_chain(),
        "-f", "v4l2", VIDEO_DEVICE,
    ]
    _ffmpeg_proc = subprocess.Popen(cmd)


def _stop_ffmpeg():
    global _ffmpeg_proc
    if _ffmpeg_proc is not None:
        _ffmpeg_proc.terminate()
        try:
            _ffmpeg_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _ffmpeg_proc.kill()
        _ffmpeg_proc = None


def _uygula_ve_yeniden_baslat():
    """Kamera tarafındaki yayını da yeniden başlatarak temiz bir senkron sağlar."""
    global _son_restart_zamani
    with _lock:
        Config.dosyaya_kaydet()
        _stop_ffmpeg()
        api.yayin_durdur()
        cw, ch = CAMERA_RESOLUTIONS[Config.STREAM_CAMERA_RESOLUTION]["boyut"]
        api.preview_format_ayarla(cw, ch)
        api.yayin_baslat()
        time.sleep(0.3)
        _start_ffmpeg()
        _son_restart_zamani = time.time()


def _zamanli_yeniden_baslat():
    """Ayar değişikliklerini birleştirir VE bir önceki restart'ın senkronize
    olması için en az RESTART_COOLDOWN saniye geçmeden yeni restart tetiklemez
    — böylece art arda değişiklikler akışı sürekli kesmek yerine, kullanıcı
    durduğunda TEK bir restart ile en son ayarları uygular."""
    global _restart_timer
    if _restart_timer is not None:
        _restart_timer.cancel()
    gecen = time.time() - _son_restart_zamani
    gecikme = max(DEBOUNCE, RESTART_COOLDOWN - gecen)
    _restart_timer = threading.Timer(gecikme, _uygula_ve_yeniden_baslat)
    _restart_timer.daemon = True
    _restart_timer.start()


def _watchdog():
    """ffmpeg beklenmedik şekilde çökerse otomatik yeniden başlatır."""
    while True:
        time.sleep(3)
        with _lock:
            if _ffmpeg_proc is not None and _ffmpeg_proc.poll() is not None:
                print("[watchdog] ffmpeg beklenmedik şekilde durdu, yeniden başlatılıyor...")
                _start_ffmpeg()


def _oturum_canli_tut():
    while True:
        time.sleep(10)
        try:
            api._komut_gonder("camera.updateSession", {"sessionId": api.session_id})
        except Exception as e:
            print(f"[oturum] updateSession hatası: {e}")


@app.route("/")
def index():
    sliders_html = ""
    for key, (attr, lo, hi) in SLIDERS.items():
        value = getattr(Config, attr)
        sliders_html += f"""
        <div class="control">
          <label for="{key}">{key} <span id="{key}_val">{value}</span></label>
          <input type="range" id="{key}" min="{lo}" max="{hi}" value="{value}"
                 oninput="ayarDegisti('{key}', this.value)">
        </div>"""

    lens_options = "".join(
        f'<option value="{k}" {"selected" if k == Config.STREAM_LENS_ANGLE else ""}>{v["etiket"]}</option>'
        for k, v in CROP_PRESETS.items()
    )
    res_options = "".join(
        f'<option value="{k}" {"selected" if k == Config.STREAM_CAMERA_RESOLUTION else ""}>{v["etiket"]}</option>'
        for k, v in CAMERA_RESOLUTIONS.items()
    )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>LG 360 CAM - Görüntü Ayarları</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #111; color: #eee; margin: 0; padding: 20px; }}
  h1 {{ font-size: 1.2rem; }}
  .wrap {{ display: flex; gap: 24px; flex-wrap: wrap; }}
  img {{ max-width: 640px; border-radius: 8px; border: 1px solid #333; }}
  .control {{ margin-bottom: 16px; }}
  label {{ display: block; margin-bottom: 4px; font-size: 0.9rem; text-transform: capitalize; }}
  input[type=range], select {{ width: 260px; }}
  select {{ background: #222; color: #eee; border: 1px solid #444; padding: 4px; border-radius: 4px; }}
  .panel {{ min-width: 280px; }}
  .durum {{ font-size: 0.8rem; color: #888; margin-top: 8px; }}
</style>
</head>
<body>
  <h1>LG 360 CAM - Görüntü Ayarları</h1>
  <div class="wrap">
    <img src="/preview" alt="Canlı Önizleme">
    <div class="panel">
      <div class="control">
        <label for="lens_angle">Lens Açısı / Kırpma</label>
        <select id="lens_angle" onchange="secimDegisti('lens_angle', this.value)">{lens_options}</select>
      </div>
      <div class="control">
        <label for="camera_resolution">Kamera Çözünürlüğü</label>
        <select id="camera_resolution" onchange="secimDegisti('camera_resolution', this.value)">{res_options}</select>
      </div>
      {sliders_html}
      <div id="durum" class="durum"></div>
    </div>
  </div>
<script>
let zamanlayici = null;
function durumGoster(msg) {{ document.getElementById('durum').textContent = msg; }}
function gonder(payload) {{
  fetch('/settings', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(payload)
  }}).then(() => durumGoster('Uygulandı.'));
}}
function ayarDegisti(key, val) {{
  document.getElementById(key + '_val').textContent = val;
  durumGoster('Değişiklik uygulanıyor...');
  clearTimeout(zamanlayici);
  zamanlayici = setTimeout(() => gonder({{[key]: val}}), 250);
}}
function secimDegisti(key, val) {{
  durumGoster('Değişiklik uygulanıyor (birkaç saniye sürebilir)...');
  gonder({{[key]: val}});
}}
</script>
</body>
</html>"""


@app.route("/settings", methods=["POST"])
def settings():
    data = request.get_json(force=True)
    for key, value in data.items():
        if key in SLIDERS:
            attr, lo, hi = SLIDERS[key]
            setattr(Config, attr, max(lo, min(hi, int(float(value)))))
        elif key == "lens_angle" and value in CROP_PRESETS:
            Config.STREAM_LENS_ANGLE = value
        elif key == "camera_resolution" and value in CAMERA_RESOLUTIONS:
            Config.STREAM_CAMERA_RESOLUTION = value
    _zamanli_yeniden_baslat()
    return jsonify({"ok": True})


def _mjpeg_frames():
    cap = cv2.VideoCapture(VIDEO_DEVICE)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.1)
                continue
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                + buf.tobytes()
                + b"\r\n"
            )
    finally:
        cap.release()


@app.route("/preview")
def preview():
    return Response(_mjpeg_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


def _kamerayi_baslat():
    """İlk bağlantı — camera_api.py'nin kanıtlanmış tam_baslat() akışıyla aynı
    (preview format burada zorlanmıyor, kamera varsayılan formatla başlıyor;
    çözünürlük değişimi sadece kullanıcı panelden seçtiğinde uygulanıyor)."""
    if not api.baglan():
        raise SystemExit("Kameraya bağlanılamadı, çıkılıyor.")
    api.oturum_baslat()
    api._capture_mode_ayarla()
    time.sleep(1.0)
    if not api.yayin_baslat():
        raise SystemExit("Yayın başlatılamadı, çıkılıyor.")


if __name__ == "__main__":
    Config.dosyadan_yukle()
    _kamerayi_baslat()
    _start_ffmpeg()
    threading.Thread(target=_watchdog, daemon=True).start()
    threading.Thread(target=_oturum_canli_tut, daemon=True).start()
    try:
        app.run(host=Config.WEB_HOST, port=Config.WEB_PORT, threaded=True)
    finally:
        _stop_ffmpeg()
        api.oturum_kapat()
