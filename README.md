# 🧟 FRANKENSTEIN 1.0

**Physics-Grounded AI Desktop Assistant**

A quantum-classical hybrid AI system with an integrated terminal interface for scientific computing and engineering tasks. Phase 1 (Core Engine) and Phase 2 (Predictive Synthesis) are complete. Phase 3 (Universal Integration) is now in progress. 

---

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/nah414/Frankenstein-1.0.git
cd Frankenstein-1.0

# Install dependencies
pip install -r requirements.txt

# Launch the Monster Terminal
python launch_terminal.py
```

Or double-click `RUN_FRANKENSTEIN.bat` on Windows.

---

## 🖥️ Monster Terminal Features

| Category | Commands |
|----------|----------|
| **Navigation** | `cd`, `pwd`, `ls`, `find` |
| **File Ops** | `cat`, `touch`, `mkdir`, `rm`, `cp`, `mv` |
| **Git** | `git status`, `git add`, `git commit`, `git push` |
| **SSH** | `ssh`, `scp`, `ssh-keygen` |
| **Package Mgmt** | `pip`, `npm`, `conda` |
| **Editors** | `nano`, `vim`, `notepad`, `code` |
| **Environment** | `export`, `env`, `set`, `unset` |
| **Scripting** | `python`, `node`, `source` |
| **Hardware** | `hardware` — live system detection & tier classification |
| **Providers** | `providers`, `providers suggest`, `providers setup <id>` |
| **Workloads** | `analyze "<task>"`, `analyze quantum`, `analyze classical` |
| **Connections** | `connect <id>`, `disconnect <id>` |

Type `help` in the terminal for full command list.

---

## 📁 Project Structure

```
Frankenstein-1.0/
├── launch_terminal.py    # Terminal launcher
├── frankenstein.py       # Main entry point
├── RUN_FRANKENSTEIN.bat  # Windows quick launch
├── requirements.txt      # Dependencies
│
├── widget/               # Terminal UI
│   ├── terminal.py       # Monster Terminal implementation
│   ├── quantum_mode.py   # Quantum mode interface
│   └── synthesis_panel.py # Synthesis control panel
│
├── core/                 # Core engine
│   ├── governor.py       # Resource management
│   ├── safety.py         # Safety constraints
│   ├── memory.py         # Memory systems
│   ├── orchestrator.py   # Task orchestration
│   ├── hardware_monitor.py    # Hardware monitoring
│   ├── hardware_dashboard.py  # Hardware dashboard
│   └── system_diagnostics.py  # System diagnostics
│
├── synthesis/            # Predictive Synthesis Engine
│   ├── engine.py         # Main synthesis engine
│   ├── relativistic_quantum.py  # Lorentz transformations
│   ├── core/             # True engine implementation
│   ├── compute/          # Math/physics/quantum compute
│   └── quantum/          # Quantum visualization & circuits
│
├── security/             # Security module
│   ├── monitor.py        # Threat detection
│   ├── dashboard.py      # Security dashboard
│   └── shield.py         # The Shield widget
│
├── agents/               # AI agents
│   ├── base.py           # Base agent framework
│   ├── sandbox.py        # Sandboxed execution
│   └── swarms/           # Compute swarm implementation
│
├── data/                 # Data Pipeline & Telemetry
│   ├── pipeline.py       # Unified data flow management
│   ├── telemetry.py      # Always-on metrics collection
│   ├── events.py         # Pub/sub event bus
│   ├── metrics.py        # Statistics aggregation
│   └── storage.py        # File-based JSON persistence
│
├── integration/          # Phase 3: Universal Integration
│   ├── discovery.py      # Hardware auto-detection engine
│   ├── analyzer.py       # Workload profiling & complexity scoring
│   ├── commands.py       # Terminal command handlers
│   ├── guide.py          # Smart recommendation engine
│   └── providers/        # Provider registry & adapters
│       ├── registry.py   # Central registry (14 providers)
│       ├── quantum/      # Quantum adapter stubs
│       └── classical/    # Classical adapter stubs
│
├── quantum/              # Quantum computing integration
├── classical/            # Classical computing
├── configs/              # Configuration files
├── tests/                # Unit tests
├── assets/               # Icons and resources
└── docs/                 # Documentation
```

---

## 🛡️ Safety Constraints

Hard-coded limits protect your system:
- **CPU**: Max 80%
- **Memory**: Max 70%
- **Auto-throttle**: Enabled
- **Emergency stop**: Available

---

## 🗺️ Development Roadmap

FRANKENSTEIN is being built in 4 phases. Each phase adds new capabilities while maintaining stability and safety.

### Phase 1: Core Engine ✅ COMPLETE
*Foundation & Hardware Protection*
- Safety system with immutable constraints
- Resource governor with 5-level auto-throttle
- Memory system with session persistence
- Task orchestrator with priority queue
- Monster Terminal (Git Bash-style interface)

### Phase 2: Predictive Synthesis ✅ COMPLETE
*Intelligence Layer with Security Monitoring*

| Step | Feature | Status |
|------|---------|--------|
| 1 | Security Dashboard + Live Threat Monitor | ✅ Complete |
| 2 | Hardware Health + Auto-Switch Warning | ✅ Complete |
| 3 | Classical-Quantum Synthesis Engine | ✅ Complete |
| 4 | Quantum Visualization (Bloch Sphere) | ✅ Complete |
| 5 | Compute Swarms + Distributed Processing | ✅ Complete |
| 6 | Relativistic Quantum Integration | ✅ Complete |
| 7 | Data Pipeline + Telemetry | ✅ Complete |
| 8 | Lab Monitors Panel (Final Polish) | ✅ Complete |

### Phase 3: Universal Integration 🔄 IN PROGRESS
*The Ultimate Connection & Configuration Optimizer*

| Step | Feature | Status |
|------|---------|--------|
| 1 | Hardware Discovery Engine — auto-detects CPU, GPU, RAM, tier classification | ✅ Complete |
| 2 | Provider Registry + Smart Guide — 14 providers, lazy-load, `providers suggest` | ✅ Complete |
| 3 | Workload Analyzer — task profiling, complexity scoring, provider matching | ✅ Complete |
| 4 | Configuration Optimizer | 📋 Planned |
| 5 | Intelligent Router | 📋 Planned |
| 6 | Permission & Automation | 📋 Planned |
| 7 | Real-Time Adaptation | 📋 Planned |
| 8 | Terminal Integration (Final Polish) | 📋 Planned |

**Supported Providers (14 total):**
- **Quantum Cloud**: IBM Quantum, AWS Braket, Azure Quantum, Google Cirq, IonQ, Rigetti, Xanadu, D-Wave
- **Quantum Local**: Built-in NumPy simulator (~20 qubits on 8GB RAM)
- **Classical**: Local CPU, NVIDIA CUDA, AMD ROCm, Intel oneAPI, Apple Metal

### Phase 4: Autonomous Agents 📋 PLANNED
*MCP Framework with Multi-Agent Collaboration*
- Sandboxed agent execution environment
- Built-in agent library (Compute, Research, Optimization, Security, Hardware)
- Multi-agent orchestration and collaboration
- User-defined agent creation

---

## 📋 Requirements

- Python 3.10+
- Windows 10/11
- Git (for version control commands)

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

*"It's alive... and ready to serve science." ⚡*
