@echo off
REM Creates a desktop shortcut to launch FRANKENSTEIN 1.0

echo Creating FRANKENSTEIN 1.0 desktop shortcut...

set SCRIPT_DIR=%~dp0
set SHORTCUT_NAME=FRANKENSTEIN 1.0.lnk
set TARGET=%SCRIPT_DIR%install_and_run.bat
set DESKTOP=%USERPROFILE%\Desktop

REM Create VBS script to make shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%DESKTOP%\%SHORTCUT_NAME%" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%TARGET%" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> CreateShortcut.vbs
echo oLink.Description = "FRANKENSTEIN 1.0 - Quantum-Classical Hybrid AI System" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

REM Run the VBS script
cscript //nologo CreateShortcut.vbs

REM Clean up
del CreateShortcut.vbs

echo.
echo ✓ Desktop shortcut created!
echo.
echo You can now launch FRANKENSTEIN 1.0 from:
echo   %DESKTOP%\%SHORTCUT_NAME%
echo.
pause
