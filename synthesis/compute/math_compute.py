"""
FRANKENSTEIN 1.0 - Math Compute Module
Phase 2 Step 3: Real Mathematical Computations

Provides actual mathematical calculations:
- Symbolic mathematics (differentiation, integration)
- Numerical analysis
- Linear algebra
- Optimization
"""

import numpy as np
from typing import Dict, Any, Optional, List, Callable, Union
import logging

logger = logging.getLogger(__name__)


class MathCompute:
    """Real mathematical computation engine."""
    
    def __init__(self):
        self._sympy_available = self._check_sympy()
        self._scipy_available = self._check_scipy()
    
    def _check_sympy(self) -> bool:
        try:
            import sympy
            return True
        except ImportError:
            return False
    
    def _check_scipy(self) -> bool:
        try:
            import scipy
            return True
        except ImportError:
            return False
    
    def evaluate(self, expression: str, variables: Dict[str, Any] = None) -> Any:
        """Evaluate mathematical expression"""
        variables = variables or {}
        safe_dict = {
            "np": np, "sin": np.sin, "cos": np.cos, "tan": np.tan,
            "exp": np.exp, "log": np.log, "sqrt": np.sqrt,
            "pi": np.pi, "e": np.e, "abs": np.abs,
            **variables
        }
        return eval(expression, {"__builtins__": {}}, safe_dict)
    
    def differentiate(self, expression: str, variable: str = "x", order: int = 1) -> str:
        """Symbolic differentiation"""
        if not self._sympy_available:
            raise ImportError("SymPy required for symbolic differentiation")
        
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr
        
        x = sp.Symbol(variable)
        expr = parse_expr(expression, local_dict={variable: x})
        for _ in range(order):
            expr = sp.diff(expr, x)
        return str(sp.simplify(expr))

    def integrate(self, expression: str, variable: str = "x", 
                  limits: Optional[tuple] = None) -> Union[str, float]:
        """Symbolic or definite integration"""
        if not self._sympy_available:
            raise ImportError("SymPy required")
        
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr
        
        x = sp.Symbol(variable)
        expr = parse_expr(expression, local_dict={variable: x})
        
        if limits:
            result = sp.integrate(expr, (x, limits[0], limits[1]))
            try:
                return float(result.evalf())
            except (TypeError, ValueError):
                return str(result)
        return str(sp.integrate(expr, x))
    
    def solve(self, equation: str, variable: str = "x") -> List[str]:
        """Solve equation symbolically"""
        if not self._sympy_available:
            raise ImportError("SymPy required")
        
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr
        
        x = sp.Symbol(variable)
        
        if "=" in equation and "==" not in equation:
            left, right = equation.split("=", 1)
            expr = parse_expr(left, local_dict={variable: x}) - parse_expr(right, local_dict={variable: x})
        else:
            expr = parse_expr(equation, local_dict={variable: x})
        
        solutions = sp.solve(expr, x)
        return [str(s) for s in solutions]
    
    def taylor_series(self, expression: str, variable: str = "x", 
                      point: float = 0, order: int = 5) -> str:
        """Compute Taylor series expansion"""
        if not self._sympy_available:
            raise ImportError("SymPy required")
        
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr
        
        x = sp.Symbol(variable)
        expr = parse_expr(expression, local_dict={variable: x})
        series = sp.series(expr, x, point, order + 1).removeO()
        return str(series)
    
    def limit(self, expression: str, variable: str = "x", point: Any = 0) -> str:
        """Compute limit"""
        if not self._sympy_available:
            raise ImportError("SymPy required")
        
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr
        
        x = sp.Symbol(variable)
        expr = parse_expr(expression, local_dict={variable: x})
        
        if point == "inf":
            point = sp.oo
        elif point == "-inf":
            point = -sp.oo
        
        result = sp.limit(expr, x, point)
        return str(result)

    def matrix_inverse(self, matrix: np.ndarray) -> np.ndarray:
        """Matrix inverse"""
        return np.linalg.inv(matrix)
    
    def matrix_eigenvalues(self, matrix: np.ndarray) -> tuple:
        """Eigenvalues and eigenvectors"""
        return np.linalg.eig(matrix)
    
    def svd(self, matrix: np.ndarray) -> tuple:
        """Singular Value Decomposition"""
        return np.linalg.svd(matrix)
    
    def optimize_minimize(self, func: Callable, x0: np.ndarray, 
                          method: str = "BFGS") -> Dict[str, Any]:
        """Numerical optimization"""
        if not self._scipy_available:
            raise ImportError("SciPy required")
        
        from scipy.optimize import minimize
        result = minimize(func, x0, method=method)
        return {
            "x": result.x.tolist(),
            "fun": float(result.fun),
            "success": result.success,
            "message": result.message
        }
    
    def root_find(self, func: Callable, x0: float) -> Dict[str, Any]:
        """Find root of function"""
        if not self._scipy_available:
            raise ImportError("SciPy required")
        
        from scipy.optimize import root_scalar
        result = root_scalar(func, x0=x0, method='newton')
        return {
            "root": float(result.root),
            "converged": result.converged,
            "iterations": result.iterations
        }
    
    def fft(self, data: np.ndarray) -> np.ndarray:
        """Fast Fourier Transform"""
        return np.fft.fft(data)
    
    def ifft(self, data: np.ndarray) -> np.ndarray:
        """Inverse FFT"""
        return np.fft.ifft(data)
    
    def polynomial_fit(self, x: np.ndarray, y: np.ndarray, degree: int) -> np.ndarray:
        """Polynomial curve fitting"""
        return np.polyfit(x, y, degree)
    
    def interpolate(self, x: np.ndarray, y: np.ndarray, x_new: np.ndarray) -> np.ndarray:
        """Interpolation"""
        if not self._scipy_available:
            # Fallback to numpy interp
            return np.interp(x_new, x, y)
        
        from scipy.interpolate import interp1d
        f = interp1d(x, y, kind='cubic', fill_value='extrapolate')
        return f(x_new)


# Singleton
_math_compute: Optional['MathCompute'] = None

def get_math_compute() -> MathCompute:
    global _math_compute
    if _math_compute is None:
        _math_compute = MathCompute()
    return _math_compute
