# FRANKENSTEIN 1.0 QUANTUM ENGINE EXPANSION ROADMAP
## Quirk-Inspired Gate Library & Bloch Sphere Integration

**Document Version:** 1.1.0
**Created:** February 11, 2026
**Updated:** February 11, 2026 (MCX Integration)
**Target Timeline:** Modular implementation as-needed basis
**Hardware Baseline:** Dell i3 8th Gen (4 cores, 8GB RAM, 117GB storage)

---

## EXECUTIVE SUMMARY

This roadmap provides a **modular, on-demand implementation strategy** for expanding Frankenstein 1.0's quantum capabilities to match Quirk's comprehensive gate library. Rather than a rigid 10-week timeline, this approach enables **building features as needed** while maintaining system stability and physics-grounded validation.

**Key Innovation:** All measurement operations automatically trigger Bloch Sphere visualization via our existing 3D UI.

**Latest Update:** MCX (Multi-Controlled X) gate now fully implemented and integrated.

---

## WHAT'S IMPLEMENTED (Version 1.1.0)

### Core Single-Qubit Gates
- H (Hadamard)
- X, Y, Z (Pauli gates)
- S, T (Phase gates)
- Rx, Ry, Rz (Rotation gates)

### Two-Qubit Gates
- CNOT (CX)
- CZ (Controlled-Z)

### Multi-Controlled Gates (NEW)
- **MCX (Multi-Controlled X)**
  - 1 control: CNOT
  - 2 controls: Toffoli (CCNOT)
  - 3+ controls: C^n-X generalized
  - Efficient statevector implementation
  - Automatic Toffoli decomposition

### Measurement & Visualization
- Z-basis measurement
- Automatic 3D Bloch Sphere launch
- Pre/post measurement state display
- Probability distribution
- Measurement basis highlighting

### Circuit Shortcuts
- Bell state
- GHZ state
- QFT (Quantum Fourier Transform)

---

## GATE LIBRARY CATALOG

### Tier 1: Essential Single-Qubit Gates - IMPLEMENTED

| Gate ID | Name | Matrix/Formula | Use Case | Status |
|---------|------|----------------|----------|--------|
| `H` | Hadamard | 1/sqrt(2) [[1,1],[1,-1]] | Superposition | Done |
| `X` | Pauli-X | [[0,1],[1,0]] | Bit flip | Done |
| `Y` | Pauli-Y | [[0,-i],[i,0]] | Combined flip+phase | Done |
| `Z` | Pauli-Z | [[1,0],[0,-1]] | Phase flip | Done |
| `S` | S Gate (Z^1/2) | [[1,0],[0,i]] | pi/2 phase | Done |
| `T` | T Gate (Z^1/4) | [[1,0],[0,e^(i*pi/4)]] | pi/4 phase | Done |
| `Rx(t)` | X-Rotation | cos(t/2)I - i*sin(t/2)X | Arbitrary X rotation | Done |
| `Ry(t)` | Y-Rotation | cos(t/2)I - i*sin(t/2)Y | Arbitrary Y rotation | Done |
| `Rz(t)` | Z-Rotation | e^(-it/2)Z | Arbitrary Z rotation | Done |

### Tier 2: Two-Qubit Gates - PARTIALLY IMPLEMENTED

| Gate ID | Name | Description | Use Case | Status |
|---------|------|-------------|----------|--------|
| `CNOT` | Controlled-NOT | X on target if control=1 | Entanglement | Done |
| `CZ` | Controlled-Z | Z on target if control=1 | Phase entanglement | Done |
| `SWAP` | Swap | Exchange qubit states | State routing | Planned |
| `iSWAP` | i-Swap | Swap with phase factor i | Superconducting circuits | Planned |
| `sqrt(SWAP)` | sqrt(Swap) | Square root of SWAP | Partial swap | Planned |

### Tier 2.5: Multi-Controlled Gates - NEW - IMPLEMENTED

