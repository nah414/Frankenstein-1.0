"""
FRANKENSTEIN 1.0 - Eye of Sauron
Phase 4: Master Orchestrator Agent

CRITICAL: Do NOT import EyeOfSauron at module level.
Use get_sauron() for lazy-loaded singleton access.
The LLM model (~4.5GB RAM) must NOT load at terminal startup.
"""

_sauron_instance = None


def get_sauron():
    """Lazy load Eye of Sauron only when called."""
    global _sauron_instance
    if _sauron_instance is None:
        from .engine import EyeOfSauron
        _sauron_instance = EyeOfSauron()
    return _sauron_instance


def is_loaded() -> bool:
    """Check if Eye of Sauron is currently loaded in memory."""
    return _sauron_instance is not None


def unload_sauron() -> None:
    """Unload Eye of Sauron and free RAM. Safe to call even if not loaded."""
    global _sauron_instance
    if _sauron_instance is not None:
        _sauron_instance.unload()
        _sauron_instance = None
