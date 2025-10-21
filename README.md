# Velocity GUI Minecraft Server Manager 🤖🪄

Welcome to the purple-tinged control center you never knew you needed but secretly always wanted. This repo powers the Velocity GUI Minecraft Server Manager — a desktop launcher that wrangles your Minecraft and Velocity servers, keeps Playit in line, and lets you pretend you’re a wizard while sipping coffee at 3 AM.

## Why Does This Exist?

Because:

1. Starting five servers manually is boring.
2. Copy-pasting `/stop` into random terminals at warp speed is a great way to nuke the wrong world.
3. Console windows that bounce around your taskbar are the opposite of chill.
4. Neo0oen demanded something fabulous with zero white backgrounds.

So we built a GUI that actually respects your time, your clipboard, and your aesthetic.

## Key Features (a.k.a. Why this launcher flexes harder than your SMP’s spawn)

### 🧮 Servers Tab
- Add/duplicate/edit/remove servers with a couple clicks.
- See live status, PID, memory range, runtime, and a shiny uptime timer.
- Open `server.properties`, `whitelist.json`, or the server folder right from the app.

### 🧾 Console Tab
- **Filter logs** using the search bar (with instant match counts).
- **Auto-scroll toggle**: stay glued to the latest logs or freeze the screen mid-scroll—your call.
- **Pause/Resume**: freeze updates while you copy walls of text, then jump back to present time.
- **Saved command tree**: nested categories, numbered entries, drag & drop ordering, hover previews, copy/send buttons… basically your command war chest.
- **Save Log**: exports to timestamped folders so evidence never “accidentally” disappears.

### 📊 Monitoring Tab
- System overview (CPU, RAM, swap, disk) courtesy of psutil, updated every 2 seconds.
- Per-server metrics: status, PID, uptime, CPU %, and memory usage. Perfect for spotting that one JVM having a midlife crisis.

### 🖼️ Branding & Polish
- Transparent icon (no more white squares screaming 2003 freeware).
- Status bar credit: `made with <3 by neo0oen`, because purple hearts > plain text.

## Getting Started

1. **Download / build** the EXE:
   ```powershell
   ./tools/build_exe.bat
   ```
   Output lands in `dist/velocity gui minecraft server manger.exe`.

2. **Install dependencies** if you want to run from source:
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. **Launch**
   ```powershell
   python src/main.py
   ```

4. **Configure** using [`config/example_server_launcher_config.json`](config/example_server_launcher_config.json) as a guide. Saved commands are now order-aware (config version 4) so they’ll keep behaving even if you rename folders.

## Tech Stack

- Python 3.13
- PySide6 (Qt)
- psutil (metrics)
- pillow (icon alchemy)
- PyInstaller (for bundling the magic into one click)

## Roadmap / Possible Shenanigans

- [ ] Toast notifications when servers crash harder than you during finals.
- [ ] Multi-line saved command snippets for 200-line data pack installs.
- [ ] Remote monitoring agent that tattles on CPU spikes via Discord webhooks.

Got ideas? PRs with memes in the description get priority review.*

> \*Legally binding as long as you also fix a bug.

## Credits

- **Neo0oen** – Visionary, purple enthusiast, chaos coordinator.
- **Everyone else** – People who like not typing `java -Xms512M` a thousand times.

## License

TBD. Until then, assume “be nice and don’t sell it on eBay.”

---

“Buttons that work are cool, but buttons that work and look sassy? That’s culture.” – Someone, probably.
