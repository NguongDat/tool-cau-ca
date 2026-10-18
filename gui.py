import os
import sys
import threading
import datetime
from collections import deque
import customtkinter as ctk
import keyboard
from bot_core import FishingBot, STATE_IDLE, STATE_CASTING, STATE_WAIT_BITE, STATE_FIGHT, STATE_CAUGHT
from config_manager import load_config, save_config

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FishingBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Bậc Thầy Câu Cá - Auto Tool Roblox (Pro Edition)")
        self.geometry("780x750")
        self.minsize(700, 650)

        self.config = load_config()
        self.log_lines = deque(maxlen=10)
        self.bot = FishingBot(
            log_callback=self.on_log,
            status_callback=self.on_status_change,
            count_callback=self.on_count_change
        )

        self.setup_ui()
        self.setup_hotkeys()

        # Update initial fish count
        self.fish_count_var.set(f"{self.bot.fish_count} con")

    def setup_ui(self):
        # 1. Header Frame
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1e29")
        header.pack(fill="x", padx=15, pady=(12, 6))

        title_lbl = ctk.CTkLabel(
            header,
            text="🎣 BẬC THẦY CÂU CÁ - AUTO BOT",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title_lbl.pack(side="left", padx=15, pady=10)

        self.status_badge = ctk.CTkLabel(
            header,
            text="● ĐÃ DỪNG (F6)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ef4444",
            fg_color="#371e24",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right", padx=15, pady=10)

        # 2. Controls Frame (Bật / Tắt Auto bằng F6)
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=15, pady=6)

        self.btn_toggle = ctk.CTkButton(
            ctrl_frame,
            text="▶ BẮT ĐẦU AUTO (F6)",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=46,
            command=self.toggle_bot
        )
        self.btn_toggle.pack(fill="x", expand=True)

        # 3. Tabview for Settings
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=6)

        self.tab_skills = self.tabview.add("⚡ Ưu Tiên Kỹ Năng (DPS)")
        self.tab_fishing = self.tabview.add("🎣 Cài Đặt Câu & QTE")
        self.tab_stats = self.tabview.add("📊 Thống Kê & Số Cá")

        self.build_skills_tab()
        self.build_fishing_tab()
        self.build_stats_tab()

        # 4. Live Log Console
        log_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#111827")
        log_frame.pack(fill="both", expand=True, padx=15, pady=(6, 12))

        log_hdr = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_hdr.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(log_hdr, text="📋 NHẬT KÝ THỜI GIAN THỰC (10 DÒNG GẦN NHẤT)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#9ca3af").pack(side="left")
        ctk.CTkButton(log_hdr, text="Xóa Log", width=70, height=22, fg_color="#374151", hover_color="#4b5563", command=self.clear_log).pack(side="right")

        self.log_box = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#0f172a", text_color="#e2e8f0")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(2, 8))

    def build_skills_tab(self):
        desc = ctk.CTkLabel(
            self.tab_skills,
            text="Sắp xếp thứ tự ưu tiên xả chiêu (Ưu tiên 1 sẽ được xả trước ngay khi hồi chiêu):",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8"
        )
        desc.pack(anchor="w", padx=10, pady=(5, 10))

        # Skill rows container
        self.skill_rows_frame = ctk.CTkFrame(self.tab_skills, fg_color="transparent")
        self.skill_rows_frame.pack(fill="x", padx=10, pady=5)

        self.skill_widgets = []
        self.render_skill_rows()

        # Extra attack options
        extra_frame = ctk.CTkFrame(self.tab_skills, fg_color="#1e293b", corner_radius=8)
        extra_frame.pack(fill="x", padx=10, pady=(15, 5))

        self.spam_click_var = ctk.BooleanVar(value=self.config.get("spam_click", True))
        chk_spam = ctk.CTkCheckBox(
            extra_frame,
            text="Spam Click chuột trái xen kẽ giữa các skill (Gây thêm sát thương phụ)",
            variable=self.spam_click_var,
            command=self.save_all_settings
        )
        chk_spam.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 6))

        ctk.CTkLabel(
            extra_frame,
            text="Tốc độ xả chiêu (Độ trễ giữa 2 skill liên tiếp - ms):",
            font=ctk.CTkFont(size=13)
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(4, 10))

        self.skill_delay_var = ctk.StringVar(value=str(self.config.get("skill_delay_ms", 25)))
        ent_skill_delay = ctk.CTkEntry(extra_frame, width=80, textvariable=self.skill_delay_var)
        ent_skill_delay.grid(row=1, column=1, sticky="w", padx=10, pady=(4, 10))
        ent_skill_delay.bind("<FocusOut>", lambda e: self.save_all_settings())
        ent_skill_delay.bind("<Return>", lambda e: self.save_all_settings())

    def render_skill_rows(self):
        for widget in self.skill_rows_frame.winfo_children():
            widget.destroy()
        self.skill_widgets.clear()

        skills = self.config.get("skills", [])
        skills.sort(key=lambda x: x.get("priority", 99))

        for idx, sk in enumerate(skills):
            row = ctk.CTkFrame(self.skill_rows_frame, fg_color="#1e293b", corner_radius=8, height=45)
            row.pack(fill="x", pady=4)

            # Priority Label
            p_lbl = ctk.CTkLabel(
                row,
                text=f"Top {idx + 1}",
                width=50,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#38bdf8"
            )
            p_lbl.pack(side="left", padx=10)

            # Key Badge
            k_badge = ctk.CTkLabel(
                row,
                text=f"[{sk['key']}]",
                width=45,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="#0f172a",
                corner_radius=6,
                text_color="#f59e0b"
            )
            k_badge.pack(side="left", padx=5)

            # Skill Name
            n_lbl = ctk.CTkLabel(
                row,
                text=sk.get("name", ""),
                font=ctk.CTkFont(size=13),
                anchor="w",
                width=180
            )
            n_lbl.pack(side="left", padx=10)

            # Cooldown Entry
            ctk.CTkLabel(row, text="Hồi chiêu:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(side="left", padx=(10, 2))
            cd_var = ctk.StringVar(value=str(sk.get("cooldown", 5.0)))
            cd_ent = ctk.CTkEntry(row, width=50, height=28, textvariable=cd_var)
            cd_ent.pack(side="left", padx=(0, 2))
            ctk.CTkLabel(row, text="s", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(side="left", padx=(0, 10))

            # Enable Toggle
            en_var = ctk.BooleanVar(value=sk.get("enabled", True))
            en_chk = ctk.CTkCheckBox(row, text="Bật", width=55, variable=en_var, command=self.save_all_settings)
            en_chk.pack(side="left", padx=5)

            # Move Up / Down buttons
            btn_up = ctk.CTkButton(
                row,
                text="▲",
                width=30,
                height=26,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda i=idx: self.move_skill(i, -1)
            )
            btn_up.pack(side="right", padx=(2, 10))

            btn_down = ctk.CTkButton(
                row,
                text="▼",
                width=30,
                height=26,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda i=idx: self.move_skill(i, 1)
            )
            btn_down.pack(side="right", padx=(2, 2))

            self.skill_widgets.append({
                "key": sk['key'],
                "cd_var": cd_var,
                "en_var": en_var
            })

    def move_skill(self, index, direction):
        skills = self.config.get("skills", [])
        new_index = index + direction
        if 0 <= new_index < len(skills):
            skills[index], skills[new_index] = skills[new_index], skills[index]
            for i, s in enumerate(skills):
                s["priority"] = i + 1
            self.config["skills"] = skills
            save_config(self.config)
            self.bot.reload_config(self.config)
            self.render_skill_rows()

    def build_fishing_tab(self):
        f = ctk.CTkFrame(self.tab_fishing, fg_color="#1e293b", corner_radius=8)
        f.pack(fill="x", padx=10, pady=10)

        # Cast hold time
        ctk.CTkLabel(f, text="Thời gian giữ chuột quăng cần (giây):", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=15, pady=8)
        self.cast_time_var = ctk.StringVar(value=str(self.config.get("cast_hold_time", 1.0)))
        ent_cast = ctk.CTkEntry(f, width=80, textvariable=self.cast_time_var)
        ent_cast.grid(row=0, column=1, sticky="w", padx=10, pady=8)

        # Wait bite timeout
        ctk.CTkLabel(f, text="Thời gian chờ cá cắn tối đa (giây):", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", padx=15, pady=8)
        self.wait_bite_var = ctk.StringVar(value=str(self.config.get("wait_bite_timeout", 15.0)))
        ent_wait_bite = ctk.CTkEntry(f, width=80, textvariable=self.wait_bite_var)
        ent_wait_bite.grid(row=1, column=1, sticky="w", padx=10, pady=8)

        # QTE enabled
        self.qte_var = ctk.BooleanVar(value=self.config.get("qte_enabled", True))
        chk_qte = ctk.CTkCheckBox(f, text="Tự động nhận diện và phản xạ bấm phím QTE [A], [W], [D], [S]", variable=self.qte_var, command=self.save_all_settings)
        chk_qte.grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=8)

        # QTE hold duration
        ctk.CTkLabel(f, text="Thời gian giữ phím QTE tối thiểu (ms):", font=ctk.CTkFont(size=13)).grid(row=3, column=0, sticky="w", padx=15, pady=8)
        self.qte_delay_var = ctk.StringVar(value=str(self.config.get("qte_press_delay_ms", 80)))
        ent_qte_delay = ctk.CTkEntry(f, width=80, textvariable=self.qte_delay_var)
        ent_qte_delay.grid(row=3, column=1, sticky="w", padx=10, pady=8)

        # Tip
        tip = ctk.CTkLabel(
            self.tab_fishing,
            text="💡 Mẹo: Tool nhận diện chính xác 100% phím QTE [A, W, D, S] & mũi tên PULL, tự động ĐÈ GIỮ phím theo nhịp minigame.\nChỉ cần cầm sẵn cần câu và bấm F6 để bắt đầu.",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            justify="left"
        )
        tip.pack(anchor="w", padx=15, pady=10)

        btn_save = ctk.CTkButton(self.tab_fishing, text="Lưu Cấu Hình", fg_color="#2563eb", hover_color="#1d4ed8", command=self.save_all_settings)
        btn_save.pack(anchor="e", padx=15, pady=10)

    def build_stats_tab(self):
        f = ctk.CTkFrame(self.tab_stats, fg_color="#1e293b", corner_radius=8)
        f.pack(fill="x", padx=10, pady=10)

        # Fish count
        ctk.CTkLabel(f, text="Số lượng cá đã câu được:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=15, pady=12)
        self.fish_count_var = ctk.StringVar(value="0 con")
        lbl_count = ctk.CTkLabel(f, textvariable=self.fish_count_var, font=ctk.CTkFont(size=15, weight="bold"), text_color="#10b981")
        lbl_count.grid(row=0, column=1, sticky="w", padx=10, pady=12)

        btn_reset = ctk.CTkButton(f, text="Reset Về 0", width=90, height=28, fg_color="#475569", hover_color="#64748b", command=self.reset_count)
        btn_reset.grid(row=0, column=2, padx=15, pady=12)

        # Mẹo sử dụng
        info = ctk.CTkFrame(self.tab_stats, fg_color="#0f172a", corner_radius=8)
        info.pack(fill="x", padx=10, pady=12)

        ctk.CTkLabel(
            info,
            text="💡 HƯỚNG DẪN CÂU CÁ TỰ ĐỘNG:\n\n"
                 "• Bấm F6 để BẮT ĐẦU tự động câu. Bấm F6 một lần nữa để DỪNG LẠI.\n"
                 "• Bot tự động đè giữ chuột quăng cần, đứng yên tại chỗ 100% không di chuyển.\n"
                 "• Kéo cá lên thành công sẽ lập tức quăng lượt cần mới ngay tức thì.",
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8",
            justify="left"
        ).pack(padx=15, pady=12, anchor="w")

    def save_all_settings(self):
        try:
            self.config["cast_hold_time"] = float(self.cast_time_var.get())
        except ValueError:
            self.config["cast_hold_time"] = 1.2

        try:
            self.config["wait_bite_timeout"] = float(self.wait_bite_var.get())
        except ValueError:
            self.config["wait_bite_timeout"] = 15.0

        self.config["spam_click"] = self.spam_click_var.get()
        try:
            self.config["skill_delay_ms"] = int(self.skill_delay_var.get())
        except (ValueError, TypeError):
            self.config["skill_delay_ms"] = 40

        self.config["qte_enabled"] = self.qte_var.get()
        try:
            self.config["qte_press_delay_ms"] = int(self.qte_delay_var.get())
        except (ValueError, TypeError):
            self.config["qte_press_delay_ms"] = 80

        # Update skills cooldown and enabled
        skills = self.config.get("skills", [])
        for w in self.skill_widgets:
            k = w["key"]
            for s in skills:
                if s["key"] == k:
                    try:
                        s["cooldown"] = float(w["cd_var"].get())
                    except ValueError:
                        pass
                    s["enabled"] = w["en_var"].get()

        save_config(self.config)
        self.bot.reload_config(self.config)
        self.on_log("Đã lưu và cập nhật cấu hình mới thành công!")

    def reset_count(self):
        self.bot.set_fish_count(0)
        self.fish_count_var.set(f"0 / {self.config.get('max_fish', 50)}")
        self.on_log("Đã đặt lại số đếm cá trong túi về 0.")

    def toggle_bot(self):
        if self.bot.is_running:
            self.stop_bot()
        else:
            self.start_bot()

    def start_bot(self):
        self.save_all_settings()
        self.bot.start()
        self.btn_toggle.configure(text="⏹ DỪNG TOOL (F6)", fg_color="#ef4444", hover_color="#dc2626")

    def stop_bot(self):
        self.bot.stop()
        self.btn_toggle.configure(text="▶ BẮT ĐẦU AUTO (F6)", fg_color="#10b981", hover_color="#059669")

    def setup_hotkeys(self):
        def _on_f6():
            self.after(0, self.toggle_bot)

        try:
            keyboard.add_hotkey("f6", _on_f6)
        except Exception as e:
            self.on_log(f"Cảnh báo: Không thể đăng ký phím tắt toàn cục: {e}")

    def on_status_change(self, state):
        def _update():
            if state == STATE_IDLE:
                self.status_badge.configure(text="● ĐÃ DỪNG (F6)", text_color="#ef4444", fg_color="#371e24")
                self.btn_toggle.configure(text="▶ BẮT ĐẦU AUTO (F6)", fg_color="#10b981", hover_color="#059669")
            else:
                names = {
                    STATE_CASTING: "🎣 ĐANG QUĂNG CẦN",
                    STATE_WAIT_BITE: "⏳ ĐANG CHỜ CÁ CẮN",
                    STATE_FIGHT: "⚔️ ĐANG KÉO CÁ & QTE",
                    STATE_CAUGHT: "🎉 ĐÃ BẮT CÁ!"
                }
                text = names.get(state, state)
                self.status_badge.configure(text=f"● {text}", text_color="#10b981", fg_color="#133e2b")
                self.btn_toggle.configure(text="⏹ DỪNG TOOL (F6)", fg_color="#ef4444", hover_color="#dc2626")
        self.after(0, _update)

    def on_count_change(self, count):
        def _update():
            self.fish_count_var.set(f"{count} con")
        self.after(0, _update)

    def on_log(self, msg):
        def _update():
            t = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_lines.append(f"[{t}] {msg}")
            self.log_box.delete("1.0", "end")
            self.log_box.insert("end", "\n".join(self.log_lines) + "\n")
            self.log_box.see("end")
        self.after(0, _update)

    def clear_log(self):
        self.log_lines.clear()
        self.log_box.delete("1.0", "end")

if __name__ == "__main__":
    app = FishingBotGUI()
    app.mainloop()
