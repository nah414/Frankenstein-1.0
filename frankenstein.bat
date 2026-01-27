@echo off
REM ═══════════════════════════════════════════════════════════════
REM  FRANKENSTEIN 1.0 - Windows Launcher
REM  "It's alive... and ready to serve science."
REM ═══════════════════════════════════════════════════════════════

title FRANKENSTEIN 1.0

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Change to the project directory
cd /d "%SCRIPT_DIR%"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Launch FRANKENSTEIN
echo.
echo ⚡ Launching FRANKENSTEIN 1.0...
echo.
python frankenstein.py

REM Deactivate on exit
deactivate
