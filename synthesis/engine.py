#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Synthesis Engine
Phase 2, Step 3: Core Synthesis Engine

Purpose: Orchestrate quantum-classical hybrid computations using local hardware
         No external quantum hardware connections - pure simulation on Tier 1 hardware
         
Features:
- Pure NumPy/SciPy quantum state simulation
- Schrödinger equation solver with time evolution
- Lorentz transformation support for relativistic corrections
- Integration with Monster Terminal
- Auto-launch 3D Bloch sphere visualization after calculations

Author: Frankenstein Project
Hardware Target: Dell i3 8th Gen (Tier 1) - 4 cores, 8GB RAM
"""

import os
import sys
import time
import json
import threading
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

import numpy as np
from numpy import pi, sqrt, exp, sin, cos

# Optional SciPy for advanced solvers
try:
    from scipy import linalg as sp_linalg
    from scipy.integrate import solve_ivp
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class ComputeMode(Enum):
    """Computation execution modes"""
    STATEVECTOR = "statevector"      # Pure state simulation
    DENSITY = "density"               # Density matrix simulation  
    SCHRODINGER = "schrodinger"       # Time evolution via Schrödinger eq
    UNITARY = "unitary"               # Unitary matrix computation


class VisualizationMode(Enum):
    """Output visualization modes"""
    NONE = "none"
    TERMINAL = "terminal"             # ASCII in Monster Terminal
    BLOCH_3D = "bloch_3d"            # 3D HTML Bloch sphere
    HISTOGRAM = "histogram"           # Measurement probability histogram


@dataclass
class ComputeResult:
    """Result from a quantum computation"""
    result_id: str
    mode: ComputeMode
    success: bool
    
    # State data
    statevector: Optional[np.ndarray] = None
    density_matrix: Optional[np.ndarray] = None
    probabilities: Optional[Dict[str, float]] = None
    measurements: Optional[Dict[str, int]] = None
    
    # Bloch sphere coordinates (for single qubit)
    bloch_coords: Optional[Tuple[float, float, float]] = None
    
    # Metadata
    num_qubits: int = 1
    gate_count: int = 0
    compute_time_ms: float = 0.0
    error: Optional[str] = None
    
    # Time evolution data (for Schrödinger mode)
    time_points: Optional[np.ndarray] = None
    state_history: Optional[List[np.ndarray]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            "result_id": self.result_id,
            "mode": self.mode.value,
            "success": self.success,
            "statevector_real": self.statevector.real.tolist() if self.statevector is not None else None,
            "statevector_imag": self.statevector.imag.tolist() if self.statevector is not None else None,
            "probabilities": self.probabilities,
            "measurements": self.measurements,
            "bloch_coords": list(self.bloch_coords) if self.bloch_coords else None,
            "num_qubits": self.num_qubits,
            "gate_count": self.gate_count,
            "compute_time_ms": self.compute_time_ms,
            "error": self.error
        }


class SynthesisEngine:
    """
    Core Synthesis Engine for FRANKENSTEIN 1.0
    
    Provides quantum-classical hybrid computation using only local hardware.
    Optimized for Tier 1 constraints (Dell i3, 8GB RAM).
    
    Max recommended:
    - Statevector: 16 qubits (65,536 amplitudes = ~1MB complex128)
    - Density matrix: 10 qubits (1M elements = ~16MB complex128)
    """
    
    # Hardware limits for Tier 1
    MAX_QUBITS_STATEVECTOR = 16
    MAX_QUBITS_DENSITY = 10
    
    def __init__(self, auto_visualize: bool = True, visualization_mode: VisualizationMode = VisualizationMode.BLOCH_3D):
        """
        Initialize the Synthesis Engine.
        
        Args:
            auto_visualize: Automatically show visualization after computation
            visualization_mode: Default visualization mode
        """
        self.auto_visualize = auto_visualize
        self.visualization_mode = visualization_mode
        
        # Quantum state (working register)
        self._num_qubits = 1
        self._statevector: Optional[np.ndarray] = None
        self._density_matrix: Optional[np.ndarray] = None
        
        # Circuit tracking (with memory limits to prevent RAM buildup)
        self._gate_log: List[Dict[str, Any]] = []
        self._max_gate_log = 100  # Keep last 100 gates for debugging
        self._result_history: List[ComputeResult] = []
        self._max_results = 50  # Keep last 50 results to prevent RAM overflow
        
        # Callbacks
        self._output_callback: Optional[Callable[[str], None]] = None
        self._visualization_callback: Optional[Callable[[ComputeResult], None]] = None
        
        # Initialize to |0⟩
        self.reset(1)
    
    def set_output_callback(self, callback: Callable[[str], None]):
        """Set callback for terminal output"""
        self._output_callback = callback
    
    def set_visualization_callback(self, callback: Callable[[ComputeResult], None]):
        """Set callback for visualization trigger"""
        self._visualization_callback = callback
    
    def _output(self, text: str):
        """Output text to terminal or stdout"""
        if self._output_callback:
            self._output_callback(text)
        else:
            print(text)
    
    def reset(self, num_qubits: int = 1):
        """
        Reset the quantum register to |0...0⟩ state.
        
        Args:
            num_qubits: Number of qubits (1-16 for statevector mode)
        """
        if num_qubits > self.MAX_QUBITS_STATEVECTOR:
            raise ValueError(f"Max {self.MAX_QUBITS_STATEVECTOR} qubits for Tier 1 hardware")
        
        self._num_qubits = num_qubits
        dim = 2 ** num_qubits
        
        # Initialize to |0...0⟩
        self._statevector = np.zeros(dim, dtype=np.complex128)
        self._statevector[0] = 1.0 + 0j
        
        self._density_matrix = None
        self._gate_log = []
    
    def set_state(self, state: np.ndarray):
        """
        Set custom initial state.
        
        Args:
            state: Complex amplitude vector (will be normalized)
        """
        state = np.array(state, dtype=np.complex128)
        norm = np.linalg.norm(state)
        if norm < 1e-10:
            raise ValueError("State vector has zero norm")
        
        self._statevector = state / norm
        self._num_qubits = int(np.log2(len(state)))
    
    # ==================== QUANTUM GATES ====================
    
    def apply_gate(self, gate: np.ndarray, target: int, control: Optional[int] = None):
        """
        Apply a quantum gate to the statevector.
        
        Args:
            gate: 2x2 unitary matrix
            target: Target qubit index (0-indexed from right/LSB)
            control: Optional control qubit for controlled gates
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized. Call reset() first.")
        
        n = self._num_qubits
        dim = 2 ** n
        
        if control is None:
            # Single-qubit gate
            full_gate = self._expand_gate(gate, target, n)
        else:
            # Controlled gate
            full_gate = self._expand_controlled_gate(gate, control, target, n)
        
        self._statevector = full_gate @ self._statevector
        self._gate_log.append({
            "gate": gate.tolist(),
            "target": target,
            "control": control,
            "timestamp": time.time()
        })
        # Trim gate log to prevent memory buildup
        if len(self._gate_log) > self._max_gate_log:
            self._gate_log.pop(0)
    
    def _expand_gate(self, gate: np.ndarray, target: int, n: int) -> np.ndarray:
        """Expand single-qubit gate to full n-qubit space using tensor products"""
        result = np.array([[1.0]], dtype=np.complex128)
        
        for i in range(n):
            if i == target:
                result = np.kron(gate, result)
            else:
                result = np.kron(np.eye(2, dtype=np.complex128), result)
        
        return result
    
    def _expand_controlled_gate(self, gate: np.ndarray, control: int, target: int, n: int) -> np.ndarray:
        """Expand controlled gate to full n-qubit space"""
        dim = 2 ** n
        full_gate = np.eye(dim, dtype=np.complex128)
        
        # Iterate through all basis states
        for i in range(dim):
            # Check if control qubit is |1⟩
            if (i >> control) & 1:
                # Apply gate to target qubit
                target_bit = (i >> target) & 1
                for new_target_bit in range(2):
                    j = i ^ (target_bit << target) ^ (new_target_bit << target)
                    full_gate[j, i] = gate[new_target_bit, target_bit]
                    if new_target_bit != target_bit:
                        full_gate[i, i] = 0  # Clear diagonal if modified
        
        return full_gate
    
    # ==================== STANDARD GATE SET ====================
    
    # Pauli gates
    PAULI_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
    PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
    PAULI_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
    
    # Hadamard
    HADAMARD = np.array([[1, 1], [1, -1]], dtype=np.complex128) / sqrt(2)
    
    # Phase gates
    S_GATE = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
    T_GATE = np.array([[1, 0], [0, exp(1j * pi / 4)]], dtype=np.complex128)
    
    # Identity
    IDENTITY = np.eye(2, dtype=np.complex128)
    
    @staticmethod
    def rx(theta: float) -> np.ndarray:
        """Rotation around X axis"""
        return np.array([
            [cos(theta/2), -1j * sin(theta/2)],
            [-1j * sin(theta/2), cos(theta/2)]
        ], dtype=np.complex128)
    
    @staticmethod
    def ry(theta: float) -> np.ndarray:
        """Rotation around Y axis"""
        return np.array([
            [cos(theta/2), -sin(theta/2)],
            [sin(theta/2), cos(theta/2)]
        ], dtype=np.complex128)
    
    @staticmethod
    def rz(theta: float) -> np.ndarray:
        """Rotation around Z axis"""
        return np.array([
            [exp(-1j * theta/2), 0],
            [0, exp(1j * theta/2)]
        ], dtype=np.complex128)
    
    @staticmethod
    def phase(phi: float) -> np.ndarray:
        """General phase gate"""
        return np.array([[1, 0], [0, exp(1j * phi)]], dtype=np.complex128)
    
    # ==================== CONVENIENCE METHODS ====================
    
    def x(self, target: int):
        """Apply Pauli-X (NOT) gate"""
        self.apply_gate(self.PAULI_X, target)
    
    def y(self, target: int):
        """Apply Pauli-Y gate"""
        self.apply_gate(self.PAULI_Y, target)
    
    def z(self, target: int):
        """Apply Pauli-Z gate"""
        self.apply_gate(self.PAULI_Z, target)
    
    def h(self, target: int):
        """Apply Hadamard gate"""
        self.apply_gate(self.HADAMARD, target)
    
    def s(self, target: int):
        """Apply S (√Z) gate"""
        self.apply_gate(self.S_GATE, target)
    
    def t(self, target: int):
        """Apply T (π/8) gate"""
        self.apply_gate(self.T_GATE, target)
    
    def cx(self, control: int, target: int):
        """Apply CNOT (controlled-X) gate"""
        self.apply_gate(self.PAULI_X, target, control)
    
    def cz(self, control: int, target: int):
        """Apply controlled-Z gate"""
        self.apply_gate(self.PAULI_Z, target, control)
    
    def rotate_x(self, target: int, theta: float):
        """Apply Rx rotation"""
        self.apply_gate(self.rx(theta), target)
    
    def rotate_y(self, target: int, theta: float):
        """Apply Ry rotation"""
        self.apply_gate(self.ry(theta), target)
    
    def rotate_z(self, target: int, theta: float):
        """Apply Rz rotation"""
        self.apply_gate(self.rz(theta), target)
    
    # ==================== MEASUREMENT ====================
    
    def get_probabilities(self) -> Dict[str, float]:
        """
        Get measurement probabilities for all basis states.
        
        Returns:
            Dict mapping binary strings to probabilities
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized")
        
        probs = {}
        for i, amp in enumerate(self._statevector):
            prob = float(np.abs(amp) ** 2)
            if prob > 1e-10:  # Filter near-zero
                basis = format(i, f'0{self._num_qubits}b')
                probs[basis] = prob
        
        return probs
    
    def measure(self, shots: int = 1024) -> Dict[str, int]:
        """
        Perform measurement simulation.
        
        Args:
            shots: Number of measurement repetitions
            
        Returns:
            Dict mapping basis states to count
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized")
        
        probs = np.abs(self._statevector) ** 2
        indices = np.arange(len(probs))
        
        samples = np.random.choice(indices, size=shots, p=probs)
        
        counts = {}
        for idx in samples:
            basis = format(idx, f'0{self._num_qubits}b')
            counts[basis] = counts.get(basis, 0) + 1
        
        return dict(sorted(counts.items()))
    
    def measure_single(self, qubit: int) -> int:
        """
        Measure a single qubit (collapses state).
        
        Args:
            qubit: Qubit index to measure
            
        Returns:
            Measurement outcome (0 or 1)
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized")
        
        # Calculate probability of measuring |1⟩ on target qubit
        p1 = 0.0
        for i, amp in enumerate(self._statevector):
            if (i >> qubit) & 1:
                p1 += np.abs(amp) ** 2
        
        # Collapse based on probability
        outcome = 1 if np.random.random() < p1 else 0
        
        # Project and renormalize
        new_state = np.zeros_like(self._statevector)
        for i, amp in enumerate(self._statevector):
            if ((i >> qubit) & 1) == outcome:
                new_state[i] = amp
        
        norm = np.linalg.norm(new_state)
        self._statevector = new_state / norm
        
        return outcome
    
    # ==================== BLOCH SPHERE ====================
    
    def get_bloch_coords(self, qubit: int = 0) -> Tuple[float, float, float]:
        """
        Get Bloch sphere coordinates for a single qubit.
        
        For multi-qubit states, traces out other qubits to get
        reduced density matrix.
        
        Args:
            qubit: Which qubit to get coordinates for
            
        Returns:
            (x, y, z) Bloch sphere coordinates
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized")
        
        if self._num_qubits == 1:
            # Direct calculation for single qubit
            alpha = self._statevector[0]
            beta = self._statevector[1]
            
            # Bloch coordinates from |ψ⟩ = α|0⟩ + β|1⟩
            x = float(2 * np.real(np.conj(alpha) * beta))
            y = float(2 * np.imag(np.conj(alpha) * beta))
            z = float(np.abs(alpha)**2 - np.abs(beta)**2)
            
            return (x, y, z)
        else:
            # Partial trace to get reduced density matrix
            rho = self._partial_trace(qubit)
            
            # Extract Bloch coordinates from density matrix
            # ρ = (I + x·σx + y·σy + z·σz) / 2
            x = float(2 * np.real(rho[0, 1]))
            y = float(2 * np.imag(rho[1, 0]))
            z = float(np.real(rho[0, 0] - rho[1, 1]))
            
            return (x, y, z)
    
    def _partial_trace(self, keep_qubit: int) -> np.ndarray:
        """
        Compute partial trace, keeping only one qubit.
        
        Args:
            keep_qubit: Index of qubit to keep
            
        Returns:
            2x2 reduced density matrix
        """
        n = self._num_qubits
        dim = 2 ** n
        
        # Full density matrix
        rho_full = np.outer(self._statevector, np.conj(self._statevector))
        
        # Trace out all other qubits
        rho_reduced = np.zeros((2, 2), dtype=np.complex128)
        
        for i in range(2):
            for j in range(2):
                for k in range(dim):
                    for l in range(dim):
                        # Check if keep_qubit has values i, j
                        if ((k >> keep_qubit) & 1) == i and ((l >> keep_qubit) & 1) == j:
                            # Check if all other qubits match
                            other_k = k ^ (i << keep_qubit)
                            other_l = l ^ (j << keep_qubit)
                            if other_k == other_l:
                                rho_reduced[i, j] += rho_full[k, l]
        
        return rho_reduced
    
    # ==================== SCHRÖDINGER EQUATION SOLVER ====================
    
    def evolve_schrodinger(
        self,
        hamiltonian: np.ndarray,
        t_span: Tuple[float, float],
        num_points: int = 100,
        hbar: float = 1.0
    ) -> Tuple[np.ndarray, List[np.ndarray]]:
        """
        Solve the time-dependent Schrödinger equation.
        
        iℏ ∂|ψ⟩/∂t = H|ψ⟩
        
        Args:
            hamiltonian: Hamiltonian matrix (must match statevector dimension)
            t_span: (t_start, t_end) time interval
            num_points: Number of time points to evaluate
            hbar: Reduced Planck constant (default 1 for natural units)
            
        Returns:
            (time_points, state_history) where state_history[i] is |ψ(t_i)⟩
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized")
        
        dim = len(self._statevector)
        if hamiltonian.shape != (dim, dim):
            raise ValueError(f"Hamiltonian must be {dim}x{dim}")
        
        # Initial state
        psi0 = self._statevector.copy()
        
        # Time points
        t_eval = np.linspace(t_span[0], t_span[1], num_points)
        
        if SCIPY_AVAILABLE:
            # Use SciPy's ODE solver for better accuracy
            def schrodinger_rhs(t, psi_flat):
                psi = psi_flat[:dim] + 1j * psi_flat[dim:]
                dpsi_dt = -1j / hbar * (hamiltonian @ psi)
                return np.concatenate([dpsi_dt.real, dpsi_dt.imag])
            
            # Flatten complex to real for solver
            y0 = np.concatenate([psi0.real, psi0.imag])
            
            sol = solve_ivp(
                schrodinger_rhs,
                t_span,
                y0,
                t_eval=t_eval,
                method='RK45',
                rtol=1e-8,
                atol=1e-10
            )
            
            # Reconstruct complex states
            state_history = []
            for i in range(len(sol.t)):
                psi = sol.y[:dim, i] + 1j * sol.y[dim:, i]
                # Renormalize (numerical drift)
                psi = psi / np.linalg.norm(psi)
                state_history.append(psi)
            
            return sol.t, state_history
        else:
            # Fallback: Simple Euler method (less accurate but functional)
            dt = (t_span[1] - t_span[0]) / (num_points - 1)
            state_history = [psi0.copy()]
            psi = psi0.copy()
            
            for _ in range(num_points - 1):
                dpsi = -1j / hbar * (hamiltonian @ psi) * dt
                psi = psi + dpsi
                psi = psi / np.linalg.norm(psi)  # Renormalize
                state_history.append(psi.copy())
            
            return t_eval, state_history
    
    def evolve_unitary(self, time: float, hamiltonian: np.ndarray, hbar: float = 1.0):
        """
        Evolve state by time t using matrix exponential.
        
        |ψ(t)⟩ = exp(-iHt/ℏ)|ψ(0)⟩
        
        This is exact for time-independent Hamiltonians.
        
        Args:
            time: Evolution time
            hamiltonian: Hamiltonian matrix
            hbar: Reduced Planck constant
        """
        if self._statevector is None:
            raise RuntimeError("No statevector initialized")
        
        if SCIPY_AVAILABLE:
            U = sp_linalg.expm(-1j * hamiltonian * time / hbar)
        else:
            # Fallback: Taylor series approximation (less accurate)
            U = np.eye(len(hamiltonian), dtype=np.complex128)
            term = np.eye(len(hamiltonian), dtype=np.complex128)
            factor = -1j * time / hbar
            
            for k in range(1, 20):  # 20 terms
                term = term @ hamiltonian * factor / k
                U = U + term
                if np.max(np.abs(term)) < 1e-12:
                    break
        
        self._statevector = U @ self._statevector
        self._statevector = self._statevector / np.linalg.norm(self._statevector)
    
    # ==================== LORENTZ TRANSFORMATIONS ====================
    
    def lorentz_boost_phase(self, velocity: float, position: float = 0.0, c: float = 1.0):
        """
        Apply relativistic phase correction via Lorentz boost.
        
        In quantum mechanics, a Lorentz boost introduces a phase factor
        that depends on the particle's position and momentum.
        
        For a simplified model, we apply:
        |ψ⟩ → exp(iγmv·x/ℏ)|ψ⟩
        
        where γ = 1/√(1 - v²/c²) is the Lorentz factor.
        
        Args:
            velocity: Boost velocity (|v| < c)
            position: Particle position
            c: Speed of light (default 1 for natural units)
        """
        if abs(velocity) >= c:
            raise ValueError(f"Velocity must be less than c ({c})")
        
        gamma = 1.0 / sqrt(1 - (velocity/c)**2)
        
        # Phase factor (simplified model)
        phase = gamma * velocity * position
        
        self._statevector = self._statevector * exp(1j * phase)
    
    def apply_time_dilation(self, proper_time: float, velocity: float, c: float = 1.0) -> float:
        """
        Calculate dilated time for a moving quantum system.
        
        t = γ·τ where τ is proper time
        
        Args:
            proper_time: Time in rest frame
            velocity: System velocity
            c: Speed of light
            
        Returns:
            Dilated time in lab frame
        """
        if abs(velocity) >= c:
            raise ValueError(f"Velocity must be less than c ({c})")
        
        gamma = 1.0 / sqrt(1 - (velocity/c)**2)
        return gamma * proper_time
    
    # ==================== COMPUTATION ENTRY POINT ====================
    
    def compute(
        self,
        mode: ComputeMode = ComputeMode.STATEVECTOR,
        shots: int = 1024,
        visualize: Optional[bool] = None
    ) -> ComputeResult:
        """
        Execute computation and return results.
        
        Args:
            mode: Computation mode
            shots: Number of measurement shots (for STATEVECTOR mode)
            visualize: Override auto_visualize setting
            
        Returns:
            ComputeResult with all relevant data
        """
        start_time = time.time()
        result_id = f"synth_{uuid.uuid4().hex[:8]}"
        
        try:
            probs = self.get_probabilities()
            measurements = self.measure(shots) if shots > 0 else None
            bloch = self.get_bloch_coords(0) if self._num_qubits <= 4 else None
            
            result = ComputeResult(
                result_id=result_id,
                mode=mode,
                success=True,
                statevector=self._statevector.copy(),
                probabilities=probs,
                measurements=measurements,
                bloch_coords=bloch,
                num_qubits=self._num_qubits,
                gate_count=len(self._gate_log),
                compute_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            result = ComputeResult(
                result_id=result_id,
                mode=mode,
                success=False,
                error=str(e),
                num_qubits=self._num_qubits,
                gate_count=len(self._gate_log),
                compute_time_ms=(time.time() - start_time) * 1000
            )
        
        self._result_history.append(result)
        # Trim result history to prevent RAM overflow
        if len(self._result_history) > self._max_results:
            self._result_history.pop(0)

        # Trigger visualization
        do_viz = visualize if visualize is not None else self.auto_visualize
        if do_viz and result.success:
            self._trigger_visualization(result)
        
        return result
    
    def _trigger_visualization(self, result: ComputeResult):
        """Trigger visualization based on mode"""
        if self._visualization_callback:
            self._visualization_callback(result)
        elif self.visualization_mode == VisualizationMode.BLOCH_3D:
            self._launch_bloch_sphere(result)
        elif self.visualization_mode == VisualizationMode.TERMINAL:
            self._print_ascii_bloch(result)
    
    def _launch_bloch_sphere(self, result: ComputeResult):
        """Launch 3D Bloch sphere in browser"""
        if result.bloch_coords is None:
            self._output("⚠️  Bloch visualization only available for ≤4 qubit systems\n")
            return
        
        # Find the HTML file
        widget_dir = Path(__file__).parent.parent / "widget"
        html_path = widget_dir / "bloch_sphere.html"
        
        if not html_path.exists():
            self._output(f"⚠️  Bloch sphere HTML not found at {html_path}\n")
            return
        
        # Create temp HTML with embedded data
        x, y, z = result.bloch_coords
        
        # Read template and inject data
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inject coordinates
        html_content = html_content.replace('{{BLOCH_X}}', str(x))
        html_content = html_content.replace('{{BLOCH_Y}}', str(y))
        html_content = html_content.replace('{{BLOCH_Z}}', str(z))
        
        # Inject probabilities
        probs_json = json.dumps(result.probabilities or {})
        html_content = html_content.replace('{{PROBABILITIES}}', probs_json)
        
        # Inject statevector
        if result.statevector is not None:
            sv_data = {
                'real': result.statevector.real.tolist(),
                'imag': result.statevector.imag.tolist()
            }
            html_content = html_content.replace('{{STATEVECTOR}}', json.dumps(sv_data))
        
        # Write temp file
        temp_dir = Path.home() / ".frankenstein" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_html = temp_dir / f"bloch_{result.result_id}.html"
        
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Launch in browser
        webbrowser.open(f'file:///{temp_html.as_posix()}')
        self._output(f"🌐 Launched Bloch sphere visualization: {temp_html.name}\n")
    
    def _print_ascii_bloch(self, result: ComputeResult):
        """Print ASCII representation of Bloch sphere"""
        if result.bloch_coords is None:
            return
        
        x, y, z = result.bloch_coords
        
        output = f"""
