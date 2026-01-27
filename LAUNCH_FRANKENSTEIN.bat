@echo off
REM FRANKENSTEIN 1.0 - Interactive System Launcher
REM Choose your launch mode
REM
REM Location: Root directory (for easy access)
REM See: GETTING_STARTED.md for usage instructions

echo.
echo    ⚡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━⚡
echo.
echo         ███████╗██████╗  █████╗ ███╗   ██╗██╗  ██╗
echo         ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝
echo         █████╗  ██████╔╝███████║██╔██╗ ██║█████╔╝
echo         ██╔══╝  ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗
echo         ██║     ██║  ██║██║  ██║██║ ╚████║██║  ██╗
echo         ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
echo.
echo              FRANKENSTEIN 1.0 - System Launcher
echo           Quantum-Classical Hybrid AI System
echo.
echo    ⚡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━⚡
echo.

REM Check if dependencies are installed
echo [Checking dependencies...]
python -c "import psutil" 2>nul
if errorlevel 1 (
    echo.
    echo ⚠️  Missing dependencies detected!
    echo.
    echo Would you like to install dependencies now?
    set /p install="Install now? (y/n): "
    if /i "%install%"=="y" (
        echo.
        echo Installing dependencies...
        python -m pip install -r requirements.txt
        if errorlevel 1 (
            echo.
            echo ❌ Installation failed!
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo Please run: setup_env.bat
        pause
        exit /b 1
    )
)

python -c "import customtkinter" 2>nul
if errorlevel 1 (
    echo.
    echo ⚠️  customtkinter not installed (required for widget display)
    echo.
    set /p install_ctk="Install customtkinter for widget? (y/n): "
    if /i "%install_ctk%"=="y" (
        echo Installing customtkinter...
        python -m pip install customtkinter
    ) else (
        echo.
        echo Widget will not be available. Continue in console mode.
        timeout /t 2 >nul
    )
)

echo.
echo ✓ Dependencies verified
echo.

REM Launch options
echo ════════════════════════════════════════════════════════
echo Choose launch mode:
echo ════════════════════════════════════════════════════════
echo.
echo   1. 🎮 Widget Mode (Always-on-top window with live stats)
echo   2. 💻 Interactive Mode (Console interface)
echo   3. 📊 Status Check (View system status and exit)
echo   4. 🧪 System Test (Quick functionality test)
echo.
set /p mode="Enter choice (1-4): "

echo.
echo ════════════════════════════════════════════════════════
echo.

if "%mode%"=="1" (
    echo Starting FRANKENSTEIN with Widget Display...
    echo.
    echo The widget window will appear on screen (always-on-top)
    echo Press Ctrl+C in this console to shutdown
    echo.
    python frankenstein.py --widget
) else if "%mode%"=="2" (
    echo Starting FRANKENSTEIN in Interactive Mode...
    echo.
    python frankenstein.py
) else if "%mode%"=="3" (
    echo Checking FRANKENSTEIN Status...
    echo.
    python frankenstein.py --status
) else if "%mode%"=="4" (
    echo Running System Test...
    echo.
    python frankenstein.py --test
) else (
    echo Invalid choice. Starting in Interactive Mode...
    echo.
    timeout /t 2 >nul
    python frankenstein.py
)

echo.
echo.
echo ════════════════════════════════════════════════════════
echo FRANKENSTEIN 1.0 - Session Complete
echo ════════════════════════════════════════════════════════
echo.
pause
