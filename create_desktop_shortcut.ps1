# ═══════════════════════════════════════════════════════════════
#  FRANKENSTEIN 1.0 - Desktop Shortcut Creator
#  Creates a desktop shortcut with monster emoji icon
# ═══════════════════════════════════════════════════════════════

param(
    [string]$ProjectPath = (Get-Location).Path
)

Write-Host ""
Write-Host "⚡ FRANKENSTEIN Desktop Shortcut Creator" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Get paths
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "FRANKENSTEIN.lnk"
$LauncherPath = Join-Path $ProjectPath "frankenstein.bat"
$IconPath = Join-Path $ProjectPath "assets\frankenstein.ico"

# Check if launcher exists
if (-not (Test-Path $LauncherPath)) {
    Write-Host "ERROR: frankenstein.bat not found at $LauncherPath" -ForegroundColor Red
    Write-Host "Make sure you're running this from the project directory." -ForegroundColor Yellow
    exit 1
}

# Create assets directory if it doesn't exist
$AssetsDir = Join-Path $ProjectPath "assets"
if (-not (Test-Path $AssetsDir)) {
    New-Item -ItemType Directory -Path $AssetsDir -Force | Out-Null
    Write-Host "Created assets directory" -ForegroundColor Cyan
}

# Check for icon, generate if needed
if (-not (Test-Path $IconPath)) {
    Write-Host "Generating monster icon..." -ForegroundColor Cyan
    
    # Try to run the icon generator Python script
    $IconGenScript = Join-Path $ProjectPath "scripts\generate_icon.py"
    if (Test-Path $IconGenScript) {
        python $IconGenScript
    } else {
        Write-Host "Icon generator not found. Using default icon." -ForegroundColor Yellow
        $IconPath = $null  # Will use default
    }
}

# Create the shortcut
Write-Host "Creating desktop shortcut..." -ForegroundColor Cyan

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LauncherPath
$Shortcut.WorkingDirectory = $ProjectPath
$Shortcut.Description = "FRANKENSTEIN 1.0 - Physics-Grounded AI Assistant"
$Shortcut.WindowStyle = 1  # Normal window

# Set icon if available
if ($IconPath -and (Test-Path $IconPath)) {
    $Shortcut.IconLocation = "$IconPath,0"
    Write-Host "Using custom monster icon" -ForegroundColor Green
} else {
    # Use a built-in Windows icon as fallback (lightning bolt style)
    $Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,76"
    Write-Host "Using system icon (custom icon not found)" -ForegroundColor Yellow
}

$Shortcut.Save()

Write-Host ""
Write-Host "✅ Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "   Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click 'FRANKENSTEIN' on your desktop to launch!" -ForegroundColor Green
Write-Host ""
