#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==================================="
echo "LG 360 CAM - Canlı Webcam Başlatıcı"
echo "==================================="

echo "Önceki yayınlar temizleniyor..."
killall ffmpeg 2>/dev/null

echo "OSC sunucusu (kamera ev ağındayken) tetikleniyor..."
python3 enable_osc.py || { echo "OSC sunucusu açılamadı, çıkılıyor."; exit 1; }

echo "Kamera API'sine bağlanılıyor ve yayın başlatılıyor..."
# Python betiğini arkaplanda çalıştır (oturumu canlı tutması için)
python3 start_stream.py &
PYTHON_PID=$!

echo "Kameranın hazırlık yapması için bekleniyor..."
sleep 4

echo "Görüntü /dev/video9 (Webcam) cihazına aktarılıyor..."
echo "Çıkmak için CTRL+C tuşlarına basabilirsiniz."
echo "-----------------------------------"

# FFMPEG komutunu çalıştır (Geniş açıyı daraltmak için merkezden 640x480 kırpma yapıldı)
ffmpeg -v warning -fflags nobuffer -flags low_delay -i "udp://@:1234?reuse=1" -threads 1 -vf "crop=640:480" -f v4l2 /dev/video9

# Eğer ffmpeg kapanırsa (örn: kullanıcı CTRL+C yaparsa), arkaplandaki python betiğini de sonlandır
kill $PYTHON_PID 2>/dev/null
echo "Yayın başarıyla kapatıldı."
