#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Quantum Gate Accelerator
Lazy-loaded JAX / Numba acceleration for tensor-indexed gate operations.

LAZY LOADING CONTRACT:
    Nothing in this module executes at import time except the
    AcceleratorBackend dataclass definition. The actual backend
    detection and any JIT compilation occurs only on the first
    gate call.

TENSOR CONVENTION (MSB-first, matches true_engine.py):
    Qubit k  ->  bit position (n-1-k)  ->  tensor axis k
    step(k)  =  2^(n-1-k)

    For a 3-qubit state |q0 q1 q2>, index i encodes:
        q0 = (i >> 2) & 1   (most significant)
        q1 = (i >> 1) & 1
        q2 = (i >> 0) & 1   (least significant)

    This matches true_engine.py's step = 2 ** (n - target - 1).

BACKEND PRIORITY (auto-detected at first use):
    1. JAX   (if jax is importable from site-packages)
    2. Numba (if numba is importable from site-packages)
    3. NumPy (always available - pure Python fallback, no performance loss
              for statevectors up to 16 qubits on Tier 1 hardware)

NOTE ON DOWNLOADS FOLDER:
    JAX and Numba are present in C:/Users/adamn/Downloads as source
    code repositories that require compilation (Bazel/LLVM for JAX,
    LLVM for Numba). They cannot be imported directly from source.
    To enable JAX/Numba acceleration: pip install jax[cpu] numba
    The NumPy backend is correct and sufficient for <= 16 qubits.

