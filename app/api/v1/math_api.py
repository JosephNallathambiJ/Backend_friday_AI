"""API endpoints for the FRIDAY Mathematical Engine."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.enums import MathDomain
from app.math.engine import MathematicalEngine
from app.math.models import MathProblemRequest, MathResult

router = APIRouter(prefix="/api/v1/math", tags=["mathematics"])


class MathCalculateRequest(BaseModel):
    expression: str = Field(..., description="Mathematical expression, e.g. '2 + 2', 'sqrt(16) * 5', '2/3 + 5/7'.")
    precision: int = Field(default=10, ge=1, le=50)
    exact: bool = Field(default=True)


class MathSolveRequest(BaseModel):
    equation: str = Field(..., description="Equation f(x) = 0 or expression, e.g. 'x**2 - 9'.")
    variable: str = Field(default="x")


class MathMatrixRequest(BaseModel):
    operation: str = Field(default="determinant", description="determinant, inverse, eigenvalues, matrix_multiply, solve_linear_system.")
    matrix_a: list[list[float]]
    matrix_b: list[list[float]] | None = None
    vector_b: list[float] | None = None


class MathStatisticsRequest(BaseModel):
    data: list[float]
    operation: str = Field(default="descriptive", description="descriptive, regression.")
    data_y: list[float] | None = None


@router.post("/calculate", response_model=MathResult)
async def calculate_expression(req: MathCalculateRequest) -> MathResult:
    """Perform deterministic arithmetic, power, root, and elementary function calculations."""
    return await MathematicalEngine.compute(
        MathProblemRequest(
            expression=req.expression,
            precision=req.precision,
            exact=req.exact,
        )
    )


@router.post("/solve", response_model=MathResult)
async def solve_algebraic_equation(req: MathSolveRequest) -> MathResult:
    """Solve analytical equations with residual substitution verification."""
    return await MathematicalEngine.compute(
        MathProblemRequest(
            expression=req.equation,
            operation="solve",
            domain=MathDomain.ALGEBRA,
            parameters={"variable": req.variable},
        )
    )


@router.post("/matrix", response_model=MathResult)
async def compute_matrix_algebra(req: MathMatrixRequest) -> MathResult:
    """Execute matrix linear algebra computations."""
    params: dict[str, Any] = {
        "sub_operation": req.operation,
        "matrix_a": req.matrix_a,
    }
    if req.matrix_b:
        params["matrix_b"] = req.matrix_b
    if req.vector_b:
        params["vector_b"] = req.vector_b
    return await MathematicalEngine.compute(
        MathProblemRequest(
            expression=f"matrix_{req.operation}",
            operation=req.operation,
            domain=MathDomain.LINEAR_ALGEBRA,
            parameters=params,
        )
    )


@router.post("/statistics", response_model=MathResult)
async def analyze_data_statistics(req: MathStatisticsRequest) -> MathResult:
    """Compute descriptive sample statistics and linear regressions."""
    params: dict[str, Any] = {
        "sub_operation": req.operation,
        "data": req.data,
    }
    if req.data_y:
        params["data_y"] = req.data_y
    return await MathematicalEngine.compute(
        MathProblemRequest(
            expression=f"statistics_{req.operation}",
            operation=req.operation,
            domain=MathDomain.STATISTICS,
            parameters=params,
        )
    )


@router.get("/domains")
async def list_mathematical_domains() -> dict[str, Any]:
    """List all 16 supported mathematical domains and their capability status."""
    return {
        "domains_count": len(MathDomain),
        "supported_domains": [
            {"id": "arithmetic", "name": "Arithmetic and Number Systems", "status": "AVAILABLE", "exact": True},
            {"id": "algebra", "name": "Algebra & Symbolic Simplification", "status": "AVAILABLE", "exact": True},
            {"id": "geometry", "name": "Geometry and Trigonometry", "status": "AVAILABLE", "exact": True},
            {"id": "calculus", "name": "Calculus (Derivatives & Integrals)", "status": "AVAILABLE", "exact": True},
            {"id": "linear_algebra", "name": "Linear Algebra & Matrices", "status": "AVAILABLE", "exact": True},
            {"id": "discrete_math", "name": "Discrete Mathematics & Combinatorics", "status": "AVAILABLE", "exact": True},
            {"id": "probability", "name": "Probability & Bayes Theorem", "status": "AVAILABLE", "exact": False},
            {"id": "statistics", "name": "Sample Statistics & Regression", "status": "AVAILABLE", "exact": False},
            {"id": "numerical_methods", "name": "Numerical Root Finding & Integration", "status": "AVAILABLE", "exact": False},
            {"id": "optimization", "name": "Optimization & Operations Research", "status": "AVAILABLE", "exact": False},
            {"id": "information_theory", "name": "Information Theory & Modular Math", "status": "AVAILABLE", "exact": True},
            {"id": "financial_math", "name": "Financial & Business Mathematics", "status": "AVAILABLE", "exact": False},
            {"id": "physics_engineering", "name": "Physics & Engineering Unit Conversions", "status": "AVAILABLE", "exact": True},
            {"id": "data_science_ml", "name": "Data Science & Machine Learning Metrics", "status": "AVAILABLE", "exact": False},
            {"id": "signals_transforms", "name": "Signals & Discrete Transforms (FFT)", "status": "AVAILABLE", "exact": False},
            {"id": "logic_proofs", "name": "Logic & Symbolic Proof Verification", "status": "AVAILABLE", "exact": True},
        ],
    }
