# Frankenstein 1.0 - Service Disabling + Defender Exclusion (REQUIRES ADMIN)
# Self-elevates via UAC if not already running as admin.

$currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Not admin - requesting UAC elevation..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList ('-ExecutionPolicy Bypass -File "' + $PSCommandPath + '"') -Verb RunAs
    exit
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ELEVATED: Services + Defender Exclusion" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --- DISABLE SERVICES ---
Write-Host ""
Write-Host "[1/2] Disabling services..." -ForegroundColor Yellow

$serviceList = @("SysMain", "WSearch", "DiagTrack", "Spooler")

foreach ($svcName in $serviceList) {
    try {
        $s = Get-Service -Name $svcName -ErrorAction Stop
        if ($s.Status -eq "Running") {
            Stop-Service -Name $svcName -Force -ErrorAction SilentlyContinue
            Write-Host ("  STOPPED: " + $svcName) -ForegroundColor DarkYellow
        }
        Set-Service -Name $svcName -StartupType Disabled -ErrorAction Stop
        Write-Host ("  DISABLED: " + $svcName) -ForegroundColor Green
    } catch {
        $r = & sc.exe config $svcName start= disabled 2>&1
        if ($r -match "SUCCESS") {
            Write-Host ("  DISABLED via sc.exe: " + $svcName) -ForegroundColor Green
        } else {
            Write-Host ("  FAILED: " + $svcName + " - " + $_.Exception.Message) -ForegroundColor Red
        }
    }
}

# --- WINDOWS DEFENDER EXCLUSIONS ---
Write-Host ""
Write-Host "[2/2] Adding Defender exclusions..." -ForegroundColor Yellow

$exclusions = @(
    "C:\Users\adamn\Frankenstein-1.0",
    "$env:USERPROFILE\.ollama"
)

foreach ($excPath in $exclusions) {
    try {
        Add-MpPreference -ExclusionPath $excPath -ErrorAction Stop
        Write-Host ("  EXCLUDED: " + $excPath) -ForegroundColor Green
    } catch {
        Write-Host ("  FAILED: " + $excPath + " - " + $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DONE - REBOOT to finalize service changes" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close"
