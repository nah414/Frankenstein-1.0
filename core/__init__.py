"""
FRANKENSTEIN 1.0 - Core Module
Optimized for Tier 1 hardware (Dell i3 8th Gen, 8GB RAM)

Hard Limits (non-negotiable):
- CPU: 80% max
- Memory: 70% max

Features:
- Adaptive resource monitoring
- Agent scheduling with throttling
- Low memory mode for constrained systems
"""

from .resource_manager import (
    get_resource_manager,
    ensure_resource_manager_running,
    AdaptiveResourceManager,
    MonitorState,
    ResourceSample
)

from .agent_scheduler import (
    get_scheduler,
    ensure_scheduler_running,
    AgentScheduler,
    AgentPriority,
    AgentState,
    AgentTask
)

from .low_memory_mode import (
    get_low_memory_manager,
    ensure_low_memory_manager_running,
    check_startup_memory,
    LowMemoryManager,
    MemoryMode,
    ModeSettings,
    MODE_CONFIGS
)

__all__ = [
    # Resource Manager
    'get_resource_manager',
    'ensure_resource_manager_running',
    'AdaptiveResourceManager',
    'MonitorState',
    'ResourceSample',
    # Agent Scheduler
    'get_scheduler',
    'ensure_scheduler_running',
    'AgentScheduler',
    'AgentPriority',
    'AgentState',
    'AgentTask',
    # Low Memory Mode
    'get_low_memory_manager',
    'ensure_low_memory_manager_running',
    'check_startup_memory',
    'LowMemoryManager',
    'MemoryMode',
    'ModeSettings',
    'MODE_CONFIGS',
]
