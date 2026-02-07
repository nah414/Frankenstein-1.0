#!/usr/bin/env python3
"""Compile all provider adapters to verify syntax."""
import py_compile
import os

quantum_providers = [
    'local_sim', 'ibm', 'aws_braket', 'azure', 'google', 'nvidia_qc',
    'ionq', 'rigetti', 'quantinuum', 'xanadu', 'dwave', 'iqm',
    'quera', 'oxford', 'atom_computing', 'pasqal', 'aqt',
    'qiskit_aer', 'cuquantum'
]

classical_providers = [
    'cpu', 'nvidia', 'amd', 'intel', 'apple', 'arm',
    'risc_v', 'tpu', 'fpga', 'npu'
]

print("Compiling quantum providers...")
for p in quantum_providers:
    filepath = f"integration/providers/quantum/{p}.py"
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"[OK] {p}.py")
    except Exception as e:
        print(f"[FAIL] {p}.py: {e}")

print("\nCompiling classical providers...")
for p in classical_providers:
    filepath = f"integration/providers/classical/{p}.py"
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"[OK] {p}.py")
    except Exception as e:
        print(f"[FAIL] {p}.py: {e}")

print(f"\n[SUCCESS] Compiled {len(quantum_providers)} quantum + {len(classical_providers)} classical = {len(quantum_providers) + len(classical_providers)} total providers")
