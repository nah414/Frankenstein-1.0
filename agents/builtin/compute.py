"""
FRANKENSTEIN Built-in Agent - Compute
Performs mathematical calculations safely
"""

import math
import operator
from typing import Any, Dict
from ..base import BaseAgent, AgentResult


class ComputeAgent(BaseAgent):
    """
    Agent for performing mathematical calculations.
    Safely evaluates mathematical expressions.
    """

    name = "compute"
    description = "Performs mathematical calculations"
    version = "1.0.0"
    requires_network = False
    requires_filesystem = False
    max_execution_time = 5

    # Safe operations
    SAFE_OPS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '//': operator.floordiv,
        '%': operator.mod,
        '**': operator.pow,
    }

    # Safe functions
    SAFE_FUNCS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'pi': math.pi,
        'e': math.e,
    }

    def execute(self, expression: str = "", **kwargs) -> AgentResult:
        """
        Execute a mathematical expression.

        Args:
            expression: Math expression to evaluate (e.g., "2 + 2")
        """
        if not expression:
            return AgentResult(
                success=False,
                error="No expression provided"
            )

        try:
            # Sanitize - only allow safe characters
            allowed = set("0123456789+-*/.() ,")
            if not all(c in allowed or c.isalpha() for c in expression):
                return AgentResult(
                    success=False,
                    error="Invalid characters in expression",
                    security_warnings=["Potentially unsafe expression rejected"]
                )

            # Build safe namespace
            namespace = {"__builtins__": {}}
            namespace.update(self.SAFE_FUNCS)

            # Evaluate
            result = eval(expression, namespace)

            return AgentResult(
                success=True,
                data={"expression": expression, "result": result}
            )

        except ZeroDivisionError:
            return AgentResult(success=False, error="Division by zero")
        except Exception as e:
            return AgentResult(success=False, error=str(e))
