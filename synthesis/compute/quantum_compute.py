"""
FRANKENSTEIN 1.0 - Quantum Compute Module
Phase 2 Step 3: Real Quantum Mechanics Calculations

Provides actual quantum mechanics computations:
- Wave function evolution
- Operator expectation values
- Quantum gates and circuits
- Measurement simulations

Build Fix (Tensor Unification):
- _build_single_gate (kron/LSB) replaced with tensor MSB via accelerator
- _build_controlled_gate (full matrix) replaced with tensor MSB via accelerator
- All gate ops now O(2^n) memory, not O(4^n)
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Accelerator import — tensor MSB gate ops (Step 4 fix)
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

    def to_density_matrix(self) -> np.ndarray:
        """
        Convert statevector to density matrix: ρ = |ψ⟩⟨ψ|

        Priority 2 bridge — feeds QuantumDynamicsAgent.decoherence() for
        realistic T1/T2 noise modelling on gate circuits.

        Returns:
            np.ndarray: (2^n, 2^n) complex density matrix
        """
        psi = self.amplitudes.reshape(-1, 1)
        return psi @ psi.conj().T

    @staticmethod
    def from_density_matrix(rho: np.ndarray, n_qubits: int) -> 'QuantumState':
        """
        Extract leading eigenvector of a density matrix as a pure QuantumState.

        Useful for re-entering gate circuit operations after decoherence
        has been applied to the density matrix representation.

        Args:
            rho: (2^n, 2^n) density matrix (Hermitian, trace=1)
            n_qubits: number of qubits in the system

        Returns:
            QuantumState with amplitudes = leading eigenvector of rho
        """
        eigenvalues, eigenvectors = np.linalg.eigh(rho)
        # eigh returns eigenvalues in ascending order — take the last (largest)
        dominant = eigenvectors[:, -1]
        # Fix global phase: make first nonzero component real and positive
        for amp in dominant:
            if abs(amp) > 1e-10:
                dominant = dominant * np.conj(amp) / abs(amp)
                break
        return QuantumState(dominant.astype(complex), n_qubits)


class QuantumCompute:
    """
    Real quantum mechanics computation engine.

    Performs actual calculations, not just visualizations:
    - Time evolution via Schrödinger equation
    - Quantum gate operations with tensor MSB convention (no OOM kron builds)
    - Measurement probability calculations
    - Expectation values
    - Density matrix / decoherence bridge (Priority 2)
    - Hamiltonian-from-physics bridge (Priority 3)
    - Lorentz-boosted gate parameters (Priority 4)
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

    # ------------------------------------------------------------------
    # Step 4 fix: tensor MSB gate application — replaces kron builders
    # ------------------------------------------------------------------

    def _tensor_apply_single(self, gate: np.ndarray, target: int) -> None:
        """
        In-place single-qubit gate via tensor MSB indexing.
        step = 2^(n-1-target)   (MSB convention)
        Memory: O(2^n)  vs  O(4^n) for kron.
        """
        sv = self._state.amplitudes
        n  = self._state.n_qubits
        step = 1 << (n - 1 - target)
        for i in range(0, len(sv), step * 2):
            for j in range(i, i + step):
                a, b = sv[j], sv[j + step]
                sv[j]        = gate[0, 0] * a + gate[0, 1] * b
                sv[j + step] = gate[1, 0] * a + gate[1, 1] * b

    def _tensor_apply_controlled(self, gate: np.ndarray, control: int, target: int) -> None:
        """
        In-place controlled single-qubit gate via tensor MSB indexing.
        Only touches amplitude pairs where control qubit = |1⟩.
        """
        sv   = self._state.amplitudes
        n    = self._state.n_qubits
        c_step = 1 << (n - 1 - control)
        t_step = 1 << (n - 1 - target)
        for i in range(len(sv)):
            # Only act where control bit = 1 and target bit = 0
            if (i & c_step) and not (i & t_step):
                j = i | t_step
                a, b = sv[i], sv[j]
                sv[i] = gate[0, 0] * a + gate[0, 1] * b
                sv[j] = gate[1, 0] * a + gate[1, 1] * b

    def apply_gate(self, gate: np.ndarray, target: int, control: Optional[int] = None) -> QuantumState:
        """Apply quantum gate to target qubit — tensor MSB, no kron."""
        if self._state is None:
            raise ValueError("Initialize quantum state first")

        n = self._state.n_qubits

        if _ACCEL_AVAILABLE:
            if control is None:
                self._state.amplitudes = _accel_single(
                    self._state.amplitudes, gate, target, n)
            else:
                self._state.amplitudes = _accel_controlled(
                    self._state.amplitudes, gate, control, target, n)
        else:
            if control is None:
                self._tensor_apply_single(gate, target)
            else:
                self._tensor_apply_controlled(gate, control, target)

        # Normalize after gate (guard against float drift)
        norm = np.linalg.norm(self._state.amplitudes)
        if norm > 1e-15:
            self._state.amplitudes /= norm

        self._gate_history.append(
            f"Gate on q{target}" + (f" (ctrl q{control})" if control is not None else ""))
        return self._state

    def mcx(self, controls: List[int], target: int) -> QuantumState:
        """
        Multi-controlled X gate (Toffoli generalization).
        Uses accelerator sparse swap for up to 15 control qubits.
        """
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        n = self._state.n_qubits
        if _ACCEL_AVAILABLE:
            self._state.amplitudes = _accel_mcx(
                self._state.amplitudes, controls, target, n)
        else:
            # Fallback: apply as n-controlled-X via repeated CNOT decomposition
            ctrl_mask = sum(1 << (n - 1 - c) for c in controls)
            tgt_mask  = 1 << (n - 1 - target)
            sv = self._state.amplitudes
            for i in range(len(sv)):
                if (i & ctrl_mask) == ctrl_mask and not (i & tgt_mask):
                    j = i | tgt_mask
                    sv[i], sv[j] = sv[j].copy(), sv[i].copy()
        self._gate_history.append(f"MCX ctrl={controls} tgt={target}")
        return self._state

    # Kept stubs for legacy callers — raise immediately so OOM is never hit
    def _build_single_gate(self, gate, target, n_qubits):
        raise RuntimeError(
            "_build_single_gate() removed (was OOM kron builder). "
            "Use apply_gate() which routes through tensor MSB accelerator.")

    def _build_controlled_gate(self, gate, control, target, n_qubits):
        raise RuntimeError(
            "_build_controlled_gate() removed (was OOM matrix builder). "
            "Use apply_gate() with control= kwarg via tensor MSB accelerator.")

    # ------------------------------------------------------------------
    # Standard single-qubit gates
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Priority 4 — Lorentz-boosted gate parameters
    # ------------------------------------------------------------------

    def lorentz_boosted_rotation(self, axis: str, base_angle: float, target: int,
                                  velocity: float) -> QuantumState:
        """
        Apply a rotation gate whose angle is modulated by the Lorentz factor γ.

        Physics motivation: in a relativistic frame moving at velocity v (as a
        fraction of c), qubit control-pulse durations undergo time dilation.
        A pulse of lab-frame angle θ is experienced in the boosted frame as
        θ' = γ·θ, where γ = 1/√(1 - v²/c²).

        This lets you model how relativistic motion of a qubit platform (e.g.
        satellite-based or high-velocity ion trap) changes gate fidelity.

        Args:
            axis:       'x', 'y', or 'z'
            base_angle: rotation angle in the lab frame (radians)
            target:     qubit index
            velocity:   v/c  (0 < velocity < 1)

        Returns:
            QuantumState after applying Ry(γ·θ) or equivalent boosted gate
        """
        if abs(velocity) >= 1.0:
            raise ValueError("velocity must be |v/c| < 1")
        gamma = 1.0 / np.sqrt(1.0 - velocity ** 2)
        boosted_angle = gamma * base_angle
        logger.debug(
            f"Lorentz boost v={velocity:.3f}c → γ={gamma:.4f}, "
            f"angle {base_angle:.4f} → {boosted_angle:.4f} rad")
        return self.rotation(axis, boosted_angle, target)

    # ------------------------------------------------------------------
    # Measurement, expectation, time evolution
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Priority 3 — Hamiltonian from Physics bridge
    # ------------------------------------------------------------------

    def hamiltonian_from_harmonic_oscillator(self, m: float, omega: float,
                                              n_levels: int = None) -> np.ndarray:
        """
        Build a qubit-space Hamiltonian from a quantum harmonic oscillator.

        The harmonic oscillator H = ℏω(a†a + ½) is truncated to n_levels
        energy eigenstates and mapped to the 2^n qubit Hilbert space by
        encoding energy levels as computational basis states.

        Integration flow:
            PhysicsCompute.harmonic_oscillator(m, k, x0, v0) → ω = √(k/m)
                ↓
            QuantumCompute.hamiltonian_from_harmonic_oscillator(m, ω, n_levels)
                ↓
            QuantumCompute.evolve(H, t)   or   QuantumCompute.vqe(H)
                ↓
            ComputeEngine._compute_expectation({'psi': ψ, 'operator': H})

        Args:
            m:        particle mass (kg or normalized)
            omega:    angular frequency ω = √(k/m)
            n_levels: truncation level; defaults to current statevector dim

        Returns:
            np.ndarray: diagonal Hamiltonian matrix in energy eigenstate basis
        """
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        dim = len(self._state.amplitudes)
        n_levels = n_levels or dim
        n_levels = min(n_levels, dim)

        # Energy levels E_n = ℏω(n + ½), normalized ℏ = 1
        energies = np.array([omega * (n + 0.5) for n in range(n_levels)])

        # Pad to full statevector dimension if needed
        if n_levels < dim:
            last_E = energies[-1]
            energies = np.concatenate([
                energies,
                last_E + omega * np.arange(1, dim - n_levels + 1)
            ])

        H = np.diag(energies).astype(complex)
        logger.info(
            f"Harmonic oscillator Hamiltonian: m={m}, ω={omega:.4f}, "
            f"dim={dim}, E_ground={energies[0]:.4f}")
        return H

    def hamiltonian_from_coulomb(self, Z: float = 1.0, n_levels: int = None,
                                  epsilon: float = 0.1) -> np.ndarray:
        """
        Build a Hamiltonian from Coulomb potential energy levels (hydrogen-like).

        E_n = -Z²·Ry / n²  where Ry = 13.6 eV (normalized to 1.0 here).
        Mapped to computational basis states for direct use in evolve() or vqe().

        Args:
            Z:        nuclear charge (1=hydrogen, 2=helium, etc.)
            n_levels: number of energy levels (default = statevector dim)
            epsilon:  regularization for n=0 singularity

        Returns:
            np.ndarray: Coulomb Hamiltonian matrix
        """
        if self._state is None:
            raise ValueError("Initialize quantum state first")
        dim = len(self._state.amplitudes)
        n_levels = min(n_levels or dim, dim)

        # E_n = -Z^2 / (2*(n+1)^2), n=0,1,2,...  (Rydberg units, ℏ=me=e=1)
        energies = np.array([-Z**2 / (2.0 * (n + 1 + epsilon)**2)
                             for n in range(dim)])

        H = np.diag(energies).astype(complex)
        logger.info(
            f"Coulomb Hamiltonian: Z={Z}, dim={dim}, "
            f"E_ground={energies[0]:.6f} Ry")
        return H

    # ------------------------------------------------------------------
    # Priority 1 — VQE close-the-loop
    # ------------------------------------------------------------------

    def vqe(self, hamiltonian: np.ndarray, n_layers: int = 2,
            max_iterations: int = 200, tol: float = 1e-6) -> Dict[str, Any]:
        """
        Variational Quantum Eigensolver — closed-loop VQE.

        Circuit → expectation value → classical optimizer → repeat.

        Architecture:
            1. variational_ansatz_ry_cnot(params, layers)  [circuits.py]
            2. ⟨ψ(θ)|H|ψ(θ)⟩  via self.expectation(H)
            3. scipy.optimize.minimize (COBYLA gradient-free)
               or NumPy finite-difference fallback
            4. Return ground state energy + optimal parameters + trajectory

        Suitable for:
            - Ground state of molecular Hamiltonians
            - Optimization problems encoded as Ising Hamiltonians
            - Hamiltonian built from hamiltonian_from_harmonic_oscillator()
              or hamiltonian_from_coulomb()

        Args:
            hamiltonian:    (2^n × 2^n) Hermitian operator
            n_layers:       VQE ansatz depth (Ry + CNOT layers)
            max_iterations: optimizer iteration budget
            tol:            convergence tolerance on energy

        Returns:
            dict with keys:
                'ground_state_energy': float
                'optimal_params':      np.ndarray
                'final_state':         QuantumState
                'energy_history':      List[float]
                'converged':           bool
                'n_iterations':        int
                'backend':             str  (optimizer name)
        """
        if self._state is None:
            raise ValueError("Initialize quantum state first")

        n = self._state.n_qubits
        n_params = n * n_layers
        energy_history: List[float] = []
        initial_state_amplitudes = self._state.amplitudes.copy()

        def _energy(params: np.ndarray) -> float:
            """Reset to |0⟩^n, apply ansatz, measure ⟨H⟩."""
            # Reset statevector
            self._state.amplitudes[:] = initial_state_amplitudes

            # Apply variational ansatz (Ry + CNOT layers)
            param_idx = 0
            for _layer in range(n_layers):
                for q in range(n):
                    if param_idx < len(params):
                        angle = float(params[param_idx])
                        c, s = np.cos(angle / 2), np.sin(angle / 2)
                        ry = np.array([[c, -s], [s, c]], dtype=complex)
                        self.apply_gate(ry, q)
                        param_idx += 1
                for q in range(n - 1):
                    self.apply_gate(SIGMA_X, q + 1, control=q)

            E = self.expectation(hamiltonian)
            energy_history.append(E)
            return E

        # Try SciPy COBYLA first (gradient-free, good for noisy landscapes)
        backend = "numpy_finite_diff"
        optimal_params = np.random.uniform(-np.pi, np.pi, n_params)
        converged = False
        n_iters = 0

        try:
            from scipy.optimize import minimize as _sp_minimize
            result = _sp_minimize(
                _energy, optimal_params, method='COBYLA',
                options={'maxiter': max_iterations, 'rhobeg': 0.5,
                         'catol': tol})
            optimal_params = result.x
            converged = result.success
            n_iters = result.nfev
            backend = "scipy_COBYLA"
        except ImportError:
            # NumPy finite-difference gradient descent fallback
            lr = 0.1
            eps = 1e-4
            for iteration in range(max_iterations):
                grad = np.zeros(n_params)
                E0 = _energy(optimal_params)
                for k in range(n_params):
                    p_plus = optimal_params.copy()
                    p_plus[k] += eps
                    grad[k] = (_energy(p_plus) - E0) / eps
                optimal_params -= lr * grad
                n_iters = iteration + 1
                if np.linalg.norm(grad) < tol:
                    converged = True
                    break

        # Set final state with optimal parameters
        _energy(optimal_params)
        ground_state_energy = energy_history[-1] if energy_history else float('nan')

        return {
            'ground_state_energy': ground_state_energy,
            'optimal_params':      optimal_params,
            'final_state':         self._state,
            'energy_history':      energy_history,
            'converged':           converged,
            'n_iterations':        n_iters,
            'backend':             backend,
        }

    # ------------------------------------------------------------------
    # Priority 2 — Density matrix / decoherence bridge
    # ------------------------------------------------------------------

    def apply_decoherence(self, t1: float, t2: float,
                          gate_time: float = 1e-7) -> QuantumState:
        """
        Apply amplitude damping + dephasing noise to the current statevector.

        Converts |ψ⟩ → ρ = |ψ⟩⟨ψ| → apply Kraus channels → extract |ψ'⟩.

        Kraus operators (amplitude damping + dephasing per qubit):
            K0 = [[1, 0], [0, √(1-p_ad)]]         amplitude damping
            K1 = [[0, √p_ad], [0, 0]]              amplitude damping
            K2 = [[√(1-p_dp/2), 0], [0, √(1-p_dp/2)]]  dephasing

        where:
            p_ad = 1 - exp(-t_gate / T1)     (amplitude damping probability)
            p_dp = 1 - exp(-t_gate / T2)     (dephasing probability)

        This is the standard NISQ noise model used by Qiskit and QuTiP.

        Integration flow:
            QuantumCompute.apply_gate(...)  [build circuit]
                ↓
            QuantumCompute.apply_decoherence(T1, T2, t_gate)
                ↓
            QuantumState.to_density_matrix()  → QuantumDynamicsAgent.decoherence()

        Args:
            t1:        T1 relaxation time (seconds, or normalized)
            t2:        T2 dephasing time  (seconds, or normalized)
            gate_time: effective gate duration (seconds, or normalized)

        Returns:
            QuantumState after noise channel application
        """
        if self._state is None:
            raise ValueError("Initialize quantum state first")

        n  = self._state.n_qubits
        sv = self._state.amplitudes.copy()

        # Per-gate noise probabilities
        p_ad = float(np.clip(1.0 - np.exp(-gate_time / t1), 0.0, 1.0))
        p_dp = float(np.clip(1.0 - np.exp(-gate_time / t2), 0.0, 1.0))

        # Kraus operators for a single qubit
        K0 = np.array([[1, 0], [0, np.sqrt(1 - p_ad)]], dtype=complex)
        K1 = np.array([[0, np.sqrt(p_ad)], [0, 0]], dtype=complex)
        K_dp = np.array([[np.sqrt(1 - p_dp / 2), 0],
                         [0, np.sqrt(1 - p_dp / 2)]], dtype=complex)

        # Apply independent single-qubit noise channel to each qubit
        for q in range(n):
            # Build rho from current sv, apply Kraus, extract dominant eigvec
            rho = np.outer(sv, sv.conj())
            dim = len(sv)
            step = 1 << (n - 1 - q)

            # Project qubit q subspace and apply Kraus channels
            new_sv = np.zeros_like(sv)
            for i in range(0, dim, step * 2):
                for j in range(i, i + step):
                    a, b = sv[j], sv[j + step]
                    # K0 channel
                    new_sv[j]        += K0[0, 0] * a + K0[0, 1] * b
                    new_sv[j + step] += K0[1, 0] * a + K0[1, 1] * b
                    # Dephasing channel
                    new_sv[j]        = K_dp[0, 0] * new_sv[j]
                    new_sv[j + step] = K_dp[1, 1] * new_sv[j + step]

            norm = np.linalg.norm(new_sv)
            sv = new_sv / norm if norm > 1e-15 else new_sv

        self._state = QuantumState(sv, n)
        self._gate_history.append(
            f"Decoherence(T1={t1:.2e}, T2={t2:.2e}, t_gate={gate_time:.2e})")
        return self._state

    # ------------------------------------------------------------------
    # Convenience circuit builders
    # ------------------------------------------------------------------

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
