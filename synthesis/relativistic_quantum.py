"""
FRANKENSTEIN 2.0 - Relativistic Quantum Simulator
Phase 2 Step 3: Schrödinger Equation + Lorentz Transformations

Classical simulation of quantum dynamics under special relativity.
Tier 1 local hardware constraints (no quantum hardware required).

Physics:
- Schrödinger equation: iℏ∂ψ/∂t = Ĥψ
- Lorentz transformation: t' = γ(t - vx/c²), x' = γ(x - vt)
- Relativistic corrections to quantum dynamics
"""

import numpy as np
from typing import Optional, List, Tuple, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import math
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Physical constants (SI units where applicable, normalized for simulation)
HBAR = 1.0545718e-34  # Reduced Planck constant (J·s)
C = 299792458.0       # Speed of light (m/s)
C_NORMALIZED = 1.0    # Normalized c for relativistic simulations

# Tier 1 Hardware Limits (Dell i3 8th Gen)
MAX_GRID_POINTS = 512      # Spatial discretization limit
MAX_TIME_STEPS = 10000     # Evolution steps limit
MAX_DIMENSIONS = 3         # Max spatial dimensions
MAX_QUBITS_SIMULATED = 18  # Max qubits for state vectors
COMPUTATION_TIMEOUT = 30.0  # Seconds


class SimulationFrame(Enum):
    """Reference frames for relativistic simulations."""
    LAB = "lab"              # Laboratory rest frame
    PARTICLE = "particle"    # Co-moving with particle
    BOOSTED = "boosted"      # Arbitrary boosted frame


class QuantumPotential(Enum):
    """Pre-defined quantum potentials."""
    FREE_PARTICLE = "free"
    HARMONIC_OSCILLATOR = "harmonic"
    SQUARE_WELL = "square_well"
    DOUBLE_WELL = "double_well"
    COULOMB = "coulomb"
    CUSTOM = "custom"


