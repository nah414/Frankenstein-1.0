"""
FRANKENSTEIN 1.0 - Synthesis Panel Widget
Monster Terminal Integration

Provides UI panel for quantum-classical synthesis visualization
with 3D Bloch sphere and simulation controls.
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button, Label, ProgressBar
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.message import Message
from typing import Optional, Dict, Any, List
import math


class SynthesisHeader(Static):
    """Animated header for synthesis panel."""
    
    DEFAULT_CSS = """
    SynthesisHeader {
        width: 100%;
        height: 3;
        background: $surface;
        border: heavy $success;
        text-align: center;
        padding: 0 1;
    }
    """
    
    frame = reactive(0)
    
    def __init__(self):
        super().__init__()
        self._symbols = ["◇", "◆", "◈", "◆"]
        self._title = "⚗ SYNTHESIS ENGINE ⚗"

    
    def on_mount(self):
        """Start animation timer."""
        self.set_interval(0.3, self._animate)
    
    def _animate(self):
        """Animate the header symbols."""
        self.frame = (self.frame + 1) % len(self._symbols)
    
    def watch_frame(self, frame: int):
        """Update display when frame changes."""
        sym = self._symbols[frame]
        self.update(f"{sym} {self._title} {sym}")


class BlochSphereDisplay(Static):
    """ASCII Bloch sphere visualization widget."""
    
    DEFAULT_CSS = """
    BlochSphereDisplay {
        width: 100%;
        height: 22;
        background: #0a0a0a;
        border: round $success;
        padding: 0 1;
        color: $success;
    }
    """
    
    theta = reactive(0.0)
    phi = reactive(0.0)
    
    def __init__(self):
        super().__init__()
        self._width = 45
        self._height = 18

    
    def set_state(self, theta: float, phi: float):
        """Set the quantum state to display."""
        self.theta = theta
        self.phi = phi
    
    def render_sphere(self) -> str:
        """Render ASCII Bloch sphere with current state."""
        w, h = self._width, self._height
        canvas = [[' ' for _ in range(w)] for _ in range(h)]
        cx, cy = w // 2, h // 2
        rx, ry = w // 3, h // 2 - 2
        
        # Draw sphere ellipse outline
        for i in range(72):
            angle = 2 * math.pi * i / 72
            x = int(cx + rx * math.cos(angle))
            y = int(cy + ry * 0.6 * math.sin(angle))
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = '·'
        
        # Draw equator ellipse
        for i in range(72):
            angle = 2 * math.pi * i / 72
            x = int(cx + rx * math.cos(angle))
            y = int(cy + ry * 0.15 * math.sin(angle))
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = '─' if canvas[y][x] == ' ' else '┼'
        
        # Draw Z-axis
        for i in range(-ry, ry + 1):
            y = cy + i
            if 0 <= y < h:
                canvas[y][cx] = '│' if canvas[y][cx] == ' ' else '┼'

        
        # Calculate state position on sphere
        state_x = math.sin(self.theta) * math.cos(self.phi)
        state_y = math.sin(self.theta) * math.sin(self.phi)
        state_z = math.cos(self.theta)
        
        # Project to 2D
        px = int(cx + state_x * rx)
        py = int(cy - state_z * ry * 0.6)
        
        # Draw state vector line from center
        steps = 15
        for i in range(1, steps):
            t = i / steps
            lx = int(cx + t * (px - cx))
            ly = int(cy + t * (py - cy))
            if 0 <= lx < w and 0 <= ly < h:
                canvas[ly][lx] = '╱' if state_x * state_z > 0 else '╲'
        
        # Draw state point
        if 0 <= px < w and 0 <= py < h:
            canvas[py][px] = '◉'
        
        # Add labels
        if cx < w:
            canvas[0][cx] = '0'  # |0⟩
            canvas[h-1][cx] = '1'  # |1⟩
        if cx + rx < w:
            canvas[cy][cx + rx - 1] = '+'  # |+⟩
        if cx - rx >= 0:
            canvas[cy][cx - rx + 1] = '-'  # |-⟩
        
        # Title line
        title = "═══ BLOCH SPHERE ═══"
        title_start = (w - len(title)) // 2
        return title + '\n' + '\n'.join(''.join(row) for row in canvas)

    
    def watch_theta(self, theta: float):
        """Update display when theta changes."""
        self.update(self.render_sphere())
    
    def watch_phi(self, phi: float):
        """Update display when phi changes."""
        self.update(self.render_sphere())
    
    def on_mount(self):
        """Initialize display."""
        self.update(self.render_sphere())


class SimulationControls(Container):
    """Control buttons for synthesis simulations."""
    
    DEFAULT_CSS = """
    SimulationControls {
        width: 100%;
        height: 5;
        layout: horizontal;
        padding: 1;
        background: $surface;
        border: round $success;
    }
    
    SimulationControls Button {
        margin: 0 1;
        min-width: 12;
    }
    """
    
    class SimulationStarted(Message):
        """Simulation started message."""
        def __init__(self, sim_type: str):
            self.sim_type = sim_type
            super().__init__()

    
    def compose(self) -> ComposeResult:
        """Create control buttons."""
        yield Button("▶ Rabi", id="btn-rabi", variant="success")
        yield Button("⟳ Hadamard", id="btn-hadamard", variant="primary")
        yield Button("↺ X-Gate", id="btn-xgate", variant="primary")
        yield Button("⊙ Measure", id="btn-measure", variant="warning")
        yield Button("⬚ Reset", id="btn-reset", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle control button presses."""
        btn_id = event.button.id
        if btn_id == "btn-rabi":
            self.post_message(self.SimulationStarted("rabi"))
        elif btn_id == "btn-hadamard":
            self.post_message(self.SimulationStarted("hadamard"))
        elif btn_id == "btn-xgate":
            self.post_message(self.SimulationStarted("xgate"))
        elif btn_id == "btn-measure":
            self.post_message(self.SimulationStarted("measure"))
        elif btn_id == "btn-reset":
            self.post_message(self.SimulationStarted("reset"))


