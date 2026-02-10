#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Hardware Agent
Phase 3.5: Lazy-loaded wrapper for Qiskit toolset

Provides quantum circuit construction, transpilation for target hardware,
circuit optimization, statevector simulation, and noise modeling.
"""

from typing import Any, Dict, List, Optional, Union

from ..base import BaseAgent, AgentResult


class QuantumHardwareAgent(BaseAgent):
    """
    Agent for quantum circuit transpilation and hardware interface via Qiskit.

    Capabilities:
    - Quantum circuit construction
    - Circuit transpilation for target backends
    - Circuit optimization (levels 0–3)
    - Statevector / density-matrix simulation
    - Circuit depth and gate-count analysis
    """

    name = "quantum_hardware"
    description = "Quantum circuit transpilation and hardware interface (Qiskit)"
    version = "1.0.0"
    requires_network = False
    requires_filesystem = False
    max_execution_time = 60

    def __init__(self):
        super().__init__()
        self._qiskit = None

    def _ensure_loaded(self):
        """Lazy-load Qiskit only when a method is actually called."""
        if self._qiskit is None:
            from libs.local_toolsets import load_qiskit
            self._qiskit = load_qiskit()
            if self._qiskit is None:
                raise RuntimeError(
                    "Failed to load Qiskit — insufficient RAM or not installed"
                )

    def execute(self, operation: str = "", **kwargs) -> AgentResult:
        """
        Dispatch to the requested quantum hardware operation.

        Args:
            operation: One of 'build_circuit', 'transpile', 'optimize',
                       'simulate', 'analyze'
            **kwargs: Operation-specific parameters
        """
        if not operation:
            return AgentResult(
                success=False,
                error="No operation specified. Available: build_circuit, "
                      "transpile, optimize, simulate, analyze",
            )

        dispatch = {
            "build_circuit": self._run_build_circuit,
            "transpile": self._run_transpile,
            "optimize": self._run_optimize,
            "simulate": self._run_simulate,
            "analyze": self._run_analyze,
        }

        handler = dispatch.get(operation)
        if handler is None:
            return AgentResult(
                success=False,
                error=f"Unknown operation: {operation!r}. "
                      f"Available: {', '.join(sorted(dispatch))}",
            )

        try:
            self._ensure_loaded()
            return handler(**kwargs)
        except RuntimeError as exc:
            return AgentResult(success=False, error=str(exc))
        except Exception as exc:
            return AgentResult(success=False, error=f"{type(exc).__name__}: {exc}")

    # ── Circuit construction ─────────────────────────────────────────────

    def _run_build_circuit(
        self,
        num_qubits: int = 2,
        gates: Optional[List[Dict[str, Any]]] = None,
        measure_all: bool = False,
        **kwargs,
    ) -> AgentResult:
        """
        Build a quantum circuit from a gate specification.

        Args:
            num_qubits: Number of qubits
            gates: List of gate dicts, e.g. [{"gate": "h", "qubits": [0]},
                                              {"gate": "cx", "qubits": [0, 1]}]
            measure_all: Whether to add measurement on all qubits
        """
        qk = self._qiskit
        qc = qk.QuantumCircuit(num_qubits)

        if gates:
            for g in gates:
                gate_name = g.get("gate", "").lower()
                qubits = g.get("qubits", [])
                params = g.get("params", [])

                gate_fn = getattr(qc, gate_name, None)
                if gate_fn is None:
                    return AgentResult(
                        success=False,
                        error=f"Unknown gate: {gate_name!r}",
                    )
                gate_fn(*params, *qubits) if params else gate_fn(*qubits)

        if measure_all:
            qc.measure_all()

        return AgentResult(
            success=True,
            data={
                "circuit": qc,
                "num_qubits": qc.num_qubits,
                "depth": qc.depth(),
                "gate_count": qc.size(),
                "openqasm": qc.qasm() if hasattr(qc, "qasm") else None,
            },
        )

    # ── Transpilation ────────────────────────────────────────────────────

    def _run_transpile(
        self,
        circuit=None,
        num_qubits: int = 5,
        basis_gates: Optional[List[str]] = None,
        optimization_level: int = 1,
        **kwargs,
    ) -> AgentResult:
        """
        Transpile a circuit for a target backend.

        Args:
            circuit: A Qiskit QuantumCircuit (or build one if None with kwargs)
            num_qubits: Backend qubit count for GenericBackendV2
            basis_gates: Target basis gate set (default: ['cx', 'id', 'rz', 'sx', 'x'])
            optimization_level: 0 (none) to 3 (heavy)
        """
        qk = self._qiskit

        if circuit is None:
            return AgentResult(
                success=False,
                error="transpile requires a 'circuit' argument",
            )

        from qiskit.providers.fake_provider import GenericBackendV2
        backend = GenericBackendV2(num_qubits=max(num_qubits, circuit.num_qubits))

        transpiled = qk.transpile(
            circuit,
            backend=backend,
            basis_gates=basis_gates,
            optimization_level=optimization_level,
        )

        return AgentResult(
            success=True,
            data={
                "transpiled_circuit": transpiled,
                "original_depth": circuit.depth(),
                "transpiled_depth": transpiled.depth(),
                "original_gates": circuit.size(),
                "transpiled_gates": transpiled.size(),
                "optimization_level": optimization_level,
                "backend_qubits": num_qubits,
            },
        )

    # ── Optimization ─────────────────────────────────────────────────────

    def _run_optimize(
        self,
        circuit=None,
        optimization_level: int = 3,
        **kwargs,
    ) -> AgentResult:
        """
        Optimize a quantum circuit via transpilation at the given level.

        Args:
            circuit: A Qiskit QuantumCircuit
            optimization_level: 0 (none) to 3 (heavy optimization)
        """
        qk = self._qiskit

        if circuit is None:
            return AgentResult(
                success=False,
                error="optimize requires a 'circuit' argument",
            )

        optimized = qk.transpile(
            circuit,
            optimization_level=optimization_level,
        )

        return AgentResult(
            success=True,
            data={
                "optimized_circuit": optimized,
                "original_depth": circuit.depth(),
                "optimized_depth": optimized.depth(),
                "original_gates": circuit.size(),
                "optimized_gates": optimized.size(),
                "reduction_percent": round(
                    (1 - optimized.size() / max(circuit.size(), 1)) * 100, 1
                ),
                "optimization_level": optimization_level,
            },
        )

    # ── Statevector simulation ───────────────────────────────────────────

    def _run_simulate(
        self,
        circuit=None,
        output: str = "statevector",
        **kwargs,
    ) -> AgentResult:
        """
        Simulate a circuit and return the final quantum state.

        Args:
            circuit: A Qiskit QuantumCircuit (without measurements)
            output: 'statevector' or 'density_matrix'
        """
        if circuit is None:
            return AgentResult(
                success=False,
                error="simulate requires a 'circuit' argument",
            )

        from qiskit.quantum_info import Statevector, DensityMatrix

        if output == "statevector":
            sv = Statevector.from_instruction(circuit)
            probs = sv.probabilities_dict()
            return AgentResult(
                success=True,
                data={
                    "statevector": sv,
                    "probabilities": probs,
                    "num_qubits": circuit.num_qubits,
                    "output_type": "statevector",
                },
            )
        elif output == "density_matrix":
            dm = DensityMatrix.from_instruction(circuit)
            return AgentResult(
                success=True,
                data={
                    "density_matrix": dm,
                    "purity": dm.purity(),
                    "num_qubits": circuit.num_qubits,
                    "output_type": "density_matrix",
                },
            )
        else:
            return AgentResult(
                success=False,
                error=f"Unknown output type: {output!r}. Use 'statevector' or 'density_matrix'.",
            )

    # ── Circuit analysis ─────────────────────────────────────────────────

    def _run_analyze(
        self,
        circuit=None,
        **kwargs,
    ) -> AgentResult:
        """
        Analyze circuit properties: depth, gate counts, qubit usage.

        Args:
            circuit: A Qiskit QuantumCircuit
        """
        if circuit is None:
            return AgentResult(
                success=False,
                error="analyze requires a 'circuit' argument",
            )

        # Count gates by type
        gate_counts: Dict[str, int] = {}
        for instruction in circuit.data:
            name = instruction.operation.name
            gate_counts[name] = gate_counts.get(name, 0) + 1

        return AgentResult(
            success=True,
            data={
                "num_qubits": circuit.num_qubits,
                "num_clbits": circuit.num_clbits,
                "depth": circuit.depth(),
                "total_gates": circuit.size(),
                "gate_counts": gate_counts,
                "num_parameters": circuit.num_parameters,
            },
        )
