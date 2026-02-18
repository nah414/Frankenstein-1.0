"""
Unit tests for Task Scheduler.

Tests scheduling, task execution, resource checks, and provider tracking.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 4
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from automation.scheduler import (
    TaskScheduler,
    ScheduledTask,
    ScheduleType,
    TaskStatus,
    get_scheduler,
)


@pytest.fixture
def fresh_scheduler():
    """Create a fresh TaskScheduler instance for each test."""
    # Reset singleton
    TaskScheduler._instance = None
    TaskScheduler._initialized = False

    scheduler = TaskScheduler()
    yield scheduler

    # Stop scheduler if running
    if scheduler.is_running():
        scheduler.stop()

    # Cleanup
    TaskScheduler._instance = None
    TaskScheduler._initialized = False


@pytest.fixture
def mock_resources():
    """Mock psutil resource checks to avoid delays."""
    with patch('automation.scheduler.psutil.cpu_percent', return_value=50.0), \
         patch('automation.scheduler.psutil.virtual_memory') as mock_mem:
        mock_mem.return_value = MagicMock(percent=50.0)
        yield


class TestSingletonBehavior:
    """Test singleton pattern implementation."""

    def test_singleton_instance(self, fresh_scheduler):
        """Verify only one instance is created."""
        scheduler1 = fresh_scheduler
        scheduler2 = TaskScheduler()
        assert scheduler1 is scheduler2

    def test_get_scheduler(self, fresh_scheduler):
        """Test helper function returns singleton."""
        scheduler1 = fresh_scheduler
        scheduler2 = get_scheduler()
        assert scheduler1 is scheduler2


class TestTaskRegistration:
    """Test task registration."""

    def test_register_recurring_task(self, fresh_scheduler, mock_resources):
        """Test registering a recurring task."""
        task_func = Mock()

        task = fresh_scheduler.register_task(
            task_id="test_task",
            task_func=task_func,
            schedule_type="recurring",
            interval_seconds=10
        )

        assert task.task_id == "test_task"
        assert task.schedule_type == ScheduleType.RECURRING
        assert task.interval_seconds == 10
        assert task.status == TaskStatus.PENDING

    def test_register_one_time_task(self, fresh_scheduler, mock_resources):
        """Test registering a one-time task."""
        task_func = Mock()

        task = fresh_scheduler.register_task(
            task_id="one_time_task",
            task_func=task_func,
            schedule_type="one_time"
        )

        assert task.schedule_type == ScheduleType.ONE_TIME
        assert task.status == TaskStatus.PENDING

    def test_register_event_triggered_task(self, fresh_scheduler, mock_resources):
        """Test registering an event-triggered task."""
        task_func = Mock()
        trigger = Mock(return_value=False)

        task = fresh_scheduler.register_task(
            task_id="event_task",
            task_func=task_func,
            schedule_type="event_triggered",
            trigger_condition=trigger
        )

        assert task.schedule_type == ScheduleType.EVENT_TRIGGERED
        assert task.trigger_condition == trigger

    def test_register_task_with_providers(self, fresh_scheduler, mock_resources):
        """Test registering task with target providers."""
        task_func = Mock()

        task = fresh_scheduler.register_task(
            task_id="provider_task",
            task_func=task_func,
            schedule_type="recurring",
            interval_seconds=10,
            target_providers=["IBM Quantum", "AWS Braket"]
        )

        assert len(task.target_providers) == 2
        assert "IBM Quantum" in task.target_providers

    def test_register_duplicate_task_id(self, fresh_scheduler, mock_resources):
        """Test that duplicate task IDs raise ValueError."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="duplicate",
            task_func=task_func,
            schedule_type="one_time"
        )

        with pytest.raises(ValueError, match="already exists"):
            fresh_scheduler.register_task(
                task_id="duplicate",
                task_func=task_func,
                schedule_type="one_time"
            )

    def test_register_invalid_schedule_type(self, fresh_scheduler, mock_resources):
        """Test that invalid schedule type raises ValueError."""
        task_func = Mock()

        with pytest.raises(ValueError, match="Invalid schedule_type"):
            fresh_scheduler.register_task(
                task_id="invalid",
                task_func=task_func,
                schedule_type="invalid_type"
            )

    def test_recurring_task_requires_interval(self, fresh_scheduler, mock_resources):
        """Test that recurring tasks require interval_seconds."""
        task_func = Mock()

        with pytest.raises(ValueError, match="require interval_seconds"):
            fresh_scheduler.register_task(
                task_id="no_interval",
                task_func=task_func,
                schedule_type="recurring"
            )

    def test_event_task_requires_trigger(self, fresh_scheduler, mock_resources):
        """Test that event-triggered tasks require trigger_condition."""
        task_func = Mock()

        with pytest.raises(ValueError, match="require trigger_condition"):
            fresh_scheduler.register_task(
                task_id="no_trigger",
                task_func=task_func,
                schedule_type="event_triggered"
            )


