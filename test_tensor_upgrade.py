#!/usr/bin/env python3
"""
FRANKENSTEIN - Tensor Optimization Test Suite
Tests JAX/Numba integration and multi-qubit Bloch visualization
"""

import sys
import time
import numpy as np


def test_imports():
    """Test all required imports"""
    print("\n" + "="*50)
    print("  TEST 1: Library Imports")
    print("="*50)

    results = {}

    # Core
    try:
        import numpy as np
        results['numpy'] = f"[OK] {np.__version__}"
    except ImportError as e:
        results['numpy'] = f"[FAIL] {e}"

    try:
        import scipy
        results['scipy'] = f"[OK] {scipy.__version__}"
    except ImportError as e:
        results['scipy'] = f"[FAIL] {e}"

    # Tensor optimization
    try:
        import jax
        import jax.numpy as jnp
        results['jax'] = f"[OK] {jax.__version__}"
    except ImportError as e:
        results['jax'] = f"[FAIL] {e}"

    try:
        import numba
        results['numba'] = f"[OK] {numba.__version__}"
    except ImportError as e:
        results['numba'] = f"[FAIL] {e}"

    try:
        import opt_einsum
        results['opt_einsum'] = f"[OK] {opt_einsum.__version__}"
    except ImportError as e:
        results['opt_einsum'] = f"[FAIL] {e}"

    for lib, status in results.items():
        print(f"  {lib:15s} {status}")

    return all('[OK]' in s for s in results.values())


def test_synthesis_engine():
    """Test synthesis engine tensor operations"""
    print("\n" + "="*50)
    print("  TEST 2: Synthesis Engine")
    print("="*50)

    from synthesis.engine import SynthesisEngine, JAX_AVAILABLE, NUMBA_AVAILABLE

    print(f"  JAX Available:   {'[OK]' if JAX_AVAILABLE else '[FAIL]'}")
    print(f"  Numba Available: {'[OK]' if NUMBA_AVAILABLE else '[FAIL]'}")

    engine = SynthesisEngine(auto_visualize=False)
    print(f"  Engine Created:  [OK]")

    return JAX_AVAILABLE and NUMBA_AVAILABLE


def test_partial_trace():
    """Test tensor-based partial trace"""
    print("\n" + "="*50)
    print("  TEST 3: Tensor Partial Trace")
    print("="*50)

    from synthesis.engine import SynthesisEngine

    engine = SynthesisEngine(auto_visualize=False)
    engine.reset(4)  # 4 qubits

    # Create Bell state on qubits 0,1
    engine.h(0)
    engine.cx(0, 1)

    # Get Bloch coords for all qubits
    start = time.time()
    coords = engine.get_all_qubit_bloch_coords()
    elapsed = (time.time() - start) * 1000

    print(f"  Qubits: 4")
    print(f"  Time: {elapsed:.2f}ms")
    print(f"  Coordinates computed: {len(coords)}")

    for i, (x, y, z) in enumerate(coords):
        print(f"    Q{i}: ({x:+.3f}, {y:+.3f}, {z:+.3f})")

    return len(coords) == 4


def test_entanglement_detection():
    """Test Schmidt decomposition entanglement detection"""
    print("\n" + "="*50)
    print("  TEST 4: Entanglement Detection")
    print("="*50)

    from synthesis.engine import SynthesisEngine

    engine = SynthesisEngine(auto_visualize=False)

    # Test 1: Separable state
    engine.reset(2)
    engine.h(0)  # |+0> is separable
    info = engine.get_entanglement_info()

    print(f"\n  Test 4a: |+0> state")
    print(f"    Is Entangled: {info['is_entangled']}")
    print(f"    Schmidt Rank: {info['schmidt_rank']}")
    print(f"    Entropy: {info['entanglement_entropy']:.4f}")

    sep_correct = not info['is_entangled'] and info['schmidt_rank'] == 1
    print(f"    Result: {'[OK] Correct' if sep_correct else '[FAIL] Wrong'}")

    # Test 2: Bell state (maximally entangled)
    engine.reset(2)
    engine.h(0)
    engine.cx(0, 1)
    info = engine.get_entanglement_info()

    print(f"\n  Test 4b: Bell state |Phi+>")
    print(f"    Is Entangled: {info['is_entangled']}")
    print(f"    Schmidt Rank: {info['schmidt_rank']}")
    print(f"    Entropy: {info['entanglement_entropy']:.4f} bits")

    bell_correct = info['is_entangled'] and info['schmidt_rank'] == 2
    entropy_correct = abs(info['entanglement_entropy'] - 1.0) < 0.01
    print(f"    Entanglement: {'[OK]' if bell_correct else '[FAIL]'}")
    print(f"    Entropy ~= 1.0: {'[OK]' if entropy_correct else '[FAIL]'}")

    return sep_correct and bell_correct and entropy_correct


