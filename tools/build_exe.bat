@echo off
setlocal

if "%~1"=="" (
    set OUTPUT_NAME=velocity gui minecraft server manger
) else (
    set OUTPUT_NAME=%~1
)

echo Installing build dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install --disable-pip-version-check -r requirements.txt pyinstaller >nul

if exist build rd /s /q build
if exist dist rd /s /q dist
if exist "%OUTPUT_NAME%.spec" del "%OUTPUT_NAME%.spec"

echo Building executable...
pyinstaller --clean --onefile --name "%OUTPUT_NAME%" --icon logo.ico main.py

if exist "dist\%OUTPUT_NAME%.exe" (
    echo Done. Find the executable at dist\%OUTPUT_NAME%.exe
) else (
    echo Build failed. Check the PyInstaller output for details.
)

endlocal
