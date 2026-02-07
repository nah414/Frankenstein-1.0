#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Provider Registry
Phase 3: Universal Integration Engine

Quantum and Classical provider adapters.
All providers are LAZY-LOADED — nothing runs until called.
"""

from .registry import (
    ProviderRegistry,
    ProviderInfo,
    ProviderState,
    ProviderType,
    ProviderStatus,
    ProviderCapability,
    ALL_PROVIDERS,
    QUANTUM_PROVIDERS,
    CLASSICAL_PROVIDERS,
    get_registry,
)

__all__ = [
    'ProviderRegistry',
    'ProviderInfo',
    'ProviderState',
    'ProviderType',
    'ProviderStatus',
    'ProviderCapability',
    'ALL_PROVIDERS',
    'QUANTUM_PROVIDERS',
    'CLASSICAL_PROVIDERS',
    'get_registry',
]
