@echo off
REM ═══════════════════════════════════════════════════════════════
REM FRANKENSTEIN 1.0 - Monster Terminal Launcher
REM Double-click to launch the FRANKENSTEIN terminal GUI
REM ═══════════════════════════════════════════════════════════════

title FRANKENSTEIN 1.0 - Monster Terminal

REM Navigate to project directory
cd /d "%~dp0"

REM Set UTF-8 encoding for proper character display
chcp 65001 > nul 2>&1

REM Check if Python exists
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.9+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check for customtkinter (required for GUI)
python -c "import customtkinter" 2>nul
if errorlevel 1 (
    echo.
    echo [*] Installing GUI dependencies...
    echo.
    python -m pip install customtkinter --quiet
    if errorlevel 1 (
        echo [ERROR] Failed to install customtkinter
        echo         Launching in console mode instead...
        echo.
        python frankenstein.py --console
        goto :end
    )
)

REM Check for other dependencies
python -c "import psutil" 2>nul
if errorlevel 1 (
    echo [*] Installing psutil...
    python -m pip install psutil --quiet
)

python -c "import yaml" 2>nul
if errorlevel 1 (
    echo [*] Installing pyyaml...
    python -m pip install pyyaml --quiet
)

REM Clear screen and launch
cls
python frankenstein.py

:end
REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo ═══════════════════════════════════════════════════════════════
    echo [ERROR] FRANKENSTEIN exited with an error.
    echo ═══════════════════════════════════════════════════════════════
    echo.
    echo Possible solutions:
    echo   1. Run: pip install customtkinter psutil pyyaml
    echo   2. Try console mode: python frankenstein.py --console
    echo   3. Check Python installation
    echo.
    pause
)
