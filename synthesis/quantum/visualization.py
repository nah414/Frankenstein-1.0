#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Visualization Tools
Phase 2, Step 3: Enhanced Visualization for Quantum States

Provides visualization utilities including:
- Multi-qubit Bloch sphere projection
- State vector histograms
- Time evolution animations
- Circuit diagrams (ASCII)

Author: Frankenstein Project
"""

import os
import json
import webbrowser
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from numpy import pi


class QuantumVisualizer:
    """
    Visualization tools for quantum states and computations.
    """
    
    def __init__(self, output_callback=None):
        self._output = output_callback or print
        self._temp_dir = Path.home() / ".frankenstein" / "visualizations"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
    
    def set_output_callback(self, callback):
        """Set terminal output callback"""
        self._output = callback
    
    # ==================== BLOCH SPHERE ====================
    
    def launch_bloch_sphere(
        self,
        coords: Tuple[float, float, float],
        probabilities: Dict[str, float] = None,
        statevector: np.ndarray = None,
        result_id: str = "quantum"
    ) -> bool:
        """
        Launch interactive 3D Bloch sphere in browser.
        
        Args:
            coords: (x, y, z) Bloch coordinates
            probabilities: Measurement probabilities
            statevector: Full statevector
            result_id: Unique identifier for temp file
            
        Returns:
            True if launched successfully
        """
        widget_dir = Path(__file__).parent.parent.parent / "widget"
        template_path = widget_dir / "bloch_sphere.html"
        
        if not template_path.exists():
            self._output(f"⚠️  Bloch sphere template not found at {template_path}\n")
            return False
        
        x, y, z = coords
        
        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Inject data
        html = html.replace('{{BLOCH_X}}', str(x))
        html = html.replace('{{BLOCH_Y}}', str(y))
        html = html.replace('{{BLOCH_Z}}', str(z))
        
        if probabilities:
            html = html.replace('{{PROBABILITIES}}', json.dumps(probabilities))
        else:
            html = html.replace('{{PROBABILITIES}}', '{}')
        
        if statevector is not None:
            sv_data = {
                'real': statevector.real.tolist(),
                'imag': statevector.imag.tolist()
            }
            html = html.replace('{{STATEVECTOR}}', json.dumps(sv_data))
        else:
            html = html.replace('{{STATEVECTOR}}', '{"real":[1,0],"imag":[0,0]}')
        
        # Write temp file
        output_path = self._temp_dir / f"bloch_{result_id}.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Launch browser
        webbrowser.open(f'file:///{output_path.as_posix()}')
        
        return True

    def launch_multi_qubit_bloch(
        self,
        qubit_coords: List[Tuple[float, float, float]],
        entanglement_info: Dict[str, Any],
        num_qubits: int,
        gate_count: int = 0,
        result_id: str = "multi"
    ) -> bool:
        """
        Launch multi-qubit Bloch sphere visualization.

        Shows all qubits in a grid layout with entanglement status.

        Args:
            qubit_coords: List of (x, y, z) Bloch coordinates per qubit
            entanglement_info: Dict from get_entanglement_info()
            num_qubits: Number of qubits in the system
            gate_count: Number of gates applied
            result_id: Unique ID for temp file

        Returns:
            True if launched successfully
        """
        widget_dir = Path(__file__).parent.parent.parent / "widget"
        template_path = widget_dir / "bloch_sphere_multi.html"

        if not template_path.exists():
            self._output(f"⚠️ Multi-qubit template not found at {template_path}\n")
            # Fall back to single-qubit visualization
            if qubit_coords:
                return self.launch_bloch_sphere(qubit_coords[0], result_id=result_id)
            return False

        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # Prepare data
        is_entangled = entanglement_info.get('is_entangled', False)

        # Check if JAX is available (for backend display)
        try:
            import jax
            backend = 'JAX'
        except ImportError:
            backend = 'NumPy'

        # Inject values
        html = html.replace('{{NUM_QUBITS}}', str(num_qubits))
        html = html.replace('{{QUBIT_COORDS}}', json.dumps(qubit_coords))
        html = html.replace('{{IS_ENTANGLED}}', 'true' if is_entangled else 'false')
        html = html.replace('{{SCHMIDT_RANK}}', str(entanglement_info.get('schmidt_rank', 1)))
        html = html.replace('{{ENTROPY}}', f"{entanglement_info.get('entanglement_entropy', 0.0):.3f}")
        html = html.replace('{{MAX_ENTROPY}}', f"{entanglement_info.get('max_entanglement', 0.0):.1f}")
        html = html.replace('{{GATE_COUNT}}', str(gate_count))
        html = html.replace('{{BACKEND}}', backend)

        html = html.replace('{{ENTANGLEMENT_CLASS}}', 'entangled' if is_entangled else 'separable')
        html = html.replace('{{ENTANGLEMENT_STATUS}}', '⚛️ ENTANGLED' if is_entangled else '✓ SEPARABLE')

        # Write temp file
        output_path = self._temp_dir / f"bloch_multi_{result_id}.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        # Launch browser
        webbrowser.open(f'file:///{output_path.as_posix()}')

        return True

    def get_multi_qubit_bloch(
        self,
        statevector: np.ndarray,
        n_qubits: int
    ) -> List[Tuple[float, float, float]]:
        """
        Get Bloch coordinates for each qubit in a multi-qubit state.
        
        Uses partial trace to get reduced density matrix for each qubit.
        
        Args:
            statevector: Full statevector
            n_qubits: Number of qubits
            
        Returns:
            List of (x, y, z) tuples for each qubit
        """
        coords = []
        
        for q in range(n_qubits):
            rho = self._partial_trace_single(statevector, q, n_qubits)
            
            # Extract Bloch coordinates from density matrix
            x = float(2 * np.real(rho[0, 1]))
            y = float(2 * np.imag(rho[1, 0]))
            z = float(np.real(rho[0, 0] - rho[1, 1]))
            
            coords.append((x, y, z))
        
        return coords
    
    def _partial_trace_single(
        self,
        statevector: np.ndarray,
        keep_qubit: int,
        n_qubits: int
    ) -> np.ndarray:
        """Partial trace keeping only one qubit"""
        dim = 2 ** n_qubits
        rho_full = np.outer(statevector, np.conj(statevector))
        rho_reduced = np.zeros((2, 2), dtype=np.complex128)
        
        for i in range(2):
            for j in range(2):
                for k in range(dim):
                    for l in range(dim):
                        if ((k >> keep_qubit) & 1) == i and ((l >> keep_qubit) & 1) == j:
                            other_k = k ^ (i << keep_qubit)
                            other_l = l ^ (j << keep_qubit)
                            if other_k == other_l:
                                rho_reduced[i, j] += rho_full[k, l]
        
        return rho_reduced
    
    # ==================== ASCII VISUALIZATION ====================
    
    def ascii_bloch(self, x: float, y: float, z: float) -> str:
        """
        Generate ASCII art representation of Bloch sphere with state.
        
        Returns multiline string.
        """
        # Simple 2D projection
        # Project onto XZ plane (side view)
        lines = []
        lines.append("        |0⟩")
        lines.append("         ↑")
        lines.append("         │")
        
        # Draw sphere boundary (simplified)
        for row in range(7):
            row_pos = 3 - row  # -3 to 3
            
            if row == 0 or row == 6:
                lines.append("         │")
            elif row == 3:
                # Equator
                if abs(x) < 0.1 and abs(z) < 0.1:
                    lines.append("    ←────●────→ X")
                else:
                    # Map x to position
                    x_pos = int(4 + x * 4)
                    x_pos = max(0, min(9, x_pos))
                    line = list("    ←─────────→ X")
                    line[x_pos + 4] = '●'
                    lines.append(''.join(line))
            else:
                lines.append("         │")
        
        lines.append("         │")
        lines.append("         ↓")
        lines.append("        |1⟩")
        lines.append("")
        lines.append(f"  Bloch: x={x:+.3f}, y={y:+.3f}, z={z:+.3f}")
        
        return '\n'.join(lines)
    
    def ascii_histogram(self, probabilities: Dict[str, float], width: int = 40) -> str:
        """
        Generate ASCII histogram of measurement probabilities.
        """
        lines = []
        lines.append("\n📊 Probability Distribution")
        lines.append("─" * (width + 15))
        
        max_prob = max(probabilities.values()) if probabilities else 1.0
        
        for basis, prob in sorted(probabilities.items()):
            bar_len = int(prob / max_prob * width)
            bar = "█" * bar_len + "░" * (width - bar_len)
            lines.append(f"  |{basis}⟩ {bar} {prob*100:5.1f}%")
        
        lines.append("─" * (width + 15))
        
        return '\n'.join(lines)
    
    def ascii_statevector(self, statevector: np.ndarray, n_qubits: int) -> str:
        """
        Generate ASCII representation of statevector.
        """
        lines = []
        lines.append("\n🌊 Statevector")
        lines.append("─" * 50)
        
        terms = []
        for i, amp in enumerate(statevector):
            if np.abs(amp) > 1e-6:
                basis = format(i, f'0{n_qubits}b')
                
                # Format amplitude
                if np.abs(amp.imag) < 1e-6:
                    amp_str = f"{amp.real:+.4f}"
                elif np.abs(amp.real) < 1e-6:
                    amp_str = f"{amp.imag:+.4f}i"
                else:
                    amp_str = f"({amp.real:+.4f}{amp.imag:+.4f}i)"
                
                terms.append(f"  {amp_str} |{basis}⟩")
        
        lines.append("|ψ⟩ =")
        lines.extend(terms[:10])  # Limit output
        if len(terms) > 10:
            lines.append(f"  ... and {len(terms) - 10} more terms")
        
        lines.append("─" * 50)
        
        return '\n'.join(lines)
    
    # ==================== CIRCUIT DIAGRAMS ====================
    
    def ascii_circuit(self, gate_log: List[Dict[str, Any]], n_qubits: int) -> str:
        """
        Generate ASCII circuit diagram from gate log.
        
        Args:
            gate_log: List of gate operations from SynthesisEngine
            n_qubits: Number of qubits
            
        Returns:
            ASCII circuit diagram string
        """
        # Initialize qubit lines
        lines = [f"q{i}: ─" for i in range(n_qubits)]
        
        # Map gate matrices to names
        gate_names = {
            'H': 'H',
            'X': 'X', 
            'Y': 'Y',
            'Z': 'Z',
            'S': 'S',
            'T': 'T',
        }
        
        for gate_info in gate_log[:20]:  # Limit to first 20 gates
            target = gate_info.get('target', 0)
            control = gate_info.get('control')
            
            # Determine gate symbol
            gate_matrix = np.array(gate_info.get('gate', [[1, 0], [0, 1]]))
            symbol = 'U'
            
            # Try to identify common gates
            for name, sym in gate_names.items():
                if name in str(gate_info):
                    symbol = sym
                    break
            
            if control is not None:
                # Two-qubit gate
                for i in range(n_qubits):
                    if i == control:
                        lines[i] += "─●─"
                    elif i == target:
                        lines[i] += f"─{symbol}─"
                    elif min(control, target) < i < max(control, target):
                        lines[i] += "─│─"
                    else:
                        lines[i] += "───"
            else:
                # Single-qubit gate
                for i in range(n_qubits):
                    if i == target:
                        lines[i] += f"─{symbol}─"
                    else:
                        lines[i] += "───"
        
        # Add termination
        for i in range(n_qubits):
            lines[i] += "─"
        
        # Reverse order (qubit 0 at bottom typically)
        lines = lines[::-1]
        
        header = "\n🔲 Circuit Diagram\n" + "─" * 60 + "\n"
        footer = "\n" + "─" * 60
        
        return header + '\n'.join(lines) + footer
    
    # ==================== MEASUREMENT RESULTS ====================
    
    def format_measurement_results(
        self,
        results: Dict[str, int],
        shots: int,
        show_histogram: bool = True
    ) -> str:
        """
        Format measurement results for terminal display.
        """
        lines = []
        lines.append(f"\n📊 Measurement Results ({shots} shots)")
        lines.append("─" * 45)
        
        sorted_results = sorted(results.items(), key=lambda x: -x[1])
        
        for basis, count in sorted_results:
            pct = count / shots * 100
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  |{basis}⟩  {bar} {count:4d} ({pct:5.1f}%)")
        
        lines.append("─" * 45)
        
        return '\n'.join(lines)


# ==================== GLOBAL INSTANCE ====================

_visualizer: Optional[QuantumVisualizer] = None

def get_visualizer() -> QuantumVisualizer:
    """Get or create global visualizer instance"""
    global _visualizer
    if _visualizer is None:
        _visualizer = QuantumVisualizer()
    return _visualizer
