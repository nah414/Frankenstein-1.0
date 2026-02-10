# FRANKENSTEIN 1.0 - Local Toolset Audit Report
## Phase 3.5: Local Toolset Integration

**Date:** 2026-02-09
**Audited by:** Claude Code (Phase 3.5 Step 1)
**Python version:** 3.12.10
**System:** Dell i3 8th Gen, 4 cores, 8GB RAM, Windows

---

## Executive Summary

All 5 local toolsets have been located and audited in `C:\Users\adamn\Downloads\`.
Each toolset's directory structure, build system, dependencies, import patterns,
and installation method have been documented below.

### Key Findings

| Toolset | Build System | Install Method | Python Req | Currently Installed | Import Name |
|---------|-------------|----------------|------------|-------------------|-------------|
| numpy-main | meson-python | Requires C compilation (meson build) | >=3.12 | YES (pip 2.3.5) | `numpy` |
| scipy-main | meson-python | Requires C/Fortran compilation (meson build) | >=3.12 | YES (pip 1.16.3) | `scipy` |
| qutip-master | setuptools + Cython | `pip install -e .` (has setup.py) | >=3.10 | NO | `qutip` |
| qiskit-main | setuptools + Rust | Requires Rust toolchain (setuptools-rust) | >=3.10 | YES (pip 2.2.3) | `qiskit` |
| qencrypt-local | setuptools | `pip install -e .` (pure Python) | >=3.10 | NO | `qencrypt_local` |

### Critical Discovery: Build Complexity

**numpy-main and scipy-main** use the `meson-python` build system with C/Cython/Fortran
compilation. These CANNOT be trivially installed with `pip install -e .` from source
without a full C compiler toolchain and meson. Since working pip versions (numpy 2.3.5,
scipy 1.16.3) are already installed, the integration layer should use **sys.path
insertion** to access the local source tree's pure-Python modules, while falling back
to the already-installed pip versions for compiled extensions.

**qiskit-main** requires `setuptools-rust` and a Rust toolchain (Cargo.toml present).
A working pip version (2.2.3) is already installed. Same strategy applies.

**qutip-master** uses setuptools + Cython with a setup.py that compiles C++ extensions.
It requires Cython and numpy at build time. NOT currently installed.

**qencrypt-local** is pure Python with a clean src-layout. Simplest to install via
`pip install -e .` or sys.path insertion to `src/`.

---

## Detailed Audit: Toolset #1 - numpy-main

### Location
`C:\Users\adamn\Downloads\numpy-main\numpy-main\`

### Directory Structure
```
numpy-main/
  pyproject.toml          (meson-python build system)
  meson.build             (meson build configuration)
  meson.options           (meson build options)
  numpy/                  (source package)
    __init__.py
    _core/                (C extensions, compiled)
    linalg/               (linear algebra - wraps LAPACK)
    fft/                  (FFT - pocketfft)
    random/               (random number generation)
    ma/                   (masked arrays)
    ...
  vendored-meson/         (vendored meson build tool)
  requirements/           (build/test requirements)
```

### Build System
- **Backend:** `mesonpy` (meson-python)
- **Build requires:** `meson-python>=0.18.0`, `Cython>=3.0.6`
- **Compilation:** Heavy C/C++ compilation required (LAPACK, BLAS, SIMD)

### Version
- **Source version:** `2.5.0.dev0` (development branch)
- **Installed pip version:** `2.3.5` (stable release)

### Dependencies
- No runtime Python dependencies (self-contained)
- Build-time: C compiler, Cython, meson-python

### Import Pattern
```python
import numpy
import numpy as np
from numpy import linalg, fft, random
```

### Installation Method
- **Recommended:** Use pip-installed version (2.3.5) as primary
- **Local source access:** sys.path insertion for pure-Python utilities only
- **Full build from source:** Requires meson, C compiler, OpenBLAS - NOT recommended on this system
- **Editable install:** NOT supported with meson-python build backend on this system without full toolchain

### Estimated RAM Footprint
- ~80-150 MB when fully loaded
- Core array operations: ~50 MB
- Additional submodules loaded on demand

---

## Detailed Audit: Toolset #2 - scipy-main

### Location
`C:\Users\adamn\Downloads\scipy-main\scipy-main\`

### Directory Structure
```
scipy-main/
  pyproject.toml          (meson-python build system)
  meson.build             (meson build configuration)
  scipy/                  (source package)
    __init__.py
    linalg/               (linear algebra)
    integrate/            (numerical integration)
    optimize/             (optimization algorithms)
    fft/                  (Fast Fourier Transform)
    signal/               (signal processing)
    sparse/               (sparse matrices)
    stats/                (statistics)
    special/              (special functions)
    interpolate/          (interpolation)
    ...
  subprojects/            (meson subprojects)
  requirements/           (build/test requirements)
