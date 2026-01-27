@echo off
REM FRANKENSTEIN 1.0 - Test Runner
REM Runs automated tests with coverage reporting
REM =====================================================

title FRANKENSTEIN 1.0 - Test Runner

cd /d "%~dp0.."

REM Check if pytest is installed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo [*] Installing pytest...
    python -m pip install pytest pytest-cov --quiet
)

set TEST_MODE=%1
if "%TEST_MODE%"=="" set TEST_MODE=standard

echo.
echo ============================================
echo   FRANKENSTEIN 1.0 - Test Runner
echo   Mode: %TEST_MODE%
echo ============================================
echo.

if "%TEST_MODE%"=="quick" (
    echo Running quick tests...
    python -m pytest tests/ -v
) else if "%TEST_MODE%"=="coverage" (
    echo Running tests with full coverage...
    python -m pytest tests/ -v --cov=core --cov-report=html --cov-report=term
    echo.
    echo Coverage report: htmlcov\index.html
) else if "%TEST_MODE%"=="verbose" (
    echo Running verbose tests...
    python -m pytest tests/ -vv -s
) else if "%TEST_MODE%"=="unit" (
    echo Running unit tests only...
    python -m pytest tests/unit/ -v
) else (
    echo Running standard tests...
    python -m pytest tests/ -v --cov=core --cov-report=term
)

echo.
if errorlevel 1 (
    echo [FAIL] Some tests failed!
) else (
    echo [PASS] All tests passed!
)

echo.
echo Test modes:
echo   run_tests.bat          - Standard tests
echo   run_tests.bat quick    - Quick (no coverage)
echo   run_tests.bat coverage - Full coverage report
echo   run_tests.bat verbose  - Verbose output
echo   run_tests.bat unit     - Unit tests only
echo.
pause
