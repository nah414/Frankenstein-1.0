#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Intelligent Router Tests
Phase 3, Step 5.8: Comprehensive test suite

Tests:
  - Lazy loading (no heavy init on import)
  - Tier 1 routing constraints
  - Resource safety limits (CPU 80%, RAM 70%)
  - Fallback chain activation
  - Quantum routing by qubit count
  - Classical routing by hardware
  - Priority mode effects on scoring
  - Scoring determinism
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLazyLoading(unittest.TestCase):
    """Test that router doesn't initialize on import."""

    def test_import_no_heavy_init(self):
        """Verify router module imports without triggering heavy initialization."""
        # Fresh import should not trigger lazy init
        from router.intelligent_router import IntelligentRouter

        # Reset singleton for clean test
        IntelligentRouter._instance = None
        router = IntelligentRouter()

        self.assertFalse(router._lazy_initialized)
        self.assertIsNone(router._registry)
        self.assertIsNone(router._discovery)

        # Cleanup
        IntelligentRouter._instance = None

    def test_memory_footprint_before_route(self):
        """Verify memory footprint is small before first route() call."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        # Router should have minimal attributes before lazy init
        self.assertFalse(router._lazy_initialized)
        self.assertEqual(len(router._history), 0)

        # Cleanup
        IntelligentRouter._instance = None

    def test_lazy_init_triggered_on_route(self):
        """Verify _lazy_init is called on first route()."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        self.assertFalse(router._lazy_initialized)

        # Call route — should trigger lazy init
        result = router.route({"workload_type": "quantum_simulation", "qubit_count": 5})
        self.assertTrue(router._lazy_initialized)
        self.assertIn("provider", result)

        # Cleanup
        IntelligentRouter._instance = None


class TestWorkloadSpec(unittest.TestCase):
    """Test workload specification parsing and validation."""

    def test_default_values(self):
        """Test default workload spec values."""
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec()
        self.assertEqual(spec.workload_type, WorkloadType.CLASSICAL_OPTIMIZATION)
        self.assertEqual(spec.qubit_count, 0)
        self.assertEqual(spec.circuit_depth, 0)
        self.assertEqual(spec.classical_cpu_threads, 1)
        self.assertEqual(spec.memory_requirement_mb, 100)
        self.assertEqual(spec.priority, "cost")

    def test_from_dict(self):
        """Test creating spec from dictionary."""
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec.from_dict({
            "workload_type": "quantum_simulation",
            "qubit_count": 10,
            "priority": "speed",
        })
        self.assertEqual(spec.workload_type, WorkloadType.QUANTUM_SIMULATION)
        self.assertEqual(spec.qubit_count, 10)
        self.assertEqual(spec.priority, "speed")

    def test_to_dict_roundtrip(self):
        """Test dict serialization roundtrip."""
        from router.workload_spec import WorkloadSpec

        spec = WorkloadSpec(qubit_count=15, priority="accuracy")
        d = spec.to_dict()
        spec2 = WorkloadSpec.from_dict(d)
        self.assertEqual(spec.qubit_count, spec2.qubit_count)
        self.assertEqual(spec.priority, spec2.priority)

    def test_tier1_validation(self):
        """Test Tier 1 hardware limit validation."""
        from router.workload_spec import WorkloadSpec, WorkloadType

        # Within Tier 1 limits
        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
            classical_cpu_threads=2,
            memory_requirement_mb=500,
        )
        valid, issues = spec.validate_tier1()
        self.assertTrue(valid)
        self.assertEqual(len(issues), 0)

        # Exceeds Tier 1 limits
        spec_big = WorkloadSpec(
            qubit_count=25,
            classical_cpu_threads=8,
            memory_requirement_mb=16000,
        )
        valid, issues = spec_big.validate_tier1()
        self.assertFalse(valid)
        self.assertGreater(len(issues), 0)

    def test_requires_quantum(self):
        """Test quantum requirement detection."""
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec_q = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=5,
        )
        self.assertTrue(spec_q.requires_quantum())

        spec_c = WorkloadSpec(
            workload_type=WorkloadType.CLASSICAL_OPTIMIZATION,
        )
        self.assertFalse(spec_c.requires_quantum())

    def test_invalid_priority_defaults_to_cost(self):
        """Test that invalid priority normalizes to cost."""
        from router.workload_spec import WorkloadSpec

        spec = WorkloadSpec(priority="invalid_mode")
        self.assertEqual(spec.priority, "cost")

    def test_negative_values_clamped(self):
        """Test negative values are clamped to minimums."""
        from router.workload_spec import WorkloadSpec

        spec = WorkloadSpec(qubit_count=-5, classical_cpu_threads=-1, memory_requirement_mb=-100)
        self.assertEqual(spec.qubit_count, 0)
        self.assertEqual(spec.classical_cpu_threads, 1)
        self.assertEqual(spec.memory_requirement_mb, 1)

    def test_estimated_memory_quantum(self):
        """Test quantum memory estimation."""
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=20,
        )
        est = spec.estimated_memory_mb()
        # 2^20 * 16 bytes = 16MB, * 1.5 overhead = 24MB
        self.assertGreater(est, 20)