class TestSchedulerStartStop:
    """Test scheduler start/stop functionality."""

    def test_start_scheduler(self, fresh_scheduler, mock_resources):
        """Test starting the scheduler."""
        assert not fresh_scheduler.is_running()

        fresh_scheduler.start()

        assert fresh_scheduler.is_running()

    def test_stop_scheduler(self, fresh_scheduler, mock_resources):
        """Test stopping the scheduler."""
        fresh_scheduler.start()
        assert fresh_scheduler.is_running()

        fresh_scheduler.stop()

        assert not fresh_scheduler.is_running()

    def test_double_start_no_error(self, fresh_scheduler, mock_resources):
        """Test that starting twice doesn't cause errors."""
        fresh_scheduler.start()
        fresh_scheduler.start()  # Should be no-op

        assert fresh_scheduler.is_running()

    def test_stop_when_not_running(self, fresh_scheduler, mock_resources):
        """Test that stopping when not running doesn't cause errors."""
        fresh_scheduler.stop()  # Should be no-op
        assert not fresh_scheduler.is_running()


class TestTaskExecution:
    """Test task execution."""

    def test_one_time_task_executes(self, fresh_scheduler, mock_resources):
        """Test that one-time tasks execute."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="execute_once",
            task_func=task_func,
            schedule_type="one_time"
        )

        fresh_scheduler.start()
        time.sleep(0.5)  # Give task time to execute

        task_func.assert_called_once()

    def test_recurring_task_executes_multiple_times(self, fresh_scheduler, mock_resources):
        """Test that recurring tasks execute multiple times."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="recurring",
            task_func=task_func,
            schedule_type="recurring",
            interval_seconds=1  # 1 second interval
        )

        fresh_scheduler.start()
        time.sleep(2.5)  # Wait for ~2 executions

        # Should have executed at least twice
        assert task_func.call_count >= 2

    def test_task_run_count_increments(self, fresh_scheduler, mock_resources):
        """Test that task run count increments."""
        task_func = Mock()

        task = fresh_scheduler.register_task(
            task_id="count_test",
            task_func=task_func,
            schedule_type="one_time"
        )

        fresh_scheduler.start()
        time.sleep(0.5)

        assert task.run_count >= 1

    def test_task_error_handling(self, fresh_scheduler, mock_resources):
        """Test that task errors are caught and recorded."""
        task_func = Mock(side_effect=Exception("Test error"))

        task = fresh_scheduler.register_task(
            task_id="error_task",
            task_func=task_func,
            schedule_type="one_time"
        )

        fresh_scheduler.start()
        time.sleep(0.5)

        assert task.status == TaskStatus.FAILED
        assert task.error_count >= 1
        assert "Test error" in task.last_error


