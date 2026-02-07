"""
FRANKENSTEIN 2.0 - 3D Visualization Popup Window
Phase 2 Step 3: Separate Terminal for Quantum Visualization

This window spawns ONLY when a calculation is triggered from Monster Terminal.
Displays Schrödinger equation evolution with Lorentz transformation visualization.
"""

import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import queue
import math
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

COLORS = {
    "background": "#0a0a0a", "grid": "#1a3d1a", "wireframe": "#00ff00",
    "wavefunction": "#00ffaa", "probability": "#00ff88", "potential": "#ffaa00",
    "boosted_frame": "#ff00aa", "text": "#00ff00", "dim_text": "#006600",
    "highlight": "#00ffff", "warning": "#ffcc00", "error": "#ff4444"
}


class VisualizationMode(Enum):
    WAVEFUNCTION_3D = "wavefunction_3d"
    PROBABILITY_2D = "probability_2d"
    BLOCH_SPHERE = "bloch_sphere"
    LORENTZ_COMPARISON = "lorentz_comparison"


@dataclass
class VisualizationFrame:
    time: float
    grid: np.ndarray
    wavefunction_real: np.ndarray
    wavefunction_imag: np.ndarray
    probability: np.ndarray
    potential: Optional[np.ndarray] = None
    expectation_x: Optional[float] = None
    
    @property
    def wavefunction(self) -> np.ndarray:
        return self.wavefunction_real + 1j * self.wavefunction_imag


@dataclass
class VisualizationConfig:
    window_title: str = "⚡ FRANKENSTEIN Quantum Visualizer"
    window_width: int = 1200
    window_height: int = 800
    mode: VisualizationMode = VisualizationMode.WAVEFUNCTION_3D
    show_potential: bool = True
    show_expectation: bool = True
    animation_speed: float = 1.0
    loop_animation: bool = True
    show_boosted_frame: bool = False
    use_monster_theme: bool = True


class VisualizationDataBuffer:
    """Thread-safe buffer for visualization data."""
    def __init__(self, max_size: int = 100):
        self._queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._latest_data: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()
    
    def push(self, data: Dict[str, Any]) -> bool:
        try:
            self._queue.put_nowait(data)
            with self._lock:
                self._latest_data = data
            return True
        except queue.Full:
            return False
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._latest_data