╔═══════════════════════════════════════╗
║         BLOCH SPHERE COORDINATES      ║
╠═══════════════════════════════════════╣
║  x = {x:+.6f}                        ║
║  y = {y:+.6f}                        ║
║  z = {z:+.6f}                        ║
╠═══════════════════════════════════════╣
║  |ψ⟩ = {self._format_state()}
╚═══════════════════════════════════════╝
"""
        self._output(output)
    
    def _format_state(self) -> str:
        """Format statevector as ket notation"""
        if self._statevector is None or self._num_qubits > 2:
            return "..."
        
        terms = []
        for i, amp in enumerate(self._statevector):
            if np.abs(amp) > 1e-6:
                basis = format(i, f'0{self._num_qubits}b')
                
                # Format amplitude
                if np.abs(amp.imag) < 1e-6:
                    amp_str = f"{amp.real:.3f}"
                elif np.abs(amp.real) < 1e-6:
                    amp_str = f"{amp.imag:.3f}i"
                else:
                    amp_str = f"({amp.real:.3f}{amp.imag:+.3f}i)"
                
                terms.append(f"{amp_str}|{basis}⟩")
        
        return " + ".join(terms) if terms else "0"
    
    # ==================== UTILITY METHODS ====================
    
    def get_state(self) -> Optional[np.ndarray]:
        """Get current statevector (copy)"""
        return self._statevector.copy() if self._statevector is not None else None
    
    def get_num_qubits(self) -> int:
        """Get number of qubits"""
        return self._num_qubits
    
    def get_gate_count(self) -> int:
        """Get number of gates applied"""
        return len(self._gate_log)
    
    def get_result_history(self) -> List[ComputeResult]:
        """Get history of computation results"""
        return self._result_history.copy()
    
    def print_state(self):
        """Print current state to output"""
        if self._statevector is None:
            self._output("No state initialized\n")
            return
        
        self._output(f"\n|ψ⟩ = {self._format_state()}\n")
        self._output(f"Qubits: {self._num_qubits}, Gates: {len(self._gate_log)}\n\n")


# ==================== GLOBAL INSTANCE ====================

_engine: Optional[SynthesisEngine] = None

def get_synthesis_engine() -> SynthesisEngine:
    """Get or create the global synthesis engine instance"""
    global _engine
    if _engine is None:
        _engine = SynthesisEngine()
    return _engine


# ==================== PREDEFINED HAMILTONIANS ====================

def hamiltonian_pauli_x(omega: float = 1.0) -> np.ndarray:
    """Hamiltonian for Rabi oscillations: H = ω·σx/2"""
    return omega * SynthesisEngine.PAULI_X / 2

def hamiltonian_pauli_z(omega: float = 1.0) -> np.ndarray:
    """Hamiltonian for Larmor precession: H = ω·σz/2"""
    return omega * SynthesisEngine.PAULI_Z / 2

def hamiltonian_free_precession(omega_0: float = 1.0, omega_1: float = 0.1) -> np.ndarray:
    """Combined free precession + driving: H = ω₀·σz/2 + ω₁·σx/2"""
    return omega_0 * SynthesisEngine.PAULI_Z / 2 + omega_1 * SynthesisEngine.PAULI_X / 2
