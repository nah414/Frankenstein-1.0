"""
FRANKENSTEIN 1.0 - Core Engine
Phase 1: Foundation Components

Exports the core building blocks.
"""

from .safety import (
    SAFETY,
    SafetyConstraints,
    check_resource_violation,
    get_constraints_dict,
    is_within_tier1_limits
)

from .governor import (
    ResourceGovernor,
    ResourceSnapshot,
    ThrottleLevel,
    get_governor
)

from .memory import (
    MemorySystem,
    SessionState,
    TaskRecord,
    get_memory
)

from .orchestrator import (
    TaskOrchestrator,
    Task,
    TaskType,
    TaskStatus,
    TaskPriority,
    get_orchestrator
)

__all__ = [
    # Safety
    "SAFETY",
    "SafetyConstraints",
    "check_resource_violation",
    "get_constraints_dict",
    "is_within_tier1_limits",
    # Governor
    "ResourceGovernor",
    "ResourceSnapshot",
    "ThrottleLevel",
    "get_governor",
    # Memory
    "MemorySystem",
    "SessionState",
    "TaskRecord",
    "get_memory",
    # Orchestrator
    "TaskOrchestrator",
    "Task",
    "TaskType",
    "TaskStatus",
    "TaskPriority",
    "get_orchestrator",
]

__version__ = "1.0.0-phase1"
