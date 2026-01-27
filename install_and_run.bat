@echo off
REM FRANKENSTEIN 1.0 - One-Click Install and Run
REM Installs everything and launches with widget
REM
REM Location: Root directory (for easy access)
REM See: GETTING_STARTED.md for usage instructions

echo.
echo ⚡ FRANKENSTEIN 1.0 - Quick Install and Launch ⚡
echo.

REM Step 1: Install dependencies
echo [1/3] Installing dependencies...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

if errorlevel 1 (
    echo ❌ Installation failed!
    pause
    exit /b 1
)

echo ✓ Core dependencies installed

REM Step 2: Install customtkinter for widget
echo [2/3] Installing widget support...
python -m pip install customtkinter -q

if errorlevel 1 (
    echo ⚠️  Widget installation failed, continuing without widget
) else (
    echo ✓ Widget support installed
)

REM Step 3: Launch FRANKENSTEIN with widget
echo [3/3] Launching FRANKENSTEIN 1.0...
echo.
echo ════════════════════════════════════════════════════════
echo The widget window will appear shortly!
echo Press Ctrl+C to shutdown when done
echo ════════════════════════════════════════════════════════
echo.

timeout /t 2 >nul

python frankenstein.py --widget

echo.
pause
