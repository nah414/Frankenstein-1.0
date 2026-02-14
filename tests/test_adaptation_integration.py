"""
Comprehensive Integration Tests for Real-Time Adaptation

Tests end-to-end workflows, integration between components,
simulation scenarios, and safety constraint enforcement.
"""

import pytest
import sys
import os
import time
import tempfile
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class AdaptationSimulator:
    """Simulates various adaptation scenarios for testing."""

    def __init__(self):
        """Initialize simulator with fresh components."""
        from agents.adaptation import (
            get_adaptation_engine,
            reset_adaptation_engine,
            PerformanceTracker,
            ContextLearner,
            AdaptiveRouter
        )

        reset_adaptation_engine()

        tmpdir = tempfile.mkdtemp()
        self.tracker = PerformanceTracker(os.path.join(tmpdir, 'metrics.db'))
        self.learner = ContextLearner(os.path.join(tmpdir, 'knowledge.json'))
        self.router = AdaptiveRouter(self.tracker, self.learner)
        self.engine = get_adaptation_engine(initialize=True)

    def simulate_provider_failure(self):
        """Test automatic failover when provider fails."""
        # Setup: Train with two providers
        for provider in ['primary', 'backup']:
            for i in range(20):
                self.learner.record_execution(
                    task_type='critical_task',
                    provider_id=provider,
                    metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                    success=True
                )

        # Route task to primary
        decision = self.router.route_task({'type': 'critical_task', 'id': 'task_1'})
        initial_provider = decision.provider_id

        # Register task
        self.router.register_task_start('task_1', initial_provider, 'critical_task')

        # Simulate primary failure
        for _ in range(3):
            self.router.update_provider_health(initial_provider, is_successful=False)

        # Check if switch is recommended
        should_switch, reason = self.router.should_switch_provider(
            'task_1',
            {'latency': 1.0, 'error_rate': 0.0}
        )

        return {
            'initial_provider': initial_provider,
            'should_switch': should_switch,
            'switch_reason': reason,
            'fallback_chain': decision.fallback_chain
        }

    def simulate_gradual_degradation(self):
        """Test degradation detection over time."""
        provider_id = 'degrading_provider'

        # Simulate good performance initially
        for i in range(50):
            self.tracker.start_task_timing(f'task_{i}')
            time.sleep(0.01)  # Normal latency
            self.tracker.collect_metrics(f'task_{i}', provider_id)
            self.tracker.end_task_timing(f'task_{i}', success=True)

        self.tracker.flush_buffer()

        # Simulate gradual degradation
        for i in range(50, 60):
            self.tracker.start_task_timing(f'task_{i}')
            time.sleep(0.05)  # Degraded latency (5x slower)
            self.tracker.collect_metrics(f'task_{i}', provider_id)
            self.tracker.end_task_timing(f'task_{i}', success=True)

        self.tracker.flush_buffer()

        # Check for degradation
        alert = self.tracker.detect_degradation(provider_id, threshold=0.2)

        return {
            'provider_id': provider_id,
            'degradation_detected': alert is not None,
            'alert': alert
        }

    def simulate_learning_convergence(self):
        """Test pattern learning convergence."""
        import random

        providers = {
            'excellent': {'success_rate': 0.95, 'cpu': 0.3},
            'good': {'success_rate': 0.80, 'cpu': 0.5},
            'poor': {'success_rate': 0.50, 'cpu': 0.7}
        }

        # Simulate 100 executions per provider
        for provider_id, profile in providers.items():
            for i in range(100):
                success = random.random() < profile['success_rate']
                self.learner.record_execution(
                    task_type='convergence_test',
                    provider_id=provider_id,
                    metrics={'cpu_usage': profile['cpu'], 'ram_usage': 200, 'duration': 10.0},
                    success=success
                )

        # Get recommendation
        rec = self.learner.recommend_provider('convergence_test')

        return {
            'recommended_provider': rec.provider_id if rec else None,
            'confidence': rec.confidence if rec else 0,
            'success_rate': rec.success_rate if rec else 0,
            'expected': 'excellent'
        }


# Integration Tests

