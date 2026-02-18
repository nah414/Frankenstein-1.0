"""
Performance Tracker for Real-Time Adaptation

Collects and analyzes execution metrics for provider performance monitoring.
Maintains historical data and calculates trends to identify optimization
opportunities and performance degradation.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging
import os
import time

logger = logging.getLogger(__name__)


@dataclass
class TrendAnalysis:
    """Result of trend analysis."""
    slope: float
    direction: str  # 'improving', 'degrading', 'stable', 'insufficient_data'
    confidence: float  # 0.0 to 1.0


@dataclass
class DegradationAlert:
    """Alert for performance degradation."""
    provider_id: str
    metric: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    details: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PerformanceTracker:
    """
    Tracks and analyzes system performance metrics.

    Maintains historical data and calculates trends to identify
    optimization opportunities and performance degradation.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize performance tracker.

        Args:
            storage_path: Path to metrics database (optional)
        """
        self.storage_path = storage_path or self._get_default_storage_path()
        self.metrics_store = None  # Lazy-loaded
        self.current_metrics = {}
        self.metric_buffer = []
        self.buffer_size = 100

        # Task timing tracking
        self.task_start_times = {}
        self.task_completion_counts = {}
        self.task_error_counts = {}

        # Throughput calculation
        self.throughput_window_start = time.time()
        self.completed_tasks_in_window = 0

        logger.info(f"PerformanceTracker initialized (storage: {self.storage_path})")

    def collect_metrics(self, task_id: str, provider_id: str) -> Dict[str, Any]:
        """
        Collect current performance metrics for a task.

        Args:
            task_id: Task being monitored
            provider_id: Provider handling task

        Returns:
            Dict with current metrics
        """
        metrics = {
            'task_id': task_id,
            'provider_id': provider_id,
            'timestamp': datetime.now(),
            'latency': self._measure_latency(task_id),
            'cpu_usage': self._get_cpu_usage(),
            'ram_usage': self._get_ram_usage(),
            'throughput': self._calculate_throughput(),
            'error_rate': self._get_error_rate(provider_id),
            'queue_depth': self._get_queue_depth()
        }

        # Store in current metrics
        self.current_metrics[task_id] = metrics

        # Buffer for batch storage
        self.metric_buffer.append(metrics)
        if len(self.metric_buffer) >= self.buffer_size:
            self.flush_buffer()

        return metrics

    def get_performance_history(
        self,
        provider_id: Optional[str] = None,
        window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical performance data.

        Args:
            provider_id: Filter by provider (optional)
            window_hours: Time window to query

        Returns:
            List of historical metrics
        """
        if self.metrics_store is None:
            self._initialize_storage()

        start_time = datetime.now() - timedelta(hours=window_hours)
        return self.metrics_store.query_metrics(
            provider_id=provider_id,
            start_time=start_time
        )

    def calculate_trends(
        self,
        provider_id: str,
        metric_name: str,
        window_size: int = 50
    ) -> TrendAnalysis:
        """
        Calculate trend for a specific metric.

        Args:
            provider_id: Provider to analyze
            metric_name: Metric to trend
            window_size: Number of data points

        Returns:
            TrendAnalysis with slope, direction, confidence
        """
        history = self.get_performance_history(provider_id, window_hours=1)

        if len(history) < window_size:
            return TrendAnalysis(
                slope=0,
                direction='insufficient_data',
                confidence=0
            )

        recent = history[-window_size:]
        values = [m[metric_name] for m in recent if metric_name in m]

        if not values:
            return TrendAnalysis(slope=0, direction='no_data', confidence=0)

        # Linear regression (use numpy if available, fallback to simple implementation)
        try:
            import numpy as np
            slope, r_squared = self._calculate_trend_numpy(values)
        except ImportError:
            # Fallback to simple implementation
            slope = self._calculate_slope(values)
            r_squared = self._calculate_r_squared(values, slope)

        if slope < -0.01:
            direction = 'improving'
        elif slope > 0.01:
            direction = 'degrading'
        else:
            direction = 'stable'

        return TrendAnalysis(
            slope=slope,
            direction=direction,
            confidence=r_squared
        )

    def detect_degradation(
        self,
        provider_id: str,
        threshold: float = 0.2
    ) -> Optional[DegradationAlert]:
        """
        Detect if provider performance is degrading.

        Args:
            provider_id: Provider to check
            threshold: Degradation threshold (20% default)

        Returns:
            DegradationAlert if detected, None otherwise
        """
        latency_trend = self.calculate_trends(provider_id, 'latency')
        error_trend = self.calculate_trends(provider_id, 'error_rate')

        # Check latency degradation
        if latency_trend.slope > 0 and latency_trend.confidence > 0.7:
            history = self.get_performance_history(provider_id, window_hours=24)
            if len(history) < 20:
                return None

            recent_avg = self._avg_metric(history[-10:], 'latency')
            baseline_avg = self._avg_metric(history[:100], 'latency')

            if recent_avg > baseline_avg * (1 + threshold):
                return DegradationAlert(
                    provider_id=provider_id,
                    metric='latency',
                    severity='high' if recent_avg > baseline_avg * 1.5 else 'medium',
                    details={
                        'current_avg': recent_avg,
                        'baseline_avg': baseline_avg,
                        'increase_percent': ((recent_avg - baseline_avg) / baseline_avg) * 100
                    }
                )

        # Check error rate degradation
        if error_trend.slope > 0 and error_trend.confidence > 0.7:
            history = self.get_performance_history(provider_id, window_hours=1)
            if len(history) < 10:
                return None

            recent_errors = self._avg_metric(history[-10:], 'error_rate')
            if recent_errors > 0.2:  # >20% error rate
                return DegradationAlert(
                    provider_id=provider_id,
                    metric='error_rate',
                    severity='critical' if recent_errors > 0.5 else 'high',
                    details={'current_error_rate': recent_errors}
                )

        return None

    def detect_all_degradations(self) -> List[DegradationAlert]:
        """
        Check all providers for degradation across all metrics.

        Returns:
            List of degradation alerts
        """
        alerts = []

        # Get unique providers from recent history
        recent_history = self.get_performance_history(window_hours=24)
        providers = set(m.get('provider_id') for m in recent_history if m.get('provider_id'))

        for provider_id in providers:
            # Check for degradation
            alert = self.detect_degradation(provider_id)
            if alert:
                alerts.append(alert)

            # Also check for critical resource usage
            recent_metrics = [m for m in recent_history if m.get('provider_id') == provider_id]
            if recent_metrics:
                recent_cpu = self._avg_metric(recent_metrics[-10:], 'cpu_usage')
                recent_ram = self._avg_metric(recent_metrics[-10:], 'ram_usage')

                # Alert if consistently high resource usage
                if recent_cpu > 0.75:  # >75% CPU
                    alerts.append(DegradationAlert(
                        provider_id=provider_id,
                        metric='cpu_usage',
                        severity='high' if recent_cpu > 0.85 else 'medium',
                        details={'avg_cpu': recent_cpu, 'threshold': 0.75}
                    ))

                if recent_ram > 0.70:  # >70% RAM
                    alerts.append(DegradationAlert(
                        provider_id=provider_id,
                        metric='ram_usage',
                        severity='high' if recent_ram > 0.80 else 'medium',
                        details={'avg_ram': recent_ram, 'threshold': 0.70}
                    ))

        return alerts

    def get_provider_rankings(self, metric: str = 'latency') -> List[Dict[str, Any]]:
        """
        Rank providers by performance metric.

        Args:
            metric: Metric to rank by (latency, error_rate, throughput, cpu_usage, ram_usage)

        Returns:
            List of providers ranked by performance (best first)
        """
        if self.metrics_store is None:
            self._initialize_storage()

        # Get all provider summaries
        rankings = []

        # Query recent metrics for all providers
        recent_history = self.get_performance_history(window_hours=24)

        # Group by provider
        provider_metrics = {}
        for m in recent_history:
            provider = m.get('provider_id')
            if not provider:
                continue

            if provider not in provider_metrics:
                provider_metrics[provider] = []
            provider_metrics[provider].append(m)

        # Calculate rankings
        for provider_id, metrics_list in provider_metrics.items():
            if not metrics_list:
                continue

            # Calculate averages
            avg_latency = self._avg_metric(metrics_list, 'latency')
            avg_error_rate = self._avg_metric(metrics_list, 'error_rate')
            avg_throughput = self._avg_metric(metrics_list, 'throughput')
            avg_cpu = self._avg_metric(metrics_list, 'cpu_usage')
            avg_ram = self._avg_metric(metrics_list, 'ram_usage')

            # Get recent trend
            trend = self.calculate_trends(provider_id, metric, window_size=min(len(metrics_list), 50))

            # Calculate composite score (lower is better for latency/errors, higher for throughput)
            if metric == 'latency':
                score = avg_latency
            elif metric == 'error_rate':
                score = avg_error_rate
            elif metric == 'throughput':
                score = -avg_throughput  # Negate so higher throughput = lower score
            elif metric == 'cpu_usage':
                score = avg_cpu
            elif metric == 'ram_usage':
                score = avg_ram
            else:
                score = avg_latency  # Default to latency

            rankings.append({
                'provider_id': provider_id,
                'score': score,
                'avg_latency': avg_latency,
                'avg_error_rate': avg_error_rate,
                'avg_throughput': avg_throughput,
                'avg_cpu_usage': avg_cpu,
                'avg_ram_usage': avg_ram,
                'sample_count': len(metrics_list),
                'trend': trend.direction,
                'trend_confidence': trend.confidence
            })

        # Sort by score (ascending for latency/errors, descending for throughput)
        rankings.sort(key=lambda x: x['score'])

        return rankings

    def start_task_timing(self, task_id: str):
        """
        Start timing a task.

        Args:
            task_id: Task to time
        """
        self.task_start_times[task_id] = time.time()
        logger.debug(f"Started timing task: {task_id}")

    def end_task_timing(self, task_id: str, success: bool = True):
        """
        End timing a task and record result.

        Args:
            task_id: Task to end
            success: Whether task succeeded
        """
        if task_id not in self.task_start_times:
            logger.warning(f"Task {task_id} not found in start times")
            return

        # Calculate duration
        duration = time.time() - self.task_start_times[task_id]
        del self.task_start_times[task_id]

        # Update counters
        provider_id = self.current_metrics.get(task_id, {}).get('provider_id', 'unknown')

        if success:
            if provider_id not in self.task_completion_counts:
                self.task_completion_counts[provider_id] = 0
            self.task_completion_counts[provider_id] += 1
            self.completed_tasks_in_window += 1
        else:
            if provider_id not in self.task_error_counts:
                self.task_error_counts[provider_id] = 0
            self.task_error_counts[provider_id] += 1

        logger.debug(f"Ended task {task_id}: duration={duration:.2f}s, success={success}")

    def reset_throughput_window(self):
        """Reset throughput calculation window."""
        self.throughput_window_start = time.time()
        self.completed_tasks_in_window = 0

    def flush_buffer(self):
        """Flush metric buffer to storage."""
        if not self.metric_buffer:
            return

        if self.metrics_store is None:
            self._initialize_storage()

        self.metrics_store.store_metrics(self.metric_buffer)
        logger.debug(f"Flushed {len(self.metric_buffer)} metrics to storage")
        self.metric_buffer.clear()

    # Private methods

    def _get_default_storage_path(self) -> str:
        """Get default storage path for metrics database."""
        home = os.path.expanduser('~')
        data_dir = os.path.join(home, '.frankenstein', 'data', 'adaptation')
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, 'metrics.db')

    def _initialize_storage(self):
        """Lazy-load metrics store."""
        from .metrics_store import MetricsStore
        self.metrics_store = MetricsStore(self.storage_path)
        logger.info("Metrics store initialized")

    def _measure_latency(self, task_id: str) -> float:
        """Measure task latency from start time."""
        if task_id in self.task_start_times:
            return time.time() - self.task_start_times[task_id]
        return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1) / 100
        except Exception:
            return 0.0

    def _get_ram_usage(self) -> float:
        """Get current RAM usage."""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100
        except Exception:
            return 0.0

    def _calculate_throughput(self) -> float:
        """Calculate current throughput (tasks per second)."""
        window_duration = time.time() - self.throughput_window_start
        if window_duration < 1.0:  # Avoid division by very small numbers
            return 0.0

        throughput = self.completed_tasks_in_window / window_duration

        # Reset window every 60 seconds
        if window_duration > 60:
            self.reset_throughput_window()

        return throughput

    def _get_error_rate(self, provider_id: str) -> float:
        """Get error rate for provider (errors / total tasks)."""
        total_tasks = self.task_completion_counts.get(provider_id, 0) + self.task_error_counts.get(provider_id, 0)
        if total_tasks == 0:
            return 0.0

        errors = self.task_error_counts.get(provider_id, 0)
        return errors / total_tasks

    def _get_queue_depth(self) -> int:
        """Get current queue depth (number of tasks currently timing)."""
        return len(self.task_start_times)

    def _calculate_slope(self, values: List[float]) -> float:
        """Calculate slope using simple linear regression."""
        n = len(values)
        if n < 2:
            return 0.0

        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        return numerator / denominator if denominator != 0 else 0.0

    def _calculate_r_squared(self, values: List[float], slope: float) -> float:
        """Calculate R-squared for fit quality."""
        n = len(values)
        if n < 2:
            return 0.0

        y_mean = sum(values) / n
        x = list(range(n))
        x_mean = sum(x) / n
        intercept = y_mean - slope * x_mean

        y_pred = [slope * x[i] + intercept for i in range(n)]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    def _avg_metric(self, metrics: List[Dict[str, Any]], metric_name: str) -> float:
        """Calculate average of a metric."""
        values = [m[metric_name] for m in metrics if metric_name in m]
        return sum(values) / len(values) if values else 0.0

    def _calculate_trend_numpy(self, values: List[float]) -> tuple:
        """
        Calculate trend using numpy (more accurate).

        Args:
            values: List of metric values

        Returns:
            Tuple of (slope, r_squared)
        """
        import numpy as np

        n = len(values)
        x = np.arange(n)
        y = np.array(values)

        # Linear regression using numpy's polyfit
        coefficients = np.polyfit(x, y, 1)
        slope = coefficients[0]

        # Calculate R-squared
        y_pred = np.polyval(coefficients, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        return slope, r_squared
