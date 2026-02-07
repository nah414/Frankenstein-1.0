"""
FRANKENSTEIN 2.0 - 3D Bloch Sphere Popup Window
Phase 2 Step 3: Beautiful 3D Visualization that ACTUALLY pops up!

Generates and launches an interactive Three.js Bloch sphere visualization
in your default browser when calculations are triggered from Monster Terminal.
"""

import numpy as np
import webbrowser
import tempfile
import os
import json
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)

# Output directory for visualization files
VIS_OUTPUT_DIR = Path.home() / "Frankenstein-1.0" / "visualizations"


@dataclass
class BlochStateData:
    """Data for a single Bloch sphere state."""
    theta: float  # Polar angle [0, π]
    phi: float    # Azimuthal angle [0, 2π]
    time: float
    label: str = ""
    
    @property
    def cartesian(self) -> Tuple[float, float, float]:
        """Convert to Cartesian coordinates on unit sphere."""
        x = np.sin(self.theta) * np.cos(self.phi)
        y = np.sin(self.theta) * np.sin(self.phi)
        z = np.cos(self.theta)
        return (float(x), float(y), float(z))


def state_vector_to_bloch(psi: np.ndarray) -> Tuple[float, float]:
    """
    Convert 2D quantum state vector to Bloch sphere angles.
    |ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩
    """
    if len(psi) != 2:
        raise ValueError("Bloch sphere requires 2D state (qubit)")
    
    # Normalize
    psi = psi / np.linalg.norm(psi)
    
    # Extract amplitudes
    alpha, beta = psi[0], psi[1]
    
    # Calculate theta from |alpha|² = cos²(θ/2)
    theta = 2 * np.arccos(np.clip(np.abs(alpha), 0, 1))
    
    # Calculate phi from the phase difference
    if np.abs(beta) > 1e-10:
        phi = np.angle(beta) - np.angle(alpha)
    else:
        phi = 0.0
    
    return float(theta), float(phi)


def generate_bloch_sphere_html(
    trajectory: List[BlochStateData],
    title: str = "Quantum State Evolution",
    lorentz_gamma: Optional[float] = None,
    auto_rotate: bool = True,
    show_trajectory: bool = True
) -> str:
    """
    Generate beautiful Three.js Bloch sphere HTML with Monster Terminal theme.
    """
    
    # Convert trajectory to JSON for JavaScript
    trajectory_json = json.dumps([
        {"theta": s.theta, "phi": s.phi, "time": s.time, 
         "x": s.cartesian[0], "y": s.cartesian[1], "z": s.cartesian[2],
         "label": s.label}
        for s in trajectory
    ])
    
    lorentz_info = f"γ = {lorentz_gamma:.4f}" if lorentz_gamma else ""
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>⚡ FRANKENSTEIN - {title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0a0a0a;
            color: #00ff00;
            font-family: 'Courier New', 'Consolas', monospace;
            overflow: hidden;
        }}
        #container {{
            width: 100vw;
            height: 100vh;
            position: relative;
        }}
        #info-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0, 20, 0, 0.9);
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            min-width: 280px;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
            z-index: 100;
        }}
        #info-panel h1 {{
            color: #00ffaa;
            font-size: 18px;
            margin-bottom: 15px;
            text-shadow: 0 0 10px #00ffaa;
        }}
        #info-panel .logo {{
            color: #00ff00;
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 5px 0;
            border-bottom: 1px solid #003300;
        }}
        .stat-label {{ color: #006600; }}
        .stat-value {{ color: #00ff00; font-weight: bold; }}
        .highlight {{ color: #00ffaa; text-shadow: 0 0 5px #00ffaa; }}
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0, 20, 0, 0.9);
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 15px;
            z-index: 100;
        }}
        button {{
            background: #001a00;
            color: #00ff00;
            border: 1px solid #00ff00;
            padding: 10px 20px;
            margin: 5px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border-radius: 5px;
            transition: all 0.3s;
        }}
        button:hover {{
            background: #003300;
            box-shadow: 0 0 10px #00ff00;
        }}
        button.active {{
            background: #004400;
            box-shadow: 0 0 15px #00ff00;
        }}
        #time-slider {{
            width: 200px;
            margin: 10px 0;
            accent-color: #00ff00;
        }}
        #state-display {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 20, 0, 0.9);
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            min-width: 200px;
            z-index: 100;
        }}
        .ket {{ color: #00ffaa; font-size: 18px; }}
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 24px;
            color: #00ff00;
            text-shadow: 0 0 20px #00ff00;
        }}
    </style>
