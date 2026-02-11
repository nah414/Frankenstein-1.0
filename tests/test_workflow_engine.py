"""
Unit tests for Workflow Engine.

Tests all 6 automated workflows supporting 28 quantum and classical providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 5
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from automation.workflow_engine import WorkflowEngine, get_workflow_engine


@pytest.fixture
def temp_report_dir(monkeypatch):
    """Create a temporary report directory for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / ".frankenstein" / "logs" / "resource_reports"
    temp_path.mkdir(parents=True, exist_ok=True)

    # Monkey patch the home directory
    monkeypatch.setattr(
        "automation.workflow_engine.Path.home",
        lambda: Path(temp_dir)
    )

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_resources():
    """Mock psutil resource checks to avoid delays."""
    with patch('automation.workflow_engine.psutil.cpu_percent', return_value=50.0), \
         patch('automation.workflow_engine.psutil.virtual_memory') as mock_mem:
        mock_mem.return_value = MagicMock(percent=50.0)
        yield


@pytest.fixture
def workflow_engine(temp_report_dir, mock_resources):
    """Create a fresh WorkflowEngine instance for each test."""
    # Reset singleton
    import automation.workflow_engine
    automation.workflow_engine._workflow_engine = None

    # Mock permission manager and audit logger
    with patch('automation.workflow_engine.get_permission_manager') as mock_pm, \
         patch('automation.workflow_engine.get_audit_logger') as mock_al:

        mock_pm_instance = MagicMock()
        mock_pm_instance.get_user_role.return_value = "Admin"
        mock_pm_instance.validate_operation.return_value = None
        mock_pm.return_value = mock_pm_instance

        mock_al_instance = MagicMock()
        mock_al_instance.get_all_providers_stats.return_value = {}
        mock_al.return_value = mock_al_instance

        engine = WorkflowEngine()
        # Set as singleton for tests
        automation.workflow_engine._workflow_engine = engine
        yield engine


class TestWorkflowEngineSingleton:
    """Test singleton pattern."""

    def test_singleton_instance(self, workflow_engine):
        """Verify only one instance is created."""
        engine1 = workflow_engine
        engine2 = get_workflow_engine()
        assert engine1 is engine2


