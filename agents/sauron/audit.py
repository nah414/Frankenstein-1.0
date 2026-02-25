"""
FRANKENSTEIN 1.0 - Eye of Sauron: Audit Logger
Phase 4 / Day 2: Security Layer

Wraps the existing security pipeline (security.shield, security.monitor)
with Sauron-specific event types. All events write to:
  - ~/.frankenstein/logs/sauron_audit.log  (Sauron-specific log)
  - ~/.frankenstein/logs/security.log      (existing security pipeline)
  - security.monitor (real-time threat tracking, active threats list)

Event severity mapping:
  RING1_BLOCK, WEB_BLOCKED, INJECTION_ALERT  → CRITICAL / HIGH
  PERMISSION_DENY                             → MEDIUM
  WEB_FETCH, TOOL_CALL, PERMISSION_ASK        → LOW
  QUERY, MEMORY_READ, PERMISSION_GRANT        → INFO
"""

import json
import logging
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

LOG_DIR = Path.home() / ".frankenstein" / "logs"
SAURON_LOG_FILE = LOG_DIR / "sauron_audit.log"


# ── Event Types ────────────────────────────────────────────────────────────────

class SauronEvent(Enum):
    QUERY            = "sauron_query"            # NL input received from user
    TOOL_CALL        = "sauron_tool_call"         # Sauron invoked a tool
    PERMISSION_ASK   = "sauron_permission_ask"    # Ring 2 prompt shown
    PERMISSION_GRANT = "sauron_permission_grant"  # User approved Ring 2 action
    PERMISSION_DENY  = "sauron_permission_deny"   # User denied Ring 2 action
    WEB_FETCH        = "sauron_web_fetch"         # Successful web fetch
    WEB_BLOCKED      = "sauron_web_blocked"       # Non-whitelist URL blocked
    MEMORY_READ      = "sauron_memory_read"       # State or circuit recall
    INJECTION_ALERT  = "sauron_injection_alert"   # Prompt injection detected
    RING1_BLOCK      = "sauron_ring1_block"       # Forbidden action blocked
    ENGINE_START     = "sauron_engine_start"      # LLM loaded
    ENGINE_STOP      = "sauron_engine_stop"       # LLM unloaded / timeout


# Severity strings for feeding into security.monitor
_SEVERITY_MAP: Dict[SauronEvent, str] = {
    SauronEvent.RING1_BLOCK:      "CRITICAL",
    SauronEvent.INJECTION_ALERT:  "HIGH",
    SauronEvent.WEB_BLOCKED:      "HIGH",
    SauronEvent.PERMISSION_DENY:  "MEDIUM",
    SauronEvent.WEB_FETCH:        "LOW",
    SauronEvent.TOOL_CALL:        "LOW",
    SauronEvent.PERMISSION_ASK:   "LOW",
    SauronEvent.QUERY:            "INFO",
    SauronEvent.MEMORY_READ:      "INFO",
    SauronEvent.PERMISSION_GRANT: "INFO",
    SauronEvent.ENGINE_START:     "INFO",
    SauronEvent.ENGINE_STOP:      "INFO",
}


# ── Audit Logger ───────────────────────────────────────────────────────────────

