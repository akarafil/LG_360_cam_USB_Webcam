# LG 360 CAM USB Webcam Hack 🚀

![LG 360 CAM](https://img.shields.io/badge/LG-360_CAM-red.svg) ![Zero Latency](https://img.shields.io/badge/Latency-0ms-success.svg) ![Platform](https://img.shields.io/badge/Platform-Linux-blue.svg)

[TR] LG 360 CAM (LG-R105) cihazınızı kablosuz ağınız üzerinden (Wi-Fi), sıfır gecikme ve kırpılmış standart kamera açısıyla (Webcam) bilgisayarınıza bağlamanızı sağlayan hack ve otomasyon aracıdır.

[EN] A hack and automation tool that allows you to connect your LG 360 CAM (LG-R105) to your computer over your wireless network (Wi-Fi) as a standard USB Webcam, with zero latency and cropped normal viewing angle.

---

## 🌟 Features / Özellikler

- **No Bluetooth Needed (Bluetooth Gerektirmez):** Cihazın standart uygulamasının aksine, kamerayı uyandırmak ve yayını başlatmak için Bluetooth kullanmaz. Kameranın kök (root) dizinine enjekte edilen kalıcı bir kod ile cihaz her açıldığında Wi-Fi bağlantısını otomatik sağlar.
- **Zero Latency (Sıfır Gecikme):** FFMPEG'in önbellekleme (buffering) sistemlerini tamamen atlayan (bypassing) ekstrem komut setleri kullanır.
- **Auto Sleep Fix (Uyku Modu Çözümü):** Kameranın kullanılmadığında 2 dakika içinde kapanmasını sağlayan özelliği kök (root) seviyesinde devre dışı bırakır. USB'ye bağlı olduğu sürece 7/24 yayında kalır.
- **Crop / Normal View (Kırpılmış Normal Açı):** 180 derece balıkgözü (fisheye) lensi yerine, videonun tam merkezinden (640x480 veya 800x600) kesit alarak görüntülü görüşmeler için ideal olan standart webcam formatını oluşturur.
- **Dummy AP Trick (Sahte Hotspot):** Kamera, yerel modeminize bağlı olmasına rağmen kendini "Hotspot yayınlıyor" zannederek OSC API'sini açık tutar.

## 🛠 Requirements / Gereksinimler

- Linux OS (Ubuntu / Debian / Arch vb.)
- FFMPEG (`sudo apt install ffmpeg`)
- V4L2Loopback (`sudo apt install v4l2loopback-dkms v4l2loopback-utils`)
- Python 3 ve `requests` kütüphanesi

## 🚀 Installation & Usage / Kurulum ve Kullanım

### 1. V4L2 (Sanal Kamera) Sürücüsünü Yükleme
Linux üzerinde sanal bir `/dev/video9` cihazı oluşturun:
```bash
sudo modprobe v4l2loopback video_nr=9 card_label="LG 360 CAM" exclusive_caps=1
```

### 2. Yapılandırma (Configuration)
`config.py` ve `start_stream.py` içindeki IP adresini (`CAMERA_IP`), eğer cihaz modeminize bağlıysa cihazın yerel IP adresiyle değiştirin. Varsayılan IP `192.168.43.1` olarak ayarlıdır (kendi Wi-Fi ağına bağlanıyorsanız).

### 3. Yayını Başlatma (Start Streaming)
```bash
chmod +x baslat.sh
./baslat.sh
```
Bu komut, kamera ile oturumu açacak, `updateSession` ile yayını canlı tutacak ve `ffmpeg` üzerinden gelen görüntüyü 0 gecikme ile `/dev/video9` sanal kamerasına akıtacaktır.

## ⚠️ Cihazı Rootlamak (Hacking the Device)
Eğer kameranız fabrika ayarlarına dönerse veya bu projeyi sıfırdan kuruyorsanız:
1. `lglaf/` dizinini kullanarak cihazın seri portundan kök (root) erişimi alın.
2. `setup.sh` içindeki yönergeleri izleyerek kameranın içerisine `busybox` ve `socat` binary dosyalarını atın.
3. `/system/bin/install-recovery.sh` dosyasına arka kapı (backdoor) `netcat` komutunu yazdırın.
4. Kamera yeniden başladığında gizli komut dosyanız (Dummy AP State) otomatik olarak Wi-Fi'yi tetikleyecektir.

---
*Disclaimer: Bu proje LG 360 CAM cihazının sınırlarını aşmak için eğitim ve araştırma amaçlı geliştirilmiştir. Cihaza donanımsal zarar verme ihtimali düşüktür ancak tüm sorumluluk kullanıcıya aittir.*
