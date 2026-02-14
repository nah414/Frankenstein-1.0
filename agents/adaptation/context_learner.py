"""
Context Learner for Real-Time Adaptation

Learns from execution patterns and provides intelligent recommendations
for provider selection and resource allocation. Uses exponential moving
averages for continuous learning and multi-factor confidence scoring.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import os
import logging

logger = logging.getLogger(__name__)

# Learning parameters
ALPHA = 0.3  # EMA weighting factor (30% new, 70% old)
CONFIDENCE_CAP_EXECUTIONS = 20  # Max executions for base confidence
RECENCY_HALF_LIFE_DAYS = 30  # 30-day half-life for recency factor


@dataclass
class ProviderRecommendation:
    """Recommendation for provider selection."""
    provider_id: str
    confidence: float  # 0.0 to 1.0
    reason: str
    resource_estimate: Dict[str, float]
    success_rate: float
    execution_count: int


@dataclass
class ResourcePrediction:
    """Predicted resource needs for a task."""
    cpu: float
    ram: float  # MB
    duration: float  # seconds
    confidence: float
    sample_count: int


class ContextLearner:
    """
    Pattern learning and recommendation system.

    Learns from execution history using exponential moving averages
    and provides intelligent recommendations with confidence scoring.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize context learner.

        Args:
            storage_path: Path to knowledge storage file (JSON)
        """
        self.storage_path = storage_path or self._get_default_storage_path()
        self.knowledge_base = {}  # Pattern key -> Pattern data
        self.adaptation_history = []  # Recent adaptations

        # Load existing knowledge
        self._load_knowledge()

        logger.info(f"ContextLearner initialized (storage: {self.storage_path})")

    def record_execution(
        self,
        task_type: str,
        provider_id: str,
        metrics: Dict[str, Any],
        success: bool
    ):
        """
        Learn from task execution.

        Args:
            task_type: Type of task executed
            provider_id: Provider that handled task
            metrics: Execution metrics (cpu_usage, ram_usage, duration, etc.)
            success: Whether task succeeded
        """
        pattern_key = f"{task_type}::{provider_id}"

        # Get or create pattern
        if pattern_key not in self.knowledge_base:
            self.knowledge_base[pattern_key] = self._create_new_pattern(
                task_type, provider_id
            )

        pattern = self.knowledge_base[pattern_key]

        # Update execution count
        pattern['execution_count'] += 1

        # Update success rate using EMA
        old_success_rate = pattern['success_rate']
        new_observation = 1.0 if success else 0.0
        pattern['success_rate'] = (
            ALPHA * new_observation + (1 - ALPHA) * old_success_rate
        )

        # Update resource profile using EMA
        self._update_resource_profile(pattern['resource_profile'], metrics)

        # Update timestamp
        pattern['last_updated'] = datetime.now().isoformat()

        # Persist knowledge
        self._save_knowledge()

        logger.debug(f"Recorded execution: {pattern_key}, success={success}")

    def record_adaptation(self, task_id: str, result: Any):
        """
        Learn from adaptation results.

        Args:
            task_id: Task that was adapted
            result: AdaptationResult object
        """
        adaptation_record = {
            'task_id': task_id,
            'success': result.success,
            'reason': result.reason,
            'details': result.details,
            'timestamp': result.timestamp.isoformat()
        }

        self.adaptation_history.append(adaptation_record)

        # Keep only recent 100 adaptations
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-100:]

        logger.debug(f"Recorded adaptation: {task_id}, success={result.success}")

    def get_patterns_for_task(self, task_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve learned patterns for a task type.

        Args:
            task_type: Type of task to query

        Returns:
            List of patterns matching task type
        """
        patterns = []

        for pattern_key, pattern_data in self.knowledge_base.items():
            if pattern_data['task_type'] == task_type:
                # Calculate current confidence
                confidence = self._calculate_confidence(pattern_data)
                pattern_with_confidence = pattern_data.copy()
                pattern_with_confidence['confidence'] = confidence
                patterns.append(pattern_with_confidence)

        # Sort by confidence (highest first)
        patterns.sort(key=lambda x: x['confidence'], reverse=True)

        return patterns

    def recommend_provider(
        self,
        task_type: str,
        resource_constraints: Optional[Dict[str, float]] = None
    ) -> Optional[ProviderRecommendation]:
        """
        Recommend optimal provider for a task type.

        Args:
            task_type: Type of task
            resource_constraints: Optional resource limits (cpu_max, ram_max)

        Returns:
            ProviderRecommendation or None if no suitable provider
        """
        patterns = self.get_patterns_for_task(task_type)

        if not patterns:
            logger.debug(f"No learned patterns for task type: {task_type}")
            return None

        # Filter by resource constraints if provided
        if resource_constraints:
            patterns = self._filter_by_constraints(patterns, resource_constraints)

        if not patterns:
            logger.debug(f"No providers match resource constraints")
            return None

        # Get best pattern (highest confidence)
        best_pattern = patterns[0]

        # Build recommendation
        recommendation = ProviderRecommendation(
            provider_id=best_pattern['provider_id'],
            confidence=best_pattern['confidence'],
            reason=self._generate_recommendation_reason(best_pattern),
            resource_estimate={
                'cpu': best_pattern['resource_profile']['avg_cpu'],
                'ram': best_pattern['resource_profile']['avg_ram'],
                'duration': best_pattern['resource_profile']['avg_duration']
            },
            success_rate=best_pattern['success_rate'],
            execution_count=best_pattern['execution_count']
        )

        logger.info(f"Recommended {recommendation.provider_id} for {task_type} "
                   f"(confidence: {recommendation.confidence:.2f})")

        return recommendation

    def predict_resource_needs(
        self,
        task_type: str,
        provider_id: Optional[str] = None
    ) -> Optional[ResourcePrediction]:
        """
        Predict resource needs for a task.

        Args:
            task_type: Type of task
            provider_id: Specific provider (optional)

        Returns:
            ResourcePrediction or None
        """
        if provider_id:
            # Predict for specific provider
            pattern_key = f"{task_type}::{provider_id}"
            if pattern_key not in self.knowledge_base:
                return None

            pattern = self.knowledge_base[pattern_key]
            confidence = self._calculate_confidence(pattern)

            return ResourcePrediction(
                cpu=pattern['resource_profile']['avg_cpu'],
                ram=pattern['resource_profile']['avg_ram'],
                duration=pattern['resource_profile']['avg_duration'],
                confidence=confidence,
                sample_count=pattern['resource_profile']['sample_count']
            )
        else:
            # Predict across all providers (average)
            patterns = self.get_patterns_for_task(task_type)
            if not patterns:
                return None

            # Weighted average by confidence
            total_weight = sum(p['confidence'] for p in patterns)
            if total_weight == 0:
                return None

            avg_cpu = sum(p['resource_profile']['avg_cpu'] * p['confidence']
                         for p in patterns) / total_weight
            avg_ram = sum(p['resource_profile']['avg_ram'] * p['confidence']
                         for p in patterns) / total_weight
            avg_duration = sum(p['resource_profile']['avg_duration'] * p['confidence']
                              for p in patterns) / total_weight

            total_samples = sum(p['resource_profile']['sample_count'] for p in patterns)
            avg_confidence = sum(p['confidence'] for p in patterns) / len(patterns)

            return ResourcePrediction(
                cpu=avg_cpu,
                ram=avg_ram,
                duration=avg_duration,
                confidence=avg_confidence,
                sample_count=total_samples
            )

    def analyze_execution_patterns(self, window_size: int = 100) -> List[Dict[str, Any]]:
        """
        Analyze execution patterns for insights.

        Args:
            window_size: Number of recent executions to analyze

        Returns:
            List of insights and patterns
        """
        insights = []

        # Identify high-performing providers
        high_performers = []
        for pattern_key, pattern in self.knowledge_base.items():
            confidence = self._calculate_confidence(pattern)
            if confidence > 0.7 and pattern['success_rate'] > 0.9:
                high_performers.append({
                    'pattern_key': pattern_key,
                    'provider_id': pattern['provider_id'],
                    'task_type': pattern['task_type'],
                    'success_rate': pattern['success_rate'],
                    'confidence': confidence,
                    'execution_count': pattern['execution_count']
                })

        if high_performers:
            insights.append({
                'type': 'high_performers',
                'count': len(high_performers),
                'providers': high_performers
            })

        # Identify underperformers
        underperformers = []
        for pattern_key, pattern in self.knowledge_base.items():
            if pattern['execution_count'] >= 10 and pattern['success_rate'] < 0.7:
                underperformers.append({
                    'pattern_key': pattern_key,
                    'provider_id': pattern['provider_id'],
                    'task_type': pattern['task_type'],
                    'success_rate': pattern['success_rate'],
                    'execution_count': pattern['execution_count']
                })

        if underperformers:
            insights.append({
                'type': 'underperformers',
                'count': len(underperformers),
                'providers': underperformers
            })

        # Analyze adaptation history
        if self.adaptation_history:
            recent_adaptations = self.adaptation_history[-window_size:]
            success_rate = sum(1 for a in recent_adaptations if a['success']) / len(recent_adaptations)

            insights.append({
                'type': 'adaptation_effectiveness',
                'total_adaptations': len(recent_adaptations),
                'success_rate': success_rate,
                'recent_reasons': [a['reason'] for a in recent_adaptations[-10:]]
            })

        return insights

    def clear_stale_patterns(self, days_old: int = 90):
        """
        Remove patterns older than specified days.

        Args:
            days_old: Age threshold in days
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        stale_keys = []

        for pattern_key, pattern in self.knowledge_base.items():
            last_updated = datetime.fromisoformat(pattern['last_updated'])
            if last_updated < cutoff_date:
                stale_keys.append(pattern_key)

        for key in stale_keys:
            del self.knowledge_base[key]

        if stale_keys:
            self._save_knowledge()
            logger.info(f"Cleared {len(stale_keys)} stale patterns")

    # Private methods

    def _get_default_storage_path(self) -> str:
        """Get default storage path for knowledge base."""
        home = os.path.expanduser('~')
        data_dir = os.path.join(home, '.frankenstein', 'data', 'adaptation')
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, 'knowledge_base.json')

    def _create_new_pattern(self, task_type: str, provider_id: str) -> Dict[str, Any]:
        """Create a new pattern entry."""
        return {
            'task_type': task_type,
            'provider_id': provider_id,
            'execution_count': 0,
            'success_rate': 0.5,  # Start neutral
            'resource_profile': {
                'avg_cpu': 0.0,
                'avg_ram': 0.0,
                'avg_duration': 0.0,
                'sample_count': 0
            },
            'last_updated': datetime.now().isoformat()
        }

    def _update_resource_profile(self, profile: Dict[str, Any], metrics: Dict[str, Any]):
        """Update resource profile using EMA."""
        sample_count = profile['sample_count']

        # Extract metrics
        cpu = metrics.get('cpu_usage', 0.0)
        ram = metrics.get('ram_usage', 0.0)  # Should be in MB
        duration = metrics.get('duration', 0.0)

        if sample_count == 0:
            # First sample
            profile['avg_cpu'] = cpu
            profile['avg_ram'] = ram
            profile['avg_duration'] = duration
        else:
            # EMA update
            profile['avg_cpu'] = ALPHA * cpu + (1 - ALPHA) * profile['avg_cpu']
            profile['avg_ram'] = ALPHA * ram + (1 - ALPHA) * profile['avg_ram']
            profile['avg_duration'] = ALPHA * duration + (1 - ALPHA) * profile['avg_duration']

        profile['sample_count'] = sample_count + 1

    def _calculate_confidence(self, pattern: Dict[str, Any]) -> float:
        """
        Calculate confidence score for a pattern.

        Multi-factor calculation:
        - Base confidence: execution count (caps at 20)
        - Success factor: current success rate
        - Recency factor: exponential decay (30-day half-life)
        """
        # Base confidence (0 to 1, caps at 20 executions)
        execution_count = pattern['execution_count']
        base_confidence = min(execution_count / CONFIDENCE_CAP_EXECUTIONS, 1.0)

        # Success factor (0 to 1)
        success_factor = pattern['success_rate']

        # Recency factor (exponential decay)
        last_updated = datetime.fromisoformat(pattern['last_updated'])
        days_old = (datetime.now() - last_updated).days
        recency_factor = 0.5 ** (days_old / RECENCY_HALF_LIFE_DAYS)

        # Composite confidence (weighted average)
        composite_confidence = (
            base_confidence * 0.4 +
            success_factor * 0.4 +
            recency_factor * 0.2
        )

        return composite_confidence

    def _filter_by_constraints(
        self,
        patterns: List[Dict[str, Any]],
        constraints: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Filter patterns by resource constraints."""
        filtered = []

        cpu_max = constraints.get('cpu_max', 1.0)
        ram_max = constraints.get('ram_max', float('inf'))

        for pattern in patterns:
            profile = pattern['resource_profile']
            if profile['avg_cpu'] <= cpu_max and profile['avg_ram'] <= ram_max:
                filtered.append(pattern)

        return filtered

    def _generate_recommendation_reason(self, pattern: Dict[str, Any]) -> str:
        """Generate human-readable recommendation reason."""
        success_rate = pattern['success_rate']
        execution_count = pattern['execution_count']
        confidence = pattern['confidence']

        if confidence > 0.9:
            return f"High confidence based on {execution_count} successful executions ({success_rate:.1%} success rate)"
        elif confidence > 0.7:
            return f"Good track record with {execution_count} executions ({success_rate:.1%} success rate)"
        elif confidence > 0.5:
            return f"Moderate confidence from {execution_count} executions ({success_rate:.1%} success rate)"
        else:
            return f"Limited data ({execution_count} executions, {success_rate:.1%} success rate)"

    def _load_knowledge(self):
        """Load knowledge base from JSON storage."""
        if not os.path.exists(self.storage_path):
            logger.debug("No existing knowledge base found")
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.knowledge_base = data.get('patterns', {})
                self.adaptation_history = data.get('adaptation_history', [])

            logger.info(f"Loaded {len(self.knowledge_base)} patterns from storage")
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            self.knowledge_base = {}
            self.adaptation_history = []

    def _save_knowledge(self):
        """Save knowledge base to JSON storage."""
        try:
            data = {
                'patterns': self.knowledge_base,
                'adaptation_history': self.adaptation_history,
                'last_saved': datetime.now().isoformat()
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Knowledge base saved")
        except Exception as e:
            logger.error(f"Error saving knowledge base: {e}")
