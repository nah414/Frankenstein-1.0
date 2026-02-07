#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Metrics Aggregator
Phase 2, Step 7: Statistics Computation

Purpose: Aggregate and compute statistics from telemetry data
"""

import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics


@dataclass
class MetricSnapshot:
    """Point-in-time snapshot of all metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    system: Dict[str, float] = field(default_factory=dict)
    synthesis: Dict[str, float] = field(default_factory=dict)
    quantum: Dict[str, float] = field(default_factory=dict)
    security: Dict[str, float] = field(default_factory=dict)
    agents: Dict[str, float] = field(default_factory=dict)
    pipeline: Dict[str, float] = field(default_factory=dict)
    terminal: Dict[str, float] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'system': self.system,
            'synthesis': self.synthesis,
            'quantum': self.quantum,
            'security': self.security,
            'agents': self.agents,
            'pipeline': self.pipeline,
            'terminal': self.terminal,
            'counters': self.counters
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'MetricSnapshot':
        return cls(
            timestamp=datetime.fromisoformat(d['timestamp']),
            system=d.get('system', {}),
            synthesis=d.get('synthesis', {}),
            quantum=d.get('quantum', {}),
            security=d.get('security', {}),
            agents=d.get('agents', {}),
            pipeline=d.get('pipeline', {}),
            terminal=d.get('terminal', {}),
            counters=d.get('counters', {})
        )


