"""
LG 360 CAM - OSC Sunucusunu Ev Wi-Fi Ağında Tetikleme
=======================================================
BULGU: Kameranın OSC (Open Spherical Camera) HTTP/UDP sunucusu
(com.lge.camera.ccs / CameraControlService), sadece kamera KENDİ
Wi-Fi hotspot'unu yayınlarken açılıyor. Bunu şu sistem yayınını
dinleyerek anlıyor: android.net.wifi.WIFI_AP_STATE_CHANGED

Kamera ev Wi-Fi ağına (station modu) bağlandığında bu yayın hiç
gelmiyor, dolayısıyla OSC sunucusu (port 6624) hiç başlamıyor —
Bluetooth veya fiziksel düğmeye gerek kalmadan bunu çözmenin yolu,
root erişimiyle (install-recovery.sh'e önceden eklenmiş netcat
backdoor, port 9999) bu yayını KENDİMİZ, sahte parametrelerle
göndermek. Uygulama bunu gerçek hotspot açılışı sanıp OSC
sunucusunu başlatıyor; kamera hâlâ ev ağına bağlı kalıyor.

Kullanım:
    python3 enable_osc.py [kamera_ip]
"""

import socket
import sys
import time

from config import Config

BACKDOOR_PORT = 9999
OSC_PORT = 6624
BROADCAST_CMD = (
    "am broadcast -a android.net.wifi.WIFI_AP_STATE_CHANGED "
    "--ei wifi_state 13 --ei previous_wifi_state 12\n"
)


def root_shell(ip: str, cmd: str, wait: float = 2.0) -> str:
    """Root netcat backdoor'a (install-recovery.sh ile kalıcı hale getirilmiş,
    bkz. README 'İleri Seviye: Rootlama') bir komut gönderir ve çıktısını döner."""
    with socket.create_connection((ip, BACKDOOR_PORT), timeout=10) as s:
        s.sendall(cmd.encode() if cmd.endswith("\n") else (cmd + "\n").encode())
        time.sleep(wait)
        s.settimeout(3)
        data = b""
        try:
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        return data.decode(errors="replace")


def osc_is_open(ip: str, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((ip, OSC_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else Config.CAMERA_IP
    print(f"[{ip}] Kamera kontrol ediliyor...")

    if osc_is_open(ip):
        print("OSC sunucusu zaten açık (port 6624 dinliyor). Bir şey yapmaya gerek yok.")
        return

    print("OSC sunucusu kapalı, sahte WIFI_AP_STATE_CHANGED yayını gönderiliyor...")
    try:
        out = root_shell(ip, BROADCAST_CMD)
        print(out.strip() or "(çıktı yok)")
    except OSError as e:
        print(f"HATA: Root backdoor'a (port {BACKDOOR_PORT}) bağlanılamadı: {e}")
        print("Kamera açık mı, ev ağına bağlı mı ve daha önce rootlanmış mı kontrol edin.")
        sys.exit(1)

    for _ in range(5):
        time.sleep(1)
        if osc_is_open(ip):
            print("Başarılı: OSC sunucusu (port 6624) şimdi açık.")
            return

    print("UYARI: Yayından sonra port 6624 hâlâ açılmadı, tekrar deneyin.")
    sys.exit(1)


if __name__ == "__main__":
    main()