class TestWorkflow1QuantumQueueOptimization:
    """Test quantum job queue optimization workflow."""

    def test_optimize_quantum_queue_success(self, workflow_engine):
        """Test successful quantum queue optimization."""
        result = workflow_engine.optimize_quantum_queue()

        assert result["status"] == "success"
        assert result["providers_checked"] == 15  # 15 quantum providers
        assert "providers" in result
        assert len(result["providers"]) == 15

    def test_optimize_quantum_queue_permission_denied(self, workflow_engine):
        """Test queue optimization with permission denied."""
        from permissions.permission_manager import PermissionDeniedError

        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Permission denied")

        result = workflow_engine.optimize_quantum_queue()

        assert result["status"] == "denied"

    def test_optimize_quantum_queue_high_resources(self, workflow_engine):
        """Test queue optimization pauses when resources high."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0):
            result = workflow_engine.optimize_quantum_queue()

            assert result["status"] == "paused"
            assert "Resource limits" in result["reason"]

    def test_optimize_quantum_queue_logs_action(self, workflow_engine):
        """Test that workflow logs actions."""
        workflow_engine.optimize_quantum_queue()

        # Verify audit logger was called
        workflow_engine.audit_logger.log_action.assert_called()


class TestWorkflow2ClassicalQueueOptimization:
    """Test classical compute queue optimization workflow."""

    def test_optimize_classical_queue_success(self, workflow_engine):
        """Test successful classical queue optimization."""
        result = workflow_engine.optimize_classical_queue()

        assert result["status"] == "success"
        assert result["providers_checked"] == 13  # 13 classical providers
        assert "providers" in result
        assert len(result["providers"]) == 13

    def test_optimize_classical_queue_permission_denied(self, workflow_engine):
        """Test queue optimization with permission denied."""
        from permissions.permission_manager import PermissionDeniedError

        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Permission denied")

        result = workflow_engine.optimize_classical_queue()

        assert result["status"] == "denied"

    def test_optimize_classical_queue_high_ram(self, workflow_engine):
        """Test queue optimization pauses when RAM is high."""
        with patch('automation.workflow_engine.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=75.0)

            result = workflow_engine.optimize_classical_queue()

            assert result["status"] == "paused"


class TestWorkflow3CredentialExpiry:
    """Test credential expiry warning workflow."""

    def test_check_credential_expiry_success(self, workflow_engine):
        """Test successful credential expiry check."""
        result = workflow_engine.check_credential_expiry()

        assert result["status"] == "success"
        assert "warnings" in result
        assert result["warnings"]["total_checked"] == 28  # All 28 providers

    def test_check_credential_expiry_permission_denied(self, workflow_engine):
        """Test credential check with permission denied."""
        from permissions.permission_manager import PermissionDeniedError

        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Permission denied")

        result = workflow_engine.check_credential_expiry()

        assert result["status"] == "denied"

    def test_check_credential_expiry_categorizes_warnings(self, workflow_engine):
        """Test that warnings are categorized by provider type."""
        result = workflow_engine.check_credential_expiry()

        assert "quantum" in result["warnings"]
        assert "classical" in result["warnings"]


class TestWorkflow4ResourceReporting:
    """Test resource usage reporting workflow."""

    def test_generate_resource_report_success(self, workflow_engine):
        """Test successful resource report generation."""
        result = workflow_engine.generate_resource_report()

        assert result["status"] == "success"
        assert "report_file" in result
        assert "providers_tracked" in result

    def test_generate_resource_report_creates_file(self, workflow_engine, temp_report_dir):
        """Test that report file is created."""
        result = workflow_engine.generate_resource_report()

        # Check that a report file exists
        report_files = list(temp_report_dir.glob("resource_report_*.json"))
        assert len(report_files) >= 1

    def test_generate_resource_report_high_resources(self, workflow_engine):
        """Test report generation pauses when resources high."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0):
            result = workflow_engine.generate_resource_report()

            assert result["status"] == "paused"


class TestWorkflow5ProviderHealthMonitoring:
    """Test provider health monitoring workflow."""

    def test_monitor_provider_health_success(self, workflow_engine):
        """Test successful provider health monitoring."""
        result = workflow_engine.monitor_provider_health()

        assert result["status"] == "success"
        assert result["total_checked"] == 28  # All 28 providers
        assert "health_status" in result

    def test_monitor_provider_health_checks_quantum(self, workflow_engine):
        """Test that quantum providers are checked."""
        result = workflow_engine.monitor_provider_health()

        quantum_status = result["health_status"]["quantum"]
        assert len(quantum_status) == 15  # 15 quantum providers

    def test_monitor_provider_health_checks_classical(self, workflow_engine):
        """Test that classical providers are checked."""
        result = workflow_engine.monitor_provider_health()

        classical_status = result["health_status"]["classical"]
        assert len(classical_status) == 13  # 13 classical providers

    def test_monitor_provider_health_permission_denied(self, workflow_engine):
        """Test health monitoring with permission denied."""
        from permissions.permission_manager import PermissionDeniedError

        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Permission denied")

        result = workflow_engine.monitor_provider_health()

        assert result["status"] == "denied"


