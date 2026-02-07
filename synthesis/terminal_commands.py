"""
FRANKENSTEIN 2.0 - Monster Terminal Synthesis Commands
Phase 2 Step 3: Terminal Integration for Quantum Simulations

Commands for triggering Schrödinger-Lorentz simulations from Monster Terminal.
Spawns separate 3D visualization window when calculations are executed.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import time
from datetime import datetime

from .relativistic_quantum import (
    RelativisticQuantumEngine, SimulationConfig, SimulationResult,
    LorentzBoost, QuantumPotential, create_schrodinger_lorentz_simulation
)
from .visualization_window import (
    VisualizationManager, VisualizationConfig, get_visualization_manager
)
from .bloch_sphere_popup import (
    launch_bloch_sphere, get_bloch_popup, BlochSpherePopup
)

logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class CommandResult:
    status: CommandStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    visualization_ready: bool = False
    execution_time: float = 0.0


class SynthesisTerminalCommands:
    """Terminal command handlers for quantum synthesis simulations."""
    
    def __init__(self):
        self._engine: Optional[RelativisticQuantumEngine] = None
        self._last_result: Optional[SimulationResult] = None
        self._history: List[Dict[str, Any]] = []
        self._vis_manager = get_visualization_manager()
        self._current_config = SimulationConfig()
        self._commands: Dict[str, Callable] = {
            "run": self.cmd_run, "visualize": self.cmd_visualize, "lorentz": self.cmd_lorentz,
            "potential": self.cmd_potential, "status": self.cmd_status, "history": self.cmd_history,
            "gaussian": self.cmd_gaussian, "tunneling": self.cmd_tunneling, "harmonic": self.cmd_harmonic,
            "compare": self.cmd_compare_frames, "help": self.cmd_help, "bloch": self.cmd_bloch,
        }
    
    def execute(self, command: str, args: List[str]) -> CommandResult:
        start_time = time.time()
        if command not in self._commands:
            return CommandResult(status=CommandStatus.ERROR, message=f"Unknown command: {command}")
        try:
            result = self._commands[command](args)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return CommandResult(status=CommandStatus.ERROR, message=f"Command failed: {str(e)}")
    
    def cmd_run(self, args: List[str]) -> CommandResult:
        preset = args[0] if args else "gaussian"
        velocity, n_points, t_max = 0.0, 256, 10.0
        for i, arg in enumerate(args):
            if arg == "--velocity" and i + 1 < len(args): velocity = float(args[i + 1])
            elif arg == "--points" and i + 1 < len(args): n_points = int(args[i + 1])
            elif arg == "--time" and i + 1 < len(args): t_max = float(args[i + 1])
        
        self._engine = create_schrodinger_lorentz_simulation(velocity=velocity, potential="free" if preset=="gaussian" else preset, n_points=n_points, t_max=t_max)
        
        if preset == "gaussian": result = self._engine.simulate_gaussian_spreading()
        elif preset == "tunneling": result = self._engine.simulate_tunneling()
        elif preset == "harmonic": result = self._engine.simulate_harmonic_oscillator()
        elif preset == "relativistic": result = self._engine.simulate_relativistic_comparison(velocity if velocity else 0.5)
        else: return CommandResult(status=CommandStatus.ERROR, message=f"Unknown preset: {preset}")
        
        self._last_result = result
        if result.success:
            self._history.append({"timestamp": datetime.now().isoformat(), "preset": preset, "frames": len(result.states)})
            vis_data = self._engine.get_visualization_data(result)
            self._vis_manager.send_to_window(vis_data)
            return CommandResult(status=CommandStatus.SUCCESS, message=self._format_output(result, preset), visualization_ready=True)
        return CommandResult(status=CommandStatus.ERROR, message=f"Simulation failed: {result.error_message}")

    
    def cmd_visualize(self, args: List[str]) -> CommandResult:
        mode = args[0] if args else "ascii"
        window = self._vis_manager.get_active_window()
        if not window or not window._frames:
            return CommandResult(status=CommandStatus.ERROR, message="No simulation data. Run 'synthesis run <preset>' first")
        output = window.render_3d_wireframe_ascii(window._frames) if mode == "3d" else window.render_to_terminal()
        return CommandResult(status=CommandStatus.SUCCESS, message=output, visualization_ready=True)
    
    def cmd_lorentz(self, args: List[str]) -> CommandResult:
        if not args: return CommandResult(status=CommandStatus.ERROR, message="Usage: synthesis lorentz <velocity>")
        velocity = float(args[0])
        if abs(velocity) >= 1.0: return CommandResult(status=CommandStatus.ERROR, message="Velocity must be |v/c| < 1")
        boost = LorentzBoost(velocity=velocity)
        self._current_config.include_relativity = True
        self._current_config.boost = boost
        return CommandResult(status=CommandStatus.SUCCESS, message=f"Lorentz boost set: v={velocity}c, γ={boost.gamma:.4f}")
    
    def cmd_potential(self, args: List[str]) -> CommandResult:
        if not args: return CommandResult(status=CommandStatus.ERROR, message="Usage: synthesis potential <type>")
        pot_map = {"free": QuantumPotential.FREE_PARTICLE, "harmonic": QuantumPotential.HARMONIC_OSCILLATOR,
                   "square_well": QuantumPotential.SQUARE_WELL, "double_well": QuantumPotential.DOUBLE_WELL, "coulomb": QuantumPotential.COULOMB}
        if args[0] not in pot_map: return CommandResult(status=CommandStatus.ERROR, message=f"Unknown potential: {args[0]}")
        self._current_config.potential_type = pot_map[args[0]]
        return CommandResult(status=CommandStatus.SUCCESS, message=f"Potential set to: {args[0]}")
    
    def cmd_gaussian(self, args: List[str]) -> CommandResult:
        sigma = float(args[0]) if len(args) > 0 else 0.5
        k0 = float(args[1]) if len(args) > 1 else 2.0
        self._engine = create_schrodinger_lorentz_simulation(velocity=0, potential="free")
        result = self._engine.run_simulation(state_type="gaussian", sigma=sigma, k0=k0)
        self._last_result = result
        if result.success:
            self._vis_manager.send_to_window(self._engine.get_visualization_data(result))
            return CommandResult(status=CommandStatus.SUCCESS, message=self._format_output(result, f"Gaussian σ={sigma}"), visualization_ready=True)
        return CommandResult(status=CommandStatus.ERROR, message=str(result.error_message))
    
    def cmd_tunneling(self, args: List[str]) -> CommandResult:
        barrier = float(args[0]) if args else 5.0
        self._engine = create_schrodinger_lorentz_simulation(velocity=0, potential="square_well")
        result = self._engine.simulate_tunneling(barrier_height=barrier)
        self._last_result = result
        if result.success:
            self._vis_manager.send_to_window(self._engine.get_visualization_data(result))
            return CommandResult(status=CommandStatus.SUCCESS, message=self._format_output(result, f"Tunneling V₀={barrier}"), visualization_ready=True)
        return CommandResult(status=CommandStatus.ERROR, message=str(result.error_message))

    
    def cmd_harmonic(self, args: List[str]) -> CommandResult:
        omega = float(args[0]) if args else 1.0
        self._engine = create_schrodinger_lorentz_simulation(velocity=0, potential="harmonic")
        result = self._engine.simulate_harmonic_oscillator(omega=omega)
        self._last_result = result
        if result.success:
            self._vis_manager.send_to_window(self._engine.get_visualization_data(result))
            return CommandResult(status=CommandStatus.SUCCESS, message=self._format_output(result, f"Harmonic ω={omega}"), visualization_ready=True)
        return CommandResult(status=CommandStatus.ERROR, message=str(result.error_message))
    
    def cmd_compare_frames(self, args: List[str]) -> CommandResult:
        if not args: return CommandResult(status=CommandStatus.ERROR, message="Usage: synthesis compare <velocity>")
        velocity = float(args[0])
        self._engine = create_schrodinger_lorentz_simulation(velocity=velocity, potential="free")
        result = self._engine.simulate_relativistic_comparison(velocity=velocity)
        self._last_result = result
        if result.success:
            self._vis_manager.send_to_window(self._engine.get_visualization_data(result))
            gamma = self._engine.config.boost.gamma
            msg = f"Lorentz comparison: v={velocity}c, γ={gamma:.4f}\nTime dilation: Δt'=Δt/{gamma:.3f}"
            return CommandResult(status=CommandStatus.SUCCESS, message=msg, visualization_ready=True)
        return CommandResult(status=CommandStatus.ERROR, message=str(result.error_message))
    
    def cmd_status(self, args: List[str]) -> CommandResult:
        lines = ["╔═══════════════════════════════════════════════════════════════╗",
                 "║  🧬 SYNTHESIS ENGINE STATUS                                   ║",
                 "╠═══════════════════════════════════════════════════════════════╣"]
        if self._engine:
            cfg = self._engine.config
            lines.append(f"║  Engine: ACTIVE  │  Grid: {cfg.n_points} pts  │  t_max: {cfg.t_max}s             ║")
            if cfg.include_relativity and cfg.boost:
                lines.append(f"║  Lorentz: γ={cfg.boost.gamma:.4f} (v={cfg.boost.velocity}c)                       ║")
        else:
            lines.append("║  Engine: NOT INITIALIZED                                      ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        lines.append("║  TIER 1 LIMITS: 512 pts │ 10,000 steps │ 30s timeout          ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        return CommandResult(status=CommandStatus.SUCCESS, message="\n".join(lines))
    
    def cmd_history(self, args: List[str]) -> CommandResult:
        if not self._history: return CommandResult(status=CommandStatus.SUCCESS, message="No simulation history")
        lines = ["Simulation History:"] + [f"  {i+1}. {h['preset']} - {h['frames']} frames" for i, h in enumerate(self._history[-10:])]
        return CommandResult(status=CommandStatus.SUCCESS, message="\n".join(lines))
    
    def cmd_bloch(self, args: List[str]) -> CommandResult:
        """Launch 3D Bloch sphere visualization popup."""
        sim_type = args[0] if args else "rabi"
        valid_types = ["rabi", "precession", "spiral", "hadamard"]
        
        if sim_type not in valid_types:
            return CommandResult(status=CommandStatus.ERROR, 
                message=f"Unknown type: {sim_type}. Use: {', '.join(valid_types)}")
        
        # Parse optional parameters
        kwargs = {}
        for i, arg in enumerate(args):
            if arg == "--omega" and i + 1 < len(args): kwargs['omega'] = float(args[i + 1])
            elif arg == "--gamma" and i + 1 < len(args): kwargs['lorentz_gamma'] = float(args[i + 1])
        
        success = launch_bloch_sphere(sim_type, **kwargs)
        
        if success:
            msg = f"[BLOCH] 3D BLOCH SPHERE LAUNCHED!\n   Type: {sim_type}\n   Check your browser for the interactive visualization!"
            return CommandResult(status=CommandStatus.SUCCESS, message=msg, visualization_ready=True)
        return CommandResult(status=CommandStatus.ERROR, message="Failed to launch Bloch sphere")

    
    def cmd_help(self, args: List[str]) -> CommandResult:
        help_text = """
