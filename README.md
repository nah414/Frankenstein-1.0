# 🧟 FRANKENSTEIN 1.0

**Physics-Grounded AI Desktop Assistant**

A quantum-classical hybrid AI system with an integrated terminal interface for scientific computing and engineering tasks. Phase 1 (Core Engine), Phase 2 (Predictive Synthesis), and Phase 3 Steps 1-4 (Universal Integration) are complete.

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
| **Providers** | `providers`, `connect`, `disconnect`, `credentials` |
| **Diagnostics** | `hardware`, `security`, `diagnose`, `status` |
| **Quantum** | `quantum`, `qubit`, `bloch`, `synthesis` |

Type `help` or `help <command>` in the terminal for detailed guides.

---

## 🔌 Provider Integration (Phase 3)

Frankenstein connects to **29 providers** across quantum and classical computing. All providers are lazy-loaded — nothing runs until you explicitly connect.

### Quantum Providers (19)
| Provider | ID | Technology |
|----------|----|------------|
| IBM Quantum | `ibm_quantum` | Superconducting |
| AWS Braket | `aws_braket` | Multi-vendor gateway |
| Azure Quantum | `azure_quantum` | Multi-vendor gateway |
| Google Quantum AI | `google_cirq` | Superconducting |
| IonQ | `ionq` | Trapped ion |
| Rigetti | `rigetti` | Superconducting |
| Xanadu | `xanadu` | Photonic |
| D-Wave | `dwave` | Quantum annealing |
| Quantinuum | `quantinuum` | Trapped ion |
| IQM | `iqm` | Superconducting |
| QuEra | `quera` | Neutral atom |
| Oxford QC | `oxford` | Superconducting |
| Atom Computing | `atom_computing` | Neutral atom |
| Pasqal | `pasqal` | Neutral atom |
| AQT | `aqt` | Trapped ion |
| NVIDIA Quantum Cloud | `nvidia_quantum_cloud` | Simulation |
| Qiskit Aer | `qiskit_aer` | Local simulator |
| cuQuantum | `cuquantum` | GPU simulator |
| Local Simulator | `local_simulator` | NumPy (free, offline) |

### Classical Providers (10)
| Provider | ID | Architecture |
|----------|----|-------------|
| Local CPU | `local_cpu` | x86/ARM (free, always available) |
| NVIDIA CUDA | `nvidia_cuda` | CUDA GPU |
| AMD ROCm | `amd_rocm` | ROCm GPU |
| Apple Metal | `apple_metal` | Metal GPU |
| Intel oneAPI | `intel_oneapi` | oneAPI accelerator |
| ARM Compute | `arm` | ARM CPU |
| RISC-V | `risc_v` | RISC-V CPU |
| Google TPU | `tpu` | TPU accelerator |
| FPGA | `fpga` | FPGA fabric |
| NPU | `npu` | Neural Processing Unit |

### Quick Connect

```bash
# Free, no credentials needed:
connect local_simulator
connect local_cpu

# Cloud providers (credentials required):
credentials save ibm_quantum --token "YOUR_TOKEN"
connect ibm_quantum

# Verify credentials before connecting:
credentials verify ibm_quantum

# Check what's connected:
providers
```

---

## 📁 Project Structure

