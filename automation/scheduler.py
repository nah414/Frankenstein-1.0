"""
Task Scheduler - Lightweight scheduling engine for Frankenstein 1.0

Manages recurring, one-time, and event-triggered tasks with resource safety checks.
Supports provider-specific task tracking for all 28 quantum and classical providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6
"""

import sched
import time
import threading
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import psutil
from core.safety import SAFETY


class ScheduleType(Enum):
    """Task schedule types."""
    RECURRING = "recurring"
    ONE_TIME = "one_time"
    EVENT_TRIGGERED = "event_triggered"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    task_id: str
    task_func: Callable
    schedule_type: ScheduleType
    interval_seconds: Optional[int] = None
    trigger_condition: Optional[Callable[[], bool]] = None
    target_providers: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


class TaskScheduler:
    """
    Lightweight task scheduler using Python's sched module.

    Supports recurring, one-time, and event-triggered tasks with resource safety checks.
    Maximum 5 concurrent tasks to support 28 providers efficiently.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    # Resource safety limits — sourced from core/safety.py (single source of truth)
    MAX_CONCURRENT_TASKS = 5

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the task scheduler (only once)."""
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self._scheduler = sched.scheduler(time.time, time.sleep)
                self._tasks: Dict[str, ScheduledTask] = {}
                self._running_tasks: set = set()
                self._scheduler_thread: Optional[threading.Thread] = None
                self._stop_event = threading.Event()
                self._is_running = False
                self._initialized = True

    def _check_resources(self) -> bool:
        """
        Check if system resources are within safe limits.

        Returns:
            True if resources are safe, False otherwise
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0)  # interval=0 returns cached value, non-blocking
            ram_percent = psutil.virtual_memory().percent

            return (
                cpu_percent < SAFETY.MAX_CPU_PERCENT and
                ram_percent < SAFETY.MAX_MEMORY_PERCENT
            )
        except Exception:
            # If we can't check resources, assume they're safe
            return True

    def _can_run_task(self) -> bool:
        """
        Check if a new task can be started.

        Returns:
            True if task can run, False otherwise
        """
        with self._lock:
            # Check concurrent task limit
            if len(self._running_tasks) >= self.MAX_CONCURRENT_TASKS:
                return False

            # Check resource limits
            return self._check_resources()

    def _execute_task(self, task: ScheduledTask):
        """
        Execute a scheduled task with error handling.

        Args:
            task: ScheduledTask to execute
        """
        # Check if we can run the task
        if not self._can_run_task():
            task.status = TaskStatus.SKIPPED
            return

        # Mark task as running
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.last_run = datetime.now()
            self._running_tasks.add(task.task_id)

        try:
            # Execute the task function
            task.task_func()

            # Mark as completed
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.run_count += 1

        except Exception as e:
            # Handle errors
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error_count += 1
                task.last_error = str(e)

        finally:
            # Remove from running tasks
            with self._lock:
                self._running_tasks.discard(task.task_id)

            # Reschedule if recurring
            if task.schedule_type == ScheduleType.RECURRING:
                self._schedule_recurring_task(task)

    def _schedule_recurring_task(self, task: ScheduledTask):
        """
        Schedule the next execution of a recurring task.

        Args:
            task: ScheduledTask to reschedule
        """
        if not self._is_running or task.status == TaskStatus.PAUSED:
            return

        if task.interval_seconds is not None:
            # Calculate next run time
            next_run = datetime.now().timestamp() + task.interval_seconds
            task.next_run = datetime.fromtimestamp(next_run)

            # Schedule the task
            self._scheduler.enter(
                task.interval_seconds,
                1,  # Priority
                self._execute_task,
                (task,)
            )

            # Reset status to pending
            with self._lock:
                task.status = TaskStatus.PENDING

    def _schedule_one_time_task(self, task: ScheduledTask, delay_seconds: int = 0):
        """
        Schedule a one-time task.

        Args:
            task: ScheduledTask to schedule
            delay_seconds: Delay before execution (default: 0 = immediate)
        """
        if not self._is_running:
            return

        # Calculate run time
        next_run = datetime.now().timestamp() + delay_seconds
        task.next_run = datetime.fromtimestamp(next_run)

        # Schedule the task
        self._scheduler.enter(
            delay_seconds,
            1,  # Priority
            self._execute_task,
            (task,)
        )

    def _check_event_triggered_tasks(self):
        """Check and execute event-triggered tasks if conditions are met."""
        if not self._is_running:
            return

        with self._lock:
            event_tasks = [
                task for task in self._tasks.values()
                if task.schedule_type == ScheduleType.EVENT_TRIGGERED
                and task.status == TaskStatus.PENDING
                and task.trigger_condition is not None
            ]

        for task in event_tasks:
            try:
                # Check if trigger condition is met
                if task.trigger_condition():
                    self._execute_task(task)
            except Exception as e:
                task.last_error = f"Trigger check failed: {str(e)}"

        # Reschedule event check
        if self._is_running:
            self._scheduler.enter(
                5,  # Check every 5 seconds
                2,  # Lower priority than regular tasks
                self._check_event_triggered_tasks,
                ()
            )

    def _scheduler_loop(self):
        """Main scheduler loop running in separate thread."""
        # Start event-triggered task checker
        self._scheduler.enter(5, 2, self._check_event_triggered_tasks, ())

        # Run scheduler
        while not self._stop_event.is_set():
            try:
                # Run pending tasks
                self._scheduler.run(blocking=False)
                time.sleep(0.1)  # Short sleep to prevent CPU spinning
            except Exception:
                # Continue running even if there's an error
                pass

    def register_task(
        self,
        task_id: str,
        task_func: Callable,
        schedule_type: str,
        interval_seconds: Optional[int] = None,
        trigger_condition: Optional[Callable[[], bool]] = None,
        target_providers: Optional[List[str]] = None
    ) -> ScheduledTask:
        """
        Register a new task with the scheduler.

        Args:
            task_id: Unique identifier for the task
            task_func: Function to execute
            schedule_type: Type of schedule ('recurring', 'one_time', 'event_triggered')
            interval_seconds: Interval for recurring tasks
            trigger_condition: Condition function for event-triggered tasks
            target_providers: List of provider names this task monitors

        Returns:
            ScheduledTask instance

        Raises:
            ValueError: If task_id already exists or invalid schedule_type
        """
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task with ID '{task_id}' already exists")

            # Validate schedule type
            try:
                sched_type = ScheduleType(schedule_type)
            except ValueError:
                raise ValueError(
                    f"Invalid schedule_type: {schedule_type}. "
                    f"Must be one of: recurring, one_time, event_triggered"
                )

            # Validate parameters
            if sched_type == ScheduleType.RECURRING and interval_seconds is None:
                raise ValueError("Recurring tasks require interval_seconds")

            if sched_type == ScheduleType.EVENT_TRIGGERED and trigger_condition is None:
                raise ValueError("Event-triggered tasks require trigger_condition")

            # Create task
            task = ScheduledTask(
                task_id=task_id,
                task_func=task_func,
                schedule_type=sched_type,
                interval_seconds=interval_seconds,
                trigger_condition=trigger_condition,
                target_providers=target_providers or []
            )

            # Register task
            self._tasks[task_id] = task

            # Schedule if scheduler is running
            if self._is_running:
                if sched_type == ScheduleType.RECURRING:
                    self._schedule_recurring_task(task)
                elif sched_type == ScheduleType.ONE_TIME:
                    self._schedule_one_time_task(task)
                # Event-triggered tasks are checked periodically

            return task

    def start(self):
        """
        Start the scheduler (lazy - only when automation enabled).

        Thread-safe operation.
        """
        with self._lock:
            if self._is_running:
                return  # Already running

            self._is_running = True
            self._stop_event.clear()

            # Start scheduler thread
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True
            )
            self._scheduler_thread.start()

            # Schedule all registered recurring and one-time tasks
            for task in self._tasks.values():
                if task.schedule_type == ScheduleType.RECURRING:
                    self._schedule_recurring_task(task)
                elif task.schedule_type == ScheduleType.ONE_TIME:
                    self._schedule_one_time_task(task)

    def stop(self):
        """
        Stop the scheduler and all scheduled tasks.

        Thread-safe operation.
        """
        with self._lock:
            if not self._is_running:
                return  # Not running

            self._is_running = False
            self._stop_event.set()

            # Clear scheduler queue
            for event in self._scheduler.queue:
                try:
                    self._scheduler.cancel(event)
                except ValueError:
                    pass

            # Wait for scheduler thread to finish
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                self._scheduler_thread.join(timeout=5)

            # Reset all task statuses
            for task in self._tasks.values():
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.PAUSED

    def pause_task(self, task_id: str):
        """
        Pause a specific task.

        Args:
            task_id: ID of task to pause

        Raises:
            KeyError: If task_id not found
        """
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task '{task_id}' not found")

            task = self._tasks[task_id]
            task.status = TaskStatus.PAUSED

    def resume_task(self, task_id: str):
        """
        Resume a paused task.

        Args:
            task_id: ID of task to resume

        Raises:
            KeyError: If task_id not found
        """
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task '{task_id}' not found")

            task = self._tasks[task_id]
            task.status = TaskStatus.PENDING

            # Reschedule if scheduler is running
            if self._is_running:
                if task.schedule_type == ScheduleType.RECURRING:
                    self._schedule_recurring_task(task)
                elif task.schedule_type == ScheduleType.ONE_TIME:
                    self._schedule_one_time_task(task)

    def get_active_tasks(self) -> List[ScheduledTask]:
        """
        Get list of all active (non-completed) tasks.

        Returns:
            List of ScheduledTask instances
        """
        with self._lock:
            return [
                task for task in self._tasks.values()
                if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]

    def get_tasks_by_provider(self, provider_name: str) -> List[ScheduledTask]:
        """
        Get all tasks monitoring a specific provider.

        Args:
            provider_name: Provider name (one of 28 providers)

        Returns:
            List of ScheduledTask instances
        """
        with self._lock:
            return [
                task for task in self._tasks.values()
                if provider_name in task.target_providers
            ]

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        Get a specific task by ID.

        Args:
            task_id: Task ID

        Returns:
            ScheduledTask or None if not found
        """
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """
        Get all registered tasks.

        Returns:
            List of all ScheduledTask instances
        """
        with self._lock:
            return list(self._tasks.values())

    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        Returns:
            True if running, False otherwise
        """
        with self._lock:
            return self._is_running


# Singleton instance getter
_scheduler_instance = None

def get_scheduler() -> TaskScheduler:
    """
    Get the singleton TaskScheduler instance.

    Returns:
        TaskScheduler singleton
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
