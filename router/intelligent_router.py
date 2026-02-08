#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Intelligent Router
Phase 3, Step 5.1: Core routing orchestrator

Selects optimal quantum/classical computing providers based on:
  - Hardware capabilities (detected via HardwareDiscovery)
  - Workload requirements (defined via WorkloadSpec)
  - Resource constraints (enforced via SafetyFilter)
  - Provider availability (queried via ProviderRegistry)
  - User priority (cost / speed / accuracy)

LAZY LOADING: Router structure builds on import but executes
ONLY when route() is called. No heavy initialization during import.
Memory footprint <10MB before first route() call.
"""

import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("frankenstein.router")


class IntelligentRouter:
    """
    Central routing orchestrator for Frankenstein 1.0.

    Usage:
        router = IntelligentRouter()
        result = router.route({"workload_type": "quantum_simulation", "qubit_count": 10})
        recommendations = router.get_recommendations({"qubit_count": 5, "priority": "cost"})

    All heavy imports and initialization are deferred to first route() call.
    """

    _instance = None  # Singleton

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # State flags — NO heavy imports here
        self._lazy_initialized = False

        # Cached references (populated on first use)
        self._registry = None
        self._discovery = None

        # Routing history (bounded)
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100

    def _lazy_init(self):
        """
        Perform heavy initialization on first route() call.
        Loads provider registry and hardware discovery.
        """
        if self._lazy_initialized:
            return

        try:
            from integration.providers.registry import get_registry
            self._registry = get_registry()
        except ImportError:
            logger.warning("ProviderRegistry not available — using stub")
            self._registry = None

        try:
            from integration.discovery import get_discovery_engine
            self._discovery = get_discovery_engine()
        except ImportError:
            logger.warning("HardwareDiscovery not available — using defaults")
            self._discovery = None

        self._lazy_initialized = True
        logger.info("IntelligentRouter initialized (lazy)")

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def route(self, workload_spec: dict) -> Dict[str, Any]:
        """
        Route a workload to the optimal provider.

        Args:
            workload_spec: Dict describing the workload. Keys:
                - workload_type: "quantum_simulation", "classical_optimization",
                                 "hybrid_computation", "data_synthesis"
                - qubit_count: Number of qubits (default 0)
                - circuit_depth: Circuit depth (default 0)
                - classical_cpu_threads: CPU threads needed (default 1)
                - memory_requirement_mb: RAM needed in MB (default 100)
                - priority: "cost", "speed", or "accuracy" (default "cost")
                - constraints: Optional dict of additional constraints

        Returns:
            Dict with:
                - provider: Primary provider ID
                - score: Provider score (0.0 - 1.0)
                - fallbacks: List of fallback provider IDs
                - reasoning: Human-readable explanation
                - safety: Resource safety check result
                - timestamp: ISO timestamp
        """
        start_time = time.perf_counter()
        self._lazy_init()

        # Import routing components (lazy)
        from .workload_spec import WorkloadSpec, WorkloadType
        from .decision_engine import (
            route_quantum_workload, route_classical_workload,
            route_hybrid_workload, route_data_synthesis,
            filter_by_capabilities, apply_priority_filter,
        )
        from .scoring import rank_providers
        from .safety_filter import filter_safe_providers
        from .fallback import get_fallback_chain

        # Parse workload spec
        spec = WorkloadSpec.from_dict(workload_spec)

        # Get hardware info
        hw = self._get_hardware_info()
        current_cpu, current_ram, total_ram_mb = self._get_resource_usage()

        # Get available providers
        available = self._get_available_providers()

        # Build provider info map for capability filtering
        provider_info = self._get_provider_info_map()

        # Route based on workload type
        if spec.workload_type == WorkloadType.QUANTUM_SIMULATION:
            candidates = route_quantum_workload(
                spec, hw.get("has_nvidia_gpu", False), available
            )
        elif spec.workload_type == WorkloadType.CLASSICAL_OPTIMIZATION:
            candidates = route_classical_workload(
                spec, hw.get("gpu_vendor", "none"),
                hw.get("cpu_vendor", "intel"), available
            )
        elif spec.workload_type == WorkloadType.HYBRID_COMPUTATION:
            hybrid = route_hybrid_workload(
                spec, hw.get("has_nvidia_gpu", False),
                hw.get("gpu_vendor", "none"),
                hw.get("cpu_vendor", "intel"), available
            )
            # Merge quantum and classical candidates
            candidates = hybrid["quantum"] + hybrid["classical"]
            # Deduplicate
            seen = set()
            candidates = [p for p in candidates
                          if p not in seen and not seen.add(p)]
        elif spec.workload_type == WorkloadType.DATA_SYNTHESIS:
            candidates = route_data_synthesis(
                spec, hw.get("gpu_vendor", "none"),
                hw.get("cpu_vendor", "intel"), available
            )
        else:
            candidates = ["local_cpu"]

        # Filter by capabilities
        candidates = filter_by_capabilities(candidates, spec, provider_info)

        # Apply priority reordering
        candidates = apply_priority_filter(candidates, spec.priority)

        # Safety filter
        safe_candidates, rejected = filter_safe_providers(
            candidates, spec, current_cpu, current_ram, total_ram_mb
        )

        # If all candidates rejected by safety, try cloud providers (low local impact)
        if not safe_candidates and candidates:
            from .safety_filter import check_resource_safety
            # Cloud providers use minimal local resources
            cloud_fallbacks = [
                "ibm_quantum", "aws_braket", "azure_quantum",
            ]
            for fb in cloud_fallbacks:
                check = check_resource_safety(
                    fb, spec, current_cpu, current_ram, total_ram_mb
                )
                if check["safe"]:
                    safe_candidates.append(fb)
                    break

        # Final fallback
        if not safe_candidates:
            safe_candidates = ["local_cpu"]

        # Score and rank
        provider_states = self._get_provider_states()
        ranked = rank_providers(safe_candidates, spec, spec.priority, provider_states)

        # Select primary
        primary = ranked[0] if ranked else {"provider_id": "local_cpu", "score": 0.0}
        fallbacks = get_fallback_chain(primary["provider_id"])

        # Build reasoning
        reasoning = self._build_reasoning(spec, primary, hw, rejected)

        # Build safety info
        from .safety_filter import check_resource_safety
        safety = check_resource_safety(
            primary["provider_id"], spec, current_cpu, current_ram, total_ram_mb
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = {
            "provider": primary["provider_id"],
            "score": primary["score"],
            "fallbacks": fallbacks,
            "alternatives": [r["provider_id"] for r in ranked[1:5]],
            "reasoning": reasoning,
            "safety": safety,
            "workload_summary": spec.summary(),
            "routing_time_ms": round(elapsed_ms, 1),
            "timestamp": datetime.now().isoformat(),
        }

        # Record history
        self._record_history(result)

        return result

    def get_recommendations(self, workload_spec: dict) -> List[Dict[str, Any]]:
        """
        Get ranked provider recommendations without committing to a route.

        Args:
            workload_spec: Same format as route()

        Returns:
            List of dicts with provider_id, score, rank, safety info
        """
        self._lazy_init()

        from .workload_spec import WorkloadSpec, WorkloadType
        from .decision_engine import (
            route_quantum_workload, route_classical_workload,
            route_data_synthesis, filter_by_capabilities,
        )
        from .scoring import rank_providers
        from .safety_filter import check_resource_safety

        spec = WorkloadSpec.from_dict(workload_spec)
        hw = self._get_hardware_info()
        current_cpu, current_ram, total_ram_mb = self._get_resource_usage()
        available = self._get_available_providers()
        provider_info = self._get_provider_info_map()

        # Get candidates based on type
        if spec.workload_type == WorkloadType.QUANTUM_SIMULATION:
            candidates = route_quantum_workload(
                spec, hw.get("has_nvidia_gpu", False), available
            )
        elif spec.workload_type == WorkloadType.CLASSICAL_OPTIMIZATION:
            candidates = route_classical_workload(
                spec, hw.get("gpu_vendor", "none"),
                hw.get("cpu_vendor", "intel"), available
            )
        else:
            candidates = route_quantum_workload(
                spec, hw.get("has_nvidia_gpu", False), available
            ) + route_classical_workload(
                spec, hw.get("gpu_vendor", "none"),
                hw.get("cpu_vendor", "intel"), available
            )

        candidates = filter_by_capabilities(candidates, spec, provider_info)
        provider_states = self._get_provider_states()
        ranked = rank_providers(candidates, spec, spec.priority, provider_states)

        # Add safety info to each
        for entry in ranked:
            safety = check_resource_safety(
                entry["provider_id"], spec,
                current_cpu, current_ram, total_ram_mb
            )
            entry["safe"] = safety["safe"]
            entry["estimated_cpu"] = safety["estimated_cpu"]
            entry["estimated_ram"] = safety["estimated_ram"]

        return ranked

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent routing decisions."""
        return list(reversed(self._history[-limit:]))

    def reset(self):
        """Reset lazy initialization (for testing)."""
        self._lazy_initialized = False
        self._registry = None
        self._discovery = None
        self._history.clear()

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware capabilities from discovery engine."""
        if self._discovery is None:
            return {
                "has_nvidia_gpu": False,
                "gpu_vendor": "none",
                "cpu_vendor": "intel",
                "cpu_cores": 4,
                "ram_gb": 8.0,
                "tier": "tier1",
            }

        try:
            fp = self._discovery.discover()
            gpu_vendor = fp.gpu.vendor.value if fp.gpu else "none"
            return {
                "has_nvidia_gpu": gpu_vendor == "nvidia",
                "gpu_vendor": gpu_vendor,
                "cpu_vendor": fp.cpu.vendor.lower() if fp.cpu.vendor else "intel",
                "cpu_cores": fp.cpu.logical_cores or 4,
                "ram_gb": fp.ram.total_gb or 8.0,
                "tier": fp.tier.value,
            }
        except Exception as e:
            logger.warning("Hardware discovery failed: %s", e)
            return {
                "has_nvidia_gpu": False,
                "gpu_vendor": "none",
                "cpu_vendor": "intel",
                "cpu_cores": 4,
                "ram_gb": 8.0,
                "tier": "tier1",
            }

    def _get_resource_usage(self) -> tuple:
        """
        Get current CPU%, RAM%, and total RAM MB.

        Returns:
            (current_cpu, current_ram_percent, total_ram_mb)
        """
        if self._discovery is not None:
            try:
                usage = self._discovery.get_current_usage()
                fp = self._discovery.discover()
                total_ram_mb = fp.ram.total_gb * 1024 if fp.ram.total_gb else 8192.0
                return (
                    usage.get("cpu_percent", 0.0),
                    usage.get("memory_percent", 0.0),
                    total_ram_mb,
                )
            except Exception:
                pass

        # Fallback: try psutil directly
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            return cpu, mem.percent, mem.total / (1024 * 1024)
        except ImportError:
            return 0.0, 0.0, 8192.0

    def _get_available_providers(self) -> Optional[List[str]]:
        """Get list of providers with SDKs installed."""
        if self._registry is None:
            return None  # Don't filter if registry unavailable

        try:
            return self._registry.get_available_providers()
        except Exception:
            return None

    def _get_provider_info_map(self) -> Optional[Dict[str, Any]]:
        """Get provider info as a dict for capability filtering."""
        if self._registry is None:
            return None

        try:
            from integration.providers.registry import ALL_PROVIDERS
            return {
                pid: {
                    "max_qubits": info.max_qubits,
                    "free_tier": info.free_tier,
                    "provider_type": info.provider_type.value,
                    "capabilities": [c.value for c in info.capabilities],
                }
                for pid, info in ALL_PROVIDERS.items()
            }
        except Exception:
            return None

    def _get_provider_states(self) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get runtime state for scoring."""
        if self._registry is None:
            return None

        try:
            from integration.providers.registry import ALL_PROVIDERS
            states = {}
            for pid in ALL_PROVIDERS:
                state = self._registry.get_state(pid)
                states[pid] = {
                    "sdk_installed": state.sdk_installed,
                    "status": state.status.value,
                }
            return states
        except Exception:
            return None

    def _build_reasoning(
        self,
        spec,
        primary: Dict,
        hw: Dict,
        rejected: List,
    ) -> str:
        """Build human-readable routing explanation."""
        parts = []

        parts.append(
            f"Workload: {spec.workload_type.value}"
        )

        if spec.qubit_count > 0:
            parts.append(f"Qubits: {spec.qubit_count}")

        parts.append(
            f"Hardware: {hw.get('tier', 'tier1').upper()} "
            f"({hw.get('cpu_cores', 4)} cores, "
            f"{hw.get('ram_gb', 8):.0f}GB RAM, "
            f"GPU: {hw.get('gpu_vendor', 'none')})"
        )

        parts.append(
            f"Selected: {primary['provider_id']} "
            f"(score: {primary['score']:.2f}, priority: {spec.priority})"
        )

        if rejected:
            names = [r["provider_id"] for r in rejected[:3]]
            parts.append(f"Rejected (safety): {', '.join(names)}")

        return " | ".join(parts)

    def _record_history(self, result: Dict[str, Any]):
        """Record a routing decision in bounded history."""
        entry = {
            "provider": result["provider"],
            "score": result["score"],
            "workload": result["workload_summary"],
            "timestamp": result["timestamp"],
            "routing_time_ms": result["routing_time_ms"],
        }
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


# ============================================================================
# MODULE-LEVEL CONVENIENCE (lazy singleton)
# ============================================================================

_router: Optional[IntelligentRouter] = None


def get_router() -> IntelligentRouter:
    """Get the intelligent router singleton."""
    global _router
    if _router is None:
        _router = IntelligentRouter()
    return _router
