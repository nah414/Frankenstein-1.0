"""
FRANKENSTEIN 1.0 - Hardware Dashboard
Phase 2: Hardware Health Display for Terminal

Purpose: Terminal-integrated hardware health visualization
"""

from datetime import datetime
from typing import Optional, List, Callable
from .hardware_monitor import (
    HardwareHealthMonitor, 
    get_hardware_monitor,
    HealthStatus,
    HardwareTier,
    SwitchRecommendation
)


class HardwareDashboard:
    """
    Hardware Dashboard for Monster Terminal integration.
    """

    def __init__(self, monitor: Optional[HardwareHealthMonitor] = None):
        self._monitor = monitor or get_hardware_monitor()

    def get_status_bar(self) -> str:
        """Get single-line status for terminal header"""
        stats = self._monitor.get_stats()
        status = HealthStatus[stats['health_status']]
        
        if stats['switch_recommended']:
            return f"{status.icon} {stats['switch_urgency'].upper()}: Switch recommended"
        else:
            return f"{status.icon} {stats['health_status']} | Headroom: {stats['headroom_percent']:.0f}%"

    def get_full_dashboard(self) -> str:
        """Get full hardware dashboard for 'hardware status' command"""
        stats = self._monitor.get_stats()
        status = HealthStatus[stats['health_status']]
        trend = self._monitor.get_trend()
        recommendation = self._monitor.get_switch_recommendation()

        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║            🖥️  HARDWARE HEALTH DASHBOARD  🖥️                      ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            f"║  CURRENT TIER: {stats['current_tier']:<40}       ║",
            f"║  Description:  {stats['tier_description']:<40}       ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            f"║  HEALTH STATUS: {status.icon} {status.label:<12}                              ║",
            f"║  {status.description:<60}  ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  RESOURCE USAGE (5-min average)                                  ║",
        ]

        if trend:
            cpu_bar = self._make_bar(trend.cpu_avg_5min, 50)
            mem_bar = self._make_bar(trend.memory_avg_5min, 50)
            lines.extend([
                f"║    CPU:    [{cpu_bar}] {trend.cpu_avg_5min:5.1f}% ({trend.cpu_trend})     ║",
                f"║    Memory: [{mem_bar}] {trend.memory_avg_5min:5.1f}% ({trend.memory_trend})     ║",
                "║                                                                  ║",
                f"║    CPU Peak:    {trend.cpu_peak_5min:5.1f}%    Memory Peak:    {trend.memory_peak_5min:5.1f}%       ║",
                f"║    CPU Predict: {trend.predicted_cpu_10min:5.1f}%    Memory Predict: {trend.predicted_memory_10min:5.1f}%       ║",
            ])
            
            # Time to thresholds
            if trend.time_to_warning_min is not None:
                lines.append(f"║    ⏱️  Time to Warning:  ~{trend.time_to_warning_min:.0f} minutes                          ║")
            if trend.time_to_critical_min is not None:
                lines.append(f"║    ⏱️  Time to Critical: ~{trend.time_to_critical_min:.0f} minutes                          ║")
        else:
            lines.append("║    Collecting data... (need ~20 seconds)                         ║")

        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  HEADROOM: {stats['headroom_percent']:5.1f}%                                              ║")

        # Switch recommendation
        if recommendation.should_switch:
            urgency_icons = {"low": "🟡", "medium": "🟠", "high": "🔴", "immediate": "⚠️"}
            icon = urgency_icons.get(recommendation.urgency, "⚠️")
            lines.extend([
                "╠══════════════════════════════════════════════════════════════════╣",
                f"║  {icon} SWITCH RECOMMENDATION                                       ║",
                f"║    Urgency: {recommendation.urgency.upper():<15}                                  ║",
                f"║    Reason:  {recommendation.reason:<50} ║",
                f"║    Recommended: {recommendation.recommended_tier.name:<40}   ║",
            ])
            if recommendation.auto_switch_available:
                lines.append("║    Auto-switch: AVAILABLE (use 'hardware auto-switch')           ║")
            else:
                lines.append("║    Auto-switch: Not available for this tier                      ║")
        else:
            lines.extend([
                "╠══════════════════════════════════════════════════════════════════╣",
                "║  ✅ NO SWITCH NEEDED - System within capacity                    ║",
            ])

        # Diagnosis section (always show when there are issues)
        diagnosis = stats.get('diagnosis', {})
        issues = diagnosis.get('issues', [])
        recommendations = diagnosis.get('recommendations', [])
        
        if issues or status in (HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.OVERLOAD):
            lines.extend([
                "╠══════════════════════════════════════════════════════════════════╣",
                "║  🔍 REAL-TIME DIAGNOSIS                                          ║",
            ])
            
            # Primary cause
            primary = diagnosis.get('primary_cause', 'Unknown')
            lines.append(f"║    Primary Cause: {primary:<43}  ║")
            
            # Tier limits
            tier_limits = diagnosis.get('tier_limits', {})
            if tier_limits:
                lines.append(f"║    Tier Limits: CPU {tier_limits.get('max_cpu', 80)}% | Memory {tier_limits.get('max_memory', 70)}%                       ║")
            
            # Issues
            if issues:
                lines.append("║                                                                  ║")
                lines.append("║    Issues Detected:                                              ║")
                for issue in issues[:4]:  # Limit to 4 issues
                    # Truncate long issues
                    if len(issue) > 52:
                        issue = issue[:49] + "..."
                    lines.append(f"║      • {issue:<54}  ║")
            
            # Recommendations
            if recommendations:
                lines.append("║                                                                  ║")
                lines.append("║    Recommendations:                                              ║")
                for rec in recommendations[:3]:  # Limit to 3 recommendations
                    if len(rec) > 52:
                        rec = rec[:49] + "..."
                    lines.append(f"║      → {rec:<54}  ║")

        lines.extend([
            "╚══════════════════════════════════════════════════════════════════╝",
            ""
        ])

        return "\n".join(lines)

    def get_trend_report(self) -> str:
        """Get detailed trend analysis"""
        trend = self._monitor.get_trend()
        stats = self._monitor.get_stats()

        if trend is None:
            return "\n⏳ Collecting data... Please wait ~20 seconds for trend analysis.\n"

        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║                   📊 RESOURCE TREND ANALYSIS                     ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            f"║  Analysis Window: {self._monitor._history_minutes} minutes                                     ║",
            f"║  Samples Collected: {stats['samples_collected']:<5}                                      ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  CPU ANALYSIS                                                    ║",
            f"║    Current Average: {trend.cpu_avg_5min:5.1f}%                                      ║",
            f"║    Peak:            {trend.cpu_peak_5min:5.1f}%                                      ║",
            f"║    Trend:           {trend.cpu_trend.upper():<10}                                  ║",
            f"║    10-min Forecast: {trend.predicted_cpu_10min:5.1f}%                                      ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  MEMORY ANALYSIS                                                 ║",
            f"║    Current Average: {trend.memory_avg_5min:5.1f}%                                      ║",
            f"║    Peak:            {trend.memory_peak_5min:5.1f}%                                      ║",
            f"║    Trend:           {trend.memory_trend.upper():<10}                                  ║",
            f"║    10-min Forecast: {trend.predicted_memory_10min:5.1f}%                                      ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            "║  PREDICTIONS                                                     ║",
        ]

        if trend.time_to_warning_min is not None:
            lines.append(f"║    Time to WARNING:  ~{trend.time_to_warning_min:5.1f} minutes                            ║")
        else:
            lines.append("║    Time to WARNING:  Not projected (stable/falling)             ║")

        if trend.time_to_critical_min is not None:
            lines.append(f"║    Time to CRITICAL: ~{trend.time_to_critical_min:5.1f} minutes                            ║")
        else:
            lines.append("║    Time to CRITICAL: Not projected (stable/falling)             ║")

        lines.extend([
            "╚══════════════════════════════════════════════════════════════════╝",
            ""
        ])

        return "\n".join(lines)

    def get_tier_info(self) -> str:
        """Get information about all hardware tiers"""
        current = self._monitor.get_current_tier()

        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║                   🏗️  HARDWARE TIER REFERENCE                    ║",
            "╠══════════════════════════════════════════════════════════════════╣",
        ]

        for tier in HardwareTier:
            marker = "→ " if tier == current else "  "
            lines.extend([
                f"║  {marker}{tier.name:<55}║",
                f"║      {tier.description:<55}║",
                f"║      Max CPU: {tier.max_cpu}%  Max Memory: {tier.max_memory}%  Workers: {tier.max_workers:<5}    ║",
                "║                                                                  ║",
            ])

        lines.extend([
            "╚══════════════════════════════════════════════════════════════════╝",
            ""
        ])

        return "\n".join(lines)

    def _make_bar(self, percent: float, width: int = 20) -> str:
        """Create a text progress bar"""
        filled = int(percent / 100 * width)
        empty = width - filled
        return "█" * filled + "░" * empty


