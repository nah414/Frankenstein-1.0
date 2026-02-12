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

- **74+ terminal commands** - Navigation, file ops, Git, SSH, scripting, environment management
- **Quantum simulation (Phase 2 Enhanced)** - Statevector simulation up to 16 qubits with MCX gates (15 controls + 1 target)
  - 26 quantum gates including multi-controlled gates with 3-tier optimization
  - NumPy statevector (3-7 controls), SciPy sparse matrices (8-15 controls)
  - Bloch sphere visualization (Three.js 3D, Matplotlib 2D/3D)
- **Synthesis engine** - Schrodinger equation solver, Lorentz transformations, gate-based circuits
- **29 provider adapters** - IBM Quantum, AWS Braket, Azure Quantum, IonQ, Rigetti, and more (all lazy-loaded)
- **Intelligent routing** - Auto-selects optimal provider based on workload, hardware, and cost
- **Permissions & automation** - Role-based access control, 6 automated workflows, task scheduler
- **6 local toolsets** - NumPy, SciPy, QuTiP, Qiskit, Matplotlib, qencrypt integrated via lazy-loading layer

---

## Quantum Mode Features (v1.2.0)

**Enhanced Multi-Controlled Gates**
```bash
quantum
qubit 16

# Toffoli (2 controls)
mcx 0,1 2

# C³X (3 controls - NumPy)
mcx 0,1,2 3

# C⁷X (7 controls - SciPy sparse)
mcx 0,1,2,3,4,5,6 7

# C¹⁵X (15 controls - Maximum capacity!)
mcx 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 15

measure
```

**Complete Gate Set (26 Commands)**
- **Pauli Gates**: h, x, y, z
- **Phase Gates**: s, t, sdg, tdg, sx, sxdg, p
- **Rotation Gates**: rx, ry, rz
- **Two-Qubit**: cx, cy, cz, ch, cp, swap, cswap
- **Multi-Controlled**: mcx (up to 16 qubits)
- **Measurement**: measure, mx, my, prob, state
- **Visualization**: bloch (3D), bloch2d (2D), bloch2d 3d (interactive)

**Performance Benchmarks (Tier 1 Hardware)**
| Control Count | Algorithm | Time |
|---------------|-----------|------|
| 1-2 controls | Gate decomposition | <5ms |
| 3-7 controls | NumPy statevector | ~50ms |
| 8-15 controls | SciPy sparse matrices | ~200ms |

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
|-- permissions/              # Role-based access control, audit logging
|-- automation/               # Task scheduler, automated workflows
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
| RAM | Max 75% (90% for Bloch visualization) | Hard gate on toolset loading |
| Auto-throttle | 5-level progressive | Automatic downgrade |
| Lazy loading | All modules | Nothing loads until called |
| MCX Gate Limit | 15 controls + 1 target (16 qubits) | Tier 1 hardware validation |

---

## Development Roadmap

### Phase 1: Core Engine - COMPLETE
Safety system, resource governor, memory persistence, task orchestrator, Monster Terminal (70+ commands)

### Phase 2: Predictive Synthesis - COMPLETE ✅
Security dashboard, hardware health monitor, quantum-classical synthesis engine, Bloch sphere visualization, compute swarms, relativistic quantum integration, data pipeline, lab monitors

**Phase 2 Enhancement (v1.2.0) - COMPLETE ✅**
- **MCX Gates Enhanced**: 16-qubit support (15 controls + 1 target) with 3-tier optimization
- **26 Quantum Gates**: Complete gate set including sdg, tdg, sx, sxdg, cy, ch, cp, swap, cswap
- **Matplotlib Integration**: 2D/3D Bloch sphere visualization with 90% RAM override for graphics
- **Performance Tiers**: Gate decomposition (<5ms), NumPy statevector (~50ms), SciPy sparse (~200ms)
- **Enhanced Documentation**: Full gate inventory visible on quantum mode startup

### Phase 3: Universal Integration - COMPLETE ✅ (Steps 1-6)
Hardware discovery, provider registry (29 providers), setup guide, provider adapters + credential management, intelligent workload router (scoring, safety, fallback), permissions & automation system (4 roles, 6 workflows, task scheduler)

### Phase 3.5: Local Toolset Integration - COMPLETE ✅
Lazy-loading integration layer for 6 scientific toolsets (NumPy, SciPy, QuTiP, Qiskit, Matplotlib, qencrypt), 4 dedicated agents (quantum dynamics, quantum hardware, quantum crypto, numerical computing), synthesis engine refactored to use integration layer, quantum mode expanded with 26 commands, 66-test suite, resource monitor

### Phase 4: Autonomous Agents - PLANNED
Sandboxed agent execution, multi-agent orchestration, user-defined agents

### Phase 5: Real-Time Adaptation - PLANNED
Dynamic provider switching, learning-based routing, security integration

---

## Requirements

- **Python 3.10+** | **Windows 10/11** | **Git**
- Core: `customtkinter`, `numpy>=2.3.5`, `scipy>=1.16.3`, `psutil`
- Quantum: `qutip>=5.2.3`, `qiskit`
- Visualization: `matplotlib>=3.10.8`
- Crypto: `qencrypt-local` (local editable install)
- Optional cloud SDKs: `qiskit-ibm-runtime`, `amazon-braket-sdk`, `azure-quantum`

---

## License

MIT License - See [LICENSE](LICENSE)
