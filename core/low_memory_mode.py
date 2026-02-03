"""
FRANKENSTEIN 1.0 - Low Memory Mode
Ultra-conservative resource management for constrained systems

Purpose: Dramatically reduce CPU/RAM usage when system is under pressure
Design: Automatic detection + manual toggle, disables non-essential features
Target: Run smoothly even with <2GB free RAM

Author: Frankenstein Project
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

# Check for psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class MemoryMode(Enum):
    """Memory mode levels"""
    NORMAL = "normal"           # Full features, standard polling
    CONSERVATIVE = "conservative"  # Reduced features, slower polling
    LOW_MEMORY = "low_memory"   # Minimal features, very slow polling
    CRITICAL = "critical"       # Survival mode - bare minimum


@dataclass
class ModeSettings:
    """Settings for each memory mode"""
    # Polling intervals (seconds)
    resource_poll_interval: float
    ui_update_interval: float  # milliseconds for tkinter.after()
    security_check_interval: int  # Every N updates
    
    # Feature flags
    enable_security_monitor: bool
    enable_hardware_monitor: bool
    enable_agent_scheduler: bool
    enable_synthesis_engine: bool
    enable_quantum_mode: bool
    enable_auto_visualization: bool
    
    # Limits
    max_history_size: int
    max_output_lines: int
    cache_ttl: float
    
    # UI
    enable_live_monitor_panel: bool
    monitor_panel_updates: bool


# Predefined mode configurations
MODE_CONFIGS: Dict[MemoryMode, ModeSettings] = {
    MemoryMode.NORMAL: ModeSettings(
        resource_poll_interval=4.0,
        ui_update_interval=5000,
        security_check_interval=5,
        enable_security_monitor=True,
        enable_hardware_monitor=True,
        enable_agent_scheduler=True,
        enable_synthesis_engine=True,
        enable_quantum_mode=True,
        enable_auto_visualization=True,
        max_history_size=100,
        max_output_lines=10000,
        cache_ttl=1.0,
        enable_live_monitor_panel=True,
        monitor_panel_updates=True,
    ),
    MemoryMode.CONSERVATIVE: ModeSettings(
        resource_poll_interval=8.0,
        ui_update_interval=8000,
        security_check_interval=10,
        enable_security_monitor=True,
        enable_hardware_monitor=True,
        enable_agent_scheduler=True,
        enable_synthesis_engine=True,
        enable_quantum_mode=True,
        enable_auto_visualization=False,  # Disable auto-viz
        max_history_size=50,
        max_output_lines=5000,
        cache_ttl=2.0,
        enable_live_monitor_panel=True,
        monitor_panel_updates=True,
    ),
    MemoryMode.LOW_MEMORY: ModeSettings(
        resource_poll_interval=15.0,      # Very slow polling
        ui_update_interval=15000,         # 15 second UI updates
        security_check_interval=30,       # Very infrequent security checks
        enable_security_monitor=False,    # Disabled by default
        enable_hardware_monitor=False,    # Disabled by default
        enable_agent_scheduler=False,     # Disabled
        enable_synthesis_engine=True,     # Keep core feature
        enable_quantum_mode=True,         # Keep core feature
        enable_auto_visualization=False,
        max_history_size=25,
        max_output_lines=2000,
        cache_ttl=5.0,                    # Long cache
        enable_live_monitor_panel=True,
        monitor_panel_updates=False,      # Static display only
    ),
    MemoryMode.CRITICAL: ModeSettings(
        resource_poll_interval=30.0,      # Minimal polling
        ui_update_interval=30000,         # 30 second UI updates
        security_check_interval=60,
        enable_security_monitor=False,
        enable_hardware_monitor=False,
        enable_agent_scheduler=False,
        enable_synthesis_engine=False,    # Disabled - too heavy
        enable_quantum_mode=False,        # Disabled - too heavy
        enable_auto_visualization=False,
        max_history_size=10,
        max_output_lines=500,
        cache_ttl=10.0,
        enable_live_monitor_panel=False,  # Hide panel entirely
        monitor_panel_updates=False,
    ),
}


class LowMemoryManager:
    """
    Manages low memory mode for Frankenstein Terminal.
    
    Features:
    1. Automatic detection of low memory conditions
    2. Manual mode toggle via command
    3. Gradual degradation as memory pressure increases
    4. Automatic recovery when memory frees up
    5. Callback system for notifying components
    """
    
    # Thresholds for automatic mode switching (% of total RAM used)
    THRESHOLDS = {
        MemoryMode.NORMAL: 60,        # Below 60% = normal
        MemoryMode.CONSERVATIVE: 70,  # 60-70% = conservative
        MemoryMode.LOW_MEMORY: 80,    # 70-80% = low memory
        MemoryMode.CRITICAL: 100,     # Above 80% = critical
    }
    
    # Minimum free RAM thresholds (GB)
    MIN_FREE_RAM = {
        MemoryMode.NORMAL: 3.0,
        MemoryMode.CONSERVATIVE: 2.0,
        MemoryMode.LOW_MEMORY: 1.0,
        MemoryMode.CRITICAL: 0.5,
    }
    
    def __init__(self):
        self._lock = threading.Lock()
        self._current_mode = MemoryMode.NORMAL
        self._manual_override: Optional[MemoryMode] = None
        self._auto_detect = True
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks for mode changes
        self._mode_callbacks: List[Callable[[MemoryMode, ModeSettings], None]] = []
        
        # Stats
        self._mode_changes = 0
        self._last_check_time = 0
        self._last_memory_percent = 0
        self._last_free_gb = 0
    
    def start(self) -> bool:
        """Start automatic memory monitoring"""
        if self._running:
            return False
        
        if not PSUTIL_AVAILABLE:
            print("⚠️ psutil not available - using CONSERVATIVE mode by default")
            self._set_mode(MemoryMode.CONSERVATIVE)
            return False
        
        # Do initial check
        self._check_memory()
        
        # Start monitoring thread
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="FrankensteinLowMemoryManager"
        )
        self._thread.start()
        return True
    
    def stop(self):
        """Stop automatic monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                if self._auto_detect and self._manual_override is None:
                    self._check_memory()
            except Exception as e:
                print(f"LowMemoryManager error: {e}")
            
            # Check every 10 seconds
            time.sleep(10.0)
    
    def _check_memory(self):
        """Check current memory and adjust mode if needed"""
        if not PSUTIL_AVAILABLE:
            return
        
        mem = psutil.virtual_memory()
        self._last_memory_percent = mem.percent
        self._last_free_gb = mem.available / (1024**3)
        self._last_check_time = time.time()
        
        # Determine appropriate mode
        new_mode = self._determine_mode(mem.percent, self._last_free_gb)
        
        if new_mode != self._current_mode:
            self._set_mode(new_mode)
    
    def _determine_mode(self, percent_used: float, free_gb: float) -> MemoryMode:
        """Determine the appropriate mode based on memory state"""
        # Check by percentage
        if percent_used >= 80:
            mode_by_percent = MemoryMode.CRITICAL
        elif percent_used >= 70:
            mode_by_percent = MemoryMode.LOW_MEMORY
        elif percent_used >= 60:
            mode_by_percent = MemoryMode.CONSERVATIVE
        else:
            mode_by_percent = MemoryMode.NORMAL
        
        # Check by free RAM
        if free_gb < 0.5:
            mode_by_free = MemoryMode.CRITICAL
        elif free_gb < 1.0:
            mode_by_free = MemoryMode.LOW_MEMORY
        elif free_gb < 2.0:
            mode_by_free = MemoryMode.CONSERVATIVE
        else:
            mode_by_free = MemoryMode.NORMAL
        
        # Use the more conservative of the two
        modes_order = [MemoryMode.NORMAL, MemoryMode.CONSERVATIVE, 
                       MemoryMode.LOW_MEMORY, MemoryMode.CRITICAL]
        
        idx1 = modes_order.index(mode_by_percent)
        idx2 = modes_order.index(mode_by_free)
        
        return modes_order[max(idx1, idx2)]
    
    def _set_mode(self, mode: MemoryMode):
        """Set the current mode and notify callbacks"""
        with self._lock:
            old_mode = self._current_mode
            self._current_mode = mode
            self._mode_changes += 1
        
        settings = MODE_CONFIGS[mode]
        
        # Notify callbacks
        for callback in self._mode_callbacks:
            try:
                callback(mode, settings)
            except Exception as e:
                print(f"Mode callback error: {e}")
        
        # Log the change
        if old_mode != mode:
            print(f"⚡ Memory Mode: {old_mode.value} → {mode.value}")
    
    # ==================== PUBLIC API ====================
    
    def get_mode(self) -> MemoryMode:
        """Get current memory mode"""
        return self._manual_override or self._current_mode
    
    def get_settings(self) -> ModeSettings:
        """Get settings for current mode"""
        return MODE_CONFIGS[self.get_mode()]
    
    def set_mode(self, mode: MemoryMode, permanent: bool = False):
        """
        Manually set memory mode.
        
        Args:
            mode: The mode to set
            permanent: If True, disables auto-detection
        """
        self._manual_override = mode
        if permanent:
            self._auto_detect = False
        self._set_mode(mode)
    
    def clear_override(self):
        """Clear manual override and return to auto-detection"""
        self._manual_override = None
        self._auto_detect = True
        self._check_memory()
    
    def add_mode_callback(self, callback: Callable[[MemoryMode, ModeSettings], None]):
        """Subscribe to mode changes"""
        self._mode_callbacks.append(callback)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled in current mode"""
        settings = self.get_settings()
        return getattr(settings, f"enable_{feature}", False)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status"""
        settings = self.get_settings()
        return {
            "mode": self.get_mode().value,
            "auto_detect": self._auto_detect,
            "manual_override": self._manual_override.value if self._manual_override else None,
            "mode_changes": self._mode_changes,
            "last_memory_percent": round(self._last_memory_percent, 1),
            "last_free_gb": round(self._last_free_gb, 2),
            "settings": {
                "resource_poll_interval": settings.resource_poll_interval,
                "ui_update_interval": settings.ui_update_interval,
                "security_enabled": settings.enable_security_monitor,
                "synthesis_enabled": settings.enable_synthesis_engine,
                "quantum_enabled": settings.enable_quantum_mode,
                "max_output_lines": settings.max_output_lines,
            }
        }
    
    def get_recommendations(self) -> List[str]:
        """Get recommendations based on current state"""
        recommendations = []
        mode = self.get_mode()
        
        if mode == MemoryMode.CRITICAL:
            recommendations.extend([
                "Close Claude Desktop app (using ~1.6GB RAM)",
                "Close unused browser tabs",
                "Disable Windows Search indexing temporarily",
                "Consider restarting your computer",
            ])
        elif mode == MemoryMode.LOW_MEMORY:
            recommendations.extend([
                "Close unnecessary applications",
                "Use 'resources stop' to disable security monitor",
                "Avoid running synthesis/quantum simulations",
            ])
        elif mode == MemoryMode.CONSERVATIVE:
            recommendations.extend([
                "System is managing well",
                "Consider closing a few browser tabs",
            ])
        
        return recommendations


