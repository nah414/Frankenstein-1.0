@echo off
REM FRANKENSTEIN 1.0 - GitHub Push Script
REM Run this after creating the repository on GitHub

echo ========================================
echo   FRANKENSTEIN 1.0 - GitHub Push
echo ========================================
echo.

cd /d "%~dp0"

echo Current directory: %CD%
echo.

REM Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo Step 1: Adding GitHub remote...
git remote add origin https://github.com/nah414/frankenstein-1.0.git 2>nul
if errorlevel 1 (
    echo Remote 'origin' already exists, updating URL...
    git remote set-url origin https://github.com/nah414/frankenstein-1.0.git
)

echo Step 2: Renaming branch to 'main'...
git branch -M main

echo Step 3: Pushing to GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Push failed!
    echo ========================================
    echo.
    echo Possible reasons:
    echo 1. Repository not created on GitHub yet
    echo    Create it at: https://github.com/new
    echo 2. Authentication required
    echo    Configure Git credentials or use GitHub CLI
    echo 3. Permission denied
    echo    Make sure you're logged in to the correct account
    echo.
    echo See SETUP_GITHUB.md for detailed instructions
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Repository pushed to GitHub
echo ========================================
echo.
echo Your repository is now available at:
echo https://github.com/nah414/frankenstein-1.0
echo.
echo Next steps:
echo - Visit the repository URL above
echo - Add repository topics: quantum-computing, ai, python
echo - Review the README.md
echo.
pause
