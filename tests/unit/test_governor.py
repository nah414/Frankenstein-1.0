"""
FRANKENSTEIN 1.0 - Resource Governor Tests
Unit tests for core/governor.py
"""

import pytest
import time
from core.governor import (
    ResourceGovernor,
    ResourceSnapshot,
    ThrottleLevel,
    get_governor
)


class TestThrottleLevel:
    """Test throttle level enumeration"""

    def test_throttle_levels_exist(self):
        """Test all throttle levels are defined"""
        assert ThrottleLevel.NONE is not None
        assert ThrottleLevel.LIGHT is not None
        assert ThrottleLevel.MODERATE is not None
        assert ThrottleLevel.HEAVY is not None
        assert ThrottleLevel.EMERGENCY is not None

    def test_throttle_levels_ordered(self):
        """Test throttle levels have correct ordering"""
        assert ThrottleLevel.NONE.value < ThrottleLevel.LIGHT.value
        assert ThrottleLevel.LIGHT.value < ThrottleLevel.MODERATE.value
        assert ThrottleLevel.MODERATE.value < ThrottleLevel.HEAVY.value
        assert ThrottleLevel.HEAVY.value < ThrottleLevel.EMERGENCY.value


class TestResourceSnapshot:
    """Test resource snapshot data structure"""

    def test_snapshot_creation(self):
        """Test creating a resource snapshot"""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_gb=4.8,
            memory_available_gb=3.2
        )
        assert snapshot is not None
        assert snapshot.cpu_percent == 50.0
        assert snapshot.memory_percent == 60.0

    def test_snapshot_defaults(self):
        """Test snapshot default values"""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_gb=4.8,
            memory_available_gb=3.2
        )
        assert snapshot.safe is True
        assert snapshot.gpu_percent == 0.0
        assert snapshot.throttle_level == ThrottleLevel.NONE
        assert len(snapshot.violations) == 0


class TestResourceGovernor:
    """Test resource governor functionality"""

    def test_governor_creation(self):
        """Test creating a ResourceGovernor instance"""
        governor = ResourceGovernor(poll_interval=1.0)
        assert governor is not None
        assert governor.poll_interval == 1.0

    def test_governor_initial_state(self):
        """Test governor starts in stopped state"""
        governor = ResourceGovernor()
        assert governor._running is False
        assert governor._thread is None

    def test_governor_start(self):
        """Test starting the governor"""
        governor = ResourceGovernor(poll_interval=2.0)
        result = governor.start()
        assert result is True
        assert governor._running is True

        # Clean up
        governor.stop()
        time.sleep(0.5)

    def test_governor_stop(self):
        """Test stopping the governor"""
        governor = ResourceGovernor()
        governor.start()
        time.sleep(0.5)

        result = governor.stop()
        assert result is True
        time.sleep(0.5)
        assert governor._running is False

    def test_governor_double_start_fails(self):
        """Test that starting an already running governor returns False"""
        governor = ResourceGovernor()
        first_start = governor.start()
        second_start = governor.start()

        assert first_start is True
        assert second_start is False

        # Clean up
        governor.stop()
        time.sleep(0.5)

    def test_get_status_structure(self):
        """Test that get_status returns expected structure"""
        governor = ResourceGovernor()
        governor.start()
        time.sleep(1.5)  # Wait for first snapshot

        status = governor.get_status()

        # Check required keys
        assert "running" in status
        assert "poll_interval" in status
        assert "throttle_level" in status

        # Clean up
        governor.stop()
        time.sleep(0.5)

    def test_governor_snapshot_after_start(self):
        """Test that governor creates snapshots after starting"""
        governor = ResourceGovernor(poll_interval=1.0)
        governor.start()
        time.sleep(2.0)  # Wait for snapshots

        snapshot = governor.get_latest_snapshot()
        if snapshot is not None:  # Only if psutil is available
            assert snapshot.cpu_percent >= 0
            assert snapshot.memory_percent >= 0

        # Clean up
        governor.stop()
        time.sleep(0.5)


class TestGovernorSingleton:
    """Test global governor instance"""

    def test_get_governor_returns_instance(self):
        """Test that get_governor returns a ResourceGovernor"""
        governor = get_governor()
        assert governor is not None
        assert isinstance(governor, ResourceGovernor)

    def test_get_governor_returns_same_instance(self):
        """Test that get_governor returns singleton"""
        gov1 = get_governor()
        gov2 = get_governor()
        assert gov1 is gov2


class TestGovernorSafety:
    """Test governor safety features"""

    def test_governor_custom_poll_interval(self):
        """Test custom poll intervals"""
        governor = ResourceGovernor(poll_interval=0.5)
        assert governor.poll_interval == 0.5

    def test_governor_thread_name(self):
        """Test governor thread has proper name"""
        governor = ResourceGovernor()
        governor.start()
        time.sleep(0.5)

        if governor._thread:
            assert "Frankenstein" in governor._thread.name or "Governor" in governor._thread.name

        # Clean up
        governor.stop()
        time.sleep(0.5)
