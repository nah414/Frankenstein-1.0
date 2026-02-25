"""
FRANKENSTEIN 1.0 - Eye of Sauron: Base Tool
Phase 4 / Day 2: Tool Foundation

All Sauron tools inherit from BaseTool. Provides:
  - Standardised ToolResult return type
  - Permission enforcement via PermissionManager
  - Resource check against SAFETY limits
  - Audit logging on every execution
"""

import logging
import psutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from core.safety import SAFETY
from agents.sauron.permissions import PermissionLevel, get_permission_manager
from agents.sauron.audit import SauronEvent, get_sauron_audit

logger = logging.getLogger(__name__)


# ── Result Type ────────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """Standard return type for all Sauron tool executions."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    permission_level: PermissionLevel = PermissionLevel.SAFE
    # Set to True if web content contained a detected injection pattern
    injection_flagged: bool = False
    # Human-readable summary for Sauron's LLM context
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "permission_level": self.permission_level.name,
            "injection_flagged": self.injection_flagged,
            "summary": self.summary,
        }


# ── Base Tool ──────────────────────────────────────────────────────────────────

class BaseTool(ABC):
    """
    Abstract base class for all Eye of Sauron tools.

    Subclasses must define:
        name            (str)        — unique tool identifier
        description     (str)        — what the tool does (shown to LLM)
        permission_level (PermissionLevel) — Ring classification

    And implement:
        execute(**kwargs) -> ToolResult
    """

    name: str = "base_tool"
    description: str = "Base tool (do not use directly)"
    permission_level: PermissionLevel = PermissionLevel.SAFE

    # Override in subclass if tool requires external network access
    requires_network: bool = False

    def run(self, **kwargs) -> ToolResult:
        """
        Public entry point. Handles the full execute lifecycle:
          1. Resource check
          2. Permission check (Ring 1 block / Ring 2 prompt)
          3. Audit log start
          4. execute(**kwargs)
          5. Audit log result
        """
        audit = get_sauron_audit()
        pm = get_permission_manager()

        # Resource guard
        if not self._check_resources():
            msg = f"Insufficient resources to run {self.name}"
            audit.log(SauronEvent.TOOL_CALL, f"SKIPPED (resources): {self.name}", {"reason": msg})
            return ToolResult(success=False, error=msg)

        # Permission enforcement
        if self.permission_level == PermissionLevel.FORBIDDEN:
            audit.log_ring1_block(self.name)
            return ToolResult(
                success=False,
                error=f"Ring 1 FORBIDDEN: {self.name} is not permitted.",
                permission_level=PermissionLevel.FORBIDDEN,
            )

        if self.permission_level == PermissionLevel.SENSITIVE:
            description = kwargs.get("_description", f"Execute tool: {self.name}")
            audit.log_permission(SauronEvent.PERMISSION_ASK, self.name, description)
            approved = pm.request_permission(self.name, description)
            if not approved:
                audit.log_permission(SauronEvent.PERMISSION_DENY, self.name, description)
                return ToolResult(
                    success=False,
                    error=f"Permission denied for: {self.name}",
                    permission_level=PermissionLevel.SENSITIVE,
                )
            audit.log_permission(SauronEvent.PERMISSION_GRANT, self.name, description)

        # Execute
        kwargs.pop("_description", None)  # Strip internal key before dispatch
        audit.log_tool_call(self.name, str(kwargs)[:150])
        try:
            result = self.execute(**kwargs)
            return result
        except Exception as e:
            logger.error("Tool %s raised: %s", self.name, e, exc_info=True)
            return ToolResult(success=False, error=str(e))

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Implement the tool's actual logic here."""

    def _check_resources(self) -> bool:
        """
        Verify CPU and RAM are within SAFETY limits before executing.
        Returns False if the system is over the hard limits.
        """
        try:
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory().percent
            if cpu > SAFETY.MAX_CPU_PERCENT:
                logger.warning("CPU %.1f%% > limit %d%%", cpu, SAFETY.MAX_CPU_PERCENT)
                return False
            if ram > SAFETY.MAX_MEMORY_PERCENT:
                logger.warning("RAM %.1f%% > limit %d%%", ram, SAFETY.MAX_MEMORY_PERCENT)
                return False
            return True
        except Exception:
            return True  # Non-fatal — allow execution if psutil fails

    def get_info(self) -> dict:
        """Return tool metadata for the registry and LLM system prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "ring": self.permission_level.name,
            "requires_network": self.requires_network,
        }
