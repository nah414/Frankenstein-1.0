#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Workload Analyzer
Phase 3, Step 3: Intelligent Task Profiling & Resource Estimation

Analyzes incoming computational workloads to determine:
1. CLASSIFICATION - What type of computation is this?
   (quantum_gate, quantum_annealing, classical_numeric, classical_ml,
    hybrid, synthesis_engine, simulation)
2. COMPLEXITY PROFILE - How demanding is this task?
   (qubit count, circuit depth, gate count, matrix dimensions,
    memory footprint, estimated CPU/GPU time)
3. PROVIDER MATCHING - Which providers can handle this?
   (cross-references with registry capabilities + hardware tier)
4. ROUTING RECOMMENDATION - Where should this run?
   (local vs cloud, specific provider, confidence score)

Architecture: LAZY-LOADED — only instantiated when analyze() is called.
All estimation uses lightweight heuristics, not actual execution.

References:
- Quantum Volume (QV) metric: IBM 2017, log2(QV) = circuit_depth * qubits
- Circuit complexity: 2Q gate count, depth, connectivity requirements
- Memory estimation: 2^n * 16 bytes for n-qubit statevector simulation
- NISQ era constraints: gate fidelity ~99.5%, coherence limits depth
- Benchpress benchmarking suite (Nature Comp Sci 2025)
- qprof circuit profiling methodology (ACM TQC 2022)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import math
import time


# ═══════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════

class WorkloadType(Enum):
    """Classification of computational workload types."""
    QUANTUM_GATE = "quantum_gate"            # Gate-based quantum circuit
    QUANTUM_ANNEALING = "quantum_annealing"  # QUBO/Ising optimization
    QUANTUM_SIMULATION = "quantum_simulation" # Simulate quantum systems classically
    CLASSICAL_NUMERIC = "classical_numeric"   # Linear algebra, matrix ops, FFT
    CLASSICAL_ML = "classical_ml"            # Machine learning / neural nets
    CLASSICAL_OPTIMIZATION = "classical_optimization"  # Classical optimizers (SA, GA, etc.)
    SYNTHESIS_ENGINE = "synthesis_engine"     # Frankenstein's PSE workload
    HYBRID = "hybrid"                        # Mixed quantum-classical (VQE, QAOA)
    UNKNOWN = "unknown"


class ComplexityTier(Enum):
    """How demanding is this workload?"""
    TRIVIAL = "trivial"       # < 1 sec, < 100MB RAM
    LIGHT = "light"           # 1-30 sec, < 500MB RAM
    MODERATE = "moderate"     # 30s-5min, < 2GB RAM
    HEAVY = "heavy"           # 5-30min, < 4GB RAM
    EXTREME = "extreme"       # 30min+, > 4GB RAM
    INFEASIBLE = "infeasible" # Cannot run on detected hardware


class RoutingTarget(Enum):
    """Where should this workload execute?"""
    LOCAL_CPU = "local_cpu"
    LOCAL_GPU = "local_gpu"
    LOCAL_SIMULATOR = "local_simulator"
    CLOUD_QUANTUM = "cloud_quantum"
    CLOUD_ANNEALER = "cloud_annealer"
    CLOUD_GPU = "cloud_gpu"
    HYBRID_LOCAL_CLOUD = "hybrid_local_cloud"
    NOT_POSSIBLE = "not_possible"


# Memory required for statevector simulation: 2^n complex128 values
# Each complex128 = 16 bytes. So memory = 2^n * 16 bytes
QUBIT_MEMORY_TABLE = {
    n: (2**n * 16) for n in range(1, 35)
}

# Provider capability limits (max qubits that make sense)
PROVIDER_QUBIT_LIMITS = {
    "local_simulator": 20,    # ~16GB RAM needed for 20q
    "ibm_quantum": 127,       # IBM Heron/Eagle
    "aws_braket": 79,         # Via IonQ/Rigetti
    "azure_quantum": 32,      # IonQ trapped-ion
    "google_cirq": 72,        # Sycamore-class
    "ionq": 36,               # IonQ Aria
    "rigetti": 84,            # Ankaa-class
    "xanadu": 24,             # Photonic (Borealis)
    "dwave": 5000,            # Annealing qubits (different paradigm)
    "local_cpu": 0,           # N/A for quantum, unlimited for classical
    "nvidia_cuda": 0,         # GPU accelerated classical
    "amd_rocm": 0,
    "intel_oneapi": 0,
    "apple_metal": 0,
}

# Gate fidelity estimates (2-qubit gate error rates, approximate)
PROVIDER_GATE_FIDELITY = {
    "ibm_quantum": 0.995,    # Heron r3: <0.001 error on best couplers
    "ionq": 0.995,           # Trapped-ion high fidelity
    "rigetti": 0.990,        # Superconducting
    "google_cirq": 0.994,    # Sycamore
    "azure_quantum": 0.993,  # Quantinuum/IonQ
    "aws_braket": 0.992,     # Varies by backend
    "xanadu": 0.990,         # Photonic
    "local_simulator": 1.0,  # Perfect simulation
}


