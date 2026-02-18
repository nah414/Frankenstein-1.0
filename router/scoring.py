#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Provider Scoring System
Phase 3, Step 5.4: Score and rank providers for workload routing

Scoring factors:
  - Cost:         Free tier bonus, estimated execution cost
  - Speed:        Estimated execution time, queue depth
  - Accuracy:     Error rates, qubit fidelity
  - Availability: SDK installed, API status, connection state
  - Resource fit: Hardware compatibility, memory/CPU fit

Priority weight maps control which factors dominate:
  - cost mode:     0.6 cost, 0.2 speed, 0.2 accuracy
  - speed mode:    0.1 cost, 0.7 speed, 0.2 accuracy
  - accuracy mode: 0.1 cost, 0.2 speed, 0.7 accuracy
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .workload_spec import WorkloadSpec


# ============================================================================
# PRIORITY WEIGHT MAPS
# ============================================================================

PRIORITY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "cost": {
        "cost": 0.6,
        "speed": 0.2,
        "accuracy": 0.2,
    },
    "speed": {
        "cost": 0.1,
        "speed": 0.7,
        "accuracy": 0.2,
    },
    "accuracy": {
        "cost": 0.1,
        "speed": 0.2,
        "accuracy": 0.7,
    },
}


# ============================================================================
# PROVIDER CHARACTERISTICS (static knowledge base)
# ============================================================================

# Estimated relative speed: 1.0 = baseline (local CPU numpy)
# Lower is faster
_SPEED_ESTIMATES: Dict[str, float] = {
    # Local providers (fastest for small workloads)
    "local_cpu": 1.0,
    "local_simulator": 1.2,
    "qiskit_aer": 0.8,
    "cuquantum": 0.3,
    # Cloud quantum (includes queue time)
    "ibm_quantum": 5.0,
    "aws_braket": 4.5,
    "azure_quantum": 4.8,
    "google_cirq": 4.0,
    "ionq": 6.0,
    "rigetti": 5.5,
    "xanadu": 5.0,
    "dwave": 3.0,
    "quantinuum": 7.0,
    "iqm": 6.0,
    "quera": 5.5,
    "oxford": 6.5,
    "atom_computing": 6.0,
    "pasqal": 5.5,
    "aqt": 6.0,
    "nvidia_quantum_cloud": 3.5,
    # Classical accelerators
    "nvidia_cuda": 0.4,
    "amd_rocm": 0.5,
    "intel_oneapi": 0.7,
    "apple_metal": 0.5,
    "arm": 1.1,
    "risc_v": 1.3,
    "tpu": 0.3,
    "fpga": 0.6,
    "npu": 0.7,
}

# Estimated accuracy: 1.0 = perfect, 0.0 = unusable
_ACCURACY_ESTIMATES: Dict[str, float] = {
    # Simulators (perfect for supported qubit counts)
    "local_simulator": 1.0,
    "qiskit_aer": 1.0,
    "cuquantum": 1.0,
    # Cloud quantum (real hardware has noise)
    "ibm_quantum": 0.85,
    "aws_braket": 0.85,
    "azure_quantum": 0.85,
    "google_cirq": 0.88,
    "ionq": 0.92,       # Trapped-ion, high fidelity
    "rigetti": 0.82,
    "xanadu": 0.80,
    "dwave": 0.75,       # Annealing, approximate
    "quantinuum": 0.95,  # Highest fidelity trapped-ion
    "iqm": 0.83,
    "quera": 0.85,
    "oxford": 0.82,
    "atom_computing": 0.86,
    "pasqal": 0.84,
    "aqt": 0.88,
    "nvidia_quantum_cloud": 0.95,  # GPU sim = exact
    # Classical (exact computation)
    "local_cpu": 1.0,
    "nvidia_cuda": 1.0,
    "amd_rocm": 1.0,
    "intel_oneapi": 1.0,
    "apple_metal": 1.0,
    "arm": 1.0,
    "risc_v": 1.0,
    "tpu": 0.99,
    "fpga": 0.99,
    "npu": 0.98,
}

