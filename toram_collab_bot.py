"""
Toram Online - Collab Battle Lv140 Auto Bot
============================================
Runs the Collab Battle loop automatically with human-like behavior.
Works even when the game window is behind other windows (uses Win32 API).

Requirements:
    pip install pyautogui pygetwindow opencv-python pillow pywin32

Usage:
    python toram_collab_bot.py
"""

import time
import random
import sys
import os
import ctypes
import threading

try:
    import pyautogui
    import pygetwindow as gw
    import cv2
    import numpy as np
    from PIL import Image, ImageGrab
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("\nPlease install required packages:")
    print("  pip install pyautogui pygetwindow opencv-python pillow pywin32")
    sys.exit(1)

# ─────────────────────────────────────────────
#  CONFIG  (tweak these to match your setup)
# ─────────────────────────────────────────────

GAME_WINDOW_TITLE = "Toram Online"   # Partial match is fine

# Image templates – put these PNG files in the same folder as the script
# (screenshot them yourself for best accuracy)
IMG_COLLAB_TITLE   = "img_collab_title.png"    # "Collab Battle Lv140" button
IMG_READY          = "img_ready.png"            # "I'm ready!!" button
IMG_OK_BLUE        = "img_ok_blue.png"          # Blue OK button (victory screen)
IMG_OK_ORANGE      = "img_ok_orange.png"        # Orange OK (hover state / fallback)
IMG_SWORD          = "img_sword.png"            # Sword/skill icon (optional)

# Confidence thresholds for template matching (0.0 – 1.0)
MATCH_CONFIDENCE   = 0.75

# Keyboard shortcut to use skill (alternative to clicking sword icon)
SKILL_KEY          = "6"

# Hotkey to START / STOP the bot
TOGGLE_KEY         = "F8"

# Human-like delay range helpers  (min_sec, max_sec)
DELAY_SHORT        = (0.3,  0.7)
DELAY_MEDIUM       = (0.8,  1.4)
DELAY_LONG         = (1.5,  2.5)

# Fixed waits (approximate game timings)
WAIT_BLACKSCREEN   = 2.5   # seconds – after clicking Ready
WAIT_BOSS_INTRO    = 6.5   # seconds – boss intro cutscene
WAIT_BETWEEN_SKILL = 5.0   # seconds – wait before re-using skill
WAIT_VICTORY       = 3.5   # seconds – wait after OK for map to reload
WALK_UP_DURATION   = 2.0   # seconds – hold W to walk toward NPC

# ─────────────────────────────────────────────
#  GLOBALS
# ─────────────────────────────────────────────

running = False
bot_thread = None

# ─────────────────────────────────────────────
#  UTILITY FUNCTIONS
# ─────────────────────────────────────────────

def human_delay(range_: tuple):
    """Sleep for a random duration within range_, adding micro-jitter."""
    base = random.uniform(*range_)
    jitter = random.gauss(0, 0.05)
    time.sleep(max(0.05, base + jitter))


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def find_game_window():
    """Return the hwnd of the game window, or None."""
    result = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if GAME_WINDOW_TITLE.lower() in title.lower():
                result.append(hwnd)

    win32gui.EnumWindows(callback, None)
    return result[0] if result else None


def get_window_rect(hwnd):
    """Return (left, top, right, bottom) of the client area in screen coords."""
    rect = win32gui.GetClientRect(hwnd)
    pt = win32gui.ClientToScreen(hwnd, (rect[0], rect[1]))
    return (pt[0], pt[1], pt[0] + rect[2], pt[1] + rect[3])


def capture_window(hwnd):
    """Screenshot the game window (works even if partially covered)."""
    l, t, r, b = get_window_rect(hwnd)
    img = ImageGrab.grab(bbox=(l, t, r, b))
    return np.array(img)


def find_template(screenshot_np, template_path, confidence=MATCH_CONFIDENCE):
    """
    Find a template image inside the screenshot.
    Returns (cx, cy) in SCREEN coords, or None.
    """
    if not os.path.exists(template_path):
        return None

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        return None

    screen_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        th, tw = template.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return (cx, cy)
    return None


