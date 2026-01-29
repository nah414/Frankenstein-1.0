"""
FRANKENSTEIN 1.0 - Hardware Health Monitor
Phase 2: Hardware Auto-Switch Warning System

Purpose: Predictive workload monitoring and hardware switch recommendations
Integrates with: governor.py, safety.py
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics

from .governor import get_governor, ResourceSnapshot, ThrottleLevel
from .safety import SAFETY


class HardwareTier(Enum):
    """Hardware tier definitions"""
    TIER1_EDGE = ("Tier 1: Edge", "Dell i3 8th Gen", 80, 75, 3)
    TIER2_WORKSTATION = ("Tier 2: Workstation", "Mid-range Desktop", 85, 80, 6)
    TIER3_HPC = ("Tier 3: HPC Local", "High-end Multi-GPU", 90, 85, 12)
    TIER4_CLOUD = ("Tier 4: Cloud Burst", "On-demand Cloud", 95, 90, 32)
    TIER5_QUANTUM = ("Tier 5: Quantum Hybrid", "Quantum + Classical", 95, 90, 64)

    @property
    def name(self) -> str:
        return self.value[0]

    @property
    def description(self) -> str:
        return self.value[1]

    @property
    def max_cpu(self) -> int:
        return self.value[2]

    @property
    def max_memory(self) -> int:
        return self.value[3]

    @property
    def max_workers(self) -> int:
        return self.value[4]


class HealthStatus(Enum):
    """System health status levels"""
    OPTIMAL = ("OPTIMAL", "🟢", "#00ff88", "System running efficiently")
    NORMAL = ("NORMAL", "🟢", "#00ff88", "Normal operation")
    ELEVATED = ("ELEVATED", "🟡", "#ffcc00", "Above average load")
    WARNING = ("WARNING", "🟠", "#ff9900", "Approaching capacity limits")
    CRITICAL = ("CRITICAL", "🔴", "#ff4444", "At or exceeding safe limits")
    OVERLOAD = ("OVERLOAD", "⚠️", "#ff0000", "Hardware switch recommended")

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def icon(self) -> str:
        return self.value[1]

    @property
    def color(self) -> str:
        return self.value[2]

    @property
    def description(self) -> str:
        return self.value[3]


@dataclass
class HealthTrend:
    """Resource usage trend analysis"""
    cpu_trend: str          # rising, falling, stable
    memory_trend: str       # rising, falling, stable
    cpu_avg_5min: float
    memory_avg_5min: float
    cpu_peak_5min: float
    memory_peak_5min: float
    predicted_cpu_10min: float
    predicted_memory_10min: float
    time_to_warning_min: Optional[float]
    time_to_critical_min: Optional[float]


@dataclass
class SwitchRecommendation:
    """Hardware switch recommendation"""
    should_switch: bool
    urgency: str            # none, low, medium, high, immediate
    reason: str
    current_tier: HardwareTier
    recommended_tier: HardwareTier
    estimated_headroom_percent: float
    auto_switch_available: bool


class HardwareHealthMonitor:
    """
    Monitors hardware health and predicts when workload will exceed capacity.
    
    Features:
    - Trend analysis (5-minute rolling window)
    - Predictive warnings (estimates time to capacity)
    - Hardware switch recommendations
    - Optional auto-migration support
    """

    def __init__(self, 
                 current_tier: HardwareTier = HardwareTier.TIER1_EDGE,
                 history_minutes: int = 5,
                 prediction_minutes: int = 10):
        """
        Initialize the hardware health monitor.

        Args:
            current_tier: Current hardware tier
            history_minutes: Minutes of history to keep for trend analysis
            prediction_minutes: How far ahead to predict
        """
        self._current_tier = current_tier
        self._history_minutes = history_minutes
        self._prediction_minutes = prediction_minutes
        
        # History storage (samples every 2 seconds = 30 per minute)
        max_samples = history_minutes * 30
        self._cpu_history: deque = deque(maxlen=max_samples)
        self._memory_history: deque = deque(maxlen=max_samples)
        self._timestamps: deque = deque(maxlen=max_samples)
        
        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._governor = get_governor()
        
        # Current status
        self._health_status = HealthStatus.NORMAL
        self._last_recommendation: Optional[SwitchRecommendation] = None
        
        # Callbacks
        self._warning_callbacks: List[Callable[[SwitchRecommendation], None]] = []
        self._status_callbacks: List[Callable[[HealthStatus], None]] = []
        
        # Warning state (prevent spam)
        self._last_warning_time: Optional[datetime] = None
        self._warning_cooldown_sec = 60

    def start(self) -> bool:
        """Start the hardware health monitor"""
        if self._running:
            return False

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="FrankensteinHardwareMonitor"
        )
        self._thread.start()
        return True

    def stop(self) -> bool:
        """Stop the hardware health monitor"""
        if not self._running:
            return False

        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        return True

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_sample()
                self._analyze_health()
                time.sleep(2.0)  # Sample every 2 seconds
            except Exception as e:
                print(f"Hardware monitor error: {e}")
                time.sleep(5.0)

    def _collect_sample(self):
        """Collect a resource sample from the governor"""
        snapshot = self._governor.take_snapshot()
        
        with self._lock:
            self._cpu_history.append(snapshot.cpu_percent)
            self._memory_history.append(snapshot.memory_percent)
            self._timestamps.append(time.time())

    def _analyze_health(self):
        """Analyze system health and generate warnings if needed"""
        trend = self.get_trend()
        if trend is None:
            return

        # Determine health status
        new_status = self._calculate_health_status(trend)
        
        # Check if status changed
        if new_status != self._health_status:
            old_status = self._health_status
            self._health_status = new_status
            self._notify_status_change(new_status)

        # Check if warning needed
        if new_status in (HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.OVERLOAD):
            self._check_and_send_warning(trend)

    def _calculate_health_status(self, trend: HealthTrend) -> HealthStatus:
        """Calculate current health status based on trend"""
        cpu_avg = trend.cpu_avg_5min
        mem_avg = trend.memory_avg_5min
        cpu_peak = trend.cpu_peak_5min
        mem_peak = trend.memory_peak_5min
        
        max_cpu = self._current_tier.max_cpu
        max_mem = self._current_tier.max_memory

        # Check for overload (exceeding limits)
        if cpu_peak > max_cpu or mem_peak > max_mem:
            return HealthStatus.OVERLOAD

        # Check for critical (at limits)
        if cpu_avg > max_cpu * 0.95 or mem_avg > max_mem * 0.95:
            return HealthStatus.CRITICAL

        # Check for warning (approaching limits)
        if cpu_avg > max_cpu * 0.85 or mem_avg > max_mem * 0.85:
            return HealthStatus.WARNING

        # Check for elevated
        if cpu_avg > max_cpu * 0.70 or mem_avg > max_mem * 0.70:
            return HealthStatus.ELEVATED

        # Check for optimal (very low usage)
        if cpu_avg < 30 and mem_avg < 40:
            return HealthStatus.OPTIMAL

        return HealthStatus.NORMAL

    def _check_and_send_warning(self, trend: HealthTrend):
        """Check if we should send a warning and do so if needed"""
        now = datetime.now()
        
        # Check cooldown
        if self._last_warning_time:
            elapsed = (now - self._last_warning_time).total_seconds()
            if elapsed < self._warning_cooldown_sec:
                return

        # Generate recommendation
        recommendation = self.get_switch_recommendation()
        
        if recommendation.should_switch:
            self._last_warning_time = now
            self._last_recommendation = recommendation
            self._notify_warning(recommendation)

    def _notify_status_change(self, status: HealthStatus):
        """Notify callbacks of status change"""
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception:
                pass

    def _notify_warning(self, recommendation: SwitchRecommendation):
        """Notify callbacks of switch recommendation"""
        for callback in self._warning_callbacks:
            try:
                callback(recommendation)
            except Exception:
                pass

    # ==================== PUBLIC API ====================

    def get_trend(self) -> Optional[HealthTrend]:
        """Get current resource trend analysis"""
        with self._lock:
            if len(self._cpu_history) < 10:
                return None

            cpu_list = list(self._cpu_history)
            mem_list = list(self._memory_history)

        # Calculate averages
        cpu_avg = statistics.mean(cpu_list)
        mem_avg = statistics.mean(mem_list)
        cpu_peak = max(cpu_list)
        mem_peak = max(mem_list)

        # Calculate trends (compare first half to second half)
        mid = len(cpu_list) // 2
        cpu_first = statistics.mean(cpu_list[:mid]) if mid > 0 else cpu_avg
        cpu_second = statistics.mean(cpu_list[mid:]) if mid > 0 else cpu_avg
        mem_first = statistics.mean(mem_list[:mid]) if mid > 0 else mem_avg
        mem_second = statistics.mean(mem_list[mid:]) if mid > 0 else mem_avg

        cpu_trend = "rising" if cpu_second > cpu_first + 5 else "falling" if cpu_second < cpu_first - 5 else "stable"
        mem_trend = "rising" if mem_second > mem_first + 5 else "falling" if mem_second < mem_first - 5 else "stable"

        # Predict future values (simple linear extrapolation)
        cpu_delta = cpu_second - cpu_first
        mem_delta = mem_second - mem_first
        
        # Extrapolate for prediction_minutes (2x the history window)
        cpu_predicted = min(100, max(0, cpu_avg + cpu_delta * 2))
        mem_predicted = min(100, max(0, mem_avg + mem_delta * 2))

        # Calculate time to warning/critical
        time_to_warning = self._estimate_time_to_threshold(
            cpu_avg, cpu_delta, self._current_tier.max_cpu * 0.85
        )
        time_to_critical = self._estimate_time_to_threshold(
            cpu_avg, cpu_delta, self._current_tier.max_cpu * 0.95
        )

        return HealthTrend(
            cpu_trend=cpu_trend,
            memory_trend=mem_trend,
            cpu_avg_5min=round(cpu_avg, 1),
            memory_avg_5min=round(mem_avg, 1),
            cpu_peak_5min=round(cpu_peak, 1),
            memory_peak_5min=round(mem_peak, 1),
            predicted_cpu_10min=round(cpu_predicted, 1),
            predicted_memory_10min=round(mem_predicted, 1),
            time_to_warning_min=time_to_warning,
            time_to_critical_min=time_to_critical
        )

    def _estimate_time_to_threshold(self, current: float, delta_per_window: float, threshold: float) -> Optional[float]:
        """Estimate minutes until threshold is reached"""
        if current >= threshold:
            return 0.0
        if delta_per_window <= 0:
            return None  # Not rising, won't reach threshold
        
        remaining = threshold - current
        windows_needed = remaining / delta_per_window
        minutes = windows_needed * self._history_minutes
        
        return round(minutes, 1) if minutes < 60 else None

    def get_switch_recommendation(self) -> SwitchRecommendation:
        """Get hardware switch recommendation"""
        trend = self.get_trend()
        
        if trend is None:
            return SwitchRecommendation(
                should_switch=False,
                urgency="none",
                reason="Insufficient data for analysis",
                current_tier=self._current_tier,
                recommended_tier=self._current_tier,
                estimated_headroom_percent=100,
                auto_switch_available=False
            )

        max_cpu = self._current_tier.max_cpu
        max_mem = self._current_tier.max_memory
        
        # Calculate headroom
        cpu_headroom = max(0, max_cpu - trend.cpu_avg_5min)
        mem_headroom = max(0, max_mem - trend.memory_avg_5min)
        headroom = min(cpu_headroom, mem_headroom)

        # Determine if switch is needed
        should_switch = False
        urgency = "none"
        reason = "System within capacity"
        recommended_tier = self._current_tier

        if trend.cpu_peak_5min > max_cpu or trend.memory_peak_5min > max_mem:
            should_switch = True
            urgency = "immediate"
            reason = f"Workload exceeding {self._current_tier.name} capacity"
            recommended_tier = self._get_next_tier()
        elif trend.time_to_critical_min is not None and trend.time_to_critical_min < 5:
            should_switch = True
            urgency = "high"
            reason = f"Critical capacity in ~{trend.time_to_critical_min:.0f} minutes"
            recommended_tier = self._get_next_tier()
        elif trend.time_to_warning_min is not None and trend.time_to_warning_min < 10:
            should_switch = True
            urgency = "medium"
            reason = f"Warning threshold in ~{trend.time_to_warning_min:.0f} minutes"
            recommended_tier = self._get_next_tier()
        elif headroom < 10 and trend.cpu_trend == "rising":
            should_switch = True
            urgency = "low"
            reason = "Low headroom with rising trend"
            recommended_tier = self._get_next_tier()

        return SwitchRecommendation(
            should_switch=should_switch,
            urgency=urgency,
            reason=reason,
            current_tier=self._current_tier,
            recommended_tier=recommended_tier,
            estimated_headroom_percent=round(headroom, 1),
            auto_switch_available=self._is_auto_switch_available(recommended_tier)
        )

    def _get_next_tier(self) -> HardwareTier:
        """Get the next tier up from current"""
        tiers = list(HardwareTier)
        current_idx = tiers.index(self._current_tier)
        if current_idx < len(tiers) - 1:
            return tiers[current_idx + 1]
        return self._current_tier

    def _is_auto_switch_available(self, tier: HardwareTier) -> bool:
        """Check if auto-switch is available for a tier"""
        # In Phase 2, only cloud tiers could potentially auto-switch
        # Full implementation in Phase 3
        return tier in (HardwareTier.TIER4_CLOUD, HardwareTier.TIER5_QUANTUM)

    def get_health_status(self) -> HealthStatus:
        """Get current health status"""
        return self._health_status

    def get_diagnosis(self) -> Dict[str, Any]:
        """Get real-time diagnosis of current health state"""
        trend = self.get_trend()
        max_cpu = self._current_tier.max_cpu
        max_mem = self._current_tier.max_memory
        
        diagnosis = {
            "status": self._health_status.label,
            "tier_limits": {
                "max_cpu": max_cpu,
                "max_memory": max_mem
            },
            "issues": [],
            "primary_cause": None,
            "recommendations": []
        }
        
        if trend is None:
            diagnosis["primary_cause"] = "Insufficient data (collecting samples...)"
            return diagnosis
        
        # Check what's causing the current status
        cpu_avg = trend.cpu_avg_5min
        mem_avg = trend.memory_avg_5min
        cpu_peak = trend.cpu_peak_5min
        mem_peak = trend.memory_peak_5min
        
        # Identify issues
        if cpu_peak > max_cpu:
            diagnosis["issues"].append(f"CPU peak ({cpu_peak:.1f}%) exceeds limit ({max_cpu}%)")
        if mem_peak > max_mem:
            diagnosis["issues"].append(f"Memory peak ({mem_peak:.1f}%) exceeds limit ({max_mem}%)")
        if cpu_avg > max_cpu * 0.85:
            diagnosis["issues"].append(f"CPU average ({cpu_avg:.1f}%) near limit ({max_cpu}%)")
        if mem_avg > max_mem * 0.85:
            diagnosis["issues"].append(f"Memory average ({mem_avg:.1f}%) near limit ({max_mem}%)")
        if trend.cpu_trend == "rising":
            diagnosis["issues"].append("CPU usage trending upward")
        if trend.memory_trend == "rising":
            diagnosis["issues"].append("Memory usage trending upward")
        
        # Determine primary cause
        if cpu_peak > max_cpu and mem_peak > max_mem:
            diagnosis["primary_cause"] = "Both CPU and Memory exceeding Tier 1 limits"
        elif cpu_peak > max_cpu:
            diagnosis["primary_cause"] = f"CPU spikes above {max_cpu}% limit"
        elif mem_peak > max_mem:
            diagnosis["primary_cause"] = f"Memory spikes above {max_mem}% limit"
        elif cpu_avg > mem_avg:
            diagnosis["primary_cause"] = "High sustained CPU usage"
        elif mem_avg > cpu_avg:
            diagnosis["primary_cause"] = "High sustained Memory usage"
        else:
            diagnosis["primary_cause"] = "System within normal parameters"
        
        # Recommendations
        if self._health_status in (HealthStatus.OVERLOAD, HealthStatus.CRITICAL):
            diagnosis["recommendations"].append("Close unnecessary applications")
            diagnosis["recommendations"].append("Consider upgrading to Tier 2 hardware")
            if cpu_peak > max_cpu:
                diagnosis["recommendations"].append("Reduce CPU-intensive background tasks")
            if mem_peak > max_mem:
                diagnosis["recommendations"].append("Free up RAM by closing browser tabs")
        elif self._health_status == HealthStatus.WARNING:
            diagnosis["recommendations"].append("Monitor workload closely")
            diagnosis["recommendations"].append("Prepare for possible tier escalation")
        
        return diagnosis

    def get_current_tier(self) -> HardwareTier:
        """Get current hardware tier"""
        return self._current_tier

    def set_tier(self, tier: HardwareTier):
        """Manually set hardware tier"""
        self._current_tier = tier

    def add_warning_callback(self, callback: Callable[[SwitchRecommendation], None]):
        """Subscribe to switch recommendations"""
        self._warning_callbacks.append(callback)

    def add_status_callback(self, callback: Callable[[HealthStatus], None]):
        """Subscribe to status changes"""
        self._status_callbacks.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get hardware monitor statistics"""
        trend = self.get_trend()
        recommendation = self.get_switch_recommendation()
        diagnosis = self.get_diagnosis()

        return {
            "running": self._running,
            "current_tier": self._current_tier.name,
            "tier_description": self._current_tier.description,
            "tier_max_cpu": self._current_tier.max_cpu,
            "tier_max_memory": self._current_tier.max_memory,
            "health_status": self._health_status.label,
            "health_icon": self._health_status.icon,
            "health_color": self._health_status.color,
            "cpu_avg": trend.cpu_avg_5min if trend else 0,
            "memory_avg": trend.memory_avg_5min if trend else 0,
            "cpu_peak": trend.cpu_peak_5min if trend else 0,
            "memory_peak": trend.memory_peak_5min if trend else 0,
            "cpu_trend": trend.cpu_trend if trend else "unknown",
            "memory_trend": trend.memory_trend if trend else "unknown",
            "cpu_predicted": trend.predicted_cpu_10min if trend else 0,
            "memory_predicted": trend.predicted_memory_10min if trend else 0,
            "headroom_percent": recommendation.estimated_headroom_percent,
            "switch_recommended": recommendation.should_switch,
            "switch_urgency": recommendation.urgency,
            "switch_reason": recommendation.reason,
            "recommended_tier": recommendation.recommended_tier.name,
            "samples_collected": len(self._cpu_history),
            "diagnosis": diagnosis
        }

    def get_status_line(self) -> str:
        """Get single-line status for display"""
        stats = self.get_stats()
        return (
            f"{stats['health_icon']} {stats['health_status']} | "
            f"CPU: {stats['cpu_avg']:.0f}% ({stats['cpu_trend']}) | "
            f"Headroom: {stats['headroom_percent']:.0f}%"
        )


# ==================== GLOBAL INSTANCE ====================

_hardware_monitor: Optional[HardwareHealthMonitor] = None

def get_hardware_monitor() -> HardwareHealthMonitor:
    """Get or create the global hardware monitor"""
    global _hardware_monitor
    if _hardware_monitor is None:
        _hardware_monitor = HardwareHealthMonitor()
    return _hardware_monitor
