"""
FRANKENSTEIN 1.0 - Safety System Tests
Unit tests for core/safety.py
"""

import pytest
from core.safety import (
    SAFETY,
    SafetyConstraints,
    check_resource_violation,
    get_constraints_dict,
    is_within_tier1_limits
)


class TestSafetyConstraints:
    """Test immutable safety constraints"""

    def test_safety_instance_exists(self):
        """Test that global SAFETY instance is initialized"""
        assert SAFETY is not None
        assert isinstance(SAFETY, SafetyConstraints)

    def test_safety_constraints_immutable(self):
        """Test that safety constraints cannot be modified"""
        with pytest.raises(Exception):
            SAFETY.MAX_CPU_PERCENT = 90

    def test_cpu_limits_appropriate(self):
        """Test CPU limits are set correctly for Tier 1"""
        assert SAFETY.MAX_CPU_PERCENT == 80
        assert SAFETY.MAX_CPU_PERCENT <= 100
        assert SAFETY.MAX_CPU_PERCENT > 0

    def test_memory_limits_appropriate(self):
        """Test memory limits are set correctly for Tier 1"""
        assert SAFETY.MAX_MEMORY_PERCENT == 70
        assert SAFETY.MAX_MEMORY_PERCENT <= 100
        assert SAFETY.MAX_MEMORY_PERCENT > 0

    def test_thread_limits_appropriate(self):
        """Test thread limits are set correctly for 4-core CPU"""
        assert SAFETY.MAX_WORKER_THREADS == 3
        assert SAFETY.MAX_WORKER_THREADS >= 1

    def test_auto_throttle_enabled(self):
        """Test auto-throttle is enabled by default"""
        assert SAFETY.AUTO_THROTTLE is True

    def test_emergency_stop_enabled(self):
        """Test emergency stop is available"""
        assert SAFETY.EMERGENCY_STOP_ENABLED is True


class TestResourceViolationCheck:
    """Test resource violation detection"""

    def test_no_violation_safe_resources(self):
        """Test that safe resource usage passes"""
        result = check_resource_violation(
            cpu_percent=50.0,
            memory_percent=50.0
        )
        assert result["safe"] is True
        assert len(result["violations"]) == 0
        assert len(result["recommended_actions"]) == 0

    def test_cpu_violation_detected(self):
        """Test CPU violation is detected"""
        result = check_resource_violation(
            cpu_percent=85.0,
            memory_percent=50.0
        )
        assert result["safe"] is False
        assert len(result["violations"]) == 1
        assert "CPU" in result["violations"][0]
        assert "throttle_cpu" in result["recommended_actions"]

    def test_memory_violation_detected(self):
        """Test memory violation is detected"""
        result = check_resource_violation(
            cpu_percent=50.0,
            memory_percent=75.0
        )
        assert result["safe"] is False
        assert len(result["violations"]) == 1
        assert "Memory" in result["violations"][0]
        assert "throttle_memory" in result["recommended_actions"]

    def test_multiple_violations_detected(self):
        """Test multiple violations are detected"""
        result = check_resource_violation(
            cpu_percent=90.0,
            memory_percent=80.0,
            gpu_percent=90.0,
            disk_io_mbps=250.0
        )
        assert result["safe"] is False
        assert len(result["violations"]) == 4
        assert len(result["recommended_actions"]) == 4

    def test_result_structure(self):
        """Test that result has expected structure"""
        result = check_resource_violation(50.0, 50.0)
        assert "safe" in result
        assert "violations" in result
        assert "recommended_actions" in result
        assert "auto_throttle" in result
        assert "emergency_stop_available" in result


class TestConstraintsDict:
    """Test constraints dictionary export"""

    def test_get_constraints_dict_returns_dict(self):
        """Test that constraints are returned as dictionary"""
        constraints = get_constraints_dict()
        assert isinstance(constraints, dict)

    def test_constraints_dict_contains_required_keys(self):
        """Test that all required keys are present"""
        constraints = get_constraints_dict()
        required_keys = [
            "max_cpu_percent",
            "max_memory_percent",
            "max_worker_threads",
            "auto_throttle",
            "emergency_stop"
        ]
        for key in required_keys:
            assert key in constraints

    def test_constraints_dict_values_match_safety(self):
        """Test that dict values match SAFETY instance"""
        constraints = get_constraints_dict()
        assert constraints["max_cpu_percent"] == SAFETY.MAX_CPU_PERCENT
        assert constraints["max_memory_percent"] == SAFETY.MAX_MEMORY_PERCENT
        assert constraints["max_worker_threads"] == SAFETY.MAX_WORKER_THREADS


class TestTier1Limits:
    """Test Tier 1 compliance checks"""

    def test_is_within_tier1_limits_returns_dict(self):
        """Test that Tier 1 check returns a dictionary"""
        result = is_within_tier1_limits()
        assert isinstance(result, dict)

    def test_tier1_cpu_limit(self):
        """Test CPU limit is appropriate for Tier 1"""
        result = is_within_tier1_limits()
        assert result["cpu_limit_appropriate"] is True

    def test_tier1_memory_limit(self):
        """Test memory limit is appropriate for Tier 1"""
        result = is_within_tier1_limits()
        assert result["memory_limit_appropriate"] is True

    def test_tier1_thread_limit(self):
        """Test thread limit is appropriate for Tier 1"""
        result = is_within_tier1_limits()
        assert result["thread_limit_appropriate"] is True

    def test_tier1_compliant(self):
        """Test overall Tier 1 compliance"""
        result = is_within_tier1_limits()
        assert result["tier1_compliant"] is True
