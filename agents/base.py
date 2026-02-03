"""
FRANKENSTEIN Agents - Base Agent Class
All agents inherit from this class
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Security blocked


@dataclass
class AgentResult:
    """Result from agent execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    security_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "security_warnings": self.security_warnings
        }


class BaseAgent(ABC):
    """
    Base class for all FRANKENSTEIN agents.

    Agents are isolated units that perform specific tasks.
    They run in a sandboxed environment with security restrictions.
    """

    # Agent metadata - override in subclasses
    name: str = "base_agent"
    description: str = "Base agent class"
    version: str = "1.0.0"

    # Security settings
    requires_network: bool = False
    requires_filesystem: bool = False
    max_execution_time: int = 30  # seconds

    def __init__(self):
        self.status = AgentStatus.IDLE
        self._start_time: Optional[datetime] = None
        self._result: Optional[AgentResult] = None

    @abstractmethod
    def execute(self, **kwargs) -> AgentResult:
        """
        Execute the agent's task.
        Must be implemented by subclasses.
        """
        pass

    def run(self, **kwargs) -> AgentResult:
        """
        Run the agent with timing and error handling.
        This is the public interface - do not override.
        """
        self.status = AgentStatus.RUNNING
        self._start_time = datetime.now()

        try:
            result = self.execute(**kwargs)
            self.status = AgentStatus.COMPLETED
        except Exception as e:
            result = AgentResult(
                success=False,
                error=str(e),
                execution_time=self._get_elapsed()
            )
            self.status = AgentStatus.FAILED

        result.execution_time = self._get_elapsed()
        self._result = result
        return result

    def _get_elapsed(self) -> float:
        """Get elapsed time since start"""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return 0.0

    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "requires_network": self.requires_network,
            "requires_filesystem": self.requires_filesystem,
        }
