import os
import time
import cv2
import numpy as np
import win32gui
import win32con
from PIL import ImageGrab

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

class RobloxVision:
    def __init__(self, template_dir=None):
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.template_dir = template_dir
        
        self.templates = {}
        self.precomputed_templates = []
        self.load_templates()
        self.sct = None
        self.roblox_hwnd = None
        self.cached_rect = None
        self.last_rect_check = 0.0
        if HAS_MSS:
            try:
                self.sct = mss.MSS()
            except Exception:
                self.sct = None

    def load_templates(self):
        """Loads keycap and skill templates and precomputes scaled grayscale versions."""
        self.templates = {}
        self.precomputed_templates = []
        for key in ['w', 'a', 'd']:
            p = os.path.join(self.template_dir, f"key_{key}.png")
            if os.path.exists(p):
                tpl = cv2.imread(p)
                if tpl is not None:
                    self.templates[key.upper()] = tpl
            p_gen = os.path.join(self.template_dir, f"key_{key}_gen.png")
            if os.path.exists(p_gen):
                tpl_g = cv2.imread(p_gen)
                if tpl_g is not None:
                    self.templates[f"{key.upper()}_GEN"] = tpl_g
        p_arrow = os.path.join(self.template_dir, "arrow_head.png")
        if os.path.exists(p_arrow):
            tpl_arrow = cv2.imread(p_arrow)
            if tpl_arrow is not None:
                self.templates["ARROW_HEAD"] = tpl_arrow

        # Tier 1: Primary 1.0x templates (priority order for instant matching)
        self.primary_templates = []
        preferred_order = ["W_GEN", "A_GEN", "D_GEN", "ARROW_HEAD", "W", "A", "D"]
        for k in preferred_order:
            if k in self.templates and self.templates[k] is not None:
                tpl_gray = cv2.cvtColor(self.templates[k], cv2.COLOR_BGR2GRAY)
                self.primary_templates.append((k, tpl_gray))

        # Tier 2: Fallback scales for different window resolutions
        self.fallback_templates = []
        scales = [0.85, 1.15]
        for key_name, tpl in self.templates.items():
            if tpl is None:
                continue
            tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
            th, tw = tpl_gray.shape[:2]
            for s in scales:
                sw = int(tw * s)
                sh = int(th * s)
                if sw < 10 or sh < 10:
                    continue
                scaled_tpl = cv2.resize(tpl_gray, (sw, sh), interpolation=cv2.INTER_LINEAR)
                self.fallback_templates.append((key_name, scaled_tpl))

    def find_roblox_rect(self):
        """Finds Roblox window bounding box with caching for maximum performance."""
        now = time.time()
        # 1. Use cached handle if still valid
        if self.roblox_hwnd and win32gui.IsWindow(self.roblox_hwnd) and not win32gui.IsIconic(self.roblox_hwnd):
            if now - self.last_rect_check < 0.8 and self.cached_rect:
                return self.cached_rect
            try:
                rect = win32gui.GetWindowRect(self.roblox_hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 400 and h > 300:
                    self.cached_rect = rect
                    self.last_rect_check = now
                    return rect
            except Exception:
                self.roblox_hwnd = None

        # 2. Fast direct check
        try:
            hwnd = win32gui.FindWindow("WINDOWSCLIENT", None)
            if hwnd and win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 400 and h > 300:
                    self.roblox_hwnd = hwnd
                    self.cached_rect = rect
                    self.last_rect_check = now
                    return rect
        except Exception:
            pass

        # 3. Fallback EnumWindows only if not found
        self.roblox_hwnd = None
        def callback(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "roblox" in title.lower():
                        if not win32gui.IsIconic(hwnd):
                            self.roblox_hwnd = hwnd
                            return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass

        if self.roblox_hwnd and win32gui.IsWindow(self.roblox_hwnd):
            try:
                rect = win32gui.GetWindowRect(self.roblox_hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 400 and h > 300:
                    self.cached_rect = rect
                    self.last_rect_check = now
                    return rect
            except Exception:
                pass
        self.cached_rect = None
        return None

    def activate_roblox(self):
        """Brings Roblox window to foreground if found."""
        if not hasattr(self, 'roblox_hwnd') or not self.roblox_hwnd or not win32gui.IsWindow(self.roblox_hwnd):
            self.find_roblox_rect()
        if hasattr(self, 'roblox_hwnd') and self.roblox_hwnd and win32gui.IsWindow(self.roblox_hwnd):
            try:
                if win32gui.IsIconic(self.roblox_hwnd):
                    win32gui.ShowWindow(self.roblox_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.roblox_hwnd)
                return True
            except Exception:
                pass
        return False

    def get_safe_casting_coords(self, target_rect=None):
        """Calculates safe coordinates in water area to cast rod without hitting UI."""
        rect = target_rect or self.find_roblox_rect()
        if rect:
            left, top, right, bottom = rect
            # Center horizontally, 55% vertically (safe water surface)
            cx = (left + right) // 2
            cy = top + int((bottom - top) * 0.55)
            return cx, cy
        try:
            import win32api
            sw = win32api.GetSystemMetrics(0)
            sh = win32api.GetSystemMetrics(1)
            return sw // 2, int(sh * 0.55)
        except Exception:
            return 960, 540

    def capture_frame(self, target_rect=None):
        """
        Captures the screen or specific window.
        Ưu tiên mss (nhanh ~5-10ms), fallback sang ImageGrab (~50ms).
        Returns BGR numpy array or None.
        """
        try:
            if self.sct and target_rect:
                left, top, right, bottom = target_rect
                mon = {"left": left, "top": top, "width": right - left, "height": bottom - top}
                sct_img = self.sct.grab(mon)
                return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            elif self.sct:
                mon = self.sct.monitors[1]
                sct_img = self.sct.grab(mon)
                return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
        except Exception:
            pass
        # Fallback: ImageGrab
        try:
            if target_rect:
                left, top, right, bottom = target_rect
                img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            else:
                img = ImageGrab.grab(all_screens=True)
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception:
            pass
        return None

    def detect_key_prompt(self, frame_bgr):
        """
        Detects which key (W, A, D) is currently prompted via tiered template matching.
        Ultra-fast (1.5ms) on primary templates with early exit.
        Returns: dict with 'key', 'confidence', 'method' or None
        """
        if frame_bgr is None:
            return None

        h, w = frame_bgr.shape[:2]
        # Active keycap appears in central region of minigame
        y1, y2 = int(h * 0.22), int(h * 0.68)
        x1, x2 = int(w * 0.28), int(w * 0.72)
        roi_bgr = frame_bgr[y1:y2, x1:x2]
        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

        best_key = None
        best_score = 0.0

        # Pass 1: Ultra-fast check with primary 1.0x templates (1.5ms)
        for key_name, tpl_gray in self.primary_templates:
            sh, sw = tpl_gray.shape[:2]
            if sw >= roi_gray.shape[1] or sh >= roi_gray.shape[0]:
                continue
            res = cv2.matchTemplate(roi_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best_key = key_name
                if max_val > 0.80:
                    break

        # Pass 2: Fallback to scaled templates only if no clear match was found
        if best_score < 0.70 and hasattr(self, 'fallback_templates'):
            for key_name, scaled_tpl in self.fallback_templates:
                sh, sw = scaled_tpl.shape[:2]
                if sw >= roi_gray.shape[1] or sh >= roi_gray.shape[0]:
                    continue
                res = cv2.matchTemplate(roi_gray, scaled_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_key = key_name
                    if max_val > 0.82:
                        break

        if best_score > 0.55 and best_key:
            clean_key = best_key.split('_')[0]
            if clean_key == "ARROW":
                clean_key = "W"  # Prompt pull arrow defaults to reel up
            return {"key": clean_key, "confidence": float(best_score), "method": "template"}

        return None

    def detect_tension_bar(self, frame_bgr):
        """
        Detects if minigame HP/tension bar is on screen and calculates tension percentage.
        Returns:
            dict: {
                'active': bool,
                'tension_pct': float,
                'status': 'SAFE' | 'DANGER_HIGH' | 'DANGER_LOW' | 'UNKNOWN'
            }
        """
        if frame_bgr is None:
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

        h, w = frame_bgr.shape[:2]
        # Look in top 35% of Roblox screen
        roi_top = frame_bgr[0:int(h * 0.35), :]
        b, g, r = cv2.split(roi_top)
        
        # Red HP bar detection
        red_mask = (r > 120) & (r > 1.4 * b) & (r > 1.4 * g)
        cnts, _ = cv2.findContours(red_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_bars = []
        for c in cnts:
            bx, by, bw, bh = cv2.boundingRect(c)
            # HP bar is a horizontal bar
            if bw >= 80 and 4 <= bh <= 45 and (bw / float(bh)) >= 3.0:
                valid_bars.append((bx, by, bw, bh))

        if not valid_bars:
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

        min_x = min(b[0] for b in valid_bars)
        max_x = max(b[0] + b[2] for b in valid_bars)
        max_y = max(b[1] + b[3] for b in valid_bars)
        hp_height = max(b[3] for b in valid_bars)

        bar_y1 = max_y + 1
        bar_y2 = min(roi_top.shape[0], max_y + int(hp_height * 1.5) + 12)

        if bar_y2 <= bar_y1 + 4 or max_x <= min_x + 50:
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

        tension_crop = roi_top[bar_y1:bar_y2, min_x:max_x]
        if tension_crop.shape[0] < 5 or tension_crop.shape[1] < 50:
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

        # Analyze horizontal columns in tension bar
        tb, tg, tr = cv2.split(tension_crop)
        has_color = ((tb > 60) | (tg > 60) | (tr > 60)) & ~((tb < 40) & (tg < 40) & (tr < 40))
        col_active = np.sum(has_color, axis=0) > (tension_crop.shape[0] * 0.25)

        active_indices = np.where(col_active)[0]
        if len(active_indices) == 0:
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

        fill_right = active_indices[-1]
        tension_pct = (fill_right / float(tension_crop.shape[1])) * 100.0
        tension_pct = max(0.0, min(100.0, tension_pct))

        status = 'SAFE'
        if tension_pct > 78.0:
            status = 'DANGER_HIGH'
        elif tension_pct < 20.0:
            status = 'DANGER_LOW'

        return {
            'active': True,
            'tension_pct': round(float(tension_pct), 1),
            'status': status
        }

    def detect_caught_notification(self, frame_bgr):
        """
        Phát hiện thông báo 'Caught ...' xuất hiện ở đỉnh màn hình Roblox.
        Dùng 2 phương pháp kết hợp:
          1. Phát hiện màu vàng của icon coin (cam/vàng đặc trưng)
          2. Phát hiện màu trắng text trên nền xanh biển
        Returns: bool
        """
        if frame_bgr is None:
            return False

        h, w = frame_bgr.shape[:2]

        # Quét vùng rất hẹp: chỉ 8% đầu màn hình, giữa 15%-85%
        # Thông báo Caught luôn nằm ở dây đầu tiên, giữa màn hình
        y1, y2 = int(h * 0.02), int(h * 0.10)
        x1, x2 = int(w * 0.15), int(w * 0.85)
        roi = frame_bgr[y1:y2, x1:x2]

        if roi.shape[0] < 4 or roi.shape[1] < 20:
            return False

        b_ch, g_ch, r_ch = cv2.split(roi)
        r = r_ch.astype(np.int32)
        g = g_ch.astype(np.int32)
        b = b_ch.astype(np.int32)

        # Phương pháp 1: Icon coin màu VÀNG / CAM đặc trưng
        # Vàng: R cao, G cao, B thấp
        yellow_mask = (
            (r > 180) &
            (g > 130) &
            (b < 100) &
            (r > g + 30)  # R rõ ràng > G
        )
        yellow_count = int(np.sum(yellow_mask))
        roi_area = roi.shape[0] * roi.shape[1]
        if yellow_count / max(roi_area, 1) >= 0.003:  # 0.3% pixel vàng
            return True

        # Phương pháp 2: Text trắng thuần sáng (R≈G≈B > 210)
        white_mask = (
            (r > 210) &
            (g > 210) &
            (b > 210) &
            (np.abs(r - g) < 25) &
            (np.abs(r - b) < 25)
        )
        white_count = int(np.sum(white_mask))

        # Loại bỏ: nếu nền xanh biển chiếm ưu thế (không có thông báo)
        # Kiểm tra xem có đủ pixel trắng không (>= 0.5% vùng nhỏ này)
        if white_count / max(roi_area, 1) >= 0.005:
            return True

        return False

    def detect_chat_open(self, frame_bgr):
        """
        Phát hiện chat box Roblox đang mở (người dùng đang gõ chat).
        Chat input box xuất hiện ở góc DƯỚI TRÁI màn hình: nền trắng/xám sáng.

        Returns:
            bool: True nếu chat đang mở, False nếu không.
        """
        if frame_bgr is None:
            return False

        h, w = frame_bgr.shape[:2]

        # Vùng chat input: góc dưới trái, khoảng 5% chiều cao x 40% chiều rộng
        y1, y2 = int(h * 0.88), int(h * 0.98)
        x1, x2 = int(w * 0.01), int(w * 0.45)
        roi = frame_bgr[y1:y2, x1:x2]

        if roi.shape[0] < 5 or roi.shape[1] < 20:
            return False

        b_ch, g_ch, r_ch = cv2.split(roi)
        r = r_ch.astype(np.int32)
        g = g_ch.astype(np.int32)
        b = b_ch.astype(np.int32)

        # Chat box: vùng trắng/xám sáng (R≈G≈B > 180, độ lệch nhỏ)
        light_gray_mask = (
            (r > 180) & (g > 180) & (b > 180) &
            (np.abs(r - g) < 40) & (np.abs(r - b) < 40)
        )
        roi_area = roi.shape[0] * roi.shape[1]
        ratio = int(np.sum(light_gray_mask)) / max(roi_area, 1)

        # Nếu hơn 20% vùng đó là màu trắng/xám sáng → chat đang mở
        return ratio >= 0.20


if __name__ == '__main__':

    vision = RobloxVision()
    sample = cv2.imread(r"c:\Users\ASUS\OneDrive\Documents\BTVN\tool cau ca\templates\sample_minigame.png")
    
    key_res = vision.detect_key_prompt(sample)
    print("Detected Key:", key_res)
    
    tension_res = vision.detect_tension_bar(sample)
    print("Detected Tension Bar:", tension_res)
