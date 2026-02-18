"""
Unit tests for Audit Logger.

Tests JSON-based logging, filtering, provider tracking, and log management
for all 28 quantum and classical providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 3
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import time

from permissions.audit_logger import (
    AuditLogger,
    get_audit_logger,
)


@pytest.fixture
def temp_log_dir(monkeypatch):
    """Create a temporary log directory for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / ".frankenstein" / "logs"
    temp_path.mkdir(parents=True, exist_ok=True)

    # Monkey patch the log directory
    monkeypatch.setattr(
        "permissions.audit_logger.Path.home",
        lambda: Path(temp_dir)
    )

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def fresh_logger(temp_log_dir):
    """Create a fresh AuditLogger instance for each test."""
    # Reset singleton
    AuditLogger._instance = None
    AuditLogger._initialized = False

    logger = AuditLogger()
    yield logger

    # Cleanup
    AuditLogger._instance = None
    AuditLogger._initialized = False


class TestSingletonBehavior:
    """Test singleton pattern implementation."""

    def test_singleton_instance(self, fresh_logger):
        """Verify only one instance is created."""
        logger1 = fresh_logger
        logger2 = AuditLogger()
        assert logger1 is logger2

    def test_get_audit_logger(self, fresh_logger):
        """Test helper function returns singleton."""
        logger1 = fresh_logger
        logger2 = get_audit_logger()
        assert logger1 is logger2


class TestLogFileCreation:
    """Test log file and directory creation."""

    def test_log_directory_created(self, fresh_logger, temp_log_dir):
        """Log directory should be created on first run."""
        assert temp_log_dir.exists()
        assert temp_log_dir.is_dir()

    def test_log_file_created(self, fresh_logger, temp_log_dir):
        """Log file should be created on first run."""
        log_file = temp_log_dir / "audit_log.json"
        assert log_file.exists()

    def test_key_file_created(self, fresh_logger, temp_log_dir):
        """Encryption key file should be created."""
        key_file = temp_log_dir / "audit.key"
        assert key_file.exists()

    def test_initial_log_file_empty(self, fresh_logger, temp_log_dir):
        """Initial log file should be empty JSON array."""
        log_file = temp_log_dir / "audit_log.json"
        with open(log_file, 'r') as f:
            logs = json.load(f)
        assert logs == []


