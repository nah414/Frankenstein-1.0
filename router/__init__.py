#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Intelligent Router
Phase 3, Step 5: Workload Routing Engine

Routes quantum and classical workloads to optimal providers
based on hardware capabilities, resource constraints, and user priority.

Usage:
    from router import get_router
    router = get_router()
    result = router.route({"workload_type": "quantum_simulation", "qubit_count": 10})
"""

from .intelligent_router import IntelligentRouter, get_router
from .workload_spec import WorkloadSpec, WorkloadType, WorkloadPriority

__all__ = [
    "IntelligentRouter",
    "get_router",
    "WorkloadSpec",
    "WorkloadType",
    "WorkloadPriority",
]

__version__ = "1.0.0"
__phase__ = "3.5"
