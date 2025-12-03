# Velocity GUI Minecraft Server Manager 🧪☕💜

> Welcome to the purple-tinged control center you never knew you needed but secretly always wanted.

This repo powers the **Velocity GUI Minecraft Server Manager** — a desktop launcher that wrangles your Minecraft and Velocity servers, keeps Playit in line, and lets you pretend you’re a wizard while sipping coffee at 3 AM.

---

## 🧠 Why Does This Exist?

Because managing servers like a caveman hurts:

1. Starting five servers manually is boring.
2. Copy-pasting `/stop` into random terminals at warp speed is a great way to nuke the *wrong* world.
3. Console windows bouncing around your taskbar are the opposite of chill.
4. Neo0oen demanded something fabulous with **zero white backgrounds**.

So this GUI exists to actually respect your time, your clipboard, and your aesthetic.

---

## ⚙️ Key Features  
*(a.k.a. why this launcher flexes harder than your SMP’s spawn)*

### 🧱 Servers Tab

- Add / duplicate / edit / remove servers with a couple clicks.
- See live status, PID, memory range, runtime, and a shiny uptime timer.
- Open `server.properties`, `whitelist.json`, or the server folder directly from the app.
- Start / stop servers without playing “find the right terminal” on your taskbar.

### 📜 Console Tab

- Filter logs using the search bar (with instant match counts).
- Auto-scroll toggle: stay glued to the latest logs or freeze the screen mid-scroll — your choice.
- Pause / Resume: freeze updates while you copy walls of text, then jump straight back to real-time.
- Saved command tree:
  - Nested categories, numbered entries, drag-and-drop ordering.
  - Hover previews, copy / send buttons… basically your command war chest.
- Save Log: exports to timestamped folders so evidence never “accidentally” disappears.

### 📈 Monitoring Tab

- System overview: CPU, RAM, swap, disk usage via `psutil`, updated every ~2 seconds.
- Per-server metrics: status, PID, uptime, CPU %, memory usage.
- Great for spotting that one JVM having a mid-life crisis while the others behave.

### 🎨 Branding & Polish

- Transparent app icon (no more white squares screaming “2003 shareware”).  
- Status bar credit: `made with <3 by neo0oen` — because purple hearts > plain text.  
- Dark-themed UI so your eyes don’t file a complaint at 3 AM.

---

## 🚀 Getting Started

### 1. Build the EXE (optional but comfy)

From the repo root:

```bash
./tools/build_exe.bat
```

The output lands in:

```text
dist/velocity gui minecraft server manger.exe
```

Yes, the filename is cursed. No, we’re not fixing it. It builds, it runs, we move on.

### 2. Run from source (for devs / tinkerers)

```bash
python -m pip install -r requirements.txt
python src/main.py
```

### 3. Configure your servers

Use `config/example_server_launcher_config.json` as your template and create your own config file in the `config/` folder.

Saved commands use **config version 4** and are now order-aware, so they keep behaving even if you rename folders or categories.

---

## 🧩 Configuration Notes

- Each server entry includes its **name**, **working directory**, **start command**, and optional flags.
- Saved commands are organized in a tree:
  - Categories (folders)
  - Ordered commands with labels + actual command text.
- The app keeps track of both:
  - The **display order**, and
  - The **stored IDs**  
  so rearranging things doesn’t accidentally nuke your muscle memory.

If you break your JSON, the launcher will not be impressed. Use a formatter or your IDE’s JSON tools if you value your sanity.

---

## 😵 Dark-ish FAQ

**Q: Can this fix my lag?**  
A: No. It just helps you *watch* your lag in real time with pretty graphs.

**Q: Does this work with modded servers / Paper / Velocity / etc.?**  
A: If you can start it from a terminal with a command, this launcher can probably start it too. It just wraps processes and shows you what they’re doing.

**Q: Why is the EXE name so weird?**  
A: Because that’s what happens when you let devs type while sleep-deprived. You’re welcome to rename the shortcut.

**Q: Is this safe?**  
A: It’s a Python Qt app that starts processes you point it at. If you tell it to run `format C:`, that’s on you. Pick your commands carefully.

**Q: Can I run this on Linux / macOS?**  
A: The code is Python + PySide6, so yes, from source. The provided EXE is for Windows, but nothing stops you from running `python src/main.py` elsewhere if your environment has the deps installed.

---

## 🤝 Contributing

Bug found? Feature idea? Button that vibes wrong?

- Open an **issue** describing what happened and how to reproduce it.
- Open a **PR** if you:
  - Added a feature,
  - Fixed a bug,
  - Or removed particularly cursed code and replaced it with something marginally less cursed.

Memes in PR descriptions get moral support. Fixing at least one bug gets actual attention.

---

## 🧪 Tech Stack

- Python 3.13  
- PySide6 (Qt)  
- psutil (system metrics)  
- pillow (icon alchemy)  
- PyInstaller (for bundling the desktop magic into one click)  

---

## 📜 License

**TBD.**  
Until then, treat it as: *“be nice and don’t sell it on eBay.”*  
If you’re unsure whether something is “nice”, it probably isn’t. Ask first.

---

> “Buttons that work are cool, but buttons that work **and look sassy**? That’s culture.” – Someone, probably.


---

## Credits

- **Neo0oen** – Visionary, purple enthusiast, chaos coordinator.
- **Everyone else** – People who like not typing `java -Xms512M` a thousand times.

