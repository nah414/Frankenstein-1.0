# FRANKENSTEIN 1.0 - Low Memory Mode

## Overview

Low Memory Mode is an automatic resource conservation system that dramatically reduces CPU and RAM usage when your system is under pressure. It automatically detects memory conditions and adjusts features accordingly.

## Modes

| Mode | RAM Threshold | Description |
|------|---------------|-------------|
| **NORMAL** | < 60% | Full features, standard polling |
| **CONSERVATIVE** | 60-70% | Reduced features, slower polling |
| **LOW_MEMORY** | 70-80% | Minimal features, very slow polling |
| **CRITICAL** | > 80% | Survival mode - bare minimum |

## Commands

```bash
lowmem              # Show current mode and status
lowmem status       # Detailed status with recommendations
lowmem normal       # Switch to normal mode (manual)
lowmem conservative # Switch to conservative mode
lowmem low          # Switch to low memory mode
lowmem critical     # Switch to critical/survival mode
lowmem auto         # Re-enable automatic detection
```

## Mode Settings Comparison

| Setting | NORMAL | CONSERVATIVE | LOW_MEMORY | CRITICAL |
|---------|--------|--------------|------------|----------|
| Resource Poll | 4s | 8s | 15s | 30s |
| UI Update | 5s | 8s | 15s | 30s |
| Security Monitor | YES | YES | NO | NO |
| Hardware Monitor | YES | YES | NO | NO |
| Agent Scheduler | YES | YES | NO | NO |
| Synthesis Engine | YES | YES | YES | NO |
| Quantum Mode | YES | YES | YES | NO |
| Auto Visualization | YES | NO | NO | NO |
| Max History | 100 | 50 | 25 | 10 |
| Max Output Lines | 10000 | 5000 | 2000 | 500 |
| Cache TTL | 1s | 2s | 5s | 10s |
| Live Monitor Panel | YES | YES | YES | NO |

## Automatic Detection

The system automatically switches modes based on:

1. **Percentage of RAM used**
   - < 60% = NORMAL
   - 60-70% = CONSERVATIVE
   - 70-80% = LOW_MEMORY
   - > 80% = CRITICAL

2. **Free RAM available**
   - > 3 GB = NORMAL
   - 2-3 GB = CONSERVATIVE
   - 1-2 GB = LOW_MEMORY
   - < 1 GB = CRITICAL

The more conservative threshold wins.

## Manual Override

You can manually set a mode:

```bash
lowmem low          # Force low memory mode
lowmem critical     # Force critical mode
```

To return to automatic detection:

```bash
lowmem auto
```

## Integration with Other Features

### With Resource Manager
- Low Memory Mode adjusts the base polling intervals
- Resource Manager still provides adaptive speedup during alerts

### With Security Monitor  
- Security is disabled in LOW_MEMORY and CRITICAL modes
- Use `resources start` to manually enable if needed

### With Terminal UI
- Monitor panel is hidden in CRITICAL mode
- UI updates slow to 30 seconds in CRITICAL mode

## Recommendations

When in LOW_MEMORY or CRITICAL mode, the system provides recommendations:

**CRITICAL mode:**
- Close Claude Desktop app (using ~1.6GB RAM)
- Close unused browser tabs
- Disable Windows Search indexing temporarily
- Consider restarting your computer

**LOW_MEMORY mode:**
- Close unnecessary applications
- Use 'resources stop' to disable security monitor
- Avoid running synthesis/quantum simulations

## Startup Check

The system checks memory at startup:

- **< 500MB free**: Won't start, shows critical warning
- **< 1GB free**: Starts in LOW_MEMORY mode with warning
- **< 2GB free**: Starts in CONSERVATIVE mode with note
- **> 2GB free**: Starts normally

## Testing

Run the test script:

```bash
python test_lowmem.py
```
