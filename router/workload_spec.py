#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Workload Specification Schema
Phase 3, Step 5.2: Defines workload types and specifications for routing

Workload specs describe WHAT needs to be computed so the router
can decide WHERE to compute it.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional


# ============================================================================
# WORKLOAD CLASSIFICATION
# ============================================================================

class WorkloadType(Enum):
    """Types of computation workloads"""
    QUANTUM_SIMULATION = "quantum_simulation"
    CLASSICAL_OPTIMIZATION = "classical_optimization"
    HYBRID_COMPUTATION = "hybrid_computation"
    DATA_SYNTHESIS = "data_synthesis"


class WorkloadPriority(Enum):
    """Optimization priority for routing decisions"""
    COST = "cost"           # Minimize cost (prefer free/local)
    SPEED = "speed"         # Minimize execution time
    ACCURACY = "accuracy"   # Maximize result quality


# ============================================================================
# WORKLOAD SPECIFICATION
# ============================================================================

# Tier 1 hardware limits (Dell i3 8th Gen, 4 cores, 8GB RAM)
_TIER1_MAX_QUBITS_LOCAL = 20       # RAM limit for local simulation
_TIER1_MAX_CPU_THREADS = 3         # Leave 1 core for OS
_TIER1_MAX_MEMORY_MB = 5632        # ~5.5GB (70% of 8GB)
_TIER1_MAX_CIRCUIT_DEPTH = 1000    # Reasonable for local sim


@dataclass
class WorkloadSpec:
    """
    Specification for a compute workload.

    Describes resource requirements so the router can match
    the workload to an appropriate provider.
    """
    workload_type: WorkloadType = WorkloadType.CLASSICAL_OPTIMIZATION
    qubit_count: int = 0
    circuit_depth: int = 0
    classical_cpu_threads: int = 1
    memory_requirement_mb: int = 100
    priority: str = "cost"
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Optional metadata
    description: str = ""
    timeout_seconds: int = 300

    def __post_init__(self):
        """Validate and normalize inputs."""
        if isinstance(self.workload_type, str):
            self.workload_type = WorkloadType(self.workload_type)
        if self.qubit_count < 0:
            self.qubit_count = 0
        if self.circuit_depth < 0:
            self.circuit_depth = 0
        if self.classical_cpu_threads < 1:
            self.classical_cpu_threads = 1
        if self.memory_requirement_mb < 1:
            self.memory_requirement_mb = 1
        if self.priority not in ("cost", "speed", "accuracy"):
            self.priority = "cost"

    def validate_tier1(self) -> tuple:
        """
        Check if this workload fits Tier 1 hardware limits.

        Returns:
            (is_valid: bool, issues: list[str])
        """
        issues = []

        if self.classical_cpu_threads > _TIER1_MAX_CPU_THREADS:
            issues.append(
                f"Requested {self.classical_cpu_threads} threads, "
                f"Tier 1 max is {_TIER1_MAX_CPU_THREADS}"
            )

        if self.memory_requirement_mb > _TIER1_MAX_MEMORY_MB:
            issues.append(
                f"Requested {self.memory_requirement_mb}MB RAM, "
                f"Tier 1 max is {_TIER1_MAX_MEMORY_MB}MB"
            )

        if self.qubit_count > _TIER1_MAX_QUBITS_LOCAL:
            issues.append(
                f"Local simulation of {self.qubit_count} qubits exceeds "
                f"Tier 1 limit of {_TIER1_MAX_QUBITS_LOCAL} qubits "
                f"(requires cloud provider)"
            )

        if self.circuit_depth > _TIER1_MAX_CIRCUIT_DEPTH:
            issues.append(
                f"Circuit depth {self.circuit_depth} exceeds "
                f"Tier 1 recommendation of {_TIER1_MAX_CIRCUIT_DEPTH}"
            )

        return len(issues) == 0, issues

    def requires_quantum(self) -> bool:
        """Check if this workload needs a quantum provider."""
        return self.workload_type in (
            WorkloadType.QUANTUM_SIMULATION,
            WorkloadType.HYBRID_COMPUTATION,
        ) or self.qubit_count > 0

    def requires_gpu(self) -> bool:
        """Check if this workload would benefit from GPU acceleration."""
        return (
            self.qubit_count > 15
            or self.memory_requirement_mb > 2048
            or self.constraints.get("gpu_required", False)
        )

    def estimated_memory_mb(self) -> int:
        """
        Estimate actual memory usage based on workload parameters.
        Quantum state vector: 2^n * 16 bytes (complex128).
        """
        if self.qubit_count > 0:
            # State vector memory: 2^n complex numbers * 16 bytes each
            state_vector_mb = (2 ** self.qubit_count * 16) / (1024 * 1024)
            # Circuit operations add ~50% overhead
            quantum_mb = int(state_vector_mb * 1.5)
            return max(self.memory_requirement_mb, quantum_mb)
        return self.memory_requirement_mb

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['workload_type'] = self.workload_type.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkloadSpec':
        """Create WorkloadSpec from a dictionary."""
        if 'workload_type' in data and isinstance(data['workload_type'], str):
            data['workload_type'] = WorkloadType(data['workload_type'])
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    def summary(self) -> str:
        """Human-readable summary of this workload."""
        parts = [f"Type: {self.workload_type.value}"]
        if self.qubit_count > 0:
            parts.append(f"Qubits: {self.qubit_count}")
        if self.circuit_depth > 0:
            parts.append(f"Depth: {self.circuit_depth}")
        parts.append(f"Threads: {self.classical_cpu_threads}")
        parts.append(f"Memory: {self.memory_requirement_mb}MB")
        parts.append(f"Priority: {self.priority}")
        return " | ".join(parts)
