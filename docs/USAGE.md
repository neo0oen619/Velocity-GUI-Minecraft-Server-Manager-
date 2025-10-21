# Using Velocity GUI Minecraft Server Manager

## Launching

- **Packaged build**: run `dist/velocity gui minecraft server manger.exe`.
- **From source**: `python src/main.py` (after installing dependencies).

The app loads `server_launcher_config.json` from the working directory. If the file is absent, it starts with an empty configuration.

## Servers Tab

- Displays configured servers with type, status, PID, RAM, and quick actions.
- Start/Stop/Force Stop control the selected server; file buttons open `server.properties`, `whitelist.json`, or the server folder.
- The details panel now includes a live **Uptime** timer that refreshes every second while the server is running.

## Console Tab

- **Filter field**: type to narrow the displayed log lines; a badge shows matches vs total lines.
- **Auto-scroll toggle**: enabled by default. When off, new log lines no longer yank the viewport while you scroll.
- **Pause/Resume**: freezes updates but buffers incoming lines so you can resume without losing data.
- **Save Log**: exports the current buffer to `logs/<server>_<timestamp>/console.log`.
- **Saved commands**:
  - Organized as a tree; use `/` in the category to create nested folders.
  - Items are numbered within each category and include hover tooltips.
  - Drag and drop commands to reorder or move between categories; order is persisted automatically.
  - Buttons: **Add**, **Edit**, **Remove**, **Copy**, **Send**. Double-click sends the command immediately.

## Monitoring Tab

- Shows system metrics (CPU, RAM, swap, disk) and per-server status.
- Each server row displays status, PID, uptime, CPU %, and memory usage (RSS) for the running process.
- Metrics refresh every 2 seconds; rows update automatically as servers start or stop.

## Credits

A purple footer note (“made with <3 by neo0oen”) stays anchored in the main window per branding requirements.

## Configuration Tips

- Use `config/example_server_launcher_config.json` as a reference when creating your own config. Version 4 adds the `order` field for saved commands.
- Saved commands and ordering persist alongside server definitions in `server_launcher_config.json`.
- Ensure server paths and custom executables are accessible from the machine running the launcher.

## Troubleshooting

- **Missing psutil/PySide6**: reinstall dependencies with `pip install -r requirements.txt`.
- **No console output**: only Java-based servers stream console logs; check each server’s `launch_type`.
- **Playit agent**: use the Tools menu to add or launch the Playit entry automatically.
