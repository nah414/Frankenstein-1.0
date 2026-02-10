#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Dynamics Agent
Phase 3.5: Lazy-loaded wrapper for QuTiP toolset

Provides quantum system evolution, master equation solving,
decoherence modeling, and open quantum system simulations.
"""

from typing import Any, Dict, List, Optional

from ..base import BaseAgent, AgentResult


class QuantumDynamicsAgent(BaseAgent):
    """
    Agent for quantum system evolution using QuTiP.

    Capabilities:
    - Schrodinger equation solving (sesolve)
    - Lindblad master equation solving (mesolve)
    - Monte Carlo quantum trajectories (mcsolve)
    - Steady-state computation
    - Decoherence modeling via collapse operators
    - Quantum entropy measures
    """

    name = "quantum_dynamics"
    description = "Quantum system evolution with decoherence (QuTiP)"
    version = "1.0.0"
    requires_network = False
    requires_filesystem = False
    max_execution_time = 120  # quantum solvers can be slow

    def __init__(self):
        super().__init__()
        self._qutip = None

    def _ensure_loaded(self):
        """Lazy-load QuTiP only when a method is actually called."""
        if self._qutip is None:
            from libs.local_toolsets import load_qutip
            self._qutip = load_qutip()
            if self._qutip is None:
                raise RuntimeError(
                    "Failed to load QuTiP — insufficient RAM or not installed"
                )

    def execute(self, operation: str = "", **kwargs) -> AgentResult:
        """
        Dispatch to the requested quantum dynamics operation.

        Args:
            operation: One of 'mesolve', 'sesolve', 'mcsolve',
                       'steadystate', 'entropy', 'decoherence'
            **kwargs: Operation-specific parameters
        """
        if not operation:
            return AgentResult(
                success=False,
                error="No operation specified. Available: mesolve, sesolve, "
                      "mcsolve, steadystate, entropy, decoherence",
            )

        dispatch = {
            "mesolve": self._run_mesolve,
            "sesolve": self._run_sesolve,
            "mcsolve": self._run_mcsolve,
            "steadystate": self._run_steadystate,
            "entropy": self._run_entropy,
            "decoherence": self._run_decoherence,
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

    # ── Master equation (Lindblad) ───────────────────────────────────────

    def _run_mesolve(
        self,
        hamiltonian=None,
        rho0=None,
        tlist=None,
        c_ops: Optional[List] = None,
        e_ops: Optional[List] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Solve the Lindblad master equation for an open quantum system.

        Args:
            hamiltonian: Qobj Hamiltonian (or list for time-dependent)
            rho0: Initial state (ket or density matrix)
            tlist: Array of time points
            c_ops: List of collapse operators (decoherence channels)
            e_ops: List of expectation-value operators
        """
        qt = self._qutip
        if hamiltonian is None or rho0 is None or tlist is None:
            return AgentResult(
                success=False,
                error="mesolve requires hamiltonian, rho0, and tlist",
            )

        result = qt.mesolve(
            hamiltonian, rho0, tlist,
            c_ops=c_ops or [],
            e_ops=e_ops or [],
        )
        return AgentResult(
            success=True,
            data={
                "states": result.states if not e_ops else None,
                "expect": result.expect if e_ops else None,
                "num_collapse": result.num_collapse
                    if hasattr(result, "num_collapse") else None,
                "solver": "mesolve",
                "times": list(tlist),
            },
        )

    # ── Schrodinger equation (closed system) ─────────────────────────────

    def _run_sesolve(
        self,
        hamiltonian=None,
        psi0=None,
        tlist=None,
        e_ops: Optional[List] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Solve the Schrodinger equation for a closed quantum system.

        Args:
            hamiltonian: Qobj Hamiltonian
            psi0: Initial ket state
            tlist: Array of time points
            e_ops: List of expectation-value operators
        """
        qt = self._qutip
        if hamiltonian is None or psi0 is None or tlist is None:
            return AgentResult(
                success=False,
                error="sesolve requires hamiltonian, psi0, and tlist",
            )

        result = qt.sesolve(
            hamiltonian, psi0, tlist,
            e_ops=e_ops or [],
        )
        return AgentResult(
            success=True,
            data={
                "states": result.states if not e_ops else None,
                "expect": result.expect if e_ops else None,
                "solver": "sesolve",
                "times": list(tlist),
            },
        )

    # ── Monte Carlo trajectories ─────────────────────────────────────────

    def _run_mcsolve(
        self,
        hamiltonian=None,
        psi0=None,
        tlist=None,
        c_ops: Optional[List] = None,
        e_ops: Optional[List] = None,
        ntraj: int = 100,
        **kwargs,
    ) -> AgentResult:
        """
        Solve via Monte Carlo quantum trajectories.

        Args:
            hamiltonian: Qobj Hamiltonian
            psi0: Initial ket state
            tlist: Array of time points
            c_ops: List of collapse operators
            e_ops: List of expectation-value operators
            ntraj: Number of trajectories (default 100)
        """
        qt = self._qutip
        if hamiltonian is None or psi0 is None or tlist is None:
            return AgentResult(
                success=False,
                error="mcsolve requires hamiltonian, psi0, and tlist",
            )

        result = qt.mcsolve(
            hamiltonian, psi0, tlist,
            c_ops=c_ops or [],
            e_ops=e_ops or [],
            ntraj=ntraj,
        )
        return AgentResult(
            success=True,
            data={
                "expect": result.expect if e_ops else None,
                "num_trajectories": ntraj,
                "solver": "mcsolve",
                "times": list(tlist),
            },
        )

    # ── Steady state ─────────────────────────────────────────────────────

    def _run_steadystate(
        self,
        hamiltonian=None,
        c_ops: Optional[List] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Compute the steady-state density matrix.

        Args:
            hamiltonian: Qobj Hamiltonian
            c_ops: List of collapse operators
        """
        qt = self._qutip
        if hamiltonian is None or not c_ops:
            return AgentResult(
                success=False,
                error="steadystate requires hamiltonian and c_ops",
            )

        rho_ss = qt.steadystate(hamiltonian, c_ops)
        return AgentResult(
            success=True,
            data={
                "steady_state": rho_ss,
                "purity": (rho_ss * rho_ss).tr().real,
                "solver": "steadystate",
            },
        )

    # ── Quantum entropy ──────────────────────────────────────────────────

    def _run_entropy(
        self,
        state=None,
        measure: str = "von_neumann",
        **kwargs,
    ) -> AgentResult:
        """
        Compute quantum entropy of a state.

        Args:
            state: Qobj density matrix or ket
            measure: 'von_neumann' or 'linear'
        """
        qt = self._qutip
        if state is None:
            return AgentResult(success=False, error="entropy requires a state")

        if measure == "von_neumann":
            value = qt.entropy_vn(state)
        elif measure == "linear":
            value = qt.entropy_linear(state)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown entropy measure: {measure!r}. Use 'von_neumann' or 'linear'.",
            )

        return AgentResult(
            success=True,
            data={"entropy": value, "measure": measure},
        )

    # ── Decoherence modeling ─────────────────────────────────────────────

    def _run_decoherence(
        self,
        state=None,
        gamma: float = 0.1,
        tlist=None,
        decoherence_type: str = "amplitude_damping",
        **kwargs,
    ) -> AgentResult:
        """
        Model decoherence effects on a quantum state.

        Args:
            state: Initial Qobj ket state
            gamma: Decoherence rate
            tlist: Array of time points
            decoherence_type: 'amplitude_damping', 'dephasing', or 'depolarizing'
        """
        qt = self._qutip
        import numpy as np

        if state is None or tlist is None:
            return AgentResult(
                success=False,
                error="decoherence requires state and tlist",
            )

        dim = state.shape[0]

        # Build collapse operators based on decoherence type
        if decoherence_type == "amplitude_damping":
            # Spontaneous emission: sqrt(gamma) * |0><1|
            c_ops = [np.sqrt(gamma) * qt.destroy(dim)]
            H = qt.qeye(dim) * 0  # free evolution (no Hamiltonian drive)
        elif decoherence_type == "dephasing":
            # Pure dephasing: sqrt(gamma/2) * sigma_z
            c_ops = [np.sqrt(gamma / 2.0) * qt.sigmaz()]
            H = qt.qeye(2) * 0
        elif decoherence_type == "depolarizing":
            # Depolarizing channel: equal rates on x, y, z
            rate = np.sqrt(gamma / 4.0)
            c_ops = [
                rate * qt.sigmax(),
                rate * qt.sigmay(),
                rate * qt.sigmaz(),
            ]
            H = qt.qeye(2) * 0
        else:
            return AgentResult(
                success=False,
                error=f"Unknown decoherence_type: {decoherence_type!r}. "
                      "Use 'amplitude_damping', 'dephasing', or 'depolarizing'.",
            )

        result = qt.mesolve(H, state, tlist, c_ops=c_ops)

        # Compute purity at each time step
        purities = [(rho * rho).tr().real for rho in result.states]

        return AgentResult(
            success=True,
            data={
                "states": result.states,
                "purities": purities,
                "gamma": gamma,
                "decoherence_type": decoherence_type,
                "times": list(tlist),
                "solver": "mesolve (decoherence)",
            },
        )
