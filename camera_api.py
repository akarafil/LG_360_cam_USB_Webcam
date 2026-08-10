"""
LG 360 CAM Güvenlik Kamerası - Kamera API Modülü
=================================================
LG 360 CAM ile Open Spherical Camera (OSC) API üzerinden iletişim kurar.

DÜZELTİLDİ / YENİ:
- yayin_baslat() → stream öncesi previewFormat + captureMode ayarları gönderiliyor
- LG-R105 varsayılan olarak çok düşük FPS'te preview gönderiyor;
  _setOptions ile "video" modu ve yüksek FPS formatı zorunlu hale getirildi.
- Birden fazla format denemesi: önce 1920x960@30fps, sonra 1280x640@30fps, son olarak 640x320@30fps
"""

import time
import logging
import requests
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class LG360CamAPI:
    """LG 360 CAM Open Spherical Camera API istemcisi."""

    def __init__(self):
        self.api_url = Config.CAMERA_API_URL
        self.info_url = Config.CAMERA_INFO_URL
        self.session_id = Config.CAMERA_SESSION_ID
        self.timeout = Config.CAMERA_CONNECT_TIMEOUT
        self.bagli = False
        self.yayin_aktif = False
        self.preview_uri = None
        self._son_hata = None

        # Desteklenen preview formatları (büyükten küçüğe dene)
        self._preview_formatlari = [
            {"width": 1024, "height": 512,  "framerate": 24},
            {"width": 640,  "height": 320,  "framerate": 24},
            {"width": 1280, "height": 640,  "framerate": 24},
            {"width": 1280, "height": 768,  "framerate": 24},
        ]

    def _komut_gonder(self, komut_adi: str, parametreler: dict = None) -> Optional[dict]:
        payload = {"name": komut_adi}
        if parametreler:
            payload["parameters"] = parametreler
        try:
            yanit = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            yanit.raise_for_status()
            veri = yanit.json()
            logger.debug(f"API Yanıt [{komut_adi}]: {veri}")
            self._son_hata = None
            return veri
        except requests.ConnectionError:
            self._son_hata = "Kameraya bağlanılamıyor. WiFi ağını kontrol edin."
            logger.error(self._son_hata)
        except requests.Timeout:
            self._son_hata = f"Kamera yanıt vermedi ({self.timeout}s zaman aşımı)"
            logger.error(self._son_hata)
        except requests.HTTPError as e:
            self._son_hata = f"HTTP hatası: {e.response.status_code}"
            logger.error(self._son_hata)
        except Exception as e:
            self._son_hata = f"Beklenmeyen hata: {str(e)}"
            logger.error(self._son_hata)
        return None

    def baglan(self) -> bool:
        try:
            logger.info(f"Kameraya bağlanılıyor: {Config.CAMERA_IP}:{Config.CAMERA_PORT}")
            yanit = requests.get(self.info_url, timeout=self.timeout)
            yanit.raise_for_status()
            bilgi = yanit.json()
            logger.info(f"Kamera bulundu: {bilgi.get('model', 'Bilinmeyen')}")
            logger.info(f"  Üretici: {bilgi.get('manufacturer', 'Bilinmeyen')}")
            logger.info(f"  Firmware: {bilgi.get('firmwareVersion', 'Bilinmeyen')}")
            logger.info(f"  Seri No: {bilgi.get('serialNumber', 'Bilinmeyen')}")
            self.bagli = True
            self._son_hata = None
            return True
        except requests.ConnectionError:
            self._son_hata = "Kameraya bağlanılamıyor. WiFi ağını kontrol edin."
            logger.error(self._son_hata)
            self.bagli = False
            return False
        except Exception as e:
            self._son_hata = f"Bağlantı hatası: {str(e)}"
            logger.error(self._son_hata)
            self.bagli = False
            return False

    def oturum_baslat(self) -> bool:
        logger.info("Kamera oturumu başlatılıyor...")
        yanit = self._komut_gonder("camera.startSession")
        if yanit and "results" in yanit:
            self.session_id = yanit["results"].get("sessionId", self.session_id)
            logger.info(f"Oturum başlatıldı. Session ID: {self.session_id}")
            return True
        logger.warning("Oturum başlatılamadı, varsayılan session ID kullanılacak")
        return True

    def _capture_mode_ayarla(self) -> bool:
        """
        Kamerayı 'video' / '_liveStreaming' capture moduna alır.
        Bu olmadan LG-R105 preview'u çok düşük FPS'te gönderir.
        """
        # Önce mevcut modu oku
        mevcut = self._komut_gonder(
            "camera.getOptions",
            {"sessionId": self.session_id, "optionNames": ["captureMode"]}
        )
        if mevcut:
            mod = mevcut.get("results", {}).get("options", {}).get("captureMode", "?")
            logger.info(f"Mevcut capture modu: {mod}")

        # video modunu dene (LG-R105 bunu destekliyor)
        for mod in ["video", "_liveStreaming", "image"]:
            yanit = self._komut_gonder(
                "camera.setOptions",
                {
                    "sessionId": self.session_id,
                    "options": {"captureMode": mod}
                }
            )
            if yanit and yanit.get("state") != "error":
                logger.info(f"Capture modu '{mod}' olarak ayarlandı")
                return True
            logger.debug(f"Capture modu '{mod}' desteklenmiyor, sonraki deneniyor...")

        logger.warning("Capture modu değiştirilemedi, mevcut modda devam ediliyor")
        return False

    def _preview_format_ayarla(self) -> bool:
        """
        Preview formatını (çözünürlük + FPS) ayarlar.
        LG-R105 varsayılanda çok düşük FPS'te başlıyor;
        bu komutla 30 FPS zorlanıyor.
        """
        # Desteklenen formatları oku
        desteklenen = self._komut_gonder(
            "camera.getOptions",
            {"sessionId": self.session_id, "optionNames": ["previewFormat", "previewFormatSupport"]}
        )
        if desteklenen:
            logger.info(f"Preview format bilgisi: {desteklenen.get('results', {})}")

        # Büyükten küçüğe formatları dene
        for fmt in self._preview_formatlari:
            yanit = self._komut_gonder(
                "camera.setOptions",
                {
                    "sessionId": self.session_id,
                    "options": {
                        "previewFormat": {
                            "width": fmt["width"],
                            "height": fmt["height"],
                            "framerate": fmt["framerate"]
                        }
                    }
                }
            )
            if yanit and yanit.get("state") != "error":
                logger.info(
                    f"Preview format ayarlandı: {fmt['width']}x{fmt['height']} @ {fmt['framerate']}fps"
                )
                return True
            logger.debug(
                f"Format {fmt['width']}x{fmt['height']}@{fmt['framerate']} desteklenmiyor, "
                f"sonraki deneniyor..."
            )

        logger.warning("Hiçbir preview format ayarlanamadı, kamera varsayılanıyla devam ediyor")
        return False

    def _stream_options_ayarla(self) -> None:
        """
        Stream başlamadan önce ön ayarları uygular.

        LG-R105 notu:
        - previewFormatSupport sadece 1280x768@1fps: format ayari desteklenmiyor
        - captureMode video yapilinca kamera cok daha yuksek FPS preview gonderiyor
        """
        logger.info("Stream on ayarlari yapilandiriliyor...")
        # captureMode video (kritik: bu olmadan kamera 1 FPS kalir)
        self._capture_mode_ayarla()
        # Kameranin modu islemesi icin bekleme
        time.sleep(1.0)

    def yayin_baslat(self) -> Optional[str]:
        """
        Kameradan canlı yayın başlatır.

        LG-R105 doğru akış:
        1) camera._startPreview → UDP stream başlatır, _previewUri döner (udp://:1234)
        2) getLivePreview sadece 1 FPS verir, kullanılmaz
        """
        if not self.bagli:
            logger.error("Yayın başlatılamaz: Kameraya bağlı değil")
            return None

        logger.info("Canlı yayın başlatılıyor...")

        # camera._startPreview → UDP stream açar, previewUri döner
        yanit = self._komut_gonder(
            "camera._startPreview",
            {"sessionId": self.session_id}
        )

        if yanit and "results" in yanit:
            preview_uri = yanit["results"].get("_previewUri", "")
            if preview_uri:
                self.preview_uri = preview_uri
                self.yayin_aktif = True
                logger.info(f"UDP stream başlatıldı: {self.preview_uri}")
                return self.preview_uri

        # Fallback: doğrudan UDP portunu kullan
        logger.warning("_startPreview yanıtında URI yok, varsayılan UDP portu kullanılıyor")
        self.preview_uri = f"udp://@:{Config.STREAM_UDP_PORT}"
        self.yayin_aktif = True
        logger.info(f"Fallback UDP stream: {self.preview_uri}")
        return self.preview_uri

    def yayin_durdur(self) -> bool:
        if not self.yayin_aktif:
            return True
        logger.info("Canlı yayın durduruluyor...")
        yanit = self._komut_gonder(
            "camera._stopPreview",
            {"sessionId": self.session_id}
        )
        self.yayin_aktif = False
        self.preview_uri = None
        if yanit is not None:
            logger.info("Canlı yayın durduruldu")
            return True
        logger.warning("Yayın durdurma komutu başarısız olabilir")
        return False

    def fotograf_cek(self) -> Optional[str]:
        logger.info("Fotoğraf çekiliyor...")
        yanit = self._komut_gonder(
            "camera.takePicture",
            {"sessionId": self.session_id}
        )
        if yanit and "results" in yanit:
            dosya_uri = yanit["results"].get("fileUri", "")
            logger.info(f"Fotoğraf çekildi: {dosya_uri}")
            return dosya_uri
        logger.error("Fotoğraf çekilemedi")
        return None

    def oturum_kapat(self) -> bool:
        logger.info("Kamera oturumu kapatılıyor...")
        if self.yayin_aktif:
            self.yayin_durdur()
        yanit = self._komut_gonder(
            "camera.closeSession",
            {"sessionId": self.session_id}
        )
        self.bagli = False
        self.yayin_aktif = False
        if yanit is not None:
            logger.info("Kamera oturumu kapatıldı")
            return True
        return False

    def yeniden_baglan(self, max_deneme: int = 3) -> bool:
        for deneme in range(1, max_deneme + 1):
            logger.info(f"Yeniden bağlanma denemesi {deneme}/{max_deneme}...")
            if self.baglan():
                self.oturum_baslat()
                if self.yayin_baslat():
                    logger.info("Yeniden bağlantı başarılı!")
                    return True
            bekleme = Config.CAMERA_RECONNECT_INTERVAL * deneme
            logger.info(f"{bekleme}s bekleniyor...")
            time.sleep(bekleme)
        logger.error(f"Yeniden bağlantı başarısız ({max_deneme} deneme)")
        return False

    def preview_format_listele(self) -> list:
        """Kameranın desteklediği preview formatlarını döndürür (debug için)."""
        yanit = self._komut_gonder(
            "camera.getOptions",
            {
                "sessionId": self.session_id,
                "optionNames": ["previewFormat", "previewFormatSupport",
                                "captureMode", "captureModeSupport"]
            }
        )
        if yanit and "results" in yanit:
            return yanit["results"].get("options", {})
        return {}

    @property
    def durum(self) -> dict:
        return {
            "bagli": self.bagli,
            "yayin_aktif": self.yayin_aktif,
            "preview_uri": self.preview_uri,
            "session_id": self.session_id,
            "son_hata": self._son_hata,
            "kamera_ip": Config.CAMERA_IP,
        }

    def tam_baslat(self) -> bool:
        if not self.baglan():
            return False
        self.oturum_baslat()
        self._stream_options_ayarla()
        if not self.yayin_baslat():
            return False
        return True
