"""
FRANKENSTEIN Security - Audit Logging
All security events are logged for review
"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class AuditEvent:
    timestamp: str
    event_type: str  # input, output, threat, agent, access
    severity: str    # info, warn, error, critical
    source: str      # widget, agent, mcp, system
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class AuditLog:
    """
    Thread-safe audit logging for security events.
    Logs to both file and memory (for terminal display).
    """

    def __init__(self, log_dir: Optional[Path] = None, max_memory: int = 1000):
        self.log_dir = log_dir or Path.home() / ".frankenstein" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.security_log = self.log_dir / "security.log"
        self.audit_log = self.log_dir / "audit.log"

        self._lock = threading.Lock()
        self._memory: List[AuditEvent] = []
        self._max_memory = max_memory
        self._callbacks: List[callable] = []

    def log(self, event_type: str, severity: str, source: str,
            message: str, details: Optional[Dict] = None):
        """Log an audit event"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            severity=severity,
            source=source,
            message=message,
            details=details
        )

        with self._lock:
            # Add to memory
            self._memory.append(event)
            if len(self._memory) > self._max_memory:
                self._memory = self._memory[-self._max_memory:]

            # Write to file
            self._write_to_file(event)

            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(event)
                except:
                    pass

    def _write_to_file(self, event: AuditEvent):
        """Write event to log file"""
        try:
            log_file = self.security_log if event.severity in ["error", "critical"] else self.audit_log
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            print(f"Audit write error: {e}")

    def add_callback(self, callback: callable):
        """Add callback for real-time event notification"""
        self._callbacks.append(callback)

    def get_recent(self, count: int = 50, severity: Optional[str] = None) -> List[AuditEvent]:
        """Get recent events from memory"""
        with self._lock:
            events = self._memory[-count:]
            if severity:
                events = [e for e in events if e.severity == severity]
            return events

    def log_threat(self, threat_name: str, input_text: str, action: str):
        """Convenience method for logging threats"""
        self.log(
            event_type="threat",
            severity="error",
            source="security",
            message=f"Threat detected: {threat_name}",
            details={"threat": threat_name, "input_preview": input_text[:100], "action": action}
        )

    def log_access(self, resource: str, allowed: bool, agent: str = "system"):
        """Log resource access attempt"""
        self.log(
            event_type="access",
            severity="info" if allowed else "warn",
            source=agent,
            message=f"Access {'granted' if allowed else 'denied'}: {resource}",
            details={"resource": resource, "allowed": allowed}
        )


# Global audit log instance
_audit_log: Optional[AuditLog] = None

def get_audit_log() -> AuditLog:
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log
