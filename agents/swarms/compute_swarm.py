#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Compute Swarm
Phase 2 Step 3: Multi-Agent Computational System

Real computational agents using the Swarms framework.
Each agent specializes in a domain: physics, math, quantum simulation.

Hardware Constraints (Tier 1 - Dell i3 8th Gen):
- Max concurrent agents: 3
- Memory limit per agent: 1GB
- CPU throttle: 80% max
"""

import os
import sys
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio

# ---------------------------------------------------------------------------
# Accelerator import — tensor MSB gate ops (Step 5 fix)
# Replaces kron-based _tensor_gate and _controlled_gate in QuantumSimAgent
# ---------------------------------------------------------------------------
try:
    from synthesis.accelerator import (
        apply_single_qubit_gate as _accel_single,
        apply_controlled_gate   as _accel_controlled,
        apply_mcx_gate          as _accel_mcx,
        get_backend_name        as _accel_backend,
    )
    _ACCEL_AVAILABLE = True
except ImportError:
    _ACCEL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Priority integration bridges — lazy imports (loaded only when first called)
# ---------------------------------------------------------------------------
# Priority 1 — VQE: QuantumCompute.vqe() is already the closed-loop runner;
#              ComputeSwarm.run_vqe() delegates to it with physics Hamiltonians.
# Priority 2 — Density matrix: QuantumState.to_density_matrix() added to
#              quantum_compute.py; ComputeSwarm.apply_circuit_decoherence() wraps it.
# Priority 3 — Hamiltonian from physics: ComputeSwarm.hamiltonian_from_physics()
#              translates PhysicsCompute params → QuantumCompute Hamiltonian matrix.
# Priority 4 — Lorentz-boosted gates: ComputeSwarm.apply_lorentz_circuit()
#              wraps QuantumCompute.lorentz_boosted_rotation().

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for swarms availability
try:
    from swarms import Agent
    from swarms.structs import ConcurrentWorkflow
    SWARMS_AVAILABLE = True
except ImportError:
    SWARMS_AVAILABLE = False
    logger.warning("Swarms framework not available. Using fallback mode.")

# Import safety constraints
try:
    from core.safety import SafetyConstraints
    from core.governor import get_governor
    SAFETY_AVAILABLE = True
except ImportError:
    SAFETY_AVAILABLE = False
    logger.warning("Safety module not available.")


# ============================================================================
# TIER 1 HARDWARE CONSTRAINTS
# ============================================================================

TIER1_LIMITS = {
    "max_concurrent_agents": 3,
    "max_memory_per_agent_mb": 1024,
    "max_cpu_percent": 80,
    "max_computation_time_sec": 30,
    "max_matrix_dimension": 512,
    "max_qubits_simulated": 16,
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ComputeTask:
    """A computational task to be executed by agents."""
    task_id: str
    task_type: str  # "physics", "math", "quantum", "synthesis"
    description: str
    input_data: Dict[str, Any]
    priority: int = 5  # 1-10, 10 is highest
    timeout_sec: float = 30.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComputeResult:
    """Result from agent computation."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    computation_time: float = 0.0
    agent_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# BASE COMPUTE AGENT (Fallback when Swarms not available)
# ============================================================================

class BaseComputeAgent:
    """
    Base computational agent with real math/physics capabilities.
    Used as fallback when Swarms framework is not available.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._active = True
        self._computation_count = 0
        self._total_compute_time = 0.0
    
    def execute(self, task: ComputeTask) -> ComputeResult:
        """Execute a computational task. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active": self._active,
            "computations": self._computation_count,
            "total_time": f"{self._total_compute_time:.3f}s"
        }


# ============================================================================
# PHYSICS AGENT - Real Physics Calculations
# ============================================================================

