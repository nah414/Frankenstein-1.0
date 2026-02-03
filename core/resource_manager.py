"""
FRANKENSTEIN 1.0 - Resource Manager
Optimized resource monitoring with adaptive intervals

Purpose: Single source of truth for system resources with intelligent polling
Design: Lazy initialization, shared sampling, adaptive intervals
Target: Keep CPU < 80%, RAM < 70% on Tier 1 hardware

Author: Frankenstein Project
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import deque

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class MonitorState(Enum):
    """Monitor operational states"""
    IDLE = "idle"           # Minimal polling (5s)
    ACTIVE = "active"       # Normal polling (2s)
    ALERT = "alert"         # Frequent polling (1s)
    CRITICAL = "critical"   # Maximum polling (0.5s)


@dataclass
class ResourceSample:
    """Single resource measurement"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float


class AdaptiveResourceManager:
    """
    Centralized resource manager with adaptive polling.
    
    Key optimizations:
    1. Single psutil instance shared by all components
    2. Adaptive polling intervals based on system state
    3. Lazy initialization - starts only when needed
    4. Cached values reduce redundant measurements
    5. Event-driven updates instead of continuous polling
    
    Polling intervals by state:
    - IDLE: 5 seconds (low activity)
    - ACTIVE: 2 seconds (normal operation)
    - ALERT: 1 second (elevated usage)
    - CRITICAL: 0.5 seconds (at limits)
    """
    
    # Tier 1 limits (hard-coded safety)
    MAX_CPU = 80
    MAX_MEMORY = 70
    
    # Adaptive interval settings (CONSERVATIVE for Tier 1 hardware)
    INTERVALS = {
        MonitorState.IDLE: 8.0,      # 8 seconds when idle (was 5)
        MonitorState.ACTIVE: 4.0,    # 4 seconds when active (was 2)
        MonitorState.ALERT: 2.0,     # 2 seconds when alert (was 1)
        MonitorState.CRITICAL: 1.0,  # 1 second when critical (was 0.5)
    }
    
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Current state
        self._state = MonitorState.IDLE
        self._current_interval = self.INTERVALS[MonitorState.IDLE]
        
        # Cached sample
        self._latest: Optional[ResourceSample] = None
        self._last_sample_time: float = 0
        self._cache_ttl = 1.0  # Cache valid for 1 second (was 500ms)
        
        # History for trend analysis (60 samples max)
        self._history: deque = deque(maxlen=60)
        
        # Callbacks for state changes
        self._state_callbacks: List[Callable[[MonitorState], None]] = []
        self._sample_callbacks: List[Callable[[ResourceSample], None]] = []
        
        # Idle detection
        self._last_activity_time: float = time.time()
        self._idle_threshold_sec = 30  # Go idle after 30s of low usage
        
        # Agent tracking
        self._active_agents: Dict[str, float] = {}  # agent_id -> last_activity
    
    def start(self) -> bool:
        """Start the resource manager"""
        if self._running:
            return False
        
        if not PSUTIL_AVAILABLE:
            print("⚠️ psutil not installed - resource monitoring disabled")
            return False
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="FrankensteinResourceManager"
        )
        self._thread.start()
        return True
    
    def stop(self):
        """Stop the resource manager"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def _monitor_loop(self):
        """Main adaptive monitoring loop"""
        while self._running:
            try:
                # Take sample
                sample = self._take_sample()
                
                with self._lock:
                    self._latest = sample
                    self._history.append(sample)
                
                # Update state based on sample
                self._update_state(sample)
                
                # Notify callbacks
                for cb in self._sample_callbacks:
                    try:
                        cb(sample)
                    except Exception:
                        pass
                
            except Exception as e:
                print(f"ResourceManager error: {e}")
            
            # Adaptive sleep
            time.sleep(self._current_interval)
    
    def _take_sample(self) -> ResourceSample:
        """Take a single resource measurement"""
        # Use non-blocking CPU measurement for lower overhead
        # Instead of cpu_percent(interval=0.1) which blocks
        cpu = psutil.cpu_percent(interval=None)  # Uses previous measurement
        
        mem = psutil.virtual_memory()
        
        return ResourceSample(
            timestamp=time.time(),
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_used_gb=mem.used / (1024**3),
            memory_available_gb=mem.available / (1024**3)
        )
    
    def _update_state(self, sample: ResourceSample):
        """Update monitoring state based on current usage"""
        cpu = sample.cpu_percent
        mem = sample.memory_percent
        
        # Determine new state
        if cpu > self.MAX_CPU or mem > self.MAX_MEMORY:
            new_state = MonitorState.CRITICAL
        elif cpu > self.MAX_CPU * 0.85 or mem > self.MAX_MEMORY * 0.85:
            new_state = MonitorState.ALERT
        elif cpu > 30 or mem > 40:
            # Check if we've been low for a while
            if time.time() - self._last_activity_time > self._idle_threshold_sec:
                new_state = MonitorState.IDLE
            else:
                new_state = MonitorState.ACTIVE
            self._last_activity_time = time.time()
        else:
            # Low usage - check idle threshold
            if time.time() - self._last_activity_time > self._idle_threshold_sec:
                new_state = MonitorState.IDLE
            else:
                new_state = MonitorState.ACTIVE
        
        # State changed?
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._current_interval = self.INTERVALS[new_state]
            
            # Notify callbacks
            for cb in self._state_callbacks:
                try:
                    cb(new_state)
                except Exception:
                    pass
    
    # ==================== PUBLIC API ====================
    
    def get_sample(self, force_refresh: bool = False) -> Optional[ResourceSample]:
        """
        Get current resource sample (cached unless force_refresh).
        
        Uses cached value if within TTL to reduce overhead.
        """
        now = time.time()
        
        with self._lock:
            # Return cached if fresh enough
            if not force_refresh and self._latest:
                if now - self._last_sample_time < self._cache_ttl:
                    return self._latest
            
            # Need fresh sample
            if PSUTIL_AVAILABLE:
                sample = self._take_sample()
                self._latest = sample
                self._last_sample_time = now
                return sample
            
            return self._latest
    
    def get_state(self) -> MonitorState:
        """Get current monitoring state"""
        return self._state
    
    def get_current_interval(self) -> float:
        """Get current polling interval"""
        return self._current_interval
    
    def is_safe(self) -> bool:
        """Quick check if system is within limits"""
        sample = self.get_sample()
        if not sample:
            return True
        return sample.cpu_percent < self.MAX_CPU and sample.memory_percent < self.MAX_MEMORY
    
    def get_headroom(self) -> Dict[str, float]:
        """Get remaining headroom before limits"""
        sample = self.get_sample()
        if not sample:
            return {"cpu": 100, "memory": 100}
        
        return {
            "cpu": max(0, self.MAX_CPU - sample.cpu_percent),
            "memory": max(0, self.MAX_MEMORY - sample.memory_percent)
        }
    
    def signal_activity(self):
        """Signal that there's user/agent activity (delays idle mode)"""
        self._last_activity_time = time.time()
    
    # ==================== AGENT SCHEDULING ====================
    
    def can_start_agent(self, agent_id: str, estimated_cpu: float = 10, estimated_memory: float = 5) -> bool:
        """
        Check if an agent can be started based on available resources.
        
        Returns True if there's enough headroom for the estimated usage.
        """
        headroom = self.get_headroom()
        return (headroom["cpu"] >= estimated_cpu and 
                headroom["memory"] >= estimated_memory)
    
    def register_agent(self, agent_id: str):
        """Register an active agent"""
        self._active_agents[agent_id] = time.time()
        self.signal_activity()
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent when it completes"""
        self._active_agents.pop(agent_id, None)
    
    def get_active_agent_count(self) -> int:
        """Get count of currently active agents"""
        return len(self._active_agents)
    
    def suggest_agent_delay(self) -> float:
        """
        Suggest delay before starting next agent based on load.
        
        Returns seconds to wait (0 if safe to proceed immediately).
        """
        sample = self.get_sample()
        if not sample:
            return 0
        
        if self._state == MonitorState.CRITICAL:
            return 5.0  # Wait 5 seconds
        elif self._state == MonitorState.ALERT:
            return 2.0  # Wait 2 seconds
        elif self._state == MonitorState.ACTIVE:
            return 0.5  # Small delay
        return 0
    
    # ==================== CALLBACKS ====================
    
    def add_state_callback(self, callback: Callable[[MonitorState], None]):
        """Subscribe to state changes"""
        self._state_callbacks.append(callback)
    
    def add_sample_callback(self, callback: Callable[[ResourceSample], None]):
        """Subscribe to new samples"""
        self._sample_callbacks.append(callback)
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats"""
        sample = self.get_sample()
        history_list = list(self._history)
        
        stats = {
            "running": self._running,
            "state": self._state.value,
            "interval": self._current_interval,
            "max_cpu": self.MAX_CPU,
            "max_memory": self.MAX_MEMORY,
            "active_agents": len(self._active_agents),
            "samples_collected": len(history_list),
        }
        
        if sample:
            stats.update({
                "cpu_percent": round(sample.cpu_percent, 1),
                "memory_percent": round(sample.memory_percent, 1),
                "memory_used_gb": round(sample.memory_used_gb, 2),
                "memory_available_gb": round(sample.memory_available_gb, 2),
                "is_safe": self.is_safe(),
            })
            
            headroom = self.get_headroom()
            stats.update({
                "cpu_headroom": round(headroom["cpu"], 1),
                "memory_headroom": round(headroom["memory"], 1),
            })
        
        # Trend info from history
        if len(history_list) >= 10:
            recent = history_list[-10:]
            cpu_avg = sum(s.cpu_percent for s in recent) / len(recent)
            mem_avg = sum(s.memory_percent for s in recent) / len(recent)
            stats["cpu_avg_recent"] = round(cpu_avg, 1)
            stats["memory_avg_recent"] = round(mem_avg, 1)
        
        return stats


# ==================== GLOBAL INSTANCE ====================

_resource_manager: Optional[AdaptiveResourceManager] = None
_manager_lock = threading.Lock()

def get_resource_manager() -> AdaptiveResourceManager:
    """Get or create the global resource manager (lazy initialization)"""
    global _resource_manager
    with _manager_lock:
        if _resource_manager is None:
            _resource_manager = AdaptiveResourceManager()
        return _resource_manager


def ensure_resource_manager_running() -> AdaptiveResourceManager:
    """Get the resource manager and ensure it's running"""
    manager = get_resource_manager()
    if not manager._running:
        manager.start()
    return manager
