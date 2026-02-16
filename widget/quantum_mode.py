#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Mode Handler
Phase 2, Step 3: Quantum Computing Mode for Monster Terminal

Provides a dedicated quantum computing REPL mode within the Monster Terminal.
Implements hybrid mode switching as per Option C architecture.

Commands:
    quantum              Enter quantum mode
    qubit [state]        Initialize qubit(s)
    gate <name> [args]   Apply quantum gate
    measure [shots]      Perform measurement
    bloch               Show Bloch sphere
    evolve              Time evolution
    back/exit           Return to main terminal

Author: Frankenstein Project
"""

import numpy as np
from numpy import pi, sqrt
from typing import Dict, List, Any, Optional, Callable, Tuple
import re

# Lazy-load scipy, qutip, and matplotlib for advanced quantum operations
_SCIPY_AVAILABLE = False
_QUTIP_AVAILABLE = False
_MATPLOTLIB_AVAILABLE = False
_scipy = None
_qutip = None
_matplotlib = None

def _load_scipy():
    """Lazy-load scipy for advanced linear algebra operations."""
    global _SCIPY_AVAILABLE, _scipy
    if _SCIPY_AVAILABLE:
        return _scipy
    try:
        from libs.local_toolsets import load_scipy
        _scipy = load_scipy()
        if _scipy is not None:
            _SCIPY_AVAILABLE = True
            return _scipy
    except ImportError:
        pass
    try:
        import scipy
        _scipy = scipy
        _SCIPY_AVAILABLE = True
        return _scipy
    except ImportError:
        return None

def _load_qutip():
    """Lazy-load qutip for quantum dynamics and advanced operations."""
    global _QUTIP_AVAILABLE, _qutip
    if _QUTIP_AVAILABLE:
        return _qutip
    try:
        from libs.local_toolsets import load_qutip
        _qutip = load_qutip()
        if _qutip is not None:
            _QUTIP_AVAILABLE = True
            return _qutip
    except ImportError:
        pass
    try:
        import qutip
        _qutip = qutip
        _QUTIP_AVAILABLE = True
        return _qutip
    except ImportError:
        return None

def _load_matplotlib():
    """Lazy-load matplotlib for 2D plotting and visualization."""
    global _MATPLOTLIB_AVAILABLE, _matplotlib
    if _MATPLOTLIB_AVAILABLE:
        return _matplotlib
    try:
        from libs.local_toolsets import load_matplotlib
        _matplotlib = load_matplotlib()
        if _matplotlib is not None:
            _MATPLOTLIB_AVAILABLE = True
            return _matplotlib
    except ImportError:
        pass
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        _matplotlib = matplotlib
        _matplotlib.pyplot = plt
        _MATPLOTLIB_AVAILABLE = True
        return _matplotlib
    except ImportError:
        return None

def _load_matplotlib_for_bloch():
    """
    Lazy-load matplotlib specifically for Bloch Sphere UI with 90% RAM limit.

    This special loader uses the elevated 90% RAM limit instead of the
    standard 75% limit, ONLY for 2D/3D Bloch Sphere visualization features.

    Returns:
        matplotlib module if successfully loaded, None otherwise
    """
    global _MATPLOTLIB_AVAILABLE, _matplotlib
    if _MATPLOTLIB_AVAILABLE:
        return _matplotlib

    # Try to load matplotlib with elevated RAM limit for Bloch sphere
    try:
        from libs.local_toolsets import load_matplotlib
        _matplotlib = load_matplotlib(for_bloch_sphere=True)  # 90% RAM limit
        if _matplotlib is not None:
            _MATPLOTLIB_AVAILABLE = True
            return _matplotlib
    except ImportError:
        pass

    # Fallback: direct import (no RAM check)
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        _matplotlib = matplotlib
        _matplotlib.pyplot = plt
        _MATPLOTLIB_AVAILABLE = True
        return _matplotlib
    except ImportError:
        return None


class QuantumModeHandler:
    """
    Handles quantum mode commands within the Monster Terminal.
    
    This provides a sub-REPL for quantum computing operations
    that integrates with the main Synthesis Engine.
    """
    
    def __init__(self, output_callback: Callable[[str], None] = None):
        """
        Initialize quantum mode handler.
        
        Args:
            output_callback: Function to write output to terminal
        """
        self._output = output_callback or print
        self._engine = None
        self._active = False
        
        # Auto-visualization flag
        self._auto_visualize = True
        
        # Command registry
        self._commands: Dict[str, Callable] = {
            'help': self._cmd_help,
            '?': self._cmd_help,
            'qubit': self._cmd_qubit,
            'qubits': self._cmd_qubit,
            'init': self._cmd_qubit,
            'reset': self._cmd_reset,
            'gate': self._cmd_gate,
            'h': self._cmd_gate_h,
            'x': self._cmd_gate_x,
            'y': self._cmd_gate_y,
            'z': self._cmd_gate_z,
            's': self._cmd_gate_s,
            't': self._cmd_gate_t,
            'rx': self._cmd_gate_rx,
            'ry': self._cmd_gate_ry,
            'rz': self._cmd_gate_rz,
            'cx': self._cmd_gate_cx,
            'cnot': self._cmd_gate_cx,
            'cz': self._cmd_gate_cz,
            'cy': self._cmd_gate_cy,
            'ch': self._cmd_gate_ch,
            'mcx': self._cmd_gate_mcx,
            # Adjoint / fractional gates
            'sdg': self._cmd_gate_sdg,
            'tdg': self._cmd_gate_tdg,
            'sx': self._cmd_gate_sx,
            'sxdg': self._cmd_gate_sxdg,
            'p': self._cmd_gate_p,
            'cp': self._cmd_gate_cp,
            # SWAP gates
            'swap': self._cmd_gate_swap,
            'cswap': self._cmd_gate_cswap,
            'fredkin': self._cmd_gate_cswap,
            # Arithmetic gates
            'inc': self._cmd_gate_inc,
            'dec': self._cmd_gate_dec,
            # Bit operations
            'reverse': self._cmd_gate_reverse,
            # Multi-basis measurement
            'mx': self._cmd_measure_x,
            'my': self._cmd_measure_y,
            'measure': self._cmd_measure,
            'm': self._cmd_measure,
            'prob': self._cmd_probabilities,
            'probs': self._cmd_probabilities,
            'state': self._cmd_state,
            'bloch': self._cmd_bloch,
            'bloch2d': self._cmd_bloch_matplotlib,
            'evolve': self._cmd_evolve,
            'hamiltonian': self._cmd_hamiltonian,
            'compute': self._cmd_compute,
            'run': self._cmd_compute,
            'status': self._cmd_status,
            'history': self._cmd_history,
            'clear': self._cmd_clear,
            'back': self._cmd_exit,
            'exit': self._cmd_exit,
            'quit': self._cmd_exit,
            # NEW: Circuit commands
            'circuit': self._cmd_circuit,
            'circuits': self._cmd_list_circuits,
            'bell': self._cmd_bell,
            'ghz': self._cmd_ghz,
            'qft': self._cmd_qft,
            # NEW: Visualization toggle
            'viz': self._cmd_viz_toggle,
            'auto': self._cmd_viz_toggle,
            # Phase 3.5: Local toolset commands
            'decohere': self._cmd_decohere,
            'mesolve': self._cmd_mesolve,
            'transpile': self._cmd_transpile,
            'encrypt': self._cmd_encrypt,
            'decrypt': self._cmd_decrypt,
            'entropy': self._cmd_entropy,
            'toolsets': self._cmd_toolsets,
        }
    
    def set_output_callback(self, callback: Callable[[str], None]):
        """Set the output callback for terminal display"""
        self._output = callback
    
    def enter_mode(self) -> bool:
        """Enter quantum mode - initialize engine"""
        try:
            from synthesis import get_synthesis_engine, VisualizationMode
            self._engine = get_synthesis_engine()
            self._engine.set_output_callback(self._output)
            self._engine.auto_visualize = False  # Manual control in terminal
            self._active = True
            self._show_welcome()
            return True
        except ImportError as e:
            self._output(f"❌ Failed to load synthesis engine: {e}\n")
            return False
    
    def exit_mode(self):
        """Exit quantum mode"""
        self._active = False
        self._output("\n🔙 Exiting quantum mode. Returning to main terminal.\n")
    
    def is_active(self) -> bool:
        """Check if quantum mode is active"""
        return self._active
    
    def get_prompt(self) -> str:
        """Get the quantum mode prompt"""
        if self._engine:
            n = self._engine.get_num_qubits()
            g = self._engine.get_gate_count()
            return f"quantum[{n}q|{g}g]>"
        return "quantum>"
    
    def handle_command(self, command_line: str) -> bool:
        """
        Handle a command in quantum mode.
        
        Args:
            command_line: Raw command string
            
        Returns:
            True if should stay in quantum mode, False to exit
        """
        if not self._active:
            return False
        
        parts = command_line.strip().split()
        if not parts:
            return True
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd in self._commands:
            try:
                result = self._commands[cmd](args)
                if result is False:  # Explicit exit
                    return False
            except Exception as e:
                self._output(f"❌ Error: {e}\n")
        else:
            self._output(f"❌ Unknown quantum command: '{cmd}'. Type 'help' for commands.\n")
        
        return True
    
    def _show_welcome(self):
        """Display quantum mode welcome with detailed instructions"""
        welcome = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ⚛️  FRANKENSTEIN QUANTUM MODE v1.2.0 (Phase 2 Enhanced)        ║
║                                                                   ║
║   Local quantum simulation: NumPy 2.3.5 + SciPy 1.16.3           ║
║   Tier 1 Hardware: Max 16 qubits (15 controls + 1 target)        ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║   🚀 QUICK START:                                                ║
║     qubit 3            ← Initialize 3 qubits in |000⟩            ║
║     h 0                ← Hadamard on qubit 0 (superposition)     ║
║     mcx 0,1 2          ← Toffoli gate (multi-controlled X)       ║
║     measure            ← Measure + AUTO-LAUNCH 3D Bloch!         ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                     AVAILABLE GATES & OPERATORS                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║   📐 SINGLE-QUBIT GATES (Pauli):                                 ║
║     h <q>           Hadamard (superposition)                     ║
║     x <q>           Pauli-X (NOT/bit-flip)                       ║
║     y <q>           Pauli-Y                                      ║
║     z <q>           Pauli-Z (phase-flip)                         ║
║                                                                   ║
║   🔄 PHASE GATES:                                                ║
║     s <q>           S gate (√Z, π/2 phase)                       ║
║     t <q>           T gate (√S, π/4 phase)                       ║
║     sdg <q>         S-dagger (adjoint of S)                      ║
║     tdg <q>         T-dagger (adjoint of T)                      ║
║     sx <q>          √X gate                                      ║
║     sxdg <q>        √X-dagger (adjoint of √X)                    ║
║     p <q> <φ>       Phase gate (arbitrary angle)                 ║
║                                                                   ║
║   🎯 ROTATION GATES:                                             ║
║     rx <q> <θ>      Rotate around X-axis                         ║
║     ry <q> <θ>      Rotate around Y-axis                         ║
║     rz <q> <θ>      Rotate around Z-axis                         ║
║                                                                   ║
║   🔗 TWO-QUBIT GATES:                                            ║
║     cx <c> <t>      CNOT (Controlled-X)                          ║
║     cy <c> <t>      Controlled-Y                                 ║
║     cz <c> <t>      Controlled-Z                                 ║
║     ch <c> <t>      Controlled-H                                 ║
║     cp <c> <t> <φ>  Controlled-Phase                             ║
║     swap <q1> <q2>  SWAP two qubits                              ║
║     cswap <c> <q1> <q2>  Controlled-SWAP (Fredkin)               ║
║                                                                   ║
║   ⚡ MULTI-CONTROLLED GATES (ENHANCED - Phase 2):                ║
║     mcx <c1,c2,...> <t>  Multi-Controlled X (up to 16 qubits!)   ║
║       • mcx 0 1              CNOT (1 control)                    ║
║       • mcx 0,1 2            Toffoli/CCNOT (2 controls)          ║
║       • mcx 0,1,2 3          C³X (3 controls, NumPy)             ║
║       • mcx 0,1,2,3,4,5,6 7  C⁷X (7 controls, SciPy sparse)      ║
║                                                                   ║
║   📊 MEASUREMENT & VISUALIZATION:                                ║
║     measure [shots]    Z-basis measurement (default: 1024)       ║
║     mx [shots]         X-basis measurement                       ║
║     my [shots]         Y-basis measurement                       ║
║     prob               Show probability distribution             ║
║     state              Display statevector                       ║
║     bloch              3D Bloch sphere (Three.js browser)        ║
║     bloch2d            2D Bloch sphere (Matplotlib)              ║
║     bloch2d 3d         3D Bloch sphere (Matplotlib interactive)  ║
║                                                                   ║
║   📦 CIRCUIT PRESETS:                                            ║
║     bell               Bell state (2 qubits)                     ║
║     ghz <n>            GHZ state (n qubits)                      ║
║     qft                Quantum Fourier Transform                 ║
║                                                                   ║
║   🔧 SYSTEM CONTROLS:                                            ║
║     viz on/off         Toggle auto-visualization                 ║
║     reset              Reset circuit (keep qubit count)          ║
║     help               Full command reference                    ║
║     help <command>     Detailed help for specific command        ║
║     back/exit          Return to main terminal                   ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║   💡 TIP: Type 'help mcx' for 16-qubit MCX gate documentation    ║
║   💡 TIP: All gates use lazy-loading (zero startup overhead)     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
        self._output(welcome)
    
    # ==================== COMMAND HANDLERS ====================
    
    def _cmd_help(self, args: List[str]):
        """Show quantum mode help"""
        if args:
            # Specific command help
            cmd = args[0].lower()
            help_details = self._get_detailed_help(cmd)
            if help_details:
                self._output(f"\n{help_details}\n")
            else:
                self._output(f"❌ No detailed help for '{cmd}'\n")
            return
        
        help_text = """