def send_click(hwnd, x_rel, y_rel, double=False):
    """
    Send a mouse click to (x_rel, y_rel) relative to the window client area.
    Works even when the window is minimized or behind other windows.
    """
    lparam = win32api.MAKELONG(int(x_rel), int(y_rel))
    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    human_delay((0.05, 0.12))

    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    human_delay((0.04, 0.10))
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    if double:
        human_delay((0.08, 0.18))
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        human_delay((0.04, 0.10))
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def send_key(hwnd, vk_code, hold_sec=0):
    """Send a keypress (optionally held for hold_sec seconds)."""
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
    if hold_sec > 0:
        time.sleep(hold_sec)
    else:
        human_delay((0.05, 0.10))
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)


def click_on_template(hwnd, screenshot, template_path, double=False, label=""):
    """Find template and click it. Returns True on success."""
    pos = find_template(screenshot, template_path)
    if pos:
        log(f"  ✓ Found '{label}' at {pos}, clicking…")
        send_click(hwnd, pos[0], pos[1], double=double)
        return True
    log(f"  ✗ Template '{label}' not found in screenshot")
    return False


# ─────────────────────────────────────────────
#  BOT STEPS
# ─────────────────────────────────────────────

def step_walk_to_npc(hwnd):
    """Walk up (W key) for ~2 seconds to approach the NPC."""
    log("Step 1 – Walking up toward NPC (W held 2 s)…")
    VK_W = ord('W')
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_W, 0)
    time.sleep(WALK_UP_DURATION + random.uniform(-0.2, 0.3))
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
    human_delay(DELAY_SHORT)


def step_click_collab(hwnd):
    """Click the 'Collab Battle Lv140' menu entry."""
    log("Step 2 – Looking for 'Collab Battle Lv140'…")
    for attempt in range(6):
        ss = capture_window(hwnd)
        if click_on_template(hwnd, ss, IMG_COLLAB_TITLE, label="Collab Battle Lv140"):
            human_delay(DELAY_MEDIUM)
            return True
        log(f"  Attempt {attempt+1}/6 – not found, retrying…")
        human_delay(DELAY_LONG)
    log("  [WARN] Could not find Collab title after 6 attempts. Skipping.")
    return False


def step_click_ready(hwnd):
    """Click 'I'm ready!!'."""
    log("Step 3 – Clicking 'I'm ready!!'…")
    for attempt in range(5):
        ss = capture_window(hwnd)
        if click_on_template(hwnd, ss, IMG_READY, label="I'm ready!!"):
            return True
        human_delay(DELAY_MEDIUM)
    log("  [WARN] Ready button not found.")
    return False


def step_wait_for_battle(hwnd):
    """Wait through black screen + boss intro."""
    log(f"Step 4 – Waiting for black screen ({WAIT_BLACKSCREEN:.0f}s) + boss intro ({WAIT_BOSS_INTRO:.0f}s)…")
    time.sleep(WAIT_BLACKSCREEN + random.uniform(0, 0.5))
    time.sleep(WAIT_BOSS_INTRO + random.uniform(0, 1.0))


def step_use_skill(hwnd):
    """Double-press 6 (or click sword icon) to use the skill."""
    log("Step 5 – Using skill (pressing 6)…")
    VK_6 = ord('6')
    send_key(hwnd, VK_6)
    human_delay(DELAY_SHORT)
    send_key(hwnd, VK_6)   # double press = double-click equivalent


def step_finish_boss(hwnd):
    """Wait, then use skill again if boss still alive, loop until OK appears."""
    log("Step 6 – Waiting for boss to die or using skill again…")
    for round_ in range(1, 6):   # up to 5 extra rounds
        time.sleep(WAIT_BETWEEN_SKILL + random.uniform(-0.5, 1.0))
        ss = capture_window(hwnd)

        # Check if victory OK is already visible
        if (find_template(ss, IMG_OK_BLUE)
                or find_template(ss, IMG_OK_ORANGE)):
            log("  Victory screen detected early!")
            return

        log(f"  Round {round_} – Boss still up, using skill again…")
        step_use_skill(hwnd)

    # Final long wait
    time.sleep(WAIT_BETWEEN_SKILL)


