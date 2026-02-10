# FRANKENSTEIN 1.0

**Physics-Grounded AI Desktop Assistant - Quantum-Classical Hybrid Computing**

A terminal-based desktop assistant built on a Predictive Synthesis Engine that uses real quantum computing libraries (QuTiP, Qiskit, qencrypt) and numerical toolsets (NumPy, SciPy) with lazy-loading architecture for resource-constrained hardware.

## Quick Start

```bash
git clone https://github.com/nah414/Frankenstein-1.0.git
cd Frankenstein-1.0
pip install -r requirements.txt
python launch_terminal.py
```

Or double-click `RUN_FRANKENSTEIN.bat` on Windows.

---

## What It Does

- **70+ terminal commands** - Navigation, file ops, Git, SSH, scripting, environment management
- **Quantum simulation** - Statevector simulation up to 16 qubits with Bloch sphere visualization
- **Synthesis engine** - Schrodinger equation solver, Lorentz transformations, gate-based circuits
- **29 provider adapters** - IBM Quantum, AWS Braket, Azure Quantum, IonQ, Rigetti, and more (all lazy-loaded)
- **Intelligent routing** - Auto-selects optimal provider based on workload, hardware, and cost
- **5 local toolsets** - NumPy, SciPy, QuTiP, Qiskit, qencrypt integrated via lazy-loading layer

---

## Project Structure

```
Frankenstein-1.0/
|-- launch_terminal.py        # Entry point
|-- widget/                   # Terminal UI + Quantum REPL
|-- core/                     # Safety system, governor, memory, hardware monitor
|-- synthesis/                # Predictive Synthesis Engine + Compute Engine
|-- agents/                   # AI agents (5 registered, all lazy-loaded)
|   |-- builtin/
|       |-- compute.py                    # General compute agent
|       |-- quantum_dynamics_agent.py     # QuTiP wrapper
|       |-- quantum_hardware_agent.py     # Qiskit wrapper
|       |-- quantum_crypto_agent.py       # qencrypt wrapper
|       |-- numerical_computing_agent.py  # NumPy/SciPy wrapper
|-- libs/                     # Local toolset integration layer
|-- integration/              # Provider discovery, credentials, adapters
|-- router/                   # Intelligent workload router
|-- security/                 # Shield, filters, audit, monitoring
|-- tests/                    # Unit + integration tests
|-- scripts/                  # Verification and monitoring tools
|-- docs/                     # Toolset audit, installation guides
```

---

## Safety Constraints

| Limit | Value | Enforcement |
|-------|-------|-------------|
| CPU | Max 80% | Advisory throttle |
| RAM | Max 75% | Hard gate on toolset loading |
| Auto-throttle | 5-level progressive | Automatic downgrade |
| Lazy loading | All modules | Nothing loads until called |

---

## Development Roadmap

### Phase 1: Core Engine - COMPLETE
Safety system, resource governor, memory persistence, task orchestrator, Monster Terminal (70+ commands)

### Phase 2: Predictive Synthesis - COMPLETE
Security dashboard, hardware health monitor, quantum-classical synthesis engine, Bloch sphere visualization, compute swarms, relativistic quantum integration, data pipeline, lab monitors

### Phase 3: Universal Integration - COMPLETE (Steps 1-5)
Hardware discovery, provider registry (29 providers), setup guide, provider adapters + credential management, intelligent workload router (scoring, safety, fallback)

### Phase 3.5: Local Toolset Integration - COMPLETE
Lazy-loading integration layer for 5 scientific toolsets, 4 dedicated agents (quantum dynamics, quantum hardware, quantum crypto, numerical computing), synthesis engine refactored to use integration layer, quantum mode expanded with 7 new commands, 66-test suite, resource monitor

### Phase 4: Autonomous Agents - PLANNED
Sandboxed agent execution, multi-agent orchestration, user-defined agents

### Phase 5: Real-Time Adaptation - PLANNED
Dynamic provider switching, learning-based routing, security integration

---

## Requirements

- **Python 3.10+** | **Windows 10/11** | **Git**
- Core: `customtkinter`, `numpy`, `scipy`, `psutil`
- Quantum: `qutip`, `qiskit`
- Crypto: `qencrypt-local` (local editable install)
- Optional cloud SDKs: `qiskit-ibm-runtime`, `amazon-braket-sdk`, `azure-quantum`

---

## License

MIT License - See [LICENSE](LICENSE)
