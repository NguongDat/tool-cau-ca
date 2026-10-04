import os
import sys
import time
import re
import cv2
import numpy as np
import winsound
import threading
import direct_input as di

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── Tesseract OCR setup ────────────────────────────────────────────────────
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\ASUS\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\tools\tesseract\tesseract.exe",
]

_ocr_engine = None   # "tesseract" | None

def _init_ocr():
    """Khởi tạo OCR engine một lần (lazy singleton). Trả về 'tesseract' hoặc None."""
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine

    try:
        import pytesseract
        for p in _TESSERACT_PATHS:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break
        # Smoke-test
        import PIL.Image
        img_test = PIL.Image.fromarray(np.zeros((10, 80, 3), dtype=np.uint8))
        pytesseract.image_to_string(img_test, config="--psm 7")
        _ocr_engine = "tesseract"
        return _ocr_engine
    except Exception:
        pass

    _ocr_engine = None
    return _ocr_engine


def _extract_kg_from_raw(raw_text):
    """
    Trích xuất số KG từ raw OCR text.
    OCR hay nhầm: ':' thay '.', ký tự nhiễu ở đầu, 'KG' bị nhận dạng thành 'Ko'...
    Ví dụ raw:
      'Aa\\n91392.74 KoA'   → 1392.74
      '33:32 KG), /'        → 33.32
      '93:15 KG'            → 33.15 (chỉ lấy phần sau ':')
    """
    if not raw_text:
        return None

    # Chuẩn hóa: thay ':' thành '.' (OCR hay nhầm dấu phân cách thập phân)
    text = raw_text.replace(':', '.').replace(',', '.')

    # Pattern 1: số thập phân rõ ràng như "1392.74" hoặc "33.32"
    # Tìm tất cả candidates số thập phân
    decimal_matches = re.findall(r'\b(\d{1,5}\.\d{1,2})\b', text)
    # Lọc lấy giá trị hợp lệ
    for m in decimal_matches:
        try:
            val = float(m)
            if 0.5 <= val <= 99999:
                return val
        except Exception:
            pass

    # Pattern 2: tìm "XYZ.WV KG" hoặc "XYZ KG" (trước chữ K/KG)
    # vd: "1392.74 KG" hoặc "274 KG"
    kg_pattern = re.search(r'(\d{1,6}(?:\.\d{1,2})?)\s*[Kk]', text)
    if kg_pattern:
        try:
            val = float(kg_pattern.group(1))
            if 0.5 <= val <= 99999:
                return val
        except Exception:
            pass

    # Pattern 3: fallback số nguyên 2+ chữ số
    int_matches = re.findall(r'\b(\d{2,6})\b', text)
    for m in int_matches:
        try:
            val = float(m)
            if 0.5 <= val <= 99999:
                return val
        except Exception:
            pass

    return None


def _read_kg_from_card(card_bgr):
    """
    Đọc số KG từ vùng text của một card cá bằng Tesseract OCR.
    
    Cấu trúc card cá (từ trên xuống):
      0%  - 18%: Tên rarity màu (Thần cấp, Huyền thoại...)
      18% - 42%: Số KG (vd: "1392.74 KG")
      42% - 80%: Ảnh con cá
      80% - 100%: Tên cá
    
    Trả về float KG nếu đọc được, None nếu không.
    """
    if card_bgr is None or card_bgr.shape[0] < 30 or card_bgr.shape[1] < 30:
        return None

    h, w = card_bgr.shape[:2]

    # Crop vùng chứa số KG: 18% ~ 42% chiều cao
    kg_roi = card_bgr[int(h * 0.18):int(h * 0.42), int(w * 0.02):int(w * 0.98)]
    if kg_roi.shape[0] < 6 or kg_roi.shape[1] < 20:
        return None

    engine = _init_ocr()
    if engine != "tesseract":
        return None

    try:
        import pytesseract
        from PIL import Image as PILImage

        # Phóng to 4x để tăng độ chính xác OCR
        scale = 4
        kg_up = cv2.resize(kg_roi,
                           (kg_roi.shape[1] * scale, kg_roi.shape[0] * scale),
                           interpolation=cv2.INTER_CUBIC)

        # Chuyển sang grayscale
        gray = cv2.cvtColor(kg_up, cv2.COLOR_BGR2GRAY)

        # Invert nếu ảnh tối (chữ trắng trên nền tối → đen trên trắng cho OCR)
        if np.mean(gray) < 128:
            gray = cv2.bitwise_not(gray)

        # Tăng tương phản
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        gray = clahe.apply(gray)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # Threshold Otsu
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        pil_img = PILImage.fromarray(thresh)
        raw = pytesseract.image_to_string(pil_img, config="--psm 6 --oem 1").strip()
        result = _extract_kg_from_raw(raw)
        if result is not None:
            return result

        # Fallback: adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2
        )
        pil_img2 = PILImage.fromarray(adaptive)
        raw2 = pytesseract.image_to_string(pil_img2, config="--psm 6 --oem 1").strip()
        return _extract_kg_from_raw(raw2)

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────