```
Frankenstein-1.0/
├── launch_terminal.py        # Terminal launcher
├── frankenstein.py           # Main entry point
├── RUN_FRANKENSTEIN.bat      # Windows quick launch
├── requirements.txt          # Dependencies
│
├── widget/                   # Terminal UI
│   ├── terminal.py           # Monster Terminal (3000+ lines)
│   ├── quantum_mode.py       # Quantum REPL mode
│   └── synthesis_panel.py    # Synthesis control panel
│
├── core/                     # Core engine
│   ├── governor.py           # Resource governor (5-level auto-throttle)
│   ├── safety.py             # Immutable safety constraints
│   ├── memory.py             # Session persistence
│   ├── orchestrator.py       # Task orchestration
│   ├── hardware_monitor.py   # Hardware health monitoring
│   ├── hardware_dashboard.py # Hardware dashboard
│   └── system_diagnostics.py # System diagnostics
│
├── integration/              # Universal Integration Engine
│   ├── discovery.py          # Hardware auto-detection
│   ├── credentials.py        # Credential management (JSON storage)
│   ├── commands.py           # Terminal command handlers
│   ├── guide.py              # Smart provider recommendations
│   └── providers/
│       ├── base.py           # ProviderAdapter ABC + dataclasses
│       ├── registry.py       # ProviderRegistry (29 providers)
│       ├── quantum/          # 19 quantum adapter modules
│       └── classical/        # 10 classical adapter modules
│
├── synthesis/                # Predictive Synthesis Engine
│   ├── engine.py             # Main synthesis engine
│   ├── relativistic_quantum.py  # Lorentz transformations
│   ├── core/                 # True engine implementation
│   ├── compute/              # Math/physics/quantum compute
│   └── quantum/              # Bloch sphere & circuit visualization
│
├── security/                 # Security module
│   ├── monitor.py            # Live threat detection
│   ├── dashboard.py          # Security dashboard
│   └── shield.py             # Input/output filtering
│
├── agents/                   # AI agents (lazy-loaded)
│   ├── base.py               # Base agent framework
│   ├── sandbox.py            # Sandboxed execution
│   └── swarms/               # Compute swarm implementation
│
├── data/                     # Data Pipeline & Telemetry
│   ├── pipeline.py           # Unified data flow
│   ├── telemetry.py          # Metrics collection
│   ├── events.py             # Pub/sub event bus
│   ├── metrics.py            # Statistics aggregation
│   └── storage.py            # JSON persistence
│
├── configs/                  # Configuration files
├── tests/                    # Unit tests
└── assets/                   # Icons and resources
```

---

## 🛡️ Safety Constraints

Hard-coded limits protect your system:
- **CPU**: Max 80%
- **Memory**: Max 70%
- **Auto-throttle**: Enabled (5-level progressive)
- **Emergency stop**: Available
- **Lazy loading**: All providers, monitors, and agents only initialize on explicit user command

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
*Quantum + Classical Provider Connectivity*

| Step | Feature | Status |
|------|---------|--------|
| 1 | Hardware Discovery (auto-detect CPU, GPU, QPU) | ✅ Complete |
| 2 | Provider Registry (29 providers cataloged) | ✅ Complete |
| 3 | Setup Guide + Smart Recommendations | ✅ Complete |
| 4 | Provider Adapters + Credential Management | ✅ Complete |
| 5 | Intelligent Workload Router | 📋 Planned |
| 6 | Cost/Performance Optimization | 📋 Planned |

**Step 4 delivered:**
- 30 provider adapter modules (19 quantum + 11 classical) with consistent API
- Credential management with save/list/show/delete/verify subcommands
- `connect` command auto-detects missing credentials and shows setup guidance
- All adapters handle missing SDKs gracefully (no crashes, clear install instructions)
- Full help system with detailed per-provider setup guides

### Phase 4: Autonomous Agents 📋 PLANNED
*MCP Framework with Multi-Agent Collaboration*
- Sandboxed agent execution environment
- Built-in agent library (Compute, Research, Optimization, Security, Hardware)
- Multi-agent orchestration and collaboration
- User-defined agent creation
- Extensive security guardrails 

---

## 📋 Requirements

- Python 3.10+
- Windows 10/11
- Git (for version control commands)

### Core Dependencies (required)
- `customtkinter` — Terminal UI
- `numpy` — Numerical computing
- `psutil` — System monitoring

### Optional SDKs (install only what you need)
```bash
pip install qiskit qiskit-ibm-runtime    # IBM Quantum
pip install amazon-braket-sdk            # AWS Braket
pip install azure-quantum                # Azure Quantum
pip install cirq cirq-google             # Google Quantum
pip install pennylane                    # Xanadu
pip install dwave-ocean-sdk              # D-Wave
pip install cupy-cuda12x                 # NVIDIA CUDA
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

*"It's alive... and ready to serve science." ⚡*
