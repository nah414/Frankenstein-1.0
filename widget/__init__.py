"""
FRANKENSTEIN 1.0 - Widget Package
Phase 1: Core Engine

Exports terminal widget components.
"""

from .terminal import FrankensteinTerminal, get_terminal, launch_terminal

__all__ = [
    "FrankensteinTerminal",
    "get_terminal", 
    "launch_terminal",
]
