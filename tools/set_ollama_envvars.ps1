# Frankenstein 1.0 — Set Ollama Environment Variables (User-level, no admin needed)

Write-Host "=== SETTING OLLAMA ENV VARS ===" -ForegroundColor Cyan

$vars = @{
    'OLLAMA_MAX_LOADED_MODELS' = '1'    # Only keep 1 model loaded at a time — prevents RAM spike
    'OLLAMA_NUM_PARALLEL'      = '1'    # Only 1 request at a time — reduces VRAM/RAM usage
    'OLLAMA_KEEP_ALIVE'        = '300'  # Unload model after 5 min idle (not 30 min default)
}

foreach ($var in $vars.GetEnumerator()) {
    # Set for current user (no admin needed)
    [System.Environment]::SetEnvironmentVariable($var.Key, $var.Value, 'User')
    # Also set for current session
    [System.Environment]::SetEnvironmentVariable($var.Key, $var.Value, 'Process')
    Write-Host "SET: $($var.Key) = $($var.Value)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Verifying..." -ForegroundColor Yellow
foreach ($var in $vars.GetEnumerator()) {
    $val = [System.Environment]::GetEnvironmentVariable($var.Key, 'User')
    Write-Host "  CONFIRMED: $($var.Key) = $val" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== OLLAMA ENV VARS SET ===" -ForegroundColor Cyan
Write-Host "NOTE: Restart Ollama service for changes to take effect." -ForegroundColor Yellow
