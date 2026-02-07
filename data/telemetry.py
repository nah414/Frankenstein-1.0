#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Telemetry Collector
Phase 2, Step 7: Always-On Metrics Collection

Purpose: Comprehensive system metrics gathering
"""

import threading
import time
import psutil
from datetime import datetime, timedelta
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from collections import deque
import statistics


class MetricType(Enum):
    """All trackable metric types"""
    # System Metrics
    CPU_PERCENT = auto()
    MEMORY_PERCENT = auto()
    MEMORY_USED_MB = auto()
    DISK_PERCENT = auto()
    DISK_IO_READ = auto()
    DISK_IO_WRITE = auto()
    
    # Performance Metrics
    OPERATION_LATENCY_MS = auto()
    THROUGHPUT_OPS_SEC = auto()
    QUEUE_DEPTH = auto()
    ACTIVE_THREADS = auto()
    
    # Synthesis Metrics
    SYNTHESIS_COUNT = auto()
    SYNTHESIS_SUCCESS_RATE = auto()
    SYNTHESIS_AVG_TIME_MS = auto()
    WAVE_FUNCTION_COUNT = auto()
    COLLAPSE_COUNT = auto()
    
    # Quantum Metrics
    QUBIT_COUNT = auto()
    GATE_COUNT = auto()
    CIRCUIT_DEPTH = auto()
    MEASUREMENT_COUNT = auto()
    FIDELITY_ESTIMATE = auto()
    
    # Security Metrics
    THREATS_DETECTED = auto()
    THREATS_BLOCKED = auto()
    SCAN_COUNT = auto()
    INJECTION_ATTEMPTS = auto()
    
    # Agent Metrics
    ACTIVE_AGENTS = auto()
    AGENT_TASKS_TOTAL = auto()
    AGENT_TASKS_SUCCESS = auto()
    AGENT_TASKS_FAILED = auto()
    SWARM_SIZE = auto()
    
    # Pipeline Metrics
    PIPELINE_THROUGHPUT = auto()
    PIPELINE_LATENCY_MS = auto()
    PIPELINE_ERRORS = auto()
    DATA_BYTES_PROCESSED = auto()
    
    # Terminal Metrics
    COMMANDS_EXECUTED = auto()
    COMMANDS_FAILED = auto()
    SESSION_DURATION_SEC = auto()


@dataclass
class MetricSample:
    """Single metric measurement"""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric': self.metric_type.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


class TelemetryCollector:
    """
    Always-on telemetry collection system
    
    Features:
    - Automatic system metrics collection
    - Custom metric registration
    - Rolling time windows for aggregation
    - Callback hooks for real-time monitoring
    - Thread-safe operation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton for global telemetry"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Metric storage - rolling windows
        self._metrics: Dict[MetricType, deque] = {}
        self._window_size = 1000  # samples per metric
        
        # Counters for cumulative metrics
        self._counters: Dict[str, int] = {}
        
        # Callbacks for real-time updates
        self._callbacks: List[Callable[[MetricSample], None]] = []
        
        # Collection thread
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._collection_interval = 1.0  # seconds
        
        # Session tracking
        self._session_start = datetime.now()
        
        # Lock for thread safety
        self._data_lock = threading.Lock()
        
        self._initialized = True
    
    def start(self):
        """Start automatic collection"""
        if self._running:
            return
        self._running = True
        self._session_start = datetime.now()
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="Telemetry-Collector"
        )
        self._collection_thread.start()
    
    def stop(self):
        """Stop automatic collection"""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2.0)

    
    def record(self, metric_type: MetricType, value: float, **tags):
        """Record a metric sample"""
        sample = MetricSample(
            metric_type=metric_type,
            value=value,
            tags=tags
        )
        
        with self._data_lock:
            if metric_type not in self._metrics:
                self._metrics[metric_type] = deque(maxlen=self._window_size)
            self._metrics[metric_type].append(sample)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(sample)
            except Exception:
                pass
    
    def increment(self, counter_name: str, amount: int = 1):
        """Increment a counter"""
        with self._data_lock:
            self._counters[counter_name] = self._counters.get(counter_name, 0) + amount
    
    def get_counter(self, counter_name: str) -> int:
        """Get counter value"""
        with self._data_lock:
            return self._counters.get(counter_name, 0)
    
    def add_callback(self, callback: Callable[[MetricSample], None]):
        """Add real-time metric callback"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[MetricSample], None]):
        """Remove metric callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _collection_loop(self):
        """Background collection of system metrics"""
        while self._running:
            try:
                self._collect_system_metrics()
                time.sleep(self._collection_interval)
            except Exception as e:
                print(f"Telemetry collection error: {e}")
                time.sleep(self._collection_interval)
    
    def _collect_system_metrics(self):
        """Collect current system metrics"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        self.record(MetricType.CPU_PERCENT, cpu_percent)
        
        # Memory
        mem = psutil.virtual_memory()
        self.record(MetricType.MEMORY_PERCENT, mem.percent)
        self.record(MetricType.MEMORY_USED_MB, mem.used / (1024 * 1024))
        
        # Disk
        try:
            disk = psutil.disk_usage('/')
            self.record(MetricType.DISK_PERCENT, disk.percent)
        except Exception:
            pass
        
        # Threads
        self.record(MetricType.ACTIVE_THREADS, threading.active_count())
        
        # Session duration
        duration = (datetime.now() - self._session_start).total_seconds()
        self.record(MetricType.SESSION_DURATION_SEC, duration)

    
    def get_latest(self, metric_type: MetricType) -> Optional[MetricSample]:
        """Get most recent sample for a metric"""
        with self._data_lock:
            if metric_type in self._metrics and self._metrics[metric_type]:
                return self._metrics[metric_type][-1]
        return None
    
    def get_samples(self, metric_type: MetricType, 
                    limit: int = 100,
                    since: Optional[datetime] = None) -> List[MetricSample]:
        """Get samples for a metric"""
        with self._data_lock:
            if metric_type not in self._metrics:
                return []
            samples = list(self._metrics[metric_type])
        
        if since:
            samples = [s for s in samples if s.timestamp >= since]
        
        return samples[-limit:]
    
    def get_stats(self, metric_type: MetricType,
                  window_seconds: float = 60.0) -> Dict[str, float]:
        """Get statistics for a metric over a time window"""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        samples = self.get_samples(metric_type, limit=1000, since=cutoff)
        
        if not samples:
            return {'count': 0, 'min': 0, 'max': 0, 'avg': 0, 'std': 0}
        
        values = [s.value for s in samples]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def get_all_stats(self, window_seconds: float = 60.0) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics"""
        stats = {}
        with self._data_lock:
            metric_types = list(self._metrics.keys())
        
        for metric_type in metric_types:
            stats[metric_type.name] = self.get_stats(metric_type, window_seconds)
        
        return stats
    
    def get_counters(self) -> Dict[str, int]:
        """Get all counter values"""
        with self._data_lock:
            return self._counters.copy()
    
    def get_session_duration(self) -> float:
        """Get current session duration in seconds"""
        return (datetime.now() - self._session_start).total_seconds()
    
    def reset_counters(self):
        """Reset all counters"""
        with self._data_lock:
            self._counters.clear()
    
    def clear_metrics(self):
        """Clear all metric history"""
        with self._data_lock:
            self._metrics.clear()
