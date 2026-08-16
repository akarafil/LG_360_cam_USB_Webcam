"""
LG 360 CAM - Görüntü Ayarları Paneli
======================================
webcam.sh kurulumu bitirdikten sonra çalışır. /dev/video9'a akan ffmpeg
sürecini bu script yönetir (başlatır, ayar değişince yeniden başlatır) ve
tarayıcıda kaydırma çubuklu bir panel + canlı MJPEG önizleme sunar.

Düşük gecikme önceliklidir: ana /dev/video9 hattı hep aynı "nobuffer/
low_delay" ffmpeg bayraklarıyla çalışır, sadece görüntü filtresi (eq/
unsharp/hqdn3d) değişir. Önizleme ayrı, hafif bir OpenCV okuyucudur ve
ana hattı etkilemez. Ses bu hatta hiç taşınmıyor (v4l2 çıkışı zaten
görüntü-only), dolayısıyla ses/görüntü kayması oluşmaz.
"""

import subprocess
import threading
import time

import cv2
from flask import Flask, Response, jsonify, request

from config import Config

app = Flask(__name__)

VIDEO_DEVICE = "/dev/video9"
UDP_SOURCE = "udp://@:1234?reuse=1"

_ffmpeg_proc = None
_ffmpeg_lock = threading.Lock()


def _build_filter_chain() -> str:
    brightness = (Config.STREAM_BRIGHTNESS - 50) / 50.0
    contrast = Config.STREAM_CONTRAST / 50.0
    saturation = Config.STREAM_SATURATION / 50.0
    gamma = Config.STREAM_GAMMA / 100.0

    filters = [
        "crop=640:480",
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
        "-probesize", "32",
        "-analyzeduration", "0",
        "-i", UDP_SOURCE,
        "-threads", "1",
        "-vf", _build_filter_chain(),
        "-f", "v4l2", VIDEO_DEVICE,
    ]
    _ffmpeg_proc = subprocess.Popen(cmd)


def _restart_ffmpeg():
    global _ffmpeg_proc
    with _ffmpeg_lock:
        if _ffmpeg_proc is not None:
            _ffmpeg_proc.terminate()
            try:
                _ffmpeg_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _ffmpeg_proc.kill()
        _start_ffmpeg()


SETTINGS = {
    "brightness": ("STREAM_BRIGHTNESS", 0, 100),
    "contrast": ("STREAM_CONTRAST", 0, 100),
    "saturation": ("STREAM_SATURATION", 0, 100),
    "sharpness": ("STREAM_SHARPNESS", 0, 100),
    "denoise": ("STREAM_DENOISE", 0, 10),
    "gamma": ("STREAM_GAMMA", 50, 200),
}


@app.route("/")
def index():
    sliders_html = ""
    for key, (attr, lo, hi) in SETTINGS.items():
        value = getattr(Config, attr)
        sliders_html += f"""
        <div class="control">
          <label for="{key}">{key} <span id="{key}_val">{value}</span></label>
          <input type="range" id="{key}" min="{lo}" max="{hi}" value="{value}"
                 oninput="ayarDegisti('{key}', this.value)">
        </div>"""

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
  input[type=range] {{ width: 260px; }}
  .panel {{ min-width: 280px; }}
</style>
</head>
<body>
  <h1>LG 360 CAM - Görüntü Ayarları</h1>
  <div class="wrap">
    <img src="/preview" alt="Canlı Önizleme">
    <div class="panel">{sliders_html}</div>
  </div>
<script>
let zamanlayici = null;
function ayarDegisti(key, val) {{
  document.getElementById(key + '_val').textContent = val;
  clearTimeout(zamanlayici);
  zamanlayici = setTimeout(() => {{
    fetch('/settings', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{[key]: val}})
    }});
  }}, 300);
}}
</script>
</body>
</html>"""


@app.route("/settings", methods=["POST"])
def settings():
    data = request.get_json(force=True)
    for key, value in data.items():
        if key not in SETTINGS:
            continue
        attr, lo, hi = SETTINGS[key]
        value = max(lo, min(hi, int(float(value))))
        setattr(Config, attr, value)
    Config.dosyaya_kaydet()
    _restart_ffmpeg()
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


if __name__ == "__main__":
    Config.dosyadan_yukle()
    _start_ffmpeg()
    try:
        app.run(host=Config.WEB_HOST, port=Config.WEB_PORT, threaded=True)
    finally:
        if _ffmpeg_proc is not None:
            _ffmpeg_proc.terminate()
