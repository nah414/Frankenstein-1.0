"""
Real-Time Adaptation Module for Frankenstein 1.0

This module provides dynamic system optimization based on runtime conditions.
ALL components are lazy-loaded to ensure zero startup overhead.

Usage:
    # Get adaptation engine (lazy-loaded)
    from agents.adaptation import get_adaptation_engine

    engine = get_adaptation_engine(initialize=True)
    engine.start_monitoring()

    # Monitor execution
    metrics = engine.monitor_execution(task_id, provider_id)

    # Trigger adaptation
    result = engine.trigger_adaptation(task_id, reason)

Safety Constraints (HARD-CODED):
    - CPU_MAX: 80%
    - RAM_MAX: 70%
    - Adaptation CPU budget: 5%
    - Adaptation RAM budget: 50MB
    - Minimum adaptation interval: 5 seconds
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global singleton instance (lazy-loaded)
_adaptation_engine_instance = None


def get_adaptation_engine(initialize: bool = False):
    """
    Get the adaptation engine instance (lazy-loaded singleton).

    Args:
        initialize: If True, create instance if it doesn't exist.
                   If False, return None if not yet created.

    Returns:
        AdaptationEngine instance or None
    """
    global _adaptation_engine_instance

    if not initialize:
        return _adaptation_engine_instance

    if _adaptation_engine_instance is None:
        logger.info("Lazy-loading AdaptationEngine...")
        from .adaptation_engine import AdaptationEngine
        _adaptation_engine_instance = AdaptationEngine()
        logger.info("AdaptationEngine loaded successfully")

    return _adaptation_engine_instance


def reset_adaptation_engine():
    """
    Reset the adaptation engine instance.

    Used primarily for testing.
    """
    global _adaptation_engine_instance
    if _adaptation_engine_instance:
        if _adaptation_engine_instance.monitoring_active:
            _adaptation_engine_instance.stop_monitoring()
    _adaptation_engine_instance = None
    logger.info("AdaptationEngine reset")


# Export key classes for direct import (when needed)
__all__ = [
    'get_adaptation_engine',
    'reset_adaptation_engine',
]


# Make classes available for direct import, but don't instantiate
def __getattr__(name):
    """
    Lazy import of classes to avoid startup overhead.

    This allows 'from agents.adaptation import AdaptationEngine'
    without loading the module at startup.
    """
    if name == 'AdaptationEngine':
        from .adaptation_engine import AdaptationEngine
        return AdaptationEngine
    elif name == 'PerformanceTracker':
        from .performance_tracker import PerformanceTracker
        return PerformanceTracker
    elif name == 'MetricsStore':
        from .metrics_store import MetricsStore
        return MetricsStore
    elif name == 'ContextLearner':
        from .context_learner import ContextLearner
        return ContextLearner
    elif name == 'AdaptiveRouter':
        from .adaptive_router import AdaptiveRouter
        return AdaptiveRouter
    elif name == 'AdaptationResult':
        from .adaptation_engine import AdaptationResult
        return AdaptationResult
    elif name == 'TrendAnalysis':
        from .performance_tracker import TrendAnalysis
        return TrendAnalysis
    elif name == 'DegradationAlert':
        from .performance_tracker import DegradationAlert
        return DegradationAlert
    elif name == 'ProviderRecommendation':
        from .context_learner import ProviderRecommendation
        return ProviderRecommendation
    elif name == 'ResourcePrediction':
        from .context_learner import ResourcePrediction
        return ResourcePrediction
    elif name == 'RoutingDecision':
        from .adaptive_router import RoutingDecision
        return RoutingDecision
    elif name == 'ProviderHealth':
        from .adaptive_router import ProviderHealth
        return ProviderHealth
    elif name == 'ProviderHealthStatus':
        from .adaptive_router import ProviderHealthStatus
        return ProviderHealthStatus
    elif name == 'get_adaptation_commands':
        from .adaptation_commands import get_adaptation_commands
        return get_adaptation_commands
    elif name == 'AdaptationCommands':
        from .adaptation_commands import AdaptationCommands
        return AdaptationCommands

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
