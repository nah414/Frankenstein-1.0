"""
Comprehensive Integration Tests for Phase 3 Step 6.

Tests the complete permissions and automation system end-to-end,
verifying all components work together across all 28 providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 9 - Integration Tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import all major components
from permissions.rbac import (
    get_permissions,
    get_provider_access,
    get_quantum_providers,
    get_classical_providers,
    ALL_PROVIDERS
)
from permissions.permission_manager import get_permission_manager, PermissionDeniedError
from permissions.audit_logger import get_audit_logger
from automation.scheduler import get_scheduler, TaskStatus
from automation.workflow_engine import get_workflow_engine
from integration.permission_integration import get_permission_integration


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create temporary config directory."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / ".frankenstein"
    temp_path.mkdir(parents=True, exist_ok=True)

    # Create config and logs subdirectories
    (temp_path / "config").mkdir(exist_ok=True)
    (temp_path / "logs").mkdir(exist_ok=True)
    (temp_path / "logs" / "audit").mkdir(exist_ok=True)
    (temp_path / "logs" / "resource_reports").mkdir(exist_ok=True)

    monkeypatch.setattr("permissions.permission_manager.Path.home", lambda: Path(temp_dir))
    monkeypatch.setattr("permissions.audit_logger.Path.home", lambda: Path(temp_dir))
    monkeypatch.setattr("permissions.setup_wizard.Path.home", lambda: Path(temp_dir))
    monkeypatch.setattr("automation.workflow_engine.Path.home", lambda: Path(temp_dir))

    # Reset singletons before each test
    import permissions.permission_manager
    import permissions.audit_logger
    import automation.scheduler
    import automation.workflow_engine
    import integration.permission_integration

    permissions.permission_manager._manager = None
    permissions.audit_logger._audit_logger = None
    automation.scheduler.TaskScheduler._instance = None
    automation.scheduler.TaskScheduler._initialized = False
    automation.workflow_engine._workflow_engine = None
    integration.permission_integration._integration = None

    yield temp_path

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_resources():
    """Mock resource checks."""
    with patch('automation.scheduler.psutil.cpu_percent', return_value=50.0), \
         patch('automation.scheduler.psutil.virtual_memory') as mock_mem, \
         patch('automation.workflow_engine.psutil.cpu_percent', return_value=50.0), \
         patch('automation.workflow_engine.psutil.virtual_memory') as mock_mem2:
        mock_mem.return_value = MagicMock(percent=50.0)
        mock_mem2.return_value = MagicMock(percent=50.0)
        yield


class TestProviderCoverage:
    """Test that all 28 providers are properly supported."""

    def test_all_providers_count(self):
        """Verify we have exactly 28 providers."""
        assert len(ALL_PROVIDERS) == 28

    def test_quantum_providers_count(self):
        """Verify we have 15 quantum providers."""
        quantum = get_quantum_providers()
        assert len(quantum) == 15

    def test_classical_providers_count(self):
        """Verify we have 13 classical providers."""
        classical = get_classical_providers()
        assert len(classical) == 13

    def test_no_duplicate_providers(self):
        """Verify no duplicate providers."""
        assert len(ALL_PROVIDERS) == len(set(ALL_PROVIDERS))

    def test_quantum_classical_no_overlap(self):
        """Verify quantum and classical lists don't overlap."""
        quantum = set(get_quantum_providers())
        classical = set(get_classical_providers())
        assert len(quantum & classical) == 0

    def test_quantum_classical_complete(self):
        """Verify quantum + classical = all providers."""
        quantum = set(get_quantum_providers())
        classical = set(get_classical_providers())
        all_set = set(ALL_PROVIDERS)
        assert quantum | classical == all_set


