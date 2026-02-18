#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Fallback & Error Handling
Phase 3, Step 5.6: Fallback chains for provider failures

Every provider has a defined fallback chain that terminates
at a safe default (local_cpu or local_simulator).

Error scenarios handled:
  - API auth failure
  - Rate limit exceeded
  - Resource unavailable
  - Network timeout
  - SDK not installed
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger("frankenstein.router.fallback")


# ============================================================================
# FALLBACK CHAINS
# ============================================================================

# Maps provider_id -> ordered list of fallback providers
# Every chain MUST terminate at a universally available provider
_FALLBACK_CHAINS: Dict[str, List[str]] = {
    # Quantum Cloud -> local simulators -> pure Python
    "ibm_quantum": ["qiskit_aer", "local_simulator", "local_cpu"],
    "aws_braket": ["qiskit_aer", "local_simulator", "local_cpu"],
    "azure_quantum": ["qiskit_aer", "local_simulator", "local_cpu"],
    "google_cirq": ["qiskit_aer", "local_simulator", "local_cpu"],
    "ionq": ["aws_braket", "qiskit_aer", "local_simulator", "local_cpu"],
    "rigetti": ["aws_braket", "qiskit_aer", "local_simulator", "local_cpu"],
    "xanadu": ["qiskit_aer", "local_simulator", "local_cpu"],
    "dwave": ["local_simulator", "local_cpu"],
    "quantinuum": ["azure_quantum", "qiskit_aer", "local_simulator", "local_cpu"],
    "iqm": ["qiskit_aer", "local_simulator", "local_cpu"],
    "quera": ["aws_braket", "qiskit_aer", "local_simulator", "local_cpu"],
    "oxford": ["qiskit_aer", "local_simulator", "local_cpu"],
    "atom_computing": ["qiskit_aer", "local_simulator", "local_cpu"],
    "pasqal": ["qiskit_aer", "local_simulator", "local_cpu"],
    "aqt": ["qiskit_aer", "local_simulator", "local_cpu"],
    "nvidia_quantum_cloud": ["cuquantum", "qiskit_aer", "local_simulator", "local_cpu"],

    # Quantum Local -> lighter simulators
    "local_simulator": ["local_cpu"],
    "qiskit_aer": ["local_simulator", "local_cpu"],
    "cuquantum": ["qiskit_aer", "local_simulator", "local_cpu"],

    # Classical GPU -> CPU optimized -> pure Python
    "nvidia_cuda": ["intel_oneapi", "local_cpu"],
    "amd_rocm": ["intel_oneapi", "local_cpu"],
    "apple_metal": ["local_cpu"],

    # Classical Accelerators -> CPU
    "intel_oneapi": ["local_cpu"],
    "arm": ["local_cpu"],
    "risc_v": ["local_cpu"],
    "tpu": ["nvidia_cuda", "local_cpu"],
    "fpga": ["local_cpu"],
    "npu": ["intel_oneapi", "local_cpu"],

    # Terminal fallback
    "local_cpu": [],  # No fallback needed — always available
}


# ============================================================================
# ERROR CLASSIFICATION
# ============================================================================

class RoutingError:
    """Classified routing error with context."""

    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT = "rate_limit"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    NETWORK_TIMEOUT = "network_timeout"
    SDK_MISSING = "sdk_missing"
    SAFETY_LIMIT = "safety_limit"
    UNKNOWN = "unknown"

    def __init__(self, error_type: str, provider_id: str,
                 message: str = "", original_error: Optional[Exception] = None):
        self.error_type = error_type
        self.provider_id = provider_id
        self.message = message
        self.original_error = original_error

    def __str__(self):
        return f"[{self.error_type}] {self.provider_id}: {self.message}"


