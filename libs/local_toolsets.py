#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Local Toolset Integration Layer
Phase 3.5: Lazy-loading wrapper for custom scientific libraries

Purpose: Provide on-demand access to specialized toolsets without
         loading them at startup (RAM conservation)

Toolsets:
1. numpy       — Numerical computing (pip-installed 2.3.5)
2. scipy       — Scientific computing (pip-installed 1.16.3)
3. qutip       — Quantum dynamics and open systems (pip-installed 5.2.3)
4. qiskit      — Quantum circuit transpilation and hardware interface (pip-installed 2.2.3)
5. qencrypt    — Quantum encryption and security (editable install from local source)

Integration strategy:
  - numpy, scipy, qiskit: pip-installed stable releases (compiled C/Rust extensions)
  - qutip: pip-installed stable release (compiled Cython extensions)
  - qencrypt: editable install from C:/Users/adamn/Downloads/qencrypt-local/qencrypt-local
  - Local source trees in Downloads/ available for reference and pure-Python overlays

Safety: Lazy-loaded, RAM-aware, CPU-throttled
Author: Frankenstein Project
"""

import gc
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import psutil

logger = logging.getLogger(__name__)

# Path to local toolset source trees (for reference / pure-Python overlay access)
DOWNLOADS_PATH = Path("C:/Users/adamn/Downloads")

LOCAL_SOURCE_PATHS = {
    "numpy": DOWNLOADS_PATH / "numpy-main" / "numpy-main",
    "scipy": DOWNLOADS_PATH / "scipy-main" / "scipy-main",
    "qutip": DOWNLOADS_PATH / "qutip-master" / "qutip-master",
    "qiskit": DOWNLOADS_PATH / "qiskit-main" / "qiskit-main",
    "qencrypt": DOWNLOADS_PATH / "qencrypt-local" / "qencrypt-local",
}

# ── Safety limits ────────────────────────────────────────────────────────────
RAM_MAX_PERCENT = 75  # Refuse to load if system RAM exceeds this
CPU_MAX_PERCENT = 80  # Advisory; logged when exceeded


@dataclass
class ToolsetConfig:
    """Configuration for a managed toolset."""

    name: str
    import_name: str
    local_source_dir: str
    estimated_ram_mb: int
    description: str = ""
    loaded: bool = False
    module: Optional[Any] = None
    load_error: Optional[str] = None
    source_available: bool = False


class LocalToolsetManager:
    """
    Lazy-loading manager for scientific toolsets.

    CRITICAL: Libraries load ONLY when requested, not at startup.
    RAM usage is checked before every load (75% max = ~6 GB of 8 GB).
    """

    def __init__(self):
        self.toolsets: Dict[str, ToolsetConfig] = {
            "numpy": ToolsetConfig(
                name="numpy",
                import_name="numpy",
                local_source_dir="numpy-main/numpy-main",
                estimated_ram_mb=120,
                description="Numerical computing (arrays, linalg, FFT)",
            ),
            "scipy": ToolsetConfig(
                name="scipy",
                import_name="scipy",
                local_source_dir="scipy-main/scipy-main",
                estimated_ram_mb=180,
                description="Scientific computing (integrate, optimize, linalg)",
            ),
            "qutip": ToolsetConfig(
                name="qutip",
                import_name="qutip",
                local_source_dir="qutip-master/qutip-master",
                estimated_ram_mb=250,
                description="Quantum dynamics, master equations, open systems",
            ),
            "qiskit": ToolsetConfig(
                name="qiskit",
                import_name="qiskit",
                local_source_dir="qiskit-main/qiskit-main",
                estimated_ram_mb=300,
                description="Quantum circuit transpilation and hardware interface",
            ),
            "qencrypt": ToolsetConfig(
                name="qencrypt",
                import_name="qencrypt_local",
                local_source_dir="qencrypt-local/qencrypt-local",
                estimated_ram_mb=40,
                description="Quantum-assisted encryption (AES-256-GCM + quantum entropy)",
            ),
        }
        self._discover_sources()

    # ── Discovery ────────────────────────────────────────────────────────

    def _discover_sources(self):
        """Check which local source trees are present in Downloads."""
        for key, config in self.toolsets.items():
            source_path = DOWNLOADS_PATH / config.local_source_dir
            config.source_available = source_path.is_dir()
            if config.source_available:
                logger.debug("Local source found for %s at %s", key, source_path)
            else:
                logger.debug("No local source for %s at %s", key, source_path)

    # ── RAM safety ───────────────────────────────────────────────────────

    def _check_ram_availability(self, required_mb: int) -> bool:
        """Return True if loading *required_mb* would stay under RAM_MAX_PERCENT."""
        mem = psutil.virtual_memory()
        used_mb = mem.used / (1024 ** 2)
        total_mb = mem.total / (1024 ** 2)
        ceiling_mb = total_mb * (RAM_MAX_PERCENT / 100.0)

        projected = used_mb + required_mb
        if projected > ceiling_mb:
            logger.warning(
                "RAM check FAILED: used=%.0f MB + requested=%d MB = %.0f MB > ceiling=%.0f MB (%.0f%%)",
                used_mb, required_mb, projected, ceiling_mb, RAM_MAX_PERCENT,
            )
            return False
        return True

    def _log_cpu_warning(self):
        """Log a warning if current CPU usage exceeds the advisory limit."""
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > CPU_MAX_PERCENT:
            logger.warning("CPU usage is %.1f%% (advisory limit %d%%)", cpu, CPU_MAX_PERCENT)

    # ── Loading / unloading ──────────────────────────────────────────────

    def load_toolset(self, toolset_key: str) -> Optional[Any]:
        """
        Lazy-load a specific toolset.

        Args:
            toolset_key: One of 'numpy', 'scipy', 'qutip', 'qiskit', 'qencrypt'

        Returns:
            The imported module, or None if RAM constraint blocks the load.

        Raises:
            ValueError: If *toolset_key* is not a known toolset.
        """
        if toolset_key not in self.toolsets:
            raise ValueError(
                f"Unknown toolset: {toolset_key!r}. "
                f"Valid keys: {', '.join(sorted(self.toolsets))}"
            )

        config = self.toolsets[toolset_key]

        # Already loaded — return cached module
        if config.loaded and config.module is not None:
            return config.module

        # RAM gate
        if not self._check_ram_availability(config.estimated_ram_mb):
            msg = (
                f"Insufficient RAM to load {config.name}. "
                f"Estimated need: {config.estimated_ram_mb} MB."
            )
            logger.warning(msg)
            config.load_error = msg
            return None

        self._log_cpu_warning()

        # Attempt import
        try:
            logger.info("Loading %s (import %s)...", config.name, config.import_name)
            module = __import__(config.import_name)
            config.module = module
            config.loaded = True
            config.load_error = None

            version = getattr(module, "__version__", "unknown")
            location = getattr(module, "__file__", "unknown")
            logger.info(
                "Loaded %s %s from %s",
                config.name, version, location,
            )
            return module

        except ImportError as exc:
            msg = f"ImportError loading {config.name}: {exc}"
            logger.error(msg)
            config.load_error = msg
            return None
        except Exception as exc:
            msg = f"Unexpected error loading {config.name}: {exc}"
            logger.error(msg)
            config.load_error = msg
            return None

    def unload_toolset(self, toolset_key: str) -> bool:
        """
        Unload a toolset to free RAM.

        Returns True if the toolset was loaded and is now unloaded.
        """
        if toolset_key not in self.toolsets:
            return False

        config = self.toolsets[toolset_key]
        if not config.loaded:
            return False

        module_name = config.import_name

        # Drop our reference
        config.module = None
        config.loaded = False
        config.load_error = None

        # Remove from sys.modules to allow full GC
        keys_to_remove = [
            k for k in sys.modules if k == module_name or k.startswith(module_name + ".")
        ]
        for k in keys_to_remove:
            del sys.modules[k]

        gc.collect()
        logger.info("Unloaded %s (removed %d module entries)", config.name, len(keys_to_remove))
        return True

    # ── Status / introspection ───────────────────────────────────────────

    def get_loaded_status(self) -> Dict[str, Dict[str, Any]]:
        """Return load status of every toolset."""
        return {
            key: {
                "loaded": cfg.loaded,
                "ram_mb": cfg.estimated_ram_mb if cfg.loaded else 0,
                "source_available": cfg.source_available,
                "error": cfg.load_error,
                "description": cfg.description,
            }
            for key, cfg in self.toolsets.items()
        }

    def get_total_loaded_ram_mb(self) -> int:
        """Estimated total RAM consumed by currently loaded toolsets."""
        return sum(
            cfg.estimated_ram_mb for cfg in self.toolsets.values() if cfg.loaded
        )

    def get_system_resources(self) -> Dict[str, Any]:
        """Snapshot of current system resource usage."""
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            "cpu_percent": cpu,
            "ram_used_mb": round(mem.used / (1024 ** 2)),
            "ram_total_mb": round(mem.total / (1024 ** 2)),
            "ram_percent": mem.percent,
            "ram_limit_percent": RAM_MAX_PERCENT,
            "cpu_limit_percent": CPU_MAX_PERCENT,
            "toolsets_loaded_ram_mb": self.get_total_loaded_ram_mb(),
        }

    def get_local_source_path(self, toolset_key: str) -> Optional[Path]:
        """
        Return the local source directory for a toolset, or None if unavailable.

        Useful for agents that want to inspect or reference the source tree
        without importing compiled extensions.
        """
        if toolset_key not in self.toolsets:
            return None
        config = self.toolsets[toolset_key]
        if not config.source_available:
            return None
        return DOWNLOADS_PATH / config.local_source_dir


# ── Singleton ────────────────────────────────────────────────────────────────
_toolset_manager: Optional[LocalToolsetManager] = None


def get_toolset_manager() -> LocalToolsetManager:
    """Get or create the global LocalToolsetManager singleton."""
    global _toolset_manager
    if _toolset_manager is None:
        _toolset_manager = LocalToolsetManager()
    return _toolset_manager


# ── Convenience loaders (for agents and engine) ─────────────────────────────

def load_numpy():
    """Load numpy (lazy)."""
    return get_toolset_manager().load_toolset("numpy")


def load_scipy():
    """Load scipy (lazy)."""
    return get_toolset_manager().load_toolset("scipy")


def load_qutip():
    """Load qutip for quantum dynamics (lazy)."""
    return get_toolset_manager().load_toolset("qutip")


def load_qiskit():
    """Load qiskit for quantum hardware interface (lazy)."""
    return get_toolset_manager().load_toolset("qiskit")


def load_qencrypt():
    """Load qencrypt_local for quantum encryption (lazy)."""
    return get_toolset_manager().load_toolset("qencrypt")
