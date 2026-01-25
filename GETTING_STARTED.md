# 🚀 Getting Started with FRANKENSTEIN 1.0

**Welcome!** This guide will get you up and running in under 2 minutes.

---

## Quick Start (30 Seconds)

### One-Click Launch

Double-click this file to install and run FRANKENSTEIN with the widget display:

```
install_and_run.bat
```

That's it! The widget window will appear showing live system stats.

---

## What is FRANKENSTEIN 1.0?

A **Quantum-Classical Hybrid AI System** optimized for Dell i3 8th Gen laptops (or better) with:

- ⚡ Real-time resource monitoring with auto-throttle
- 🎮 Always-on-top widget display
- 🛡️ Hardware safety protection
- ⚙️ Task orchestration with priority queues
- 💾 Persistent memory and session tracking

**Phase 1 Status**: Core Engine ✅ Complete

---

## System Requirements

✅ **Already Verified on Your System:**
- Python 3.12.10 ✓
- Windows 10/11 ✓
- 8GB RAM ✓
- Intel i3 8th Gen or better ✓

✅ **Dependencies Installed:**
- psutil 7.2.1 ✓
- customtkinter 5.2.2 ✓
- pyyaml 6.0.3 ✓
- pytest 7.4.0+ ✓

---

## Three Ways to Run

### Option 1: Widget Mode (Recommended)

**Launch:**
```batch
install_and_run.bat
```

**What You Get:**
- Always-on-top window with live CPU/RAM stats
- Command input field
- Quick action buttons (Status, Emergency Stop)
- Real-time monitoring

**Widget Display:**
```
╔════════════════════════════════════╗
║ ⚡ FRANKENSTEIN 1.0    🟢 READY   ║
╠════════════════════════════════════╣
║ CPU: 50%        RAM: 78%           ║
╠════════════════════════════════════╣
║ [Enter command...]         [▶]    ║
╠════════════════════════════════════╣
║  [📊 Status]    [🛑 Stop]         ║
╚════════════════════════════════════╝
```

### Option 2: Interactive Launcher

**Launch:**
```batch
LAUNCH_FRANKENSTEIN.bat
```

**Choose Mode:**
1. 🎮 Widget Mode - Always-on-top window
2. 💻 Interactive Mode - Console interface
3. 📊 Status Check - View system status
4. 🧪 System Test - Run functionality test

### Option 3: Command Line

```batch
# Widget mode
python frankenstein.py --widget

# Interactive console
python frankenstein.py

# Status check
python frankenstein.py --status

# System test
python frankenstein.py --test
```

---

## Your First Session

### 1. Launch FRANKENSTEIN
```batch
install_and_run.bat
```

### 2. Widget Appears
- Small window in top-right corner
- Shows live CPU/RAM usage
- Status indicator (🟢 READY or 🟡 THROTTLED)

### 3. Try Commands
In the widget input field, type:
- `status` → View detailed system info
- `stop` → Shutdown FRANKENSTEIN

### 4. Shutdown
- Press **Ctrl+C** in console window
- Or click **🛑 Stop** button in widget

---

## Understanding Status Indicators

### 🟢 SAFE / READY
System running normally, resources within limits:
- CPU < 80%
- RAM < 70%

### 🟡 THROTTLED
Auto-throttle active to protect your laptop:
- **LIGHT** - Slightly reduced load
- **MODERATE** - Non-critical tasks paused
- **HEAVY** - Essential operations only
- **EMERGENCY** - Full stop

**Note:** Your current RAM usage (78.5%) exceeds the 70% limit, so FRANKENSTEIN starts in MODERATE throttle. This is normal and protects your system!

---

## Safety Features

FRANKENSTEIN protects your laptop with:

1. **Immutable Safety Limits**
   - Max CPU: 80% (leaves 20% for OS)
   - Max RAM: 70% (leaves 30% headroom)
   - Max Workers: 3 threads (leaves 1 core free)

2. **Real-time Monitoring**
   - Checks resources every 1 second
   - Automatic throttling when limits approached

3. **Emergency Controls**
   - Widget stop button
   - Ctrl+C keyboard interrupt
   - Automatic shutdown on violations

4. **Storage Protection**
   - 20GB maximum storage use
   - Data stored in `~/.frankenstein/`

---

## What You Can Do (Phase 1)

### ✅ Currently Available

- **Monitor Resources** - Live CPU/RAM tracking
- **Task Management** - Submit and track computational tasks
- **Session Persistence** - History saved across restarts
- **Widget Control** - Always-on-top command interface
- **Safety Protection** - Automatic hardware safeguards

### 🔮 Coming Soon

- **Phase 2** - Predictive Synthesis Engine
- **Phase 3** - Quantum Integration (IBM, AWS, Azure)
- **Phase 4** - MCP Agent Framework

---

## File Structure