```

### Build System
- **Backend:** `mesonpy` (meson-python)
- **Build requires:** `meson-python>=0.15.0`, `Cython>=3.0.8`, `pybind11>=2.13.2`, `pythran>=0.14.0`, `numpy>=2.0.0`
- **Compilation:** Heavy C/C++/Fortran compilation required

### Version
- **Source version:** `1.18.0.dev0` (development branch)
- **Installed pip version:** `1.16.3` (stable release)

### Dependencies
- **Runtime:** `numpy>=2.0.0`
- **Build-time:** C/C++/Fortran compilers, Cython, pybind11, pythran, meson-python

### Import Pattern
```python
import scipy
from scipy import linalg, integrate, optimize, fft, signal
from scipy.linalg import expm, eigh
from scipy.integrate import solve_ivp
```

### Installation Method
- **Recommended:** Use pip-installed version (1.16.3) as primary
- **Local source access:** sys.path insertion for pure-Python algorithms only
- **Full build from source:** Requires meson, C/Fortran compilers, BLAS/LAPACK - NOT recommended
- **Editable install:** NOT supported with meson-python build backend

### Estimated RAM Footprint
- ~100-200 MB when fully loaded
- Individual submodules: ~20-50 MB each
- Loaded on demand per submodule

---

## Detailed Audit: Toolset #3 - qutip-master

### Location
`C:\Users\adamn\Downloads\qutip-master\qutip-master\`

### Directory Structure
```
qutip-master/
  pyproject.toml          (setuptools build system)
  setup.py                (Cython extension compilation)
  VERSION                 (version file)
  requirements.txt        (cython>=0.29.20, numpy>=1.22, scipy>=1.8, packaging)
  qutip/                  (source package)
    __init__.py           (imports core/*, solver/*, bloch, visualization, etc.)
    core/                 (quantum objects, operators, data structures)
    solver/               (mesolve, sesolve, brmesolve, nonmarkov)
    bloch.py              (Bloch sphere visualization)
    entropy.py            (quantum entropy measures)
    random_objects.py     (random quantum states/operators)
    measurement.py        (quantum measurement)
    tomography.py         (quantum state tomography)
    distributions.py      (Wigner, Q-function distributions)
    continuous_variables.py
    ...
```

### Build System
- **Backend:** `setuptools.build_meta`
- **Build requires:** `setuptools>=77.0.3`, `packaging`, `wheel`, `cython>=0.29.20`, `numpy>=2.0.0`, `scipy>=1.9`
- **setup.py:** Compiles Cython (.pyx) extensions to C++ with numpy includes
- **Compilation:** Cython -> C++ required for core data structures

### Version
- **Source version:** Read from `VERSION` file (dev release)
- **Installed:** NOT installed

### Dependencies
- **Runtime:** `numpy>=1.22`, `scipy>=1.9,!=1.16.0,!=1.17.0`, `packaging`
- **Build-time:** Cython, numpy, scipy, setuptools
- **Optional:** matplotlib (graphics), cvxpy (SDP), mpi4py (parallel)

### Import Pattern
```python
import qutip
from qutip import basis, sigmax, sigmay, sigmaz, mesolve, Qobj
from qutip.solver import mesolve, sesolve
from qutip.core import data
```

### Installation Method
- **Primary:** `pip install -e .` from `qutip-master/qutip-master/` (requires Cython + C compiler)
- **Fallback:** sys.path insertion for pure-Python modules only (solver logic, entropy, etc.)
- **Note:** scipy!=1.16.0 conflict with currently installed scipy 1.16.3 - may need version check

### IMPORTANT: SciPy Version Conflict
The qutip pyproject.toml specifies `scipy>=1.9,!=1.16.0,!=1.17.0` but the system has
scipy 1.16.3 installed. Version 1.16.3 is NOT in the exclusion list (only 1.16.0 is
excluded), so this should be compatible.

### Estimated RAM Footprint
- ~150-300 MB when fully loaded (depends on solver usage)
- Core quantum objects: ~50 MB
- Solvers loaded on demand: ~50-100 MB each

---

## Detailed Audit: Toolset #4 - qiskit-main

### Location
`C:\Users\adamn\Downloads\qiskit-main\qiskit-main\`

### Directory Structure
```
qiskit-main/
  pyproject.toml          (setuptools + setuptools-rust)
  setup.py                (setuptools build)
  Cargo.toml              (Rust workspace)
  Cargo.lock              (Rust dependency lock)
  crates/                 (Rust source code for _accelerate module)
  requirements.txt        (rustworkx>=0.15.0, numpy>=1.17, scipy>=1.5, dill, stevedore, typing-extensions)
  qiskit/                 (source package)
    __init__.py
    circuit/              (quantum circuit construction)
    compiler/             (circuit compilation)
    transpiler/           (circuit transpilation for hardware)
    providers/            (backend providers)
    quantum_info/         (quantum information tools)
    synthesis/            (circuit synthesis)
    qasm2/                (OpenQASM 2.0 support)
    qasm3/                (OpenQASM 3.0 support)
    qpy/                  (Qiskit binary serialization)
    visualization/        (circuit visualization)
    ...
```

### Build System
- **Backend:** `setuptools.build_meta`
- **Build requires:** `setuptools>=77.0`, `setuptools-rust`
- **Compilation:** Rust compilation required (Cargo workspace with crates/)
- **Rust toolchain:** Required for `qiskit._accelerate` module

### Version
- **Source version:** Read from `qiskit/VERSION.txt`
- **Installed pip version:** `2.2.3` (stable release)

### Dependencies
- **Runtime:** `rustworkx>=0.15.0`, `numpy>=1.17,<3`, `scipy>=1.5`, `dill>=0.3`, `stevedore>=3.0.0`, `typing-extensions`
- **Build-time:** setuptools, setuptools-rust, Rust compiler
- **Optional:** matplotlib, pydot, Pillow, pylatexenc, seaborn, sympy (visualization)

### Import Pattern
```python
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler import PassManager
from qiskit.quantum_info import Statevector, Operator
from qiskit.providers import BackendV2
```

### Installation Method
- **Recommended:** Use pip-installed version (2.2.3) as primary
- **Local source access:** sys.path insertion for pure-Python modules (circuit, transpiler, etc.)
- **Full build from source:** Requires Rust toolchain - NOT recommended on this system
- **Note:** The pip version already includes compiled Rust extensions

### Estimated RAM Footprint
- ~200-400 MB when fully loaded
- Circuit construction: ~50 MB
- Transpiler: ~100 MB
- Provider interface: ~50 MB

---

## Detailed Audit: Toolset #5 - qencrypt-local

### Location
`C:\Users\adamn\Downloads\qencrypt-local\qencrypt-local\`

### Directory Structure
```
qencrypt-local/
  pyproject.toml          (setuptools, pure Python)
  requirements.txt        (cryptography, qiskit, qiskit-ibm-runtime, streamlit)
  pytest.ini              (test configuration)
  src/                    (src-layout package)
    qencrypt_local/
      __init__.py         (exports: encrypt_text, decrypt_text)
      cli.py              (CLI entry point)
      crypto.py           (AES-256-GCM encryption with quantum entropy)
      quantum_entropy.py  (quantum entropy source - IBM Quantum or fallback)
      schema.py           (encryption package schema validation)
  tests/                  (test suite)
  scripts/                (utility scripts)
  wolfram/                (Wolfram integration)
  app_streamlit.py        (Streamlit web UI)
```

### Build System
- **Backend:** `setuptools.build_meta`
- **Build requires:** `setuptools>=68`, `wheel`
- **Compilation:** NONE - pure Python package
- **Layout:** src-layout (`package-dir = {"" = "src"}`)

### Version
- `0.1.0`
- **Installed:** NOT installed

### Dependencies
- **Runtime:** `cryptography>=42.0.0`, `qiskit>=1.0.0`, `qiskit-ibm-runtime>=0.20.0`
- **Optional:** `streamlit>=1.31.0` (UI), `pytest>=8.0.0`, `ruff>=0.5.0` (dev)
- **Note:** Depends on qiskit, which is already installed (2.2.3)

### Import Pattern
```python
import qencrypt_local
from qencrypt_local import encrypt_text, decrypt_text
from qencrypt_local.crypto import encrypt_text, decrypt_text
from qencrypt_local.quantum_entropy import get_entropy, EntropySource
```

### Key API
- `encrypt_text(plaintext, passphrase, *, entropy_source, entropy_bytes, num_qubits, shots, scrypt_n, scrypt_r, scrypt_p)` -> EncryptionPackage
- `decrypt_text(pkg, passphrase)` -> str
- Uses AES-256-GCM with quantum entropy seeding (IBM Quantum or OS fallback)
- HKDF-SHA256 key derivation with XOR mixing of quantum + OS entropy

### Installation Method
- **Primary:** `pip install -e C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local`
- **Alternative:** sys.path insertion to `src/` directory
- **Simplest to install** - pure Python, no compilation needed

### Estimated RAM Footprint
- ~30-50 MB (lightweight, pure Python)
- Depends on cryptography library (~20 MB)
- Quantum entropy generation adds qiskit overhead only when used

---

## Integration Strategy Recommendations

### Tier 1: Direct pip install -e (Simplest)
1. **qencrypt-local** - Pure Python, src-layout, no compilation. Install immediately.

### Tier 2: pip install -e with compilation (Moderate)
2. **qutip-master** - Requires Cython + C compiler. Installable if MSVC is present.

### Tier 3: Use existing pip versions + local source overlay (Complex)
3. **numpy-main** - Use pip numpy 2.3.5. Access local source for reference/utilities only.
4. **scipy-main** - Use pip scipy 1.16.3. Access local source for reference/utilities only.
5. **qiskit-main** - Use pip qiskit 2.2.3. Access local source for pure-Python extensions only.

### RAM Budget (75% of 8GB = 6GB max)

| Component | Estimated RAM | Load Trigger |
|-----------|--------------|-------------|
| Base system + Terminal | ~500 MB | Startup |
| numpy (already loaded by others) | ~100 MB | On first numerical operation |
| scipy | ~150 MB | On first scientific computation |
| qutip | ~200 MB | On quantum dynamics request |
| qiskit (already installed) | ~250 MB | On circuit/transpilation request |
| qencrypt-local | ~40 MB | On encryption request |
| **Total if ALL loaded** | **~1240 MB** | Never all at once |
| **Headroom** | **~4760 MB** | Safety margin |

### Lazy-Loading Priority Order
1. numpy (most frequently needed, often already loaded)
2. scipy (needed for linalg, integration)
3. qiskit (needed for quantum circuits - already pip-installed)
4. qutip (needed for master equations, decoherence)
5. qencrypt-local (needed only for encryption operations)

---

## Existing Project Compatibility Notes

### BaseAgent Interface (agents/base.py)
The spec's agent templates use `super().__init__(name=..., description=..., capabilities=...)`,
but the actual BaseAgent.__init__() takes NO parameters. Agent metadata is set via class
attributes (`name`, `description`, `version`). The new agents must use class-level attributes
instead:

```python
class QuantumDynamicsAgent(BaseAgent):
    name = "quantum_dynamics"
    description = "Quantum system evolution with decoherence"
    # NOT: super().__init__(name="...", description="...", capabilities=[...])
```

### Agent Registry (agents/registry.py)
Uses a `register(agent_class)` method, not a dictionary literal. New agents must call:
```python
registry = get_registry()
registry.register(QuantumDynamicsAgent)
```

### Synthesis Engine Location
The actual compute engine is at `synthesis/compute/engine.py`, NOT `synthesis/engine.py`
as stated in the spec. The imports at line 9 are `import numpy as np` - standard pip import.

### Import Name: qencrypt-local
The package import name is `qencrypt_local` (underscore), NOT `qencrypt` (as the spec assumes).
The integration layer must map `qencrypt` -> `qencrypt_local` appropriately.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| numpy/scipy source build fails (no meson/C compiler) | HIGH | Use pip-installed versions as primary, local source as reference only |
| qutip Cython compilation fails | MEDIUM | Try pip install -e first; fall back to sys.path for pure-Python modules |
| qiskit Rust build fails | HIGH | Use pip-installed version (2.2.3); local source for Python-only access |
| RAM overflow if multiple toolsets loaded simultaneously | MEDIUM | Lazy-loading manager with 75% RAM cap enforced |
| Import name conflict (pip vs local) | MEDIUM | Use sys.path ordering carefully; document precedence |
| qutip scipy version conflict | LOW | scipy 1.16.3 is NOT in qutip's exclusion list |

---

## Conclusion

All 5 toolsets are present and auditable. The integration approach must account for the
fact that numpy, scipy, and qiskit are **already pip-installed** in working versions, while
qutip and qencrypt-local are **not installed**. The local source trees for numpy/scipy/qiskit
use complex build systems (meson/Rust) that make editable installs impractical on this system.

The recommended approach is a **hybrid strategy**: use pip-installed versions as the runtime
backbone, install qencrypt-local via `pip install -e .`, attempt qutip installation, and
provide the `LocalToolsetManager` as a unified lazy-loading interface that abstracts these
details from the rest of the application.
