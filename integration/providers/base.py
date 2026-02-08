#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Provider Adapter Base Class
Phase 3, Step 4: Universal adapter interface for ALL providers

Supports:
- 19 Quantum Providers (16 hardware + 3 simulators)
- 12 Classical Hardware Types (CPUs, GPUs, Accelerators)

All provider adapters inherit from this base class.
Ensures consistent API across quantum and classical providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import time


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS - Provider Classification
# ═══════════════════════════════════════════════════════════════════════════

class ProviderCategory(Enum):
    """High-level provider category"""
    QUANTUM_CLOUD = "quantum_cloud"           # Cloud quantum platforms
    QUANTUM_HARDWARE = "quantum_hardware"     # Direct hardware access
    QUANTUM_SIMULATOR = "quantum_simulator"   # Local/GPU simulators
    CLASSICAL_CPU = "classical_cpu"           # CPU compute
    CLASSICAL_GPU = "classical_gpu"           # GPU compute
    CLASSICAL_ACCELERATOR = "classical_accel" # TPU, FPGA, NPU


class QuantumTechnology(Enum):
    """Quantum hardware technology type"""
    SUPERCONDUCTING = "superconducting"       # IBM, Google, Rigetti, IQM, OQC
    TRAPPED_ION = "trapped_ion"               # IonQ, Quantinuum, AQT
    NEUTRAL_ATOM = "neutral_atom"             # QuEra, Pasqal, Atom Computing
    PHOTONIC = "photonic"                     # Xanadu
    ANNEALING = "annealing"                   # D-Wave
    SIMULATION = "simulation"                 # Local simulators
    

class ClassicalArchitecture(Enum):
    """Classical hardware architecture"""
    X86_INTEL = "x86_intel"
    X86_AMD = "x86_amd"
    ARM = "arm"
    APPLE_SILICON = "apple_silicon"
    RISC_V = "risc_v"
    CUDA = "cuda"
    ROCM = "rocm"
    ONEAPI = "oneapi"
    METAL = "metal"
    TPU = "tpu"
    FPGA = "fpga"
    NPU = "npu"


class JobStatus(Enum):
    """Standard job status across all providers"""
    QUEUED = "queued"               # Job submitted, waiting in queue
    VALIDATING = "validating"       # Provider validating circuit/payload
    RUNNING = "running"             # Actively executing
    COMPLETED = "completed"         # Finished successfully
    FAILED = "failed"               # Execution failed
    CANCELLED = "cancelled"         # User cancelled
    TIMED_OUT = "timed_out"        # Exceeded time limit


class ProviderStatus(Enum):
    """Provider connection status"""
    UNINITIALIZED = "uninitialized"     # Not yet initialized
    SDK_MISSING = "sdk_missing"         # SDK not installed
    AVAILABLE = "available"             # SDK installed, ready to connect
    CONNECTING = "connecting"           # Connection in progress
    AUTHENTICATED = "authenticated"     # Connected and authenticated
    DEGRADED = "degraded"               # Connected but experiencing issues
    ERROR = "error"                     # Connection error
    OFFLINE = "offline"                 # No network / provider down



# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES - Job Handling
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class JobResult:
    """Standard job result format across all providers"""
    job_id: str
    status: JobStatus
    provider_id: str
    backend_name: str = ""
    
    # Result data (varies by provider type)
    output: Optional[Any] = None              # Measurements, counts, array data
    error_message: Optional[str] = None       # Error details if failed
    
    # Metadata
    submitted_at: float = 0.0                 # Unix timestamp
    started_at: float = 0.0
    completed_at: float = 0.0
    
    # Provider-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.submitted_at == 0.0:
            self.submitted_at = time.time()
    
    @property
    def execution_time(self) -> float:
        """Total execution time in seconds"""
        if self.completed_at > 0 and self.started_at > 0:
            return self.completed_at - self.started_at
        return 0.0
    
    @property
    def queue_time(self) -> float:
        """Time spent in queue (seconds)"""
        if self.started_at > 0 and self.submitted_at > 0:
            return self.started_at - self.submitted_at
        return 0.0


