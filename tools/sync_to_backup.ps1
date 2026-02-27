# Frankenstein 1.0 - Sync LIVE to BACKUP
# Per deployment protocol: edit LIVE first, then sync to BACKUP

$live   = "C:\Users\adamn\Frankenstein-1.0"
$backup = "C:\Users\adamn\OneDrive\Desktop\Frankenstein_Terminal"

if (-not (Test-Path $backup)) {
    Write-Host "BACKUP directory not found: $backup" -ForegroundColor Red
    exit 1
}

Write-Host "Syncing LIVE to BACKUP..." -ForegroundColor Cyan
Write-Host "  FROM: $live" -ForegroundColor DarkGray
Write-Host "  TO:   $backup" -ForegroundColor DarkGray
Write-Host ""

# Use robocopy - mirrors LIVE to BACKUP, skips __pycache__
$result = & robocopy $live $backup /MIR /XD "__pycache__" ".git" /XF "*.pyc" "*.log" /NFL /NDL /NJH /NJS /NC /NS 2>&1
$exitCode = $LASTEXITCODE

# Robocopy exit codes: 0=no change, 1=files copied, 2=extra files, 3=both, 4+=errors
if ($exitCode -le 3) {
    Write-Host "SYNC COMPLETE (robocopy exit: $exitCode)" -ForegroundColor Green
} else {
    Write-Host "SYNC WARNING - robocopy exit code: $exitCode" -ForegroundColor Yellow
    Write-Host $result
}

# Verify key files exist in backup
$keyFiles = @(
    "agents\sauron\engine.py",
    "agents\sauron\prompts\system.txt",
    "configs\sauron_model.yaml",
    "widget\terminal.py",
    "RUN_FRANKENSTEIN.bat"
)

Write-Host ""
Write-Host "Verifying key files in BACKUP:" -ForegroundColor Yellow
foreach ($f in $keyFiles) {
    $path = Join-Path $backup $f
    if (Test-Path $path) {
        $liveTime   = (Get-Item (Join-Path $live $f)).LastWriteTime
        $backupTime = (Get-Item $path).LastWriteTime
        Write-Host ("  OK: " + $f) -ForegroundColor Green
    } else {
        Write-Host ("  MISSING: " + $f) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Deployment sync done." -ForegroundColor Cyan
