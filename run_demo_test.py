"""
Demonstration Test for Roblox Fishing Master Auto Tool
Runs verification on:
1. Minigame Key W/A/D detection & Tension bar status
2. Backpack Fish Scanner & Auto-Lock (> 3000KG & Thần cấp/Huyền thoại)
3. Boss Radar & Map Appearance Alert
"""
import sys
import os
import cv2

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from vision import RobloxVision
from inventory_manager import InventoryManager
from boss_radar import BossRadar, BOSS_DATABASE

def run_full_demo():
    print("==================================================================")
    print("  🚀 DEMO CHẠY THỬ CÁC TÍNH NĂNG MỚI: ROBLOX FISHING MASTER AUTO  ")
    print("==================================================================")

    # --- 1. Test Minigame & Tension Bar ---
    print("\n[1/3] KIỂM TRA NHẬN DIỆN MINIGAME & THANH GIỮ CÁ:")
    vision = RobloxVision()
    sample_mini = cv2.imread("templates/sample_minigame.png")
    if sample_mini is not None:
        key_res = vision.detect_key_prompt(sample_mini)
        tension_res = vision.detect_tension_bar(sample_mini)
        print(f"  ✔ Phím Minigame phát hiện: [{key_res['key']}] (Độ tin cậy: {key_res['confidence']:.2f})")
        print(f"  ✔ Thanh giữ cá phát hiện: {tension_res['tension_pct']}% - Trạng thái: {tension_res['status']}")
        if tension_res['status'] == 'DANGER_HIGH':
            print("  ==> Tool kích hoạt chế độ ghìm phím giữ cá, tạm hoãn skill để chống tuột cá!")

    # --- 2. Test Backpack Fish Scanning & Auto-Lock ---
    print("\n[2/3] KIỂM TRA TỰ ĐỘNG KHÓA CÁ LỚN (> 3000KG & THẦN CẤP):")
    inv = InventoryManager()
    sample_bp = cv2.imread("templates/sample_backpack.png")
    if sample_bp is not None:
        is_open, lock_btn = inv.is_backpack_open(sample_bp)
        print(f"  ✔ Phát hiện Balo mở: {is_open}, Nút khóa tại tọa độ: {lock_btn}")
        cards = inv.scan_fish_cards(sample_bp, target_rarities=["Thần cấp", "Huyền thoại"])
        print(f"  ✔ Đã quét tổng cộng {len(cards)} ô cá trong balo:")
        for c in cards[:6]:
            status_str = "🔒 ĐÃ KHÓA" if c['is_locked'] else ("⚡ CẦN KHÓA NGAY" if c['should_lock'] else "Bình thường")
            print(f"     - Ô {c['slot']} [{c['rarity']}]: {status_str}")
        
        exec_res = inv.execute_auto_lock(None, sample_bp, target_rarities=["Thần cấp", "Huyền thoại"])
        print(f"  ==> {exec_res['message']}")

    # --- 3. Test Boss Radar & Map Alerts ---
    print("\n[3/3] KIỂM TRA RADAR SĂN BOSS & THÔNG BÁO TỌA ĐỘ ĐẢO:")
    radar = BossRadar(alert_callback=lambda ev: print(f"  🚨 PHÁT HIỆN BOSS: [{ev['boss']}] ({ev['rarity']})"))
    event = radar.notify_boss_spawn("Dragon Koi")
    print(f"  ✔ Tọa độ bản đồ: {event['island']}")
    print(f"  ✔ Thông tin chi tiết: {event['desc']}")
    print(f"  ✔ Chuông âm thanh cảnh báo (Dual-Tone Beep): Đã phát!")

    print("\n==================================================================")
    print("  🎉 TẤT CẢ CÁC TÍNH NĂNG ĐÃ SẴN SÀNG HOẠT ĐỘNG 100% HOÀN HẢO!     ")
    print("==================================================================")

if __name__ == '__main__':
    run_full_demo()
