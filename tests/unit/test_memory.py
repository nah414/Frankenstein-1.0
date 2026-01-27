"""
FRANKENSTEIN 1.0 - Memory System Tests
Unit tests for core/memory.py
"""

import pytest
import time
import tempfile
from pathlib import Path
from core.memory import (
    MemorySystem,
    SessionState,
    TaskRecord,
    get_memory
)


class TestTaskRecord:
    """Test task record data structure"""

    def test_task_record_creation(self):
        """Test creating a task record"""
        record = TaskRecord(
            task_id="test-001",
            task_type="classical",
            started_at=time.time(),
            completed_at=time.time() + 5.0,
            duration_sec=5.0,
            success=True,
            input_summary="Test input",
            output_summary="Test output"
        )
        assert record is not None
        assert record.task_id == "test-001"
        assert record.success is True

    def test_task_record_with_error(self):
        """Test task record with error"""
        record = TaskRecord(
            task_id="test-002",
            task_type="quantum",
            started_at=time.time(),
            completed_at=time.time() + 2.0,
            duration_sec=2.0,
            success=False,
            input_summary="Test",
            output_summary="Failed",
            error="Test error message"
        )
        assert record.success is False
        assert record.error == "Test error message"


class TestSessionState:
    """Test session state data structure"""

    def test_session_state_creation(self):
        """Test creating a session state"""
        session = SessionState(
            session_id="session-001",
            started_at=time.time()
        )
        assert session is not None
        assert session.session_id == "session-001"

    def test_session_state_defaults(self):
        """Test session state default values"""
        session = SessionState(
            session_id="session-002",
            started_at=time.time()
        )
        assert session.task_count == 0
        assert session.successful_tasks == 0
        assert session.failed_tasks == 0
        assert session.total_compute_time_sec == 0.0
        assert session.active_task_id is None

    def test_session_state_with_data(self):
        """Test session state with actual data"""
        session = SessionState(
            session_id="session-003",
            started_at=time.time(),
            task_count=10,
            successful_tasks=8,
            failed_tasks=2,
            total_compute_time_sec=150.5
        )
        assert session.task_count == 10
        assert session.successful_tasks == 8
        assert session.failed_tasks == 2


class TestMemorySystem:
    """Test memory system functionality"""

    def test_memory_system_creation(self):
        """Test creating a memory system"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemorySystem(base_path=Path(tmpdir))
            assert memory is not None
            assert memory.base_path == Path(tmpdir)

    def test_memory_system_default_path(self):
        """Test memory system uses default path"""
        memory = MemorySystem()
        assert memory.base_path == Path.home() / ".frankenstein"

    def test_memory_system_paths_defined(self):
        """Test that all required paths are defined"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemorySystem(base_path=Path(tmpdir))
            assert memory.session_file is not None
            assert memory.history_dir is not None
            assert memory.learning_dir is not None
            assert memory.cache_dir is not None

    def test_memory_system_initialize(self):
        """Test initializing memory system"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemorySystem(base_path=Path(tmpdir))
            result = memory.initialize()
            assert result is True
            assert memory._initialized is True

    def test_memory_directories_created(self):
        """Test that initialize creates required directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemorySystem(base_path=Path(tmpdir))
            memory.initialize()
            assert Path(tmpdir).exists()
            assert memory.history_dir.exists()
            assert memory.learning_dir.exists()
            assert memory.cache_dir.exists()

    def test_get_session_stats(self):
        """Test getting session statistics"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemorySystem(base_path=Path(tmpdir))
            memory.initialize()
            stats = memory.get_session_stats()
            assert isinstance(stats, dict)
            assert "session_id" in stats

    def test_new_session_creation(self):
        """Test creating a new session"""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemorySystem(base_path=Path(tmpdir))
            memory.initialize()
            session = memory._session
            assert session is not None
            assert session.task_count == 0


class TestMemorySingleton:
    """Test global memory instance"""

    def test_get_memory_returns_instance(self):
        """Test that get_memory returns a MemorySystem"""
        memory = get_memory()
        assert memory is not None
        assert isinstance(memory, MemorySystem)

    def test_get_memory_returns_same_instance(self):
        """Test that get_memory returns singleton"""
        mem1 = get_memory()
        mem2 = get_memory()
        assert mem1 is mem2


class TestMemoryLimits:
    """Test memory system respects limits"""

    def test_max_history_limit_set(self):
        """Test that max history limit is defined"""
        memory = MemorySystem()
        assert memory._max_history == 1000

    def test_task_history_initialized(self):
        """Test that task history list is initialized"""
        memory = MemorySystem()
        assert memory._task_history is not None
        assert isinstance(memory._task_history, list)
