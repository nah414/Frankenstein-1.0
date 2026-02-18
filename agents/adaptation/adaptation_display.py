"""
Real-Time Adaptation Display Functions

Provides text-based visualization for adaptation monitoring.
Designed for terminal/console output with ASCII graphics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdaptationDisplay:
    """
    Text-based display for adaptation monitoring.

    Provides ASCII-based visualizations for terminal output.
    """

    @staticmethod
    def render_status_panel(engine) -> str:
        """
        Render compact status panel.

        Args:
            engine: AdaptationEngine instance

        Returns:
            Formatted status string
        """
        status = engine.get_status()

        lines = []
        lines.append("┌─────────────────────────────────────┐")
        lines.append("│  REAL-TIME ADAPTATION STATUS        │")
        lines.append("├─────────────────────────────────────┤")
        lines.append(f"│ Monitoring: {'ACTIVE ' if status['monitoring_active'] else 'STOPPED':<22}│")
        lines.append(f"│ Adaptations:{status['adaptation_count']:<22}│")
        lines.append(f"│ CPU:        {AdaptationDisplay._format_percent(status['current_resources']['cpu_usage']):<22}│")
        lines.append(f"│ RAM:        {AdaptationDisplay._format_percent(status['current_resources']['ram_usage']):<22}│")
        lines.append(f"│ Safe:       {'YES' if engine._check_safe_to_adapt() else 'NO ':<22}│")
        lines.append("└─────────────────────────────────────┘")

        return "\n".join(lines)

    @staticmethod
    def render_performance_summary(tracker, provider_id: Optional[str] = None) -> str:
        """
        Render performance summary.

        Args:
            tracker: PerformanceTracker instance
            provider_id: Optional provider filter

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("┌──────────────────────────────────────────────┐")
        lines.append("│  PERFORMANCE SUMMARY                         │")
        lines.append("├──────────────────────────────────────────────┤")

        if provider_id:
            history = tracker.get_performance_history(provider_id=provider_id, window_hours=1)[:10]
            if history:
                avg_latency = sum(m['latency'] for m in history) / len(history)
                avg_cpu = sum(m['cpu_usage'] for m in history) / len(history)

                lines.append(f"│ Provider: {provider_id:<34} │")
                lines.append(f"│ Samples:  {len(history):<34} │")
                lines.append(f"│ Latency:  {avg_latency:.3f}s{'':<27} │")
                lines.append(f"│ CPU:      {avg_cpu:.1%}{'':<29} │")

                # Check degradation
                alert = tracker.detect_degradation(provider_id)
                if alert:
                    lines.append("│                                              │")
                    lines.append(f"│ ⚠️  DEGRADATION: {alert['metric']:<24} │")
            else:
                lines.append(f"│ No data for {provider_id:<30} │")
        else:
            rankings = tracker.get_provider_rankings()
            lines.append("│ Top Providers:                               │")
            for i, rank in enumerate(rankings[:3], 1):
                lines.append(f"│   {i}. {rank['provider_id']:<39} │")

        lines.append("└──────────────────────────────────────────────┘")

        return "\n".join(lines)

    @staticmethod
    def render_learning_summary(learner, task_type: Optional[str] = None) -> str:
        """
        Render learning summary.

        Args:
            learner: ContextLearner instance
            task_type: Optional task type filter

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("┌──────────────────────────────────────────────┐")
        lines.append("│  LEARNING SUMMARY                            │")
        lines.append("├──────────────────────────────────────────────┤")

        total_patterns = len(learner.knowledge_base)
        lines.append(f"│ Total Patterns: {total_patterns:<30} │")

        if task_type:
            patterns = learner.get_patterns_for_task(task_type)
            lines.append(f"│ Task: {task_type:<38} │")
            lines.append("│                                              │")

            if patterns:
                for pattern in patterns[:3]:
                    lines.append(f"│   {pattern['provider_id']:<42} │")
                    lines.append(f"│     Confidence: {pattern['confidence']:.1%}{'':<29} │")
            else:
                lines.append(f"│ No patterns for {task_type:<28} │")
        else:
            # Show top patterns
            all_patterns = list(learner.knowledge_base.values())
            if all_patterns:
                lines.append("│ Top Task Types:                              │")
                task_counts = {}
                for p in all_patterns:
                    task = p['task_type']
                    task_counts[task] = task_counts.get(task, 0) + 1

                for task, count in sorted(task_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                    lines.append(f"│   {task}: {count} providers{'':<24} │")

        lines.append("└──────────────────────────────────────────────┘")

        return "\n".join(lines)

    @staticmethod
    def render_simple_graph(data: List[float], width: int = 40, height: int = 8, label: str = "Value") -> str:
        """
        Render simple ASCII line graph.

        Args:
            data: Data points to graph
            width: Graph width in characters
            height: Graph height in lines
            label: Y-axis label

        Returns:
            ASCII graph string
        """
        if not data:
            return "No data to display"

        lines = []

        # Normalize data to height
        min_val = min(data)
        max_val = max(data)
        value_range = max_val - min_val if max_val > min_val else 1

        # Graph title
        lines.append(f"┌{'─' * (width + 2)}┐")
        lines.append(f"│ {label:<{width}} │")
        lines.append(f"├{'─' * (width + 2)}┤")

        # Draw graph
        for row in range(height, 0, -1):
            line_chars = ['│ ']
            threshold = min_val + (value_range * row / height)

            # Sample data to fit width
            step = max(1, len(data) // width)
            sampled_data = [data[i] for i in range(0, len(data), step)][:width]

            for value in sampled_data:
                if value >= threshold:
                    line_chars.append('█')
                else:
                    line_chars.append(' ')

            # Pad to width
            while len(line_chars) - 2 < width:
                line_chars.append(' ')

            line_chars.append(' │')
            lines.append(''.join(line_chars))

        # Bottom border
        lines.append(f"└{'─' * (width + 2)}┘")
        lines.append(f"  Range: {min_val:.2f} - {max_val:.2f}")

        return "\n".join(lines)

    @staticmethod
    def render_latency_graph(tracker, provider_id: str, hours: int = 1) -> str:
        """
        Render latency trend graph.

        Args:
            tracker: PerformanceTracker instance
            provider_id: Provider to graph
            hours: Hours of history

        Returns:
            ASCII graph string
        """
        history = tracker.get_performance_history(
            provider_id=provider_id,
            window_hours=hours
        )

        if not history:
            return f"No latency data for {provider_id}"

        latencies = [m['latency'] for m in history]

        return AdaptationDisplay.render_simple_graph(
            latencies,
            width=50,
            height=10,
            label=f"Latency (s) - {provider_id} - Last {hours}h"
        )

    @staticmethod
    def render_dashboard(engine) -> str:
        """
        Render full dashboard with all panels.

        Args:
            engine: AdaptationEngine instance

        Returns:
            Complete dashboard string
        """
        lines = []

        # Title
        lines.append("=" * 80)
        lines.append("FRANKENSTEIN 1.0 - REAL-TIME ADAPTATION DASHBOARD".center(80))
        lines.append("=" * 80)
        lines.append("")

        # Status panel
        lines.append(AdaptationDisplay.render_status_panel(engine))
        lines.append("")

        # Performance summary
        lines.append(AdaptationDisplay.render_performance_summary(engine.performance_tracker))
        lines.append("")

        # Learning summary
        lines.append(AdaptationDisplay.render_learning_summary(engine.context_learner))
        lines.append("")

        # Footer
        lines.append("=" * 80)
        lines.append(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
        lines.append("=" * 80)

        return "\n".join(lines)

    @staticmethod
    def _format_percent(value: float) -> str:
        """Format percentage with color indicator."""
        pct = f"{value:.1%}"

        if value >= 0.75:
            return f"{pct} ⚠️"
        elif value >= 0.60:
            return f"{pct} ⚡"
        else:
            return f"{pct} ✓"


def get_adaptation_display():
    """Get AdaptationDisplay instance."""
    return AdaptationDisplay()