class PhysicsAgent(BaseComputeAgent):
    """
    Agent specialized in physics calculations.
    
    Capabilities:
    - Classical mechanics (kinematics, dynamics)
    - Wave equations (Schrödinger, wave propagation)
    - Relativistic corrections (Lorentz transformations)
    - Conservation law validation
    """
    
    def __init__(self):
        super().__init__(
            name="PhysicsAgent",
            description="Specialized in physics calculations and simulations"
        )
        # Physical constants
        self.HBAR = 1.054571817e-34  # Reduced Planck constant (J·s)
        self.C = 299792458.0          # Speed of light (m/s)
        self.ME = 9.1093837015e-31    # Electron mass (kg)
    
    def execute(self, task: ComputeTask) -> ComputeResult:
        """Execute physics computation."""
        import time
        start = time.time()
        
        try:
            result = None
            
            if task.task_type == "schrodinger":
                result = self._solve_schrodinger(task.input_data)
            elif task.task_type == "lorentz":
                result = self._apply_lorentz(task.input_data)
            elif task.task_type == "wave_propagation":
                result = self._propagate_wave(task.input_data)
            elif task.task_type == "energy_levels":
                result = self._compute_energy_levels(task.input_data)
            else:
                return ComputeResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Unknown physics task: {task.task_type}",
                    agent_name=self.name
                )
            
            self._computation_count += 1
            compute_time = time.time() - start
            self._total_compute_time += compute_time
            
            return ComputeResult(
                task_id=task.task_id,
                success=True,
                result=result,
                computation_time=compute_time,
                agent_name=self.name
            )
            
        except Exception as e:
            return ComputeResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                computation_time=time.time() - start,
                agent_name=self.name
            )
    
    def _solve_schrodinger(self, data: Dict) -> Dict[str, Any]:
        """
        Solve time-dependent Schrödinger equation.
        iℏ ∂ψ/∂t = Ĥψ
        
        Uses split-step Fourier method for efficiency.
        """
        # Extract parameters
        psi_0 = np.array(data.get("initial_state", [1, 0]), dtype=complex)
        hamiltonian = np.array(data.get("hamiltonian", [[0, 1], [1, 0]]), dtype=complex)
        t_max = data.get("t_max", 10.0)
        dt = data.get("dt", 0.01)
        
        # Validate dimensions
        dim = hamiltonian.shape[0]
        if dim > TIER1_LIMITS["max_matrix_dimension"]:
            raise ValueError(f"Matrix dimension {dim} exceeds limit")
        
        # Time evolution using matrix exponential
        n_steps = int(t_max / dt)
        n_steps = min(n_steps, 10000)  # Safety limit
        
        # Compute evolution operator U = exp(-iHt/ℏ)
        times = np.linspace(0, t_max, n_steps + 1)
        states = np.zeros((n_steps + 1, dim), dtype=complex)
        states[0] = psi_0 / np.linalg.norm(psi_0)
        
        # Diagonalize Hamiltonian for efficient evolution
        eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
        
        for i, t in enumerate(times[1:], 1):
            # Transform to energy basis
            c = eigenvectors.T.conj() @ states[i-1]
            # Evolve in energy basis
            c *= np.exp(-1j * eigenvalues * dt)
            # Transform back
            states[i] = eigenvectors @ c
            # Normalize
            states[i] /= np.linalg.norm(states[i])
        
        return {
            "times": times.tolist(),
            "states": states.tolist(),
            "eigenvalues": eigenvalues.tolist(),
            "final_state": states[-1].tolist(),
            "norm_preserved": bool(abs(np.linalg.norm(states[-1]) - 1.0) < 1e-6)
        }
    
    def _apply_lorentz(self, data: Dict) -> Dict[str, Any]:
        """
        Apply Lorentz transformation.
        t' = γ(t - vx/c²)
        x' = γ(x - vt)
        """
        velocity = data.get("velocity", 0.5)  # v/c
        t = np.array(data.get("t", [0.0]))
        x = np.array(data.get("x", [0.0]))
        
        if abs(velocity) >= 1.0:
            raise ValueError("Velocity must be |v/c| < 1")
        
        gamma = 1.0 / np.sqrt(1 - velocity**2)
        
        t_prime = gamma * (t - velocity * x)
        x_prime = gamma * (x - velocity * t)
        
        return {
            "velocity": velocity,
            "gamma": gamma,
            "t_prime": t_prime.tolist(),
            "x_prime": x_prime.tolist(),
            "time_dilation": 1/gamma,
            "length_contraction": 1/gamma
        }
    
    def _propagate_wave(self, data: Dict) -> Dict[str, Any]:
        """Propagate wave packet in 1D potential."""
        x_min = data.get("x_min", -10)
        x_max = data.get("x_max", 10)
        n_points = min(data.get("n_points", 256), TIER1_LIMITS["max_matrix_dimension"])
        k0 = data.get("momentum", 2.0)
        sigma = data.get("width", 1.0)
        
        x = np.linspace(x_min, x_max, n_points)
        dx = x[1] - x[0]
        
        # Gaussian wave packet
        psi = np.exp(-(x**2) / (4*sigma**2)) * np.exp(1j * k0 * x)
        psi /= np.sqrt(np.sum(np.abs(psi)**2) * dx)
        
        return {
            "x": x.tolist(),
            "psi_real": psi.real.tolist(),
            "psi_imag": psi.imag.tolist(),
            "probability": (np.abs(psi)**2).tolist(),
            "norm": float(np.sum(np.abs(psi)**2) * dx)
        }
    
    def _compute_energy_levels(self, data: Dict) -> Dict[str, Any]:
        """Compute energy levels for quantum system."""
        hamiltonian = np.array(data.get("hamiltonian"), dtype=complex)
        eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
        
        return {
            "energies": eigenvalues.tolist(),
            "ground_state_energy": float(eigenvalues[0]),
            "energy_gaps": np.diff(eigenvalues).tolist(),
            "degeneracies": self._find_degeneracies(eigenvalues)
        }
    
    def _find_degeneracies(self, eigenvalues: np.ndarray, tol: float = 1e-10) -> List[int]:
        """Find degeneracies in energy spectrum."""
        degeneracies = []
        i = 0
        while i < len(eigenvalues):
            count = 1
            while i + count < len(eigenvalues) and abs(eigenvalues[i+count] - eigenvalues[i]) < tol:
                count += 1
            degeneracies.append(count)
            i += count
        return degeneracies


