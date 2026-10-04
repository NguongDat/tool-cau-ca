import ctypes
import time

# SendInput structures
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class Input_I(ctypes.Union):
    _fields_ = [
        ("ki", KeyBdInput),
        ("mi", MouseInput),
        ("hi", HardwareInput)
    ]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", Input_I)
    ]

# Constants
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1
INPUT_MOUSE = 0

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# DirectX Scancodes:
SCANCODES = {
    'w': 0x11,
    'a': 0x1E,
    's': 0x1F,
    'd': 0x20,
    'z': 0x2C,
    'x': 0x2D,
    'c': 0x2E,
    'v': 0x2F,
    'space': 0x39,
    '1': 0x02,
    '2': 0x03,
    '3': 0x04,
    '4': 0x05,
}

def press_key(key_char):
    """Presses down a key via DirectInput scan code."""
    k = key_char.lower()
    if k not in SCANCODES:
        return
    sc = SCANCODES[k]
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, sc, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(key_char):
    """Releases a key via DirectInput scan code."""
    k = key_char.lower()
    if k not in SCANCODES:
        return
    sc = SCANCODES[k]
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, sc, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def tap_key(key_char, duration=0.02):
    """Taps a key with duration (default 20ms for fast responsive game input)."""
    press_key(key_char)
    time.sleep(duration)
    release_key(key_char)

def mouse_down():
    """Presses and holds left mouse button down."""
    try:
        import pydirectinput
        pydirectinput.FAILSAFE = False
        pydirectinput.PAUSE = 0
        pydirectinput.mouseDown(button='left')
    except Exception:
        pass
    try:
        import win32api
        import win32con
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    except Exception:
        pass

def mouse_up():
    """Releases left mouse button."""
    try:
        import pydirectinput
        pydirectinput.FAILSAFE = False
        pydirectinput.PAUSE = 0
        pydirectinput.mouseUp(button='left')
    except Exception:
        pass
    try:
        import win32api
        import win32con
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    except Exception:
        pass

def hold_left_mouse(duration=1.8, stop_check=None):
    """
    Simulates firmly holding left mouse button down for charging rod (x5 damage),
    then releases it smoothly.
    """
    mouse_down()
    t_end = time.time() + max(0.1, float(duration))
    while time.time() < t_end:
        if stop_check and stop_check():
            break
        time.sleep(0.02)
    mouse_up()


# ============================================================
# BACKGROUND INPUT: PostMessage - Gửi input vào Roblox window
# mà KHÔNG cần cửa sổ phải là foreground (không giật màn hình)
# ============================================================

# Virtual Key codes cho PostMessage
VK_CODES = {
    'w': 0x57, 'a': 0x41, 's': 0x53, 'd': 0x44,
    'z': 0x5A, 'x': 0x58, 'c': 0x43, 'v': 0x56,
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    'space': 0x20,
}

WM_KEYDOWN     = 0x0100
WM_KEYUP       = 0x0101
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP   = 0x0202
MK_LBUTTON     = 0x0001

def _make_lparam(lo, hi):
    """Pack two 16-bit values into a 32-bit LPARAM."""
    return (hi & 0xFFFF) << 16 | (lo & 0xFFFF)

def _make_key_lparam(vk, is_up=False):
    """Build correct lParam for WM_KEYDOWN/WM_KEYUP."""
    try:
        import ctypes
        scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0) & 0xFF
    except Exception:
        scan = 0
    repeat = 1
    ext = 0
    prev_state = 1 if is_up else 0
    transition = 1 if is_up else 0
    lp = (transition << 31) | (prev_state << 30) | (ext << 24) | (scan << 16) | repeat
    return lp

def post_key_to_hwnd(hwnd, key_char, duration=0.02):
    """
    Gửi phím xuống cửa sổ Roblox qua PostMessage.
    Hoạt động kể cả khi Roblox không phải foreground window.
    """
    try:
        import ctypes
        k = key_char.lower()
        vk = VK_CODES.get(k)
        if not vk or not hwnd:
            return
        lp_down = _make_key_lparam(vk, is_up=False)
        lp_up   = _make_key_lparam(vk, is_up=True)
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lp_down)
        time.sleep(max(0.015, duration))
        ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP,   vk, lp_up)
    except Exception:
        # Fallback ve SendInput neu PostMessage loi
        tap_key(key_char, duration=duration)

def post_mouse_hold_to_hwnd(hwnd, client_x, client_y, duration=1.2, stop_check=None):
    """
    Gia lap GIU chuot trai tai vi tri (client_x, client_y) trong cua so Roblox
    qua PostMessage - khong can foreground, khong giat man hinh.
    """
    try:
        import ctypes
        lp = _make_lparam(client_x, client_y)
        ctypes.windll.user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
        t_end = time.time() + max(0.1, float(duration))
        while time.time() < t_end:
            if stop_check and stop_check():
                break
            time.sleep(0.02)
        ctypes.windll.user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lp)
    except Exception:
        # Fallback ve SendInput neu loi
        hold_left_mouse(duration=duration, stop_check=stop_check)

if __name__ == '__main__':
    print("DirectInput module verified and ready.")

