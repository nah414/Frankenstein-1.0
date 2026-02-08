#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Routing Decision Engine
Phase 3, Step 5.3: Core routing logic for workload->provider matching

Routing rules:
  Quantum workloads:
    <=5 qubits   -> local simulators (local_simulator, qiskit_aer)
    6-29 qubits  -> IBM Quantum, AWS Braket, Azure Quantum
    30+ qubits   -> IonQ, Rigetti, QuEra, Atom Computing

  Classical workloads:
    NVIDIA GPU detected -> nvidia_cuda, cuquantum
    Apple Silicon       -> apple_metal
    AMD GPU             -> amd_rocm
    Intel CPU           -> intel_oneapi, local_cpu
    Default             -> local_cpu (numpy/scipy)

  Hybrid workloads:
    Splits quantum and classical components, routes each independently.
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .workload_spec import WorkloadSpec

logger = logging.getLogger("frankenstein.router.decision")


# ============================================================================
# PROVIDER GROUPS (static classification)
# ============================================================================

LOCAL_QUANTUM_SIMULATORS = ["local_simulator", "qiskit_aer"]
GPU_QUANTUM_SIMULATORS = ["cuquantum"]
SMALL_CIRCUIT_CLOUD = ["ibm_quantum", "aws_braket", "azure_quantum", "google_cirq"]
MEDIUM_CIRCUIT_CLOUD = ["ibm_quantum", "aws_braket", "azure_quantum", "rigetti", "xanadu"]
LARGE_CIRCUIT_CLOUD = ["ionq", "rigetti", "quera", "atom_computing", "pasqal",
                       "quantinuum", "nvidia_quantum_cloud"]
ANNEALING_PROVIDERS = ["dwave"]

LOCAL_CPU_PROVIDERS = ["local_cpu"]
NVIDIA_GPU_PROVIDERS = ["nvidia_cuda"]
AMD_GPU_PROVIDERS = ["amd_rocm"]
INTEL_PROVIDERS = ["intel_oneapi"]
APPLE_PROVIDERS = ["apple_metal"]

FREE_TIER_QUANTUM = [
    "local_simulator", "qiskit_aer", "ibm_quantum", "aws_braket",
    "azure_quantum", "xanadu", "dwave", "ionq", "rigetti", "aqt", "quera",
]
FREE_TIER_CLASSICAL = [
    "local_cpu", "nvidia_cuda", "amd_rocm", "intel_oneapi", "apple_metal",
    "arm", "risc_v", "fpga", "npu",
]


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_quantum_workload(
    workload: 'WorkloadSpec',
    has_nvidia_gpu: bool = False,
    available_providers: Optional[List[str]] = None,
) -> List[str]:
    """
    Select providers for a quantum workload based on qubit count.

    Args:
        workload: WorkloadSpec with qubit_count and circuit_depth
        has_nvidia_gpu: Whether NVIDIA GPU is detected
        available_providers: Optional whitelist of available provider IDs

    Returns:
        Ordered list of candidate provider IDs
    """
    qubits = workload.qubit_count
    candidates = []

    if qubits <= 5:
        # Small circuits: local simulators are fast and free
        candidates = list(LOCAL_QUANTUM_SIMULATORS)
        if has_nvidia_gpu:
            candidates = list(GPU_QUANTUM_SIMULATORS) + candidates

    elif qubits <= 20:
        # Medium circuits: still possible locally on Tier 1
        candidates = list(LOCAL_QUANTUM_SIMULATORS)
        if has_nvidia_gpu:
            candidates = list(GPU_QUANTUM_SIMULATORS) + candidates
        # Add cloud as fallback
        candidates.extend(SMALL_CIRCUIT_CLOUD)

    elif qubits <= 29:
        # Too large for local sim on 8GB RAM
        candidates = list(MEDIUM_CIRCUIT_CLOUD)
        if has_nvidia_gpu:
            candidates = list(GPU_QUANTUM_SIMULATORS) + candidates

    else:
        # 30+ qubits: need real hardware or powerful simulators
        candidates = list(LARGE_CIRCUIT_CLOUD)

    # D-Wave for annealing workloads
    if workload.constraints.get("annealing", False):
        candidates = list(ANNEALING_PROVIDERS) + candidates

    # Filter by availability if provided
    if available_providers is not None:
        candidates = [p for p in candidates if p in available_providers]

    # Ensure at least one fallback
    if not candidates:
        candidates = ["local_simulator", "local_cpu"]

    return _deduplicate(candidates)


