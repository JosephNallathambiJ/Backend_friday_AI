"""Unit tests for the FRIDAY Deterministic Mathematical Engine across all 16 domains."""

import pytest

from app.core.exceptions import ValidationError
from app.domain.enums import MathComputationStatus, MathDomain, MathVerificationStatus
from app.math.engine import MathematicalEngine
from app.math.models import MathProblemRequest
from app.math.parser import SafeMathParser


@pytest.mark.asyncio
async def test_domain_a_arithmetic():
    """Test arithmetic, fractions, primes, gcd/lcm, and base conversions."""
    # Basic arithmetic and power
    res = await MathematicalEngine.compute(MathProblemRequest(expression="2 + 3 * 4"))
    assert res.result == "14"
    assert res.computation_status == MathComputationStatus.EXACT

    # Exact rational fraction
    res_frac = await MathematicalEngine.compute(MathProblemRequest(expression="1/3 + 1/6"))
    assert res_frac.result == "1/2"
    assert res_frac.computation_status == MathComputationStatus.EXACT

    # Prime testing and factorization
    res_prime = await MathematicalEngine.compute(
        MathProblemRequest(expression="primes", domain=MathDomain.ARITHMETIC, parameters={"sub_operation": "primes", "n": 29})
    )
    assert res_prime.result["is_prime"] is True

    # GCD and LCM
    res_gcd = await MathematicalEngine.compute(
        MathProblemRequest(expression="gcd_lcm", domain=MathDomain.ARITHMETIC, parameters={"sub_operation": "gcd_lcm", "a": 54, "b": 24})
    )
    assert res_gcd.result["gcd"] == 6
    assert res_gcd.result["lcm"] == 216

    # Base conversion
    res_base = await MathematicalEngine.compute(
        MathProblemRequest(expression="255", domain=MathDomain.ARITHMETIC, parameters={"sub_operation": "base_conversion", "to_base": 16})
    )
    assert res_base.result == "0xff"


@pytest.mark.asyncio
async def test_arithmetic_guards_zero_division_and_overflow():
    """Verify division by zero and excessive power limits are caught safely."""
    # Division by zero
    res_zero = await MathematicalEngine.compute(MathProblemRequest(expression="10 / 0"))
    assert res_zero.computation_status == MathComputationStatus.FAILED
    assert "division by zero" in res_zero.error_details.lower()

    # Disallowed AST element (import attempt)
    with pytest.raises(ValidationError):
        SafeMathParser.validate_ast("__import__('os').system('ls')")

    # Exponent too large
    with pytest.raises(ValidationError):
        SafeMathParser.validate_ast("2 ** 999999")


@pytest.mark.asyncio
async def test_domain_b_algebra():
    """Test algebraic simplification, expansion, factoring, and equation solving."""
    # Simplify
    res_simp = await MathematicalEngine.compute(
        MathProblemRequest(expression="(x**2 - 1)/(x - 1)", operation="simplify")
    )
    assert res_simp.result == "x + 1"

    # Expand
    res_exp = await MathematicalEngine.compute(
        MathProblemRequest(expression="(x + 2)**2", operation="expand")
    )
    assert "x**2 + 4*x + 4" in res_exp.result

    # Solve quadratic equation with residual verification
    res_solve = await MathematicalEngine.compute(
        MathProblemRequest(expression="x**2 - 16", operation="solve", parameters={"variable": "x"})
    )
    assert "-4" in res_solve.result and "4" in res_solve.result
    assert res_solve.verification_status == MathVerificationStatus.SUBSTITUTION_CONFIRMED
    assert res_solve.residual is not None and res_solve.residual < 1e-6


@pytest.mark.asyncio
async def test_domain_c_geometry():
    """Test circle properties, triangle Heron's formula, and 2D distance."""
    # Circle
    res_circ = await MathematicalEngine.compute(
        MathProblemRequest(expression="circle", domain=MathDomain.GEOMETRY, parameters={"sub_operation": "circle", "radius": 3.0})
    )
    assert abs(res_circ.result["area"] - 28.2743) < 0.01

    # Triangle Heron formula (3, 4, 5 right triangle -> area 6.0)
    res_tri = await MathematicalEngine.compute(
        MathProblemRequest(expression="triangle", domain=MathDomain.GEOMETRY, parameters={"sub_operation": "triangle", "a": 3, "b": 4, "c": 5})
    )
    assert res_tri.result["area"] == 6.0
    assert res_tri.result["perimeter"] == 12.0

    # 2D distance between (0, 0) and (3, 4) -> 5.0
    res_dist = await MathematicalEngine.compute(
        MathProblemRequest(expression="distance", domain=MathDomain.GEOMETRY, parameters={"sub_operation": "distance_2d", "p1": [0, 0], "p2": [3, 4]})
    )
    assert res_dist.result["distance"] == 5.0


@pytest.mark.asyncio
async def test_domain_d_calculus():
    """Test symbolic differentiation, limits, and integration."""
    # Derivative: d/dx(x**3 + 2*x) = 3*x**2 + 2
    res_diff = await MathematicalEngine.compute(
        MathProblemRequest(expression="x**3 + 2*x", operation="derivative")
    )
    assert "3*x**2 + 2" in res_diff.result

    # Definite integral: int_0^2 (3*x**2) dx = 8
    res_int = await MathematicalEngine.compute(
        MathProblemRequest(expression="3*x**2", operation="integral", parameters={"limits": [0, 2]})
    )
    assert res_int.result == "8"

    # Limit: lim_{x->0} sin(x)/x = 1
    res_lim = await MathematicalEngine.compute(
        MathProblemRequest(expression="sin(x)/x", operation="limit", parameters={"target": 0})
    )
    assert res_lim.result == "1"


