"""
FRANKENSTEIN Built-in Agent - Hardware
Phase 4 / Day 6: Thin wrapper over core.hardware_monitor

Exposes the existing hardware health subsystem as a BaseAgent so that
the Sauron orchestrator can discover and delegate to it uniformly.

The hardware monitor import lives entirely inside execute() — never at
class level — so this agent adds zero startup overhead.

Supported actions:
  status      — Full stats dict from HardwareHealthMonitor.get_stats()
  status_line — Single-line status string (CPU, RAM, health icon)
  tier        — Current hardware tier name + description
  recommend   — Switch recommendation (should we upgrade tier?)
"""

import logging
import time
from typing import Any, Dict

from ..base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class HardwareAgent(BaseAgent):
    """
    Thin wrapper over FRANKENSTEIN's hardware health monitor.

    Delegates to core.hardware_monitor via its existing singleton factory.
    No new monitoring logic is introduced here.
    """

    name = "hardware"
    description = (
        "Hardware health, CPU/RAM stats, tier status, switch recommendations. "
        "Actions: status, status_line, tier, recommend"
    )
    version = "1.0.0"
    requires_network = False
    requires_filesystem = False
    max_execution_time = 5

    def execute(self, action: str = "status", **kwargs) -> AgentResult:
        """
        Execute a hardware query action.

        Args:
            action: One of status | status_line | tier | recommend
        """
        start = time.time()

        try:
            if action == "status":
                data = self._get_status()
            elif action == "status_line":
                data = self._get_status_line()
            elif action == "tier":
                data = self._get_tier()
            elif action == "recommend":
                data = self._get_recommendation()
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action '{action}'. Valid: status, status_line, tier, recommend",
                    execution_time=time.time() - start,
                )

            return AgentResult(
                success=True,
                data=data,
                execution_time=time.time() - start,
            )

        except Exception as exc:
            logger.exception("HardwareAgent.execute failed: %s", exc)
            return AgentResult(
                success=False,
                error=str(exc),
                execution_time=time.time() - start,
            )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_status(self) -> Dict[str, Any]:
        from core.hardware_monitor import get_hardware_monitor
        return get_hardware_monitor().get_stats()

    def _get_status_line(self) -> Dict[str, Any]:
        from core.hardware_monitor import get_hardware_monitor
        line = get_hardware_monitor().get_status_line()
        return {"status_line": line}

    def _get_tier(self) -> Dict[str, Any]:
        from core.hardware_monitor import get_hardware_monitor
        monitor = get_hardware_monitor()
        tier = monitor.get_current_tier()
        return {
            "tier_name": tier.name,
            "tier_description": tier.description,
            "max_cpu": tier.max_cpu,
            "max_memory": tier.max_memory,
            "max_workers": tier.max_workers,
        }

    def _get_recommendation(self) -> Dict[str, Any]:
        from core.hardware_monitor import get_hardware_monitor
        stats = get_hardware_monitor().get_stats()
        return {
            "switch_recommended": stats.get("switch_recommended", False),
            "switch_urgency": stats.get("switch_urgency", "none"),
            "switch_reason": stats.get("switch_reason", ""),
            "recommended_tier": stats.get("recommended_tier", "unknown"),
            "headroom_percent": stats.get("headroom_percent", 0),
        }