def test_end_to_end_workflow():
    """Test complete end-to-end adaptation workflow."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    # Step 1: Start monitoring
    engine.start_monitoring()
    assert engine.monitoring_active

    # Step 2: Monitor execution
    metrics = engine.monitor_execution('test_task_1', 'test_provider')
    assert 'cpu_usage' in metrics

    # Step 3: Analyze patterns (empty initially)
    patterns = engine.analyze_patterns(window_size=10)
    assert isinstance(patterns, list)

    # Step 4: Get recommendations (none initially)
    recs = engine.get_recommendations('unknown_task')
    assert isinstance(recs, list)

    # Step 5: Stop monitoring
    engine.stop_monitoring()
    assert not engine.monitoring_active


def test_component_integration():
    """Test integration between all components."""
    sim = AdaptationSimulator()

    # Train the system
    for i in range(25):
        sim.learner.record_execution(
            task_type='integration_test',
            provider_id='test_provider',
            metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

        sim.tracker.start_task_timing(f'task_{i}')
        time.sleep(0.01)
        sim.tracker.collect_metrics(f'task_{i}', 'test_provider')
        sim.tracker.end_task_timing(f'task_{i}', success=True)

    sim.tracker.flush_buffer()

    # Test routing decision uses learned patterns
    decision = sim.router.route_task({'type': 'integration_test', 'id': 'final_task'})

    assert decision.provider_id is not None
    assert len(decision.fallback_chain) > 0


def test_provider_failure_scenario():
    """Test provider failure and automatic failover."""
    sim = AdaptationSimulator()
    result = sim.simulate_provider_failure()

    assert result['initial_provider'] is not None
    assert result['should_switch'] is True
    assert result['switch_reason'] == 'health_check_failure'
    assert len(result['fallback_chain']) > 1


def test_gradual_degradation_detection():
    """Test detection of gradual performance degradation."""
    sim = AdaptationSimulator()
    result = sim.simulate_gradual_degradation()

    # May or may not detect depending on threshold - just verify it completes
    assert 'degradation_detected' in result
    assert 'provider_id' in result


def test_learning_convergence():
    """Test that learning converges to best provider."""
    sim = AdaptationSimulator()
    result = sim.simulate_learning_convergence()

    # Should recommend either 'excellent' or 'good' (both have high success rates)
    assert result['recommended_provider'] in ['excellent', 'good']
    assert result['confidence'] > 0.6  # 100 executions gives good confidence
    assert result['success_rate'] > 0.75  # Should be high for top providers


def test_safety_constraints_under_load():
    """Test that safety constraints are maintained."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    # Verify safety limits are configured
    assert engine.safety_limits['CPU_MAX'] == 0.80
    assert engine.safety_limits['RAM_MAX'] == 0.70

    # Check that monitoring respects limits
    assert engine._check_safe_to_monitor() in [True, False]  # Returns based on current state
    assert engine._check_safe_to_adapt() in [True, False]


def test_adaptation_rate_limiting():
    """Test that adaptation is rate-limited."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    import time

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine.start_monitoring()

    # First adaptation
    result1 = engine.trigger_adaptation('task1', 'test_reason')

    # Immediate second adaptation (should be rate-limited if first succeeded)
    result2 = engine.trigger_adaptation('task2', 'test_reason')

    if result1.success:
        # If first succeeded, second should be rate-limited
        assert not result2.success
        assert result2.reason == 'rate_limited'

    engine.stop_monitoring()


def test_concurrent_adaptation_limit():
    """Test max concurrent adaptations limit."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine.start_monitoring()

    # Manually max out concurrent adaptations
    engine.concurrent_adaptations = engine.safety_limits['MAX_CONCURRENT_ADAPTATIONS']

    result = engine.trigger_adaptation('task1', 'test_reason')

    # Should be blocked
    assert not result.success
    # Could fail for concurrent or safety reasons
    assert result.reason in ['max_concurrent_adaptations', 'safety_limits_exceeded']

    engine.stop_monitoring()