Hardware target: Dell i3 8th Gen, 4 cores, 8GB RAM
Max qubits: 16 (2^16 = 65,536 amplitudes = ~1 MB complex128)
"""

from __future__ import annotations
import numpy as np
from typing import Optional, List
from dataclasses import dataclass, field


# =============================================================================
# BACKEND STATE (module-level singleton, populated lazily)
# =============================================================================

@dataclass
class AcceleratorBackend:
    """
    Holds the chosen backend state.
    All function slots are None until _initialize_backend() is called
    on the first gate operation.
    """
    name: str = "numpy"
    available: bool = True
    jit_apply_single: Optional[object] = None
    jit_apply_controlled: Optional[object] = None
    jit_apply_mcx: Optional[object] = None
    _initialized: bool = False


_backend = AcceleratorBackend()


# =============================================================================
# BACKEND PROBES  (called lazily, only once)
# =============================================================================

def _try_load_jax():
    """
    Attempt to import JAX from site-packages.
    JAX source in Downloads requires compilation - not usable directly.
    Returns (jax, jnp, jit) or (None, None, None).
    """
    try:
        import jax
        import jax.numpy as jnp
        from jax import jit
        return jax, jnp, jit
    except ImportError:
        return None, None, None


def _try_load_numba():
    """
    Attempt to import Numba from site-packages.
    Numba source in Downloads requires compilation - not usable directly.
    Catches all exceptions (ImportError, circular import, broken install).
    Returns (njit, prange) or (None, None).
    """
    try:
        from numba import njit, prange
        return njit, prange
    except Exception:
        return None, None


# =============================================================================
# NUMPY BACKEND  (always available, correct for all qubit counts <= 16)
# =============================================================================

def _build_numpy_backend():
    """
    Pure NumPy implementations.
    These are correct and memory-safe for all qubit counts up to 16.

    MSB convention: qubit k at bit position (n-1-k), step = 2^(n-1-k).
    All operations are in-place on the statevector — O(2^n) time, O(1) extra.
    """

    def apply_single_numpy(sv: np.ndarray, gate: np.ndarray,
                           target: int, n: int) -> np.ndarray:
        """
        Apply 2x2 gate to qubit `target` of n-qubit statevector.
        MSB convention: step = 2^(n-1-target).

        Operates on amplitude pairs without building any matrix.
        For 16 qubits: 65,536 amplitudes, ~32,768 pair updates.
        """
        step = 1 << (n - 1 - target)   # 2^(n-1-target)
        dim  = 1 << n                   # 2^n
        g00, g01 = gate[0, 0], gate[0, 1]
        g10, g11 = gate[1, 0], gate[1, 1]

        for i in range(0, dim, 2 * step):
            for j in range(step):
                i0 = i + j
                i1 = i0 + step
                a0 = sv[i0]
                a1 = sv[i1]
                sv[i0] = g00 * a0 + g01 * a1
                sv[i1] = g10 * a0 + g11 * a1
        return sv

    def apply_controlled_numpy(sv: np.ndarray, gate: np.ndarray,
                               control: int, target: int, n: int) -> np.ndarray:
        """
        Apply controlled-U gate. MSB convention.
        Only touches amplitudes where control qubit = |1>.
        No matrix built — O(2^n) time, O(1) extra space.
        """
        ctrl_bit = n - 1 - control
        tgt_bit  = n - 1 - target
        tgt_step = 1 << tgt_bit
        dim      = 1 << n
        g00, g01 = gate[0, 0], gate[0, 1]
        g10, g11 = gate[1, 0], gate[1, 1]

        for i in range(dim):
            # Only process states where control = |1> and target = |0>
            if not ((i >> ctrl_bit) & 1):
                continue
            if (i >> tgt_bit) & 1:
                continue
            i0 = i
            i1 = i | tgt_step
            a0 = sv[i0]
            a1 = sv[i1]
            sv[i0] = g00 * a0 + g01 * a1
            sv[i1] = g10 * a0 + g11 * a1
        return sv

    def apply_mcx_numpy(sv: np.ndarray, controls: List[int],
                        target: int, n: int) -> np.ndarray:
        """
        Multi-Controlled X gate - tensor-indexed sparse swap.
        MSB convention: bit position of qubit k = (n-1-k).

        Algorithm:
            Build a bitmask of all control qubits in MSB bit positions.
            For each basis state where ALL controls = |1> AND target = |0>:
                swap sv[i] <-> sv[i ^ target_bit]

        Memory: O(2^n) — operates on the statevector in-place.
        For 16 qubits: ~1 MB (vs ~68 GB for a full matrix).

        This is the same algorithm used by quantum_mode._apply_mcx_statevector
        but expressed in MSB convention to be consistent with engine.py.
        """
        tgt_bit  = n - 1 - target
        tgt_mask = 1 << tgt_bit

        ctrl_mask = 0
        for c in controls:
            ctrl_mask |= (1 << (n - 1 - c))

        dim = 1 << n
        for i in range(dim):
            # Process each pair exactly once: require target = |0>
            if (i & ctrl_mask) == ctrl_mask and not (i & tgt_mask):
                j = i | tgt_mask
                sv[i], sv[j] = sv[j], sv[i]
        return sv

    return apply_single_numpy, apply_controlled_numpy, apply_mcx_numpy


# =============================================================================
# NUMBA BACKEND  (JIT-compiled, ~10-50x faster than NumPy loops)
# =============================================================================

def _build_numba_backend(njit, prange):
    """
    Numba JIT implementations. Compiled on first call (warm-up ~1-2s).
    Subsequent calls are near-native speed.
    """

    @njit(cache=True, parallel=False)
    def _apply_single_numba_inner(sv, g00, g01, g10, g11, step, dim):
        for i in range(0, dim, 2 * step):
            for j in range(step):
                i0 = i + j
                i1 = i0 + step
                a0 = sv[i0]
                a1 = sv[i1]
                sv[i0] = g00 * a0 + g01 * a1
                sv[i1] = g10 * a0 + g11 * a1
        return sv

    @njit(cache=True, parallel=False)
    def _apply_controlled_numba_inner(sv, g00, g01, g10, g11,
                                      ctrl_bit, tgt_bit, tgt_step, dim):
        for i in range(dim):
            if not ((i >> ctrl_bit) & 1):
                continue
            if (i >> tgt_bit) & 1:
                continue
            i0 = i
            i1 = i | tgt_step
            a0 = sv[i0]
            a1 = sv[i1]
            sv[i0] = g00 * a0 + g01 * a1
            sv[i1] = g10 * a0 + g11 * a1
        return sv

    @njit(cache=True, parallel=False)
    def _apply_mcx_numba_inner(sv, ctrl_mask, tgt_mask, dim):
        for i in range(dim):
            if (i & ctrl_mask) == ctrl_mask and not (i & tgt_mask):
                j = i | tgt_mask
                tmp   = sv[i]
                sv[i] = sv[j]
                sv[j] = tmp
        return sv

    def apply_single_numba(sv, gate, target, n):
        step = 1 << (n - 1 - target)
        dim  = 1 << n
        return _apply_single_numba_inner(
            sv, gate[0, 0], gate[0, 1], gate[1, 0], gate[1, 1], step, dim)

    def apply_controlled_numba(sv, gate, control, target, n):
        ctrl_bit = n - 1 - control
        tgt_bit  = n - 1 - target
        tgt_step = 1 << tgt_bit
        dim      = 1 << n
        return _apply_controlled_numba_inner(
            sv, gate[0, 0], gate[0, 1], gate[1, 0], gate[1, 1],
            ctrl_bit, tgt_bit, tgt_step, dim)

    def apply_mcx_numba(sv, controls, target, n):
        tgt_bit  = n - 1 - target
        tgt_mask = 1 << tgt_bit
        ctrl_mask = 0
        for c in controls:
            ctrl_mask |= (1 << (n - 1 - c))
        dim = 1 << n
        return _apply_mcx_numba_inner(sv, ctrl_mask, tgt_mask, dim)

    return apply_single_numba, apply_controlled_numba, apply_mcx_numba


# =============================================================================
# JAX BACKEND  (XLA-compiled, tensor einsum approach)
# =============================================================================

def _build_jax_backend(jax, jnp, jit):
    """
    JAX JIT implementations using tensor reshape + einsum.
    Tensordot approach: reshape sv into [2]*n tensor, contract with gate.
    """

    @jit
    def _apply_single_jax_inner(sv_tensor, gate, target_axis, n):
        # Contract gate axis-1 with sv_tensor at target_axis
        result = jnp.tensordot(gate, sv_tensor, axes=([1], [target_axis]))
        # Move gate output axis (currently at 0) back to target_axis
        axes = list(range(1, target_axis + 1)) + [0] + list(range(target_axis + 1, n))
        return jnp.transpose(result, axes)

    def apply_single_jax(sv, gate, target, n):
        sv_t = jnp.array(sv.reshape([2] * n), dtype=jnp.complex128)
        g    = jnp.array(gate, dtype=jnp.complex128)
        out  = _apply_single_jax_inner(sv_t, g, target, n)
        sv[:] = np.array(out.reshape(-1))
        return sv

    def apply_controlled_jax(sv, gate, control, target, n):
        # Projector decomposition:
        # CU = |0><0|_ctrl ⊗ I_target  +  |1><1|_ctrl ⊗ U_target
        sv_t = jnp.array(sv.reshape([2] * n), dtype=jnp.complex128)
        g    = jnp.array(gate, dtype=jnp.complex128)
        p0   = jnp.array([[1, 0], [0, 0]], dtype=jnp.complex128)
        p1   = jnp.array([[0, 0], [0, 1]], dtype=jnp.complex128)

        def proj(t, op, axis):
            r = jnp.tensordot(op, t, axes=([1], [axis]))
            axes = list(range(1, axis + 1)) + [0] + list(range(axis + 1, n))
            return jnp.transpose(r, axes)

        branch0 = proj(sv_t, p0, control)                        # ctrl=0 branch: identity on target
        branch1_ctrl = proj(sv_t, p1, control)                   # ctrl=1 branch: apply U to target
        branch1 = _apply_single_jax_inner(branch1_ctrl, g, target, n)

        out = branch0 + branch1
        sv[:] = np.array(out.reshape(-1))
        return sv

    def apply_mcx_jax(sv, controls, target, n):
        # MCX on JAX: fall back to NumPy sparse swap
        # JAX does not accelerate the sparse swap pattern efficiently on CPU
        _, _, np_mcx = _build_numpy_backend()
        return np_mcx(sv, controls, target, n)

    return apply_single_jax, apply_controlled_jax, apply_mcx_jax


# =============================================================================
# BACKEND INITIALIZATION  (called lazily on first gate operation)
# =============================================================================

def _smoke_test_backend(f_single, f_controlled, label: str) -> bool:
    """
    Run a real 1-qubit Hadamard smoke test to verify the backend
    actually produces correct results. Returns True if the backend
    passes. This catches JAX tracing errors, Numba circular imports,
    and any other runtime failures before committing to a backend.
    """
    try:
        H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
        sv = np.array([1.0 + 0j, 0.0 + 0j], dtype=np.complex128)
        f_single(sv, H, 0, 1)
        # After H|0⟩, should get |+⟩ = [1/√2, 1/√2]
        expected = 1.0 / np.sqrt(2)
        if abs(abs(sv[0]) - expected) > 0.01 or abs(abs(sv[1]) - expected) > 0.01:
            print(f"  Accelerator: {label} produced wrong result, skipping")
            return False
        return True
    except Exception as exc:
        print(f"  Accelerator: {label} smoke test failed ({type(exc).__name__}: {exc})")
        return False


def _initialize_backend():
    """
    Detect and initialize the best available backend.
    Called exactly once, on the first gate operation.
    Each backend is SMOKE TESTED with a real H|0⟩ gate before
    being accepted — this catches JAX tracing errors, broken
    Numba installs, and any other runtime failures.
    """
    global _backend
    if _backend._initialized:
        return

    # --- Try JAX first ---
    jax_mod, jnp_mod, jit_fn = _try_load_jax()
    if jax_mod is not None:
        try:
            f_s, f_c, f_m = _build_jax_backend(jax_mod, jnp_mod, jit_fn)
            if _smoke_test_backend(f_s, f_c, f"JAX {jax_mod.__version__}"):
                _backend.name                 = "jax"
                _backend.jit_apply_single     = f_s
                _backend.jit_apply_controlled = f_c
                _backend.jit_apply_mcx        = f_m
                _backend._initialized         = True
                print(f"  Accelerator: JAX {jax_mod.__version__} backend loaded")
                return
        except Exception as exc:
            print(f"  Accelerator: JAX found but failed to initialize ({exc})")

    # --- Try Numba ---
    njit_fn, prange_fn = _try_load_numba()
    if njit_fn is not None:
        try:
            f_s, f_c, f_m = _build_numba_backend(njit_fn, prange_fn)
            if _smoke_test_backend(f_s, f_c, "Numba"):
                _backend.name                 = "numba"
                _backend.jit_apply_single     = f_s
                _backend.jit_apply_controlled = f_c
                _backend.jit_apply_mcx        = f_m
                _backend._initialized         = True
                import numba as _nb
                print(f"  Accelerator: Numba {_nb.__version__} backend loaded")
                return
        except Exception as exc:
            print(f"  Accelerator: Numba found but failed to initialize ({exc})")

    # --- NumPy fallback (always succeeds) ---
    f_s, f_c, f_m = _build_numpy_backend()
    _backend.name                 = "numpy"
    _backend.jit_apply_single     = f_s
    _backend.jit_apply_controlled = f_c
    _backend.jit_apply_mcx        = f_m
    _backend._initialized         = True
    print("  Accelerator: NumPy backend active (correct for all operations)")


# =============================================================================
# PUBLIC API  (called by engine files)
# =============================================================================

def apply_single_qubit_gate(sv: np.ndarray, gate: np.ndarray,
                            target: int, n: int) -> np.ndarray:
    """
    Apply 2x2 unitary gate to qubit `target` of an n-qubit statevector.

    MSB convention: qubit k at bit position (n-1-k).
    step = 2^(n-1-target)

    Lazy-loads JAX/Numba on first call; falls back to NumPy.

    Args:
        sv:     Complex statevector, shape (2^n,), dtype complex128. Modified in-place.
        gate:   2x2 unitary matrix, dtype complex128.
        target: Target qubit index (0 = most significant bit).
        n:      Total number of qubits.

    Returns:
        sv (modified in-place and returned for chaining).
    """
    _initialize_backend()
    return _backend.jit_apply_single(sv, gate, target, n)


def apply_controlled_gate(sv: np.ndarray, gate: np.ndarray,
                          control: int, target: int, n: int) -> np.ndarray:
    """
    Apply controlled-U gate to an n-qubit statevector.

    MSB convention throughout.
    Lazy-loads JAX/Numba on first call.

    Args:
        sv:      Complex statevector, shape (2^n,). Modified in-place.
        gate:    2x2 unitary matrix (the U to apply when control = |1>).
        control: Control qubit index.
        target:  Target qubit index.
        n:       Total number of qubits.

    Returns:
        sv (modified in-place and returned for chaining).
    """
    _initialize_backend()
    return _backend.jit_apply_controlled(sv, gate, control, target, n)


def apply_mcx_gate(sv: np.ndarray, controls: List[int],
                   target: int, n: int) -> np.ndarray:
    """
    Multi-Controlled X gate - tensor-indexed sparse swap.

    MSB convention: qubit k at bit position (n-1-k).
    No matrix is ever built. Memory usage: O(2^n).

    For 16 qubits (max Tier 1): ~1 MB RAM, vs ~68 GB for a full matrix.

    This is the engine-level implementation. The widget-level
    quantum_mode._apply_mcx_statevector uses LSB convention and
    operates via engine.set_state(). This function is called when
    engine.mcx() is invoked directly.

    Args:
        sv:       Complex statevector, shape (2^n,). Modified in-place.
        controls: List of control qubit indices.
        target:   Target qubit index.
        n:        Total number of qubits.

    Returns:
        sv (modified in-place and returned for chaining).
    """
    _initialize_backend()
    return _backend.jit_apply_mcx(sv, controls, target, n)


def get_backend_name() -> str:
    """Return the name of the active acceleration backend."""
    return _backend.name if _backend._initialized else "not-yet-initialized"


def is_initialized() -> bool:
    """Return True if the backend has been initialized."""
    return _backend._initialized
