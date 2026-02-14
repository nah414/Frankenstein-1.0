"""
Terminal Commands for Real-Time Adaptation

Provides command-line interface for monitoring and controlling
the adaptation system from the Frankenstein Terminal.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AdaptationCommands:
    """
    Terminal command handlers for adaptation system.

    Provides CLI interface for:
    - Viewing adaptation status
    - Checking learned patterns
    - Monitoring performance metrics
    - Triggering manual adaptations
    """

    def __init__(self):
        """Initialize command handler."""
        self.engine = None  # Lazy-loaded
        logger.debug("AdaptationCommands initialized (lazy)")

    def _ensure_engine(self):
        """Ensure adaptation engine is loaded."""
        if self.engine is None:
            from . import get_adaptation_engine
            self.engine = get_adaptation_engine(initialize=True)
            # Ensure components are loaded
            if self.engine.performance_tracker is None:
                self.engine._initialize_components()
        return self.engine

    def cmd_adapt_status(self, args: List[str]) -> str:
        """
        Display current adaptation status.

        Usage: adapt-status

        Returns:
            Formatted status string
        """
        engine = self._ensure_engine()
        status = engine.get_status()

        output = []
        output.append("=" * 60)
        output.append("REAL-TIME ADAPTATION STATUS")
        output.append("=" * 60)
        output.append(f"Monitoring Active: {'YES' if status['monitoring_active'] else 'NO'}")
        output.append(f"Total Adaptations: {status['adaptation_count']}")
        output.append(f"Concurrent:        {status['concurrent_adaptations']}")
        output.append(f"CPU Usage:         {status['current_resources']['cpu_usage']:.1%}")
        output.append(f"RAM Usage:         {status['current_resources']['ram_usage']:.1%}")
        output.append("")

        # Safety status
        safe_to_adapt = engine._check_safe_to_adapt()
        output.append("Safety Limits:")
        output.append(f"  CPU:  {status['current_resources']['cpu_usage']:.1%} / {status['safety_limits']['CPU_MAX']:.0%} (Safe: {safe_to_adapt})")
        output.append(f"  RAM:  {status['current_resources']['ram_usage']:.1%} / {status['safety_limits']['RAM_MAX']:.0%} (Safe: {safe_to_adapt})")
        output.append("=" * 60)

        return "\n".join(output)

    def cmd_adapt_patterns(self, args: List[str]) -> str:
        """
        Display learned patterns.

        Usage: adapt-patterns [task_type]

        Args:
            args: Optional task type filter

        Returns:
            Formatted patterns string
        """
        engine = self._ensure_engine()

        task_type = args[0] if args else None

        output = []
        output.append("=" * 60)
        output.append("LEARNED ADAPTATION PATTERNS")
        output.append("=" * 60)

        if task_type:
            patterns = engine.context_learner.get_patterns_for_task(task_type)
            output.append(f"Task Type: {task_type}")
            output.append("")

            if patterns:
                for pattern in patterns[:10]:  # Top 10
                    output.append(f"Provider: {pattern['provider_id']}")
                    output.append(f"  Confidence:   {pattern['confidence']:.1%}")
                    output.append(f"  Success Rate: {pattern['success_rate']:.1%}")
                    output.append(f"  Executions:   {pattern['execution_count']}")
                    output.append(f"  Avg CPU:      {pattern['resource_profile']['avg_cpu']:.1%}")
                    output.append(f"  Avg RAM:      {pattern['resource_profile']['avg_ram']:.0f} MB")
                    output.append("")
            else:
                output.append(f"No learned patterns for task type: {task_type}")
        else:
            # Show all patterns summary
            all_patterns = engine.context_learner.knowledge_base
            output.append(f"Total Patterns: {len(all_patterns)}")
            output.append("")

            # Group by task type
            by_task = {}
            for key, pattern in all_patterns.items():
                task = pattern['task_type']
                if task not in by_task:
                    by_task[task] = []
                by_task[task].append(pattern)

            for task, patterns in sorted(by_task.items()):
                output.append(f"Task: {task}")
                output.append(f"  Providers: {len(patterns)}")
                output.append(f"  Total Executions: {sum(p['execution_count'] for p in patterns)}")
                output.append("")

        output.append("=" * 60)
        return "\n".join(output)

    def cmd_adapt_performance(self, args: List[str]) -> str:
        """
        Display performance metrics and rankings.

        Usage: adapt-performance [provider_id]

        Args:
            args: Optional provider ID filter

        Returns:
            Formatted performance string
        """
        engine = self._ensure_engine()

        provider_id = args[0] if args else None

        output = []
        output.append("=" * 60)
        output.append("PERFORMANCE METRICS")
        output.append("=" * 60)

        if provider_id:
            # Show specific provider
            history = engine.performance_tracker.get_performance_history(
                provider_id=provider_id,
                window_hours=1
            )

            output.append(f"Provider: {provider_id}")
            output.append(f"Recent Executions: {len(history)}")
            output.append("")

            if history:
                avg_latency = sum(m['latency'] for m in history) / len(history)
                avg_cpu = sum(m['cpu_usage'] for m in history) / len(history)
                avg_ram = sum(m['ram_usage'] for m in history) / len(history)

                output.append(f"  Avg Latency:  {avg_latency:.3f}s")
                output.append(f"  Avg CPU:      {avg_cpu:.1%}")
                output.append(f"  Avg RAM:      {avg_ram:.0f} MB")
                output.append("")

                # Check degradation
                alert = engine.performance_tracker.detect_degradation(provider_id)
                if alert:
                    output.append(f"  ⚠️  DEGRADATION ALERT")
                    output.append(f"  Metric:       {alert['metric']}")
                    output.append(f"  Current:      {alert['current_value']:.3f}")
                    output.append(f"  Baseline:     {alert['baseline']:.3f}")
                    output.append(f"  Deviation:    {alert['deviation']:.1%}")
            else:
                output.append(f"No performance history for {provider_id}")
        else:
            # Show rankings
            rankings = engine.performance_tracker.get_provider_rankings()

            output.append("Provider Rankings (by latency):")
            output.append("")

            for i, rank in enumerate(rankings[:10], 1):
                output.append(f"{i}. {rank['provider_id']}")
                output.append(f"   Score:      {rank['score']:.3f}")
                output.append(f"   Executions: {rank['sample_count']}")
                output.append("")

        output.append("=" * 60)
        return "\n".join(output)

    def cmd_adapt_insights(self, args: List[str]) -> str:
        """
        Display adaptation insights and analytics.

        Usage: adapt-insights

        Returns:
            Formatted insights string
        """
        engine = self._ensure_engine()

        output = []
        output.append("=" * 60)
        output.append("ADAPTATION INSIGHTS")
        output.append("=" * 60)

        # Get insights from learner
        insights = engine.context_learner.analyze_execution_patterns()

        for insight in insights:
            insight_type = insight['type']

            if insight_type == 'high_performers':
                output.append(f"🌟 HIGH PERFORMERS ({insight['count']})")
                output.append("")
                for provider in insight['providers'][:5]:
                    output.append(f"  {provider['provider_id']}")
                    output.append(f"    Success Rate: {provider['success_rate']:.1%}")
                    output.append(f"    Confidence:   {provider['confidence']:.1%}")
                    output.append("")

            elif insight_type == 'underperformers':
                output.append(f"⚠️  UNDERPERFORMERS ({insight['count']})")
                output.append("")
                for provider in insight['providers'][:5]:
                    output.append(f"  {provider['provider_id']}")
                    output.append(f"    Success Rate: {provider['success_rate']:.1%}")
                    output.append(f"    Executions:   {provider['execution_count']}")
                    output.append("")

            elif insight_type == 'adaptation_effectiveness':
                output.append(f"📊 ADAPTATION EFFECTIVENESS")
                output.append(f"  Total Adaptations: {insight['total_adaptations']}")
                output.append(f"  Success Rate:      {insight['success_rate']:.1%}")
                output.append("")
                if insight['recent_reasons']:
                    output.append("  Recent Reasons:")
                    for reason in insight['recent_reasons'][:5]:
                        output.append(f"    - {reason}")
                output.append("")

        if not insights:
            output.append("No insights available yet.")
            output.append("Run more tasks to accumulate data.")

        output.append("=" * 60)
        return "\n".join(output)

    def cmd_adapt_recommend(self, args: List[str]) -> str:
        """
        Get provider recommendation for a task type.

        Usage: adapt-recommend <task_type>

        Args:
            args: Task type (required)

        Returns:
            Formatted recommendation string
        """
        if not args:
            return "Usage: adapt-recommend <task_type>"

        engine = self._ensure_engine()
        task_type = args[0]

        output = []
        output.append("=" * 60)
        output.append(f"PROVIDER RECOMMENDATION: {task_type}")
        output.append("=" * 60)

        rec = engine.context_learner.recommend_provider(task_type)

        if rec and rec.provider_id:
            output.append(f"Recommended Provider: {rec.provider_id}")
            output.append(f"Confidence:           {rec.confidence:.1%}")
            output.append(f"Reason:               {rec.reason}")
            output.append(f"Success Rate:         {rec.success_rate:.1%}")
            output.append(f"Execution Count:      {rec.execution_count}")
            output.append("")
            output.append("Estimated Resources:")
            output.append(f"  CPU:      {rec.resource_estimate['cpu']:.1%}")
            output.append(f"  RAM:      {rec.resource_estimate['ram']:.0f} MB")
            output.append(f"  Duration: {rec.resource_estimate['duration']:.1f}s")
        else:
            output.append("No recommendation available.")
            output.append("Insufficient learned patterns for this task type.")

        output.append("=" * 60)
        return "\n".join(output)

    def cmd_adapt_history(self, args: List[str]) -> str:
        """
        Display adaptation history.

        Usage: adapt-history [limit]

        Args:
            args: Optional limit (default: 10)

        Returns:
            Formatted history string
        """
        engine = self._ensure_engine()

        limit = int(args[0]) if args else 10

        output = []
        output.append("=" * 60)
        output.append(f"ADAPTATION HISTORY (last {limit})")
        output.append("=" * 60)

        history = engine.context_learner.adaptation_history[-limit:]

        if history:
            for i, record in enumerate(reversed(history), 1):
                output.append(f"{i}. Task: {record['task_id']}")
                output.append(f"   Success:   {record['success']}")
                output.append(f"   Reason:    {record['reason']}")
                output.append(f"   Timestamp: {record['timestamp']}")

                if record.get('details'):
                    details = record['details']
                    if 'old_provider' in details:
                        output.append(f"   Switch:    {details['old_provider']} → {details['new_provider']}")
                output.append("")
        else:
            output.append("No adaptation history available.")

        output.append("=" * 60)
        return "\n".join(output)

    def get_command_map(self) -> Dict[str, Any]:
        """
        Get map of command names to handler functions.

        Returns:
            Dictionary mapping command names to functions
        """
        return {
            'adapt-status': self.cmd_adapt_status,
            'adapt-patterns': self.cmd_adapt_patterns,
            'adapt-performance': self.cmd_adapt_performance,
            'adapt-insights': self.cmd_adapt_insights,
            'adapt-recommend': self.cmd_adapt_recommend,
            'adapt-history': self.cmd_adapt_history,
        }


# Singleton instance
_commands_instance = None


def get_adaptation_commands():
    """Get singleton adaptation commands instance."""
    global _commands_instance
    if _commands_instance is None:
        _commands_instance = AdaptationCommands()
    return _commands_instance
