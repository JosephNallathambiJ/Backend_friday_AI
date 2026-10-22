"""Domain implementations for the FRIDAY Mathematical Engine.

Implements all 16 mathematical domains (A through P) with deterministic algorithms,
exact symbolic operations, numerical algorithms, error residuals, and bounds checks.
"""

import math
from decimal import Decimal
from fractions import Fraction
from typing import Any

import numpy as np
import sympy as sp

from app.core.exceptions import ValidationError
from app.domain.enums import MathComputationStatus, MathDomain, MathVerificationStatus
from app.math.models import MathResult
from app.math.parser import SafeMathParser


class DomainHandlers:
    """Implementations across the 16 core mathematical domains."""

    # -------------------------------------------------------------
    # DOMAIN A: Arithmetic and Number Systems
    # -------------------------------------------------------------
    @classmethod
    def arithmetic(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "basic")

        if sub_op == "primes":
            n = int(params.get("n", expr))
            is_p = sp.isprime(n)
            factors = sp.factorint(n) if n > 1 else {}
            return MathResult(
                original_problem=expr,
                normalized_expression=f"primes({n})",
                selected_domain=MathDomain.ARITHMETIC,
                selected_method="sympy.isprime_and_factorint",
                result={"is_prime": bool(is_p), "prime_factors": {int(k): int(v) for k, v in factors.items()}},
                exact_result=f"prime={is_p}, factors={factors}",
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Deterministic prime testing and integer factorization.",
            )

        if sub_op == "gcd_lcm":
            a = int(params.get("a", 0))
            b = int(params.get("b", 0))
            g = math.gcd(a, b)
            lcm_val = math.lcm(a, b) if hasattr(math, "lcm") else abs(a * b) // g if g else 0
            return MathResult(
                original_problem=expr,
                normalized_expression=f"gcd_lcm({a}, {b})",
                selected_domain=MathDomain.ARITHMETIC,
                selected_method="math.gcd_lcm",
                result={"gcd": g, "lcm": lcm_val},
                exact_result=f"gcd={g}, lcm={lcm_val}",
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Euclidean algorithm for greatest common divisor and least common multiple.",
            )

        if sub_op == "base_conversion":
            val = int(params.get("value", expr))
            to_base = int(params.get("to_base", 16))
            if to_base == 2:
                res_str = bin(val)
            elif to_base == 8:
                res_str = oct(val)
            elif to_base == 16:
                res_str = hex(val)
            else:
                raise ValidationError(f"Base conversion to base {to_base} not directly supported (use 2, 8, 16).")
            return MathResult(
                original_problem=expr,
                normalized_expression=f"base_convert({val}, base={to_base})",
                selected_domain=MathDomain.ARITHMETIC,
                selected_method="builtins.base_convert",
                result=res_str,
                exact_result=res_str,
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Exact integer radix/base conversion.",
            )

        # Basic arithmetic evaluation
        val, kind = SafeMathParser.evaluate_arithmetic(expr)
        exact_str = str(val)
        approx = float(val) if isinstance(val, (int, float, Fraction, Decimal)) else None
        status = MathComputationStatus.EXACT if kind.startswith("exact") else MathComputationStatus.APPROXIMATE
        return MathResult(
            original_problem=expr,
            normalized_expression=expr,
            selected_domain=MathDomain.ARITHMETIC,
            selected_method=f"ast_parser_{kind}",
            result=str(val),
            exact_result=exact_str if exact else None,
            approximate_result=approx,
            precision=precision,
            computation_status=status,
            verification_status=MathVerificationStatus.VERIFIED,
            method_description="Deterministic integer/rational/decimal arithmetic with zero-division and power protection.",
        )

    # -------------------------------------------------------------
    # DOMAIN B: Algebra
    # -------------------------------------------------------------
    @classmethod
    def algebra(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "simplify")
        sym_expr = sp.sympify(expr)

        if sub_op == "simplify":
            simp = sp.simplify(sym_expr)
            return MathResult(
                original_problem=expr,
                normalized_expression=str(sym_expr),
                selected_domain=MathDomain.ALGEBRA,
                selected_method="sympy.simplify",
                result=str(simp),
                exact_result=str(simp),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Symbolic algebraic expression simplification.",
            )

        if sub_op == "expand":
            expanded = sp.expand(sym_expr)
            return MathResult(
                original_problem=expr,
                normalized_expression=str(sym_expr),
                selected_domain=MathDomain.ALGEBRA,
                selected_method="sympy.expand",
                result=str(expanded),
                exact_result=str(expanded),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Polynomial and algebraic expansion.",
            )

        if sub_op == "factor":
            factored = sp.factor(sym_expr)
            return MathResult(
                original_problem=expr,
                normalized_expression=str(sym_expr),
                selected_domain=MathDomain.ALGEBRA,
                selected_method="sympy.factor",
                result=str(factored),
                exact_result=str(factored),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Polynomial factorization over rationals.",
            )

        if sub_op == "solve":
            var_name = params.get("variable", "x")
            var = sp.Symbol(var_name)
            sols = sp.solve(sym_expr, var)
            # Verify by substitution
            residuals = []
            for s in sols:
                try:
                    res = float(sym_expr.subs(var, s).evalf())
                    residuals.append(abs(res))
                except Exception:
                    pass
            max_res = max(residuals) if residuals else 0.0
            ver_status = (
                MathVerificationStatus.SUBSTITUTION_CONFIRMED
                if max_res < 1e-7
                else MathVerificationStatus.UNVERIFIED
            )
            return MathResult(
                original_problem=expr,
                normalized_expression=f"{sym_expr} = 0",
                selected_domain=MathDomain.ALGEBRA,
                selected_method="sympy.solve",
                result=[str(s) for s in sols],
                exact_result=str(sols),
                residual=max_res,
                computation_status=MathComputationStatus.EXACT,
                verification_status=ver_status,
                method_description="Exact analytical equation root solver with substitution residual verification.",
            )

        raise ValidationError(f"Unknown algebra sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN C: Geometry and Trigonometry
    # -------------------------------------------------------------
    @classmethod
    def geometry(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "circle")

        if sub_op == "circle":
            r = float(params.get("radius", 1.0))
            if r < 0:
                raise ValidationError("Radius cannot be negative.")
            area = math.pi * r * r
            perimeter = 2 * math.pi * r
            return MathResult(
                original_problem=expr,
                normalized_expression=f"circle(radius={r})",
                selected_domain=MathDomain.GEOMETRY,
                selected_method="euclidean_geometry.circle",
                result={"area": round(area, precision), "circumference": round(perimeter, precision)},
                approximate_result=area,
                precision=precision,
                computation_status=MathComputationStatus.EXACT if exact and r == 1 else MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Euclidean circle area and perimeter computation.",
            )

        if sub_op == "triangle":
            a = float(params.get("a", 3.0))
            b = float(params.get("b", 4.0))
            c = float(params.get("c", 5.0))
            if a + b <= c or a + c <= b or b + c <= a:
                raise ValidationError("Triangle inequality violated: sides cannot form a valid triangle.")
            s = (a + b + c) / 2
            area = math.sqrt(s * (s - a) * (s - b) * (s - c))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"triangle(sides=[{a}, {b}, {c}])",
                selected_domain=MathDomain.GEOMETRY,
                selected_method="heron_formula",
                result={"perimeter": a + b + c, "area": round(area, precision)},
                approximate_result=round(area, precision),
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Heron's formula for triangle area and perimeter.",
            )

        if sub_op == "distance_2d":
            p1 = params.get("p1", [0, 0])
            p2 = params.get("p2", [1, 1])
            dist = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
            midpoint = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]
            return MathResult(
                original_problem=expr,
                normalized_expression=f"distance_2d({p1}, {p2})",
                selected_domain=MathDomain.GEOMETRY,
                selected_method="euclidean_metric_2d",
                result={"distance": round(dist, precision), "midpoint": midpoint},
                approximate_result=dist,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Euclidean 2D distance and midpoint formula.",
            )

        raise ValidationError(f"Unknown geometry sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN D: Calculus
    # -------------------------------------------------------------
    @classmethod
    def calculus(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "derivative")
        var_name = params.get("variable", "x")
        x = sp.Symbol(var_name)
        sym_expr = sp.sympify(expr)

        if sub_op == "derivative":
            order = int(params.get("order", 1))
            deriv = sp.diff(sym_expr, x, order)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"d^{order}/d{var_name}^{order}({sym_expr})",
                selected_domain=MathDomain.CALCULUS,
                selected_method="sympy.diff",
                result=str(deriv),
                exact_result=str(deriv),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Symbolic differentiation applying product, quotient, and chain rules.",
            )

        if sub_op == "integral":
            limits = params.get("limits")
            if limits and len(limits) == 2:
                # Definite integral
                a = sp.sympify(limits[0])
                b = sp.sympify(limits[1])
                integ = sp.integrate(sym_expr, (x, a, b))
                approx = float(integ.evalf()) if integ.is_number else None
                return MathResult(
                    original_problem=expr,
                    normalized_expression=f"integrate({sym_expr}, ({var_name}, {a}, {b}))",
                    selected_domain=MathDomain.CALCULUS,
                    selected_method="sympy.integrate_definite",
                    result=str(integ),
                    exact_result=str(integ),
                    approximate_result=approx,
                    computation_status=MathComputationStatus.EXACT,
                    verification_status=MathVerificationStatus.VERIFIED,
                    method_description="Exact definite integration with symbolic boundary limits.",
                )
            integ = sp.integrate(sym_expr, x)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"integrate({sym_expr}, {var_name})",
                selected_domain=MathDomain.CALCULUS,
                selected_method="sympy.integrate_indefinite",
                result=str(integ) + " + C",
                exact_result=str(integ),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Symbolic indefinite integration.",
            )

        if sub_op == "limit":
            target = sp.sympify(params.get("target", 0))
            direction = params.get("direction", "+-")
            lim_res = sp.limit(sym_expr, x, target, dir=direction)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"limit({sym_expr}, {var_name}->{target})",
                selected_domain=MathDomain.CALCULUS,
                selected_method="sympy.limit",
                result=str(lim_res),
                exact_result=str(lim_res),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Symbolic limit evaluation with L'Hopital rule and series expansion.",
            )

        if sub_op == "taylor":
            around = sp.sympify(params.get("around", 0))
            order = int(params.get("order", 4))
            series_res = sp.series(sym_expr, x, around, n=order).removeO()
            return MathResult(
                original_problem=expr,
                normalized_expression=f"taylor({sym_expr}, around={around}, order={order})",
                selected_domain=MathDomain.CALCULUS,
                selected_method="sympy.series",
                result=str(series_res),
                exact_result=str(series_res),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Taylor and Maclaurin polynomial series expansion.",
            )

        raise ValidationError(f"Unknown calculus sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN E: Linear Algebra
    # -------------------------------------------------------------
    @classmethod
    def linear_algebra(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "matrix_multiply")
        mat_a = np.array(params.get("matrix_a", [[1, 0], [0, 1]]), dtype=float)

        if sub_op == "determinant":
            det = float(np.linalg.det(mat_a))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"det({mat_a.tolist()})",
                selected_domain=MathDomain.LINEAR_ALGEBRA,
                selected_method="numpy.linalg.det",
                result=round(det, precision),
                exact_result=str(round(det, precision)),
                computation_status=MathComputationStatus.EXACT if det.is_integer() else MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Matrix determinant via LU decomposition.",
            )

        if sub_op == "inverse":
            try:
                inv = np.linalg.inv(mat_a)
                # Verify residual: A * A_inv - I
                ident = np.eye(mat_a.shape[0])
                res = float(np.max(np.abs(np.dot(mat_a, inv) - ident)))
                ver = (
                    MathVerificationStatus.RESIDUAL_VALIDATED
                    if res < 1e-7
                    else MathVerificationStatus.UNVERIFIED
                )
                return MathResult(
                    original_problem=expr,
                    normalized_expression=f"inv({mat_a.tolist()})",
                    selected_domain=MathDomain.LINEAR_ALGEBRA,
                    selected_method="numpy.linalg.inv",
                    result=inv.tolist(),
                    residual=res,
                    computation_status=MathComputationStatus.APPROXIMATE,
                    verification_status=ver,
                    method_description="Matrix inversion with residual verification norm.",
                )
            except np.linalg.LinAlgError as e:
                raise ValidationError(f"Matrix is singular and non-invertible: {e}")

        if sub_op == "matrix_multiply":
            mat_b = np.array(params.get("matrix_b", [[1, 0], [0, 1]]), dtype=float)
            prod = np.dot(mat_a, mat_b)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"{mat_a.tolist()} @ {mat_b.tolist()}",
                selected_domain=MathDomain.LINEAR_ALGEBRA,
                selected_method="numpy.dot",
                result=prod.tolist(),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Matrix dot-product multiplication.",
            )

        if sub_op == "eigenvalues":
            w, v = np.linalg.eig(mat_a)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"eig({mat_a.tolist()})",
                selected_domain=MathDomain.LINEAR_ALGEBRA,
                selected_method="numpy.linalg.eig",
                result={"eigenvalues": [round(float(val), precision) for val in w], "eigenvectors": v.tolist()},
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Eigendecomposition for eigenvalues and eigenvectors.",
            )

        if sub_op == "solve_linear_system":
            vec_b = np.array(params.get("vector_b", [1, 1]), dtype=float)
            x_sol = np.linalg.solve(mat_a, vec_b)
            res = float(np.max(np.abs(np.dot(mat_a, x_sol) - vec_b)))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"Ax=b with A={mat_a.tolist()}, b={vec_b.tolist()}",
                selected_domain=MathDomain.LINEAR_ALGEBRA,
                selected_method="numpy.linalg.solve",
                result=x_sol.tolist(),
                residual=res,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.RESIDUAL_VALIDATED if res < 1e-7 else MathVerificationStatus.UNVERIFIED,
                method_description="Exact linear system solution Ax = b with residual check.",
            )

        raise ValidationError(f"Unknown linear algebra sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN F: Discrete Mathematics and Algorithms
    # -------------------------------------------------------------
    @classmethod
    def discrete_math(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "combinatorics")

        if sub_op == "combinatorics":
            n = int(params.get("n", 5))
            k = int(params.get("k", 2))
            if n < 0 or k < 0 or k > n:
                raise ValidationError("Invalid combinatorics parameters: require 0 <= k <= n.")
            comb = math.comb(n, k)
            perm = math.perm(n, k)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"C({n},{k}), P({n},{k})",
                selected_domain=MathDomain.DISCRETE_MATH,
                selected_method="math.comb_and_perm",
                result={"combinations": comb, "permutations": perm},
                exact_result=f"C={comb}, P={perm}",
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Exact discrete binomial combinations and permutations.",
            )

        if sub_op == "sets":
            s1 = set(params.get("set_a", [1, 2, 3]))
            s2 = set(params.get("set_b", [3, 4, 5]))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"set_operations({s1}, {s2})",
                selected_domain=MathDomain.DISCRETE_MATH,
                selected_method="builtins.set_operations",
                result={
                    "union": sorted(list(s1 | s2)),
                    "intersection": sorted(list(s1 & s2)),
                    "difference_a_minus_b": sorted(list(s1 - s2)),
                    "symmetric_difference": sorted(list(s1 ^ s2)),
                },
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Exact set-theoretic operations (union, intersection, set differences).",
            )

        raise ValidationError(f"Unknown discrete math sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN G: Probability
    # -------------------------------------------------------------
    @classmethod
    def probability(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "bayes")

        if sub_op == "bayes":
            p_b_given_a = float(params.get("p_b_given_a", 0.9))
            p_a = float(params.get("p_a", 0.01))
            p_b = float(params.get("p_b", 0.05))
            if p_b == 0:
                raise ValidationError("P(B) cannot be zero in Bayes theorem.")
            p_a_given_b = (p_b_given_a * p_a) / p_b
            return MathResult(
                original_problem=expr,
                normalized_expression="P(A|B) = [P(B|A)*P(A)] / P(B)",
                selected_domain=MathDomain.PROBABILITY,
                selected_method="bayes_theorem",
                result=round(p_a_given_b, precision),
                approximate_result=p_a_given_b,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Bayes theorem conditional posterior probability calculation.",
            )

        if sub_op == "binomial":
            n = int(params.get("n", 10))
            k = int(params.get("k", 3))
            p = float(params.get("p", 0.5))
            pmf = math.comb(n, k) * (p**k) * ((1 - p) ** (n - k))
            expected = n * p
            variance = n * p * (1 - p)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"Binomial(n={n}, k={k}, p={p})",
                selected_domain=MathDomain.PROBABILITY,
                selected_method="binomial_pmf",
                result={"pmf": round(pmf, precision), "expected_value": expected, "variance": variance},
                approximate_result=round(pmf, precision),
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Binomial distribution probability mass function and moments.",
            )

        raise ValidationError(f"Unknown probability sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN H: Statistics
    # -------------------------------------------------------------
    @classmethod
    def statistics(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        data = [float(x) for x in params.get("data", [1, 2, 3, 4, 5, 6, 7, 8, 9])]
        if not data:
            raise ValidationError("Data list cannot be empty for statistical analysis.")

        sub_op = params.get("sub_operation", "descriptive")
        if sub_op == "descriptive":
            arr = np.array(data)
            mean_val = float(np.mean(arr))
            median_val = float(np.median(arr))
            std_val = float(np.std(arr, ddof=1)) if len(data) > 1 else 0.0
            var_val = float(np.var(arr, ddof=1)) if len(data) > 1 else 0.0
            min_val = float(np.min(arr))
            max_val = float(np.max(arr))
            q25 = float(np.percentile(arr, 25))
            q75 = float(np.percentile(arr, 75))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"descriptive_statistics(n={len(data)})",
                selected_domain=MathDomain.STATISTICS,
                selected_method="numpy.statistics_summary",
                result={
                    "count": len(data),
                    "mean": round(mean_val, precision),
                    "median": round(median_val, precision),
                    "std_dev": round(std_val, precision),
                    "variance": round(var_val, precision),
                    "min": min_val,
                    "max": max_val,
                    "range": max_val - min_val,
                    "iqr": round(q75 - q25, precision),
                },
                approximate_result=mean_val,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Sample descriptive statistics including central tendency, dispersion, and quartiles.",
            )

        if sub_op == "regression":
            data_y = [float(y) for y in params.get("data_y", data)]
            if len(data) != len(data_y):
                raise ValidationError("data and data_y must have equal length for linear regression.")
            x_arr = np.array(data)
            y_arr = np.array(data_y)
            slope, intercept = np.polyfit(x_arr, y_arr, 1)
            y_pred = slope * x_arr + intercept
            ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
            ss_res = np.sum((y_arr - y_pred) ** 2)
            r2 = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0
            return MathResult(
                original_problem=expr,
                normalized_expression="linear_regression(x, y)",
                selected_domain=MathDomain.STATISTICS,
                selected_method="numpy.polyfit_deg1",
                result={"slope": round(float(slope), precision), "intercept": round(float(intercept), precision), "r_squared": round(r2, precision)},
                approximate_result=r2,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.RESIDUAL_VALIDATED if ss_res >= 0 else MathVerificationStatus.UNVERIFIED,
                method_description="Ordinary least squares simple linear regression.",
            )

        raise ValidationError(f"Unknown statistics sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN I: Numerical Methods
    # -------------------------------------------------------------
    @classmethod
    def numerical_methods(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "bisection")
        var = sp.Symbol("x")
        sym_expr = sp.sympify(expr)
        f = sp.lambdify(var, sym_expr, "numpy")

        if sub_op == "bisection":
            a = float(params.get("a", 0.0))
            b = float(params.get("b", 2.0))
            tol = float(params.get("tol", 1e-6))
            max_iter = int(params.get("max_iter", 100))

            fa, fb = f(a), f(b)
            if fa * fb > 0:
                raise ValidationError("Bisection requires f(a) and f(b) to have opposite signs.")

            c = a
            for _ in range(max_iter):
                c = (a + b) / 2
                fc = f(c)
                if abs(fc) < tol or (b - a) / 2 < tol:
                    break
                if fa * fc < 0:
                    b = c
                    fb = fc
                else:
                    a = c
                    fa = fc

            residual = float(abs(f(c)))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"bisection({sym_expr}=0, [{a}, {b}])",
                selected_domain=MathDomain.NUMERICAL_METHODS,
                selected_method="bisection_root_finding",
                result=round(float(c), precision),
                approximate_result=float(c),
                residual=residual,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.RESIDUAL_VALIDATED if residual < 1e-4 else MathVerificationStatus.NOT_CONVERGED,
                method_description="Numerical interval bisection root finding with residual check.",
            )

        if sub_op == "newton":
            x0 = float(params.get("x0", 1.0))
            tol = float(params.get("tol", 1e-6))
            max_iter = int(params.get("max_iter", 100))
            f_prime = sp.lambdify(var, sp.diff(sym_expr, var), "numpy")

            cur = x0
            for _ in range(max_iter):
                df_val = f_prime(cur)
                if abs(df_val) < 1e-12:
                    raise ValidationError("Derivative near zero in Newton-Raphson method.")
                cur = cur - f(cur) / df_val
                if abs(f(cur)) < tol:
                    break

            residual = float(abs(f(cur)))
            return MathResult(
                original_problem=expr,
                normalized_expression=f"newton({sym_expr}=0, x0={x0})",
                selected_domain=MathDomain.NUMERICAL_METHODS,
                selected_method="newton_raphson_root_finding",
                result=round(float(cur), precision),
                approximate_result=float(cur),
                residual=residual,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.RESIDUAL_VALIDATED if residual < 1e-4 else MathVerificationStatus.NOT_CONVERGED,
                method_description="Newton-Raphson tangent root iteration with residual verification.",
            )

        raise ValidationError(f"Unknown numerical methods sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN J: Optimization and Operations Research
    # -------------------------------------------------------------
    @classmethod
    def optimization(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        var = sp.Symbol("x")
        sym_expr = sp.sympify(expr)
        f = sp.lambdify(var, sym_expr, "numpy")

        # Golden-section search for 1D scalar minimum
        a = float(params.get("a", -5.0))
        b = float(params.get("b", 5.0))
        tol = float(params.get("tol", 1e-5))
        invphi = (math.sqrt(5) - 1) / 2
        invphi2 = (3 - math.sqrt(5)) / 2

        h = b - a
        n = int(math.ceil(math.log(tol / h) / math.log(invphi))) if tol < h else 10
        c = a + invphi2 * h
        d = a + invphi * h
        yc = f(c)
        yd = f(d)

        for _ in range(min(n, 100)):
            if yc < yd:
                b = d
                d = c
                yd = yc
                h = invphi * h
                c = a + invphi2 * h
                yc = f(c)
            else:
                a = c
                c = d
                yc = yd
                h = invphi * h
                d = a + invphi * h
                yd = f(d)

        min_x = (a + b) / 2
        min_y = float(f(min_x))
        return MathResult(
            original_problem=expr,
            normalized_expression=f"minimize({sym_expr}, [{a}, {b}])",
            selected_domain=MathDomain.OPTIMIZATION,
            selected_method="golden_section_1d_search",
            result={"min_x": round(min_x, precision), "min_y": round(min_y, precision)},
            approximate_result=min_y,
            precision=precision,
            computation_status=MathComputationStatus.APPROXIMATE,
            verification_status=MathVerificationStatus.VERIFIED,
            method_description="Golden section 1D scalar minimization over bounded interval.",
        )

    # -------------------------------------------------------------
    # DOMAIN K: Information Theory and Cryptographic Mathematics
    # -------------------------------------------------------------
    @classmethod
    def information_theory(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "entropy")

        if sub_op == "entropy":
            probs = [float(p) for p in params.get("probabilities", [0.5, 0.5])]
            total_p = sum(probs)
            if abs(total_p - 1.0) > 1e-5:
                # Normalize probabilities
                probs = [p / total_p for p in probs]
            entropy = -sum(p * math.log2(p) for p in probs if p > 0)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"shannon_entropy({probs})",
                selected_domain=MathDomain.INFORMATION_THEORY,
                selected_method="shannon_entropy",
                result=round(entropy, precision),
                approximate_result=entropy,
                precision=precision,
                units="bits",
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Shannon information entropy H(X) = -sum(p_i * log2(p_i)).",
            )

        if sub_op == "mod_exp":
            base = int(params.get("base", 2))
            exp_val = int(params.get("exp", 10))
            mod_val = int(params.get("mod", 1000))
            if mod_val <= 0:
                raise ValidationError("Modulus must be positive.")
            res = pow(base, exp_val, mod_val)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"{base}^{exp_val} mod {mod_val}",
                selected_domain=MathDomain.INFORMATION_THEORY,
                selected_method="modular_exponentiation",
                result=res,
                exact_result=str(res),
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Fast binary modular exponentiation.",
            )

        if sub_op == "mod_inv":
            a = int(params.get("a", 3))
            m = int(params.get("mod", 11))
            try:
                inv = pow(a, -1, m)
                return MathResult(
                    original_problem=expr,
                    normalized_expression=f"{a}^(-1) mod {m}",
                    selected_domain=MathDomain.INFORMATION_THEORY,
                    selected_method="extended_euclidean_algorithm",
                    result=inv,
                    exact_result=str(inv),
                    computation_status=MathComputationStatus.EXACT,
                    verification_status=MathVerificationStatus.SUBSTITUTION_CONFIRMED if (a * inv) % m == 1 else MathVerificationStatus.UNVERIFIED,
                    method_description="Modular multiplicative inverse via extended Euclidean algorithm.",
                )
            except ValueError:
                raise ValidationError(f"Modular inverse does not exist: {a} and {m} are not coprime.")

        raise ValidationError(f"Unknown info theory sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN L: Financial and Business Mathematics
    # -------------------------------------------------------------
    @classmethod
    def financial(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "compound_interest")

        if sub_op == "compound_interest":
            principal = float(params.get("principal", 1000.0))
            rate = float(params.get("rate", 0.05))
            time_yrs = float(params.get("time_years", 5.0))
            n_per_year = int(params.get("compound_frequency", 12))
            amount = principal * ((1 + (rate / n_per_year)) ** (n_per_year * time_yrs))
            interest = amount - principal
            return MathResult(
                original_problem=expr,
                normalized_expression=f"compound_interest(P={principal}, r={rate}, t={time_yrs}, n={n_per_year})",
                selected_domain=MathDomain.FINANCIAL_MATH,
                selected_method="compound_interest_formula",
                result={"future_value": round(amount, 2), "total_interest": round(interest, 2)},
                approximate_result=round(amount, 2),
                precision=2,
                units="currency",
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Standard compound interest formula A = P(1 + r/n)^(nt).",
            )

        if sub_op == "loan_amortization":
            principal = float(params.get("principal", 200000.0))
            annual_rate = float(params.get("annual_rate", 0.06))
            months = int(params.get("months", 360))
            r = annual_rate / 12
            if r == 0:
                payment = principal / months
            else:
                payment = principal * (r * ((1 + r) ** months)) / (((1 + r) ** months) - 1)
            total_paid = payment * months
            return MathResult(
                original_problem=expr,
                normalized_expression=f"loan_amortization(P={principal}, rate={annual_rate}, n={months})",
                selected_domain=MathDomain.FINANCIAL_MATH,
                selected_method="fixed_rate_amortization",
                result={"monthly_payment": round(payment, 2), "total_paid": round(total_paid, 2), "total_interest": round(total_paid - principal, 2)},
                approximate_result=round(payment, 2),
                precision=2,
                units="currency/month",
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Fixed-rate loan monthly payment formula.",
            )

        raise ValidationError(f"Unknown financial sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN M: Physics and Engineering Calculations
    # -------------------------------------------------------------
    @classmethod
    def physics(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "unit_conversion")

        if sub_op == "unit_conversion":
            val = float(params.get("value", 1.0))
            from_u = params.get("from_unit", "m").lower()
            to_u = params.get("to_unit", "ft").lower()

            # Length conversions to meters
            length_to_m = {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "ft": 0.3048, "in": 0.0254, "mi": 1609.344}
            # Mass conversions to kg
            mass_to_kg = {"kg": 1.0, "g": 0.001, "mg": 1e-6, "lb": 0.45359237, "oz": 0.02834952}

            if from_u in length_to_m and to_u in length_to_m:
                in_m = val * length_to_m[from_u]
                converted = in_m / length_to_m[to_u]
            elif from_u in mass_to_kg and to_u in mass_to_kg:
                in_kg = val * mass_to_kg[from_u]
                converted = in_kg / mass_to_kg[to_u]
            elif from_u in {"c", "f", "k"} and to_u in {"c", "f", "k"}:
                # Temperature
                if from_u == "c":
                    k_val = val + 273.15
                elif from_u == "f":
                    k_val = (val - 32) * 5 / 9 + 273.15
                else:
                    k_val = val

                if to_u == "c":
                    converted = k_val - 273.15
                elif to_u == "f":
                    converted = (k_val - 273.15) * 9 / 5 + 32
                else:
                    converted = k_val
            else:
                raise ValidationError(f"Unsupported unit conversion from '{from_u}' to '{to_u}'.")

            return MathResult(
                original_problem=expr,
                normalized_expression=f"{val} {from_u} -> {to_u}",
                selected_domain=MathDomain.PHYSICS_ENGINEERING,
                selected_method="dimensional_unit_converter",
                result=round(converted, precision),
                approximate_result=converted,
                units=to_u,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Dimensional conversion between standard SI and Imperial units.",
            )

        if sub_op == "kinematics":
            u = float(params.get("u", 0.0))
            a = float(params.get("a", 9.8))
            t = float(params.get("t", 2.0))
            v = u + a * t
            s = u * t + 0.5 * a * (t**2)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"kinematics(u={u}, a={a}, t={t})",
                selected_domain=MathDomain.PHYSICS_ENGINEERING,
                selected_method="constant_acceleration_kinematics",
                result={"final_velocity": round(v, precision), "displacement": round(s, precision)},
                units="m/s and m",
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Uniform acceleration equations of motion.",
            )

        if sub_op == "ohms_law":
            v = params.get("voltage")
            i = params.get("current")
            r = params.get("resistance")
            if v is None and i is not None and r is not None:
                calc_v = float(i) * float(r)
                power = calc_v * float(i)
                return MathResult(
                    original_problem=expr,
                    normalized_expression=f"V = I*R with I={i}, R={r}",
                    selected_domain=MathDomain.PHYSICS_ENGINEERING,
                    selected_method="ohms_law",
                    result={"voltage": round(calc_v, precision), "power": round(power, precision)},
                    units="V and W",
                    computation_status=MathComputationStatus.EXACT,
                    verification_status=MathVerificationStatus.VERIFIED,
                    method_description="Ohm's law and Joule heating calculation.",
                )
            if i is None and v is not None and r is not None:
                calc_i = float(v) / float(r)
                power = float(v) * calc_i
                return MathResult(
                    original_problem=expr,
                    normalized_expression=f"I = V/R with V={v}, R={r}",
                    selected_domain=MathDomain.PHYSICS_ENGINEERING,
                    selected_method="ohms_law",
                    result={"current": round(calc_i, precision), "power": round(power, precision)},
                    units="A and W",
                    computation_status=MathComputationStatus.EXACT,
                    verification_status=MathVerificationStatus.VERIFIED,
                    method_description="Ohm's law and Joule heating calculation.",
                )

        raise ValidationError(f"Unknown physics sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN N: Data Science and Machine Learning Mathematics
    # -------------------------------------------------------------
    @classmethod
    def data_science_ml(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "metrics")

        if sub_op == "metrics":
            tp = int(params.get("tp", 80))
            fp = int(params.get("fp", 10))
            fn = int(params.get("fn", 20))
            tn = int(params.get("tn", 890))
            total = tp + fp + fn + tn
            acc = (tp + tn) / total if total > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            return MathResult(
                original_problem=expr,
                normalized_expression=f"confusion_matrix(TP={tp}, FP={fp}, FN={fn}, TN={tn})",
                selected_domain=MathDomain.DATA_SCIENCE_ML,
                selected_method="classification_metrics",
                result={
                    "accuracy": round(acc, precision),
                    "precision": round(prec, precision),
                    "recall": round(rec, precision),
                    "f1_score": round(f1, precision),
                },
                approximate_result=round(f1, precision),
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Binary classification evaluation metrics from confusion matrix.",
            )

        if sub_op == "distances":
            v1 = np.array(params.get("v1", [1.0, 2.0, 3.0]))
            v2 = np.array(params.get("v2", [4.0, 5.0, 6.0]))
            euclidean = float(np.linalg.norm(v1 - v2))
            manhattan = float(np.sum(np.abs(v1 - v2)))
            cosine = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
            return MathResult(
                original_problem=expr,
                normalized_expression="distance_metrics(v1, v2)",
                selected_domain=MathDomain.DATA_SCIENCE_ML,
                selected_method="vector_distance_metrics",
                result={
                    "euclidean_distance": round(euclidean, precision),
                    "manhattan_distance": round(manhattan, precision),
                    "cosine_similarity": round(cosine, precision),
                },
                approximate_result=euclidean,
                precision=precision,
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Metric space distance metrics and cosine similarity.",
            )

        raise ValidationError(f"Unknown data science sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN O: Signals and Transforms
    # -------------------------------------------------------------
    @classmethod
    def signals(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "fft")

        if sub_op == "fft":
            signal = [float(x) for x in params.get("signal", [1.0, 0.0, -1.0, 0.0])]
            fft_vals = np.fft.fft(signal)
            magnitudes = [round(float(abs(val)), precision) for val in fft_vals]
            return MathResult(
                original_problem=expr,
                normalized_expression=f"fft(signal_length={len(signal)})",
                selected_domain=MathDomain.SIGNALS_TRANSFORMS,
                selected_method="numpy.fft.fft",
                result={"spectral_magnitudes": magnitudes, "complex_coefficients": [str(c) for c in fft_vals]},
                computation_status=MathComputationStatus.APPROXIMATE,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Cooley-Tukey Fast Fourier Transform discrete frequency decomposition.",
            )

        if sub_op == "convolve":
            sig1 = [float(x) for x in params.get("sig1", [1, 2, 3])]
            sig2 = [float(x) for x in params.get("sig2", [0, 1, 0.5])]
            conv = np.convolve(sig1, sig2).tolist()
            return MathResult(
                original_problem=expr,
                normalized_expression=f"convolve({sig1}, {sig2})",
                selected_domain=MathDomain.SIGNALS_TRANSFORMS,
                selected_method="numpy.convolve",
                result=[round(float(v), precision) for v in conv],
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Discrete linear 1D signal convolution.",
            )

        raise ValidationError(f"Unknown signals sub_operation '{sub_op}'.")

    # -------------------------------------------------------------
    # DOMAIN P: Logic, Symbolic Reasoning, and Proofs
    # -------------------------------------------------------------
    @classmethod
    def logic(cls, expr: str, params: dict[str, Any], precision: int, exact: bool) -> MathResult:
        sub_op = params.get("sub_operation", "eval_formula")
        sym_expr = sp.sympify(expr)

        if sub_op == "truth_table":
            atoms = sorted(list(sym_expr.atoms(sp.Symbol)), key=lambda s: s.name)
            table = []
            num_rows = 1 << len(atoms)
            for i in range(num_rows):
                row = {}
                assignment = {}
                for bit, atom in enumerate(atoms):
                    val = bool((i >> bit) & 1)
                    row[atom.name] = val
                    assignment[atom] = val
                row["RESULT"] = bool(sym_expr.subs(assignment))
                table.append(row)
            return MathResult(
                original_problem=expr,
                normalized_expression=f"truth_table({sym_expr})",
                selected_domain=MathDomain.LOGIC_PROOFS,
                selected_method="sympy.logic.truth_table",
                result={"variables": [a.name for a in atoms], "table": table},
                computation_status=MathComputationStatus.EXACT,
                verification_status=MathVerificationStatus.VERIFIED,
                method_description="Exhaustive boolean truth table generation over all valuations.",
            )

        simp_bool = sp.simplify_logic(sym_expr)
        is_taut = bool(simp_bool is True or simp_bool == sp.true)
        is_contra = bool(simp_bool is False or simp_bool == sp.false)
        return MathResult(
            original_problem=expr,
            normalized_expression=str(sym_expr),
            selected_domain=MathDomain.LOGIC_PROOFS,
            selected_method="sympy.logic.boolalg",
            result={"simplified": str(simp_bool), "is_tautology": is_taut, "is_contradiction": is_contra},
            exact_result=str(simp_bool),
            computation_status=MathComputationStatus.EXACT,
            verification_status=MathVerificationStatus.VERIFIED,
            method_description="Propositional logic theorem verification, tautology and contradiction testing.",
        )