# ============================================================================
# MATH AGENT - Real Mathematical Computations
# ============================================================================

class MathAgent(BaseComputeAgent):
    """
    Agent specialized in mathematical computations.
    
    Capabilities:
    - Linear algebra (eigenvalues, SVD, matrix operations)
    - Numerical integration
    - Optimization
    - Statistical analysis
    """
    
    def __init__(self):
        super().__init__(
            name="MathAgent",
            description="Specialized in mathematical computations"
        )
    
    def execute(self, task: ComputeTask) -> ComputeResult:
        """Execute mathematical computation."""
        import time
        start = time.time()
        
        try:
            result = None
            
            if task.task_type == "eigensolve":
                result = self._eigensolve(task.input_data)
            elif task.task_type == "svd":
                result = self._svd(task.input_data)
            elif task.task_type == "integrate":
                result = self._integrate(task.input_data)
            elif task.task_type == "optimize":
                result = self._optimize(task.input_data)
            elif task.task_type == "fft":
                result = self._fft(task.input_data)
            elif task.task_type == "statistics":
                result = self._statistics(task.input_data)
            else:
                return ComputeResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Unknown math task: {task.task_type}",
                    agent_name=self.name
                )
            
            self._computation_count += 1
            compute_time = time.time() - start
            self._total_compute_time += compute_time
            
            return ComputeResult(
                task_id=task.task_id,
                success=True,
                result=result,
                computation_time=compute_time,
                agent_name=self.name
            )
            
        except Exception as e:
            return ComputeResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                computation_time=time.time() - start,
                agent_name=self.name
            )
    
    def _eigensolve(self, data: Dict) -> Dict[str, Any]:
        """Solve eigenvalue problem."""
        matrix = np.array(data.get("matrix"), dtype=complex)
        hermitian = data.get("hermitian", True)
        
        if hermitian:
            eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        else:
            eigenvalues, eigenvectors = np.linalg.eig(matrix)
            # Sort by real part
            idx = np.argsort(eigenvalues.real)
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]
        
        return {
            "eigenvalues": eigenvalues.tolist(),
            "eigenvectors": eigenvectors.tolist(),
            "trace": float(np.trace(matrix).real),
            "determinant": float(np.linalg.det(matrix).real),
            "condition_number": float(np.linalg.cond(matrix))
        }
    
    def _svd(self, data: Dict) -> Dict[str, Any]:
        """Singular value decomposition."""
        matrix = np.array(data.get("matrix"))
        full_matrices = data.get("full_matrices", False)
        
        U, S, Vh = np.linalg.svd(matrix, full_matrices=full_matrices)
        
        return {
            "U": U.tolist(),
            "singular_values": S.tolist(),
            "Vh": Vh.tolist(),
            "rank": int(np.sum(S > 1e-10)),
            "frobenius_norm": float(np.sqrt(np.sum(S**2)))
        }
    
    def _fft(self, data: Dict) -> Dict[str, Any]:
        """Fast Fourier Transform."""
        signal = np.array(data.get("signal"))
        sample_rate = data.get("sample_rate", 1.0)
        
        fft_result = np.fft.fft(signal)
        freqs = np.fft.fftfreq(len(signal), 1/sample_rate)
        
        return {
            "frequencies": freqs.tolist(),
            "amplitudes": np.abs(fft_result).tolist(),
            "phases": np.angle(fft_result).tolist(),
            "power_spectrum": (np.abs(fft_result)**2).tolist()
        }
    
    def _integrate(self, data: Dict) -> Dict[str, Any]:
        """Numerical integration."""
        from scipy import integrate
        
        func_str = data.get("function", "x**2")
        a = data.get("lower", 0)
        b = data.get("upper", 1)
        
        # Create function from string (safely)
        def f(x):
            return eval(func_str, {"x": x, "np": np, "sin": np.sin, 
                                   "cos": np.cos, "exp": np.exp, "sqrt": np.sqrt})
        
        result, error = integrate.quad(f, a, b)
        
        return {
            "integral": float(result),
            "error_estimate": float(error),
            "function": func_str,
            "bounds": [a, b]
        }
    
    def _optimize(self, data: Dict) -> Dict[str, Any]:
        """Optimization (minimize function)."""
        from scipy import optimize
        
        func_str = data.get("function", "x**2")
        x0 = data.get("initial_guess", 0.0)
        
        def f(x):
            return eval(func_str, {"x": x, "np": np, "sin": np.sin, 
                                   "cos": np.cos, "exp": np.exp, "sqrt": np.sqrt})
        
        result = optimize.minimize(lambda x: f(x[0]), [x0], method='BFGS')
        
        return {
            "minimum_x": float(result.x[0]),
            "minimum_value": float(result.fun),
            "converged": bool(result.success),
            "iterations": int(result.nit)
        }
    
    def _statistics(self, data: Dict) -> Dict[str, Any]:
        """Statistical analysis."""
        values = np.array(data.get("data"))
        
        return {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "variance": float(np.var(values)),
            "median": float(np.median(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "percentiles": {
                "25": float(np.percentile(values, 25)),
                "50": float(np.percentile(values, 50)),
                "75": float(np.percentile(values, 75))
            }
        }


# ============================================================================
# QUANTUM SIMULATION AGENT
# ============================================================================

class QuantumSimAgent(BaseComputeAgent):
    """
    Agent specialized in quantum simulation.
    
    Capabilities:
    - Qubit state manipulation
    - Quantum gate operations
    - Measurement simulation
    - Entanglement metrics
    """
    
    def __init__(self):
        super().__init__(
            name="QuantumSimAgent",
            description="Specialized in quantum simulation"
        )
        self._max_qubits = TIER1_LIMITS["max_qubits_simulated"]
        
        # Pauli matrices
        self.I = np.array([[1, 0], [0, 1]], dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)
        self.H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    
    def execute(self, task: ComputeTask) -> ComputeResult:
        """Execute quantum simulation."""
        import time
        start = time.time()
        
        try:
            result = None
            
            if task.task_type == "circuit":
                result = self._run_circuit(task.input_data)
            elif task.task_type == "measure":
                result = self._measure(task.input_data)
            elif task.task_type == "entanglement":
                result = self._compute_entanglement(task.input_data)
            elif task.task_type == "bloch":
                result = self._bloch_coordinates(task.input_data)
            else:
                return ComputeResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Unknown quantum task: {task.task_type}",
                    agent_name=self.name
                )
            
            self._computation_count += 1
            compute_time = time.time() - start
            self._total_compute_time += compute_time
            
            return ComputeResult(
                task_id=task.task_id,
                success=True,
                result=result,
                computation_time=compute_time,
                agent_name=self.name
            )
            
        except Exception as e:
            return ComputeResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                computation_time=time.time() - start,
                agent_name=self.name
            )
    
    def _run_circuit(self, data: Dict) -> Dict[str, Any]:
        """Run quantum circuit."""
        n_qubits = data.get("n_qubits", 1)
        gates = data.get("gates", [])  # List of {"gate": "H", "target": 0, ...}
        
        if n_qubits > self._max_qubits:
            raise ValueError(f"n_qubits={n_qubits} exceeds limit {self._max_qubits}")
        
        # Initialize state |00...0⟩
        dim = 2 ** n_qubits
        state = np.zeros(dim, dtype=complex)
        state[0] = 1.0
        
        # Apply gates
        applied_gates = []
        for gate_spec in gates:
            gate_name = gate_spec.get("gate", "I")
            target = gate_spec.get("target", 0)
            control = gate_spec.get("control", None)
            angle = gate_spec.get("angle", None)
            
            state = self._apply_gate(state, n_qubits, gate_name, target, control, angle)
            applied_gates.append(gate_spec)
        
        # Compute probabilities
        probabilities = np.abs(state) ** 2
        
        return {
            "state": state.tolist(),
            "probabilities": probabilities.tolist(),
            "n_qubits": n_qubits,
            "gates_applied": len(applied_gates),
            "norm": float(np.linalg.norm(state))
        }
    
    def _apply_gate_to_state(self, state: np.ndarray, n_qubits: int,
                             gate: np.ndarray, target: int,
                             control: Optional[int] = None) -> np.ndarray:
        """
        Apply a 2×2 gate matrix in-place via tensor MSB indexing.

        Step 5 fix: replaces kron-based _tensor_gate and full-matrix
        _controlled_gate. Memory: O(2^n) not O(4^n).

        Uses accelerator (JAX/Numba/NumPy) when available, otherwise
        falls back to pure-NumPy tensor MSB loop.
        """
        if _ACCEL_AVAILABLE:
            if control is None:
                return _accel_single(state, gate, target, n_qubits)
            else:
                return _accel_controlled(state, gate, control, target, n_qubits)

        # NumPy tensor MSB fallback
        sv = state.copy()
        if control is None:
            step = 1 << (n_qubits - 1 - target)
            for i in range(0, len(sv), step * 2):
                for j in range(i, i + step):
                    a, b = sv[j], sv[j + step]
                    sv[j]        = gate[0, 0] * a + gate[0, 1] * b
                    sv[j + step] = gate[1, 0] * a + gate[1, 1] * b
        else:
            c_step = 1 << (n_qubits - 1 - control)
            t_step = 1 << (n_qubits - 1 - target)
            for i in range(len(sv)):
                if (i & c_step) and not (i & t_step):
                    j = i | t_step
                    a, b = sv[i], sv[j]
                    sv[i] = gate[0, 0] * a + gate[0, 1] * b
                    sv[j] = gate[1, 0] * a + gate[1, 1] * b
        return sv

    def _apply_gate(self, state: np.ndarray, n_qubits: int, gate_name: str,
                    target: int, control: Optional[int] = None,
                    angle: Optional[float] = None) -> np.ndarray:
        """Apply a named quantum gate to state — tensor MSB, no kron."""
        # Get single-qubit gate matrix
        if gate_name == "H":
            gate = self.H
        elif gate_name == "X":
            gate = self.X
        elif gate_name == "Y":
            gate = self.Y
        elif gate_name == "Z":
            gate = self.Z
        elif gate_name == "RX" and angle is not None:
            gate = np.array([
                [np.cos(angle/2), -1j*np.sin(angle/2)],
                [-1j*np.sin(angle/2), np.cos(angle/2)]
            ], dtype=complex)
        elif gate_name == "RY" and angle is not None:
            gate = np.array([
                [np.cos(angle/2), -np.sin(angle/2)],
                [np.sin(angle/2), np.cos(angle/2)]
            ], dtype=complex)
        elif gate_name == "RZ" and angle is not None:
            gate = np.array([
                [np.exp(-1j*angle/2), 0],
                [0, np.exp(1j*angle/2)]
            ], dtype=complex)
        else:
            gate = self.I

        return self._apply_gate_to_state(state, n_qubits, gate, target, control)

    # Legacy stubs — raise immediately so OOM kron is never hit
    def _tensor_gate(self, gate, target, n_qubits):
        raise RuntimeError(
            "_tensor_gate() removed (was OOM kron builder). "
            "Use _apply_gate_to_state() via tensor MSB accelerator.")

    def _controlled_gate(self, gate, control, target, n_qubits):
        raise RuntimeError(
            "_controlled_gate() removed (was OOM full-matrix builder). "
            "Use _apply_gate_to_state() with control= via tensor MSB accelerator.")
    
    def _measure(self, data: Dict) -> Dict[str, Any]:
        """Simulate quantum measurement."""
        state = np.array(data.get("state"), dtype=complex)
        shots = min(data.get("shots", 1000), 10000)
        
        probabilities = np.abs(state) ** 2
        probabilities /= probabilities.sum()  # Normalize
        
        # Sample measurements
        outcomes = np.random.choice(len(state), size=shots, p=probabilities)
        counts = {}
        for outcome in outcomes:
            key = format(outcome, f'0{int(np.log2(len(state)))}b')
            counts[key] = counts.get(key, 0) + 1
        
        return {
            "counts": counts,
            "shots": shots,
            "probabilities": probabilities.tolist(),
            "most_likely": max(counts, key=counts.get)
        }
    
    def _compute_entanglement(self, data: Dict) -> Dict[str, Any]:
        """Compute entanglement entropy."""
        state = np.array(data.get("state"), dtype=complex)
        n_qubits = int(np.log2(len(state)))
        
        if n_qubits < 2:
            return {"entropy": 0.0, "entangled": False}
        
        # Reshape into bipartite system
        n_a = n_qubits // 2
        n_b = n_qubits - n_a
        dim_a = 2 ** n_a
        dim_b = 2 ** n_b
        
        psi_matrix = state.reshape(dim_a, dim_b)
        
        # Compute reduced density matrix
        rho_a = psi_matrix @ psi_matrix.conj().T
        
        # Compute von Neumann entropy
        eigenvalues = np.linalg.eigvalsh(rho_a)
        eigenvalues = eigenvalues[eigenvalues > 1e-12]
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
        
        return {
            "entropy": float(entropy),
            "max_entropy": float(n_a),  # log2(dim_a)
            "entangled": bool(entropy > 0.01),
            "purity": float(np.trace(rho_a @ rho_a).real)
        }
    
    def _bloch_coordinates(self, data: Dict) -> Dict[str, Any]:
        """Compute Bloch sphere coordinates."""
        state = np.array(data.get("state"), dtype=complex)
        
        if len(state) != 2:
            raise ValueError("Bloch sphere requires 2D state (single qubit)")
        
        state = state / np.linalg.norm(state)
        alpha, beta = state[0], state[1]
        
        # Compute Bloch vector
        x = 2 * (alpha.conj() * beta).real
        y = 2 * (alpha.conj() * beta).imag
        z = np.abs(alpha)**2 - np.abs(beta)**2
        
        # Compute angles
        theta = 2 * np.arccos(np.clip(np.abs(alpha), 0, 1))
        phi = np.angle(beta) - np.angle(alpha) if np.abs(beta) > 1e-10 else 0
        
        return {
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "theta": float(theta),
            "phi": float(phi),
            "purity": float(x**2 + y**2 + z**2)
        }


