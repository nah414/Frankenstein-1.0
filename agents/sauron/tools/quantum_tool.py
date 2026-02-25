"""
FRANKENSTEIN 1.0 - Eye of Sauron: Quantum Tool
Phase 4 / Day 3: Tool Framework

Gives Sauron direct programmatic control over the quantum engine.
Integrates: SynthesisEngine (native), Qiskit (QASM/Aer), QuTiP (open systems),
            SciPy (linear algebra), NumPy (statevector math).

Two execution modes:
  Direct mode  — Sauron calls individual gate ops on the live SynthesisEngine
                 state. Manual terminal mode and Sauron share the SAME engine
                 singleton — they co-exist and can hand off to each other.

  Circuit mode — Sauron submits a full circuit definition (list of gate dicts,
                 matching CircuitDefinition.gates format) which executes in
                 sequence. Works with circuits recalled from memory_tool.

Permission mapping:
  Ring 3 (SAFE):     init_qubits, apply_gate, run_circuit, get_state_info
  Ring 2 (SENSITIVE): measure, save_state, load_circuit_and_run,
                       qiskit_run, qutip_evolve, show_bloch
"""

import logging
from typing import Any, Optional

from agents.sauron.permissions import PermissionLevel, get_permission_manager
from agents.sauron.audit import SauronEvent, get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Gate methods that take (target) only
_SINGLE_QUBIT_GATES = frozenset({
    "h", "x", "y", "z", "s", "t", "sdg", "tdg", "sx", "sxdg",
})

# Gate methods that take (target, angle)
_ROTATION_GATES = {
    "rx": "rotate_x",
    "ry": "rotate_y",
    "rz": "rotate_z",
    "rotate_x": "rotate_x",
    "rotate_y": "rotate_y",
    "rotate_z": "rotate_z",
    "p": "p",
    "phase": "p",
    "u1": "p",
}

# Gate methods that take (control, target)
_TWO_QUBIT_GATES = frozenset({
    "cx", "cnot", "cz", "cy", "ch", "swap",
})

# Gate methods that take (control, target, angle)
_CONTROLLED_ROTATION_GATES = frozenset({"cp"})

# Three-qubit gates
_THREE_QUBIT_GATES = frozenset({"cswap", "ccx", "toffoli"})


