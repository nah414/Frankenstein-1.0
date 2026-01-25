@echo off
REM FRANKENSTEIN 1.0 - Automated Test Runner
REM Runs all tests with coverage reporting

echo ========================================
echo FRANKENSTEIN 1.0 - Test Runner
echo ========================================
echo.

REM Check if pytest is installed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo ERROR: pytest not installed
    echo Please run setup_env.bat first
    pause
    exit /b 1
)

REM Check for test mode argument
set TEST_MODE=%1
if "%TEST_MODE%"=="" set TEST_MODE=standard

echo Test Mode: %TEST_MODE%
echo.

if "%TEST_MODE%"=="quick" (
    echo Running quick tests (no coverage)...
    python -m pytest tests/ -v
) else if "%TEST_MODE%"=="coverage" (
    echo Running tests with coverage report...
    python -m pytest tests/ -v --cov=core --cov=quantum --cov=classical --cov=synthesis --cov=agents --cov=security --cov-report=html --cov-report=term
    echo.
    echo Coverage report generated: htmlcov/index.html
) else if "%TEST_MODE%"=="verbose" (
    echo Running tests with verbose output...
    python -m pytest tests/ -vv -s
) else if "%TEST_MODE%"=="unit" (
    echo Running unit tests only...
    python -m pytest tests/unit/ -v
) else (
    echo Running standard tests...
    python -m pytest tests/ -v --cov=core --cov-report=term
)

if errorlevel 1 (
    echo.
    echo ========================================
    echo TESTS FAILED
    echo ========================================
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo ALL TESTS PASSED
    echo ========================================
)

echo.
echo Test modes:
echo   run_tests.bat          - Standard tests with basic coverage
echo   run_tests.bat quick    - Quick tests, no coverage
echo   run_tests.bat coverage - Full coverage report (HTML + terminal)
echo   run_tests.bat verbose  - Verbose output with print statements
echo   run_tests.bat unit     - Unit tests only
echo.
pause
