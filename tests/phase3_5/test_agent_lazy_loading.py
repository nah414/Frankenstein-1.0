#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 — Phase 3.5 Tests
Test 7.2: Agent lazy-loading verification.

Covers:
  - Each agent instantiates with toolset reference = None (lazy)
  - execute() without an operation returns a helpful error
  - execute() with a valid operation triggers _ensure_loaded()
  - Agent registry contains all 5 agents
  - Agents operate correctly with their toolsets (smoke tests)
"""

import sys
import os
import warnings

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base import AgentResult
from agents.builtin.quantum_dynamics_agent import QuantumDynamicsAgent
from agents.builtin.quantum_hardware_agent import QuantumHardwareAgent
from agents.builtin.quantum_crypto_agent import QuantumCryptoAgent
from agents.builtin.numerical_computing_agent import NumericalComputingAgent
from agents.registry import get_registry


# ── 1. Lazy instantiation (toolset is None at __init__) ────────────────────

class TestLazyInstantiation:
    def test_quantum_dynamics_lazy(self):
        agent = QuantumDynamicsAgent()
        assert agent._qutip is None
        assert agent.name == "quantum_dynamics"

    def test_quantum_hardware_lazy(self):
        agent = QuantumHardwareAgent()
        assert agent._qiskit is None
        assert agent.name == "quantum_hardware"

    def test_quantum_crypto_lazy(self):
        agent = QuantumCryptoAgent()
        assert agent._qencrypt is None
        assert agent.name == "quantum_crypto"

    def test_numerical_computing_lazy(self):
        agent = NumericalComputingAgent()
        assert agent._np is None
        assert agent._scipy is None
        assert agent.name == "numerical_computing"


# ── 2. execute() with no operation ─────────────────────────────────────────

class TestNoOperation:
    def test_dynamics_no_op(self):
        r = QuantumDynamicsAgent().execute()
        assert r.success is False
        assert "operation" in r.error.lower()

    def test_hardware_no_op(self):
        r = QuantumHardwareAgent().execute()
        assert r.success is False
        assert "operation" in r.error.lower()

    def test_crypto_no_op(self):
        r = QuantumCryptoAgent().execute()
        assert r.success is False
        assert "operation" in r.error.lower()

    def test_numerical_no_op(self):
        r = NumericalComputingAgent().execute()
        assert r.success is False
        assert "operation" in r.error.lower()


# ── 3. execute() with unknown operation ────────────────────────────────────

class TestUnknownOperation:
    def test_dynamics_unknown(self):
        r = QuantumDynamicsAgent().execute(operation="bogus")
        assert r.success is False
        assert "bogus" in r.error

    def test_hardware_unknown(self):
        r = QuantumHardwareAgent().execute(operation="bogus")
        assert r.success is False

    def test_crypto_unknown(self):
        r = QuantumCryptoAgent().execute(operation="bogus")
        assert r.success is False

    def test_numerical_unknown(self):
        r = NumericalComputingAgent().execute(operation="bogus")
        assert r.success is False


# ── 4. Registry integration ───────────────────────────────────────────────

class TestRegistryIntegration:
    def test_all_agents_registered(self):
        registry = get_registry()
        for name in [
            "compute",
            "quantum_dynamics",
            "quantum_hardware",
            "quantum_crypto",
            "numerical_computing",
        ]:
            assert registry.has_agent(name), f"{name} not registered"

    def test_registry_get_returns_correct_type(self):
        registry = get_registry()
        assert isinstance(registry.get("quantum_dynamics"), QuantumDynamicsAgent)
        assert isinstance(registry.get("quantum_hardware"), QuantumHardwareAgent)
        assert isinstance(registry.get("quantum_crypto"), QuantumCryptoAgent)
        assert isinstance(registry.get("numerical_computing"), NumericalComputingAgent)

    def test_registry_list_agents_has_five(self):
        registry = get_registry()
        agents = registry.list_agents()
        assert len(agents) >= 5
        names = {a["name"] for a in agents}
        assert "quantum_dynamics" in names
        assert "quantum_hardware" in names
        assert "quantum_crypto" in names
        assert "numerical_computing" in names
        assert "compute" in names


# ── 5. Agent smoke tests (real toolset usage) ─────────────────────────────

class TestQuantumDynamicsSmoke:
    """Smoke tests for QuantumDynamicsAgent with real QuTiP calls."""

    def test_sesolve(self):
        agent = QuantumDynamicsAgent()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            agent._ensure_loaded()
        qt = agent._qutip

        H = qt.sigmax()
        psi0 = qt.basis(2, 0)
        tlist = np.linspace(0, 1, 20)

        r = agent.execute(
            operation="sesolve",
            hamiltonian=H,
            psi0=psi0,
            tlist=tlist,
        )
        assert r.success is True
        assert r.data["solver"] == "sesolve"
        assert len(r.data["states"]) == 20

    def test_entropy(self):
        agent = QuantumDynamicsAgent()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            agent._ensure_loaded()
        qt = agent._qutip

        # Pure state -> zero entropy
        psi = qt.basis(2, 0)
        rho = psi * psi.dag()
        r = agent.execute(operation="entropy", state=rho, measure="von_neumann")
        assert r.success is True
        assert abs(r.data["entropy"]) < 1e-10

    def test_missing_params(self):
        agent = QuantumDynamicsAgent()
        r = agent.execute(operation="mesolve")
        assert r.success is False
        assert "requires" in r.error.lower()


class TestQuantumHardwareSmoke:
    """Smoke tests for QuantumHardwareAgent with real Qiskit calls."""

    def test_build_circuit(self):
        agent = QuantumHardwareAgent()
        r = agent.execute(
            operation="build_circuit",
            num_qubits=2,
            gates=[
                {"gate": "h", "qubits": [0]},
                {"gate": "cx", "qubits": [0, 1]},
            ],
        )
        assert r.success is True
        assert r.data["num_qubits"] == 2
        assert r.data["gate_count"] == 2

    def test_simulate_bell_state(self):
        agent = QuantumHardwareAgent()
        agent._ensure_loaded()
        qk = agent._qiskit

        qc = qk.QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)

        r = agent.execute(operation="simulate", circuit=qc, output="statevector")
        assert r.success is True
        probs = r.data["probabilities"]
        # Bell state: |00> and |11> each ~50%
        assert abs(probs.get("00", 0) - 0.5) < 0.01
        assert abs(probs.get("11", 0) - 0.5) < 0.01

    def test_analyze(self):
        agent = QuantumHardwareAgent()
        agent._ensure_loaded()
        qk = agent._qiskit

        qc = qk.QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)

        r = agent.execute(operation="analyze", circuit=qc)
        assert r.success is True
        assert r.data["num_qubits"] == 3
        assert r.data["total_gates"] == 3


class TestQuantumCryptoSmoke:
    """Smoke tests for QuantumCryptoAgent with real qencrypt calls."""

    def test_encrypt_decrypt_roundtrip(self):
        agent = QuantumCryptoAgent()
        r_enc = agent.execute(
            operation="encrypt",
            plaintext="Hello Frankenstein",
            passphrase="test-pass-123",
            entropy_source="local",
        )
        assert r_enc.success is True
        assert "package" in r_enc.data

        r_dec = agent.execute(
            operation="decrypt",
            package=r_enc.data["package"],
            passphrase="test-pass-123",
        )
        assert r_dec.success is True
        assert r_dec.data["plaintext"] == "Hello Frankenstein"

    def test_encrypt_empty_plaintext(self):
        agent = QuantumCryptoAgent()
        r = agent.execute(
            operation="encrypt",
            plaintext="",
            passphrase="pw",
        )
        assert r.success is False

    def test_inspect_package(self):
        agent = QuantumCryptoAgent()
        r_enc = agent.execute(
            operation="encrypt",
            plaintext="test",
            passphrase="pw",
            entropy_source="local",
        )
        assert r_enc.success is True

        r_insp = agent.execute(
            operation="inspect_package",
            package=r_enc.data["package"],
        )
        assert r_insp.success is True
        assert r_insp.data["has_ciphertext"] is True


class TestNumericalComputingSmoke:
    """Smoke tests for NumericalComputingAgent with real NumPy/SciPy calls."""

    def test_solve_linear(self):
        agent = NumericalComputingAgent()
        A = [[2, 1], [1, 3]]
        b = [5, 7]
        r = agent.execute(operation="solve_linear", A=A, b=b)
        assert r.success is True
        x = r.data["solution"]
        # 2*x0 + x1 = 5, x0 + 3*x1 = 7  =>  x0 = 1.6, x1 = 1.8
        assert abs(x[0] - 1.6) < 1e-10
        assert abs(x[1] - 1.8) < 1e-10

    def test_eigenvalues(self):
        agent = NumericalComputingAgent()
        M = [[1, 0], [0, 2]]
        r = agent.execute(operation="eigenvalues", matrix=M)
        assert r.success is True
        eigs = sorted([complex(e).real for e in r.data["eigenvalues"]])
        assert abs(eigs[0] - 1.0) < 1e-10
        assert abs(eigs[1] - 2.0) < 1e-10

    def test_matrix_exp_identity(self):
        agent = NumericalComputingAgent()
        # exp(0) = I
        Z = [[0, 0], [0, 0]]
        r = agent.execute(operation="matrix_exp", matrix=Z)
        assert r.success is True
        result = np.array(r.data["matrix_exp"])
        assert np.allclose(result, np.eye(2))

    def test_fft(self):
        agent = NumericalComputingAgent()
        signal = [1, 0, 1, 0]
        r = agent.execute(operation="fft", signal=signal)
        assert r.success is True
        assert r.data["length"] == 4
        assert len(r.data["magnitude"]) == 4

    def test_matrix_analysis(self):
        agent = NumericalComputingAgent()
        I2 = [[1, 0], [0, 1]]
        r = agent.execute(operation="matrix_analysis", matrix=I2)
        assert r.success is True
        assert r.data["rank"] == 2
        assert r.data["is_unitary"] is True
        assert r.data["is_hermitian"] is True

    def test_missing_params(self):
        agent = NumericalComputingAgent()
        r = agent.execute(operation="solve_linear")
        assert r.success is False
        assert "requires" in r.error.lower()
