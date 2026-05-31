"""
Template Capture Helper
========================
Run this script to easily screenshot UI elements from Toram Online
and save them as the template images needed by the bot.

Usage:
    python capture_templates.py
"""

import time
import os
import sys
try:
    from PIL import Image, ImageGrab
    import win32gui
    import win32api
    import win32con
except ImportError:
    print("Run: pip install pillow pywin32")
    sys.exit(1)

GAME_TITLE = "Toram Online"

TEMPLATES = [
    ("img_collab_title.png", "Collab Battle Lv140  – the clickable menu entry"),
    ("img_ready.png",        "I'm ready!! button  – blue, idle state"),
    ("img_ok_blue.png",      "OK button            – blue, victory screen"),
    ("img_ok_orange.png",    "OK button            – orange hover state (optional)"),
    ("img_sword.png",        "Sword/skill icon     – bottom bar (optional)"),
]

def find_window():
    result = []
    def cb(hwnd, _):
        if GAME_TITLE.lower() in win32gui.GetWindowText(hwnd).lower():
            result.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return result[0] if result else None


def capture_region():
    """Let the user draw a rectangle with the mouse."""
    import tkinter as tk
    coords = {}

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.configure(bg="black")
    root.attributes("-topmost", True)

    canvas = tk.Canvas(root, cursor="cross", bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    start = {}

    def on_press(e):
        start["x"], start["y"] = e.x_root, e.y_root

    def on_release(e):
        coords["bbox"] = (
            min(start["x"], e.x_root),
            min(start["y"], e.y_root),
            max(start["x"], e.x_root),
            max(start["y"], e.y_root),
        )
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.mainloop()
    return coords.get("bbox")


def main():
    print("=" * 50)
    print("  Toram Bot – Template Image Capture Tool")
    print("=" * 50)
    print()
    print("Instructions:")
    print("  1. Open Toram Online and navigate to the relevant screen.")
    print("  2. When prompted, a transparent overlay will appear.")
    print("  3. Click-and-drag around the UI element to capture it.")
    print()

    for filename, description in TEMPLATES:
        if os.path.exists(filename):
            ans = input(f"'{filename}' already exists. Recapture? (y/N): ").strip().lower()
            if ans != "y":
                print(f"  Skipping {filename}\n")
                continue

        print(f"── Capture: {description}")
        print(f"   File: {filename}")
        input("   Press ENTER when the element is visible on screen…")

        time.sleep(0.5)
        bbox = capture_region()
        if not bbox or bbox[2] - bbox[0] < 5 or bbox[3] - bbox[1] < 5:
            print("   Selection too small or cancelled. Skipping.\n")
            continue

        img = ImageGrab.grab(bbox=bbox)
        img.save(filename)
        print(f"   ✓ Saved {filename} ({img.width}×{img.height} px)\n")

    print("=" * 50)
    print("All done! You can now run toram_collab_bot.py")
    print("=" * 50)


if __name__ == "__main__":
    main()