@dataclass
class BackendInfo:
    """Information about a compute backend"""
    name: str
    provider_id: str
    backend_type: str                         # "simulator", "qpu", "cpu", "gpu"
    
    # Quantum-specific
    num_qubits: int = 0
    quantum_technology: Optional[QuantumTechnology] = None
    basis_gates: List[str] = field(default_factory=list)
    coupling_map: List[List[int]] = field(default_factory=list)
    
    # Classical-specific
    compute_units: int = 0                    # CPU cores, GPU SMs, etc.
    memory_gb: float = 0.0
    architecture: Optional[ClassicalArchitecture] = None
    
    # Performance metrics
    queue_depth: int = 0
    avg_queue_time_sec: float = 0.0
    is_available: bool = True
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)



# ═══════════════════════════════════════════════════════════════════════════
# BASE ADAPTER CLASS
# ═══════════════════════════════════════════════════════════════════════════

class ProviderAdapter(ABC):
    """
    Universal base class for ALL provider adapters.
    
    Design Principles:
    - **LAZY INITIALIZATION**: Adapter creation does NOT trigger connection
    - **STATELESS**: Connection state tracked in registry, not adapter
    - **MINIMAL**: Only essential methods required
    - **SAFE**: All errors return gracefully, no crashes
    - **UNIVERSAL**: Works for quantum AND classical providers
    
    Supported Provider Types:
    - Quantum Cloud (IBM, AWS Braket, Azure, Google, NVIDIA)
    - Quantum Hardware (IonQ, Rigetti, Quantinuum, D-Wave, etc.)
    - Quantum Simulators (Local, Qiskit Aer, cuQuantum)
    - Classical CPU (Intel, AMD, ARM, Apple, RISC-V)
    - Classical GPU (NVIDIA CUDA, AMD ROCm, Intel oneAPI, Apple Metal)
    - Classical Accelerators (TPU, FPGA, NPU)
    """
    
    def __init__(
        self,
        provider_id: str,
        category: ProviderCategory,
        credentials: Optional[Dict[str, Any]] = None
    ):

        """
        Initialize adapter (does NOT connect).
        
        Args:
            provider_id: Unique provider identifier (e.g., "ibm_quantum")
            category: Provider category enum
            credentials: Optional credentials dict
        """
        self.provider_id = provider_id
        self.category = category
        self._credentials = credentials or {}
        self.status = ProviderStatus.UNINITIALIZED
        self.error_message: Optional[str] = None
        self._backends: List[BackendInfo] = []
        self._jobs: Dict[str, JobResult] = {}
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to provider."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Close connection and release resources."""
        pass
    
    @abstractmethod
    def get_backends(self) -> List[BackendInfo]:
        """List available compute backends."""
        pass

    
    @abstractmethod
    def submit_job(self, payload: Any, backend_name: str, **kwargs) -> Optional[str]:
        """Submit a job to the provider."""
        pass
    
    @abstractmethod
    def get_job_status(self, job_id: str) -> JobStatus:
        """Check status of a submitted job."""
        pass
    
    @abstractmethod
    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Retrieve results from a completed job."""
        pass
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job (if supported)."""
        return False
    
    def estimate_cost(self, payload: Any, backend_name: str, **kwargs) -> Dict[str, Any]:
        """Estimate job cost before submission."""
        return {"currency": "USD", "amount": 0.0, "unit": "free"}
    
    @property
    def is_connected(self) -> bool:
        """Check if adapter is currently connected."""
        return self.status == ProviderStatus.AUTHENTICATED
    
    @property
    def is_quantum(self) -> bool:
        """Check if this is a quantum provider."""
        return self.category in [
            ProviderCategory.QUANTUM_CLOUD,
            ProviderCategory.QUANTUM_HARDWARE,
            ProviderCategory.QUANTUM_SIMULATOR
        ]