class TestTier1Routing(unittest.TestCase):
    """Test routing stays within i3 8th Gen capabilities."""

    def test_10_qubit_routes_local(self):
        """10 qubit workload should route to local simulators on Tier 1."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        # Mock resource usage to simulate low-load conditions
        with patch.object(router, '_get_resource_usage', return_value=(20.0, 30.0, 8192.0)):
            result = router.route({
                "workload_type": "quantum_simulation",
                "qubit_count": 10,
                "priority": "cost",
            })

        # Should route to a local simulator (not cloud)
        local_providers = {"local_simulator", "qiskit_aer", "local_cpu"}
        self.assertIn(result["provider"], local_providers,
                      f"Expected local provider for 10 qubits, got {result['provider']}")

        IntelligentRouter._instance = None

    def test_small_classical_routes_local_cpu(self):
        """Small classical workload should route to local CPU."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        # Mock resource usage to simulate low-load conditions
        with patch.object(router, '_get_resource_usage', return_value=(20.0, 30.0, 8192.0)):
            result = router.route({
                "workload_type": "classical_optimization",
                "classical_cpu_threads": 1,
                "memory_requirement_mb": 100,
                "priority": "cost",
            })

        local_providers = {"local_cpu", "intel_oneapi"}
        self.assertIn(result["provider"], local_providers)

        IntelligentRouter._instance = None


class TestSafetyLimits(unittest.TestCase):
    """Test resource safety enforcement."""

    def test_cpu_limit_enforcement(self):
        """Verify router blocks routes exceeding CPU 80% limit."""
        from router.safety_filter import check_resource_safety
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=15,
        )

        # Simulate high CPU usage
        result = check_resource_safety(
            "local_simulator", spec,
            current_cpu=75.0, current_ram=30.0, total_ram_mb=8192.0,
        )

        # local_simulator uses ~50% CPU, 75 + 50 = 125% > 80%
        self.assertFalse(result["safe"])
        self.assertGreater(result["estimated_cpu"], 80.0)

    def test_ram_limit_enforcement(self):
        """Verify router blocks routes exceeding RAM 70% limit."""
        from router.safety_filter import check_resource_safety
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=20,
            memory_requirement_mb=2048,
        )

        # Simulate high RAM usage
        result = check_resource_safety(
            "local_simulator", spec,
            current_cpu=20.0, current_ram=60.0, total_ram_mb=8192.0,
        )

        # 20 qubits = ~24MB state vector, but spec says 2048MB
        # 60% + estimated% should exceed 70%
        self.assertFalse(result["safe"])

    def test_cloud_provider_low_local_impact(self):
        """Cloud providers should pass safety checks even at high local usage."""
        from router.safety_filter import check_resource_safety
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
        )

        result = check_resource_safety(
            "ibm_quantum", spec,
            current_cpu=70.0, current_ram=60.0, total_ram_mb=8192.0,
        )

        # IBM Quantum uses ~5% CPU and ~80MB RAM locally
        self.assertTrue(result["safe"])

    def test_filter_safe_providers(self):
        """Test bulk filtering of providers by safety."""
        from router.safety_filter import filter_safe_providers
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=15,
        )

        candidates = ["local_simulator", "ibm_quantum", "local_cpu"]

        safe, rejected = filter_safe_providers(
            candidates, spec,
            current_cpu=70.0, current_ram=60.0, total_ram_mb=8192.0,
        )

        # Cloud provider should pass, local may be rejected at high usage
        self.assertIn("ibm_quantum", safe)


