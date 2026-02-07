"""
FRANKENSTEIN 1.0 - Quantum Compute Module
Phase 2 Step 3: Real Quantum Mechanics Calculations

Provides actual quantum mechanics computations:
- Wave function evolution
- Operator expectation values
- Quantum gates and circuits
- Measurement simulations
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Pauli matrices (fundamental quantum operators)
SIGMA_X = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_Z = np.array([[1, 0], [0, -1]], dtype=complex)
IDENTITY = np.eye(2, dtype=complex)

# Standard quantum gates
HADAMARD = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
PHASE_S = np.array([[1, 0], [0, 1j]], dtype=complex)
PHASE_T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
CNOT = np.array([[1,0,0,0], [0,1,0,0], [0,0,0,1], [0,0,1,0]], dtype=complex)


@dataclass
class QuantumState:
    """Quantum state representation"""
    amplitudes: np.ndarray
    n_qubits: int
    
    @property
    def probabilities(self) -> np.ndarray:
        return np.abs(self.amplitudes) ** 2
    
    @property
    def norm(self) -> float:
        return np.linalg.norm(self.amplitudes)
    
    def normalize(self) -> 'QuantumState':
        return QuantumState(self.amplitudes / self.norm, self.n_qubits)
    
    def to_bloch(self) -> Tuple[float, float, float]:
        """Convert to Bloch sphere coordinates (for single qubit)"""
        if self.n_qubits != 1:
            raise ValueError("Bloch representation only for single qubit")
        a, b = self.amplitudes[0], self.amplitudes[1]
        x = 2 * np.real(np.conj(a) * b)
        y = 2 * np.imag(np.conj(a) * b)
        z = np.abs(a)**2 - np.abs(b)**2
        return (float(x), float(y), float(z))


class QuantumCompute:
    """
    Real quantum mechanics computation engine.
    
    Performs actual calculations, not just visualizations:
    - Time evolution via Schrödinger equation
    - Quantum gate operations
    - Measurement probability calculations
    - Expectation values
    """
    
    MAX_QUBITS = 16  # Tier 1 hardware limit
    
    def __init__(self):
        self._state: Optional[QuantumState] = None
        self._gate_history: List[str] = []
        self._measurement_results: List[Dict] = []
    
    def initialize(self, n_qubits: int = 1, state: str = "zero") -> QuantumState:
        """Initialize quantum register"""
        if n_qubits > self.MAX_QUBITS:
            raise ValueError(f"Max qubits: {self.MAX_QUBITS}")
        
        dim = 2 ** n_qubits
        amplitudes = np.zeros(dim, dtype=complex)
        
        if state == "zero":
            amplitudes[0] = 1.0
        elif state == "one":
            amplitudes[-1] = 1.0
        elif state == "plus":
            amplitudes[:] = 1.0 / np.sqrt(dim)
        elif state == "minus":
            amplitudes[::2] = 1.0 / np.sqrt(dim // 2)
            amplitudes[1::2] = -1.0 / np.sqrt(dim // 2)
        else:
            amplitudes[0] = 1.0
        
        self._state = QuantumState(amplitudes, n_qubits)
        self._gate_history = []
        return self._state
    
    def apply_gate(self, gate: np.ndarray, target: int, control: Optional[int] = None) -> QuantumState:
        """Apply quantum gate to target qubit"""
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        
        n = self._state.n_qubits
        dim = 2 ** n
        
        if control is not None:
            # Controlled gate
            full_gate = self._build_controlled_gate(gate, control, target, n)
        else:
            # Single qubit gate
            full_gate = self._build_single_gate(gate, target, n)
        
        new_amplitudes = full_gate @ self._state.amplitudes
        self._state = QuantumState(new_amplitudes, n).normalize()
        self._gate_history.append(f"Gate on q{target}" + (f" (ctrl q{control})" if control else ""))
        return self._state

    def _build_single_gate(self, gate: np.ndarray, target: int, n_qubits: int) -> np.ndarray:
        """Build full-system gate matrix for single qubit operation"""
        result = np.array([[1]], dtype=complex)
        for i in range(n_qubits):
            if i == target:
                result = np.kron(result, gate)
            else:
                result = np.kron(result, IDENTITY)
        return result
    
    def _build_controlled_gate(self, gate: np.ndarray, control: int, target: int, 
                                n_qubits: int) -> np.ndarray:
        """Build controlled gate matrix"""
        dim = 2 ** n_qubits
        full_gate = np.eye(dim, dtype=complex)
        
        for i in range(dim):
            # Check if control qubit is |1⟩
            if (i >> (n_qubits - 1 - control)) & 1:
                # Apply gate to target
                for j in range(dim):
                    if (i >> (n_qubits - 1 - target)) & 1 != (j >> (n_qubits - 1 - target)) & 1:
                        # Target bit differs
                        if bin(i ^ (1 << (n_qubits - 1 - target))).count('1') == bin(j).count('1'):
                            full_gate[i, j] = gate[1, 0] if (i >> (n_qubits - 1 - target)) & 1 else gate[0, 1]
                            full_gate[i, i] = gate[1, 1] if (i >> (n_qubits - 1 - target)) & 1 else gate[0, 0]
        return full_gate
    
    def hadamard(self, target: int) -> QuantumState:
        """Apply Hadamard gate"""
        return self.apply_gate(HADAMARD, target)
    
    def pauli_x(self, target: int) -> QuantumState:
        """Apply Pauli-X (NOT) gate"""
        return self.apply_gate(SIGMA_X, target)
    
    def pauli_y(self, target: int) -> QuantumState:
        """Apply Pauli-Y gate"""
        return self.apply_gate(SIGMA_Y, target)
    
    def pauli_z(self, target: int) -> QuantumState:
        """Apply Pauli-Z gate"""
        return self.apply_gate(SIGMA_Z, target)
    
    def cnot(self, control: int, target: int) -> QuantumState:
        """Apply CNOT gate"""
        return self.apply_gate(SIGMA_X, target, control)
    
    def rotation(self, axis: str, angle: float, target: int) -> QuantumState:
        """Apply rotation gate around axis"""
        c, s = np.cos(angle / 2), np.sin(angle / 2)
        if axis.lower() == 'x':
            gate = np.array([[c, -1j*s], [-1j*s, c]], dtype=complex)
        elif axis.lower() == 'y':
            gate = np.array([[c, -s], [s, c]], dtype=complex)
        elif axis.lower() == 'z':
            gate = np.array([[np.exp(-1j*angle/2), 0], [0, np.exp(1j*angle/2)]], dtype=complex)
        else:
            raise ValueError(f"Unknown axis: {axis}")
        return self.apply_gate(gate, target)

    def measure(self, shots: int = 1024) -> Dict[str, Any]:
        """Perform measurement simulation"""
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        
        probs = self._state.probabilities
        n = self._state.n_qubits
        
        # Sample from probability distribution
        outcomes = np.random.choice(len(probs), size=shots, p=probs)
        
        # Count outcomes
        counts = {}
        for outcome in outcomes:
            bitstring = format(outcome, f'0{n}b')
            counts[bitstring] = counts.get(bitstring, 0) + 1
        
        # Sort by count
        counts = dict(sorted(counts.items(), key=lambda x: -x[1]))
        
        result = {
            "counts": counts,
            "shots": shots,
            "probabilities": {format(i, f'0{n}b'): float(p) for i, p in enumerate(probs) if p > 1e-10},
            "most_likely": max(counts.keys(), key=lambda k: counts[k]),
        }
        self._measurement_results.append(result)
        return result
    
    def expectation(self, operator: np.ndarray) -> float:
        """Compute expectation value ⟨ψ|O|ψ⟩"""
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        return float(np.real(np.conj(self._state.amplitudes) @ operator @ self._state.amplitudes))
    
    def evolve(self, hamiltonian: np.ndarray, time: float, steps: int = 100) -> List[QuantumState]:
        """Time evolution under Hamiltonian: e^(-iHt/ℏ)|ψ⟩"""
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        
        dt = time / steps
        states = [self._state]
        psi = self._state.amplitudes.copy()
        
        # Compute evolution operator
        eigenvalues, eigenvectors = np.linalg.eig(hamiltonian)
        
        for _ in range(steps):
            U = eigenvectors @ np.diag(np.exp(-1j * eigenvalues * dt)) @ np.linalg.inv(eigenvectors)
            psi = U @ psi
            psi = psi / np.linalg.norm(psi)
            states.append(QuantumState(psi.copy(), self._state.n_qubits))
        
        self._state = states[-1]
        return states
    
    def create_bell_state(self) -> QuantumState:
        """Create Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2"""
        self.initialize(2, "zero")
        self.hadamard(0)
        self.cnot(0, 1)
        return self._state
    
    def create_ghz_state(self, n_qubits: int = 3) -> QuantumState:
        """Create GHZ state (|00...0⟩ + |11...1⟩)/√2"""
        self.initialize(n_qubits, "zero")
        self.hadamard(0)
        for i in range(1, n_qubits):
            self.cnot(0, i)
        return self._state
    
    def get_state(self) -> Optional[QuantumState]:
        return self._state
    
    def get_history(self) -> List[str]:
        return self._gate_history.copy()


# Singleton
_quantum_compute: Optional[QuantumCompute] = None

def get_quantum_compute() -> QuantumCompute:
    global _quantum_compute
    if _quantum_compute is None:
        _quantum_compute = QuantumCompute()
    return _quantum_compute
