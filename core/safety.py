"""
FRANKENSTEIN 1.0 - Safety Constraints
Phase 1: Core Engine

Purpose: Immutable safety limits protecting Dell i3 8th Gen hardware
Hardware: Intel i3-8xxx, 4 cores, 8GB RAM, 117GB Storage
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class SafetyConstraints:
    """Immutable safety constraints - CANNOT be changed at runtime"""

    # Resource Limits (tuned for i3 8th Gen with 8GB RAM)
    MAX_CPU_PERCENT: int = 80          # Leave 20% for OS
    MAX_MEMORY_PERCENT: int = 75       # ~6GB max, leave headroom
    MAX_GPU_PERCENT: int = 85          # If discrete GPU present
    MAX_DISK_IO_MBPS: int = 200        # Conservative for laptop SSD
    MAX_STORAGE_USE_GB: int = 20       # 117GB total, keep lean

    # Thread Limits (4-core CPU)
    MAX_WORKER_THREADS: int = 2        # Optimized for tier1: 2 workers + monitors

    # Quantum Budget (cloud API protection)
    MAX_QUANTUM_SHOTS: int = 10000     # Cost protection

    # Behavior Flags
    AUTO_THROTTLE: bool = True
    EMERGENCY_STOP_ENABLED: bool = True

    # Timeouts (seconds)
    TASK_TIMEOUT: int = 300            # 5 min max per task
    QUANTUM_TIMEOUT: int = 600         # 10 min for cloud quantum
    STARTUP_TIMEOUT: int = 30          # Max startup time


# Global immutable instance - THE source of truth
SAFETY = SafetyConstraints()


def check_resource_violation(
    cpu_percent: float,
    memory_percent: float,
    gpu_percent: float = 0.0,
    disk_io_mbps: float = 0.0
) -> Dict[str, Any]:
    """
    Check if current resource usage violates safety constraints.

    Args:
        cpu_percent: Current CPU usage (0-100)
        memory_percent: Current RAM usage (0-100)
        gpu_percent: Current GPU usage (0-100), default 0
        disk_io_mbps: Current disk I/O in MB/s

    Returns:
        Dict with 'safe' boolean, 'violations' list, and recommended actions
    """
    violations = []
    actions = []

    if cpu_percent > SAFETY.MAX_CPU_PERCENT:
        violations.append(f"CPU {cpu_percent:.1f}% exceeds limit {SAFETY.MAX_CPU_PERCENT}%")
        actions.append("throttle_cpu")

    if memory_percent > SAFETY.MAX_MEMORY_PERCENT:
        violations.append(f"Memory {memory_percent:.1f}% exceeds limit {SAFETY.MAX_MEMORY_PERCENT}%")
        actions.append("throttle_memory")

    if gpu_percent > SAFETY.MAX_GPU_PERCENT:
        violations.append(f"GPU {gpu_percent:.1f}% exceeds limit {SAFETY.MAX_GPU_PERCENT}%")
        actions.append("throttle_gpu")

    if disk_io_mbps > SAFETY.MAX_DISK_IO_MBPS:
        violations.append(f"Disk I/O {disk_io_mbps:.1f} MB/s exceeds limit {SAFETY.MAX_DISK_IO_MBPS}")
        actions.append("throttle_disk")

    return {
        "safe": len(violations) == 0,
        "violations": violations,
        "recommended_actions": actions,
        "auto_throttle": SAFETY.AUTO_THROTTLE,
        "emergency_stop_available": SAFETY.EMERGENCY_STOP_ENABLED
    }


def get_constraints_dict() -> Dict[str, Any]:
    """Return all constraints as dictionary for display/logging"""
    return {
        "max_cpu_percent": SAFETY.MAX_CPU_PERCENT,
        "max_memory_percent": SAFETY.MAX_MEMORY_PERCENT,
        "max_gpu_percent": SAFETY.MAX_GPU_PERCENT,
        "max_disk_io_mbps": SAFETY.MAX_DISK_IO_MBPS,
        "max_storage_use_gb": SAFETY.MAX_STORAGE_USE_GB,
        "max_worker_threads": SAFETY.MAX_WORKER_THREADS,
        "max_quantum_shots": SAFETY.MAX_QUANTUM_SHOTS,
        "auto_throttle": SAFETY.AUTO_THROTTLE,
        "emergency_stop": SAFETY.EMERGENCY_STOP_ENABLED,
        "task_timeout_sec": SAFETY.TASK_TIMEOUT,
        "quantum_timeout_sec": SAFETY.QUANTUM_TIMEOUT
    }


def is_within_tier1_limits() -> Dict[str, bool]:
    """
    Verify current config is appropriate for Tier 1 (Dell i3 laptop).
    Used during startup validation.
    """
    return {
        "cpu_limit_appropriate": SAFETY.MAX_CPU_PERCENT <= 80,
        "memory_limit_appropriate": SAFETY.MAX_MEMORY_PERCENT <= 80,
        "thread_limit_appropriate": SAFETY.MAX_WORKER_THREADS <= 2,
        "storage_limit_appropriate": SAFETY.MAX_STORAGE_USE_GB <= 30,
        "tier1_compliant": True
    }
