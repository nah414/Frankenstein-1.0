"""
FRANKENSTEIN Security - Input/Output Filters
Sanitize all data entering and leaving the system
"""

import re
import html
from typing import Tuple, Optional, List
from .patterns import check_threats, get_threat_level, ThreatPattern
from .audit import get_audit_log


class InputFilter:
    """
    Filters and validates all input before processing.
    Detects injection attempts and sanitizes data.
    """

    # Maximum input length
    MAX_INPUT_LENGTH = 10000

    # Characters to strip/escape
    DANGEROUS_CHARS = ['<script>', '</script>', 'javascript:', 'data:']

    def __init__(self):
        self.audit = get_audit_log()
        self._blocked_count = 0

    def filter(self, text: str, source: str = "user") -> Tuple[bool, str, Optional[str]]:
        """
        Filter input text.

        Returns:
            Tuple of (is_safe, filtered_text, rejection_reason)
        """
        if not text:
            return True, "", None

        # Length check
        if len(text) > self.MAX_INPUT_LENGTH:
            self.audit.log("input", "warn", source, f"Input too long: {len(text)} chars")
            return False, "", f"Input too long (max {self.MAX_INPUT_LENGTH})"

        # Check for threats
        threats = check_threats(text)
        if threats:
            threat_level = get_threat_level(threats)
            threat_names = [t.name for t in threats]

            self.audit.log_threat(
                threat_name=", ".join(threat_names),
                input_text=text,
                action="blocked" if threat_level in ["high", "critical"] else "warned"
            )

            if threat_level in ["high", "critical"]:
                self._blocked_count += 1
                return False, "", f"Security threat detected: {threats[0].description}"

        # Sanitize
        filtered = self._sanitize(text)

        # Log successful filter
        self.audit.log("input", "info", source, "Input accepted",
                      {"length": len(filtered), "threats_detected": len(threats)})

        return True, filtered, None

    def _sanitize(self, text: str) -> str:
        """Sanitize text by removing dangerous content"""
        result = text

        # Remove dangerous strings
        for danger in self.DANGEROUS_CHARS:
            result = result.replace(danger, "")

        # Escape HTML entities
        result = html.escape(result, quote=False)

        # Remove null bytes
        result = result.replace("\x00", "")

        return result

    @property
    def blocked_count(self) -> int:
        return self._blocked_count


class OutputFilter:
    """
    Filters output before displaying to user.
    Prevents sensitive data leakage.
    """

    # Patterns that should never appear in output
    SENSITIVE_PATTERNS = [
        (r'[A-Za-z0-9+/]{40,}={0,2}', "Possible API key/token"),
        (r'\b\d{3}-\d{2}-\d{4}\b', "SSN pattern"),
        (r'\b\d{16}\b', "Credit card pattern"),
        (r'password\s*[:=]\s*\S+', "Password in output"),
    ]

    def __init__(self):
        self.audit = get_audit_log()
        self._compiled = [(re.compile(p, re.I), d) for p, d in self.SENSITIVE_PATTERNS]

    def filter(self, text: str, source: str = "system") -> str:
        """Filter output, redacting sensitive data"""
        result = text

        for pattern, description in self._compiled:
            matches = pattern.findall(result)
            if matches:
                self.audit.log("output", "warn", source,
                             f"Sensitive data redacted: {description}",
                             {"matches": len(matches)})
                result = pattern.sub("[REDACTED]", result)

        return result
