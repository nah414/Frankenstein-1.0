# Frankenstein 1.0 — Cache & Log Cleanup (no admin needed)

Write-Host "=== FRANKENSTEIN CACHE CLEANUP ===" -ForegroundColor Cyan

# Frankenstein logs
$paths = @(
    "$env:USERPROFILE\.frankenstein\logs",
    "$env:USERPROFILE\.frankenstein\synthesis_data\cache"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $files = Get-ChildItem -Path $p -Recurse -File -ErrorAction SilentlyContinue
        $count = 0
        foreach ($f in $files) {
            try { Remove-Item $f.FullName -Force -ErrorAction Stop; $count++ } catch {}
        }
        Write-Host "CLEARED $count file(s): $p" -ForegroundColor Green
    } else {
        Write-Host "NOT FOUND (already clean): $p" -ForegroundColor DarkGray
    }
}

# User TEMP
Write-Host "Clearing user TEMP..." -ForegroundColor Yellow
$tempPath = $env:TEMP
$cleared = 0
$skipped = 0
Get-ChildItem -Path $tempPath -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction Stop
        $cleared++
    } catch {
        $skipped++
    }
}
Write-Host "TEMP: $cleared items cleared | $skipped skipped (in-use)" -ForegroundColor Green

# Ollama logs (not models)
$ollamaLogs = "$env:LOCALAPPDATA\Ollama\logs"
if (Test-Path $ollamaLogs) {
    Get-ChildItem $ollamaLogs -File -ErrorAction SilentlyContinue |
        ForEach-Object { try { Remove-Item $_.FullName -Force } catch {} }
    Write-Host "Ollama logs cleared: $ollamaLogs" -ForegroundColor Green
} else {
    Write-Host "Ollama logs not found (clean): $ollamaLogs" -ForegroundColor DarkGray
}

# Windows Update download cache
$wuCache = "C:\Windows\SoftwareDistribution\Download"
if (Test-Path $wuCache) {
    $wuCount = 0
    Get-ChildItem -Path $wuCache -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        try { Remove-Item $_.FullName -Force -ErrorAction Stop; $wuCount++ } catch {}
    }
    Write-Host "Windows Update cache: $wuCount files cleared" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== CACHE CLEANUP COMPLETE ===" -ForegroundColor Cyan
