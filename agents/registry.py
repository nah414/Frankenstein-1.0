"""
FRANKENSTEIN Agents - Agent Registry
Manages registration and lookup of agents

Phase 3.5: Auto-registers built-in agents including local toolset agents.
All registrations store class references only - no instantiation at import time.
"""

from typing import Dict, Type, Optional, List
import logging

from .base import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for all available agents.
    Agents must register here to be usable.

    Phase 3.5: Built-in agents (including toolset agents) are auto-registered
    on first registry creation via _register_builtins(). Agent classes are
    stored as references - instantiation happens lazily on get().
    """

    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._instances: Dict[str, BaseAgent] = {}
        self._register_builtins()

    def _register_builtins(self):
        """
        Auto-register all built-in agents.

        Imports are inside this method (not at module level) so that
        toolset dependencies are NOT loaded at import time - they remain
        lazy until an agent's methods are actually called.
        """
        # Existing agents
        try:
            from .builtin.compute import ComputeAgent
            self.register(ComputeAgent)
        except Exception as e:
            logger.debug(f"Could not register ComputeAgent: {e}")

        # Phase 3.5: Local Toolset Agents (lazy-loaded)
        try:
            from .builtin.quantum_dynamics_agent import QuantumDynamicsAgent
            self.register(QuantumDynamicsAgent)
        except Exception as e:
            logger.debug(f"Could not register QuantumDynamicsAgent: {e}")

        try:
            from .builtin.quantum_hardware_agent import QuantumHardwareAgent
            self.register(QuantumHardwareAgent)
        except Exception as e:
            logger.debug(f"Could not register QuantumHardwareAgent: {e}")

        try:
            from .builtin.quantum_crypto_agent import QuantumCryptoAgent
            self.register(QuantumCryptoAgent)
        except Exception as e:
            logger.debug(f"Could not register QuantumCryptoAgent: {e}")

        try:
            from .builtin.numerical_computing_agent import NumericalComputingAgent
            self.register(NumericalComputingAgent)
        except Exception as e:
            logger.debug(f"Could not register NumericalComputingAgent: {e}")

    def register(self, agent_class: Type[BaseAgent]) -> bool:
        """Register an agent class (class reference only, no instantiation)"""
        name = agent_class.name
        if name in self._agents:
            return False
        self._agents[name] = agent_class
        return True

    def unregister(self, name: str) -> bool:
        """Unregister an agent"""
        if name in self._agents:
            del self._agents[name]
            if name in self._instances:
                del self._instances[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name (lazy instantiation)"""
        if name not in self._agents:
            return None

        if name not in self._instances:
            self._instances[name] = self._agents[name]()

        return self._instances[name]

    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        return [
            {"name": name, "description": cls.description}
            for name, cls in self._agents.items()
        ]

    def has_agent(self, name: str) -> bool:
        """Check if agent is registered"""
        return name in self._agents


# Global registry
_registry: Optional[AgentRegistry] = None

def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
