# LG 360 CAM USB Webcam Hack 🚀

![LG 360 CAM](https://img.shields.io/badge/LG-360_CAM-red.svg) ![Platform](https://img.shields.io/badge/Platform-Linux-blue.svg)

[TR] LG 360 CAM (LG-R105) cihazınızı kablosuz ağınız (Wi-Fi) üzerinden bilgisayarınıza standart bir USB webcam gibi bağlamanızı sağlayan araç seti.

[EN] A toolkit that lets your LG 360 CAM (LG-R105) act as a standard webcam on Linux, streaming over Wi-Fi into a `/dev/video*` virtual camera device.

> Bu kılavuz, projeyi hiç görmemiş biri için sıfırdan yazılmıştır. Sırasıyla uygulayın; her adımın sonunda ne görmeniz gerektiği belirtilmiştir.

---

## 📦 İçindekiler

1. [Nasıl Çalışır?](#-nasıl-çalışır)
2. [Gereksinimler](#-gereksinimler)
3. [Adım 1 — Bağımlılıkları Kurma](#adım-1--bağımlılıkları-kurma)
4. [Adım 2 — Sanal Webcam Cihazını Oluşturma](#adım-2--sanal-webcam-cihazını-oluşturma)
5. [Adım 3 — Kamerayı Wi-Fi Yayın Moduna Alma](#adım-3--kamerayı-wi-fi-yayın-moduna-alma)
6. [Adım 4 — Bilgisayarı Kamera Ağına Bağlama](#adım-4--bilgisayarı-kamera-ağına-bağlama)
7. [Adım 5 — Yayını Başlatma (Webcam Olarak Kullanma)](#adım-5--yayını-başlatma-webcam-olarak-kullanma)
8. [Sorun Giderme](#-sorun-giderme)
9. [İleri Seviye: Rootlama ve Otomatik Bağlantı](#️-ileri-seviye-rootlama-ve-otomatik-bağlantı-opsiyonel)
10. [Proje Yapısı](#-proje-yapısı)

---

## 🔍 Nasıl Çalışır?

LG 360 CAM, standart bir USB Video Class (UVC) webcam değildir — bilgisayara USB ile takıldığında sadece **şarj modunda** görünür, `/dev/video*` cihazı oluşturmaz. Ancak kamera, kendi Wi-Fi erişim noktasını (AP) açtığında Open Spherical Camera (OSC) adlı bir HTTP API üzerinden canlı görüntüyü **UDP video akışı** olarak yayınlayabilir.

Bu proje şu zinciri kurar:

```
LG 360 CAM  --(Wi-Fi AP)-->  Bilgisayar  --(OSC API ile başlat)-->  UDP video akışı
    --(ffmpeg ile kırp/dönüştür)-->  v4l2loopback  -->  /dev/video9 (sanal webcam)
```

`/dev/video9` oluştuktan sonra Linux'taki **her uygulama** (tarayıcı görüntülü görüşme, OBS, Zoom, `cheese` vb.) bunu normal bir webcam gibi seçebilir.

USB kablosu bu senaryoda sadece **güç/şarj** için kullanılır; veri her zaman Wi-Fi üzerinden gider.

---

## 🛠 Gereksinimler

### Donanım
- LG 360 CAM (LG-R105)
- Bilgisayarda bir Wi-Fi kartı (kameraya bağlanmak için)
- USB kablosu (kamerayı şarjda/açık tutmak için, opsiyonel ama önerilir)

### Yazılım (Linux)
| Araç | Kurulum (Arch/CachyOS) | Kurulum (Debian/Ubuntu) |
|---|---|---|
| ffmpeg | `sudo pacman -S ffmpeg` | `sudo apt install ffmpeg` |
| v4l2loopback | `sudo pacman -S v4l2loopback-dkms` | `sudo apt install v4l2loopback-dkms v4l2loopback-utils` |
| NetworkManager (`nmcli`) | `sudo pacman -S networkmanager` | `sudo apt install network-manager` |
| Python 3 + `requests` | `sudo pacman -S python python-requests` | `sudo apt install python3 python3-requests` |

Kurulumdan sonra her birinin var olduğunu doğrulayın:
```bash
ffmpeg -version && v4l2-ctl --version && nmcli --version && python3 -c "import requests"
```

---

## Adım 1 — Bağımlılıkları Kurma

Yukarıdaki tablodaki paketleri kurun. Python bağımlılıkları için proje kökünde:
```bash
pip install -r requirements.txt
```
> Not: `requirements.txt` içindeki `flask`, `opencv-python`, `bleak` gibi paketler bu projenin *ileride* eklenecek web paneli/hareket algılama özellikleri içindir; temel webcam akışı için sadece `requests` yeterlidir.

**Doğrulama:** Komutlar hatasız çalıştıysa bu adım tamam.

---

## Adım 2 — Sanal Webcam Cihazını Oluşturma

`v4l2loopback` çekirdek modülünü, adı ve numarası sabit bir sanal kamera ile yükleyin:
```bash
sudo modprobe v4l2loopback video_nr=9 card_label="LG 360 CAM" exclusive_caps=1
```

**Doğrulama:**
```bash
v4l2-ctl --list-devices
```
Çıktıda `LG 360 CAM` etiketiyle `/dev/video9` görünmeli.

> Her yeniden başlatmada bu komutu tekrar çalıştırmanız gerekir. Kalıcı yapmak isterseniz `/etc/modules-load.d/v4l2loopback.conf` içine `v4l2loopback` ve `/etc/modprobe.d/v4l2loopback.conf` içine `options v4l2loopback video_nr=9 card_label="LG 360 CAM" exclusive_caps=1` satırlarını ekleyin.

---

## Adım 3 — Kamerayı Wi-Fi Yayın Moduna Alma

1. LG 360 CAM'in **Güç düğmesine** basarak cihazı açın.
2. Cihaz açıldıktan sonra **Güç Düğmesi ve Çekim (Deklanşör) Düğmesine aynı anda çift tıklayın**.
3. Kameranın üzerindeki Wi-Fi ışığının yanıp söndüğünü/yandığını görün — bu, kameranın kendi Wi-Fi ağını (`LGR105_XXXXXX` gibi bir SSID) yayınlamaya başladığı anlamına gelir.

**Doğrulama:** Telefonunuzun veya bilgisayarınızın Wi-Fi ağ listesinde `LGR105_` ile başlayan bir ağ görünmeli.

---

## Adım 4 — Bilgisayarı Kamera Ağına Bağlama

Otomatik ve interaktif kurulum betiğini kullanın:
```bash
sudo bash setup.sh
```
Bu betik sizden sırasıyla ister:
- Kullanılacak Wi-Fi kartını seçmenizi,
- Kamera ağını taramasını ve bulduğunda bağlanmasını (şifre genelde `00` + SSID'nin son 6 hanesi, betik bunu otomatik dener),
- İnternete çıkan başka bir arayüz varsa (ör. Ethernet) onunla NAT köprüsü kurmasını (opsiyonel, sadece uzaktan erişim istiyorsanız gerekli).

**Manuel bağlanmak isterseniz:**
```bash
nmcli dev wifi connect "LGR105_XXXXXX" password "00XXXXXX" ifname wlan0
```

**Doğrulama:**
```bash
ping 192.168.43.1
```
Kameradan yanıt almalısınız. Bu IP, kameranın OSC API adresidir (`config.py` içinde `CAMERA_IP` olarak tanımlı).

---

## Adım 5 — Yayını Başlatma (Webcam Olarak Kullanma)

```bash
chmod +x baslat.sh
./baslat.sh
```

Bu komut sırasıyla:
1. `start_stream.py` ile kameraya OSC API üzerinden bağlanır, oturum açar ve UDP video yayınını başlatır (`camera.updateSession` ile oturumu canlı tutar),
2. `ffmpeg` ile gelen UDP akışını 640x480 olacak şekilde merkezden kırpar ve `/dev/video9` sanal kamerasına yazar.

**Doğrulama:**
```bash
ffplay /dev/video9
```
veya herhangi bir görüntülü görüşme/kayıt uygulamasını açıp kamera listesinden **LG 360 CAM**'i seçin. Görüntü akıyorsa kurulum tamamlanmıştır. 🎉

Durdurmak için terminalde `CTRL+C`.

---

## 🩺 Sorun Giderme

| Belirti | Olası Sebep / Çözüm |
|---|---|
| `setup.sh`: "Sistemde hiçbir WiFi kartı bulunamadı" | `nmcli device` ile Wi-Fi kartınızın görünüp görünmediğini kontrol edin, sürücü eksik olabilir. |
| Kamera ağı taramada çıkmıyor | Adım 3'ü tekrarlayın (çift tık yeterince hızlı olmayabilir), kamera bataryasını/şarjını kontrol edin. |
| `nmcli dev wifi connect` şifre hatası veriyor | SSID'nin tam son 6 hanesini kontrol edip şifreyi `00XXXXXX` formatında elle girin. |
| `ping 192.168.43.1` yanıt vermiyor | Bilgisayar başka bir ağa (ör. Ethernet varsayılan rotası) öncelik veriyor olabilir; `ip route` ile kontrol edin. |
| `ffplay /dev/video9` siyah ekran / görüntü yok | Kamera "video" capture moduna geçemiyor olabilir; `camera_api.py` içindeki `preview_format_listele()` ile desteklenen formatları loglayın. |
| Video donuk/çok düşük FPS | Kamera varsayılanda 1 FPS preview gönderebilir; `camera_api.py` bunu `captureMode=video` ayarıyla düzeltmeye çalışır, loglarda hangi modun tutunduğunu kontrol edin. |
| Kamera birkaç dakika sonra kapanıyor | `python3 disable_sleep.py` çalıştırarak otomatik uyku/kapanmayı devre dışı bırakın (her açılışta tekrar gerekebilir, kalıcı çözüm için aşağıdaki "İleri Seviye" bölümüne bakın). |

---

## ⚠️ İleri Seviye: Rootlama ve Otomatik Bağlantı (Opsiyonel)

Yukarıdaki adımlar **her açılışta manuel** olarak kameranın Wi-Fi moduna alınmasını gerektirir. Kamerayı kalıcı bir güvenlik kamerası gibi kullanmak isteyenler için `lglaf/` aracıyla cihaza kök (root) erişimi alıp, cihaz her açıldığında otomatik Wi-Fi'ye bağlanan bir betik enjekte etmek mümkündür.

**Bu adım geri alınması zor / riskli bir işlemdir, sadece temel webcam akışını (Adım 1-5) test edip çalıştığından emin olduktan sonra deneyin.**

1. `lglaf/` dizinindeki araçla cihazın Download/LAF modundan kök erişimi alın (bkz. `lglaf/README.md`).
2. `busybox-armv7l` ve gerekli araçları cihaza kopyalayın.
3. `/system/bin/install-recovery.sh` içine, cihaz açıldığında otomatik Wi-Fi bağlantısını tetikleyen bir komut dosyası ekleyin.
4. Cihazı ev Wi-Fi ağınıza bağlamak için `scrcpy` ile kameranın gizli Android ekranına erişebilirsiniz:
   ```bash
   adb shell am start -a android.settings.WIFI_SETTINGS
   scrcpy
   ```
   Açılan ekrandan ev ağınızı seçip bağlanın.

Bu bölüm henüz uçtan uca doğrulanmadı — ilerleyen adımlarda bu README ve `log.md` güncellenecek.

---

## 📁 Proje Yapısı

```
lg_cam/
├── README.md            # Bu dosya
├── log.md                # Geliştirme günlüğü (her adım burada kayıtlı)
├── requirements.txt      # Python bağımlılıkları
├── config.py             # Merkezi yapılandırma (kamera IP, port, stream ayarları...)
├── config.json            # config.py için kullanıcı override'ları
├── camera_api.py           # LG 360 CAM OSC API istemcisi (oturum aç, yayın başlat/durdur)
├── start_stream.py         # camera_api.py'yi kullanıp yayını başlatan ve canlı tutan betik
├── disable_sleep.py         # Kameranın otomatik uyku/kapanmasını devre dışı bırakır
├── baslat.sh                # Tüm zinciri başlatan ana betik (stream + ffmpeg → /dev/video9)
├── setup.sh                  # İnteraktif Wi-Fi bağlantı + NAT köprüsü sihirbazı
├── setup_network.sh           # setup.sh'nin komut satırından çalıştırılabilen versiyonu
├── busybox-armv7l              # Rootlama sonrası kameraya yüklenecek statik busybox (ileri seviye)
└── lglaf/                       # LG cihazlarında Download/LAF modu üzerinden root erişim aracı
```

> `main.py` (Flask tabanlı web paneli, hareket algılama, kayıt) henüz yazılmadı — bu, temel webcam akışından sonraki bir sonraki aşama olarak planlanıyor. Güncel durum için `log.md` dosyasına bakın.

---
*Disclaimer: Bu proje LG 360 CAM cihazının sınırlarını aşmak için eğitim ve araştırma amaçlı geliştirilmiştir. Cihaza donanımsal zarar verme ihtimali düşüktür ancak tüm sorumluluk kullanıcıya aittir.*
