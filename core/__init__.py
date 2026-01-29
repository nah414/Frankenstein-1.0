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

from .hardware_monitor import (
    HardwareHealthMonitor,
    HardwareTier,
    HealthStatus,
    HealthTrend,
    SwitchRecommendation,
    get_hardware_monitor
)

from .hardware_dashboard import (
    HardwareDashboard,
    get_hardware_dashboard,
    handle_hardware_command
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
    # Hardware Monitor (Phase 2)
    "HardwareHealthMonitor",
    "HardwareTier",
    "HealthStatus",
    "HealthTrend",
    "SwitchRecommendation",
    "get_hardware_monitor",
    # Hardware Dashboard (Phase 2)
    "HardwareDashboard",
    "get_hardware_dashboard",
    "handle_hardware_command",
]

__version__ = "2.0.0-phase2"