class InventoryManager:
    def __init__(self, template_dir=None):
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.template_dir = template_dir

        self.tpl_lock_badge = cv2.imread(os.path.join(self.template_dir, "lock_pure.png"))
        self.tpl_lock_btn = cv2.imread(os.path.join(self.template_dir, "lock_tool_btn.png"))
        self.is_scanning = False

    def is_backpack_open(self, frame_bgr):
        """Kiểm tra xem Balo/Inventory GUI có đang hiển thị không."""
        if frame_bgr is None:
            return False, None

        h, w = frame_bgr.shape[:2]

        # 1. Template matching nút khóa
        if self.tpl_lock_btn is not None:
            roi = frame_bgr[0:int(h * 0.25), int(w * 0.3):int(w * 0.9)]
            res = cv2.matchTemplate(roi, self.tpl_lock_btn, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > 0.45:
                btn_x = int(w * 0.3) + max_loc[0] + self.tpl_lock_btn.shape[1] // 2
                btn_y = max_loc[1] + self.tpl_lock_btn.shape[0] // 2
                return True, (btn_x, btn_y)

        # 2. Fallback: header tối của Backpack UI
        hdr_roi = frame_bgr[0:int(h * 0.18), int(w * 0.05):int(w * 0.95)]
        mean_val = np.mean(hdr_roi)
        if mean_val < 90:
            return True, (int(w * 0.605), int(h * 0.075))

        return False, None

    def scan_fish_cards(self, frame_bgr, min_lock_kg=None, target_rarities=None):
        """
        Quét tất cả ô cá trong balo.

        Tiêu chí khóa:
          - Nếu min_lock_kg > 0 VÀ OCR khả dụng:
              → Khóa những con có KG đọc được >= min_lock_kg
          - Fallback (không có OCR / KG = 0):
              → Khóa theo rarity (target_rarities)

        Trả về list dict thông tin từng card.
        """
        if target_rarities is None:
            target_rarities = ["Thần cấp", "Huyền thoại", "Sử thi"]

        if frame_bgr is None:
            return []

        h, w = frame_bgr.shape[:2]
        grid_y1 = int(h * 0.12)
        grid_y2 = int(h * 0.92)
        grid_x1 = int(w * 0.04)
        grid_x2 = int(w * 0.96)

        num_cols = 7
        card_w = (grid_x2 - grid_x1) // num_cols
        card_h = int(card_w * 1.05)

        fish_list = []
        slot_idx = 0

        ocr_available = (_init_ocr() is not None)
        use_kg_mode = (min_lock_kg is not None and min_lock_kg > 0 and ocr_available)

        for row in range(3):
            cy1 = grid_y1 + row * card_h
            cy2 = min(h, cy1 + card_h)
            if cy2 > grid_y2:
                break

            for col in range(num_cols):
                cx1 = grid_x1 + col * card_w
                cx2 = min(w, cx1 + card_w)

                card = frame_bgr[cy1:cy2, cx1:cx2]
                if card.shape[0] < 30 or card.shape[1] < 30:
                    continue

                # Bỏ qua ô trống
                if np.mean(card) < 12:
                    continue

                # Kiểm tra đã khóa chưa
                is_locked = False
                if self.tpl_lock_badge is not None:
                    res_lock = cv2.matchTemplate(card, self.tpl_lock_badge, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res_lock)
                    if max_val >= 0.58:
                        is_locked = True

                # Nhận diện rarity theo màu text
                label_roi = card[0:int(card.shape[0] * 0.30), :]
                b, g, r = cv2.split(label_roi)

                rarity = "Thông thường"
                pink_mask   = (r > 160) & (g < 135) & ((b > 65) | (r > 1.35 * g))
                gold_mask   = (r > 160) & (g > 120) & (b < 100)
                purple_mask = (r > 135) & (b > 135) & (g < 135)
                cyan_mask   = (b > 160) & (g > 160) & (r < 130)

                if np.sum(pink_mask) > 10:
                    rarity = "Thần cấp"
                elif np.sum(gold_mask) > 10:
                    rarity = "Huyền thoại"
                elif np.sum(purple_mask) > 10:
                    rarity = "Sử thi"
                elif np.sum(cyan_mask) > 10:
                    rarity = "Hiếm"

                # Đọc KG bằng OCR (chỉ khi chưa khóa để tiết kiệm thời gian)
                kg_value = None
                if ocr_available and not is_locked:
                    kg_value = _read_kg_from_card(card)

                # Xác định có nên khóa không
                should_lock = False
                if not is_locked:
                    if use_kg_mode:
                        if kg_value is not None and kg_value >= min_lock_kg:
                            # OCR đọc được KG >= ngưỡng → khóa
                            should_lock = True
                        elif kg_value is None and rarity in target_rarities:
                            # OCR thất bại nhưng cá quý (Thần cấp/Huyền thoại) → vẫn khóa
                            should_lock = True
                    else:
                        # Chế độ rarity thuần
                        if rarity in target_rarities:
                            should_lock = True

                center_x = cx1 + card_w // 2
                center_y = cy1 + card_h // 2

                fish_list.append({
                    "slot": slot_idx,
                    "row": row,
                    "col": col,
                    "center": (center_x, center_y),
                    "rarity": rarity,
                    "kg": kg_value,
                    "is_locked": is_locked,
                    "should_lock": should_lock
                })
                slot_idx += 1

        return fish_list

    def execute_auto_lock(self, window_rect, frame_bgr, target_rarities=None, min_lock_kg=None):
        """
        Tự động click chế độ khóa và khóa tất cả cá đủ tiêu chí.

        Ưu tiên khóa theo KG (nếu OCR khả dụng và min_lock_kg > 0),
        fallback sang khóa theo rarity.
        """
        import win32api
        import win32con

        is_open, lock_btn_pos = self.is_backpack_open(frame_bgr)
        if not is_open:
            return {"success": False, "message": "Chưa mở Balo (Nhấn phím 2 trong game để mở)"}

        ocr_ok = (_init_ocr() is not None)
        use_kg_mode = (min_lock_kg is not None and min_lock_kg > 0 and ocr_ok)

        cards = self.scan_fish_cards(frame_bgr, min_lock_kg=min_lock_kg, target_rarities=target_rarities)
        to_lock = [c for c in cards if c["should_lock"]]

        if not to_lock:
            if use_kg_mode:
                return {
                    "success": True,
                    "message": f"✅ Không có cá nào cần khóa (tất cả đã khóa hoặc KG < {min_lock_kg:.0f} KG)."
                }
            if not ocr_ok:
                return {
                    "success": True,
                    "message": "⚠️ OCR chưa sẵn sàng (Tesseract chưa cài). Tất cả cá quý đã khóa hoặc không tìm thấy."
                }
            return {"success": True, "message": "✅ Tất cả cá quý đã được khóa an toàn 🔒!"}

        # Toạ độ màn hình
        off_x = window_rect[0] if window_rect else 0
        off_y = window_rect[1] if window_rect else 0

        btn_scr_x = off_x + lock_btn_pos[0]
        btn_scr_y = off_y + lock_btn_pos[1]

        def click_pos(x, y):
            try:
                win32api.SetCursorPos((int(x), int(y)))
                time.sleep(0.06)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.12)
            except Exception:
                pass

        # 1. Bật chế độ khóa
        click_pos(btn_scr_x, btn_scr_y)
        time.sleep(0.25)

        # 2. Click từng card cá
        locked_count = 0
        kg_info_parts = []
        for fish in to_lock:
            fx = off_x + fish["center"][0]
            fy = off_y + fish["center"][1]
            click_pos(fx, fy)
            locked_count += 1
            if fish.get("kg") is not None:
                kg_info_parts.append(f"{fish['kg']:.1f}KG ({fish['rarity']})")
            else:
                kg_info_parts.append(f"{fish['rarity']}")
            time.sleep(0.15)

        # 3. Tắt chế độ khóa
        click_pos(btn_scr_x, btn_scr_y)

        # Âm thanh xác nhận
        try:
            winsound.Beep(1400, 150)
            time.sleep(0.05)
            winsound.Beep(1800, 200)
        except Exception:
            pass

        if use_kg_mode:
            detail = ", ".join(kg_info_parts[:5])
            if len(kg_info_parts) > 5:
                detail += f"... (+{len(kg_info_parts)-5} con khác)"
            msg = (
                f"🔒 Đã khóa {locked_count} con cá có KG ≥ {min_lock_kg:.0f} KG!\n"
                f"   Chi tiết: {detail}"
            )
        else:
            msg = f"🔒 Đã khóa thành công {locked_count} con cá quý (theo phẩm cấp)!"

        return {
            "success": True,
            "locked_count": locked_count,
            "message": msg,
            "ocr_used": use_kg_mode
        }


if __name__ == '__main__':
    mgr = InventoryManager()
    sample = cv2.imread(os.path.join(os.path.dirname(__file__), "templates", "sample_backpack.png"))
    is_open, pos = mgr.is_backpack_open(sample)
    print("Backpack open:", is_open, "Lock button pos:", pos)

    ocr = _init_ocr()
    print("OCR engine:", ocr)

    cards = mgr.scan_fish_cards(sample, min_lock_kg=100)
    print(f"\nScanned {len(cards)} fish slots (min_lock_kg=100):")
    for c in cards[:15]:
        print(f"  Slot {c['slot']} Row{c['row']} Col{c['col']} | {c['rarity']:12s} | KG={c['kg']} | Locked={c['is_locked']} | ShouldLock={c['should_lock']}")