# Estimated cost: 0.0 = free, 1.0 = expensive
_COST_ESTIMATES: Dict[str, float] = {
    # Free / local
    "local_cpu": 0.0,
    "local_simulator": 0.0,
    "qiskit_aer": 0.0,
    "cuquantum": 0.0,
    # Free tier available
    "ibm_quantum": 0.2,
    "aws_braket": 0.3,
    "azure_quantum": 0.3,
    "ionq": 0.4,
    "rigetti": 0.3,
    "xanadu": 0.1,
    "dwave": 0.2,
    "aqt": 0.2,
    "quera": 0.3,
    # Paid only
    "google_cirq": 0.5,
    "quantinuum": 0.8,
    "iqm": 0.6,
    "oxford": 0.7,
    "atom_computing": 0.7,
    "pasqal": 0.6,
    "nvidia_quantum_cloud": 0.5,
    # Classical accelerators (hardware cost, not per-use)
    "nvidia_cuda": 0.0,
    "amd_rocm": 0.0,
    "intel_oneapi": 0.0,
    "apple_metal": 0.0,
    "arm": 0.0,
    "risc_v": 0.0,
    "tpu": 0.4,
    "fpga": 0.0,
    "npu": 0.0,
}


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def calculate_provider_score(
    provider_id: str,
    workload: 'WorkloadSpec',
    priority: str = "cost",
    provider_state: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Calculate a composite score for a provider given a workload.

    Args:
        provider_id: Provider identifier
        workload: WorkloadSpec describing the computation
        priority: "cost", "speed", or "accuracy"
        provider_state: Optional runtime state (sdk_installed, connected, etc.)

    Returns:
        Score from 0.0 (worst) to 1.0 (best)
    """
    weights = PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS["cost"])

    # Cost score: invert so lower cost = higher score
    raw_cost = _COST_ESTIMATES.get(provider_id, 0.5)
    cost_score = 1.0 - raw_cost

    # Speed score: invert so lower latency = higher score
    raw_speed = _SPEED_ESTIMATES.get(provider_id, 5.0)
    speed_score = max(0.0, 1.0 - (raw_speed / 10.0))

    # Accuracy score: direct mapping
    accuracy_score = _ACCURACY_ESTIMATES.get(provider_id, 0.5)

    # Availability bonus: SDK installed and/or connected
    availability_bonus = 0.0
    if provider_state:
        if provider_state.get("sdk_installed", False):
            availability_bonus += 0.05
        if provider_state.get("status") == "connected":
            availability_bonus += 0.05

    # Resource fit bonus: local providers get a boost on Tier 1
    resource_fit_bonus = 0.0
    if provider_id in ("local_cpu", "local_simulator", "qiskit_aer"):
        resource_fit_bonus = 0.1
        # But penalize if workload exceeds local capacity
        if workload.qubit_count > 20:
            resource_fit_bonus = -0.2

    # Weighted composite
    composite = (
        weights["cost"] * cost_score
        + weights["speed"] * speed_score
        + weights["accuracy"] * accuracy_score
        + availability_bonus
        + resource_fit_bonus
    )

    return round(max(0.0, min(1.0, composite)), 4)


def rank_providers(
    provider_ids: List[str],
    workload: 'WorkloadSpec',
    priority: str = "cost",
    provider_states: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Rank a list of providers by score for a given workload.

    Args:
        provider_ids: List of provider IDs to rank
        workload: WorkloadSpec describing the computation
        priority: "cost", "speed", or "accuracy"
        provider_states: Optional dict of provider_id -> state dict

    Returns:
        List of dicts with 'provider_id', 'score', 'rank' sorted descending
    """
    scored = []
    for pid in provider_ids:
        state = (provider_states or {}).get(pid)
        score = calculate_provider_score(pid, workload, priority, state)
        scored.append({
            "provider_id": pid,
            "score": score,
        })

    # Sort descending by score (deterministic: break ties alphabetically)
    scored.sort(key=lambda x: (-x["score"], x["provider_id"]))

    for i, entry in enumerate(scored):
        entry["rank"] = i + 1

    return scored
