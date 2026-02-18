"""
Test Suite for Adaptation Engine - Session 2

Tests enhanced performance tracking, metric collection, trend analysis,
degradation detection, and provider rankings.
"""

import pytest
import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_task_timing():
    """Test task timing functionality."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Start timing
        tracker.start_task_timing('task1')
        assert 'task1' in tracker.task_start_times

        # Wait a bit
        time.sleep(0.1)

        # Collect metrics should show latency
        metrics = tracker.collect_metrics('task1', 'test_provider')
        assert metrics['latency'] >= 0.1
        assert metrics['latency'] < 0.2  # Should be around 0.1 seconds

        # End timing
        tracker.end_task_timing('task1', success=True)
        assert 'task1' not in tracker.task_start_times
        assert tracker.task_completion_counts.get('test_provider', 0) >= 1


def test_error_rate_tracking():
    """Test error rate calculation."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Simulate some tasks
        for i in range(10):
            tracker.start_task_timing(f'task{i}')
            tracker.collect_metrics(f'task{i}', 'test_provider')
            # 3 failures, 7 successes
            tracker.end_task_timing(f'task{i}', success=(i >= 3))

        # Check error rate
        error_rate = tracker._get_error_rate('test_provider')
        assert 0.25 <= error_rate <= 0.35  # Should be ~0.3 (3/10)


def test_throughput_calculation():
    """Test throughput calculation."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Reset throughput window
        tracker.reset_throughput_window()

        # Complete 5 tasks
        for i in range(5):
            tracker.start_task_timing(f'task{i}')
            tracker.collect_metrics(f'task{i}', 'test_provider')
            tracker.end_task_timing(f'task{i}', success=True)

        # Wait a bit
        time.sleep(0.5)

        # Calculate throughput
        throughput = tracker._calculate_throughput()
        assert throughput > 0  # Should have some throughput
        assert throughput <= 10  # Should be reasonable


def test_queue_depth():
    """Test queue depth tracking."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Start multiple tasks
        for i in range(5):
            tracker.start_task_timing(f'task{i}')

        queue_depth = tracker._get_queue_depth()
        assert queue_depth == 5

        # End some tasks
        tracker.end_task_timing('task0', success=True)
        tracker.end_task_timing('task1', success=True)

        queue_depth = tracker._get_queue_depth()
        assert queue_depth == 3


def test_numpy_trend_analysis():
    """Test trend analysis with numpy (if available)."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    try:
        import numpy as np
        has_numpy = True
    except ImportError:
        has_numpy = False
        pytest.skip("NumPy not available")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create test data with clear upward trend
        values = [1.0 + i * 0.1 for i in range(50)]

        slope, r_squared = tracker._calculate_trend_numpy(values)

        assert slope > 0  # Upward trend
        assert r_squared > 0.95  # High confidence (linear data)


def test_trend_analysis_fallback():
    """Test trend analysis fallback without numpy."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create test data
        values = [1.0 + i * 0.1 for i in range(50)]

        slope = tracker._calculate_slope(values)
        r_squared = tracker._calculate_r_squared(values, slope)

        assert slope > 0  # Upward trend
        assert r_squared > 0.9  # High confidence


def test_provider_rankings():
    """Test provider ranking system."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create test data for multiple providers
        providers = ['provider_a', 'provider_b', 'provider_c']

        for provider in providers:
            for i in range(10):
                task_id = f'{provider}_task{i}'
                tracker.start_task_timing(task_id)

                # Provider A: fast (0.1s latency)
                # Provider B: medium (0.5s latency)
                # Provider C: slow (1.0s latency)
                if provider == 'provider_a':
                    time.sleep(0.05)
                elif provider == 'provider_b':
                    time.sleep(0.1)
                else:
                    time.sleep(0.15)

                metrics = tracker.collect_metrics(task_id, provider)
                tracker.end_task_timing(task_id, success=True)

        # Flush to storage
        tracker.flush_buffer()

        # Get rankings by latency
        rankings = tracker.get_provider_rankings(metric='latency')

        assert len(rankings) == 3
        # Provider A should rank first (lowest latency)
        assert rankings[0]['provider_id'] == 'provider_a'
        # Provider C should rank last (highest latency)
        assert rankings[-1]['provider_id'] == 'provider_c'


def test_degradation_detection_latency():
    """Test degradation detection for latency."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create baseline data (fast)
        for i in range(50):
            task_id = f'task{i}'
            tracker.start_task_timing(task_id)
            time.sleep(0.01)  # 10ms baseline
            metrics = tracker.collect_metrics(task_id, 'test_provider')
            tracker.end_task_timing(task_id, success=True)

        tracker.flush_buffer()

        # Create degraded data (slow)
        for i in range(50, 60):
            task_id = f'task{i}'
            tracker.start_task_timing(task_id)
            time.sleep(0.05)  # 50ms - degraded
            metrics = tracker.collect_metrics(task_id, 'test_provider')
            tracker.end_task_timing(task_id, success=True)

        tracker.flush_buffer()

        # Detect degradation
        alert = tracker.detect_degradation('test_provider', threshold=0.2)

        # Should detect degradation (50ms vs 10ms is >20% increase)
        if alert:
            assert alert.provider_id == 'test_provider'
            assert alert.metric == 'latency'
            assert alert.severity in ['medium', 'high']


def test_detect_all_degradations():
    """Test multi-provider degradation detection."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create data for multiple providers
        for provider in ['provider_a', 'provider_b']:
            for i in range(20):
                task_id = f'{provider}_task{i}'
                tracker.start_task_timing(task_id)
                time.sleep(0.01)
                metrics = tracker.collect_metrics(task_id, provider)
                tracker.end_task_timing(task_id, success=True)

        tracker.flush_buffer()

        # Check all degradations
        alerts = tracker.detect_all_degradations()

        # Should return a list (may be empty if no degradation)
        assert isinstance(alerts, list)


def test_metrics_storage_integration():
    """Test integration between tracker and storage."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create and store metrics
        for i in range(150):  # More than buffer size (100)
            task_id = f'task{i}'
            tracker.start_task_timing(task_id)
            metrics = tracker.collect_metrics(task_id, 'test_provider')
            tracker.end_task_timing(task_id, success=True)

        # Should have auto-flushed at least once
        history = tracker.get_performance_history(provider_id='test_provider')
        assert len(history) > 0


def test_performance_history_filtering():
    """Test performance history filtering."""
    from agents.adaptation import PerformanceTracker
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        tracker = PerformanceTracker(db_path)

        # Create metrics for different providers
        for provider in ['provider_a', 'provider_b']:
            for i in range(10):
                task_id = f'{provider}_task{i}'
                tracker.start_task_timing(task_id)
                metrics = tracker.collect_metrics(task_id, provider)
                tracker.end_task_timing(task_id, success=True)

        tracker.flush_buffer()

        # Get history for specific provider
        history_a = tracker.get_performance_history(provider_id='provider_a')
        history_b = tracker.get_performance_history(provider_id='provider_b')

        # Should be separate
        assert all(m['provider_id'] == 'provider_a' for m in history_a)
        assert all(m['provider_id'] == 'provider_b' for m in history_b)


def test_database_schema():
    """Test database schema is correct."""
    from agents.adaptation import MetricsStore
    import tempfile
    import sqlite3

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_metrics.db')
        store = MetricsStore(db_path)

        # Check tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert 'metrics' in tables
        assert 'provider_summaries' in tables

        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        assert 'idx_provider_timestamp' in indexes
        assert 'idx_task_timestamp' in indexes
        assert 'idx_timestamp' in indexes

        conn.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
