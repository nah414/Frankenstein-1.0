"""
FRANKENSTEIN 1.0 - Physics Compute Module
Phase 2 Step 3: Real Physics Calculations

Provides actual physics computations:
- Classical mechanics
- Special relativity
- Electromagnetism
- Thermodynamics
- Quantum mechanics constants
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Physical constants (SI units)
CONSTANTS = {
    "c": 299792458.0,           # Speed of light (m/s)
    "h": 6.62607015e-34,        # Planck constant (J·s)
    "hbar": 1.054571817e-34,    # Reduced Planck constant (J·s)
    "G": 6.67430e-11,           # Gravitational constant (m³/(kg·s²))
    "e": 1.602176634e-19,       # Elementary charge (C)
    "me": 9.1093837015e-31,     # Electron mass (kg)
    "mp": 1.67262192369e-27,    # Proton mass (kg)
    "kb": 1.380649e-23,         # Boltzmann constant (J/K)
    "NA": 6.02214076e23,        # Avogadro's number (1/mol)
    "epsilon0": 8.8541878128e-12, # Vacuum permittivity (F/m)
    "mu0": 1.25663706212e-6,    # Vacuum permeability (H/m)
    "alpha": 7.2973525693e-3,   # Fine-structure constant
    "R": 8.314462618,           # Gas constant (J/(mol·K))
}


@dataclass
class LorentzTransform:
    """Lorentz transformation result"""
    gamma: float
    t_prime: np.ndarray
    x_prime: np.ndarray
    time_dilation: float
    length_contraction: float


class PhysicsCompute:
    """Real physics computation engine."""
    
    def __init__(self):
        self.constants = CONSTANTS.copy()
    
    def get_constant(self, name: str) -> float:
        """Get physical constant value"""
        if name not in self.constants:
            raise ValueError(f"Unknown constant: {name}")
        return self.constants[name]

    # === SPECIAL RELATIVITY ===
    
    def lorentz_factor(self, v: float) -> float:
        """Compute Lorentz factor γ = 1/√(1-v²/c²)"""
        c = self.constants["c"]
        if abs(v) >= c:
            raise ValueError("Velocity must be less than c")
        beta = v / c
        return 1.0 / np.sqrt(1 - beta**2)
    
    def lorentz_transform(self, t: np.ndarray, x: np.ndarray, v: float) -> LorentzTransform:
        """Apply Lorentz transformation"""
        c = self.constants["c"]
        gamma = self.lorentz_factor(v)
        beta = v / c
        
        t_prime = gamma * (t - beta * x / c)
        x_prime = gamma * (x - v * t)
        
        return LorentzTransform(
            gamma=gamma,
            t_prime=t_prime,
            x_prime=x_prime,
            time_dilation=gamma,
            length_contraction=1/gamma
        )
    
    def relativistic_energy(self, m: float, v: float) -> Dict[str, float]:
        """Compute relativistic energy components"""
        c = self.constants["c"]
        gamma = self.lorentz_factor(v)
        
        rest_energy = m * c**2
        total_energy = gamma * rest_energy
        kinetic_energy = (gamma - 1) * rest_energy
        momentum = gamma * m * v
        
        return {
            "rest_energy": rest_energy,
            "total_energy": total_energy,
            "kinetic_energy": kinetic_energy,
            "momentum": momentum,
            "gamma": gamma
        }
    
    def relativistic_doppler(self, f0: float, v: float, approaching: bool = True) -> float:
        """Relativistic Doppler effect"""
        c = self.constants["c"]
        beta = v / c
        if approaching:
            return f0 * np.sqrt((1 + beta) / (1 - beta))
        return f0 * np.sqrt((1 - beta) / (1 + beta))

    # === CLASSICAL MECHANICS ===
    
    def projectile_motion(self, v0: float, angle: float, g: float = 9.81, 
                          t_max: Optional[float] = None) -> Dict[str, np.ndarray]:
        """Calculate projectile motion trajectory"""
        theta = np.radians(angle)
        vx = v0 * np.cos(theta)
        vy = v0 * np.sin(theta)
        
        # Time of flight
        t_flight = 2 * vy / g if t_max is None else t_max
        t = np.linspace(0, t_flight, 100)
        
        x = vx * t
        y = vy * t - 0.5 * g * t**2
        y = np.maximum(y, 0)  # Ground level
        
        return {
            "t": t, "x": x, "y": y,
            "range": float(vx * t_flight),
            "max_height": float(vy**2 / (2*g)),
            "time_of_flight": float(t_flight)
        }
    
    def harmonic_oscillator(self, m: float, k: float, x0: float, v0: float, 
                            t_max: float, n_points: int = 100) -> Dict[str, np.ndarray]:
        """Simple harmonic oscillator solution"""
        omega = np.sqrt(k / m)
        A = np.sqrt(x0**2 + (v0/omega)**2)
        phi = np.arctan2(v0/omega, x0)
        
        t = np.linspace(0, t_max, n_points)
        x = A * np.cos(omega * t - phi)
        v = -A * omega * np.sin(omega * t - phi)
        
        return {
            "t": t, "x": x, "v": v,
            "amplitude": float(A),
            "angular_frequency": float(omega),
            "period": float(2 * np.pi / omega),
            "frequency": float(omega / (2 * np.pi))
        }
    
    def orbital_velocity(self, M: float, r: float) -> float:
        """Orbital velocity for circular orbit"""
        G = self.constants["G"]
        return np.sqrt(G * M / r)
    
    def escape_velocity(self, M: float, r: float) -> float:
        """Escape velocity from gravitational body"""
        G = self.constants["G"]
        return np.sqrt(2 * G * M / r)

    # === ELECTROMAGNETISM ===
    
    def coulomb_force(self, q1: float, q2: float, r: float) -> float:
        """Coulomb force between two charges"""
        k = 1 / (4 * np.pi * self.constants["epsilon0"])
        return k * q1 * q2 / r**2
    
    def electric_field(self, q: float, r: float) -> float:
        """Electric field magnitude from point charge"""
        k = 1 / (4 * np.pi * self.constants["epsilon0"])
        return k * q / r**2
    
    def magnetic_force(self, q: float, v: np.ndarray, B: np.ndarray) -> np.ndarray:
        """Lorentz force: F = qv × B"""
        return q * np.cross(v, B)
    
    # === THERMODYNAMICS ===
    
    def ideal_gas(self, n: Optional[float] = None, P: Optional[float] = None,
                  V: Optional[float] = None, T: Optional[float] = None) -> Dict[str, float]:
        """Ideal gas law: PV = nRT"""
        R = self.constants["R"]
        known = sum(x is not None for x in [n, P, V, T])
        
        if known != 3:
            raise ValueError("Exactly 3 of n, P, V, T must be provided")
        
        if n is None:
            n = P * V / (R * T)
        elif P is None:
            P = n * R * T / V
        elif V is None:
            V = n * R * T / P
        else:
            T = P * V / (n * R)
        
        return {"n": n, "P": P, "V": V, "T": T}
    
    def entropy_change(self, Q: float, T: float) -> float:
        """Entropy change for reversible process"""
        return Q / T
    
    def blackbody_radiation(self, T: float, wavelength: np.ndarray) -> np.ndarray:
        """Planck's blackbody radiation law"""
        h = self.constants["h"]
        c = self.constants["c"]
        kb = self.constants["kb"]
        
        numerator = 2 * h * c**2 / wavelength**5
        denominator = np.exp(h * c / (wavelength * kb * T)) - 1
        return numerator / denominator
    
    # === QUANTUM MECHANICS ===
    
    def de_broglie_wavelength(self, m: float, v: float) -> float:
        """de Broglie wavelength λ = h/p"""
        h = self.constants["h"]
        return h / (m * v)
    
    def uncertainty_principle(self, delta_x: Optional[float] = None,
                               delta_p: Optional[float] = None) -> float:
        """Heisenberg uncertainty: Δx·Δp ≥ ℏ/2"""
        hbar = self.constants["hbar"]
        min_product = hbar / 2
        
        if delta_x is not None:
            return min_product / delta_x  # Returns minimum Δp
        elif delta_p is not None:
            return min_product / delta_p  # Returns minimum Δx
        return min_product
    
    def photon_energy(self, frequency: Optional[float] = None,
                      wavelength: Optional[float] = None) -> float:
        """Photon energy E = hf = hc/λ"""
        h = self.constants["h"]
        c = self.constants["c"]
        
        if frequency is not None:
            return h * frequency
        elif wavelength is not None:
            return h * c / wavelength
        raise ValueError("Provide frequency or wavelength")


# Singleton
_physics_compute: Optional['PhysicsCompute'] = None

def get_physics_compute() -> PhysicsCompute:
    global _physics_compute
    if _physics_compute is None:
        _physics_compute = PhysicsCompute()
    return _physics_compute
