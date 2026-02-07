"""
FRANKENSTEIN 1.0 - Synthesis Core Module
Phase 2 Step 3: TRUE Synthesis Engine

This is the real computational backend for quantum simulation.
"""

from .true_engine import (
    TrueSynthesisEngine,
    QuantumState,
    SimulationResult,
    SimulationMode,
    HardwareConfig,
    get_true_engine,
    create_engine,
    HBAR, C, ME
)

__all__ = [
    'TrueSynthesisEngine',
    'QuantumState', 
    'SimulationResult',
    'SimulationMode',
    'HardwareConfig',
    'get_true_engine',
    'create_engine',
    'HBAR', 'C', 'ME'
]
