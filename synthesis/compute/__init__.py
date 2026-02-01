"""
FRANKENSTEIN 1.0 - Compute Engine
Phase 2 Step 3: Real Computational Synthesis

This module provides ACTUAL computation capabilities:
- Quantum state simulations (Schrödinger equation)
- Mathematical computations (symbolic + numeric)
- Physics calculations (relativistic, quantum mechanics)
- Data synthesis and analysis

NOT a toy simulator - performs real calculations on local hardware.
"""

from .engine import ComputeEngine, ComputeResult, ComputeMode
from .quantum_compute import QuantumCompute
from .math_compute import MathCompute
from .physics_compute import PhysicsCompute

__all__ = [
    'ComputeEngine',
    'ComputeResult', 
    'ComputeMode',
    'QuantumCompute',
    'MathCompute',
    'PhysicsCompute',
]
