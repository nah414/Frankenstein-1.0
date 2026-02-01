"""
FRANKENSTEIN 2.0 - 3D Bloch Sphere Visualization
Phase 2 Step 3: Quantum State Visualization

Renders interactive 3D Bloch sphere in Monster Terminal theme.
Shows quantum state evolution and measurement outcomes.
"""

import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
import math


@dataclass
class BlochSphereConfig:
    """Configuration for Bloch sphere rendering."""
    # Monster Terminal theme colors (green phosphor aesthetic)
    sphere_color: str = "#1a3d1a"          # Dark green sphere
    wireframe_color: str = "#00ff00"        # Bright green wireframe
    state_color: str = "#00ffaa"            # Cyan-green state vector
    trajectory_color: str = "#ffaa00"       # Orange trajectory
    axis_color: str = "#00aa00"             # Dim green axes
    text_color: str = "#00ff00"             # Bright green text
    
    # Rendering settings
    wireframe_segments: int = 16
    sphere_opacity: float = 0.2
    vector_length: float = 1.0
    animation_speed: float = 1.0
    show_axes: bool = True
    show_labels: bool = True
    show_trajectory: bool = True


@dataclass
class BlochState:
    """Quantum state on the Bloch sphere."""
    theta: float = 0.0      # Polar angle [0, π]
    phi: float = 0.0        # Azimuthal angle [0, 2π]
    label: str = ""
    color: Optional[str] = None
    
    @property
    def cartesian(self) -> Tuple[float, float, float]:
        """Convert to Cartesian coordinates (x, y, z)."""
        x = math.sin(self.theta) * math.cos(self.phi)
        y = math.sin(self.theta) * math.sin(self.phi)
        z = math.cos(self.theta)
        return (x, y, z)
    
    @classmethod
    def from_cartesian(cls, x: float, y: float, z: float, label: str = "") -> 'BlochState':
        """Create state from Cartesian coordinates."""
        r = math.sqrt(x*x + y*y + z*z)
        if r < 1e-10:
            return cls(theta=0.0, phi=0.0, label=label)
        
        theta = math.acos(z / r)
        phi = math.atan2(y, x)
        if phi < 0:
            phi += 2 * math.pi
        return cls(theta=theta, phi=phi, label=label)
    
    @classmethod
    def from_state_vector(cls, psi: np.ndarray, label: str = "") -> 'BlochState':
        """Create from quantum state vector |ψ⟩ = α|0⟩ + β|1⟩."""
        alpha, beta = psi[0], psi[1]
        theta = 2 * math.acos(min(1.0, abs(alpha)))
        phi = np.angle(beta) - np.angle(alpha) if abs(beta) > 1e-10 else 0.0
        phi = phi % (2 * math.pi)
        return cls(theta=theta, phi=phi, label=label)


# Standard basis states
BLOCH_ZERO = BlochState(theta=0, phi=0, label="|0⟩")           # North pole
BLOCH_ONE = BlochState(theta=math.pi, phi=0, label="|1⟩")      # South pole
BLOCH_PLUS = BlochState(theta=math.pi/2, phi=0, label="|+⟩")   # +X axis
BLOCH_MINUS = BlochState(theta=math.pi/2, phi=math.pi, label="|-⟩")  # -X axis
BLOCH_PLUS_I = BlochState(theta=math.pi/2, phi=math.pi/2, label="|+i⟩")  # +Y axis
BLOCH_MINUS_I = BlochState(theta=math.pi/2, phi=3*math.pi/2, label="|-i⟩")  # -Y axis


