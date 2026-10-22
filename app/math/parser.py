"""Safe mathematical expression parser and AST sanitizer.

Strictly disallows arbitrary eval/exec, imports, attribute access, and system calls.
Enforces resource limits to protect against computational denial of service.
"""

import ast
import math
from decimal import Decimal, getcontext
from fractions import Fraction
from typing import Any

from app.core.exceptions import ValidationError

# Set precision for decimal arithmetic
getcontext().prec = 30

ALLOWED_MATH_FUNCS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.pow(x, 1 / 3) if x >= 0 else -math.pow(-x, 1 / 3),
    "log": math.log,
    "ln": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "gcd": math.gcd,
    "lcm": math.lcm,
    "factorial": math.factorial,
}

ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": float("inf"),
}

ALLOWED_OPERATORS = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)

MAX_EXPONENT_VALUE = 10000
MAX_EXPRESSION_LENGTH = 2048


class SafeMathParser:
    """AST-based mathematical expression sanitizer and evaluator."""

    @classmethod
    def validate_ast(cls, expr: str) -> ast.AST:
        """Parse and strictly validate an expression against safe AST rules."""
        if not expr or len(expr) > MAX_EXPRESSION_LENGTH:
            raise ValidationError(f"Expression exceeds maximum allowed length ({MAX_EXPRESSION_LENGTH} characters).")

        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as e:
            raise ValidationError(f"Invalid mathematical syntax: {e}")

        for node in ast.walk(tree):
            # Allowed node types
            if isinstance(
                node,
                (
                    ast.Expression,
                    ast.BinOp,
                    ast.UnaryOp,
                    ast.Call,
                    ast.Constant,
                    ast.Name,
                    ast.Load,
                    ast.List,
                    ast.Tuple,
                    ast.operator,
                    ast.unaryop,
                ),
            ):
                pass
            else:
                raise ValidationError(f"Disallowed syntax element '{type(node).__name__}' in mathematical expression.")

            # Validate operators
            if isinstance(node, ast.BinOp) and not isinstance(node.op, ALLOWED_OPERATORS):
                raise ValidationError(f"Disallowed binary operator '{type(node.op).__name__}'.")
            if isinstance(node, ast.UnaryOp) and not isinstance(node.op, (ast.UAdd, ast.USub)):
                raise ValidationError(f"Disallowed unary operator '{type(node.op).__name__}'.")

            # Check for excessive power operations to prevent CPU denial of service
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
                    if abs(node.right.value) > MAX_EXPONENT_VALUE:
                        raise ValidationError(
                            f"Exponent {node.right.value} exceeds maximum safe limit ({MAX_EXPONENT_VALUE})."
                        )

            # Check function calls
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise ValidationError("Only direct standard mathematical function calls are permitted.")
                func_name = node.func.id
                if func_name not in ALLOWED_MATH_FUNCS and func_name not in {"Fraction", "Decimal"}:
                    raise ValidationError(f"Unknown or unapproved function '{func_name}'.")

            # Check variable and constant names
            if isinstance(node, ast.Name):
                name = node.id
                if name.startswith("__"):
                    raise ValidationError("Disallowed identifier access.")
                # Allow standard constants, math funcs, or single-letter symbolic variables
                if (
                    name not in ALLOWED_CONSTANTS
                    and name not in ALLOWED_MATH_FUNCS
                    and name not in {"x", "y", "z", "t", "a", "b", "c", "n", "k", "r", "s", "m", "p", "q"}
                ):
                    # Will be verified in specific domain context
                    pass

        return tree

    @classmethod
    def evaluate_arithmetic(cls, expr: str) -> tuple[Any, str]:
        """Safely evaluate arithmetic expression returning (exact_or_approx, type_label)."""
        tree = cls.validate_ast(expr)

        def _eval_node(node: ast.AST) -> Any:
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name):
                if node.id in ALLOWED_CONSTANTS:
                    return ALLOWED_CONSTANTS[node.id]
                raise ValidationError(f"Unbound variable '{node.id}' in purely arithmetic calculation.")
            if isinstance(node, ast.UnaryOp):
                operand = _eval_node(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                if isinstance(node.op, ast.UAdd):
                    return +operand
            if isinstance(node, ast.BinOp):
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    if right == 0:
                        raise ZeroDivisionError("Division by zero in mathematical expression.")
                    # Keep as Fraction if both integers for exact rational arithmetic
                    if isinstance(left, int) and isinstance(right, int):
                        return Fraction(left, right)
                    return left / right
                if isinstance(node.op, ast.FloorDiv):
                    if right == 0:
                        raise ZeroDivisionError("Floor division by zero.")
                    return left // right
                if isinstance(node.op, ast.Mod):
                    if right == 0:
                        raise ZeroDivisionError("Modulo by zero.")
                    return left % right
                if isinstance(node.op, ast.Pow):
                    return left**right
            if isinstance(node, ast.Call):
                func_name = node.func.id  # type: ignore
                args = [_eval_node(arg) for arg in node.args]
                func = ALLOWED_MATH_FUNCS[func_name]
                return func(*args)

            raise ValidationError(f"Unsupported AST node in evaluation: {type(node).__name__}")

        val = _eval_node(tree)
        if isinstance(val, Fraction):
            if val.denominator == 1:
                return (val.numerator, "exact_integer")
            return (val, "exact_rational")
        if isinstance(val, int):
            return (val, "exact_integer")
        if isinstance(val, Decimal):
            return (val, "exact_decimal")
        return (val, "floating_point")
