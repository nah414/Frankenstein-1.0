"""
FRANKENSTEIN 1.0 - Eye of Sauron: Tool Registry
Phase 4 / Day 2
Updated Day 4: git_tools, code_tools, package_tools, shell env_read/env_write
Updated Day 6: agent_tools (AgentDispatchTool, MultiAgentDispatchTool)

Central registry for all Sauron tools. Provides:
  - Tool registration and lookup by name
  - Quantum library availability manifest (Qiskit, QuTiP, SciPy, NumPy)
  - System prompt fragment listing all available tools + libraries

Auto-registers all tools on first access:
  Day 2: web_tool, memory_tool
  Day 3: quantum_tool, file_tools, dir_tools, search_tools, shell_tools
  Day 4: git_tools, code_tools, package_tools (shell_tools extended in-place)
"""

import logging
from typing import Dict, List, Optional

from agents.sauron.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


# ── Quantum Library Manifest ───────────────────────────────────────────────────
# These libraries are confirmed installed and available for quantum_tool.py (Day 3).
# Stored here so Sauron's system prompt can reference them from Day 2 onward.

AVAILABLE_LIBRARIES = {
    "qiskit": {
        "version": "2.2.3",
        "use": (
            "Quantum circuit construction, OpenQASM 2.0 compilation, "
            "Qiskit-Aer local simulation, IBM Quantum backend submission"
        ),
    },
    "qutip": {
        "version": "5.2.3",
        "use": (
            "Open quantum systems, Lindblad master equations, "
            "density matrices, time evolution, QuTiP Bloch sphere"
        ),
    },
    "scipy": {
        "version": "1.16.3",
        "use": (
            "Sparse matrix ops, linear algebra (linalg), FFT, "
            "optimization (minimize), special functions (scipy.special)"
        ),
    },
    "numpy": {
        "version": "2.3.5",
        "use": (
            "Statevector math, tensor products (kron), complex128 arrays, "
            "random sampling, matrix exponentiation (expm via scipy)"
        ),
    },
}


# ── Tool Registry ──────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Registry for all Eye of Sauron tools.

    Tools register themselves by class; instances are created lazily on first get().
    """

    def __init__(self):
        self._tool_classes: Dict[str, type] = {}
        self._instances: Dict[str, BaseTool] = {}

    def register(self, tool_class: type) -> None:
        """Register a tool class. Instance created on first get()."""
        name = tool_class.name
        self._tool_classes[name] = tool_class
        logger.debug("Tool registered: %s", name)

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a lazily instantiated tool by name."""
        if name not in self._tool_classes:
            return None
        if name not in self._instances:
            self._instances[name] = self._tool_classes[name]()
        return self._instances[name]

    def execute(self, name: str, **kwargs) -> ToolResult:
        """Look up and run a tool by name."""
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: '{name}'. Available: {self.list_names()}",
            )
        return tool.run(**kwargs)

    def list_tools(self) -> List[dict]:
        """Return metadata for all registered tools (for LLM system prompt)."""
        results = []
        for name, cls in self._tool_classes.items():
            results.append({
                "name": name,
                "description": getattr(cls, "description", ""),
                "ring": getattr(cls, "permission_level", None),
                "requires_network": getattr(cls, "requires_network", False),
            })
        return results

    def list_names(self) -> List[str]:
        return list(self._tool_classes.keys())

    def system_prompt_fragment(self) -> str:
        """
        Generate the tools + libraries section of Sauron's system prompt.
        Called by engine.py when building the system context.
        """
        lines = ["## Available Tools\n"]
        for t in self.list_tools():
            ring = t["ring"].name if t["ring"] else "UNKNOWN"
            net = " [network]" if t["requires_network"] else ""
            lines.append(f"- `{t['name']}` (Ring {ring}){net}: {t['description']}")

        lines.append("\n## Available Quantum Libraries\n")
        for lib, info in AVAILABLE_LIBRARIES.items():
            lines.append(f"- **{lib}** v{info['version']}: {info['use']}")

        return "\n".join(lines)


# ── Global Registry + Auto-Registration ───────────────────────────────────────

_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create the global ToolRegistry, auto-registering built-in tools."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _auto_register(_registry)
    return _registry


def _auto_register(registry: ToolRegistry) -> None:
    """Register all built-in tools (Day 2 + Day 3)."""
    # ── Day 2 ──────────────────────────────────────────────────────────────────
    try:
        from agents.sauron.tools.web_tool import WebFetchTool
        registry.register(WebFetchTool)
    except Exception as e:
        logger.warning("Could not register WebFetchTool: %s", e)

    try:
        from agents.sauron.tools.memory_tool import MemoryTool
        registry.register(MemoryTool)
    except Exception as e:
        logger.warning("Could not register MemoryTool: %s", e)

    # ── Day 3 ──────────────────────────────────────────────────────────────────
    try:
        from agents.sauron.tools.quantum_tool import QuantumTool
        registry.register(QuantumTool)
    except Exception as e:
        logger.warning("Could not register QuantumTool: %s", e)

    try:
        from agents.sauron.tools.file_tools import FileTool
        registry.register(FileTool)
    except Exception as e:
        logger.warning("Could not register FileTool: %s", e)

    try:
        from agents.sauron.tools.dir_tools import DirTool
        registry.register(DirTool)
    except Exception as e:
        logger.warning("Could not register DirTool: %s", e)

    try:
        from agents.sauron.tools.search_tools import SearchTool
        registry.register(SearchTool)
    except Exception as e:
        logger.warning("Could not register SearchTool: %s", e)

    try:
        from agents.sauron.tools.shell_tools import ShellTool
        registry.register(ShellTool)
    except Exception as e:
        logger.warning("Could not register ShellTool: %s", e)

    # ── Day 4 ──────────────────────────────────────────────────────────────────
    try:
        from agents.sauron.tools.git_tools import GitTool
        registry.register(GitTool)
    except Exception as e:
        logger.warning("Could not register GitTool: %s", e)

    try:
        from agents.sauron.tools.code_tools import CodeTool
        registry.register(CodeTool)
    except Exception as e:
        logger.warning("Could not register CodeTool: %s", e)

    try:
        from agents.sauron.tools.package_tools import PackageTool
        registry.register(PackageTool)
    except Exception as e:
        logger.warning("Could not register PackageTool: %s", e)

    # ── Day 6 ──────────────────────────────────────────────────────────────────
    try:
        from agents.sauron.tools.agent_tools import AgentDispatchTool
        registry.register(AgentDispatchTool)
    except Exception as e:
        logger.warning("Could not register AgentDispatchTool: %s", e)

    try:
        from agents.sauron.tools.agent_tools import MultiAgentDispatchTool
        registry.register(MultiAgentDispatchTool)
    except Exception as e:
        logger.warning("Could not register MultiAgentDispatchTool: %s", e)
