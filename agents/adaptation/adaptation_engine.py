"""
Real-Time Adaptation Engine for Frankenstein 1.0

This module orchestrates all adaptation activities including performance monitoring,
learning, and dynamic routing adjustments. All components are lazy-loaded to ensure
zero startup overhead.

CRITICAL SAFETY CONSTRAINTS:
- CPU_MAX: 80% (hard-coded, never exceed)
- RAM_MAX: 70% (hard-coded, never exceed)
- Adaptation CPU budget: 5% max
- Adaptation RAM budget: 50MB max
- Minimum adaptation interval: 5 seconds
- Max concurrent adaptations: 2
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# Default safety limits (HARD-CODED - DO NOT MODIFY)
DEFAULT_SAFETY_LIMITS = {
    'CPU_MAX': 0.80,                          # 80% CPU ceiling
    'RAM_MAX': 0.70,                          # 70% RAM ceiling
    'ADAPTATION_CPU_BUDGET': 0.05,            # Max 5% CPU for adaptation
    'ADAPTATION_RAM_BUDGET': 50 * 1024 * 1024, # Max 50MB RAM
    'ADAPTATION_INTERVAL': 5.0,               # Minimum seconds between adaptations
    'MAX_CONCURRENT_ADAPTATIONS': 2           # Prevent cascade failures
}


class AdaptationResult:
    """Result of an adaptation attempt."""

    def __init__(self, success: bool, reason: str, details: Optional[Dict[str, Any]] = None):
        self.success = success
        self.reason = reason
        self.details = details or {}
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"AdaptationResult(success={self.success}, reason='{self.reason}')"


class AdaptationEngine:
    """
    Central orchestrator for real-time adaptation.

    This class coordinates performance tracking, learning, and routing
    to optimize system behavior dynamically while maintaining safety.

    All components are lazy-loaded to prevent startup overhead.
    """

    def __init__(self, safety_limits: Optional[Dict[str, Any]] = None):
        """
        Initialize adaptation engine with safety constraints.

        Args:
            safety_limits: Dict with CPU_MAX, RAM_MAX, etc. (optional)
        """
        self.safety_limits = safety_limits or DEFAULT_SAFETY_LIMITS.copy()

        # Lazy-loaded components
        self.performance_tracker = None
        self.context_learner = None
        self.adaptive_router = None

        # State tracking
        self.monitoring_active = False
        self.adaptation_count = 0
        self.last_adaptation_time = None
        self.concurrent_adaptations = 0

        logger.info("AdaptationEngine initialized (lazy-load mode)")

    def start_monitoring(self):
        """
        Begin monitoring system performance.
        Initializes tracking components as needed.
        """
        if not self.monitoring_active:
            self._initialize_components()
            self.monitoring_active = True
            logger.info("Adaptation monitoring started")
        else:
            logger.warning("Monitoring already active")

    def stop_monitoring(self):
        """Gracefully stop all monitoring activities."""
        if self.monitoring_active:
            self.monitoring_active = False
            self._cleanup_resources()
            logger.info("Adaptation monitoring stopped")

    def monitor_execution(self, task_id: str, provider_id: str) -> Dict[str, Any]:
        """
        Track current task performance in real-time.

        Args:
            task_id: Unique identifier for task
            provider_id: Current provider handling task

        Returns:
            Dict with current performance metrics
        """
        if not self._check_safe_to_monitor():
            return {
                "status": "throttled",
                "reason": "resource_limits",
                "cpu_usage": self._get_cpu_usage(),
                "ram_usage": self._get_ram_usage()
            }

        if self.performance_tracker is None:
            logger.warning("Performance tracker not initialized, starting monitoring first")
            self.start_monitoring()

        metrics = self.performance_tracker.collect_metrics(task_id, provider_id)
        return self._analyze_metrics(metrics)

    def analyze_patterns(self, window_size: int = 100) -> List[Dict[str, Any]]:
        """
        Identify optimization opportunities from historical data.

        Args:
            window_size: Number of recent executions to analyze

        Returns:
            List of identified patterns and recommendations
        """
        if self.context_learner is None:
            logger.warning("Context learner not initialized")
            return []

        return self.context_learner.analyze_execution_patterns(window_size)

    def trigger_adaptation(
        self,
        task_id: str,
        reason: str,
        alternative_provider: Optional[str] = None
    ) -> AdaptationResult:
        """
        Execute adaptive response to runtime conditions.

        Args:
            task_id: Task requiring adaptation
            reason: Why adaptation is needed
            alternative_provider: Suggested alternative (optional)

        Returns:
            AdaptationResult with outcome details
        """
        # Safety check - resource limits
        if not self._check_safe_to_adapt():
            return AdaptationResult(
                success=False,
                reason="safety_limits_exceeded",
                details={
                    "cpu": self._get_cpu_usage(),
                    "ram": self._get_ram_usage(),
                    "cpu_limit": self.safety_limits['CPU_MAX'],
                    "ram_limit": self.safety_limits['RAM_MAX']
                }
            )

        # Safety check - rate limiting
        if not self._check_adaptation_rate_limit():
            return AdaptationResult(
                success=False,
                reason="rate_limited",
                details={
                    "last_adaptation": self.last_adaptation_time,
                    "min_interval": self.safety_limits['ADAPTATION_INTERVAL']
                }
            )

        # Safety check - concurrent adaptations
        if self.concurrent_adaptations >= self.safety_limits['MAX_CONCURRENT_ADAPTATIONS']:
            return AdaptationResult(
                success=False,
                reason="max_concurrent_adaptations",
                details={
                    "current": self.concurrent_adaptations,
                    "max": self.safety_limits['MAX_CONCURRENT_ADAPTATIONS']
                }
            )

        # Initialize router if needed
        if self.adaptive_router is None:
            logger.warning("Adaptive router not initialized, starting monitoring first")
            self.start_monitoring()

        # Execute adaptation
        self.concurrent_adaptations += 1
        try:
            result = self.adaptive_router.adapt_task(
                task_id=task_id,
                reason=reason,
                alternative_provider=alternative_provider
            )

            # Update state on success
            if result.success:
                self.adaptation_count += 1
                self.last_adaptation_time = datetime.now()
                if self.context_learner:
                    self.context_learner.record_adaptation(task_id, result)

            return result
        finally:
            self.concurrent_adaptations -= 1

    def get_recommendations(
        self,
        task_type: str,
        current_provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Provide optimization suggestions based on learned patterns.

        Args:
            task_type: Type of task to optimize
            current_provider: Current provider (optional)

        Returns:
            List of recommendations with confidence scores
        """
        if self.context_learner is None:
            logger.warning("Context learner not initialized")
            return []

        learned_patterns = self.context_learner.get_patterns_for_task(task_type)
        return self._generate_recommendations(learned_patterns, current_provider)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current adaptation engine status.

        Returns:
            Dict with status information
        """
        return {
            'monitoring_active': self.monitoring_active,
            'adaptation_count': self.adaptation_count,
            'last_adaptation': self.last_adaptation_time,
            'concurrent_adaptations': self.concurrent_adaptations,
            'components_loaded': {
                'performance_tracker': self.performance_tracker is not None,
                'context_learner': self.context_learner is not None,
                'adaptive_router': self.adaptive_router is not None
            },
            'safety_limits': self.safety_limits,
            'current_resources': {
                'cpu_usage': self._get_cpu_usage(),
                'ram_usage': self._get_ram_usage()
            }
        }

    # Private methods

    def _initialize_components(self):
        """Lazy-load required components."""
        logger.info("Initializing adaptation components...")

        # Import only when needed
        from .performance_tracker import PerformanceTracker
        from .context_learner import ContextLearner
        from .adaptive_router import AdaptiveRouter

        self.performance_tracker = PerformanceTracker()
        self.context_learner = ContextLearner()
        self.adaptive_router = AdaptiveRouter(
            performance_tracker=self.performance_tracker,
            context_learner=self.context_learner
        )

        logger.info("Adaptation components initialized")

    def _cleanup_resources(self):
        """Clean up resources on shutdown."""
        if self.performance_tracker:
            self.performance_tracker.flush_buffer()

        # Components remain loaded but inactive
        logger.info("Adaptation resources cleaned up")

    def _check_safe_to_monitor(self) -> bool:
        """Verify monitoring won't exceed safety limits."""
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1) / 100
            ram_usage = psutil.virtual_memory().percent / 100

            # Leave 5% buffer for monitoring overhead
            cpu_safe = cpu_usage < (self.safety_limits['CPU_MAX'] - 0.05)
            ram_safe = ram_usage < (self.safety_limits['RAM_MAX'] - 0.05)

            return cpu_safe and ram_safe
        except Exception as e:
            logger.error(f"Error checking monitoring safety: {e}")
            return False

    def _check_safe_to_adapt(self) -> bool:
        """Verify adaptation won't exceed safety limits."""
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1) / 100
            ram_usage = psutil.virtual_memory().percent / 100
            total_ram = psutil.virtual_memory().total

            # Calculate budgets
            cpu_budget = self.safety_limits['ADAPTATION_CPU_BUDGET']
            ram_budget_ratio = self.safety_limits['ADAPTATION_RAM_BUDGET'] / total_ram

            # Check if we have room for adaptation overhead
            cpu_safe = (cpu_usage + cpu_budget) <= self.safety_limits['CPU_MAX']
            ram_safe = (ram_usage + ram_budget_ratio) <= self.safety_limits['RAM_MAX']

            return cpu_safe and ram_safe
        except Exception as e:
            logger.error(f"Error checking adaptation safety: {e}")
            return False

    def _check_adaptation_rate_limit(self) -> bool:
        """Ensure minimum time between adaptations."""
        if self.last_adaptation_time is None:
            return True

        time_since_last = (datetime.now() - self.last_adaptation_time).total_seconds()
        return time_since_last >= self.safety_limits['ADAPTATION_INTERVAL']

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1) / 100
        except Exception:
            return 0.0

    def _get_ram_usage(self) -> float:
        """Get current RAM usage percentage."""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100
        except Exception:
            return 0.0

    def _analyze_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze collected metrics for issues."""
        # Placeholder for now - will be expanded in later sessions
        metrics['status'] = 'ok'
        return metrics

    def _generate_recommendations(
        self,
        patterns: List[Dict[str, Any]],
        current_provider: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations from learned patterns."""
        # Placeholder for now - will be expanded in later sessions
        return patterns