```
Frankenstein-1.0/
├── frankenstein.py           # Main application
├── install_and_run.bat       # One-click launcher
├── LAUNCH_FRANKENSTEIN.bat   # Interactive launcher
├── QUICKSTART.bat            # Automated setup + test
├── GETTING_STARTED.md        # This file
├── README.md                 # Project overview
│
├── core/                     # Core engine modules
│   ├── safety.py            # Safety constraints
│   ├── governor.py          # Resource monitoring
│   ├── memory.py            # Session persistence
│   └── orchestrator.py      # Task management
│
├── widget/                   # UI overlay
│   └── overlay.py           # Widget display
│
├── configs/                  # Configuration files
│   └── tier1_laptop.yaml    # Your laptop config
│
├── tests/                    # Test suite
│   └── unit/                # Unit tests (78+ tests)
│
├── docs/                     # Documentation
│   ├── TESTING.md           # Testing guide
│   └── AUTOMATION_SETUP.md  # Setup details
│
└── scripts/                  # Utility scripts
    ├── setup_env.bat        # Environment setup
    ├── run_tests.bat        # Test runner
    └── test_runner.py       # Python test runner
```

---

## Running Tests

### Quick Test
```batch
cd scripts
run_tests.bat quick
```

### Full Test Suite
```batch
cd scripts
run_tests.bat coverage
```

### All Test Modes
- `quick` - Fast tests, no coverage
- `standard` - Normal tests with basic coverage
- `coverage` - Full coverage report (HTML)
- `verbose` - Detailed output
- `unit` - Unit tests only

**See** [docs/TESTING.md](docs/TESTING.md) for complete testing guide.

---

## Common Commands

### Widget Commands
- `status` - Detailed system status
- `stop` - Emergency shutdown

### Batch Scripts
```batch
install_and_run.bat              # Quick launch with widget
LAUNCH_FRANKENSTEIN.bat          # Interactive launcher
QUICKSTART.bat                   # Setup + automated test
scripts\run_tests.bat            # Run tests
scripts\Create_Desktop_Shortcut.bat  # Desktop shortcut
```

### Python Commands
```bash
python frankenstein.py --widget  # Widget mode
python frankenstein.py           # Interactive mode
python frankenstein.py --status  # Status check
python frankenstein.py --test    # System test
```

---

## Troubleshooting

### Widget doesn't appear
**Solution:**
```batch
python -m pip install customtkinter
```

### "Throttled" status showing
**Expected behavior!** Your RAM is at 78.5%, exceeding the 70% safety limit. FRANKENSTEIN automatically throttles to protect your laptop. This is normal and safe.

### High resource usage
FRANKENSTEIN automatically throttles at safety limits. The protection system is working correctly.

### Can't find Python
Use full path:
```batch
C:\Users\adamn\AppData\Local\Programs\Python\Python312\python.exe frankenstein.py --widget
```

---

## Desktop Shortcut

Create a desktop shortcut for quick access:

```batch
scripts\Create_Desktop_Shortcut.bat
```

This adds "FRANKENSTEIN 1.0" to your desktop.

---

## Configuration

Edit `configs/tier1_laptop.yaml` to customize:

```yaml
resources:
  max_cpu_percent: 80        # CPU limit
  max_memory_percent: 70     # RAM limit
  max_worker_threads: 3      # Thread count

widget:
  position: "top_right"      # Widget position
  transparency: 0.95         # Window transparency
  always_on_top: true        # Stay on top
```

---

## Data Storage

FRANKENSTEIN stores data in:
- `~/.frankenstein/session.json` - Current session
- `~/.frankenstein/history/` - Task history
- `~/.frankenstein/logs/` - Log files
- `~/.frankenstein/cache/` - Temporary cache

**Storage Limit:** 20GB maximum

---

## Documentation

### Quick Reference
- **GETTING_STARTED.md** - This file
- **README.md** - Project overview
- **BUILD_COMPLETE.md** - Build information

### Detailed Guides
- **docs/TESTING.md** - Complete testing guide
- **docs/AUTOMATION_SETUP.md** - Automation details

### Source Documentation
- **core/\*.py** - Module docstrings
- **widget/overlay.py** - Widget documentation

---

## Current System Status

Based on recent check:

```
Hardware: Dell i3 8th Gen (4 cores)
RAM: 7.80GB total, 6.12GB used (78.5%)
CPU: 50.0% usage
Status: 🟡 THROTTLED (MODERATE)
Reason: RAM exceeds 70% safety limit
Safety: ✓ Active and protecting
```

This is **normal operation**. FRANKENSTEIN is protecting your laptop by automatically throttling.

---

## Next Steps

### 1. Launch Now
```batch
install_and_run.bat
```

### 2. Explore Features
- Watch live resource monitoring
- Try widget commands
- View detailed status
- Test emergency stop

### 3. Run Tests (Optional)
```batch
scripts\run_tests.bat coverage
```

### 4. Learn More
- Read [README.md](README.md) for project details
- Check [docs/TESTING.md](docs/TESTING.md) for testing
- Review configuration in `configs/tier1_laptop.yaml`

---

## Support

### Documentation
- [README.md](README.md) - Project overview
- [docs/TESTING.md](docs/TESTING.md) - Testing guide
- [docs/AUTOMATION_SETUP.md](docs/AUTOMATION_SETUP.md) - Setup details

### Quick Help
```batch
python frankenstein.py --help
```

---

## Summary

**FRANKENSTEIN 1.0 is ready!**

✅ All dependencies installed
✅ Widget display enabled
✅ Safety systems active
✅ 78+ automated tests passing
✅ Documentation complete

**To start:** Double-click `install_and_run.bat`

**To shutdown:** Press Ctrl+C or click 🛑 Stop

---

**Version:** 1.0 - Phase 1 (Core Engine)
**Date:** January 25, 2026
**Status:** ✅ Operational

Welcome to FRANKENSTEIN! ⚡
