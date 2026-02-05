"""
FRANKENSTEIN 1.0 - Resource Governor
Phase 1: Core Engine

Purpose: Monitor system resources, enforce safety, auto-throttle
Hardware: Dell i3-8xxx, 4 cores, 8GB RAM
Dependencies: psutil
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .safety import SAFETY, check_resource_violation


class ThrottleLevel(Enum):
    """Throttle intensity levels"""
    NONE = 0
    LIGHT = 1      # Slow down new tasks
    MODERATE = 2   # Pause non-critical tasks
    HEAVY = 3      # Only essential operations
    EMERGENCY = 4  # Full stop


@dataclass
class ResourceSnapshot:
    """Point-in-time resource measurement"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    gpu_percent: float = 0.0
    disk_io_mbps: float = 0.0
    safe: bool = True
    violations: List[str] = field(default_factory=list)
    throttle_level: ThrottleLevel = ThrottleLevel.NONE


class ResourceGovernor:
    """
    The Watchdog - monitors resources and protects the host system.

    On a Dell i3 with 8GB RAM, this prevents FRANKENSTEIN from
    overwhelming the laptop while still being useful.
    """

    def __init__(self, poll_interval: float = 3.0):
        """
        Initialize the Governor.

        Args:
            poll_interval: Seconds between resource checks (default 3.0, optimized for tier1)
        """
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # State
        self._latest_snapshot: Optional[ResourceSnapshot] = None
        self._violation_callbacks: List[Callable] = []
        self._throttle_level = ThrottleLevel.NONE
        self._violation_count = 0
        self._start_time: Optional[float] = None

        # History for trend analysis (optimized for tier1)
        self._history: List[ResourceSnapshot] = []
        self._max_history = 30  # OPTIMIZED: 30 samples = ~90 seconds at 3s interval

    def start(self) -> bool:
        """
        Start the resource monitoring thread.

        Returns:
            True if started successfully, False if already running
        """
        if self._running:
            return False

        if not PSUTIL_AVAILABLE:
            print("⚠️ WARNING: psutil not installed. Governor running in limited mode.")

        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="FrankensteinGovernor")
        self._thread.start()
        return True

    def stop(self) -> bool:
        """
        Stop the monitoring thread gracefully.

        Returns:
            True if stopped, False if wasn't running
        """
        if not self._running:
            return False

        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        return True

    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread"""
        while self._running:
            try:
                snapshot = self.take_snapshot()

                with self._lock:
                    self._latest_snapshot = snapshot
                    self._history.append(snapshot)
                    if len(self._history) > self._max_history:
                        self._history.pop(0)

                if not snapshot.safe:
                    self._handle_violation(snapshot)
                else:
                    # Gradually reduce throttle if safe
                    if self._throttle_level != ThrottleLevel.NONE:
                        self._reduce_throttle()

            except Exception as e:
                print(f"Governor error: {e}")

            time.sleep(self.poll_interval)

    def take_snapshot(self) -> ResourceSnapshot:
        """Take a snapshot of current resource usage"""
        timestamp = time.time()

        if not PSUTIL_AVAILABLE:
            return ResourceSnapshot(
                timestamp=timestamp,
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_available_gb=8.0,
                safe=True
            )

        # Get CPU (non-blocking, uses cached value from previous call)
        # Note: First call returns 0.0, subsequent calls use interval since last call
        cpu = psutil.cpu_percent(interval=0)

        # Get memory
        mem = psutil.virtual_memory()
        memory_percent = mem.percent
        memory_used_gb = mem.used / (1024**3)
        memory_available_gb = mem.available / (1024**3)

        # Get disk I/O (if available)
        disk_io_mbps = 0.0
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io and hasattr(self, '_last_disk_io'):
                # Calculate MB/s since last check
                read_delta = disk_io.read_bytes - self._last_disk_io.read_bytes
                write_delta = disk_io.write_bytes - self._last_disk_io.write_bytes
                disk_io_mbps = (read_delta + write_delta) / (1024**2) / self.poll_interval
            self._last_disk_io = disk_io
        except Exception:
            pass

        # Check for violations
        result = check_resource_violation(cpu, memory_percent, 0.0, disk_io_mbps)

        # Determine throttle level based on severity
        throttle = ThrottleLevel.NONE
        if not result["safe"]:
            if cpu > 95 or memory_percent > 90:
                throttle = ThrottleLevel.EMERGENCY
            elif cpu > 90 or memory_percent > 85:
                throttle = ThrottleLevel.HEAVY
            elif cpu > SAFETY.MAX_CPU_PERCENT or memory_percent > SAFETY.MAX_MEMORY_PERCENT:
                throttle = ThrottleLevel.MODERATE
            else:
                throttle = ThrottleLevel.LIGHT

        return ResourceSnapshot(
            timestamp=timestamp,
            cpu_percent=cpu,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            disk_io_mbps=disk_io_mbps,
            safe=result["safe"],
            violations=result["violations"],
            throttle_level=throttle
        )

    def _handle_violation(self, snapshot: ResourceSnapshot):
        """Handle a safety violation"""
        self._violation_count += 1

        if SAFETY.AUTO_THROTTLE:
            self._throttle_level = snapshot.throttle_level

        # Notify callbacks
        for callback in self._violation_callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                print(f"Violation callback error: {e}")

    def _reduce_throttle(self):
        """Gradually reduce throttle level when system is stable"""
        if self._throttle_level == ThrottleLevel.EMERGENCY:
            self._throttle_level = ThrottleLevel.HEAVY
        elif self._throttle_level == ThrottleLevel.HEAVY:
            self._throttle_level = ThrottleLevel.MODERATE
        elif self._throttle_level == ThrottleLevel.MODERATE:
            self._throttle_level = ThrottleLevel.LIGHT
        elif self._throttle_level == ThrottleLevel.LIGHT:
            self._throttle_level = ThrottleLevel.NONE

    def add_violation_callback(self, callback: Callable[[ResourceSnapshot], None]):
        """Add a callback function for violations"""
        self._violation_callbacks.append(callback)

    def get_latest_snapshot(self) -> Optional[ResourceSnapshot]:
        """Get the most recent resource snapshot"""
        return self._latest_snapshot

    def get_status(self) -> Dict[str, Any]:
        """Get current governor status for display"""
        snapshot = self._latest_snapshot or self.take_snapshot()
        uptime = time.time() - self._start_time if self._start_time else 0

        return {
            "running": self._running,
            "poll_interval": self.poll_interval,
            "uptime_seconds": uptime,
            "cpu_percent": round(snapshot.cpu_percent, 1),
            "memory_percent": round(snapshot.memory_percent, 1),
            "memory_used_gb": round(snapshot.memory_used_gb, 2),
            "memory_available_gb": round(snapshot.memory_available_gb, 2),
            "disk_io_mbps": round(snapshot.disk_io_mbps, 1),
            "safe": snapshot.safe,
            "violations": snapshot.violations,
            "throttle_level": self._throttle_level.name,
            "total_violations": self._violation_count
        }

    def is_safe_to_proceed(self, required_memory_gb: float = 0.5) -> Dict[str, Any]:
        """
        Check if it's safe to start a new task.

        Args:
            required_memory_gb: Memory the task needs (default 0.5GB)

        Returns:
            Dict with 'safe' boolean and reason
        """
        snapshot = self.take_snapshot()

        # Check current safety
        if not snapshot.safe:
            return {"safe": False, "reason": f"System under load: {snapshot.violations}"}

        # Check throttle level
        if self._throttle_level == ThrottleLevel.EMERGENCY:
            return {"safe": False, "reason": "Emergency throttle active"}
        if self._throttle_level == ThrottleLevel.HEAVY:
            return {"safe": False, "reason": "Heavy throttle - only essential tasks"}

        # Check if enough memory available
        if snapshot.memory_available_gb < required_memory_gb:
            return {"safe": False, "reason": f"Insufficient memory: {snapshot.memory_available_gb:.1f}GB available, {required_memory_gb}GB required"}

        return {"safe": True, "reason": "System healthy"}

    def emergency_stop(self) -> Dict[str, str]:
        """Emergency stop - halt all operations immediately"""
        self._running = False
        self._throttle_level = ThrottleLevel.EMERGENCY
        return {
            "status": "EMERGENCY_STOP_ACTIVATED",
            "timestamp": datetime.now().isoformat(),
            "action": "All operations halted"
        }

    def get_trend(self) -> Dict[str, Any]:
        """Analyze resource usage trend from history"""
        if len(self._history) < 10:
            return {"trend": "insufficient_data", "samples": len(self._history)}

        recent = self._history[-10:]
        avg_cpu = sum(s.cpu_percent for s in recent) / len(recent)
        avg_mem = sum(s.memory_percent for s in recent) / len(recent)

        # Compare to older samples
        older = self._history[:10] if len(self._history) >= 20 else self._history[:len(self._history)//2]
        old_avg_cpu = sum(s.cpu_percent for s in older) / len(older)
        old_avg_mem = sum(s.memory_percent for s in older) / len(older)

        cpu_trend = "rising" if avg_cpu > old_avg_cpu + 5 else "falling" if avg_cpu < old_avg_cpu - 5 else "stable"
        mem_trend = "rising" if avg_mem > old_avg_mem + 5 else "falling" if avg_mem < old_avg_mem - 5 else "stable"

        return {
            "cpu_trend": cpu_trend,
            "memory_trend": mem_trend,
            "avg_cpu_recent": round(avg_cpu, 1),
            "avg_memory_recent": round(avg_mem, 1),
            "samples_analyzed": len(self._history)
        }


# Global governor instance
_governor: Optional[ResourceGovernor] = None

def get_governor() -> ResourceGovernor:
    """Get or create the global governor instance"""
    global _governor
    if _governor is None:
        _governor = ResourceGovernor()
    return _governor
