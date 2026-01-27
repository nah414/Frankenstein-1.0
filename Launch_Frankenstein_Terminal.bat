@echo off
REM ==============================================
REM FRANKENSTEIN 1.0 - Clean Terminal Launcher
REM ==============================================
REM This launcher ensures no cached bytecode interferes

echo.
echo ==================================================
echo   FRANKENSTEIN 1.0 - Terminal Launcher
echo ==================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Clear Python bytecode cache to ensure fresh code runs
echo Clearing Python cache...
if exist "widget\__pycache__" rmdir /s /q "widget\__pycache__" 2>nul
if exist "__pycache__" rmdir /s /q "__pycache__" 2>nul
echo Done.
echo.

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)

REM Check for customtkinter
echo Checking for customtkinter...
python -c "import customtkinter" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo customtkinter not found. Installing...
    pip install customtkinter
    echo.
)

REM Show Python version
python --version
echo.

REM Launch the terminal with no optimization (forces recompile)
echo Launching Frankenstein Terminal...
echo.
python -B launch_terminal.py

REM Keep window open if there was an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Terminal exited with error code %ERRORLEVEL%
    pause
)