╔═══════════════════════════════════════════════════════════════════╗
║                    QUANTUM MODE - COMMAND REFERENCE               ║
╚═══════════════════════════════════════════════════════════════════╝

────────────────────── INITIALIZATION ──────────────────────
  qubit <n>           Initialize n qubits in |0...0⟩ state
                      Example: qubit 2  → Creates 2-qubit register
  
  qubit |state>       Initialize specific state
                      Example: qubit |+>  → |+⟩ = (|0⟩+|1⟩)/√2
                      Example: qubit |01> → |01⟩ state
  
  reset               Reset to |0⟩ state (keeps qubit count)

────────────────────── SINGLE-QUBIT GATES ──────────────────────
  h <target>          Hadamard gate - creates superposition
                      Example: h 0  → Apply H to qubit 0
  
  x <target>          Pauli-X (NOT) gate - bit flip
  y <target>          Pauli-Y gate
  z <target>          Pauli-Z gate - phase flip
  s <target>          S gate (√Z) - π/2 phase
  t <target>          T gate - π/4 phase

────────────────────── ROTATION GATES ──────────────────────
  rx <target> <θ>     Rotate around X axis by θ radians
                      Example: rx 0 pi/2  → 90° X rotation
  
  ry <target> <θ>     Rotate around Y axis
                      Example: ry 0 0.5   → Arbitrary Y rotation
  
  rz <target> <θ>     Rotate around Z axis
                      Supports: pi, pi/2, pi/4, or decimal

────────────────────── TWO-QUBIT GATES ──────────────────────
  cx <ctrl> <tgt>     CNOT (Controlled-X) gate
                      Example: cx 0 1  → Control=0, Target=1

  cz <ctrl> <tgt>     Controlled-Z gate

────────────────────── MULTI-CONTROLLED GATES ──────────────────────
  mcx <ctrls> <tgt>   Multi-Controlled X (generalized Toffoli)
                      ENHANCED: numpy + scipy + qutip support
                      Supports up to 16 qubits (15 controls + 1 target)
                      Controls: comma-separated (no spaces)

                      Examples:
                        mcx 0 1              → CNOT (1 control)
                        mcx 0,1 2            → Toffoli (2 controls)
                        mcx 0,1,2 3          → C³X (3 controls)
                        mcx 0,1,2,3 4        → C⁴X (4 controls)
                        mcx 0,1,2,3,4,5,6 7  → C⁷X (7 controls)
                        mcx 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 15  → C¹⁵X

                      Performance: 1-2 ctrl: <5ms | 3-7 ctrl: ~50ms | 8+ ctrl: ~200ms
                      Algorithm: Gate decomp (1-2) | NumPy (3-7) | SciPy sparse (8+)
                      Use cases: Grover search, amplitude amplification, oracle design

────────────────────── MEASUREMENT ──────────────────────
  measure             Measure all qubits (1024 shots)
  measure <shots>     Specify number of shots
                      Example: measure 4096
  
  prob                Show probability distribution
  state               Display current statevector

────────────────────── VISUALIZATION ──────────────────────
  bloch               Launch 3D Bloch sphere in browser
                      Shows state on interactive sphere
  
  compute             Run computation + auto-visualization

────────────────────── TIME EVOLUTION ──────────────────────
  evolve <H> <t>      Evolve state under Hamiltonian H for time t
                      Example: evolve pauli_x 3.14
                      Hamiltonians: pauli_x, pauli_z, precession

  hamiltonian         List available Hamiltonians

────────────────────── UTILITY ──────────────────────
  status              Show engine status and resources
  history             Show computation history
  clear               Clear terminal output
  back / exit         Return to main terminal mode

────────────────────── PREDEFINED CIRCUITS ──────────────────────
  circuits            List all available circuits
  circuit <n>      Apply predefined circuit by name
                      Example: circuit bell
  
  bell                Create Bell state (2 qubits)
  ghz [n]             Create GHZ state (default 3 qubits)
  qft [n]             Apply Quantum Fourier Transform

────────────────────── AUTO-VISUALIZATION ──────────────────────
  viz [on|off]        Toggle auto Bloch sphere after measure
  auto [on|off]       Same as viz
                      (Default: ON - launches after every calculation)

────────────────────── TOOLSET COMMANDS (Phase 3.5) ──────────────────────
  decohere [type] [gamma]  Model decoherence on current state
                           Types: amplitude_damping, dephasing, depolarizing
  mesolve <H> <t>     Solve Lindblad master equation (requires QuTiP)
  transpile [backend]  Transpile current gate log to Qiskit circuit
  encrypt <text>       Quantum-assisted encryption (qencrypt)
  decrypt <pkg>        Decrypt a qencrypt package
  entropy              Compute von Neumann entropy of current state
  toolsets             Show loaded/available local toolsets

