# FRANKENSTEIN 1.0 - Local Toolset Installation Guide
## Phase 3.5: Local Toolset Integration

---

## Quick Start

```bash
# From the Frankenstein-1.0 project root:

# 1. Install core dependencies (if not already installed)
pip install -r requirements.txt

# 2. Install qencrypt-local from local source (editable)
pip install -e "C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local"

# 3. Verify all toolsets
python scripts/verify_toolsets.py
```

---

## Toolset Overview

| Toolset | Import Name | Version | Install Method | Purpose |
|---------|------------|---------|---------------|---------|
| NumPy | `numpy` | 2.3.5 | `pip install numpy` | Array computing, linear algebra, FFT |
| SciPy | `scipy` | 1.16.3 | `pip install scipy` | ODE solvers, optimization, matrix exponentials |
| QuTiP | `qutip` | 5.2.3 | `pip install qutip` | Quantum dynamics, master equations, decoherence |
| Qiskit | `qiskit` | 2.2.3 | `pip install qiskit` | Quantum circuits, transpilation, hardware interface |
| qencrypt-local | `qencrypt_local` | 0.1.0 | `pip install -e <path>` | Quantum-assisted AES-256-GCM encryption |

---

## Detailed Installation Instructions

### 1. NumPy (Numerical Computing)

NumPy provides the array and linear algebra foundation used throughout Frankenstein.

```bash
pip install "numpy>=2.0.0"
```

**Used by:** SynthesisEngine, ComputeEngine, all quantum agents, Bloch sphere
**RAM footprint:** ~120 MB when loaded
**Note:** NumPy is loaded eagerly by the synthesis engine (required for gate matrix definitions).

---

### 2. SciPy (Scientific Computing)

SciPy provides advanced numerical methods: ODE solvers (`solve_ivp`), matrix exponentials
(`expm`), optimization, and integration.

```bash
pip install "scipy>=1.9.0"
```

**Used by:** SynthesisEngine (Schrodinger evolution, unitary evolution), NumericalComputingAgent
**RAM footprint:** ~180 MB when loaded
**Note:** Loaded lazily on first use (not at startup). Falls back to NumPy-only methods if unavailable.

**Important:** QuTiP excludes scipy 1.16.0 and 1.17.0. Version 1.16.3 is compatible.

---

### 3. QuTiP (Quantum Dynamics)

QuTiP provides quantum object (`Qobj`) representation, master equation solvers (`mesolve`,
`sesolve`, `mcsolve`), steady-state computation, and entropy measures.

```bash
pip install "qutip>=5.0.0"
```

**Used by:** QuantumDynamicsAgent, quantum mode `decohere` and `mesolve` commands
**RAM footprint:** ~250 MB when loaded
**Note:** Lazy-loaded only when the user invokes decoherence or master equation commands.

**Warning about matplotlib:** QuTiP will emit a warning if matplotlib is not installed.
This is harmless — Frankenstein uses its own visualization system (3D Bloch sphere HTML).

**Building from source (optional):**
If you need the development version from local source, MSVC C++ Build Tools are required:
```bash
# Requires: Microsoft Visual C++ 14.0 or greater
# Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
pip install cython>=3.0.0
pip install -e "C:/Users/adamn/Downloads/qutip-master/qutip-master"
```

---

### 4. Qiskit (Quantum Hardware Interface)

Qiskit provides quantum circuit construction, transpilation for target hardware backends,
statevector/density-matrix simulation, and circuit optimization.

```bash
pip install "qiskit>=1.0.0"
```

**Used by:** QuantumHardwareAgent, quantum mode `transpile` command
**RAM footprint:** ~300 MB when loaded
**Note:** Lazy-loaded only when the user invokes transpilation or circuit analysis commands.

**Optional companion packages:**
```bash
pip install qiskit-ibm-runtime   # For IBM Quantum hardware access
pip install qiskit-aer           # For noise simulation
```

**Building from source (not recommended):**
Qiskit requires a Rust toolchain for the `_accelerate` module. Use the pip wheel.

---

### 5. qencrypt-local (Quantum Encryption)

qencrypt-local provides quantum-assisted text encryption using AES-256-GCM with quantum
entropy seeding (IBM Quantum hardware, simulator, or local OS entropy fallback).

**This package is NOT on PyPI.** It must be installed from local source:

```bash
pip install -e "C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local"
```

**Used by:** QuantumCryptoAgent, quantum mode `encrypt`, `decrypt`, `entropy` commands
**RAM footprint:** ~40 MB when loaded
**Note:** Pure Python package, no compilation needed. Depends on `cryptography` and `qiskit`.

**Source location:** `C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local/`
**Package layout:** src-layout (`src/qencrypt_local/`)
**API:**
- `qencrypt_local.encrypt_text(plaintext, passphrase, *, entropy_source='local')`
- `qencrypt_local.decrypt_text(package, passphrase)`

---

## Local Source Trees

The following source trees are available in Downloads for reference and development.
They are NOT required for normal operation — pip-installed packages are used at runtime.

| Source Tree | Path | Build System | Notes |
|-------------|------|-------------|-------|
| numpy-main | `C:/Users/adamn/Downloads/numpy-main/numpy-main/` | meson-python | C compilation required |
| scipy-main | `C:/Users/adamn/Downloads/scipy-main/scipy-main/` | meson-python | C/Fortran compilation required |
| qutip-master | `C:/Users/adamn/Downloads/qutip-master/qutip-master/` | setuptools+Cython | Requires MSVC C++ |
| qiskit-main | `C:/Users/adamn/Downloads/qiskit-main/qiskit-main/` | setuptools-rust | Requires Rust toolchain |
| qencrypt-local | `C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local/` | setuptools | Pure Python (editable install) |

---

## Safety Constraints

The integration layer (`libs/local_toolsets.py`) enforces resource limits:

- **RAM limit:** 75% of total system RAM (~6 GB on 8 GB system)
- **CPU advisory:** Logs warning when CPU exceeds 80%
- **Lazy loading:** Toolsets load ONLY when their agent or command is invoked
- **Graceful fallback:** If a toolset can't load (RAM limit, ImportError), the system
  falls back to pip-installed versions or degrades gracefully with a warning

---

## Verification

Run the verification script to check all toolsets:

```bash
python scripts/verify_toolsets.py
```

This will:
1. Check each toolset is importable
2. Verify the integration layer loads correctly
3. Test that each agent can be instantiated without loading its toolset
4. Confirm RAM and CPU limits are enforced
5. Report system resource usage

---

## Troubleshooting

### "matplotlib not found" warning from QuTiP
Harmless. Frankenstein uses its own HTML-based Bloch sphere visualization.
Install matplotlib only if you need QuTiP's built-in plots: `pip install matplotlib`

### qencrypt-local import fails
Ensure the editable install completed:
```bash
pip show qencrypt-local
# Should show: Version: 0.1.0, Location: ...
```
If missing, re-run: `pip install -e "C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local"`

### QuTiP build from source fails ("Microsoft Visual C++ 14.0 required")
Use the PyPI wheel instead: `pip install qutip`
The local source in Downloads requires MSVC C++ Build Tools for Cython compilation.

### RAM limit blocking toolset loads
Check current usage: enter quantum mode and type `toolsets`.
If RAM is above 75%, close other applications or unload unused toolsets.
The integration layer automatically refuses loads that would exceed the limit.

### scipy version conflict with QuTiP
QuTiP excludes scipy 1.16.0 and 1.17.0. Versions 1.16.1+ (except 1.17.0) are compatible.
Current installed version 1.16.3 works correctly.
