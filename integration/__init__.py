#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Integration Module
Phase 3: Universal Integration Engine

This module provides:
- Hardware discovery and fingerprinting (Step 1)
- Provider registry — quantum + classical (Step 2)
- Workload analysis and routing (Step 3 - planned)
- Configuration optimization (Step 4 - planned)
- Permission management (Step 6 - planned)
- Real-time adaptation (Step 7 - planned)

ALL components are LAZY-LOADED — nothing runs at import time.
"""

from .discovery import HardwareDiscovery, get_hardware_fingerprint
from .providers.registry import ProviderRegistry, get_registry
from .credentials import CredentialManager, get_credential_manager

__all__ = [
    'HardwareDiscovery',
    'get_hardware_fingerprint',
    'ProviderRegistry',
    'get_registry',
    'CredentialManager',
    'get_credential_manager',
]

__version__ = '0.2.0'
__phase__ = 3
