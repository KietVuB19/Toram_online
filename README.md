# ⚔️ Toram Online — Collab Battle Lv140 Auto Bot
RESOLUTION: (960x540)

A Python automation bot for **Toram Online** that automatically farms the **Collab Battle Lv140** repeatedly — walking to the NPC, entering the fight, using skills, and collecting rewards in a loop.

> **Disclaimer:** This is a fan-made tool for personal use. Use at your own risk. Automation may violate Toram Online's Terms of Service.

---

## 🤖 How It Works

The bot runs a full Collab Battle loop automatically:

1. **Wake input handler** — taps `W` briefly to reactivate Toram's input after map transitions
2. **Walk to NPC** — holds `W` via pyautogui to walk toward the Collab NPC
3. **Click Collab Battle Lv140** — detects and clicks the battle entry tooltip via image matching
4. **Click "I'm ready!!"** — confirms entry into the battle
5. **Wait through loading** — waits for black screen + boss intro cutscene
6. **Use skill** — double-clicks the skill icon in slot 6 to activate the skill
7. **Monitor boss** — repeatedly uses skill until the victory screen appears
8. **Click OK** — detects and clicks the OK button on the victory screen
9. **Wait for map reload** — waits for the game to return to the map
10. **Repeat** ♻️

The bot uses **PrintWindow API** for background window capture and **SendInput / pyautogui** for clicks and keypresses, so it can detect UI elements even when the game window is behind other windows.

---

## 📋 Requirements

- Windows OS
- Python `>= 3.8`
- Toram Online installed (PC / Steam / emulator)

### Install dependencies

```bash
pip install pyautogui opencv-python pillow pywin32
```

---

## 🖼️ Template Images (Required)

The bot uses **image recognition** (`opencv`) to find UI elements. Screenshot these from your own game and save them as PNG files in the **same folder** as the script:

| File | What to screenshot |
|------|--------------------|
| `img_collab_title.png` | The "Collab Battle Lv140" tooltip text |
| `img_ready.png` | The "I'm ready!!" button |
| `img_ok_orange.png` | The OK button on the victory screen |
| `img_skill_icon.png` | The skill icon in your hotbar slot 6 |

> **Tip:** Use Windows Snipping Tool to capture these images accurately. Recapture if match scores are consistently low — UI appearance varies by resolution.

---

## 🚀 Usage

Before starting the bot, **manually complete one round** so your character is standing at the correct spawn position on the map. The bot assumes this position at the start of every loop.

```bash
python toram_collab_bot.py
```

| Key | Action |
|-----|--------|
| `F8` | Start / Stop the bot |
| `F9` | Force quit |

After pressing `F8`, you have **5 seconds** to switch to the Toram Online window. The bot will warn you at startup if any template images are missing.

---

## ⚙️ Configuration

Edit the constants near the top of `toram_collab_bot.py`:

```python
MATCH_CONFIDENCE   = 0.65    # Image match threshold (0.0–1.0)
SKILL_KEY          = "6"     # Fallback skill key (normally uses icon click
WAIT_BLACKSCREEN   = 3.0     # Wait after clicking Ready (seconds)
WAIT_BOSS_INTRO    = 9.0     # Wait for boss intro cutscene (seconds)
WAIT_BETWEEN_SKILL = 9.0     # Delay between skill uses during boss fight (seconds)
WAIT_VICTORY       = 7       # Wait after OK click for map to fully reload (seconds)
STARTUP_DELAY      = 5       # Seconds after F8 to switch to game
```

---

## 📁 Project Structure

```
Toram_online/
├── toram_collab_bot.py      # Main bot script
├── img_collab_title.png     # (you create these)
├── img_ready.png
├── img_ok_orange.png
└── img_skill_icon.png
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---------|---------|
| `opencv-python` | Template image matching |
| `Pillow` / `PrintWindow API` | Background window capture (works when game is behind other windows) |
| `pywin32` (win32gui/api) | Window detection, foreground focus, SendInput clicks |
| `pyautogui` | W/S movement keypresses (reliable across map transitions) |
| `threading` | Non-blocking bot loop with F8/F9 hotkey listener |

---

## ⚠️ Notes

- **Movement keys** (`W`/`S`) are sent via `pyautogui` which requires the game window to be in the foreground. All click actions use `SendInput` and work regardless of foreground state.
- A **wake input tap** is performed after each map reload to ensure Toram's input handler is active before walking begins.
- **Human-like random delays** are added between actions to reduce detection risk.
- If template matching fails repeatedly, recapture your template images — UI appearance differs by resolution and game version.
- The bot performs a **double-confirm** before clicking OK on the victory screen to avoid false positives.
- Emergency stop: move your mouse to **any screen corner** to trigger pyautogui's failsafe.

---

## 📜 License

MIT License — free to use and modify.