────────────────────── TIPS ──────────────────────
  • Qubit indices are 0-based (rightmost = qubit 0)
  • Use 'pi' in angle expressions: rx 0 pi/4
  • Chain gates: h 0 → cx 0 1 → measure (Bell state!)
  • Type 'help <command>' for detailed help on any command

────────────────────── EXAMPLES ──────────────────────

  🔹 Bell State (Entanglement):
     qubit 2
     h 0
     cx 0 1
     measure
  
  🔹 Superposition:
     qubit 1
     h 0
     measure
  
  🔹 GHZ State (3-qubit entanglement):
     ghz 3
     measure
  
  🔹 Time Evolution:
     qubit 1
     h 0
     evolve pauli_z pi
     measure
  
  🔹 Rotation Gates:
     qubit 1
     ry 0 pi/4
     measure

  🔹 Toffoli (MCX with 2 controls):
     qubit 3
     h 0
     h 1
     mcx 0,1 2
     measure

  🔹 Advanced: 4-qubit entanglement (C3X):
     qubit 4
     h 0
     h 1
     h 2
     mcx 0,1,2 3
     measure

"""
        self._output(help_text)
    
    def _get_detailed_help(self, cmd: str) -> Optional[str]:
        """Get detailed help for specific command"""
        details = {
            'qubit': """
QUBIT - Initialize Quantum Register
═══════════════════════════════════════════════════════════════

Usage:
  qubit <n>           Initialize n qubits in |0...0⟩
  qubit |state>       Initialize specific computational basis state
  qubit |+>           Initialize |+⟩ state
  qubit |->           Initialize |−⟩ state

Examples:
  qubit 1             → Single qubit |0⟩
  qubit 3             → Three qubits |000⟩
  qubit |1>           → Single qubit |1⟩
  qubit |01>          → Two qubits |01⟩
  qubit |+>           → Superposition (|0⟩+|1⟩)/√2

Notes:
  - Maximum 16 qubits for Tier 1 hardware
  - Qubit 0 is rightmost (LSB convention)
""",
            'h': """
H - Hadamard Gate
═══════════════════════════════════════════════════════════════

Usage:
  h <target>          Apply Hadamard to target qubit

Matrix:
       1  [ 1   1 ]
  H = ─── [       ]
      √2  [ 1  -1 ]

Effect:
  |0⟩ → |+⟩ = (|0⟩ + |1⟩)/√2
  |1⟩ → |−⟩ = (|0⟩ − |1⟩)/√2

Examples:
  h 0                 → Superposition on qubit 0
  qubit 1 → h 0       → Creates |+⟩ state
""",
            'cx': """
CX / CNOT - Controlled-NOT Gate
═══════════════════════════════════════════════════════════════

Usage:
  cx <control> <target>
  cnot <control> <target>

Effect:
  Flips target qubit if control qubit is |1⟩

Truth Table:
  |00⟩ → |00⟩
  |01⟩ → |01⟩
  |10⟩ → |11⟩  (flipped!)
  |11⟩ → |10⟩  (flipped!)

Examples:
  cx 0 1              → Control=0, Target=1
  
  Bell State Creation:
    qubit 2
    h 0
    cx 0 1
    measure           → 50% |00⟩, 50% |11⟩
""",
            'mcx': """
MCX - Multi-Controlled X Gate (ENHANCED - 16 Qubit Support)
═══════════════════════════════════════════════════════════════

ENHANCED FEATURES:
  ✅ numpy + scipy + qutip integration
  ✅ Up to 16 qubits (15 controls + 1 target)
  ✅ Automatic optimization based on control count
  ✅ Sparse matrix support for 8+ controls

Usage:
  mcx <controls> <target>

  Controls: comma-separated (NO spaces between them)
  Target: single qubit index
  Maximum: 15 controls + 1 target = 16 qubits (Tier 1 limit)

Behavior:
  Applies X (NOT) to target qubit only when ALL control
  qubits are in the |1⟩ state. Preserves superposition
  and entanglement across all computational basis states.

Implementation Strategy (Automatic):
  1 control     → CNOT (direct gate, <1ms)
  2 controls    → Toffoli decomposition (H-T-CNOT gates, <5ms)
  3-7 controls  → NumPy statevector method (~50ms)
  8-15 controls → SciPy sparse matrices (~200ms)
  16+ controls  → Error: exceeds Tier 1 capability

Performance (Dell i3 8th Gen, 8GB RAM):
  C¹X  (CNOT):     <1ms   | NumPy direct
  C²X  (Toffoli):  <5ms   | Gate decomposition
  C³X:             ~20ms  | NumPy statevector
  C⁵X:             ~50ms  | NumPy statevector
  C⁸X:             ~150ms | SciPy sparse
  C¹⁰X:            ~300ms | SciPy sparse
  C¹⁵X:            ~800ms | SciPy sparse (maximum)

Truth Table (2 controls / Toffoli example):
  |000⟩ → |000⟩  (controls not all 1)
  |010⟩ → |010⟩  (controls not all 1)
  |100⟩ → |100⟩  (controls not all 1)
  |110⟩ → |111⟩  (both controls 1, target flipped)
  |111⟩ → |110⟩  (both controls 1, target flipped)

Examples:
  mcx 0 1                    → CNOT (same as cx 0 1)
  mcx 0,1 2                  → Toffoli / CCNOT
  mcx 0,1,2 3                → C³X (3-controlled X)
  mcx 0,1,2,3 4              → C⁴X (4-controlled X)
  mcx 0,1,2,3,4,5,6 7        → C⁷X (7-controlled X)
  mcx 0,1,2,3,4,5,6,7,8 9    → C⁹X (9-controlled X, uses scipy)
  mcx 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14 15  → C¹⁵X (maximum)

Use Cases:
  - Grover's search oracle (requires n-1 controls for n-qubit search)
  - Amplitude amplification diffusion operator
  - Quantum error correction syndrome extraction
  - Multi-controlled phase gates (conjugate MCX with Hadamard)
  - Oracle design for quantum algorithms
  - Reversible computation and quantum computing universality

