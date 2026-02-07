#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Synthesis Engine Module
Phase 2, Step 3: Quantum-Classical Hybrid Computation

This module provides the core synthesis capabilities:
- SynthesisEngine: Main quantum computation engine
- QuantumCircuitLibrary: Predefined quantum circuits
- QuantumVisualizer: Visualization tools
- Hamiltonians for time evolution

Usage:
    from synthesis import get_synthesis_engine, ComputeMode
    
    engine = get_synthesis_engine()
    engine.reset(2)        # Initialize 2 qubits
    engine.h(0)            # Hadamard on qubit 0
    engine.cx(0, 1)        # CNOT to create Bell state
    result = engine.compute()  # Run and visualize
"""

from .engine import (
    # Main engine
    SynthesisEngine,
    get_synthesis_engine,
    
    # Enums
    ComputeMode,
    VisualizationMode,
    
    # Result class
    ComputeResult,
    
    # Predefined Hamiltonians
    hamiltonian_pauli_x,
    hamiltonian_pauli_z,
    hamiltonian_free_precession,
)

from .quantum import (
    # Circuit library
    QuantumCircuitLibrary,
    CIRCUIT_REGISTRY,
    get_circuit,
    list_circuits,
    
    # Visualization
    QuantumVisualizer,
    get_visualizer,
)

__all__ = [
    # Engine
    'SynthesisEngine',
    'get_synthesis_engine',
    
    # Modes
    'ComputeMode',
    'VisualizationMode',
    
    # Results
    'ComputeResult',
    
    # Hamiltonians
    'hamiltonian_pauli_x',
    'hamiltonian_pauli_z',
    'hamiltonian_free_precession',
    
    # Circuits
    'QuantumCircuitLibrary',
    'CIRCUIT_REGISTRY',
    'get_circuit',
    'list_circuits',
    
    # Visualization
    'QuantumVisualizer',
    'get_visualizer',
]
