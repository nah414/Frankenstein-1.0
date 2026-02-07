#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Provider Adapter Test Suite
Quick verification that all 5 adapters work correctly.
"""

import sys


def test_imports():
    """Test that all adapters import successfully."""
    print("=" * 60)
    print("TEST 1: Import Verification")
    print("=" * 60)
    
    try:
        from integration.providers.base import ProviderAdapter
        print("[OK] base.py imports successfully")
    except Exception as e:
        print(f"[FAIL] base.py failed: {e}")
        return False
    
    try:
        from integration.providers.quantum.local_sim import LocalSimAdapter
        print("[OK] local_sim.py imports successfully")
    except Exception as e:
        print(f"[FAIL] local_sim.py failed: {e}")
        return False
    
    try:
        from integration.providers.classical.cpu import LocalCPUAdapter
        print("[OK] cpu.py imports successfully")
    except Exception as e:
        print(f"[FAIL] cpu.py failed: {e}")
        return False
    
    try:
        from integration.providers.quantum.ibm import IBMQuantumAdapter
        print("[OK] ibm.py imports successfully")
    except Exception as e:
        print(f"[FAIL] ibm.py failed: {e}")
        return False
    
    try:
        from integration.providers.classical.nvidia import NVIDIACUDAAdapter
        print("[OK] nvidia.py imports successfully")
    except Exception as e:
        print(f"[FAIL] nvidia.py failed: {e}")
        return False
    
    try:
        from integration.providers.quantum.aws_braket import AWSBraketAdapter
        print("[OK] aws_braket.py imports successfully")
    except Exception as e:
        print(f"[FAIL] aws_braket.py failed: {e}")
        return False
    
    print()
    return True


def test_local_simulator():
    """Test local quantum simulator."""
    print("=" * 60)
    print("TEST 2: Local Quantum Simulator")
    print("=" * 60)
    
    try:
        from integration.providers.quantum.local_sim import LocalSimAdapter
        
        sim = LocalSimAdapter()
        print(f"Initial status: {sim.status.value}")
        
        success = sim.connect()
        print(f"Connect result: {success}")
        print(f"After connect: {sim.status.value}")
        
        backends = sim.get_backends()
        print(f"Backends: {[b.name for b in backends]}")
        
        if backends:
            b = backends[0]
            print(f"  Name: {b.name}")
            print(f"  Qubits: {b.num_qubits}")
        
        print("[OK] Local simulator test PASSED")
        print()
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_local_cpu():
    """Test local CPU adapter."""
    print("=" * 60)
    print("TEST 3: Local CPU Compute")
    print("=" * 60)
    
    try:
        from integration.providers.classical.cpu import LocalCPUAdapter
        
        cpu = LocalCPUAdapter()
        print(f"Initial status: {cpu.status.value}")
        
        success = cpu.connect()
        print(f"Connect result: {success}")
        print(f"After connect: {cpu.status.value}")
        
        backends = cpu.get_backends()
        print(f"Backends: {[b.name for b in backends]}")
        
        if backends:
            b = backends[0]
            print(f"  Name: {b.name}")
            print(f"  Cores: {b.compute_units}")
            print(f"  Memory: {b.memory_gb:.1f} GB")
        
        print("[OK] Local CPU test PASSED")
        print()
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_job_submission():
    """Test job submission."""
    print("=" * 60)
    print("TEST 4: Job Submission")
    print("=" * 60)
    
    try:
        from integration.providers.quantum.local_sim import LocalSimAdapter
        
        sim = LocalSimAdapter()
        sim.connect()
        
        payload = {"qubits": 2, "gates": [], "measure_all": True}
        job_id = sim.submit_job(payload, "statevector_simulator", shots=1024)
        print(f"Job ID: {job_id}")
        
        status = sim.get_job_status(job_id)
        print(f"Status: {status.value}")
        
        result = sim.get_job_result(job_id)
        if result:
            print(f"Provider: {result.provider_id}")
            print(f"Output: {list(result.output.keys()) if result.output else 'None'}")
        
        print("[OK] Job submission test PASSED")
        print()
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests."""
    print()
    print("=" * 60)
    print("FRANKENSTEIN 1.0 - PROVIDER ADAPTER TEST SUITE")
    print("Phase 3, Step 4 Verification")
    print("=" * 60)
    print()
    
    results = [
        ("Import Verification", test_imports()),
        ("Local Quantum Simulator", test_local_simulator()),
        ("Local CPU Compute", test_local_cpu()),
        ("Job Submission", test_job_submission()),
    ]
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
    
    total = sum(1 for _, p in results if p)
    print()
    print(f"Result: {total}/{len(results)} tests passed")
    
    if total == len(results):
        print("\nSUCCESS: All tests passed!")
        return 0
    else:
        print("\nWARNING: Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
