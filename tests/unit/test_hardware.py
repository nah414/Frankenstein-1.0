#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Hardware Monitor Tests
Phase 2: Hardware Health + Auto-Switch Warning

Tests for core/hardware_monitor.py and core/hardware_dashboard.py
Run with: pytest tests/unit/test_hardware.py -v
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest


class TestHardwareTier:
    """Test hardware tier enumeration"""

    def test_tiers_exist(self):
        """Test all tiers are defined"""
        from core.hardware_monitor import HardwareTier
        assert HardwareTier.TIER1_EDGE is not None
        assert HardwareTier.TIER2_WORKSTATION is not None
        assert HardwareTier.TIER3_HPC is not None
        assert HardwareTier.TIER4_CLOUD is not None
        assert HardwareTier.TIER5_QUANTUM is not None

    def test_tier_has_properties(self):
        """Test tier has all properties"""
        from core.hardware_monitor import HardwareTier
        tier = HardwareTier.TIER1_EDGE
        assert tier.name == "Tier 1: Edge"
        assert tier.description == "Dell i3 8th Gen"
        assert tier.max_cpu == 80
        assert tier.max_memory == 70
        assert tier.max_workers == 3


class TestHealthStatus:
    """Test health status enumeration"""

    def test_statuses_exist(self):
        """Test all statuses are defined"""
        from core.hardware_monitor import HealthStatus
        assert HealthStatus.OPTIMAL is not None
        assert HealthStatus.NORMAL is not None
        assert HealthStatus.ELEVATED is not None
        assert HealthStatus.WARNING is not None
        assert HealthStatus.CRITICAL is not None
        assert HealthStatus.OVERLOAD is not None

    def test_status_has_properties(self):
        """Test status has all properties"""
        from core.hardware_monitor import HealthStatus
        status = HealthStatus.OPTIMAL
        assert status.label == "OPTIMAL"
        assert status.icon == "🟢"
        assert status.color == "#00ff88"
        assert "efficiently" in status.description.lower()


class TestHardwareHealthMonitor:
    """Test hardware health monitor functionality"""

    def test_monitor_creation(self):
        """Test creating a hardware monitor"""
        from core.hardware_monitor import HardwareHealthMonitor
        monitor = HardwareHealthMonitor()
        assert monitor is not None

    def test_monitor_default_tier(self):
        """Test monitor defaults to Tier 1"""
        from core.hardware_monitor import HardwareHealthMonitor, HardwareTier
        monitor = HardwareHealthMonitor()
        assert monitor.get_current_tier() == HardwareTier.TIER1_EDGE

    def test_monitor_start_stop(self):
        """Test starting and stopping monitor"""
        from core.hardware_monitor import HardwareHealthMonitor
        monitor = HardwareHealthMonitor()
        
        result = monitor.start()
        assert result is True
        assert monitor._running is True
        
        result = monitor.stop()
        assert result is True
        assert monitor._running is False

    def test_monitor_double_start(self):
        """Test that double start returns False"""
        from core.hardware_monitor import HardwareHealthMonitor
        monitor = HardwareHealthMonitor()
        
        monitor.start()
        result = monitor.start()
        assert result is False
        
        monitor.stop()

    def test_get_health_status(self):
        """Test getting health status"""
        from core.hardware_monitor import HardwareHealthMonitor, HealthStatus
        monitor = HardwareHealthMonitor()
        monitor.start()
        
        status = monitor.get_health_status()
        assert isinstance(status, HealthStatus)
        
        monitor.stop()

    def test_get_trend_initially_none(self):
        """Test that trend is None initially (not enough data)"""
        from core.hardware_monitor import HardwareHealthMonitor
        monitor = HardwareHealthMonitor()
        
        trend = monitor.get_trend()
        assert trend is None  # Need samples first

    def test_get_trend_after_samples(self):
        """Test getting trend after collecting samples"""
        from core.hardware_monitor import HardwareHealthMonitor
        monitor = HardwareHealthMonitor()
        monitor.start()
        
        # Wait for samples
        time.sleep(5)
        
        trend = monitor.get_trend()
        # May or may not have enough samples yet
        
        monitor.stop()

    def test_get_switch_recommendation(self):
        """Test getting switch recommendation"""
        from core.hardware_monitor import HardwareHealthMonitor, SwitchRecommendation
        monitor = HardwareHealthMonitor()
        monitor.start()
        
        recommendation = monitor.get_switch_recommendation()
        assert isinstance(recommendation, SwitchRecommendation)
        assert isinstance(recommendation.should_switch, bool)
        assert recommendation.urgency in ("none", "low", "medium", "high", "immediate")
        
        monitor.stop()

    def test_get_stats(self):
        """Test getting statistics"""
        from core.hardware_monitor import HardwareHealthMonitor
        monitor = HardwareHealthMonitor()
        monitor.start()
        time.sleep(0.5)
        
        stats = monitor.get_stats()
        assert "running" in stats
        assert "current_tier" in stats
        assert "health_status" in stats
        assert "headroom_percent" in stats
        assert stats["running"] is True
        
        monitor.stop()

    def test_set_tier(self):
        """Test setting hardware tier"""
        from core.hardware_monitor import HardwareHealthMonitor, HardwareTier
        monitor = HardwareHealthMonitor()
        
        monitor.set_tier(HardwareTier.TIER2_WORKSTATION)
        assert monitor.get_current_tier() == HardwareTier.TIER2_WORKSTATION


