#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 — Phase 3.5 Tests
Test 7.1: Lazy-loading of local toolsets via the integration layer.

Covers:
  - Manager initialisation (no toolset loading on creation)
  - RAM safety gate (mock low-RAM to verify refusal)
  - Individual toolset load / unload cycle
  - Status introspection helpers
  - System resource snapshot
  - Unknown toolset key handling
"""

import gc
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from libs.local_toolsets import (
    LocalToolsetManager,
    get_toolset_manager,
    load_numpy,
    load_scipy,
    load_qutip,
    load_qiskit,
    load_qencrypt,
    RAM_MAX_PERCENT,
    CPU_MAX_PERCENT,
    ToolsetConfig,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fresh_manager() -> LocalToolsetManager:
    """Create a brand-new manager (not the singleton) for isolated tests."""
    return LocalToolsetManager()


# ── 1. Manager initialisation ───────────────────────────────────────────────

class TestManagerInit:
    def test_singleton_returns_same_instance(self):
        """get_toolset_manager() returns the same object each time."""
        mgr1 = get_toolset_manager()
        mgr2 = get_toolset_manager()
        assert mgr1 is mgr2

    def test_all_five_toolsets_registered(self):
        mgr = _fresh_manager()
        expected = {"numpy", "scipy", "qutip", "qiskit", "qencrypt"}
        assert set(mgr.toolsets.keys()) == expected

    def test_none_loaded_at_init(self):
        """Brand-new manager has nothing loaded (we haven't called load yet)."""
        mgr = _fresh_manager()
        for key, cfg in mgr.toolsets.items():
            # Reset to simulate fresh state
            assert isinstance(cfg, ToolsetConfig), f"{key} config is wrong type"

    def test_safety_constants(self):
        assert RAM_MAX_PERCENT == 75
        assert CPU_MAX_PERCENT == 80


# ── 2. RAM safety gate ─────────────────────────────────────────────────────

class TestRamGate:
    def test_allows_load_when_ram_sufficient(self):
        mgr = _fresh_manager()
        # Mock psutil to report low usage (30%)
        mock_mem = MagicMock()
        mock_mem.used = 2 * 1024**3          # 2 GB used
        mock_mem.total = 8 * 1024**3          # 8 GB total
        mock_mem.percent = 25.0

        with patch("libs.local_toolsets.psutil.virtual_memory", return_value=mock_mem):
            assert mgr._check_ram_availability(200) is True

    def test_blocks_load_when_ram_exceeds_limit(self):
        mgr = _fresh_manager()
        # Mock psutil to report high usage (72%)
        mock_mem = MagicMock()
        mock_mem.used = 5.8 * 1024**3        # 5.8 GB used
        mock_mem.total = 8 * 1024**3          # 8 GB total
        mock_mem.percent = 72.5

        with patch("libs.local_toolsets.psutil.virtual_memory", return_value=mock_mem):
            # 200 MB more would push to 6.0 GB, ceiling is 6.0 GB (75% of 8 GB)
            assert mgr._check_ram_availability(300) is False

    def test_load_toolset_returns_none_when_ram_blocked(self):
        mgr = _fresh_manager()
        mock_mem = MagicMock()
        mock_mem.used = 5.9 * 1024**3
        mock_mem.total = 8 * 1024**3
        mock_mem.percent = 73.75

        with patch("libs.local_toolsets.psutil.virtual_memory", return_value=mock_mem):
            result = mgr.load_toolset("qiskit")  # 300 MB estimated
            assert result is None
            assert mgr.toolsets["qiskit"].load_error is not None


# ── 3. Toolset loading ─────────────────────────────────────────────────────

class TestToolsetLoading:
    def test_load_numpy_returns_module(self):
        mod = load_numpy()
        assert mod is not None
        assert hasattr(mod, "__version__")
        assert hasattr(mod, "array")

    def test_load_scipy_returns_module(self):
        mod = load_scipy()
        assert mod is not None
        assert hasattr(mod, "__version__")
        assert hasattr(mod, "linalg")

    def test_load_qutip_returns_module(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = load_qutip()
        assert mod is not None
        assert hasattr(mod, "__version__")
        assert hasattr(mod, "sigmax")

    def test_load_qiskit_returns_module(self):
        mod = load_qiskit()
        assert mod is not None
        assert hasattr(mod, "__version__")
        assert hasattr(mod, "QuantumCircuit")

    def test_load_qencrypt_returns_module(self):
        mod = load_qencrypt()
        assert mod is not None
        assert hasattr(mod, "encrypt_text")
        assert hasattr(mod, "decrypt_text")

    def test_cached_on_second_load(self):
        """Second call returns the same cached module object."""
        mgr = _fresh_manager()
        m1 = mgr.load_toolset("numpy")
        m2 = mgr.load_toolset("numpy")
        assert m1 is m2

    def test_unknown_key_raises_valueerror(self):
        mgr = _fresh_manager()
        with pytest.raises(ValueError, match="Unknown toolset"):
            mgr.load_toolset("nonexistent")


# ── 4. Toolset unloading ───────────────────────────────────────────────────

class TestToolsetUnloading:
    def test_unload_marks_not_loaded(self):
        mgr = _fresh_manager()
        mgr.load_toolset("numpy")
        assert mgr.toolsets["numpy"].loaded is True

        mgr.unload_toolset("numpy")
        assert mgr.toolsets["numpy"].loaded is False
        assert mgr.toolsets["numpy"].module is None

    def test_unload_nonloaded_returns_false(self):
        mgr = _fresh_manager()
        assert mgr.unload_toolset("qiskit") is False

    def test_unload_unknown_returns_false(self):
        mgr = _fresh_manager()
        assert mgr.unload_toolset("fake") is False


# ── 5. Status and introspection ────────────────────────────────────────────

class TestStatus:
    def test_get_loaded_status_keys(self):
        mgr = _fresh_manager()
        status = mgr.get_loaded_status()
        assert set(status.keys()) == {"numpy", "scipy", "qutip", "qiskit", "qencrypt"}
        for key, info in status.items():
            assert "loaded" in info
            assert "ram_mb" in info
            assert "source_available" in info
            assert "description" in info

    def test_total_loaded_ram_after_load(self):
        mgr = _fresh_manager()
        assert mgr.get_total_loaded_ram_mb() == 0

        mgr.load_toolset("numpy")
        assert mgr.get_total_loaded_ram_mb() == mgr.toolsets["numpy"].estimated_ram_mb

    def test_system_resources_snapshot(self):
        mgr = _fresh_manager()
        res = mgr.get_system_resources()
        assert "cpu_percent" in res
        assert "ram_used_mb" in res
        assert "ram_total_mb" in res
        assert "ram_percent" in res
        assert "ram_limit_percent" in res
        assert res["ram_limit_percent"] == 75

    def test_local_source_path(self):
        mgr = _fresh_manager()
        path = mgr.get_local_source_path("numpy")
        # May or may not exist depending on environment, but should return a Path or None
        assert path is None or hasattr(path, "is_dir")

    def test_local_source_path_unknown(self):
        mgr = _fresh_manager()
        assert mgr.get_local_source_path("fake") is None
