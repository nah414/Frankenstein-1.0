"""
FRANKENSTEIN Built-in Agent - Security
Phase 4 / Day 6: Thin wrapper over security.shield + security.monitor

Exposes the existing security subsystem as a BaseAgent so that the
Sauron orchestrator can discover and delegate to it uniformly.

All security modules are imported INSIDE execute() — never at class level —
so this agent adds zero startup overhead.

Supported actions:
  status          — Shield status + active threat count
  scan            — Check a text string for threats (payload: {"text": "..."})
  threats         — List currently active threat events
  audit_recent    — Last N lines from the sauron audit log
"""

import logging
from typing import Any, Dict

from ..base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """
    Thin wrapper over FRANKENSTEIN's security subsystem.

    Delegates to security.shield (input validation, status) and
    security.monitor (live threat feed) via their existing singleton
    factories — no new security logic is introduced here.
    """

    name = "security"
    description = (
        "Security scanning, threat detection, and shield status. "
        "Actions: status, scan, threats, audit_recent"
    )
    version = "1.0.0"
    requires_network = False
    requires_filesystem = False
    max_execution_time = 5

    def execute(self, action: str = "status", **kwargs) -> AgentResult:
        """
        Execute a security action.

        Args:
            action: One of status | scan | threats | audit_recent
            **kwargs:
                text  (str)  — for action="scan"
                lines (int)  — for action="audit_recent" (default 20)
        """
        import time
        start = time.time()

        try:
            if action == "status":
                data = self._get_status()
            elif action == "scan":
                text = kwargs.get("text", "")
                data = self._scan_input(text)
            elif action == "threats":
                data = self._get_threats()
            elif action == "audit_recent":
                lines = int(kwargs.get("lines", 20))
                data = self._get_audit_recent(lines)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action '{action}'. Valid: status, scan, threats, audit_recent",
                    execution_time=time.time() - start,
                )

            return AgentResult(
                success=True,
                data=data,
                execution_time=time.time() - start,
            )

        except Exception as exc:
            logger.exception("SecurityAgent.execute failed: %s", exc)
            return AgentResult(
                success=False,
                error=str(exc),
                execution_time=time.time() - start,
            )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_status(self) -> Dict[str, Any]:
        from security.shield import get_shield
        from security.monitor import get_monitor
        shield_status = get_shield().get_status()
        monitor_line = get_monitor().get_status_line()
        return {
            "shield": shield_status,
            "monitor": monitor_line,
        }

    def _scan_input(self, text: str) -> Dict[str, Any]:
        from security.shield import get_shield
        is_safe, message = get_shield().check_input(text, source="sauron")
        return {"is_safe": is_safe, "message": message, "text_scanned": text[:120]}

    def _get_threats(self) -> Dict[str, Any]:
        from security.monitor import get_monitor
        events = get_monitor().get_active_threats()
        return {
            "active_threat_count": len(events),
            "threats": [e.to_dict() for e in events[:10]],  # Cap at 10
        }

    def _get_audit_recent(self, lines: int) -> Dict[str, Any]:
        """Read the last N lines from the sauron audit log."""
        from pathlib import Path
        log_path = Path.home() / ".frankenstein" / "logs" / "sauron_audit.log"
        if not log_path.exists():
            return {"lines": [], "log_path": str(log_path), "exists": False}
        try:
            all_lines = log_path.read_text(encoding="utf-8").splitlines()
            recent = all_lines[-lines:]
            return {"lines": recent, "log_path": str(log_path), "exists": True}
        except Exception as exc:
            return {"lines": [], "error": str(exc), "exists": True}
