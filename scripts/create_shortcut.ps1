# FRANKENSTEIN 1.0 - Create Desktop Shortcut
# Run with: powershell -ExecutionPolicy Bypass -File create_shortcut.ps1

$ErrorActionPreference = "SilentlyContinue"

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "FRANKENSTEIN 1.0.lnk"

Write-Host ""
Write-Host "Creating FRANKENSTEIN 1.0 desktop shortcut..." -ForegroundColor Cyan
Write-Host "  Project: $ProjectDir"
Write-Host "  Desktop: $DesktopPath"
Write-Host ""

try {
    # Create shortcut
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    
    # Target the batch file
    $TargetPath = Join-Path $ProjectDir "FRANKENSTEIN.bat"
    if (-not (Test-Path $TargetPath)) {
        Write-Host "[ERROR] FRANKENSTEIN.bat not found at: $TargetPath" -ForegroundColor Red
        exit 1
    }
    
    $Shortcut.TargetPath = $TargetPath
    $Shortcut.WorkingDirectory = $ProjectDir
    $Shortcut.Description = "FRANKENSTEIN 1.0 - Quantum-Classical Hybrid AI System"
    $Shortcut.WindowStyle = 1  # Normal window
    
    # Set icon if exists
    $IconPath = Join-Path $ProjectDir "assets\frankenstein.ico"
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = "$IconPath,0"
        Write-Host "  Icon: Using monster icon" -ForegroundColor Green
    } else {
        Write-Host "  Icon: Using default (icon file not found)" -ForegroundColor Yellow
    }
    
    # Save shortcut
    $Shortcut.Save()
    
    # Verify
    if (Test-Path $ShortcutPath) {
        Write-Host ""
        Write-Host "[OK] Desktop shortcut created successfully!" -ForegroundColor Green
        Write-Host "     Location: $ShortcutPath"
        Write-Host ""
    } else {
        Write-Host "[WARN] Shortcut file not found after save" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to create shortcut: $_" -ForegroundColor Red
    exit 1
}
