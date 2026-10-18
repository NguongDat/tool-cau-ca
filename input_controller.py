import time
import ctypes
from ctypes import wintypes
import pydirectinput

# Reduce default pydirectinput delay for ultra-fast reaction
pydirectinput.PAUSE = 0.001
pydirectinput.FAILSAFE = False

class InputController:
    def __init__(self):
        self.user32 = ctypes.windll.user32

    def get_roblox_hwnd(self):
        """Finds the actual Roblox game window handle, filtering out browser tabs."""
        # 1. First priority: Check standard Roblox window class
        hwnd = self.user32.FindWindowW("WINDOWSCLIENT", "Roblox")
        if hwnd and self.user32.IsWindowVisible(hwnd):
            return hwnd

        hwnd = self.user32.FindWindowW(None, "Roblox")
        if hwnd and self.user32.IsWindowVisible(hwnd):
            cname = ctypes.create_unicode_buffer(256)
            self.user32.GetClassNameW(hwnd, cname, 256)
            cn = cname.value.lower()
            if "chrome" not in cn and "edge" not in cn and "firefox" not in cn:
                return hwnd

        # 2. Enumerate visible top-level windows matching roblox
        best_hwnd = 0
        def enum_windows_callback(h, extra):
            nonlocal best_hwnd
            if self.user32.IsWindowVisible(h):
                cname = ctypes.create_unicode_buffer(256)
                self.user32.GetClassNameW(h, cname, 256)
                if cname.value == "WINDOWSCLIENT":
                    best_hwnd = h
                    return False

                length = self.user32.GetWindowTextLengthW(h)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(h, buff, length + 1)
                    title = buff.value.lower()
                    cn = cname.value.lower()
                    if "roblox" in title and "chrome" not in cn and "edge" not in cn and "firefox" not in cn:
                        rect = wintypes.RECT()
                        self.user32.GetWindowRect(h, ctypes.byref(rect))
                        if (rect.right - rect.left) > 300 and (rect.bottom - rect.top) > 300:
                            best_hwnd = h
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, ctypes.c_void_p)
        self.user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        return best_hwnd

    def get_roblox_rect(self):
        """Returns (left, top, right, bottom) of Roblox window or None."""
        hwnd = self.get_roblox_hwnd()
        if hwnd:
            rect = wintypes.RECT()
            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return (rect.left, rect.top, rect.right, rect.bottom)
        return None

    def focus_roblox(self):
        """Brings the Roblox game window to foreground if running."""
        try:
            hwnd = self.get_roblox_hwnd()
            if hwnd:
                fg = self.user32.GetForegroundWindow()
                if fg != hwnd:
                    self.user32.ShowWindow(hwnd, 9) # SW_RESTORE
                    self.user32.SetForegroundWindow(hwnd)
                    time.sleep(0.08)
                return True
        except Exception as e:
            print(f"[Input] Focus Roblox error: {e}")
        return False

    def mouse_down(self):
        """Sends hardware Left Mouse Down event (Giữ chuột trái liên tục)."""
        self.user32.mouse_event(0x0002, 0, 0, 0, 0) # MOUSEEVENTF_LEFTDOWN
        pydirectinput.mouseDown(button='left', _pause=False)

    def mouse_up(self):
        """Sends hardware Left Mouse Up event (Thả chuột trái)."""
        self.user32.mouse_event(0x0004, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP
        pydirectinput.mouseUp(button='left', _pause=False)

    def cast_rod(self, hold_time=1.2):
        """
        Quăng cần câu chuẩn xác:
        - Giữ nguyên vị trí chuột người chơi hướng ra mặt nước (không kéo vào giữa màn hình đè lên nhân vật).
        - GIỮ CHUỘT TRÁI liên tục trong suốt hold_time (tích đầy thanh lực quăng cần).
        - THẢ CHUỘT TRÁI để phóng cần câu ra xa.
        - Đứng yên tại chỗ tuyệt đối.
        """
        self.focus_roblox()
        time.sleep(0.04)

        # Đảm bảo thả chuột sạch sẽ trước khi đè giữ
        self.mouse_up()
        time.sleep(0.03)

        # BẮT ĐẦU ĐÈ GIỮ CHUỘT TRÁI
        self.mouse_down()

        # Duy trì trạng thái GIỮ CHUỘT liên tục trong suốt hold_time
        start_time = time.time()
        while time.time() - start_time < hold_time:
            # Gửi tín hiệu duy trì giữ chuột mỗi 40ms để game nhận chuẩn trạng thái sạc lực
            self.user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.04)

        # THẢ CHUỘT TRÁI để quăng cần câu ra xa
        self.mouse_up()
        time.sleep(0.06)

    def single_click(self, hold_time=0.06):
        """Nhấn và nhả chuột trái 1 lần dứt khoát (để giật cần khi cá cắn câu)."""
        self.mouse_down()
        time.sleep(hold_time)
        self.mouse_up()

    def key_down(self, key_char):
        """Holds a hardware key DOWN (used for holding QTE keys like A, W, D)."""
        k = key_char.lower()
        pydirectinput.keyDown(k)

    def key_up(self, key_char):
        """Releases a held hardware key."""
        k = key_char.lower()
        pydirectinput.keyUp(k)

    def press_key(self, key_char, hold_duration=0.03):
        """Presses and releases a key with reliable duration."""
        k = key_char.lower()
        try:
            pydirectinput.keyDown(k)
            if hold_duration > 0:
                time.sleep(hold_duration)
        finally:
            pydirectinput.keyUp(k)

    def click_fast(self, hold_time=0.02):
        """Click chuột trái dứt khoát chuẩn xác, đảm bảo game nhận 100% không bị nuốt click."""
        self.user32.mouse_event(0x0002, 0, 0, 0, 0) # MOUSEEVENTF_LEFTDOWN
        if hold_time > 0:
            time.sleep(hold_time)
        self.user32.mouse_event(0x0004, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP

    def spam_click(self, count=1, delay=0.01):
        """Performs fast left clicks for damage."""
        for _ in range(count):
            self.click_fast()
            if delay > 0:
                time.sleep(delay)

    def click_at(self, x, y, button='left', delay_after=0.2):
        """Moves cursor to screen coordinate (x, y) and clicks."""
        pydirectinput.moveTo(int(x), int(y))
        time.sleep(0.04)
        pydirectinput.click(button=button)
        if delay_after > 0:
            time.sleep(delay_after)

    def hold_key(self, key_char, duration):
        """Holds a movement key for navigation."""
        k = key_char.lower()
        pydirectinput.keyDown(k)
        time.sleep(duration)
        pydirectinput.keyUp(k)

    def rotate_camera(self, delta_x=100, delta_y=0, duration=0.1):
        """Drags right mouse to rotate character camera in 3D."""
        pydirectinput.mouseDown(button='right')
        time.sleep(0.02)
        pydirectinput.moveRel(delta_x, delta_y, relative=True)
        time.sleep(duration)
        pydirectinput.mouseUp(button='right')
