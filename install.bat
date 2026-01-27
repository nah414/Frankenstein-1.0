@echo off
REM ═══════════════════════════════════════════════════════════════
REM FRANKENSTEIN 1.0 - One-Click Installer
REM Installs dependencies, creates desktop shortcut, and launches
REM ═══════════════════════════════════════════════════════════════

title FRANKENSTEIN 1.0 - Installer

cd /d "%~dp0"
chcp 65001 > nul 2>&1

echo.
echo  ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗
echo  ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝
echo  █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝
echo  ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗
echo  ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗
echo  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
echo.
echo  FRANKENSTEIN 1.0 - One-Click Installer
echo  ═══════════════════════════════════════════════════════════════
echo.

REM Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo       [ERROR] Python not found!
    echo       Please install Python 3.9+ from python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo       Python %%i found

REM Install dependencies
echo.
echo [2/5] Installing dependencies...
python -m pip install --upgrade pip --quiet 2>nul
python -m pip install psutil pyyaml customtkinter pillow --quiet
if errorlevel 1 (
    echo       [WARN] Some dependencies may not have installed correctly
) else (
    echo       Dependencies installed
)

REM Create/verify icon
echo.
echo [3/5] Creating monster icon...
if exist "assets\frankenstein.ico" (
    echo       Icon already exists
) else (
    python scripts\create_icon.py
)

REM Create desktop shortcut
echo.
echo [4/5] Creating desktop shortcut...
powershell -ExecutionPolicy Bypass -File "scripts\create_shortcut.ps1" >nul 2>&1
if errorlevel 1 (
    echo       [WARN] Could not create shortcut automatically
    echo       Run: scripts\create_shortcut.ps1
) else (
    echo       Desktop shortcut created!
)

echo.
echo [5/5] Installation complete!
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo  FRANKENSTEIN 1.0 is now installed!
echo.
echo  To launch:
echo    - Double-click "FRANKENSTEIN 1.0" on your desktop
echo    - Or run: FRANKENSTEIN.bat
echo    - Or run: python frankenstein.py
echo.
echo  Commands:
echo    --console    Console mode (no GUI)
echo    --status     Show system status
echo    --test       Run system test
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

set /p launch="Launch FRANKENSTEIN now? (Y/n): "
if /i not "%launch%"=="n" (
    echo.
    echo Launching FRANKENSTEIN...
    python frankenstein.py
)

pause
