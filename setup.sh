#!/bin/bash
# ==============================================================================
# LG 360 CAM Güvenlik Kamerası - Etkileşimli Kurulum Scripti
# ==============================================================================
# 1. WiFi arayüzlerini listeler.
# 2. Seçilen arayüz ile ağ taraması yapar ve talimatları gösterir.
# 3. Bulunan LG 360 CAM ağına bağlanır.
# 4. İnternet erişimi sağlayan diğer ağ arayüzü ile köprü kurar.
# ==============================================================================

set -e

# --- Renk ve Biçimlendirme Kodları ---
KIRMIZI='\033[0;31m'
YESIL='\033[0;32m'
SARI='\033[0;33m'
MAVI='\033[0;34m'
SIYAN='\033[0;36m'
KALIN='\033[1m'
NC='\033[0m' # Renk sıfırlama

clear
echo -e "${SIYAN}${KALIN}======================================================${NC}"
echo -e "${SIYAN}${KALIN}        LG 360 CAM Securu — Kurulum Sihirbazı         ${NC}"
echo -e "${SIYAN}${KALIN}======================================================${NC}\n"

# --- 0. Root / Sudo Kontrolü ---
if [ "$EUID" -ne 0 ]; then
    echo -e "${KIRMIZI}HATA: Bu script root yetkisi gerektirir.${NC}"
    echo "Lütfen 'sudo bash setup.sh' komutunu kullanın."
    exit 1
fi

# Paket kontrolü
echo -ne "Gerekli paketler kontrol ediliyor... "
if ! command -v nmcli &> /dev/null; then
    echo -e "${KIRMIZI}Eksik!${NC}"
    echo "Lütfen NetworkManager paketini (nmcli) yükleyin."
    exit 1
fi
echo -e "${YESIL}Tamam.${NC}\n"


# ==============================================================================
# 1. WiFi Kartlarını Listeleme ve Seçme
# ==============================================================================
echo -e "${SARI}Adım 1: WiFi Kartı Seçimi${NC}"
echo -e "Kameraya bağlanmak için kullanılacak WiFi kartını seçin.\n"

# Mevcut WiFi cihazlarını bul
mapfile -t WIFI_INTERFACES < <(nmcli -t -f DEVICE,TYPE device | grep wifi | cut -d: -f1)

