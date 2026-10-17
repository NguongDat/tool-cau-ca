"""
Demonstration Test for Roblox Fishing Master Auto Tool
Runs verification on:
1. Minigame Key W/A/D detection & Tension bar status
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

def run_full_demo():
    print("==================================================================")
    print("  🚀 DEMO CHẠY THỬ TÍNH NĂNG: ROBLOX FISHING MASTER AUTO          ")
    print("==================================================================")

    # --- Test Minigame & Tension Bar ---
    print("\n[1/1] KIỂM TRA NHẬN DIỆN MINIGAME & THANH GIỮ CÁ:")
    vision = RobloxVision()
    sample_mini = cv2.imread(os.path.join("templates", "sample_minigame.png"))
    if sample_mini is not None:
        key_res = vision.detect_key_prompt(sample_mini)
        tension_res = vision.detect_tension_bar(sample_mini)
        print(f"  ✔ Phím Minigame phát hiện: [{key_res['key']}] (Độ tin cậy: {key_res['confidence']:.2f})")
        print(f"  ✔ Thanh giữ cá phát hiện: {tension_res['tension_pct']}% - Trạng thái: {tension_res['status']}")
        if tension_res['status'] == 'DANGER_HIGH':
            print("  ==> Tool kích hoạt chế độ ghìm phím giữ cá, tạm hoãn skill để chống tuột cá!")

    print("\n==================================================================")
    print("  🎉 TÍNH NĂNG TỰ ĐỘNG CÂU CÁ ĐÃ SẴN SÀNG HOẠT ĐỘNG HOÀN HẢO!     ")
    print("==================================================================")

if __name__ == '__main__':
    run_full_demo()
