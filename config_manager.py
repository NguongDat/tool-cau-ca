import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "cast_hold_time": 1.2,
    "cast_cooldown": 0.6,
    "wait_bite_timeout": 15.0,
    "skills": [
        {"key": "Z", "name": "Heaven-Lifting Hook", "enabled": True, "cooldown": 1.5, "priority": 1},
        {"key": "C", "name": "Rod Gate-Open", "enabled": True, "cooldown": 1.5, "priority": 2},
        {"key": "X", "name": "Rod Gate-Block", "enabled": True, "cooldown": 2.0, "priority": 3},
        {"key": "V", "name": "Fish-Beating Staff Technique", "enabled": True, "cooldown": 2.5, "priority": 4}
    ],
    "spam_click": True,
    "click_delay_ms": 40,
    "skill_delay_ms": 25,
    "skill_hold_ms": 30,
    "qte_enabled": True,
    "qte_press_delay_ms": 60,
    "current_fish": 0,
    "hotkey_toggle": "f6"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge defaults for any missing keys
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            print(f"Error loading config: {e}, using defaults.")
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
