"""
FRANKENSTEIN 1.0 - Task Orchestrator
Phase 1: Core Engine

Purpose: Route tasks to appropriate execution paths, manage queue
Hardware: Dell i3-8xxx, max 3 worker threads
"""

import uuid
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, Future

from .safety import SAFETY
from .governor import get_governor, ThrottleLevel
from .memory import get_memory


class TaskType(Enum):
    """Types of tasks FRANKENSTEIN can handle"""
    CLASSICAL = "classical"      # CPU-bound computation
    QUANTUM = "quantum"          # Cloud quantum (Phase 3)
    SYNTHESIS = "synthesis"      # Predictive synthesis (Phase 2)
    AGENT = "agent"              # MCP agents (Phase 4)
    SYSTEM = "system"            # Internal system tasks


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    THROTTLED = "throttled"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A task to be executed"""
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    payload: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value > other.priority.value  # Higher priority first


class TaskOrchestrator:
    """
    The Brain - routes tasks to the right place and manages execution.

    On Dell i3 (4 cores), we use max 3 worker threads to leave
    headroom for the OS and monitoring.
    """

    def __init__(self, max_workers: int = None):
        """
        Initialize the orchestrator.

        Args:
            max_workers: Override max workers (default from SAFETY)
        """
        self.max_workers = max_workers or SAFETY.MAX_WORKER_THREADS

        # Task queue and tracking
        self._task_queue: Queue = Queue()
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, Task] = {}
        self._max_completed_tasks = 100  # OPTIMIZED: Limit completed task history to prevent RAM buildup

        # Thread pool for execution
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: Dict[str, Future] = {}

        # Task handlers by type
        self._handlers: Dict[TaskType, Callable] = {}

        # State
        self._running = False
        self._lock = threading.Lock()
        self._queue_thread: Optional[threading.Thread] = None

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register built-in task handlers"""
        self._handlers[TaskType.CLASSICAL] = self._handle_classical
        self._handlers[TaskType.SYSTEM] = self._handle_system
        # Quantum, Synthesis, Agent handlers added in later phases

    def start(self) -> bool:
        """
        Start the orchestrator.

        Returns:
            True if started successfully
        """
        if self._running:
            return False

        self._running = True
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="FrankensteinWorker"
        )

        # Start queue processing thread
        self._queue_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="FrankensteinOrchestrator"
        )
        self._queue_thread.start()

        return True

    def stop(self, wait: bool = True) -> bool:
        """
        Stop the orchestrator.

        Args:
            wait: Wait for pending tasks to complete

        Returns:
            True if stopped successfully
        """
        if not self._running:
            return False

        self._running = False

        if self._executor:
            self._executor.shutdown(wait=wait)

        if self._queue_thread:
            self._queue_thread.join(timeout=5.0)

        return True

    def submit(
        self,
        task_type: TaskType,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """
        Submit a task for execution.

        Args:
            task_type: Type of task
            payload: Task data/parameters
            priority: Execution priority

        Returns:
            task_id for tracking
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        task = Task(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            payload=payload
        )

        with self._lock:
            self._active_tasks[task_id] = task
            task.status = TaskStatus.QUEUED

        self._task_queue.put(task)

        # Record in memory
        get_memory().record_task_start(task_id, task_type.value)

        return task_id

    def _process_queue(self):
        """Main queue processing loop"""
        governor = get_governor()

        while self._running:
            try:
                # Check if safe to proceed
                safety_check = governor.is_safe_to_proceed()
                if not safety_check["safe"]:
                    time.sleep(1.0)  # Back off when throttled
                    continue

                # Get next task (with timeout to allow shutdown)
                try:
                    task = self._task_queue.get(timeout=0.5)
                except Empty:
                    continue

                # Execute task
                self._execute_task(task)

            except Exception as e:
                print(f"Queue processor error: {e}")
                time.sleep(0.5)

    def _execute_task(self, task: Task):
        """Execute a single task"""
        task.started_at = time.time()
        task.status = TaskStatus.RUNNING

        handler = self._handlers.get(task.task_type)

        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task type: {task.task_type}"
            self._complete_task(task)
            return

        # Submit to thread pool
        future = self._executor.submit(handler, task)
        self._futures[task.task_id] = future

        # Add callback for completion
        future.add_done_callback(lambda f: self._on_task_done(task, f))

    def _on_task_done(self, task: Task, future: Future):
        """Handle task completion"""
        try:
            result = future.result(timeout=0)
            task.result = result
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

        self._complete_task(task)

    def _complete_task(self, task: Task):
        """Finalize a completed task"""
        task.completed_at = time.time()

        with self._lock:
            if task.task_id in self._active_tasks:
                del self._active_tasks[task.task_id]
            self._completed_tasks[task.task_id] = task
            # Trim completed tasks to prevent unbounded RAM growth
            if len(self._completed_tasks) > self._max_completed_tasks:
                # Remove oldest task (first item in dict)
                oldest_task_id = next(iter(self._completed_tasks))
                del self._completed_tasks[oldest_task_id]

        # Record in memory
        get_memory().record_task_complete(
            task_id=task.task_id,
            task_type=task.task_type.value,
            started_at=task.started_at or task.created_at,
            success=task.status == TaskStatus.COMPLETED,
            input_summary=str(task.payload)[:100],
            output_summary=str(task.result)[:100] if task.result else "",
            error=task.error
        )

    def _handle_classical(self, task: Task) -> Any:
        """Handle classical computation tasks"""
        payload = task.payload

        # Extract computation function if provided
        if "function" in payload and callable(payload["function"]):
            func = payload["function"]
            args = payload.get("args", [])
            kwargs = payload.get("kwargs", {})
            return func(*args, **kwargs)

        # Simple echo for testing
        return {"echo": payload, "task_id": task.task_id}

    def _handle_system(self, task: Task) -> Any:
        """Handle internal system tasks"""
        action = task.payload.get("action")

        if action == "health_check":
            return {
                "status": "healthy",
                "governor": get_governor().get_status(),
                "memory": get_memory().get_session_stats()
            }
        elif action == "clear_cache":
            return get_memory().clear_cache()

        return {"action": action, "status": "unknown_action"}

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""
        with self._lock:
            task = self._active_tasks.get(task_id) or self._completed_tasks.get(task_id)

        if not task:
            return {"error": "Task not found", "task_id": task_id}

        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "priority": task.priority.name,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error
        }

    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        with self._lock:
            active_count = len(self._active_tasks)
            completed_count = len(self._completed_tasks)

        return {
            "running": self._running,
            "queue_size": self._task_queue.qsize(),
            "active_tasks": active_count,
            "completed_tasks": completed_count,
            "max_workers": self.max_workers
        }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        with self._lock:
            task = self._active_tasks.get(task_id)

        if not task:
            return False

        if task.status == TaskStatus.QUEUED:
            task.status = TaskStatus.CANCELLED
            self._complete_task(task)
            return True

        if task_id in self._futures:
            future = self._futures[task_id]
            cancelled = future.cancel()
            if cancelled:
                task.status = TaskStatus.CANCELLED
                self._complete_task(task)
            return cancelled

        return False


# Global orchestrator instance
_orchestrator: Optional[TaskOrchestrator] = None

def get_orchestrator() -> TaskOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskOrchestrator()
    return _orchestrator