@dataclass
class LorentzBoost:
    """Lorentz transformation parameters."""
    velocity: float          # v/c (dimensionless, -1 < v < 1)
    gamma: float = field(init=False)
    direction: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0]))
    
    def __post_init__(self):
        if abs(self.velocity) >= 1.0:
            raise ValueError("Velocity must be |v/c| < 1 for subluminal motion")
        self.gamma = 1.0 / math.sqrt(1.0 - self.velocity**2)
    
    def transform_spacetime(self, t: np.ndarray, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Apply Lorentz transformation: t' = γ(t - vx/c²), x' = γ(x - vt)"""
        v = self.velocity
        t_prime = self.gamma * (t - v * x)
        x_prime = self.gamma * (x - v * t)
        return t_prime, x_prime
    
    def transform_momentum_energy(self, E: np.ndarray, p: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Transform energy-momentum 4-vector."""
        v = self.velocity
        E_prime = self.gamma * (E - v * p)
        p_prime = self.gamma * (p - v * E)
        return E_prime, p_prime
    
    def time_dilation_factor(self) -> float:
        return self.gamma
    
    def length_contraction_factor(self) -> float:
        return 1.0 / self.gamma


@dataclass
class SimulationConfig:
    """Configuration for quantum simulation."""
    x_min: float = -10.0
    x_max: float = 10.0
    n_points: int = 256
    dimensions: int = 1
    t_max: float = 10.0
    n_steps: int = 1000
    mass: float = 1.0
    hbar: float = 1.0
    potential_type: QuantumPotential = QuantumPotential.FREE_PARTICLE
    potential_params: Dict[str, float] = field(default_factory=dict)
    include_relativity: bool = False
    boost: Optional[LorentzBoost] = None
    enforce_limits: bool = True
    
    def __post_init__(self):
        if self.enforce_limits:
            self.n_points = min(self.n_points, MAX_GRID_POINTS)
            self.n_steps = min(self.n_steps, MAX_TIME_STEPS)
            self.dimensions = min(self.dimensions, MAX_DIMENSIONS)


@dataclass
class QuantumState:
    """Quantum state representation."""
    wavefunction: np.ndarray
    grid: np.ndarray
    time: float
    probabilities: np.ndarray = field(init=False)
    
    def __post_init__(self):
        self.probabilities = np.abs(self.wavefunction)**2

    
    @property
    def norm(self) -> float:
        dx = self.grid[1] - self.grid[0] if len(self.grid) > 1 else 1.0
        return np.sum(self.probabilities) * dx
    
    def expectation_position(self) -> float:
        dx = self.grid[1] - self.grid[0]
        return np.sum(self.grid * self.probabilities) * dx / self.norm
    
    def expectation_momentum(self, hbar: float = 1.0) -> float:
        dx = self.grid[1] - self.grid[0]
        k = np.fft.fftfreq(len(self.grid), dx) * 2 * np.pi
        psi_k = np.fft.fft(self.wavefunction)
        dk = 2 * np.pi / (len(self.grid) * dx)
        return hbar * np.real(np.sum(k * np.abs(psi_k)**2)) * dk / self.norm
    
    def uncertainty_position(self) -> float:
        dx = self.grid[1] - self.grid[0]
        x_mean = self.expectation_position()
        x2_mean = np.sum(self.grid**2 * self.probabilities) * dx / self.norm
        return np.sqrt(max(0, x2_mean - x_mean**2))


@dataclass
class SimulationResult:
    """Result of quantum simulation."""
    success: bool
    config: SimulationConfig
    states: List[QuantumState]
    times: np.ndarray
    computation_time: float
    bloch_trajectory: Optional[List[Tuple[float, float]]] = None
    expectation_x: Optional[np.ndarray] = None
    expectation_p: Optional[np.ndarray] = None
    lab_frame_states: Optional[List[QuantumState]] = None
    boosted_frame_states: Optional[List[QuantumState]] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class RelativisticQuantumEngine:
    """
    Schrödinger equation solver with Lorentz transformation support.
    Solves: iℏ∂ψ/∂t = Ĥψ where Ĥ = -ℏ²/2m ∇² + V(x)
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self._running = False
        self._x: Optional[np.ndarray] = None
        self._dx: Optional[float] = None
        self._k: Optional[np.ndarray] = None
        self._kinetic_k: Optional[np.ndarray] = None
        self._potential: Optional[np.ndarray] = None
        self._last_result: Optional[SimulationResult] = None
        logger.info(f"RelativisticQuantumEngine initialized")
    
    def setup_grid(self) -> None:
        self._x = np.linspace(self.config.x_min, self.config.x_max, self.config.n_points)
        self._dx = self._x[1] - self._x[0]
        self._k = 2 * np.pi * np.fft.fftfreq(self.config.n_points, self._dx)
        self._kinetic_k = (self.config.hbar**2 * self._k**2) / (2 * self.config.mass)
    
    def setup_potential(self, custom_potential: Optional[Callable] = None) -> None:
        if self._x is None:
            self.setup_grid()
        x = self._x
        params = self.config.potential_params
        
        if custom_potential is not None:
            self._potential = custom_potential(x)
        elif self.config.potential_type == QuantumPotential.FREE_PARTICLE:
            self._potential = np.zeros_like(x)
        elif self.config.potential_type == QuantumPotential.HARMONIC_OSCILLATOR:
            omega = params.get('omega', 1.0)
            self._potential = 0.5 * self.config.mass * omega**2 * x**2
        elif self.config.potential_type == QuantumPotential.SQUARE_WELL:
            width = params.get('width', 4.0)
            depth = params.get('depth', 10.0)
            self._potential = np.where(np.abs(x) < width/2, -depth, 0)
        elif self.config.potential_type == QuantumPotential.DOUBLE_WELL:
            a = params.get('a', 1.0)
            b = params.get('b', 4.0)
            self._potential = a * x**4 - b * x**2
        elif self.config.potential_type == QuantumPotential.COULOMB:
            Z = params.get('Z', 1.0)
            epsilon = params.get('epsilon', 0.1)
            self._potential = -Z / (np.abs(x) + epsilon)

    
    def create_initial_state(self, state_type: str = "gaussian", **kwargs) -> QuantumState:
        if self._x is None:
            self.setup_grid()
        x = self._x
        
        if state_type == "gaussian":
            x0 = kwargs.get('x0', 0.0)
            sigma = kwargs.get('sigma', 1.0)
            k0 = kwargs.get('k0', 0.0)
            norm = (2 * np.pi * sigma**2)**(-0.25)
            psi = norm * np.exp(-(x - x0)**2 / (4 * sigma**2)) * np.exp(1j * k0 * x)
        elif state_type == "plane_wave":
            k0 = kwargs.get('k0', 1.0)
            window = np.exp(-((x - x.mean())**2) / (2 * ((x.max()-x.min())/4)**2))
            psi = window * np.exp(1j * k0 * x)
            psi /= np.sqrt(np.sum(np.abs(psi)**2) * self._dx)
        elif state_type == "superposition":
            x1, x2 = kwargs.get('x1', -2.0), kwargs.get('x2', 2.0)
            sigma = kwargs.get('sigma', 0.5)
            psi1 = np.exp(-(x - x1)**2 / (4 * sigma**2))
            psi2 = np.exp(-(x - x2)**2 / (4 * sigma**2))
            psi = (psi1 + psi2) / np.sqrt(2)
            psi /= np.sqrt(np.sum(np.abs(psi)**2) * self._dx)
        else:
            raise ValueError(f"Unknown state type: {state_type}")
        return QuantumState(wavefunction=psi, grid=x.copy(), time=0.0)
    
    def evolve_step(self, psi: np.ndarray, dt: float) -> np.ndarray:
        """Split-step Fourier method."""
        hbar = self.config.hbar
        psi = psi * np.exp(-1j * self._potential * dt / (2 * hbar))
        psi_k = np.fft.fft(psi)
        psi_k = psi_k * np.exp(-1j * self._kinetic_k * dt / hbar)
        psi = np.fft.ifft(psi_k)
        psi = psi * np.exp(-1j * self._potential * dt / (2 * hbar))
        return psi

    
    def apply_lorentz_transform(self, states: List[QuantumState], times: np.ndarray,
                                boost: LorentzBoost) -> Tuple[List[QuantumState], np.ndarray]:
        """Transform simulation results to a boosted reference frame."""
        transformed_states = []
        for state in states:
            x = state.grid
            t = state.time
            v, gamma = boost.velocity, boost.gamma
            x_prime = x.copy()
            t_prime = t / gamma
            x_lab = gamma * (x_prime + v * t_prime)
            psi_transformed = np.interp(x_prime, x_lab, state.wavefunction, left=0, right=0)
            k_boost = self.config.mass * v / self.config.hbar
            phase_correction = np.exp(-1j * k_boost * x_prime)
            psi_transformed = psi_transformed * phase_correction
            norm = np.sqrt(np.sum(np.abs(psi_transformed)**2) * self._dx)
            if norm > 1e-10:
                psi_transformed /= norm
            transformed_states.append(QuantumState(wavefunction=psi_transformed, grid=x_prime, time=t_prime))
        return transformed_states, times / boost.gamma
    
    def run_simulation(self, initial_state: Optional[QuantumState] = None, **kwargs) -> SimulationResult:
        start_time = time.time()
        self._running = True
        warnings = []
        try:
            self.setup_grid()
            self.setup_potential()
            if initial_state is None:
                initial_state = self.create_initial_state(**kwargs)
            psi = initial_state.wavefunction.copy()
            dt = self.config.t_max / self.config.n_steps
            times = np.linspace(0, self.config.t_max, self.config.n_steps + 1)
            states: List[QuantumState] = [initial_state]
            expectation_x = [initial_state.expectation_position()]
            expectation_p = [initial_state.expectation_momentum(self.config.hbar)]

            
            for i, t in enumerate(times[1:], 1):
                if time.time() - start_time > COMPUTATION_TIMEOUT:
                    warnings.append(f"Simulation truncated at step {i} due to timeout")
                    break
                psi = self.evolve_step(psi, dt)
                if i % 10 == 0 or i == len(times) - 1:
                    state = QuantumState(wavefunction=psi.copy(), grid=self._x.copy(), time=t)
                    states.append(state)
                    expectation_x.append(state.expectation_position())
                    expectation_p.append(state.expectation_momentum(self.config.hbar))
            
            boosted_states = None
            if self.config.include_relativity and self.config.boost:
                boosted_states, _ = self.apply_lorentz_transform(states, np.array([s.time for s in states]), self.config.boost)
                if self.config.boost.gamma > 2.0:
                    warnings.append(f"High Lorentz factor γ={self.config.boost.gamma:.2f}")
            
            computation_time = time.time() - start_time
            result = SimulationResult(
                success=True, config=self.config, states=states,
                times=np.array([s.time for s in states]), computation_time=computation_time,
                expectation_x=np.array(expectation_x), expectation_p=np.array(expectation_p),
                lab_frame_states=states, boosted_frame_states=boosted_states, warnings=warnings
            )
            self._last_result = result
            return result
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return SimulationResult(success=False, config=self.config, states=[], times=np.array([]),
                                    computation_time=time.time()-start_time, error_message=str(e))
        finally:
            self._running = False

    
    def get_visualization_data(self, result: SimulationResult) -> Dict[str, Any]:
        """Package simulation results for 3D visualization window."""
        if not result.success or not result.states:
            return {"error": "No valid simulation data"}
        vis_data = {
            "type": "schrodinger_lorentz", "timestamp": datetime.now().isoformat(),
            "config": {"x_range": [self.config.x_min, self.config.x_max], "t_max": self.config.t_max,
                       "potential": self.config.potential_type.value, "relativistic": self.config.include_relativity},
            "grid": self._x.tolist() if self._x is not None else [], "times": result.times.tolist(), "frames": []
        }
        for state in result.states:
            vis_data["frames"].append({"time": state.time, "psi_real": state.wavefunction.real.tolist(),
                "psi_imag": state.wavefunction.imag.tolist(), "probability": state.probabilities.tolist(),
                "x_expectation": state.expectation_position(), "norm": state.norm})
        if result.boosted_frame_states:
            vis_data["boosted_frames"] = [{"time": s.time, "psi_real": s.wavefunction.real.tolist(),
                "psi_imag": s.wavefunction.imag.tolist(), "probability": s.probabilities.tolist()} 
                for s in result.boosted_frame_states]
            vis_data["lorentz"] = {"velocity": self.config.boost.velocity if self.config.boost else 0,
                "gamma": self.config.boost.gamma if self.config.boost else 1.0,
                "time_dilation": self.config.boost.time_dilation_factor() if self.config.boost else 1.0}
        vis_data["summary"] = {"computation_time": result.computation_time, "n_frames": len(result.states),
            "warnings": result.warnings}
        return vis_data
    
    def simulate_gaussian_spreading(self, sigma: float = 0.5, k0: float = 0) -> SimulationResult:
        self.config.potential_type = QuantumPotential.FREE_PARTICLE
        return self.run_simulation(state_type="gaussian", sigma=sigma, k0=k0)
    
    def simulate_harmonic_oscillator(self, omega: float = 1.0) -> SimulationResult:
        self.config.potential_type = QuantumPotential.HARMONIC_OSCILLATOR
        self.config.potential_params = {"omega": omega}
        return self.run_simulation(state_type="gaussian", x0=2.0, sigma=0.5)

    
    def simulate_tunneling(self, barrier_height: float = 5.0) -> SimulationResult:
        def barrier_potential(x):
            return np.where((x > 0) & (x < 1), barrier_height, 0)
        self.config.potential_type = QuantumPotential.CUSTOM
        self.setup_potential(custom_potential=barrier_potential)
        return self.run_simulation(state_type="gaussian", x0=-3.0, k0=3.0, sigma=0.5)
    
    def simulate_relativistic_comparison(self, velocity: float = 0.5) -> SimulationResult:
        self.config.include_relativity = True
        self.config.boost = LorentzBoost(velocity=velocity)
        self.config.potential_type = QuantumPotential.FREE_PARTICLE
        result = self.run_simulation(state_type="gaussian", x0=0, k0=2.0, sigma=0.5)
        if result.success:
            gamma = self.config.boost.gamma
            result.warnings.append(f"Lorentz boost v={velocity}c, γ={gamma:.3f}")
        return result


def create_schrodinger_lorentz_simulation(velocity: float = 0.0, potential: str = "free",
                                          n_points: int = 256, t_max: float = 10.0) -> RelativisticQuantumEngine:
    """Factory function for quick simulation setup."""
    potential_map = {"free": QuantumPotential.FREE_PARTICLE, "harmonic": QuantumPotential.HARMONIC_OSCILLATOR,
        "square_well": QuantumPotential.SQUARE_WELL, "double_well": QuantumPotential.DOUBLE_WELL, "coulomb": QuantumPotential.COULOMB}
    config = SimulationConfig(
        n_points=n_points, t_max=t_max,
        potential_type=potential_map.get(potential, QuantumPotential.FREE_PARTICLE),
        include_relativity=abs(velocity) > 0.001,
        boost=LorentzBoost(velocity=velocity) if abs(velocity) > 0.001 else None
    )
    return RelativisticQuantumEngine(config)
