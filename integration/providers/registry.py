#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Provider Registry
Phase 3, Step 2: Universal Provider Catalog

Central registry for all quantum and classical compute providers.
ALL providers are LAZY-LOADED — nothing instantiates until explicitly called.

Supported Quantum Providers:
  IBM Quantum, AWS Braket, Azure Quantum, Google Cirq,
  IonQ, Rigetti, Xanadu (PennyLane), D-Wave, Local Simulator

Supported Classical Providers:
  Local CPU, NVIDIA CUDA, AMD ROCm, Intel oneAPI, Apple Metal

Safety: No credentials stored in code. All connections require explicit user action.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


# ============================================================================
# ENUMS AND CLASSIFICATION
# ============================================================================

class ProviderType(Enum):
    """Provider category"""
    QUANTUM_CLOUD = "quantum_cloud"
    QUANTUM_LOCAL = "quantum_local"
    CLASSICAL_CPU = "classical_cpu"
    CLASSICAL_GPU = "classical_gpu"
    CLASSICAL_ACCEL = "classical_accelerator"


class ProviderStatus(Enum):
    """Connection status"""
    AVAILABLE = "available"       # SDK installed, not connected
    CONNECTED = "connected"       # Actively connected
    DEGRADED = "degraded"         # Connected but experiencing issues
    UNAVAILABLE = "unavailable"   # SDK not installed
    ERROR = "error"               # Connection failed
    NOT_CONFIGURED = "not_configured"  # Needs credentials/setup


class ProviderCapability(Enum):
    """What a provider can do"""
    GATE_BASED = "gate_based"
    ANNEALING = "annealing"
    SIMULATION = "simulation"
    TENSOR_NETWORK = "tensor_network"
    CPU_COMPUTE = "cpu_compute"
    GPU_COMPUTE = "gpu_compute"
    TPU_COMPUTE = "tpu_compute"
    FPGA_COMPUTE = "fpga_compute"


# ============================================================================
# PROVIDER DATA CLASSES
# ============================================================================

@dataclass
class ProviderInfo:
    """Static information about a provider"""
    id: str                          # Unique identifier (e.g., "ibm_quantum")
    name: str                        # Display name (e.g., "IBM Quantum")
    provider_type: ProviderType
    capabilities: List[ProviderCapability] = field(default_factory=list)
    sdk_package: str = ""            # pip package name (e.g., "qiskit")
    sdk_import: str = ""             # Python import check (e.g., "qiskit")
    description: str = ""
    website: str = ""
    free_tier: bool = False
    max_qubits: int = 0              # 0 = N/A or unlimited
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['provider_type'] = self.provider_type.value
        result['capabilities'] = [c.value for c in self.capabilities]
        return result


@dataclass
class ProviderState:
    """Runtime state for a connected provider"""
    status: ProviderStatus = ProviderStatus.UNAVAILABLE
    sdk_installed: bool = False
    sdk_version: str = ""
    last_check: str = ""
    last_error: str = ""
    credentials_configured: bool = False
    connection_latency_ms: float = 0.0
    queue_depth: int = 0             # For cloud quantum providers
    available_backends: List[str] = field(default_factory=list)


# ============================================================================
# PROVIDER CATALOG — ALL KNOWN PROVIDERS
# ============================================================================

# Every provider Frankenstein knows about, defined statically.
# The adapter classes are LAZY-LOADED only when the user calls connect.

