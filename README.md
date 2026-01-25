# ⚡ FRANKENSTEIN 1.0

**Phase 1: Core Engine**

A quantum-classical hybrid AI system optimized for Dell Intel i3 8th Gen hardware (4 cores, 8GB RAM, 117GB storage).

---

## 🎯 Project Overview

FRANKENSTEIN 1.0 is a resource-aware AI system that combines classical computation, quantum simulation capabilities, and predictive synthesis. Built with hardware safety as a top priority, it includes real-time resource monitoring and automatic throttling to protect your laptop.

**Target Hardware:** Dell Intel i3 8th Gen
**Date:** January 25, 2026
**Phase:** 1 (Core Engine)

---

## 🏗️ Architecture

### Core Components

- **Safety System** (`core/safety.py`) - Immutable safety constraints protecting hardware
- **Resource Governor** (`core/governor.py`) - Real-time resource monitoring with auto-throttling
- **Memory System** (`core/memory.py`) - Session state and persistent task history
- **Task Orchestrator** (`core/orchestrator.py`) - Task routing and queue management
- **Widget Overlay** (`widget/overlay.py`) - Always-on-top command window

### Directory Structure

```
frankenstein-1.0/
├── core/              # Core engine components
├── synthesis/         # Predictive synthesis (Phase 2)
├── quantum/           # Quantum simulation (Phase 3)
├── agents/            # MCP agents (Phase 4)
├── security/          # Security shield
├── widget/            # UI overlay
├── classical/         # Classical computation
├── configs/           # Configuration files
├── docker/            # Docker deployment
├── tests/             # Unit tests
└── docs/              # Documentation
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Windows 10/11 (for widget overlay)
- 8GB RAM minimum
- Intel i3 8th Gen or better

### Installation

```bash
# Clone the repository
git clone https://github.com/nah414/frankenstein-1.0.git
cd frankenstein-1.0

# Install dependencies
pip install -r requirements.txt

# Run FRANKENSTEIN
python frankenstein.py
```

---

## 📦 Dependencies

- **psutil** - System resource monitoring
- **customtkinter** - Modern UI framework for widget overlay
- **pyyaml** - Configuration file parsing

Optional (Phase 2+):
- **qiskit** - Quantum simulation
- **numpy** - Numerical computation
- **scipy** - Scientific computing

---

## ⚙️ Configuration

Configuration files are located in `configs/`:

- `tier1_laptop.yaml` - Dell i3 8th Gen configuration

### Safety Limits (Tier 1)

- **Max CPU:** 80% (leaves 20% for OS)
- **Max Memory:** 70% (~5.6GB of 8GB)
- **Worker Threads:** 3 (leaves 1 core for OS)
- **Storage Budget:** 20GB max

---

## 🎮 Usage

### Command Line

```bash
# Start with default config
python frankenstein.py

# Start with custom config
python frankenstein.py --config configs/tier1_laptop.yaml

# Enable widget overlay
python frankenstein.py --widget

# Check system status
python frankenstein.py --status
```

### Widget Overlay

The widget provides:
- Real-time CPU and RAM monitoring
- Command input interface
- Quick status checks
- Emergency stop button

**Widget Commands:**
- `status` - Show detailed system status
- `stop` - Emergency stop all operations

---

## 🛡️ Safety Features

### Resource Protection

1. **Automatic Throttling** - Reduces load when limits are approached
2. **Emergency Stop** - Immediate halt capability
3. **Resource Monitoring** - 1-second polling interval
4. **Violation Callbacks** - Notify on safety breaches

### Throttle Levels

- **NONE** - Normal operation
- **LIGHT** - Slow down new tasks
- **MODERATE** - Pause non-critical tasks
- **HEAVY** - Only essential operations
- **EMERGENCY** - Full stop

---

## 📊 System Status

Monitor system health:

```python
from core import get_governor, get_memory, get_orchestrator

# Check resource status
governor = get_governor()
status = governor.get_status()
print(f"CPU: {status['cpu_percent']}%")
print(f"RAM: {status['memory_percent']}%")

# Check session stats
memory = get_memory()
session = memory.get_session_stats()
print(f"Tasks completed: {session['task_count']}")

# Check queue status
orchestrator = get_orchestrator()
queue = orchestrator.get_queue_status()
print(f"Active tasks: {queue['active_tasks']}")
```

---

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=core --cov-report=html
```

---

## 🔮 Roadmap

### Phase 1: Core Engine ✅ (Current)
- Safety constraints
- Resource governor
- Memory system
- Task orchestrator
- Widget overlay

### Phase 2: Predictive Synthesis (Planned)
- Classical-quantum synthesis
- Physics-informed models
- Predictive task routing

### Phase 3: Quantum Integration (Planned)
- Cloud quantum providers (IBM, AWS, Azure)
- Local quantum simulation
- Hybrid quantum-classical workflows

### Phase 4: Agent System (Planned)
- MCP agent framework
- Multi-agent collaboration
- Tool integration

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## ⚠️ Important Notes

### Hardware Limits

This system is specifically tuned for **Tier 1** hardware (Dell i3 8th Gen). Running on higher-tier hardware will still respect conservative limits unless you create a custom configuration.

### Resource Constraints

- Max 3 worker threads
- 70% RAM usage limit
- 80% CPU usage limit
- 20GB storage budget

These limits ensure stable operation without overwhelming your laptop.

---

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the [docs/](docs/) folder for detailed documentation

---

## 🎓 Credits

**Project:** FRANKENSTEIN 1.0
**Architecture:** Quantum-Classical Hybrid AI
**Optimization Target:** Dell Intel i3 8th Gen (Tier 1)
**Build Date:** January 25, 2026

---

**Status:** Phase 1 Complete ✅
**Next Phase:** Predictive Synthesis Engine

---

*Built with safety and efficiency in mind. Your hardware is protected.*