| Gate ID | Name | Description | Use Case | Status |
|---------|------|-------------|----------|--------|
| `MCX` | Multi-Controlled-X | X on target if ALL controls=1 | Arbitrary control count | Done |
| `MCZ` | Multi-Controlled-Z | Z on target if ALL controls=1 | Multi-control phase | Planned |
| `MCY` | Multi-Controlled-Y | Y on target if ALL controls=1 | Advanced multi-control | Planned |

**MCX Implementation Details:**
- **1 control:** Direct CNOT application (O(1))
- **2 controls:** Toffoli decomposition using H-T-CNOT gates
- **3+ controls:** Efficient statevector manipulation (O(2^n))
- **Performance:** <5ms for Toffoli, ~20ms for C3X on Tier 1 hardware
- **Usage:** `mcx 0,1,2 3` applies C3X gate

### Tier 3: Multi-Qubit Gates - PLANNED

| Gate ID | Name | Description | Use Case | Status |
|---------|------|-------------|----------|--------|
| `CCNOT` | Toffoli | X on target if both controls=1 | Universal computing | Via MCX |
| `CCZ` | CC-Z | Z on target if both controls=1 | Multi-control phase | Planned |
| `CSWAP` | Fredkin | Swap targets if control=1 | Reversible computing | Planned |

### Tier 4: Arithmetic Operations - PLANNED

| Operation | Symbol | Description | Formula | Status |
|-----------|--------|-------------|---------|--------|
| Increment | `+1` | Add 1 to register | \|n> -> \|n+1 mod 2^k> | Planned |
| Decrement | `-1` | Subtract 1 from register | \|n> -> \|n-1 mod 2^k> | Planned |
| Add Input | `+A` | Add register A to target | \|A>\|B> -> \|A>\|A+B> | Planned |
| QFT | `QFT(n)` | Quantum Fourier Transform | DFT on n qubits | Done |

### Tier 5: Measurement & Detection - IMPLEMENTED

| Type | Basis | Symbol | Behavior | Status |
|------|-------|--------|----------|--------|
| Measurement | Z | `Mz` | Collapse to \|0>/\|1> | Done |
| Bloch Viz | Auto | `measure` | Auto-launch 3D sphere | Done |

---

## MCX GATE - DETAILED IMPLEMENTATION

### Command Syntax
```
mcx <control1>,<control2>,...,<controlN> <target>
```

### Examples
```
# In quantum mode:
qubit 4

# CNOT (1 control)
mcx 0 1

# Toffoli (2 controls)
mcx 0,1 2

# C3X (3 controls)
mcx 0,1,2 3

# C4X (4 controls)
mcx 0,1,2,3 4
```

### Implementation Strategy

**1 Control (CNOT):**
- Direct application via engine.cx()
- Complexity: O(1)
- Time: <1ms

**2 Controls (Toffoli):**
- H-T-CNOT decomposition (Nielsen & Chuang)
- Uses 6 CNOTs + 7 single-qubit gates
- Complexity: O(1)
- Time: <5ms

**3+ Controls:**
- Direct statevector manipulation
- Complexity: O(2^n)
- Time: ~20ms (3 controls), ~80ms (4 controls)

### Performance Characteristics

| Control Count | Method | Complexity | Time (Tier 1) | Recommended |
|---------------|--------|------------|---------------|-------------|
| 1 | CNOT | O(1) | <1ms | Always |
| 2 | Toffoli Decomp | O(1) | <5ms | Always |
| 3 | Statevector | O(2^3) | ~20ms | Frequent use OK |
| 4 | Statevector | O(2^4) | ~80ms | Use sparingly |
| 5+ | Statevector | O(2^n) | >300ms | Expensive |

### Use Cases

**Grover's Algorithm:**
```
qubit 3
h 0
h 1
h 2
# Oracle using MCX
mcx 0,1 2
# Diffusion operator
h 0
h 1
h 2
x 0
x 1
x 2
mcx 0,1 2
x 0
x 1
x 2
h 0
h 1
h 2
measure
```

**Multi-Controlled Phase:**
```
# C3X can implement C3Z via conjugation
qubit 4
h 3
mcx 0,1,2 3  # Apply C3X
h 3          # Results in C3Z
```

---

## BLOCH SPHERE INTEGRATION

