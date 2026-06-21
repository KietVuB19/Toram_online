"""
Simple Template Capture Tool
==============================
Instead of dragging on an overlay (which can be tricky),
this tool lets you:
  1. Position your game window showing the element
  2. Press ENTER in terminal
  3. A 3-second countdown gives you time to click on the game
  4. Then use your mouse to SELECT a region using the snipping tool approach

Actually even simpler: press F10 while the element is on screen,
and it saves a FULL screenshot. Then you crop it manually in Paint.

OR: use the auto-crop method - you hover your mouse over the element,
press F10, and it saves a small region around your cursor.
"""

import time
import os
import sys

try:
    from PIL import Image, ImageGrab
    import win32api
    import win32con
    import win32gui
except ImportError:
    print("Run: pip install pillow pywin32")
    sys.exit(1)

TEMPLATES = [
    ("img_collab_title.png", "Collab Battle Lv140 tooltip", 60,
     "Walk near the crystal NPC until dark brown tooltip appears, hover mouse OVER it"),
    ("img_ready.png",        "I'm ready!! button  (ORANGE - hover state)", 60,
     "In battle lobby: move mouse OVER the button so it turns ORANGE, then stay still"),
    ("img_ok_orange.png",    "OK button  (ORANGE - hover state)", 60,
     "On victory screen: move mouse OVER the OK button so it turns ORANGE, then stay still"),
    ("img_skill_icon.png",   "Skill icon in slot 6 (SMALL - tight crop)", 18,
     "During battle: hover mouse directly over the CENTER of the icon in slot 6 only"),
]



def countdown(n=3):
    for i in range(n, 0, -1):
        print(f"  Capturing in {i}...", end="\r")
        time.sleep(1)
    print("  Capturing NOW!     ")


def capture_around_cursor(radius=25):
    """Capture a small region around the current mouse cursor."""
    x, y = win32api.GetCursorPos()
    bbox = (x - radius, y - radius, x + radius, y + radius)
    # Make sure bbox is within screen bounds
    sw = win32api.GetSystemMetrics(0)
    sh = win32api.GetSystemMetrics(1)
    bbox = (
        max(0, bbox[0]),
        max(0, bbox[1]),
        min(sw, bbox[2]),
        min(sh, bbox[3]),
    )
    return ImageGrab.grab(bbox=bbox), (x, y)


def capture_fullscreen():
    """Capture the entire screen."""
    return ImageGrab.grab()


def main():
    print("=" * 55)
    print("  Toram Bot – Simple Template Capture Tool")
    print("=" * 55)
    print()
    print("HOW IT WORKS:")
    print("  • For each template, you get a 5-second countdown")
    print("  • During countdown: switch to game, HOVER your mouse")
    print("    directly OVER the button/element you want to capture")
    print("  • It saves a 120x120 pixel region around your cursor")
    print("  • Simple and reliable!")
    print()
    print("TIP: Make sure the game is visible (not minimized)")
    print()

    os.makedirs("templates_preview", exist_ok=True)

    for filename, label, radius, instruction in TEMPLATES:
        print(f"{'─'*55}")
        print(f"  Next: {label}")
        print(f"  → {instruction}")
        print()

        if os.path.exists(filename):
            ans = input(f"  '{filename}' already exists. Recapture? (y/N): ").strip().lower()
            if ans != "y":
                print(f"  Skipping.\n")
                continue

        input(f"  Press ENTER to start 5-second countdown…")
        print(f"  → Switch to game and hover mouse over: {label}")

        for i in range(5, 0, -1):
            print(f"  Capturing in {i}...  (hover mouse over the element!)", end="\r")
            time.sleep(1)
        print()

        img, cursor_pos = capture_around_cursor(radius=radius)
        img.save(filename)

        # Also save a preview with larger context
        preview, _ = capture_around_cursor(radius=radius + 60)
        preview.save(f"templates_preview/preview_{filename}")

        print(f"  ✓ Saved {filename}  ({img.width}×{img.height}px)  cursor was at {cursor_pos}")
        print(f"  ✓ Preview saved to templates_preview/preview_{filename}")
        print()

    print("=" * 55)
    print("  All templates captured!")
    print("  Check the 'templates_preview' folder to verify")
    print("  they look correct before running the bot.")
    print()
    print("  Next step:  py toram_collab_bot.py")
    print("=" * 55)


if __name__ == "__main__":
    main()