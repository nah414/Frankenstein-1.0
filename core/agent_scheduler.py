"""
FRANKENSTEIN 1.0 - Agent Scheduler
Demand-Based Agent Lifecycle Management

Purpose: Prevent resource exhaustion by controlling when agents run
Design: Central coordinator with priority queues and throttling
Target: CPU < 80%, RAM < 70% at ALL times

Author: Frankenstein Project
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import deque
import weakref

from .resource_manager import (
    get_resource_manager, 
    MonitorState, 
    AdaptiveResourceManager
)


class AgentPriority(Enum):
    """Agent priority levels for scheduling"""
    CRITICAL = 0    # Must run (security threats)
    HIGH = 1        # Important (user-initiated)
    NORMAL = 2      # Standard agents
    LOW = 3         # Background tasks
    IDLE = 4        # Only when system is idle


class AgentState(Enum):
    """Agent lifecycle states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    THROTTLED = "throttled"


@dataclass
class AgentTask:
    """Represents a schedulable agent task"""
    agent_id: str
    priority: AgentPriority
    callback: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    estimated_cpu: float = 10.0  # Estimated CPU usage %
    estimated_memory: float = 5.0  # Estimated memory usage %
    max_runtime_sec: float = 30.0  # Maximum runtime before forced stop
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    state: AgentState = AgentState.PENDING


