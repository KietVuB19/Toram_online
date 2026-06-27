"""
Toram Online - Collab Battle Lv140 Auto Bot (v4)
=================================================
- Auto-detects the game window by scanning all open windows
- Clicks the CENTER of the game window to focus it (not Chrome)
- 5s startup delay after F8
- Debug screenshots saved on template failures
"""

import time
import random
import sys
import os
import threading

try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image, ImageGrab
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError as e:
    print(f"[ERROR] Missing: {e}")
    print("  pip install pyautogui opencv-python pillow pywin32")
    sys.exit(1)

import ctypes

# ─────────────────────────────────────────────
#  SendInput - true OS-level click (Toram ignores PostMessage clicks)
# ─────────────────────────────────────────────

PUL = ctypes.POINTER(ctypes.c_ulong)

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("mi", MouseInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

MOUSEEVENTF_MOVE     = 0x0001
MOUSEEVENTF_LEFTDOWN  = 0x0002
MOUSEEVENTF_LEFTUP    = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP   = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
INPUT_MOUSE          = 0

def sendinput_click(screen_x, screen_y, restore_cursor=True):
    """
    True OS-level click. Saves your real cursor position first,
    clicks at (screen_x, screen_y), then restores cursor back
    to where it was — so your mouse on the manga/video side
    is never "stolen" for more than a fraction of a second.
    """
    # Save current real cursor position
    orig_pos = win32api.GetCursorPos() if restore_cursor else None

    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    abs_x = int(screen_x * 65535 / screen_w)
    abs_y = int(screen_y * 65535 / screen_h)
    extra = ctypes.c_ulong(0)

    def send(flag, ax=abs_x, ay=abs_y):
        ii_ = Input_I()
        ii_.mi = MouseInput(ax, ay, 0, flag | MOUSEEVENTF_ABSOLUTE, 0, ctypes.pointer(extra))
        x = Input(INPUT_MOUSE, ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    send(MOUSEEVENTF_MOVE)
    time.sleep(random.uniform(0.03, 0.07))
    send(MOUSEEVENTF_LEFTDOWN)
    time.sleep(random.uniform(0.06, 0.13))
    send(MOUSEEVENTF_LEFTUP)

    # Restore cursor back to where the user had it
    if restore_cursor and orig_pos:
        time.sleep(random.uniform(0.03, 0.07))
        ow, oh = orig_pos
        oabs_x = int(ow * 65535 / screen_w)
        oabs_y = int(oh * 65535 / screen_h)
        send(MOUSEEVENTF_MOVE, oabs_x, oabs_y)

# ─────────────────────────────────────────────
#  SendInput - true OS-level key press (for skill keys / movement)
# ─────────────────────────────────────────────

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_K(ctypes.Union):
    _fields_ = [("ki", KeyBdInput)]

class InputK(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_K)]

INPUT_KEYBOARD  = 1
KEYEVENTF_KEYUP = 0x0002

VK_MAP = {
    'w': 0x57, 'a': 0x41, 's': 0x53, 'd': 0x44, 'f': 0x46,
    '0':0x30,'1':0x31,'2':0x32,'3':0x33,'4':0x34,
    '5':0x35,'6':0x36,'7':0x37,'8':0x38,'9':0x39,
}

def sendinput_key_down(key):
    vk = VK_MAP.get(key.lower())
    if vk is None:
        return
    extra = ctypes.c_ulong(0)
    ii_ = Input_K()
    ii_.ki = KeyBdInput(vk, 0, 0, 0, ctypes.pointer(extra))
    x = InputK(INPUT_KEYBOARD, ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def sendinput_key_up(key):
    vk = VK_MAP.get(key.lower())
    if vk is None:
        return
    extra = ctypes.c_ulong(0)
    ii_ = Input_K()
    ii_.ki = KeyBdInput(vk, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    x = InputK(INPUT_KEYBOARD, ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def sendinput_key_press(key, hold_sec=0):
    """True OS-level key press. Needed because Toram ignores PostMessage keys."""
    sendinput_key_down(key)
    if hold_sec > 0:
        time.sleep(hold_sec)
    else:
        time.sleep(random.uniform(0.06, 0.12))
    sendinput_key_up(key)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

# Keywords to auto-detect the game window (case-insensitive, any match works)
GAME_WINDOW_KEYWORDS = ["toram", "ToramOnline"]

IMG_COLLAB_TITLE    = "img_collab_title.png"   # Collab Battle Lv140
IMG_READY           = "img_ready.png"
IMG_OK              = "img_ok_orange.png"
IMG_SKILL_ICON      = "img_skill_icon.png"  # skill icon in slot 6 (clicked, not keyed)

MATCH_CONFIDENCE    = 0.65

SKILL_KEY           = "6"   # kept as fallback only

DELAY_SHORT         = (0.3, 0.7)
DELAY_MEDIUM        = (0.8, 1.4)
DELAY_LONG          = (1.5, 2.5)

WAIT_BLACKSCREEN = (2.5, 3.5)
WAIT_BOSS_INTRO  = (8.0, 10.5)
WAIT_BETWEEN_SKILL  = 9.0
WAIT_VICTORY        = 7
WALK_UP_DURATION    = 2.0
STARTUP_DELAY       = 5        # seconds after F8 to switch to game

DEBUG_FOLDER        = "debug_screenshots"

pyautogui.FAILSAFE  = True
pyautogui.PAUSE     = 0.05

# ─────────────────────────────────────────────
#  GLOBALS
# ─────────────────────────────────────────────

running    = False
bot_thread = None

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def human_delay(r):
    time.sleep(max(0.05, random.uniform(*r) + random.gauss(0, 0.04)))

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# def save_debug(name, img_np):
#     os.makedirs(DEBUG_FOLDER, exist_ok=True)
#     path = os.path.join(DEBUG_FOLDER, f"{name}_{int(time.time())}.png")
#     cv2.imwrite(path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
#     log(f"  [DEBUG] Saved: {path}")

# ── Window detection ────────────────────────

def find_game_window():
    """
    Find the game window by exact title 'ToramOnline'.
    Explicitly excludes VS Code, Chrome, and other apps
    that might contain 'toram' in their title bar.
    """
    EXCLUDE_KEYWORDS = [
        "visual studio code", "vscode",
        "google chrome", "chrome",
        "firefox", "edge", "opera",
        "explorer", "notepad",
    ]

    matches = []
    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        title_lower = title.lower()

        # Skip any known non-game windows
        for ex in EXCLUDE_KEYWORDS:
            if ex in title_lower:
                return

        # Must match exactly 'ToramOnline' (the real game exe window)
        if title == "ToramOnline":
            matches.append((hwnd, title))

    win32gui.EnumWindows(cb, None)

    if matches:
        hwnd, title = matches[0]
        log(f"  [WINDOW] Found game: '{title}'")
        return hwnd

    log("  [WINDOW] 'ToramOnline' not found! All visible windows:")
    def cb2(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if t:
                print(f"    → '{t}'")
    win32gui.EnumWindows(cb2, None)
    log("  → Is Toram Online running? Make sure the game is open.")
    return None

def get_window_rect(hwnd):
    rect = win32gui.GetClientRect(hwnd)
    pt   = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
    return (pt[0], pt[1], pt[0] + rect[2], pt[1] + rect[3])

def force_foreground(hwnd):
    """
    Reliably bring hwnd to foreground even when called from a
    background process (VS Code terminal). Uses the AttachThreadInput
    trick which Windows requires for background apps to steal focus.
    """
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        fg_hwnd = win32gui.GetForegroundWindow()
        fg_thread = win32api.GetCurrentThreadId()
        target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        cur_thread = win32api.GetCurrentThreadId()

        if target_thread != cur_thread:
            ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, True)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            ctypes.windll.user32.AttachThreadInput(cur_thread, target_thread, False)
        else:
            win32gui.SetForegroundWindow(hwnd)

        return True
    except Exception as e:
        log(f"  [WARN] force_foreground failed: {e}")
        # Fallback: simple alt-key trick to unlock SetForegroundWindow restriction
        try:
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # ALT down
            win32gui.SetForegroundWindow(hwnd)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # ALT up
            return True
        except Exception as e2:
            log(f"  [WARN] Fallback foreground also failed: {e2}")
            return False


def focus_game_window(hwnd, click_center=False):
    """
    Bring game window to true foreground (no manual click needed).
    click_center=True → also clicks center (rarely needed now)
    """
    ok = force_foreground(hwnd)
    time.sleep(0.2)
    if click_center:
        l, t, r, b = get_window_rect(hwnd)
        cx, cy = (l + r) // 2, (t + b) // 2
        sendinput_click(cx, cy)
        time.sleep(0.2)
        log(f"  [FOCUS] Clicked game center ({cx}, {cy})")
    else:
        log(f"  [FOCUS] Game forced to foreground (no click) — ok={ok}")

def capture_window(hwnd):
    """
    Capture game window using PrintWindow API.
    Works even when the window is covered, minimized, or behind other windows.
    """
    try:
        import ctypes
        from ctypes import windll
        import win32ui

        l, t, r, b = get_window_rect(hwnd)
        w = r - l
        h = b - t

        # Create device context and bitmap
        hwnd_dc     = win32gui.GetWindowDC(hwnd)
        mfc_dc      = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc     = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(save_bitmap)

        # PrintWindow captures window content regardless of visibility
        result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        bmp_info = save_bitmap.GetInfo()
        bmp_str  = save_bitmap.GetBitmapBits(True)
        img = np.frombuffer(bmp_str, dtype=np.uint8).reshape(h, w, 4)
        img = img[:, :, :3]  # drop alpha, keep RGB (actually BGR from win32)
        img = img[:, :, ::-1].copy()  # convert BGR to RGB

        # Cleanup
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return img, (l, t)

    except Exception as e:
        # Fallback to ImageGrab if PrintWindow fails
        log(f"  [WARN] PrintWindow failed ({e}), falling back to ImageGrab")
        l, t, r, b = get_window_rect(hwnd)
        img = ImageGrab.grab(bbox=(l, t, r, b))
        return np.array(img), (l, t)

# ── Template matching ───────────────────────

def find_template(screenshot_np, template_path, confidence=MATCH_CONFIDENCE):
    if not os.path.exists(template_path):
        log(f"  [WARN] Missing template: {template_path}")
        return None
    tmpl = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if tmpl is None:
        return None
    sh, sw = screenshot_np.shape[:2]
    th, tw = tmpl.shape[:2]
    if th > sh or tw > sw:
        log(f"  [WARN] Template bigger than window! Recapture it.")
        return None
    screen_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    res = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    log(f"  [MATCH] {os.path.basename(template_path)}: {max_val:.3f} (need {confidence})")
    if max_val >= confidence:
        return (max_loc[0] + tw // 2, max_loc[1] + th // 2)
    return None

def real_click(sx, sy, double=False):
    """
    True OS-level click at absolute screen coords (sx, sy).
    Toram ignores SendMessage/PostMessage clicks, so we use SendInput
    which briefly moves the real cursor and sends a genuine click.
    """
    jx = random.randint(-5, 5)
    jy = random.randint(-4, 4)
    sendinput_click(sx + jx, sy + jy)
    if double:
        human_delay((0.08, 0.22))
        sendinput_click(sx + jx, sy + jy)

def click_template(hwnd, template_path, label="", double=False, debug=False):
    ss, (wl, wt) = capture_window(hwnd)
    # if debug:
    #     save_debug(label.replace(" ","_"), ss)
    pos = find_template(ss, template_path)
    if pos:
        sx, sy = wl + pos[0], wt + pos[1]
        log(f"  ✓ '{label}' found → clicking ({sx}, {sy})")
        real_click(sx, sy, double=double)
        return True
    return False

def press_key(key, hold_sec=0):
    """Send key via pyautogui — only call AFTER focus_game_window."""
    if hold_sec > 0:
        pyautogui.keyDown(key)
        time.sleep(hold_sec)
        pyautogui.keyUp(key)
    else:
        pyautogui.press(key)

def send_key_to_window(hwnd, key, hold_sec=0):
    """
    Send a key DIRECTLY to the game window handle using PostMessage.
    Works regardless of which window has focus — W will NEVER go to VS Code.
    """
    vk = win32api.VkKeyScan(key) & 0xFF   # get virtual key code
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    if hold_sec > 0:
        time.sleep(hold_sec)
    else:
        human_delay((0.05, 0.12))
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

# ─────────────────────────────────────────────
#  BOT STEPS
# ─────────────────────────────────────────────

# def step_walk_to_npc(hwnd):
#     """
#     Hold W and scan every 0.3s for the Collab tooltip.
#     Stop walking, wait for character to settle, then click the
#     tooltip text directly (F key not reliable enough - back to click).
#     Cursor auto-restores after click.
#     Max walk time = 4 seconds before giving up.
#     Returns True if tooltip was found and clicked.
#     """
#     log("Step 1+2 – Walking toward NPC, watching for Collab Battle Lv140 tooltip...")
#     force_foreground(hwnd)
#     time.sleep(0.2)
#     MAX_WALK = 4.0
#     CHECK_INTERVAL = 0.3

#     VK_W = win32api.VkKeyScan("w") & 0xFF
#     VK_S = win32api.VkKeyScan("s") & 0xFF
#     start = time.time()
#     found = False

#     # Hold W - send directly to game window (no focus needed)
#     win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_W, 0)

#     while time.time() - start < MAX_WALK:
#         time.sleep(CHECK_INTERVAL)
#         ss, (wl, wt) = capture_window(hwnd)
#         pos = find_template(ss, IMG_COLLAB_TITLE)
#         if pos:
#             # Release W
#             win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
#             # Tap S to stop momentum
#             win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_S, 0)
#             time.sleep(0.20)
#             win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_S, 0)

#             # Let character fully settle before clicking
#             time.sleep(0.5)

#             # Re-check tooltip position after settling (text may have shifted)
#             ss2, (wl2, wt2) = capture_window(hwnd)
#             pos2 = find_template(ss2, IMG_COLLAB_TITLE)
#             if pos2:
#                 sx, sy = wl2 + pos2[0], wt2 + pos2[1]
#             else:
#                 sx, sy = wl + pos[0], wt + pos[1]

#             log(f"  Tooltip confirmed after {time.time()-start:.1f}s -> clicking ({sx},{sy})")
#             real_click(sx, sy)
#             found = True
#             break

#     if not found:
#         win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
#         log("  [WARN] Tooltip not found within 4s of walking.")

#     human_delay(DELAY_MEDIUM)
#     return found

# def step_walk_to_npc(hwnd):
#     log("Step 1+2 – Walking toward NPC, watching for Collab Battle Lv140 tooltip...")

#     force_foreground(hwnd)
#     time.sleep(0.4)
#     log(f"  [FOCUS] Foreground: {win32gui.GetWindowText(win32gui.GetForegroundWindow())}")
    
#     MAX_WALK = 6.0
#     CHECK_INTERVAL = 0.3

#     VK_W = win32api.VkKeyScan("w") & 0xFF
#     VK_S = win32api.VkKeyScan("s") & 0xFF
#     start = time.time()
#     found = False

#     win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_W, 0)

#     while time.time() - start < MAX_WALK:
#         time.sleep(CHECK_INTERVAL)
#         ss, (wl, wt) = capture_window(hwnd)
#         pos = find_template(ss, IMG_COLLAB_TITLE)
#         if pos:
#             win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
#             win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_S, 0)
#             time.sleep(0.20)
#             win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_S, 0)
#             time.sleep(0.5)

#             ss2, (wl2, wt2) = capture_window(hwnd)
#             pos2 = find_template(ss2, IMG_COLLAB_TITLE)
#             sx, sy = (wl2 + pos2[0], wt2 + pos2[1]) if pos2 else (wl + pos[0], wt + pos[1])

#             log(f"  Tooltip confirmed after {time.time()-start:.1f}s -> clicking ({sx},{sy})")
#             real_click(sx, sy)
#             found = True
#             break

#     if not found:
#         win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
#         log("  [WARN] Tooltip not found within 6s of walking.")

#     human_delay(DELAY_MEDIUM)
#     return found

def step_walk_to_npc(hwnd):
    log("Step 1+2 – Walking toward NPC, watching for Collab Battle Lv140 tooltip...")

    force_foreground(hwnd)
    time.sleep(0.5)
    log(f"  [FOCUS] Foreground: {win32gui.GetWindowText(win32gui.GetForegroundWindow())}")

    MAX_WALK = 6.0
    CHECK_INTERVAL = 0.3
    start = time.time()
    found = False

    pyautogui.keyDown('w')   # ← swap to pyautogui
    try:
        while time.time() - start < MAX_WALK:
            time.sleep(CHECK_INTERVAL)
            ss, (wl, wt) = capture_window(hwnd)
            pos = find_template(ss, IMG_COLLAB_TITLE)
            if pos:
                pyautogui.keyUp('w')
                pyautogui.keyDown('s')
                time.sleep(0.20)
                pyautogui.keyUp('s')
                time.sleep(0.5)

                ss2, (wl2, wt2) = capture_window(hwnd)
                pos2 = find_template(ss2, IMG_COLLAB_TITLE)
                sx, sy = (wl2 + pos2[0], wt2 + pos2[1]) if pos2 else (wl + pos[0], wt + pos[1])
                log(f"  Tooltip confirmed after {time.time()-start:.1f}s -> clicking ({sx},{sy})")
                real_click(sx, sy)
                found = True
                break
    finally:
        pyautogui.keyUp('w')   # always release

    if not found:
        log("  [WARN] Tooltip not found within 6s of walking.")

    human_delay(DELAY_MEDIUM)
    return found

def step_approach_and_click(hwnd):
    """
    Full approach: walk toward NPC, stop on tooltip, click it.
    Retries up to 3 times if character overshoots.
    """
    for attempt in range(3):
        if attempt > 0:
            log(f"  Retry approach #{attempt+1} – walking back toward NPC...")
        result = step_walk_to_npc(hwnd)
        if result:
            return True
        log("  Didn't find tooltip while walking, trying again...")
    return False


def step_click_collab(hwnd):
    # Fallback: tooltip may already be visible before walking
    log("Step 2 – Fallback check for tooltip...")
    for i in range(3):
        if click_template(hwnd, IMG_COLLAB_TITLE,
                          label="Collab Battle Lv140", debug=(i == 0)):
            human_delay(DELAY_MEDIUM)
            return True
        human_delay(DELAY_SHORT)
    return False

def step_click_ready(hwnd):
    log("Step 3 – Clicking 'I'm ready!!'…")
    for i in range(8):
        if click_template(hwnd, IMG_READY,
                          label="I'm ready!!", debug=(i < 2)):
            human_delay(DELAY_SHORT)
            return True
        log(f"  Attempt {i+1}/8 – retrying…")
        human_delay(random.choice([DELAY_SHORT, DELAY_MEDIUM, DELAY_LONG]))
    log("  [WARN] Ready button not found.")
    return False

def step_wait_for_battle():
    # total = WAIT_BLACKSCREEN + WAIT_BOSS_INTRO + random.uniform(0, 1.5)
    total = random.uniform(*WAIT_BLACKSCREEN) + random.uniform(*WAIT_BOSS_INTRO)
    log(f"Step 4 – Waiting {total:.1f}s for intro…")
    time.sleep(total)

def step_use_skill(hwnd):
    """
    Use skill by double-clicking the skill icon (slot 6).
    Keyboard '6' doesn't work for this action in Toram - needs a real click.
    Cursor auto-restores after click.
    """
    log("Step 5 – Using skill (double-click on skill icon)...")
    ss, (wl, wt) = capture_window(hwnd)
    pos = find_template(ss, IMG_SKILL_ICON)
    if pos:
        sx, sy = wl + pos[0], wt + pos[1]
        log(f"  ✓ Skill icon found -> double-clicking ({sx},{sy})")
        real_click(sx, sy, double=True)
    else:
        log("  [WARN] Skill icon not found. Falling back to keyboard '6'...")
        force_foreground(hwnd)
        time.sleep(0.15)
        sendinput_key_press(SKILL_KEY)
        human_delay((0.20, 0.40))
        sendinput_key_press(SKILL_KEY)
    human_delay((0.10, 0.20))

def step_finish_boss(hwnd):
    log("Step 6 – Monitoring boss fight…")
    for round_ in range(1, 6):
        time.sleep(WAIT_BETWEEN_SKILL + random.uniform(-1.0, 3.0))
        ss, (wl, wt) = capture_window(hwnd)

        # Raise threshold — 0.35 is way too low, causes false positives
        pos = find_template(ss, IMG_OK, confidence=0.65)
        if pos:
            log(f"  Victory screen detected! Waiting 1s for it to fully render...")
            time.sleep(1.0)  # let the victory screen fully animate in
            # Re-confirm the OK button is still there
            ss2, (wl2, wt2) = capture_window(hwnd)
            pos2 = find_template(ss2, IMG_OK, confidence=0.65)
            if pos2:
                sx, sy = wl2 + pos2[0], wt2 + pos2[1]
                log(f"  ✓ OK confirmed → clicking ({sx}, {sy})")
                real_click(sx, sy)
                human_delay(DELAY_MEDIUM)
                return True
            else:
                log(f"  False positive — OK not confirmed on re-check, continuing...")

        log(f"  Round {round_} – Boss still alive, using skill…")
        step_use_skill(hwnd)

    time.sleep(WAIT_BETWEEN_SKILL)
    return False

def step_click_ok(hwnd):
    log("Step 7 – Clicking OK…")
    focus_game_window(hwnd)
    for i in range(10):
        if click_template(hwnd, IMG_OK, label="OK", debug=(i < 2)):  # uses default 0.55
            human_delay(DELAY_MEDIUM)
            return True
        log(f"  Attempt {i+1}/10 – waiting…")
        human_delay(DELAY_LONG)
    log("  [WARN] OK not found.")
    return False

def step_wait_return():
    wait = WAIT_VICTORY + random.uniform(0, 1.5)
    log(f"Step 8 – Waiting {wait:.1f}s for map reload…")
    time.sleep(wait)
    time.sleep(random.uniform(0.5, 2.5))

def step_wake_input(hwnd):
    """
    Tap W briefly to wake up Toram's input handler after map transition.
    0.05s is too short to visibly move the character.
    """
    force_foreground(hwnd)
    time.sleep(0.3)
    pyautogui.keyDown('w')
    time.sleep(random.uniform(0.04, 0.09))
    pyautogui.keyUp('w')
    time.sleep(0.2)
    log("  [WAKE] Input handler activated.")

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────

def bot_loop():
    global running
    log(f"Starting in {STARTUP_DELAY}s — switch to Toram Online now!")
    for i in range(STARTUP_DELAY, 0, -1):
        print(f"  {i}...", end="\r", flush=True)
        time.sleep(1)
    print()

    iteration = 0
    while running:
        iteration += 1
        log(f"\n{'═'*52}\n  Iteration #{iteration}\n{'═'*52}")

        hwnd = find_game_window()
        if not hwnd:
            time.sleep(5)
            continue

        try:
            # Walk toward NPC, stop on tooltip, click it (retries if overshoot)
            if not step_approach_and_click(hwnd):
                if not step_click_collab(hwnd):
                    continue
            if not step_click_ready(hwnd):
                continue
            step_wait_for_battle()
            step_use_skill(hwnd)
            if not step_finish_boss(hwnd):
                step_click_ok(hwnd) 
            step_wait_return()
            step_wake_input(hwnd)
            time.sleep(random.uniform(0.3, 1.2))
        except pyautogui.FailSafeException:
            log("[FAILSAFE] Corner triggered — stopped!")
            running = False
        except Exception as e:
            log(f"[ERROR] {e}")
            time.sleep(3)

    log("Bot stopped.")

# ─────────────────────────────────────────────
#  HOTKEY
# ─────────────────────────────────────────────

def toggle_bot():
    global running, bot_thread
    if not running:
        running = True
        bot_thread = threading.Thread(target=bot_loop, daemon=True)
        bot_thread.start()
        print(f"\n[F8] ▶ STARTED — {STARTUP_DELAY}s to switch to game!\n")
    else:
        running = False
        print("\n[F8] ■ STOPPING…\n")

def listen_for_hotkey():
    VK_F8, VK_F9 = 0x77, 0x78
    print("F8 = Start/Stop    F9 = Quit")
    print("Emergency stop: move mouse to any screen corner\n")
    prev = False
    while True:
        down = bool(win32api.GetAsyncKeyState(VK_F8) & 0x8000)
        if down and not prev:
            toggle_bot()
        prev = down
        if win32api.GetAsyncKeyState(VK_F9) & 0x8000:
            sys.exit(0)
        time.sleep(0.05)

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Toram Online – Collab Battle Lv140 Bot  (v4)")
    print("=" * 55)
    print(f"  Keywords : {GAME_WINDOW_KEYWORDS}")
    print(f"  Skill    : key '{SKILL_KEY}'")
    print(f"  Delay    : {STARTUP_DELAY}s after F8")
    print(f"  Debug    : {DEBUG_FOLDER}/")
    print("=" * 55 + "\n")

    missing = [t for t in [IMG_COLLAB_TITLE, IMG_READY, IMG_OK, IMG_SKILL_ICON]
           if not os.path.exists(t)]
    if missing:
        print("[WARN] Missing templates — run capture_templates.py first:")
        for m in missing:
            print(f"  – {m}")
        print()

    listen_for_hotkey()