# ==================== TERMINAL COMMAND HANDLER ====================

def handle_hardware_command(args: List[str], write_output: Callable[[str], None]) -> None:
    """
    Handle 'hardware' command in Monster Terminal.
    
    Usage:
        hardware              - Show status
        hardware status       - Show full dashboard
        hardware trend        - Show trend analysis
        hardware tiers        - Show tier information
        hardware recommend    - Show switch recommendation
    """
    dashboard = HardwareDashboard()
    monitor = get_hardware_monitor()

    # Ensure monitor is running
    if not monitor._running:
        monitor.start()

    if not args:
        args = ["status"]

    subcmd = args[0].lower()

    if subcmd == "status":
        write_output(dashboard.get_full_dashboard())

    elif subcmd == "trend":
        write_output(dashboard.get_trend_report())

    elif subcmd == "tiers":
        write_output(dashboard.get_tier_info())

    elif subcmd == "recommend":
        recommendation = monitor.get_switch_recommendation()
        if recommendation.should_switch:
            write_output(f"\n⚠️  SWITCH RECOMMENDED\n")
            write_output(f"   Urgency: {recommendation.urgency.upper()}\n")
            write_output(f"   Reason: {recommendation.reason}\n")
            write_output(f"   Current: {recommendation.current_tier.name}\n")
            write_output(f"   Recommended: {recommendation.recommended_tier.name}\n")
            write_output(f"   Headroom: {recommendation.estimated_headroom_percent:.1f}%\n\n")
        else:
            write_output(f"\n✅ No switch needed. Headroom: {recommendation.estimated_headroom_percent:.1f}%\n\n")

    elif subcmd == "line":
        write_output(f"\n{monitor.get_status_line()}\n\n")

    elif subcmd == "diagnose" or subcmd == "diag":
        diagnosis = monitor.get_diagnosis()
        write_output("\n🔍 HARDWARE DIAGNOSIS\n")
        write_output("=" * 50 + "\n")
        write_output(f"Status: {diagnosis['status']}\n")
        write_output(f"Primary Cause: {diagnosis['primary_cause']}\n\n")
        
        limits = diagnosis.get('tier_limits', {})
        write_output(f"Tier Limits: CPU {limits.get('max_cpu', 80)}% | Memory {limits.get('max_memory', 70)}%\n\n")
        
        issues = diagnosis.get('issues', [])
        if issues:
            write_output("Issues Detected:\n")
            for issue in issues:
                write_output(f"  • {issue}\n")
            write_output("\n")
        
        recommendations = diagnosis.get('recommendations', [])
        if recommendations:
            write_output("Recommendations:\n")
            for rec in recommendations:
                write_output(f"  → {rec}\n")
            write_output("\n")
        
        if not issues and not recommendations:
            write_output("✅ No issues detected. System running normally.\n\n")

    else:
        write_output(f"\n❌ Unknown hardware command: {subcmd}\n")
        write_output("Usage: hardware [status|trend|tiers|recommend|diagnose]\n\n")


# ==================== GLOBAL DASHBOARD INSTANCE ====================

_dashboard: Optional[HardwareDashboard] = None

def get_hardware_dashboard() -> HardwareDashboard:
    """Get or create the global dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = HardwareDashboard()
    return _dashboard
