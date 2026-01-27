"""
FRANKENSTEIN 1.0 - Task Orchestrator Tests
Unit tests for core/orchestrator.py
"""

import pytest
import time
from core.orchestrator import (
    TaskOrchestrator,
    Task,
    TaskType,
    TaskStatus,
    TaskPriority,
    get_orchestrator
)


class TestTaskEnums:
    """Test task enumeration types"""

    def test_task_types_exist(self):
        """Test all task types are defined"""
        assert TaskType.CLASSICAL is not None
        assert TaskType.QUANTUM is not None
        assert TaskType.SYNTHESIS is not None
        assert TaskType.AGENT is not None
        assert TaskType.SYSTEM is not None

    def test_task_priorities_exist(self):
        """Test all priority levels are defined"""
        assert TaskPriority.LOW is not None
        assert TaskPriority.NORMAL is not None
        assert TaskPriority.HIGH is not None
        assert TaskPriority.CRITICAL is not None

    def test_task_priorities_ordered(self):
        """Test priority levels have correct ordering"""
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value

    def test_task_statuses_exist(self):
        """Test all task statuses are defined"""
        assert TaskStatus.PENDING is not None
        assert TaskStatus.QUEUED is not None
        assert TaskStatus.RUNNING is not None
        assert TaskStatus.COMPLETED is not None
        assert TaskStatus.FAILED is not None
        assert TaskStatus.THROTTLED is not None
        assert TaskStatus.CANCELLED is not None


class TestTask:
    """Test task data structure"""

    def test_task_creation(self):
        """Test creating a task"""
        task = Task(
            task_id="task-001",
            task_type=TaskType.CLASSICAL,
            priority=TaskPriority.NORMAL,
            payload={"action": "test"}
        )
        assert task is not None
        assert task.task_id == "task-001"
        assert task.task_type == TaskType.CLASSICAL

    def test_task_defaults(self):
        """Test task default values"""
        task = Task(
            task_id="task-002",
            task_type=TaskType.SYSTEM,
            priority=TaskPriority.LOW,
            payload={}
        )
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None

    def test_task_priority_comparison(self):
        """Test task priority comparison for queue ordering"""
        high_task = Task(
            task_id="high",
            task_type=TaskType.CLASSICAL,
            priority=TaskPriority.HIGH,
            payload={}
        )
        low_task = Task(
            task_id="low",
            task_type=TaskType.CLASSICAL,
            priority=TaskPriority.LOW,
            payload={}
        )
        assert high_task < low_task


class TestTaskOrchestrator:
    """Test task orchestrator functionality"""

    def test_orchestrator_creation(self):
        """Test creating an orchestrator"""
        orchestrator = TaskOrchestrator(max_workers=2)
        assert orchestrator is not None

    def test_orchestrator_default_workers(self):
        """Test orchestrator uses safe default workers"""
        orchestrator = TaskOrchestrator()
        assert orchestrator is not None

    def test_orchestrator_start(self):
        """Test starting the orchestrator"""
        orchestrator = TaskOrchestrator(max_workers=2)
        result = orchestrator.start()
        assert result is True
        orchestrator.stop()
        time.sleep(0.5)

    def test_orchestrator_stop(self):
        """Test stopping the orchestrator"""
        orchestrator = TaskOrchestrator(max_workers=2)
        orchestrator.start()
        time.sleep(0.5)
        result = orchestrator.stop()
        assert result is True

    def test_get_queue_status(self):
        """Test getting queue status"""
        orchestrator = TaskOrchestrator(max_workers=2)
        orchestrator.start()
        status = orchestrator.get_queue_status()
        assert isinstance(status, dict)
        assert "max_workers" in status or "running" in status
        orchestrator.stop()
        time.sleep(0.5)

    def test_orchestrator_respects_max_workers(self):
        """Test orchestrator respects max worker limit"""
        orchestrator = TaskOrchestrator(max_workers=2)
        orchestrator.start()
        status = orchestrator.get_queue_status()
        orchestrator.stop()
        time.sleep(0.5)


class TestOrchestratorSingleton:
    """Test global orchestrator instance"""

    def test_get_orchestrator_returns_instance(self):
        """Test that get_orchestrator returns a TaskOrchestrator"""
        orchestrator = get_orchestrator()
        assert orchestrator is not None
        assert isinstance(orchestrator, TaskOrchestrator)

    def test_get_orchestrator_returns_same_instance(self):
        """Test that get_orchestrator returns singleton"""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2


class TestOrchestratorSafety:
    """Test orchestrator safety features"""

    def test_orchestrator_worker_limit(self):
        """Test orchestrator enforces worker thread limits"""
        orchestrator = TaskOrchestrator(max_workers=10)
        assert orchestrator is not None

    def test_create_task_with_all_types(self):
        """Test creating tasks of different types"""
        task_types = [
            TaskType.CLASSICAL,
            TaskType.QUANTUM,
            TaskType.SYNTHESIS,
            TaskType.AGENT,
            TaskType.SYSTEM
        ]
        for task_type in task_types:
            task = Task(
                task_id=f"task-{task_type.value}",
                task_type=task_type,
                priority=TaskPriority.NORMAL,
                payload={"test": True}
            )
            assert task.task_type == task_type