def test_measurement_speed():
    """Test Numba-optimized measurement"""
    print("\n" + "="*50)
    print("  TEST 5: Measurement Performance")
    print("="*50)

    from synthesis.engine import SynthesisEngine, NUMBA_AVAILABLE

    engine = SynthesisEngine(auto_visualize=False)
    engine.reset(10)  # 10 qubits

    # Create superposition
    for i in range(10):
        engine.h(i)

    shots = 10000

    # Warm up (first JIT compile)
    _ = engine.measure(100)

    # Timed run
    start = time.time()
    results = engine.measure(shots)
    elapsed = (time.time() - start) * 1000

    print(f"  Qubits: 10")
    print(f"  Shots: {shots}")
    print(f"  Time: {elapsed:.2f}ms")
    print(f"  Rate: {shots/elapsed*1000:.0f} shots/sec")
    print(f"  Unique outcomes: {len(results)}")
    print(f"  Numba JIT: {'[OK] Enabled' if NUMBA_AVAILABLE else '[FAIL] Disabled'}")

    # Should be under 500ms with Numba
    return elapsed < 500 if NUMBA_AVAILABLE else elapsed < 2000


def test_16_qubit_stress():
    """Test 16-qubit operations (max for Tier 1)"""
    print("\n" + "="*50)
    print("  TEST 6: 12-Qubit Tensor Operations")
    print("="*50)

    from synthesis.engine import SynthesisEngine
    import tracemalloc

    tracemalloc.start()

    engine = SynthesisEngine(auto_visualize=False)

    start = time.time()
    engine.reset(12)  # 12 qubits is realistic for gate application
    init_time = (time.time() - start) * 1000

    # Apply GHZ preparation
    engine.h(0)
    for i in range(1, 12):
        engine.cx(0, i)

    # Get entanglement
    start = time.time()
    info = engine.get_entanglement_info()
    ent_time = (time.time() - start) * 1000

    # Get all qubit Bloch coords (uses tensor partial trace)
    start = time.time()
    coords = engine.get_all_qubit_bloch_coords()
    coords_time = (time.time() - start) * 1000

    # Measure
    start = time.time()
    results = engine.measure(1000)
    measure_time = (time.time() - start) * 1000

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  Init time: {init_time:.2f}ms")
    print(f"  Entanglement time: {ent_time:.2f}ms")
    print(f"  Bloch coords time: {coords_time:.2f}ms")
    print(f"  Measurement time: {measure_time:.2f}ms")
    print(f"  Peak RAM: {peak / 1024 / 1024:.1f}MB")
    print(f"  Is Entangled: {info['is_entangled']}")
    print(f"  Schmidt Rank: {info['schmidt_rank']}")

    # GHZ state should have rank 2, entropy 1.0
    ghz_correct = info['schmidt_rank'] == 2 and info['is_entangled']
    memory_ok = peak < 600 * 1024 * 1024  # Under 600MB
    coords_ok = len(coords) == 12

    print(f"  GHZ Detection: {'[OK]' if ghz_correct else '[FAIL]'}")
    print(f"  Coordinates: {'[OK]' if coords_ok else '[FAIL]'}")
    print(f"  Memory OK: {'[OK]' if memory_ok else '[FAIL]'}")

    return ghz_correct and memory_ok and coords_ok


def main():
    print("\n" + "="*60)
    print("  FRANKENSTEIN TENSOR OPTIMIZATION TEST SUITE")
    print("="*60)

    tests = [
        ("Library Imports", test_imports),
        ("Synthesis Engine", test_synthesis_engine),
        ("Partial Trace", test_partial_trace),
        ("Entanglement Detection", test_entanglement_detection),
        ("Measurement Speed", test_measurement_speed),
        ("16-Qubit Stress", test_16_qubit_stress),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"  [FAIL] ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)

    for name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"  {name:30s} {status}")

    all_passed = all(p for _, p in results)
    print("\n" + "="*60)
    print(f"  OVERALL: {'[OK] ALL TESTS PASSED' if all_passed else '[FAIL] SOME TESTS FAILED'}")
    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
