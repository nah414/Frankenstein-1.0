#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Resource Safety Integration
Phase 3, Step 5.5: Enforce CPU/RAM hard limits during routing

Hard limits:
  - CPU: current + estimated must not exceed 80%
  - RAM: current + estimated must not exceed 75%

Integrates with:
  - HardwareDiscovery for real-time resource tracking
  - SafetyConstraints (core/safety.py) for limit definitions
"""

import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .workload_spec import WorkloadSpec

logger = logging.getLogger("frankenstein.router.safety")

# Hard limits — these NEVER change
MAX_CPU_PERCENT = 80.0
MAX_RAM_PERCENT = 75.0


# ============================================================================
# CPU/RAM USAGE PREDICTION BY PROVIDER
# ============================================================================

# Estimated CPU usage (percent of total) for different provider types
_CPU_USAGE_ESTIMATES: Dict[str, float] = {
    # Local providers — use actual CPU
    "local_cpu": 40.0,
    "local_simulator": 50.0,
    "qiskit_aer": 55.0,
    "cuquantum": 15.0,       # GPU-offloaded, low CPU
    # Cloud quantum — minimal local CPU (just API calls)
    "ibm_quantum": 5.0,
    "aws_braket": 5.0,
    "azure_quantum": 5.0,
    "google_cirq": 5.0,
    "ionq": 3.0,
    "rigetti": 5.0,
    "xanadu": 5.0,
    "dwave": 3.0,
    "quantinuum": 3.0,
    "iqm": 3.0,
    "quera": 3.0,
    "oxford": 3.0,
    "atom_computing": 3.0,
    "pasqal": 3.0,
    "aqt": 3.0,
    "nvidia_quantum_cloud": 5.0,
    # Classical accelerators
    "nvidia_cuda": 20.0,
    "amd_rocm": 20.0,
    "intel_oneapi": 35.0,
    "apple_metal": 15.0,
    "arm": 40.0,
    "risc_v": 40.0,
    "tpu": 10.0,
    "fpga": 10.0,
    "npu": 15.0,
}

# Estimated RAM usage (MB) for different provider types
_RAM_USAGE_ESTIMATES: Dict[str, float] = {
    # Local providers — use actual RAM
    "local_cpu": 200.0,
    "local_simulator": 300.0,
    "qiskit_aer": 400.0,
    "cuquantum": 150.0,
    # Cloud quantum — minimal local RAM
    "ibm_quantum": 80.0,
    "aws_braket": 80.0,
    "azure_quantum": 80.0,
    "google_cirq": 80.0,
    "ionq": 50.0,
    "rigetti": 80.0,
    "xanadu": 80.0,
    "dwave": 50.0,
    "quantinuum": 50.0,
    "iqm": 50.0,
    "quera": 50.0,
    "oxford": 50.0,
    "atom_computing": 50.0,
    "pasqal": 50.0,
    "aqt": 50.0,
    "nvidia_quantum_cloud": 100.0,
    # Classical accelerators
    "nvidia_cuda": 300.0,
    "amd_rocm": 300.0,
    "intel_oneapi": 250.0,
    "apple_metal": 200.0,
    "arm": 200.0,
    "risc_v": 200.0,
    "tpu": 150.0,
    "fpga": 100.0,
    "npu": 150.0,
}


# ============================================================================
# PREDICTION FUNCTIONS
# ============================================================================

def predict_cpu_usage(provider_id: str, workload: 'WorkloadSpec') -> float:
    """
    Estimate CPU load for a provider + workload combination.

    Args:
        provider_id: Provider identifier
        workload: WorkloadSpec with resource requirements

    Returns:
        Estimated CPU percentage (0-100)
    """
    base = _CPU_USAGE_ESTIMATES.get(provider_id, 30.0)

    # Scale by thread count for local providers
    if provider_id in ("local_cpu", "local_simulator", "qiskit_aer",
                       "intel_oneapi", "arm", "risc_v"):
        thread_factor = workload.classical_cpu_threads / 4.0  # Tier 1 = 4 cores
        base *= max(0.5, min(thread_factor, 2.0))

    # Quantum simulation scales with qubit count for local sims
    if provider_id in ("local_simulator", "qiskit_aer") and workload.qubit_count > 10:
        qubit_scale = 1.0 + (workload.qubit_count - 10) * 0.1
        base *= min(qubit_scale, 2.0)

    return round(min(base, 100.0), 1)


def predict_ram_usage(provider_id: str, workload: 'WorkloadSpec') -> float:
    """
    Estimate RAM usage in MB for a provider + workload combination.

    Args:
        provider_id: Provider identifier
        workload: WorkloadSpec with resource requirements

    Returns:
        Estimated RAM usage in MB
    """
    base = _RAM_USAGE_ESTIMATES.get(provider_id, 200.0)

    # Quantum state vector memory: 2^n * 16 bytes (complex128)
    if provider_id in ("local_simulator", "qiskit_aer", "cuquantum"):
        if workload.qubit_count > 0:
            state_vector_mb = (2 ** workload.qubit_count * 16) / (1024 * 1024)
            base = max(base, state_vector_mb * 1.5)  # 50% overhead

    # Classical workloads use specified memory
    base = max(base, workload.memory_requirement_mb)

    return round(base, 1)


def predict_ram_usage_percent(provider_id: str, workload: 'WorkloadSpec',
                              total_ram_mb: float = 8192.0) -> float:
    """
    Estimate RAM usage as percentage of total system RAM.

    Args:
        provider_id: Provider identifier
        workload: WorkloadSpec
        total_ram_mb: Total system RAM in MB (default 8GB for Tier 1)

    Returns:
        Estimated RAM usage as percentage (0-100)
    """
    usage_mb = predict_ram_usage(provider_id, workload)
    return round((usage_mb / total_ram_mb) * 100.0, 1)


# ============================================================================
# SAFETY CHECK
# ============================================================================

def check_resource_safety(
    provider_id: str,
    workload: 'WorkloadSpec',
    current_cpu: float = 0.0,
    current_ram: float = 0.0,
    total_ram_mb: float = 8192.0,
) -> Dict[str, Any]:
    """
    Check if routing to a provider would exceed resource limits.

    Args:
        provider_id: Target provider
        workload: WorkloadSpec describing the computation
        current_cpu: Current CPU usage percentage
        current_ram: Current RAM usage percentage
        total_ram_mb: Total system RAM in MB

    Returns:
        Dict with:
          - safe (bool): True if within limits
          - estimated_cpu (float): Predicted CPU after routing
          - estimated_ram (float): Predicted RAM after routing
          - reason (str): Explanation if unsafe
    """
    est_cpu = predict_cpu_usage(provider_id, workload)
    est_ram_pct = predict_ram_usage_percent(provider_id, workload, total_ram_mb)

    projected_cpu = current_cpu + est_cpu
    projected_ram = current_ram + est_ram_pct

    reasons = []

    if projected_cpu > MAX_CPU_PERCENT:
        reasons.append(
            f"CPU would reach {projected_cpu:.1f}% "
            f"(current {current_cpu:.1f}% + estimated {est_cpu:.1f}%, "
            f"limit {MAX_CPU_PERCENT:.0f}%)"
        )

    if projected_ram > MAX_RAM_PERCENT:
        reasons.append(
            f"RAM would reach {projected_ram:.1f}% "
            f"(current {current_ram:.1f}% + estimated {est_ram_pct:.1f}%, "
            f"limit {MAX_RAM_PERCENT:.0f}%)"
        )

    safe = len(reasons) == 0

    if not safe:
        logger.warning(
            "Safety filter REJECTED %s for workload: %s",
            provider_id, "; ".join(reasons)
        )

    return {
        "safe": safe,
        "estimated_cpu": round(projected_cpu, 1),
        "estimated_ram": round(projected_ram, 1),
        "estimated_cpu_delta": round(est_cpu, 1),
        "estimated_ram_delta": round(est_ram_pct, 1),
        "reason": "; ".join(reasons) if reasons else "Within limits",
    }


def filter_safe_providers(
    provider_ids: List[str],
    workload: 'WorkloadSpec',
    current_cpu: float = 0.0,
    current_ram: float = 0.0,
    total_ram_mb: float = 8192.0,
) -> tuple:
    """
    Filter a list of providers, keeping only those within resource limits.

    Args:
        provider_ids: Candidate providers
        workload: WorkloadSpec
        current_cpu: Current CPU %
        current_ram: Current RAM %
        total_ram_mb: Total system RAM in MB

    Returns:
        (safe_providers: list[str], rejected: list[dict])
    """
    safe = []
    rejected = []

    for pid in provider_ids:
        result = check_resource_safety(
            pid, workload, current_cpu, current_ram, total_ram_mb
        )
        if result["safe"]:
            safe.append(pid)
        else:
            rejected.append({
                "provider_id": pid,
                "reason": result["reason"],
            })

    return safe, rejected
