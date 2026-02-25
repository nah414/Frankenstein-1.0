"""
agents/sauron/orchestrator.py
------------------------------
Day 6: Sub-Agent Coordinator for Eye of Sauron.
Day 6 patch: TrueSynthesisEngine (20GB storage) wired as "true_synthesis" agent.

The SauronOrchestrator sits between the Sauron tool layer and the existing
FRANKENSTEIN agent ecosystem (agents/registry.py).  It provides:

  • Agent discovery   — list all registered agents with status
  • Single dispatch   — run one agent action and return a structured result
  • Multi dispatch    — run several agent calls concurrently (fan-out / fan-in)
  • Synthesis bridge  — SynthesisEngine (16-qubit, RAM-only, fast)
  • TrueSynthesis     — TrueSynthesisEngine (18-qubit, 20GB disk allocation,
                        memory-mapped states, Schrödinger solver, persist/load)

Two synthesis engines, two dispatch targets
───────────────────────────────────────────
  "synthesis"       → synthesis/engine.py :: SynthesisEngine
                      Fast in-RAM ops, terminal quantum mode, 16 qubits max.
                      Actions: status, reset, compute, get_state, schrodinger

  "true_synthesis"  → synthesis/core/true_engine.py :: TrueSynthesisEngine
                      20GB disk-backed, 18 qubits, mmap for large states,
                      full Schrödinger solver, save/load/list quantum states.
                      Actions: status, storage, list_states, save_state,
                               load_state, delete_state, initialize, measure,
                               state_info, bell_state, ghz_state, schrodinger

Thread safety
─────────────
All dispatches honour SAFETY.MAX_WORKER_THREADS (3).  The ThreadPoolExecutor
uses min(requested, MAX_WORKER_THREADS) workers so concurrent multi-dispatch
never exceeds the hard cap.

Lazy loading
────────────
All engine imports live inside methods — never at class/module level.
Importing this file has zero startup cost.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.safety import SAFETY

logger = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class AgentInfo:
    """Metadata snapshot for a single registered agent."""
    name: str
    description: str
    available: bool = True
    error: Optional[str] = None


@dataclass
class DispatchResult:
    """Result of a single agent dispatch."""
    agent_name: str
    action: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "action": self.action,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": round(self.execution_time * 1000, 1),
        }


@dataclass
class MultiDispatchResult:
    """Aggregated results from a fan-out multi-agent call."""
    results: List[DispatchResult] = field(default_factory=list)
    total_time: float = 0.0
    all_success: bool = True

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "total_time_ms": round(self.total_time * 1000, 1),
            "all_success": self.all_success,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


# ── Orchestrator ───────────────────────────────────────────────────────────────

class SauronOrchestrator:
    """
    Central sub-agent coordinator for the Eye of Sauron.

    Usage
    ─────
        orchestrator = SauronOrchestrator()

        # Discover what's available
        agents = orchestrator.discover()

        # Single call
        result = orchestrator.dispatch("hardware", "status")

        # Parallel fan-out
        calls = [
            {"agent": "hardware", "action": "status"},
            {"agent": "security", "action": "threats"},
        ]
        multi = orchestrator.multi_dispatch(calls)
    """

    # Logical agent names for the two synthesis engines (neither is in AgentRegistry)
    SYNTHESIS_AGENT_NAME      = "synthesis"       # synthesis/engine.py  (fast, RAM-only)
    TRUE_SYNTHESIS_AGENT_NAME = "true_synthesis"  # synthesis/core/true_engine.py (20GB disk)

    def __init__(self):
        # Max concurrent workers capped at SAFETY hard limit
        self._max_workers: int = min(SAFETY.MAX_WORKER_THREADS, 3)
        logger.debug(
            "SauronOrchestrator initialised (max_workers=%d)", self._max_workers
        )

    # ── Discovery ──────────────────────────────────────────────────────────────

    def discover(self) -> List[AgentInfo]:
        """
        Return metadata for every available agent.

        Combines agents from AgentRegistry with the special-cased synthesis
        engine.  Never instantiates any agent.
        """
        infos: List[AgentInfo] = []

        # ── Registry agents ──
        try:
            from agents.registry import get_registry
            registry = get_registry()
            for entry in registry.list_agents():
                infos.append(AgentInfo(
                    name=entry["name"],
                    description=entry.get("description", ""),
                    available=True,
                ))
        except Exception as exc:
            logger.warning("Could not query AgentRegistry: %s", exc)

        # ── SynthesisEngine (fast, RAM-only) ──
        try:
            from synthesis.engine import get_synthesis_engine  # noqa: F401
            infos.append(AgentInfo(
                name=self.SYNTHESIS_AGENT_NAME,
                description=(
                    "Fast in-RAM quantum simulation (SynthesisEngine, 16 qubits). "
                    "Actions: status, reset, compute, get_state, schrodinger"
                ),
                available=True,
            ))
        except Exception as exc:
            infos.append(AgentInfo(
                name=self.SYNTHESIS_AGENT_NAME,
                description="SynthesisEngine (unavailable)",
                available=False,
                error=str(exc),
            ))

        # ── TrueSynthesisEngine (18-qubit, 20GB disk allocation) ──
        try:
            from synthesis.core.true_engine import get_true_engine  # noqa: F401
            infos.append(AgentInfo(
                name=self.TRUE_SYNTHESIS_AGENT_NAME,
                description=(
                    "Disk-backed quantum simulation (TrueSynthesisEngine, 18 qubits, 20GB storage). "
                    "Actions: status, storage, list_states, save_state, load_state, "
                    "delete_state, initialize, measure, state_info, "
                    "bell_state, ghz_state, schrodinger"
                ),
                available=True,
            ))
        except Exception as exc:
            infos.append(AgentInfo(
                name=self.TRUE_SYNTHESIS_AGENT_NAME,
                description="TrueSynthesisEngine (unavailable)",
                available=False,
                error=str(exc),
            ))

        return infos

    def agent_names(self) -> List[str]:
        """Return list of all available agent names."""
        return [a.name for a in self.discover() if a.available]

    def has_agent(self, name: str) -> bool:
        """Check whether an agent with this name is available."""
        return name in self.agent_names()

    # ── Single dispatch ────────────────────────────────────────────────────────

    def dispatch(
        self,
        agent_name: str,
        action: str = "status",
        **kwargs: Any,
    ) -> DispatchResult:
        """
        Run a single agent action synchronously.

        Routes synthesis calls to the SynthesisEngine singleton; all other
        calls go through the AgentRegistry.

        Returns a DispatchResult — never raises.
        """
        start = time.time()

        try:
            if agent_name == self.SYNTHESIS_AGENT_NAME:
                data = self._dispatch_synthesis(action, **kwargs)
            elif agent_name == self.TRUE_SYNTHESIS_AGENT_NAME:
                data = self._dispatch_true_synthesis(action, **kwargs)
            else:
                data = self._dispatch_registry_agent(agent_name, action, **kwargs)

            return DispatchResult(
                agent_name=agent_name,
                action=action,
                success=True,
                data=data,
                execution_time=time.time() - start,
            )

        except Exception as exc:
            logger.exception(
                "Orchestrator dispatch failed: agent=%s action=%s", agent_name, action
            )
            return DispatchResult(
                agent_name=agent_name,
                action=action,
                success=False,
                error=str(exc),
                execution_time=time.time() - start,
            )

    # ── Multi dispatch (fan-out / fan-in) ──────────────────────────────────────

    def multi_dispatch(
        self,
        calls: List[Dict[str, Any]],
    ) -> MultiDispatchResult:
        """
        Execute multiple agent calls concurrently, then aggregate results.

        Each call dict must have keys:
            agent  (str)           — agent name
            action (str, optional) — defaults to "status"
            **kwargs               — forwarded to agent execute()

        Workers are capped at SAFETY.MAX_WORKER_THREADS to protect
        the i3's 4-core budget.

        Returns MultiDispatchResult — never raises.
        """
        if not calls:
            return MultiDispatchResult()

        start = time.time()
        workers = min(len(calls), self._max_workers)
        results: List[DispatchResult] = []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {}
            for call in calls:
                agent_name = call.get("agent", "")
                action = call.get("action", "status")
                extra = {k: v for k, v in call.items() if k not in ("agent", "action")}
                future = pool.submit(self.dispatch, agent_name, action, **extra)
                future_map[future] = (agent_name, action)

            for future in as_completed(future_map):
                try:
                    results.append(future.result())
                except Exception as exc:
                    agent_name, action = future_map[future]
                    results.append(DispatchResult(
                        agent_name=agent_name,
                        action=action,
                        success=False,
                        error=f"Future raised: {exc}",
                        execution_time=0.0,
                    ))

        total = time.time() - start
        all_ok = all(r.success for r in results)

        return MultiDispatchResult(
            results=results,
            total_time=total,
            all_success=all_ok,
        )

    # ── Internal routing ───────────────────────────────────────────────────────

    def _dispatch_registry_agent(
        self, agent_name: str, action: str, **kwargs: Any
    ) -> Any:
        """Delegate to a BaseAgent via AgentRegistry."""
        from agents.registry import get_registry

        registry = get_registry()
        agent = registry.get(agent_name)
        if agent is None:
            raise ValueError(
                f"Agent '{agent_name}' not found in registry. "
                f"Available: {[a['name'] for a in registry.list_agents()]}"
            )

        result = agent.execute(action=action, **kwargs)

        if not result.success:
            raise RuntimeError(result.error or "Agent returned failure")

        return result.data

    def _dispatch_synthesis(self, action: str, **kwargs: Any) -> Any:
        """
        Delegate to the SynthesisEngine singleton.

        Supported actions:
          status    — engine metadata (qubits, gate_count, backends)
          reset     — reset(num_qubits) — kwargs: num_qubits (int, default 1)
          compute   — run compute() and return result dict
                      kwargs: shots (int, default 1024)
          schrodinger — evolve_schrodinger stub (returns capability info)
          get_state — get_state() → real/imag arrays
        """
        from synthesis.engine import get_synthesis_engine, ComputeMode

        engine = get_synthesis_engine()

        if action == "status":
            return {
                "num_qubits": engine.get_num_qubits(),
                "gate_count": engine.get_gate_count(),
                "max_qubits_statevector": engine.MAX_QUBITS_STATEVECTOR,
                "max_qubits_density": engine.MAX_QUBITS_DENSITY,
                "auto_visualize": engine.auto_visualize,
                "result_history_len": len(engine.get_result_history()),
            }

        elif action == "reset":
            num_qubits = int(kwargs.get("num_qubits", 1))
            engine.reset(num_qubits)
            return {"reset": True, "num_qubits": num_qubits}

        elif action == "compute":
            shots = int(kwargs.get("shots", 1024))
            result = engine.compute(
                mode=ComputeMode.STATEVECTOR,
                shots=shots,
                visualize=False,  # No browser popup from agent calls
            )
            return result.to_dict()

        elif action == "get_state":
            state = engine.get_state()
            if state is None:
                return {"state": None}
            return {
                "real": state.real.tolist(),
                "imag": state.imag.tolist(),
                "num_qubits": engine.get_num_qubits(),
            }

        elif action == "schrodinger":
            # Return capability summary — full evolution requires a Hamiltonian
            # which is too heavy to pass via NL. Let the user know.
            return {
                "available": True,
                "description": (
                    "Schrödinger equation solver (evolve_schrodinger). "
                    "Requires a Hamiltonian matrix. "
                    "Use synthesis terminal commands for full control."
                ),
            }

        else:
            raise ValueError(
                f"Unknown synthesis action '{action}'. "
                "Valid: status, reset, compute, get_state, schrodinger"
            )

    def _dispatch_true_synthesis(self, action: str, **kwargs: Any) -> Any:
        """
        Delegate to the TrueSynthesisEngine singleton (20GB disk allocation).

        Storage path: ~/.frankenstein/synthesis_data/
          states/   — saved quantum states (.npz)
          results/  — saved simulation results
          cache/    — temporary mmap files for states >100MB

        Supported actions
        ─────────────────
          status        — Engine status + storage summary
          storage       — Full 20GB storage usage breakdown
          list_states   — All saved quantum states with metadata
          save_state    — Save current state; kwargs: name (str)
          load_state    — Load saved state into engine; kwargs: name (str)
          delete_state  — Delete a saved state; kwargs: name (str)
          initialize    — Initialize qubit register;
                          kwargs: n_qubits (int, default 2),
                                  initial_state (str, default "zero")
                          initial_state options: "zero","one","plus","minus",
                                                 or binary string e.g. "0101"
          measure       — Measure with Born-rule sampling;
                          kwargs: shots (int, default 1024),
                                  collapse (bool, default True)
          state_info    — Non-zero amplitudes + probabilities for current state
          bell_state    — Create Bell state;
                          kwargs: pair_type (str, default "phi_plus")
                          pair_type options: phi_plus, phi_minus, psi_plus, psi_minus
          ghz_state     — Create GHZ state;
                          kwargs: n_qubits (int, default 3)
          schrodinger   — Capability description (full solver available via terminal)
        """
        from synthesis.core.true_engine import get_true_engine

        engine = get_true_engine()

        if action == "status":
            return engine.status()

        elif action == "storage":
            usage = engine.get_storage_usage()
            allocated_gb = usage["allocated_bytes"] / 1e9
            used_gb      = usage["used_bytes"] / 1e9
            available_gb = usage["available_bytes"] / 1e9
            return {
                **usage,
                "allocated_gb":  round(allocated_gb, 3),
                "used_gb":       round(used_gb, 6),
                "available_gb":  round(available_gb, 3),
                "used_percent":  round(usage["used_percent"], 4),
            }

        elif action == "list_states":
            return {
                "states": engine.list_states(),
                "storage_path": str(engine.config.storage_path / "states"),
            }

        elif action == "save_state":
            name = kwargs.get("name")
            if not name:
                raise ValueError("save_state requires kwarg: name (str)")
            filepath = engine.save_state(str(name))
            return {"saved": True, "name": name, "path": str(filepath)}

        elif action == "load_state":
            name = kwargs.get("name")
            if not name:
                raise ValueError("load_state requires kwarg: name (str)")
            state = engine.load_state(str(name))
            return {
                "loaded": True,
                "name": name,
                "n_qubits": state.n_qubits,
                "dimension": state.dim,
                "memory_bytes": state.memory_required,
            }

        elif action == "delete_state":
            name = kwargs.get("name")
            if not name:
                raise ValueError("delete_state requires kwarg: name (str)")
            deleted = engine.delete_state(str(name))
            return {"deleted": deleted, "name": name}

        elif action == "initialize":
            n_qubits      = int(kwargs.get("n_qubits", 2))
            initial_state = str(kwargs.get("initial_state", "zero"))
            state = engine.initialize_qubits(n_qubits, initial_state)
            return {
                "initialized": True,
                "n_qubits": n_qubits,
                "initial_state": initial_state,
                "dimension": state.dim,
                "memory_bytes": state.memory_required,
                "memory_mb": round(state.memory_required / 1e6, 3),
            }

        elif action == "measure":
            shots    = int(kwargs.get("shots", 1024))
            collapse = bool(kwargs.get("collapse", True))
            return engine.measure(shots=shots, collapse=collapse)

        elif action == "state_info":
            return engine.get_state_info()

        elif action == "bell_state":
            pair_type = str(kwargs.get("pair_type", "phi_plus"))
            amplitudes = engine.create_bell_state(pair_type)
            return {
                "bell_state": pair_type,
                "n_qubits": 2,
                "amplitudes_real": amplitudes.real.tolist(),
                "amplitudes_imag": amplitudes.imag.tolist(),
            }

        elif action == "ghz_state":
            n_qubits = int(kwargs.get("n_qubits", 3))
            amplitudes = engine.create_ghz_state(n_qubits)
            return {
                "ghz_state": True,
                "n_qubits": n_qubits,
                "dimension": len(amplitudes),
                "amplitudes_real": amplitudes.real.tolist(),
                "amplitudes_imag": amplitudes.imag.tolist(),
            }

        elif action == "schrodinger":
            return {
                "available": True,
                "engine": "TrueSynthesisEngine",
                "method": "matrix_exponentiation + eigendecomposition",
                "max_qubits": engine.config.max_qubits,
                "max_time_steps": engine.config.max_time_steps,
                "storage_backed": True,
                "description": (
                    "Full Schrödinger solver (iℏ∂ψ/∂t = Ĥψ) via matrix exponentiation. "
                    "Requires a Hermitian Hamiltonian matrix — construct via terminal "
                    "quantum commands for full interactive control."
                ),
            }

        else:
            raise ValueError(
                f"Unknown true_synthesis action '{action}'. "
                "Valid: status, storage, list_states, save_state, load_state, "
                "delete_state, initialize, measure, state_info, "
                "bell_state, ghz_state, schrodinger"
            )


# ── Module-level singleton ─────────────────────────────────────────────────────

_orchestrator: Optional[SauronOrchestrator] = None


def get_orchestrator() -> SauronOrchestrator:
    """Lazy-loaded singleton accessor."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SauronOrchestrator()
    return _orchestrator