# ============================================================================
# COMPUTE SWARM - Orchestrator
# ============================================================================

class ComputeSwarm:
    """
    Multi-agent compute orchestrator.
    
    Coordinates PhysicsAgent, MathAgent, and QuantumSimAgent
    to perform real calculations for FRANKENSTEIN.
    """
    
    def __init__(self):
        # Lazy-load agents on first access to save memory at startup
        self._agents_cache = {}
        self._task_history: List[ComputeResult] = []
        logger.info("ComputeSwarm initialized with lazy agent loading (optimized)")

    @property
    def physics(self):
        """Lazy-load PhysicsAgent on first access"""
        if 'physics' not in self._agents_cache:
            logger.info("Loading PhysicsAgent on-demand...")
            self._agents_cache['physics'] = PhysicsAgent()
        return self._agents_cache['physics']

    @property
    def math(self):
        """Lazy-load MathAgent on first access"""
        if 'math' not in self._agents_cache:
            logger.info("Loading MathAgent on-demand...")
            self._agents_cache['math'] = MathAgent()
        return self._agents_cache['math']

    @property
    def quantum(self):
        """Lazy-load QuantumSimAgent on first access"""
        if 'quantum' not in self._agents_cache:
            logger.info("Loading QuantumSimAgent on-demand...")
            self._agents_cache['quantum'] = QuantumSimAgent()
        return self._agents_cache['quantum']

    @property
    def _agents(self):
        """Backward compatibility: return dict of loaded agents"""
        return {
            "physics": self.physics,   # Will lazy-load if accessed
            "math": self.math,         # Will lazy-load if accessed
            "quantum": self.quantum    # Will lazy-load if accessed
        }

    # ======================================================================
    # PRIORITY INTEGRATION BRIDGES
    # Connects Physics / Math / Relativistic engines to circuit operations
    # ======================================================================

    # ------------------------------------------------------------------
    # Priority 3 — Hamiltonian from Physics
    # ------------------------------------------------------------------

    def hamiltonian_from_physics(self, physics_type: str,
                                 params: Dict[str, Any],
                                 n_qubits: int) -> np.ndarray:
        """
        Translate PhysicsCompute parameters into a qubit-space Hamiltonian.

        This is the bridge between PhysicsCompute (classical/relativistic
        physics engine) and QuantumCompute.evolve() / .vqe().

        Supported physics_type values:
            'harmonic'  — quantum harmonic oscillator: H = ℏω(a†a + ½)
                          params: {'m': mass, 'k': spring_const}
                          or directly {'omega': angular_frequency}
            'coulomb'   — hydrogen-like atom: E_n = -Z²Ry/n²
                          params: {'Z': nuclear_charge}
            'ising'     — transverse-field Ising model: H = -J Σ ZZ - h Σ X
                          params: {'J': coupling, 'h': transverse_field}
            'free'      — free particle momentum eigenstates (kinetic only)
                          params: {'mass': m}

        Integration flow:
            PhysicsCompute.harmonic_oscillator(m, k, x0, v0) → omega = √(k/m)
                ↓
            ComputeSwarm.hamiltonian_from_physics('harmonic', {'m': m, 'k': k}, n)
                ↓
            ComputeSwarm.run_vqe(H, n_qubits)  →  ground state energy

        Args:
            physics_type: one of 'harmonic', 'coulomb', 'ising', 'free'
            params:       physical parameters (see above)
            n_qubits:     number of qubits / Hilbert space dimension = 2^n

        Returns:
            np.ndarray: (2^n, 2^n) Hamiltonian matrix suitable for
                        QuantumCompute.evolve() or .vqe()
        """
        from synthesis.compute.quantum_compute import get_quantum_compute
        qc = get_quantum_compute()
        qc.initialize(n_qubits, "zero")

        if physics_type == 'harmonic':
            omega = params.get('omega')
            if omega is None:
                m = params.get('m', 1.0)
                k = params.get('k', 1.0)
                omega = float(np.sqrt(k / m))
            m = params.get('m', 1.0)
            return qc.hamiltonian_from_harmonic_oscillator(m, omega)

        elif physics_type == 'coulomb':
            Z = params.get('Z', 1.0)
            epsilon = params.get('epsilon', 0.1)
            return qc.hamiltonian_from_coulomb(Z=Z, epsilon=epsilon)

        elif physics_type == 'ising':
            dim = 2 ** n_qubits
            J = params.get('J', 1.0)
            h = params.get('h', 0.5)
            H = np.zeros((dim, dim), dtype=complex)
            sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
            sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
            I2 = np.eye(2, dtype=complex)

            # ZZ coupling terms
            for q in range(n_qubits - 1):
                # Build I⊗...⊗Z⊗Z⊗...⊗I (qubits q and q+1)
                ops = [I2] * n_qubits
                ops[q] = sigma_z
                ops[q + 1] = sigma_z
                M = ops[0]
                for op in ops[1:]:
                    M = np.kron(M, op)
                H -= J * M

            # Transverse X field
            for q in range(n_qubits):
                ops = [I2] * n_qubits
                ops[q] = sigma_x
                M = ops[0]
                for op in ops[1:]:
                    M = np.kron(M, op)
                H -= h * M

            return H

        elif physics_type == 'free':
            m = params.get('mass', 1.0)
            dim = 2 ** n_qubits
            # Kinetic energy in momentum basis: T_k = (ℏk)²/2m
            # Using discrete momentum levels k = 2πn/L, L=1, ℏ=1
            energies = np.array(
                [(2 * np.pi * (i - dim // 2)) ** 2 / (2 * m)
                 for i in range(dim)])
            return np.diag(energies).astype(complex)

        else:
            raise ValueError(
                f"Unknown physics_type '{physics_type}'. "
                "Choose: 'harmonic', 'coulomb', 'ising', 'free'")

    # ------------------------------------------------------------------
    # Priority 1 — VQE closed loop
    # ------------------------------------------------------------------

    def run_vqe(self, hamiltonian: np.ndarray, n_qubits: int,
                n_layers: int = 2, max_iterations: int = 200,
                tol: float = 1e-6) -> Dict[str, Any]:
        """
        Run Variational Quantum Eigensolver via QuantumCompute.vqe().

        Combines:
            - QuantumCircuitLibrary.variational_ansatz_ry_cnot() ansatz
            - QuantumCompute.expectation(H) energy evaluation
            - SciPy COBYLA or NumPy finite-diff optimization
            - Hamiltonian built by hamiltonian_from_physics()

        Example — ground state of H₂ molecule (simplified Ising encoding):
            H = swarm.hamiltonian_from_physics('ising', {'J': 1.0, 'h': 0.5}, 4)
            result = swarm.run_vqe(H, n_qubits=4, n_layers=3)
            print(result['ground_state_energy'])

        Args:
            hamiltonian:    (2^n × 2^n) Hermitian operator
            n_qubits:       number of qubits
            n_layers:       VQE ansatz depth
            max_iterations: optimizer budget
            tol:            convergence tolerance

        Returns:
            dict from QuantumCompute.vqe() with:
                'ground_state_energy', 'optimal_params', 'final_state',
                'energy_history', 'converged', 'n_iterations', 'backend'
        """
        from synthesis.compute.quantum_compute import get_quantum_compute
        qc = get_quantum_compute()
        qc.initialize(n_qubits, "zero")
        return qc.vqe(hamiltonian, n_layers=n_layers,
                      max_iterations=max_iterations, tol=tol)

    def run_vqe_from_physics(self, physics_type: str, params: Dict[str, Any],
                              n_qubits: int, n_layers: int = 2,
                              max_iterations: int = 200) -> Dict[str, Any]:
        """
        One-call VQE: physics parameters → Hamiltonian → ground state.

        Chains hamiltonian_from_physics() → run_vqe().

        Example:
            result = swarm.run_vqe_from_physics(
                'harmonic', {'m': 1.0, 'k': 4.0}, n_qubits=4)
            # Returns ground state energy of quantum harmonic oscillator
            # at ω = √(k/m) = 2.0, E_ground ≈ ω/2 = 1.0
        """
        H = self.hamiltonian_from_physics(physics_type, params, n_qubits)
        return self.run_vqe(H, n_qubits, n_layers=n_layers,
                            max_iterations=max_iterations)

    # ------------------------------------------------------------------
    # Priority 2 — Statevector → Density matrix → Decoherence bridge
    # ------------------------------------------------------------------

    def apply_circuit_decoherence(self, circuit_gates: List[Dict[str, Any]],
                                   n_qubits: int,
                                   t1: float = 1e-4, t2: float = 5e-5,
                                   gate_time: float = 1e-7) -> Dict[str, Any]:
        """
        Run a gate circuit then apply realistic T1/T2 decoherence.

        Bridges QuantumCompute gate circuits and QuantumState.to_density_matrix()
        for NISQ noise model simulation.

        Args:
            circuit_gates: list of gate specs, e.g.
                [{'gate': 'H', 'target': 0},
                 {'gate': 'X', 'target': 1, 'control': 0},
                 {'gate': 'RY', 'target': 2, 'angle': 1.57}]
            n_qubits:   number of qubits
            t1:         amplitude damping time (T1 relaxation)
            t2:         dephasing time (T2 coherence)
            gate_time:  effective gate duration

        Returns:
            dict with:
                'state_before': QuantumState (ideal, no noise)
                'state_after':  QuantumState (with decoherence applied)
                'density_matrix': np.ndarray (rho after noise)
                'fidelity': float  (|⟨ideal|noisy⟩|²)
                'gate_history': List[str]
        """
        from synthesis.compute.quantum_compute import get_quantum_compute
        qc = get_quantum_compute()
        qc.initialize(n_qubits, "zero")

        sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        hadamard = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
        I2 = np.eye(2, dtype=complex)

        gate_map = {
            'H': hadamard, 'X': sigma_x, 'Y': sigma_y, 'Z': sigma_z, 'I': I2
        }

        for spec in circuit_gates:
            gname = spec.get('gate', 'I')
            target = spec.get('target', 0)
            control = spec.get('control', None)
            angle = spec.get('angle', None)

            if gname in gate_map:
                gate_mat = gate_map[gname]
            elif gname == 'RX' and angle is not None:
                c, s = np.cos(angle/2), np.sin(angle/2)
                gate_mat = np.array([[c, -1j*s], [-1j*s, c]], dtype=complex)
            elif gname == 'RY' and angle is not None:
                c, s = np.cos(angle/2), np.sin(angle/2)
                gate_mat = np.array([[c, -s], [s, c]], dtype=complex)
            elif gname == 'RZ' and angle is not None:
                gate_mat = np.array([[np.exp(-1j*angle/2), 0],
                                     [0, np.exp(1j*angle/2)]], dtype=complex)
            else:
                gate_mat = I2

            qc.apply_gate(gate_mat, target, control)

        ideal_state = qc.get_state()
        ideal_amplitudes = ideal_state.amplitudes.copy()

        # Apply decoherence
        noisy_state = qc.apply_decoherence(t1, t2, gate_time)
        density_matrix = noisy_state.to_density_matrix()

        # Fidelity: |⟨ideal|noisy⟩|²
        fidelity = float(abs(np.conj(ideal_amplitudes) @ noisy_state.amplitudes) ** 2)

        return {
            'state_before':   ideal_state,
            'state_after':    noisy_state,
            'density_matrix': density_matrix,
            'fidelity':       fidelity,
            'gate_history':   qc.get_history(),
        }

    # ------------------------------------------------------------------
    # Priority 4 — Lorentz-boosted gate circuit
    # ------------------------------------------------------------------

    def apply_lorentz_circuit(self, rotation_gates: List[Dict[str, Any]],
                               n_qubits: int,
                               velocity: float = 0.0) -> Dict[str, Any]:
        """
        Apply a rotation circuit with Lorentz-boosted gate angles.

        Models how relativistic motion (satellite qubit platforms, high-velocity
        ion traps, or theoretical relativistic QC architectures) modifies gate
        fidelity via time dilation of control pulses.

        Physics:
            θ_boosted = γ · θ_lab,  γ = 1/√(1 - v²/c²)

        Args:
            rotation_gates: list of rotation specs, e.g.
                [{'axis': 'y', 'angle': 1.57, 'target': 0},
                 {'axis': 'x', 'angle': 0.78, 'target': 1}]
            n_qubits:  number of qubits
            velocity:  v/c (0.0 = no boost, 0.9 = 0.9c)

        Returns:
            dict with:
                'lab_angles':    List[float]  (original angles)
                'boosted_angles': List[float] (γ·θ angles applied)
                'gamma':         float        (Lorentz factor)
                'final_state':   QuantumState
                'gate_history':  List[str]
        """
        if abs(velocity) >= 1.0:
            raise ValueError("velocity must be |v/c| < 1")

        gamma = 1.0 / np.sqrt(1.0 - velocity ** 2) if abs(velocity) > 0 else 1.0

        from synthesis.compute.quantum_compute import get_quantum_compute
        qc = get_quantum_compute()
        qc.initialize(n_qubits, "zero")

        lab_angles: List[float] = []
        boosted_angles: List[float] = []

        for spec in rotation_gates:
            axis   = spec.get('axis', 'y')
            angle  = float(spec.get('angle', 0.0))
            target = spec.get('target', 0)

            lab_angles.append(angle)
            if abs(velocity) > 1e-6:
                qc.lorentz_boosted_rotation(axis, angle, target, velocity)
                boosted_angles.append(gamma * angle)
            else:
                qc.rotation(axis, angle, target)
                boosted_angles.append(angle)

        return {
            'lab_angles':     lab_angles,
            'boosted_angles': boosted_angles,
            'gamma':          gamma,
            'final_state':    qc.get_state(),
            'gate_history':   qc.get_history(),
        }

    # ------------------------------------------------------------------
    # Relativistic Quantum Simulation convenience wrapper
    # ------------------------------------------------------------------

    def run_relativistic_simulation(self, potential: str = 'harmonic',
                                     velocity: float = 0.0,
                                     n_points: int = 256,
                                     t_max: float = 10.0) -> Dict[str, Any]:
        """
        Run a full Schrödinger + Lorentz simulation via RelativisticQuantumEngine.

        Bridges synthesis/relativistic_quantum.py into the swarm API so the
        same workflow that builds gate circuits can also run PDE-based quantum
        dynamics (split-step Fourier, arbitrary potentials).

        Available potentials:
            'free'        — free particle Gaussian spreading
            'harmonic'    — quantum harmonic oscillator (coherent state)
            'square_well' — particle in a square well
            'double_well' — double-well tunneling
            'coulomb'     — Coulomb/hydrogen-like potential
            'tunneling'   — custom barrier tunneling demo

        Args:
            potential: one of the above
            velocity:  Lorentz boost v/c (0.0 = no boost)
            n_points:  spatial grid resolution (max 512 on Tier 1)
            t_max:     simulation time

        Returns:
            dict from RelativisticQuantumEngine.get_visualization_data()
            plus 'summary' and 'engine' handle for further queries
        """
        from synthesis.relativistic_quantum import create_schrodinger_lorentz_simulation

        engine = create_schrodinger_lorentz_simulation(
            velocity=velocity,
            potential=potential,
            n_points=n_points,
            t_max=t_max,
        )

        if potential == 'harmonic':
            result = engine.simulate_harmonic_oscillator()
        elif potential == 'tunneling':
            result = engine.simulate_tunneling()
        elif abs(velocity) > 0.001:
            result = engine.simulate_relativistic_comparison(velocity=velocity)
        else:
            result = engine.simulate_gaussian_spreading()

        vis_data = engine.get_visualization_data(result)
        vis_data['engine'] = engine
        vis_data['success'] = result.success
        vis_data['warnings'] = result.warnings
        vis_data['computation_time'] = result.computation_time

        return vis_data