class TestLogAction:
    """Test logging actions."""

    def test_log_simple_action(self, fresh_logger):
        """Test logging a simple action."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test_action",
            resource="test_resource",
            result="success"
        )

        logs = fresh_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["user_role"] == "Admin"
        assert logs[0]["action"] == "test_action"
        assert logs[0]["resource"] == "test_resource"
        assert logs[0]["result"] == "success"

    def test_log_with_provider(self, fresh_logger):
        """Test logging action with provider information."""
        fresh_logger.log_action(
            user_role="User",
            action="quantum_job_submit",
            resource="IBM Quantum API",
            result="success",
            provider_name="IBM Quantum",
            provider_category="quantum"
        )

        logs = fresh_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["provider_name"] == "IBM Quantum"
        assert logs[0]["provider_category"] == "quantum"

    def test_log_with_agent(self, fresh_logger):
        """Test logging action by agent."""
        fresh_logger.log_action(
            user_role="Agent",
            action="provider_health_check",
            resource="All providers",
            result="success",
            agent_name="HealthMonitorAgent"
        )

        logs = fresh_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]["agent_name"] == "HealthMonitorAgent"

    def test_log_includes_timestamp(self, fresh_logger):
        """Test that logs include ISO 8601 timestamp."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success"
        )

        logs = fresh_logger.get_logs()
        assert "timestamp" in logs[0]
        # Should be parseable as ISO 8601
        datetime.fromisoformat(logs[0]["timestamp"])

    def test_log_includes_resource_impact(self, fresh_logger):
        """Test that logs include CPU/RAM usage."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success"
        )

        logs = fresh_logger.get_logs()
        assert "resource_impact" in logs[0]
        assert "cpu_percent" in logs[0]["resource_impact"]
        assert "ram_percent" in logs[0]["resource_impact"]

    def test_log_with_details(self, fresh_logger):
        """Test logging with additional details."""
        fresh_logger.log_action(
            user_role="Admin",
            action="credential_modify",
            resource="AWS Braket credentials",
            result="success",
            provider_name="AWS Braket",
            details="Updated API key"
        )

        logs = fresh_logger.get_logs()
        assert logs[0]["details"] == "Updated API key"

    def test_log_multiple_actions(self, fresh_logger):
        """Test logging multiple actions."""
        for i in range(5):
            fresh_logger.log_action(
                user_role="Admin",
                action=f"test_action_{i}",
                resource=f"resource_{i}",
                result="success"
            )

        logs = fresh_logger.get_logs()
        assert len(logs) == 5


class TestGetLogs:
    """Test log retrieval and filtering."""

    def test_get_all_logs(self, fresh_logger):
        """Test retrieving all logs."""
        # Log some actions
        for i in range(3):
            fresh_logger.log_action(
                user_role="Admin",
                action=f"action_{i}",
                resource="test",
                result="success"
            )

        logs = fresh_logger.get_logs()
        assert len(logs) == 3

    def test_filter_by_action(self, fresh_logger):
        """Test filtering logs by action."""
        fresh_logger.log_action(
            user_role="Admin",
            action="quantum_job_submit",
            resource="test",
            result="success"
        )
        fresh_logger.log_action(
            user_role="Admin",
            action="credential_view",
            resource="test",
            result="success"
        )

        logs = fresh_logger.get_logs(action="quantum_job_submit")
        assert len(logs) == 1
        assert logs[0]["action"] == "quantum_job_submit"

    def test_filter_by_provider(self, fresh_logger):
        """Test filtering logs by provider name."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success",
            provider_name="IBM Quantum"
        )
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success",
            provider_name="AWS Braket"
        )

        logs = fresh_logger.get_logs(provider_name="IBM Quantum")
        assert len(logs) == 1
        assert logs[0]["provider_name"] == "IBM Quantum"

    def test_filter_by_user_role(self, fresh_logger):
        """Test filtering logs by user role."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success"
        )
        fresh_logger.log_action(
            user_role="User",
            action="test",
            resource="test",
            result="success"
        )

        logs = fresh_logger.get_logs(user_role="Admin")
        assert len(logs) == 1
        assert logs[0]["user_role"] == "Admin"

    def test_filter_by_result(self, fresh_logger):
        """Test filtering logs by result."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success"
        )
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="denied"
        )

        logs = fresh_logger.get_logs(result="denied")
        assert len(logs) == 1
        assert logs[0]["result"] == "denied"

    def test_filter_with_limit(self, fresh_logger):
        """Test limiting number of returned logs."""
        for i in range(10):
            fresh_logger.log_action(
                user_role="Admin",
                action="test",
                resource="test",
                result="success"
            )

        logs = fresh_logger.get_logs(limit=5)
        assert len(logs) == 5

    def test_filter_by_date_range(self, fresh_logger):
        """Test filtering logs by date range."""
        # Log some actions
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success"
        )

        # Get logs from last hour
        start_date = datetime.now() - timedelta(hours=1)
        logs = fresh_logger.get_logs(start_date=start_date)
        assert len(logs) == 1

    def test_multiple_filters(self, fresh_logger):
        """Test combining multiple filters."""
        fresh_logger.log_action(
            user_role="Admin",
            action="quantum_job_submit",
            resource="test",
            result="success",
            provider_name="IBM Quantum"
        )
        fresh_logger.log_action(
            user_role="User",
            action="quantum_job_submit",
            resource="test",
            result="denied",
            provider_name="IBM Quantum"
        )

        logs = fresh_logger.get_logs(
            action="quantum_job_submit",
            provider_name="IBM Quantum",
            result="success"
        )
        assert len(logs) == 1
        assert logs[0]["user_role"] == "Admin"


