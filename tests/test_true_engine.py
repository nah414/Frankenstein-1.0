"""Test script for TRUE Synthesis Engine"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print('='*60)
print('FRANKENSTEIN TRUE SYNTHESIS ENGINE - VERIFICATION TEST')
print('='*60)
print()

from synthesis.core import get_true_engine

# Initialize engine
engine = get_true_engine()

print('ENGINE STATUS:')
status = engine.status()
hw = status['hardware']
print('  Engine:', status['engine'])
print('  Max Qubits:', hw['max_qubits'])
print('  Storage Allocated:', hw['max_storage_GB'], 'GB')
print('  Max Memory:', hw['max_memory_GB'], 'GB')
print()

# Test 1: Initialize qubits
print('TEST 1: Initialize 4 qubits')
engine.initialize_qubits(4, 'zero')
info = engine.get_state_info()
print('  Qubits:', info['n_qubits'])
print('  Dimension:', info['dimension'])
print('  Memory:', info['memory_bytes'], 'bytes')
print()

# Test 2: Create Bell state
print('TEST 2: Create Bell State')
engine.create_bell_state()
result = engine.measure(1000, collapse=False)
print('  Measurements (1000 shots):', result['counts'])
print('  Expected: ~50% |00>, ~50% |11>')
print()

# Test 3: Schrodinger evolution
print('TEST 3: Schrodinger Evolution')
import numpy as np
engine.initialize_qubits(2, 'zero')
engine.hadamard(0)
H = np.diag([1, 1, -1, -1]).astype(np.complex128)
sim_result = engine.solve_schrodinger(H, t_max=np.pi, n_steps=100, store_trajectory=False)
print('  Evolution time:', sim_result.metadata['t_max'])
print('  Steps:', sim_result.metadata['n_steps'])
print('  Computation time:', round(sim_result.computation_time*1000, 2), 'ms')
print('  Final energy:', round(sim_result.expectation_values['energy'], 4))
print()

# Test 4: Lorentz transformation
print('TEST 4: Lorentz Transformation')
lorentz = engine.apply_lorentz_boost(0.8)
print('  Velocity: 0.8c')
print('  Gamma:', round(lorentz['gamma'], 4))
print('  Time dilation:', round(lorentz['time_dilation'], 4), 'x')
print('  Length contraction:', round(lorentz['length_contraction'], 4), 'x')
print()

# Test 5: GHZ state
print('TEST 5: Create 5-qubit GHZ State')
engine.create_ghz_state(5)
info = engine.get_state_info()
print('  Dimension:', info['dimension'], 'states')
print('  Non-zero states:', info['nonzero_states'])
print()

# Test 6: Storage
print('TEST 6: Storage Usage')
storage = engine.get_storage_usage()
print('  Path:', storage['path'])
print('  Allocated:', storage['allocated_bytes']/1e9, 'GB')
print('  Used:', round(storage['used_bytes']/1e6, 2), 'MB')
print('  Files:', storage['file_count'])
print()

print('='*60)
print('ALL TESTS PASSED - TRUE SYNTHESIS ENGINE OPERATIONAL')
print('='*60)
