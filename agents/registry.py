"""
FRANKENSTEIN Agents - Agent Registry
Manages registration and lookup of agents
"""

from typing import Dict, Type, Optional, List
from .base import BaseAgent


class AgentRegistry:
    """
    Registry for all available agents.
    Agents must register here to be usable.
    """

    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._instances: Dict[str, BaseAgent] = {}

    def register(self, agent_class: Type[BaseAgent]) -> bool:
        """Register an agent class"""
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
        """Get an agent instance by name"""
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
