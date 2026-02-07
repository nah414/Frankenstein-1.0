#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Synthesis Submodule
Phase 2, Step 3

Quantum computation tools including:
- Predefined circuit library
- Visualization tools
- Gate definitions
"""

from .circuits import (
    QuantumCircuitLibrary,
    CIRCUIT_REGISTRY,
    get_circuit,
    list_circuits,
)

from .visualization import (
    QuantumVisualizer,
    get_visualizer,
)

__all__ = [
    # Circuit library
    'QuantumCircuitLibrary',
    'CIRCUIT_REGISTRY',
    'get_circuit',
    'list_circuits',
    # Visualization
    'QuantumVisualizer',
    'get_visualizer',
]