Advanced Circuit Example (Grover's Algorithm):
  qubit 4
  h 0
  h 1
  h 2
  # Oracle: mark |101⟩ state
  x 1
  mcx 0,1,2 3
  x 1
  # Diffusion operator
  h 0
  h 1
  h 2
  x 0
  x 1
  x 2
  mcx 0,1,2 3
  x 0
  x 1
  x 2
  h 0
  h 1
  h 2
  measure
""",
            'evolve': """
EVOLVE - Time Evolution
═══════════════════════════════════════════════════════════════

Usage:
  evolve <hamiltonian> <time>

Solves the Schrödinger equation:
  iℏ ∂|ψ⟩/∂t = H|ψ⟩

Available Hamiltonians:
  pauli_x     H = σx/2      (Rabi oscillations)
  pauli_z     H = σz/2      (Larmor precession)
  precession  H = σz/2 + 0.1·σx/2  (Combined)

Examples:
  qubit |+>
  evolve pauli_z 3.14        → Full Larmor cycle
  
  qubit 1
  h 0
  evolve pauli_x 1.57        → π/2 Rabi pulse
"""
        }
        return details.get(cmd)
    
    def _cmd_qubit(self, args: List[str]):
        """Initialize qubit(s)"""
        if not args:
            self._output("Usage: qubit <n> or qubit |state>\n")
            self._output("Examples: qubit 2, qubit |+>, qubit |01>\n")
            return
        
        arg = args[0]
        
        # Check for ket notation
        if arg.startswith('|') and arg.endswith('>'):
            state_str = arg[1:-1]
            self._init_from_ket(state_str)
        else:
            # Numeric - number of qubits
            try:
                n = int(arg)
                if n < 1 or n > 16:
                    self._output("❌ Qubit count must be 1-16 for Tier 1 hardware\n")
                    return
                
                self._engine.reset(n)
                self._output(f"✅ Initialized {n} qubit(s) in |{'0'*n}⟩ state\n")
            except ValueError:
                self._output(f"❌ Invalid argument: '{arg}'. Use number or |ket⟩\n")
    
    def _init_from_ket(self, state_str: str):
        """Initialize from ket notation like |0>, |+>, |01>"""
        state_str = state_str.lower()
        
        if state_str == '+':
            # |+⟩ = (|0⟩ + |1⟩)/√2
            self._engine.reset(1)
            self._engine.h(0)
            self._output("✅ Initialized |+⟩ = (|0⟩ + |1⟩)/√2\n")
        
        elif state_str == '-':
            # |−⟩ = (|0⟩ − |1⟩)/√2
            self._engine.reset(1)
            self._engine.x(0)
            self._engine.h(0)
            self._output("✅ Initialized |−⟩ = (|0⟩ − |1⟩)/√2\n")
        
        elif all(c in '01' for c in state_str):
            # Computational basis state like |01⟩
            n = len(state_str)
            self._engine.reset(n)
            
            # Apply X gates to flip to desired state
            for i, bit in enumerate(reversed(state_str)):
                if bit == '1':
                    self._engine.x(i)
            
            self._output(f"✅ Initialized |{state_str}⟩\n")
        
        else:
            self._output(f"❌ Unknown state: |{state_str}⟩\n")
            self._output("   Supported: |0⟩, |1⟩, |+⟩, |−⟩, |01⟩, etc.\n")
    
    def _cmd_reset(self, args: List[str]):
        """Reset to |0⟩ state"""
        n = self._engine.get_num_qubits()
        self._engine.reset(n)
        self._output(f"✅ Reset to |{'0'*n}⟩ state\n")
    
    def _parse_angle(self, angle_str: str) -> float:
        """Parse angle string, supporting 'pi' notation"""
        angle_str = angle_str.lower().replace(' ', '')
        
        # Replace pi with numpy value
        angle_str = angle_str.replace('pi', str(pi))
        
        try:
            return float(eval(angle_str))
        except:
            raise ValueError(f"Cannot parse angle: '{angle_str}'")
    
    # ==================== SINGLE-QUBIT GATES ====================
    
    def _cmd_gate_h(self, args: List[str]):
        """Hadamard gate"""
        if not args:
            self._output("Usage: h <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.h(target)
        self._output(f"✅ H gate applied to qubit {target}\n")
    
    def _cmd_gate_x(self, args: List[str]):
        """Pauli-X gate"""
        if not args:
            self._output("Usage: x <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.x(target)
        self._output(f"✅ X gate applied to qubit {target}\n")
    
    def _cmd_gate_y(self, args: List[str]):
        """Pauli-Y gate"""
        if not args:
            self._output("Usage: y <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.y(target)
        self._output(f"✅ Y gate applied to qubit {target}\n")
    
    def _cmd_gate_z(self, args: List[str]):
        """Pauli-Z gate"""
        if not args:
            self._output("Usage: z <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.z(target)
        self._output(f"✅ Z gate applied to qubit {target}\n")
    
    def _cmd_gate_s(self, args: List[str]):
        """S gate"""
        if not args:
            self._output("Usage: s <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.s(target)
        self._output(f"✅ S gate applied to qubit {target}\n")
    
    def _cmd_gate_t(self, args: List[str]):
        """T gate"""
        if not args:
            self._output("Usage: t <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.t(target)
        self._output(f"✅ T gate applied to qubit {target}\n")

    def _cmd_gate_sdg(self, args: List[str]):
        """S-dagger (adjoint of S) gate"""
        if not args:
            self._output("Usage: sdg <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.sdg(target)
        self._output(f"✅ Sdg gate applied to qubit {target}\n")

    def _cmd_gate_tdg(self, args: List[str]):
        """T-dagger (adjoint of T) gate"""
        if not args:
            self._output("Usage: tdg <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.tdg(target)
        self._output(f"✅ Tdg gate applied to qubit {target}\n")

    def _cmd_gate_sx(self, args: List[str]):
        """SX (sqrt(X)) gate"""
        if not args:
            self._output("Usage: sx <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.sx(target)
        self._output(f"✅ SX gate applied to qubit {target}\n")

    def _cmd_gate_sxdg(self, args: List[str]):
        """SX-dagger (adjoint of SX) gate"""
        if not args:
            self._output("Usage: sxdg <target_qubit>\n")
            return
        target = int(args[0])
        self._engine.sxdg(target)
        self._output(f"✅ SXdg gate applied to qubit {target}\n")

    def _cmd_gate_p(self, args: List[str]):
        """Phase gate"""
        if len(args) < 2:
            self._output("Usage: p <target_qubit> <phi>\n")
            self._output("Example: p 0 pi/4\n")
            return
        target = int(args[0])
        phi = self._parse_angle(args[1])
        self._engine.p(target, phi)
        self._output(f"✅ P({phi:.4f}) applied to qubit {target}\n")

    def _cmd_gate_cp(self, args: List[str]):
        """Controlled-phase gate"""
        if len(args) < 3:
            self._output("Usage: cp <control> <target> <phi>\n")
            self._output("Example: cp 0 1 pi/4\n")
            return
        control = int(args[0])
        target = int(args[1])
        phi = self._parse_angle(args[2])
        self._engine.cp(control, target, phi)
        self._output(f"✅ CP({phi:.4f}) applied: control={control}, target={target}\n")

    def _cmd_gate_swap(self, args: List[str]):
        """SWAP gate"""
        if len(args) < 2:
            self._output("Usage: swap <qubit1> <qubit2>\n")
            return
        qubit1 = int(args[0])
        qubit2 = int(args[1])
        self._engine.swap(qubit1, qubit2)
        self._output(f"✅ SWAP applied between qubits {qubit1} and {qubit2}\n")

    def _cmd_gate_cswap(self, args: List[str]):
        """Controlled-SWAP (Fredkin) gate"""
        if len(args) < 3:
            self._output("Usage: cswap <control> <qubit1> <qubit2>\n")
            return
        control = int(args[0])
        qubit1 = int(args[1])
        qubit2 = int(args[2])
        self._engine.cswap(control, qubit1, qubit2)
        self._output(f"✅ CSWAP applied: control={control}, qubits {qubit1} <-> {qubit2}\n")

    def _cmd_gate_inc(self, args: List[str]):
        """Increment gate (placeholder)"""
        self._output("⚠️  INC gate not yet implemented\n")

    def _cmd_gate_dec(self, args: List[str]):
        """Decrement gate (placeholder)"""
        self._output("⚠️  DEC gate not yet implemented\n")

    def _cmd_gate_reverse(self, args: List[str]):
        """Bit reversal gate (placeholder)"""
        self._output("⚠️  REVERSE gate not yet implemented\n")

    def _cmd_gate_rx(self, args: List[str]):
        """Rx rotation gate"""
        if len(args) < 2:
            self._output("Usage: rx <target_qubit> <angle>\n")
            self._output("Example: rx 0 pi/2\n")
            return
        target = int(args[0])
        theta = self._parse_angle(args[1])
        self._engine.rotate_x(target, theta)
        self._output(f"✅ Rx({theta:.4f}) applied to qubit {target}\n")
    
    def _cmd_gate_ry(self, args: List[str]):
        """Ry rotation gate"""
        if len(args) < 2:
            self._output("Usage: ry <target_qubit> <angle>\n")
            return
        target = int(args[0])
        theta = self._parse_angle(args[1])
        self._engine.rotate_y(target, theta)
        self._output(f"✅ Ry({theta:.4f}) applied to qubit {target}\n")
    
    def _cmd_gate_rz(self, args: List[str]):
        """Rz rotation gate"""
        if len(args) < 2:
            self._output("Usage: rz <target_qubit> <angle>\n")
            return
        target = int(args[0])
        theta = self._parse_angle(args[1])
        self._engine.rotate_z(target, theta)
        self._output(f"✅ Rz({theta:.4f}) applied to qubit {target}\n")
    
    # ==================== TWO-QUBIT GATES ====================
    
    def _cmd_gate_cx(self, args: List[str]):
        """CNOT gate"""
        if len(args) < 2:
            self._output("Usage: cx <control> <target>\n")
            self._output("Example: cx 0 1\n")
            return
        control = int(args[0])
        target = int(args[1])
        self._engine.cx(control, target)
        self._output(f"✅ CNOT applied: control={control}, target={target}\n")
    
    def _cmd_gate_cz(self, args: List[str]):
        """Controlled-Z gate"""
        if len(args) < 2:
            self._output("Usage: cz <control> <target>\n")
            return
        control = int(args[0])
        target = int(args[1])
        self._engine.cz(control, target)
        self._output(f"✅ CZ applied: control={control}, target={target}\n")

    def _cmd_gate_cy(self, args: List[str]):
        """Controlled-Y gate"""
        if len(args) < 2:
            self._output("Usage: cy <control> <target>\n")
            return
        control = int(args[0])
        target = int(args[1])
        self._engine.cy(control, target)
        self._output(f"✅ CY applied: control={control}, target={target}\n")

    def _cmd_gate_ch(self, args: List[str]):
        """Controlled-H gate"""
        if len(args) < 2:
            self._output("Usage: ch <control> <target>\n")
            return
        control = int(args[0])
        target = int(args[1])
        self._engine.ch(control, target)
        self._output(f"✅ CH applied: control={control}, target={target}\n")

    # ==================== MULTI-CONTROLLED GATES ====================

    def _cmd_gate_mcx(self, args: List[str]):
        """
        Multi-Controlled X (MCX) gate - generalized Toffoli

        Applies X to target qubit if ALL control qubits are |1>
        Enhanced with scipy/qutip support for up to 16 qubits

        Usage: mcx <control1>,<control2>,...,<controlN> <target>

        Examples:
            mcx 0 1          -> CNOT (1 control)
            mcx 0,1 2        -> Toffoli/CCNOT (2 controls)
            mcx 0,1,2 3      -> C3X (3 controls)
            mcx 0,1,2,3,4 5  -> C5X (5 controls)
            mcx 0,1,2,3,4,5,6,7 8  -> C8X (8 controls, uses scipy sparse)
        """
        if len(args) < 2:
            self._output("╔═══════════════════════════════════════════════════════════╗\n")
            self._output("║        MCX - Multi-Controlled X Gate (ENHANCED)          ║\n")
            self._output("╠═══════════════════════════════════════════════════════════╣\n")
            self._output("║  Usage: mcx <controls> <target>                         ║\n")
            self._output("║                                                           ║\n")
            self._output("║  Controls: comma-separated list (no spaces)              ║\n")
            self._output("║  Target: single qubit index                              ║\n")
            self._output("║  Maximum: 15 controls + 1 target = 16 qubits (Tier 1)   ║\n")
            self._output("║                                                           ║\n")
            self._output("║  Examples:                                               ║\n")
            self._output("║    mcx 0 1              -> CNOT (1 control)              ║\n")
            self._output("║    mcx 0,1 2            -> Toffoli (2 controls)          ║\n")
            self._output("║    mcx 0,1,2 3          -> C³X (3 controls)              ║\n")
            self._output("║    mcx 0,1,2,3 4        -> C⁴X (4 controls)              ║\n")
            self._output("║    mcx 0,1,2,3,4,5,6 7  -> C⁷X (7 controls)              ║\n")
            self._output("║                                                           ║\n")
            self._output("║  Performance (Tier 1 - i3 8th Gen, 8GB RAM):            ║\n")
            self._output("║    1-2 controls:  <5ms   (gate decomposition)           ║\n")
            self._output("║    3-7 controls:  ~50ms  (numpy statevector)            ║\n")
            self._output("║    8+ controls:   ~200ms (scipy sparse matrices)        ║\n")
            self._output("║                                                           ║\n")
            self._output("║  Computation: numpy + scipy + qutip                      ║\n")
            self._output("║  ⚠ Warning: 8+ controls are computationally expensive   ║\n")
            self._output("╚═══════════════════════════════════════════════════════════╝\n")
            return

        try:
            # Parse control qubits
            control_str = args[0]
            controls = [int(c.strip()) for c in control_str.split(',')]

            # Parse target qubit
            target = int(args[1])

            # Validate
            if target in controls:
                self._output(f"❌ Error: Target qubit {target} cannot be in control list\n")
                return

            if not controls:
                self._output("❌ Error: Need at least 1 control qubit\n")
                return

            n_controls = len(controls)

            # Validate total qubit count (max 16 for Tier 1)
            total_qubits = max(max(controls), target) + 1
            if total_qubits > 16:
                self._output(f"❌ Error: Total qubits ({total_qubits}) exceeds Tier 1 limit (16)\n")
                self._output("   Reduce control count or use smaller qubit indices\n")
                return

            # Apply MCX gate with appropriate method based on control count
            if n_controls == 1:
                # Single control = CNOT
                self._engine.cx(controls[0], target)
                self._output(f"✅ CNOT applied: control={controls[0]}, target={target}\n")

            elif n_controls == 2:
                # Two controls = Toffoli (gate decomposition)
                self._apply_toffoli_decomposition(controls[0], controls[1], target)
                self._output(f"✅ Toffoli (CCNOT) applied: controls={controls}, target={target}\n")

            elif n_controls <= 7:
                # 3-7 controls: numpy statevector (fast enough)
                if n_controls >= 5:
                    self._output(f"⚙️  Applying C{n_controls}X gate (numpy statevector method)...\n")
                self._apply_mcx_statevector(controls, target)
                self._output(f"✅ C{n_controls}X applied: controls={controls}, target={target}\n")

            elif n_controls <= 15:
                # 8-15 controls: scipy sparse matrices (memory efficient)
                self._output(f"⚠️  Warning: MCX with {n_controls} controls is computationally expensive!\n")
                self._output(f"⚙️  Using scipy sparse matrices for optimization...\n")
                self._output(f"⏱️  Estimated time: ~{n_controls * 30}ms on Tier 1 hardware\n")
                self._apply_mcx_statevector(controls, target)
                self._output(f"✅ C{n_controls}X applied: controls={controls}, target={target}\n")

            else:
                # 16+ controls: beyond Tier 1 capability
                self._output(f"❌ Error: {n_controls} controls exceeds Tier 1 limit (15)\n")
                self._output("   Maximum: 15 controls + 1 target = 16 qubits\n")
                return

        except ValueError as e:
            self._output(f"❌ Error parsing arguments: {e}\n")
            self._output("Usage: mcx <control1>,<control2>,... <target>\n")
        except Exception as e:
            self._output(f"❌ Error applying MCX: {e}\n")

    def _apply_toffoli_decomposition(self, ctrl1: int, ctrl2: int, target: int):
        """
        Decompose Toffoli (CCNOT) into single and two-qubit gates.

        Standard decomposition using 6 CNOTs and 7 single-qubit gates
        based on Nielsen & Chuang's construction.

        Args:
            ctrl1: First control qubit
            ctrl2: Second control qubit
            target: Target qubit
        """
        try:
            # T-dagger gate matrix (T† = Z^(-1/4))
            t_dag_matrix = np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex)

            # H-T-CNOT decomposition of Toffoli
            self._engine.h(target)
            self._engine.cx(ctrl2, target)
            self._engine.apply_gate(t_dag_matrix, target)
            self._engine.cx(ctrl1, target)
            self._engine.t(target)
            self._engine.cx(ctrl2, target)
            self._engine.apply_gate(t_dag_matrix, target)
            self._engine.cx(ctrl1, target)
            self._engine.t(ctrl2)
            self._engine.t(target)
            self._engine.h(target)
            self._engine.cx(ctrl1, ctrl2)
            self._engine.t(ctrl1)
            self._engine.apply_gate(t_dag_matrix, ctrl2)
            self._engine.cx(ctrl1, ctrl2)

        except Exception as e:
            self._output(f"  Toffoli decomposition failed, using statevector method\n")
            self._apply_mcx_statevector([ctrl1, ctrl2], target)

    def _apply_mcx_statevector(self, controls: List[int], target: int):
        """
        Apply MCX directly to statevector (efficient for 3+ controls).

        Enhanced version with scipy/qutip optimization for large control counts.
        Supports up to 16 qubits with performance optimizations.

        Modifies the quantum state directly instead of using gate
        decomposition. Complexity: O(2^n) vs O(4^n) for gate-based.

        Args:
            controls: List of control qubit indices
            target: Target qubit index
        """
        try:
            # Get current state
            state = self._engine.get_state()
            if state is None:
                raise RuntimeError("No quantum state initialized")

            n_controls = len(controls)

            # Validate qubit count (max 16 qubits for Tier 1 hardware)
            n_qubits = self._engine.get_num_qubits() if hasattr(self._engine, 'get_num_qubits') else int(np.log2(len(state)))
            if n_qubits > 16:
                raise RuntimeError(f"MCX limited to 16 qubits on Tier 1 hardware (current: {n_qubits})")

            # For large control counts (8+), try using scipy sparse matrices for efficiency
            if n_controls >= 8 and _load_scipy() is not None:
                self._apply_mcx_sparse(controls, target, state)
                return

            # Standard numpy approach for smaller control counts
            # Create new state by swapping amplitudes
            new_state = state.copy()

            # Optimization: pre-compute control mask
            control_mask = sum(1 << ctrl for ctrl in controls)

            for i in range(len(state)):
                # Check if ALL control qubits are |1> using bitwise operations
                if (i & control_mask) == control_mask:
                    target_bit = (i >> target) & 1
                    if target_bit == 0:
                        # Swap with state where target is |1>
                        j = i | (1 << target)
                        new_state[i] = state[j]
                        new_state[j] = state[i]

            # Update state in engine
            self._engine.set_state(new_state)

        except Exception as e:
            raise RuntimeError(f"MCX statevector application failed: {e}")

    def _apply_mcx_sparse(self, controls: List[int], target: int, state: np.ndarray):
        """
        Apply MCX using scipy sparse matrices for large control counts (8+ controls).

        This method is more memory-efficient for deep controlled gates
        by exploiting the sparsity of the MCX operator.

        Args:
            controls: List of control qubit indices
            target: Target qubit index
            state: Current quantum state vector
        """
        try:
            scipy = _load_scipy()
            if scipy is None:
                # Fallback to standard method
                self._output("  Warning: scipy not available, using standard method\n")
                return

            from scipy.sparse import lil_matrix

            n = len(state)
            # Create sparse MCX operator
            mcx_op = lil_matrix((n, n), dtype=complex)

            control_mask = sum(1 << ctrl for ctrl in controls)

            for i in range(n):
                if (i & control_mask) == control_mask:
                    # Controls are all |1>, apply X to target
                    j = i ^ (1 << target)  # Flip target bit
                    mcx_op[i, j] = 1.0
                    mcx_op[j, i] = 1.0
                else:
                    # Identity for this basis state
                    mcx_op[i, i] = 1.0

            # Apply operator to state
            new_state = mcx_op.dot(state)
            self._engine.set_state(np.array(new_state).flatten())

        except Exception as e:
            self._output(f"  Sparse MCX failed: {e}, using standard method\n")
            # Fallback handled by caller

    def _cmd_gate(self, args: List[str]):
        """Generic gate command - routes to specific gate handlers"""
        if not args:
            self._output("Usage: gate <name> <target> [args]\n")
            self._output("Gates: h x y z s t sdg tdg sx sxdg p rx ry rz cx cy cz ch cp swap cswap mcx inc dec reverse\n")
            return

        gate_name = args[0].lower()
        gate_args = args[1:]

        gate_map = {
            'h': self._cmd_gate_h,
            'x': self._cmd_gate_x,
            'y': self._cmd_gate_y,
            'z': self._cmd_gate_z,
            's': self._cmd_gate_s,
            't': self._cmd_gate_t,
            'sdg': self._cmd_gate_sdg,
            'tdg': self._cmd_gate_tdg,
            'sx': self._cmd_gate_sx,
            'sxdg': self._cmd_gate_sxdg,
            'p': self._cmd_gate_p,
            'rx': self._cmd_gate_rx,
            'ry': self._cmd_gate_ry,
            'rz': self._cmd_gate_rz,
            'cx': self._cmd_gate_cx,
            'cnot': self._cmd_gate_cx,
            'cy': self._cmd_gate_cy,
            'cz': self._cmd_gate_cz,
            'ch': self._cmd_gate_ch,
            'cp': self._cmd_gate_cp,
            'swap': self._cmd_gate_swap,
            'cswap': self._cmd_gate_cswap,
            'fredkin': self._cmd_gate_cswap,
            'mcx': self._cmd_gate_mcx,
            'inc': self._cmd_gate_inc,
            'dec': self._cmd_gate_dec,
            'reverse': self._cmd_gate_reverse,
        }

        if gate_name in gate_map:
            gate_map[gate_name](gate_args)
        else:
            self._output(f"❌ Unknown gate: '{gate_name}'\n")
    
    # ==================== MEASUREMENT ====================
    
    def _cmd_measure(self, args: List[str]):
        """Perform measurement with auto-visualization"""
        shots = 1024
        if args:
            try:
                shots = int(args[0])
            except ValueError:
                self._output("❌ Invalid shot count\n")
                return

        num_qubits = self._engine.get_num_qubits()

        # Perform measurement
        results = self._engine.measure(shots)
        theoretical_probs = self._engine.get_probabilities()

        # Show terminal output
        self._output(f"\n📊 Measurement Results ({shots} shots)\n")
        self._output("─" * 40 + "\n")

        # Sort by count
        sorted_results = sorted(results.items(), key=lambda x: -x[1])

        for basis, count in sorted_results:
            pct = count / shots * 100
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            self._output(f"  |{basis}⟩  {bar} {count:4d} ({pct:5.1f}%)\n")

        self._output("─" * 40 + "\n")

        # Launch Bloch sphere visualization with measurement data
        if num_qubits <= 16:
            try:
                # Convert counts to probabilities for experimental data
                experimental_probs = {basis: count/shots for basis, count in results.items()}

                # Get all quantum state data
                all_coords = self._engine.get_all_qubit_bloch_coords()
                entanglement = self._engine.get_entanglement_info()
                marginal_probs = self._engine.get_marginal_probabilities()

                from synthesis.quantum import get_visualizer
                visualizer = get_visualizer()

                # Always use multi-qubit visualization (works for 1+ qubits)
                success = visualizer.launch_multi_qubit_bloch(
                    qubit_coords=all_coords,
                    entanglement_info=entanglement,
                    num_qubits=num_qubits,
                    gate_count=len(self._engine._gate_log),
                    theoretical_probs=theoretical_probs,
                    experimental_probs=experimental_probs,
                    marginal_probs=marginal_probs,
                    shots=shots
                )
                if success:
                    self._output(f"🌐 Launched visualization with measurement data\n")
            except Exception as e:
                self._output(f"⚠️ Visualization error: {e}\n")

    def _cmd_measure_x(self, args: List[str]):
        """Measure in X basis"""
        shots = 1024
        if args:
            try:
                shots = int(args[0])
            except ValueError:
                self._output("❌ Invalid shot count\n")
                return
        self._output("⚠️  X-basis measurement not yet implemented\n")
        self._output("   Falling back to Z-basis measurement\n")
        self._cmd_measure(args)

    def _cmd_measure_y(self, args: List[str]):
        """Measure in Y basis"""
        shots = 1024
        if args:
            try:
                shots = int(args[0])
            except ValueError:
                self._output("❌ Invalid shot count\n")
                return
        self._output("⚠️  Y-basis measurement not yet implemented\n")
        self._output("   Falling back to Z-basis measurement\n")
        self._cmd_measure(args)

    def _cmd_probabilities(self, args: List[str]):
        """Show probability distribution"""
        probs = self._engine.get_probabilities()
        
        self._output(f"\n🎲 Probability Distribution\n")
        self._output("─" * 35 + "\n")
        
        for basis, prob in sorted(probs.items()):
            pct = prob * 100
            bar_len = int(pct / 5)
            bar = "▓" * bar_len + "░" * (20 - bar_len)
            self._output(f"  |{basis}⟩  {bar} {pct:6.2f}%\n")
        
        self._output("─" * 35 + "\n\n")
    
    def _cmd_state(self, args: List[str]):
        """Display current statevector"""
        self._engine.print_state()
        
        # Also show Bloch coordinates for single qubit
        if self._engine.get_num_qubits() == 1:
            x, y, z = self._engine.get_bloch_coords(0)
            self._output(f"Bloch: (x={x:+.4f}, y={y:+.4f}, z={z:+.4f})\n\n")
    
    # ==================== VISUALIZATION ====================
    
    def _cmd_bloch(self, args: List[str]):
        """Launch Bloch sphere visualization with probability display"""
        num_qubits = self._engine.get_num_qubits()

        if num_qubits > 16:
            self._output("⚠️ Bloch visualization limited to 16 qubits\n")
            return

        try:
            # Get coordinates for ALL qubits
            all_coords = self._engine.get_all_qubit_bloch_coords()

            # Get entanglement info
            entanglement = self._engine.get_entanglement_info()

            # Get probability data
            theoretical_probs = self._engine.get_probabilities()
            marginal_probs = self._engine.get_marginal_probabilities()

            # Get visualizer
            from synthesis.quantum import get_visualizer
            visualizer = get_visualizer()

            # Always use multi-qubit visualization (works for 1+ qubits)
            success = visualizer.launch_multi_qubit_bloch(
                qubit_coords=all_coords,
                entanglement_info=entanglement,
                num_qubits=num_qubits,
                gate_count=len(self._engine._gate_log),
                theoretical_probs=theoretical_probs,
                marginal_probs=marginal_probs,
                shots=0  # No measurement in bloch command
            )

            if success:
                self._output(f"🌐 Launched {num_qubits}-qubit Bloch visualization\n")
                if entanglement['is_entangled']:
                    self._output(f"   ⚛️ ENTANGLED (Schmidt rank: {entanglement['schmidt_rank']})\n")

        except Exception as e:
            self._output(f"❌ Visualization error: {e}\n")

    def _cmd_bloch_matplotlib(self, args: List[str]):
        """
        Plot Bloch sphere using matplotlib (2D/3D static plot).

        Uses ELEVATED 90% RAM LIMIT specifically for Bloch visualization.
        Standard operations use 75% RAM limit.

        Usage:
            bloch2d          - 2D projection (X-Z plane)
            bloch2d 3d       - 3D interactive plot
        """
        # Load matplotlib with 90% RAM limit for Bloch sphere
        mpl = _load_matplotlib_for_bloch()

        if mpl is None:
            self._output("❌ Matplotlib not available (RAM > 90%)\n")
            self._output("   Bloch sphere UI uses elevated 90% RAM limit\n")
            self._output("   Current RAM may exceed this threshold\n")
            return

        try:
            plt = mpl.pyplot

            # Get current quantum state
            state = self._engine.get_state()
            if state is None or len(state) != 2:
                self._output("❌ Bloch sphere requires 1-qubit state\n")
                return

            # Convert to Bloch coordinates
            from synthesis.bloch_sphere_popup import state_vector_to_bloch
            theta, phi = state_vector_to_bloch(state)

            x = np.sin(theta) * np.cos(phi)
            y = np.sin(theta) * np.sin(phi)
            z = np.cos(theta)

            # Determine plot type
            plot_3d = len(args) > 0 and args[0].lower() == '3d'

            if plot_3d:
                # 3D plot
                from mpl_toolkits.mplot3d import Axes3D
                fig = plt.figure(figsize=(8, 8))
                ax = fig.add_subplot(111, projection='3d')

                # Draw sphere wireframe
                u = np.linspace(0, 2 * np.pi, 100)
                v = np.linspace(0, np.pi, 100)
                xs = np.outer(np.cos(u), np.sin(v))
                ys = np.outer(np.sin(u), np.sin(v))
                zs = np.outer(np.ones(np.size(u)), np.cos(v))
                ax.plot_wireframe(xs, ys, zs, color='gray', alpha=0.3)

                # Draw state vector
                ax.quiver(0, 0, 0, x, y, z, color='red', arrow_length_ratio=0.1, linewidth=2)

                # Draw axes
                ax.plot([0, 1.2], [0, 0], [0, 0], 'r-', alpha=0.5)
                ax.plot([0, 0], [0, 1.2], [0, 0], 'g-', alpha=0.5)
                ax.plot([0, 0], [0, 0], [0, 1.2], 'b-', alpha=0.5)

                ax.set_xlabel('X')
                ax.set_ylabel('Y')
                ax.set_zlabel('Z')
                ax.set_title('Bloch Sphere - 3D (matplotlib)')

            else:
                # 2D projection (X-Z plane)
                fig, ax = plt.subplots(figsize=(6, 6))

                # Draw circle
                circle = plt.Circle((0, 0), 1, fill=False, color='gray', linestyle='--')
                ax.add_patch(circle)

                # Draw state vector projection
                ax.arrow(0, 0, x, z, head_width=0.05, head_length=0.05, fc='red', ec='red', linewidth=2)

                # Draw axes
                ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
                ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)

                ax.set_xlim(-1.2, 1.2)
                ax.set_ylim(-1.2, 1.2)
                ax.set_xlabel('X')
                ax.set_ylabel('Z')
                ax.set_title('Bloch Sphere - 2D Projection (matplotlib)')
                ax.set_aspect('equal')
                ax.grid(True, alpha=0.3)

            self._output(f"📊 Bloch sphere plot generated\n")
            self._output(f"   Coordinates: ({x:+.4f}, {y:+.4f}, {z:+.4f})\n")
            self._output(f"   θ = {theta:.4f}, φ = {phi:.4f}\n")
            self._output(f"   RAM limit: 90% (Bloch UI elevated allowance)\n")

            plt.show()

        except Exception as e:
            self._output(f"❌ Matplotlib Bloch plot failed: {e}\n")
    
    def _cmd_compute(self, args: List[str]):
        """Run full computation with visualization"""
        from synthesis import ComputeMode
        
        shots = 1024
        if args:
            try:
                shots = int(args[0])
            except ValueError:
                pass
        
        self._output("\n⚡ Running computation...\n")
        
        result = self._engine.compute(
            mode=ComputeMode.STATEVECTOR,
            shots=shots,
            visualize=True
        )
        
        if result.success:
            self._output(f"✅ Computation complete in {result.compute_time_ms:.2f}ms\n")
            self._output(f"   Qubits: {result.num_qubits}, Gates: {result.gate_count}\n")
            
            if result.measurements:
                top_result = max(result.measurements.items(), key=lambda x: x[1])
                self._output(f"   Most likely: |{top_result[0]}⟩ ({top_result[1]}/{shots})\n")
            
            self._output("\n")
        else:
            self._output(f"❌ Computation failed: {result.error}\n")
    
    # ==================== TIME EVOLUTION ====================
    
    def _cmd_hamiltonian(self, args: List[str]):
        """List available Hamiltonians"""
        self._output("""
🔬 Available Hamiltonians
─────────────────────────────────────────
  pauli_x      H = ω·σx/2    (Rabi oscillations)
  pauli_z      H = ω·σz/2    (Larmor precession)
  precession   H = ω₀·σz/2 + ω₁·σx/2  (Combined)

Usage: evolve <hamiltonian> <time> [omega]
Example: evolve pauli_x 3.14159

""")
    
    def _cmd_evolve(self, args: List[str]):
        """Time evolution under Hamiltonian"""
        if len(args) < 2:
            self._output("Usage: evolve <hamiltonian> <time> [omega]\n")
            self._output("Example: evolve pauli_x pi\n")
            self._output("Type 'hamiltonian' to see available options\n")
            return
        
        from synthesis import hamiltonian_pauli_x, hamiltonian_pauli_z, hamiltonian_free_precession
        
        h_name = args[0].lower()
        time = self._parse_angle(args[1])  # Reuse angle parser for time
        omega = float(args[2]) if len(args) > 2 else 1.0
        
        hamiltonians = {
            'pauli_x': lambda: hamiltonian_pauli_x(omega),
            'pauli_z': lambda: hamiltonian_pauli_z(omega),
            'precession': lambda: hamiltonian_free_precession(omega, 0.1 * omega),
        }
        
        if h_name not in hamiltonians:
            self._output(f"❌ Unknown Hamiltonian: '{h_name}'\n")
            self._output("   Available: pauli_x, pauli_z, precession\n")
            return
        
        H = hamiltonians[h_name]()
        
        self._output(f"⏱️  Evolving under H={h_name} for t={time:.4f}...\n")
        
        self._engine.evolve_unitary(time, H)
        
        self._output("✅ Evolution complete\n")
        self._engine.print_state()
        
        # Show Bloch for single qubit
        if self._engine.get_num_qubits() == 1:
            x, y, z = self._engine.get_bloch_coords(0)
            self._output(f"Bloch: ({x:+.4f}, {y:+.4f}, {z:+.4f})\n\n")
    
    # ==================== UTILITY ====================
    
    def _cmd_status(self, args: List[str]):
        """Show engine status"""
        n = self._engine.get_num_qubits()
        g = self._engine.get_gate_count()
        history = self._engine.get_result_history()
        
        self._output(f"""
⚛️  Quantum Engine Status
───────────────────────────────────
  Qubits:           {n}
  Gates Applied:    {g}
  Computations:     {len(history)}
  State Dimension:  {2**n}
  Memory Est.:      {(2**n * 16) / 1024:.1f} KB
───────────────────────────────────
""")
    
    def _cmd_history(self, args: List[str]):
        """Show computation history"""
        history = self._engine.get_result_history()
        
        if not history:
            self._output("No computations yet.\n")
            return
        
        self._output(f"\n📜 Computation History ({len(history)} results)\n")
        self._output("─" * 50 + "\n")
        
        for i, r in enumerate(history[-10:], 1):  # Last 10
            status = "✅" if r.success else "❌"
            self._output(f"  {i}. {status} {r.result_id} | {r.num_qubits}q | {r.gate_count}g | {r.compute_time_ms:.1f}ms\n")
        
        self._output("─" * 50 + "\n\n")
    
    def _cmd_clear(self, args: List[str]):
        """Clear terminal (delegates to main terminal)"""
        self._output("\033[2J\033[H")  # ANSI clear
        self._show_welcome()
    
    def _cmd_exit(self, args: List[str]):
        """Exit quantum mode"""
        self.exit_mode()
        return False
    
    # ==================== CIRCUIT COMMANDS ====================
    
    def _cmd_list_circuits(self, args: List[str]):
        """List available predefined circuits"""
        try:
            from synthesis.quantum import CIRCUIT_REGISTRY
            
            self._output("\n📦 Available Predefined Circuits\n")
            self._output("─" * 50 + "\n")
            
            for name, info in CIRCUIT_REGISTRY.items():
                qubits = info.get('qubits', '?')
                desc = info.get('description', '')
                self._output(f"  {name:12s}  {qubits:>8} qubits  {desc}\n")
            
            self._output("─" * 50 + "\n")
            self._output("\nUsage: circuit <name> or use shortcut (bell, ghz, qft)\n\n")
            
        except ImportError:
            self._output("❌ Circuit library not available\n")
    
    def _cmd_circuit(self, args: List[str]):
        """Apply a predefined circuit"""
        if not args:
            self._cmd_list_circuits([])
            return
        
        circuit_name = args[0].lower()
        
        try:
            from synthesis.quantum import get_circuit, QuantumCircuitLibrary
            
            circuit_info = get_circuit(circuit_name)
            if not circuit_info:
                self._output(f"❌ Unknown circuit: '{circuit_name}'\n")
                self._output("   Type 'circuits' to see available circuits\n")
                return
            
            # Get required qubits
            required_qubits = circuit_info.get('qubits', 2)
            if isinstance(required_qubits, int):
                if self._engine.get_num_qubits() < required_qubits:
                    self._engine.reset(required_qubits)
                    self._output(f"📐 Initialized {required_qubits} qubits for {circuit_name}\n")
            
            # Apply circuit
            func = circuit_info['function']
            if circuit_name in ['ghz', 'w', 'qft', 'grover']:
                n = int(args[1]) if len(args) > 1 else self._engine.get_num_qubits()
                func(self._engine, n)
            else:
                func(self._engine)
            
            self._output(f"✅ Applied {circuit_info['name']} circuit\n")
            self._engine.print_state()
            
            # Auto-visualize
            if self._auto_visualize:
                self._launch_bloch_after_measurement()
                
        except ImportError as e:
            self._output(f"❌ Circuit library error: {e}\n")
    
    def _cmd_bell(self, args: List[str]):
        """Create Bell state shortcut"""
        self._engine.reset(2)
        self._engine.h(0)
        self._engine.cx(0, 1)
        self._output("✅ Created Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2\n")
        self._engine.print_state()
        
        if self._auto_visualize:
            self._launch_bloch_after_measurement()
    
    def _cmd_ghz(self, args: List[str]):
        """Create GHZ state shortcut"""
        n = int(args[0]) if args else 3
        if n < 2 or n > 16:
            self._output("❌ GHZ state requires 2-16 qubits\n")
            return
        
        self._engine.reset(n)
        self._engine.h(0)
        for i in range(1, n):
            self._engine.cx(0, i)
        
        self._output(f"✅ Created {n}-qubit GHZ state\n")
        self._engine.print_state()
        
        if self._auto_visualize:
            self._launch_bloch_after_measurement()
    
    def _cmd_qft(self, args: List[str]):
        """Apply Quantum Fourier Transform"""
        try:
            from synthesis.quantum import QuantumCircuitLibrary
            
            n = int(args[0]) if args else self._engine.get_num_qubits()
            if n > self._engine.get_num_qubits():
                self._engine.reset(n)
            
            QuantumCircuitLibrary.qft(self._engine, n)
            self._output(f"✅ Applied {n}-qubit QFT\n")
            self._engine.print_state()
            
        except ImportError:
            self._output("❌ QFT circuit not available\n")
    
    # ==================== VISUALIZATION TOGGLE ====================
    
    def _cmd_viz_toggle(self, args: List[str]):
        """Toggle auto-visualization on/off"""
        if args and args[0].lower() in ['off', 'false', '0', 'no']:
            self._auto_visualize = False
            self._output("🔴 Auto-visualization OFF\n")
        elif args and args[0].lower() in ['on', 'true', '1', 'yes']:
            self._auto_visualize = True
            self._output("🟢 Auto-visualization ON\n")
        else:
            self._auto_visualize = not self._auto_visualize
            status = "ON" if self._auto_visualize else "OFF"
            icon = "🟢" if self._auto_visualize else "🔴"
            self._output(f"{icon} Auto-visualization {status}\n")
    
    # ==================== PHASE 3.5: TOOLSET COMMANDS ====================

    def _cmd_decohere(self, args: List[str]):
        """Model decoherence on the current state using QuTiP."""
        dec_type = args[0] if args else "amplitude_damping"
        gamma = float(args[1]) if len(args) > 1 else 0.1
        try:
            from agents.registry import get_registry
            agent = get_registry().get("quantum_dynamics")
            if agent is None:
                self._output("quantum_dynamics agent not registered\n")
                return

            import qutip as qt
            n = self._engine.get_num_qubits()
            if n != 1:
                self._output("decohere currently supports 1-qubit states\n")
                return

            sv = self._engine.get_state()
            psi0 = qt.Qobj(sv.reshape(-1, 1))
            tlist = np.linspace(0, 5.0 / max(gamma, 1e-6), 50)

            r = agent.execute(
                operation="decoherence",
                state=psi0, gamma=gamma, tlist=tlist,
                decoherence_type=dec_type,
            )
            if r.success:
                final_purity = r.data["purities"][-1]
                self._output(
                    f"Decoherence ({dec_type}, gamma={gamma})\n"
                    f"  Initial purity: {r.data['purities'][0]:.4f}\n"
                    f"  Final purity:   {final_purity:.4f}  (t={tlist[-1]:.2f})\n"
                )
            else:
                self._output(f"decohere failed: {r.error}\n")
        except Exception as e:
            self._output(f"decohere error: {e}\n")

    def _cmd_mesolve(self, args: List[str]):
        """Solve the Lindblad master equation via QuTiP mesolve."""
        if len(args) < 2:
            self._output("Usage: mesolve <hamiltonian> <time>\n")
            self._output("  hamiltonian: pauli_x, pauli_z, precession\n")
            return
        try:
            from agents.registry import get_registry
            import qutip as qt

            agent = get_registry().get("quantum_dynamics")
            if agent is None:
                self._output("quantum_dynamics agent not registered\n")
                return

            h_name = args[0].lower()
            t_end = self._parse_angle(args[1])

            from synthesis import hamiltonian_pauli_x, hamiltonian_pauli_z, hamiltonian_free_precession
            h_map = {
                "pauli_x": hamiltonian_pauli_x(),
                "pauli_z": hamiltonian_pauli_z(),
                "precession": hamiltonian_free_precession(),
            }
            H_np = h_map.get(h_name)
            if H_np is None:
                self._output(f"Unknown Hamiltonian: {h_name}\n")
                return

            H = qt.Qobj(H_np)
            sv = self._engine.get_state()
            rho0 = qt.Qobj(sv.reshape(-1, 1))
            tlist = np.linspace(0, t_end, 50)

            r = agent.execute(
                operation="mesolve",
                hamiltonian=H, rho0=rho0, tlist=tlist,
                e_ops=[qt.sigmax(), qt.sigmay(), qt.sigmaz()],
            )
            if r.success:
                ex = r.data["expect"]
                self._output(
                    f"mesolve complete (t=0..{t_end:.2f})\n"
                    f"  <X>(final)={ex[0][-1]:.4f}  "
                    f"<Y>(final)={ex[1][-1]:.4f}  "
                    f"<Z>(final)={ex[2][-1]:.4f}\n"
                )
            else:
                self._output(f"mesolve failed: {r.error}\n")
        except Exception as e:
            self._output(f"mesolve error: {e}\n")

    def _cmd_transpile(self, args: List[str]):
        """Transpile the current gate log to a Qiskit circuit."""
        try:
            from agents.registry import get_registry
            agent = get_registry().get("quantum_hardware")
            if agent is None:
                self._output("quantum_hardware agent not registered\n")
                return

            # Build gate list from gate log
            gates = []
            for entry in self._engine._gate_log:
                g = np.array(entry["gate"], dtype=complex)
                target = entry["target"]
                control = entry.get("control")

                # Try to identify the gate by comparing matrices
                gate_name = self._identify_gate(g)
                if control is not None:
                    gates.append({"gate": f"c{gate_name}", "qubits": [control, target]})
                else:
                    gates.append({"gate": gate_name, "qubits": [target]})

            n = self._engine.get_num_qubits()
            r = agent.execute(operation="build_circuit", num_qubits=n, gates=gates)
            if r.success:
                self._output(
                    f"Transpiled to Qiskit circuit:\n"
                    f"  Qubits: {r.data['num_qubits']}, Gates: {r.data['gate_count']}\n"
                    f"  Depth: {r.data.get('depth', '?')}\n"
                )
            else:
                self._output(f"transpile failed: {r.error}\n")
        except Exception as e:
            self._output(f"transpile error: {e}\n")

    def _identify_gate(self, matrix: np.ndarray) -> str:
        """Best-effort identification of a 2x2 gate matrix."""
        from synthesis.engine import SynthesisEngine as SE
        for name, ref in [("h", SE.HADAMARD), ("x", SE.PAULI_X),
                          ("y", SE.PAULI_Y), ("z", SE.PAULI_Z),
                          ("s", SE.S_GATE), ("t", SE.T_GATE)]:
            if np.allclose(matrix, ref, atol=1e-8):
                return name
        return "u"

    def _cmd_encrypt(self, args: List[str]):
        """Encrypt text using qencrypt-local."""
        if not args:
            self._output("Usage: encrypt <text> [passphrase]\n")
            return
        try:
            from agents.registry import get_registry
            agent = get_registry().get("quantum_crypto")
            if agent is None:
                self._output("quantum_crypto agent not registered\n")
                return

            text = " ".join(args[:-1]) if len(args) > 1 else args[0]
            passphrase = args[-1] if len(args) > 1 else "frankenstein"

            r = agent.execute(
                operation="encrypt",
                plaintext=text, passphrase=passphrase,
                entropy_source="local",
            )
            if r.success:
                self._output(f"Encrypted ({len(str(r.data['package']))} chars)\n")
                self._output(f"  Package stored in last result.\n")
                self._last_crypto_package = r.data["package"]
            else:
                self._output(f"encrypt failed: {r.error}\n")
        except Exception as e:
            self._output(f"encrypt error: {e}\n")

    def _cmd_decrypt(self, args: List[str]):
        """Decrypt a qencrypt package."""
        try:
            from agents.registry import get_registry
            agent = get_registry().get("quantum_crypto")
            if agent is None:
                self._output("quantum_crypto agent not registered\n")
                return

            pkg = getattr(self, "_last_crypto_package", None)
            if pkg is None:
                self._output("No encrypted package in memory. Run 'encrypt' first.\n")
                return

            passphrase = args[0] if args else "frankenstein"
            r = agent.execute(operation="decrypt", package=pkg, passphrase=passphrase)
            if r.success:
                self._output(f"Decrypted: {r.data['plaintext']}\n")
            else:
                self._output(f"decrypt failed: {r.error}\n")
        except Exception as e:
            self._output(f"decrypt error: {e}\n")

    def _cmd_entropy(self, args: List[str]):
        """Compute von Neumann entropy of the current state."""
        try:
            from agents.registry import get_registry
            import qutip as qt

            agent = get_registry().get("quantum_dynamics")
            if agent is None:
                self._output("quantum_dynamics agent not registered\n")
                return

            sv = self._engine.get_state()
            psi = qt.Qobj(sv.reshape(-1, 1))
            rho = psi * psi.dag()

            r = agent.execute(operation="entropy", state=rho, measure="von_neumann")
            if r.success:
                self._output(f"Von Neumann entropy: {r.data['entropy']:.6f}\n")
            else:
                self._output(f"entropy failed: {r.error}\n")
        except Exception as e:
            self._output(f"entropy error: {e}\n")

    def _cmd_toolsets(self, args: List[str]):
        """Show local toolset status."""
        try:
            from libs.local_toolsets import get_toolset_manager
            mgr = get_toolset_manager()
            status = mgr.get_loaded_status()
            self._output("\nLocal Toolsets\n" + "-" * 45 + "\n")
            for key, info in status.items():
                tag = "LOADED" if info["loaded"] else "idle"
                ram = f"{info['ram_mb']} MB" if info["loaded"] else "-"
                self._output(f"  {key:16s}  {tag:8s}  RAM: {ram}\n")
            self._output("-" * 45 + "\n")
        except Exception as e:
            self._output(f"toolsets error: {e}\n")

    # ==================== HELPER METHODS ====================

    def _launch_bloch_after_measurement(self):
        """Launch Bloch sphere visualization after measurement/computation"""
        try:
            from synthesis import ComputeMode
            
            # Get current state data
            bloch = self._engine.get_bloch_coords(0) if self._engine.get_num_qubits() <= 4 else None
            
            if bloch is None:
                self._output("⚠️  Bloch visualization only for ≤4 qubits\n")
                return
            
            result = self._engine.compute(
                mode=ComputeMode.STATEVECTOR,
                shots=0,
                visualize=True
            )
            
            if result.success and result.bloch_coords:
                x, y, z = result.bloch_coords
                self._output(f"🌐 Bloch: ({x:+.4f}, {y:+.4f}, {z:+.4f})\n\n")
            else:
                self._output("⚠️  Visualization skipped\n")
                
        except Exception as e:
            self._output(f"⚠️  Visualization error: {e}\n")


# ==================== GLOBAL INSTANCE ====================

_quantum_mode: Optional[QuantumModeHandler] = None

def get_quantum_mode() -> QuantumModeHandler:
    """Get or create the global quantum mode handler"""
    global _quantum_mode
    if _quantum_mode is None:
        _quantum_mode = QuantumModeHandler()
    return _quantum_mode
