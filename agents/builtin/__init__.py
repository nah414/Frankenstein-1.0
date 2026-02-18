"""FRANKENSTEIN Built-in Agents"""
from .compute import ComputeAgent

# Phase 3.5: Local Toolset Agents (lazy-loaded - importing the class
# does NOT load the underlying toolset; that happens on first use)
from .quantum_dynamics_agent import QuantumDynamicsAgent
from .quantum_hardware_agent import QuantumHardwareAgent
from .quantum_crypto_agent import QuantumCryptoAgent
from .numerical_computing_agent import NumericalComputingAgent

__all__ = [
    "ComputeAgent",
    "QuantumDynamicsAgent",
    "QuantumHardwareAgent",
    "QuantumCryptoAgent",
    "NumericalComputingAgent",
]
