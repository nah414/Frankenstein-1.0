# FRANKENSTEIN 1.0

**Physics-Grounded AI Desktop Assistant — Quantum-Classical Hybrid Computing**

Phase 1 (Core Engine), Phase 2 (Predictive Synthesis), and Phase 3 Steps 1–5 (Universal Integration) are complete. 46 tests passing.

## Quick Start

```bash
git clone https://github.com/nah414/Frankenstein-1.0.git
cd Frankenstein-1.0
pip install -r requirements.txt
python launch_terminal.py
```

Or double-click `RUN_FRANKENSTEIN.bat` on Windows.

---

## Terminal Commands

| Category | Commands |
|----------|----------|
| **Navigation** | `cd`, `pwd`, `ls`, `find` |
| **File Ops** | `cat`, `touch`, `mkdir`, `rm`, `cp`, `mv`, `head`, `tail`, `grep`, `wc` |
| **Git (Enhanced)** | `git status` (color-coded), `git clone` (progress bars), `git log` (visual graph) |
| **SSH** | `ssh`, `scp`, `ssh-keygen` |
| **Packages** | `pip`, `npm`, `conda` |
| **Editors** | `nano`, `vim`, `notepad`, `code` |
| **Environment** | `export`, `env`, `set`, `unset`, `printenv` |
| **Scripting** | `python`, `node`, `source` |
| **Providers** | `providers`, `connect`, `disconnect`, `credentials` |
| **Routing** | `route`, `route-options`, `route-test`, `route-history` |
| **Diagnostics** | `hardware`, `security`, `diagnose`, `status` |
| **Quantum** | `quantum`, `qubit`, `bloch`, `synthesis` |

Type `help` or `help <command>` for detailed guides.

---

## Provider Integration (Phase 3)

29 quantum + classical providers, all lazy-loaded. Nothing runs until you explicitly connect.

<details>
<summary><strong>19 Quantum Providers</strong></summary>

| Provider | ID | Technology | Free Tier |
|----------|----|------------|-----------|
| IBM Quantum | `ibm_quantum` | Superconducting, 127q | Yes |
| AWS Braket | `aws_braket` | Multi-vendor gateway | Yes |
| Azure Quantum | `azure_quantum` | Multi-vendor gateway | Yes |
| Google Quantum AI | `google_cirq` | Superconducting, 72q | No |
| IonQ | `ionq` | Trapped ion, 36q | Yes |
| Rigetti | `rigetti` | Superconducting, 84q | Yes |
| Xanadu | `xanadu` | Photonic, 24q | Yes |
| D-Wave | `dwave` | Quantum annealing, 5000q | Yes |
| Quantinuum | `quantinuum` | Trapped ion, 56q | No |
| IQM | `iqm` | Superconducting, 20q | No |
| QuEra | `quera` | Neutral atom, 256q | Yes |
| Oxford QC | `oxford` | Superconducting, 32q | No |
| Atom Computing | `atom_computing` | Neutral atom, 1225q | No |
| Pasqal | `pasqal` | Neutral atom, 200q | No |
| AQT | `aqt` | Trapped ion, 24q | Yes |
| NVIDIA Quantum Cloud | `nvidia_quantum_cloud` | GPU simulation | No |
| Qiskit Aer | `qiskit_aer` | Local simulator, 32q | Yes |
| cuQuantum | `cuquantum` | GPU simulator, 30q | Yes |
| Local Simulator | `local_simulator` | NumPy, 20q, offline | Yes |

</details>

<details>
<summary><strong>10 Classical Providers</strong></summary>

| Provider | ID | Architecture | Free |
|----------|----|-------------|------|
| Local CPU | `local_cpu` | x86/ARM, always available | Yes |
| NVIDIA CUDA | `nvidia_cuda` | CUDA GPU | Yes |
| AMD ROCm | `amd_rocm` | ROCm GPU | Yes |
| Apple Metal | `apple_metal` | Metal GPU (macOS) | Yes |
| Intel oneAPI | `intel_oneapi` | oneAPI accelerator | Yes |
| ARM Compute | `arm` | ARM CPU | Yes |
| RISC-V | `risc_v` | RISC-V CPU | Yes |
| Google TPU | `tpu` | TPU accelerator | Yes |
| FPGA | `fpga` | FPGA fabric | Yes |
| NPU | `npu` | Neural Processing Unit | Yes |

</details>

```bash
# Free, no credentials:
connect local_simulator
connect local_cpu

# Cloud providers:
credentials save ibm_quantum --token "YOUR_TOKEN"
connect ibm_quantum
```

---

## Intelligent Router (Phase 3, Step 5)

Automatically selects the optimal provider based on workload, hardware, and resource constraints.

```bash
# Route a 10-qubit simulation, prefer free providers:
route --qubits 10 --priority cost

# See all compatible providers ranked:
route-options --type quantum_simulation --qubits 15

# Test a specific provider:
route-test --provider ibm_quantum --qubits 10

# View routing history:
route-history
```

**Routing rules:**
- <= 5 qubits → local simulators (free, instant)
- 6–20 qubits → local + cloud fallback
- 21–29 qubits → cloud providers (IBM, AWS, Azure)
- 30+ qubits → large-scale hardware (IonQ, Rigetti, QuEra)