class TestFallbackActivation(unittest.TestCase):
    """Test fallback chain behavior on provider failure."""

    def test_fallback_chain_exists(self):
        """Every provider should have a fallback chain."""
        from router.fallback import get_fallback_chain, _FALLBACK_CHAINS

        for provider_id in _FALLBACK_CHAINS:
            chain = get_fallback_chain(provider_id)
            if provider_id != "local_cpu":
                self.assertGreater(len(chain), 0,
                                   f"Provider {provider_id} has no fallback chain")

    def test_all_chains_terminate_safely(self):
        """All fallback chains should terminate at a safe provider."""
        from router.fallback import get_fallback_chain, _FALLBACK_CHAINS

        safe_terminals = {"local_cpu", "local_simulator"}

        for provider_id in _FALLBACK_CHAINS:
            chain = get_fallback_chain(provider_id)
            if chain:
                # Last in chain should be a safe terminal
                self.assertIn(chain[-1], safe_terminals,
                              f"Chain for {provider_id} doesn't terminate safely: {chain}")

    def test_handle_routing_error(self):
        """Test error handling returns valid fallback."""
        from router.fallback import handle_routing_error

        result = handle_routing_error(
            Exception("Connection refused"),
            "ibm_quantum",
            "quantum_simulation",
        )

        self.assertIn("fallback_provider", result)
        self.assertIn("user_message", result)
        self.assertEqual(result["original_provider"], "ibm_quantum")

    def test_error_classification(self):
        """Test error type classification."""
        from router.fallback import classify_error, RoutingError

        auth_err = classify_error(Exception("401 Unauthorized"), "ibm_quantum")
        self.assertEqual(auth_err.error_type, RoutingError.AUTH_FAILURE)

        rate_err = classify_error(Exception("Rate limit exceeded"), "aws_braket")
        self.assertEqual(rate_err.error_type, RoutingError.RATE_LIMIT)

        timeout_err = classify_error(Exception("Connection timed out"), "azure_quantum")
        self.assertEqual(timeout_err.error_type, RoutingError.NETWORK_TIMEOUT)