================================================================
  FRANKENSTEIN SYNTHESIS ENGINE | Phase 2 Step 3
  Schrodinger Equation + Lorentz + 3D Bloch Sphere
================================================================
  synthesis run <preset> [--velocity V]   Run simulation
    presets: gaussian, tunneling, harmonic, relativistic
    
  synthesis bloch <type> [--omega W] [--gamma G]
    LAUNCHES 3D BLOCH SPHERE POPUP IN BROWSER!
    types: rabi, precession, spiral, hadamard
    
  synthesis gaussian [sigma] [k0]         Gaussian wave packet
  synthesis tunneling [barrier]           Quantum tunneling
  synthesis harmonic [omega]              Harmonic oscillator
  synthesis lorentz <velocity>            Set Lorentz boost (v/c)
  synthesis compare <velocity>            Lab vs boosted frame
  synthesis visualize [ascii|3d]          Show ASCII visualization
  synthesis status                        Show engine status
================================================================
  EXAMPLE: synthesis bloch spiral --gamma 1.25
================================================================"""
        return CommandResult(status=CommandStatus.SUCCESS, message=help_text)
    
    def _format_output(self, result: SimulationResult, title: str) -> str:
        lines = [f"✅ SIMULATION COMPLETE: {title}",
                 f"   Computation time: {result.computation_time:.4f}s",
                 f"   Frames: {len(result.states)}",
                 f"   Time range: 0 → {result.times[-1]:.4f}"]
        if result.boosted_frame_states:
            lines.append(f"   ⚡ Lorentz frame comparison available")
        lines.append("   🖥️ Visualization window ready - run 'synthesis visualize'")
        return "\n".join(lines)


_synthesis_commands: Optional[SynthesisTerminalCommands] = None

def get_synthesis_commands() -> SynthesisTerminalCommands:
    global _synthesis_commands
    if _synthesis_commands is None:
        _synthesis_commands = SynthesisTerminalCommands()
    return _synthesis_commands

def register_with_monster_terminal(terminal) -> bool:
    """Register synthesis commands with Monster Terminal."""
    commands = get_synthesis_commands()
    def handler(args: List[str]) -> str:
        if not args: return commands.execute("help", []).message
        return commands.execute(args[0], args[1:] if len(args) > 1 else []).message
    # terminal.register_command("synthesis", handler, "Quantum synthesis simulations")
    return True
