@echo off
REM FRANKENSTEIN 1.0 - Desktop Shortcut Creator (PowerShell version)
REM Creates a desktop shortcut with monster icon
REM =====================================================

echo.
echo ============================================
echo   FRANKENSTEIN 1.0 - Desktop Shortcut Setup
echo ============================================
echo.

REM Get paths
set "PROJECT_DIR=%~dp0.."
for %%i in ("%PROJECT_DIR%") do set "PROJECT_DIR=%%~fi"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=FRANKENSTEIN 1.0"

echo Project Directory: %PROJECT_DIR%
echo Desktop: %DESKTOP%
echo.

REM Create the icon first
echo [1/3] Creating monster icon...
python "%PROJECT_DIR%\scripts\create_icon.py"
if errorlevel 1 (
    echo [WARN] Could not create custom icon, using default
)

REM Create shortcut using PowerShell
echo [2/3] Creating desktop shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%.lnk'); $s.TargetPath = '%PROJECT_DIR%\FRANKENSTEIN.bat'; $s.WorkingDirectory = '%PROJECT_DIR%'; $s.Description = 'FRANKENSTEIN 1.0 - Monster Terminal AI System'; $s.IconLocation = '%PROJECT_DIR%\assets\frankenstein.ico,0'; $s.Save()"

echo [3/3] Verifying shortcut...
if exist "%DESKTOP%\%SHORTCUT_NAME%.lnk" (
    echo.
    echo ============================================
    echo   SUCCESS! Desktop shortcut created!
    echo ============================================
    echo.
    echo   Location: %DESKTOP%\%SHORTCUT_NAME%.lnk
    echo.
    echo   Double-click the shortcut to launch
    echo   FRANKENSTEIN terminal!
    echo.
) else (
    echo [ERROR] Failed to create shortcut via PowerShell
    echo Trying alternate method...
    
    REM Fallback: create a simple .bat link file on desktop
    echo @echo off > "%DESKTOP%\%SHORTCUT_NAME%.bat"
    echo cd /d "%PROJECT_DIR%" >> "%DESKTOP%\%SHORTCUT_NAME%.bat"
    echo start "" "%PROJECT_DIR%\FRANKENSTEIN.bat" >> "%DESKTOP%\%SHORTCUT_NAME%.bat"
    
    if exist "%DESKTOP%\%SHORTCUT_NAME%.bat" (
        echo [OK] Created batch file launcher instead
        echo Location: %DESKTOP%\%SHORTCUT_NAME%.bat
    ) else (
        echo [ERROR] All methods failed. Please create shortcut manually.
    )
)

pause