</head>
<body>
    <div id="container">
        <div id="loading">⚡ Initializing Quantum Visualization...</div>
    </div>
    
    <div id="info-panel">
        <div class="logo">⚡ FRANKENSTEIN 2.0</div>
        <h1>BLOCH SPHERE VISUALIZATION</h1>
        <div class="stat-row">
            <span class="stat-label">Simulation:</span>
            <span class="stat-value">{title}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Time:</span>
            <span class="stat-value" id="current-time">t = 0.000</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">θ (polar):</span>
            <span class="stat-value" id="theta-val">0.000</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">φ (azimuth):</span>
            <span class="stat-value" id="phi-val">0.000</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Frame:</span>
            <span class="stat-value" id="frame-count">1 / {len(trajectory)}</span>
        </div>
        {"<div class='stat-row'><span class='stat-label'>Lorentz:</span><span class='stat-value highlight'>" + lorentz_info + "</span></div>" if lorentz_gamma else ""}
    </div>
    
    <div id="state-display">
        <div style="margin-bottom: 10px; color: #006600;">Quantum State:</div>
        <div class="ket" id="ket-display">|ψ⟩ = |0⟩</div>
        <div style="margin-top: 15px; color: #006600;">Cartesian:</div>
        <div id="cartesian-display" style="font-size: 12px;">
            x: 0.000<br>y: 0.000<br>z: 1.000
        </div>
    </div>
    
    <div id="controls">
        <button id="play-btn" class="active">▶ Play</button>
        <button id="pause-btn">⏸ Pause</button>
        <button id="reset-btn">↺ Reset</button>
        <button id="trajectory-btn">◉ Trail</button>
        <br>
        <input type="range" id="time-slider" min="0" max="{len(trajectory)-1}" value="0">
        <br>
        <span style="font-size: 12px; color: #006600;">Animation Speed:</span>
        <input type="range" id="speed-slider" min="1" max="10" value="3" style="width: 100px;">
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>

        // Trajectory data from Python
        const trajectoryData = {trajectory_json};
        
        // Monster Terminal Colors
        const COLORS = {{
            background: 0x0a0a0a,
            sphereWireframe: 0x00ff00,
            sphereFill: 0x0a1a0a,
            stateVector: 0x00ffaa,
            statePoint: 0x00ffff,
            trajectory: 0xffaa00,
            axisX: 0xff4444,
            axisY: 0x44ff44,
            axisZ: 0x4444ff,
            equator: 0x006600,
            text: 0x00ff00
        }};
        
        let scene, camera, renderer;
        let blochSphere, stateVector, statePoint;
        let trajectoryLine, trajectoryPoints = [];
        let currentFrame = 0;
        let isPlaying = true;
        let showTrajectory = true;
        let animationSpeed = 3;
        let frameCounter = 0;
        
        function init() {{
            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(COLORS.background);
            
            // Camera
            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(3, 2, 3);
            camera.lookAt(0, 0, 0);
            
            // Renderer
            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            document.getElementById('container').appendChild(renderer.domElement);
            document.getElementById('loading').style.display = 'none';
            
            // Create Bloch sphere
            createBlochSphere();
            
            // Create state visualization
            createStateVisualization();
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
            scene.add(ambientLight);
            
            const pointLight = new THREE.PointLight(0x00ff00, 0.8);
            pointLight.position.set(5, 5, 5);
            scene.add(pointLight);
            
            // Mouse controls
            setupMouseControls();
            
            // UI controls
            setupUIControls();
            
            // Start animation
            animate();
        }}
        
        function createBlochSphere() {{
            // Wireframe sphere
            const sphereGeom = new THREE.SphereGeometry(1, 32, 24);
            const wireframeMat = new THREE.MeshBasicMaterial({{
                color: COLORS.sphereWireframe,
                wireframe: true,
                transparent: true,
                opacity: 0.15
            }});
            blochSphere = new THREE.Mesh(sphereGeom, wireframeMat);
            scene.add(blochSphere);
            
            // Solid inner sphere (slightly smaller)
            const innerSphereGeom = new THREE.SphereGeometry(0.98, 32, 24);
            const innerMat = new THREE.MeshPhongMaterial({{
                color: COLORS.sphereFill,
                transparent: true,
                opacity: 0.3,
                side: THREE.BackSide
            }});
            const innerSphere = new THREE.Mesh(innerSphereGeom, innerMat);
            scene.add(innerSphere);
            
            // Equator circle
            const equatorPoints = [];
            for (let i = 0; i <= 64; i++) {{
                const angle = (i / 64) * Math.PI * 2;
                equatorPoints.push(new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle)));
            }}
            const equatorGeom = new THREE.BufferGeometry().setFromPoints(equatorPoints);
            const equatorLine = new THREE.Line(equatorGeom, new THREE.LineBasicMaterial({{ color: COLORS.equator, transparent: true, opacity: 0.5 }}));
            scene.add(equatorLine);
            
            // Prime meridian
            const meridianPoints = [];
            for (let i = 0; i <= 64; i++) {{
                const angle = (i / 64) * Math.PI * 2;
                meridianPoints.push(new THREE.Vector3(0, Math.sin(angle), Math.cos(angle)));
            }}
            const meridianGeom = new THREE.BufferGeometry().setFromPoints(meridianPoints);
            const meridianLine = new THREE.Line(meridianGeom, new THREE.LineBasicMaterial({{ color: COLORS.equator, transparent: true, opacity: 0.3 }}));
            scene.add(meridianLine);
            
            // Axes
            createAxis(new THREE.Vector3(1.3, 0, 0), COLORS.axisX, 'X |+⟩');
            createAxis(new THREE.Vector3(0, 1.3, 0), COLORS.axisY, 'Y |+i⟩');
            createAxis(new THREE.Vector3(0, 0, 1.3), COLORS.axisZ, 'Z |0⟩');
            createAxis(new THREE.Vector3(-1.3, 0, 0), COLORS.axisX, '|-⟩');
            createAxis(new THREE.Vector3(0, -1.3, 0), COLORS.axisY, '|-i⟩');
            createAxis(new THREE.Vector3(0, 0, -1.3), COLORS.axisZ, '|1⟩');
        }}
        
        function createAxis(end, color, label) {{
            const points = [new THREE.Vector3(0, 0, 0), end];
            const geom = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geom, new THREE.LineBasicMaterial({{ color: color }}));
            scene.add(line);
        }}

        
        function createStateVisualization() {{
            // State point (glowing sphere at tip)
            const pointGeom = new THREE.SphereGeometry(0.08, 16, 16);
            const pointMat = new THREE.MeshBasicMaterial({{ color: COLORS.statePoint }});
            statePoint = new THREE.Mesh(pointGeom, pointMat);
            scene.add(statePoint);
            
            // Glow effect for state point
            const glowGeom = new THREE.SphereGeometry(0.12, 16, 16);
            const glowMat = new THREE.MeshBasicMaterial({{
                color: COLORS.statePoint,
                transparent: true,
                opacity: 0.3
            }});
            const glow = new THREE.Mesh(glowGeom, glowMat);
            statePoint.add(glow);
            
            // State vector (line from origin to state)
            updateStateVector(trajectoryData[0]);
            
            // Initialize trajectory
            trajectoryPoints = [];
        }}
        
        function updateStateVector(data) {{
            // Remove old vector
            if (stateVector) scene.remove(stateVector);
            
            // Create new vector
            const points = [
                new THREE.Vector3(0, 0, 0),
                new THREE.Vector3(data.x, data.z, data.y)  // Swap y/z for Three.js
            ];
            const geom = new THREE.BufferGeometry().setFromPoints(points);
            const mat = new THREE.LineBasicMaterial({{ color: COLORS.stateVector, linewidth: 3 }});
            stateVector = new THREE.Line(geom, mat);
            scene.add(stateVector);
            
            // Update state point position
            statePoint.position.set(data.x, data.z, data.y);
            
            // Add to trajectory
            if (showTrajectory) {{
                trajectoryPoints.push(new THREE.Vector3(data.x, data.z, data.y));
                if (trajectoryPoints.length > 500) trajectoryPoints.shift();
                updateTrajectoryLine();
            }}
            
            // Update UI
            updateUI(data);
        }}
        
        function updateTrajectoryLine() {{
            if (trajectoryLine) scene.remove(trajectoryLine);
            if (trajectoryPoints.length < 2) return;
            
            const geom = new THREE.BufferGeometry().setFromPoints(trajectoryPoints);
            const mat = new THREE.LineBasicMaterial({{
                color: COLORS.trajectory,
                transparent: true,
                opacity: 0.7
            }});
            trajectoryLine = new THREE.Line(geom, mat);
            scene.add(trajectoryLine);
        }}
        
        function updateUI(data) {{
            document.getElementById('current-time').textContent = 't = ' + data.time.toFixed(3);
            document.getElementById('theta-val').textContent = data.theta.toFixed(4);
            document.getElementById('phi-val').textContent = data.phi.toFixed(4);
            document.getElementById('frame-count').textContent = (currentFrame + 1) + ' / ' + trajectoryData.length;
            
            // Cartesian
            document.getElementById('cartesian-display').innerHTML = 
                'x: ' + data.x.toFixed(3) + '<br>y: ' + data.y.toFixed(3) + '<br>z: ' + data.z.toFixed(3);
            
            // Ket notation
            const cosHalf = Math.cos(data.theta / 2);
            const sinHalf = Math.sin(data.theta / 2);
            let ket = '|ψ⟩ = ';
            if (Math.abs(cosHalf) > 0.01) {{
                ket += cosHalf.toFixed(2) + '|0⟩';
                if (Math.abs(sinHalf) > 0.01) ket += ' + ';
            }}
            if (Math.abs(sinHalf) > 0.01) {{
                ket += 'e^(i' + data.phi.toFixed(2) + ')' + sinHalf.toFixed(2) + '|1⟩';
            }}
            document.getElementById('ket-display').textContent = ket;
        }}
        
        function setupMouseControls() {{
            let isDragging = false;
            let previousPosition = {{ x: 0, y: 0 }};
            
            renderer.domElement.addEventListener('mousedown', (e) => {{
                isDragging = true;
                previousPosition = {{ x: e.clientX, y: e.clientY }};
            }});
            
            renderer.domElement.addEventListener('mouseup', () => isDragging = false);
            renderer.domElement.addEventListener('mouseleave', () => isDragging = false);
            
            renderer.domElement.addEventListener('mousemove', (e) => {{
                if (!isDragging) return;
                
                const deltaX = e.clientX - previousPosition.x;
                const deltaY = e.clientY - previousPosition.y;
                
                // Rotate camera around origin
                const spherical = new THREE.Spherical();
                spherical.setFromVector3(camera.position);
                spherical.theta -= deltaX * 0.005;
                spherical.phi -= deltaY * 0.005;
                spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
                
                camera.position.setFromSpherical(spherical);
                camera.lookAt(0, 0, 0);
                
                previousPosition = {{ x: e.clientX, y: e.clientY }};
            }});
            
            // Zoom with wheel
            renderer.domElement.addEventListener('wheel', (e) => {{
                const zoom = e.deltaY > 0 ? 1.1 : 0.9;
                camera.position.multiplyScalar(zoom);
                camera.position.clampLength(2, 10);
            }});
        }}

        
        function setupUIControls() {{
            document.getElementById('play-btn').addEventListener('click', () => {{
                isPlaying = true;
                document.getElementById('play-btn').classList.add('active');
                document.getElementById('pause-btn').classList.remove('active');
            }});
            
            document.getElementById('pause-btn').addEventListener('click', () => {{
                isPlaying = false;
                document.getElementById('pause-btn').classList.add('active');
                document.getElementById('play-btn').classList.remove('active');
            }});
            
            document.getElementById('reset-btn').addEventListener('click', () => {{
                currentFrame = 0;
                trajectoryPoints = [];
                if (trajectoryLine) scene.remove(trajectoryLine);
                updateStateVector(trajectoryData[0]);
                document.getElementById('time-slider').value = 0;
            }});
            
            document.getElementById('trajectory-btn').addEventListener('click', function() {{
                showTrajectory = !showTrajectory;
                this.classList.toggle('active');
                if (!showTrajectory && trajectoryLine) {{
                    scene.remove(trajectoryLine);
                    trajectoryPoints = [];
                }}
            }});
            
            document.getElementById('time-slider').addEventListener('input', (e) => {{
                currentFrame = parseInt(e.target.value);
                updateStateVector(trajectoryData[currentFrame]);
            }});
            
            document.getElementById('speed-slider').addEventListener('input', (e) => {{
                animationSpeed = parseInt(e.target.value);
            }});
        }}
        
        function animate() {{
            requestAnimationFrame(animate);
            
            // Gentle sphere rotation
            blochSphere.rotation.y += 0.001;
            
            // Animation playback
            if (isPlaying) {{
                frameCounter++;
                if (frameCounter >= (11 - animationSpeed)) {{
                    frameCounter = 0;
                    currentFrame = (currentFrame + 1) % trajectoryData.length;
                    updateStateVector(trajectoryData[currentFrame]);
                    document.getElementById('time-slider').value = currentFrame;
                }}
            }}
            
            // Pulse effect on state point
            const pulse = 1 + 0.1 * Math.sin(Date.now() * 0.005);
            statePoint.scale.set(pulse, pulse, pulse);
            
            renderer.render(scene, camera);
        }}
        
        // Handle resize
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        
        // Initialize
        init();
    </script>
