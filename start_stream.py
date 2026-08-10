from camera_api import LG360CamAPI
from config import Config
import time

# Wi-Fi üzerinden (orijinal IP ile) bağlanıyoruz
Config.CAMERA_IP = "192.168.43.1"

print(f"[{Config.CAMERA_IP}] Kameraya bağlanılıyor...")
api = LG360CamAPI()
api.tam_baslat()
print("Yayın başlatıldı! Şimdi ffmpeg komutunu çalıştırın.")

try:
    while True:
        time.sleep(10)
        api._komut_gonder("camera.updateSession", {"sessionId": api.session_id})
except KeyboardInterrupt:
    print("\nYayın durduruluyor...")
    api.oturum_kapat()