def route_classical_workload(
    workload: 'WorkloadSpec',
    gpu_vendor: str = "none",
    cpu_vendor: str = "intel",
    available_providers: Optional[List[str]] = None,
) -> List[str]:
    """
    Select providers for a classical workload based on hardware.

    Args:
        workload: WorkloadSpec with CPU/memory requirements
        gpu_vendor: Detected GPU vendor ("nvidia", "amd", "intel", "apple", "none")
        cpu_vendor: Detected CPU vendor ("intel", "amd", "arm", "apple")
        available_providers: Optional whitelist

    Returns:
        Ordered list of candidate provider IDs
    """
    candidates = []

    # GPU-accelerated options first
    if gpu_vendor == "nvidia":
        candidates.extend(NVIDIA_GPU_PROVIDERS)
    elif gpu_vendor == "amd":
        candidates.extend(AMD_GPU_PROVIDERS)
    elif gpu_vendor == "apple":
        candidates.extend(APPLE_PROVIDERS)

    # CPU-optimized options
    if cpu_vendor in ("intel", "x86_intel"):
        candidates.extend(INTEL_PROVIDERS)
    elif cpu_vendor in ("arm", "apple"):
        candidates.append("arm")

    # Always include local CPU as baseline
    candidates.extend(LOCAL_CPU_PROVIDERS)

    # Filter by availability
    if available_providers is not None:
        candidates = [p for p in candidates if p in available_providers]

    if not candidates:
        candidates = ["local_cpu"]

    return _deduplicate(candidates)


def route_hybrid_workload(
    workload: 'WorkloadSpec',
    has_nvidia_gpu: bool = False,
    gpu_vendor: str = "none",
    cpu_vendor: str = "intel",
    available_providers: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """
    Route a hybrid workload by splitting quantum and classical components.

    Returns:
        Dict with 'quantum' and 'classical' provider lists
    """
    quantum_candidates = route_quantum_workload(
        workload, has_nvidia_gpu, available_providers
    )
    classical_candidates = route_classical_workload(
        workload, gpu_vendor, cpu_vendor, available_providers
    )

    return {
        "quantum": quantum_candidates,
        "classical": classical_candidates,
    }


def route_data_synthesis(
    workload: 'WorkloadSpec',
    gpu_vendor: str = "none",
    cpu_vendor: str = "intel",
    available_providers: Optional[List[str]] = None,
) -> List[str]:
    """
    Route a data synthesis workload (primarily classical with optional quantum).

    Data synthesis benefits from GPU acceleration but works on CPU.
    """
    candidates = route_classical_workload(
        workload, gpu_vendor, cpu_vendor, available_providers
    )

    # If synthesis involves quantum elements
    if workload.qubit_count > 0:
        quantum = route_quantum_workload(
            workload, gpu_vendor == "nvidia", available_providers
        )
        # Interleave quantum providers
        candidates = quantum[:2] + candidates

    return _deduplicate(candidates)


# ============================================================================
# FILTER FUNCTIONS
# ============================================================================

def filter_by_capabilities(
    provider_ids: List[str],
    workload: 'WorkloadSpec',
    provider_info: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Remove providers incompatible with the workload.

    Args:
        provider_ids: Candidate providers
        workload: WorkloadSpec
        provider_info: Optional dict of provider_id -> ProviderInfo data

    Returns:
        Filtered list of compatible providers
    """
    if not provider_info:
        return provider_ids  # Can't filter without info

    compatible = []
    for pid in provider_ids:
        info = provider_info.get(pid)
        if not info:
            compatible.append(pid)  # Unknown provider, let it through
            continue

        # Check qubit limit
        max_qubits = info.get("max_qubits", 0)
        if max_qubits > 0 and workload.qubit_count > max_qubits:
            logger.debug(
                "Filtered %s: workload needs %d qubits, max is %d",
                pid, workload.qubit_count, max_qubits
            )
            continue

        compatible.append(pid)

    return compatible


def apply_priority_filter(
    provider_ids: List[str],
    priority: str = "cost",
) -> List[str]:
    """
    Reorder providers based on priority mode.

    In cost mode: free tier providers first.
    In speed mode: local/fast providers first.
    In accuracy mode: high-fidelity providers first.
    """
    if priority == "cost":
        free = [p for p in provider_ids if p in FREE_TIER_QUANTUM + FREE_TIER_CLASSICAL]
        paid = [p for p in provider_ids if p not in free]
        return free + paid

    if priority == "speed":
        local = [p for p in provider_ids
                 if p in LOCAL_CPU_PROVIDERS + LOCAL_QUANTUM_SIMULATORS + GPU_QUANTUM_SIMULATORS
                 + NVIDIA_GPU_PROVIDERS + AMD_GPU_PROVIDERS + APPLE_PROVIDERS]
        cloud = [p for p in provider_ids if p not in local]
        return local + cloud

    # accuracy mode: keep original order (scoring handles ranking)
    return provider_ids


# ============================================================================
# HELPERS
# ============================================================================

def _deduplicate(items: List[str]) -> List[str]:
    """Remove duplicates while preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