class AgentScheduler:
    """
    Central coordinator for all agent activity.
    
    Key Features:
    1. Priority-based scheduling
    2. Resource-aware throttling
    3. Automatic pause when limits exceeded
    4. Demand-based activation (agents sleep until needed)
    5. Graceful degradation under load
    
    Hard Limits (non-negotiable):
    - CPU: 80% max
    - Memory: 70% max
    - Concurrent agents: 3 max (Tier 1)
    """
    
    # Hard limits for Tier 1 hardware
    MAX_CONCURRENT_AGENTS = 3
    THROTTLE_CPU_THRESHOLD = 70  # Start throttling at 70%
    THROTTLE_MEM_THRESHOLD = 60  # Start throttling at 60%
    CRITICAL_CPU_THRESHOLD = 80  # Hard stop at 80%
    CRITICAL_MEM_THRESHOLD = 70  # Hard stop at 70%
    
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
        # Task queues by priority
        self._queues: Dict[AgentPriority, deque] = {
            p: deque() for p in AgentPriority
        }
        
        # Active tasks
        self._active_tasks: Dict[str, AgentTask] = {}
        self._task_threads: Dict[str, threading.Thread] = {}
        
        # Completed/failed task history
        self._history: deque = deque(maxlen=100)
        
        # Resource manager reference
        self._resource_manager: Optional[AdaptiveResourceManager] = None
        
        # Throttling state
        self._throttle_level = 0  # 0=none, 1=light, 2=heavy, 3=critical
        self._last_throttle_check = 0
        
        # Callbacks
        self._on_throttle_callbacks: List[Callable[[int], None]] = []
        
        # Stats
        self._stats = {
            "tasks_scheduled": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_throttled": 0,
            "total_runtime_sec": 0,
        }
    
    def start(self) -> bool:
        """Start the scheduler"""
        if self._running:
            return False
        
        # Get resource manager (lazy init)
        self._resource_manager = get_resource_manager()
        if not self._resource_manager._running:
            self._resource_manager.start()
        
        # Subscribe to critical state changes
        self._resource_manager.add_state_callback(self._on_resource_state_change)
        
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="FrankensteinAgentScheduler"
        )
        self._scheduler_thread.start()
        return True
    
    def stop(self):
        """Stop the scheduler gracefully"""
        self._running = False
        
        # Wait for active tasks to complete (with timeout)
        with self._lock:
            for agent_id, thread in list(self._task_threads.items()):
                thread.join(timeout=2.0)
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2.0)
    
    def _scheduler_loop(self):
        """Main scheduling loop - runs continuously but efficiently"""
        while self._running:
            try:
                # Check resource state and update throttle level
                self._update_throttle_level()
                
                # If critical, don't schedule new tasks
                if self._throttle_level >= 3:
                    time.sleep(1.0)
                    continue
                
                # Try to schedule pending tasks
                self._process_pending_tasks()
                
                # Check for stuck/overtime tasks
                self._check_task_timeouts()
                
            except Exception as e:
                print(f"Scheduler error: {e}")
            
            # Adaptive sleep based on activity
            if self._active_tasks:
                time.sleep(0.5)  # More frequent when tasks active
            else:
                time.sleep(2.0)  # Less frequent when idle
    
    def _update_throttle_level(self):
        """Update throttle level based on current resources"""
        now = time.time()
        if now - self._last_throttle_check < 0.5:
            return
        
        self._last_throttle_check = now
        
        if not self._resource_manager:
            return
        
        sample = self._resource_manager.get_sample()
        if not sample:
            return
        
        cpu = sample.cpu_percent
        mem = sample.memory_percent
        
        old_level = self._throttle_level
        
        # Determine throttle level
        if cpu >= self.CRITICAL_CPU_THRESHOLD or mem >= self.CRITICAL_MEM_THRESHOLD:
            self._throttle_level = 3  # Critical - stop all
        elif cpu >= self.THROTTLE_CPU_THRESHOLD or mem >= self.THROTTLE_MEM_THRESHOLD:
            self._throttle_level = 2  # Heavy throttle
        elif cpu >= 50 or mem >= 45:
            self._throttle_level = 1  # Light throttle
        else:
            self._throttle_level = 0  # No throttle
        
        # Notify if changed
        if old_level != self._throttle_level:
            for cb in self._on_throttle_callbacks:
                try:
                    cb(self._throttle_level)
                except Exception:
                    pass
    
    def _process_pending_tasks(self):
        """Process pending tasks respecting throttle level"""
        with self._lock:
            # Check if we can run more tasks
            active_count = len(self._active_tasks)
            
            # Adjust max concurrent based on throttle
            max_concurrent = self.MAX_CONCURRENT_AGENTS
            if self._throttle_level == 1:
                max_concurrent = 2
            elif self._throttle_level == 2:
                max_concurrent = 1
            elif self._throttle_level >= 3:
                max_concurrent = 0
            
            if active_count >= max_concurrent:
                return
            
            # Find next task to run (priority order)
            task = self._get_next_task()
            if task:
                self._start_task(task)
    
    def _get_next_task(self) -> Optional[AgentTask]:
        """Get next task from queues (priority order)"""
        for priority in AgentPriority:
            queue = self._queues[priority]
            if queue:
                # Check if this priority level is allowed at current throttle
                if self._throttle_level >= 2 and priority.value > 1:
                    continue  # Skip normal/low/idle at heavy throttle
                if self._throttle_level >= 1 and priority.value > 2:
                    continue  # Skip low/idle at light throttle
                
                return queue.popleft()
        return None
    
    def _start_task(self, task: AgentTask):
        """Start a task in its own thread"""
        task.state = AgentState.RUNNING
        task.started_at = time.time()
        
        self._active_tasks[task.agent_id] = task
        
        # Register with resource manager
        self._resource_manager.register_agent(task.agent_id)
        
        # Create thread for task
        thread = threading.Thread(
            target=self._run_task,
            args=(task,),
            daemon=True,
            name=f"Agent-{task.agent_id}"
        )
        self._task_threads[task.agent_id] = thread
        thread.start()
    
    def _run_task(self, task: AgentTask):
        """Execute a task and handle completion"""
        try:
            # Run the callback
            task.callback(*task.args, **task.kwargs)
            task.state = AgentState.COMPLETED
            self._stats["tasks_completed"] += 1
        except Exception as e:
            task.state = AgentState.FAILED
            self._stats["tasks_failed"] += 1
            print(f"Agent {task.agent_id} failed: {e}")
        finally:
            # Calculate runtime
            if task.started_at:
                runtime = time.time() - task.started_at
                self._stats["total_runtime_sec"] += runtime
            
            # Cleanup
            with self._lock:
                self._active_tasks.pop(task.agent_id, None)
                self._task_threads.pop(task.agent_id, None)
                self._history.append(task)
            
            # Unregister from resource manager
            if self._resource_manager:
                self._resource_manager.unregister_agent(task.agent_id)
    
    def _check_task_timeouts(self):
        """Check for tasks exceeding their max runtime"""
        now = time.time()
        with self._lock:
            for agent_id, task in list(self._active_tasks.items()):
                if task.started_at:
                    runtime = now - task.started_at
                    if runtime > task.max_runtime_sec:
                        # Force stop
                        task.state = AgentState.THROTTLED
                        self._stats["tasks_throttled"] += 1
                        print(f"Agent {agent_id} throttled (exceeded {task.max_runtime_sec}s)")
    
    def _on_resource_state_change(self, state: MonitorState):
        """Handle resource manager state changes"""
        if state == MonitorState.CRITICAL:
            # Pause all low-priority tasks
            self._throttle_level = 3
            print("⚠️ CRITICAL: All agents paused due to resource limits")
    
    # ==================== PUBLIC API ====================
    
    def schedule(
        self,
        agent_id: str,
        callback: Callable,
        priority: AgentPriority = AgentPriority.NORMAL,
        estimated_cpu: float = 10.0,
        estimated_memory: float = 5.0,
        max_runtime_sec: float = 30.0,
        *args,
        **kwargs
    ) -> bool:
        """
        Schedule an agent task for execution.
        
        Returns True if scheduled, False if rejected (resources too low).
        """
        # Check if we can accept this task
        if self._throttle_level >= 3 and priority.value > 0:
            return False  # Only critical tasks at throttle level 3
        
        # Check resource headroom
        if self._resource_manager:
            if not self._resource_manager.can_start_agent(
                agent_id, estimated_cpu, estimated_memory
            ):
                if priority.value > 1:  # Not critical/high
                    return False
        
        task = AgentTask(
            agent_id=agent_id,
            priority=priority,
            callback=callback,
            args=args,
            kwargs=kwargs,
            estimated_cpu=estimated_cpu,
            estimated_memory=estimated_memory,
            max_runtime_sec=max_runtime_sec,
        )
        
        with self._lock:
            self._queues[priority].append(task)
            self._stats["tasks_scheduled"] += 1
        
        return True
    
    def cancel(self, agent_id: str) -> bool:
        """Cancel a pending or running task"""
        with self._lock:
            # Check pending queues
            for queue in self._queues.values():
                for task in list(queue):
                    if task.agent_id == agent_id:
                        queue.remove(task)
                        return True
            
            # Check active tasks (can't really cancel, but mark)
            if agent_id in self._active_tasks:
                self._active_tasks[agent_id].state = AgentState.THROTTLED
                return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        with self._lock:
            pending_counts = {p.name: len(q) for p, q in self._queues.items()}
            
            return {
                "running": self._running,
                "throttle_level": self._throttle_level,
                "throttle_desc": ["none", "light", "heavy", "critical"][self._throttle_level],
                "active_tasks": len(self._active_tasks),
                "active_ids": list(self._active_tasks.keys()),
                "pending_by_priority": pending_counts,
                "total_pending": sum(pending_counts.values()),
                "stats": self._stats.copy(),
            }
    
    def add_throttle_callback(self, callback: Callable[[int], None]):
        """Subscribe to throttle level changes"""
        self._on_throttle_callbacks.append(callback)


# ==================== GLOBAL INSTANCE ====================

_scheduler: Optional[AgentScheduler] = None
_scheduler_lock = threading.Lock()

def get_scheduler() -> AgentScheduler:
    """Get or create the global agent scheduler"""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = AgentScheduler()
        return _scheduler

def ensure_scheduler_running() -> AgentScheduler:
    """Get the scheduler and ensure it's running"""
    scheduler = get_scheduler()
    if not scheduler._running:
        scheduler.start()
    return scheduler