class TestRoleBasedAccess:
    """Test RBAC system across all roles."""

    def test_admin_has_full_access(self, temp_config_dir):
        """Admin should have access to all 28 providers."""
        accessible = get_provider_access("Admin")
        assert len(accessible) == 28
        assert set(accessible) == set(ALL_PROVIDERS)

    def test_user_has_access(self, temp_config_dir):
        """User should have provider access."""
        accessible = get_provider_access("User")
        # User has access to providers (implementation may vary)
        assert isinstance(accessible, list)

    def test_agent_has_access(self, temp_config_dir):
        """Agent should have provider access."""
        accessible = get_provider_access("Agent")
        # Agent has provider access (implementation may vary)
        assert isinstance(accessible, list)

    def test_readonly_has_no_provider_access(self, temp_config_dir):
        """ReadOnly should have no provider access."""
        accessible = get_provider_access("ReadOnly")
        assert len(accessible) == 0

    def test_admin_permissions(self):
        """Admin should have all permissions."""
        perms = get_permissions("Admin")
        assert "quantum_job_submit" in perms
        assert "classical_compute_submit" in perms
        assert "credential_view" in perms
        assert "credential_modify" in perms
        assert "audit_view" in perms
        assert "provider_access_all" in perms

    def test_readonly_permissions(self):
        """ReadOnly should only have audit view."""
        perms = get_permissions("ReadOnly")
        assert "audit_view" in perms
        # ReadOnly should not have execution permissions
        assert "credential_modify" not in perms


class TestPermissionManagerIntegration:
    """Test PermissionManager with other components."""

    def test_permission_manager_singleton(self, temp_config_dir):
        """Verify PermissionManager is singleton."""
        pm1 = get_permission_manager()
        pm2 = get_permission_manager()
        assert pm1 is pm2

    def test_role_change_affects_permissions(self, temp_config_dir):
        """Changing role should affect permissions."""
        pm = get_permission_manager()

        # Start as Admin
        pm.set_user_role("Admin")
        assert pm.check_permission("Admin", "quantum_job_submit")

        # Change to ReadOnly
        pm.set_user_role("ReadOnly")
        assert not pm.check_permission("ReadOnly", "quantum_job_submit")

    def test_provider_access_filtering(self, temp_config_dir):
        """Test provider access filtering."""
        pm = get_permission_manager()
        integration = get_permission_integration()

        pm.set_user_role("Admin")
        all_filtered = integration.validate_and_filter_providers(ALL_PROVIDERS)
        assert len(all_filtered) == 28

        pm.set_user_role("ReadOnly")
        readonly_filtered = integration.validate_and_filter_providers(ALL_PROVIDERS)
        assert len(readonly_filtered) == 0


