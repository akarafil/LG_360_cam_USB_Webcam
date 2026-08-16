# LG 360 CAM USB Webcam Hack 🚀

![LG 360 CAM](https://img.shields.io/badge/LG-360_CAM-red.svg) ![Platform](https://img.shields.io/badge/Platform-Linux-blue.svg)

[TR] LG 360 CAM (LG-R105) cihazınızı kablosuz ağınız (Wi-Fi) üzerinden bilgisayarınıza standart bir USB webcam gibi bağlamanızı sağlayan araç seti.

[EN] A toolkit that lets your LG 360 CAM (LG-R105) act as a standard webcam on Linux, streaming over Wi-Fi into a `/dev/video*` virtual camera device.

> Bu kılavuz, projeyi hiç görmemiş biri için sıfırdan yazılmıştır. Sırasıyla uygulayın; her adımın sonunda ne görmeniz gerektiği belirtilmiştir.

---

## 🚀 Hızlı Başlangıç (kamera zaten rootlanmış ve ev ağına bağlıysa)

Adım 3 (rootlama) ve Adım 4 (ev Wi-Fi'ye bağlama) bir kere yapıldıktan sonra, her seferinde tek komut yeterli:

```bash
./webcam.sh
```

Bu script v4l2loopback'i yükler, kamerayı kontrol eder (uykudaysa uyandırmanızı ister), OSC sunucusunu tetikler, güvenlik duvarını ayarlar, yayını başlatır ve son olarak **görüntü ayarları panelini** açar: **http://localhost:5555** — buradan parlaklık, kontrast, doygunluk, keskinlik, gürültü azaltma, gamma, **lens açısı/kırpma** (zoom/normal/geniş) ve **kamera çözünürlüğü**'nü canlı önizlemeli kaydırma çubuklarıyla ayarlayabilirsiniz. Çıkmak için terminalde `CTRL+C`.

> Her ayar değişikliği, kameranın kendi yayınının da temiz bir şekilde yeniden başlamasını gerektirir (~5-15 saniye sürebilir, bu sırada önizleme kısa süre donuk kalır). Kaydırma çubuğunu hızlı hızlı sürüklemek sorun değil — panel art arda gelen değişiklikleri tek bir yeniden başlatmada birleştirir.

İlk kurulum için (rootlama dahil) aşağıdaki adımları sırayla takip edin.

---

## 📦 İçindekiler

1. [Nasıl Çalışır?](#-nasıl-çalışır)
2. [Gereksinimler](#-gereksinimler)
3. [Adım 1 — Bağımlılıkları Kurma](#adım-1--bağımlılıkları-kurma)
4. [Adım 2 — Sanal Webcam Cihazını Oluşturma](#adım-2--sanal-webcam-cihazını-oluşturma)
5. [Adım 3 — Kamerayı Rootlama (bir kere yapılır)](#adım-3--kamerayı-rootlama-bir-kere-yapılır)
6. [Adım 4 — Kamerayı Ev Wi-Fi Ağına Bağlama](#adım-4--kamerayı-ev-wi-fi-ağına-bağlama)
7. [Adım 5 — Yayını Başlatma (Webcam Olarak Kullanma)](#adım-5--yayını-başlatma-webcam-olarak-kullanma)
8. [Sorun Giderme](#-sorun-giderme)
9. [Nasıl Çözüldü: OSC Sunucusunun Bluetooth'suz Tetiklenmesi](#-nasıl-çözüldü-osc-sunucusunun-bluetoothsuz-tetiklenmesi)
10. [Proje Yapısı](#-proje-yapısı)

---

## 🔍 Nasıl Çalışır?

LG 360 CAM, standart bir USB Video Class (UVC) webcam değildir — bilgisayara USB ile takıldığında sadece **şarj modunda** görünür, `/dev/video*` cihazı oluşturmaz. Kamera, Open Spherical Camera (OSC) adlı bir HTTP API'ye sahip ve bunun üzerinden canlı görüntüyü **UDP video akışı** olarak yayınlayabiliyor — ama resmi olarak bunu sadece kendi Wi-Fi hotspot'unu açtığında (ve bunu genelde Bluetooth üzerinden tetiklediğinde) yapıyor.

Bu projenin bulduğu kısayol: kamerayı **rootlayıp**, "hotspot açıldı" sistem sinyalini **sahte olarak** göndererek, kamera **ev Wi-Fi ağınıza bağlıyken bile** (station modu) OSC sunucusunu açık tutmasını sağlıyoruz. Detaylı teknik açıklama için [Nasıl Çözüldü](#-nasıl-çözüldü-osc-sunucusunun-bluetoothsuz-tetiklenmesi) bölümüne bakın.

Kurulan zincir:

```
LG 360 CAM (ev Wi-Fi ağınızda) --(sahte "hotspot açıldı" sinyali)--> OSC API açılır
    --(OSC API ile _startPreview)--> UDP video akışı --(ffmpeg ile kırp/dönüştür)-->
    v4l2loopback --> /dev/video9 (sanal webcam)
```

`/dev/video9` oluştuktan sonra Linux'taki **her uygulama** (tarayıcı görüntülü görüşme, OBS, Zoom, `cheese` vb.) bunu normal bir webcam gibi seçebilir.

USB kablosu bu senaryoda sadece **güç** için kullanılır (kamera pilini boşaltmasın diye); veri hep Wi-Fi üzerinden, ev ağınız içinde gider — Bluetooth'a hiç gerek yok.

---

## 🛠 Gereksinimler

### Donanım
- LG 360 CAM (LG-R105)
- Bilgisayar, kameranızla **aynı ev Wi-Fi/LAN ağında** (kendisi Wi-Fi ile de Ethernet ile de bağlı olabilir — kamerayla aynı ağda olması yeterli)
- USB kablosu (kamerayı sürekli açık/şarjlı tutmak için önerilir; veri için gerekli değil)

### Yazılım (Linux)
| Araç | Kurulum (Arch/CachyOS) | Kurulum (Debian/Ubuntu) |
|---|---|---|
| ffmpeg | `sudo pacman -S ffmpeg` | `sudo apt install ffmpeg` |
| v4l2loopback | `sudo pacman -S v4l2loopback-dkms` | `sudo apt install v4l2loopback-dkms v4l2loopback-utils` |
| adb (android-tools) | `sudo pacman -S android-tools` | `sudo apt install android-tools-adb` |
| Python 3 + `requests` | `sudo pacman -S python python-requests` | `sudo apt install python3 python3-requests` |

Kurulumdan sonra her birinin var olduğunu doğrulayın:
```bash
ffmpeg -version && v4l2-ctl --version && adb --version && python3 -c "import requests"
```

> **Güvenlik duvarı notu:** Eğer `ufw` (veya başka bir güvenlik duvarı) kullanıyorsanız, video akışı UDP paket olarak bilgisayarınıza geleceği için gelen bağlantılara varsayılan `deny` politikası akışı sessizce engeller. Adım 5'te bunu nasıl açacağınız anlatılıyor.

---

## Adım 1 — Bağımlılıkları Kurma

Yukarıdaki tablodaki paketleri kurun. Python bağımlılıkları için proje kökünde:
```bash
pip install -r requirements.txt
```
> Not: `flask` ve `opencv-python` görüntü ayarları paneli (`panel.py`) için kullanılıyor. `bleak` ise henüz kullanılmayan, ileride eklenebilecek bir Bluetooth özelliği içindir. Bu paketler proje köküne oluşturulan `venv/` içine kurulur (bkz. Adım 3), sistem pip'ine değil.

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

## Adım 3 — Kamerayı Rootlama (bir kere yapılır)

Bu proje, kameranın OSC sunucusunu ev ağınızdayken de açık tutabilmek için **root erişimi** gerektirir (neden gerektiğini [aşağıda](#-nasıl-çözüldü-osc-sunucusunun-bluetoothsuz-tetiklenmesi) anlatıyoruz). Bu adım sadece **bir kere** yapılır; kalıcıdır.

1. Kamerayı **Download/LAF moduna** alın (düğme kombinasyonu cihaza göre değişir — kendi kameranızda hangisi olduğunu bulup burayı güncelleyin) ve USB ile bilgisayara bağlayın.
2. `lglaf/rules.d/42-usb-lglaf.rules` dosyasını udev kurallarına ekleyin ki cihaza root olmadan erişilebilsin:
   ```bash
   sudo cp lglaf/rules.d/42-usb-lglaf.rules /etc/udev/rules.d/
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
3. Proje köküne bir venv oluşturup `lglaf` bağımlılıklarını kurun (Arch gibi "externally managed" dağıtımlarda sistem pip'i bunu reddeder):
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install pyusb requests cryptography flask opencv-python-headless numpy
   ```
4. Root erişimini doğrulayın:
   ```bash
   ./venv/bin/python lglaf/lglaf.py --cr -c "id"
   ```
   `uid=0(root) gid=0(root)` dönmeli. (`--cr` bayrağı zorunlu — bu olmadan `LAF_ERROR_ACCESS_DENIED` alırsınız.)
5. Kalıcı bir root shell (backdoor) kurun — cihaz her açıldığında otomatik başlayan, `nc` ile dinleyen bir root kabuğu:
   ```bash
   ./venv/bin/python lglaf/lglaf.py --cr -c "echo '(/data/local/tmp/busybox nc -lk -p 9999 -e /system/bin/sh) &' >> /system/bin/install-recovery.sh"
   ```
   (`busybox-armv7l` daha önce cihaza `/data/local/tmp/busybox` olarak kopyalanmış olmalı — `dump-file.py`/`lglaf.py` ile push edin.)
6. Kamerayı güç düğmesiyle kapatıp açarak normal Android moduna döndürün.

**Doğrulama:**
```bash
adb devices -l          # cihazı görmeli (model:LG_R105)
adb shell id             # uid=2000(shell) — normal, root için 9999 portu kullanılacak
```

> Bu adım geri alınması nispeten zor bir sistem-dosyası değişikliğidir (`/system/bin/install-recovery.sh`e yazar). Cihazı donanımsal olarak bozma riski düşük, ama factory reset'e kadar bu değişiklik kalıcıdır.

---

## Adım 4 — Kamerayı Ev Wi-Fi Ağına Bağlama

Kameranın gizli Android arayüzüne `scrcpy` ile erişip ev Wi-Fi ağınıza bağlayın:
```bash
adb shell am start -a android.settings.WIFI_SETTINGS
scrcpy
```
Açılan ekrandan ev ağınızı seçip şifrenizi girin. Bu da **bir kere** yapılır — kamera bu ağı hatırlar ve sonraki açılışlarda otomatik bağlanır.

**Doğrulama:**
```bash
adb shell ip addr show wlan0
```
Kameranın ev ağınızdaki IP'sini (`inet ...` satırı) not edin ve `config.py` içindeki `CAMERA_IP` değerini buna göre güncelleyin (DHCP ile değişebilir).

---

## Adım 5 — Yayını Başlatma (Webcam Olarak Kullanma)

```bash
chmod +x webcam.sh
./webcam.sh
```

Bu tek script sırasıyla: v4l2loopback'i kontrol eder, kameraya bağlanır (uykudaysa uyandırmanızı ister), uyku modunu engeller, kameranın güncel IP'sini bulur, `enable_osc.py` ile OSC sunucusunu (port 6624) tetikler, güvenlik duvarında UDP 1234'ü açar, önceki yayınları temizler, `start_stream.py` ile OSC oturumunu canlı tutar ve son olarak **görüntü ayarları panelini** (`panel.py`) açar — bu panel kendi içinde `ffmpeg`'i başlatıp UDP akışını kırpıp `/dev/video9`'a yazar.

**Doğrulama:**
```bash
ffplay /dev/video9
```
veya herhangi bir görüntülü görüşme/kayıt uygulamasını açıp kamera listesinden **LG 360 CAM**'i seçin. Ayrıca tarayıcıda **http://localhost:5555** açıp canlı önizleme + görüntü ayarı kaydırma çubuklarını görebilirsiniz. Görüntü akıyorsa kurulum tamamlanmıştır. 🎉

Durdurmak için terminalde `CTRL+C`.

> Eski `baslat.sh` hâlâ çalışır (panelsiz, sadece ham akış) ama `webcam.sh` artık önerilen yoldur.

---

## 🩺 Sorun Giderme

| Belirti | Olası Sebep / Çözüm |
|---|---|
| `adb devices` cihazı göstermiyor | Kamera uykuda olabilir (USB "Charge mode"a düşer) — güç düğmesine kısa basıp uyandırın. Kalıcı çözüm: `adb shell settings put system screen_off_timeout 2147483647` |
| `enable_osc.py`: "Root backdoor'a bağlanılamadı" | Adım 3 (rootlama + backdoor) yapılmamış veya kamera farklı bir IP'de; `config.py`'deki `CAMERA_IP`'yi kontrol edin. |
| OSC sunucusu (port 6624) hâlâ açılmıyor | `adb shell netstat -an \| grep 6624` ile kontrol edin; `adb logcat \| grep CCSCameraApp` ile hata mesajlarına bakın. |
| `ffplay /dev/video9` siyah ekran / görüntü yok | Muhtemelen güvenlik duvarı UDP:1234'ü engelliyor (`sudo ufw allow 1234/udp`) — bkz. Adım 5. |
| Video donuk/çok düşük FPS | Kamera varsayılanda 1 FPS preview gönderebilir; `camera_api.py` bunu `captureMode=video` ayarıyla düzeltmeye çalışır, loglarda hangi modun tutunduğunu kontrol edin. |
| Kamera birkaç dakika sonra kapanıyor / bağlantı kopuyor | Cihaz otomatik uykuya dalıyor. `python3 disable_sleep.py` (OSC açıkken) veya `adb shell settings put system screen_off_timeout 2147483647` ile kalıcı olarak engelleyin. |

---

## 🔬 Nasıl Çözüldü: OSC Sunucusunun Bluetooth'suz Tetiklenmesi

Bu bölüm, projenin en kritik bulgusunu belgeliyor — ilerleyen bakımlar için.

Kameranın OSC sunucusunu barındıran uygulama (`com.lge.camera.ccs`, APK: `/system/priv-app/LGOSCCameraApp/`) `adb pull` ile indirilip (`strings`, `dumpsys package r`) incelendiğinde, `CameraControlService`'in standart Android sistem yayını **`android.net.wifi.WIFI_AP_STATE_CHANGED`**'ı dinlediği görüldü — yani OSC sunucusu (port 6624), Android'e "hotspot'um açıldı" dedirten bu yayın geldiğinde başlıyor. Kamera ev ağına (station modu) bağlıyken bu yayın hiç tetiklenmiyor, dolayısıyla port 6624 hiç açılmıyor.

**Çözüm:** Root shell üzerinden, gerçek bir hotspot açmadan, sadece bu yayının kendisini sahte parametrelerle göndermek:
```bash
am broadcast -a android.net.wifi.WIFI_AP_STATE_CHANGED --ei wifi_state 13 --ei previous_wifi_state 12
```
(`wifi_state=13` → `WIFI_AP_STATE_ENABLED`.) Bu, uygulamayı "hotspot gerçekten açıldı" sanmaya kandırıyor ve OSC sunucusunu ev ağı IP'sinde açık tutuyor — kamera station modunda kalırken. `enable_osc.py` bu komutu otomatikleştirir.

Video akışı tarafında da (`camera._startPreview`), `logcat`'te görülen `AllMightyServer`/`LSService` günlükleri akışın hedef IP'yi (`clientIP`) OSC isteğini yapan bilgisayarın IP'sinden doğru şekilde aldığını ve `LSServer.apk` içine gömülü bir `ffmpeg` ikili dosyasıyla UDP:1234 üzerinden gerçekten yayın yaptığını doğruladı — ekstra bir "dummy AP" ağ numarasına gerek kalmadı, sadece bu tek sistem yayınının sahtesi yeterli.

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
├── enable_osc.py            # Sahte WIFI_AP_STATE_CHANGED yayını gönderip OSC sunucusunu tetikler
├── start_stream.py         # camera_api.py'yi kullanıp yayını başlatan ve canlı tutan betik
├── disable_sleep.py         # Kameranın otomatik uyku/kapanmasını devre dışı bırakır
├── panel.py                  # Flask görüntü ayarları paneli (localhost:5555) — ffmpeg'i yönetir
├── webcam.sh                  # ÖNERİLEN: tüm süreci kontrol edip başlatan tek script
├── baslat.sh                # Eski/basit başlatıcı (panelsiz, sadece ham akış → /dev/video9)
├── setup.sh                  # (Artık gerekli değil — kameranın kendi hotspot moduna bağlanma sihirbazıydı)
├── setup_network.sh           # (Artık gerekli değil — aynı amaç, komut satırı versiyonu)
├── busybox-armv7l              # Rootlama sırasında kameraya yüklenen statik busybox (bkz. Adım 3)
├── venv/                        # lglaf/enable_osc.py için Python venv (git'e dahil değil)
└── lglaf/                       # LG cihazlarında Download/LAF modu üzerinden root erişim aracı
```

> `main.py` (Flask tabanlı web paneli, hareket algılama, kayıt) henüz yazılmadı — bu, temel webcam akışından sonraki bir sonraki aşama olarak planlanıyor. Güncel durum için `log.md` dosyasına bakın.

---
*Disclaimer: Bu proje LG 360 CAM cihazının sınırlarını aşmak için eğitim ve araştırma amaçlı geliştirilmiştir. Cihaza donanımsal zarar verme ihtimali düşüktür ancak tüm sorumluluk kullanıcıya aittir.*
