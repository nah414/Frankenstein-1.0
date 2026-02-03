#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Integration Module
Phase 3: Universal Integration Engine

This module provides:
- Hardware discovery and fingerprinting
- Provider registry (quantum + classical)
- Workload analysis and routing
- Configuration optimization
- Permission management
- Real-time adaptation
"""

from .discovery import HardwareDiscovery, get_hardware_fingerprint

__all__ = [
    'HardwareDiscovery',
    'get_hardware_fingerprint',
]

__version__ = '0.1.0'
__phase__ = 3
