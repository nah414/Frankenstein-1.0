"""
agents/sauron/tools/agent_tools.py
------------------------------------
Day 6: Agent Dispatch Tool — bridges Sauron tool layer ↔ SauronOrchestrator.

Exposes a single AgentDispatchTool that the router can call as a normal
Sauron tool.  The tool routes to the correct sub-agent via the orchestrator.

All agent calls are Ring 3 (SAFE) — no destructive operations are possible
through this interface.  Individual agents enforce their own limits.

Supported "action" values exposed to the LLM
─────────────────────────────────────────────
  agent_dispatch  (the tool name in the registry)
    action  (str)  — dot-notation "agent_name.agent_action"
                     e.g.  "compute.calculate"
                           "hardware.status"
                           "security.scan"
                           "synthesis.compute"
                           "discover"             ← special: list all agents

    **extra kwargs forwarded to the underlying agent's execute()

Dot-notation examples
─────────────────────
  action="hardware.status"      → HardwareAgent.execute("status")
  action="security.scan", text="rm -rf /"  → SecurityAgent.execute("scan", text=...)
  action="synthesis.reset", num_qubits=3   → SynthesisEngine reset(3)
  action="compute.calculate", expression="2**10"
  action="discover"             → list all registered agents
"""

from __future__ import annotations

import logging
from typing import Any

from agents.sauron.tools.base import BaseTool, ToolResult
from agents.sauron.permissions import PermissionLevel

logger = logging.getLogger(__name__)


class AgentDispatchTool(BaseTool):
    """
    Sauron tool that delegates work to FRANKENSTEIN sub-agents via the
    SauronOrchestrator.

    The orchestrator is imported lazily inside execute() so this file
    has zero startup cost.
    """

    name = "agent_dispatch"
    description = (
        "Delegate tasks to FRANKENSTEIN sub-agents. "
        "Use action='discover' to list available agents. "
        "Use action='<agent_name>.<agent_action>' to run a specific agent. "
        "Agents: compute, numerical_computing, quantum_dynamics, "
        "quantum_hardware, quantum_crypto, security, hardware, synthesis. "
        "Examples: action='hardware.status', action='security.scan' text='some input', "
        "action='synthesis.compute' shots=512, action='discover'"
    )
    permission_level = PermissionLevel.SAFE
    requires_network = False

    def execute(self, action: str = "discover", **kwargs: Any) -> ToolResult:
        """
        Route to the appropriate sub-agent.

        Args:
            action: 'discover' OR '<agent_name>.<agent_action>'
            **kwargs: forwarded to the underlying agent
        """
        from agents.sauron.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()

        # ── Special: discover ─────────────────────────────────────────────────
        if action == "discover":
            agents = orchestrator.discover()
            data = [
                {
                    "name": a.name,
                    "description": a.description,
                    "available": a.available,
                }
                for a in agents
            ]
            summary = (
                f"Found {len(data)} agents: "
                + ", ".join(a["name"] for a in data if a["available"])
            )
            return ToolResult(
                success=True,
                data=data,
                summary=summary,
                permission_level=PermissionLevel.SAFE,
            )

        # ── Parse dot-notation ────────────────────────────────────────────────
        if "." not in action:
            return ToolResult(
                success=False,
                error=(
                    f"Invalid action format '{action}'. "
                    "Use dot-notation: '<agent_name>.<agent_action>' "
                    "or 'discover' to list agents."
                ),
            )

        agent_name, agent_action = action.split(".", 1)

        if not orchestrator.has_agent(agent_name):
            available = orchestrator.agent_names()
            return ToolResult(
                success=False,
                error=(
                    f"Agent '{agent_name}' not found. "
                    f"Available agents: {available}"
                ),
            )

        # ── Single dispatch ───────────────────────────────────────────────────
        result = orchestrator.dispatch(agent_name, agent_action, **kwargs)

        if not result.success:
            return ToolResult(
                success=False,
                error=result.error,
                summary=f"Agent '{agent_name}' failed on '{agent_action}': {result.error}",
            )

        summary = (
            f"Agent '{agent_name}' completed '{agent_action}' "
            f"in {result.execution_time * 1000:.0f}ms"
        )
        return ToolResult(
            success=True,
            data=result.data,
            summary=summary,
            permission_level=PermissionLevel.SAFE,
        )


class MultiAgentDispatchTool(BaseTool):
    """
    Fan-out tool: run multiple agent calls concurrently in one invocation.

    Useful when Sauron needs to gather state from several sub-systems at once,
    e.g. hardware status + security threats + synthesis state simultaneously.

    Args:
        calls (list[dict]): Each dict must have:
            agent  (str)  — agent name
            action (str)  — agent action (default "status")
            Any additional keys are forwarded to the agent as kwargs.

    Example router call:
        tool="multi_agent_dispatch"
        calls=[
          {"agent":"hardware","action":"status"},
          {"agent":"security","action":"threats"},
          {"agent":"synthesis","action":"status"},
        ]
    """

    name = "multi_agent_dispatch"
    description = (
        "Fan-out: run multiple sub-agent calls concurrently and aggregate results. "
        "Pass calls=[{agent, action, ...kwargs}, ...]. "
        "Returns aggregated results from all agents. "
        "Thread count capped at SAFETY.MAX_WORKER_THREADS."
    )
    permission_level = PermissionLevel.SAFE
    requires_network = False

    def execute(self, calls: list | None = None, **kwargs: Any) -> ToolResult:
        if not calls:
            return ToolResult(
                success=False,
                error="'calls' list is required for multi_agent_dispatch.",
            )

        from agents.sauron.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()
        multi_result = orchestrator.multi_dispatch(calls)

        summary = (
            f"Multi-dispatch: {multi_result.success_count}/{len(calls)} succeeded "
            f"in {multi_result.total_time * 1000:.0f}ms"
        )

        return ToolResult(
            success=multi_result.all_success,
            data=multi_result.to_dict(),
            summary=summary,
            error=(
                None
                if multi_result.all_success
                else f"{multi_result.failure_count} agent(s) failed"
            ),
        )