class QuantumVisualizationWindow:
    """Separate popup window for quantum simulation visualization."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self._buffer = VisualizationDataBuffer()
        self._frames: List[VisualizationFrame] = []
        self._current_frame_idx: int = 0
        self._lorentz_data: Optional[Dict[str, Any]] = None
        logger.info("QuantumVisualizationWindow initialized")
    
    def load_simulation_data(self, vis_data: Dict[str, Any]) -> bool:
        try:
            if "error" in vis_data:
                return False
            self._frames.clear()
            grid = np.array(vis_data.get("grid", []))
            for frame_data in vis_data.get("frames", []):
                frame = VisualizationFrame(
                    time=frame_data["time"], grid=grid,
                    wavefunction_real=np.array(frame_data["psi_real"]),
                    wavefunction_imag=np.array(frame_data["psi_imag"]),
                    probability=np.array(frame_data["probability"]),
                    expectation_x=frame_data.get("x_expectation"))
                self._frames.append(frame)
            if "lorentz" in vis_data:
                self._lorentz_data = vis_data["lorentz"]
                self.config.show_boosted_frame = True
            self._current_frame_idx = 0
            return True
        except Exception as e:
            logger.error(f"Failed to load visualization data: {e}")
            return False

    
    def render_frame_ascii(self, frame: VisualizationFrame) -> str:
        """Render a frame as ASCII art for terminal display."""
        lines = []
        width, height = 80, 20
        lines.append(f"{'═' * width}")
        lines.append(f"║ SCHRÖDINGER-LORENTZ VISUALIZATION │ t = {frame.time:.4f}")
        lines.append(f"{'═' * width}")
        
        prob = frame.probability
        prob_norm = prob / (np.max(prob) + 1e-10)
        plot_chars = " ░▒▓█"
        indices = np.linspace(0, len(prob_norm) - 1, width - 4).astype(int)
        resampled = prob_norm[indices]
        
        for row in range(height, 0, -1):
            threshold = row / height
            line = "│ "
            for val in resampled:
                if val >= threshold:
                    char_idx = min(int(val * 4), 4)
                    line += plot_chars[char_idx]
                else:
                    line += " "
            line += " │"
            lines.append(line)
        
        lines.append(f"├{'─' * (width - 4)}┤")
        x_min, x_max = frame.grid[0], frame.grid[-1]
        lines.append(f"│ x: [{x_min:.1f}{'─' * (width - 22)}{x_max:.1f}] │")
        lines.append(f"├{'─' * (width - 4)}┤")
        stats = f"⟨x⟩ = {frame.expectation_x:.4f}" if frame.expectation_x else "⟨x⟩ = N/A"
        dx = frame.grid[1] - frame.grid[0]
        norm = np.sum(prob) * dx
        stats += f"  │  Norm = {norm:.4f}"
        lines.append(f"│ {stats:^{width-4}} │")
        lines.append(f"{'═' * width}")
        return "\n".join(lines)

    
    def render_3d_wireframe_ascii(self, frames: List[VisualizationFrame]) -> str:
        """Render 3D-style ASCII visualization of wavefunction evolution."""
        lines = []
        width, depth_lines = 70, 15
        lines.append(f"╔{'═' * (width + 10)}╗")
        lines.append(f"║ 3D SCHRÖDINGER EVOLUTION │ {len(frames)} time steps{' ' * (width - 25)}║")
        lines.append(f"╠{'═' * (width + 10)}╣")
        
        frame_indices = np.linspace(0, len(frames) - 1, depth_lines).astype(int)
        depth_chars = "█▓▒░ "
        
        for i, idx in enumerate(reversed(frame_indices)):
            frame = frames[idx]
            prob = frame.probability / (np.max(frame.probability) + 1e-10)
            sample_idx = np.linspace(0, len(prob) - 1, width).astype(int)
            line_data = prob[sample_idx]
            depth_level = i / depth_lines
            char_set = depth_chars[:max(1, int((1 - depth_level) * len(depth_chars)))]
            line = ""
            for val in line_data:
                if val > 0.7: line += char_set[0]
                elif val > 0.4: line += char_set[min(1, len(char_set)-1)]
                elif val > 0.1: line += char_set[min(2, len(char_set)-1)]
                else: line += " "
            offset = " " * (depth_lines - i)
            t_label = f"t={frame.time:.2f}"
            lines.append(f"║{offset}{line} {t_label}{'.'*(10-len(offset)-len(t_label))}║")
        
        lines.append(f"╠{'═' * (width + 10)}╣")
        lines.append(f"║ x →{' ' * (width - 10)}time ↗{' ' * 8}║")
        lines.append(f"╚{'═' * (width + 10)}╝")
        return "\n".join(lines)
    
    def render_to_terminal(self) -> str:
        output = []
        output.append("╔" + "═" * 80 + "╗")
        output.append("║  ⚡ FRANKENSTEIN 2.0 │ QUANTUM VISUALIZATION WINDOW │ Phase 2 Step 3          ║")
        output.append("╠" + "═" * 80 + "╣")
        if not self._frames:
            output.append("║                     No simulation data loaded                                  ║")
        else:
            frame = self._frames[self._current_frame_idx]
            output.append(f"║ Frame: {self._current_frame_idx + 1}/{len(self._frames)}  │  t = {frame.time:.4f}{' ' * 50}║")
            output.append("╠" + "═" * 80 + "╣")
            output.append(self.render_frame_ascii(frame))
        output.append("╚" + "═" * 80 + "╝")
        return "\n".join(output)
    
    def get_current_frame(self) -> Optional[VisualizationFrame]:
        return self._frames[self._current_frame_idx] if self._frames else None
    
    def next_frame(self) -> bool:
        if not self._frames: return False
        self._current_frame_idx = (self._current_frame_idx + 1) % len(self._frames)
        return True


class VisualizationManager:
    """Manages visualization window lifecycle and communication with Monster Terminal."""
    _instance: Optional['VisualizationManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        self._windows: Dict[str, QuantumVisualizationWindow] = {}
        self._active_window_id: Optional[str] = None
        self._initialized = True
    
    def spawn_window(self, window_id: str = "main", config: Optional[VisualizationConfig] = None) -> QuantumVisualizationWindow:
        if window_id in self._windows:
            return self._windows[window_id]
        window = QuantumVisualizationWindow(config)
        self._windows[window_id] = window
        self._active_window_id = window_id
        logger.info(f"Spawned visualization window: {window_id}")
        return window
    
    def get_window(self, window_id: str = "main") -> Optional[QuantumVisualizationWindow]:
        return self._windows.get(window_id)
    
    def get_active_window(self) -> Optional[QuantumVisualizationWindow]:
        return self._windows.get(self._active_window_id) if self._active_window_id else None
    
    def close_window(self, window_id: str) -> bool:
        if window_id in self._windows:
            del self._windows[window_id]
            if self._active_window_id == window_id:
                self._active_window_id = None
            return True
        return False
    
    def send_to_window(self, vis_data: Dict[str, Any], window_id: str = "main") -> bool:
        window = self.get_window(window_id) or self.spawn_window(window_id)
        return window.load_simulation_data(vis_data)
    
    def render_active_window(self) -> str:
        window = self.get_active_window()
        return window.render_to_terminal() if window else "No active visualization window"


def get_visualization_manager() -> VisualizationManager:
    """Get the global visualization manager instance."""
    return VisualizationManager()
