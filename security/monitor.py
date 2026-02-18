"""
FRANKENSTEIN 1.0 - Security Monitor
Phase 2: Security Dashboard + Live Threat Detection

Purpose: Real-time threat monitoring engine with event streaming
Integrates with: audit.py, shield.py, patterns.py, governor.py
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from .audit import AuditEvent, get_audit_log
from .patterns import check_threats, get_threat_level, ThreatPattern


class ThreatSeverity(Enum):
    """Threat severity levels with visual indicators"""
    CLEAR = ("CLEAR", "🟢", "#00ff88")      # No threats
    LOW = ("LOW", "🟡", "#ffcc00")           # Minor concerns
    MEDIUM = ("MEDIUM", "🟠", "#ff9900")     # Moderate threats
    HIGH = ("HIGH", "🔴", "#ff4444")         # Serious threats
    CRITICAL = ("CRITICAL", "⚠️", "#ff0000")  # Immediate action required

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def icon(self) -> str:
        return self.value[1]

    @property
    def color(self) -> str:
        return self.value[2]


@dataclass
class SecurityEvent:
    """A security event for the live feed"""
    timestamp: datetime
    event_type: str          # threat, access, input, output, system
    severity: ThreatSeverity
    source: str              # widget, agent, mcp, network, system
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    threat_pattern: Optional[str] = None

    def to_display_string(self) -> str:
        """Format for terminal display"""
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] {self.severity.icon} [{self.event_type.upper()}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "severity": self.severity.label,
            "source": self.source,
            "message": self.message,
            "details": self.details,
            "threat_pattern": self.threat_pattern
        }


@dataclass
class ThreatStats:
    """Aggregated threat statistics"""
    total_events: int = 0
    threats_blocked: int = 0
    threats_warned: int = 0
    injection_attempts: int = 0
    exfil_attempts: int = 0
    access_denials: int = 0
    last_threat_time: Optional[datetime] = None
    peak_severity: ThreatSeverity = ThreatSeverity.CLEAR


class SecurityMonitor:
    """
    Real-time security monitoring engine.
    
    Responsibilities:
    - Track all security events in real-time
    - Maintain live threat feed (rolling window)
    - Calculate current threat level
    - Provide statistics and analytics
    - Notify subscribers of security events
    """

    def __init__(self, max_events: int = 200, alert_window_minutes: int = 15):  # OPTIMIZED for tier1
        """
        Initialize the security monitor.

        Args:
            max_events: Maximum events to keep in memory
            alert_window_minutes: Time window for threat level calculation
        """
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Event storage (thread-safe deque)
        self._events: deque = deque(maxlen=max_events)
        self._max_events = max_events
        self._alert_window = timedelta(minutes=alert_window_minutes)

        # Statistics
        self._stats = ThreatStats()
        self._start_time: Optional[datetime] = None

        # Current state
        self._current_severity = ThreatSeverity.CLEAR
        self._active_threats: List[SecurityEvent] = []

        # Callbacks for real-time notifications
        self._callbacks: List[Callable[[SecurityEvent], None]] = []
        self._severity_callbacks: List[Callable[[ThreatSeverity], None]] = []

        # Connect to audit log
        self._audit = get_audit_log()
        self._audit.add_callback(self._on_audit_event)

    def start(self) -> bool:
        """Start the security monitor"""
        if self._running:
            return False

        self._running = True
        self._start_time = datetime.now()
        
        # Start background analysis thread
        self._thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="FrankensteinSecurityMonitor"
        )
        self._thread.start()

        # Log startup
        self._add_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="system",
            severity=ThreatSeverity.CLEAR,
            source="monitor",
            message="Security Monitor initialized - Phase 2 Active"
        ))

        return True

    def stop(self) -> bool:
        """Stop the security monitor"""
        if not self._running:
            return False

        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        return True

    def _analysis_loop(self):
        """Background loop for continuous threat analysis"""
        while self._running:
            try:
                self._update_threat_level()
                self._cleanup_old_threats()
                time.sleep(1.0)  # Check every second
            except Exception as e:
                print(f"Security monitor error: {e}")
                time.sleep(5.0)

    def _on_audit_event(self, audit_event: AuditEvent):
        """Handle incoming audit events"""
        # Convert audit severity to ThreatSeverity
        severity_map = {
            "info": ThreatSeverity.CLEAR,
            "warn": ThreatSeverity.LOW,
            "error": ThreatSeverity.MEDIUM,
            "critical": ThreatSeverity.CRITICAL
        }
        severity = severity_map.get(audit_event.severity, ThreatSeverity.LOW)

        # Elevate severity for threat events
        if audit_event.event_type == "threat":
            severity = ThreatSeverity.HIGH
            if audit_event.details and audit_event.details.get("threat"):
                if "critical" in str(audit_event.details.get("threat", "")).lower():
                    severity = ThreatSeverity.CRITICAL

        event = SecurityEvent(
            timestamp=datetime.fromisoformat(audit_event.timestamp),
            event_type=audit_event.event_type,
            severity=severity,
            source=audit_event.source,
            message=audit_event.message,
            details=audit_event.details or {},
            threat_pattern=audit_event.details.get("threat") if audit_event.details else None
        )

        self._add_event(event)

    def _add_event(self, event: SecurityEvent):
        """Add a security event to the feed"""
        with self._lock:
            self._events.append(event)
            self._update_stats(event)

            # Track active threats
            if event.severity in (ThreatSeverity.HIGH, ThreatSeverity.CRITICAL):
                self._active_threats.append(event)
                self._stats.last_threat_time = event.timestamp

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass

    def _update_stats(self, event: SecurityEvent):
        """Update statistics based on event"""
        self._stats.total_events += 1

        if event.event_type == "threat":
            if event.severity in (ThreatSeverity.HIGH, ThreatSeverity.CRITICAL):
                self._stats.threats_blocked += 1
            else:
                self._stats.threats_warned += 1

            # Check threat type
            if event.threat_pattern:
                pattern_lower = event.threat_pattern.lower()
                if "injection" in pattern_lower or "override" in pattern_lower:
                    self._stats.injection_attempts += 1
                elif "exfil" in pattern_lower or "leak" in pattern_lower:
                    self._stats.exfil_attempts += 1

        elif event.event_type == "access" and "denied" in event.message.lower():
            self._stats.access_denials += 1

        # Update peak severity
        if event.severity.value[0] > self._stats.peak_severity.value[0]:
            self._stats.peak_severity = event.severity

    def _update_threat_level(self):
        """Recalculate current threat level based on recent events"""
        cutoff = datetime.now() - self._alert_window

        with self._lock:
            recent_events = [e for e in self._events if e.timestamp > cutoff]

        if not recent_events:
            new_severity = ThreatSeverity.CLEAR
        else:
            # Count events by severity
            critical_count = sum(1 for e in recent_events if e.severity == ThreatSeverity.CRITICAL)
            high_count = sum(1 for e in recent_events if e.severity == ThreatSeverity.HIGH)
            medium_count = sum(1 for e in recent_events if e.severity == ThreatSeverity.MEDIUM)

            if critical_count > 0:
                new_severity = ThreatSeverity.CRITICAL
            elif high_count >= 3:
                new_severity = ThreatSeverity.CRITICAL
            elif high_count > 0:
                new_severity = ThreatSeverity.HIGH
            elif medium_count >= 5:
                new_severity = ThreatSeverity.HIGH
            elif medium_count > 0:
                new_severity = ThreatSeverity.MEDIUM
            else:
                # Only low/clear events
                low_count = sum(1 for e in recent_events if e.severity == ThreatSeverity.LOW)
                new_severity = ThreatSeverity.LOW if low_count > 3 else ThreatSeverity.CLEAR

        # Notify if changed
        if new_severity != self._current_severity:
            old_severity = self._current_severity
            self._current_severity = new_severity

            for callback in self._severity_callbacks:
                try:
                    callback(new_severity)
                except Exception:
                    pass

    def _cleanup_old_threats(self):
        """Remove resolved threats from active list"""
        cutoff = datetime.now() - timedelta(minutes=5)
        with self._lock:
            self._active_threats = [t for t in self._active_threats if t.timestamp > cutoff]

    # ==================== PUBLIC API ====================

    def check_input(self, text: str, source: str = "user") -> tuple:
        """
        Check input text for threats.
        
        Returns:
            Tuple of (is_safe, severity, message)
        """
        threats = check_threats(text)

        if not threats:
            return True, ThreatSeverity.CLEAR, "Input validated"

        threat_level = get_threat_level(threats)
        severity_map = {
            "none": ThreatSeverity.CLEAR,
            "low": ThreatSeverity.LOW,
            "medium": ThreatSeverity.MEDIUM,
            "high": ThreatSeverity.HIGH,
            "critical": ThreatSeverity.CRITICAL
        }
        severity = severity_map.get(threat_level, ThreatSeverity.MEDIUM)

        # Log the threat
        threat_names = ", ".join(t.name for t in threats)
        self._add_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="threat",
            severity=severity,
            source=source,
            message=f"Threat detected: {threats[0].description}",
            details={"patterns": threat_names, "input_preview": text[:100]},
            threat_pattern=threat_names
        ))

        is_safe = severity not in (ThreatSeverity.HIGH, ThreatSeverity.CRITICAL)
        return is_safe, severity, threats[0].description if threats else ""

    def log_access(self, resource: str, allowed: bool, source: str = "system"):
        """Log a resource access attempt"""
        severity = ThreatSeverity.CLEAR if allowed else ThreatSeverity.LOW
        self._add_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="access",
            severity=severity,
            source=source,
            message=f"Access {'granted' if allowed else 'DENIED'}: {resource}",
            details={"resource": resource, "allowed": allowed}
        ))

    def log_system_event(self, message: str, severity: ThreatSeverity = ThreatSeverity.CLEAR):
        """Log a system security event"""
        self._add_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="system",
            severity=severity,
            source="system",
            message=message
        ))

    def add_event_callback(self, callback: Callable[[SecurityEvent], None]):
        """Subscribe to security events"""
        self._callbacks.append(callback)

    def add_severity_callback(self, callback: Callable[[ThreatSeverity], None]):
        """Subscribe to severity level changes"""
        self._severity_callbacks.append(callback)

    def get_current_severity(self) -> ThreatSeverity:
        """Get current threat severity level"""
        return self._current_severity

    def get_recent_events(self, count: int = 20, 
                          severity_filter: Optional[ThreatSeverity] = None) -> List[SecurityEvent]:
        """Get recent security events"""
        with self._lock:
            events = list(self._events)

        if severity_filter:
            events = [e for e in events if e.severity == severity_filter]

        return events[-count:]

    def get_active_threats(self) -> List[SecurityEvent]:
        """Get currently active threats"""
        with self._lock:
            return list(self._active_threats)

    def get_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0

        return {
            "current_severity": self._current_severity.label,
            "severity_icon": self._current_severity.icon,
            "severity_color": self._current_severity.color,
            "total_events": self._stats.total_events,
            "threats_blocked": self._stats.threats_blocked,
            "threats_warned": self._stats.threats_warned,
            "injection_attempts": self._stats.injection_attempts,
            "exfil_attempts": self._stats.exfil_attempts,
            "access_denials": self._stats.access_denials,
            "active_threats": len(self._active_threats),
            "last_threat": self._stats.last_threat_time.isoformat() if self._stats.last_threat_time else None,
            "peak_severity": self._stats.peak_severity.label,
            "uptime_seconds": round(uptime, 1),
            "running": self._running
        }

    def get_status_line(self) -> str:
        """Get a single-line status for terminal display"""
        stats = self.get_stats()
        return (
            f"{stats['severity_icon']} Security: {stats['current_severity']} | "
            f"Blocked: {stats['threats_blocked']} | "
            f"Active: {stats['active_threats']}"
        )


# ==================== GLOBAL INSTANCE ====================

_monitor: Optional[SecurityMonitor] = None

def get_monitor() -> SecurityMonitor:
    """Get or create the global security monitor"""
    global _monitor
    if _monitor is None:
        _monitor = SecurityMonitor()
    return _monitor