def classify_error(error: Exception, provider_id: str) -> RoutingError:
    """
    Classify an exception into a RoutingError type.

    Args:
        error: The exception that occurred
        provider_id: Which provider failed

    Returns:
        RoutingError with classification
    """
    msg = str(error).lower()

    if any(kw in msg for kw in ("auth", "credential", "token", "forbidden", "401", "403")):
        return RoutingError(RoutingError.AUTH_FAILURE, provider_id,
                            str(error), error)

    if any(kw in msg for kw in ("rate limit", "throttle", "429", "too many")):
        return RoutingError(RoutingError.RATE_LIMIT, provider_id,
                            str(error), error)

    if any(kw in msg for kw in ("timeout", "timed out", "connection refused")):
        return RoutingError(RoutingError.NETWORK_TIMEOUT, provider_id,
                            str(error), error)

    if any(kw in msg for kw in ("not found", "unavailable", "offline", "503")):
        return RoutingError(RoutingError.RESOURCE_UNAVAILABLE, provider_id,
                            str(error), error)

    if any(kw in msg for kw in ("import", "module", "no module", "sdk")):
        return RoutingError(RoutingError.SDK_MISSING, provider_id,
                            str(error), error)

    return RoutingError(RoutingError.UNKNOWN, provider_id,
                        str(error), error)


# ============================================================================
# FALLBACK FUNCTIONS
# ============================================================================

def get_fallback_chain(primary_provider: str) -> List[str]:
    """
    Get the ordered fallback chain for a provider.

    Args:
        primary_provider: The provider that failed

    Returns:
        List of fallback provider IDs (may be empty for terminal providers)
    """
    return list(_FALLBACK_CHAINS.get(primary_provider, ["local_cpu"]))


def handle_routing_error(
    error: Exception,
    provider_id: str,
    workload_type: str = "unknown",
) -> Dict:
    """
    Handle a routing error by selecting an appropriate fallback.

    Args:
        error: The exception that occurred
        provider_id: Provider that failed
        workload_type: Type of workload for context

    Returns:
        Dict with fallback_provider, error_info, and user_message
    """
    classified = classify_error(error, provider_id)
    chain = get_fallback_chain(provider_id)

    logger.warning("Routing error for %s: %s", provider_id, classified)

    # Select first available fallback
    fallback = chain[0] if chain else "local_cpu"

    # Build user-facing message
    user_messages = {
        RoutingError.AUTH_FAILURE: (
            f"Authentication failed for {provider_id}. "
            f"Check credentials with: credentials show {provider_id}"
        ),
        RoutingError.RATE_LIMIT: (
            f"Rate limit reached for {provider_id}. "
            f"Falling back to {fallback}."
        ),
        RoutingError.NETWORK_TIMEOUT: (
            f"Network timeout connecting to {provider_id}. "
            f"Falling back to {fallback}."
        ),
        RoutingError.RESOURCE_UNAVAILABLE: (
            f"Provider {provider_id} is currently unavailable. "
            f"Falling back to {fallback}."
        ),
        RoutingError.SDK_MISSING: (
            f"SDK not installed for {provider_id}. "
            f"Install with: pip install <package>. "
            f"Falling back to {fallback}."
        ),
        RoutingError.SAFETY_LIMIT: (
            f"Resource limits would be exceeded with {provider_id}. "
            f"Falling back to {fallback}."
        ),
    }

    user_msg = user_messages.get(
        classified.error_type,
        f"Error with {provider_id}: {classified.message}. "
        f"Falling back to {fallback}."
    )

    return {
        "fallback_provider": fallback,
        "fallback_chain": chain,
        "error_type": classified.error_type,
        "error_message": classified.message,
        "user_message": user_msg,
        "original_provider": provider_id,
    }


def get_safe_default(workload_type: str = "unknown") -> str:
    """
    Get the ultimate safe default provider for any workload.

    Quantum workloads fall back to local_simulator.
    Everything else falls back to local_cpu.
    """
    if "quantum" in workload_type.lower():
        return "local_simulator"
    return "local_cpu"
