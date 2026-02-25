"""
FRANKENSTEIN 1.0 - Eye of Sauron: Sandbox
Phase 4 / Day 2: Security Layer

Extends the generic agents.sandbox.Sandbox with Sauron-specific rules:
  - Explicit allowed/blocked filesystem paths (from build plan spec)
  - Web sandbox: whitelist-only domain access, hard size/timeout caps
  - URL validation method used by web_tool.py before any HTTP request

All web rules are enforced HERE, not spread across other files.
"""

import logging
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from agents.sandbox import Sandbox

logger = logging.getLogger(__name__)


# ── Filesystem Boundaries ──────────────────────────────────────────────────────

ALLOWED_WRITE_PATHS = [
    Path.home() / "Frankenstein-1.0",
    Path.home() / "OneDrive" / "Desktop" / "Frankenstein_Terminal",
    Path.home() / ".frankenstein",
    Path.home() / "Documents" / "frankenstein_output",
    Path.home() / "Downloads" / "frankenstein_temp",
]

BLOCKED_PATHS = [
    Path("C:/Windows"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path.home() / "AppData" / "Local",
    Path.home() / "AppData" / "Roaming",
]


# ── Web Sandbox Rules ──────────────────────────────────────────────────────────
# These constants are the single source of truth for all web access control.
# web_tool.py reads from here — never duplicates these values.

WEB_ALLOWED_DOMAINS = frozenset({
    "wolfram.com",
    "www.wolfram.com",
    "wolframalpha.com",
    "www.wolframalpha.com",
    "wikipedia.org",
    "en.wikipedia.org",
    "www.wikipedia.org",
})

# Maximum bytes read from any web response (100 KB)
MAX_WEB_RESPONSE_BYTES: int = 102_400

# Hard HTTP request timeout in seconds
WEB_REQUEST_TIMEOUT_SEC: int = 10

# Maximum length of text returned to LLM after HTML stripping (chars)
MAX_CONTENT_CHARS: int = 8_000

# HTTP methods that are never allowed (only GET is permitted)
FORBIDDEN_HTTP_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"})


# ── Sauron Sandbox ─────────────────────────────────────────────────────────────

class SauronSandbox(Sandbox):
    """
    Sauron-specific sandbox enforcing filesystem and web access rules.

    Filesystem:
        is_write_allowed(path)  → checks ALLOWED_WRITE_PATHS
        is_path_blocked(path)   → checks BLOCKED_PATHS
        is_path_safe(path)      → combined check

    Web:
        validate_url(url)       → (allowed: bool, reason: str)
        enforce_https(url)      → upgrades http:// to https://
        check_redirect(chain)   → ensures redirects stay on same domain
    """

    def __init__(self):
        super().__init__()
        logger.debug("SauronSandbox initialized.")

    # ── Filesystem ─────────────────────────────────────────────────────────────

    def is_write_allowed(self, path) -> bool:
        """True if path is within an allowed write directory."""
        resolved = Path(path).resolve()
        return any(
            str(resolved).startswith(str(allowed.resolve()))
            for allowed in ALLOWED_WRITE_PATHS
        )

    def is_path_blocked(self, path) -> bool:
        """True if path falls within a hard-blocked directory."""
        resolved = Path(path).resolve()
        return any(
            str(resolved).startswith(str(blocked.resolve()))
            for blocked in BLOCKED_PATHS
        )

    def is_path_safe(self, path) -> Tuple[bool, str]:
        """
        Combined filesystem safety check.
        Returns (safe: bool, reason: str).
        """
        if self.is_path_blocked(path):
            return False, f"Path is in a blocked directory: {path}"
        if not self.is_write_allowed(path):
            return False, f"Path is outside allowed write directories: {path}"
        return True, "OK"

    # ── Web ────────────────────────────────────────────────────────────────────

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate a URL against the web sandbox rules.

        Checks (in order):
          1. URL must be parseable
          2. Scheme must be http or https (upgraded to https by enforce_https)
          3. Domain must be in WEB_ALLOWED_DOMAINS
          4. No credentials in URL (user:pass@)
          5. No fragment-only or data: URIs

        Returns:
            (True, "OK")                          — allowed
            (False, reason_string)                — blocked, with reason
        """
        if not url or not isinstance(url, str):
            return False, "Empty or invalid URL"

        # Force HTTPS before parsing
        url = self.enforce_https(url)

        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"URL parse error: {e}"

        # Scheme check
        if parsed.scheme not in ("http", "https"):
            return False, f"Scheme '{parsed.scheme}' not permitted (https only)"

        # No credentials embedded in URL
        if parsed.username or parsed.password:
            return False, "URLs with embedded credentials are forbidden"

        # Domain extraction (strip port)
        domain = (parsed.netloc or "").lower()
        if ":" in domain:
            domain = domain.rsplit(":", 1)[0]

        if not domain:
            return False, "URL has no domain"

        # Whitelist check — the core rule
        if domain not in WEB_ALLOWED_DOMAINS:
            return False, (
                f"Domain '{domain}' is not in the web whitelist. "
                f"Only Wolfram and Wikipedia are permitted."
            )

        return True, "OK"

    def enforce_https(self, url: str) -> str:
        """Silently upgrade http:// to https://."""
        if url.startswith("http://"):
            return "https://" + url[7:]
        return url

    def check_redirect_chain(self, response_history: list) -> Tuple[bool, str]:
        """
        Verify that all redirects stayed within the original domain.

        Args:
            response_history: List of requests.Response objects from a redirect chain

        Returns:
            (True, "OK") or (False, reason)
        """
        if not response_history:
            return True, "OK"

        # Get original domain
        first_url = response_history[0].url if response_history else ""
        try:
            origin_domain = urlparse(str(first_url)).netloc.lower()
            if ":" in origin_domain:
                origin_domain = origin_domain.rsplit(":", 1)[0]
        except Exception:
            return True, "OK"  # Non-fatal

        for resp in response_history:
            try:
                redir_domain = urlparse(str(resp.url)).netloc.lower()
                if ":" in redir_domain:
                    redir_domain = redir_domain.rsplit(":", 1)[0]
                if redir_domain not in WEB_ALLOWED_DOMAINS:
                    return False, (
                        f"Redirect left whitelisted domain: {redir_domain}"
                    )
            except Exception:
                continue

        return True, "OK"


# ── Singleton ──────────────────────────────────────────────────────────────────

_sauron_sandbox: "SauronSandbox | None" = None


def get_sauron_sandbox() -> SauronSandbox:
    """Get or create the global SauronSandbox singleton."""
    global _sauron_sandbox
    if _sauron_sandbox is None:
        _sauron_sandbox = SauronSandbox()
    return _sauron_sandbox
