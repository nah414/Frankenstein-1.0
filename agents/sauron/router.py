"""
agents/sauron/router.py
-----------------------
Day 5: Action Router — ReAct loop (up to 8 steps).

Receives a user message + rolling message history, calls the IntentParser
to decide what to do, executes tool calls via the ToolRegistry, appends
structured messages so the model can observe results, and returns a
RouterResult when the model produces a final text answer or the step
limit is reached.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from agents.sauron.parser import get_parser, ParsedIntent
from agents.sauron.tools import get_registry
from agents.sauron.tools.base import ToolResult

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────

@dataclass
class ToolExecution:
    """Record of a single tool call made during a ReAct step."""
    tool_name: str
    action: str
    arguments: dict
    result: ToolResult
    step: int


@dataclass
class RouterResult:
    """Final output returned to the caller after the ReAct loop completes."""
    final_answer: str                              # Model's last text response
    executions: list[ToolExecution] = field(default_factory=list)
    steps: int = 0
    success: bool = True
    stopped_early: bool = False                    # True if MAX_STEPS was hit


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MAX_STEPS = 8
RESULT_CAP_CHARS = 2_000   # Truncate tool output before feeding back to model
SUMMARY_PROMPT = (
    "You have reached the maximum number of tool-use steps. "
    "Summarise what you have found so far and give the best answer you can "
    "with the information already collected. Do not call any more tools."
)


# ─────────────────────────────────────────────
# ActionRouter
# ─────────────────────────────────────────────

class ActionRouter:
    """
    Implements the ReAct (Reason + Act) loop for Sauron.

    Each call to `run()` appends the user message to the provided
    messages list (mutated in-place for the rolling 20-turn window),
    then iterates up to MAX_STEPS:

      1. Call IntentParser → ParsedIntent
      2a. If has_tool_call  → execute, append assistant + tool messages, loop
      2b. If text response  → append assistant message, return RouterResult

    On hitting MAX_STEPS the router injects a summary prompt so the
    model produces a graceful final answer rather than a hard stop.
    """

    def __init__(self) -> None:
        self._parser = get_parser()
        self._registry = get_registry()

    # ──────────────────────────────────────
    # Public API
    # ──────────────────────────────────────

    def run(self, user_message: str, messages: list[dict]) -> RouterResult:
        """
        Execute the ReAct loop.

        Args:
            user_message: The raw user input string.
            messages:     Mutable rolling-window message list (modified in-place).

        Returns:
            RouterResult with final answer and execution history.
        """
        # Append the new user turn
        messages.append({"role": "user", "content": user_message})

        executions: list[ToolExecution] = []
        step = 0

        while step < MAX_STEPS:
            step += 1
            logger.debug("ReAct step %d/%d", step, MAX_STEPS)

            # ── Parse intent ──────────────────────────────────────────────
            intent: ParsedIntent = self._parser.parse_from_messages(messages)

            # ── Text answer → done ────────────────────────────────────────
            if not intent.has_tool_call:
                answer = intent.text_response or ""
                messages.append({"role": "assistant", "content": answer})
                return RouterResult(
                    final_answer=answer,
                    executions=executions,
                    steps=step,
                    success=True,
                    stopped_early=False,
                )

            # ── Tool call → execute ───────────────────────────────────────
            tool_result = self._execute(intent)

            execution = ToolExecution(
                tool_name=intent.tool_name or "unknown",
                action=intent.action or "unknown",
                arguments=intent.arguments,
                result=tool_result,
                step=step,
            )
            executions.append(execution)

            # Append assistant message with tool_calls (Ollama format)
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "function": {
                            "name": intent.tool_name,
                            "arguments": intent.arguments,
                        }
                    }
                ],
            })

            # Append tool result so the model can observe it
            formatted = self._format_result(tool_result)
            messages.append({
                "role": "tool",
                "content": formatted,
            })

            logger.debug(
                "Step %d: %s.%s → success=%s",
                step,
                intent.tool_name,
                intent.action,
                tool_result.success,
            )

        # ── MAX_STEPS reached — ask model to summarise ────────────────────
        logger.warning("ReAct loop hit MAX_STEPS (%d). Requesting summary.", MAX_STEPS)
        messages.append({"role": "user", "content": SUMMARY_PROMPT})

        final_intent = self._parser.parse_from_messages(messages)
        summary_answer = final_intent.text_response or (
            "I reached the step limit. Here is what was collected:\n"
            + "\n".join(
                f"Step {e.step}: {e.tool_name}.{e.action} → "
                + ("OK" if e.result.success else f"ERROR: {e.result.error}")
                for e in executions
            )
        )
        messages.append({"role": "assistant", "content": summary_answer})

        return RouterResult(
            final_answer=summary_answer,
            executions=executions,
            steps=MAX_STEPS,
            success=False,
            stopped_early=True,
        )

    # ──────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────

    def _execute(self, intent: ParsedIntent) -> ToolResult:
        """
        Dispatch the tool call to the ToolRegistry.

        Passes action plus all remaining arguments.  The registry's
        BaseTool.run() handles ring enforcement and audit logging.
        """
        tool_name = intent.tool_name
        if not tool_name:
            return ToolResult(
                success=False,
                error="Parser returned a tool call with no tool_name.",
            )

        registry = self._registry
        available = [t["name"] for t in registry.list_tools()]
        if tool_name not in available:
            return ToolResult(
                success=False,
                error=f"Unknown tool '{tool_name}'. Available: {available}",
            )

        kwargs = dict(intent.arguments)
        # 'action' is a top-level kwarg consumed by BaseTool dispatch
        # Make sure it's present (parser puts it inside arguments already,
        # but guard against edge cases)
        if "action" not in kwargs and intent.action:
            kwargs["action"] = intent.action

        try:
            return registry.execute(tool_name, **kwargs)
        except Exception as exc:  # pragma: no cover
            logger.exception("Unexpected error executing %s: %s", tool_name, exc)
            return ToolResult(
                success=False,
                error=f"Execution raised {type(exc).__name__}: {exc}",
            )

    def _format_result(self, result: ToolResult) -> str:
        """
        Serialise a ToolResult into a string the model can read.

        Caps at RESULT_CAP_CHARS to avoid blowing the context window.
        """
        if not result.success:
            body = f"ERROR: {result.error}"
        else:
            try:
                body = json.dumps(result.data, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                body = str(result.data)

        if len(body) > RESULT_CAP_CHARS:
            body = body[:RESULT_CAP_CHARS] + f"\n... [truncated at {RESULT_CAP_CHARS} chars]"

        if result.summary:
            body = f"{result.summary}\n\n{body}"

        return body


# ─────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────

_router_instance: Optional[ActionRouter] = None


def get_router() -> ActionRouter:
    """Return the module-level singleton ActionRouter (lazy init)."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ActionRouter()
    return _router_instance
