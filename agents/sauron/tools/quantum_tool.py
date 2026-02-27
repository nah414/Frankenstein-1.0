"""
FRANKENSTEIN 1.0 - Eye of Sauron: Quantum Tool
Phase 4 / Day 3: Tool Framework  (expanded Day 7+)

Gives Frank full programmatic control over every quantum and synthesis operation
available in the Monster Terminal.  Manual terminal mode and Frank share the SAME
engine singletons — they co-exist and can hand off to each other.

Two quantum engines:
  SynthesisEngine    — 16-qubit RAM-only (fast, default for n_qubits <= 16)
  TrueSynthesisEngine— 18-qubit disk-backed 20 GB (auto-selected for n_qubits > 16)

Permission mapping:
  Ring 3 (SAFE):      init_qubits, apply_gate, run_circuit, run_preset,
                      get_state_info, list_circuits, synthesis_status,
                      true_engine_status
  Ring 2 (SENSITIVE): measure, save_state, save_circuit, delete_circuit,
                      load_circuit_and_run, qiskit_run, qutip_evolve, show_bloch,
                      synthesis_run, synthesis_bloch, synthesis_gaussian,
                      synthesis_tunneling, synthesis_harmonic, synthesis_lorentz
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

    22 actions dispatched via execute(action=...):

    Ring 3 (auto-safe):
      init_qubits        — reset engine to n-qubit |0...0> (1-18; >16 uses TrueEngine)
      apply_gate         — single gate operation
      run_circuit        — execute list of gate dicts in sequence
      run_preset         — build bell / ghz / qft circuit automatically
      get_state_info     — read probabilities, Bloch coords, qubit count
      list_circuits      — list saved circuits from the library
      synthesis_status   — synthesis engine status
      true_engine_status — 20 GB TrueSynthesisEngine storage status

    Ring 2 (requires approval):
      measure            — run measurement + auto-launch Bloch sphere
      save_state         — persist current state to .npz
      save_circuit       — save current circuit to named library entry
      delete_circuit     — remove a named circuit from the library
      load_circuit_and_run — recall named circuit + execute + measure
      qiskit_run         — compile QASM string via Qiskit + run on Aer
      qutip_evolve       — Schrodinger/Lindblad time evolution via QuTiP
      show_bloch         — launch Bloch sphere browser visualisation
      synthesis_run      — run synthesis preset (gaussian/tunneling/harmonic/relativistic)
      synthesis_bloch    — launch synthesis Bloch popup (rabi/precession/spiral/hadamard)
      synthesis_gaussian — Gaussian wave packet simulation
      synthesis_tunneling— quantum tunneling simulation
      synthesis_harmonic — harmonic oscillator simulation
      synthesis_lorentz  — relativistic Lorentz boost simulation
    """

    name = "quantum"
    description = (
        "Full quantum computing automation via FRANKENSTEIN synthesis engines. "
        "Ring 3 (free): init_qubits, apply_gate, run_circuit, run_preset (bell/ghz/qft), "
        "get_state_info, list_circuits, synthesis_status, true_engine_status. "
        "Ring 2 (approval): measure (auto-launches Bloch sphere), show_bloch, save_state, "
        "save_circuit, delete_circuit, load_circuit_and_run, qiskit_run, qutip_evolve, "
        "synthesis_run, synthesis_bloch, synthesis_gaussian, synthesis_tunneling, "
        "synthesis_harmonic, synthesis_lorentz. "
        "Supports up to 18 qubits (>16 auto-routes to 20 GB TrueSynthesisEngine)."
    )
    permission_level = PermissionLevel.SAFE

    # Actions that require Ring 2 approval
    _SENSITIVE_ACTIONS = frozenset({
        "measure", "save_state", "save_circuit", "delete_circuit",
        "load_circuit_and_run", "qiskit_run", "qutip_evolve", "show_bloch",
        "synthesis_run", "synthesis_bloch", "synthesis_gaussian",
        "synthesis_tunneling", "synthesis_harmonic", "synthesis_lorentz",
    })

    def __init__(self):
        # Tracks whether the last init_qubits call selected the TrueSynthesisEngine
        self._use_true_engine: bool = False

    def execute(self, action: str = "get_state_info", **kwargs) -> ToolResult:
        """Dispatch to the requested quantum action."""
        if action in self._SENSITIVE_ACTIONS:
            self.permission_level = PermissionLevel.SENSITIVE
        else:
            self.permission_level = PermissionLevel.SAFE

        dispatch = {
            # Ring 3
            "init_qubits":           self._init_qubits,
            "apply_gate":            self._apply_gate,
            "run_circuit":           self._run_circuit,
            "run_preset":            self._run_preset,
            "get_state_info":        self._get_state_info,
            "list_circuits":         self._list_circuits,
            "synthesis_status":      self._synthesis_status,
            "true_engine_status":    self._true_engine_status,
            # Ring 2
            "measure":               self._measure,
            "save_state":            self._save_state,
            "save_circuit":          self._save_circuit,
            "delete_circuit":        self._delete_circuit,
            "load_circuit_and_run":  self._load_circuit_and_run,
            "qiskit_run":            self._qiskit_run,
            "qutip_evolve":          self._qutip_evolve,
            "show_bloch":            self._show_bloch,
            "synthesis_run":         self._synthesis_run,
            "synthesis_bloch":       self._synthesis_bloch,
            "synthesis_gaussian":    self._synthesis_gaussian,
            "synthesis_tunneling":   self._synthesis_tunneling,
            "synthesis_harmonic":    self._synthesis_harmonic,
            "synthesis_lorentz":     self._synthesis_lorentz,
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

    # ── Engine routing ──────────────────────────────────────────────────────────

    def _get_engine(self):
        """Return the active quantum engine (RAM or TrueEngine based on last init)."""
        if self._use_true_engine:
            from synthesis.core.true_engine import get_true_engine
            return get_true_engine()
        from synthesis.engine import get_synthesis_engine
        return get_synthesis_engine()

    def _describe_action(self, action: str, kwargs: dict) -> str:
        """Human-readable description for permission prompts."""
        descriptions = {
            "measure":              f"Run {kwargs.get('shots', 1024)}-shot measurement + launch Bloch sphere",
            "save_state":           f"Save quantum state as '{kwargs.get('name', '?')}'",
            "save_circuit":         f"Save current circuit as '{kwargs.get('name', '?')}'",
            "delete_circuit":       f"Delete circuit '{kwargs.get('name', '?')}' from library",
            "load_circuit_and_run": f"Load + run circuit '{kwargs.get('name', '?')}' and measure",
            "qiskit_run":           f"Compile + run QASM circuit via Qiskit-Aer ({kwargs.get('shots', 1024)} shots)",
            "qutip_evolve":         "Run QuTiP open-system time evolution",
            "show_bloch":           "Launch Bloch sphere visualisation in browser",
            "synthesis_run":        f"Run synthesis simulation: {kwargs.get('preset', 'gaussian')}",
            "synthesis_bloch":      f"Launch synthesis Bloch sphere: {kwargs.get('sim_type', 'rabi')}",
            "synthesis_gaussian":   f"Run Gaussian wave packet (sigma={kwargs.get('sigma', 1.0)}, k0={kwargs.get('k0', 0.0)})",
            "synthesis_tunneling":  f"Run quantum tunneling (barrier={kwargs.get('barrier', 1.0)})",
            "synthesis_harmonic":   f"Run harmonic oscillator (omega={kwargs.get('omega', 1.0)})",
            "synthesis_lorentz":    f"Apply Lorentz boost (velocity={kwargs.get('velocity', 0.5)}c)",
        }
        return descriptions.get(action, f"Execute quantum.{action}")

    # ── Ring 3 Actions ──────────────────────────────────────────────────────────

    def _init_qubits(self, n_qubits: int = 1, **kwargs) -> ToolResult:
        """
        Reset the quantum register to |0...0> with n_qubits.
        1-16 qubits: uses the 16-qubit RAM SynthesisEngine.
        17-18 qubits: automatically uses the 20 GB TrueSynthesisEngine.
        """
        if not isinstance(n_qubits, int) or n_qubits < 1 or n_qubits > 18:
            return ToolResult(
                success=False,
                error=f"n_qubits must be 1-18 (got {n_qubits}). TrueEngine supports up to 18.",
            )
        try:
            if n_qubits > 16:
                from synthesis.core.true_engine import get_true_engine
                engine = get_true_engine()
                engine.initialize_qubits(n_qubits)
                self._use_true_engine = True
                engine_name = "TrueSynthesisEngine (20 GB)"
            else:
                from synthesis.engine import get_synthesis_engine
                engine = get_synthesis_engine()
                engine.reset(n_qubits)
                self._use_true_engine = False
                engine_name = "SynthesisEngine (RAM)"
            return ToolResult(
                success=True,
                data={"n_qubits": n_qubits, "state": "|" + "0" * n_qubits + ">",
                      "engine": engine_name},
                summary=f"Initialized {n_qubits}-qubit register in |{'0'*n_qubits}> on {engine_name}.",
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
                    results.append(f"measure({shots}) -> {len(measure_results)} outcomes")

                elif targets:
                    target = targets[0]
                    ctrl = controls[0] if controls else None
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

    def _run_preset(self, preset: str = "bell", n_qubits: int = None, **kwargs) -> ToolResult:
        """
        Build and run a standard quantum circuit preset automatically.

        Presets:
          bell  — Bell state |Phi+> on 2 qubits: H(0) -> CNOT(0,1)
          ghz   — GHZ state on n_qubits (default 3): H(0) -> CNOT(0,1..n-1)
          qft   — Quantum Fourier Transform on n_qubits (default 3)

        Args:
            preset:   "bell", "ghz", or "qft"
            n_qubits: Number of qubits (bell ignores this, uses 2)
        """
        try:
            p = preset.lower().strip()

            if p == "bell":
                r = self._init_qubits(n_qubits=2)
                if not r.success:
                    return r
                engine = self._get_engine()
                engine.h(0)
                engine.cx(0, 1)
                return ToolResult(
                    success=True,
                    data={"preset": "bell", "n_qubits": 2,
                          "circuit": ["reset(2)", "h(0)", "cx(0,1)"]},
                    summary="Bell state prepared: H(0) -> CNOT(0,1). State: (|00>+|11>)/sqrt(2).",
                )

            elif p == "ghz":
                n = n_qubits if n_qubits and n_qubits >= 2 else 3
                r = self._init_qubits(n_qubits=n)
                if not r.success:
                    return r
                engine = self._get_engine()
                engine.h(0)
                steps = ["reset({})".format(n), "h(0)"]
                for i in range(1, n):
                    engine.cx(0, i)
                    steps.append(f"cx(0,{i})")
                return ToolResult(
                    success=True,
                    data={"preset": "ghz", "n_qubits": n, "circuit": steps},
                    summary=f"GHZ state prepared on {n} qubits. State: (|{'0'*n}>+|{'1'*n}>)/sqrt(2).",
                )

            elif p == "qft":
                import math
                n = n_qubits if n_qubits and n_qubits >= 1 else 3
                r = self._init_qubits(n_qubits=n)
                if not r.success:
                    return r
                engine = self._get_engine()
                steps = [f"reset({n})"]
                for i in range(n):
                    engine.h(i)
                    steps.append(f"h({i})")
                    for j in range(i + 1, n):
                        angle = math.pi / (2 ** (j - i))
                        engine.cp(j, i, angle)
                        steps.append(f"cp({j},{i},{angle:.4f})")
                # Bit reversal swaps
                for i in range(n // 2):
                    engine.swap(i, n - 1 - i)
                    steps.append(f"swap({i},{n-1-i})")
                return ToolResult(
                    success=True,
                    data={"preset": "qft", "n_qubits": n, "circuit": steps},
                    summary=f"QFT applied to {n}-qubit register ({len(steps)-1} gates).",
                )

            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown preset '{preset}'. Valid: bell, ghz, qft",
                )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

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
                    "engine":      "TrueSynthesisEngine" if self._use_true_engine else "SynthesisEngine",
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

    def _list_circuits(self, **kwargs) -> ToolResult:
        """List all saved circuits in the circuit library."""
        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            circuits = lib.list_circuits()
            return ToolResult(
                success=True,
                data={"circuits": circuits, "count": len(circuits)},
                summary=f"{len(circuits)} circuits in library."
                        + (f" Names: {', '.join(c['name'] for c in circuits[:10])}" if circuits else " Library is empty."),
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _synthesis_status(self, **kwargs) -> ToolResult:
        """Return synthesis engine status (safe read-only)."""
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            cmds = get_synthesis_commands()
            result = cmds.execute("status", [])
            return ToolResult(
                success=result.status.name in ("SUCCESS", "OK"),
                data=result.data,
                summary=result.message,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _true_engine_status(self, **kwargs) -> ToolResult:
        """Return 20 GB TrueSynthesisEngine storage and state info."""
        try:
            from synthesis.core.true_engine import get_true_engine
            engine = get_true_engine()
            usage = engine.get_storage_usage()
            status = engine.status()
            return ToolResult(
                success=True,
                data={"storage": usage, "status": status},
                summary=(
                    f"TrueSynthesisEngine: {status.get('n_qubits', 0)} qubits active. "
                    f"Storage: {usage.get('used_gb', 0):.2f} GB / {usage.get('total_gb', 20):.0f} GB. "
                    f"Saved states: {usage.get('state_count', 0)}."
                ),
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # ── Ring 2 Actions ──────────────────────────────────────────────────────────

    def _measure(self, shots: int = 1024, **kwargs) -> ToolResult:
        """
        Run measurement simulation, return counts, and auto-launch Bloch sphere.
        Permission already checked in execute() before dispatch.
        """
        try:
            engine = self._get_engine()
            if engine.get_num_qubits() == 0:
                return ToolResult(success=False, error="No state to measure. Call init_qubits first.")
            counts = engine.measure(int(shots))
            total = sum(counts.values())
            top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]

            # Auto-launch Bloch sphere (mirrors quantum_mode.py _cmd_measure behaviour)
            self._launch_bloch_for_measure(engine, int(shots), counts)

            return ToolResult(
                success=True,
                data={
                    "shots":  total,
                    "counts": counts,
                    "top_outcomes": [
                        {"state": s, "count": c, "probability": round(c / total, 4)}
                        for s, c in top
                    ],
                    "bloch_launched": True,
                },
                summary=(
                    f"Measured {total} shots. Top: |{top[0][0]}> {top[0][1]}x "
                    f"({top[0][1]/total*100:.1f}%). Bloch sphere launched."
                ) if top else "Measurement complete.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _launch_bloch_for_measure(self, engine, shots: int, counts: dict) -> None:
        """
        Internal helper: launch the multi-qubit Bloch sphere visualiser after a
        measurement.  Non-fatal — a visualiser error never blocks the measurement
        result.  Only runs for n_qubits <= 16 (browser visualiser limit).
        """
        try:
            n = engine.get_num_qubits()
            if n == 0 or n > 16:
                return
            total = sum(counts.values()) or 1
            experimental_probs = {k: v / total for k, v in counts.items()}
            from synthesis.quantum import get_visualizer
            visualizer = get_visualizer()
            visualizer.launch_multi_qubit_bloch(
                qubit_coords=engine.get_all_qubit_bloch_coords(),
                entanglement_info=engine.get_entanglement_info(),
                num_qubits=n,
                gate_count=len(getattr(engine, "_gate_log", [])),
                theoretical_probs=engine.get_probabilities(),
                experimental_probs=experimental_probs,
                marginal_probs=engine.get_marginal_probabilities(),
                shots=shots,
            )
        except Exception as e:
            logger.warning("Bloch auto-launch after measure failed (non-fatal): %s", e)

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

    def _save_circuit(self, name: str = "", description: str = "", **kwargs) -> ToolResult:
        """Save the current engine's gate log as a named circuit in the library."""
        if not name:
            return ToolResult(success=False, error="'name' parameter required")
        try:
            from synthesis.circuit_library import get_circuit_library, CircuitDefinition
            engine = self._get_engine()
            n = engine.get_num_qubits()
            gate_log = getattr(engine, "_gate_log", [])
            if not gate_log:
                return ToolResult(success=False, error="No gates applied yet. Build a circuit first.")
            lib = get_circuit_library()
            circ = CircuitDefinition(name=name, n_qubits=n, description=description)
            for entry in gate_log:
                # gate_log entries vary by engine; handle both dict and object forms
                if isinstance(entry, dict):
                    circ.gates.append(entry)
                else:
                    circ.gates.append({"gate": str(entry)})
            path = lib.save(circ)
            return ToolResult(
                success=True,
                data={"name": name, "n_qubits": n, "gates": len(circ.gates), "path": str(path)},
                summary=f"Circuit '{name}' saved ({len(circ.gates)} gates, {n} qubits).",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _delete_circuit(self, name: str = "", **kwargs) -> ToolResult:
        """Delete a named circuit from the library."""
        if not name:
            return ToolResult(success=False, error="'name' parameter required")
        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            success = lib.delete(name)
            if success:
                return ToolResult(
                    success=True,
                    data={"name": name},
                    summary=f"Circuit '{name}' deleted from library.",
                )
            return ToolResult(success=False, error=f"Circuit '{name}' not found in library.")
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

            run_result = self._run_circuit(circuit=circuit_def.gates)
            if not run_result.success:
                return run_result

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

        Schrodinger equation (c_ops=None): Uses qt.sesolve(H, psi0, tlist)
        Lindblad master equation (c_ops provided): Uses qt.mesolve(...)

        Args:
            H:     Hamiltonian as nested list (NxN complex matrix)
            psi0:  Initial state as flat list of complex amplitudes
            tlist: Time points as list of floats
            c_ops: Optional collapse operators for open systems
        """
        if H is None or psi0 is None or tlist is None:
            return ToolResult(
                success=False,
                error="Required: H (Hamiltonian), psi0 (initial state), tlist (time points)",
            )
        try:
            import qutip as qt
            import numpy as np

            H_arr = np.array(H, dtype=complex)
            dims = H_arr.shape[0]
            H_qobj = qt.Qobj(H_arr, dims=[[dims], [dims]])

            psi0_arr = np.array(psi0, dtype=complex).reshape(dims, 1)
            psi0_qobj = qt.Qobj(psi0_arr, dims=[[dims], [1]])

            t_arr = list(tlist)

            if c_ops:
                c_ops_qobj = [qt.Qobj(np.array(c, dtype=complex)) for c in c_ops]
                result = qt.mesolve(H_qobj, psi0_qobj * psi0_qobj.dag(), t_arr, c_ops_qobj, [])
                final_state = result.states[-1] if result.states else None
                mode = "mesolve (Lindblad)"
                final_data = final_state.full().tolist() if final_state else None
            else:
                result = qt.sesolve(H_qobj, psi0_qobj, t_arr)
                final_state = result.states[-1] if result.states else None
                mode = "sesolve (Schrodinger)"
                final_data = final_state.full().flatten().tolist() if final_state else None

            return ToolResult(
                success=True,
                data={
                    "mode":        mode,
                    "time_steps":  len(t_arr),
                    "t_start":     t_arr[0],
                    "t_end":       t_arr[-1],
                    "hilbert_dim": dims,
                    "final_state": final_data,
                    "n_states":    len(result.states),
                },
                summary=(
                    f"QuTiP {mode}: {dims}D Hilbert space, "
                    f"{len(t_arr)} time steps [{t_arr[0]:.2f}->{t_arr[-1]:.2f}]."
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

    # ── Synthesis Engine Actions ────────────────────────────────────────────────

    def _synthesis_run(self, preset: str = "gaussian", **kwargs) -> ToolResult:
        """
        Run a synthesis physics simulation preset.

        Presets: gaussian, tunneling, harmonic, relativistic
        Optional kwargs forwarded as CLI args (velocity, points, time).
        """
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            cmds = get_synthesis_commands()
            args = [preset]
            for key in ("velocity", "points", "time"):
                if key in kwargs:
                    args += [f"--{key}", str(kwargs[key])]
            result = cmds.execute("run", args)
            return ToolResult(
                success=result.status.name in ("SUCCESS", "OK"),
                data=result.data,
                summary=result.message,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _synthesis_bloch(self, sim_type: str = "rabi", omega: float = None,
                         gamma: float = None, **kwargs) -> ToolResult:
        """
        Launch a synthesis 3D Bloch sphere popup.

        sim_type: rabi | precession | spiral | hadamard
        omega:    optional frequency override
        gamma:    optional Lorentz gamma factor
        """
        try:
            from synthesis.bloch_sphere_popup import launch_bloch_sphere
            extra = {}
            if omega is not None:
                extra["omega"] = omega
            if gamma is not None:
                extra["lorentz_gamma"] = gamma
            success = launch_bloch_sphere(sim_type, **extra)
            return ToolResult(
                success=success,
                data={"sim_type": sim_type, "launched": success},
                summary=f"Synthesis Bloch sphere launched: {sim_type}."
                        if success else f"Failed to launch synthesis Bloch sphere: {sim_type}.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _synthesis_gaussian(self, sigma: float = 1.0, k0: float = 0.0, **kwargs) -> ToolResult:
        """Run Gaussian wave packet simulation."""
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            cmds = get_synthesis_commands()
            result = cmds.execute("gaussian", [str(sigma), str(k0)])
            return ToolResult(
                success=result.status.name in ("SUCCESS", "OK"),
                data=result.data,
                summary=result.message,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _synthesis_tunneling(self, barrier: float = 1.0, **kwargs) -> ToolResult:
        """Run quantum tunneling simulation."""
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            cmds = get_synthesis_commands()
            result = cmds.execute("tunneling", [str(barrier)])
            return ToolResult(
                success=result.status.name in ("SUCCESS", "OK"),
                data=result.data,
                summary=result.message,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _synthesis_harmonic(self, omega: float = 1.0, **kwargs) -> ToolResult:
        """Run harmonic oscillator simulation."""
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            cmds = get_synthesis_commands()
            result = cmds.execute("harmonic", [str(omega)])
            return ToolResult(
                success=result.status.name in ("SUCCESS", "OK"),
                data=result.data,
                summary=result.message,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _synthesis_lorentz(self, velocity: float = 0.5, **kwargs) -> ToolResult:
        """
        Apply a Lorentz boost to the synthesis engine.

        Args:
            velocity: Fraction of speed of light (strictly 0.0 < velocity < 1.0;
                      v=0 produces no boost, v=1 is physically undefined)
        """
        if not (0.0 < velocity < 1.0):
            return ToolResult(success=False, error="velocity must be strictly between 0.0 and 1.0 (v=0 is no-op; v=1 is undefined)")
        try:
            from synthesis.terminal_commands import get_synthesis_commands
            cmds = get_synthesis_commands()
            result = cmds.execute("lorentz", [str(velocity)])
            return ToolResult(
                success=result.status.name in ("SUCCESS", "OK"),
                data=result.data,
                summary=result.message,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
