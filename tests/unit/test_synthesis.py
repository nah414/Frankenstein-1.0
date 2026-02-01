#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Synthesis Engine Test
Phase 2, Step 3: Verification Tests

Run this file to verify the synthesis engine components work correctly.

Usage:
    python tests/unit/test_synthesis.py
"""

import sys
import os
import numpy as np
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_synthesis_imports():
    """Test that all synthesis modules import correctly"""
    print("Testing imports...")
    
    try:
        from synthesis import (
            SynthesisEngine,
            get_synthesis_engine,
            ComputeMode,
            VisualizationMode,
            ComputeResult,
            hamiltonian_pauli_x,
            hamiltonian_pauli_z,
            QuantumCircuitLibrary,
            get_circuit,
            list_circuits,
            QuantumVisualizer,
        )
        print("  ✅ All synthesis imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_basic_gates():
    """Test basic quantum gate operations"""
    print("\nTesting basic gates...")
    
    from synthesis import get_synthesis_engine
    
    engine = get_synthesis_engine()
    engine.auto_visualize = False  # Disable for testing
    
    # Test 1: Hadamard creates superposition
    engine.reset(1)
    engine.h(0)
    probs = engine.get_probabilities()
    
    assert abs(probs.get('0', 0) - 0.5) < 0.01, "Hadamard should create 50/50 superposition"
    assert abs(probs.get('1', 0) - 0.5) < 0.01, "Hadamard should create 50/50 superposition"
    print("  ✅ Hadamard gate works")
    
    # Test 2: X gate flips
    engine.reset(1)
    engine.x(0)
    probs = engine.get_probabilities()
    
    assert probs.get('1', 0) > 0.99, "X gate should flip |0⟩ to |1⟩"
    print("  ✅ Pauli-X gate works")
    
    # Test 3: Bell state
    engine.reset(2)
    engine.h(0)
    engine.cx(0, 1)
    probs = engine.get_probabilities()
    
    assert abs(probs.get('00', 0) - 0.5) < 0.01, "Bell state should have 50% |00⟩"
    assert abs(probs.get('11', 0) - 0.5) < 0.01, "Bell state should have 50% |11⟩"
    print("  ✅ Bell state creation works")
    
    return True


def test_bloch_coordinates():
    """Test Bloch sphere coordinate calculation"""
    print("\nTesting Bloch coordinates...")
    
    from synthesis import get_synthesis_engine
    
    engine = get_synthesis_engine()
    engine.auto_visualize = False
    
    # Test |0⟩ state - should be at north pole
    engine.reset(1)
    x, y, z = engine.get_bloch_coords(0)
    assert abs(z - 1.0) < 0.01, "|0⟩ should have z=1"
    print(f"  ✅ |0⟩ state: z={z:.4f} (expected 1.0)")
    
    # Test |1⟩ state - should be at south pole
    engine.reset(1)
    engine.x(0)
    x, y, z = engine.get_bloch_coords(0)
    assert abs(z + 1.0) < 0.01, "|1⟩ should have z=-1"
    print(f"  ✅ |1⟩ state: z={z:.4f} (expected -1.0)")
    
    # Test |+⟩ state - should be on equator at x=1
    engine.reset(1)
    engine.h(0)
    x, y, z = engine.get_bloch_coords(0)
    assert abs(x - 1.0) < 0.01, "|+⟩ should have x=1"
    assert abs(z) < 0.01, "|+⟩ should have z=0"
    print(f"  ✅ |+⟩ state: x={x:.4f}, z={z:.4f} (expected x=1, z=0)")
    
    return True


def test_schrodinger_evolution():
    """Test Schrödinger equation solver"""
    print("\nTesting time evolution...")
    
    from synthesis import get_synthesis_engine, hamiltonian_pauli_x
    
    engine = get_synthesis_engine()
    engine.auto_visualize = False
    
    # Start in |0⟩, evolve under σx Hamiltonian for π/2
    # This should give |ψ⟩ ≈ (|0⟩ - i|1⟩)/√2
    engine.reset(1)
    H = hamiltonian_pauli_x(omega=1.0)
    engine.evolve_unitary(np.pi, H)
    
    # After π evolution, should flip to |1⟩ (approximately)
    probs = engine.get_probabilities()
    print(f"  After π rotation under σx: P(|0⟩)={probs.get('0', 0):.4f}, P(|1⟩)={probs.get('1', 0):.4f}")
    
    # Should be mostly |1⟩
    assert probs.get('1', 0) > 0.9, "π rotation under σx should flip |0⟩ to |1⟩"
    print("  ✅ Time evolution works")
    
    return True


def test_circuit_library():
    """Test predefined circuit library"""
    print("\nTesting circuit library...")
    
    from synthesis import list_circuits, get_circuit, QuantumCircuitLibrary, get_synthesis_engine
    
    # List circuits
    circuits = list_circuits()
    print(f"  Available circuits: {circuits}")
    assert len(circuits) >= 5, "Should have at least 5 predefined circuits"
    print(f"  ✅ Found {len(circuits)} circuits")
    
    # Get specific circuit
    bell_info = get_circuit('bell')
    assert bell_info is not None, "Bell circuit should exist"
    assert bell_info['qubits'] == 2, "Bell circuit needs 2 qubits"
    print("  ✅ Circuit registry works")
    
    # Apply GHZ circuit
    engine = get_synthesis_engine()
    engine.auto_visualize = False
    engine.reset(3)
    QuantumCircuitLibrary.ghz_state(engine, 3)
    probs = engine.get_probabilities()
    
    assert abs(probs.get('000', 0) - 0.5) < 0.01, "GHZ should have 50% |000⟩"
    assert abs(probs.get('111', 0) - 0.5) < 0.01, "GHZ should have 50% |111⟩"
    print("  ✅ GHZ circuit works")
    
    return True


def test_measurement():
    """Test measurement simulation"""
    print("\nTesting measurement...")
    
    from synthesis import get_synthesis_engine
    
    engine = get_synthesis_engine()
    engine.auto_visualize = False
    
    # Create Bell state and measure
    engine.reset(2)
    engine.h(0)
    engine.cx(0, 1)
    
    results = engine.measure(shots=1000)
    
    # Should only get |00⟩ and |11⟩ outcomes
    assert '01' not in results, "Bell state should not produce |01⟩"
    assert '10' not in results, "Bell state should not produce |10⟩"
    
    # Counts should be roughly equal
    count_00 = results.get('00', 0)
    count_11 = results.get('11', 0)
    
    assert abs(count_00 - 500) < 100, "Bell state should have ~50% |00⟩"
    assert abs(count_11 - 500) < 100, "Bell state should have ~50% |11⟩"
    
    print(f"  Measurement results: |00⟩={count_00}, |11⟩={count_11}")
    print("  ✅ Measurement simulation works")
    
    return True


def test_compute_result():
    """Test compute() method and result structure"""
    print("\nTesting compute result...")
    
    from synthesis import get_synthesis_engine, ComputeMode
    
    engine = get_synthesis_engine()
    engine.auto_visualize = False
    
    # Create simple state and compute
    engine.reset(1)
    engine.h(0)
    
    result = engine.compute(mode=ComputeMode.STATEVECTOR, shots=512, visualize=False)
    
    assert result.success, "Computation should succeed"
    assert result.num_qubits == 1, "Should have 1 qubit"
    assert result.gate_count == 1, "Should have 1 gate"
    assert result.bloch_coords is not None, "Should have Bloch coordinates"
    assert result.probabilities is not None, "Should have probabilities"
    assert result.measurements is not None, "Should have measurements"
    assert result.compute_time_ms >= 0, "Should have compute time"
    
    print(f"  Result ID: {result.result_id}")
    print(f"  Bloch coords: {result.bloch_coords}")
    print(f"  Compute time: {result.compute_time_ms:.2f}ms")
    print("  ✅ Compute result structure works")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("FRANKENSTEIN 1.0 - SYNTHESIS ENGINE TESTS")
    print("Phase 2, Step 3 Verification")
    print("=" * 60)
    
    tests = [
        test_synthesis_imports,
        test_basic_gates,
        test_bloch_coordinates,
        test_schrodinger_evolution,
        test_circuit_library,
        test_measurement,
        test_compute_result,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Synthesis Engine is ready!")
    else:
        print(f"\n⚠️  {failed} test(s) failed - Review above errors")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
