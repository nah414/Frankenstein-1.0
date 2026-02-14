"""
Test Suite for Adaptation Engine - Session 4

Tests adaptive routing, provider switching, fallback chains,
health monitoring, and load balancing.
"""

import pytest
import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def create_router_with_context():
    """Helper to create router with context."""
    from agents.adaptation import PerformanceTracker, ContextLearner, AdaptiveRouter
    import tempfile

    tmpdir = tempfile.mkdtemp()
    tracker = PerformanceTracker(os.path.join(tmpdir, 'metrics.db'))
    learner = ContextLearner(os.path.join(tmpdir, 'knowledge.json'))
    router = AdaptiveRouter(tracker, learner)

    return router, tracker, learner


def test_adaptive_router_initialization():
    """Test AdaptiveRouter initialization."""
    router, _, _ = create_router_with_context()

    assert router.provider_health == {}
    assert router.active_tasks == {}
    assert router.provider_load == {}
    assert router.max_fallback_chain == 3


def test_route_task_with_learned_pattern():
    """Test routing with learned patterns."""
    router, tracker, learner = create_router_with_context()

    # Create learned pattern with high confidence
    for _ in range(25):
        learner.record_execution(
            task_type='quantum_sim',
            provider_id='IBM_Quantum',
            metrics={'cpu_usage': 0.3, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

    # Route task
    decision = router.route_task({'type': 'quantum_sim', 'id': 'task_1'})

    assert decision.provider_id == 'IBM_Quantum'
    assert len(decision.fallback_chain) > 0
    assert 'learned_pattern' in decision.reason
    assert decision.confidence > 0.7


def test_route_task_fallback_to_rankings():
    """Test fallback to performance rankings."""
    router, tracker, learner = create_router_with_context()

    # Add performance data
    for provider in ['provider_a', 'provider_b']:
        for i in range(10):
            tracker.start_task_timing(f'{provider}_task{i}')
            time.sleep(0.01)
            tracker.collect_metrics(f'{provider}_task{i}', provider)
            tracker.end_task_timing(f'{provider}_task{i}', success=True)

    tracker.flush_buffer()

    # Route task (no learned pattern)
    decision = router.route_task({'type': 'unknown_task', 'id': 'task_2'})

    assert decision.provider_id is not None
    assert len(decision.fallback_chain) > 0


def test_route_task_default_fallback():
    """Test default fallback when no data."""
    router, _, _ = create_router_with_context()

    # Route task with no data
    decision = router.route_task({'type': 'unknown', 'id': 'task_3'})

    assert decision.provider_id == 'local_cpu'
    assert 'default_fallback' in decision.reason


def test_fallback_chain_building():
    """Test fallback chain construction."""
    router, _, learner = create_router_with_context()

    # Create multiple providers for same task
    providers = ['provider_a', 'provider_b', 'provider_c']
    for provider in providers:
        for _ in range(15):
            learner.record_execution(
                task_type='task_x',
                provider_id=provider,
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

    # Build fallback chain
    chain = router._build_fallback_chain('provider_a', 'task_x')

    assert len(chain) <= router.max_fallback_chain
    assert chain[0] == 'provider_a'
    # local_cpu may not be in chain if already at max length with better providers
    assert len(chain) >= 2  # At least primary + one fallback


def test_provider_health_tracking():
    """Test provider health monitoring."""
    router, _, _ = create_router_with_context()

    # Record successful operations
    for _ in range(5):
        router.update_provider_health('test_provider', is_successful=True, response_time=0.5)

    health = router._get_provider_health('test_provider')
    assert health.status.value == 'healthy'
    assert health.consecutive_failures == 0
    assert health.avg_response_time > 0


def test_provider_health_degradation():
    """Test provider health degradation on failures."""
    from agents.adaptation import ProviderHealth

    router, _, _ = create_router_with_context()

    # Record failures
    router.update_provider_health('failing_provider', is_successful=False)
    health = router._get_provider_health('failing_provider')
    assert health.status == ProviderHealth.DEGRADED
    assert health.consecutive_failures == 1

    # More failures
    router.update_provider_health('failing_provider', is_successful=False)
    health = router._get_provider_health('failing_provider')
    assert health.status == ProviderHealth.UNHEALTHY
    assert health.consecutive_failures == 2

    # Critical failure
    router.update_provider_health('failing_provider', is_successful=False)
    health = router._get_provider_health('failing_provider')
    assert health.status == ProviderHealth.OFFLINE
    assert health.consecutive_failures >= 3


def test_provider_health_recovery():
    """Test provider health recovery after failures."""
    from agents.adaptation import ProviderHealth

    router, _, _ = create_router_with_context()

    # Fail then succeed
    router.update_provider_health('recovering_provider', is_successful=False)
    router.update_provider_health('recovering_provider', is_successful=True)

    health = router._get_provider_health('recovering_provider')
    assert health.consecutive_failures == 0
    assert health.status == ProviderHealth.HEALTHY


def test_task_registration():
    """Test task start/completion registration."""
    router, _, _ = create_router_with_context()

    # Start task
    router.register_task_start('task_1', 'provider_a', 'quantum_sim')

    assert 'task_1' in router.active_tasks
    assert router.provider_load.get('provider_a', 0) == 1

    # Complete task
    router.register_task_completion('task_1', success=True, response_time=1.5)

    assert 'task_1' not in router.active_tasks
    assert router.provider_load.get('provider_a', 0) == 0


def test_should_switch_provider_latency_spike():
    """Test switch detection on latency spike."""
    router, _, _ = create_router_with_context()

    # Register task and set baseline
    router.register_task_start('task_1', 'provider_a', 'test_task')
    router.baseline_metrics['provider_a'] = {'latency': 1.0}

    # Check with normal latency
    should_switch, reason = router.should_switch_provider(
        'task_1',
        {'latency': 1.5, 'error_rate': 0.0}
    )
    assert not should_switch

    # Check with latency spike (>3x)
    should_switch, reason = router.should_switch_provider(
        'task_1',
        {'latency': 4.0, 'error_rate': 0.0}
    )
    assert should_switch
    assert reason == 'latency_spike'


def test_should_switch_provider_error_threshold():
    """Test switch detection on error threshold."""
    router, _, _ = create_router_with_context()

    router.register_task_start('task_1', 'provider_a', 'test_task')

    # High error rate
    should_switch, reason = router.should_switch_provider(
        'task_1',
        {'latency': 1.0, 'error_rate': 0.25}
    )
    assert should_switch
    assert reason == 'error_threshold'


def test_should_switch_provider_health_failure():
    """Test switch detection on health failure."""
    from agents.adaptation import ProviderHealth

    router, _, _ = create_router_with_context()

    router.register_task_start('task_1', 'provider_a', 'test_task')

    # Initialize and mark provider as unhealthy
    health = router._get_provider_health('provider_a')
    health.status = ProviderHealth.UNHEALTHY

    should_switch, reason = router.should_switch_provider(
        'task_1',
        {'latency': 1.0, 'error_rate': 0.0}
    )
    assert should_switch
    assert reason == 'health_check_failure'


def test_adapt_task_success():
    """Test successful task adaptation."""
    router, _, learner = create_router_with_context()

    # Setup: learned patterns for alternative
    for provider in ['provider_a', 'provider_b']:
        for _ in range(15):
            learner.record_execution(
                task_type='test_task',
                provider_id=provider,
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

    # Register active task
    router.register_task_start('task_1', 'provider_a', 'test_task')

    # Adapt task
    result = router.adapt_task('task_1', 'latency_spike', alternative_provider='provider_b')

    assert result.success
    assert result.details['old_provider'] == 'provider_a'
    assert result.details['new_provider'] == 'provider_b'


def test_adapt_task_not_found():
    """Test adaptation of non-existent task."""
    router, _, _ = create_router_with_context()

    result = router.adapt_task('nonexistent_task', 'test_reason')

    assert not result.success
    assert result.reason == 'task_not_found'


def test_adapt_task_no_alternative():
    """Test adaptation when no alternative available."""
    router, _, _ = create_router_with_context()

    # Register task with no alternatives
    router.register_task_start('task_1', 'only_provider', 'unique_task')

    # Mark only_provider as the only option, then try to find alternative
    result = router.adapt_task('task_1', 'test_reason')

    # Should fail to find alternative or succeed with local_cpu
    assert result.success or result.reason in ['no_alternative_provider', 'alternative_unhealthy']


def test_load_balancing():
    """Test load-balanced provider selection."""
    router, _, learner = create_router_with_context()

    # Create learned patterns for multiple providers
    providers = ['provider_a', 'provider_b', 'provider_c']
    for provider in providers:
        for _ in range(15):
            learner.record_execution(
                task_type='load_test',
                provider_id=provider,
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

    # Manually set different loads
    router.provider_load['provider_a'] = 5
    router.provider_load['provider_b'] = 2
    router.provider_load['provider_c'] = 8

    # Get load-balanced provider
    selected = router.get_load_balanced_provider('load_test')

    # Should select provider_b (lowest load)
    assert selected == 'provider_b'


def test_routing_stats():
    """Test routing statistics collection."""
    router, _, _ = create_router_with_context()

    # Register some tasks
    router.register_task_start('task_1', 'provider_a', 'test_task')
    router.register_task_start('task_2', 'provider_b', 'test_task')

    # Update health
    router.update_provider_health('provider_a', True, 0.5)

    stats = router.get_routing_stats()

    assert stats['active_tasks'] == 2
    assert 'provider_a' in stats['provider_load']
    assert 'provider_health' in stats
    assert stats['total_providers_tracked'] > 0


def test_baseline_metrics_update():
    """Test baseline metrics tracking."""
    router, _, _ = create_router_with_context()

    # Update baseline
    router._update_baseline_metrics('provider_a', 1.0)
    assert router.baseline_metrics['provider_a']['latency'] == 1.0

    # Update again (EMA)
    router._update_baseline_metrics('provider_a', 2.0)
    baseline = router.baseline_metrics['provider_a']['latency']
    assert 1.0 < baseline < 2.0  # Should be between old and new


def test_provider_load_tracking():
    """Test provider load increment/decrement."""
    router, _, _ = create_router_with_context()

    # Increment
    router._increment_provider_load('provider_a')
    router._increment_provider_load('provider_a')
    assert router.provider_load['provider_a'] == 2

    # Decrement
    router._decrement_provider_load('provider_a')
    assert router.provider_load['provider_a'] == 1

    # Decrement to zero
    router._decrement_provider_load('provider_a')
    assert router.provider_load['provider_a'] == 0


def test_is_provider_healthy():
    """Test provider health check."""
    from agents.adaptation import ProviderHealth

    router, _, _ = create_router_with_context()

    # Healthy
    router.provider_health['provider_a'] = router._get_provider_health('provider_a')
    router.provider_health['provider_a'].status = ProviderHealth.HEALTHY
    assert router._is_provider_healthy('provider_a')

    # Degraded but still usable
    router.provider_health['provider_a'].status = ProviderHealth.DEGRADED
    assert router._is_provider_healthy('provider_a')

    # Unhealthy
    router.provider_health['provider_a'].status = ProviderHealth.UNHEALTHY
    assert not router._is_provider_healthy('provider_a')

    # Offline
    router.provider_health['provider_a'].status = ProviderHealth.OFFLINE
    assert not router._is_provider_healthy('provider_a')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
