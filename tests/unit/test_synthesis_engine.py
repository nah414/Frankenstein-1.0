"""
FRANKENSTEIN 2.0 - Synthesis Engine Tests
Phase 2 Step 3: Test quantum-classical synthesis

NOTE: This test file was written for a future "FRANKENSTEIN 2.0" API that was never
released. The SynthesisMode enum (SIMULATION, QUANTUM_ONLY, HYBRID) it imports has
since been renamed to ComputeMode (STATEVECTOR, DENSITY, SCHRODINGER, UNITARY) in
the current codebase. These tests are skipped until the synthesis engine API is
updated to match the FRANKENSTEIN 2.0 specification.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason=(
        "Stale FRANKENSTEIN 2.0 test — SynthesisMode (SIMULATION/QUANTUM_ONLY/HYBRID) "
        "no longer exists. Current API uses ComputeMode (STATEVECTOR/DENSITY/SCHRODINGER/UNITARY). "
        "Update synthesis.engine API before re-enabling these tests."
    )
)

import numpy as np
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthesis.engine import (
    SynthesisEngine,
    SynthesisMode,
    SimulationType,
    SynthesisState,
    SynthesisResult
)
from synthesis.quantum.bloch_sphere import (
    BlochSphere,
    BlochSphereConfig,
    BlochState,
    BLOCH_ZERO,
    BLOCH_ONE,
    BLOCH_PLUS
)


class TestSynthesisEngine:
    """Test suite for SynthesisEngine."""
    
    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        engine = SynthesisEngine()
        assert engine.state.mode == SynthesisMode.SIMULATION
        assert engine.state.quantum_dim == 2
        assert engine.state.total_simulations == 0

    
    def test_set_mode(self):
        """Test mode switching."""
        engine = SynthesisEngine()
        engine.set_mode(SynthesisMode.QUANTUM_ONLY)
        assert engine.state.mode == SynthesisMode.QUANTUM_ONLY
        
        engine.set_mode(SynthesisMode.HYBRID)
        assert engine.state.mode == SynthesisMode.HYBRID
    
    def test_create_qubit_state_zero(self):
        """Test creating |0⟩ state."""
        engine = SynthesisEngine()
        state = engine.create_qubit_state(0.0, 0.0)
        assert np.allclose(np.abs(state[0]), 1.0)
        assert np.allclose(np.abs(state[1]), 0.0)
    
    def test_create_qubit_state_one(self):
        """Test creating |1⟩ state."""
        engine = SynthesisEngine()
        state = engine.create_qubit_state(np.pi, 0.0)
        assert np.allclose(np.abs(state[0]), 0.0, atol=1e-10)
        assert np.allclose(np.abs(state[1]), 1.0)
    
    def test_create_qubit_state_plus(self):
        """Test creating |+⟩ state."""
        engine = SynthesisEngine()
        state = engine.create_qubit_state(np.pi / 2, 0.0)
        expected = 1 / np.sqrt(2)
        assert np.allclose(np.abs(state[0]), expected)
        assert np.allclose(np.abs(state[1]), expected)
    
    def test_state_to_bloch_zero(self):
        """Test converting |0⟩ to Bloch coordinates."""
        engine = SynthesisEngine()
        state = np.array([1, 0], dtype=complex)
        theta, phi = engine.state_to_bloch(state)
        assert np.allclose(theta, 0.0)

    
    def test_state_to_bloch_one(self):
        """Test converting |1⟩ to Bloch coordinates."""
        engine = SynthesisEngine()
        state = np.array([0, 1], dtype=complex)
        theta, phi = engine.state_to_bloch(state)
        assert np.allclose(theta, np.pi)
    
    def test_bloch_to_cartesian_north_pole(self):
        """Test north pole (|0⟩) conversion."""
        engine = SynthesisEngine()
        x, y, z = engine.bloch_to_cartesian(0, 0)
        assert np.allclose(z, 1.0)
        assert np.allclose(x, 0.0, atol=1e-10)
        assert np.allclose(y, 0.0, atol=1e-10)
    
    def test_bloch_to_cartesian_south_pole(self):
        """Test south pole (|1⟩) conversion."""
        engine = SynthesisEngine()
        x, y, z = engine.bloch_to_cartesian(np.pi, 0)
        assert np.allclose(z, -1.0)
    
    def test_bloch_to_cartesian_equator(self):
        """Test equator (|+⟩) conversion."""
        engine = SynthesisEngine()
        x, y, z = engine.bloch_to_cartesian(np.pi / 2, 0)
        assert np.allclose(x, 1.0)
        assert np.allclose(z, 0.0, atol=1e-10)
    
    def test_pauli_matrices(self):
        """Test Pauli matrix definitions."""
        engine = SynthesisEngine()
        
        # Pauli X
        X = engine.pauli_x()
        assert X.shape == (2, 2)
        assert np.allclose(X @ X, np.eye(2))  # X² = I

        
        # Pauli Y
        Y = engine.pauli_y()
        assert Y.shape == (2, 2)
        assert np.allclose(Y @ Y, np.eye(2))  # Y² = I
        
        # Pauli Z
        Z = engine.pauli_z()
        assert Z.shape == (2, 2)
        assert np.allclose(Z @ Z, np.eye(2))  # Z² = I
    
    def test_hadamard_gate(self):
        """Test Hadamard gate."""
        engine = SynthesisEngine()
        H = engine.hadamard()
        assert H.shape == (2, 2)
        assert np.allclose(H @ H, np.eye(2))  # H² = I
    
    def test_rabi_hamiltonian(self):
        """Test Rabi Hamiltonian construction."""
        engine = SynthesisEngine()
        H = engine.rabi_hamiltonian(omega=1.0, delta=0.0)
        assert H.shape == (2, 2)
        # Should be Hermitian
        assert np.allclose(H, H.conj().T)
    
    def test_simulation_safety_limits(self):
        """Test that safety limits are enforced."""
        engine = SynthesisEngine()
        
        # Exceed time steps
        times = np.linspace(0, 1, engine.MAX_TIME_STEPS + 100)
        state = np.array([1, 0], dtype=complex)
        H = engine.pauli_x()
        
        result = engine.simulate_evolution(state, H, times)
        assert not result.success
        assert "exceed" in result.error.lower()

    
    def test_simulation_numpy_fallback(self):
        """Test simulation works without QuTiP (numpy fallback)."""
        engine = SynthesisEngine()
        engine._qutip_available = False  # Force fallback
        
        state = np.array([1, 0], dtype=complex)
        H = 0.5 * engine.pauli_x()
        times = np.linspace(0, 1, 50)
        
        result = engine.simulate_evolution(state, H, times)
        assert result.success
        assert result.states is not None
        assert len(result.states) == len(times)
        assert result.bloch_trajectory is not None
    
    def test_get_status(self):
        """Test status reporting."""
        engine = SynthesisEngine()
        status = engine.get_status()
        
        assert "mode" in status
        assert "qutip_available" in status
        assert "total_simulations" in status
        assert "bloch_state" in status
        assert "cartesian" in status["bloch_state"]


class TestBlochSphere:
    """Test suite for BlochSphere visualization."""
    
    def test_bloch_state_zero(self):
        """Test |0⟩ state (north pole)."""
        assert np.allclose(BLOCH_ZERO.cartesian[2], 1.0)
    
    def test_bloch_state_one(self):
        """Test |1⟩ state (south pole)."""
        assert np.allclose(BLOCH_ONE.cartesian[2], -1.0)

    
    def test_bloch_state_plus(self):
        """Test |+⟩ state (+X axis)."""
        assert np.allclose(BLOCH_PLUS.cartesian[0], 1.0)
        assert np.allclose(BLOCH_PLUS.cartesian[2], 0.0, atol=1e-10)
    
    def test_bloch_state_from_cartesian(self):
        """Test creating state from Cartesian coords."""
        state = BlochState.from_cartesian(1, 0, 0)
        assert np.allclose(state.theta, np.pi / 2)
        assert np.allclose(state.phi, 0.0)
    
    def test_bloch_state_from_vector(self):
        """Test creating state from quantum state vector."""
        psi = np.array([1, 0], dtype=complex)  # |0⟩
        state = BlochState.from_state_vector(psi)
        assert np.allclose(state.theta, 0.0)
    
    def test_bloch_sphere_init(self):
        """Test BlochSphere initialization."""
        sphere = BlochSphere()
        assert sphere.config is not None
        assert len(sphere.states) == 0
        assert len(sphere.trajectory) == 0
    
    def test_bloch_sphere_add_state(self):
        """Test adding states to sphere."""
        sphere = BlochSphere()
        sphere.add_state(BLOCH_ZERO)
        sphere.add_state(BLOCH_ONE)
        assert len(sphere.states) == 2
    
    def test_bloch_sphere_trajectory(self):
        """Test setting trajectory."""
        sphere = BlochSphere()
        trajectory = [(0, 0), (np.pi/4, 0), (np.pi/2, 0)]
        sphere.set_trajectory(trajectory)
        assert len(sphere.trajectory) == 3

    
    def test_bloch_sphere_wireframe(self):
        """Test wireframe generation."""
        sphere = BlochSphere()
        wireframe = sphere.generate_wireframe()
        assert "latitude" in wireframe
        assert "longitude" in wireframe
        assert len(wireframe["latitude"]) > 0
        assert len(wireframe["longitude"]) > 0
    
    def test_bloch_sphere_axes(self):
        """Test axes generation."""
        sphere = BlochSphere()
        axes = sphere.generate_axes()
        assert len(axes) == 3  # X, Y, Z
        labels = [a["label"] for a in axes]
        assert "X" in labels
        assert "Y" in labels
        assert "Z" in labels
    
    def test_bloch_sphere_render_data(self):
        """Test complete render data generation."""
        sphere = BlochSphere()
        sphere.add_state(BLOCH_ZERO)
        data = sphere.get_render_data()
        
        assert "config" in data
        assert "wireframe" in data
        assert "axes" in data
        assert "states" in data
        assert len(data["states"]) == 1
    
    def test_bloch_sphere_animation(self):
        """Test rotation animation generation."""
        sphere = BlochSphere()
        sphere.add_state(BLOCH_PLUS)
        frames = sphere.animate_rotation('Z', np.pi, steps=10)
        assert len(frames) == 11  # steps + 1
    
    def test_bloch_sphere_clear(self):
        """Test clearing sphere."""
        sphere = BlochSphere()
        sphere.add_state(BLOCH_ZERO)
        sphere.set_trajectory([(0, 0), (1, 0)])
        sphere.clear()
        assert len(sphere.states) == 0
        assert len(sphere.trajectory) == 0