class SauronAudit:
    """
    Sauron-specific audit logger.

    Thread-safe. Writes structured JSON lines to sauron_audit.log and
    forwards security-relevant events to the existing security pipeline.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._buffer: list = []
        self._max_buffer = 200
        self._initialized = False
        self._shield = None
        self._monitor = None
        self._init()

    def _init(self) -> None:
        """Initialize log file and connect to existing security singletons."""
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            # Ensure log file exists
            SAURON_LOG_FILE.touch(exist_ok=True)
        except Exception as e:
            logger.warning("Could not create sauron audit log: %s", e)

        # Connect to existing security pipeline (lazy, non-fatal if unavailable)
        try:
            from security.shield import get_shield
            self._shield = get_shield()
        except Exception:
            pass

        try:
            from security.monitor import get_monitor
            self._monitor = get_monitor()
        except Exception:
            pass

        self._initialized = True

    def log(
        self,
        event: SauronEvent,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        source: str = "eye_of_sauron",
    ) -> None:
        """
        Log a Sauron event.

        Args:
            event:   SauronEvent enum value
            message: Human-readable description
            details: Optional structured data (dict)
            source:  Component that generated the event
        """
        severity = _SEVERITY_MAP.get(event, "INFO")
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event.value,
            "severity": severity,
            "source": source,
            "message": message,
            "details": details or {},
        }

        # Write to file
        self._write_to_file(record)

        # Keep in-memory buffer
        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) > self._max_buffer:
                self._buffer.pop(0)

        # Forward HIGH/CRITICAL to existing security monitor
        if severity in ("CRITICAL", "HIGH", "MEDIUM"):
            self._forward_to_monitor(event, severity, message, details)

        # Standard Python logging
        log_fn = {
            "CRITICAL": logger.critical,
            "HIGH":     logger.error,
            "MEDIUM":   logger.warning,
            "LOW":      logger.info,
            "INFO":     logger.debug,
        }.get(severity, logger.debug)
        log_fn("[%s] %s", event.value, message)

    def _write_to_file(self, record: dict) -> None:
        """Append JSON line to sauron_audit.log."""
        try:
            with self._lock:
                with open(SAURON_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning("Audit file write failed: %s", e)

    def _forward_to_monitor(
        self,
        event: SauronEvent,
        severity: str,
        message: str,
        details: Optional[Dict],
    ) -> None:
        """Forward high-severity events to existing security.monitor."""
        if self._monitor is None:
            return
        try:
            self._monitor.log_system_event(
                event_type=event.value,
                message=message,
                severity=severity,
                details=details or {},
            )
        except Exception:
            pass  # Non-fatal — monitor may not be running

    # ── Convenience helpers ────────────────────────────────────────────────────

    def log_ring1_block(self, action: str) -> None:
        self.log(
            SauronEvent.RING1_BLOCK,
            f"Ring 1 FORBIDDEN action blocked: {action[:80]}",
            {"action": action[:200]},
        )

    def log_web_blocked(self, url: str, reason: str) -> None:
        self.log(
            SauronEvent.WEB_BLOCKED,
            f"Web request blocked: {url[:80]} — {reason}",
            {"url": url[:200], "reason": reason},
        )

    def log_web_fetch(self, url: str, chars_returned: int) -> None:
        self.log(
            SauronEvent.WEB_FETCH,
            f"Web fetch: {url[:80]} ({chars_returned} chars)",
            {"url": url[:200], "chars": chars_returned},
        )

    def log_injection_alert(self, url: str, pattern: str) -> None:
        self.log(
            SauronEvent.INJECTION_ALERT,
            f"Prompt injection pattern detected in web content from {url[:60]}",
            {"url": url[:200], "pattern": pattern[:100]},
        )

    def log_permission(self, event: SauronEvent, action: str, description: str) -> None:
        self.log(
            event,
            f"Permission {event.name.lower()}: {action}",
            {"action": action[:100], "description": description[:200]},
        )

    def log_memory_read(self, resource_type: str, name: str) -> None:
        self.log(
            SauronEvent.MEMORY_READ,
            f"Memory read: {resource_type} '{name}'",
            {"type": resource_type, "name": name},
        )

    def log_tool_call(self, tool_name: str, kwargs_summary: str) -> None:
        self.log(
            SauronEvent.TOOL_CALL,
            f"Tool call: {tool_name} — {kwargs_summary[:80]}",
            {"tool": tool_name, "args": kwargs_summary[:200]},
        )

    def get_recent(self, n: int = 50) -> list:
        """Return the n most recent audit records from the in-memory buffer."""
        with self._lock:
            return list(self._buffer[-n:])


# ── Singleton ──────────────────────────────────────────────────────────────────

_sauron_audit: Optional[SauronAudit] = None


def get_sauron_audit() -> SauronAudit:
    """Get or create the global SauronAudit singleton."""
    global _sauron_audit
    if _sauron_audit is None:
        _sauron_audit = SauronAudit()
    return _sauron_audit