def step_click_ok(hwnd):
    """Click the OK button on the victory screen."""
    log("Step 7 – Clicking OK (victory)…")
    for attempt in range(8):
        ss = capture_window(hwnd)
        # Try blue OK first, then orange (hover state)
        for img, label in [(IMG_OK_BLUE, "OK (blue)"), (IMG_OK_ORANGE, "OK (orange)")]:
            if click_on_template(hwnd, ss, img, label=label):
                human_delay(DELAY_MEDIUM)
                return True
        log(f"  Attempt {attempt+1}/8 – OK button not found, waiting…")
        human_delay(DELAY_LONG)
    log("  [WARN] OK button not found after 8 attempts.")
    return False


def step_wait_return(hwnd):
    """Wait for the map to reload."""
    wait = WAIT_VICTORY + random.uniform(0, 1.5)
    log(f"Step 8 – Waiting {wait:.1f}s for map to reload…")
    time.sleep(wait)


# ─────────────────────────────────────────────
#  MAIN BOT LOOP
# ─────────────────────────────────────────────

def bot_loop():
    global running
    log("Bot started. Press F8 to stop.")

    iteration = 0
    while running:
        iteration += 1
        log(f"\n{'═'*50}")
        log(f"  Iteration #{iteration}")
        log(f"{'═'*50}")

        hwnd = find_game_window()
        if not hwnd:
            log(f"[ERROR] Game window '{GAME_WINDOW_TITLE}' not found! Retrying in 5s…")
            time.sleep(5)
            continue

        # Optionally bring window to foreground for walking (W key)
        # Comment this out if you want fully background operation
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.3)
        except Exception:
            pass  # Continue anyway if focus fails

        try:
            step_walk_to_npc(hwnd)
            if not step_click_collab(hwnd):
                continue
            if not step_click_ready(hwnd):
                continue
            step_wait_for_battle(hwnd)
            step_use_skill(hwnd)
            step_finish_boss(hwnd)
            step_click_ok(hwnd)
            step_wait_return(hwnd)

        except Exception as e:
            log(f"[ERROR] Exception in bot loop: {e}")
            time.sleep(3)

    log("Bot stopped.")


# ─────────────────────────────────────────────
#  HOTKEY LISTENER
# ─────────────────────────────────────────────

def toggle_bot():
    global running, bot_thread
    if not running:
        running = True
        bot_thread = threading.Thread(target=bot_loop, daemon=True)
        bot_thread.start()
        print("\n[F8] Bot STARTED\n")
    else:
        running = False
        print("\n[F8] Bot STOPPING (finishing current action…)\n")


def listen_for_hotkey():
    """Poll for F8 key press to toggle the bot."""
    VK_F8 = 0x77
    VK_F9 = 0x78  # Emergency stop
    print("Press F8 to START / STOP the bot.")
    print("Press F9 to force-quit.\n")
    f8_was_down = False
    while True:
        f8_down = bool(win32api.GetAsyncKeyState(VK_F8) & 0x8000)
        if f8_down and not f8_was_down:
            toggle_bot()
        f8_was_down = f8_down

        if win32api.GetAsyncKeyState(VK_F9) & 0x8000:
            log("F9 pressed – force quitting.")
            sys.exit(0)

        time.sleep(0.05)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Toram Online – Collab Battle Lv140 Auto Bot")
    print("=" * 55)
    print(f"  Game window:  {GAME_WINDOW_TITLE!r}")
    print(f"  Start/Stop:   F8")
    print(f"  Force quit:   F9")
    print("=" * 55)
    print()

    # Warn if template images are missing
    templates = [IMG_COLLAB_TITLE, IMG_READY, IMG_OK_BLUE, IMG_OK_ORANGE]
    missing = [t for t in templates if not os.path.exists(t)]
    if missing:
        print("[WARN] The following template images are missing:")
        for m in missing:
            print(f"  – {m}")
        print("\nThe bot will SKIP steps where templates are not found.")
        print("Screenshot each UI element and save as the filenames above.\n")

    listen_for_hotkey()