QUANTUM_PROVIDERS: Dict[str, ProviderInfo] = {
    "ibm_quantum": ProviderInfo(
        id="ibm_quantum",
        name="IBM Quantum",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED, ProviderCapability.SIMULATION],
        sdk_package="qiskit",
        sdk_import="qiskit",
        description="IBM's quantum computing platform via Qiskit",
        website="https://quantum.ibm.com",
        free_tier=True,
        max_qubits=127,
        notes="Free tier: 10 min/month. Supports real hardware + simulators."
    ),
    "aws_braket": ProviderInfo(
        id="aws_braket",
        name="AWS Braket",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED, ProviderCapability.ANNEALING, ProviderCapability.SIMULATION],
        sdk_package="amazon-braket-sdk",
        sdk_import="braket",
        description="Amazon's managed quantum computing service",
        website="https://aws.amazon.com/braket",
        free_tier=True,
        max_qubits=79,
        notes="Free tier: 1 hour simulator/month. Access to IonQ, Rigetti, D-Wave hardware."
    ),
    "azure_quantum": ProviderInfo(
        id="azure_quantum",
        name="Azure Quantum",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED, ProviderCapability.SIMULATION],
        sdk_package="azure-quantum",
        sdk_import="azure.quantum",
        description="Microsoft's quantum cloud with IonQ, Quantinuum access",
        website="https://azure.microsoft.com/en-us/products/quantum",
        free_tier=True,
        max_qubits=32,
        notes="Free credits for new accounts. Supports Q# and Qiskit."
    ),
    "google_cirq": ProviderInfo(
        id="google_cirq",
        name="Google Quantum AI",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED, ProviderCapability.SIMULATION],
        sdk_package="cirq",
        sdk_import="cirq",
        description="Google's quantum computing framework",
        website="https://quantumai.google",
        free_tier=False,
        max_qubits=72,
        notes="Sycamore processor. Research access via application."
    ),
    "ionq": ProviderInfo(
        id="ionq",
        name="IonQ",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED],
        sdk_package="cirq-ionq",
        sdk_import="cirq_ionq",
        description="Trapped-ion quantum computers with high fidelity",
        website="https://ionq.com",
        free_tier=True,
        max_qubits=36,
        notes="Accessible via AWS Braket, Azure, or direct API. Free credits available."
    ),
    "rigetti": ProviderInfo(
        id="rigetti",
        name="Rigetti Computing",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED, ProviderCapability.SIMULATION],
        sdk_package="pyquil",
        sdk_import="pyquil",
        description="Superconducting qubit platform with Forest SDK",
        website="https://www.rigetti.com",
        free_tier=True,
        max_qubits=84,
        notes="QCS access. Also available via AWS Braket."
    ),
    "xanadu": ProviderInfo(
        id="xanadu",
        name="Xanadu (PennyLane)",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.GATE_BASED, ProviderCapability.SIMULATION],
        sdk_package="pennylane",
        sdk_import="pennylane",
        description="Photonic quantum computing with PennyLane framework",
        website="https://xanadu.ai",
        free_tier=True,
        max_qubits=24,
        notes="PennyLane is hardware-agnostic. Supports auto-differentiation."
    ),
    "dwave": ProviderInfo(
        id="dwave",
        name="D-Wave",
        provider_type=ProviderType.QUANTUM_CLOUD,
        capabilities=[ProviderCapability.ANNEALING],
        sdk_package="dwave-ocean-sdk",
        sdk_import="dwave",
        description="Quantum annealing for optimization problems",
        website="https://www.dwavesys.com",
        free_tier=True,
        max_qubits=5000,
        notes="Annealing only (not gate-based). Free Leap account with 1 min/month."
    ),
    "local_simulator": ProviderInfo(
        id="local_simulator",
        name="Local Quantum Simulator",
        provider_type=ProviderType.QUANTUM_LOCAL,
        capabilities=[ProviderCapability.SIMULATION, ProviderCapability.GATE_BASED],
        sdk_package="numpy",
        sdk_import="numpy",
        description="Frankenstein's built-in quantum state simulator using NumPy",
        website="",
        free_tier=True,
        max_qubits=20,
        notes="No cloud needed. Limited by local RAM (~20 qubits on 8GB)."
    ),
}

CLASSICAL_PROVIDERS: Dict[str, ProviderInfo] = {
    "local_cpu": ProviderInfo(
        id="local_cpu",
        name="Local CPU",
        provider_type=ProviderType.CLASSICAL_CPU,
        capabilities=[ProviderCapability.CPU_COMPUTE, ProviderCapability.SIMULATION],
        sdk_package="numpy",
        sdk_import="numpy",
        description="Local CPU compute via NumPy/SciPy",
        website="",
        free_tier=True,
        notes="Always available. Performance scales with CPU tier."
    ),
    "nvidia_cuda": ProviderInfo(
        id="nvidia_cuda",
        name="NVIDIA CUDA",
        provider_type=ProviderType.CLASSICAL_GPU,
        capabilities=[ProviderCapability.GPU_COMPUTE, ProviderCapability.SIMULATION],
        sdk_package="cupy",
        sdk_import="cupy",
        description="NVIDIA GPU acceleration via CUDA toolkit",
        website="https://developer.nvidia.com/cuda-toolkit",
        free_tier=True,
        notes="Requires NVIDIA GPU with CUDA support. CuPy or PyTorch CUDA."
    ),
    "amd_rocm": ProviderInfo(
        id="amd_rocm",
        name="AMD ROCm",
        provider_type=ProviderType.CLASSICAL_GPU,
        capabilities=[ProviderCapability.GPU_COMPUTE],
        sdk_package="torch",
        sdk_import="torch",
        description="AMD GPU acceleration via ROCm platform",
        website="https://www.amd.com/en/products/software/rocm.html",
        free_tier=True,
        notes="Requires AMD GPU with ROCm support. PyTorch ROCm backend."
    ),
    "intel_oneapi": ProviderInfo(
        id="intel_oneapi",
        name="Intel oneAPI",
        provider_type=ProviderType.CLASSICAL_ACCEL,
        capabilities=[ProviderCapability.CPU_COMPUTE, ProviderCapability.GPU_COMPUTE],
        sdk_package="dpnp",
        sdk_import="dpnp",
        description="Intel accelerated computing via oneAPI (CPU + Intel GPU)",
        website="https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html",
        free_tier=True,
        notes="Optimizes NumPy-style code for Intel hardware. Free toolkit."
    ),
    "apple_metal": ProviderInfo(
        id="apple_metal",
        name="Apple Metal",
        provider_type=ProviderType.CLASSICAL_GPU,
        capabilities=[ProviderCapability.GPU_COMPUTE],
        sdk_package="torch",
        sdk_import="torch",
        description="Apple Silicon GPU acceleration via Metal Performance Shaders",
        website="https://developer.apple.com/metal/",
        free_tier=True,
        notes="macOS only. PyTorch MPS backend for M1/M2/M3 chips."
    ),
}

