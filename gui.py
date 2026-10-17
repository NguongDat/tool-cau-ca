import os
import sys
import time
import threading
import json
import customtkinter as ctk
import keyboard
import cv2

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from bot_logic import FishingBot

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FishingBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Roblox Fishing Master - Auto Pro")
        self.geometry("860x680")
        self.minsize(820, 600)

        self.bot = FishingBot(callback_state_update=self.on_bot_state_update)
        self.latest_state = None

        self.create_widgets()
        self.setup_hotkeys()
        self.update_gui_loop()

    # ─────────────────────────────────────────────────────────────
    def create_widgets(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="#181A26", corner_radius=12)
        header_frame.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            header_frame,
            text="🎣 ROBLOX FISHING MASTER AUTO PRO",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#00E5FF"
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            header_frame,
            text="Auto W/A/D | Skills Z-X-C-V | Phím tắt: F6 Bật/Tắt",
            font=ctk.CTkFont(size=12),
            text_color="#8892B0"
        ).pack(side="right", padx=16, pady=12)

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=12, fg_color="#1E2130")
        self.tabview.pack(fill="both", expand=True, padx=16, pady=6)

        self.tab_fishing = self.tabview.add("🎣 Auto Câu Cá & Skills")
        self.tab_share   = self.tabview.add("🚀 Chia Sẻ Cho Bạn Bè")

        self.build_tab_fishing()
        self.build_tab_share()

        # Footer
        bottom_bar = ctk.CTkFrame(self, fg_color="#181A26", corner_radius=10)
        bottom_bar.pack(fill="x", padx=16, pady=(4, 10))

        self.lbl_fps = ctk.CTkLabel(
            bottom_bar,
            text="FPS: 0.0 | Cửa sổ Roblox: Đang quét...",
            font=ctk.CTkFont(size=11),
            text_color="#8892B0"
        )
        self.lbl_fps.pack(side="left", padx=16, pady=6)

        self.lbl_caught_counter = ctk.CTkLabel(
            bottom_bar,
            text="Số cá đã câu: 0 con",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00E676"
        )
        self.lbl_caught_counter.pack(side="right", padx=16, pady=6)

    # ─────────────────────────────────────────────────────────────
    def build_tab_fishing(self):
        parent = self.tab_fishing

        main_content = ctk.CTkFrame(parent, fg_color="transparent")
        main_content.pack(fill="both", expand=True, padx=8, pady=4)

        left_col = ctk.CTkFrame(main_content, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right_col = ctk.CTkFrame(main_content, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ── Trạng thái & Điều khiển ──────────────────────────────
        status_box = ctk.CTkFrame(left_col, fg_color="#141724", corner_radius=10)
        status_box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            status_box,
            text="ĐIỀU KHIỂN & TRẠNG THÁI HUD",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#E6F1FF"
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.btn_toggle = ctk.CTkButton(
            status_box,
            text="▶ BẬT AUTO CÂU CÁ (F6)",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#00C853", hover_color="#009624",
            height=44,
            command=self.toggle_bot
        )
        self.btn_toggle.pack(fill="x", padx=12, pady=6)

        state_row = ctk.CTkFrame(status_box, fg_color="transparent")
        state_row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(state_row, text="Trạng thái:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.lbl_bot_state = ctk.CTkLabel(
            state_row, text="ĐANG CHỜ (IDLE)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#8892B0"
        )
        self.lbl_bot_state.pack(side="right")

        # Phím đang bấm
        key_frame = ctk.CTkFrame(status_box, fg_color="#0D0F18", corner_radius=8)
        key_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(key_frame, text="Phím W/A/D Đang Bấm:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(4, 0))
        self.lbl_active_key = ctk.CTkLabel(key_frame, text="[ - ]", font=ctk.CTkFont(size=30, weight="bold"), text_color="#00E5FF")
        self.lbl_active_key.pack(pady=(0, 2))

        # Cài đặt độ trễ quan sát phím W/A/D: Nhìn kỹ rồi mới bấm
        wad_delay_row = ctk.CTkFrame(key_frame, fg_color="transparent")
        wad_delay_row.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkLabel(wad_delay_row, text="⏱ Độ trễ nhìn W/A/D:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.entry_qte_delay = ctk.CTkEntry(wad_delay_row, width=44, height=24, font=ctk.CTkFont(size=11, weight="bold"))
        self.entry_qte_delay.insert(0, str(self.bot.config.get("qte_reaction_delay_ms", 120)))
        self.entry_qte_delay.pack(side="left", padx=4)
        ctk.CTkLabel(wad_delay_row, text="ms (Nhìn kỹ rồi hãy bấm)", font=ctk.CTkFont(size=10), text_color="#8892B0").pack(side="left")

        # Thanh tension
        tension_frame = ctk.CTkFrame(status_box, fg_color="#0D0F18", corner_radius=8)
        tension_frame.pack(fill="x", padx=12, pady=(0, 10))

        t_row = ctk.CTkFrame(tension_frame, fg_color="transparent")
        t_row.pack(fill="x", padx=10, pady=(4, 2))
        ctk.CTkLabel(t_row, text="Thanh Giữ Cá (Tension):", font=ctk.CTkFont(size=11)).pack(side="left")
        self.lbl_tension_val = ctk.CTkLabel(t_row, text="0.0%", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8892B0")
        self.lbl_tension_val.pack(side="right")

        self.tension_bar = ctk.CTkProgressBar(tension_frame, height=12, corner_radius=6)
        self.tension_bar.set(0.0)
        self.tension_bar.pack(fill="x", padx=10, pady=(2, 4))

        self.lbl_tension_alert = ctk.CTkLabel(
            tension_frame, text="✔ An toàn",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#00C853"
        )
        self.lbl_tension_alert.pack(pady=(0, 4))

        # ── Quăng cần ──────────────────────────────────────────
        cast_box = ctk.CTkFrame(left_col, fg_color="#141724", corner_radius=10)
        cast_box.pack(fill="x")

        ctk.CTkLabel(
            cast_box,
            text="🎣 QUĂNG CẦN: GIỮ CHUỘT TRÁI SẠC LỰC (x5 DAMAGE)",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#E6F1FF"
        ).pack(anchor="w", padx=12, pady=(6, 2))
        ctk.CTkLabel(
            cast_box,
            text="* Tự động GIỮ chặt chuột trái để tích lực rồi thả cần",
            font=ctk.CTkFont(size=10), text_color="#8892B0"
        ).pack(anchor="w", padx=12, pady=(0, 4))

        self.btn_cast_once = ctk.CTkButton(
            cast_box,
            text="⚡ Giữ Chuột Quăng Cần (Thủ Công)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0288D1", hover_color="#01579B",
            height=32,
            command=self.trigger_cast
        )
        self.btn_cast_once.pack(fill="x", padx=12, pady=4)

        self.chk_auto_recast = ctk.CTkCheckBox(
            cast_box,
            text="Tự động quăng lại sau khi bắt cá xong (Auto Loop)",
            font=ctk.CTkFont(size=11),
            command=self.on_settings_change
        )
        self.chk_auto_recast.pack(anchor="w", padx=12, pady=(4, 2))
        if self.bot.config.get("auto_cast", True):
            self.chk_auto_recast.select()

        # Cài đặt thời gian
        cast_cfg_row = ctk.CTkFrame(cast_box, fg_color="transparent")
        cast_cfg_row.pack(fill="x", padx=12, pady=(2, 4))

        ctk.CTkLabel(cast_cfg_row, text="⏱ Giữ sạc lực:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.entry_charge_time = ctk.CTkEntry(cast_cfg_row, width=42, height=24, font=ctk.CTkFont(size=11, weight="bold"))
        self.entry_charge_time.insert(0, str(self.bot.config.get("charge_time_seconds", 1.2)))
        self.entry_charge_time.pack(side="left", padx=3)
        ctk.CTkLabel(cast_cfg_row, text="s", font=ctk.CTkFont(size=10), text_color="#8892B0").pack(side="left", padx=(0, 6))

        ctk.CTkLabel(cast_cfg_row, text="Ném lại sau câu:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.entry_recast_delay = ctk.CTkEntry(cast_cfg_row, width=42, height=24, font=ctk.CTkFont(size=11, weight="bold"))
        self.entry_recast_delay.insert(0, str(self.bot.config.get("recast_delay_after_catch", 0.1)))
        self.entry_recast_delay.pack(side="left", padx=3)
        ctk.CTkLabel(cast_cfg_row, text="s", font=ctk.CTkFont(size=10), text_color="#8892B0").pack(side="left", padx=(0, 6))

        ctk.CTkLabel(cast_cfg_row, text="Chờ cắn:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.entry_recast_timeout = ctk.CTkEntry(cast_cfg_row, width=42, height=24, font=ctk.CTkFont(size=11, weight="bold"))
        self.entry_recast_timeout.insert(0, str(self.bot.config.get("recast_timeout_seconds", 3.0)))
        self.entry_recast_timeout.pack(side="left", padx=3)
        ctk.CTkLabel(cast_cfg_row, text="s", font=ctk.CTkFont(size=10), text_color="#8892B0").pack(side="left")

        # Đứng yên
        self.chk_disable_wasd = ctk.CTkCheckBox(
            cast_box,
            text="🛑 KHÓA VỊ TRÍ ĐỨNG YÊN (Triệt tiêu quán tính, không trôi khi bấm W/A/D)",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#00E5FF",
            command=self.on_settings_change
        )
        self.chk_disable_wasd.pack(anchor="w", padx=12, pady=2)
        if self.bot.config.get("disable_wasd_movement", True):
            self.chk_disable_wasd.select()


        # ── Skills Z-X-C-V ──────────────────────────────────────
        skills_box = ctk.CTkFrame(right_col, fg_color="#141724", corner_radius=10)
        skills_box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            skills_box, text="QUẢN LÝ TUYỆT CHIÊU (Z - X - C - V)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#E6F1FF"
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.chk_skills_burst = ctk.CTkCheckBox(
            skills_box,
            text="🔥 Xả combo tuyệt chiêu tức thì (Burst Tất Cả Skill)",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#00E5FF",
            command=self.on_settings_change
        )
        self.chk_skills_burst.pack(anchor="w", padx=12, pady=(4, 2))
        if self.bot.config.get("skills_burst_mode", True):
            self.chk_skills_burst.select()

        self.chk_skills_ignore_tension = ctk.CTkCheckBox(
            skills_box,
            text="⚡ Xả chiêu liên tục (Không bị hoãn bởi thanh cá)",
            font=ctk.CTkFont(size=11),
            command=self.on_settings_change
        )
        self.chk_skills_ignore_tension.pack(anchor="w", padx=12, pady=(2, 4))
        if self.bot.config.get("skills_ignore_tension", True):
            self.chk_skills_ignore_tension.select()

        self.skill_widgets = {}
        skill_names = {
            "Z": "Taiji Hooking Art V2",
            "X": "One Hook Supreme",
            "C": "Unity of Heaven and Man",
            "V": "Shatter The Azure Heavens"
        }

        for s_key in ["Z", "X", "C", "V"]:
            s_frame = ctk.CTkFrame(skills_box, fg_color="#0D0F18", corner_radius=6)
            s_frame.pack(fill="x", padx=12, pady=2)

            s_cfg = self.bot.config["skills"].get(s_key, {"enabled": True, "cooldown": 5.0})
            chk_var = ctk.BooleanVar(value=s_cfg.get("enabled", True))
            chk = ctk.CTkCheckBox(
                s_frame,
                text=f"[{s_key}] {skill_names.get(s_key, '')}",
                variable=chk_var,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=self.on_settings_change
            )
            chk.pack(side="left", padx=8, pady=5)

            ctk.CTkLabel(s_frame, text="Hồi:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 2))
            cd_entry = ctk.CTkEntry(s_frame, width=40, height=24, font=ctk.CTkFont(size=11))
            cd_entry.insert(0, str(s_cfg.get("cooldown", 5.0)))
            cd_entry.pack(side="left", padx=(0, 2))
            ctk.CTkLabel(s_frame, text="s", font=ctk.CTkFont(size=11)).pack(side="left")

            lbl_cd = ctk.CTkLabel(s_frame, text="READY", font=ctk.CTkFont(size=10, weight="bold"), text_color="#00E676")
            lbl_cd.pack(side="right", padx=8)

            self.skill_widgets[s_key] = {"chk_var": chk_var, "cd_entry": cd_entry, "lbl_cd": lbl_cd}

        # ── Ngưỡng an toàn tension ─────────────────────────────
        safety_box = ctk.CTkFrame(right_col, fg_color="#141724", corner_radius=10)
        safety_box.pack(fill="x")
        ctk.CTkLabel(
            safety_box, text="NGƯỠNG AN TOÀN THANH GIỮ CÁ",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#E6F1FF"
        ).pack(anchor="w", padx=12, pady=(6, 2))

        slider_row = ctk.CTkFrame(safety_box, fg_color="transparent")
        slider_row.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(slider_row, text="Min:", font=ctk.CTkFont(size=11)).pack(side="left")
        self.slider_min = ctk.CTkSlider(slider_row, from_=10, to=40, number_of_steps=30, width=90, command=self.on_settings_change)
        self.slider_min.set(self.bot.config.get("tension_min_safe", 25.0))
        self.slider_min.pack(side="left", padx=2)

        ctk.CTkLabel(slider_row, text="Max:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 0))
        self.slider_max = ctk.CTkSlider(slider_row, from_=60, to=90, number_of_steps=30, width=90, command=self.on_settings_change)
        self.slider_max.set(self.bot.config.get("tension_max_safe", 75.0))
        self.slider_max.pack(side="left", padx=2)

        ctk.CTkButton(
            safety_box,
            text="🧪 Thử Nghiệm Trên Ảnh Mẫu",
            font=ctk.CTkFont(size=11), fg_color="#37474F",
            height=26, command=self.run_test_sample
        ).pack(fill="x", padx=12, pady=(6, 8))

    # ─────────────────────────────────────────────────────────────
    def build_tab_share(self):
        parent = self.tab_share

        box = ctk.CTkFrame(parent, fg_color="#141724", corner_radius=10)
        box.pack(fill="both", expand=True, padx=12, pady=8)

        ctk.CTkLabel(
            box, text="🚀 ĐÓNG GÓI & CHIA SẺ ỨNG DỤNG CHO BẠN BÈ",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#00E5FF"
        ).pack(anchor="w", padx=16, pady=(12, 4))

        info_text = (
            "Bạn có thể chia sẻ công cụ này cho bạn bè cực kỳ dễ dàng theo 2 cách:\n\n"
            "1. CÁCH 1 (Tiện nhất - Đã đóng gói thành App .exe):\n"
            "   - Chỉ cần gửi thư mục 'dist/FishingMaster_Auto_Pro' hoặc file nén .zip cho bạn bè.\n"
            "   - Bạn bè KHÔNG CẦN cài Python hay bất kỳ phần mềm nào khác!\n\n"
            "2. CÁCH 2 (Chạy nhanh qua file Run Tool):\n"
            "   - Gửi toàn bộ thư mục 'tool cau ca', bạn bè chỉ cần bấm đúp file 'run_tool.bat'.\n\n"
            "TỔNG HỢP PHÍM TẮT ĐIỀU KHIỂN:\n"
            "   • [ F6 ] : Bật / Tắt Tự Động Câu Cá (Tự giữ cần, xả chiêu Z-X-C-V & tự quăng cần)\n"
        )
        ctk.CTkLabel(
            box, text=info_text,
            font=ctk.CTkFont(size=12), text_color="#CBD5E1", justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkButton(
            box,
            text="📂 Mở Thư Mục Chứa Tool Để Gửi Cho Bạn Bè",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00C853", hover_color="#009624",
            height=38, command=self.open_tool_folder
        ).pack(anchor="w", padx=16, pady=8)

    # ─────────────────────────────────────────────────────────────
    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('F6', lambda: threading.Thread(target=self.toggle_bot, daemon=True).start(), suppress=True)
        except Exception as e:
            print("Hotkey setup warning:", e)

    def toggle_bot(self):
        try:
            self.save_current_settings()
        except Exception:
            pass
        self.bot.toggle()
        if self.bot.is_running:
            self.after(0, lambda: self.btn_toggle.configure(text="■ DỪNG AUTO (F6)", fg_color="#E53935", hover_color="#C62828"))
            try:
                import winsound
                threading.Thread(target=winsound.Beep, args=(1200, 150), daemon=True).start()
            except Exception:
                pass
        else:
            self.after(0, lambda: self.btn_toggle.configure(text="▶ BẬT AUTO CÂU CÁ (F6)", fg_color="#00C853", hover_color="#009624"))
            try:
                import winsound
                threading.Thread(target=winsound.Beep, args=(600, 150), daemon=True).start()
            except Exception:
                pass

    def trigger_cast(self):
        try:
            self.save_current_settings()
        except Exception:
            pass
        threading.Thread(target=self.bot.trigger_auto_cast, daemon=True).start()
        if not self.bot.is_running:
            self.bot.start(auto_cast_now=False)
            self.after(0, lambda: self.btn_toggle.configure(text="■ DỪNG AUTO (F6)", fg_color="#E53935", hover_color="#C62828"))

    def open_tool_folder(self):
        os.system(f'explorer "{os.path.dirname(os.path.abspath(__file__))}"')

    def on_settings_change(self, *args):
        self.save_current_settings()

    def save_current_settings(self):
        self.bot.config["auto_cast"] = bool(self.chk_auto_recast.get())
        self.bot.config["disable_wasd_movement"] = bool(self.chk_disable_wasd.get())
        self.bot.config["skills_ignore_tension"] = bool(self.chk_skills_ignore_tension.get())
        if hasattr(self, "chk_skills_burst"):
            self.bot.config["skills_burst_mode"] = bool(self.chk_skills_burst.get())
        self.bot.config["tension_min_safe"] = round(self.slider_min.get(), 1)
        self.bot.config["tension_max_safe"] = round(self.slider_max.get(), 1)

        try:
            self.bot.config["charge_time_seconds"] = float(self.entry_charge_time.get())
        except Exception:
            pass
        try:
            if hasattr(self, "entry_recast_delay"):
                self.bot.config["recast_delay_after_catch"] = float(self.entry_recast_delay.get())
        except Exception:
            pass
        try:
            if hasattr(self, "entry_qte_delay"):
                self.bot.config["qte_reaction_delay_ms"] = int(self.entry_qte_delay.get())
        except Exception:
            pass
        try:
            self.bot.config["recast_timeout_seconds"] = float(self.entry_recast_timeout.get())
        except Exception:
            pass

        for s_key, w in self.skill_widgets.items():
            en = bool(w["chk_var"].get())
            try:
                cd = float(w["cd_entry"].get())
            except ValueError:
                cd = 5.0
            self.bot.config["skills"][s_key] = {"enabled": en, "cooldown": cd}

        self.bot.save_config()

    def on_bot_state_update(self, state):
        self.latest_state = state

    # ─────────────────────────────────────────────────────────────
    def update_gui_loop(self):
        if self.latest_state:
            st = self.latest_state
            game_state = st.get("state", "IDLE")

            if not st.get("is_running", False):
                self.lbl_bot_state.configure(text="ĐÃ DỪNG (STOPPED)", text_color="#8892B0")
            elif game_state == "FISHING":
                self.lbl_bot_state.configure(text="⚡ ĐANG CÂU CÁ & XẢ SKILL...", text_color="#00E5FF")
            elif game_state == "CASTING":
                self.lbl_bot_state.configure(text="🎣 ĐANG GIỮ CHUỘT SẠC LỰC (x5)...", text_color="#FFB300")
            elif game_state == "WAITING_BITE":
                self.lbl_bot_state.configure(text="🌊 ĐÃ THẢ CẦN - ĐANG ĐỢI CÁ CẮN...", text_color="#00E676")
            else:
                self.lbl_bot_state.configure(text="ĐANG CHỜ BẮT ĐẦU CÂU...", text_color="#8892B0")

            ak = st.get("active_key")
            if ak:
                self.lbl_active_key.configure(text=f"[ {ak} ]", text_color="#00E5FF")
            else:
                self.lbl_active_key.configure(text="[ - ]", text_color="#546E7A")

            t_pct = st.get("tension_pct", 0.0)
            self.tension_bar.set(t_pct / 100.0)
            t_status = st.get("tension_status", "UNKNOWN")

            if game_state == "FISHING":
                self.lbl_tension_val.configure(text=f"{t_pct:.1f}%")
                if t_status == "DANGER_HIGH":
                    self.tension_bar.configure(progress_color="#FF1744")
                    self.lbl_tension_alert.configure(text="⚠ NGUY HIỂM: Gần đứt dây cá!", text_color="#FF1744")
                elif t_status == "DANGER_LOW":
                    self.tension_bar.configure(progress_color="#FF9100")
                    self.lbl_tension_alert.configure(text="⚠ CẢNH BÁO: Lực quá yếu!", text_color="#FF9100")
                else:
                    self.tension_bar.configure(progress_color="#00E676")
                    self.lbl_tension_alert.configure(text="✔ An toàn: Có thể xả skill!", text_color="#00E676")
            else:
                self.lbl_tension_val.configure(text="0.0% (Chờ minigame)")
                self.tension_bar.configure(progress_color="#00E5FF")
                self.lbl_tension_alert.configure(text="✔ Đang quan sát màn hình", text_color="#8892B0")

            cds = st.get("cooldowns", {})
            for s_key, w in self.skill_widgets.items():
                rem = cds.get(s_key, 0.0)
                if rem <= 0.0:
                    w["lbl_cd"].configure(text="READY", text_color="#00E676")
                else:
                    w["lbl_cd"].configure(text=f"{rem:.1f}s", text_color="#FF9100")

            found_str = "Đã tìm thấy (Windowed)" if st.get("target_found") else "Toàn màn hình (Desktop)"
            self.lbl_fps.configure(text=f"FPS: {st.get('fps', 0.0)} | Cửa sổ Roblox: {found_str}")
            self.lbl_caught_counter.configure(text=f"Số cá đã câu: {st.get('caught_count', 0)} con")

        self.after(50, self.update_gui_loop)

    def run_test_sample(self):
        sample_path = os.path.join(os.path.dirname(__file__), "templates", "sample_minigame.png")
        if os.path.exists(sample_path):
            img = cv2.imread(sample_path)
            k_res = self.bot.vision.detect_key_prompt(img)
            t_res = self.bot.vision.detect_tension_bar(img)
            k_str = k_res['key'] if k_res else 'None'
            t_pct = t_res['tension_pct'] if t_res else 0.0
            self.lbl_active_key.configure(text=f"[ {k_str} ]", text_color="#00E5FF")
            self.tension_bar.set(t_pct / 100.0)
            self.lbl_tension_val.configure(text=f"{t_pct:.1f}% (TEST)")
            self.lbl_tension_alert.configure(text="✔ Test OK!", text_color="#00E676")


if __name__ == '__main__':
    app = FishingBotGUI()
    app.mainloop()
