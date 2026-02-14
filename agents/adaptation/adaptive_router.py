"""
Adaptive Router for Real-Time Adaptation

Implements dynamic routing, provider switching, fallback chains,
and provider health monitoring for intelligent task routing.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProviderHealth(Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class RoutingDecision:
    """Decision for task routing."""
    provider_id: str
    fallback_chain: List[str]
    reason: str
    confidence: float
    estimated_resources: Optional[Dict[str, float]] = None
    task_id: Optional[str] = None


@dataclass
class ProviderHealthStatus:
    """Health status for a provider."""
    provider_id: str
    status: ProviderHealth
    last_check: datetime
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    avg_response_time: float = 0.0


class AdaptiveRouter:
    """
    Dynamic routing and provider switching.

    Intelligently routes tasks to optimal providers based on learned
    patterns, performance metrics, and real-time health status.
    """

    def __init__(self, performance_tracker, context_learner):
        """
        Initialize adaptive router.

        Args:
            performance_tracker: PerformanceTracker instance
            context_learner: ContextLearner instance
        """
        self.performance_tracker = performance_tracker
        self.context_learner = context_learner

        # Provider health tracking
        self.provider_health = {}  # provider_id -> ProviderHealthStatus

        # Active task tracking
        self.active_tasks = {}  # task_id -> (provider_id, start_time, metrics)

        # Load distribution
        self.provider_load = {}  # provider_id -> current_task_count

        # Baseline metrics for switch detection
        self.baseline_metrics = {}  # provider_id -> baseline_values

        # Configuration
        self.max_fallback_chain = 3
        self.health_check_interval = 60  # seconds
        self.latency_spike_threshold = 3.0  # 3x baseline
        self.error_rate_threshold = 0.2  # 20%
        self.max_consecutive_failures = 3

        logger.info("AdaptiveRouter initialized")

    def route_task(self, task: Dict[str, Any]) -> RoutingDecision:
        """
        Route task to optimal provider.

        Args:
            task: Task dictionary with 'type' and 'id'

        Returns:
            RoutingDecision with provider and fallback chain
        """
        task_type = task.get('type', 'unknown')
        task_id = task.get('id', 'unknown')

        logger.debug(f"Routing task {task_id} of type {task_type}")

        # Step 1: Check learned patterns (confidence > 0.7)
        recommendation = self.context_learner.recommend_provider(task_type)

        if recommendation and recommendation.confidence > 0.7:
            # Use learned recommendation
            primary_provider = recommendation.provider_id

            # Verify provider is healthy
            if self._is_provider_healthy(primary_provider):
                # Build fallback chain
                fallback_chain = self._build_fallback_chain(
                    primary_provider,
                    task_type
                )

                return RoutingDecision(
                    provider_id=primary_provider,
                    fallback_chain=fallback_chain,
                    reason=f"learned_pattern (confidence: {recommendation.confidence:.0%})",
                    confidence=recommendation.confidence,
                    estimated_resources=recommendation.resource_estimate,
                    task_id=task_id
                )

        # Step 2: Fall back to performance rankings
        rankings = self.performance_tracker.get_provider_rankings(metric='latency')

        for rank in rankings:
            provider_id = rank['provider_id']

            # Check health and availability
            if self._is_provider_healthy(provider_id) and self._check_resource_availability(provider_id):
                # Build fallback chain
                fallback_chain = self._build_fallback_chain(provider_id, task_type)

                return RoutingDecision(
                    provider_id=provider_id,
                    fallback_chain=fallback_chain,
                    reason=f"performance_ranking (rank #{rankings.index(rank) + 1})",
                    confidence=0.6,  # Moderate confidence from rankings
                    task_id=task_id
                )

        # Step 3: Default fallback to local_cpu
        fallback_chain = ['local_cpu']

        return RoutingDecision(
            provider_id='local_cpu',
            fallback_chain=fallback_chain,
            reason="default_fallback (no healthy providers found)",
            confidence=0.3,  # Low confidence, using default
            task_id=task_id
        )

    def adapt_task(
        self,
        task_id: str,
        reason: str,
        alternative_provider: Optional[str] = None
    ):
        """
        Adapt task to alternative provider.

        Args:
            task_id: Task to adapt
            reason: Reason for adaptation
            alternative_provider: Specific alternative (optional)

        Returns:
            AdaptationResult
        """
        from .adaptation_engine import AdaptationResult

        # Get current task info
        if task_id not in self.active_tasks:
            return AdaptationResult(
                success=False,
                reason="task_not_found",
                details={'task_id': task_id}
            )

        current_provider, start_time, metrics = self.active_tasks[task_id]

        # Determine alternative provider
        if alternative_provider:
            new_provider = alternative_provider
        else:
            # Find next best provider
            new_provider = self._find_alternative_provider(current_provider, metrics.get('task_type'))

        if not new_provider:
            return AdaptationResult(
                success=False,
                reason="no_alternative_provider",
                details={'current_provider': current_provider}
            )

        # Check if alternative is healthy
        if not self._is_provider_healthy(new_provider):
            return AdaptationResult(
                success=False,
                reason="alternative_unhealthy",
                details={'alternative': new_provider}
            )

        # Perform switch
        self.active_tasks[task_id] = (new_provider, datetime.now(), metrics)

        # Update load distribution
        self._decrement_provider_load(current_provider)
        self._increment_provider_load(new_provider)

        logger.info(f"Task {task_id} switched from {current_provider} to {new_provider} (reason: {reason})")

        return AdaptationResult(
            success=True,
            reason=f"switched_{reason}",
            details={
                'old_provider': current_provider,
                'new_provider': new_provider,
                'switch_reason': reason
            }
        )

    def should_switch_provider(
        self,
        task_id: str,
        current_metrics: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Determine if provider should be switched.

        Args:
            task_id: Task to check
            current_metrics: Current performance metrics

        Returns:
            Tuple of (should_switch, reason)
        """
        if task_id not in self.active_tasks:
            return False, 'task_not_active'

        current_provider, _, _ = self.active_tasks[task_id]

        # Get baseline metrics for provider
        baseline = self.baseline_metrics.get(current_provider, {})

        # Check latency spike (>3x baseline)
        if baseline.get('latency'):
            current_latency = current_metrics.get('latency', 0)
            if current_latency > baseline['latency'] * self.latency_spike_threshold:
                return True, 'latency_spike'

        # Check error threshold (>20%)
        current_error_rate = current_metrics.get('error_rate', 0)
        if current_error_rate > self.error_rate_threshold:
            return True, 'error_threshold'

        # Check provider health
        health = self._get_provider_health(current_provider)
        if health.status in [ProviderHealth.UNHEALTHY, ProviderHealth.OFFLINE]:
            return True, 'health_check_failure'

        return False, 'no_switch_needed'

    def update_provider_health(
        self,
        provider_id: str,
        is_successful: bool,
        response_time: Optional[float] = None
    ):
        """
        Update provider health status.

        Args:
            provider_id: Provider to update
            is_successful: Whether operation was successful
            response_time: Operation response time (optional)
        """
        if provider_id not in self.provider_health:
            self.provider_health[provider_id] = ProviderHealthStatus(
                provider_id=provider_id,
                status=ProviderHealth.HEALTHY,
                last_check=datetime.now()
            )

        health = self.provider_health[provider_id]

        if is_successful:
            # Reset failure count
            health.consecutive_failures = 0
            health.last_success = datetime.now()

            # Update avg response time
            if response_time is not None:
                if health.avg_response_time == 0:
                    health.avg_response_time = response_time
                else:
                    # EMA update
                    health.avg_response_time = (
                        0.3 * response_time + 0.7 * health.avg_response_time
                    )

            # Update status based on response time
            if response_time and response_time < 1.0:
                health.status = ProviderHealth.HEALTHY
            elif response_time and response_time < 5.0:
                health.status = ProviderHealth.DEGRADED
            else:
                health.status = ProviderHealth.HEALTHY  # Default

        else:
            # Increment failure count
            health.consecutive_failures += 1

            # Update status based on failures
            if health.consecutive_failures >= self.max_consecutive_failures:
                health.status = ProviderHealth.OFFLINE
            elif health.consecutive_failures >= 2:
                health.status = ProviderHealth.UNHEALTHY
            else:
                health.status = ProviderHealth.DEGRADED

        health.last_check = datetime.now()

        logger.debug(f"Provider {provider_id} health: {health.status.value} "
                    f"(failures: {health.consecutive_failures})")

    def get_load_balanced_provider(
        self,
        task_type: str,
        candidate_providers: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select provider with load balancing.

        Args:
            task_type: Type of task
            candidate_providers: List of candidate providers (optional)

        Returns:
            Provider ID or None
        """
        # Get candidates from learned patterns if not provided
        if not candidate_providers:
            patterns = self.context_learner.get_patterns_for_task(task_type)
            if patterns:
                candidate_providers = [p['provider_id'] for p in patterns
                                      if p['confidence'] > 0.5]

        if not candidate_providers:
            # Fall back to performance rankings
            rankings = self.performance_tracker.get_provider_rankings()
            candidate_providers = [r['provider_id'] for r in rankings[:5]]

        if not candidate_providers:
            return 'local_cpu'  # Ultimate fallback

        # Filter by health
        healthy_candidates = [
            p for p in candidate_providers
            if self._is_provider_healthy(p)
        ]

        if not healthy_candidates:
            return None

        # Select provider with lowest load
        min_load = float('inf')
        selected_provider = None

        for provider_id in healthy_candidates:
            load = self.provider_load.get(provider_id, 0)
            if load < min_load:
                min_load = load
                selected_provider = provider_id

        return selected_provider

    def register_task_start(
        self,
        task_id: str,
        provider_id: str,
        task_type: str
    ):
        """
        Register task start for tracking.

        Args:
            task_id: Task identifier
            provider_id: Provider handling task
            task_type: Type of task
        """
        self.active_tasks[task_id] = (
            provider_id,
            datetime.now(),
            {'task_type': task_type}
        )
        self._increment_provider_load(provider_id)

        logger.debug(f"Task {task_id} started on {provider_id}")

    def register_task_completion(
        self,
        task_id: str,
        success: bool,
        response_time: Optional[float] = None
    ):
        """
        Register task completion.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
            response_time: Task duration (optional)
        """
        if task_id not in self.active_tasks:
            return

        provider_id, start_time, _ = self.active_tasks[task_id]

        # Update provider health
        self.update_provider_health(provider_id, success, response_time)

        # Update baseline metrics
        self._update_baseline_metrics(provider_id, response_time)

        # Clean up
        del self.active_tasks[task_id]
        self._decrement_provider_load(provider_id)

        logger.debug(f"Task {task_id} completed on {provider_id} (success={success})")

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dict with routing stats
        """
        return {
            'active_tasks': len(self.active_tasks),
            'provider_load': dict(self.provider_load),
            'provider_health': {
                pid: {
                    'status': health.status.value,
                    'failures': health.consecutive_failures,
                    'avg_response_time': health.avg_response_time,
                    'last_success': health.last_success.isoformat() if health.last_success else None
                }
                for pid, health in self.provider_health.items()
            },
            'total_providers_tracked': len(self.provider_health),
            'healthy_providers': sum(
                1 for h in self.provider_health.values()
                if h.status == ProviderHealth.HEALTHY
            )
        }

    # Private methods

    def _build_fallback_chain(
        self,
        primary_provider: str,
        task_type: str
    ) -> List[str]:
        """
        Build fallback chain for a task.

        Args:
            primary_provider: Primary provider
            task_type: Type of task

        Returns:
            List of providers in fallback order
        """
        chain = [primary_provider]

        # Get alternative providers from learned patterns
        patterns = self.context_learner.get_patterns_for_task(task_type)

        for pattern in patterns:
            provider_id = pattern['provider_id']

            # Skip primary and already added providers
            if provider_id == primary_provider or provider_id in chain:
                continue

            # Check if healthy
            if self._is_provider_healthy(provider_id):
                chain.append(provider_id)

            # Stop at max chain length
            if len(chain) >= self.max_fallback_chain:
                break

        # Always include local_cpu as final fallback if not present
        if 'local_cpu' not in chain:
            chain.append('local_cpu')

        # Limit to max chain length
        return chain[:self.max_fallback_chain]

    def _find_alternative_provider(
        self,
        current_provider: str,
        task_type: Optional[str]
    ) -> Optional[str]:
        """Find alternative provider for task."""
        # Get patterns for task type
        if task_type:
            patterns = self.context_learner.get_patterns_for_task(task_type)
            for pattern in patterns:
                provider_id = pattern['provider_id']
                if provider_id != current_provider and self._is_provider_healthy(provider_id):
                    return provider_id

        # Fall back to performance rankings
        rankings = self.performance_tracker.get_provider_rankings()
        for rank in rankings:
            provider_id = rank['provider_id']
            if provider_id != current_provider and self._is_provider_healthy(provider_id):
                return provider_id

        # Ultimate fallback
        if current_provider != 'local_cpu':
            return 'local_cpu'

        return None

    def _is_provider_healthy(self, provider_id: str) -> bool:
        """Check if provider is healthy."""
        health = self._get_provider_health(provider_id)
        return health.status in [ProviderHealth.HEALTHY, ProviderHealth.DEGRADED]

    def _get_provider_health(self, provider_id: str) -> ProviderHealthStatus:
        """Get provider health status."""
        if provider_id not in self.provider_health:
            # Initialize as healthy
            self.provider_health[provider_id] = ProviderHealthStatus(
                provider_id=provider_id,
                status=ProviderHealth.HEALTHY,
                last_check=datetime.now()
            )

        return self.provider_health[provider_id]

    def _check_resource_availability(self, provider_id: str) -> bool:
        """Check if provider has available resources."""
        # Simple check: ensure not overloaded
        max_concurrent_tasks = 10  # Configurable limit
        current_load = self.provider_load.get(provider_id, 0)
        return current_load < max_concurrent_tasks

    def _increment_provider_load(self, provider_id: str):
        """Increment provider load counter."""
        self.provider_load[provider_id] = self.provider_load.get(provider_id, 0) + 1

    def _decrement_provider_load(self, provider_id: str):
        """Decrement provider load counter."""
        if provider_id in self.provider_load:
            self.provider_load[provider_id] = max(0, self.provider_load[provider_id] - 1)

    def _update_baseline_metrics(self, provider_id: str, response_time: Optional[float]):
        """Update baseline metrics for provider."""
        if response_time is None:
            return

        if provider_id not in self.baseline_metrics:
            self.baseline_metrics[provider_id] = {'latency': response_time}
        else:
            # EMA update
            old_latency = self.baseline_metrics[provider_id]['latency']
            self.baseline_metrics[provider_id]['latency'] = (
                0.3 * response_time + 0.7 * old_latency
            )