@pytest.mark.asyncio
async def test_domain_e_linear_algebra():
    """Test matrix determinant, inverse with residual validation, and eigenvalues."""
    # Determinant of [[1, 2], [3, 4]] = -2
    res_det = await MathematicalEngine.compute(
        MathProblemRequest(
            expression="det",
            domain=MathDomain.LINEAR_ALGEBRA,
            parameters={"sub_operation": "determinant", "matrix_a": [[1, 2], [3, 4]]},
        )
    )
    assert res_det.result == -2.0

    # Inverse with residual check
    res_inv = await MathematicalEngine.compute(
        MathProblemRequest(
            expression="inv",
            domain=MathDomain.LINEAR_ALGEBRA,
            parameters={"sub_operation": "inverse", "matrix_a": [[1, 2], [3, 4]]},
        )
    )
    assert res_inv.verification_status == MathVerificationStatus.RESIDUAL_VALIDATED
    assert res_inv.residual is not None and res_inv.residual < 1e-6

    # Solve Ax = b
    res_solve = await MathematicalEngine.compute(
        MathProblemRequest(
            expression="solve_sys",
            domain=MathDomain.LINEAR_ALGEBRA,
            parameters={"sub_operation": "solve_linear_system", "matrix_a": [[2, 1], [1, -1]], "vector_b": [8, 1]},
        )
    )
    assert abs(res_solve.result[0] - 3.0) < 1e-5
    assert abs(res_solve.result[1] - 2.0) < 1e-5


@pytest.mark.asyncio
async def test_domain_f_to_p_subsystems():
    """Verify remaining domains (Discrete, Probability, Statistics, Numerical, Info, Finance, Physics, ML, Signals, Logic)."""
    # Domain F: Combinatorics C(5, 2) = 10, P(5, 2) = 20
    res_comb = await MathematicalEngine.compute(
        MathProblemRequest(expression="comb", domain=MathDomain.DISCRETE_MATH, parameters={"sub_operation": "combinatorics", "n": 5, "k": 2})
    )
    assert res_comb.result["combinations"] == 10
    assert res_comb.result["permutations"] == 20

    # Domain G: Bayes theorem
    res_bayes = await MathematicalEngine.compute(
        MathProblemRequest(expression="bayes", domain=MathDomain.PROBABILITY, parameters={"sub_operation": "bayes", "p_b_given_a": 0.8, "p_a": 0.1, "p_b": 0.2})
    )
    assert abs(res_bayes.result - 0.4) < 1e-5

    # Domain H: Statistics
    res_stat = await MathematicalEngine.compute(
        MathProblemRequest(expression="stats", domain=MathDomain.STATISTICS, parameters={"sub_operation": "descriptive", "data": [2, 4, 4, 4, 5, 5, 7, 9]})
    )
    assert res_stat.result["mean"] == 5.0
    assert res_stat.result["median"] == 4.5

    # Domain I: Numerical methods (bisection root of x**2 - 2 in [1, 2] -> sqrt(2) ~ 1.4142)
    res_bisect = await MathematicalEngine.compute(
        MathProblemRequest(expression="x**2 - 2", domain=MathDomain.NUMERICAL_METHODS, parameters={"sub_operation": "bisection", "a": 1.0, "b": 2.0})
    )
    assert abs(res_bisect.result - 1.4142) < 0.001

    # Domain K: Shannon entropy (fair coin -> 1.0 bit)
    res_ent = await MathematicalEngine.compute(
        MathProblemRequest(expression="entropy", domain=MathDomain.INFORMATION_THEORY, parameters={"sub_operation": "entropy", "probabilities": [0.5, 0.5]})
    )
    assert abs(res_ent.result - 1.0) < 1e-5

    # Domain L: Financial compound interest ($1000 at 5% for 1 year compounded monthly)
    res_fin = await MathematicalEngine.compute(
        MathProblemRequest(expression="compound", domain=MathDomain.FINANCIAL_MATH, parameters={"sub_operation": "compound_interest", "principal": 1000, "rate": 0.05, "time_years": 1, "compound_frequency": 12})
    )
    assert res_fin.result["future_value"] == 1051.16

    # Domain M: Physics unit conversion (1000 m -> 1 km)
    res_phys = await MathematicalEngine.compute(
        MathProblemRequest(expression="unit", domain=MathDomain.PHYSICS_ENGINEERING, parameters={"sub_operation": "unit_conversion", "value": 1000, "from_unit": "m", "to_unit": "km"})
    )
    assert res_phys.result == 1.0

    # Domain N: Data Science ML classification metrics (TP=80, FP=20, FN=0, TN=100 -> Recall 1.0, Precision 0.8)
    res_ml = await MathematicalEngine.compute(
        MathProblemRequest(expression="metrics", domain=MathDomain.DATA_SCIENCE_ML, parameters={"sub_operation": "metrics", "tp": 80, "fp": 20, "fn": 0, "tn": 100})
    )
    assert res_ml.result["recall"] == 1.0
    assert res_ml.result["precision"] == 0.8

    # Domain O: Signals discrete convolution
    res_sig = await MathematicalEngine.compute(
        MathProblemRequest(expression="conv", domain=MathDomain.SIGNALS_TRANSFORMS, parameters={"sub_operation": "convolve", "sig1": [1, 2], "sig2": [3, 4]})
    )
    assert res_sig.result == [3.0, 10.0, 8.0]

    # Domain P: Logic truth analysis
    res_log = await MathematicalEngine.compute(
        MathProblemRequest(expression="p | ~p", domain=MathDomain.LOGIC_PROOFS)
    )
    assert res_log.result["is_tautology"] is True
