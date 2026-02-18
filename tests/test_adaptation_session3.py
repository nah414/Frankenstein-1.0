"""
Test Suite for Adaptation Engine - Session 3

Tests context learning, pattern recognition, EMA algorithms,
provider recommendations, and resource prediction.
"""

import pytest
import sys
import os
import json
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_context_learner_initialization():
    """Test ContextLearner initialization."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        assert learner.knowledge_base == {}
        assert learner.adaptation_history == []
        assert learner.storage_path == storage_path


def test_record_execution():
    """Test recording execution results."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Record successful execution
        learner.record_execution(
            task_type='quantum_simulation',
            provider_id='IBM_Quantum',
            metrics={'cpu_usage': 0.45, 'ram_usage': 250, 'duration': 12.3},
            success=True
        )

        pattern_key = 'quantum_simulation::IBM_Quantum'
        assert pattern_key in learner.knowledge_base
        assert learner.knowledge_base[pattern_key]['execution_count'] == 1
        assert learner.knowledge_base[pattern_key]['success_rate'] > 0.5  # EMA from 0.5 toward 1.0


def test_ema_learning():
    """Test exponential moving average learning."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Record multiple executions
        for i in range(10):
            learner.record_execution(
                task_type='test_task',
                provider_id='test_provider',
                metrics={'cpu_usage': 0.5, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

        pattern = learner.knowledge_base['test_task::test_provider']

        # Success rate should approach 1.0
        assert pattern['success_rate'] > 0.9
        assert pattern['execution_count'] == 10

        # Resource profile should be near input values
        assert 0.45 <= pattern['resource_profile']['avg_cpu'] <= 0.55
        assert 180 <= pattern['resource_profile']['avg_ram'] <= 220


def test_ema_with_mixed_results():
    """Test EMA with mixed success/failure."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Alternating pattern: more successes (15 success, 5 failures)
        for i in range(20):
            learner.record_execution(
                task_type='mixed_task',
                provider_id='test_provider',
                metrics={'cpu_usage': 0.4, 'ram_usage': 150, 'duration': 8.0},
                success=(i % 4 != 0)  # Fail every 4th execution (75% success)
            )

        pattern = learner.knowledge_base['mixed_task::test_provider']

        # Success rate should converge toward 0.75 with EMA
        # With ALPHA=0.3 starting from 0.5, it overshoots slightly due to recent bias
        assert 0.65 <= pattern['success_rate'] <= 0.90


def test_confidence_calculation():
    """Test multi-factor confidence scoring."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Low execution count = low confidence
        learner.record_execution(
            task_type='task1',
            provider_id='provider1',
            metrics={'cpu_usage': 0.3, 'ram_usage': 100, 'duration': 5.0},
            success=True
        )

        pattern = learner.knowledge_base['task1::provider1']
        confidence_low = learner._calculate_confidence(pattern)
        assert confidence_low < 0.5  # Low due to low execution count

        # High execution count = higher confidence
        for _ in range(19):
            learner.record_execution(
                task_type='task1',
                provider_id='provider1',
                metrics={'cpu_usage': 0.3, 'ram_usage': 100, 'duration': 5.0},
                success=True
            )

        confidence_high = learner._calculate_confidence(pattern)
        assert confidence_high > 0.8  # High due to many successful executions


def test_get_patterns_for_task():
    """Test retrieving patterns for a task type."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Record executions for multiple providers
        for provider in ['provider_a', 'provider_b', 'provider_c']:
            for _ in range(5):
                learner.record_execution(
                    task_type='quantum_sim',
                    provider_id=provider,
                    metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                    success=True
                )

        patterns = learner.get_patterns_for_task('quantum_sim')

        assert len(patterns) == 3
        # Should be sorted by confidence
        assert patterns[0]['confidence'] >= patterns[1]['confidence']
        assert patterns[1]['confidence'] >= patterns[2]['confidence']


def test_recommend_provider():
    """Test provider recommendation system."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Record good performance for provider_a
        for _ in range(20):
            learner.record_execution(
                task_type='optimization',
                provider_id='provider_a',
                metrics={'cpu_usage': 0.3, 'ram_usage': 150, 'duration': 8.0},
                success=True
            )

        # Record poor performance for provider_b
        for i in range(10):
            learner.record_execution(
                task_type='optimization',
                provider_id='provider_b',
                metrics={'cpu_usage': 0.6, 'ram_usage': 400, 'duration': 20.0},
                success=(i < 3)  # Only 30% success
            )

        # Get recommendation
        rec = learner.recommend_provider('optimization')

        assert rec is not None
        assert rec.provider_id == 'provider_a'  # Should recommend the better provider
        assert rec.confidence > 0.7
        assert rec.success_rate > 0.9


def test_recommend_provider_with_constraints():
    """Test provider recommendation with resource constraints."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Provider A: low resources, good performance
        for _ in range(15):
            learner.record_execution(
                task_type='task_x',
                provider_id='provider_a',
                metrics={'cpu_usage': 0.2, 'ram_usage': 100, 'duration': 5.0},
                success=True
            )

        # Provider B: high resources, good performance
        for _ in range(15):
            learner.record_execution(
                task_type='task_x',
                provider_id='provider_b',
                metrics={'cpu_usage': 0.8, 'ram_usage': 500, 'duration': 10.0},
                success=True
            )

        # Recommend with low resource constraint
        rec = learner.recommend_provider(
            'task_x',
            resource_constraints={'cpu_max': 0.5, 'ram_max': 200}
        )

        assert rec is not None
        assert rec.provider_id == 'provider_a'  # Only provider within constraints


