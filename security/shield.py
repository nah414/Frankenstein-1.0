"""
FRANKENSTEIN Security - The Shield
Main security controller that coordinates all security functions
"""

from typing import Tuple, Optional, Dict, Any, Callable
from datetime import datetime
from .filters import InputFilter, OutputFilter
from .audit import AuditLog, get_audit_log
from .patterns import check_threats, get_threat_level


class SecurityShield:
    """
    The Shield - Central security controller for FRANKENSTEIN.

    Responsibilities:
    - Input validation and filtering
    - Output sanitization
    - Threat detection
    - Audit logging
    - Real-time alerts to terminal
    """

    def __init__(self):
        self.input_filter = InputFilter()
        self.output_filter = OutputFilter()
        self.audit = get_audit_log()

        self._active = True
        self._threats_blocked = 0
        self._last_scan = None
        self._alert_callback: Optional[Callable] = None

        # Log startup
        self.audit.log("system", "info", "shield", "Security Shield initialized")

    def check_input(self, text: str, source: str = "user") -> Tuple[bool, str]:
        """
        Check input for security threats.

        Returns:
            Tuple of (is_safe, message)
        """
        self._last_scan = datetime.now()

        if not self._active:
            return True, "Security disabled"

        is_safe, filtered, reason = self.input_filter.filter(text, source)

        if not is_safe:
            self._threats_blocked += 1
            self._send_alert(f"Input blocked: {reason}", "warn")
            return False, reason

        return True, "Input validated"

    def filter_output(self, text: str, source: str = "system") -> str:
        """Filter output for sensitive data"""
        if not self._active:
            return text
        return self.output_filter.filter(text, source)

    def set_alert_callback(self, callback: Callable):
        """Set callback for real-time security alerts"""
        self._alert_callback = callback
        self.audit.add_callback(lambda e: self._on_audit_event(e))

    def _on_audit_event(self, event):
        """Handle audit events for alerting"""
        if event.severity in ["error", "critical"]:
            self._send_alert(event.message, event.severity)

    def _send_alert(self, message: str, level: str):
        """Send alert to terminal"""
        if self._alert_callback:
            try:
                self._alert_callback(message, level)
            except:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Get security status"""
        return {
            "active": "ACTIVE" if self._active else "DISABLED",
            "threats_blocked": self._threats_blocked,
            "last_scan": self._last_scan.strftime("%H:%M:%S") if self._last_scan else "Never",
        }

    def enable(self):
        """Enable the security shield"""
        self._active = True
        self.audit.log("system", "info", "shield", "Security Shield enabled")

    def disable(self):
        """Disable the security shield (NOT RECOMMENDED)"""
        self._active = False
        self.audit.log("system", "warn", "shield", "Security Shield DISABLED")


# Global shield instance
_shield: Optional[SecurityShield] = None

def get_shield() -> SecurityShield:
    global _shield
    if _shield is None:
        _shield = SecurityShield()
    return _shield