class TestQuantumRouting(unittest.TestCase):
    """Test routing for various qubit counts."""

    def test_5_qubit_routing(self):
        """5 qubit workload should route to local simulators."""
        from router.decision_engine import route_quantum_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=5,
        )
        providers = route_quantum_workload(spec)

        self.assertIn("local_simulator", providers)
        # Local should be first (no GPU)
        self.assertEqual(providers[0], "local_simulator")

    def test_15_qubit_routing(self):
        """15 qubit workload should include local + cloud options."""
        from router.decision_engine import route_quantum_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=15,
        )
        providers = route_quantum_workload(spec)

        # Should include both local and cloud
        self.assertTrue(
            any(p in providers for p in ["local_simulator", "qiskit_aer"]),
            "Should include local simulators for 15 qubits"
        )

    def test_35_qubit_routing(self):
        """35 qubit workload should route to cloud/hardware only."""
        from router.decision_engine import route_quantum_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=35,
        )
        providers = route_quantum_workload(spec)

        # Should NOT include local simulator (can't handle 35 qubits on 8GB)
        self.assertNotIn("local_simulator", providers)
        # Should include large-circuit cloud providers
        large_providers = {"ionq", "rigetti", "quera", "atom_computing",
                           "pasqal", "quantinuum", "nvidia_quantum_cloud"}
        self.assertTrue(
            any(p in providers for p in large_providers),
            f"Expected large-circuit providers for 35 qubits, got {providers}"
        )

    def test_nvidia_gpu_prioritizes_cuquantum(self):
        """With NVIDIA GPU, cuquantum should be prioritized for medium circuits."""
        from router.decision_engine import route_quantum_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=15,
        )
        providers = route_quantum_workload(spec, has_nvidia_gpu=True)

        self.assertIn("cuquantum", providers)
        # cuquantum should be before local_simulator
        if "local_simulator" in providers:
            self.assertLess(
                providers.index("cuquantum"),
                providers.index("local_simulator"),
            )


class TestClassicalRouting(unittest.TestCase):
    """Test routing based on hardware detection."""

    def test_default_intel_routing(self):
        """Default Intel hardware should route to local CPU options."""
        from router.decision_engine import route_classical_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.CLASSICAL_OPTIMIZATION,
        )
        providers = route_classical_workload(spec, gpu_vendor="none", cpu_vendor="intel")

        self.assertIn("local_cpu", providers)
        self.assertIn("intel_oneapi", providers)

    def test_nvidia_gpu_routing(self):
        """NVIDIA GPU should prioritize CUDA."""
        from router.decision_engine import route_classical_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.CLASSICAL_OPTIMIZATION,
        )
        providers = route_classical_workload(spec, gpu_vendor="nvidia")

        self.assertIn("nvidia_cuda", providers)
        self.assertEqual(providers[0], "nvidia_cuda")

    def test_apple_silicon_routing(self):
        """Apple Silicon should route to Metal."""
        from router.decision_engine import route_classical_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.CLASSICAL_OPTIMIZATION,
        )
        providers = route_classical_workload(spec, gpu_vendor="apple", cpu_vendor="apple")

        self.assertIn("apple_metal", providers)


class TestPriorityModes(unittest.TestCase):
    """Test cost/speed/accuracy priorities change provider ranking."""

    def test_cost_mode_prefers_free(self):
        """Cost mode should rank free providers higher."""
        from router.scoring import rank_providers
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
        )

        providers = ["ibm_quantum", "local_simulator", "quantinuum"]
        ranked = rank_providers(providers, spec, priority="cost")

        # local_simulator is free and local — should rank high in cost mode
        self.assertEqual(ranked[0]["provider_id"], "local_simulator")

    def test_speed_mode_prefers_fast(self):
        """Speed mode should rank fast providers higher."""
        from router.scoring import rank_providers
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
        )

        providers = ["ibm_quantum", "local_simulator", "quantinuum"]
        ranked = rank_providers(providers, spec, priority="speed")

        # local_simulator should beat cloud in speed
        local_rank = next(r["rank"] for r in ranked if r["provider_id"] == "local_simulator")
        ibm_rank = next(r["rank"] for r in ranked if r["provider_id"] == "ibm_quantum")
        self.assertLess(local_rank, ibm_rank)

    def test_accuracy_mode_prefers_fidelity(self):
        """Accuracy mode should rank high-fidelity providers higher."""
        from router.scoring import rank_providers
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
        )

        providers = ["dwave", "local_simulator", "quantinuum"]
        ranked = rank_providers(providers, spec, priority="accuracy")

        # local_simulator (perfect accuracy) should beat dwave (0.75)
        local_rank = next(r["rank"] for r in ranked if r["provider_id"] == "local_simulator")
        dwave_rank = next(r["rank"] for r in ranked if r["provider_id"] == "dwave")
        self.assertLess(local_rank, dwave_rank)


