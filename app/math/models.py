"""Typed data models and result contracts for the FRIDAY Mathematical Engine."""

from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import MathComputationStatus, MathDomain, MathVerificationStatus


class MathProblemRequest(BaseModel):
    """Input contract for mathematical requests."""

    expression: str = Field(..., description="Mathematical expression, equation, or command.")
    operation: str = Field(
        default="calculate",
        description="Operation: calculate, simplify, solve, differentiate, integrate, matrix, statistics, etc.",
    )
    domain: MathDomain | None = Field(default=None, description="Target domain if specified.")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific parameters (e.g. variable, limits, matrix data, initial guess).",
    )
    precision: int = Field(default=10, ge=1, le=50, description="Significant digits for approximate results.")
    exact: bool = Field(default=True, description="Attempt exact symbolic/rational result before approximation.")
    units: str | None = Field(default=None, description="Optional expected or input units.")
    timeout_seconds: float = Field(default=10.0, ge=0.1, le=60.0, description="Execution timeout.")


class MathResult(BaseModel):
    """Structured result contract for verified mathematical computations."""

    original_problem: str
    normalized_expression: str
    selected_domain: MathDomain
    selected_method: str
    result: Any
    exact_result: str | None = None
    approximate_result: float | str | None = None
    precision: int | None = None
    units: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    computation_status: MathComputationStatus = MathComputationStatus.EXACT
    verification_status: MathVerificationStatus = MathVerificationStatus.UNVERIFIED
    method_description: str
    error_details: str | None = None
    execution_time_ms: float = 0.0
    residual: float | None = None
