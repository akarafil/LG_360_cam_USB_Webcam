import requests
from config import Config

IP = Config.CAMERA_IP
PORT = Config.CAMERA_PORT
BASE_URL = f"http://{IP}:{PORT}/osc"

def disable_sleep():
    try:
        # Start session
        res = requests.post(f"{BASE_URL}/commands/execute", json={"name": "camera.startSession", "parameters": {}}, timeout=5)
        if res.status_code != 200:
            print("Oturum açılamadı:", res.text)
            return
        
        session_id = res.json()["results"]["sessionId"]
        print(f"Oturum açıldı: {session_id}")
        
        # Set sleepDelay to 65535 (disable auto-sleep)
        payload = {
            "name": "camera.setOptions",
            "parameters": {
                "sessionId": session_id,
                "options": {
                    "sleepDelay": 65535,
                    "offDelay": 65535
                }
            }
        }
        res = requests.post(f"{BASE_URL}/commands/execute", json=payload, timeout=5)
        if res.status_code == 200:
            print("Başarılı! Kameranın otomatik uyku modu (Wi-Fi'deyken) tamamen kapatıldı.")
            print("Artık USB'den güç aldığı sürece asla kapanmayacak.")
        else:
            print("Ayarlar değiştirilemedi:", res.text)
            
    except Exception as e:
        print("Hata oluştu:", e)

if __name__ == "__main__":
    disable_sleep()