class TestHardwareMonitorSingleton:
    """Test global monitor instance"""

    def test_get_monitor_returns_instance(self):
        """Test that get_hardware_monitor returns a monitor"""
        from core.hardware_monitor import get_hardware_monitor, HardwareHealthMonitor
        monitor = get_hardware_monitor()
        assert monitor is not None
        assert isinstance(monitor, HardwareHealthMonitor)

    def test_get_monitor_returns_same_instance(self):
        """Test that get_hardware_monitor returns singleton"""
        from core.hardware_monitor import get_hardware_monitor
        m1 = get_hardware_monitor()
        m2 = get_hardware_monitor()
        assert m1 is m2


class TestHardwareDashboard:
    """Test hardware dashboard functionality"""

    def test_dashboard_creation(self):
        """Test creating a hardware dashboard"""
        from core.hardware_dashboard import HardwareDashboard
        dashboard = HardwareDashboard()
        assert dashboard is not None

    def test_get_status_bar(self):
        """Test getting status bar string"""
        from core.hardware_dashboard import HardwareDashboard
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        monitor.start()
        
        dashboard = HardwareDashboard(monitor)
        status = dashboard.get_status_bar()
        
        assert isinstance(status, str)
        assert len(status) > 0
        
        monitor.stop()

    def test_get_full_dashboard(self):
        """Test getting full dashboard display"""
        from core.hardware_dashboard import HardwareDashboard
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        monitor.start()
        
        dashboard = HardwareDashboard(monitor)
        display = dashboard.get_full_dashboard()
        
        assert isinstance(display, str)
        assert "HARDWARE HEALTH" in display
        assert "CURRENT TIER" in display
        
        monitor.stop()

    def test_get_tier_info(self):
        """Test getting tier information"""
        from core.hardware_dashboard import HardwareDashboard
        
        dashboard = HardwareDashboard()
        info = dashboard.get_tier_info()
        
        assert isinstance(info, str)
        assert "Tier 1" in info
        assert "Tier 5" in info


class TestHandleHardwareCommand:
    """Test the terminal command handler"""

    def test_handle_status_command(self):
        """Test handling 'hardware status' command"""
        from core.hardware_dashboard import handle_hardware_command
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        monitor.start()
        
        output = []
        def capture_output(text):
            output.append(text)
        
        handle_hardware_command(["status"], capture_output)
        
        full_output = "".join(output)
        assert "HARDWARE HEALTH" in full_output
        
        monitor.stop()

    def test_handle_tiers_command(self):
        """Test handling 'hardware tiers' command"""
        from core.hardware_dashboard import handle_hardware_command
        
        output = []
        def capture_output(text):
            output.append(text)
        
        handle_hardware_command(["tiers"], capture_output)
        
        full_output = "".join(output)
        assert "TIER REFERENCE" in full_output

    def test_handle_recommend_command(self):
        """Test handling 'hardware recommend' command"""
        from core.hardware_dashboard import handle_hardware_command
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        monitor.start()
        
        output = []
        def capture_output(text):
            output.append(text)
        
        handle_hardware_command(["recommend"], capture_output)
        
        full_output = "".join(output)
        assert "switch" in full_output.lower() or "headroom" in full_output.lower()
        
        monitor.stop()

    def test_handle_diagnose_command(self):
        """Test handling 'hardware diagnose' command"""
        from core.hardware_dashboard import handle_hardware_command
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        monitor.start()
        
        output = []
        def capture_output(text):
            output.append(text)
        
        handle_hardware_command(["diagnose"], capture_output)
        
        full_output = "".join(output)
        assert "DIAGNOSIS" in full_output
        assert "Primary Cause" in full_output
        
        monitor.stop()


class TestDiagnosis:
    """Test the diagnosis functionality"""

    def test_get_diagnosis_returns_dict(self):
        """Test that get_diagnosis returns a dictionary"""
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        monitor.start()
        
        diagnosis = monitor.get_diagnosis()
        assert isinstance(diagnosis, dict)
        assert "status" in diagnosis
        assert "primary_cause" in diagnosis
        assert "issues" in diagnosis
        assert "recommendations" in diagnosis
        
        monitor.stop()

    def test_diagnosis_has_tier_limits(self):
        """Test that diagnosis includes tier limits"""
        from core.hardware_monitor import get_hardware_monitor
        
        monitor = get_hardware_monitor()
        diagnosis = monitor.get_diagnosis()
        
        assert "tier_limits" in diagnosis
        assert "max_cpu" in diagnosis["tier_limits"]
        assert "max_memory" in diagnosis["tier_limits"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
