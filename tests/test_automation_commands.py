"""
Unit tests for Automation Commands.

Tests terminal command handlers for automation and scheduler.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 8
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from automation.commands import (
    handle_automation_command,
    handle_scheduler_command,
)


@pytest.fixture
def mock_write():
    """Create a mock write function that captures output."""
    output = StringIO()

    def write_fn(text):
        output.write(text)

    write_fn.output = output
    return write_fn


@pytest.fixture
def mock_workflow_engine():
    """Mock workflow engine."""
    with patch('automation.workflow_engine.get_workflow_engine') as mock:
        instance = MagicMock()
        instance.user_consent_to_terminate = {}
        instance.optimize_quantum_queue.return_value = {"status": "success", "providers_checked": 15}
        instance.optimize_classical_queue.return_value = {"status": "success", "providers_checked": 13}
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_scheduler():
    """Mock task scheduler."""
    with patch('automation.scheduler.get_scheduler') as mock:
        instance = MagicMock()
        instance.is_running.return_value = True
        instance.get_all_tasks.return_value = []
        instance.get_active_tasks.return_value = []
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_permission_manager():
    """Mock permission manager."""
    with patch('permissions.permission_manager.get_permission_manager') as mock:
        instance = MagicMock()
        instance.config = {
            "automation_enabled": True,
            "automated_workflows": {
                "optimize_quantum_queue": True,
                "optimize_classical_queue": True,
                "check_credential_expiry": False,
                "generate_resource_report": True,
                "monitor_provider_health": True,
                "auto_tune_hardware": False
            }
        }
        mock.return_value = instance
        yield instance


class TestAutomationCommand:
    """Test 'automation' command."""

    def test_no_args_shows_summary(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test that no arguments shows automation summary."""
        handle_automation_command([], mock_write)

        output = mock_write.output.getvalue()
        assert "AUTOMATION STATUS" in output
        assert "WORKFLOWS" in output

    def test_start_automation(self, mock_write, mock_scheduler, mock_permission_manager):
        """Test starting automation."""
        handle_automation_command(["start"], mock_write)

        mock_scheduler.start.assert_called_once()
        output = mock_write.output.getvalue()
        assert "Automation started" in output

    def test_start_automation_disabled(self, mock_write, mock_scheduler, mock_permission_manager):
        """Test starting automation when disabled in config."""
        mock_permission_manager.config["automation_enabled"] = False

        handle_automation_command(["start"], mock_write)

        output = mock_write.output.getvalue()
        assert "disabled" in output

    def test_stop_automation(self, mock_write, mock_scheduler, mock_permission_manager):
        """Test stopping automation."""
        handle_automation_command(["stop"], mock_write)

        mock_scheduler.stop.assert_called_once()
        output = mock_write.output.getvalue()
        assert "stopped" in output

    def test_automation_status(self, mock_write, mock_scheduler, mock_permission_manager):
        """Test showing workflow execution status."""
        # Create mock task
        task = MagicMock()
        task.task_id = "test_task"
        task.status.value = "running"
        task.schedule_type.value = "recurring"
        task.run_count = 5
        task.error_count = 0
        task.last_run = "2026-02-10T10:00:00"

        mock_scheduler.get_active_tasks.return_value = [task]

        handle_automation_command(["status"], mock_write)

        output = mock_write.output.getvalue()
        assert "WORKFLOW EXECUTION STATUS" in output
        assert "test_task" in output

    def test_run_workflow_quantum(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test running quantum queue workflow."""
        handle_automation_command(["run", "quantum_queue"], mock_write)

        mock_workflow_engine.optimize_quantum_queue.assert_called_once()
        output = mock_write.output.getvalue()
        assert "completed successfully" in output

    def test_run_workflow_classical(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test running classical queue workflow."""
        handle_automation_command(["run", "classical_queue"], mock_write)

        mock_workflow_engine.optimize_classical_queue.assert_called_once()
        output = mock_write.output.getvalue()
        assert "completed successfully" in output

    def test_run_workflow_denied(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test running workflow with permission denied."""
        mock_workflow_engine.optimize_quantum_queue.return_value = {
            "status": "denied",
            "reason": "Permission denied"
        }

        handle_automation_command(["run", "quantum_queue"], mock_write)

        output = mock_write.output.getvalue()
        assert "Permission denied" in output

    def test_run_workflow_paused(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test running workflow that gets paused."""
        mock_workflow_engine.optimize_quantum_queue.return_value = {
            "status": "paused",
            "reason": "Resource limits"
        }

        handle_automation_command(["run", "quantum_queue"], mock_write)

        output = mock_write.output.getvalue()
        assert "paused" in output

    def test_run_workflow_no_arg(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test running workflow without argument."""
        handle_automation_command(["run"], mock_write)

        output = mock_write.output.getvalue()
        assert "Usage" in output

    def test_run_workflow_unknown(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test running unknown workflow."""
        handle_automation_command(["run", "unknown_workflow"], mock_write)

        output = mock_write.output.getvalue()
        assert "Unknown workflow" in output

    def test_grant_consent(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test granting termination consent."""
        handle_automation_command(["consent", "quantum_queue"], mock_write)

        mock_workflow_engine.grant_termination_consent.assert_called_once_with("quantum_queue")
        output = mock_write.output.getvalue()
        assert "consent granted" in output

    def test_grant_consent_no_arg(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test granting consent without argument."""
        handle_automation_command(["consent"], mock_write)

        output = mock_write.output.getvalue()
        assert "Usage" in output

    def test_revoke_consent(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test revoking termination consent."""
        handle_automation_command(["revoke", "quantum_queue"], mock_write)

        mock_workflow_engine.revoke_termination_consent.assert_called_once_with("quantum_queue")
        output = mock_write.output.getvalue()
        assert "consent revoked" in output

    def test_unknown_subcommand(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test unknown subcommand shows usage."""
        handle_automation_command(["unknown"], mock_write)

        output = mock_write.output.getvalue()
        assert "AUTOMATION COMMANDS" in output


class TestSchedulerCommand:
    """Test 'scheduler' command."""

    def test_no_args_shows_summary(self, mock_write, mock_scheduler):
        """Test that no arguments shows scheduler summary."""
        handle_scheduler_command([], mock_write)

        output = mock_write.output.getvalue()
        assert "TASK SCHEDULER STATUS" in output

    def test_list_tasks(self, mock_write, mock_scheduler):
        """Test listing scheduled tasks."""
        # Create mock task
        task = MagicMock()
        task.task_id = "test_task"
        task.status.value = "running"
        task.schedule_type.value = "recurring"
        task.interval_seconds = 300
        task.run_count = 10
        task.target_providers = ["IBM Quantum", "AWS Braket"]

        mock_scheduler.get_all_tasks.return_value = [task]

        handle_scheduler_command(["tasks"], mock_write)

        output = mock_write.output.getvalue()
        assert "SCHEDULED TASKS" in output
        assert "test_task" in output

    def test_list_tasks_empty(self, mock_write, mock_scheduler):
        """Test listing tasks when none exist."""
        mock_scheduler.get_all_tasks.return_value = []

        handle_scheduler_command(["tasks"], mock_write)

        output = mock_write.output.getvalue()
        assert "No scheduled tasks" in output

    def test_pause_task(self, mock_write, mock_scheduler):
        """Test pausing a task."""
        handle_scheduler_command(["pause", "test_task"], mock_write)

        mock_scheduler.pause_task.assert_called_once_with("test_task")
        output = mock_write.output.getvalue()
        assert "paused" in output

    def test_pause_task_no_arg(self, mock_write, mock_scheduler):
        """Test pausing task without argument."""
        handle_scheduler_command(["pause"], mock_write)

        output = mock_write.output.getvalue()
        assert "Usage" in output

    def test_pause_task_not_found(self, mock_write, mock_scheduler):
        """Test pausing non-existent task."""
        mock_scheduler.pause_task.side_effect = KeyError("Task not found")

        handle_scheduler_command(["pause", "nonexistent"], mock_write)

        output = mock_write.output.getvalue()
        assert "not found" in output

    def test_resume_task(self, mock_write, mock_scheduler):
        """Test resuming a task."""
        handle_scheduler_command(["resume", "test_task"], mock_write)

        mock_scheduler.resume_task.assert_called_once_with("test_task")
        output = mock_write.output.getvalue()
        assert "resumed" in output

    def test_resume_task_no_arg(self, mock_write, mock_scheduler):
        """Test resuming task without argument."""
        handle_scheduler_command(["resume"], mock_write)

        output = mock_write.output.getvalue()
        assert "Usage" in output

    def test_stop_scheduler(self, mock_write, mock_scheduler):
        """Test stopping scheduler."""
        handle_scheduler_command(["stop"], mock_write)

        mock_scheduler.stop.assert_called_once()
        output = mock_write.output.getvalue()
        assert "stopped" in output

    def test_unknown_subcommand(self, mock_write, mock_scheduler):
        """Test unknown subcommand shows usage."""
        handle_scheduler_command(["unknown"], mock_write)

        output = mock_write.output.getvalue()
        assert "SCHEDULER COMMANDS" in output


class TestErrorHandling:
    """Test error handling in commands."""

    def test_automation_start_error(self, mock_write, mock_scheduler, mock_permission_manager):
        """Test error handling when starting automation."""
        mock_scheduler.start.side_effect = Exception("Start error")

        handle_automation_command(["start"], mock_write)

        output = mock_write.output.getvalue()
        assert "Error" in output

    def test_automation_status_error(self, mock_write, mock_scheduler, mock_permission_manager):
        """Test error handling when getting status."""
        mock_scheduler.get_active_tasks.side_effect = Exception("Status error")

        handle_automation_command(["status"], mock_write)

        output = mock_write.output.getvalue()
        assert "Error" in output

    def test_run_workflow_error(self, mock_write, mock_workflow_engine, mock_permission_manager):
        """Test error handling when running workflow."""
        mock_workflow_engine.optimize_quantum_queue.side_effect = Exception("Workflow error")

        handle_automation_command(["run", "quantum_queue"], mock_write)

        output = mock_write.output.getvalue()
        assert "Error" in output

    def test_scheduler_tasks_error(self, mock_write, mock_scheduler):
        """Test error handling when listing tasks."""
        mock_scheduler.get_all_tasks.side_effect = Exception("List error")

        handle_scheduler_command(["tasks"], mock_write)

        output = mock_write.output.getvalue()
        assert "Error" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
