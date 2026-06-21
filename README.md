# ⚔️ Toram Online — Collab Battle Lv140 Auto Bot

A Python automation bot for **Toram Online** that automatically farms the **Collab Battle Lv140** repeatedly — walking to the NPC, entering the fight, using skills, and collecting rewards in a loop.

> **Disclaimer:** This is a fan-made tool for personal use. Use at your own risk. Automation may violate Toram Online's Terms of Service.

---

## 🤖 How It Works

The bot runs a full Collab Battle loop automatically:

1. **Walk to NPC** — holds `W` to walk toward the Collab NPC
2. **Click Collab Battle Lv140** — detects and clicks the battle entry button via image matching
3. **Click "I'm ready!!"** — confirms entry into the battle
4. **Wait through loading** — waits for black screen + boss intro cutscene
5. **Use skill** — presses `6` (double press) to activate the skill
6. **Monitor boss** — repeatedly uses skill until the victory screen appears
7. **Click OK** — detects and clicks the OK button on the victory screen
8. **Wait for map reload** — waits for the game to return to the map
9. **Repeat** ♻️

The bot uses **Win32 API** to send clicks and keypresses, so it can operate even when the game window is behind other windows.

---

## 📋 Requirements

- Windows OS
- Python `>= 3.8`
- Toram Online installed (PC / Steam / emulator)

### Install dependencies

```bash
pip install pyautogui pygetwindow opencv-python pillow pywin32
```

---

## 🖼️ Template Images (Required)

The bot uses **image recognition** (`opencv`) to find UI elements. You need to screenshot these from your own game and save them as PNG files in the **same folder** as the script:

| File | What to screenshot |
|------|--------------------|
| `img_collab_title.png` | The "Collab Battle Lv140" button |
| `img_ready.png` | The "I'm ready!!" button |
| `img_ok_blue.png` | Blue OK button (victory screen) |
| `img_ok_orange.png` | Orange OK button (hover/fallback) |
| `img_skill_icon.png` | Sword/skill icon *(optional)* |

> **Tip:** Use Windows Snipping Tool or `capture_templates.py` to capture these images accurately.

---

## 🚀 Usage

```bash
python toram_collab_bot.py
```

| Key | Action |
|-----|--------|
| `F8` | Start / Stop the bot |
| `F9` | Force quit |

The bot will warn you at startup if any template images are missing.

---

## ⚙️ Configuration

Edit the constants at the top of `toram_collab_bot.py` to match your setup:

```python
GAME_WINDOW_TITLE  = "Toram Online"   # Window title to target
MATCH_CONFIDENCE   = 0.75             # Image match threshold (0.0–1.0)
SKILL_KEY          = "6"              # Key to press for skill
WAIT_BLACKSCREEN   = 2.5              # Wait after clicking Ready (seconds)
WAIT_BOSS_INTRO    = 6.5              # Wait for boss intro cutscene (seconds)
WAIT_BETWEEN_SKILL = 5.0              # Delay between skill uses (seconds)
WALK_UP_DURATION   = 2.0              # How long to hold W toward NPC (seconds)
```

---

## 📁 Project Structure

```
Toram_online/
├── toram_collab_bot.py      # Main bot script
├── capture_templates.py     # Helper to capture template images
├── img_collab_title.png     # (you create these)
├── img_ready.png
├── img_ok_blue.png
└── img_ok_orange.png
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---------|---------|
| `opencv-python` | Template image matching |
| `Pillow` / `ImageGrab` | Screenshot capture |
| `pywin32` (win32gui/api) | Background window click & keypress |
| `pygetwindow` | Window detection |
| `threading` | Non-blocking bot loop |

---

## ⚠️ Notes

- The bot brings the game window to the foreground briefly for the `W` key walk step. All other steps (clicks, skill key) work in the background via Win32 messages.
- Human-like random delays are added between actions to reduce detection risk.
- If template matching fails repeatedly, re-capture your template images — UI may look different depending on resolution or game version.

---

## 📜 License

MIT License — free to use and modify.
