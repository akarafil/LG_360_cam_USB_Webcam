"""
LG 360 CAM Güvenlik Kamerası - Yapılandırma Modülü
===================================================
Tüm uygulama ayarlarını merkezi olarak yönetir.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Proje kök dizini
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Uygulama yapılandırma sınıfı."""

    # === Kamera Ayarları ===
    CAMERA_IP = "192.168.43.1"
    CAMERA_PORT = 6624
    CAMERA_API_URL = f"http://{CAMERA_IP}:{CAMERA_PORT}/osc/commands/execute"
    CAMERA_INFO_URL = f"http://{CAMERA_IP}:{CAMERA_PORT}/osc/info"
    CAMERA_SESSION_ID = "lgcam_securu_01"
    CAMERA_CONNECT_TIMEOUT = 10       # saniye
    CAMERA_RECONNECT_INTERVAL = 15    # saniye

    # === UDP Stream Ayarları ===
    STREAM_UDP_PORT = 1234
    STREAM_BUFFER_SIZE = 65536
    STREAM_FRAME_WIDTH = 1920
    STREAM_FRAME_HEIGHT = 960
    STREAM_FPS = 30

    # === Ağ Köprüsü Ayarları ===
    WIFI_INTERFACE = "wlan0"
    LAN_INTERFACE = "eth0"
    CAMERA_WIFI_SSID_PREFIX = "LGR105_"
    CAMERA_WIFI_PASSWORD = ""
    CAMERA_SUBNET = "192.168.43.0/24"

    # === Hareket Algılama Ayarları ===
    MOTION_ENABLED = False
    MOTION_THRESHOLD = 25
    MOTION_MIN_AREA = 5000
    MOTION_BLUR_SIZE = 21
    MOTION_DILATE_ITERATIONS = 2
    MOTION_COOLDOWN = 5
    MOTION_SENSITIVITY = "medium"

    # === Kayıt Ayarları ===
    RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
    RECORDING_FORMAT = "mp4"
    RECORDING_CODEC = "mp4v"
    RECORDING_FPS = 30              # ← Artık stream FPS ile eşleşiyor
    RECORDING_PRE_BUFFER = 3
    RECORDING_POST_BUFFER = 10
    RECORDING_MAX_DURATION = 300
    RECORDING_MAX_DISK_GB = 10
    RECORDING_AUTO_CLEANUP = True

    # === Kayıt Kalite / Bitrate Ayarları (YENİ) ===
    # Çözünürlük presetleri: "native" | "1080p" | "720p" | "480p"
    RECORDING_RESOLUTION_PRESET = "native"
    # CRF değeri (FFmpeg tabanlı kayıtta kullanılır, 0=lossless, 51=en düşük)
    RECORDING_CRF = 23
    # OpenCV VideoWriter için JPEG kalite benzeri parametre (0-100)
    RECORDING_QUALITY = 85
    # Bitrate tahmini (kbps) — VideoWriter istersek bunu da kullanabilir
    RECORDING_BITRATE_KBPS = 4000

    # === Stream Görüntü Ayarları ===
    STREAM_BRIGHTNESS = 50          # 0-100
    STREAM_CONTRAST = 50            # 0-100
    STREAM_SATURATION = 50          # 0-100
    # Fine-tune ayarları (YENİ)
    STREAM_SHARPNESS = 50           # 0-100 (keskinlik filtresi)
    STREAM_DENOISE = 0              # 0=kapalı, 1-10 (gürültü azaltma)
    STREAM_GAMMA = 100              # 50-200 (gamma düzeltme, 100=normal)

    # === Web Sunucu Ayarları ===
    SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 5555
    WEB_DEBUG = False
    WEB_SECRET_KEY = "lgcam_securu_secret_key_change_me"

    # MJPEG kalite/FPS — yüksek tutuldu, düşüklük stream_receiver optimizasyonu ile çözülüyor
    MJPEG_QUALITY = 80
    MJPEG_MAX_FPS = 30

    # === Log Ayarları ===
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_MAX_SIZE_MB = 50
    LOG_BACKUP_COUNT = 5

    # === Demo Modu ===
    DEMO_MODE = False
    DEMO_VIDEO_SOURCE = 0

    # === Hassasiyet Presets ===
    SENSITIVITY_PRESETS = {
        "low": {
            "threshold": 40,
            "min_area": 10000,
            "blur_size": 25,
            "dilate_iterations": 3,
            "cooldown": 10
        },
        "medium": {
            "threshold": 25,
            "min_area": 5000,
            "blur_size": 21,
            "dilate_iterations": 2,
            "cooldown": 5
        },
        "high": {
            "threshold": 15,
            "min_area": 2000,
            "blur_size": 15,
            "dilate_iterations": 1,
            "cooldown": 3
        }
    }

    # === Çözünürlük Presetleri (YENİ) ===
    RESOLUTION_PRESETS = {
        "native": (None, None),   # kaynak çözünürlüğünü koru
        "1080p": (1920, 1080),
        "720p": (1280, 720),
        "480p": (854, 480),
        "360p": (640, 360),
    }

    @classmethod
    def kayit_cozunurluk_al(cls):
        """Kayıt çözünürlüğünü döndürür. None ise kaynak boyutunu kullan."""
        return cls.RESOLUTION_PRESETS.get(cls.RECORDING_RESOLUTION_PRESET, (None, None))

    @classmethod
    def dizinleri_olustur(cls):
        for dizin in [cls.RECORDINGS_DIR, cls.SNAPSHOT_DIR, cls.LOG_DIR]:
            os.makedirs(dizin, exist_ok=True)
            logger.debug(f"Dizin kontrol edildi: {dizin}")

    @classmethod
    def hassasiyet_ayarla(cls, seviye: str):
        if seviye not in cls.SENSITIVITY_PRESETS:
            logger.warning(f"Bilinmeyen hassasiyet seviyesi: {seviye}")
            return False
        preset = cls.SENSITIVITY_PRESETS[seviye]
        cls.MOTION_THRESHOLD = preset["threshold"]
        cls.MOTION_MIN_AREA = preset["min_area"]
        cls.MOTION_BLUR_SIZE = preset["blur_size"]
        cls.MOTION_DILATE_ITERATIONS = preset["dilate_iterations"]
        cls.MOTION_COOLDOWN = preset["cooldown"]
        cls.MOTION_SENSITIVITY = seviye
        logger.info(f"Hareket algılama hassasiyeti '{seviye}' olarak ayarlandı")
        return True

    @classmethod
    def dosyadan_yukle(cls, dosya_yolu: str = None):
        if dosya_yolu is None:
            dosya_yolu = os.path.join(BASE_DIR, "config.json")
        if not os.path.exists(dosya_yolu):
            logger.info(f"Yapılandırma dosyası bulunamadı: {dosya_yolu}, varsayılan ayarlar kullanılıyor")
            return
        try:
            with open(dosya_yolu, "r", encoding="utf-8") as f:
                ayarlar = json.load(f)
            for anahtar, deger in ayarlar.items():
                anahtar_buyuk = anahtar.upper()
                if hasattr(cls, anahtar_buyuk):
                    setattr(cls, anahtar_buyuk, deger)
                    logger.debug(f"Yapılandırma yüklendi: {anahtar_buyuk} = {deger}")
            cls.CAMERA_API_URL = f"http://{cls.CAMERA_IP}:{cls.CAMERA_PORT}/osc/commands/execute"
            cls.CAMERA_INFO_URL = f"http://{cls.CAMERA_IP}:{cls.CAMERA_PORT}/osc/info"
            logger.info(f"Yapılandırma dosyasından {len(ayarlar)} ayar yüklendi")
        except Exception as e:
            logger.error(f"Yapılandırma dosyası yüklenirken hata: {e}")

    @classmethod
    def dosyaya_kaydet(cls, dosya_yolu: str = None):
        if dosya_yolu is None:
            dosya_yolu = os.path.join(BASE_DIR, "config.json")
        ayarlar = {
            "camera_ip": cls.CAMERA_IP,
            "camera_port": cls.CAMERA_PORT,
            "camera_session_id": cls.CAMERA_SESSION_ID,
            "camera_wifi_password": cls.CAMERA_WIFI_PASSWORD,
            "wifi_interface": cls.WIFI_INTERFACE,
            "lan_interface": cls.LAN_INTERFACE,
            "stream_udp_port": cls.STREAM_UDP_PORT,
            "motion_enabled": cls.MOTION_ENABLED,
            "motion_sensitivity": cls.MOTION_SENSITIVITY,
            "recording_format": cls.RECORDING_FORMAT,
            "recording_fps": cls.RECORDING_FPS,
            "recording_quality": cls.RECORDING_QUALITY,
            "recording_bitrate_kbps": cls.RECORDING_BITRATE_KBPS,
            "recording_crf": cls.RECORDING_CRF,
            "recording_resolution_preset": cls.RECORDING_RESOLUTION_PRESET,
            "recording_max_disk_gb": cls.RECORDING_MAX_DISK_GB,
            "web_port": cls.WEB_PORT,
            "mjpeg_quality": cls.MJPEG_QUALITY,
            "mjpeg_max_fps": cls.MJPEG_MAX_FPS,
            "stream_brightness": cls.STREAM_BRIGHTNESS,
            "stream_contrast": cls.STREAM_CONTRAST,
            "stream_saturation": cls.STREAM_SATURATION,
            "stream_sharpness": cls.STREAM_SHARPNESS,
            "stream_denoise": cls.STREAM_DENOISE,
            "stream_gamma": cls.STREAM_GAMMA,
            "log_level": cls.LOG_LEVEL,
        }
        try:
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(ayarlar, f, indent=2, ensure_ascii=False)
            logger.info(f"Yapılandırma kaydedildi: {dosya_yolu}")
        except Exception as e:
            logger.error(f"Yapılandırma kaydedilirken hata: {e}")

    @classmethod
    def ozet(cls) -> dict:
        return {
            "kamera": {
                "ip": cls.CAMERA_IP,
                "port": cls.CAMERA_PORT,
                "wifi_ssid_prefix": cls.CAMERA_WIFI_SSID_PREFIX,
            },
            "ag": {
                "wifi_arayuz": cls.WIFI_INTERFACE,
                "lan_arayuz": cls.LAN_INTERFACE,
            },
            "hareket_algilama": {
                "aktif": cls.MOTION_ENABLED,
                "hassasiyet": cls.MOTION_SENSITIVITY,
                "esik": cls.MOTION_THRESHOLD,
                "min_alan": cls.MOTION_MIN_AREA,
            },
            "kayit": {
                "format": cls.RECORDING_FORMAT,
                "fps": cls.RECORDING_FPS,
                "kalite": cls.RECORDING_QUALITY,
                "bitrate_kbps": cls.RECORDING_BITRATE_KBPS,
                "crf": cls.RECORDING_CRF,
                "cozunurluk_preset": cls.RECORDING_RESOLUTION_PRESET,
                "maks_disk_gb": cls.RECORDING_MAX_DISK_GB,
                "oto_temizlik": cls.RECORDING_AUTO_CLEANUP,
            },
            "goruntu": {
                "parlaklik": cls.STREAM_BRIGHTNESS,
                "kontrast": cls.STREAM_CONTRAST,
                "doygunluk": cls.STREAM_SATURATION,
                "keskinlik": cls.STREAM_SHARPNESS,
                "gurultu_azaltma": cls.STREAM_DENOISE,
                "gamma": cls.STREAM_GAMMA,
            },
            "web": {
                "port": cls.WEB_PORT,
                "mjpeg_kalite": cls.MJPEG_QUALITY,
                "mjpeg_fps": cls.MJPEG_MAX_FPS,
            },
            "demo_modu": cls.DEMO_MODE,
        }