class TestWorkflow6HardwareAutoTuning:
    """Test hardware optimization auto-tuning workflow."""

    def test_auto_tune_hardware_success(self, workflow_engine):
        """Test successful hardware auto-tuning."""
        result = workflow_engine.auto_tune_hardware()

        assert result["status"] == "success"
        assert result["providers_tuned"] == 13  # 13 classical providers
        assert "tuning_results" in result

    def test_auto_tune_hardware_permission_denied(self, workflow_engine):
        """Test auto-tuning with permission denied."""
        from permissions.permission_manager import PermissionDeniedError

        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Permission denied")

        result = workflow_engine.auto_tune_hardware()

        assert result["status"] == "denied"

    def test_auto_tune_hardware_high_resources(self, workflow_engine):
        """Test auto-tuning pauses when resources high."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0):
            result = workflow_engine.auto_tune_hardware()

            assert result["status"] == "paused"


class TestResourceSafetyFeature:
    """Test CRITICAL safety feature: user consent for termination."""

    def test_workflow_warns_on_high_resources(self, workflow_engine, capsys):
        """Test that workflow warns user when resources are high."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0):
            workflow_engine.optimize_quantum_queue()

            # Check that warning was printed
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "Resources approaching limits" in captured.out

    def test_grant_termination_consent(self, workflow_engine):
        """Test granting user consent for termination."""
        workflow_name = "optimize_quantum_queue"

        workflow_engine.grant_termination_consent(workflow_name)

        assert workflow_engine.user_consent_to_terminate[workflow_name] is True

    def test_revoke_termination_consent(self, workflow_engine):
        """Test revoking user consent for termination."""
        workflow_name = "optimize_quantum_queue"

        workflow_engine.grant_termination_consent(workflow_name)
        workflow_engine.revoke_termination_consent(workflow_name)

        assert workflow_engine.user_consent_to_terminate[workflow_name] is False

    def test_workflow_continues_with_consent(self, workflow_engine):
        """Test that workflow continues when user has given consent."""
        workflow_name = "optimize_quantum_queue"
        workflow_engine.grant_termination_consent(workflow_name)

        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0):
            result = workflow_engine.optimize_quantum_queue()

            # With consent, workflow should continue despite high resources
            assert result["status"] == "success"

    def test_workflow_pauses_without_consent(self, workflow_engine):
        """Test that workflow pauses when user hasn't given consent."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0):
            result = workflow_engine.optimize_quantum_queue()

            # Without consent, workflow should pause
            assert result["status"] == "paused"


class TestErrorHandling:
    """Test error handling across all workflows."""

    def test_workflow_handles_exceptions(self, workflow_engine):
        """Test that workflows handle exceptions gracefully."""
        from permissions.permission_manager import PermissionDeniedError

        # Simulate a permission error
        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Permission denied")

        result = workflow_engine.optimize_quantum_queue()

        # Should not crash, should return denied status
        assert result["status"] == "denied"

    def test_error_logged_to_audit(self, workflow_engine):
        """Test that errors are logged to audit trail."""
        from permissions.permission_manager import PermissionDeniedError

        workflow_engine.permission_manager.validate_operation.side_effect = \
            PermissionDeniedError("Test error")

        workflow_engine.optimize_quantum_queue()

        # Verify error was logged via _handle_workflow_error
        assert workflow_engine.audit_logger.log_action.called


class TestProviderCoverage:
    """Test that all 28 providers are correctly handled."""

    def test_quantum_providers_count(self, workflow_engine):
        """Test that quantum workflows handle 15 providers."""
        result = workflow_engine.optimize_quantum_queue()
        assert len(result["providers"]) == 15

    def test_classical_providers_count(self, workflow_engine):
        """Test that classical workflows handle 13 providers."""
        result = workflow_engine.optimize_classical_queue()
        assert len(result["providers"]) == 13

    def test_credential_check_covers_all_providers(self, workflow_engine):
        """Test that credential check covers all 28 providers."""
        result = workflow_engine.check_credential_expiry()
        assert result["warnings"]["total_checked"] == 28

    def test_health_monitoring_covers_all_providers(self, workflow_engine):
        """Test that health monitoring covers all 28 providers."""
        result = workflow_engine.monitor_provider_health()
        assert result["total_checked"] == 28


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