def test_recommend_provider_no_data():
    """Test recommendation with no learned data."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        rec = learner.recommend_provider('unknown_task')
        assert rec is None


def test_predict_resource_needs_specific_provider():
    """Test resource prediction for specific provider."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Record consistent resource usage
        for _ in range(15):
            learner.record_execution(
                task_type='compute_task',
                provider_id='gpu_provider',
                metrics={'cpu_usage': 0.6, 'ram_usage': 300, 'duration': 15.0},
                success=True
            )

        prediction = learner.predict_resource_needs('compute_task', 'gpu_provider')

        assert prediction is not None
        assert 0.55 <= prediction.cpu <= 0.65
        assert 280 <= prediction.ram <= 320
        assert 14.0 <= prediction.duration <= 16.0
        assert prediction.confidence > 0.7


def test_predict_resource_needs_average():
    """Test resource prediction across all providers."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Multiple providers with different resource profiles
        for _ in range(10):
            learner.record_execution(
                task_type='task_y',
                provider_id='provider1',
                metrics={'cpu_usage': 0.3, 'ram_usage': 100, 'duration': 5.0},
                success=True
            )
            learner.record_execution(
                task_type='task_y',
                provider_id='provider2',
                metrics={'cpu_usage': 0.5, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

        prediction = learner.predict_resource_needs('task_y')

        assert prediction is not None
        # Should be weighted average
        assert 0.3 <= prediction.cpu <= 0.5
        assert 100 <= prediction.ram <= 200


def test_record_adaptation():
    """Test recording adaptation results."""
    from agents.adaptation import ContextLearner, AdaptationResult
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        result = AdaptationResult(
            success=True,
            reason='latency_spike',
            details={'old_provider': 'provider_a', 'new_provider': 'provider_b'}
        )

        learner.record_adaptation('task_123', result)

        assert len(learner.adaptation_history) == 1
        assert learner.adaptation_history[0]['task_id'] == 'task_123'
        assert learner.adaptation_history[0]['success'] is True


def test_analyze_execution_patterns():
    """Test pattern analysis and insights."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # High performer
        for _ in range(25):
            learner.record_execution(
                task_type='task_a',
                provider_id='excellent_provider',
                metrics={'cpu_usage': 0.3, 'ram_usage': 100, 'duration': 5.0},
                success=True
            )

        # Underperformer
        for i in range(15):
            learner.record_execution(
                task_type='task_b',
                provider_id='poor_provider',
                metrics={'cpu_usage': 0.7, 'ram_usage': 400, 'duration': 20.0},
                success=(i < 5)  # 33% success rate
            )

        insights = learner.analyze_execution_patterns()

        # Should identify high performer
        high_perf = next((i for i in insights if i['type'] == 'high_performers'), None)
        assert high_perf is not None
        assert high_perf['count'] >= 1

        # Should identify underperformer
        under_perf = next((i for i in insights if i['type'] == 'underperformers'), None)
        assert under_perf is not None
        assert under_perf['count'] >= 1


def test_json_persistence():
    """Test knowledge base persistence to JSON."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')

        # Create and populate learner
        learner1 = ContextLearner(storage_path)
        for _ in range(10):
            learner1.record_execution(
                task_type='persistent_task',
                provider_id='provider_x',
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

        # Verify JSON file exists
        assert os.path.exists(storage_path)

        # Load from file
        learner2 = ContextLearner(storage_path)

        # Should have loaded the pattern
        assert 'persistent_task::provider_x' in learner2.knowledge_base
        assert learner2.knowledge_base['persistent_task::provider_x']['execution_count'] == 10


def test_clear_stale_patterns():
    """Test removing stale patterns."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Add pattern and manually set old timestamp
        learner.record_execution(
            task_type='old_task',
            provider_id='old_provider',
            metrics={'cpu_usage': 0.3, 'ram_usage': 100, 'duration': 5.0},
            success=True
        )

        # Manually set to 100 days old
        pattern = learner.knowledge_base['old_task::old_provider']
        old_date = datetime.now() - timedelta(days=100)
        pattern['last_updated'] = old_date.isoformat()
        learner._save_knowledge()

        # Clear stale patterns (90+ days)
        learner.clear_stale_patterns(days_old=90)

        # Should be removed
        assert 'old_task::old_provider' not in learner.knowledge_base


def test_recency_factor():
    """Test recency factor in confidence calculation."""
    from agents.adaptation import ContextLearner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, 'knowledge.json')
        learner = ContextLearner(storage_path)

        # Record execution
        for _ in range(20):
            learner.record_execution(
                task_type='recent_task',
                provider_id='provider_z',
                metrics={'cpu_usage': 0.4, 'ram_usage': 200, 'duration': 10.0},
                success=True
            )

        pattern = learner.knowledge_base['recent_task::provider_z']
        confidence_recent = learner._calculate_confidence(pattern)

        # Manually age the pattern
        old_date = datetime.now() - timedelta(days=60)  # 60 days old (2 half-lives)
        pattern['last_updated'] = old_date.isoformat()
        confidence_old = learner._calculate_confidence(pattern)

        # Confidence should be lower for older pattern
        assert confidence_old < confidence_recent


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
