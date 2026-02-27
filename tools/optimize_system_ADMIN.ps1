# ============================================================
# FRANKENSTEIN 1.0 — SYSTEM OPTIMIZATION SCRIPT
# Run this: Right-click → "Run with PowerShell" (or Run as Admin)
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  FRANKENSTEIN 1.0 — SYSTEM OPTIMIZER" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── STEP 1: DISABLE SERVICES ────────────────────────────────
Write-Host "[1/5] Disabling RAM-hungry services..." -ForegroundColor Yellow

$services = @{
    'SysMain'   = 'Superfetch (preloads apps, kills low-RAM machines)'
    'WSearch'   = 'Windows Search Indexer (high RAM/disk overhead)'
    'DiagTrack' = 'Telemetry / Connected User Experiences (background CPU)'
    'Spooler'   = 'Print Spooler (no printer needed)'
}

foreach ($svc in $services.GetEnumerator()) {
    try {
        $s = Get-Service -Name $svc.Key -ErrorAction Stop
        if ($s.Status -eq 'Running') {
            Stop-Service -Name $svc.Key -Force -ErrorAction SilentlyContinue
        }
        Set-Service -Name $svc.Key -StartupType Disabled -ErrorAction Stop
        Write-Host "  DISABLED: $($svc.Key) — $($svc.Value)" -ForegroundColor Green
    } catch {
        # Fallback: sc.exe
        $r = & sc.exe config $svc.Key start= disabled 2>&1
        if ($r -match "SUCCESS") {
            Write-Host "  DISABLED (sc.exe): $($svc.Key)" -ForegroundColor Green
        } else {
            Write-Host "  SKIPPED (needs admin): $($svc.Key)" -ForegroundColor Red
        }
    }
}

# ── STEP 2: OLLAMA ENVIRONMENT VARIABLES ────────────────────
Write-Host ""
Write-Host "[2/5] Setting Ollama environment variables..." -ForegroundColor Yellow

$ollamaVars = @{
    'OLLAMA_MAX_LOADED_MODELS' = '1'
    'OLLAMA_NUM_PARALLEL'      = '1'
    'OLLAMA_KEEP_ALIVE'        = '300'
}

foreach ($var in $ollamaVars.GetEnumerator()) {
    [System.Environment]::SetEnvironmentVariable($var.Key, $var.Value, 'Machine')
    Write-Host "  SET (system): $($var.Key) = $($var.Value)" -ForegroundColor Green
}

# ── STEP 3: WINDOWS DEFENDER EXCLUSION ──────────────────────
Write-Host ""
Write-Host "[3/5] Adding Defender exclusion for Frankenstein..." -ForegroundColor Yellow

$frankPath = "C:\Users\adamn\Frankenstein-1.0"
try {
    Add-MpPreference -ExclusionPath $frankPath -ErrorAction Stop
    Write-Host "  EXCLUDED: $frankPath" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: Defender exclusion — $($_.Exception.Message)" -ForegroundColor Red
}

# ── STEP 4: PURGE __pycache__ ────────────────────────────────
Write-Host ""
Write-Host "[4/5] Purging __pycache__ from LIVE and BACKUP..." -ForegroundColor Yellow

$dirs = @(
    "C:\Users\adamn\Frankenstein-1.0",
    "C:\Users\adamn\OneDrive\Desktop\Frankenstein_Terminal"
)

$totalPurged = 0
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        $caches = Get-ChildItem -Path $dir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
        foreach ($cache in $caches) {
            try {
                Remove-Item -Path $cache.FullName -Recurse -Force -ErrorAction Stop
                Write-Host "  REMOVED: $($cache.FullName)" -ForegroundColor Green
                $totalPurged++
            } catch {
                Write-Host "  SKIPPED: $($cache.FullName)" -ForegroundColor DarkYellow
            }
        }
    }
}
Write-Host "  Total __pycache__ removed: $totalPurged" -ForegroundColor Green

# ── STEP 5: CLEAR LOGS, CACHE, TEMP ─────────────────────────
Write-Host ""
Write-Host "[5/5] Clearing logs, caches, and temp files..." -ForegroundColor Yellow

$cleanPaths = @(
    "$env:USERPROFILE\.frankenstein\logs",
    "$env:USERPROFILE\.frankenstein\synthesis_data\cache",
    "$env:LOCALAPPDATA\Temp",
    "C:\Windows\Temp"
)

foreach ($path in $cleanPaths) {
    if (Test-Path $path) {
        try {
            Get-ChildItem -Path $path -Recurse -ErrorAction SilentlyContinue |
                Where-Object { -not $_.PSIsContainer } |
                Remove-Item -Force -ErrorAction SilentlyContinue
            Write-Host "  CLEARED: $path" -ForegroundColor Green
        } catch {
            Write-Host "  PARTIAL: $path (some files in use, skipped)" -ForegroundColor DarkYellow
        }
    } else {
        Write-Host "  NOT FOUND (skipping): $path" -ForegroundColor DarkGray
    }
}

# ── SUMMARY ─────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OPTIMIZATION COMPLETE" -ForegroundColor Cyan
Write-Host "  REBOOT REQUIRED for service changes" -ForegroundColor Yellow
Write-Host "  and Ollama env vars to take full effect." -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to close"
