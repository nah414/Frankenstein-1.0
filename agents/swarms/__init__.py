"""
FRANKENSTEIN 1.0 - Swarms Integration
Phase 2 Step 3: Real Computational Agents

Enterprise-grade multi-agent framework integration for FRANKENSTEIN.
Provides REAL computation, not toy simulations.

Swarms Framework: https://github.com/kyegomez/swarms
"""

from .compute_swarm import (
    ComputeSwarm,
    PhysicsAgent,
    MathAgent,
    QuantumSimAgent,
    get_compute_swarm
)

from .synthesis_agents import (
    SynthesisAgentSwarm,
    SchrodingerAgent,
    LorentzAgent,
    DataFusionAgent,
    get_synthesis_swarm
)

__all__ = [
    'ComputeSwarm',
    'PhysicsAgent',
    'MathAgent',
    'QuantumSimAgent',
    'get_compute_swarm',
    'SynthesisAgentSwarm',
    'SchrodingerAgent',
    'LorentzAgent',
    'DataFusionAgent',
    'get_synthesis_swarm'
]

__version__ = "1.0.0"