class TestScoringDeterminism(unittest.TestCase):
    """Test that same inputs produce same scores."""

    def test_same_inputs_same_score(self):
        """Identical inputs must produce identical scores."""
        from router.scoring import calculate_provider_score
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
            priority="cost",
        )

        score1 = calculate_provider_score("ibm_quantum", spec, "cost")
        score2 = calculate_provider_score("ibm_quantum", spec, "cost")
        score3 = calculate_provider_score("ibm_quantum", spec, "cost")

        self.assertEqual(score1, score2)
        self.assertEqual(score2, score3)

    def test_ranking_deterministic(self):
        """Same provider list produces same ranking order."""
        from router.scoring import rank_providers
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
        )

        providers = ["ibm_quantum", "local_simulator", "aws_braket", "ionq"]

        ranked1 = rank_providers(providers, spec, "cost")
        ranked2 = rank_providers(providers, spec, "cost")

        order1 = [r["provider_id"] for r in ranked1]
        order2 = [r["provider_id"] for r in ranked2]
        self.assertEqual(order1, order2)


class TestDecisionEngine(unittest.TestCase):
    """Test decision engine routing functions."""

    def test_hybrid_routing_returns_both(self):
        """Hybrid routing should return quantum and classical components."""
        from router.decision_engine import route_hybrid_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.HYBRID_COMPUTATION,
            qubit_count=5,
        )

        result = route_hybrid_workload(spec)
        self.assertIn("quantum", result)
        self.assertIn("classical", result)
        self.assertGreater(len(result["quantum"]), 0)
        self.assertGreater(len(result["classical"]), 0)

    def test_annealing_constraint(self):
        """Annealing constraint should prioritize D-Wave."""
        from router.decision_engine import route_quantum_workload
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=5,
            constraints={"annealing": True},
        )

        providers = route_quantum_workload(spec)
        self.assertEqual(providers[0], "dwave")

    def test_capability_filter(self):
        """Capability filter should remove providers that can't handle workload."""
        from router.decision_engine import filter_by_capabilities
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=50,
        )

        providers = ["local_simulator", "ibm_quantum", "ionq"]
        provider_info = {
            "local_simulator": {"max_qubits": 20},
            "ibm_quantum": {"max_qubits": 127},
            "ionq": {"max_qubits": 36},
        }

        filtered = filter_by_capabilities(providers, spec, provider_info)

        self.assertNotIn("local_simulator", filtered)  # 20 < 50
        self.assertIn("ibm_quantum", filtered)          # 127 >= 50
        self.assertNotIn("ionq", filtered)               # 36 < 50


class TestRouterCommands(unittest.TestCase):
    """Test terminal command argument parsing."""

    def test_parse_route_args(self):
        """Test command argument parsing."""
        from router.commands import _parse_route_args

        result = _parse_route_args([
            "--qubits", "10", "--priority", "cost", "--depth", "100",
        ])

        self.assertIsNotNone(result)
        self.assertEqual(result["qubit_count"], 10)
        self.assertEqual(result["priority"], "cost")
        self.assertEqual(result["circuit_depth"], 100)
        self.assertEqual(result["workload_type"], "quantum_simulation")

    def test_parse_empty_args(self):
        """Empty args should return None."""
        from router.commands import _parse_route_args

        self.assertIsNone(_parse_route_args([]))

    def test_parse_classical_defaults(self):
        """Classical workload type inferred when no qubits specified."""
        from router.commands import _parse_route_args

        result = _parse_route_args(["--threads", "2", "--memory", "512"])
        self.assertEqual(result["workload_type"], "classical_optimization")


