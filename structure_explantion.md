# Project Structure Explanation

This document summarizes the GitHub-ready package contents and explains the purpose of each file.

## Top-Level Items

- `README.md` – overview of the project, feature highlights, and pointers to supporting docs.
- `BUILD.md` – reproducible steps for building the executable or running from source.
- `requirements.txt` – Python dependencies (`PySide6`, `psutil`) required at runtime.
- `.gitignore` – suggested Git exclusions for local builds and IDE files.
- `logo.ico` – transparent icon used by PyInstaller and the window/taskbar.
- `structure_explantion.md` – this document.

## Directories

- `src/` – Python source code.
  - `main.py` – entry point that launches the Qt app.
  - `main_window.py` – all UI tabs (Servers, Console, Monitoring) and global wiring.
  - `controller.py` – application state, persistence, saved command ordering, uptime tracking.
  - `dialogs.py` – dialogs for editing servers, saved commands (with order preservation), and settings.
  - `models.py` – dataclasses for servers, settings, saved commands (with `order`) and config serialization.
  - `process_manager.py` – spawns/stops server processes and forwards output.
  - `server_table_model.py` – Qt table model for the Servers tab.

- `assets/` – branding resources.
  - `logo.ico` – transparent icon (multi-size).
  - `logo.jpg` – original artwork source.

- `dist/` – distributable artifacts.
  - `velocity gui minecraft server manger.exe` – latest one-file Windows build.

- `tools/` – build helpers.
  - `build_exe.bat` – installs dependencies (including psutil) and runs PyInstaller with the correct options.
  - `velocity gui minecraft server manger.spec` – generated PyInstaller spec file.

- `config/` – configuration templates.
  - `example_server_launcher_config.json` – sanitized example (config version 4) showing servers, saved command ordering, and settings.

- `docs/` – user documentation.
  - `USAGE.md` – instructions for the Servers, Console, and Monitoring tabs, plus troubleshooting tips.

Feel free to expand these sections as the project evolves; update this file when structure changes occur.