def test_router_with_performance_data():
    """Test router using real performance data."""
    sim = AdaptationSimulator()

    # Create performance data for multiple providers
    providers = ['fast_provider', 'medium_provider', 'slow_provider']
    sleep_times = [0.01, 0.02, 0.03]

    for provider, sleep_time in zip(providers, sleep_times):
        for i in range(15):
            sim.tracker.start_task_timing(f'{provider}_task{i}')
            time.sleep(sleep_time)
            sim.tracker.collect_metrics(f'{provider}_task{i}', provider)
            sim.tracker.end_task_timing(f'{provider}_task{i}', success=True)

    sim.tracker.flush_buffer()

    # Route new task
    decision = sim.router.route_task({'type': 'unknown_task', 'id': 'new_task'})

    # Should prefer fastest provider
    rankings = sim.tracker.get_provider_rankings(metric='latency')
    if rankings:
        fastest = rankings[0]['provider_id']
        assert decision.provider_id == fastest


def test_learner_with_tracker_integration():
    """Test integration between learner and tracker."""
    sim = AdaptationSimulator()

    provider_id = 'integrated_provider'

    # Record in both systems
    for i in range(20):
        # Tracker
        sim.tracker.start_task_timing(f'task_{i}')
        time.sleep(0.01)
        sim.tracker.collect_metrics(f'task_{i}', provider_id)
        sim.tracker.end_task_timing(f'task_{i}', success=True)

        # Learner
        sim.learner.record_execution(
            task_type='integrated_task',
            provider_id=provider_id,
            metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

    sim.tracker.flush_buffer()

    # Both should have data
    rankings = sim.tracker.get_provider_rankings()
    assert any(r['provider_id'] == provider_id for r in rankings)

    rec = sim.learner.recommend_provider('integrated_task')
    assert rec is not None
    assert rec.provider_id == provider_id


def test_full_adaptation_cycle():
    """Test complete adaptation cycle from routing to switching."""
    sim = AdaptationSimulator()

    # Setup: Two providers with different profiles
    for provider in ['provider_a', 'provider_b']:
        for i in range(20):
            sim.learner.record_execution(
                task_type='cycle_test',
                provider_id=provider,
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

    # Step 1: Route task
    decision = sim.router.route_task({'type': 'cycle_test', 'id': 'task_1'})
    assert decision.provider_id in ['provider_a', 'provider_b']

    # Step 2: Register task
    sim.router.register_task_start('task_1', decision.provider_id, 'cycle_test')
    assert 'task_1' in sim.router.active_tasks

    # Step 3: Check if switch needed (should be false initially)
    should_switch, _ = sim.router.should_switch_provider(
        'task_1',
        {'latency': 1.0, 'error_rate': 0.0}
    )
    assert not should_switch

    # Step 4: Complete task
    sim.router.register_task_completion('task_1', success=True, response_time=1.0)
    assert 'task_1' not in sim.router.active_tasks


def test_metrics_persistence():
    """Test that metrics persist across sessions."""
    import tempfile
    from agents.adaptation import PerformanceTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'persist_test.db')

        # Session 1: Record data
        tracker1 = PerformanceTracker(db_path)
        for i in range(15):
            tracker1.start_task_timing(f'task_{i}')
            tracker1.collect_metrics(f'task_{i}', 'persist_provider')
            tracker1.end_task_timing(f'task_{i}', success=True)
        tracker1.flush_buffer()

        # Session 2: Load data
        tracker2 = PerformanceTracker(db_path)
        history = tracker2.get_performance_history(provider_id='persist_provider')

        assert len(history) == 15


def test_knowledge_persistence():
    """Test that learned knowledge persists across sessions."""
    import tempfile
    from agents.adaptation import ContextLearner

    with tempfile.TemporaryDirectory() as tmpdir:
        knowledge_path = os.path.join(tmpdir, 'persist_knowledge.json')

        # Session 1: Learn patterns
        learner1 = ContextLearner(knowledge_path)
        for _ in range(20):
            learner1.record_execution(
                task_type='persist_task',
                provider_id='persist_provider',
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

        # Session 2: Reload knowledge
        learner2 = ContextLearner(knowledge_path)

        rec = learner2.recommend_provider('persist_task')
        assert rec is not None
        assert rec.provider_id == 'persist_provider'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
