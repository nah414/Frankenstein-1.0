"""
FRANKENSTEIN 1.0 - Local Libraries Integration
Phase 3.5: Lazy-loading wrappers for scientific toolsets
"""

from .local_toolsets import (
    get_toolset_manager,
    load_numpy,
    load_scipy,
    load_qutip,
    load_qiskit,
    load_qencrypt,
)

__all__ = [
    "get_toolset_manager",
    "load_numpy",
    "load_scipy",
    "load_qutip",
    "load_qiskit",
    "load_qencrypt",
]