class MetricsAggregator:
    """
    Aggregates telemetry into meaningful statistics
    
    Features:
    - Time-window aggregation (1min, 5min, 1hr)
    - Trend detection
    - Anomaly flagging
    - Snapshot generation
    """
    
    def __init__(self, telemetry_collector=None):
        from .telemetry import TelemetryCollector, MetricType
        self._telemetry = telemetry_collector or TelemetryCollector()
        self._MetricType = MetricType
        self._snapshots: List[MetricSnapshot] = []
        self._snapshot_limit = 1000
        self._lock = threading.Lock()

    
    def take_snapshot(self) -> MetricSnapshot:
        """Capture current state of all metrics"""
        MT = self._MetricType
        
        def safe_latest(metric_type) -> float:
            sample = self._telemetry.get_latest(metric_type)
            return sample.value if sample else 0.0
        
        snapshot = MetricSnapshot(
            system={
                'cpu_percent': safe_latest(MT.CPU_PERCENT),
                'memory_percent': safe_latest(MT.MEMORY_PERCENT),
                'memory_used_mb': safe_latest(MT.MEMORY_USED_MB),
                'disk_percent': safe_latest(MT.DISK_PERCENT),
                'active_threads': safe_latest(MT.ACTIVE_THREADS),
                'session_duration_sec': safe_latest(MT.SESSION_DURATION_SEC),
            },
            synthesis={
                'count': safe_latest(MT.SYNTHESIS_COUNT),
                'success_rate': safe_latest(MT.SYNTHESIS_SUCCESS_RATE),
                'avg_time_ms': safe_latest(MT.SYNTHESIS_AVG_TIME_MS),
                'wave_functions': safe_latest(MT.WAVE_FUNCTION_COUNT),
                'collapses': safe_latest(MT.COLLAPSE_COUNT),
            },
            quantum={
                'qubits': safe_latest(MT.QUBIT_COUNT),
                'gates': safe_latest(MT.GATE_COUNT),
                'circuit_depth': safe_latest(MT.CIRCUIT_DEPTH),
                'measurements': safe_latest(MT.MEASUREMENT_COUNT),
                'fidelity': safe_latest(MT.FIDELITY_ESTIMATE),
            },
            security={
                'threats_detected': safe_latest(MT.THREATS_DETECTED),
                'threats_blocked': safe_latest(MT.THREATS_BLOCKED),
                'scans': safe_latest(MT.SCAN_COUNT),
                'injection_attempts': safe_latest(MT.INJECTION_ATTEMPTS),
            },
            agents={
                'active': safe_latest(MT.ACTIVE_AGENTS),
                'tasks_total': safe_latest(MT.AGENT_TASKS_TOTAL),
                'tasks_success': safe_latest(MT.AGENT_TASKS_SUCCESS),
                'tasks_failed': safe_latest(MT.AGENT_TASKS_FAILED),
                'swarm_size': safe_latest(MT.SWARM_SIZE),
            },
            pipeline={
                'throughput': safe_latest(MT.PIPELINE_THROUGHPUT),
                'latency_ms': safe_latest(MT.PIPELINE_LATENCY_MS),
                'errors': safe_latest(MT.PIPELINE_ERRORS),
                'bytes_processed': safe_latest(MT.DATA_BYTES_PROCESSED),
            },
            terminal={
                'commands_executed': safe_latest(MT.COMMANDS_EXECUTED),
                'commands_failed': safe_latest(MT.COMMANDS_FAILED),
            },
            counters=self._telemetry.get_counters()
        )
        
        with self._lock:
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._snapshot_limit:
                self._snapshots = self._snapshots[-self._snapshot_limit:]
        
        return snapshot

    
    def get_snapshots(self, limit: int = 100, 
                      since: Optional[datetime] = None) -> List[MetricSnapshot]:
        """Get historical snapshots"""
        with self._lock:
            snapshots = self._snapshots.copy()
        
        if since:
            snapshots = [s for s in snapshots if s.timestamp >= since]
        
        return snapshots[-limit:]
    
    def get_trend(self, category: str, metric: str, 
                  window_minutes: int = 5) -> Dict[str, Any]:
        """Analyze trend for a specific metric"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        snapshots = self.get_snapshots(limit=1000, since=cutoff)
        
        if len(snapshots) < 2:
            return {'trend': 'insufficient_data', 'change': 0, 'values': []}
        
        values = []
        for snap in snapshots:
            cat_data = getattr(snap, category, {})
            if metric in cat_data:
                values.append(cat_data[metric])
        
        if len(values) < 2:
            return {'trend': 'insufficient_data', 'change': 0, 'values': values}
        
        # Calculate trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        avg_first = statistics.mean(first_half) if first_half else 0
        avg_second = statistics.mean(second_half) if second_half else 0
        
        if avg_first == 0:
            change_pct = 0
        else:
            change_pct = ((avg_second - avg_first) / avg_first) * 100
        
        if change_pct > 10:
            trend = 'increasing'
        elif change_pct < -10:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change_percent': round(change_pct, 2),
            'current': values[-1] if values else 0,
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'samples': len(values)
        }
    
    def detect_anomalies(self, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect metrics that deviate significantly from normal"""
        anomalies = []
        MT = self._MetricType
        
        for metric_type in MT:
            stats = self._telemetry.get_stats(metric_type, window_seconds=300)
            if stats['count'] < 10 or stats['std'] == 0:
                continue
            
            latest = self._telemetry.get_latest(metric_type)
            if not latest:
                continue
            
            z_score = abs(latest.value - stats['avg']) / stats['std']
            if z_score > threshold_std:
                anomalies.append({
                    'metric': metric_type.name,
                    'value': latest.value,
                    'expected_avg': stats['avg'],
                    'std': stats['std'],
                    'z_score': round(z_score, 2),
                    'severity': 'high' if z_score > 3 else 'medium'
                })
        
        return anomalies

    
    def get_summary(self) -> Dict[str, Any]:
        """Get high-level summary of all metrics"""
        snapshot = self.take_snapshot()
        anomalies = self.detect_anomalies()
        
        return {
            'timestamp': snapshot.timestamp.isoformat(),
            'health': self._calculate_health(snapshot),
            'system': snapshot.system,
            'synthesis': snapshot.synthesis,
            'quantum': snapshot.quantum,
            'security': snapshot.security,
            'agents': snapshot.agents,
            'pipeline': snapshot.pipeline,
            'terminal': snapshot.terminal,
            'counters': snapshot.counters,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies)
        }
    
    def _calculate_health(self, snapshot: MetricSnapshot) -> Dict[str, Any]:
        """Calculate overall system health score"""
        scores = []
        issues = []
        
        # CPU health (inverted - lower is better)
        cpu = snapshot.system.get('cpu_percent', 0)
        if cpu > 80:
            scores.append(20)
            issues.append(f"High CPU: {cpu:.1f}%")
        elif cpu > 60:
            scores.append(60)
        else:
            scores.append(100)
        
        # Memory health
        mem = snapshot.system.get('memory_percent', 0)
        if mem > 75:
            scores.append(20)
            issues.append(f"High Memory: {mem:.1f}%")
        elif mem > 60:
            scores.append(60)
        else:
            scores.append(100)
        
        # Security health
        threats = snapshot.security.get('threats_detected', 0)
        blocked = snapshot.security.get('threats_blocked', 0)
        if threats > blocked:
            scores.append(0)
            issues.append(f"Unblocked threats: {threats - blocked}")
        elif threats > 0:
            scores.append(80)
        else:
            scores.append(100)
        
        # Calculate overall
        overall = sum(scores) / len(scores) if scores else 100
        
        if overall >= 90:
            status = 'excellent'
        elif overall >= 70:
            status = 'good'
        elif overall >= 50:
            status = 'fair'
        else:
            status = 'poor'
        
        return {
            'score': round(overall, 1),
            'status': status,
            'issues': issues
        }