class StatusDisplay(Static):
    """Synthesis engine status display."""
    
    DEFAULT_CSS = """
    StatusDisplay {
        width: 100%;
        height: 6;
        background: $surface;
        border: round $success;
        padding: 0 1;
    }
    """

    
    def update_status(self, status: Dict[str, Any]):
        """Update status display with engine data."""
        mode = status.get("mode", "unknown")
        qutip = "✓" if status.get("qutip_available", False) else "✗"
        sims = status.get("total_simulations", 0)
        time = status.get("last_computation_time", "0.000s")
        
        bloch = status.get("bloch_state", {})
        theta = bloch.get("theta", 0)
        phi = bloch.get("phi", 0)
        cart = bloch.get("cartesian", (0, 0, 0))
        
        text = f"""╔══ SYNTHESIS STATUS ══╗
║ Mode: {mode:<14} QuTiP: {qutip} ║
║ Simulations: {sims:<6} Time: {time:<7} ║
║ θ={theta:.2f} φ={phi:.2f} ({cart[0]:.2f},{cart[1]:.2f},{cart[2]:.2f}) ║
╚═══════════════════════╝"""
        self.update(text)


class SynthesisPanel(Container):
    """
    Main synthesis panel widget for Monster Terminal.
    
    Integrates Bloch sphere visualization, simulation controls,
    and status display with Monster Terminal theme.
    """
    
    DEFAULT_CSS = """
    SynthesisPanel {
        width: 100%;
        height: 100%;
        background: $background;
        border: heavy $success;
        padding: 1;
    }
    """

    
    def __init__(self, synthesis_engine=None):
        """Initialize synthesis panel with optional engine reference."""
        super().__init__()
        self.engine = synthesis_engine
        self._bloch_display: Optional[BlochSphereDisplay] = None
        self._status_display: Optional[StatusDisplay] = None
        self._animation_running = False
    
    def compose(self) -> ComposeResult:
        """Build the synthesis panel UI."""
        yield SynthesisHeader()
        yield BlochSphereDisplay()
        yield SimulationControls()
        yield StatusDisplay()
    
    def on_mount(self):
        """Initialize panel and get references."""
        self._bloch_display = self.query_one(BlochSphereDisplay)
        self._status_display = self.query_one(StatusDisplay)
        
        # Initial status update
        if self.engine:
            self._status_display.update_status(self.engine.get_status())
        
        # Start animation loop
        self.set_interval(0.05, self._animation_tick)
    
    def _animation_tick(self):
        """Handle animation updates."""
        if self._animation_running and hasattr(self, '_animation_frames'):
            if self._animation_index < len(self._animation_frames):
                frame = self._animation_frames[self._animation_index]
                # Convert cartesian back to spherical
                x, y, z = frame
                theta = math.acos(max(-1, min(1, z)))
                phi = math.atan2(y, x) % (2 * math.pi)
                self._bloch_display.set_state(theta, phi)
                self._animation_index += 1
            else:
                self._animation_running = False

    
    def on_simulation_controls_simulation_started(
        self, message: SimulationControls.SimulationStarted
    ):
        """Handle simulation control events."""
        sim_type = message.sim_type
        
        if sim_type == "reset":
            self._bloch_display.set_state(0.0, 0.0)  # |0⟩ state
            self._animation_running = False
            
        elif sim_type == "hadamard":
            # Animate Hadamard gate: |0⟩ → |+⟩ (theta: 0 → π/2)
            self._start_animation_to(math.pi / 2, 0.0, steps=30)
            
        elif sim_type == "xgate":
            # Animate X gate: flip theta
            current_theta = self._bloch_display.theta
            new_theta = math.pi - current_theta
            self._start_animation_to(new_theta, self._bloch_display.phi, steps=30)
            
        elif sim_type == "rabi":
            # Rabi oscillation animation
            self._start_rabi_animation()
            
        elif sim_type == "measure":
            # Collapse to |0⟩ or |1⟩ based on probability
            import random
            prob_0 = math.cos(self._bloch_display.theta / 2) ** 2
            if random.random() < prob_0:
                self._bloch_display.set_state(0.0, 0.0)  # |0⟩
            else:
                self._bloch_display.set_state(math.pi, 0.0)  # |1⟩
        
        # Update status
        if self.engine and self._status_display:
            self._status_display.update_status(self.engine.get_status())

    
    def _start_animation_to(self, target_theta: float, target_phi: float, steps: int = 30):
        """Animate state to target position."""
        start_theta = self._bloch_display.theta
        start_phi = self._bloch_display.phi
        
        self._animation_frames = []
        for i in range(steps + 1):
            t = i / steps
            # Linear interpolation
            theta = start_theta + t * (target_theta - start_theta)
            phi = start_phi + t * (target_phi - start_phi)
            x = math.sin(theta) * math.cos(phi)
            y = math.sin(theta) * math.sin(phi)
            z = math.cos(theta)
            self._animation_frames.append((x, y, z))
        
        self._animation_index = 0
        self._animation_running = True
    
    def _start_rabi_animation(self):
        """Animate Rabi oscillation (full rotation around X-axis)."""
        self._animation_frames = []
        steps = 60
        
        # Current state
        theta = self._bloch_display.theta
        phi = self._bloch_display.phi
        x = math.sin(theta) * math.cos(phi)
        y = math.sin(theta) * math.sin(phi)
        z = math.cos(theta)
        
        # Rotate around X-axis
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            new_y = y * math.cos(angle) - z * math.sin(angle)
            new_z = y * math.sin(angle) + z * math.cos(angle)
            self._animation_frames.append((x, new_y, new_z))
        
        self._animation_index = 0
        self._animation_running = True
