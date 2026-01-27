"""
FRANKENSTEIN 1.0 - Widget Package
Phase 1: Core Engine

Exports widget components:
- FrankensteinTerminal: Git Bash-style terminal interface
- FrankensteinWidget: Simple overlay widget (legacy)
"""

from .terminal import FrankensteinTerminal, get_terminal, launch_terminal, CTK_AVAILABLE
from .overlay import FrankensteinWidget, WidgetMode, get_widget

# Alias for backward compatibility
TerminalWidget = FrankensteinTerminal

__all__ = [
    "FrankensteinTerminal",
    "TerminalWidget",
    "get_terminal",
    "launch_terminal",
    "CTK_AVAILABLE",
    "FrankensteinWidget",
    "WidgetMode",
    "get_widget",
]