if [ ${#WIFI_INTERFACES[@]} -eq 0 ]; then
    echo -e "${KIRMIZI}HATA: Sistemde hiçbir WiFi kartı bulunamadı!${NC}"
    echo "Kameraya bağlanabilmek için en az bir WiFi adaptörüne ihtiyacınız var."
    exit 1
fi

echo -e "Mevcut WiFi adaptörleri:"
for i in "${!WIFI_INTERFACES[@]}"; do
    echo -e "  [${YESIL}$((i+1))${NC}] ${WIFI_INTERFACES[$i]}"
done

WIFI_SECIM=""
while true; do
    read -p "Lütfen kullanmak istediğiniz adaptörün numarasını girin [1-${#WIFI_INTERFACES[@]}]: " SECIM_NO
    if [[ "$SECIM_NO" =~ ^[0-9]+$ ]] && [ "$SECIM_NO" -ge 1 ] && [ "$SECIM_NO" -le "${#WIFI_INTERFACES[@]}" ]; then
        WIFI_SECIM="${WIFI_INTERFACES[$((SECIM_NO-1))]}"
        break
    else
        echo -e "${KIRMIZI}Geçersiz seçim. Lütfen tekrar deneyin.${NC}"
    fi
done

echo -e "Seçilen WiFi arayüzü: ${YESIL}$WIFI_SECIM${NC}\n"


# ==============================================================================
# 2. Kamera Bağlantı Yönergesi
# ==============================================================================
echo -e "${SIYAN}${KALIN}======================================================${NC}"
echo -e "${SARI}Adım 2: Kamerayı Hazırlama${NC}\n"
echo -e "Şimdi kameranın WiFi yayını yapmasını sağlamamız gerekiyor:"
echo -e "  1. LG 360 CAM cihazınızın ${KALIN}Güç düğmesine${NC} basarak cihazı açın."
echo -e "  2. Cihaz açıldıktan sonra ${KALIN}Güç Düğmesi ve Çekim (Deklanşör) Düğmesine aynı anda çift tıklayın${NC}."
echo -e "  3. WiFi ışığının mavi renkte yanıp söndüğünden emin olun."
echo -e "     (Işık sabit yandığında veya yanıp söndüğünde kamera WiFi ağı yayınlar.)"
echo ""
read -p "Kameranızı hazır hale getirdiyseniz Taramayı Başlatmak için ENTER'a basın..."


# ==============================================================================
# 3. Ağ Taraması ve Bağlantı
# ==============================================================================
echo -e "\n${SARI}Adım 3: Kamera Ağını Arama${NC}"

KAMERA_AGLARI=()

while true; do
    echo -e "${WIFI_SECIM} üzerinden çevredeki ağlar taranıyor (Lütfen bekleyin)..."
    nmcli dev wifi rescan ifname "$WIFI_SECIM" 2>/dev/null || true
    sleep 3
    
    # "LGR105_" içeren SSID'leri filtrele
    mapfile -t KAMERA_AGLARI < <(nmcli -t -f SSID dev wifi list ifname "$WIFI_SECIM" | grep -E '^LGR105_|^LG-R105_|.OSC$')

    if [ ${#KAMERA_AGLARI[@]} -gt 0 ]; then
        echo -e "\n${YESIL}LG 360 CAM ağı (veya ağları) bulundu!${NC}"
        break
    else
        echo -e "\n${KIRMIZI}Uyarı: Çevrede LG 360 CAM ağı bulunamadı!${NC}"
        read -p "Kameranın açık ve WiFi modunda olduğundan emin olup tekrar aramak için 'e', çıkmak için 'ç' (e/ç): " TEKRAR
        if [[ "${TEKRAR,,}" == "ç" ]]; then
            echo "Çıkılıyor..."
            exit 1
        fi
    fi
done

echo -e "\nBulunan Kamera Ağları:"
for i in "${!KAMERA_AGLARI[@]}"; do
    echo -e "  [${YESIL}$((i+1))${NC}] ${KAMERA_AGLARI[$i]}"
done

SECILEN_SSID=""
if [ ${#KAMERA_AGLARI[@]} -eq 1 ]; then
    SECILEN_SSID="${KAMERA_AGLARI[0]}"
    echo -e "\nSadece ${YESIL}$SECILEN_SSID${NC} bulundu, otomatik seçildi."
else
    while true; do
        read -p "Bağlanmak istediğiniz kamera numarasını girin [1-${#KAMERA_AGLARI[@]}]: " K_NO
        if [[ "$K_NO" =~ ^[0-9]+$ ]] && [ "$K_NO" -ge 1 ] && [ "$K_NO" -le "${#KAMERA_AGLARI[@]}" ]; then
            SECILEN_SSID="${KAMERA_AGLARI[$((K_NO-1))]}"
            break
        else
            echo -e "${KIRMIZI}Geçersiz seçim.${NC}"
        fi
    done
fi

# Şifre türetme (LG CAM varsayılan: "00" + Seri Numarasının son 6 hanesi)
# Genelde SSID "LGR105_123456.OSC" şeklindedir, son 6 rakam şifrenin devamıdır.
SON_ALTI=$(echo "$SECILEN_SSID" | grep -o -E '[A-Z0-9]{6}' | head -1)

if [ -z "$SON_ALTI" ]; then
    read -p "Ağ şifresini bulamadık. Lütfen kameranın WiFi şifresini girin (Genelde 00XXXXXX formatındadır): " SIFRE
else
    SIFRE="00${SON_ALTI}"
    echo -e "Otomatik hesaplanan şifre: ${YESIL}$SIFRE${NC}"
    read -p "Bu şifreyle bağlanmayı deneyelim mi? (e/h) [Varsayılan: e]: " DEVAM
    if [[ "${DEVAM,,}" == "h" ]]; then
        read -p "Lütfen kameranın WiFi şifresini girin: " SIFRE
    fi
fi

echo -e "\n${YESIL}$SECILEN_SSID${NC} ağına bağlanılıyor..."
nmcli dev disconnect "$WIFI_SECIM" &>/dev/null || true
sleep 1

if nmcli dev wifi connect "$SECILEN_SSID" password "$SIFRE" ifname "$WIFI_SECIM"; then
    echo -e "${YESIL}Kameraya MÜKEMMEL bir şekilde bağlanıldı! 🎉${NC}\n"
else
    echo -e "${KIRMIZI}Kameraya BAĞLANILAMADI!${NC}"
    echo "Lütfen şifrenizi (Kamera SSID son 6 hanesinin başına '00' koyduğunuzdan) emin olun ve scripti tekrar çalıştırın."
    exit 1
fi


# ==============================================================================
# 4. Yerel Ağ (LAN) Arayüzünü Bulma ve NAT Köprüsü
# ==============================================================================
echo -e "${SARI}Adım 4: Ağ Köprüsü (NAT Bridge) Ayarları${NC}\n"
echo "Kameraya bağlandıktan sonra, bilgisayarınızın web arayüzünü ev ağınıza sunabilmesi için"
echo "internete/yerel ağa çıkan arayüzü seçmeliyiz."

# Kameranın bağlandığı hariç aktif IP almış olan arayüzleri listele
mapfile -t AKTIF_ARAYUZLER < <(ip -4 route show | grep default | awk '{print $5}' | sort -u)
LAN_SECIM=""

if [ ${#AKTIF_ARAYUZLER[@]} -eq 0 ]; then
    echo -e "${KIRMIZI}Uyarı: İnternete veya yerel ağa bağlı aktif bir varsayılan arayüz bulunamadı.${NC}"
    read -p "Manuel olarak köprü kurulacak arayüzü yazın (örn: eth0 veya wlan1): " LAN_SECIM
else
    # Eğer kameraya bağlanan arayüz, varsayılan ağ olarak görünüyorsa ondan kaçın.
    GECERLI_ARAYUZLER=()
    for ar in "${AKTIF_ARAYUZLER[@]}"; do
        if [ "$ar" != "$WIFI_SECIM" ]; then
            GECERLI_ARAYUZLER+=("$ar")
        fi
    done

    if [ ${#GECERLI_ARAYUZLER[@]} -eq 0 ]; then
        echo -e "${KIRMIZI}Sistemde $WIFI_SECIM haricinde aktif bir ağ bulunamadı! Sadece lokal olarak izleyebilirsiniz.${NC}"
        read -p "Yine de manuel arayüz girmek ister misiniz? (boş bırakırsanız es geçilir): " LAN_SECIM
    elif [ ${#GECERLI_ARAYUZLER[@]} -eq 1 ]; then
        LAN_SECIM="${GECERLI_ARAYUZLER[0]}"
        echo -e "Yerel ağ arayüzü otomatik olarak ${YESIL}$LAN_SECIM${NC} seçildi."
    else
        echo -e "Birden fazla yerel ağ arayüzü bulundu:"
        for i in "${!GECERLI_ARAYUZLER[@]}"; do
            echo -e "  [${YESIL}$((i+1))${NC}] ${GECERLI_ARAYUZLER[$i]}"
        done
        while true; do
            read -p "Lütfen kullanmak istediğiniz LAN arayüzünü seçin [1-${#GECERLI_ARAYUZLER[@]}]: " L_NO
            if [[ "$L_NO" =~ ^[0-9]+$ ]] && [ "$L_NO" -ge 1 ] && [ "$L_NO" -le "${#GECERLI_ARAYUZLER[@]}" ]; then
                LAN_SECIM="${GECERLI_ARAYUZLER[$((L_NO-1))]}"
                break
            else
                echo -e "${KIRMIZI}Geçersiz seçim.${NC}"
            fi
        done
    fi
fi

if [ -n "$LAN_SECIM" ]; then
    echo -e "\nNAT kuralları uygulanıyor ($WIFI_SECIM <--> $LAN_SECIM)..."
    
    # Eskisinde olan setup_network.sh kurallarını çağıralım
    # iptables config:
    sysctl -w net.ipv4.ip_forward=1 > /dev/null
    
    # Eski kuralları temizle
    iptables -t nat -S 2>/dev/null | grep "lgcam_securu" | while read -r kural; do
        iptables -t nat $(echo "$kural" | sed 's/-A/-D/') 2>/dev/null || true
    done
    iptables -S 2>/dev/null | grep "lgcam_securu" | while read -r kural; do
        iptables $(echo "$kural" | sed 's/-A/-D/') 2>/dev/null || true
    done

    # NAT masquerade
    iptables -t nat -A POSTROUTING -o "$LAN_SECIM" \
        -s 192.168.43.0/24 -j MASQUERADE \
        -m comment --comment "lgcam_securu"

    iptables -A FORWARD -i "$WIFI_SECIM" -o "$LAN_SECIM" \
        -j ACCEPT -m comment --comment "lgcam_securu"

    iptables -A FORWARD -i "$LAN_SECIM" -o "$WIFI_SECIM" \
        -m state --state RELATED,ESTABLISHED -j ACCEPT \
        -m comment --comment "lgcam_securu"

    echo -e "${YESIL}IP Forwarding ve NAT köprüsü ('$LAN_SECIM' üzerinden) başarıyla kuruldu!${NC}"
else
    echo -e "${SARI}LAN arayüzü atlandı. Sisteme sadece bu bilgisayardan (localhost) erişebilirsiniz.${NC}"
fi


# ==============================================================================
# BİTİŞ VE BİLGİLENDİRME
# ==============================================================================
echo -e "\n${SIYAN}${KALIN}======================================================${NC}"
echo -e "${YESIL}${KALIN}             TÜM KURULUM TAMAMLANDI                   ${NC}"
echo -e "${SIYAN}${KALIN}======================================================${NC}\n"

# Yerel IP'yi alalım kullanıcının bilmesi için
IP_ADRESI="localhost"
if [ -n "$LAN_SECIM" ]; then
    BIND_IP=$(ip -4 addr show "$LAN_SECIM" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    if [ -n "$BIND_IP" ]; then
        IP_ADRESI="$BIND_IP"
    fi
fi

echo -e "Şimdi güvenlik kamerası sisteminizi başlatabilirsiniz!"
echo -e "Terminalde şu komutu çalıştırın:"
echo -e "  ${YESIL}source venv/bin/activate${NC}"
echo -e "  ${YESIL}python main.py${NC}\n"
echo -e "Ardından web tarayıcınızdan panelinize gidin:"
echo -e "  ${KALIN}http://$IP_ADRESI:5555${NC}"
echo -e "  (Sadece kendi cihazınızdan bakacaksanız ${KALIN}http://localhost:5555${NC} de geçerlidir.)\n"
