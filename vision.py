import os
import cv2
import numpy as np
import mss
from PIL import Image, ImageDraw, ImageFont

class VisionSystem:
    def __init__(self, template_dir="templates"):
        self.sct = mss.mss()
        self.template_dir = os.path.abspath(template_dir)
        self.templates = {}
        self.ref_masks = {}
        self.target_monitor = None
        self._init_target_monitor()
        self.load_templates()
        self.init_reference_masks()

    def _init_target_monitor(self):
        """Automatically select the primary display or fallback to main screen."""
        for m in self.sct.monitors[1:]:
            if m.get("is_primary", False):
                self.target_monitor = m
                break
        if not self.target_monitor and len(self.sct.monitors) > 1:
            # Fallback: choose the monitor with left == 0 if available
            for m in self.sct.monitors[1:]:
                if m.get("left", 0) == 0:
                    self.target_monitor = m
                    break
        if not self.target_monitor:
            self.target_monitor = self.sct.monitors[1] if len(self.sct.monitors) > 1 else self.sct.monitors[0]

    def update_monitor_from_rect(self, rect):
        """If Roblox window rect is provided (left, top, right, bottom), select matching monitor."""
        if not rect:
            return
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        for m in self.sct.monitors[1:]:
            if m["left"] <= cx < m["left"] + m["width"] and m["top"] <= cy < m["top"] + m["height"]:
                self.target_monitor = m
                return

    def init_reference_masks(self):
        """Initializes 24x24 normalized binary reference masks for A, W, D, S."""
        # 1. Try loading clean extracted masks from templates first
        for char in ["A", "W", "D", "S"]:
            mask_path = os.path.join(self.template_dir, f"letter_mask_{char}.png")
            if os.path.exists(mask_path):
                img = cv2.imread(mask_path, 0)
                if img is not None:
                    self.ref_masks[char] = cv2.resize(img, (24, 24))
                    continue

            # Fallback: render font
            font_path = "C:/Windows/Fonts/bahnschrift.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/arialbd.ttf"
            try:
                font = ImageFont.truetype(font_path, 22)
                im = Image.new("L", (36, 36), 0)
                d = ImageDraw.Draw(im)
                d.text((6, 2), char, fill=255, font=font)
                np_im = np.array(im)
                pts = np.argwhere(np_im > 0)
                if len(pts) > 0:
                    y1, x1 = pts.min(axis=0)
                    y2, x2 = pts.max(axis=0)
                    crop = np_im[y1:y2+1, x1:x2+1]
                    self.ref_masks[char] = cv2.resize(crop, (24, 24))
                else:
                    self.ref_masks[char] = np.zeros((24, 24), dtype=np.uint8)
            except Exception:
                self.ref_masks[char] = np.zeros((24, 24), dtype=np.uint8)

    def load_templates(self):
        """Loads static UI templates for fishing combat and QTE."""
        base_files = {
            "pull_text": "pull_text.png",
            "pull_arrow_left": "pull_arrow_left.png",
            "luck_green_cap": "luck_green_cap.png",
            "strike_10x_zone": "strike_10x_zone.png",
            "strike_fish_icon": "strike_fish_icon.png",
            "key_A": "key_A.png",
            "key_W": "key_W.png",
            "key_D": "key_D.png",
            "key_S": "key_S.png"
        }
        for name, filename in base_files.items():
            path = os.path.join(self.template_dir, filename)
            if os.path.exists(path):
                img = cv2.imread(path)
                if img is not None:
                    self.templates[name] = img

        # Pre-cache grayscale & multi-scale arrow templates for ultra-fast QTE
        tpl_arrow = self.templates.get("pull_arrow_left")
        if tpl_arrow is not None:
            gray_l = cv2.cvtColor(tpl_arrow, cv2.COLOR_BGR2GRAY)
            gray_r = cv2.flip(gray_l, 1)
            self.templates["pull_arrow_left_gray"] = gray_l
            self.templates["pull_arrow_right_gray"] = gray_r
            self.templates["pull_arrow_left_small"] = cv2.resize(gray_l, (0, 0), fx=0.33, fy=0.33)
            self.templates["pull_arrow_right_small"] = cv2.resize(gray_r, (0, 0), fx=0.33, fy=0.33)

        # Pre-cache keycap grayscale templates and 0.5x half-scale templates
        for k in ["A", "W", "D", "S"]:
            tpl_k = self.templates.get(f"key_{k}")
            if tpl_k is not None:
                gray_k = cv2.cvtColor(tpl_k, cv2.COLOR_BGR2GRAY)
                self.templates[f"key_{k}_gray"] = gray_k
                self.templates[f"key_{k}_half"] = cv2.resize(gray_k, (0, 0), fx=0.5, fy=0.5)

    def to_screen_coords(self, x, y):
        """Converts frame-local (x, y) to global Windows desktop screen coordinates."""
        if not self.target_monitor:
            return int(x), int(y)
        return int(x + self.target_monitor.get("left", 0)), int(y + self.target_monitor.get("top", 0))

    def capture_screen(self, region=None):
        """Captures screenshot using MSS."""
        monitor = region if region else self.target_monitor
        sct_img = self.sct.grab(monitor)
        frame = np.array(sct_img)[:, :, :3]
        return frame, monitor

    def is_fish_hooked(self, frame):
        """
        Detects if fish is hooked by checking the red health bar at top-center.
        The boss health bar is a wide horizontal bar (> 450 red pixels).
        """
        h, w = frame.shape[:2]
        # Top-center region: y: 0 to 14%, x: 25% to 75%
        top_y = int(h * 0.14)
        left_x = int(w * 0.25)
        right_x = int(w * 0.75)
        zone = frame[0:top_y, left_x:right_x]

        hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([12, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([168, 80, 80]), np.array([180, 255, 255]))
        red_mask = mask1 | mask2

        red_pixels = cv2.countNonZero(red_mask)
        # Real fish health bar has thousands of red pixels; require at least 450
        return red_pixels > 450, red_pixels

    def detect_luck_boost(self, frame):
        """
        Nhận diện thanh LUCK BOOST khi đè giữ chuột quăng cần:
        - Quét tìm phần đỉnh màu xanh lá cây (nóc thanh LUCK BOOST).
        - Kiểm tra thanh lực màu trắng bên dưới đã tích đầy lên chạm đỉnh xanh lá cây chưa.
        Returns: (bar_found: bool, is_at_green_top: bool, (center_x, center_y))
        """
        h, w = frame.shape[:2]
        # Vùng trung tâm màn hình nơi hiển thị thanh Luck Boost
        y1, y2 = int(h * 0.15), int(h * 0.85)
        x1, x2 = int(w * 0.20), int(w * 0.80)
        zone = frame[y1:y2, x1:x2]

        hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, np.array([38, 100, 100]), np.array([82, 255, 255]))
        cnts, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in cnts:
            cx, cy, cw, ch = cv2.boundingRect(c)
            # Đỉnh xanh lá cây của thanh Luck Boost có kích thước đặc trưng
            if cw >= 8 and ch >= 10 and cv2.countNonZero(green_mask[cy:cy+ch, cx:cx+cw]) >= 15:
                # Kiểm tra thanh lực màu trắng đã sạc dâng lên chạm nóc xanh chưa
                check_zone = hsv[cy:cy+ch+8, max(0, cx-2):cx+cw+2]
                white_mask = cv2.inRange(check_zone, np.array([0, 0, 205]), np.array([180, 50, 255]))
                w_count = cv2.countNonZero(white_mask)
                is_full = w_count >= 12
                pos = (x1 + cx + cw // 2, y1 + cy + ch // 2)
                return True, is_full, pos

        return False, False, None

    def detect_strike_10x(self, frame):
        """
        Nhận diện thanh gây sát thương đầu tiên khi cá cắn câu:
        - Phát hiện thanh sát thương (phần thân màu xanh dương/cyan và đỉnh màu đỏ hồng x10 DAMAGE).
        - Theo dõi con cá trắng / con trượt di chuyển đến đỉnh màu đỏ (vùng x10 DAMAGE cao nhất).
        Returns: (bar_found: bool, is_10x: bool, (center_x, center_y))
        """
        h, w = frame.shape[:2]
        # Vùng trung tâm màn hình nơi xuất hiện thanh sát thương
        y1, y2 = int(h * 0.15), int(h * 0.85)
        x1, x2 = int(w * 0.20), int(w * 0.80)
        zone = frame[y1:y2, x1:x2]
        zh, zw = zone.shape[:2]

        hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)

        # 1. Thân thanh sát thương (màu xanh cyan/dương)
        cyan_mask = cv2.inRange(hsv, np.array([85, 80, 80]), np.array([105, 255, 255]))
        cnts, _ = cv2.findContours(cyan_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 2. Vùng đỏ hồng trên đỉnh (x10 DAMAGE)
        m1 = cv2.inRange(hsv, np.array([150, 60, 60]), np.array([180, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([12, 255, 255]))
        red_mask = m1 | m2

        for c in cnts:
            cx, cy, cw, ch = cv2.boundingRect(c)
            if cw >= 6 and ch >= 20 and cv2.countNonZero(cyan_mask[cy:cy+ch, cx:cx+cw]) >= 20:
                top_y1 = max(0, cy - int(ch * 0.7))
                top_y2 = min(zh, cy + int(ch * 0.15))

                # Kiểm tra vùng đỏ phía trên thân xanh trong đúng cột thanh năng lượng
                red_crop = red_mask[top_y1:top_y2, cx:cx+cw]
                if cv2.countNonZero(red_crop) >= 12:
                    # Đã phát hiện thanh sát thương cắn câu!
                    # Kiểm tra con cá trắng đã bơi vào vùng đỏ x10 trên đỉnh chưa
                    check_zone = hsv[top_y1:top_y2, cx:cx+cw]
                    white_mask = cv2.inRange(check_zone, np.array([0, 0, 210]), np.array([180, 50, 255]))
                    w_fish = cv2.countNonZero(white_mask)
                    is_10x = w_fish >= 12
                    pos = (x1 + cx + cw // 2, y1 + top_y1 + (top_y2 - top_y1) // 2)
                    return True, is_10x, pos

        # Fallback template matching nếu màu sắc bị ảnh hưởng bởi ánh sáng
        tpl_10x = self.templates.get("strike_10x_zone")
        if tpl_10x is not None and zh >= tpl_10x.shape[0] and zw >= tpl_10x.shape[1]:
            res = cv2.matchTemplate(zone, tpl_10x, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= 0.88:
                pos = (x1 + max_loc[0] + tpl_10x.shape[1] // 2, y1 + max_loc[1] + tpl_10x.shape[0] // 2)
                return True, True, pos

        return False, False, None

    def detect_vertical_bar(self, frame):
        """Hàm tương thích ngược với thanh cắn câu."""
        found, is_10x, pos = self.detect_strike_10x(frame)
        return found, pos

    def detect_qte(self, frame):
        """
        Scale-invariant, ultra-fast QTE detection:
        Layer 1: Keycap letter blob recognition (A, W, D, S) across resolutions (< 3ms).
        Layer 1.5: Fast pyramid template matching fallback (0.5x downsampled keycap templates).
        Layer 2: Fast pyramid arrow matching (Left -> A, Right -> D).
        Returns: ('A'/'W'/'D'/'S', (center_x, center_y), score) or (None, None, 0)
        """
        h, w = frame.shape[:2]
        # Crop combat zone: central 70% of screen (avoids chat at left, hotbar at bottom)
        if h > 150 and w > 150:
            y1, y2 = int(h * 0.15), int(h * 0.82)
            x1, x2 = int(w * 0.15), int(w * 0.85)
            zone = frame[y1:y2, x1:x2]
        else:
            y1, x1 = 0, 0
            zone = frame

        gray = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)

        # Layer 1: Scale-invariant Keycap Letter Recognition (Ultra fast: < 3ms)
        best_char = None
        best_score = 0.78
        best_pos = None

        for thresh_val in [170, 150, 130]:
            _, bright_mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                cx, cy, cw, ch = cv2.boundingRect(c)
                aspect = cw / float(ch)

                # Keycaps are roughly square (aspect 0.65 to 1.50) and size between 16px and 90px
                if 0.65 <= aspect <= 1.50 and 16 <= cw <= 90 and 16 <= ch <= 90:
                    keycap_crop = gray[cy:cy+ch, cx:cx+cw]
                    letter_mask = (keycap_crop < 130).astype(np.uint8) * 255

                    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(letter_mask)
                    if num_labels < 2:
                        continue

                    center_pt = (cw / 2.0, ch / 2.0)
                    for i in range(1, num_labels):
                        area = stats[i, cv2.CC_STAT_AREA]
                        if area < 8 or area > (cw * ch * 0.45):
                            continue
                        cent_x, cent_y = centroids[i]
                        if abs(cent_x - center_pt[0]) > cw * 0.35 or abs(cent_y - center_pt[1]) > ch * 0.35:
                            continue

                        clean_letter = (labels == i).astype(np.uint8) * 255
                        pts = np.argwhere(clean_letter > 0)
                        if len(pts) < 8:
                            continue

                        ly1, lx1 = pts.min(axis=0)
                        ly2, lx2 = pts.max(axis=0)
                        letter_box = clean_letter[ly1:ly2+1, lx1:lx2+1]
                        norm_letter = cv2.resize(letter_box, (24, 24))

                        scores = {}
                        for char in ['A', 'W', 'D', 'S']:
                            ref = self.ref_masks.get(char)
                            if ref is not None:
                                res = cv2.matchTemplate(norm_letter, ref, cv2.TM_CCOEFF_NORMED)
                                scores[char] = float(res[0][0])

                        if scores:
                            sorted_s = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                            top_c, top_s = sorted_s[0]
                            second_s = sorted_s[1][1] if len(sorted_s) > 1 else 0.0
                            if top_s > best_score and (top_s - second_s >= 0.05):
                                best_score = top_s
                                best_char = top_c
                                best_pos = (x1 + cx + cw // 2, y1 + cy + ch // 2)

            if best_char and best_score >= 0.80:
                break

        if best_char is not None:
            return best_char, best_pos, best_score

        # Layer 1.5: Fast Half-Scale Template Matching Fallback (~20ms)
        zh, zw = gray.shape[:2]
        if zh >= 60 and zw >= 60:
            gray_half = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
            tpl_scores = {}
            tpl_locs = {}
            for char in ['A', 'W', 'D', 'S']:
                tpl_h = self.templates.get(f"key_{char}_half")
                if tpl_h is not None and gray_half.shape[0] >= tpl_h.shape[0] and gray_half.shape[1] >= tpl_h.shape[1]:
                    res = cv2.matchTemplate(gray_half, tpl_h, cv2.TM_CCOEFF_NORMED)
                    _, max_v, _, max_loc = cv2.minMaxLoc(res)
                    tpl_scores[char] = float(max_v)
                    tpl_locs[char] = (max_loc, tpl_h.shape)

            if tpl_scores:
                sorted_tpl = sorted(tpl_scores.items(), key=lambda x: x[1], reverse=True)
                top_c, top_s = sorted_tpl[0]
                second_s = sorted_tpl[1][1] if len(sorted_tpl) > 1 else 0.0
                if top_s >= 0.78 and (top_s - second_s >= 0.08):
                    loc, t_shape = tpl_locs[top_c]
                    cx = int(loc[0] / 0.5) + t_shape[1]
                    cy = int(loc[1] / 0.5) + t_shape[0]
                    return top_c, (x1 + cx, y1 + cy), top_s

        # Layer 2: Fast Pyramid Arrow Match (Left -> A, Right -> D)
        tpl_s_l = self.templates.get("pull_arrow_left_small")
        tpl_s_r = self.templates.get("pull_arrow_right_small")
        tpl_full_l = self.templates.get("pull_arrow_left_gray")
        tpl_full_r = self.templates.get("pull_arrow_right_gray")

        if tpl_s_l is not None and tpl_full_l is not None:
            zh, zw = gray.shape[:2]
            th, tw = tpl_full_l.shape[:2]
            if zh >= th and zw >= tw:
                gray_small = cv2.resize(gray, (0, 0), fx=0.33, fy=0.33)
                # Check left arrow
                res_l = cv2.matchTemplate(gray_small, tpl_s_l, cv2.TM_CCOEFF_NORMED)
                _, max_sl, _, loc_sl = cv2.minMaxLoc(res_l)
                if max_sl >= 0.62:
                    rx = max(0, int(loc_sl[0] / 0.33) - 15)
                    ry = max(0, int(loc_sl[1] / 0.33) - 15)
                    rw = min(zw - rx, tw + 30)
                    rh = min(zh - ry, th + 30)
                    if rh >= th and rw >= tw:
                        sub_roi = gray[ry:ry+rh, rx:rx+rw]
                        r_full = cv2.matchTemplate(sub_roi, tpl_full_l, cv2.TM_CCOEFF_NORMED)
                        _, score_f, _, loc_f = cv2.minMaxLoc(r_full)
                        if score_f >= 0.75:
                            pos = (x1 + rx + loc_f[0] + tw // 2, y1 + ry + loc_f[1] + th // 2)
                            return 'A', pos, float(score_f)

                # Check right arrow
                if tpl_s_r is not None and tpl_full_r is not None:
                    res_r = cv2.matchTemplate(gray_small, tpl_s_r, cv2.TM_CCOEFF_NORMED)
                    _, max_sr, _, loc_sr = cv2.minMaxLoc(res_r)
                    if max_sr >= 0.62:
                        rx = max(0, int(loc_sr[0] / 0.33) - 15)
                        ry = max(0, int(loc_sr[1] / 0.33) - 15)
                        rw = min(zw - rx, tw + 30)
                        rh = min(zh - ry, th + 30)
                        if rh >= th and rw >= tw:
                            sub_roi = gray[ry:ry+rh, rx:rx+rw]
                            r_full = cv2.matchTemplate(sub_roi, tpl_full_r, cv2.TM_CCOEFF_NORMED)
                            _, score_f, _, loc_f = cv2.minMaxLoc(r_full)
                            if score_f >= 0.75:
                                pos = (x1 + rx + loc_f[0] + tw // 2, y1 + ry + loc_f[1] + th // 2)
                                return 'D', pos, float(score_f)

        return None, None, 0
