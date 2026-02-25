"""
FRANKENSTEIN 1.0 - Eye of Sauron: Permission System
Phase 4 / Day 2: Security Layer

Three-Ring permission model:
  Ring 1 (FORBIDDEN)  — hard block, no override, always logged
  Ring 2 (SENSITIVE)  — requires explicit Y/n approval at terminal
  Ring 3 (SAFE)       — execute freely, no prompt

Web access:
  - Whitelisted domains (Wolfram, Wikipedia) = Ring 2 (needs approval)
  - Any other URL = Ring 1 (FORBIDDEN, hard block)

Quantum operations:
  - Gate applications, resets, state reads = Ring 3 (safe)
  - measure, bloch launch, save_state, cloud submit = Ring 2 (sensitive)
"""

import re
import logging
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ── Enums ──────────────────────────────────────────────────────────────────────

class PermissionLevel(Enum):
    FORBIDDEN = 1   # Ring 1 — always blocked
    SENSITIVE = 2   # Ring 2 — needs explicit approval
    SAFE      = 3   # Ring 3 — free execution


# ── Web Whitelist ──────────────────────────────────────────────────────────────

WEB_ALLOWED_DOMAINS = frozenset({
    "wolfram.com",
    "www.wolfram.com",
    "wolframalpha.com",
    "www.wolframalpha.com",
    "wikipedia.org",
    "en.wikipedia.org",
    "www.wikipedia.org",
})

# ── Ring 1: Forbidden Patterns ─────────────────────────────────────────────────

RING_1_FORBIDDEN_PATTERNS = [
    # Destructive filesystem ops
    r"rm\s+-rf\s+/",
    r"rm\s+--no-preserve-root",
    r"format\s+[A-Za-z]:",
    r"del\s+/[sqSQ]",
    r"rd\s+/[sS]",
    r"rmdir\s+/[sS]",
    # Windows system paths (write/delete)
    r"[Cc]:\\[Ww]indows\\",
    r"[Cc]:\\[Pp]rogram [Ff]iles",
    r"[Cc]:\\[Pp]rogram[Ff]iles",
    r"%[Ss]ystem[Rr]oot%",
    r"\\[Ss]ystem32\\",
    # Registry modification
    r"\breg\b.*(add|delete|import|export)",
    r"regedit",
    r"HKEY_",
    # Boot / system configuration
    r"bcdedit",
    r"diskpart",
    r"fdisk",
    r"bios",
    # Credential / secret file access
    r"credentials\.json",
    r"\.frankenstein[/\\]credentials",
    r"permission\.key",
    r"audit\.key",
    r"setup\.key",
    # Disable security
    r"net\s+stop\s+(windows|firewall|defender|wdfilter)",
    r"Set-MpPreference\s+-Disable",
    r"netsh\s+advfirewall\s+set.*off",
    # Shadow copies / backup deletion
    r"vssadmin\s+delete",
    r"wmic\s+shadowcopy\s+delete",
]

_RING_1_COMPILED = [re.compile(p, re.IGNORECASE) for p in RING_1_FORBIDDEN_PATTERNS]


# ── Ring 2: Sensitive Keywords ─────────────────────────────────────────────────

# File operations
RING_2_FILE_OPS = frozenset({
    "file_write", "file_delete", "file_move", "file_overwrite",
})

# Git operations
RING_2_GIT_OPS = frozenset({
    "git push", "git force", "git reset", "git rebase",
    "git clean", "git checkout .", "git restore .",
})

# Code execution
RING_2_CODE_OPS = frozenset({
    "code_run", "code_test", "shell_exec", "shell_script",
    "pip install", "npm install", "choco install",
})

# Quantum operations that trigger computation or external effects
RING_2_QUANTUM_OPS = frozenset({
    "measure", "measure_x", "measure_y", "measure_z",
    "show_bloch", "launch_bloch", "bloch",
    "save_state", "quantum_save",
    "cloud_submit", "ibm_run", "aws_run", "azure_run",
    "evolve",
})

# Web: whitelisted URLs are Ring 2 (need approval before fetching)
RING_2_WEB_ACTION = "web_fetch"

# All Ring 2 sets combined for fast lookup
_ALL_RING_2 = (
    RING_2_FILE_OPS
    | RING_2_GIT_OPS
    | RING_2_CODE_OPS
    | RING_2_QUANTUM_OPS
    | {RING_2_WEB_ACTION}
)


# ── Ring 3: Safe Operations ────────────────────────────────────────────────────

RING_3_QUANTUM_GATES = frozenset({
    "reset", "h", "x", "y", "z", "s", "t", "sdg", "tdg",
    "sx", "sxdg", "cx", "cnot", "cz", "cy", "swap", "cswap",
    "rx", "ry", "rz", "p", "cp", "u1", "u2", "u3",
    "mcx", "ccx", "toffoli",
    "rotate_x", "rotate_y", "rotate_z",
    "inc", "dec", "reverse",
})

