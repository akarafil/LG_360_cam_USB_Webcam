#!/bin/bash
# ==============================================================================
# LG 360 CAM - Tek Komutla Webcam Başlatıcı
# ==============================================================================
# Bu script tüm süreci baştan sona kontrol edip gerekeni otomatik yapar:
#   1. Sanal webcam cihazı (/dev/video9)
#   2. Kameranın USB/ADB bağlantısı (uykudaysa uyandırmanızı ister)
#   3. Kameranın uyku moduna geçmesini engelleme
#   4. Kameranın ev ağındaki IP'sini bulma (değiştiyse config.py'yi günceller)
#   5. OSC sunucusunu tetikleme (sahte "hotspot açıldı" sinyali)
#   6. Güvenlik duvarında UDP 1234'ü açma
#   7. Önceki yayınları temizleme
#   8. Yayını başlatma
#   9. Görüntü ayarları panelini açma (http://localhost:5555)
#
# Kullanım: ./webcam.sh
# ==============================================================================

set -u

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
PY="$DIR/venv/bin/python"

KIRMIZI='\033[0;31m'
YESIL='\033[0;32m'
SARI='\033[0;33m'
MAVI='\033[0;34m'
KALIN='\033[1m'
NC='\033[0m'

STREAM_LOG="/tmp/lgcam_stream.log"
STREAM_PID=""

adim() { echo -e "\n${MAVI}${KALIN}[Adım $1] $2${NC}"; }
tamam() { echo -e "${YESIL}  ✓ $1${NC}"; }
hata()  { echo -e "${KIRMIZI}  ✗ $1${NC}"; }
bilgi() { echo -e "${SARI}  $1${NC}"; }

temizlik_ve_cikis() {
    echo ""
    [ -n "$STREAM_PID" ] && kill "$STREAM_PID" 2>/dev/null
    pkill -f "start_stream.py" 2>/dev/null
    pkill -f "panel.py" 2>/dev/null
    echo -e "${SARI}Yayın durduruldu.${NC}"
    exit 0
}
trap temizlik_ve_cikis INT TERM

echo -e "${MAVI}${KALIN}======================================================${NC}"
echo -e "${MAVI}${KALIN}   LG 360 CAM - Webcam Başlatıcı (tüm süreç otomatik)  ${NC}"
echo -e "${MAVI}${KALIN}======================================================${NC}"

# ------------------------------------------------------------------
# Adım 1: Sanal webcam cihazı
# ------------------------------------------------------------------
adim 1 "Sanal webcam cihazı (/dev/video9) kontrol ediliyor"
if [ ! -e /dev/video9 ]; then
    bilgi "/dev/video9 yok, v4l2loopback yükleniyor (sudo şifresi istenebilir)..."
    sudo modprobe v4l2loopback video_nr=9 card_label="LG 360 CAM" exclusive_caps=1
    sleep 1
fi
if [ -e /dev/video9 ]; then
    tamam "/dev/video9 hazır"
else
    hata "/dev/video9 oluşturulamadı, çıkılıyor."
    exit 1
fi

# ------------------------------------------------------------------
# Adım 2: Kameranın USB/ADB bağlantısı
# ------------------------------------------------------------------
adim 2 "Kameranın USB/ADB bağlantısı kontrol ediliyor"
adb start-server >/dev/null 2>&1

while ! adb devices | grep -q "device$"; do
    hata "Kamera adb ile görünmüyor (uykuda/Charge mode'da olabilir)."
    bilgi "Kameranın güç düğmesine kısaca basıp uyandırın."
    read -r -p "  Uyandırdıysanız ENTER'a basın (tekrar denenecek), çıkmak için CTRL+C: "
    adb kill-server >/dev/null 2>&1
    adb start-server >/dev/null 2>&1
    sleep 2
done
CIHAZ=$(adb devices | grep "device$" | head -1 | awk '{print $1}')
tamam "Kamera bağlı: $CIHAZ"

# ------------------------------------------------------------------
# Adım 3: Uyku modunu engelleme
# ------------------------------------------------------------------
adim 3 "Ekran/uyku zaman aşımı devre dışı bırakılıyor"
adb shell settings put system screen_off_timeout 2147483647 >/dev/null 2>&1
adb shell svc power stayon true >/dev/null 2>&1
tamam "Uyku modu engellendi"

