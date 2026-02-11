"""
Permissions & Automation System for Frankenstein 1.0

This module provides role-based access control, audit logging, and automated
workflows for all 28 quantum and classical computing providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6
"""

# Lazy loading - components only imported when explicitly requested
__all__ = [
    "rbac",
    "permission_manager",
    "audit_logger",
    "setup_wizard",
]

__version__ = "1.0.0"