RING_3_QUANTUM_READS = frozenset({
    "get_state", "get_probabilities", "get_bloch_coords",
    "get_num_qubits", "get_gate_count", "get_entanglement_info",
    "get_marginal_probabilities", "get_all_qubit_bloch_coords",
    "state",  # display statevector
})

RING_3_MEMORY_OPS = frozenset({
    "list_states", "load_state", "list_circuits", "load_circuit",
    "get_session_summary", "memory_read",
})

RING_3_FILE_OPS = frozenset({
    "file_read", "dir_list", "dir_navigate", "file_search",
    "file_copy", "dir_create",
})

RING_3_GIT_READS = frozenset({
    "git status", "git log", "git diff", "git branch",
    "git show", "git stash list",
})

RING_3_SHELL_INFO = frozenset({
    "hostname", "whoami", "date", "ps", "tasklist", "env",
    "uname", "ver", "where", "which",
})


# ── Permission Manager ─────────────────────────────────────────────────────────

class PermissionManager:
    """
    Classifies and enforces the three-ring permission system for Eye of Sauron.

    Usage:
        pm = PermissionManager()
        level = pm.check_action("measure")        # → SENSITIVE
        level = pm.check_url("https://evil.com")  # → FORBIDDEN
        approved = pm.request_permission("measure", "Run 1024-shot measurement")
    """

    def check_action(self, action: str) -> PermissionLevel:
        """
        Determine the permission level for an action string.

        Checks Ring 1 patterns first (regex), then Ring 2 keyword sets,
        then Ring 3 safe sets. Unknown actions default to SENSITIVE.
        """
        action_lower = action.lower().strip()

        # Ring 1 check — hard block
        for pattern in _RING_1_COMPILED:
            if pattern.search(action):
                logger.warning("RING 1 BLOCKED: %s", action[:80])
                return PermissionLevel.FORBIDDEN

        # Ring 3 check — safe sets (check before Ring 2 to catch gate names)
        # Normalize action to first token for gate lookups
        first_token = action_lower.split()[0] if action_lower else ""
        if (first_token in RING_3_QUANTUM_GATES
                or first_token in RING_3_QUANTUM_READS
                or action_lower in RING_3_MEMORY_OPS
                or action_lower in RING_3_FILE_OPS
                or action_lower in RING_3_SHELL_INFO):
            return PermissionLevel.SAFE

        # Ring 2 check — exact match or starts-with
        for keyword in _ALL_RING_2:
            if action_lower == keyword or action_lower.startswith(keyword):
                return PermissionLevel.SENSITIVE

        # Git read check
        for git_read in RING_3_GIT_READS:
            if action_lower.startswith(git_read):
                return PermissionLevel.SAFE

        # Unknown → default SENSITIVE (safer than assuming safe)
        logger.debug("Unknown action '%s' defaulting to SENSITIVE.", action[:80])
        return PermissionLevel.SENSITIVE

    def check_url(self, url: str) -> PermissionLevel:
        """
        Classify a URL request.

        Returns:
          FORBIDDEN  if domain is not in WEB_ALLOWED_DOMAINS
          SENSITIVE  if domain is whitelisted (Ring 2 — still needs approval)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().strip()
            # Strip port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            if domain in WEB_ALLOWED_DOMAINS:
                return PermissionLevel.SENSITIVE
            else:
                logger.warning("RING 1 WEB BLOCKED: domain '%s' not in whitelist.", domain)
                return PermissionLevel.FORBIDDEN
        except Exception as e:
            logger.error("URL parse error for '%s': %s", url[:120], e)
            return PermissionLevel.FORBIDDEN

    def request_permission(
        self,
        action: str,
        description: str,
        context: Optional[str] = None,
    ) -> bool:
        """
        Present a Ring 2 permission prompt at the terminal. Blocks until answered.

        Args:
            action:      Short action label (e.g. "measure", "web_fetch")
            description: Human-readable description of what will happen
            context:     Optional extra context shown to user

        Returns:
            True if approved, False if denied or invalid input
        """
        print()
        print("  " + "─" * 58)
        print("  👁️  EYE OF SAURON — Permission Required  [Ring 2]")
        print("  " + "─" * 58)
        print(f"  Action : {action}")
        print(f"  Details: {description}")
        if context:
            print(f"  Context: {context}")
        print("  " + "─" * 58)

        try:
            answer = input("  Approve? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  [DENIED — interrupted]")
            return False

        approved = answer in ("y", "yes")
        status = "GRANTED" if approved else "DENIED"
        print(f"  [{status}]")
        print()
        return approved

    def is_forbidden(self, action: str) -> bool:
        return self.check_action(action) == PermissionLevel.FORBIDDEN

    def is_sensitive(self, action: str) -> bool:
        return self.check_action(action) == PermissionLevel.SENSITIVE

    def is_safe(self, action: str) -> bool:
        return self.check_action(action) == PermissionLevel.SAFE


# ── Singleton ──────────────────────────────────────────────────────────────────

_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get or create the global PermissionManager singleton."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
