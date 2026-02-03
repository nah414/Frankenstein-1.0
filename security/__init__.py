"""
FRANKENSTEIN Security Layer
Phase 2: Security Dashboard + Live Threat Monitor

Exports all security components for easy import.
"""

from .shield import SecurityShield, get_shield
from .filters import InputFilter, OutputFilter
from .audit import AuditLog, AuditEvent, get_audit_log
from .patterns import check_threats, get_threat_level, ThreatPattern
from .monitor import (
    SecurityMonitor,
    SecurityEvent,
    ThreatSeverity,
    ThreatStats,
    get_monitor
)
from .dashboard import (
    SecurityDashboard,
    get_dashboard,
    handle_security_command
)

__all__ = [
    # Shield
    "SecurityShield",
    "get_shield",
    # Filters
    "InputFilter",
    "OutputFilter",
    # Audit
    "AuditLog",
    "AuditEvent",
    "get_audit_log",
    # Patterns
    "check_threats",
    "get_threat_level",
    "ThreatPattern",
    # Monitor (Phase 2)
    "SecurityMonitor",
    "SecurityEvent",
    "ThreatSeverity",
    "ThreatStats",
    "get_monitor",
    # Dashboard (Phase 2)
    "SecurityDashboard",
    "get_dashboard",
    "handle_security_command",
]

__version__ = "2.0.0-phase2"
