"""Deterministic Mathematical Engine for FRIDAY AI.

Dispatches validated mathematical operations across the 16 core domains,
enforces timeouts and resource bounds, avoids arbitrary eval/exec,
and performs independent verification of computed results.
"""

import asyncio
import time

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.logging import logger
from app.domain.enums import MathComputationStatus, MathDomain, MathVerificationStatus
from app.math.domains import DomainHandlers
from app.math.models import MathProblemRequest, MathResult


class MathematicalEngine:
    """Core deterministic calculation and symbolic reasoning engine."""

    DOMAIN_KEYWORDS = {
        MathDomain.CALCULUS: ["diff", "derivative", "integrate", "integral", "limit", "taylor", "series"],
        MathDomain.ALGEBRA: ["solve", "simplify", "expand", "factor", "polynomial", "quadratic"],
        MathDomain.LINEAR_ALGEBRA: ["matrix", "determinant", "det", "eigen", "inverse", "inv", "dot", "matmul"],
        MathDomain.GEOMETRY: ["triangle", "circle", "distance", "midpoint", "hypotenuse", "polygon", "radius"],
        MathDomain.STATISTICS: ["mean", "median", "std", "variance", "regression", "quartile", "iqr", "correlation"],
        MathDomain.PROBABILITY: ["bayes", "binomial", "probability", "pmf", "cdf", "chance"],
        MathDomain.NUMERICAL_METHODS: ["bisection", "newton", "root", "secant", "numerical"],
        MathDomain.OPTIMIZATION: ["minimize", "maximize", "optimum", "golden_section"],
        MathDomain.INFORMATION_THEORY: ["entropy", "shannon", "mod_exp", "mod_inv"],
        MathDomain.FINANCIAL_MATH: ["interest", "compound", "amortization", "loan", "present_value", "future_value"],
        MathDomain.PHYSICS_ENGINEERING: ["unit", "convert", "kinematics", "velocity", "ohm", "voltage", "resistance"],
        MathDomain.DATA_SCIENCE_ML: ["metrics", "confusion_matrix", "f1", "precision", "recall", "cosine_similarity"],
        MathDomain.SIGNALS_TRANSFORMS: ["fft", "fourier", "convolve", "signal", "spectrum"],
        MathDomain.LOGIC_PROOFS: ["tautology", "contradiction", "truth_table", "implies", "boolean"],
        MathDomain.DISCRETE_MATH: ["combinatorics", "permutation", "combination", "sets", "subset"],
        MathDomain.ARITHMETIC: ["prime", "factorint", "gcd", "lcm", "base", "modulo", "calc"],
    }

    @classmethod
    def detect_domain(cls, expression: str, operation: str) -> MathDomain:
        """Infer target mathematical domain from keywords or structural expression tokens."""
        text = f"{expression} {operation}".lower()

        # Check explicit keywords
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return domain

        # Algebraic equations containing '=' or single-variable expressions
        if "=" in expression or "==" in expression:
            return MathDomain.ALGEBRA

        # Default fallback is arithmetic
        return MathDomain.ARITHMETIC

    @classmethod
    async def compute(cls, request: MathProblemRequest) -> MathResult:
        """Execute mathematical request within strict timeout and safety bounds."""
        start_time = time.perf_counter()
        timeout = min(request.timeout_seconds, settings.MAX_MATH_COMPUTATION_TIMEOUT)
        # 1. Clean leading command prefixes if present
        cleaned_expr = request.expression.strip()
        for prefix in ["calculate ", "calc ", "compute ", "solve for ", "solve "]:
            if cleaned_expr.lower().startswith(prefix):
                cleaned_expr = cleaned_expr[len(prefix):].strip()
                break

        # 2. Resolve domain
        domain = request.domain or cls.detect_domain(cleaned_expr, request.operation)
        params = dict(request.parameters)

        # Map common operations to sub_operation parameter
        if "sub_operation" not in params:
            op_lower = request.operation.lower()
            if op_lower in {"simplify", "expand", "factor", "solve"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"derivative", "integral", "limit", "taylor"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"determinant", "inverse", "eigenvalues", "matrix_multiply", "solve_linear_system"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"descriptive", "regression"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"bisection", "newton"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"entropy", "mod_exp", "mod_inv"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"compound_interest", "loan_amortization"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"unit_conversion", "kinematics", "ohms_law"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"metrics", "distances"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"fft", "convolve"}:
                params["sub_operation"] = op_lower
            elif op_lower in {"truth_table"}:
                params["sub_operation"] = op_lower

        # 2. Dispatch worker synchronously in thread pool with timeout
        loop = asyncio.get_running_loop()

        def _execute() -> MathResult:
            if domain == MathDomain.ARITHMETIC:
                return DomainHandlers.arithmetic(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.ALGEBRA:
                return DomainHandlers.algebra(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.GEOMETRY:
                return DomainHandlers.geometry(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.CALCULUS:
                return DomainHandlers.calculus(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.LINEAR_ALGEBRA:
                return DomainHandlers.linear_algebra(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.DISCRETE_MATH:
                return DomainHandlers.discrete_math(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.PROBABILITY:
                return DomainHandlers.probability(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.STATISTICS:
                return DomainHandlers.statistics(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.NUMERICAL_METHODS:
                return DomainHandlers.numerical_methods(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.OPTIMIZATION:
                return DomainHandlers.optimization(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.INFORMATION_THEORY:
                return DomainHandlers.information_theory(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.FINANCIAL_MATH:
                return DomainHandlers.financial(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.PHYSICS_ENGINEERING:
                return DomainHandlers.physics(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.DATA_SCIENCE_ML:
                return DomainHandlers.data_science_ml(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.SIGNALS_TRANSFORMS:
                return DomainHandlers.signals(cleaned_expr, params, request.precision, request.exact)
            if domain == MathDomain.LOGIC_PROOFS:
                return DomainHandlers.logic(cleaned_expr, params, request.precision, request.exact)

            raise ValidationError(f"Unsupported mathematical domain '{domain}'.")

        try:
            result = await asyncio.wait_for(loop.run_in_executor(None, _execute), timeout=timeout)
            result.execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return result
        except TimeoutError:
            logger.warning(f"Mathematical calculation timed out after {timeout}s: '{request.expression}'")
            return MathResult(
                original_problem=request.expression,
                normalized_expression=request.expression,
                selected_domain=domain,
                selected_method="timeout_guard",
                result=None,
                computation_status=MathComputationStatus.TIMED_OUT,
                verification_status=MathVerificationStatus.UNVERIFIED,
                method_description="Calculation exceeded maximum execution timeout limit.",
                error_details=f"Computation timed out after {timeout} seconds.",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )
        except ZeroDivisionError as e:
            return MathResult(
                original_problem=request.expression,
                normalized_expression=request.expression,
                selected_domain=domain,
                selected_method="zero_division_guard",
                result=None,
                computation_status=MathComputationStatus.FAILED,
                verification_status=MathVerificationStatus.UNVERIFIED,
                method_description="Division by zero error caught.",
                error_details=str(e),
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )
        except Exception as e:
            logger.error(f"Mathematical engine error for '{request.expression}': {e}")
            return MathResult(
                original_problem=request.expression,
                normalized_expression=request.expression,
                selected_domain=domain,
                selected_method="error_handler",
                result=None,
                computation_status=MathComputationStatus.FAILED,
                verification_status=MathVerificationStatus.UNVERIFIED,
                method_description="Computation failed during domain execution.",
                error_details=str(e),
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

    async def evaluate_expression(self, expression: str, operation: str = "calculate") -> MathResult:
        """Convenience method to evaluate a math expression string."""
        req = MathProblemRequest(expression=expression, operation=operation)
        return await self.compute(req)


# Global instance
mathematical_engine = MathematicalEngine()
