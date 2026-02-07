"""
FRANKENSTEIN Security - Threat Detection Patterns
Detects prompt injection and other malicious inputs
"""

import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ThreatPattern:
    name: str
    pattern: str
    severity: str  # low, medium, high, critical
    description: str


# Prompt injection patterns
INJECTION_PATTERNS: List[ThreatPattern] = [
    ThreatPattern(
        name="instruction_override",
        pattern=r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
        severity="critical",
        description="Attempt to override system instructions"
    ),
    ThreatPattern(
        name="role_hijack",
        pattern=r"you\s+are\s+now\s+(a|an|the)",
        severity="high",
        description="Attempt to change AI role"
    ),
    ThreatPattern(
        name="system_prompt_leak",
        pattern=r"(show|reveal|display|print|output)\s+(your\s+)?(system\s+)?prompt",
        severity="high",
        description="Attempt to extract system prompt"
    ),
    ThreatPattern(
        name="jailbreak_keyword",
        pattern=r"\b(jailbreak|dan\s+mode|developer\s+mode|no\s+restrictions)\b",
        severity="critical",
        description="Known jailbreak terminology"
    ),
    ThreatPattern(
        name="token_manipulation",
        pattern=r"<\|[^|]+\|>",
        severity="high",
        description="Token boundary manipulation"
    ),
    ThreatPattern(
        name="code_injection",
        pattern=r"```\s*(system|exec|eval|import\s+os)",
        severity="high",
        description="Code injection attempt"
    ),
    ThreatPattern(
        name="privilege_escalation",
        pattern=r"\b(admin|root|sudo|administrator)\s+(mode|access|privilege)",
        severity="critical",
        description="Privilege escalation attempt"
    ),
    ThreatPattern(
        name="instruction_injection",
        pattern=r"(new\s+instructions?|updated?\s+rules?|override\s+settings?):",
        severity="high",
        description="Instruction injection attempt"
    ),
]

# Data exfiltration patterns
EXFIL_PATTERNS: List[ThreatPattern] = [
    ThreatPattern(
        name="api_key_leak",
        pattern=r"(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]",
        severity="critical",
        description="API key exposure attempt"
    ),
    ThreatPattern(
        name="credential_request",
        pattern=r"(password|passwd|credentials?|auth\s*token)",
        severity="medium",
        description="Credential access attempt"
    ),
    ThreatPattern(
        name="file_path_probe",
        pattern=r"(\/etc\/passwd|\.env|config\.yaml|secrets?\.)",
        severity="high",
        description="Sensitive file path probe"
    ),
]


def compile_patterns() -> List[Tuple[ThreatPattern, re.Pattern]]:
    """Compile all patterns for efficient matching"""
    compiled = []
    for pattern in INJECTION_PATTERNS + EXFIL_PATTERNS:
        try:
            regex = re.compile(pattern.pattern, re.IGNORECASE)
            compiled.append((pattern, regex))
        except re.error as e:
            print(f"Pattern compile error for {pattern.name}: {e}")
    return compiled


COMPILED_PATTERNS = compile_patterns()


def check_threats(text: str) -> List[ThreatPattern]:
    """Check text for threat patterns, return list of matches"""
    threats = []
    text_lower = text.lower()

    for pattern, regex in COMPILED_PATTERNS:
        if regex.search(text_lower):
            threats.append(pattern)

    return threats


def get_threat_level(threats: List[ThreatPattern]) -> str:
    """Get highest threat level from list"""
    if not threats:
        return "none"

    levels = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    max_level = max(levels.get(t.severity, 0) for t in threats)

    for name, level in levels.items():
        if level == max_level:
            return name
    return "low"