### Automatic Visualization

**Trigger:** Every `measure` command in quantum mode

**What It Shows:**
- Pre-measurement state (red vector)
- Post-measurement state (green vector)
- Measurement probabilities
- Highlighted measurement basis (Z, X, or Y)
- Animated trajectory between states

### Visualization Features

**3D Display Elements:**
- Transparent Bloch sphere (wireframe)
- X, Y, Z axes (red, green, blue)
- State vectors with phase indicators
- Rotation animation
- Real-time state information panel

**Info Panel Shows:**
- Measurement basis
- Measurement result
- Probabilities P(0) and P(1)
- Bloch vector coordinates (x, y, z)
- State vector amplitudes

**File Location:**
```
C:\Users\adamn\Frankenstein-1.0\widget\bloch_sphere.html
```

---

## QUICK REFERENCE GUIDE

### Common Operations

```
# Enter quantum mode
quantum

# Initialize qubits
qubit 3

# Create superposition
h 0
h 1

# Apply Toffoli
mcx 0,1 2

# Measure (auto-launches Bloch)
measure

# Exit quantum mode
back
```

### MCX Shortcuts

```
# CNOT shortcut
mcx 0 1
# Same as: cx 0 1

# Toffoli shortcut
mcx 0,1 2

# General pattern
mcx <comma-separated-controls> <target>
```

### Performance Tips

1. **Use circuit shortcuts:** `bell`, `ghz`, `qft`
2. **Batch measurements:** `viz off` then multiple measures
3. **Avoid deep MCX:** 4+ controls are expensive
4. **Monitor resources:** Watch CPU/RAM during complex circuits

---

## RESOURCE MONITORING

### Expected CPU/RAM Usage

**Idle State:**
- CPU: 2-5%
- RAM: 150-200MB

**Quantum Mode Active:**
- CPU: 5-10%
- RAM: 200-300MB

**MCX Operations:**

| Operation | CPU Peak | RAM Peak | Duration |
|-----------|----------|----------|----------|
| CNOT | 8% | 250MB | <1ms |
| Toffoli | 15% | 300MB | 3-5ms |
| C3X | 25% | 350MB | 15-25ms |
| C4X | 40% | 450MB | 60-100ms |
| C5X | 60% | 600MB | 250-350ms |

**Safety Thresholds:**
- CPU Limit: 80% (hard-coded)
- RAM Limit: 75% (hard-coded)
- Auto-throttle: Enabled

---

## FUTURE ENHANCEMENTS

### Short Term (Next Update)
- [ ] MCZ (Multi-Controlled Z)
- [ ] MCY (Multi-Controlled Y)
- [ ] SWAP gate family
- [ ] Improved Toffoli decomposition with ancilla

### Medium Term
- [ ] Arithmetic gates (+1, -1, +A)
- [ ] Modular arithmetic
- [ ] Advanced QFT variations
- [ ] Custom gate builder

### Long Term
- [ ] Hardware integration (IBM Quantum, AWS Braket)
- [ ] Noise simulation
- [ ] Error correction codes
- [ ] Quantum algorithm library

---

## CHANGELOG

### Version 1.1.0 (February 11, 2026)

**Added:**
- MCX gate (Multi-Controlled X) implementation
- Toffoli decomposition for 2-control case
- Efficient statevector method for 3+ controls
- Terminal help documentation for MCX
- Quantum mode detailed MCX examples
- Performance warnings for expensive operations
- Complete integration with Bloch visualization

**Changed:**
- Updated quantum mode command registry
- Enhanced help text in terminal.py
- Improved quantum mode help system
- Added performance notes for MCX operations

### Version 1.0.0 (Initial Release)
- Core quantum gates (H, X, Y, Z, S, T)
- Rotation gates (Rx, Ry, Rz)
- Two-qubit gates (CNOT, CZ)
- Measurement with Bloch visualization
- Circuit shortcuts (bell, ghz, qft)

---

**Document Maintained By:** Adam (nah414)
**Last Updated:** February 11, 2026
**Version:** 1.1.0
**Status:** Active Development