**Safety enforced:** CPU max 80%, RAM max 70%. Routes exceeding limits are automatically blocked with fallback to lighter providers. Every fallback chain terminates at `local_cpu`.

**Priority modes:** `cost` (prefer free/local), `speed` (prefer fastest), `accuracy` (prefer highest fidelity).

---

## Project Structure

```
Frankenstein-1.0/
├── launch_terminal.py          # Terminal launcher
├── frankenstein.py             # Main entry point
├── widget/                     # Terminal UI (3400+ lines)
│   ├── terminal.py             # Monster Terminal
│   ├── quantum_mode.py         # Quantum REPL
│   └── synthesis_panel.py      # Synthesis panel
├── core/                       # Core engine
│   ├── safety.py               # Immutable safety constraints
│   ├── governor.py             # 5-level auto-throttle
│   ├── memory.py, orchestrator.py, hardware_monitor.py, system_diagnostics.py
├── integration/                # Universal Integration
│   ├── discovery.py            # Hardware auto-detection
│   ├── credentials.py          # Credential management
│   ├── commands.py             # Terminal command handlers
│   └── providers/              # 29 provider adapters
│       ├── base.py, registry.py
│       ├── quantum/ (19)       # IBM, AWS, Azure, Google, IonQ, Rigetti...
│       └── classical/ (10)     # CPU, NVIDIA, AMD, Apple, Intel, TPU...
├── router/                     # Intelligent Router (Phase 3.5)
│   ├── intelligent_router.py   # Core orchestrator (lazy singleton)
│   ├── workload_spec.py        # WorkloadSpec + WorkloadType
│   ├── decision_engine.py      # Routing logic by qubit count & hardware
│   ├── scoring.py              # Provider scoring (cost/speed/accuracy)
│   ├── safety_filter.py        # CPU 80% / RAM 70% enforcement
│   ├── fallback.py             # Fallback chains + error classification
│   └── commands.py             # Terminal commands
├── synthesis/                  # Predictive Synthesis Engine
├── security/                   # Security (shield, filters, audit, monitor)
├── agents/                     # AI agents (lazy-loaded)
├── data/                       # Data pipeline & telemetry
├── tests/                      # Unit tests (46 router tests + more)
└── configs/, assets/
```

---

## Safety Constraints

| Limit | Value | Notes |
|-------|-------|-------|
| CPU | Max 80% | 20% reserved for OS |
| Memory | Max 70% | ~5.6GB on 8GB system |
| Auto-throttle | 5-level progressive | Automatic downgrade |
| Emergency stop | Available | Kills runaway tasks |
| Lazy loading | All modules | Nothing initializes until called |

---

## Development Roadmap

### Phase 1: Core Engine — COMPLETE
Safety system (immutable constraints) · Resource governor (5-level throttle) · Memory persistence · Task orchestrator · Monster Terminal (Git Bash-style, 70+ commands)

### Phase 2: Predictive Synthesis — COMPLETE

| Step | Feature | Status |
|------|---------|--------|
| 1 | Security Dashboard + Live Threat Monitor | Done |
| 2 | Hardware Health + Auto-Switch Warning | Done |
| 3 | Classical-Quantum Synthesis Engine | Done |
| 4 | Quantum Visualization (Bloch Sphere) | Done |
| 5 | Compute Swarms + Distributed Processing | Done |
| 6 | Relativistic Quantum Integration | Done |
| 7 | Data Pipeline + Telemetry | Done |
| 8 | Lab Monitors Panel (Final Polish) | Done |

### Phase 3: Universal Integration — IN PROGRESS

| Step | Feature | Status |
|------|---------|--------|
| 1 | Hardware Discovery (auto-detect CPU, GPU, QPU) | Done |
| 2 | Provider Registry (29 providers cataloged) | Done |
| 3 | Setup Guide + Smart Recommendations | Done |
| 4 | Provider Adapters (30 modules) + Credential Management | Done |
| 5 | Intelligent Workload Router (scoring, safety, fallback) | Done |
| 6 | Cost/Performance Optimization | Planned |

**Step 5 delivered:** Intelligent Router with lazy-init singleton, workload spec schema (4 types), decision engine (qubit-based + hardware-based routing), provider scoring (3 priority modes), safety filter (CPU/RAM hard limits with prediction), fallback chains (all terminate at safe default), 4 terminal commands, and 46 passing tests.

### Phase 4: Autonomous Agents — PLANNED
Sandboxed agent execution · Built-in agent library (Compute, Research, Optimization, Security, Hardware) · Multi-agent orchestration · User-defined agent creation

---

## Requirements

- **Python 3.10+** · **Windows 10/11** · **Git**
- Core: `customtkinter`, `numpy`, `psutil`
- Optional SDKs: `qiskit`, `amazon-braket-sdk`, `azure-quantum`, `cirq`, `pennylane`, `dwave-ocean-sdk`, `cupy-cuda12x`

---

## License

MIT License — See [LICENSE](LICENSE)

---

*"It's alive... and ready to serve science."*