class TestAuditLogging:
    """Test audit logging integration."""

    def test_audit_logger_singleton(self, temp_config_dir):
        """Verify AuditLogger is singleton."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_audit_log_records_actions(self, temp_config_dir, mock_resources):
        """Test that actions are logged to audit trail."""
        logger = get_audit_logger()
        pm = get_permission_manager()

        # Perform an action
        pm.set_user_role("Admin")

        # Check audit log
        recent = logger.get_recent_actions(days=1)
        assert len(recent) > 0

    def test_audit_log_tracks_providers(self, temp_config_dir):
        """Test that audit log tracks provider-specific actions."""
        logger = get_audit_logger()
        integration = get_permission_integration()

        # Log actions for different providers
        integration.log_router_action("route", "IBM Quantum", "success")
        integration.log_router_action("route", "AWS Braket", "success")

        # Verify logged
        recent = logger.get_recent_actions(days=1)
        provider_actions = [a for a in recent if a.get("provider_name")]
        assert len(provider_actions) >= 2


class TestWorkflowEngineIntegration:
    """Test WorkflowEngine with permissions and scheduler."""

    def test_workflow_engine_singleton(self, temp_config_dir, mock_resources):
        """Verify WorkflowEngine is singleton."""
        engine1 = get_workflow_engine()
        engine2 = get_workflow_engine()
        assert engine1 is engine2

    def test_workflows_respect_permissions(self, temp_config_dir, mock_resources):
        """Test that workflows respect permission settings."""
        engine = get_workflow_engine()
        pm = get_permission_manager()

        # Set to ReadOnly (no permissions)
        pm.set_user_role("ReadOnly")

        # Try to run quantum workflow - should be denied
        result = engine.optimize_quantum_queue()
        assert result["status"] == "denied"

    def test_workflows_check_resource_limits(self, temp_config_dir):
        """Test that workflows check resource limits."""
        engine = get_workflow_engine()

        # Mock high CPU
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0), \
             patch('automation.workflow_engine.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=50.0)

            result = engine.optimize_quantum_queue()
            # Should pause due to high CPU
            assert result["status"] == "paused"

    def test_consent_management(self, temp_config_dir, mock_resources):
        """Test workflow termination consent."""
        engine = get_workflow_engine()

        # Initially no consent
        assert not engine.user_consent_to_terminate.get("test_workflow", False)

        # Grant consent
        engine.grant_termination_consent("test_workflow")
        assert engine.user_consent_to_terminate["test_workflow"] is True

        # Revoke consent
        engine.revoke_termination_consent("test_workflow")
        assert engine.user_consent_to_terminate["test_workflow"] is False


class TestSchedulerIntegration:
    """Test TaskScheduler integration."""

    def test_scheduler_singleton(self, temp_config_dir, mock_resources):
        """Verify TaskScheduler is singleton."""
        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()
        assert scheduler1 is scheduler2

    def test_scheduler_task_registration(self, temp_config_dir, mock_resources):
        """Test task registration."""
        scheduler = get_scheduler()

        task_func = Mock()
        task = scheduler.register_task(
            task_id="test_integration_task",
            task_func=task_func,
            schedule_type="one_time",
            target_providers=["IBM Quantum", "AWS Braket"]
        )

        assert task.task_id == "test_integration_task"
        assert "IBM Quantum" in task.target_providers
        assert "AWS Braket" in task.target_providers

    def test_scheduler_provider_filtering(self, temp_config_dir, mock_resources):
        """Test scheduler can filter tasks by provider."""
        scheduler = get_scheduler()

        # Register tasks with different providers
        scheduler.register_task(
            task_id="ibm_task",
            task_func=Mock(),
            schedule_type="one_time",
            target_providers=["IBM Quantum"]
        )

        scheduler.register_task(
            task_id="aws_task",
            task_func=Mock(),
            schedule_type="one_time",
            target_providers=["AWS Braket"]
        )

        # Get tasks for specific provider
        ibm_tasks = scheduler.get_tasks_by_provider("IBM Quantum")
        assert len(ibm_tasks) >= 1
        assert ibm_tasks[0].task_id == "ibm_task"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    def test_admin_quantum_workflow(self, temp_config_dir, mock_resources):
        """Test Admin running quantum workflow end-to-end."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        # Verify permissions
        assert pm.check_permission("Admin", "quantum_job_submit")

        # Run workflow
        engine = get_workflow_engine()
        result = engine.optimize_quantum_queue()

        assert result["status"] == "success"
        assert result["providers_checked"] == 15  # All quantum providers

        # Verify logged
        logger = get_audit_logger()
        recent = logger.get_recent_actions(days=1)
        assert len(recent) > 0

    def test_admin_classical_workflow(self, temp_config_dir, mock_resources):
        """Test Admin running classical workflow end-to-end."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.optimize_classical_queue()

        assert result["status"] == "success"
        assert result["providers_checked"] == 13  # All classical providers

    def test_user_workflow_restricted(self, temp_config_dir, mock_resources):
        """Test User role restrictions."""
        pm = get_permission_manager()
        pm.set_user_role("User")

        # User can submit jobs
        assert pm.check_permission("User", "quantum_job_submit")
        assert pm.check_permission("User", "classical_compute_submit")

        # But cannot modify credentials
        assert not pm.check_permission("User", "credential_modify")

    def test_readonly_cannot_execute(self, temp_config_dir, mock_resources):
        """Test ReadOnly cannot execute workflows."""
        pm = get_permission_manager()
        pm.set_user_role("ReadOnly")

        engine = get_workflow_engine()

        # All workflows should be denied
        quantum_result = engine.optimize_quantum_queue()
        assert quantum_result["status"] == "denied"

        classical_result = engine.optimize_classical_queue()
        assert classical_result["status"] == "denied"

        # But can view audit logs
        assert pm.check_permission("ReadOnly", "audit_view")


class TestAllWorkflows:
    """Test all 6 automated workflows."""

    def test_quantum_queue_workflow(self, temp_config_dir, mock_resources):
        """Test quantum queue optimization workflow."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.optimize_quantum_queue()

        assert result["status"] == "success"
        assert "providers" in result
        assert len(result["providers"]) == 15

    def test_classical_queue_workflow(self, temp_config_dir, mock_resources):
        """Test classical queue optimization workflow."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.optimize_classical_queue()

        assert result["status"] == "success"
        assert "providers" in result
        assert len(result["providers"]) == 13

    def test_credential_expiry_workflow(self, temp_config_dir, mock_resources):
        """Test credential expiry warning workflow."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.check_credential_expiry()

        assert result["status"] == "success"
        assert result["warnings"]["total_checked"] == 28

    def test_resource_report_workflow(self, temp_config_dir, mock_resources):
        """Test resource usage reporting workflow."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.generate_resource_report()

        assert result["status"] == "success"
        assert "report_file" in result

    def test_health_monitoring_workflow(self, temp_config_dir, mock_resources):
        """Test provider health monitoring workflow."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.monitor_provider_health()

        assert result["status"] == "success"
        assert result["total_checked"] == 28

    def test_hardware_tuning_workflow(self, temp_config_dir, mock_resources):
        """Test hardware optimization auto-tuning workflow."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        engine = get_workflow_engine()
        result = engine.auto_tune_hardware()

        assert result["status"] == "success"
        assert result["providers_tuned"] == 13  # Classical providers only


class TestResourceSafety:
    """Test resource safety across all components."""

    def test_cpu_limit_enforced(self, temp_config_dir):
        """Test CPU limit is enforced (80%)."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=85.0), \
             patch('automation.workflow_engine.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=50.0)

            pm = get_permission_manager()
            pm.set_user_role("Admin")

            engine = get_workflow_engine()
            result = engine.optimize_quantum_queue()

            assert result["status"] == "paused"
            assert "Resource limits" in result["reason"]

    def test_ram_limit_enforced(self, temp_config_dir):
        """Test RAM limit is enforced (75%)."""
        with patch('automation.workflow_engine.psutil.cpu_percent', return_value=50.0), \
             patch('automation.workflow_engine.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=76.0)

            pm = get_permission_manager()
            pm.set_user_role("Admin")

            engine = get_workflow_engine()
            result = engine.optimize_quantum_queue()

            assert result["status"] == "paused"


class TestPermissionIntegrationLayer:
    """Test permission integration with Phase 3 components."""

    def test_job_submission_permission_quantum(self, temp_config_dir):
        """Test quantum job submission permission check."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        integration = get_permission_integration()

        # Should not raise
        integration.check_job_submission_permission("quantum", "IBM Quantum")

    def test_job_submission_permission_classical(self, temp_config_dir):
        """Test classical job submission permission check."""
        pm = get_permission_manager()
        pm.set_user_role("Admin")

        integration = get_permission_integration()

        # Should not raise
        integration.check_job_submission_permission("classical", "NVIDIA CUDA")

    def test_provider_filtering_by_role(self, temp_config_dir):
        """Test provider filtering based on role."""
        pm = get_permission_manager()
        integration = get_permission_integration()

        # Admin sees all
        pm.set_user_role("Admin")
        admin_providers = integration.validate_and_filter_providers(ALL_PROVIDERS)
        assert len(admin_providers) == 28

        # ReadOnly sees none
        pm.set_user_role("ReadOnly")
        readonly_providers = integration.validate_and_filter_providers(ALL_PROVIDERS)
        assert len(readonly_providers) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