</body>
</html>'''
    
    return html


def create_rabi_oscillation_trajectory(omega: float = 1.0, t_max: float = 10.0, n_steps: int = 200) -> List[BlochStateData]:
    """Generate Rabi oscillation trajectory on Bloch sphere."""
    trajectory = []
    times = np.linspace(0, t_max, n_steps)
    
    for t in times:
        # Rabi oscillation: rotation around X-axis
        theta = np.pi * (1 - np.cos(omega * t)) / 2  # Oscillates 0 to π
        phi = 0.0  # Stays in XZ plane for pure Rabi
        
        trajectory.append(BlochStateData(
            theta=float(theta),
            phi=float(phi),
            time=float(t),
            label=f"t={t:.2f}"
        ))
    
    return trajectory


def create_precession_trajectory(omega_z: float = 1.0, theta_0: float = np.pi/4, 
                                  t_max: float = 10.0, n_steps: int = 200) -> List[BlochStateData]:
    """Generate precession around Z-axis (like in magnetic field)."""
    trajectory = []
    times = np.linspace(0, t_max, n_steps)
    
    for t in times:
        theta = theta_0  # Fixed polar angle
        phi = omega_z * t  # Precessing azimuthal angle
        
        trajectory.append(BlochStateData(
            theta=float(theta),
            phi=float(phi % (2 * np.pi)),
            time=float(t),
            label=f"t={t:.2f}"
        ))
    
    return trajectory


def create_spiral_trajectory(t_max: float = 10.0, n_steps: int = 300) -> List[BlochStateData]:
    """Generate spiral trajectory (Rabi + precession combined)."""
    trajectory = []
    times = np.linspace(0, t_max, n_steps)
    
    omega_rabi = 0.5
    omega_z = 2.0
    
    for t in times:
        theta = np.pi * (1 - np.cos(omega_rabi * t)) / 2
        phi = omega_z * t
        
        trajectory.append(BlochStateData(
            theta=float(theta),
            phi=float(phi % (2 * np.pi)),
            time=float(t),
            label=f"t={t:.2f}"
        ))
    
    return trajectory


def create_hadamard_gate_trajectory(n_steps: int = 50) -> List[BlochStateData]:
    """Animate Hadamard gate: |0⟩ → |+⟩ (rotation around Y+Z axis)."""
    trajectory = []
    
    # Start at |0⟩ (north pole)
    # End at |+⟩ (on equator, x-axis)
    for i in range(n_steps):
        t = i / (n_steps - 1)
        theta = t * np.pi / 2  # 0 to π/2
        phi = 0.0
        
        trajectory.append(BlochStateData(
            theta=float(theta),
            phi=float(phi),
            time=float(t),
            label="Hadamard"
        ))
    
    return trajectory


class BlochSpherePopup:
    """Manager for launching 3D Bloch sphere visualization popups."""
    
    def __init__(self):
        self._output_dir = VIS_OUTPUT_DIR
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._last_file: Optional[Path] = None
    
    def launch(self, 
               trajectory: List[BlochStateData],
               title: str = "Quantum State Evolution",
               lorentz_gamma: Optional[float] = None) -> bool:
        """
        Generate HTML and launch in default browser.
        
        THIS IS THE POPUP TRIGGER - called when calculations run!
        """
        try:
            # Generate HTML
            html_content = generate_bloch_sphere_html(
                trajectory=trajectory,
                title=title,
                lorentz_gamma=lorentz_gamma,
                auto_rotate=True,
                show_trajectory=True
            )
            
            # Write to file
            filename = f"bloch_sphere_{int(time.time())}.html"
            filepath = self._output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self._last_file = filepath
            
            # LAUNCH IN BROWSER - THE POPUP!
            webbrowser.open(f'file://{filepath}')
            
            logger.info(f"Launched Bloch sphere visualization: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch Bloch sphere popup: {e}")
            return False
    
    def launch_rabi(self, omega: float = 1.0, t_max: float = 10.0, lorentz_gamma: Optional[float] = None) -> bool:
        """Launch Rabi oscillation visualization."""
        trajectory = create_rabi_oscillation_trajectory(omega=omega, t_max=t_max)
        return self.launch(trajectory, title=f"Rabi Oscillation (ω={omega})", lorentz_gamma=lorentz_gamma)
    
    def launch_precession(self, omega_z: float = 1.0, theta_0: float = np.pi/4, lorentz_gamma: Optional[float] = None) -> bool:
        """Launch Larmor precession visualization."""
        trajectory = create_precession_trajectory(omega_z=omega_z, theta_0=theta_0)
        return self.launch(trajectory, title=f"Larmor Precession (ω={omega_z})", lorentz_gamma=lorentz_gamma)
    
    def launch_spiral(self, lorentz_gamma: Optional[float] = None) -> bool:
        """Launch spiral (combined Rabi + precession) visualization."""
        trajectory = create_spiral_trajectory()
        return self.launch(trajectory, title="Quantum Spiral Evolution", lorentz_gamma=lorentz_gamma)
    
    def launch_hadamard(self) -> bool:
        """Launch Hadamard gate visualization."""
        trajectory = create_hadamard_gate_trajectory()
        return self.launch(trajectory, title="Hadamard Gate |0⟩ → |+⟩")


# Global instance
_bloch_popup: Optional[BlochSpherePopup] = None

def get_bloch_popup() -> BlochSpherePopup:
    """Get global Bloch sphere popup manager."""
    global _bloch_popup
    if _bloch_popup is None:
        _bloch_popup = BlochSpherePopup()
    return _bloch_popup


def launch_bloch_sphere(simulation_type: str = "rabi", **kwargs) -> bool:
    """
    Convenience function to launch Bloch sphere popup.
    
    Called by Monster Terminal when running quantum calculations!
    
    Args:
        simulation_type: "rabi", "precession", "spiral", "hadamard"
        **kwargs: Additional parameters (omega, lorentz_gamma, etc.)
    """
    popup = get_bloch_popup()
    
    if simulation_type == "rabi":
        return popup.launch_rabi(
            omega=kwargs.get('omega', 1.0),
            t_max=kwargs.get('t_max', 10.0),
            lorentz_gamma=kwargs.get('lorentz_gamma')
        )
    elif simulation_type == "precession":
        return popup.launch_precession(
            omega_z=kwargs.get('omega_z', 1.0),
            theta_0=kwargs.get('theta_0', np.pi/4),
            lorentz_gamma=kwargs.get('lorentz_gamma')
        )
    elif simulation_type == "spiral":
        return popup.launch_spiral(lorentz_gamma=kwargs.get('lorentz_gamma'))
    elif simulation_type == "hadamard":
        return popup.launch_hadamard()
    else:
        logger.warning(f"Unknown simulation type: {simulation_type}, defaulting to rabi")
        return popup.launch_rabi()


if __name__ == "__main__":
    print("⚡ FRANKENSTEIN 2.0 - Bloch Sphere Popup Test")
    print("=" * 50)
    print("Launching 3D Bloch sphere in your browser...")
    
    # Test launch
    success = launch_bloch_sphere("spiral", lorentz_gamma=1.25)
    
    if success:
        print("✅ Bloch sphere visualization launched!")
        print("   Check your browser for the 3D interactive view.")
    else:
        print("❌ Failed to launch visualization")
