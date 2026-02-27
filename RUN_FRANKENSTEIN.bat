@echo off
REM FRANKENSTEIN 1.0 - Monster Terminal Launcher

REM ── Self-relaunch hidden so no cmd.exe window is visible ────────────────────
REM    Must use cmd.exe explicitly — Start-Process cannot run .bat files directly
REM    python.exe (not pythonw) must inherit this hidden console so CTk stays alive
if not "%1"=="hidden" (
    PowerShell -WindowStyle Hidden -Command "Start-Process cmd.exe -ArgumentList '/c %~f0 hidden' -WindowStyle Hidden"
    exit /b
)

cd /d "%~dp0"

REM ── Ollama clean-slate: kill stale instances and restart fresh (hidden) ──────
REM Prevents leftover model memory (~4.6 GB) from blocking frank chat on relaunch
REM    %LOCALAPPDATA% is expanded by cmd.exe before PowerShell sees the string
taskkill /F /IM ollama.exe >nul 2>&1
timeout /t 2 /nobreak >nul
PowerShell -WindowStyle Hidden -Command "Start-Process '%LOCALAPPDATA%\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden"
timeout /t 3 /nobreak >nul

REM ── Launch Monster Terminal ──────────────────────────────────────────────────
REM    Run python directly (no 'start ""') so it inherits this hidden console.
REM    The hidden console keeps python.exe alive and gives CTk's daemon thread
REM    a proper Windows message context — without it the window closes instantly.
python launch_terminal.py