# ==================== GLOBAL INSTANCE ====================

_low_memory_manager: Optional[LowMemoryManager] = None
_manager_lock = threading.Lock()


def get_low_memory_manager() -> LowMemoryManager:
    """Get or create the global low memory manager"""
    global _low_memory_manager
    with _manager_lock:
        if _low_memory_manager is None:
            _low_memory_manager = LowMemoryManager()
        return _low_memory_manager


def ensure_low_memory_manager_running() -> LowMemoryManager:
    """Get the manager and ensure it's running"""
    manager = get_low_memory_manager()
    if not manager._running:
        manager.start()
    return manager


def check_startup_memory() -> Dict[str, Any]:
    """
    Check memory at startup and return recommendations.
    Call this before launching the terminal.
    
    Uses the same logic as LowMemoryManager._determine_mode()
    to ensure consistency.
    """
    if not PSUTIL_AVAILABLE:
        return {
            "can_start": True,
            "warning": None,
            "recommended_mode": MemoryMode.CONSERVATIVE,
        }
    
    mem = psutil.virtual_memory()
    free_gb = mem.available / (1024**3)
    percent_used = mem.percent
    
    result = {
        "total_gb": round(mem.total / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "free_gb": round(free_gb, 2),
        "percent_used": round(percent_used, 1),
    }
    
    # Determine mode by percentage (same as LowMemoryManager)
    if percent_used >= 80:
        mode_by_percent = MemoryMode.CRITICAL
    elif percent_used >= 70:
        mode_by_percent = MemoryMode.LOW_MEMORY
    elif percent_used >= 60:
        mode_by_percent = MemoryMode.CONSERVATIVE
    else:
        mode_by_percent = MemoryMode.NORMAL
    
    # Determine mode by free RAM (same as LowMemoryManager)
    if free_gb < 0.5:
        mode_by_free = MemoryMode.CRITICAL
    elif free_gb < 1.0:
        mode_by_free = MemoryMode.LOW_MEMORY
    elif free_gb < 2.0:
        mode_by_free = MemoryMode.CONSERVATIVE
    else:
        mode_by_free = MemoryMode.NORMAL
    
    # Use the MORE CONSERVATIVE of the two
    modes_order = [MemoryMode.NORMAL, MemoryMode.CONSERVATIVE, 
                   MemoryMode.LOW_MEMORY, MemoryMode.CRITICAL]
    idx1 = modes_order.index(mode_by_percent)
    idx2 = modes_order.index(mode_by_free)
    recommended_mode = modes_order[max(idx1, idx2)]
    
    result["recommended_mode"] = recommended_mode
    
    # Set can_start and warning based on mode
    if recommended_mode == MemoryMode.CRITICAL:
        if free_gb < 0.5:
            result["can_start"] = False
            result["warning"] = "CRITICAL: Less than 500MB free RAM. Close other applications first."
        else:
            result["can_start"] = True
            result["warning"] = f"CRITICAL: RAM at {percent_used:.0f}% used. Running in survival mode."
    elif recommended_mode == MemoryMode.LOW_MEMORY:
        result["can_start"] = True
        result["warning"] = f"LOW MEMORY: RAM at {percent_used:.0f}% used. Features will be limited."
    elif recommended_mode == MemoryMode.CONSERVATIVE:
        result["can_start"] = True
        result["warning"] = f"Note: RAM at {percent_used:.0f}%. Running in conservative mode."
    else:
        result["can_start"] = True
        result["warning"] = None
    
    return result
