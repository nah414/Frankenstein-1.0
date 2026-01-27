@echo off
REM FRANKENSTEIN 1.0 - Automated Environment Setup
REM Target: Windows 10/11, Python 3.9+

echo ========================================
echo FRANKENSTEIN 1.0 - Environment Setup
echo ========================================
echo.

REM Check Python version
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9 or higher.
    pause
    exit /b 1
)
python --version
echo.

REM Check pip
echo [2/5] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found. Installing pip...
    python -m ensurepip --upgrade
)
echo.

REM Upgrade pip
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo [4/5] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Install development dependencies
echo [5/5] Installing development dependencies (testing tools)...
python -m pip install pytest pytest-cov black mypy
if errorlevel 1 (
    echo WARNING: Failed to install some dev dependencies
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   - Run tests: run_tests.bat
echo   - Start FRANKENSTEIN: python frankenstein.py
echo   - Start with widget: python frankenstein.py --widget
echo.
pause
