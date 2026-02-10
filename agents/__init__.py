"""FRANKENSTEIN Agent Framework"""
from .base import BaseAgent, AgentResult
from .registry import AgentRegistry, get_registry
from .sandbox import Sandbox
from .builtin.compute import ComputeAgent

# Phase 3.5: Local Toolset Agents
from .builtin.quantum_dynamics_agent import QuantumDynamicsAgent
from .builtin.quantum_hardware_agent import QuantumHardwareAgent
from .builtin.quantum_crypto_agent import QuantumCryptoAgent
from .builtin.numerical_computing_agent import NumericalComputingAgent

__all__ = [
    "BaseAgent", "AgentResult", "AgentRegistry", "get_registry", "Sandbox",
    "ComputeAgent",
    "QuantumDynamicsAgent", "QuantumHardwareAgent",
    "QuantumCryptoAgent", "NumericalComputingAgent",
]
