#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Numerical Computing Agent
Phase 3.5: Lazy-loaded wrapper for NumPy and SciPy toolsets

Provides advanced numerical methods: linear algebra, eigenvalue decomposition,
matrix exponentials, numerical integration, optimization, and FFT.
"""

from typing import Any, Dict, List, Optional, Union

from ..base import BaseAgent, AgentResult


class NumericalComputingAgent(BaseAgent):
    """
    Agent for advanced numerical computation using NumPy and SciPy.

    Capabilities:
    - Linear algebra (solve, eigenvalues, SVD, matrix exponential)
    - Numerical integration (ODE solvers, quadrature)
    - Optimization (minimize, root-finding)
    - Fast Fourier Transform
    - Matrix analysis (norm, rank, condition number)
    """

    name = "numerical_computing"
    description = "Advanced numerical methods with NumPy/SciPy"
    version = "1.0.0"
    requires_network = False
    requires_filesystem = False
    max_execution_time = 60

    def __init__(self):
        super().__init__()
        self._np = None
        self._scipy = None

    def _ensure_loaded(self):
        """Lazy-load NumPy and SciPy only when a method is actually called."""
        if self._np is None:
            from libs.local_toolsets import load_numpy
            self._np = load_numpy()
            if self._np is None:
                raise RuntimeError(
                    "Failed to load NumPy — insufficient RAM or not installed"
                )

        if self._scipy is None:
            from libs.local_toolsets import load_scipy
            self._scipy = load_scipy()
            if self._scipy is None:
                raise RuntimeError(
                    "Failed to load SciPy — insufficient RAM or not installed"
                )

    def execute(self, operation: str = "", **kwargs) -> AgentResult:
        """
        Dispatch to the requested numerical operation.

        Args:
            operation: One of 'solve_linear', 'eigenvalues', 'matrix_exp',
                       'svd', 'integrate_ode', 'integrate_quad', 'optimize',
                       'fft', 'matrix_analysis'
            **kwargs: Operation-specific parameters
        """
        if not operation:
            return AgentResult(
                success=False,
                error="No operation specified. Available: solve_linear, eigenvalues, "
                      "matrix_exp, svd, integrate_ode, integrate_quad, optimize, "
                      "fft, matrix_analysis",
            )

        dispatch = {
            "solve_linear": self._run_solve_linear,
            "eigenvalues": self._run_eigenvalues,
            "matrix_exp": self._run_matrix_exp,
            "svd": self._run_svd,
            "integrate_ode": self._run_integrate_ode,
            "integrate_quad": self._run_integrate_quad,
            "optimize": self._run_optimize,
            "fft": self._run_fft,
            "matrix_analysis": self._run_matrix_analysis,
        }

        handler = dispatch.get(operation)
        if handler is None:
            return AgentResult(
                success=False,
                error=f"Unknown operation: {operation!r}. "
                      f"Available: {', '.join(sorted(dispatch))}",
            )

        try:
            self._ensure_loaded()
            return handler(**kwargs)
        except RuntimeError as exc:
            return AgentResult(success=False, error=str(exc))
        except Exception as exc:
            return AgentResult(success=False, error=f"{type(exc).__name__}: {exc}")

    # ── Linear system solving ────────────────────────────────────────────

    def _run_solve_linear(
        self,
        A=None,
        b=None,
        **kwargs,
    ) -> AgentResult:
        """
        Solve Ax = b for x.

        Args:
            A: Coefficient matrix (list of lists or ndarray)
            b: Right-hand side vector (list or ndarray)
        """
        np = self._np
        if A is None or b is None:
            return AgentResult(
                success=False, error="solve_linear requires A and b"
            )

        A = np.asarray(A, dtype=float)
        b = np.asarray(b, dtype=float)

        x = np.linalg.solve(A, b)
        residual = np.linalg.norm(A @ x - b)

        return AgentResult(
            success=True,
            data={
                "solution": x.tolist(),
                "residual": float(residual),
                "matrix_shape": list(A.shape),
            },
        )

    # ── Eigenvalue decomposition ─────────────────────────────────────────

    def _run_eigenvalues(
        self,
        matrix=None,
        hermitian: bool = False,
        **kwargs,
    ) -> AgentResult:
        """
        Compute eigenvalues and eigenvectors of a matrix.

        Args:
            matrix: Square matrix (list of lists or ndarray)
            hermitian: If True, use optimized solver for Hermitian matrices
        """
        np = self._np
        if matrix is None:
            return AgentResult(
                success=False, error="eigenvalues requires a matrix"
            )

        M = np.asarray(matrix, dtype=complex)

        if hermitian:
            eigenvalues, eigenvectors = np.linalg.eigh(M)
        else:
            eigenvalues, eigenvectors = np.linalg.eig(M)

        return AgentResult(
            success=True,
            data={
                "eigenvalues": eigenvalues.tolist(),
                "eigenvectors": eigenvectors.tolist(),
                "matrix_shape": list(M.shape),
                "hermitian": hermitian,
            },
        )

    # ── Matrix exponential ───────────────────────────────────────────────

    def _run_matrix_exp(
        self,
        matrix=None,
        **kwargs,
    ) -> AgentResult:
        """
        Compute the matrix exponential exp(M) using SciPy.

        Essential for quantum time evolution: U(t) = exp(-iHt/hbar).

        Args:
            matrix: Square matrix (list of lists or ndarray)
        """
        np = self._np
        sp = self._scipy
        from scipy import linalg as sp_linalg

        if matrix is None:
            return AgentResult(
                success=False, error="matrix_exp requires a matrix"
            )

        M = np.asarray(matrix, dtype=complex)
        result = sp_linalg.expm(M)

        return AgentResult(
            success=True,
            data={
                "matrix_exp": result.tolist(),
                "input_shape": list(M.shape),
            },
        )

    # ── Singular Value Decomposition ─────────────────────────────────────

    def _run_svd(
        self,
        matrix=None,
        full_matrices: bool = False,
        **kwargs,
    ) -> AgentResult:
        """
        Compute the SVD: M = U * diag(S) * Vh.

        Args:
            matrix: Input matrix (list of lists or ndarray)
            full_matrices: If False, return economy-size decomposition
        """
        np = self._np
        if matrix is None:
            return AgentResult(success=False, error="svd requires a matrix")

        M = np.asarray(matrix, dtype=complex)
        U, S, Vh = np.linalg.svd(M, full_matrices=full_matrices)

        return AgentResult(
            success=True,
            data={
                "U": U.tolist(),
                "singular_values": S.tolist(),
                "Vh": Vh.tolist(),
                "rank": int(np.sum(S > 1e-10)),
                "condition_number": float(S[0] / S[-1]) if S[-1] > 0 else float("inf"),
                "input_shape": list(M.shape),
            },
        )

    # ── ODE integration ──────────────────────────────────────────────────

    def _run_integrate_ode(
        self,
        func=None,
        y0=None,
        t_span=None,
        t_eval=None,
        method: str = "RK45",
        **kwargs,
    ) -> AgentResult:
        """
        Solve an initial value problem (ODE) using scipy.integrate.solve_ivp.

        Args:
            func: Right-hand side function f(t, y) -> dy/dt
            y0: Initial condition (list or ndarray)
            t_span: (t0, tf) integration interval
            t_eval: Times at which to store the solution
            method: Integration method ('RK45', 'RK23', 'DOP853', 'Radau', 'BDF')
        """
        np = self._np
        from scipy.integrate import solve_ivp

        if func is None or y0 is None or t_span is None:
            return AgentResult(
                success=False,
                error="integrate_ode requires func, y0, and t_span",
            )

        y0 = np.asarray(y0, dtype=float)
        result = solve_ivp(func, t_span, y0, method=method, t_eval=t_eval, dense_output=True)

        return AgentResult(
            success=True,
            data={
                "t": result.t.tolist(),
                "y": result.y.tolist(),
                "success": result.success,
                "message": result.message,
                "method": method,
            },
        )

    # ── Numerical quadrature ─────────────────────────────────────────────

    def _run_integrate_quad(
        self,
        func=None,
        a: float = 0.0,
        b: float = 1.0,
        **kwargs,
    ) -> AgentResult:
        """
        Compute a definite integral using adaptive quadrature.

        Args:
            func: Integrand function f(x) -> float
            a: Lower integration limit
            b: Upper integration limit
        """
        from scipy.integrate import quad

        if func is None:
            return AgentResult(
                success=False, error="integrate_quad requires a func"
            )

        value, error = quad(func, a, b)

        return AgentResult(
            success=True,
            data={
                "value": float(value),
                "error_estimate": float(error),
                "interval": [a, b],
            },
        )

    # ── Optimization ─────────────────────────────────────────────────────

    def _run_optimize(
        self,
        func=None,
        x0=None,
        method: str = "Nelder-Mead",
        **kwargs,
    ) -> AgentResult:
        """
        Minimize a scalar function.

        Args:
            func: Objective function f(x) -> float
            x0: Initial guess (list or ndarray)
            method: Optimization method ('Nelder-Mead', 'BFGS', 'L-BFGS-B', 'Powell', etc.)
        """
        np = self._np
        from scipy.optimize import minimize

        if func is None or x0 is None:
            return AgentResult(
                success=False, error="optimize requires func and x0"
            )

        x0 = np.asarray(x0, dtype=float)
        result = minimize(func, x0, method=method)

        return AgentResult(
            success=True,
            data={
                "x_optimal": result.x.tolist(),
                "fun_optimal": float(result.fun),
                "success": result.success,
                "message": result.message,
                "iterations": result.nit,
                "method": method,
            },
        )

    # ── Fast Fourier Transform ───────────────────────────────────────────

    def _run_fft(
        self,
        signal=None,
        inverse: bool = False,
        **kwargs,
    ) -> AgentResult:
        """
        Compute the (inverse) FFT of a signal.

        Args:
            signal: Input signal (list or ndarray)
            inverse: If True, compute inverse FFT
        """
        np = self._np
        if signal is None:
            return AgentResult(success=False, error="fft requires a signal")

        signal = np.asarray(signal, dtype=complex)

        if inverse:
            result = np.fft.ifft(signal)
        else:
            result = np.fft.fft(signal)

        freqs = np.fft.fftfreq(len(signal))

        return AgentResult(
            success=True,
            data={
                "transform": result.tolist(),
                "frequencies": freqs.tolist(),
                "magnitude": np.abs(result).tolist(),
                "phase": np.angle(result).tolist(),
                "inverse": inverse,
                "length": len(signal),
            },
        )

    # ── Matrix analysis ──────────────────────────────────────────────────

    def _run_matrix_analysis(
        self,
        matrix=None,
        **kwargs,
    ) -> AgentResult:
        """
        Comprehensive analysis of a matrix: norm, rank, determinant,
        condition number, trace.

        Args:
            matrix: Input matrix (list of lists or ndarray)
        """
        np = self._np
        if matrix is None:
            return AgentResult(
                success=False, error="matrix_analysis requires a matrix"
            )

        M = np.asarray(matrix, dtype=complex)

        analysis = {
            "shape": list(M.shape),
            "rank": int(np.linalg.matrix_rank(M)),
            "trace": complex(np.trace(M)),
            "frobenius_norm": float(np.linalg.norm(M, "fro")),
            "spectral_norm": float(np.linalg.norm(M, 2)),
        }

        # Determinant and condition number only for square matrices
        if M.shape[0] == M.shape[1]:
            analysis["determinant"] = complex(np.linalg.det(M))
            analysis["condition_number"] = float(np.linalg.cond(M))
            analysis["is_hermitian"] = bool(np.allclose(M, M.conj().T))
            analysis["is_unitary"] = bool(
                np.allclose(M @ M.conj().T, np.eye(M.shape[0]))
            )

        return AgentResult(
            success=True,
            data=analysis,
        )