class BlochSphere:
    """
    3D Bloch Sphere visualization for quantum states.
    
    Renders states, trajectories, and evolution with
    Monster Terminal aesthetics (green phosphor theme).
    """
    
    def __init__(self, config: Optional[BlochSphereConfig] = None):
        """Initialize Bloch sphere with optional configuration."""
        self.config = config or BlochSphereConfig()
        self.states: List[BlochState] = []
        self.trajectory: List[Tuple[float, float, float]] = []
        self._animation_frame: int = 0
        self._basis_vectors = [
            BLOCH_ZERO, BLOCH_ONE, 
            BLOCH_PLUS, BLOCH_MINUS,
            BLOCH_PLUS_I, BLOCH_MINUS_I
        ]

    
    def add_state(self, state: BlochState):
        """Add a state to display on the sphere."""
        self.states.append(state)
    
    def set_trajectory(self, trajectory: List[Tuple[float, float]]):
        """Set trajectory from list of (theta, phi) pairs."""
        self.trajectory = []
        for theta, phi in trajectory:
            x = math.sin(theta) * math.cos(phi)
            y = math.sin(theta) * math.sin(phi)
            z = math.cos(theta)
            self.trajectory.append((x, y, z))
    
    def clear(self):
        """Clear all states and trajectory."""
        self.states = []
        self.trajectory = []
        self._animation_frame = 0
    
    def generate_wireframe(self) -> Dict[str, List]:
        """Generate wireframe geometry for the sphere."""
        segments = self.config.wireframe_segments
        lines = {"latitude": [], "longitude": []}
        
        # Latitude circles
        for i in range(1, segments):
            theta = math.pi * i / segments
            circle = []
            for j in range(segments + 1):
                phi = 2 * math.pi * j / segments
                x = math.sin(theta) * math.cos(phi)
                y = math.sin(theta) * math.sin(phi)
                z = math.cos(theta)
                circle.append((x, y, z))
            lines["latitude"].append(circle)

        
        # Longitude circles
        for j in range(segments):
            phi = 2 * math.pi * j / segments
            circle = []
            for i in range(segments + 1):
                theta = math.pi * i / segments
                x = math.sin(theta) * math.cos(phi)
                y = math.sin(theta) * math.sin(phi)
                z = math.cos(theta)
                circle.append((x, y, z))
            lines["longitude"].append(circle)
        
        return lines
    
    def generate_axes(self) -> List[Dict]:
        """Generate axis lines for X, Y, Z."""
        return [
            {"start": (-1.2, 0, 0), "end": (1.2, 0, 0), "label": "X"},
            {"start": (0, -1.2, 0), "end": (0, 1.2, 0), "label": "Y"},
            {"start": (0, 0, -1.2), "end": (0, 0, 1.2), "label": "Z"},
        ]
    
    def get_render_data(self) -> Dict[str, Any]:
        """Get all data needed to render the Bloch sphere."""
        return {
            "config": {
                "sphere_color": self.config.sphere_color,
                "wireframe_color": self.config.wireframe_color,
                "state_color": self.config.state_color,
                "trajectory_color": self.config.trajectory_color,
                "axis_color": self.config.axis_color,
                "text_color": self.config.text_color,
                "sphere_opacity": self.config.sphere_opacity
            },
            "wireframe": self.generate_wireframe(),
            "axes": self.generate_axes() if self.config.show_axes else [],

            "states": [
                {
                    "cartesian": s.cartesian,
                    "theta": s.theta,
                    "phi": s.phi,
                    "label": s.label,
                    "color": s.color or self.config.state_color
                }
                for s in self.states
            ],
            "trajectory": self.trajectory if self.config.show_trajectory else [],
            "basis_states": [
                {"cartesian": b.cartesian, "label": b.label}
                for b in self._basis_vectors
            ] if self.config.show_labels else [],
            "animation_frame": self._animation_frame
        }
    
    def animate_rotation(self, axis: str, angle: float, steps: int = 60):
        """
        Generate animation frames for rotation around axis.
        
        Args:
            axis: 'X', 'Y', or 'Z'
            angle: Total rotation angle in radians
            steps: Number of animation frames
        """
        if not self.states:
            return []
        
        frames = []
        state = self.states[0]
        x, y, z = state.cartesian

        
        for i in range(steps + 1):
            t = angle * i / steps
            
            if axis.upper() == 'X':
                # Rotation around X-axis
                new_y = y * math.cos(t) - z * math.sin(t)
                new_z = y * math.sin(t) + z * math.cos(t)
                frames.append((x, new_y, new_z))
            elif axis.upper() == 'Y':
                # Rotation around Y-axis
                new_x = x * math.cos(t) + z * math.sin(t)
                new_z = -x * math.sin(t) + z * math.cos(t)
                frames.append((new_x, y, new_z))
            elif axis.upper() == 'Z':
                # Rotation around Z-axis
                new_x = x * math.cos(t) - y * math.sin(t)
                new_y = x * math.sin(t) + y * math.cos(t)
                frames.append((new_x, new_y, z))
        
        return frames
    
    def get_ascii_representation(self, width: int = 40, height: int = 20) -> str:
        """
        Generate ASCII art representation for terminal display.
        Monster Terminal aesthetic with green characters.
        """
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        center_x, center_y = width // 2, height // 2
        radius = min(width // 3, height // 2 - 1)

        
        # Draw sphere outline
        for i in range(60):
            angle = 2 * math.pi * i / 60
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * 0.5 * math.sin(angle))
            if 0 <= x < width and 0 <= y < height:
                canvas[y][x] = '○'
        
        # Draw axes
        for i in range(-radius, radius + 1):
            # X-axis (horizontal)
            x = center_x + i
            if 0 <= x < width:
                canvas[center_y][x] = '─' if canvas[center_y][x] == ' ' else '┼'
            # Z-axis (vertical) 
            y = center_y + int(i * 0.5)
            if 0 <= y < height:
                canvas[y][center_x] = '│' if canvas[y][center_x] == ' ' else '┼'
        
        # Draw state vector endpoint
        if self.states:
            state = self.states[0]
            x, y, z = state.cartesian
            px = int(center_x + x * radius)
            py = int(center_y - z * radius * 0.5)  # Invert Z for display
            if 0 <= px < width and 0 <= py < height:
                canvas[py][px] = '◉'
        
        # Add labels
        canvas[0][center_x] = '|0⟩'[0] if center_x < width else ' '
        canvas[height-1][center_x] = '|1⟩'[0] if center_x < width else ' '
        
        return '\n'.join(''.join(row) for row in canvas)