class TestProviderUsageStats:
    """Test provider usage statistics."""

    def test_stats_for_unused_provider(self, fresh_logger):
        """Test stats for provider with no usage."""
        stats = fresh_logger.get_provider_usage_stats("IBM Quantum")
        assert stats["total_actions"] == 0
        assert stats["successful_actions"] == 0
        assert stats["failed_actions"] == 0
        assert stats["last_used"] is None
        assert stats["actions_by_type"] == {}

    def test_stats_for_used_provider(self, fresh_logger):
        """Test stats for provider with usage."""
        # Log some actions for IBM Quantum
        fresh_logger.log_action(
            user_role="Admin",
            action="quantum_job_submit",
            resource="test",
            result="success",
            provider_name="IBM Quantum"
        )
        fresh_logger.log_action(
            user_role="User",
            action="quantum_job_submit",
            resource="test",
            result="denied",
            provider_name="IBM Quantum"
        )

        stats = fresh_logger.get_provider_usage_stats("IBM Quantum")
        assert stats["total_actions"] == 2
        assert stats["successful_actions"] == 1
        assert stats["failed_actions"] == 1
        assert stats["last_used"] is not None
        assert "quantum_job_submit" in stats["actions_by_type"]

    def test_stats_actions_by_type(self, fresh_logger):
        """Test action type breakdown in stats."""
        fresh_logger.log_action(
            user_role="Admin",
            action="quantum_job_submit",
            resource="test",
            result="success",
            provider_name="NVIDIA CUDA"
        )
        fresh_logger.log_action(
            user_role="Admin",
            action="quantum_job_submit",
            resource="test",
            result="success",
            provider_name="NVIDIA CUDA"
        )
        fresh_logger.log_action(
            user_role="Admin",
            action="provider_health_check",
            resource="test",
            result="success",
            provider_name="NVIDIA CUDA"
        )

        stats = fresh_logger.get_provider_usage_stats("NVIDIA CUDA")
        assert stats["actions_by_type"]["quantum_job_submit"] == 2
        assert stats["actions_by_type"]["provider_health_check"] == 1

    def test_stats_with_custom_days(self, fresh_logger):
        """Test stats with custom day range."""
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success",
            provider_name="AWS Braket"
        )

        # Should find logs within 30 days
        stats = fresh_logger.get_provider_usage_stats("AWS Braket", days=30)
        assert stats["total_actions"] == 1


class TestGetAllProvidersStats:
    """Test getting stats for all providers."""

    def test_all_providers_stats_empty(self, fresh_logger):
        """Test all providers stats when no logs exist."""
        stats = fresh_logger.get_all_providers_stats()
        assert stats == {}

    def test_all_providers_stats_multiple(self, fresh_logger):
        """Test all providers stats with multiple providers."""
        # Log actions for different providers
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success",
            provider_name="IBM Quantum"
        )
        fresh_logger.log_action(
            user_role="Admin",
            action="test",
            resource="test",
            result="success",
            provider_name="NVIDIA CUDA"
        )

        stats = fresh_logger.get_all_providers_stats()
        assert "IBM Quantum" in stats
        assert "NVIDIA CUDA" in stats
        assert stats["IBM Quantum"]["total_actions"] == 1
        assert stats["NVIDIA CUDA"]["total_actions"] == 1


class TestCleanupOldLogs:
    """Test cleaning up old logs."""

    def test_cleanup_removes_old_logs(self, fresh_logger):
        """Test that cleanup removes old logs."""
        # Log some actions
        for i in range(5):
            fresh_logger.log_action(
                user_role="Admin",
                action="test",
                resource="test",
                result="success"
            )

        # Cleanup logs older than 0 days (should remove all)
        removed = fresh_logger.cleanup_old_logs(days=0)
        assert removed == 5

        logs = fresh_logger.get_logs()
        assert len(logs) == 0

    def test_cleanup_keeps_recent_logs(self, fresh_logger):
        """Test that cleanup keeps recent logs."""
        # Log some actions
        for i in range(5):
            fresh_logger.log_action(
                user_role="Admin",
                action="test",
                resource="test",
                result="success"
            )

        # Cleanup logs older than 30 days (should keep all)
        removed = fresh_logger.cleanup_old_logs(days=30)
        assert removed == 0

        logs = fresh_logger.get_logs()
        assert len(logs) == 5


class TestLogRotation:
    """Test automatic log rotation."""

    def test_rotation_not_triggered_small_file(self, fresh_logger):
        """Test that rotation doesn't trigger for small files."""
        # Log a few actions (won't exceed 10MB)
        for i in range(10):
            fresh_logger.log_action(
                user_role="Admin",
                action="test",
                resource="test",
                result="success"
            )

        # Should not create rotated file
        log_dir = fresh_logger._log_dir
        rotated_files = list(log_dir.glob("audit_log_*.json"))
        assert len(rotated_files) == 0


class TestClearAllLogs:
    """Test clearing all logs."""

    def test_clear_all_logs(self, fresh_logger):
        """Test clearing all logs."""
        # Log some actions
        for i in range(5):
            fresh_logger.log_action(
                user_role="Admin",
                action="test",
                resource="test",
                result="success"
            )

        # Clear all logs
        fresh_logger.clear_all_logs()

        logs = fresh_logger.get_logs()
        assert len(logs) == 0


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_logging(self, fresh_logger):
        """Test concurrent log writes don't cause issues."""
        import threading

        def log_actions():
            for i in range(10):
                fresh_logger.log_action(
                    user_role="Admin",
                    action="test",
                    resource="test",
                    result="success"
                )

        threads = [threading.Thread(target=log_actions) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        logs = fresh_logger.get_logs()
        # Should have all 30 logs
        assert len(logs) == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