# Combined catalog
ALL_PROVIDERS: Dict[str, ProviderInfo] = {**QUANTUM_PROVIDERS, **CLASSICAL_PROVIDERS}


# ============================================================================
# PROVIDER REGISTRY ENGINE
# ============================================================================

class ProviderRegistry:
    """
    Central registry for all compute providers.
    
    LAZY-LOADING: Provider adapters are NOT instantiated at startup.
    They are only created when the user explicitly calls check() or connect().
    This keeps startup fast and memory low on Tier 1 hardware.
    
    Safety:
    - No credentials stored in code
    - All connections require explicit user action
    - SDK availability checked via import, not installation
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
        
        # Runtime state for each provider (populated on-demand)
        self._states: Dict[str, ProviderState] = {}
        
        # Active adapter instances (lazy-loaded)
        self._adapters: Dict[str, Any] = {}
        
        # Scan history
        self._last_full_scan: Optional[str] = None
    
    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[ProviderInfo]:
        """List all known providers, optionally filtered by type."""
        providers = list(ALL_PROVIDERS.values())
        if provider_type:
            providers = [p for p in providers if p.provider_type == provider_type]
        return providers
    
    def get_provider(self, provider_id: str) -> Optional[ProviderInfo]:
        """Get info for a specific provider by ID."""
        return ALL_PROVIDERS.get(provider_id)

    def get_state(self, provider_id: str) -> ProviderState:
        """Get runtime state for a provider (checks SDK on first call)."""
        if provider_id not in self._states:
            self._states[provider_id] = self._check_sdk(provider_id)
        return self._states[provider_id]
    
    def _check_sdk(self, provider_id: str) -> ProviderState:
        """Check if a provider's SDK is installed (lazy, no connect)."""
        info = ALL_PROVIDERS.get(provider_id)
        if not info:
            return ProviderState(status=ProviderStatus.ERROR, last_error="Unknown provider")
        
        state = ProviderState()
        state.last_check = datetime.now().isoformat()
        
        if not info.sdk_import:
            # No SDK needed (e.g., local simulator uses numpy)
            state.sdk_installed = True
            state.status = ProviderStatus.AVAILABLE
            return state
        
        try:
            import importlib
            mod = importlib.import_module(info.sdk_import)
            state.sdk_installed = True
            state.sdk_version = getattr(mod, '__version__', 'unknown')
            state.status = ProviderStatus.AVAILABLE
        except ImportError:
            state.sdk_installed = False
            state.status = ProviderStatus.UNAVAILABLE
            state.last_error = f"SDK '{info.sdk_package}' not installed"
        
        return state

    def scan_all(self, force: bool = False) -> Dict[str, ProviderState]:
        """
        Scan all providers for SDK availability.
        Lightweight — only does import checks, no connections.
        """
        if not force and self._last_full_scan:
            # Return cached if scanned recently (within 60s)
            return {pid: self.get_state(pid) for pid in ALL_PROVIDERS}
        
        results = {}
        for provider_id in ALL_PROVIDERS:
            self._states[provider_id] = self._check_sdk(provider_id)
            results[provider_id] = self._states[provider_id]
        
        self._last_full_scan = datetime.now().isoformat()
        return results
    
    def connect(self, provider_id: str, credentials: Optional[Dict] = None) -> ProviderState:
        """
        Attempt to connect to a provider.
        LAZY: Only loads the adapter module when connect is called.
        
        Args:
            provider_id: Provider to connect to
            credentials: Optional credentials dict (API keys, tokens, etc.)
        
        Returns:
            Updated ProviderState
        """
        info = ALL_PROVIDERS.get(provider_id)
        if not info:
            return ProviderState(status=ProviderStatus.ERROR, last_error="Unknown provider")
        
        state = self.get_state(provider_id)
        
        if not state.sdk_installed:
            state.status = ProviderStatus.UNAVAILABLE
            state.last_error = f"Install SDK first: pip install {info.sdk_package}"
            return state

        # Lazy-load the appropriate adapter
        try:
            adapter = self._load_adapter(provider_id, credentials)
            if adapter:
                self._adapters[provider_id] = adapter
                state.status = ProviderStatus.CONNECTED
                state.last_check = datetime.now().isoformat()
                # Try to get available backends
                if hasattr(adapter, 'get_backends'):
                    state.available_backends = adapter.get_backends()
            else:
                state.status = ProviderStatus.NOT_CONFIGURED
                state.last_error = "Adapter returned None — credentials may be needed"
        except Exception as e:
            state.status = ProviderStatus.ERROR
            state.last_error = str(e)
        
        self._states[provider_id] = state
        return state
    
    def disconnect(self, provider_id: str) -> bool:
        """Disconnect from a provider and release resources."""
        if provider_id in self._adapters:
            adapter = self._adapters.pop(provider_id)
            if hasattr(adapter, 'disconnect'):
                adapter.disconnect()
        if provider_id in self._states:
            self._states[provider_id].status = ProviderStatus.AVAILABLE
        return True

    def _load_adapter(self, provider_id: str, credentials: Optional[Dict] = None) -> Optional[Any]:
        """
        Lazy-load a provider adapter module.
        Adapters live in integration/providers/quantum/ and classical/.
        Each adapter is a thin wrapper that connects to the provider's SDK.
        """
        # Map provider_id to adapter module path
        adapter_map = {
            # Quantum
            "ibm_quantum": ("integration.providers.quantum.ibm", "IBMQuantumAdapter"),
            "aws_braket": ("integration.providers.quantum.aws_braket", "AWSBraketAdapter"),
            "azure_quantum": ("integration.providers.quantum.azure", "AzureQuantumAdapter"),
            "google_cirq": ("integration.providers.quantum.google", "GoogleCirqAdapter"),
            "ionq": ("integration.providers.quantum.ionq", "IonQAdapter"),
            "rigetti": ("integration.providers.quantum.rigetti", "RigettiAdapter"),
            "xanadu": ("integration.providers.quantum.xanadu", "XanaduAdapter"),
            "dwave": ("integration.providers.quantum.dwave", "DWaveAdapter"),
            "local_simulator": ("integration.providers.quantum.local_sim", "LocalSimAdapter"),
            # Classical
            "local_cpu": ("integration.providers.classical.cpu", "LocalCPUAdapter"),
            "nvidia_cuda": ("integration.providers.classical.nvidia", "NVIDIACUDAAdapter"),
            "amd_rocm": ("integration.providers.classical.amd", "AMDROCmAdapter"),
            "intel_oneapi": ("integration.providers.classical.intel", "IntelOneAPIAdapter"),
            "apple_metal": ("integration.providers.classical.apple", "AppleMetalAdapter"),
        }
        
        if provider_id not in adapter_map:
            return None

        module_path, class_name = adapter_map[provider_id]
        
        try:
            import importlib
            mod = importlib.import_module(module_path)
            adapter_class = getattr(mod, class_name)
            return adapter_class(credentials=credentials)
        except ImportError:
            # Adapter module not yet implemented — return a stub
            return _StubAdapter(provider_id, credentials)
        except Exception:
            return None

    def get_connected_providers(self) -> List[str]:
        """Return IDs of all currently connected providers."""
        return [pid for pid, state in self._states.items()
                if state.status == ProviderStatus.CONNECTED]
    
    def get_available_providers(self) -> List[str]:
        """Return IDs of providers with SDKs installed."""
        self.scan_all()
        return [pid for pid, state in self._states.items()
                if state.sdk_installed]

    def format_summary(self) -> str:
        """Format a human-readable summary of all providers."""
        self.scan_all()
        
        lines = [
            "═" * 60,
            "🔌 PROVIDER REGISTRY — FRANKENSTEIN 1.0",
            "═" * 60,
            "",
        ]
        
        # Group by type
        sections = [
            ("⚛️  QUANTUM CLOUD PROVIDERS", ProviderType.QUANTUM_CLOUD),
            ("🖥️  QUANTUM LOCAL", ProviderType.QUANTUM_LOCAL),
            ("⚡ CLASSICAL CPU", ProviderType.CLASSICAL_CPU),
            ("🎮 CLASSICAL GPU", ProviderType.CLASSICAL_GPU),
            ("🔧 CLASSICAL ACCELERATORS", ProviderType.CLASSICAL_ACCEL),
        ]
        
        for title, ptype in sections:
            providers = [p for p in ALL_PROVIDERS.values() if p.provider_type == ptype]
            if not providers:
                continue
            
            lines.append(f"─── {title} ───")
            lines.append("")

            for p in providers:
                state = self._states.get(p.id, ProviderState())
                
                # Status icon
                status_icons = {
                    ProviderStatus.CONNECTED: "🟢",
                    ProviderStatus.AVAILABLE: "🟡",
                    ProviderStatus.UNAVAILABLE: "⚪",
                    ProviderStatus.NOT_CONFIGURED: "🔵",
                    ProviderStatus.ERROR: "🔴",
                    ProviderStatus.DEGRADED: "🟠",
                }
                icon = status_icons.get(state.status, "⚪")
                
                sdk_tag = f"v{state.sdk_version}" if state.sdk_installed else f"pip install {p.sdk_package}"
                free = " [FREE]" if p.free_tier else ""
                qubits = f" ({p.max_qubits}q)" if p.max_qubits else ""
                
                lines.append(f"  {icon} {p.name:<22} {state.status.value:<16} {sdk_tag}{free}{qubits}")
            
            lines.append("")
        
        # Legend
        lines.extend([
            "─" * 60,
            "LEGEND: 🟢 Connected  🟡 SDK Ready  ⚪ Not Installed  🔴 Error",
            "",
            "COMMANDS:",
            "  providers                 Show this summary",
            "  providers scan            Refresh SDK availability",
            "  providers info <id>       Detailed info for a provider",
            "  providers install <id>    Show install command for SDK",
            "  connect <id>              Connect to a provider",
            "  disconnect <id>           Disconnect from a provider",
            "═" * 60,
        ])
        
        return "\n".join(lines)

    def format_provider_detail(self, provider_id: str) -> str:
        """Format detailed info for a single provider."""
        info = ALL_PROVIDERS.get(provider_id)
        if not info:
            return f"❌ Unknown provider: {provider_id}"
        
        state = self.get_state(provider_id)
        
        lines = [
            f"═══ {info.name} ═══",
            f"  ID:           {info.id}",
            f"  Type:         {info.provider_type.value}",
            f"  Description:  {info.description}",
            f"  Website:      {info.website or 'N/A'}",
            f"  Free Tier:    {'Yes' if info.free_tier else 'No'}",
            f"  Max Qubits:   {info.max_qubits or 'N/A'}",
            f"  Capabilities: {', '.join(c.value for c in info.capabilities)}",
            f"",
            f"  SDK Package:  {info.sdk_package}",
            f"  SDK Installed:{' Yes (v' + state.sdk_version + ')' if state.sdk_installed else ' No'}",
            f"  Status:       {state.status.value}",
            f"  Notes:        {info.notes}",
        ]
        
        if state.last_error:
            lines.append(f"  Last Error:   {state.last_error}")
        if state.available_backends:
            lines.append(f"  Backends:     {', '.join(state.available_backends)}")
        
        if not state.sdk_installed:
            lines.extend([
                f"",
                f"  INSTALL:  pip install {info.sdk_package}",
            ])
        
        return "\n".join(lines)


# ============================================================================
# STUB ADAPTER — placeholder for providers without full adapter modules
# ============================================================================

class _StubAdapter:
    """Minimal adapter for providers whose full adapter isn't built yet."""
    
    def __init__(self, provider_id: str, credentials: Optional[Dict] = None):
        self.provider_id = provider_id
        self._credentials = credentials
        self._connected = True
    
    def get_backends(self) -> List[str]:
        return ["stub_backend"]
    
    def disconnect(self):
        self._connected = False


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS (lazy singleton)
# ============================================================================

_registry: Optional[ProviderRegistry] = None

def get_registry() -> ProviderRegistry:
    """Get the provider registry singleton (lazy init)."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


# ============================================================================
# CLI INTERFACE (for testing)
# ============================================================================

if __name__ == "__main__":
    reg = get_registry()
    print(reg.format_summary())
