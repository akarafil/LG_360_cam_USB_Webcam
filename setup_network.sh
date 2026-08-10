#!/bin/bash
# ==============================================================================
# LG 360 CAM Güvenlik Kamerası - Ağ Kurulum Scripti
# ==============================================================================
# Bu script bilgisayarı NAT bridge olarak yapılandırır.
# WiFi → kamera AP, Ethernet → ev ağı
#
# Kullanım: sudo bash setup_network.sh [wifi_arayuz] [lan_arayuz]
# Örnek:    sudo bash setup_network.sh wlan0 eth0
# ==============================================================================

set -e

# Renk kodları
KIRMIZI='\033[0;31m'
YESIL='\033[0;32m'
SARI='\033[0;33m'
MAVI='\033[0;34m'
NC='\033[0m' # Renk sıfırlama

# Varsayılan arayüzler
WIFI_ARAYUZ="${1:-wlan0}"
LAN_ARAYUZ="${2:-eth0}"

echo -e "${MAVI}=======================================${NC}"
echo -e "${MAVI}  LG 360 CAM - Ağ Kurulumu${NC}"
echo -e "${MAVI}=======================================${NC}"
echo ""
echo -e "WiFi arayüzü:     ${YESIL}${WIFI_ARAYUZ}${NC} (kamera bağlantısı)"
echo -e "LAN arayüzü:      ${YESIL}${LAN_ARAYUZ}${NC} (ev ağı bağlantısı)"
echo ""

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    echo -e "${KIRMIZI}HATA: Bu script root olarak çalıştırılmalıdır.${NC}"
    echo "Kullanım: sudo bash $0"
    exit 1
fi

# ================================================
# 1. Gerekli paketleri kontrol et / yükle
# ================================================
echo -e "${SARI}[1/5] Gerekli paketler kontrol ediliyor...${NC}"

gerekli_paketler="iptables iproute2 network-manager"
eksik_paketler=""

for paket in $gerekli_paketler; do
    if ! dpkg -l | grep -q "^ii  ${paket}"; then
        eksik_paketler="${eksik_paketler} ${paket}"
    fi
done

if [ -n "$eksik_paketler" ]; then
    echo -e "Eksik paketler yükleniyor:${eksik_paketler}"
    apt-get update -qq
    apt-get install -y -qq $eksik_paketler
fi
echo -e "${YESIL}  ✓ Paketler tamam${NC}"

# ================================================
# 2. IP Forwarding aktifleştir
# ================================================
echo -e "${SARI}[2/5] IP forwarding aktifleştiriliyor...${NC}"

# Anlık olarak aktifleştir
sysctl -w net.ipv4.ip_forward=1 > /dev/null

# Kalıcı yap
if ! grep -q "^net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    echo -e "${YESIL}  ✓ IP forwarding kalıcı olarak aktifleştirildi${NC}"
else
    echo -e "${YESIL}  ✓ IP forwarding zaten aktif${NC}"
fi

# ================================================
# 3. iptables NAT kuralları
# ================================================
echo -e "${SARI}[3/5] NAT kuralları yapılandırılıyor...${NC}"

# Önceki lgcam kurallarını temizle
iptables -t nat -S 2>/dev/null | grep "lgcam_securu" | while read -r kural; do
    iptables -t nat $(echo "$kural" | sed 's/-A/-D/') 2>/dev/null || true
done
iptables -S 2>/dev/null | grep "lgcam_securu" | while read -r kural; do
    iptables $(echo "$kural" | sed 's/-A/-D/') 2>/dev/null || true
done

# NAT masquerade (kamera subnet → ev ağı)
iptables -t nat -A POSTROUTING -o ${LAN_ARAYUZ} \
    -s 192.168.43.0/24 -j MASQUERADE \
    -m comment --comment "lgcam_securu"

# Forward kuralları
iptables -A FORWARD -i ${WIFI_ARAYUZ} -o ${LAN_ARAYUZ} \
    -j ACCEPT -m comment --comment "lgcam_securu"

iptables -A FORWARD -i ${LAN_ARAYUZ} -o ${WIFI_ARAYUZ} \
    -m state --state RELATED,ESTABLISHED -j ACCEPT \
    -m comment --comment "lgcam_securu"

echo -e "${YESIL}  ✓ NAT kuralları eklendi${NC}"

# ================================================
# 4. iptables kurallarını kalıcı yap
# ================================================
echo -e "${SARI}[4/5] Kurallar kalıcı yapılıyor...${NC}"

# iptables-persistent yüklü mü kontrol et
if dpkg -l | grep -q "^ii  iptables-persistent"; then
    netfilter-persistent save 2>/dev/null
    echo -e "${YESIL}  ✓ Kurallar netfilter-persistent ile kaydedildi${NC}"
else
    # Manuel kaydet
    mkdir -p /etc/iptables
    iptables-save > /etc/iptables/rules.v4
    echo -e "${YESIL}  ✓ Kurallar /etc/iptables/rules.v4 dosyasına kaydedildi${NC}"

    # Başlangıçta yüklenecek servis oluştur
    cat > /etc/systemd/system/lgcam-iptables.service << 'EOF'
[Unit]
Description=LG CAM Securu iptables Kuralları
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iptables-restore /etc/iptables/rules.v4
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    systemctl enable lgcam-iptables.service 2>/dev/null
    echo -e "${YESIL}  ✓ Başlangıç servisi oluşturuldu${NC}"
fi

# ================================================
# 5. Durum özeti
# ================================================
echo -e "${SARI}[5/5] Yapılandırma özeti...${NC}"
echo ""
echo -e "${MAVI}=======================================${NC}"
echo -e "${MAVI}  Ağ Yapılandırması Tamamlandı${NC}"
echo -e "${MAVI}=======================================${NC}"
echo ""
echo -e "IP Forwarding:    ${YESIL}Aktif${NC}"
echo -e "NAT Masquerade:   ${YESIL}Aktif${NC} (192.168.43.0/24 → ${LAN_ARAYUZ})"
echo ""
echo -e "${SARI}Sonraki adımlar:${NC}"
echo "  1. Kamera WiFi'sine bağlanmak için:"
echo "     nmcli dev wifi connect 'LGR105_XXXXXX' password '00XXXXXX' ifname ${WIFI_ARAYUZ}"
echo ""
echo "  2. Uygulamayı başlatmak için:"
echo "     python3 main.py"
echo ""
echo "  3. Web arayüzüne erişim:"
echo "     http://localhost:5555"
echo "     http://<bilgisayar-ip>:5555 (ev ağından)"
echo ""
echo -e "${MAVI}=======================================${NC}"
