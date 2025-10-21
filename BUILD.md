# Build Instructions

A pre-built executable ships in `dist/`, but you can rebuild or run from source with the steps below.

## Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.12+ (tested with 3.13.7)
- Pip (bundled with Python)
- git (optional, for cloning)

## Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pillow
```

`psutil` (for monitoring) and `PySide6` are pulled from `requirements.txt`; `pillow` is used to regenerate the transparent `logo.ico` if needed.

## Build the Executable

Run the helper script from the repository root:

```powershell
./tools/build_exe.bat
```

The script cleans previous build artifacts and runs PyInstaller with the correct name and icon. The resulting binary appears at:

```
dist/velocity gui minecraft server manger.exe
```

## Run from Source

After installing dependencies:

```powershell
python src/main.py
```

Configuration is loaded from `server_launcher_config.json` in the working directory. Saved commands and settings persist there between sessions.