class TestTaskPauseResume:
    """Test task pause/resume functionality."""

    def test_pause_task(self, fresh_scheduler, mock_resources):
        """Test pausing a task."""
        task_func = Mock()

        task = fresh_scheduler.register_task(
            task_id="pause_test",
            task_func=task_func,
            schedule_type="recurring",
            interval_seconds=1
        )

        fresh_scheduler.start()
        fresh_scheduler.pause_task("pause_test")

        assert task.status == TaskStatus.PAUSED

    def test_resume_task(self, fresh_scheduler, mock_resources):
        """Test resuming a paused task."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="resume_test",
            task_func=task_func,
            schedule_type="recurring",
            interval_seconds=1
        )

        fresh_scheduler.start()
        fresh_scheduler.pause_task("resume_test")
        fresh_scheduler.resume_task("resume_test")

        task = fresh_scheduler.get_task("resume_test")
        assert task.status == TaskStatus.PENDING

    def test_pause_nonexistent_task(self, fresh_scheduler, mock_resources):
        """Test that pausing nonexistent task raises KeyError."""
        with pytest.raises(KeyError):
            fresh_scheduler.pause_task("nonexistent")

    def test_resume_nonexistent_task(self, fresh_scheduler, mock_resources):
        """Test that resuming nonexistent task raises KeyError."""
        with pytest.raises(KeyError):
            fresh_scheduler.resume_task("nonexistent")


class TestResourceChecks:
    """Test resource safety checks."""

    def test_task_skipped_high_cpu(self, fresh_scheduler):
        """Test that tasks are skipped when CPU is high."""
        task_func = Mock()

        with patch('automation.scheduler.psutil.cpu_percent', return_value=85.0), \
             patch('automation.scheduler.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=50.0)

            task = fresh_scheduler.register_task(
                task_id="high_cpu",
                task_func=task_func,
                schedule_type="one_time"
            )

            fresh_scheduler.start()
            time.sleep(0.5)

            # Task should be skipped
            assert task.status == TaskStatus.SKIPPED
            task_func.assert_not_called()

    def test_task_skipped_high_ram(self, fresh_scheduler):
        """Test that tasks are skipped when RAM is high."""
        task_func = Mock()

        with patch('automation.scheduler.psutil.cpu_percent', return_value=50.0), \
             patch('automation.scheduler.psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(percent=80.0)

            task = fresh_scheduler.register_task(
                task_id="high_ram",
                task_func=task_func,
                schedule_type="one_time"
            )

            fresh_scheduler.start()
            time.sleep(0.5)

            # Task should be skipped
            assert task.status == TaskStatus.SKIPPED
            task_func.assert_not_called()


class TestConcurrentTaskLimit:
    """Test maximum concurrent task limit."""

    def test_concurrent_task_limit_enforced(self, fresh_scheduler, mock_resources):
        """Test that max 5 concurrent tasks limit is enforced."""
        # Create slow tasks that will run concurrently
        def slow_task():
            time.sleep(2)

        # Register 10 tasks
        for i in range(10):
            fresh_scheduler.register_task(
                task_id=f"concurrent_{i}",
                task_func=slow_task,
                schedule_type="one_time"
            )

        fresh_scheduler.start()
        time.sleep(0.3)  # Let tasks start

        # Check running tasks
        running_count = len(fresh_scheduler._running_tasks)

        # Should not exceed MAX_CONCURRENT_TASKS (5)
        assert running_count <= TaskScheduler.MAX_CONCURRENT_TASKS


class TestTaskRetrieval:
    """Test task retrieval methods."""

    def test_get_active_tasks(self, fresh_scheduler, mock_resources):
        """Test retrieving active tasks."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="active1",
            task_func=task_func,
            schedule_type="recurring",
            interval_seconds=10
        )
        fresh_scheduler.register_task(
            task_id="active2",
            task_func=task_func,
            schedule_type="one_time"
        )

        active_tasks = fresh_scheduler.get_active_tasks()
        assert len(active_tasks) == 2

    def test_get_tasks_by_provider(self, fresh_scheduler, mock_resources):
        """Test retrieving tasks by provider."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="ibm_task",
            task_func=task_func,
            schedule_type="one_time",
            target_providers=["IBM Quantum", "AWS Braket"]
        )
        fresh_scheduler.register_task(
            task_id="nvidia_task",
            task_func=task_func,
            schedule_type="one_time",
            target_providers=["NVIDIA CUDA"]
        )

        ibm_tasks = fresh_scheduler.get_tasks_by_provider("IBM Quantum")
        assert len(ibm_tasks) == 1
        assert ibm_tasks[0].task_id == "ibm_task"

    def test_get_task_by_id(self, fresh_scheduler, mock_resources):
        """Test retrieving task by ID."""
        task_func = Mock()

        fresh_scheduler.register_task(
            task_id="specific_task",
            task_func=task_func,
            schedule_type="one_time"
        )

        task = fresh_scheduler.get_task("specific_task")
        assert task is not None
        assert task.task_id == "specific_task"

    def test_get_nonexistent_task(self, fresh_scheduler, mock_resources):
        """Test that getting nonexistent task returns None."""
        task = fresh_scheduler.get_task("nonexistent")
        assert task is None

    def test_get_all_tasks(self, fresh_scheduler, mock_resources):
        """Test retrieving all tasks."""
        task_func = Mock()

        for i in range(3):
            fresh_scheduler.register_task(
                task_id=f"task_{i}",
                task_func=task_func,
                schedule_type="one_time"
            )

        all_tasks = fresh_scheduler.get_all_tasks()
        assert len(all_tasks) == 3


class TestEventTriggeredTasks:
    """Test event-triggered task functionality."""

    def test_event_triggered_task_executes(self, fresh_scheduler, mock_resources):
        """Test that event-triggered tasks execute when condition is met."""
        task_func = Mock()
        trigger_called = {"count": 0}

        def trigger():
            trigger_called["count"] += 1
            return trigger_called["count"] >= 2  # Trigger on second check

        fresh_scheduler.register_task(
            task_id="event_task",
            task_func=task_func,
            schedule_type="event_triggered",
            trigger_condition=trigger
        )

        fresh_scheduler.start()
        time.sleep(12)  # Wait for event checks (every 5 seconds)

        # Task should have executed
        task_func.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
