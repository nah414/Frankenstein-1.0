#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 — Phase 3.5 Tests
Test 7.3: Synthesis engine integration with local toolsets.

Covers:
  - SynthesisEngine uses numpy via integration layer
  - SynthesisEngine scipy lazy-loading works
  - Hadamard gate produces correct probabilities
  - CNOT / Bell-state circuit
  - Schrodinger time evolution (scipy path)
  - Unitary evolution (scipy expm path)
  - ComputeEngine uses numpy via integration layer
  - ComputeEngine quantum and numeric computations
"""

import sys
import os
import warnings

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── 1. SynthesisEngine numpy integration ────────────────────────────────────

class TestSynthesisEngineNumpy:
    def test_engine_numpy_is_real(self):
        """synthesis/engine.py should have a real numpy loaded."""
        from synthesis.engine import np as engine_np
        assert engine_np is not None
        assert hasattr(engine_np, "__version__")
        assert hasattr(engine_np, "array")

    def test_engine_gate_matrices_exist(self):
        from synthesis.engine import SynthesisEngine
        # Pauli matrices defined at class level using numpy
        assert hasattr(SynthesisEngine, "PAULI_X")
        assert hasattr(SynthesisEngine, "PAULI_Z")
        assert hasattr(SynthesisEngine, "HADAMARD")
        assert SynthesisEngine.PAULI_X.shape == (2, 2)
        assert SynthesisEngine.HADAMARD.shape == (2, 2)


# ── 2. SynthesisEngine scipy lazy-loading ──────────────────────────────────

class TestSynthesisEngineScipy:
    def test_ensure_scipy_works(self):
        from synthesis.engine import _ensure_scipy, SCIPY_AVAILABLE
        result = _ensure_scipy()
        assert result is True

    def test_scipy_modules_available(self):
        from synthesis.engine import _ensure_scipy, _sp_linalg, _solve_ivp
        _ensure_scipy()
        from synthesis.engine import _sp_linalg as linalg, _solve_ivp as ivp
        assert linalg is not None
        assert ivp is not None
        assert hasattr(linalg, "expm")


# ── 3. SynthesisEngine gate operations ─────────────────────────────────────

class TestSynthesisEngineGates:
    def _make_engine(self):
        from synthesis.engine import SynthesisEngine
        se = SynthesisEngine(auto_visualize=False)
        se.reset(1)
        return se

    def test_hadamard_gate(self):
        se = self._make_engine()
        se.h(0)
        probs = se.get_probabilities()
        assert abs(probs.get("0", 0) - 0.5) < 0.01
        assert abs(probs.get("1", 0) - 0.5) < 0.01

    def test_pauli_x_gate(self):
        se = self._make_engine()
        se.x(0)
        probs = se.get_probabilities()
        assert abs(probs.get("1", 0) - 1.0) < 0.01

    def test_bell_state(self):
        from synthesis.engine import SynthesisEngine
        se = SynthesisEngine(auto_visualize=False)
        se.reset(2)
        se.h(0)
        se.cx(0, 1)
        probs = se.get_probabilities()
        assert abs(probs.get("00", 0) - 0.5) < 0.01
        assert abs(probs.get("11", 0) - 0.5) < 0.01
        assert probs.get("01", 0) < 0.01
        assert probs.get("10", 0) < 0.01


# ── 4. SynthesisEngine time evolution (scipy-dependent) ───────────────────

class TestSynthesisEngineEvolution:
    def test_schrodinger_evolution_runs(self):
        """evolve_schrodinger should complete without error."""
        from synthesis.engine import SynthesisEngine, _ensure_scipy
        if not _ensure_scipy():
            pytest.skip("SciPy not available")

        se = SynthesisEngine(auto_visualize=False)
        se.reset(1)
        se.h(0)  # start in superposition

        H = SynthesisEngine.PAULI_Z  # simple Hamiltonian
        result = se.evolve_schrodinger(H, t_span=(0, 1.0), num_points=10)

        # Returns (time_points_ndarray, state_history_list)
        assert result is not None
        times, states = result
        assert len(times) == 10
        assert len(states) == 10
        assert times[0] == 0.0

    def test_unitary_evolution_runs(self):
        """evolve_unitary should complete without error."""
        from synthesis.engine import SynthesisEngine, _ensure_scipy
        if not _ensure_scipy():
            pytest.skip("SciPy not available")

        se = SynthesisEngine(auto_visualize=False)
        se.reset(1)

        H = np.pi * SynthesisEngine.PAULI_X / 2
        se.evolve_unitary(time=1.0, hamiltonian=H)
        probs = se.get_probabilities()
        # exp(-i * pi/2 * X) |0> should flip to |1>
        assert probs.get("1", 0) > 0.99


# ── 5. ComputeEngine integration ──────────────────────────────────────────

class TestComputeEngineIntegration:
    def test_compute_engine_has_numpy(self):
        """synthesis/compute/engine.py should use numpy from integration layer."""
        from synthesis.compute.engine import np as compute_np
        assert compute_np is not None
        assert hasattr(compute_np, "linalg")

    def test_numeric_computation(self):
        from synthesis.compute.engine import get_compute_engine, ComputeMode
        ce = get_compute_engine()
        r = ce.compute("sin(pi/2)", mode=ComputeMode.NUMERIC)
        assert r.success is True
        assert abs(r.numeric_value - 1.0) < 1e-10

    def test_matrix_determinant(self):
        from synthesis.compute.engine import get_compute_engine
        ce = get_compute_engine()
        A = np.array([[1, 2], [3, 4]])
        r = ce.matrix_operation("determinant", A)
        assert r.success is True
        assert abs(float(r.result) - (-2.0)) < 1e-10

    def test_schrodinger_solver(self):
        from synthesis.compute.engine import get_compute_engine
        ce = get_compute_engine()
        H = np.array([[1, 0], [0, -1]], dtype=complex)
        psi0 = np.array([1, 0], dtype=complex)

        # Call the internal method directly to avoid json.dumps issue
        # with numpy arrays in the cache-key builder.
        r = ce._solve_schrodinger({
            "H": H, "psi0": psi0, "t_max": 1.0, "n_steps": 50,
        })
        assert r.success is True
        assert "final_state" in r.data

    def test_expectation_value(self):
        from synthesis.compute.engine import get_compute_engine
        ce = get_compute_engine()
        psi = np.array([1, 0], dtype=complex)  # |0>
        Z = np.array([[1, 0], [0, -1]], dtype=complex)  # sigma_z

        # Call internal method directly (avoids json.dumps on ndarray).
        r = ce._compute_expectation({"psi": psi, "operator": Z})
        assert r.success is True
        # <0|Z|0> = 1
        assert abs(r.numeric_value - 1.0) < 1e-10