class TestResourcePrediction(unittest.TestCase):
    """Test CPU and RAM usage predictions."""

    def test_local_cpu_prediction(self):
        """Local CPU provider should predict meaningful CPU usage."""
        from router.safety_filter import predict_cpu_usage
        from router.workload_spec import WorkloadSpec

        spec = WorkloadSpec(classical_cpu_threads=2)
        cpu = predict_cpu_usage("local_cpu", spec)
        self.assertGreater(cpu, 0)
        self.assertLessEqual(cpu, 100)

    def test_cloud_provider_low_cpu(self):
        """Cloud quantum providers should predict low local CPU usage."""
        from router.safety_filter import predict_cpu_usage
        from router.workload_spec import WorkloadSpec, WorkloadType

        spec = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=10,
        )
        cpu = predict_cpu_usage("ibm_quantum", spec)
        self.assertLess(cpu, 10)  # Cloud providers use <10% local CPU

    def test_quantum_memory_prediction_scales(self):
        """RAM prediction for quantum sim should scale with qubit count."""
        from router.safety_filter import predict_ram_usage
        from router.workload_spec import WorkloadSpec, WorkloadType

        # Use qubit counts large enough that state vector exceeds base estimate
        # 20 qubits: 2^20 * 16 bytes = 16MB * 1.5 = 24MB (< 300MB base)
        # 25 qubits: 2^25 * 16 bytes = 512MB * 1.5 = 768MB (> 300MB base)
        spec_20 = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=20,
        )
        spec_25 = WorkloadSpec(
            workload_type=WorkloadType.QUANTUM_SIMULATION,
            qubit_count=25,
        )

        ram_20 = predict_ram_usage("local_simulator", spec_20)
        ram_25 = predict_ram_usage("local_simulator", spec_25)

        self.assertGreater(ram_25, ram_20)


class TestFullRouteWorkflow(unittest.TestCase):
    """Integration tests for the full routing workflow."""

    def test_route_returns_complete_result(self):
        """Route should return all expected fields."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        result = router.route({
            "workload_type": "quantum_simulation",
            "qubit_count": 10,
            "priority": "cost",
        })

        required_keys = [
            "provider", "score", "fallbacks", "alternatives",
            "reasoning", "safety", "workload_summary",
            "routing_time_ms", "timestamp",
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

        self.assertIsInstance(result["score"], float)
        self.assertIsInstance(result["fallbacks"], list)
        self.assertGreater(result["routing_time_ms"], 0)

        IntelligentRouter._instance = None

    def test_get_recommendations(self):
        """get_recommendations should return ranked list with safety info."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        recs = router.get_recommendations({
            "workload_type": "quantum_simulation",
            "qubit_count": 5,
            "priority": "cost",
        })

        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)

        for rec in recs:
            self.assertIn("provider_id", rec)
            self.assertIn("score", rec)
            self.assertIn("rank", rec)
            self.assertIn("safe", rec)

        IntelligentRouter._instance = None

    def test_routing_history_recorded(self):
        """Routing decisions should be recorded in history."""
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()
        router._history.clear()

        router.route({"qubit_count": 5})
        router.route({"qubit_count": 10})

        history = router.get_history()
        self.assertEqual(len(history), 2)

        IntelligentRouter._instance = None

    def test_route_under_100ms(self):
        """Routing should complete in under 100ms (excluding first lazy init)."""
        import time
        from router.intelligent_router import IntelligentRouter

        IntelligentRouter._instance = None
        router = IntelligentRouter()

        # Mock resource usage to avoid psutil.cpu_percent(interval=0.1) latency
        mock_usage = (20.0, 30.0, 8192.0)

        # First call triggers lazy init (don't time this)
        with patch.object(router, '_get_resource_usage', return_value=mock_usage):
            router.route({"qubit_count": 5})

        # Second call should be fast
        with patch.object(router, '_get_resource_usage', return_value=mock_usage):
            start = time.perf_counter()
            router.route({"qubit_count": 10, "priority": "speed"})
            elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertLess(elapsed_ms, 100, f"Routing took {elapsed_ms:.1f}ms, expected <100ms")

        IntelligentRouter._instance = None


if __name__ == "__main__":
    unittest.main(verbosity=2)
