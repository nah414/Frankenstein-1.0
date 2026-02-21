"""
FRANKENSTEIN 1.0 — Pre-Phase 4 Integration Tests
Tests memory management and circuit library.

Run: python -m pytest tests/test_memory_circuits.py -v
"""

import json
import tempfile
from pathlib import Path
import pytest


class TestCircuitLibrary:
    """Test circuit save/load/export/delete."""

    def setup_method(self):
        """Create temp directory for test circuits."""
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

        from synthesis.circuit_library import CircuitLibrary
        self.lib = CircuitLibrary(base_path=self.tmp_path / "circuits")

    def test_create_circuit(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("test_bell", 2, "Test Bell state")
        c.add_gate("h", [0])
        c.add_gate("cx", [1], controls=[0])
        assert len(c.gates) == 2
        assert c.n_qubits == 2

    def test_save_and_load(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("bell_test", 2, "Bell pair")
        c.add_gate("h", [0])
        c.add_gate("cx", [1], controls=[0])

        self.lib.save(c)
        loaded = self.lib.load("bell_test")

        assert loaded is not None
        assert loaded.name == "bell_test"
        assert loaded.n_qubits == 2
        assert len(loaded.gates) == 2

    def test_list_circuits(self):
        from synthesis.circuit_library import CircuitDefinition

        for name in ["circuit_a", "circuit_b", "circuit_c"]:
            c = CircuitDefinition(name, 2)
            c.add_gate("h", [0])
            self.lib.save(c)

        circuits = self.lib.list_circuits()
        assert len(circuits) == 3

    def test_delete_circuit(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("to_delete", 1)
        c.add_gate("x", [0])
        self.lib.save(c)

        assert self.lib.delete("to_delete") is True
        assert self.lib.load("to_delete") is None

    def test_export_qasm(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("qasm_test", 2, "QASM export test")
        c.add_gate("h", [0])
        c.add_gate("cx", [1], controls=[0])
        self.lib.save(c)

        filepath = self.lib.export_qasm("qasm_test")
        assert filepath is not None

        content = filepath.read_text()
        assert "OPENQASM 2.0;" in content
        assert "qreg q[2];" in content
        assert "h q[0];" in content
        assert "cx q[0], q[1];" in content

    def test_version_increment(self):
        from synthesis.circuit_library import CircuitDefinition

        c1 = CircuitDefinition("versioned", 2)
        c1.add_gate("h", [0])
        self.lib.save(c1)

        c2 = CircuitDefinition("versioned", 2, "Updated")
        c2.add_gate("h", [0])
        c2.add_gate("x", [1])
        self.lib.save(c2)

        loaded = self.lib.load("versioned")
        assert loaded.version == 2

    def test_gate_count(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("count_test", 3)
        c.add_gate("h", [0])
        c.add_gate("h", [1])
        c.add_gate("cx", [1], controls=[0])
        c.add_gate("cx", [2], controls=[0])

        counts = c.gate_count()
        assert counts["h"] == 2
        assert counts["cx"] == 2


class TestComputationLogger:
    """Test computation logging."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

    def test_logger_creates_file(self):
        from synthesis.computation_log import ComputationLogger
        logger = ComputationLogger(base_path=self.tmp_path)

        assert logger._log_file.exists()

    def test_log_events(self):
        from synthesis.computation_log import ComputationLogger
        logger = ComputationLogger(base_path=self.tmp_path)

        logger.log_init(2, "zero")
        logger.log_gate("h", [0])
        logger.log_gate("cx", [1], controls=[0])
        logger.log_measurement(2, 1024, [{"state": "00", "prob": 0.5}])

        events = logger.get_recent_events()
        # session_start + 4 events = 5 total
        assert len(events) >= 4

    def test_session_summary(self):
        from synthesis.computation_log import ComputationLogger
        logger = ComputationLogger(base_path=self.tmp_path)

        logger.log_init(3, "zero")
        logger.log_gate("h", [0])
        logger.log_gate("h", [1])

        summary = logger.get_session_summary()
        assert summary["total_events"] >= 3
        assert "gate_applied" in summary["event_breakdown"]


class TestOpenQASMExport:
    """Test OpenQASM 2.0 export validity."""

    def test_bell_state_qasm(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("bell", 2, "Bell state")
        c.add_gate("h", [0])
        c.add_gate("cx", [1], controls=[0])

        qasm = c.to_openqasm2()

        assert "OPENQASM 2.0;" in qasm
        assert 'include "qelib1.inc";' in qasm
        assert "qreg q[2];" in qasm
        assert "creg c[2];" in qasm
        assert "h q[0];" in qasm
        assert "cx q[0], q[1];" in qasm

    def test_rotation_gate_qasm(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("rotation", 1)
        c.add_gate("rx", [0], params={"theta": 1.5707963})

        qasm = c.to_openqasm2()
        assert "rx(1.5707963) q[0];" in qasm

    def test_toffoli_qasm(self):
        from synthesis.circuit_library import CircuitDefinition
        c = CircuitDefinition("toffoli", 3)
        c.add_gate("ccx", [2], controls=[0, 1])

        qasm = c.to_openqasm2()
        assert "ccx q[0], q[1], q[2];" in qasm
