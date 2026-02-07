#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Predefined Quantum Circuits
Phase 2, Step 3: Quantum Circuit Library

Provides ready-to-use quantum circuits for common quantum computing patterns.
Optimized for Tier 1 hardware (Dell i3 8th Gen, max 16 qubits).

Author: Frankenstein Project
"""

import numpy as np
from numpy import pi, sqrt
from typing import List, Dict, Any, Optional, Callable


class QuantumCircuitLibrary:
    """
    Library of predefined quantum circuits.
    
    Each circuit is a sequence of operations that can be applied
    to the SynthesisEngine.
    """
    
    @staticmethod
    def bell_state(engine, pair: int = 0) -> None:
        """
        Create a Bell state (maximally entangled pair).
        
        |Φ+⟩ = (|00⟩ + |11⟩)/√2
        
        Args:
            engine: SynthesisEngine instance
            pair: Which qubit pair (0 = qubits 0,1; 1 = qubits 2,3; etc.)
        """
        q0 = pair * 2
        q1 = pair * 2 + 1
        engine.h(q0)
        engine.cx(q0, q1)
    
    @staticmethod
    def ghz_state(engine, n_qubits: int = 3) -> None:
        """
        Create a GHZ (Greenberger-Horne-Zeilinger) state.
        
        |GHZ⟩ = (|00...0⟩ + |11...1⟩)/√2
        
        Args:
            engine: SynthesisEngine instance
            n_qubits: Number of qubits (engine must be initialized with at least this many)
        """
        engine.h(0)
        for i in range(1, n_qubits):
            engine.cx(0, i)
    
    @staticmethod
    def w_state(engine, n_qubits: int = 3) -> None:
        """
        Create a W state (equal superposition with one excitation).
        
        |W⟩ = (|100...0⟩ + |010...0⟩ + ... + |00...01⟩)/√n
        
        Args:
            engine: SynthesisEngine instance  
            n_qubits: Number of qubits
        """
        # Start with |100...0⟩
        engine.x(n_qubits - 1)
        
        # Apply controlled rotations to distribute the excitation
        for i in range(n_qubits - 1, 0, -1):
            # Rotation angle to split amplitude equally
            theta = 2 * np.arccos(sqrt(1 / (i + 1)))
            engine.rotate_y(i - 1, theta)
            engine.cx(i - 1, i)
            engine.rotate_y(i - 1, -theta)
    
    @staticmethod
    def qft(engine, n_qubits: int = None) -> None:
        """
        Quantum Fourier Transform.
        
        Implements the QFT circuit which is fundamental for
        Shor's algorithm and phase estimation.
        
        Args:
            engine: SynthesisEngine instance
            n_qubits: Number of qubits (default: all qubits in engine)
        """
        if n_qubits is None:
            n_qubits = engine.get_num_qubits()
        
        for i in range(n_qubits):
            # Hadamard on qubit i
            engine.h(i)
            
            # Controlled rotations
            for j in range(i + 1, n_qubits):
                # Controlled phase rotation by π/2^(j-i)
                angle = pi / (2 ** (j - i))
                engine.apply_gate(engine.phase(angle), i, control=j)
        
        # Swap qubits to reverse order
        for i in range(n_qubits // 2):
            QuantumCircuitLibrary._swap(engine, i, n_qubits - 1 - i)
    
    @staticmethod
    def inverse_qft(engine, n_qubits: int = None) -> None:
        """
        Inverse Quantum Fourier Transform.
        
        Args:
            engine: SynthesisEngine instance
            n_qubits: Number of qubits
        """
        if n_qubits is None:
            n_qubits = engine.get_num_qubits()
        
        # Reverse the QFT operations
        # First swap qubits
        for i in range(n_qubits // 2):
            QuantumCircuitLibrary._swap(engine, i, n_qubits - 1 - i)
        
        # Then inverse rotations (in reverse order)
        for i in range(n_qubits - 1, -1, -1):
            for j in range(n_qubits - 1, i, -1):
                angle = -pi / (2 ** (j - i))
                engine.apply_gate(engine.phase(angle), i, control=j)
            engine.h(i)
    
    @staticmethod
    def _swap(engine, q1: int, q2: int) -> None:
        """SWAP two qubits using 3 CNOTs"""
        engine.cx(q1, q2)
        engine.cx(q2, q1)
        engine.cx(q1, q2)
    
    @staticmethod
    def grover_diffusion(engine, n_qubits: int = None) -> None:
        """
        Grover diffusion operator (inversion about mean).
        
        D = 2|s⟩⟨s| - I where |s⟩ is uniform superposition
        
        Args:
            engine: SynthesisEngine instance
            n_qubits: Number of qubits
        """
        if n_qubits is None:
            n_qubits = engine.get_num_qubits()
        
        # Apply H to all qubits
        for i in range(n_qubits):
            engine.h(i)
        
        # Apply X to all qubits
        for i in range(n_qubits):
            engine.x(i)
        
        # Multi-controlled Z (using decomposition)
        if n_qubits == 2:
            engine.cz(0, 1)
        elif n_qubits >= 3:
            # Apply H to last qubit, multi-controlled X, H again
            engine.h(n_qubits - 1)
            QuantumCircuitLibrary._multi_cx(engine, list(range(n_qubits - 1)), n_qubits - 1)
            engine.h(n_qubits - 1)
        
        # Apply X to all qubits
        for i in range(n_qubits):
            engine.x(i)
        
        # Apply H to all qubits
        for i in range(n_qubits):
            engine.h(i)
    
    @staticmethod
    def _multi_cx(engine, controls: List[int], target: int) -> None:
        """
        Multi-controlled X gate (Toffoli generalization).
        
        Uses decomposition into 2-qubit gates.
        """
        n = len(controls)
        if n == 1:
            engine.cx(controls[0], target)
        elif n == 2:
            # Toffoli decomposition
            engine.h(target)
            engine.cx(controls[1], target)
            engine.apply_gate(engine.rz(-pi/4), target)
            engine.cx(controls[0], target)
            engine.t(target)
            engine.cx(controls[1], target)
            engine.apply_gate(engine.rz(-pi/4), target)
            engine.cx(controls[0], target)
            engine.t(controls[1])
            engine.t(target)
            engine.h(target)
            engine.cx(controls[0], controls[1])
            engine.t(controls[0])
            engine.apply_gate(engine.rz(-pi/4), controls[1])
            engine.cx(controls[0], controls[1])
        else:
            # Recursive decomposition for n > 2
            # This is a simplified approach
            for c in controls[:-1]:
                engine.cx(c, controls[-1])
            engine.cx(controls[-1], target)
            for c in reversed(controls[:-1]):
                engine.cx(c, controls[-1])
    
    @staticmethod
    def quantum_teleportation_setup(engine) -> None:
        """
        Set up quantum teleportation circuit (3 qubits).
        
        Qubit 0: State to teleport (|ψ⟩)
        Qubit 1: Alice's half of Bell pair
        Qubit 2: Bob's half of Bell pair
        
        After setup, measure qubits 0 and 1, then apply corrections to qubit 2.
        """
        # Create Bell pair between qubits 1 and 2
        engine.h(1)
        engine.cx(1, 2)
        
        # Entangle qubit 0 with Alice's half
        engine.cx(0, 1)
        engine.h(0)
    
    @staticmethod  
    def variational_ansatz_ry_cnot(engine, params: List[float], layers: int = 2) -> None:
        """
        Variational ansatz with Ry rotations and CNOT entanglement.
        
        Common structure for VQE and QAOA.
        
        Args:
            engine: SynthesisEngine instance
            params: Rotation parameters (len = n_qubits * layers)
            layers: Number of variational layers
        """
        n = engine.get_num_qubits()
        param_idx = 0
        
        for layer in range(layers):
            # Rotation layer
            for q in range(n):
                if param_idx < len(params):
                    engine.rotate_y(q, params[param_idx])
                    param_idx += 1
            
            # Entanglement layer (linear connectivity)
            for q in range(n - 1):
                engine.cx(q, q + 1)
    
    @staticmethod
    def hadamard_test(engine, controlled_unitary: Callable = None) -> None:
        """
        Hadamard test circuit for estimating ⟨ψ|U|ψ⟩.
        
        Uses ancilla qubit (qubit 0) to estimate expectation value.
        
        Args:
            engine: SynthesisEngine instance (qubit 0 is ancilla)
            controlled_unitary: Function that applies controlled-U to engine
        """
        # H on ancilla
        engine.h(0)
        
        # Apply controlled-U if provided
        if controlled_unitary:
            controlled_unitary(engine)
        
        # H on ancilla
        engine.h(0)
        # Measure ancilla to get Re⟨ψ|U|ψ⟩


# ==================== CIRCUIT REGISTRY ====================

CIRCUIT_REGISTRY = {
    'bell': {
        'name': 'Bell State',
        'description': 'Maximally entangled 2-qubit state |Φ+⟩',
        'qubits': 2,
        'function': QuantumCircuitLibrary.bell_state,
    },
    'ghz': {
        'name': 'GHZ State',
        'description': 'N-qubit Greenberger-Horne-Zeilinger state',
        'qubits': 3,
        'function': QuantumCircuitLibrary.ghz_state,
    },
    'w': {
        'name': 'W State',
        'description': 'N-qubit W state with distributed entanglement',
        'qubits': 3,
        'function': QuantumCircuitLibrary.w_state,
    },
    'qft': {
        'name': 'Quantum Fourier Transform',
        'description': 'QFT circuit for phase estimation',
        'qubits': 'variable',
        'function': QuantumCircuitLibrary.qft,
    },
    'grover': {
        'name': 'Grover Diffusion',
        'description': 'Inversion about mean operator',
        'qubits': 'variable',
        'function': QuantumCircuitLibrary.grover_diffusion,
    },
    'teleport': {
        'name': 'Quantum Teleportation',
        'description': '3-qubit teleportation setup',
        'qubits': 3,
        'function': QuantumCircuitLibrary.quantum_teleportation_setup,
    },
    'vqe': {
        'name': 'VQE Ansatz',
        'description': 'Variational quantum eigensolver ansatz',
        'qubits': 'variable',
        'function': QuantumCircuitLibrary.variational_ansatz_ry_cnot,
    },
}


def get_circuit(name: str) -> Optional[Dict[str, Any]]:
    """Get circuit info by name"""
    return CIRCUIT_REGISTRY.get(name.lower())


def list_circuits() -> List[str]:
    """List all available circuit names"""
    return list(CIRCUIT_REGISTRY.keys())
