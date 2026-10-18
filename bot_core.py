import time
import threading
from vision import VisionSystem
from input_controller import InputController
from config_manager import load_config, save_config

STATE_IDLE = "IDLE"
STATE_CASTING = "CASTING"
STATE_WAIT_BITE = "WAIT_BITE"
STATE_FIGHT = "FIGHT"
STATE_CAUGHT = "CAUGHT"

class FishingBot:
    def __init__(self, log_callback=None, status_callback=None, count_callback=None):
        self.config = load_config()
        self.vision = VisionSystem()
        self.controller = InputController()
        
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.count_callback = count_callback
        
        self.is_running = False
        self.thread = None
        self.state = STATE_IDLE
        self.fish_count = self.config.get("current_fish", 0)
        
        self.skill_cooldowns = {}
        self.active_qte_key = None

    def log(self, msg):
        print(f"[Bot] {msg}", flush=True)
        if self.log_callback:
            self.log_callback(msg)

    def set_state(self, new_state):
        self.state = new_state
        if self.status_callback:
            self.status_callback(new_state)

    def set_fish_count(self, count):
        self.fish_count = count
        self.config["current_fish"] = count
        save_config(self.config)
        if self.count_callback:
            self.count_callback(count)

    def start(self):
        if self.is_running:
            return
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.3)
        self.is_running = True
        self.controller.focus_roblox()
        roblox_rect = self.controller.get_roblox_rect()
        if roblox_rect:
            self.vision.update_monitor_from_rect(roblox_rect)
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.log(">>> AUTO ĐÃ KHỞI ĐỘNG (F6)! <<<")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self.active_qte_key:
            self.controller.key_up(self.active_qte_key)
            self.active_qte_key = None
        self.set_state(STATE_IDLE)
        self.log(">>> AUTO ĐÃ DỪNG LẠI (F6)! <<<")

    def reload_config(self, new_cfg):
        self.config = new_cfg
        save_config(new_cfg)

    def _run_loop(self):
        self.controller.focus_roblox()
        time.sleep(0.3)
        self.set_state(STATE_CASTING)
        
        while self.is_running:
            try:
                if self.state == STATE_CASTING:
                    self._handle_casting()
                elif self.state == STATE_WAIT_BITE:
                    self._handle_wait_bite()
                elif self.state == STATE_FIGHT:
                    self._handle_fight()
                elif self.state == STATE_CAUGHT:
                    self._handle_caught()
                time.sleep(0.015)
            except Exception as e:
                self.log(f"Lỗi trong vòng lặp: {e}")
                time.sleep(1.0)

    def _handle_casting(self):
        if not self.is_running:
            return

        self.controller.focus_roblox()
        time.sleep(0.04)

        max_hold_time = float(self.config.get("cast_hold_time", 1.5))
        self.log("🎣 [Quăng cần]: Bắt đầu GIỮ CHUỘT TRÁI - Canh thanh Luck Boost đạt nóc xanh lá cây...")

        # Thả chuột sạch trước khi bắt đầu đè giữ
        self.controller.mouse_up()
        time.sleep(0.03)

        # BẮT ĐẦU ĐÈ GIỮ CHUỘT
        self.controller.mouse_down()
        start_cast = time.time()
        saw_luck_bar = False

        while self.is_running and (time.time() - start_cast < max_hold_time):
            # Duy trì tín hiệu giữ chuột phần cứng liên tục
            self.controller.user32.mouse_event(0x0002, 0, 0, 0, 0)

            frame, monitor = self.vision.capture_screen()
            bar_found, is_full, cap_pos = self.vision.detect_luck_boost(frame)

            if bar_found:
                saw_luck_bar = True
                if is_full:
                    elapsed = time.time() - start_cast
                    self.log(f"⚡ [Luck Boost]: Đã đạt NÓC MÀU XANH LÁ CÂY ({elapsed:.2f}s)! Thả chuột quăng cần...")
                    break
            elif saw_luck_bar and (time.time() - start_cast >= 0.8):
                # Thanh Luck Boost đã sạc đầy nóc
                self.log("⚡ [Luck Boost]: Đã sạc đầy nóc tối đa! Thả chuột phóng cần...")
                break

            time.sleep(0.012)

        # THẢ CHUỘT ĐỂ PHÓNG CẦN RA XA
        self.controller.mouse_up()
        time.sleep(0.06)

        # Chờ ngắn để dây câu & phao bay chạm mặt nước
        cooldown = min(1.0, max(0.4, float(self.config.get("cast_cooldown", 0.6))))
        self.log(f"Cần đã vung ra biển ({cooldown:.1f}s). Đang theo dõi phao & canh chuẩn mốc x10 DAMAGE...")
        time.sleep(cooldown)

        self.set_state(STATE_WAIT_BITE)

    def _handle_wait_bite(self):
        start_wait = time.time()
        max_wait_time = float(self.config.get("wait_bite_timeout", 15.0))
        self.log(f"Đang theo dõi phao & thanh sát thương x10 DAMAGE (Timeout: {max_wait_time:.0f}s)...")

        time.sleep(0.08)

        while self.is_running and self.state == STATE_WAIT_BITE:
            frame, monitor = self.vision.capture_screen()

            # 1. Kênh chính: Nhận diện thanh sát thương cắn câu xuất hiện
            bar_found, is_10x, pos = self.vision.detect_strike_10x(frame)
            if bar_found:
                self.log("🎣 [Cắn câu]: Xuất hiện thanh sát thương! Đang canh chuẩn mốc x10 DAMAGE...")
                strike_start = time.time()

                # Vòng lặp siêu tốc (< 8ms) canh đúng nhịp con cá chạm mốc x10 DAMAGE trên đỉnh đỏ
                while self.is_running and (time.time() - strike_start < 2.0):
                    if is_10x:
                        self.log("💥 [x10 DAMAGE]: Con cá đã chạm đỉnh đỏ x10! NHẤN CHUỘT TRÁI gây sát thương tối đa!")
                        self.controller.single_click(hold_time=0.06)
                        time.sleep(0.10)
                        self.active_qte_key = None
                        self.set_state(STATE_FIGHT)
                        return

                    time.sleep(0.008)
                    frame, monitor = self.vision.capture_screen()
                    bar_found, is_10x, pos = self.vision.detect_strike_10x(frame)

                # Timeout an toàn nếu sau 2.0s không bắt được 10x thì nhấn giật cần
                self.log("Nhấn chuột giật cần kết thúc lượt cắn câu...")
                self.controller.single_click(hold_time=0.06)
                time.sleep(0.10)
                self.active_qte_key = None
                self.set_state(STATE_FIGHT)
                return

            # 2. Kênh phụ: Kiểm tra thanh máu cá xuất hiện (nếu cá đã tự dính câu)
            hooked, red_px = self.vision.is_fish_hooked(frame)
            if hooked:
                self.log(f"🎣 [Giao chiến]: Phát hiện thanh máu cá ({red_px}px)! Bắt đầu chiến đấu...")
                self.active_qte_key = None
                self.set_state(STATE_FIGHT)
                return

            if time.time() - start_wait > max_wait_time:
                self.log(f"Sau {max_wait_time:.0f}s chưa cắn câu. Đang thu cần quăng lại...")
                self.controller.single_click(hold_time=0.08)
                time.sleep(0.5)
                self.set_state(STATE_CASTING)
                return

            time.sleep(0.015)

    def _handle_fight(self):
        self.log("Chiến đấu với cá: Bắt đầu theo dõi QTE [A, W, D, S] & xả Skill...")
        self.controller.focus_roblox()
        self.skill_cooldowns.clear() # Đặt lại hồi chiêu để toàn bộ skill sẵn sàng 100% ngay đầu trận chiến!

        fight_start_time = time.time()
        saw_health_bar = False
        no_hook_start = None
        skills = self.config.get("skills", [])
        skills_sorted = sorted(skills, key=lambda s: s.get("priority", 99))
        last_qte_time = 0
        last_qte_press = 0
        last_skill_time = 0
        last_click_time = 0
        skill_delay = max(0.015, float(self.config.get("skill_delay_ms", 25)) / 1000.0)
        skill_hold = max(0.02, float(self.config.get("skill_hold_ms", 30)) / 1000.0)
        click_delay = max(0.03, float(self.config.get("click_delay_ms", 40)) / 1000.0)

        while self.is_running and self.state == STATE_FIGHT:
            frame, monitor = self.vision.capture_screen()
            now = time.time()

            # Kiểm tra trạng thái thanh máu boss
            hooked, red_px = self.vision.is_fish_hooked(frame)
            if hooked:
                saw_health_bar = True
                no_hook_start = None
            elif saw_health_bar:
                if no_hook_start is None:
                    no_hook_start = now
                elif now - no_hook_start >= 0.4:
                    self.log(f"Thanh máu cá đã cạn kiệt! Kéo cá lên thành công!")
                    self.set_state(STATE_CAUGHT)
                    return

            # 1. QTE Detection: Ưu tiên số 1 (Quét liên tục siêu tốc)
            qte_active = False
            if self.config.get("qte_enabled", True):
                key, pos, score = self.vision.detect_qte(frame)
                if key:
                    qte_active = True
                    last_qte_time = now

                    # Gõ phím dứt khoát mỗi 70ms để game Roblox nhận chuẩn InputBegan/InputEnded
                    if (now - last_qte_press >= 0.07) or (self.active_qte_key != key):
                        self.controller.press_key(key, hold_duration=0.04)
                        last_qte_press = now
                        if self.active_qte_key != key:
                            self.active_qte_key = key
                            self.log(f"🎯 [QTE]: Nhận diện phím [{key}] (Độ tin cậy: {score:.2f}) -> Đã nhấn [{key}]!")

            # 2. Xả Skill & Spam click khi KHÔNG có QTE trên màn hình
            if not qte_active and (now - last_qte_time >= 0.03):
                self.active_qte_key = None

                # Xả liên hoàn tất cả skill sẵn sàng: dùng xong skill này là bấm skill khác LUÔN không ngắt quãng!
                skills_fired = 0
                for sk in skills_sorted:
                    if not sk.get("enabled", True):
                        continue
                    k = sk.get("key", "").upper()
                    cd = float(sk.get("cooldown", 1.5))
                    last_used = self.skill_cooldowns.get(k, 0)

                    # Kiểm tra chiêu đã hồi xong chưa
                    if now - last_used >= cd:
                        self.log(f"⚡ [Skill]: Xả chiêu [{k}] {sk.get('name', '')} (Ưu tiên {sk.get('priority', 1)})")
                        self.controller.press_key(k, hold_duration=skill_hold)
                        t_fired = time.time()
                        self.skill_cooldowns[k] = t_fired
                        last_skill_time = t_fired
                        skills_fired += 1
                        time.sleep(skill_delay) # Nghỉ cực ngắn (25ms) trước khi bấm skill kế tiếp

                # Khi chưa có skill nào hồi: Spam click dứt khoát liên tục đè thanh trượt cá xuống, chống trượt cá!
                if skills_fired == 0 and no_hook_start is None and self.config.get("spam_click", True):
                    if (now - last_click_time >= click_delay) and (now - last_skill_time >= 0.02):
                        self.controller.click_fast(hold_time=0.02)
                        last_click_time = time.time()

            # 3. Kiểm tra kết thúc giao chiến cho cá thường (không có thanh máu boss)
            if not saw_health_bar:
                if last_qte_time > 0 and (now - fight_start_time >= 2.5) and (now - last_qte_time >= 1.2):
                    self.log("Đã hoàn thành chuỗi QTE! Kéo cá lên thành công!")
                    self.set_state(STATE_CAUGHT)
                    return
                # Chưa thấy giao chiến sau 12s -> thu cần quăng lại
                if now - fight_start_time > 12.0 and last_qte_time == 0:
                    self.log("Không phát hiện giao chiến sau 12s giật cần. Đang thu cần quăng lại...")
                    self.controller.single_click(hold_time=0.06)
                    time.sleep(0.3)
                    self.set_state(STATE_CASTING)
                    return

            # Giới hạn an toàn chống kẹt giao chiến quá 90s
            if now - fight_start_time > 90.0:
                self.log("Kết thúc thời gian kéo cá (Quá 90s). Bắt đầu lượt câu tiếp theo...")
                self.set_state(STATE_CAUGHT)
                return

            time.sleep(0.005)

    def _handle_caught(self):
        new_count = self.fish_count + 1
        self.set_fish_count(new_count)
        self.log(f"🎉 Kéo cá lên thành công! (Tổng: {new_count} con)")

        self.controller.focus_roblox()
        self.controller.mouse_up()

        # Đứng yên tại chỗ tuyệt đối không di chuyển, quăng cần ngay lập tức
        self.log("Đứng yên tại chỗ & quăng cần ngay lập tức...")
        time.sleep(0.15)
        self.set_state(STATE_CASTING)
