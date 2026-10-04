import sys
import os
import time
import winsound
import threading
import cv2
import numpy as np

# Support UTF-8 printing on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BOSS_DATABASE = {
    "Dragon Koi": {
        "island": "Jungle Island",
        "rarity": "Thần cấp (Godly)",
        "color": "#FF9900",
        "desc": "Cá Chép Rồng Thần Thoại - Sinh sống tại Đảo Rừng Rậm (Jungle Island)",
        "icon": "🐉"
    },
    "Kun Version 2": {
        "island": "Fossil Island",
        "rarity": "Thần cấp (Godly)",
        "color": "#00E5FF",
        "desc": "Cá Côn Bằng Hóa Thạch Mắt Xanh - Đảo Hóa Thạch (Fossil Island)",
        "icon": "🐋"
    },
    "Kun Version": {
        "island": "Fossil Island",
        "rarity": "Huyền thoại (Legendary)",
        "color": "#FF3366",
        "desc": "Cá Côn Bằng Mắt Đỏ - Đảo Hóa Thạch (Fossil Island)",
        "icon": "🦈"
    },
    "HaLaNgu": {
        "island": "Snow Island",
        "rarity": "Huyền thoại (Legendary)",
        "color": "#FF5252",
        "desc": "Hà Lộ Ngư Hàm Răng Sắc - Đảo Băng Tuyết (Snow Island)",
        "icon": "👹"
    },
    "Ghost Shark": {
        "island": "Desert Island / Deep Sea",
        "rarity": "Huyền thoại (Legendary)",
        "color": "#E0E0E0",
        "desc": "Cá Mập Ma Xương Trắng - Vùng biển Sa Mạc (Desert Island)",
        "icon": "👻"
    }
}

ALL_ISLANDS = [
    {"name": "Starter Island", "desc": "Đảo Khởi Đầu - Cá cơ bản & tân thủ", "level": "Lv. 1 - 15"},
    {"name": "Jungle Island", "desc": "Đảo Rừng Rậm - Boss Dragon Koi (Thần cấp)", "level": "Lv. 15 - 30"},
    {"name": "Desert Island", "desc": "Đảo Sa Mạc - Ghost Shark & Cá xương cát", "level": "Lv. 30 - 45"},
    {"name": "Snow Island", "desc": "Đảo Băng Tuyết - Boss HaLaNgu", "level": "Lv. 45 - 60"},
    {"name": "Volcanic Island", "desc": "Đảo Núi Lửa - Cá nham thạch & Cực phẩm", "level": "Lv. 60 - 80"},
    {"name": "Fossil Island", "desc": "Đảo Hóa Thạch - Boss Kun Version 1 & 2", "level": "Lv. 80+"}
]

class BossRadar:
    def __init__(self, alert_callback=None):
        self.alert_callback = alert_callback
        self.boss_history = []
        self.sound_enabled = True
        self.last_alert_time = {}

    def trigger_sound(self):
        """Plays dual chime without blocking UI."""
        def play():
            try:
                winsound.Beep(1100, 180)
                time.sleep(0.05)
                winsound.Beep(1500, 250)
            except Exception:
                pass
        threading.Thread(target=play, daemon=True).start()

    def check_boss_appearance(self, frame_bgr):
        """
        Scans top portion of Roblox screen for Weather Change & Boss Event announcements.
        Requires high-density banner detection to prevent false positive spam.
        Returns detected boss event or None.
        """
        if frame_bgr is None:
            return None

        h, w = frame_bgr.shape[:2]
        # Look in top 20% server announcement bar
        banner_roi = frame_bgr[0:int(h * 0.20), int(w * 0.25):int(w * 0.75)]
        if banner_roi.shape[0] < 30 or banner_roi.shape[1] < 150:
            return None

        hsv = cv2.cvtColor(banner_roi, cv2.COLOR_BGR2HSV)
        
        # Golden / Yellow / Magenta Event Banner
        mask_gold = cv2.inRange(hsv, np.array([14, 150, 180]), np.array([35, 255, 255]))
        mask_magenta = cv2.inRange(hsv, np.array([145, 140, 180]), np.array([165, 255, 255]))
        
        gold_pixels = np.sum(mask_gold > 0)
        magenta_pixels = np.sum(mask_magenta > 0)

        now = time.time()
        detected_boss = None

        # Require large concentrated banner pixel cluster (> 3500 px)
        if gold_pixels > 3500:
            detected_boss = "Dragon Koi"
        elif magenta_pixels > 3500:
            detected_boss = "Kun Version 2"

        if detected_boss:
            last_t = self.last_alert_time.get(detected_boss, 0.0)
            # Only trigger once per 5 minutes (300 seconds) to prevent spamming
            if now - last_t > 300.0:
                self.last_alert_time[detected_boss] = now
                return self.notify_boss_spawn(detected_boss)

        return None

    def notify_boss_spawn(self, boss_name):
        """Dispatches an alert when a boss appears and logs island location."""
        info = BOSS_DATABASE.get(boss_name, {
            "island": "Chưa xác định Đảo",
            "rarity": "Boss Quý",
            "desc": "Boss đặc biệt"
        })

        now_str = time.strftime("%H:%M:%S")
        event = {
            "time": now_str,
            "boss": boss_name,
            "island": info["island"],
            "rarity": info["rarity"],
            "desc": info["desc"]
        }
        self.boss_history.insert(0, event)
        if len(self.boss_history) > 30:
            self.boss_history.pop()

        if self.sound_enabled:
            self.trigger_sound()

        if self.alert_callback:
            self.alert_callback(event)

        return event

if __name__ == '__main__':
    radar = BossRadar(alert_callback=lambda ev: print("ALERT:", ev["boss"], "at", ev["island"]))
    ev = radar.notify_boss_spawn("Dragon Koi")
    print("Test notify event:", ev["boss"])
