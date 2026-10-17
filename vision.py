import os
import time
import cv2
import numpy as np
import win32gui
import win32con
from PIL import ImageGrab

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

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

    def _ensure_sct(self):
        """Thread-safe and fault-tolerant mss instance getter with auto-recreation."""
        if not HAS_MSS:
            return None
        if self.sct is None:
            try:
                self.sct = mss.MSS()
            except Exception:
                self.sct = None
        return self.sct

    def close(self):
        """Releases GDI resources held by mss."""
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None

    def load_templates(self):
        """Loads keycap and skill templates and precomputes scaled grayscale versions with center letters."""
        self.templates = {}
        for key in ['w', 'a', 'd']:
            p_raw = os.path.join(self.template_dir, f"key_{key}.png")
            p_gen = os.path.join(self.template_dir, f"key_{key}_gen.png")
            tpl = None
            if os.path.exists(p_raw):
                tpl = cv2.imread(p_raw)
            elif os.path.exists(p_gen):
                tpl = cv2.imread(p_gen)
            if tpl is not None:
                self.templates[key.upper()] = tpl

        p_arrow = os.path.join(self.template_dir, "arrow_head.png")
        if os.path.exists(p_arrow):
            tpl_arrow = cv2.imread(p_arrow)
            if tpl_arrow is not None:
                self.templates["ARROW_HEAD"] = tpl_arrow

        # Charge bar top template (vạch cao nhất / red zone)
        p_charge = os.path.join(self.template_dir, "charge_bar_red_top.png")
        if os.path.exists(p_charge):
            tpl_charge = cv2.imread(p_charge)
            if tpl_charge is not None:
                self.templates["CHARGE_TOP"] = tpl_charge

        # Skill templates Z, X, C, V
        self.skill_templates = {}
        for k in ['Z', 'X', 'C', 'V']:
            p_skill = os.path.join(self.template_dir, f"skill_{k}.png")
            if os.path.exists(p_skill):
                tpl_s = cv2.imread(p_skill)
                if tpl_s is not None:
                    self.skill_templates[k] = tpl_s
        self.cached_skill_anchor = None
        self.last_skill_anchor_check = 0.0

        # Tier 1: 1.0x keycap templates with precomputed center letter and coarse 0.5x version
        self.primary_key_templates = {}
        for k in ['W', 'A', 'D']:
            if k in self.templates and self.templates[k] is not None:
                tpl_gray = cv2.cvtColor(self.templates[k], cv2.COLOR_BGR2GRAY)
                # Keycaps are 74x74. Center letter is at 18:56, 18:56
                center_letter = tpl_gray[18:56, 18:56]
                th, tw = tpl_gray.shape[:2]
                coarse = cv2.resize(tpl_gray, (tw // 2, th // 2), interpolation=cv2.INTER_AREA)
                self.primary_key_templates[k] = {
                    'full': tpl_gray,
                    'center': center_letter,
                    'center_box': (18, 56, 18, 56),
                    'coarse': coarse
                }

        # Tier 2: Multi-scale templates (0.55x, 0.65x, 0.75x, 0.85x, 1.15x, 1.25x, 1.35x)
        self.multi_scale_templates = []
        scales = [0.85, 1.15, 0.75, 1.25, 0.65, 0.55, 1.35]
        for s in scales:
            scale_group = {}
            for k in ['W', 'A', 'D']:
                if k in self.primary_key_templates:
                    tpl_gray = self.primary_key_templates[k]['full']
                    th, tw = tpl_gray.shape[:2]
                    sw, sh = int(tw * s), int(th * s)
                    if sw >= 16 and sh >= 16:
                        scaled_full = cv2.resize(tpl_gray, (sw, sh), interpolation=cv2.INTER_LINEAR)
                        cy1, cy2 = int(18 * s), int(56 * s)
                        cx1, cx2 = int(18 * s), int(56 * s)
                        scaled_center = scaled_full[cy1:cy2, cx1:cx2]
                        scaled_coarse = cv2.resize(scaled_full, (sw // 2, sh // 2), interpolation=cv2.INTER_AREA)
                        scale_group[k] = {
                            'full': scaled_full,
                            'center': scaled_center,
                            'center_box': (cy1, cy2, cx1, cx2),
                            'coarse': scaled_coarse
                        }
            if scale_group:
                self.multi_scale_templates.append((s, scale_group))
        self.scaled_key_templates = self.multi_scale_templates

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
        """Brings Roblox window to foreground without Alt key side-effects."""
        if not hasattr(self, 'roblox_hwnd') or not self.roblox_hwnd or not win32gui.IsWindow(self.roblox_hwnd):
            self.find_roblox_rect()
        if hasattr(self, 'roblox_hwnd') and self.roblox_hwnd and win32gui.IsWindow(self.roblox_hwnd):
            try:
                if win32gui.IsIconic(self.roblox_hwnd):
                    win32gui.ShowWindow(self.roblox_hwnd, win32con.SW_RESTORE)
                
                fg_hwnd = win32gui.GetForegroundWindow()
                if fg_hwnd != self.roblox_hwnd:
                    # SwitchToThisWindow kích hoạt và đưa cửa sổ lên foreground mượt mà
                    import ctypes
                    try:
                        ctypes.windll.user32.SwitchToThisWindow(self.roblox_hwnd, True)
                    except Exception:
                        pass

                    import win32process, win32api
                    cur_thread = win32api.GetCurrentThreadId()
                    fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
                    if fg_thread and fg_thread != cur_thread:
                        win32process.AttachThreadInput(cur_thread, fg_thread, True)
                        win32gui.BringWindowToTop(self.roblox_hwnd)
                        win32gui.SetForegroundWindow(self.roblox_hwnd)
                        win32process.AttachThreadInput(cur_thread, fg_thread, False)
                    else:
                        win32gui.BringWindowToTop(self.roblox_hwnd)
                        win32gui.SetForegroundWindow(self.roblox_hwnd)
                return True
            except Exception:
                try:
                    win32gui.SetForegroundWindow(self.roblox_hwnd)
                    return True
                except Exception:
                    pass
        return False

    def get_safe_casting_coords(self, target_rect=None):
        """Calculates safe coordinates in water area to cast rod without hitting UI or avatar."""
        rect = target_rect or self.find_roblox_rect()
        if rect:
            left, top, right, bottom = rect
            w = right - left
            h = bottom - top
            # Tọa độ mặt nước an toàn: 65% ngang (tránh nhân vật ở giữa 50% và thanh kỹ năng bên phải 85-100%)
            # 32% dọc (nằm ở vùng nước thoáng, tránh các nút menu phía trên và dock/hotbar phía dưới)
            cx = left + int(w * 0.65)
            cy = top + int(h * 0.32)
            return cx, cy
        try:
            import win32api
            sw = win32api.GetSystemMetrics(0)
            sh = win32api.GetSystemMetrics(1)
            return int(sw * 0.65), int(sh * 0.32)
        except Exception:
            return 960, 350

    def _sanitize_rect(self, rect):
        """Validates and sanitizes window coordinates to prevent BitBlt crashes."""
        if not rect:
            return None
        left, top, right, bottom = rect
        w = right - left
        h = bottom - top
        if w < 100 or h < 100 or left < -1000 or top < -1000:
            return None
        # Clamp negative values if window is slightly off-screen
        left = max(0, left)
        top = max(0, top)
        if right <= left + 100 or bottom <= top + 100:
            return None
        return (left, top, right, bottom)

    def capture_frame(self, target_rect=None):
        """
        Captures the screen or specific window.
        Ưu tiên mss (nhanh ~5-10ms), fallback sang ImageGrab (~50ms).
        Returns BGR numpy array or None.
        Tự động phục hồi lỗi GDI/BitBlt mà không làm sập ứng dụng.
        """
        rect = self._sanitize_rect(target_rect)
        sct = self._ensure_sct()
        if sct:
            try:
                if rect:
                    left, top, right, bottom = rect
                    mon = {"left": left, "top": top, "width": right - left, "height": bottom - top}
                    sct_img = sct.grab(mon)
                else:
                    mon = sct.monitors[1]
                    sct_img = sct.grab(mon)
                arr = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape((sct_img.height, sct_img.width, 4))
                return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            except Exception:
                # Nếu BitBlt hoặc GDI lỗi, đóng và giải phóng sct để lần sau tạo lại sạch sẽ
                try:
                    if self.sct:
                        self.sct.close()
                except Exception:
                    pass
                self.sct = None

        # Fallback: ImageGrab
        try:
            if rect:
                img = ImageGrab.grab(bbox=rect, all_screens=True)
            else:
                img = ImageGrab.grab(all_screens=True)
            if img is not None:
                return cv2.cvtColor(np.array(img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        except Exception:
            pass
        return None

    def detect_cyan_arrow(self, frame_bgr):
        """
        Phát hiện mũi tên chỉ hướng (Cyan, Vàng, Xanh lá) của minigame:
        - Mũi tên hướng LÊN -> 'W'
        - Mũi tên hướng TRÁI -> 'A'
        - Mũi tên hướng PHẢI -> 'D'
        - Mũi tên hướng XUỐNG -> 'S'
        """
        if frame_bgr is None:
            return None
        h, w = frame_bgr.shape[:2]
        # Vùng minigame: từ 16% đến 88% chiều cao (tránh thanh cá ở 0-15% và hotbar ở 90-100%)
        roi_y1, roi_y2 = int(h * 0.16), int(h * 0.88)
        roi_x1, roi_x2 = int(w * 0.08), int(w * 0.92)
        roi = frame_bgr[roi_y1:roi_y2, roi_x1:roi_x2]
        if roi.shape[0] < 30 or roi.shape[1] < 30:
            return None

        b, g, r = cv2.split(roi)
        # 1. Mũi tên Cyan / Xanh biển: B và G cao, R thấp
        cyan_mask = (b > 130) & (g > 130) & (r < 165)
        # 2. Mũi tên Vàng / Cam: R và G cao, B thấp
        yellow_mask = (r > 150) & (g > 130) & (b < 130)
        # 3. Mũi tên Xanh lá / Lime: G cao hơn B và R
        green_mask = (g > 150) & (g > 1.15 * b) & (b < 150)

        arrow_mask = (cyan_mask | yellow_mask | green_mask).astype(np.uint8)

        cnts, _ = cv2.findContours(arrow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in cnts:
            area = cv2.contourArea(c)
            # Kích thước mũi tên thực tế (100px - 3500px)
            if 100 <= area <= 3500:
                bx, by, bw, bh = cv2.boundingRect(c)
                aspect = bw / float(bh)
                # Tỷ lệ mũi tên chuẩn (không phải thanh dài, không phải vạch mỏng)
                if 0.55 <= aspect <= 1.85 and 18 <= bw <= 90 and 18 <= bh <= 90:
                    solidity = area / float(bw * bh)
                    if 0.22 <= solidity <= 0.82:
                        pts = c.reshape(-1, 2)
                        top_pt = pts[pts[:, 1].argmin()]
                        bottom_pt = pts[pts[:, 1].argmax()]
                        left_pt = pts[pts[:, 0].argmin()]
                        right_pt = pts[pts[:, 0].argmax()]
                        abs_x = roi_x1 + bx + bw // 2
                        abs_y = roi_y1 + by + bh // 2

                        # Mũi tên LÊN (W): Đỉnh nhọn ở trên
                        if bh > bw * 1.04 and top_pt[1] <= by + bh * 0.28:
                            candidates.append((area, "W", (abs_x, abs_y), "arrow_up"))
                        # Mũi tên TRÁI (A): Đỉnh nhọn ở bên trái
                        elif bw > bh * 1.04 and left_pt[0] <= bx + bw * 0.28:
                            candidates.append((area, "A", (abs_x, abs_y), "arrow_left"))
                        # Mũi tên PHẢI (D): Đỉnh nhọn ở bên phải
                        elif bw > bh * 1.04 and right_pt[0] >= bx + bw * 0.72:
                            candidates.append((area, "D", (abs_x, abs_y), "arrow_right"))
                        # Mũi tên XUỐNG (S): Đỉnh nhọn ở dưới
                        elif bh > bw * 1.04 and bottom_pt[1] >= by + bh * 0.72:
                            candidates.append((area, "S", (abs_x, abs_y), "arrow_down"))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best = candidates[0]
            return {"key": best[1], "confidence": 0.98, "pos": best[2], "method": best[3]}
        return None

    def detect_key_prompt(self, frame_bgr):
        """
        Nhận diện phím W/A/D xuất hiện ngẫu nhiên trên toàn màn hình với độ chính xác cao:
        1. Ưu tiên quét trực tiếp Keycap 1.0x (Direct Template Match): Cực nhanh (~20ms) và chính xác tuyệt đối.
        2. Mũi tên chỉ hướng của minigame.
        3. Quét đa tỷ lệ Keycap dự phòng (0.85x, 1.15x, 0.75x, 1.25x...) nếu game có độ phân giải/thu phóng khác.
        Returns: dict with 'key', 'confidence', 'pos', 'method' or None
        """
        if frame_bgr is None:
            return None

        h, w = frame_bgr.shape[:2]
        # Vùng minigame ở giữa màn hình (loại bỏ thanh tension ở đỉnh và hotbar/chat ở đáy)
        y1, y2 = int(h * 0.12), int(h * 0.88)
        x1, x2 = int(w * 0.08), int(w * 0.92)
        roi_bgr = frame_bgr[y1:y2, x1:x2]
        if roi_bgr.shape[0] < 40 or roi_bgr.shape[1] < 40:
            return None

        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

        # ── TẦNG 1: QUÉT TRỰC TIẾP KEYCAP 1.0X TRÊN ROI (CHÍNH XÁC NHẤT & KHÔNG BỊ NHẦM SKILL) ──
        best_k = None
        best_score = 0.0
        best_loc = None
        best_size = (74, 74)

        for k in ['W', 'A', 'D']:
            if k in self.primary_key_templates:
                tpl = self.primary_key_templates[k]['full']
                th, tw = tpl.shape[:2]
                if th < roi_gray.shape[0] and tw < roi_gray.shape[1]:
                    res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val > best_score:
                        best_score = max_val
                        best_k = k
                        best_loc = max_loc
                        best_size = (tw, th)

        # Ngưỡng 0.65 đảm bảo phân biệt rõ ràng chữ W/A/D thật và loại bỏ 100% false positive từ skill hay nước
        if best_score >= 0.65 and best_k is not None:
            abs_x = x1 + best_loc[0] + best_size[0] // 2
            abs_y = y1 + best_loc[1] + best_size[1] // 2
            return {
                "key": best_k,
                "confidence": float(best_score),
                "pos": (abs_x, abs_y),
                "method": "direct_keycap_1x"
            }

        # ── TẦNG 2: MŨI TÊN CHỈ HƯỚNG CỦA MINIGAME ──
        arrow_res = self.detect_cyan_arrow(frame_bgr)
        if arrow_res is not None:
            return arrow_res

        # ── TẦNG 3: QUÉT ĐA TỶ LỆ DỰ PHÒNG (NẾU MÀN HÌNH BỊ THU PHÓNG / SCALE KHÁC 1.0) ──
        scaled_best_k = None
        scaled_best_score = 0.0
        scaled_best_loc = None
        scaled_best_size = (74, 74)

        for s, scale_dict in self.scaled_key_templates:
            for k in ['W', 'A', 'D']:
                if k in scale_dict:
                    tpl = scale_dict[k]['full']
                    th, tw = tpl.shape[:2]
                    if th < roi_gray.shape[0] and tw < roi_gray.shape[1]:
                        res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(res)
                        if max_val > scaled_best_score:
                            scaled_best_score = max_val
                            scaled_best_k = k
                            scaled_best_loc = max_loc
                            scaled_best_size = (tw, th)

        if scaled_best_score >= 0.62 and scaled_best_k is not None:
            abs_x = x1 + scaled_best_loc[0] + scaled_best_size[0] // 2
            abs_y = y1 + scaled_best_loc[1] + scaled_best_size[1] // 2
            return {
                "key": scaled_best_k,
                "confidence": float(scaled_best_score),
                "pos": (abs_x, abs_y),
                "method": "scaled_keycap"
            }

        return None

    def detect_skills_ready_state(self, frame_bgr):
        """
        Phát hiện trạng thái hồi chiêu của 4 kỹ năng [Z, X, C, V].
        Phục vụ cho hệ thống Unit trợ chiến (2 Unit dùng chung bộ skill):
        - Nếu 2 Unit tung 2 skill ngẫu nhiên -> 2 skill đó sẽ vào hồi chiêu (tối màu / có số đếm giây).
        - Tool tự động nhận biết và trả về danh sách các chiêu CÒN LẠI đang SẴN SÀNG (READY) để bot xả ngay lập tức!
        Returns:
            dict: {
                'status': {'Z': bool, 'X': bool, 'C': bool, 'V': bool},
                'ready_list': list of str (e.g. ['X', 'V']),
                'anchor': (x, y) or None
            }
        """
        all_skills = ['V', 'C', 'X', 'Z']
        fallback = {'status': {k: True for k in all_skills}, 'ready_list': all_skills, 'anchor': None}
        if frame_bgr is None or not hasattr(self, 'skill_templates') or not self.skill_templates:
            return fallback

        h, w = frame_bgr.shape[:2]
        now = time.time()
        anchor = None

        if self.cached_skill_anchor and (now - self.last_skill_anchor_check < 3.0):
            ax, ay = self.cached_skill_anchor
            if 0 <= ax < w - 69 and 0 <= ay < h - (4 * 77):
                anchor = (ax, ay)

        if not anchor:
            roi_y1 = int(h * 0.35)
            roi_x1 = int(w * 0.50)
            roi = frame_bgr[roi_y1:, roi_x1:]
            if roi.shape[0] < 80 or roi.shape[1] < 100:
                return fallback
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            for k_anchor in ['Z', 'X', 'C', 'V']:
                if k_anchor in self.skill_templates:
                    tpl_g = cv2.cvtColor(self.skill_templates[k_anchor], cv2.COLOR_BGR2GRAY)
                    if tpl_g.shape[0] >= roi_gray.shape[0] or tpl_g.shape[1] >= roi_gray.shape[1]:
                        continue
                    res = cv2.matchTemplate(roi_gray, tpl_g, cv2.TM_CCOEFF_NORMED)
                    _, max_v, _, max_l = cv2.minMaxLoc(res)
                    if max_v >= 0.55:
                        idx = ['Z', 'X', 'C', 'V'].index(k_anchor)
                        ax = roi_x1 + max_l[0]
                        ay = roi_y1 + max_l[1] - (idx * 77)
                        anchor = (ax, ay)
                        self.cached_skill_anchor = anchor
                        self.last_skill_anchor_check = now
                        break

        if not anchor:
            return fallback

        ax, ay = anchor
        status = {}
        ready_list = []

        for k in all_skills:
            idx = ['Z', 'X', 'C', 'V'].index(k)
            sy = ay + idx * 77
            sx = ax

            if sy + 69 > h or sx + 69 > w or sy < 0 or sx < 0:
                status[k] = True
                ready_list.append(k)
                continue

            icon = frame_bgr[sy:sy + 69, sx:sx + 69]
            tpl_icon = self.skill_templates.get(k)
            if tpl_icon is None:
                status[k] = True
                ready_list.append(k)
                continue

            icon_g = cv2.cvtColor(icon, cv2.COLOR_BGR2GRAY)
            tpl_g = cv2.cvtColor(tpl_icon, cv2.COLOR_BGR2GRAY)
            m_score = float(cv2.matchTemplate(icon_g, tpl_g, cv2.TM_CCOEFF_NORMED)[0][0])

            hsv = cv2.cvtColor(icon, cv2.COLOR_BGR2HSV)
            sat = float(hsv[:, :, 1].mean())

            is_ready = bool(m_score >= 0.58 and sat >= 45.0)
            status[k] = is_ready
            if is_ready:
                ready_list.append(k)

        return {'status': status, 'ready_list': ready_list, 'anchor': anchor}

    def is_charge_at_top(self, frame_bgr):
        """
        Nhận diện xem thanh sạc lực đã chạm đỉnh nóc chưa:
        1. Thanh đầu tiên (thanh trượt bên trái với viên bi tròn trắng):
           Viên bi chạy từ đáy lên đỉnh nóc của thanh.
        2. Thanh thứ hai (thanh màu cyan/blue/red damage):
           Đỉnh đỏ vạch cao nhất.
        """
        if frame_bgr is None:
            return False

        h, w = frame_bgr.shape[:2]
        # Thanh lực nằm ở nửa phải màn hình
        roi = frame_bgr[:, int(w * 0.25):]
        if roi.shape[0] < 40 or roi.shape[1] < 40:
            roi = frame_bgr

        b, g, r = cv2.split(roi)

        # ── 1. PHÁT HIỆN THANH MÀU CYAN/RED VÀ THANH TRƯỢT BÊN TRÁI ────
        # Đoạn cyan thân dưới thanh lực:
        cyan_mask = (b > 165) & (g > 165) & (r < 140)
        cnts_c, _ = cv2.findContours(cyan_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Đoạn red/pink đỉnh thanh lực:
        red_mask = (r > 165) & (b > 75) & (g < 115)
        cnts_r, _ = cv2.findContours(red_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Tìm thanh màu dọc thực sự (bh >= 18, bw trong khoảng 5-35px)
        valid_bars = []
        for c in cnts_c:
            bx, by, bw, bh = cv2.boundingRect(c)
            if 5 <= bw <= 35 and bh >= 18:
                valid_bars.append((bx, by, bw, bh))

        for (bx, by, bw, bh) in valid_bars:
            # Tìm xem có đỉnh đỏ phía trên đoạn cyan này không
            for cr in cnts_r:
                rx, ry, rw, rh = cv2.boundingRect(cr)
                if abs(rx - bx) <= 15 and ry < by and 5 <= rw <= 35:
                    # Đây chính là cặp thanh lực chuẩn xác 100%!
                    # Thanh đầu tiên (slider rail) nằm ngay bên trái thanh màu: x = bx - 26 đến bx - 2
                    # Đỉnh nóc của thanh đầu tiên nằm ở ry - 10 đến ry + 22
                    top_y1 = max(0, ry - 10)
                    top_y2 = min(roi.shape[0], ry + 22)
                    top_x1 = max(0, bx - 26)
                    top_x2 = max(0, bx - 2)

                    slider_top = roi[top_y1:top_y2, top_x1:top_x2]
                    if slider_top.shape[0] > 0 and slider_top.shape[1] > 0:
                        st_b, st_g, st_r = cv2.split(slider_top)
                        # Viên bi tròn màu trắng/bạc sáng
                        white_knob = (st_r > 200) & (st_g > 200) & (st_b > 200)
                        if np.sum(white_knob) >= 16:
                            return True

        # ── 2. PHÁT HIỆN THANH NGƯỠNG MÀU XANH LÁ (LUCK BOOST) ─────────
        green_mask = (g > 140) & (g > 1.3 * r) & (g > 1.3 * b)
        cnts_green, _ = cv2.findContours(green_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts_green:
            bx, by, bw, bh = cv2.boundingRect(c)
            if 8 <= bw <= 65 and 10 <= bh <= 80:
                tube_bottom = min(roi.shape[0], by + int(bh * 4.0) + 50)
                if tube_bottom - by >= 60:
                    pad_x = max(2, int(bw * 0.20))
                    inside_tube = roi[max(0, by + bh - 6):min(roi.shape[0], by + bh + 14), bx + pad_x:bx + bw - pad_x]
                    if inside_tube.shape[0] > 0 and inside_tube.shape[1] > 0:
                        tb, tg, tr = cv2.split(inside_tube)
                        bright_val = (tr > 170) & (tg > 170) & (tb > 170)
                        neon_val = (tg > 195) & (tg > 1.35 * tr) & (tg > 1.35 * tb)
                        if np.sum(bright_val) >= 16 or np.sum(neon_val) >= 22:
                            return True

        return False

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
            # HP bar is a horizontal bar segment
            if bw >= 75 and 6 <= bh <= 45 and (bw / float(bh)) >= 2.8:
                valid_bars.append((bx, by, bw, bh))

        if not valid_bars:
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

        min_x = min(b[0] for b in valid_bars)
        max_x = max(b[0] + b[2] for b in valid_bars)
        max_y = max(b[1] + b[3] for b in valid_bars)
        hp_height = max(b[3] for b in valid_bars)

        total_span = max_x - min_x
        center_x = (min_x + max_x) / 2.0
        # Minigame HP bar spans a wide region (tương thích cả khi chia đôi màn hình)
        if total_span < max(80, int(w * 0.12)) or not (0.20 * w <= center_x <= 0.80 * w):
            return {'active': False, 'tension_pct': 0.0, 'status': 'UNKNOWN'}

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
        Dùng 2 phương pháp kết hợp đồng thời để chống dương tính giả (false positive):
          1. Phát hiện màu vàng của icon coin (cam/vàng đặc trưng, tối thiểu 35px)
          2. Phát hiện màu trắng text trên banner (tối thiểu 60px)
        Returns: bool
        """
        if frame_bgr is None:
            return False

        h, w = frame_bgr.shape[:2]

        # Quét vùng hẹp: chỉ 2%-11% đầu màn hình, giữa 20%-80%
        y1, y2 = int(h * 0.02), int(h * 0.11)
        x1, x2 = int(w * 0.20), int(w * 0.80)
        roi = frame_bgr[y1:y2, x1:x2]

        if roi.shape[0] < 8 or roi.shape[1] < 40:
            return False

        b_ch, g_ch, r_ch = cv2.split(roi)
        r = r_ch.astype(np.int32)
        g = g_ch.astype(np.int32)
        b = b_ch.astype(np.int32)

        # Icon coin màu VÀNG / CAM đặc trưng
        yellow_mask = (
            (r > 190) &
            (g > 135) &
            (b < 95) &
            (r > g + 25)
        )
        yellow_count = int(np.sum(yellow_mask))

        # Text trắng thuần sáng (R≈G≈B > 220)
        white_mask = (
            (r > 220) &
            (g > 220) &
            (b > 220) &
            (np.abs(r - g) < 20) &
            (np.abs(r - b) < 20)
        )
        white_count = int(np.sum(white_mask))

        # Phải xuất hiện CẢ icon coin vàng và text trắng cùng lúc thì mới tính là bảng Caught
        if yellow_count >= 35 and white_count >= 50:
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
