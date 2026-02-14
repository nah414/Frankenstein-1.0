"""
Test Suite for Adaptation Engine - Session 1

Tests lazy-loading, safety constraints, and basic functionality.
"""

import pytest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_lazy_loading_not_initialized():
    """Test that get_adaptation_engine returns None when not initialized."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    # Reset to ensure clean state
    reset_adaptation_engine()

    # Should NOT initialize automatically
    engine = get_adaptation_engine(initialize=False)
    assert engine is None, "Engine should not initialize when initialize=False"


def test_lazy_loading_on_demand():
    """Test that engine initializes on demand."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    # Reset to ensure clean state
    reset_adaptation_engine()

    # Should initialize on demand
    engine = get_adaptation_engine(initialize=True)
    assert engine is not None, "Engine should initialize when initialize=True"
    assert hasattr(engine, 'safety_limits'), "Engine should have safety_limits"


def test_safety_limits_hardcoded():
    """Test that safety limits are hard-coded correctly."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    assert engine.safety_limits['CPU_MAX'] == 0.80, "CPU_MAX should be 0.80"
    assert engine.safety_limits['RAM_MAX'] == 0.70, "RAM_MAX should be 0.70"
    assert engine.safety_limits['ADAPTATION_CPU_BUDGET'] == 0.05, "CPU budget should be 0.05"
    assert engine.safety_limits['ADAPTATION_RAM_BUDGET'] == 50 * 1024 * 1024, "RAM budget should be 50MB"
    assert engine.safety_limits['ADAPTATION_INTERVAL'] == 5.0, "Interval should be 5.0 seconds"
    assert engine.safety_limits['MAX_CONCURRENT_ADAPTATIONS'] == 2, "Max concurrent should be 2"


def test_components_not_loaded_at_init():
    """Test that components are not loaded at initialization."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    # Components should be None until monitoring starts
    assert engine.performance_tracker is None, "PerformanceTracker should not be loaded"
    assert engine.context_learner is None, "ContextLearner should not be loaded"
    assert engine.adaptive_router is None, "AdaptiveRouter should not be loaded"
    assert engine.monitoring_active is False, "Monitoring should not be active"


def test_start_monitoring_loads_components():
    """Test that starting monitoring loads components."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    # Start monitoring
    engine.start_monitoring()

    # Components should now be loaded
    assert engine.performance_tracker is not None, "PerformanceTracker should be loaded"
    assert engine.context_learner is not None, "ContextLearner should be loaded"
    assert engine.adaptive_router is not None, "AdaptiveRouter should be loaded"
    assert engine.monitoring_active is True, "Monitoring should be active"

    # Clean up
    engine.stop_monitoring()


def test_stop_monitoring():
    """Test stopping monitoring."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    engine.start_monitoring()
    assert engine.monitoring_active is True

    engine.stop_monitoring()
    assert engine.monitoring_active is False


def test_singleton_pattern():
    """Test that get_adaptation_engine returns the same instance."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine1 = get_adaptation_engine(initialize=True)
    engine2 = get_adaptation_engine(initialize=True)

    assert engine1 is engine2, "Should return same instance (singleton)"


def test_adaptation_result():
    """Test AdaptationResult class."""
    from agents.adaptation import AdaptationResult

    result = AdaptationResult(
        success=True,
        reason="test_reason",
        details={'key': 'value'}
    )

    assert result.success is True
    assert result.reason == "test_reason"
    assert result.details['key'] == 'value'
    assert isinstance(result.timestamp, datetime)


def test_get_status():
    """Test getting engine status."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)

    status = engine.get_status()

    assert 'monitoring_active' in status
    assert 'adaptation_count' in status
    assert 'components_loaded' in status
    assert 'safety_limits' in status
    assert 'current_resources' in status

    assert status['monitoring_active'] is False
    assert status['adaptation_count'] == 0


def test_rate_limiting():
    """Test adaptation rate limiting."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    import time

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine.start_monitoring()

    # First adaptation should succeed (or fail for other reasons)
    result1 = engine.trigger_adaptation('task1', 'test_reason')

    # Immediate second adaptation should be rate limited
    result2 = engine.trigger_adaptation('task2', 'test_reason')

    if not result1.success:
        # If first failed for resource reasons, second should also fail
        assert not result2.success
    else:
        # If first succeeded, second should be rate limited
        assert not result2.success
        assert result2.reason == 'rate_limited'

    # Clean up
    engine.stop_monitoring()


def test_concurrent_adaptation_limit():
    """Test max concurrent adaptations limit."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine.start_monitoring()

    # Manually set concurrent count to max
    engine.concurrent_adaptations = engine.safety_limits['MAX_CONCURRENT_ADAPTATIONS']

    # Should be blocked (either by concurrent limit or safety limit)
    result = engine.trigger_adaptation('task1', 'test_reason')

    assert not result.success
    # Could fail due to safety limits or concurrent limit
    assert result.reason in ['max_concurrent_adaptations', 'safety_limits_exceeded']

    # Clean up
    engine.concurrent_adaptations = 0
    engine.stop_monitoring()


def test_metrics_store_creation():
    """Test that MetricsStore creates database."""
    from agents.adaptation import MetricsStore
    import tempfile
    import os

    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        store = MetricsStore(db_path)

        assert os.path.exists(db_path), "Database file should be created"

        # Test database stats
        stats = store.get_database_stats()
        assert stats['total_metrics'] == 0, "New database should have no metrics"
        assert stats['database_path'] == db_path


def test_metrics_store_storage():
    """Test storing and retrieving metrics."""
    from agents.adaptation import MetricsStore
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        store = MetricsStore(db_path)

        # Store test metrics
        test_metrics = [
            {
                'task_id': 'task1',
                'provider_id': 'test_provider',
                'timestamp': datetime.now(),
                'latency': 1.5,
                'cpu_usage': 0.45,
                'ram_usage': 0.30,
                'throughput': 100.0,
                'error_rate': 0.0,
                'queue_depth': 5
            }
        ]

        store.store_metrics(test_metrics)

        # Retrieve metrics
        retrieved = store.query_metrics(provider_id='test_provider')
        assert len(retrieved) == 1, "Should retrieve stored metric"
        assert retrieved[0]['task_id'] == 'task1'
        assert retrieved[0]['latency'] == 1.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