# ------------------------------------------------------------------
# Adım 4: Kameranın ev ağı IP'si
# ------------------------------------------------------------------
adim 4 "Kameranın ev ağındaki IP'si kontrol ediliyor"
CAMERA_IP=$(adb shell ip addr show wlan0 2>/dev/null | grep -oP 'inet \K[\d.]+' | head -1)
if [ -z "$CAMERA_IP" ]; then
    hata "Kamera Wi-Fi IP'si alınamadı. Kameranın ev ağınıza bağlı olduğundan emin olun (README Adım 4)."
    exit 1
fi
YAPILANDIRILAN_IP=$(PY -c "from config import Config; print(Config.CAMERA_IP)" 2>/dev/null)
if [ "$CAMERA_IP" != "$YAPILANDIRILAN_IP" ]; then
    bilgi "IP değişmiş ($YAPILANDIRILAN_IP -> $CAMERA_IP), config.py güncelleniyor..."
    sed -i "s/CAMERA_IP = \"[0-9.]*\"/CAMERA_IP = \"$CAMERA_IP\"/" config.py
fi
tamam "Kamera IP: $CAMERA_IP"

# ------------------------------------------------------------------
# Adım 5: OSC sunucusunu tetikleme
# ------------------------------------------------------------------
adim 5 "OSC sunucusu kontrol ediliyor / tetikleniyor"
if ! "$PY" enable_osc.py "$CAMERA_IP"; then
    hata "OSC sunucusu açılamadı, çıkılıyor."
    exit 1
fi
tamam "OSC sunucusu açık (port 6624)"

# ------------------------------------------------------------------
# Adım 6: Güvenlik duvarı (UDP 1234)
# ------------------------------------------------------------------
adim 6 "Güvenlik duvarı (UDP 1234) kontrol ediliyor"
if command -v ufw >/dev/null 2>&1; then
    if sudo ufw status | grep -q "1234/udp"; then
        tamam "UDP 1234 zaten izinli"
    else
        bilgi "UDP 1234 izinli değil, ekleniyor (sudo şifresi istenebilir)..."
        if sudo ufw allow 1234/udp >/dev/null; then
            tamam "UDP 1234 izin verildi"
        else
            hata "UDP 1234 eklenemedi (sudo başarısız oldu) — görüntü gelmezse elle çalıştırın: sudo ufw allow 1234/udp"
        fi
    fi
else
    bilgi "ufw bulunamadı, güvenlik duvarı kontrolü atlanıyor (başka bir güvenlik duvarınız varsa UDP 1234'ü elle açın)."
fi

# ------------------------------------------------------------------
# Adım 7: Önceki yayınları temizleme
# ------------------------------------------------------------------
adim 7 "Önceki yayınlar temizleniyor"
pkill -f "start_stream.py" 2>/dev/null
pkill -f "panel.py" 2>/dev/null
pkill -f "ffmpeg.*video9" 2>/dev/null
sleep 1
tamam "Temizlendi"

# ------------------------------------------------------------------
# Adım 8: Yayını başlatma
# ------------------------------------------------------------------
adim 8 "Yayın başlatılıyor"
"$PY" start_stream.py > "$STREAM_LOG" 2>&1 &
STREAM_PID=$!
sleep 4
if ! kill -0 "$STREAM_PID" 2>/dev/null; then
    hata "start_stream.py başlamadı. Log:"
    cat "$STREAM_LOG"
    exit 1
fi
tamam "OSC oturumu canlı tutuluyor (arka plan PID $STREAM_PID)"

# ------------------------------------------------------------------
# Adım 9: Görüntü ayarları panelini açma
# ------------------------------------------------------------------
adim 9 "Görüntü ayarları paneli açılıyor"
echo ""
echo -e "${YESIL}${KALIN}Panel: http://localhost:${NC}${YESIL}${KALIN}5555${NC}"
echo "Kayıtlı görüntülü görüşme/kayıt uygulamalarında 'LG 360 CAM' kamerasını seçebilirsiniz."
echo "Çıkmak için CTRL+C."
echo "-----------------------------------"

"$PY" panel.py

temizlik_ve_cikis
