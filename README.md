# 👹 FRANKENSTEIN 1.0

**Phase 1: Core Engine**

A quantum-classical hybrid AI system with a Git Bash-style terminal interface.
Optimized for Dell Intel i3 8th Gen hardware (4 cores, 8GB RAM). Keep in mind that this is being built in phases thoughtfully. Right now this is like a jacked up Git Bash terminal in progress. You can run all the same Bash commands with this Monster terminal. Files will be cleaned and organized after phase 2 is complete. 

---

## 🚀 Quick Start

### One-Click Install
```batch
install.bat
```
This will:
1. Install all dependencies
2. Create the monster icon
3. Add desktop shortcut
4. Launch FRANKENSTEIN

### Or Launch Directly
```batch
FRANKENSTEIN.bat
```
Or double-click the **FRANKENSTEIN 1.0** icon on your desktop.

---

## 🎮 Features

### Terminal Interface
- **Git Bash-style** dark terminal with green text
- **Always-on-top** window
- **Real-time** CPU/RAM monitoring in title bar
- **Command history** (up/down arrows)
- **Monster branding** 👹

### System Monitoring
- Real-time resource tracking
- Automatic throttling when limits exceeded
- Safety constraints (80% CPU, 70% RAM max)

### Task Management
- Priority-based task queue
- Multi-threaded execution (3 workers)
- Task status tracking

---

## 💻 Commands

### Basic Commands
| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `status` | Show system status |
| `clear` | Clear the terminal |
| `quit` | Exit FRANKENSTEIN |

### Task Commands
| Command | Description |
|---------|-------------|
| `task <msg>` | Submit a task |
| `queue` | Show queue status |

### System Commands
| Command | Description |
|---------|-------------|
| `cpu` | Show CPU usage |
| `ram` | Show RAM usage |
| `stop` | Emergency stop all tasks |

---

## 📁 Project Structure

```
frankenstein-1.0/
├── frankenstein.py          # Main application
├── FRANKENSTEIN.bat         # Windows launcher
├── install.bat              # One-click installer
├── requirements.txt         # Dependencies
│
├── core/                    # Core engine
│   ├── safety.py           # Safety constraints
│   ├── governor.py         # Resource monitoring
│   ├── memory.py           # Persistence
│   └── orchestrator.py     # Task management
│
├── widget/                  # GUI components
│   ├── terminal.py         # Terminal widget (Git Bash style)
│   └── overlay.py          # Simple overlay widget
│
├── assets/                  # Graphics
│   └── frankenstein.ico    # Monster icon (18KB, multi-res)
│
├── scripts/                 # Utilities
│   ├── create_icon.py      # Icon generator
│   └── create_shortcut.ps1 # Shortcut creator
│
└── tests/                   # Test suite
    └── unit/               # Unit tests
```

---

## ⚙️ Configuration

### Safety Limits (Tier 1 Hardware)
| Limit | Value | Purpose |
|-------|-------|---------|
| Max CPU | 80% | Leave 20% for OS |
| Max RAM | 70% | Leave 30% headroom |
| Max Workers | 3 | Leave 1 core free |
| Max Storage | 20GB | Conservative budget |

### Widget Settings
- **Position**: Configurable (default: center)
- **Always on Top**: Yes
- **Theme**: Dark (monster green)

---

## 🔧 Installation

### Requirements
- Python 3.9 or higher
- Windows 10/11
- 8GB RAM minimum

### Dependencies
```
psutil>=5.9.0          # System monitoring
pyyaml>=6.0            # Configuration
customtkinter>=5.0.0   # GUI framework
pillow                 # Icon creation
```

### Manual Install
```bash
pip install psutil pyyaml customtkinter pillow
python frankenstein.py
```

---

## 🧪 Testing

### Run System Test
```bash
python frankenstein.py --test
```

### Run Unit Tests
```bash
python -m pytest tests/
```

---

## 📊 Command-Line Options

```
python frankenstein.py              # Launch GUI terminal (default)
python frankenstein.py --console    # Console mode (no GUI)
python frankenstein.py --status     # Show status and exit
python frankenstein.py --test       # Run system test
```

---

## 🔮 Roadmap

### Phase 1: Core Engine ✅ (Current)
- Safety constraints
- Resource monitoring
- Task orchestration
- Terminal GUI widget

### Phase 2: Predictive Synthesis (Planned)
- Data input/output processing
- Classical-quantum synthesis
- Physics-informed models

### Phase 3: Quantum Integration (Planned)
- IBM Quantum, AWS Braket, Azure Quantum
- Local quantum simulation
- Hybrid workflows

### Phase 4: Agent System (Planned)
- MCP agent framework
- Multi-agent collaboration

---

## 🛡️ Safety

FRANKENSTEIN protects your laptop with:

1. **Immutable Constraints** - Cannot be changed at runtime
2. **Auto-Throttling** - Reduces load automatically
3. **Emergency Stop** - Instant halt capability
4. **Continuous Monitoring** - 1-second polling

---

## 📝 License

MIT License - See [LICENSE](LICENSE)

---

## 👹 Credits

**FRANKENSTEIN 1.0** - Quantum-Classical Hybrid AI System
- **Target Hardware**: Dell Intel i3 8th Gen (Tier 1)
- **Build Date**: January 25, 2026
- **Phase**: 1 (Core Engine)

*Built with safety and efficiency in mind. Your hardware is protected.*
