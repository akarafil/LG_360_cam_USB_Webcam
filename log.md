# lg_cam - Konuşma ve Gelişim Günlüğü

## 2026-08-16
- Proje dizini oluşturuldu, log.md dosyası başlatıldı.
- Hedef belirlendi: LG 360 CAM (LG-R105)'i bilgisayara USB webcam gibi çalıştırmak; her adım GitHub'a düzenli push edilecek.
- USB analizi: kamera şu an sadece "Charge mode"da görünüyor (idVendor 1004:6300), tek arayüz HID — veri/video arayüzü yok, `/dev/video*` oluşmuyor. Webcam akışı için kameranın kendi WiFi AP modu (OSC API üzerinden) kullanılacak, USB sadece güç için.
- Var olan GitHub reposu bulundu ve bağlandı: https://github.com/akarafil/LG_360_cam_USB_Webcam (bu dizine `origin` olarak eklendi, `main` dalı checkout edildi).
  - Repoda hazır olanlar: `lglaf/` (root/flash aracı, opsiyonel/ileri seviye), `setup.sh`/`setup_network.sh` (kamera WiFi AP'sine bağlanma + NAT köprüsü), `camera_api.py` (OSC API ile UDP stream başlatma), `baslat.sh` (ffmpeg ile `/dev/video9` sanal webcam'e akış), `disable_sleep.py`.
  - Eksik: README/setup.sh'nin bahsettiği `main.py` (Flask web paneli + hareket algılama + kayıt) repoda yok; `requirements.txt`'teki flask/opencv/bleak buna ait ama karşılığı yok. Bu proje kapsamı dışında bırakıldı — kullanıcı projeyi "adım adım baştan" ele almak istiyor.
- Karar: Kamera daha önce root'lanmamış/backdoor kurulmamış kabul edilecek; root/lglaf adımı olmadan, cihazın standart WiFi AP modu (Güç + Deklanşör çift tık) üzerinden ilerlenecek. Rootlama isteğe bağlı, ileride ele alınabilir.
- Ortam kontrolü tamamlandı: `v4l2loopback` (v0.15.4) kurulu, `nmcli`, `ffmpeg`, `python3` (3.14.7) + `requests` (2.34.2) mevcut — ek kurulum gerekmiyor.
- Sıradaki adım: Kamerayı WiFi AP moduna almak (Güç + Deklanşör çift tık) ve bilgisayardan ağını bulup bağlanmak.