# ═══════════════════════════════════════════════════════════
# DATA CLASSES - Analysis Results
# ═══════════════════════════════════════════════════════════

@dataclass
class ResourceEstimate:
    """Estimated resource requirements for a workload."""
    ram_bytes: int = 0
    ram_human: str = ""
    cpu_seconds: float = 0.0
    gpu_useful: bool = False
    disk_bytes: int = 0
    network_required: bool = False

    @staticmethod
    def humanize_bytes(b: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"


@dataclass
class QuantumProfile:
    """Quantum-specific workload characteristics."""
    qubit_count: int = 0
    circuit_depth: int = 0
    gate_count_1q: int = 0
    gate_count_2q: int = 0
    gate_count_total: int = 0
    measurement_count: int = 0
    entanglement_density: float = 0.0   # 2q_gates / total_gates
    quantum_volume_log2: int = 0        # log2(QV) ≈ min(qubits, depth)
    requires_error_correction: bool = False
    max_fidelity_needed: float = 0.99
    is_variational: bool = False        # VQE, QAOA etc.
    is_annealing: bool = False          # QUBO/Ising formulation
    qubo_variables: int = 0             # For annealing problems


@dataclass
class ClassicalProfile:
    """Classical-specific workload characteristics."""
    matrix_dimensions: Tuple[int, ...] = ()
    matrix_elements: int = 0
    operation_type: str = ""            # matmul, eigenvalue, fft, etc.
    iteration_count: int = 1
    parallelizable: bool = True
    gpu_accelerable: bool = False
    float_precision: int = 64           # 32 or 64 bit


@dataclass
class ProviderMatch:
    """A provider that can handle this workload."""
    provider_id: str
    provider_name: str
    can_execute: bool = True
    score: float = 0.0          # 0-100 suitability score
    reason: str = ""
    estimated_time: str = ""    # Human-readable time estimate
    estimated_cost: str = ""    # Free / $ / $$ / $$$
    warnings: List[str] = field(default_factory=list)


@dataclass
class WorkloadAnalysis:
    """Complete analysis result for a workload."""
    # Classification
    workload_type: WorkloadType = WorkloadType.UNKNOWN
    complexity: ComplexityTier = ComplexityTier.TRIVIAL
    routing: RoutingTarget = RoutingTarget.LOCAL_CPU
    confidence: float = 0.0     # 0.0-1.0

    # Profiles (one or both populated)
    quantum: Optional[QuantumProfile] = None
    classical: Optional[ClassicalProfile] = None

    # Resources
    resources: ResourceEstimate = field(default_factory=ResourceEstimate)

    # Provider matches (sorted by score descending)
    provider_matches: List[ProviderMatch] = field(default_factory=list)

    # Human-readable summary
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    # Timing
    analysis_time_ms: float = 0.0


# ═══════════════════════════════════════════════════════════
# WORKLOAD ANALYZER ENGINE
# ═══════════════════════════════════════════════════════════

class WorkloadAnalyzer:
    """
    Profiles computational workloads and recommends optimal execution targets.

    Lazy-loaded singleton — only instantiated when analyze() is called.
    Cross-references hardware fingerprint and provider registry to
    produce actionable routing recommendations.
    """

    _instance: Optional["WorkloadAnalyzer"] = None

    @classmethod
    def get_instance(cls) -> "WorkloadAnalyzer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._hw_fingerprint = None
        self._registry = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy-load hardware and registry data on first use."""
        if self._initialized:
            return
        try:
            from integration.discovery import get_hardware_fingerprint
            self._hw_fingerprint = get_hardware_fingerprint()
        except Exception:
            self._hw_fingerprint = None
        try:
            from integration.providers.registry import get_registry
            self._registry = get_registry()
            self._registry.scan_all()
        except Exception:
            self._registry = None
        self._initialized = True

    # ─── PUBLIC API ───────────────────────────────────────

    def analyze_quantum_circuit(
        self,
        qubit_count: int,
        circuit_depth: int = 0,
        gate_count_1q: int = 0,
        gate_count_2q: int = 0,
        shots: int = 1024,
        is_variational: bool = False,
    ) -> WorkloadAnalysis:
        """Analyze a gate-based quantum circuit workload."""
        t0 = time.time()
        self._ensure_initialized()

        total_gates = gate_count_1q + gate_count_2q
        if total_gates == 0 and circuit_depth > 0:
            # Estimate gates from depth and qubits
            gate_count_1q = int(circuit_depth * qubit_count * 0.6)
            gate_count_2q = int(circuit_depth * qubit_count * 0.4)
            total_gates = gate_count_1q + gate_count_2q

        if circuit_depth == 0 and total_gates > 0:
            circuit_depth = max(1, total_gates // max(qubit_count, 1))

        entangle_density = gate_count_2q / max(total_gates, 1)
        qv_log2 = min(qubit_count, circuit_depth)

        qp = QuantumProfile(
            qubit_count=qubit_count,
            circuit_depth=circuit_depth,
            gate_count_1q=gate_count_1q,
            gate_count_2q=gate_count_2q,
            gate_count_total=total_gates,
            measurement_count=qubit_count,
            entanglement_density=round(entangle_density, 3),
            quantum_volume_log2=qv_log2,
            requires_error_correction=(qubit_count > 50 and circuit_depth > 100),
            max_fidelity_needed=self._estimate_fidelity_needed(gate_count_2q),
            is_variational=is_variational,
        )

        # Resource estimation for local simulation
        sim_ram = QUBIT_MEMORY_TABLE.get(qubit_count, 2**qubit_count * 16)
        sim_ram_with_shots = sim_ram * 2  # Working memory overhead
        cpu_seconds = self._estimate_sim_time(qubit_count, total_gates, shots)

        resources = ResourceEstimate(
            ram_bytes=sim_ram_with_shots,
            ram_human=ResourceEstimate.humanize_bytes(sim_ram_with_shots),
            cpu_seconds=cpu_seconds,
            gpu_useful=(qubit_count >= 15),
            network_required=False,
        )

        # Determine complexity
        complexity = self._classify_complexity(resources)

        # Determine workload type
        wtype = WorkloadType.HYBRID if is_variational else WorkloadType.QUANTUM_GATE

        # Match providers
        matches = self._match_quantum_providers(qp, resources)

        # Determine routing
        routing, confidence = self._route_quantum(qp, resources, matches)

        # Build recommendations
        recs = self._build_quantum_recommendations(qp, resources, matches)

        # Summary
        summary = self._format_quantum_summary(qp, resources, complexity, routing)

        elapsed = (time.time() - t0) * 1000

        return WorkloadAnalysis(
            workload_type=wtype,
            complexity=complexity,
            routing=routing,
            confidence=confidence,
            quantum=qp,
            resources=resources,
            provider_matches=matches,
            summary=summary,
            recommendations=recs,
            analysis_time_ms=round(elapsed, 2),
        )

    def analyze_annealing(
        self,
        qubo_variables: int,
        num_reads: int = 100,
        chain_strength: float = 1.0,
    ) -> WorkloadAnalysis:
        """Analyze a quantum annealing (QUBO/Ising) workload."""
        t0 = time.time()
        self._ensure_initialized()

        qp = QuantumProfile(
            qubit_count=qubo_variables,
            is_annealing=True,
            qubo_variables=qubo_variables,
        )

        # Annealing resource estimation
        # D-Wave embeds ~1 logical var per 4-8 physical qubits
        physical_qubits_needed = qubo_variables * 6  # avg embedding ratio
        ram_for_qubo = qubo_variables * qubo_variables * 8  # QUBO matrix
        cpu_seconds = 0.5 + (qubo_variables / 100) * num_reads * 0.01

        resources = ResourceEstimate(
            ram_bytes=ram_for_qubo,
            ram_human=ResourceEstimate.humanize_bytes(ram_for_qubo),
            cpu_seconds=cpu_seconds,
            network_required=True,  # D-Wave is cloud
        )

        complexity = self._classify_complexity(resources)
        matches = self._match_annealing_providers(qp, physical_qubits_needed)
        routing = RoutingTarget.CLOUD_ANNEALER if qubo_variables > 20 else RoutingTarget.LOCAL_CPU

        summary = (
            f"Annealing workload: {qubo_variables} QUBO variables → "
            f"~{physical_qubits_needed} physical qubits needed. "
            f"Memory: {resources.ram_human}."
        )

        recs = []
        if qubo_variables <= 20:
            recs.append("Small enough to solve classically with simulated annealing")
        if qubo_variables <= 5000:
            recs.append("D-Wave Advantage can handle this (5000+ qubits)")
        if qubo_variables > 1000:
            recs.append("Consider hybrid solver (D-Wave Leap) for large problems")

        elapsed = (time.time() - t0) * 1000
        return WorkloadAnalysis(
            workload_type=WorkloadType.QUANTUM_ANNEALING,
            complexity=complexity,
            routing=routing,
            confidence=0.85,
            quantum=qp,
            resources=resources,
            provider_matches=matches,
            summary=summary,
            recommendations=recs,
            analysis_time_ms=round(elapsed, 2),
        )

    def analyze_classical(
        self,
        operation: str = "matmul",
        matrix_dims: Tuple[int, ...] = (100, 100),
        iterations: int = 1,
        precision: int = 64,
    ) -> WorkloadAnalysis:
        """Analyze a classical numerical workload."""
        t0 = time.time()
        self._ensure_initialized()

        # Calculate matrix elements
        elements = 1
        for d in matrix_dims:
            elements *= d
        bytes_per_element = precision // 8
        matrix_bytes = elements * bytes_per_element

        # Operation cost estimates (FLOPs-based)
        op_costs = {
            "matmul": lambda: elements * matrix_dims[-1] * 2,
            "eigenvalue": lambda: elements * elements * 10,
            "fft": lambda: elements * math.log2(max(elements, 2)) * 5,
            "svd": lambda: elements * min(matrix_dims) * 22,
            "inverse": lambda: elements * matrix_dims[0] * 3,
            "solve": lambda: elements * matrix_dims[0],
            "simulation": lambda: elements * iterations * 50,
        }

        flops = op_costs.get(operation, lambda: elements * 10)()
        # Estimate CPU time: assume ~2 GFLOPS on i3 single core
        gflops_available = 2.0
        if self._hw_fingerprint:
            cores = self._hw_fingerprint.cpu.logical_cores
            gflops_available = cores * 1.5  # Conservative
        cpu_seconds = (flops / (gflops_available * 1e9)) * iterations

        # GPU acceleration potential
        gpu_useful = (elements > 100_000 and operation in ("matmul", "fft", "simulation"))

        resources = ResourceEstimate(
            ram_bytes=matrix_bytes * 3,  # Input + output + working
            ram_human=ResourceEstimate.humanize_bytes(matrix_bytes * 3),
            cpu_seconds=round(cpu_seconds, 3),
            gpu_useful=gpu_useful,
        )

        cp = ClassicalProfile(
            matrix_dimensions=matrix_dims,
            matrix_elements=elements,
            operation_type=operation,
            iteration_count=iterations,
            parallelizable=True,
            gpu_accelerable=gpu_useful,
            float_precision=precision,
        )

        complexity = self._classify_complexity(resources)
        matches = self._match_classical_providers(cp, resources)
        routing = RoutingTarget.LOCAL_GPU if gpu_useful else RoutingTarget.LOCAL_CPU

        dims_str = "×".join(str(d) for d in matrix_dims)
        summary = (
            f"Classical {operation} on {dims_str} matrix ({iterations} iterations). "
            f"Memory: {resources.ram_human}. Est. time: {cpu_seconds:.2f}s."
        )

        recs = []
        if gpu_useful:
            recs.append("GPU acceleration would significantly speed this up")
        if cpu_seconds > 60:
            recs.append("Consider chunking or parallelizing across cores")
        if elements > 1_000_000:
            recs.append("Large matrix — consider sparse representations if applicable")

        elapsed = (time.time() - t0) * 1000
        return WorkloadAnalysis(
            workload_type=WorkloadType.CLASSICAL_NUMERIC,
            complexity=complexity,
            routing=routing,
            confidence=0.90,
            classical=cp,
            resources=resources,
            provider_matches=matches,
            summary=summary,
            recommendations=recs,
            analysis_time_ms=round(elapsed, 2),
        )

    def analyze_synthesis(
        self,
        input_dimensions: int = 3,
        superposition_states: int = 8,
        lorentz_corrections: bool = True,
        collapse_strategy: str = "max_probability",
    ) -> WorkloadAnalysis:
        """Analyze a Frankenstein Predictive Synthesis Engine workload."""
        t0 = time.time()
        self._ensure_initialized()

        # PSE uses wave function simulation + Lorentz transforms
        # Memory: superposition_states * input_dimensions * complex128
        state_vector_size = superposition_states * input_dimensions
        ram_bytes = state_vector_size * 16 * 4  # Complex128 * working copies

        # Lorentz corrections add ~30% compute overhead
        base_flops = state_vector_size * state_vector_size * 50
        if lorentz_corrections:
            base_flops = int(base_flops * 1.3)

        gflops = 6.0  # Conservative for i3
        cpu_seconds = base_flops / (gflops * 1e9)

        resources = ResourceEstimate(
            ram_bytes=ram_bytes,
            ram_human=ResourceEstimate.humanize_bytes(ram_bytes),
            cpu_seconds=round(cpu_seconds, 4),
            gpu_useful=(state_vector_size > 10000),
        )

        qp = QuantumProfile(
            qubit_count=int(math.log2(max(superposition_states, 2))),
            is_variational=False,
        )

        complexity = self._classify_complexity(resources)

        summary = (
            f"Synthesis Engine: {input_dimensions}D input × "
            f"{superposition_states} superposition states. "
            f"Lorentz: {'ON' if lorentz_corrections else 'OFF'}. "
            f"Collapse: {collapse_strategy}. Memory: {resources.ram_human}."
        )

        recs = [
            "PSE runs locally using NumPy — connect local_cpu",
            f"Wave function evolution: {state_vector_size} state elements",
        ]
        if lorentz_corrections:
            recs.append("Lorentz transforms add ~30% compute but ensure physical validity")

        elapsed = (time.time() - t0) * 1000
        return WorkloadAnalysis(
            workload_type=WorkloadType.SYNTHESIS_ENGINE,
            complexity=complexity,
            routing=RoutingTarget.LOCAL_CPU,
            confidence=0.95,
            quantum=qp,
            resources=resources,
            provider_matches=[ProviderMatch(
                provider_id="local_cpu",
                provider_name="Local CPU",
                score=95.0,
                reason="PSE is optimized for local NumPy execution",
                estimated_time=f"{cpu_seconds:.3f}s",
                estimated_cost="Free",
            )],
            summary=summary,
            recommendations=recs,
            analysis_time_ms=round(elapsed, 2),
        )

    # ─── PRIVATE: Estimation Helpers ──────────────────────

    def _estimate_fidelity_needed(self, two_qubit_gates: int) -> float:
        """
        Estimate minimum gate fidelity needed for meaningful results.
        Based on: success_prob ≈ fidelity^(num_2q_gates)
        We want success_prob > 0.1 (10% signal)
        So fidelity > 0.1^(1/num_2q_gates)
        """
        if two_qubit_gates <= 0:
            return 0.9
        target_success = 0.1
        fidelity = target_success ** (1.0 / max(two_qubit_gates, 1))
        return round(max(fidelity, 0.9), 4)

    def _estimate_sim_time(self, qubits: int, gates: int, shots: int) -> float:
        """
        Estimate local simulation time in seconds.
        Statevector: O(2^n * gates) operations
        Each gate applies a 2^n matrix multiplication
        """
        if qubits <= 0:
            return 0.001
        state_size = 2 ** qubits
        ops = state_size * max(gates, 1) * 2  # Complex multiply-add
        gflops = 6.0  # i3 conservative
        sim_time = ops / (gflops * 1e9)
        # Shots overhead (sampling is cheap, but repeated sim for noisy)
        if shots > 1:
            sim_time *= 1 + (shots * 0.0001)
        return round(sim_time, 4)

    def _classify_complexity(self, res: ResourceEstimate) -> ComplexityTier:
        """Classify workload complexity from resource estimates."""
        ram_gb = res.ram_bytes / (1024**3)
        hw_ram = 8.0
        if self._hw_fingerprint:
            hw_ram = self._hw_fingerprint.ram.total_gb

        # Check feasibility first
        if ram_gb > hw_ram * 0.7:  # Exceeds 70% RAM safety limit
            return ComplexityTier.INFEASIBLE
        if res.cpu_seconds > 1800:  # > 30 min
            return ComplexityTier.EXTREME
        if res.cpu_seconds > 300:   # > 5 min
            return ComplexityTier.HEAVY
        if res.cpu_seconds > 30:
            return ComplexityTier.MODERATE
        if res.cpu_seconds > 1:
            return ComplexityTier.LIGHT
        return ComplexityTier.TRIVIAL

    # ─── PRIVATE: Provider Matching ───────────────────────

    def _match_quantum_providers(
        self, qp: QuantumProfile, res: ResourceEstimate
    ) -> List[ProviderMatch]:
        """Score and rank providers for a quantum gate workload."""
        from integration.providers.registry import ALL_PROVIDERS, ProviderType

        matches = []
        available = set()
        if self._registry:
            available = set(self._registry.get_available_providers())

        for pid, info in ALL_PROVIDERS.items():
            if info.provider_type not in (
                ProviderType.QUANTUM_CLOUD,
                ProviderType.QUANTUM_LOCAL,
            ):
                continue

            max_q = PROVIDER_QUBIT_LIMITS.get(pid, 0)
            can_run = qp.qubit_count <= max_q

            if not can_run:
                continue

            score = 50.0  # Base score
            warnings = []
            reason_parts = []

            # Qubit headroom bonus
            headroom = (max_q - qp.qubit_count) / max(max_q, 1)
            score += headroom * 20

            # SDK installed bonus
            if pid in available:
                score += 15
                reason_parts.append("SDK installed")
            else:
                score -= 10
                reason_parts.append("SDK not installed")

            # Fidelity check
            fidelity = PROVIDER_GATE_FIDELITY.get(pid, 0.99)
            if fidelity >= qp.max_fidelity_needed:
                score += 10
                reason_parts.append(f"fidelity {fidelity:.3f} meets requirement")
            else:
                score -= 20
                warnings.append(
                    f"Gate fidelity {fidelity:.3f} below needed {qp.max_fidelity_needed:.3f}"
                )

            # Local simulator: free but limited
            if pid == "local_simulator":
                hw_ram = 8.0
                if self._hw_fingerprint:
                    hw_ram = self._hw_fingerprint.ram.total_gb
                sim_ram_gb = res.ram_bytes / (1024**3)
                if sim_ram_gb < hw_ram * 0.7:
                    score += 20  # Can run locally!
                    reason_parts.append("fits in local RAM")
                else:
                    score -= 30
                    warnings.append(f"Needs {sim_ram_gb:.1f}GB RAM, you have {hw_ram:.1f}GB")

            # Variational workloads prefer local+cloud hybrid
            if qp.is_variational and pid in ("ibm_quantum", "aws_braket"):
                score += 10
                reason_parts.append("good for variational algorithms")

            # Free tier bonus
            if info.free_tier:
                score += 5
                reason_parts.append("free tier")

            # Cost estimate
            cost = "Free" if info.free_tier else "$"
            if qp.qubit_count > 50:
                cost = "$$" if info.free_tier else "$$$"

            matches.append(ProviderMatch(
                provider_id=pid,
                provider_name=info.name,
                can_execute=True,
                score=round(min(score, 100), 1),
                reason="; ".join(reason_parts),
                estimated_cost=cost,
                warnings=warnings,
            ))

        matches.sort(key=lambda m: -m.score)
        return matches

    def _match_annealing_providers(
        self, qp: QuantumProfile, physical_qubits: int
    ) -> List[ProviderMatch]:
        """Score providers for annealing workloads."""
        matches = []
        available = set()
        if self._registry:
            available = set(self._registry.get_available_providers())

        # D-Wave is the primary annealing provider
        if qp.qubo_variables <= 5000:
            score = 80.0
            if "dwave" in available:
                score += 10
            matches.append(ProviderMatch(
                provider_id="dwave",
                provider_name="D-Wave Quantum Annealer",
                score=score,
                reason=f"{qp.qubo_variables} vars fits D-Wave Advantage (5000+ qubits)",
                estimated_cost="Free" if qp.qubo_variables <= 100 else "$",
            ))

        # AWS Braket also provides D-Wave access
        if qp.qubo_variables <= 5000:
            score = 65.0
            if "aws_braket" in available:
                score += 10
            matches.append(ProviderMatch(
                provider_id="aws_braket",
                provider_name="AWS Braket (D-Wave)",
                score=score,
                reason="D-Wave access via AWS Braket",
                estimated_cost="$",
            ))

        # Local simulated annealing for small problems
        if qp.qubo_variables <= 200:
            matches.append(ProviderMatch(
                provider_id="local_cpu",
                provider_name="Local CPU (Simulated Annealing)",
                score=70.0 if qp.qubo_variables <= 50 else 45.0,
                reason="Classical SA can handle small QUBO problems locally",
                estimated_cost="Free",
            ))

        matches.sort(key=lambda m: -m.score)
        return matches

    def _match_classical_providers(
        self, cp: ClassicalProfile, res: ResourceEstimate
    ) -> List[ProviderMatch]:
        """Score providers for classical numerical workloads."""
        from integration.providers.registry import ALL_PROVIDERS, ProviderType

        matches = []
        available = set()
        if self._registry:
            available = set(self._registry.get_available_providers())

        # Local CPU — always available
        score = 70.0
        if "local_cpu" in available:
            score += 10
        if res.cpu_seconds < 60:
            score += 15
        matches.append(ProviderMatch(
            provider_id="local_cpu",
            provider_name="Local CPU (NumPy/SciPy)",
            score=round(score, 1),
            reason=f"Est. {res.cpu_seconds:.2f}s on local CPU",
            estimated_time=f"{res.cpu_seconds:.2f}s",
            estimated_cost="Free",
        ))

        # GPU providers if GPU-accelerable
        if cp.gpu_accelerable:
            for pid in ("nvidia_cuda", "amd_rocm", "apple_metal"):
                if pid in ALL_PROVIDERS:
                    info = ALL_PROVIDERS[pid]
                    gpu_score = 85.0 if pid in available else 40.0
                    gpu_time = res.cpu_seconds / 10  # ~10x speedup estimate
                    matches.append(ProviderMatch(
                        provider_id=pid,
                        provider_name=info.name,
                        score=round(gpu_score, 1),
                        reason=f"~{gpu_time:.2f}s with GPU acceleration",
                        estimated_time=f"{gpu_time:.2f}s",
                        estimated_cost="Free",
                        warnings=[] if pid in available else ["SDK not installed"],
                    ))

        # Intel oneAPI for Intel CPUs
        if "intel_oneapi" in ALL_PROVIDERS:
            intel_score = 60.0
            if self._hw_fingerprint and "intel" in self._hw_fingerprint.cpu.vendor.lower():
                intel_score = 75.0
            if "intel_oneapi" in available:
                intel_score += 10
            matches.append(ProviderMatch(
                provider_id="intel_oneapi",
                provider_name="Intel oneAPI (DPNP)",
                score=round(intel_score, 1),
                reason="Optimized NumPy for Intel CPUs",
                estimated_time=f"~{res.cpu_seconds * 0.7:.2f}s",
                estimated_cost="Free",
            ))

        matches.sort(key=lambda m: -m.score)
        return matches

    # ─── PRIVATE: Routing Logic ───────────────────────────

    def _route_quantum(
        self, qp: QuantumProfile, res: ResourceEstimate,
        matches: List[ProviderMatch]
    ) -> Tuple[RoutingTarget, float]:
        """Determine optimal routing for quantum workloads."""
        hw_ram = 8.0
        if self._hw_fingerprint:
            hw_ram = self._hw_fingerprint.ram.total_gb

        sim_ram_gb = res.ram_bytes / (1024**3)

        # Can simulate locally?
        if sim_ram_gb < hw_ram * 0.5 and qp.qubit_count <= 18:
            return RoutingTarget.LOCAL_SIMULATOR, 0.9

        # Small enough for local but tight on RAM
        if sim_ram_gb < hw_ram * 0.7 and qp.qubit_count <= 20:
            return RoutingTarget.LOCAL_SIMULATOR, 0.7

        # Must go to cloud
        if matches and matches[0].score > 50:
            return RoutingTarget.CLOUD_QUANTUM, 0.8

        # Variational: hybrid approach
        if qp.is_variational:
            return RoutingTarget.HYBRID_LOCAL_CLOUD, 0.75

        # Fallback
        if qp.qubit_count > 20:
            return RoutingTarget.CLOUD_QUANTUM, 0.6

        return RoutingTarget.NOT_POSSIBLE, 0.3

    # ─── PRIVATE: Recommendations ─────────────────────────

    def _build_quantum_recommendations(
        self, qp: QuantumProfile, res: ResourceEstimate,
        matches: List[ProviderMatch]
    ) -> List[str]:
        """Build actionable recommendations."""
        recs = []
        hw_ram = 8.0
        if self._hw_fingerprint:
            hw_ram = self._hw_fingerprint.ram.total_gb

        sim_ram_gb = res.ram_bytes / (1024**3)

        if qp.qubit_count <= 15:
            recs.append(f"Fits comfortably in local simulator ({sim_ram_gb:.2f}GB needed)")
        elif qp.qubit_count <= 20:
            recs.append(f"Local simulation possible but memory-intensive ({sim_ram_gb:.1f}GB)")
            recs.append("Consider reducing qubit count or circuit depth if possible")
        else:
            recs.append(f"Too large for local sim ({sim_ram_gb:.1f}GB). Use cloud quantum.")

        if qp.gate_count_2q > 1000:
            recs.append(f"High 2Q gate count ({qp.gate_count_2q}). Noise will be significant on NISQ hardware.")
            recs.append("Consider circuit optimization (Qiskit transpiler level 3)")

        if qp.entanglement_density > 0.5:
            recs.append("High entanglement density — trapped-ion (IonQ) has better all-to-all connectivity")

        if qp.is_variational:
            recs.append("Variational algorithm: use hybrid local+cloud. Classical optimizer runs locally, QPU executes circuits.")

        if matches:
            best = matches[0]
            recs.append(f"Top recommendation: {best.provider_name} (score: {best.score})")

        return recs

    # ─── PRIVATE: Formatting ──────────────────────────────

    def _format_quantum_summary(
        self, qp: QuantumProfile, res: ResourceEstimate,
        complexity: ComplexityTier, routing: RoutingTarget,
    ) -> str:
        """Format a human-readable summary."""
        parts = [
            f"Quantum circuit: {qp.qubit_count} qubits, depth {qp.circuit_depth}, "
            f"{qp.gate_count_total} gates ({qp.gate_count_2q} two-qubit).",
            f"QV(log2): {qp.quantum_volume_log2}. "
            f"Entanglement density: {qp.entanglement_density:.1%}.",
            f"Local sim memory: {res.ram_human}. "
            f"Est. sim time: {res.cpu_seconds:.3f}s.",
            f"Complexity: {complexity.value.upper()}. "
            f"Recommended target: {routing.value}.",
        ]
        if qp.requires_error_correction:
            parts.append("⚠ Circuit likely needs error correction for reliable results.")
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════
# PUBLIC CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════

def get_analyzer() -> WorkloadAnalyzer:
    """Get the singleton WorkloadAnalyzer instance."""
    return WorkloadAnalyzer.get_instance()


def analyze_circuit(qubits: int, depth: int = 0, **kwargs) -> WorkloadAnalysis:
    """Quick-analyze a quantum circuit."""
    return get_analyzer().analyze_quantum_circuit(qubits, depth, **kwargs)


def analyze_qubo(variables: int, **kwargs) -> WorkloadAnalysis:
    """Quick-analyze an annealing problem."""
    return get_analyzer().analyze_annealing(variables, **kwargs)


def analyze_matrix(operation: str = "matmul", dims: Tuple[int, ...] = (100, 100), **kwargs) -> WorkloadAnalysis:
    """Quick-analyze a classical computation."""
    return get_analyzer().analyze_classical(operation, dims, **kwargs)


def analyze_pse(**kwargs) -> WorkloadAnalysis:
    """Quick-analyze a Predictive Synthesis Engine workload."""
    return get_analyzer().analyze_synthesis(**kwargs)


# ═══════════════════════════════════════════════════════════
# TERMINAL DISPLAY FORMATTER
# ═══════════════════════════════════════════════════════════

def format_analysis(analysis: WorkloadAnalysis, write_fn) -> None:
    """Format a WorkloadAnalysis for terminal display."""
    write_fn("\n")
    write_fn("═" * 62 + "\n")
    write_fn("🔬 WORKLOAD ANALYSIS REPORT\n")
    write_fn("═" * 62 + "\n\n")

    # Classification
    type_icons = {
        WorkloadType.QUANTUM_GATE: "⚛️",
        WorkloadType.QUANTUM_ANNEALING: "🧲",
        WorkloadType.QUANTUM_SIMULATION: "🌊",
        WorkloadType.CLASSICAL_NUMERIC: "🔢",
        WorkloadType.CLASSICAL_ML: "🤖",
        WorkloadType.CLASSICAL_OPTIMIZATION: "📈",
        WorkloadType.SYNTHESIS_ENGINE: "🧬",
        WorkloadType.HYBRID: "🔀",
        WorkloadType.UNKNOWN: "❓",
    }
    icon = type_icons.get(analysis.workload_type, "❓")
    write_fn(f"  Type:       {icon} {analysis.workload_type.value.replace('_', ' ').title()}\n")

    # Complexity with color indicator
    cx_icons = {
        ComplexityTier.TRIVIAL: "🟢",
        ComplexityTier.LIGHT: "🟢",
        ComplexityTier.MODERATE: "🟡",
        ComplexityTier.HEAVY: "🟠",
        ComplexityTier.EXTREME: "🔴",
        ComplexityTier.INFEASIBLE: "⛔",
    }
    cx_icon = cx_icons.get(analysis.complexity, "❓")
    write_fn(f"  Complexity: {cx_icon} {analysis.complexity.value.upper()}\n")
    write_fn(f"  Route to:   {analysis.routing.value.replace('_', ' ').title()}\n")
    write_fn(f"  Confidence: {analysis.confidence:.0%}\n\n")

    # Quantum profile
    if analysis.quantum:
        qp = analysis.quantum
        write_fn("─── QUANTUM PROFILE ───\n")
        if qp.is_annealing:
            write_fn(f"  QUBO Variables:    {qp.qubo_variables}\n")
            write_fn(f"  Physical Qubits:   ~{qp.qubo_variables * 6} (estimated embedding)\n")
        else:
            write_fn(f"  Qubits:            {qp.qubit_count}\n")
            write_fn(f"  Circuit Depth:     {qp.circuit_depth}\n")
            write_fn(f"  Gates (1Q / 2Q):   {qp.gate_count_1q} / {qp.gate_count_2q}  (total: {qp.gate_count_total})\n")
            write_fn(f"  Entanglement:      {qp.entanglement_density:.1%}\n")
            write_fn(f"  QV (log2):         {qp.quantum_volume_log2}\n")
            write_fn(f"  Min Fidelity:      {qp.max_fidelity_needed:.4f}\n")
            if qp.is_variational:
                write_fn(f"  Variational:       YES (hybrid classical-quantum)\n")
            if qp.requires_error_correction:
                write_fn(f"  Error Correction:  ⚠ LIKELY REQUIRED\n")
        write_fn("\n")

    # Classical profile
    if analysis.classical:
        cp = analysis.classical
        write_fn("─── CLASSICAL PROFILE ───\n")
        dims_str = "×".join(str(d) for d in cp.matrix_dimensions)
        write_fn(f"  Operation:     {cp.operation_type}\n")
        write_fn(f"  Dimensions:    {dims_str}  ({cp.matrix_elements:,} elements)\n")
        write_fn(f"  Iterations:    {cp.iteration_count}\n")
        write_fn(f"  GPU Useful:    {'YES' if cp.gpu_accelerable else 'No'}\n")
        write_fn(f"  Precision:     {cp.float_precision}-bit\n\n")

    # Resource estimates
    write_fn("─── RESOURCE ESTIMATE ───\n")
    write_fn(f"  Memory:     {analysis.resources.ram_human}\n")
    write_fn(f"  CPU Time:   {analysis.resources.cpu_seconds:.3f}s\n")
    write_fn(f"  GPU Useful: {'YES' if analysis.resources.gpu_useful else 'No'}\n")
    write_fn(f"  Network:    {'Required' if analysis.resources.network_required else 'Not needed'}\n\n")

    # Provider matches
    if analysis.provider_matches:
        write_fn("─── PROVIDER RANKING ───\n")
        for i, m in enumerate(analysis.provider_matches[:5], 1):
            bar_len = int(m.score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            write_fn(f"  {i}. {m.provider_name}\n")
            write_fn(f"     Score: [{bar}] {m.score:.0f}/100\n")
            write_fn(f"     {m.reason}\n")
            if m.estimated_time:
                write_fn(f"     Est. time: {m.estimated_time}  Cost: {m.estimated_cost}\n")
            elif m.estimated_cost:
                write_fn(f"     Cost: {m.estimated_cost}\n")
            for w in m.warnings:
                write_fn(f"     ⚠ {w}\n")
            write_fn("\n")

    # Recommendations
    if analysis.recommendations:
        write_fn("─── RECOMMENDATIONS ───\n")
        for rec in analysis.recommendations:
            write_fn(f"  💡 {rec}\n")
        write_fn("\n")

    write_fn(f"  Analysis completed in {analysis.analysis_time_ms:.1f}ms\n")
    write_fn("═" * 62 + "\n\n")