class QuantumTool(BaseTool):
    """
    Eye of Sauron's quantum execution tool.

    Supports 6 actions dispatched via execute(action=...):
      init_qubits        — reset engine to n-qubit |0...0⟩ (Ring 3)
      apply_gate         — single gate operation (Ring 3)
      run_circuit        — execute list of gate dicts in sequence (Ring 3)
      get_state_info     — read probabilities, Bloch coords, qubit count (Ring 3)
      measure            — run measurement simulation (Ring 2)
      save_state         — persist current state to .npz (Ring 2)
      load_circuit_and_run — recall named circuit + execute + measure (Ring 2)
      qiskit_run         — compile QASM string via Qiskit + run on Aer (Ring 2)
      qutip_evolve       — Schrödinger/Lindblad time evolution via QuTiP (Ring 2)
      show_bloch         — launch Bloch sphere browser visualisation (Ring 2)
    """

    name = "quantum"
    description = (
        "Execute quantum circuits and computations using the Frankenstein synthesis engine. "
        "Supports gate operations, measurement, Qiskit QASM execution, QuTiP open-system "
        "evolution, Bloch sphere visualisation, and state save/recall. "
        "Ring 3 for gate ops and reads; Ring 2 for measure, visualise, save, Qiskit, QuTiP."
    )
    # Default permission level shown in registry; actual level is action-dependent.
    permission_level = PermissionLevel.SAFE

    # Actions that require Ring 2 approval
    _SENSITIVE_ACTIONS = frozenset({
        "measure", "save_state", "load_circuit_and_run",
        "qiskit_run", "qutip_evolve", "show_bloch",
    })

    def execute(self, action: str = "get_state_info", **kwargs) -> ToolResult:
        """
        Dispatch to the requested quantum action.

        Args:
            action: One of the supported actions (see class docstring)
            **kwargs: Action-specific parameters (see each method)
        """
        # Override permission level for sensitive actions
        if action in self._SENSITIVE_ACTIONS:
            self.permission_level = PermissionLevel.SENSITIVE
        else:
            self.permission_level = PermissionLevel.SAFE

        dispatch = {
            "init_qubits":           self._init_qubits,
            "apply_gate":            self._apply_gate,
            "run_circuit":           self._run_circuit,
            "get_state_info":        self._get_state_info,
            "measure":               self._measure,
            "save_state":            self._save_state,
            "load_circuit_and_run":  self._load_circuit_and_run,
            "qiskit_run":            self._qiskit_run,
            "qutip_evolve":          self._qutip_evolve,
            "show_bloch":            self._show_bloch,
        }

        if action not in dispatch:
            return ToolResult(
                success=False,
                error=f"Unknown quantum action '{action}'. Valid: {sorted(dispatch)}",
            )

        # Ring 2: request permission before executing sensitive actions
        if action in self._SENSITIVE_ACTIONS:
            pm = get_permission_manager()
            audit = get_sauron_audit()
            desc = self._describe_action(action, kwargs)
            audit.log_permission(SauronEvent.PERMISSION_ASK, f"quantum.{action}", desc)
            if not pm.request_permission(f"quantum.{action}", desc):
                audit.log_permission(SauronEvent.PERMISSION_DENY, f"quantum.{action}", desc)
                return ToolResult(
                    success=False,
                    error=f"Permission denied for quantum.{action}",
                    permission_level=PermissionLevel.SENSITIVE,
                )
            audit.log_permission(SauronEvent.PERMISSION_GRANT, f"quantum.{action}", desc)

        return dispatch[action](**kwargs)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_engine(self):
        """Get the shared SynthesisEngine singleton."""
        from synthesis.engine import get_synthesis_engine
        return get_synthesis_engine()

    def _describe_action(self, action: str, kwargs: dict) -> str:
        """Human-readable description for permission prompts."""
        descriptions = {
            "measure":              f"Run {kwargs.get('shots', 1024)}-shot measurement",
            "save_state":           f"Save quantum state as '{kwargs.get('name', '?')}'",
            "load_circuit_and_run": f"Load + run circuit '{kwargs.get('name', '?')}' and measure",
            "qiskit_run":           f"Compile + run QASM circuit via Qiskit-Aer ({kwargs.get('shots', 1024)} shots)",
            "qutip_evolve":         "Run QuTiP open-system time evolution",
            "show_bloch":           "Launch Bloch sphere visualisation in browser",
        }
        return descriptions.get(action, f"Execute quantum.{action}")

    # ── Ring 3 Actions ─────────────────────────────────────────────────────────

    def _init_qubits(self, n_qubits: int = 1, **kwargs) -> ToolResult:
        """
        Reset the quantum register to |0...0⟩ with n_qubits.
        Max 16 qubits on Tier 1 hardware.
        """
        if not isinstance(n_qubits, int) or n_qubits < 1 or n_qubits > 16:
            return ToolResult(
                success=False,
                error=f"n_qubits must be 1–16 (got {n_qubits})",
            )
        try:
            engine = self._get_engine()
            engine.reset(n_qubits)
            return ToolResult(
                success=True,
                data={"n_qubits": n_qubits, "state": "|" + "0" * n_qubits + ">"},
                summary=f"Initialized {n_qubits}-qubit register in |{'0'*n_qubits}> state.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _apply_gate(
        self,
        gate: str = "h",
        target: int = 0,
        control: Optional[int] = None,
        controls: Optional[list] = None,
        params: Optional[list] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Apply a single quantum gate to the statevector.

        Args:
            gate:     Gate name (h, x, y, z, cx, ry, p, mcx, etc.)
            target:   Target qubit index
            control:  Single control qubit (for 2-qubit gates)
            controls: List of control qubits (for MCX)
            params:   List of gate parameters [angle] (for rotations)
        """
        try:
            engine = self._get_engine()
            if engine.get_num_qubits() == 0:
                return ToolResult(
                    success=False,
                    error="No qubits initialized. Call init_qubits first.",
                )

            g = gate.lower()
            angle = params[0] if params else None

            if g in _SINGLE_QUBIT_GATES:
                getattr(engine, g)(target)

            elif g in _ROTATION_GATES:
                method = _ROTATION_GATES[g]
                if angle is None:
                    return ToolResult(success=False, error=f"Gate '{gate}' requires params=[angle]")
                getattr(engine, method)(target, float(angle))

            elif g in _TWO_QUBIT_GATES:
                ctrl = control if control is not None else (controls[0] if controls else None)
                if ctrl is None and g not in ("swap",):
                    return ToolResult(success=False, error=f"Gate '{gate}' requires control qubit")
                if g in ("cx", "cnot"):
                    engine.cx(ctrl, target)
                elif g == "cz":
                    engine.cz(ctrl, target)
                elif g == "cy":
                    engine.cy(ctrl, target)
                elif g == "ch":
                    engine.ch(ctrl, target)
                elif g == "swap":
                    q2 = control if control is not None else (controls[0] if controls else None)
                    if q2 is None:
                        return ToolResult(success=False, error="swap requires two qubits: target and control")
                    engine.swap(target, q2)

            elif g in _CONTROLLED_ROTATION_GATES:
                ctrl = control if control is not None else (controls[0] if controls else None)
                if ctrl is None or angle is None:
                    return ToolResult(success=False, error=f"Gate '{gate}' requires control and params=[angle]")
                engine.cp(ctrl, target, float(angle))

            elif g in _THREE_QUBIT_GATES:
                if g == "cswap":
                    ctrl = control if control is not None else (controls[0] if controls else None)
                    q2 = controls[1] if controls and len(controls) > 1 else None
                    if ctrl is None or q2 is None:
                        return ToolResult(success=False, error="cswap requires control, target, and second qubit")
                    engine.cswap(ctrl, target, q2)
                else:  # ccx / toffoli
                    ctrls = controls or ([control] if control is not None else [])
                    if len(ctrls) < 2:
                        return ToolResult(success=False, error="ccx/toffoli requires 2 control qubits")
                    engine.mcx(ctrls, target)

            elif g == "mcx":
                ctrls = controls or ([control] if control is not None else [])
                if not ctrls:
                    return ToolResult(success=False, error="mcx requires controls list")
                engine.mcx(ctrls, target)

            else:
                return ToolResult(success=False, error=f"Unknown gate: '{gate}'")

            return ToolResult(
                success=True,
                data={"gate": gate, "target": target, "control": control,
                      "controls": controls, "params": params},
                summary=f"Applied {gate} to qubit {target}.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _run_circuit(self, circuit: list = None, **kwargs) -> ToolResult:
        """
        Execute a list of gate dicts in sequence on the SynthesisEngine.

        Circuit format (matches CircuitDefinition.gates):
          [
            {"gate": "reset",  "n_qubits": 2},
            {"gate": "h",      "targets": [0]},
            {"gate": "cx",     "targets": [1], "controls": [0]},
            {"gate": "ry",     "targets": [0], "params": [1.5708]},
            {"gate": "measure","shots": 1024},
          ]

        Notes:
          - "reset" ops (Ring 3) are executed freely within the circuit.
          - "measure" ops inside a circuit are executed and their results
            included, but do NOT trigger a separate Ring 2 prompt since
            the user already approved run_circuit at the Ring 3 level.
            If you want explicit measurement approval use action="measure".
        """
        if not circuit:
            return ToolResult(success=False, error="circuit list is required and must be non-empty")

        engine = self._get_engine()
        results = []
        measure_results = None

        try:
            for i, op in enumerate(circuit):
                gate = (op.get("gate") or op.get("op", "")).lower()
                targets = op.get("targets", [op.get("target")] if "target" in op else [])
                controls = op.get("controls", [op.get("control")] if "control" in op else [])
                params = op.get("params", [op.get("angle")] if "angle" in op else [])

                # Filter None values
                targets = [t for t in targets if t is not None]
                controls = [c for c in controls if c is not None]
                params = [p for p in params if p is not None]

                if gate == "reset":
                    n = op.get("n_qubits", op.get("n", 1))
                    engine.reset(int(n))
                    results.append(f"reset({n})")

                elif gate == "measure":
                    shots = int(op.get("shots", 1024))
                    measure_results = engine.measure(shots)
                    results.append(f"measure({shots}) → {len(measure_results)} outcomes")

                elif targets:
                    target = targets[0]
                    ctrl = controls[0] if controls else None
                    angle = float(params[0]) if params else None

                    r = self._apply_gate(
                        gate=gate,
                        target=target,
                        control=ctrl,
                        controls=controls if len(controls) > 1 else None,
                        params=params if params else None,
                    )
                    if not r.success:
                        return ToolResult(
                            success=False,
                            error=f"Step {i} ({gate}): {r.error}",
                            data={"completed_steps": results},
                        )
                    results.append(f"{gate}({', '.join(str(x) for x in ([ctrl] if ctrl else []) + [target])})")
                else:
                    results.append(f"[skipped unknown op: {gate}]")

            data = {
                "steps_executed": len(results),
                "circuit_log": results,
                "n_qubits": engine.get_num_qubits(),
            }
            if measure_results is not None:
                data["measurement_counts"] = measure_results

            return ToolResult(
                success=True,
                data=data,
                summary=(
                    f"Circuit executed: {len(results)} steps, "
                    f"{engine.get_num_qubits()} qubits."
                    + (f" Measurement: {measure_results}" if measure_results else "")
                ),
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), data={"completed_steps": results})

    def _get_state_info(self, **kwargs) -> ToolResult:
        """
        Return current quantum state information: probabilities, Bloch coords,
        qubit count, and top basis states.
        """
        try:
            engine = self._get_engine()
            n = engine.get_num_qubits()
            if n == 0:
                return ToolResult(success=True, data={"n_qubits": 0}, summary="No state initialized.")

            import numpy as np
            state = engine.get_state()
            probs = engine.get_probabilities()
            marginals = engine.get_marginal_probabilities()

            # Top probable basis states
            top = sorted(probs.items(), key=lambda kv: -kv[1])[:8]

            # Bloch coords for each qubit (marginal representation)
            bloch = []
            for q in range(min(n, 8)):
                try:
                    x, y, z = engine.get_bloch_coords(q)
                    bloch.append({"qubit": q, "x": round(x, 4), "y": round(y, 4), "z": round(z, 4)})
                except Exception:
                    bloch.append({"qubit": q, "x": 0, "y": 0, "z": 0})

            gate_log = getattr(engine, "_gate_log", [])

            return ToolResult(
                success=True,
                data={
                    "n_qubits":    n,
                    "gate_count":  len(gate_log),
                    "top_states":  [{"state": s, "probability": round(p, 6)} for s, p in top],
                    "bloch_coords": bloch,
                    "marginal_probabilities": [
                        {"qubit": i, "p0": round(m["p0"], 4), "p1": round(m["p1"], 4)}
                        for i, m in enumerate(marginals)
                    ],
                },
                summary=f"{n}-qubit state, {len(gate_log)} gates applied. "
                        f"Top state: |{top[0][0]}> p={top[0][1]:.4f}" if top else f"{n}-qubit state.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ── Ring 2 Actions ─────────────────────────────────────────────────────────

    def _measure(self, shots: int = 1024, **kwargs) -> ToolResult:
        """
        Run measurement simulation and return counts dictionary.
        Permission already checked in execute() before dispatch.
        """
        try:
            engine = self._get_engine()
            if engine.get_num_qubits() == 0:
                return ToolResult(success=False, error="No state to measure. Call init_qubits first.")
            counts = engine.measure(int(shots))
            total = sum(counts.values())
            top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
            return ToolResult(
                success=True,
                data={
                    "shots":  total,
                    "counts": counts,
                    "top_outcomes": [
                        {"state": s, "count": c, "probability": round(c / total, 4)}
                        for s, c in top
                    ],
                },
                summary=f"Measured {total} shots. Top: |{top[0][0]}> {top[0][1]}x ({top[0][1]/total*100:.1f}%)" if top else "Measurement complete.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _save_state(self, name: str = "sauron_state", **kwargs) -> ToolResult:
        """Save current SynthesisEngine state to .npz under the given name."""
        try:
            from synthesis.core.true_engine import get_true_engine
            path = get_true_engine().save_state(name)
            return ToolResult(
                success=True,
                data={"name": name, "path": str(path)},
                summary=f"Quantum state saved as '{name}'.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _load_circuit_and_run(self, name: str = "", shots: int = 1024, **kwargs) -> ToolResult:
        """Recall a named circuit from the library, execute it, and measure."""
        if not name:
            return ToolResult(success=False, error="'name' parameter required")
        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            circuit_def = lib.load(name)
            if circuit_def is None:
                return ToolResult(success=False, error=f"Circuit '{name}' not found in library.")

            # Execute the circuit
            run_result = self._run_circuit(circuit=circuit_def.gates)
            if not run_result.success:
                return run_result

            # Measure
            counts = self._get_engine().measure(int(shots))
            run_result.data["measurement_counts"] = counts
            run_result.data["circuit_name"] = name
            run_result.summary = f"Ran circuit '{name}' ({len(circuit_def.gates)} gates), measured {shots} shots."
            return run_result
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _qiskit_run(self, qasm: str = "", shots: int = 1024, **kwargs) -> ToolResult:
        """
        Compile an OpenQASM 2.0 string via Qiskit and run on Aer statevector simulator.

        Args:
            qasm:  Complete OpenQASM 2.0 string
            shots: Number of measurement shots
        """
        if not qasm:
            return ToolResult(success=False, error="'qasm' parameter required (OpenQASM 2.0 string)")
        try:
            from qiskit import QuantumCircuit
            from qiskit_aer import AerSimulator

            qc = QuantumCircuit.from_qasm_str(qasm)
            if not qc.num_clbits:
                qc.measure_all()

            sim = AerSimulator(method="statevector")
            job = sim.run(qc, shots=int(shots))
            result = job.result()
            counts = dict(result.get_counts())
            total = sum(counts.values())
            top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]

            return ToolResult(
                success=True,
                data={
                    "backend":     "qiskit-aer statevector",
                    "qubits":      qc.num_qubits,
                    "shots":       total,
                    "counts":      counts,
                    "top_outcomes": [
                        {"state": s, "count": c, "probability": round(c / total, 4)}
                        for s, c in top
                    ],
                },
                summary=(
                    f"Qiskit Aer: {qc.num_qubits} qubits, {total} shots. "
                    f"Top: |{top[0][0]}> {top[0][1]/total*100:.1f}%" if top else "Qiskit run complete."
                ),
            )
        except ImportError:
            return ToolResult(success=False, error="Qiskit or qiskit-aer not installed.")
        except Exception as e:
            return ToolResult(success=False, error=f"Qiskit run error: {e}")

    def _qutip_evolve(
        self,
        H: Any = None,
        psi0: Any = None,
        tlist: Any = None,
        c_ops: Any = None,
        **kwargs,
    ) -> ToolResult:
        """
        Time-evolve a quantum state using QuTiP.

        Schrödinger equation (c_ops=None):
            Uses qt.sesolve(H, psi0, tlist)
        Lindblad master equation (c_ops provided):
            Uses qt.mesolve(H, rho0, tlist, c_ops)

        Args:
            H:     Hamiltonian as nested list (NxN complex matrix) or QuTiP Qobj
            psi0:  Initial state as flat list of complex amplitudes
            tlist: Time points as list of floats [t0, t1, ..., tN]
            c_ops: Optional collapse operators (list of nested lists) for open systems
        """
        if H is None or psi0 is None or tlist is None:
            return ToolResult(
                success=False,
                error="Required: H (Hamiltonian), psi0 (initial state), tlist (time points)",
            )
        try:
            import qutip as qt
            import numpy as np

            # Convert inputs to QuTiP objects
            H_arr = np.array(H, dtype=complex)
            dims = H_arr.shape[0]
            H_qobj = qt.Qobj(H_arr, dims=[[dims], [dims]])

            psi0_arr = np.array(psi0, dtype=complex).reshape(dims, 1)
            psi0_qobj = qt.Qobj(psi0_arr, dims=[[dims], [1]])

            t_arr = list(tlist)

            if c_ops:
                # Open system — Lindblad master equation
                c_ops_qobj = [qt.Qobj(np.array(c, dtype=complex)) for c in c_ops]
                result = qt.mesolve(H_qobj, psi0_qobj * psi0_qobj.dag(), t_arr, c_ops_qobj, [])
                final_state = result.states[-1] if result.states else None
                mode = "mesolve (Lindblad)"
                final_data = final_state.full().tolist() if final_state else None
            else:
                # Closed system — Schrödinger equation
                result = qt.sesolve(H_qobj, psi0_qobj, t_arr)
                final_state = result.states[-1] if result.states else None
                mode = "sesolve (Schrödinger)"
                final_data = final_state.full().flatten().tolist() if final_state else None

            return ToolResult(
                success=True,
                data={
                    "mode":          mode,
                    "time_steps":    len(t_arr),
                    "t_start":       t_arr[0],
                    "t_end":         t_arr[-1],
                    "hilbert_dim":   dims,
                    "final_state":   final_data,
                    "n_states":      len(result.states),
                },
                summary=(
                    f"QuTiP {mode}: {dims}D Hilbert space, "
                    f"{len(t_arr)} time steps [{t_arr[0]:.2f}→{t_arr[-1]:.2f}]."
                ),
            )
        except ImportError:
            return ToolResult(success=False, error="QuTiP not installed.")
        except Exception as e:
            return ToolResult(success=False, error=f"QuTiP evolution error: {e}")

    def _show_bloch(self, **kwargs) -> ToolResult:
        """
        Launch the Bloch sphere browser visualisation for the current state.
        Uses the same visualiser as the manual 'bloch' terminal command.
        """
        try:
            engine = self._get_engine()
            n = engine.get_num_qubits()
            if n == 0:
                return ToolResult(success=False, error="No state to visualise. Call init_qubits first.")
            if n > 16:
                return ToolResult(success=False, error="Bloch sphere limited to 16 qubits.")

            all_coords   = engine.get_all_qubit_bloch_coords()
            entanglement = engine.get_entanglement_info()
            theo_probs   = engine.get_probabilities()
            marg_probs   = engine.get_marginal_probabilities()
            gate_log     = getattr(engine, "_gate_log", [])

            from synthesis.quantum import get_visualizer
            visualizer = get_visualizer()
            success = visualizer.launch_multi_qubit_bloch(
                qubit_coords=all_coords,
                entanglement_info=entanglement,
                num_qubits=n,
                gate_count=len(gate_log),
                theoretical_probs=theo_probs,
                marginal_probs=marg_probs,
                shots=0,
            )

            return ToolResult(
                success=success,
                data={
                    "n_qubits":    n,
                    "entangled":   entanglement.get("is_entangled", False),
                    "schmidt_rank": entanglement.get("schmidt_rank", 1),
                },
                summary=(
                    f"Launched {n}-qubit Bloch sphere."
                    + (" [ENTANGLED]" if entanglement.get("is_entangled") else "")
                ),
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Bloch sphere error: {e}")
