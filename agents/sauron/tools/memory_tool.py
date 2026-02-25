"""
FRANKENSTEIN 1.0 - Eye of Sauron: Memory Tool
Phase 4 / Day 2

Gives Sauron read access to saved quantum states, circuits, and session history
from the existing Frankenstein memory system.

All operations are Ring 3 (SAFE) — read-only, no side effects.

Storage locations read:
  ~/.frankenstein/synthesis_data/states/*.npz       (quantum states)
  ~/.frankenstein/synthesis_data/circuits/*.json    (circuit definitions)
  ~/.frankenstein/session.json                      (current session)
  ~/.frankenstein/history/tasks.json                (task history)

APIs used (do NOT duplicate):
  synthesis.core.true_engine.get_true_engine()  → list_states(), load_state()
  synthesis.circuit_library.get_circuit_library() → list_circuits(), load()
  core.memory.MemorySystem                        → session state
"""

import logging
from typing import Optional

from agents.sauron.permissions import PermissionLevel
from agents.sauron.audit import get_sauron_audit
from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class MemoryTool(BaseTool):
    """
    Read-only access to Frankenstein's saved quantum states, circuits, and session.

    All sub-operations are Ring 3 (free — no permission prompt needed).
    """

    name = "memory"
    description = (
        "Read saved quantum states and circuit definitions from Frankenstein memory. "
        "Supports: list_states, load_state, list_circuits, load_circuit, session_summary. "
        "All read-only (Ring 3 — no approval needed)."
    )
    permission_level = PermissionLevel.SAFE

    def execute(self, action: str = "list_states", name: str = "", **kwargs) -> ToolResult:
        """
        Dispatch to sub-operation.

        Args:
            action: One of: list_states | load_state | list_circuits |
                            load_circuit | session_summary
            name:   Required for load_state and load_circuit
        """
        dispatch = {
            "list_states":     self._list_states,
            "load_state":      lambda: self._load_state(name),
            "list_circuits":   self._list_circuits,
            "load_circuit":    lambda: self._load_circuit(name),
            "session_summary": self._session_summary,
        }

        if action not in dispatch:
            return ToolResult(
                success=False,
                error=(
                    f"Unknown memory action '{action}'. "
                    f"Valid: {list(dispatch.keys())}"
                ),
            )

        if action in ("load_state", "load_circuit") and not name:
            return ToolResult(
                success=False,
                error=f"'name' parameter required for action '{action}'",
            )

        return dispatch[action]()

    # ── States ─────────────────────────────────────────────────────────────────

    def _list_states(self) -> ToolResult:
        """List all saved quantum states with metadata."""
        try:
            from synthesis.core.true_engine import get_true_engine
            engine = get_true_engine()
            states = engine.list_states()

            get_sauron_audit().log_memory_read("states_list", "all")

            if not states:
                return ToolResult(
                    success=True,
                    data=[],
                    summary="No saved quantum states found.",
                )

            # Format for LLM readability
            formatted = []
            for s in states:
                if "error" in s:
                    formatted.append({"name": s["name"], "status": "corrupt"})
                else:
                    formatted.append({
                        "name":     s["name"],
                        "n_qubits": s["n_qubits"],
                        "size_kb":  s["size_kb"],
                        "modified": s["modified"],
                    })

            return ToolResult(
                success=True,
                data=formatted,
                summary=f"{len(formatted)} saved quantum state(s) found.",
            )
        except Exception as e:
            logger.error("list_states error: %s", e)
            return ToolResult(success=False, error=str(e))

    def _load_state(self, name: str) -> ToolResult:
        """Load a named quantum state and return its metadata + gate log summary."""
        try:
            from synthesis.core.true_engine import get_true_engine
            import numpy as np

            engine = get_true_engine()
            state = engine.load_state(name)  # loads into engine's active state

            get_sauron_audit().log_memory_read("quantum_state", name)

            # Build a human-readable summary instead of returning raw numpy
            n_qubits = state.n_qubits
            amplitudes = state.amplitudes
            probs = (abs(amplitudes) ** 2).real
            top_states = sorted(
                [(format(i, f"0{n_qubits}b"), float(p)) for i, p in enumerate(probs)],
                key=lambda x: -x[1],
            )[:8]  # Top 8 most probable basis states

            gate_log = getattr(engine, "_gate_log", [])
            gate_summary = (
                f"{len(gate_log)} gates: "
                + ", ".join(g.get("gate", "?") for g in gate_log[-5:])
                if gate_log else "No gates recorded"
            )

            return ToolResult(
                success=True,
                data={
                    "name":        name,
                    "n_qubits":    n_qubits,
                    "state_loaded": True,
                    "gate_log_summary": gate_summary,
                    "top_probabilities": top_states,
                    "note": "State is now loaded as the active quantum state.",
                },
                summary=f"Loaded state '{name}' ({n_qubits} qubits). {gate_summary}.",
            )
        except FileNotFoundError:
            return ToolResult(success=False, error=f"State '{name}' not found.")
        except Exception as e:
            logger.error("load_state('%s') error: %s", name, e)
            return ToolResult(success=False, error=str(e))

    # ── Circuits ───────────────────────────────────────────────────────────────

    def _list_circuits(self) -> ToolResult:
        """List all saved circuit definitions."""
        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            circuits = lib.list_circuits()

            get_sauron_audit().log_memory_read("circuits_list", "all")

            if not circuits:
                return ToolResult(
                    success=True,
                    data=[],
                    summary="No saved circuits found in the circuit library.",
                )

            formatted = [
                {
                    "name":        c["name"],
                    "n_qubits":    c["n_qubits"],
                    "gate_count":  c["gates"],
                    "description": c["description"][:80],
                    "modified":    c["modified"],
                    "tags":        c.get("tags", []),
                }
                for c in circuits
            ]

            return ToolResult(
                success=True,
                data=formatted,
                summary=f"{len(formatted)} saved circuit(s) found.",
            )
        except Exception as e:
            logger.error("list_circuits error: %s", e)
            return ToolResult(success=False, error=str(e))

    def _load_circuit(self, name: str) -> ToolResult:
        """
        Load a named circuit definition. Returns gates list + OpenQASM 2.0 string.
        The OpenQASM string lets Sauron use the circuit with Qiskit directly.
        """
        try:
            from synthesis.circuit_library import get_circuit_library
            lib = get_circuit_library()
            circuit = lib.load(name)

            if circuit is None:
                return ToolResult(success=False, error=f"Circuit '{name}' not found.")

            get_sauron_audit().log_memory_read("circuit", name)

            return ToolResult(
                success=True,
                data={
                    "name":        circuit.name,
                    "n_qubits":    circuit.n_qubits,
                    "description": circuit.description,
                    "gates":       circuit.gates,
                    "gate_count":  len(circuit.gates),
                    "tags":        circuit.tags,
                    "openqasm2":   circuit.to_openqasm2(),
                },
                summary=(
                    f"Loaded circuit '{name}': {circuit.n_qubits} qubits, "
                    f"{len(circuit.gates)} gates."
                ),
            )
        except Exception as e:
            logger.error("load_circuit('%s') error: %s", name, e)
            return ToolResult(success=False, error=str(e))

    # ── Session ────────────────────────────────────────────────────────────────

    def _session_summary(self) -> ToolResult:
        """Return a summary of the current Frankenstein session."""
        try:
            from core.memory import MemorySystem
            mem = MemorySystem()
            mem.initialize()

            session = mem._session
            if session is None:
                return ToolResult(success=False, error="No active session found.")

            import time
            uptime_sec = time.time() - session.started_at
            uptime_min = int(uptime_sec // 60)

            # Recent task types from history
            recent_types = list({
                t.task_type for t in mem._task_history[-20:]
            }) if mem._task_history else []

            return ToolResult(
                success=True,
                data={
                    "session_id":      session.session_id,
                    "task_count":      session.task_count,
                    "successful":      session.successful_tasks,
                    "failed":          session.failed_tasks,
                    "uptime_minutes":  uptime_min,
                    "recent_task_types": recent_types,
                },
                summary=(
                    f"Session active {uptime_min}min. "
                    f"{session.task_count} tasks ({session.successful_tasks} ok, "
                    f"{session.failed_tasks} failed)."
                ),
            )
        except Exception as e:
            logger.error("session_summary error: %s", e)
            return ToolResult(success=False, error=str(e))
