"""
Toram Online - Collab Battle Lv90 Auto Bot (v4)
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
except ImportError as e:
    print(f"[ERROR] Missing: {e}")
    print("  pip install pyautogui opencv-python pillow pywin32")
    sys.exit(1)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

# Keywords to auto-detect the game window (case-insensitive, any match works)
GAME_WINDOW_KEYWORDS = ["toram", "ToramOnline"]

IMG_COLLAB_TITLE    = "img_collab_title.png"   # Collab Battle Lv90
IMG_READY           = "img_ready.png"
IMG_OK_BLUE         = "img_ok_orange.png"   # same file - only orange needed
IMG_OK_ORANGE       = "img_ok_orange.png"

MATCH_CONFIDENCE    = 0.65

SKILL_KEY           = "6"

DELAY_SHORT         = (0.3, 0.7)
DELAY_MEDIUM        = (0.8, 1.4)
DELAY_LONG          = (1.5, 2.5)

WAIT_BLACKSCREEN    = 2.5
WAIT_BOSS_INTRO     = 6.5
WAIT_BETWEEN_SKILL  = 5.0
WAIT_VICTORY        = 3.5
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

def save_debug(name, img_np):
    os.makedirs(DEBUG_FOLDER, exist_ok=True)
    path = os.path.join(DEBUG_FOLDER, f"{name}_{int(time.time())}.png")
    cv2.imwrite(path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    log(f"  [DEBUG] Saved: {path}")

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

def focus_game_window(hwnd):
    """
    Bring game window to front and click its CENTER to ensure
    it gets input focus (not a Chrome tab or other window).
    """
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)

        # Click the center of the game window
        l, t, r, b = get_window_rect(hwnd)
        cx = (l + r) // 2
        cy = (t + b) // 2
        pyautogui.moveTo(cx, cy, duration=0.15)
        pyautogui.click()
        time.sleep(0.25)
        log(f"  [FOCUS] Clicked game center ({cx}, {cy})")
    except Exception as e:
        log(f"  [WARN] Focus error: {e}")

def capture_window(hwnd):
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
    pyautogui.moveTo(sx + random.randint(-3,3),
                     sy + random.randint(-3,3),
                     duration=random.uniform(0.10, 0.22))
    human_delay((0.05, 0.10))
    pyautogui.click()
    if double:
        human_delay((0.08, 0.15))
        pyautogui.click()

def click_template(hwnd, template_path, label="", double=False, debug=False):
    ss, (wl, wt) = capture_window(hwnd)
    if debug:
        save_debug(label.replace(" ","_"), ss)
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

def step_walk_to_npc(hwnd):
    """
    Hold W and scan every 0.3s for the Collab tooltip.
    Stop walking the moment it appears, then click it.
    Max walk time = 4 seconds before giving up.
    Returns True if tooltip was found and clicked.
    """
    log("Step 1+2 – Walking toward NPC, watching for Collab Battle Lv140 tooltip...")
    VK_W = win32api.VkKeyScan("w") & 0xFF
    MAX_WALK = 4.0
    CHECK_INTERVAL = 0.3

    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_W, 0)
    start = time.time()
    found = False

    while time.time() - start < MAX_WALK:
        time.sleep(CHECK_INTERVAL)
        ss, (wl, wt) = capture_window(hwnd)
        pos = find_template(ss, IMG_COLLAB_TITLE)
        if pos:
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
            # Tap S briefly to cancel momentum/stop character sliding
            VK_S = win32api.VkKeyScan("s") & 0xFF
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_S, 0)
            time.sleep(0.15)
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_S, 0)
            time.sleep(0.2)
            # Re-check tooltip is still visible after stopping
            ss2, (wl2, wt2) = capture_window(hwnd)
            pos2 = find_template(ss2, IMG_COLLAB_TITLE)
            if pos2:
                sx, sy = wl2 + pos2[0], wt2 + pos2[1]
            else:
                sx, sy = wl + pos[0], wt + pos[1]  # fallback to original pos
            log(f"  Tooltip found after {time.time()-start:.1f}s -> clicking ({sx},{sy})")
            real_click(sx, sy)
            found = True
            break

    if not found:
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_W, 0)
        log("  [WARN] Tooltip not found within 4s of walking.")

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
    focus_game_window(hwnd)
    for i in range(8):
        if click_template(hwnd, IMG_READY,
                          label="I'm ready!!", debug=(i < 2)):
            human_delay(DELAY_SHORT)
            return True
        log(f"  Attempt {i+1}/8 – retrying…")
        human_delay(DELAY_MEDIUM)
    log("  [WARN] Ready button not found.")
    return False

def step_wait_for_battle():
    total = WAIT_BLACKSCREEN + WAIT_BOSS_INTRO + random.uniform(0, 1.5)
    log(f"Step 4 – Waiting {total:.1f}s for intro…")
    time.sleep(total)

def step_use_skill(hwnd):
    log("Step 5 – Using skill (key 6 directly to game)...")
    send_key_to_window(hwnd, SKILL_KEY)
    human_delay((0.15, 0.30))
    send_key_to_window(hwnd, SKILL_KEY)
def step_finish_boss(hwnd):
    log("Step 6 – Monitoring boss fight…")
    for round_ in range(1, 8):
        wait = WAIT_BETWEEN_SKILL + random.uniform(-0.5, 1.2)
        log(f"  Waiting {wait:.1f}s…")
        time.sleep(wait)
        ss, _ = capture_window(hwnd)
        if find_template(ss, IMG_OK_BLUE) or find_template(ss, IMG_OK_ORANGE):
            log("  ✓ Victory screen!")
            return
        log(f"  Round {round_} – using skill again…")
        step_use_skill(hwnd)
    time.sleep(WAIT_BETWEEN_SKILL)

def step_click_ok(hwnd):
    log("Step 7 – Clicking OK…")
    focus_game_window(hwnd)
    for i in range(10):
        for img, lbl in [(IMG_OK_BLUE,"OK blue"),(IMG_OK_ORANGE,"OK orange")]:
            if click_template(hwnd, img, label=lbl, debug=(i < 2)):
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
            step_finish_boss(hwnd)
            step_click_ok(hwnd)
            step_wait_return()

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
    print("  Toram Online – Collab Battle Lv90 Bot  (v4)")
    print("=" * 55)
    print(f"  Keywords : {GAME_WINDOW_KEYWORDS}")
    print(f"  Skill    : key '{SKILL_KEY}'")
    print(f"  Delay    : {STARTUP_DELAY}s after F8")
    print(f"  Debug    : {DEBUG_FOLDER}/")
    print("=" * 55 + "\n")

    missing = [t for t in [IMG_COLLAB_TITLE, IMG_READY, IMG_OK_BLUE, IMG_OK_ORANGE]
               if not os.path.exists(t)]
    if missing:
        print("[WARN] Missing templates — run capture_templates.py first:")
        for m in missing:
            print(f"  – {m}")
        print()

    listen_for_hotkey()