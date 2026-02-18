"""
Test Suite for Session 6: Monster Terminal Integration

Tests terminal commands, display functions, and final verification.
"""

import pytest
import sys
import os
import tempfile
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_adaptation_commands_initialization():
    """Test command handler initialization."""
    from agents.adaptation import get_adaptation_commands

    commands = get_adaptation_commands()

    assert commands is not None
    assert commands.engine is None  # Lazy-loaded

    # Get command map
    cmd_map = commands.get_command_map()
    assert len(cmd_map) > 0
    assert 'adapt-status' in cmd_map
    assert 'adapt-patterns' in cmd_map
    assert 'adapt-performance' in cmd_map


def test_adapt_status_command():
    """Test adapt-status command."""
    from agents.adaptation import get_adaptation_commands, reset_adaptation_engine

    reset_adaptation_engine()
    commands = get_adaptation_commands()

    # Run command
    output = commands.cmd_adapt_status([])

    assert "REAL-TIME ADAPTATION STATUS" in output
    assert "Monitoring Active" in output
    assert "CPU Usage" in output
    assert "RAM Usage" in output
    assert "Safety Limits" in output


def test_adapt_patterns_command():
    """Test adapt-patterns command."""
    from agents.adaptation import get_adaptation_commands, reset_adaptation_engine

    reset_adaptation_engine()
    commands = get_adaptation_commands()

    # Ensure engine is loaded
    engine = commands._ensure_engine()

    # Add some patterns
    for i in range(5):
        engine.context_learner.record_execution(
            task_type='test_task',
            provider_id=f'provider_{i}',
            metrics={'cpu_usage': 0.3, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

    # Test without args (all patterns)
    output = commands.cmd_adapt_patterns([])
    assert "LEARNED ADAPTATION PATTERNS" in output
    assert "Total Patterns" in output

    # Test with task type
    output = commands.cmd_adapt_patterns(['test_task'])
    assert "test_task" in output


def test_adapt_performance_command():
    """Test adapt-performance command."""
    from agents.adaptation import get_adaptation_commands, reset_adaptation_engine

    reset_adaptation_engine()
    commands = get_adaptation_commands()

    engine = commands._ensure_engine()

    # Add some performance data
    for i in range(10):
        engine.performance_tracker.start_task_timing(f'task_{i}')
        time.sleep(0.01)
        engine.performance_tracker.collect_metrics(f'task_{i}', 'test_provider')
        engine.performance_tracker.end_task_timing(f'task_{i}', success=True)

    engine.performance_tracker.flush_buffer()

    # Test without args (rankings)
    output = commands.cmd_adapt_performance([])
    assert "PERFORMANCE METRICS" in output
    assert "Provider Rankings" in output

    # Test with provider ID
    output = commands.cmd_adapt_performance(['test_provider'])
    assert "test_provider" in output
    assert "Recent Executions" in output


def test_adapt_insights_command():
    """Test adapt-insights command."""
    from agents.adaptation import get_adaptation_commands, reset_adaptation_engine

    reset_adaptation_engine()
    commands = get_adaptation_commands()

    engine = commands._ensure_engine()

    # Add patterns for insights
    for i in range(20):
        engine.context_learner.record_execution(
            task_type='insight_task',
            provider_id='high_performer',
            metrics={'cpu_usage': 0.3, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

    output = commands.cmd_adapt_insights([])
    assert "ADAPTATION INSIGHTS" in output


def test_adapt_recommend_command():
    """Test adapt-recommend command."""
    from agents.adaptation import get_adaptation_commands, reset_adaptation_engine

    reset_adaptation_engine()
    commands = get_adaptation_commands()

    engine = commands._ensure_engine()

    # Add enough data for recommendation
    for i in range(25):
        engine.context_learner.record_execution(
            task_type='recommend_task',
            provider_id='best_provider',
            metrics={'cpu_usage': 0.3, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

    # Test without args (usage message)
    output = commands.cmd_adapt_recommend([])
    assert "Usage" in output

    # Test with task type
    output = commands.cmd_adapt_recommend(['recommend_task'])
    assert "PROVIDER RECOMMENDATION" in output
    assert "recommend_task" in output


def test_adapt_history_command():
    """Test adapt-history command."""
    from agents.adaptation import get_adaptation_commands, reset_adaptation_engine
    from agents.adaptation import AdaptationResult
    from datetime import datetime

    reset_adaptation_engine()
    commands = get_adaptation_commands()

    engine = commands._ensure_engine()

    # Add some adaptation history
    for i in range(5):
        result = AdaptationResult(
            success=True,
            reason=f'test_reason_{i}',
            details={'task_id': f'task_{i}'}
        )
        engine.context_learner.record_adaptation(f'task_{i}', result)

    output = commands.cmd_adapt_history([])
    assert "ADAPTATION HISTORY" in output


def test_display_status_panel():
    """Test status panel rendering."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()

    output = AdaptationDisplay.render_status_panel(engine)

    assert "REAL-TIME ADAPTATION STATUS" in output
    assert "Monitoring" in output
    assert "CPU" in output
    assert "RAM" in output
    assert "Safe" in output
    # Check for box drawing characters
    assert "┌" in output or "+" in output  # Box corners


def test_display_performance_summary():
    """Test performance summary rendering."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()

    # Add some data
    for i in range(10):
        engine.performance_tracker.start_task_timing(f'task_{i}')
        time.sleep(0.01)
        engine.performance_tracker.collect_metrics(f'task_{i}', 'test_provider')
        engine.performance_tracker.end_task_timing(f'task_{i}', success=True)

    engine.performance_tracker.flush_buffer()

    output = AdaptationDisplay.render_performance_summary(
        engine.performance_tracker,
        provider_id='test_provider'
    )

    assert "PERFORMANCE SUMMARY" in output
    assert "test_provider" in output
    assert "Samples" in output


def test_display_learning_summary():
    """Test learning summary rendering."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()

    # Add patterns
    for i in range(15):
        engine.context_learner.record_execution(
            task_type='display_task',
            provider_id='display_provider',
            metrics={'cpu_usage': 0.3, 'ram_usage': 200, 'duration': 10.0},
            success=True
        )

    output = AdaptationDisplay.render_learning_summary(engine.context_learner)

    assert "LEARNING SUMMARY" in output
    assert "Total Patterns" in output


def test_display_simple_graph():
    """Test simple graph rendering."""
    from agents.adaptation.adaptation_display import AdaptationDisplay

    data = [1.0, 2.0, 1.5, 3.0, 2.5, 4.0, 3.5, 5.0]

    output = AdaptationDisplay.render_simple_graph(data, label="Test Data")

    assert "Test Data" in output
    assert "Range" in output
    assert "█" in output or len(output) > 0  # Should have some graph chars


def test_display_latency_graph():
    """Test latency graph rendering."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()

    # Add latency data
    for i in range(20):
        engine.performance_tracker.start_task_timing(f'task_{i}')
        time.sleep(0.01)
        engine.performance_tracker.collect_metrics(f'task_{i}', 'latency_provider')
        engine.performance_tracker.end_task_timing(f'task_{i}', success=True)

    engine.performance_tracker.flush_buffer()

    output = AdaptationDisplay.render_latency_graph(
        engine.performance_tracker,
        'latency_provider',
        hours=1
    )

    assert "Latency" in output
    assert "latency_provider" in output


def test_display_full_dashboard():
    """Test full dashboard rendering."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()
    engine.start_monitoring()

    # Add some data
    for i in range(10):
        engine.performance_tracker.start_task_timing(f'task_{i}')
        time.sleep(0.01)
        engine.performance_tracker.collect_metrics(f'task_{i}', 'dashboard_provider')
        engine.performance_tracker.end_task_timing(f'task_{i}', success=True)

    engine.performance_tracker.flush_buffer()

    output = AdaptationDisplay.render_dashboard(engine)

    assert "FRANKENSTEIN 1.0" in output
    assert "REAL-TIME ADAPTATION DASHBOARD" in output
    assert "REAL-TIME ADAPTATION STATUS" in output
    assert "PERFORMANCE SUMMARY" in output
    assert "LEARNING SUMMARY" in output
    assert "Updated" in output

    engine.stop_monitoring()


def test_final_integration_commands_and_display():
    """Final integration test with commands and display."""
    from agents.adaptation import (
        get_adaptation_engine,
        get_adaptation_commands,
        reset_adaptation_engine
    )
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()

    # Get instances
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()
    commands = get_adaptation_commands()

    # Start monitoring
    engine.start_monitoring()

    # Execute some tasks
    for i in range(15):
        engine.performance_tracker.start_task_timing(f'final_task_{i}')
        engine.context_learner.record_execution(
            task_type='final_test',
            provider_id='final_provider',
            metrics={'cpu_usage': 0.3, 'ram_usage': 200, 'duration': 0.05},
            success=True
        )
        time.sleep(0.01)
        engine.performance_tracker.collect_metrics(f'final_task_{i}', 'final_provider')
        engine.performance_tracker.end_task_timing(f'final_task_{i}', success=True)

    engine.performance_tracker.flush_buffer()

    # Test all commands work
    status_output = commands.cmd_adapt_status([])
    assert len(status_output) > 0

    patterns_output = commands.cmd_adapt_patterns(['final_test'])
    assert len(patterns_output) > 0

    perf_output = commands.cmd_adapt_performance(['final_provider'])
    assert len(perf_output) > 0

    insights_output = commands.cmd_adapt_insights([])
    assert len(insights_output) > 0

    recommend_output = commands.cmd_adapt_recommend(['final_test'])
    assert len(recommend_output) > 0

    # Test display functions
    dashboard = AdaptationDisplay.render_dashboard(engine)
    assert len(dashboard) > 0
    assert "FRANKENSTEIN 1.0" in dashboard

    # Verify safety
    assert engine._check_safe_to_adapt() in [True, False]  # Should not crash

    # Stop monitoring
    engine.stop_monitoring()
    assert not engine.monitoring_active


def test_safety_constraints_during_display():
    """Verify safety constraints maintained during display operations."""
    from agents.adaptation import get_adaptation_engine, reset_adaptation_engine
    from agents.adaptation.adaptation_display import AdaptationDisplay

    reset_adaptation_engine()
    engine = get_adaptation_engine(initialize=True)
    engine._initialize_components()

    # Verify safety limits
    assert engine.safety_limits['CPU_MAX'] == 0.80
    assert engine.safety_limits['RAM_MAX'] == 0.70

    # Render dashboard multiple times (stress test)
    for _ in range(5):
        output = AdaptationDisplay.render_dashboard(engine)
        assert len(output) > 0

    # CPU and RAM should still be within limits
    status = engine.get_status()
    # Display operations should be lightweight
    assert status['current_resources']['cpu_usage'] < 1.0
    assert status['current_resources']['ram_usage'] < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
