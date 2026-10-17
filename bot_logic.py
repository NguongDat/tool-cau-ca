import time
import threading
import json
import os
import direct_input as di
from vision import RobloxVision


CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "auto_cast": True,
    "charge_time_seconds": 1.2,
    "recast_delay_after_catch": 0.5,
    "recast_timeout_seconds": 6.0,
    "qte_reaction_delay_ms": 80,
    "qte_press_duration_ms": 65,
    "key_mode": "hold",
    "tap_delay_ms": 30,
    "tension_min_safe": 25.0,
    "tension_max_safe": 75.0,
    "skills": {
        "Z": {"enabled": True, "cooldown": 5.0},
        "X": {"enabled": True, "cooldown": 8.0},
        "C": {"enabled": True, "cooldown": 14.0},
        "V": {"enabled": True, "cooldown": 20.0}
    },
    "skill_order": ["V", "C", "X", "Z"],
    "disable_wasd_movement": True,
    "skills_ignore_tension": True,
    "skills_burst_mode": True
}


class FishingBot:
    def __init__(self, callback_state_update=None):
        self.vision = RobloxVision()
        self.config = self.load_config()
        self.callback_state_update = callback_state_update

        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()

        # Cast lock: dung Lock.acquire(blocking=False) de tranh race condition
        self._cast_lock = threading.Lock()
        self.is_casting = False

        # Runtime state
        self.current_state = "IDLE"
        self.active_key = None
        self.held_key = None
        self.tension_pct = 0.0
        self.tension_status = "UNKNOWN"
        self.fps = 0.0
        self.fish_caught_count = 0

        self.skill_cooldowns = {k: 0.0 for k in self.config["skills"]}
        self.last_cast_time = 0.0
        self.last_minigame_seen = 0.0
        self.target_rect = None
        self.current_prompt_key = None
        self.current_prompt_pos = None
        self.current_prompt_first_seen = 0.0
        self.current_prompt_last_seen = 0.0
        self.current_prompt_pressed = False

    # ── Config ──────────────────────────────────────────────────
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    res = DEFAULT_CONFIG.copy()
                    res.update(cfg)
                    return res
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Error saving config:", e)

    # ── Start / Stop ─────────────────────────────────────────────
    def start(self, auto_cast_now=True):
        if self.is_running:
            return
        self.fish_caught_count = 0

        self.is_running = True
        self.stop_event.clear()
        # Chi reset last_cast_time neu chua co cast nao (= 0.0)
        # Neu trigger_cast da goi cast truoc do thi giu nguyen last_cast_time
        if self.last_cast_time == 0.0:
            self.last_cast_time = time.time()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

        if auto_cast_now and self.config.get("auto_cast", True):
            threading.Thread(
                target=self.trigger_auto_cast, args=(0.0,), daemon=True
            ).start()

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.stop_event.set()
        self.release_all_keys()
        self.current_state = "IDLE"
        self.active_key = None
        self.last_cast_time = 0.0  # reset de start() khoi dong lai dung

    def toggle(self):
        if self.is_running:
            self.stop()
        else:
            self.start(auto_cast_now=True)

    def release_all_keys(self):
        if self.held_key:
            di.release_key(self.held_key)
            self.held_key = None
        for k in ["w", "a", "d", "z", "x", "c", "v"]:
            di.release_key(k)

    # ── KEY & MOVEMENT CLEANUP ──────────────────────────────────
    def release_all_movement_keys(self):
        """Nhả sạch toàn bộ phím di chuyển và chuột để nhân vật đứng yên tuyệt đối."""
        for k in ['w', 'a', 's', 'd', 'space']:
            try:
                di.release_key(k)
            except Exception:
                pass
        try:
            di.mouse_up()
        except Exception:
            pass

    def release_all_keys(self):
        self.release_all_movement_keys()

    # ── CAST ─────────────────────────────────────────────────────
    def trigger_auto_cast(self, delay_before=0.0):
        # Non-blocking acquire: neu dang co cast khac thi bo qua ngay
        acquired = self._cast_lock.acquire(blocking=False)
        if not acquired:
            return

        _was_stopped_in_delay = False
        try:
            self.is_casting = True

            if delay_before > 0:
                self.current_state = "IDLE"
                self.release_all_movement_keys()
                t_end = time.time() + float(delay_before)
                while time.time() < t_end:
                    if self.stop_event.is_set() or not self.is_running:
                        _was_stopped_in_delay = True
                        return
                    time.sleep(0.04)

            # Kiem tra lai sau delay: neu bot da dung thi thoat
            if self.stop_event.is_set() or not self.is_running:
                _was_stopped_in_delay = True
                return

            self.current_state = "CASTING"
            try:
                self._do_cast()
            except Exception as e:
                print(f"[FishingBot] _do_cast error (handled): {e}")
                # Exception duoc nut tai day - finally van chay binh thuong

        finally:
            # LUON chay du co exception hay khong
            self.last_cast_time = time.time()
            # Chi set WAITING_BITE neu bot van dang chay
            if not _was_stopped_in_delay and self.is_running and not self.stop_event.is_set():
                self.current_state = "WAITING_BITE"
            elif _was_stopped_in_delay:
                self.current_state = "IDLE"
            self.is_casting = False
            self._cast_lock.release()

        # Khoi dong watchdog NGOAI lock (chi khi bot van chay va state=WAITING_BITE)
        if self.is_running and not self.stop_event.is_set() and self.current_state == "WAITING_BITE":
            self._start_watchdog_recast()

    def _do_cast(self):
        charge_sec = max(0.1, float(self.config.get("charge_time_seconds", 1.2)))
        # 1. Luôn kích hoạt Roblox lên foreground để chắc chắn nhận lệnh chuột/phím
        if not self._is_roblox_foreground():
            self.vision.activate_roblox()
            time.sleep(0.06)

        coords = self.vision.get_safe_casting_coords(self.target_rect)
        cx, cy = coords if coords else (None, None)

        # 2. Dùng di.hold_left_mouse (SendInput qua pydirectinput): Chuẩn DirectInput của Roblox
        try:
            di.hold_left_mouse(
                duration=charge_sec,
                stop_check=lambda: self.stop_event.is_set(),
                x=cx,
                y=cy
            )
        except Exception as e:
            print(f"[FishingBot] hold_left_mouse error: {e}")

    # ── WATCHDOG ─────────────────────────────────────────────────
    def _start_watchdog_recast(self):
        """
        Watchdog doc lap sau moi lan cast.
        Dung time.time()-last_cast_time thay vi kiem tra state,
        vi state co the bi false positive doi sang FISHING.
        """
        cast_time_snapshot = self.last_cast_time  # chup thoi diem cast hien tai

        def _watchdog():
            timeout = float(self.config.get("recast_timeout_seconds", 6.0))
            time.sleep(timeout)
            if (
                self.is_running
                and not self.stop_event.is_set()
                and not self.is_casting
                and self.last_cast_time == cast_time_snapshot
                and self.current_state not in ("CASTING", "FISHING")
            ):
                threading.Thread(
                    target=self.trigger_auto_cast,
                    args=(0.0,),
                    daemon=True
                ).start()
        threading.Thread(target=_watchdog, daemon=True).start()

    # ── Helpers ──────────────────────────────────────────────────
    def _is_roblox_foreground(self):
        try:
            import win32gui
            fg = win32gui.GetForegroundWindow()
            if self.vision.roblox_hwnd and fg == self.vision.roblox_hwnd:
                return True
            title = win32gui.GetWindowText(fg).lower()
            return "roblox" in title
        except Exception:
            return False


    # ── MAIN LOOP ─────────────────────────────────────────────────
    def _loop(self):
        frame_count = 0
        t_start = time.time()

        while not self.stop_event.is_set():
            t_loop_start = time.time()

            try:
                self._loop_tick()
            except Exception as e:
                print(f"[FishingBot] Loop error (non-fatal): {e}")

            frame_count += 1
            if time.time() - t_start >= 1.0:
                self.fps = frame_count / (time.time() - t_start)
                frame_count = 0
                t_start = time.time()

            elapsed = time.time() - t_loop_start
            time.sleep(max(0.005, 0.016 - elapsed))

        self.release_all_keys()

    def _loop_tick(self):
        # ── EMERGENCY RECAST GUARD ──────────────────────────────────
        # Chay TRUOC tat ca moi thu, ke ca khi khong tim thay Roblox window.
        # Neu qua recast_timeout giay tu lan cast cuoi → quang lai ngay.
        # Day la bao ve cuoi cung, hoan toan doc lap voi detection.
        recast_timeout = float(self.config.get("recast_timeout_seconds", 6.0))
        if (
            self.config.get("auto_cast", True)
            and self.is_running
            and not self.is_casting
            and time.time() - self.last_cast_time > recast_timeout
            and self.current_state not in ("CASTING", "FISHING")
        ):
            threading.Thread(
                target=self.trigger_auto_cast,
                args=(0.0,),
                daemon=True
            ).start()
            return  # Dang xu ly recast, bo qua phan con lai cua tick nay

        self.target_rect = self.vision.find_roblox_rect()
        frame = self.vision.capture_frame(self.target_rect)
        if frame is None:
            return


        tension_info = self.vision.detect_tension_bar(frame)
        key_info = self.vision.detect_key_prompt(frame)

        is_minigame = (
            tension_info["active"]
            or (key_info is not None and key_info.get("key") is not None)
        )
        self.tension_pct = tension_info["tension_pct"]
        self.tension_status = tension_info["status"]
        disable_wasd = self.config.get("disable_wasd_movement", True)

        if is_minigame:
            self._handle_minigame(frame, key_info)
        else:
            self._handle_no_minigame(frame)

        if self.callback_state_update:
            now = time.time()
            cooldowns_remaining = {}
            for k, s_cfg in self.config["skills"].items():
                cd = float(s_cfg.get("cooldown", 5.0))
                rem = max(0.0, cd - (now - self.skill_cooldowns.get(k, 0.0)))
                cooldowns_remaining[k] = round(rem, 1)
            self.callback_state_update({
                "is_running": self.is_running,
                "state": self.current_state,
                "active_key": self.active_key,
                "tension_pct": self.tension_pct,
                "tension_status": self.tension_status,
                "fps": round(self.fps, 1),
                "target_found": self.target_rect is not None,
                "cooldowns": cooldowns_remaining,
                "caught_count": self.fish_caught_count
            })

    def _handle_minigame(self, frame, key_info):
        self.current_state = "FISHING"
        self.last_minigame_seen = time.time()

        # Đảm bảo Roblox là cửa sổ active để DirectInput gửi thẳng vào game
        if not self._is_roblox_foreground():
            self.vision.activate_roblox()

        is_fg = self._is_roblox_foreground()

        # Neu chat dang mo thi bo qua skill/WASD
        if self.vision.detect_chat_open(frame):
            self.release_all_keys()
            return

        now = time.time()

        # ── 1. QUẢN LÝ PHÍM W/A/D: "NHÌN KỸ RỒI MỚI BẤM" - KHÔNG BẤM QUÁ VỘI / KHÔNG SPAM ──
        if key_info and key_info.get("key"):
            req_key = key_info["key"].lower()
            cur_pos = key_info.get("pos")
            self.active_key = req_key.upper()

            # Kiểm tra xem đây có phải là prompt đang hiển thị không (trong vòng 0.35s gần nhất)
            is_same_prompt = (
                self.current_prompt_key == req_key
                and (now - self.current_prompt_last_seen < 0.35)
            )

            if not is_same_prompt:
                # Phát hiện phím MỚI: Bắt đầu bấm giờ quan sát ("nhìn đã rồi hãy bấm")
                self.current_prompt_key = req_key
                self.current_prompt_pos = cur_pos
                self.current_prompt_first_seen = now
                self.current_prompt_last_seen = now
                self.current_prompt_pressed = False
            else:
                self.current_prompt_last_seen = now
                if cur_pos:
                    self.current_prompt_pos = cur_pos

            # Thời gian phím đã hiển thị ổn định
            visible_duration = now - self.current_prompt_first_seen
            reaction_delay = float(self.config.get("qte_reaction_delay_ms", 80)) / 1000.0

            # "Nhìn đã rồi hãy bấm": Chỉ bấm khi đã quan sát đủ thời gian và CHƯA từng bấm
            if not self.current_prompt_pressed and visible_duration >= reaction_delay:
                press_duration = float(self.config.get("qte_press_duration_ms", 65)) / 1000.0
                di.tap_key(req_key, duration=press_duration)

                # Đánh dấu ĐÃ BẤM cho phím này -> Tuyệt đối không bấm lặp lại (tránh spam gây miss)
                self.current_prompt_pressed = True
        else:
            # Nếu tạm thời không thấy key_info trên frame này:
            # CHỈ reset khi phím đã biến mất thật sự quá 0.25 giây (chống drop frame làm reset timer)!
            if now - self.current_prompt_last_seen >= 0.25:
                self.active_key = None
                self.current_prompt_key = None
                self.current_prompt_pos = None
                self.current_prompt_first_seen = 0.0
                self.current_prompt_pressed = False

        # ── 2. XẢ SKILL Z-X-C-V (CHỈ XẢ KHI KHÔNG CÓ PHÍM W/A/D ĐANG CHỜ/BẤM) ──
        # Tuyệt đối không bấm Z/X/C/V khi đang có phím W/A/D để tránh game tính là bấm sai phím
        wad_active = (self.current_prompt_key is not None and (now - self.current_prompt_last_seen < 0.25))
        if not wad_active:
            ignore_tension = self.config.get("skills_ignore_tension", True)
            tension_safe = ignore_tension or (self.tension_status != "DANGER_HIGH")
            if tension_safe:
                skill_order = self.config.get("skill_order", ["V", "C", "X", "Z"])
                burst_mode = self.config.get("skills_burst_mode", True)
                for s_key in skill_order:
                    s_cfg = self.config["skills"].get(s_key, {})
                    if not s_cfg.get("enabled", True):
                        continue
                    cd = float(s_cfg.get("cooldown", 5.0))
                    if now - self.skill_cooldowns.get(s_key, 0.0) >= cd:
                        di.tap_key(s_key.lower(), duration=0.030)
                        self.skill_cooldowns[s_key] = now
                        if not burst_mode:
                            break

    def _handle_no_minigame(self, frame):
        caught_notification = self.vision.detect_caught_notification(frame)

        if self.current_state == "FISHING":
            # Minigame vua ket thuc - debounce 200ms
            if time.time() - self.last_minigame_seen >= 0.20:
                if self.is_running and not self.is_casting:
                    self._on_fish_caught(caught_notification)

        elif caught_notification:
            # Ca bi bat khi co notification (ke ca khi state chua kip chuyen sang FISHING)
            if self.is_running and not self.is_casting:
                self._on_fish_caught(caught_notification)

        else:
            self.active_key = None

    def _on_fish_caught(self, caught_notification):
        self.current_state = "IDLE"
        self.active_key = None
        self.fish_caught_count += 1

        # 1. Nhả sạch toàn bộ phím di chuyển và chuột để nhân vật đứng yên hoàn toàn
        self.release_all_movement_keys()

        # 2. Đứng yên sau khi câu cá lên xong xuôi, sau đó mới quăng cần xuống tiếp
        if self.config.get("auto_cast", True) and not self.is_casting:
            stand_delay = float(self.config.get("recast_delay_after_catch", 0.5))
            threading.Thread(
                target=self.trigger_auto_cast,
                args=(stand_delay,),
                daemon=True
            ).start()
