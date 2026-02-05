"""
FRANKENSTEIN 1.0 - Memory System
Phase 1: Core Engine

Purpose: Session state, task history, and persistent learning
Hardware: Dell i3-8xxx with 117GB storage (use ~10GB max)
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class TaskRecord:
    """Record of a completed task"""
    task_id: str
    task_type: str
    started_at: float
    completed_at: float
    duration_sec: float
    success: bool
    input_summary: str
    output_summary: str
    resources_used: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class SessionState:
    """Current session state"""
    session_id: str
    started_at: float
    task_count: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_compute_time_sec: float = 0.0
    active_task_id: Optional[str] = None


class MemorySystem:
    """
    FRANKENSTEIN's memory - persists across restarts.

    Storage layout (within 10GB limit):
    - ~/.frankenstein/session.json     # Current session
    - ~/.frankenstein/history/         # Task history (rolling 1000)
    - ~/.frankenstein/learning/        # Learned patterns
    - ~/.frankenstein/cache/           # Temporary cache
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize memory system.

        Args:
            base_path: Override default ~/.frankenstein path
        """
        self.base_path = base_path or Path.home() / ".frankenstein"
        self.session_file = self.base_path / "session.json"
        self.history_dir = self.base_path / "history"
        self.learning_dir = self.base_path / "learning"
        self.cache_dir = self.base_path / "cache"

        self._lock = threading.Lock()
        self._session: Optional[SessionState] = None
        self._task_history: List[TaskRecord] = []
        self._max_history = 500  # OPTIMIZED: Reduced from 1000 for tier1 RAM limits  # Rolling limit

        # Initialize on first access
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize the memory system - create directories, load state.

        Returns:
            True if initialized successfully
        """
        if self._initialized:
            return True

        try:
            # Create directories
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.history_dir.mkdir(exist_ok=True)
            self.learning_dir.mkdir(exist_ok=True)
            self.cache_dir.mkdir(exist_ok=True)

            # Load or create session
            self._load_or_create_session()

            # Load recent history
            self._load_history()

            self._initialized = True
            return True

        except Exception as e:
            print(f"Memory initialization error: {e}")
            return False

    def _load_or_create_session(self):
        """Load existing session or create new one"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self._session = SessionState(**data)
                return
            except Exception:
                pass  # Create new session

        # Create new session
        self._session = SessionState(
            session_id=f"session_{int(time.time())}",
            started_at=time.time()
        )
        self._save_session()

    def _save_session(self):
        """Persist session state to disk"""
        if self._session:
            with open(self.session_file, 'w') as f:
                json.dump(asdict(self._session), f, indent=2)

    def _load_history(self):
        """Load task history from disk"""
        history_file = self.history_dir / "tasks.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self._task_history = [TaskRecord(**t) for t in data[-self._max_history:]]
            except Exception as e:
                print(f"History load error: {e}")
                self._task_history = []

    def _save_history(self):
        """Persist task history to disk"""
        history_file = self.history_dir / "tasks.json"
        with open(history_file, 'w') as f:
            json.dump([asdict(t) for t in self._task_history[-self._max_history:]], f, indent=2)

    def record_task_start(self, task_id: str, task_type: str) -> None:
        """Record that a task has started"""
        with self._lock:
            if self._session:
                self._session.active_task_id = task_id
                self._save_session()

    def record_task_complete(
        self,
        task_id: str,
        task_type: str,
        started_at: float,
        success: bool,
        input_summary: str = "",
        output_summary: str = "",
        resources_used: Optional[Dict[str, float]] = None,
        error: Optional[str] = None
    ) -> TaskRecord:
        """
        Record a completed task.

        Returns:
            The created TaskRecord
        """
        completed_at = time.time()
        duration = completed_at - started_at

        record = TaskRecord(
            task_id=task_id,
            task_type=task_type,
            started_at=started_at,
            completed_at=completed_at,
            duration_sec=duration,
            success=success,
            input_summary=input_summary[:200],  # Truncate
            output_summary=output_summary[:200],
            resources_used=resources_used or {},
            error=error
        )

        with self._lock:
            self._task_history.append(record)

            # Update session stats
            if self._session:
                self._session.task_count += 1
                self._session.total_compute_time_sec += duration
                if success:
                    self._session.successful_tasks += 1
                else:
                    self._session.failed_tasks += 1
                self._session.active_task_id = None
                self._save_session()

            # Save history periodically (every 10 tasks)
            if len(self._task_history) % 10 == 0:
                self._save_history()

        return record

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        if not self._session:
            return {"error": "No active session"}

        uptime = time.time() - self._session.started_at
        success_rate = (
            self._session.successful_tasks / self._session.task_count * 100
            if self._session.task_count > 0 else 0
        )

        return {
            "session_id": self._session.session_id,
            "uptime_seconds": round(uptime, 1),
            "uptime_human": self._format_duration(uptime),
            "task_count": self._session.task_count,
            "successful_tasks": self._session.successful_tasks,
            "failed_tasks": self._session.failed_tasks,
            "success_rate_percent": round(success_rate, 1),
            "total_compute_time_sec": round(self._session.total_compute_time_sec, 1),
            "active_task": self._session.active_task_id
        }

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task history"""
        return [asdict(t) for t in self._task_history[-limit:]]

    def get_storage_usage(self) -> Dict[str, Any]:
        """Check storage usage of memory system"""
        total_bytes = 0

        for path in [self.session_file, self.history_dir, self.learning_dir, self.cache_dir]:
            if path.exists():
                if path.is_file():
                    total_bytes += path.stat().st_size
                else:
                    for f in path.rglob('*'):
                        if f.is_file():
                            total_bytes += f.stat().st_size

        total_mb = total_bytes / (1024 * 1024)

        return {
            "total_mb": round(total_mb, 2),
            "total_gb": round(total_mb / 1024, 3),
            "limit_gb": 10,  # From safety constraints
            "usage_percent": round(total_mb / 1024 / 10 * 100, 1)
        }

    def clear_cache(self) -> Dict[str, Any]:
        """Clear temporary cache to free space"""
        cleared_bytes = 0
        cleared_files = 0

        for f in self.cache_dir.glob('*'):
            if f.is_file():
                cleared_bytes += f.stat().st_size
                f.unlink()
                cleared_files += 1

        return {
            "cleared_mb": round(cleared_bytes / (1024 * 1024), 2),
            "cleared_files": cleared_files
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds as human-readable duration"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def shutdown(self):
        """Clean shutdown - persist all state"""
        with self._lock:
            self._save_session()
            self._save_history()


# Global memory instance
_memory: Optional[MemorySystem] = None

def get_memory() -> MemorySystem:
    """Get or create the global memory instance"""
    global _memory
    if _memory is None:
        _memory = MemorySystem()
        _memory.initialize()
    return _memory
