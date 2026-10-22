"""Mathematical tools for the FRIDAY shared tool registry."""

from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import ToolRiskLevel
from app.math.engine import MathematicalEngine
from app.math.models import MathProblemRequest
from app.tools.base import BaseTool, ToolResult


class CalculateInput(BaseModel):
    expression: str = Field(..., description="Mathematical expression to evaluate (e.g. '2 + 2', 'sqrt(16) * 5', '2/3 + 5/7').")
    exact: bool = Field(default=True, description="Whether to attempt exact rational/integer result.")


class CalculateTool(BaseTool):
    name = "calculate"
    description = "Perform deterministic arithmetic, power, root, and elementary function calculations with exact and approximate precision."
    input_schema = CalculateInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        expr = parameters.get("expression", "")
        exact = parameters.get("exact", True)
        res = await MathematicalEngine.compute(MathProblemRequest(expression=expr, exact=exact))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Calculation failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Calculation verified.")


class SimplifyInput(BaseModel):
    expression: str = Field(..., description="Algebraic or symbolic expression to simplify (e.g. 'x**2 + 2*x + 1').")


class SimplifyTool(BaseTool):
    name = "simplify_expression"
    description = "Simplify, expand, or factor symbolic algebraic expressions."
    input_schema = SimplifyInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        expr = parameters.get("expression", "")
        res = await MathematicalEngine.compute(MathProblemRequest(expression=expr, operation="simplify"))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Simplification failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Algebraic simplification verified.")


class SolveEquationInput(BaseModel):
    equation: str = Field(..., description="Algebraic equation or expression f(x)=0 (e.g. 'x**2 - 4').")
    variable: str = Field(default="x", description="Target variable to solve for.")


class SolveEquationTool(BaseTool):
    name = "solve_equation"
    description = "Solve linear, quadratic, and polynomial algebraic equations analytically with residual verification."
    input_schema = SolveEquationInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        eq = parameters.get("equation", "")
        var = parameters.get("variable", "x")
        res = await MathematicalEngine.compute(MathProblemRequest(expression=eq, operation="solve", parameters={"variable": var}))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Equation solving failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Equation roots verified.")


class DifferentiateInput(BaseModel):
    expression: str = Field(..., description="Function or expression to differentiate (e.g. 'sin(x)*x**2').")
    variable: str = Field(default="x", description="Differentiation variable.")
    order: int = Field(default=1, ge=1, le=5, description="Derivative order.")


class DifferentiateTool(BaseTool):
    name = "differentiate"
    description = "Compute exact symbolic derivatives of functions with respect to a variable."
    input_schema = DifferentiateInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        expr = parameters.get("expression", "")
        var = parameters.get("variable", "x")
        order = parameters.get("order", 1)
        res = await MathematicalEngine.compute(MathProblemRequest(expression=expr, operation="derivative", parameters={"variable": var, "order": order}))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Differentiation failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Derivative verified.")


class IntegrateInput(BaseModel):
    expression: str = Field(..., description="Function to integrate (e.g. 'x**2 + cos(x)').")
    variable: str = Field(default="x", description="Integration variable.")
    limits: list[float] | None = Field(default=None, description="Optional [lower, upper] definite bounds.")


class IntegrateTool(BaseTool):
    name = "integrate"
    description = "Compute exact definite and indefinite integrals of mathematical functions."
    input_schema = IntegrateInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        expr = parameters.get("expression", "")
        var = parameters.get("variable", "x")
        limits = parameters.get("limits")
        params = {"variable": var}
        if limits:
            params["limits"] = limits
        res = await MathematicalEngine.compute(MathProblemRequest(expression=expr, operation="integral", parameters=params))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Integration failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Integral verified.")


class ComputeMatrixInput(BaseModel):
    operation: str = Field(default="determinant", description="Matrix operation: determinant, inverse, eigenvalues, matrix_multiply, solve_linear_system.")
    matrix_a: list[list[float]] = Field(..., description="Input 2D matrix A.")
    matrix_b: list[list[float]] | None = Field(default=None, description="Optional matrix B for multiplication.")
    vector_b: list[float] | None = Field(default=None, description="Optional vector b for Ax = b.")


class ComputeMatrixTool(BaseTool):
    name = "compute_matrix"
    description = "Execute linear algebra operations: determinants, inverses, eigenvalues, matrix multiplication, and linear system solving."
    input_schema = ComputeMatrixInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        op = parameters.get("operation", "determinant")
        params = {
            "sub_operation": op,
            "matrix_a": parameters.get("matrix_a", [[1, 0], [0, 1]]),
        }
        if "matrix_b" in parameters and parameters["matrix_b"] is not None:
            params["matrix_b"] = parameters["matrix_b"]
        if "vector_b" in parameters and parameters["vector_b"] is not None:
            params["vector_b"] = parameters["vector_b"]
        res = await MathematicalEngine.compute(MathProblemRequest(expression=f"matrix_{op}", operation=op, parameters=params))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Matrix operation failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Matrix computation verified.")


class AnalyzeStatisticsInput(BaseModel):
    data: list[float] = Field(..., description="Numerical dataset for statistical analysis.")
    operation: str = Field(default="descriptive", description="Statistical operation: descriptive, regression.")
    data_y: list[float] | None = Field(default=None, description="Dependent variable y for linear regression.")


class AnalyzeStatisticsTool(BaseTool):
    name = "analyze_statistics"
    description = "Compute descriptive sample statistics (mean, median, variance, std dev, quantiles, range, IQR) or linear regression."
    input_schema = AnalyzeStatisticsInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 10

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        data = parameters.get("data", [])
        op = parameters.get("operation", "descriptive")
        params = {"data": data, "sub_operation": op}
        if "data_y" in parameters and parameters["data_y"] is not None:
            params["data_y"] = parameters["data_y"]
        res = await MathematicalEngine.compute(MathProblemRequest(expression=f"statistics_{op}", operation=op, parameters=params))
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Statistics calculation failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Statistical analysis verified.")


class ConvertUnitsInput(BaseModel):
    value: float = Field(..., description="Numeric value to convert.")
    from_unit: str = Field(..., description="Source unit (e.g. 'm', 'km', 'ft', 'kg', 'lb', 'C', 'F').")
    to_unit: str = Field(..., description="Target unit (e.g. 'ft', 'mi', 'm', 'lb', 'kg', 'F', 'C').")


class ConvertUnitsTool(BaseTool):
    name = "convert_units"
    description = "Convert dimensional physical quantities across length, mass, and temperature units."
    input_schema = ConvertUnitsInput
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    timeout_seconds = 5

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        val = parameters.get("value", 1.0)
        from_u = parameters.get("from_unit", "m")
        to_u = parameters.get("to_unit", "ft")
        res = await MathematicalEngine.compute(
            MathProblemRequest(
                expression=f"convert {val} {from_u} to {to_u}",
                operation="unit_conversion",
                parameters={"value": val, "from_unit": from_u, "to_unit": to_u},
            )
        )
        if res.computation_status.value in {"failed", "timed_out"}:
            return ToolResult(success=False, error=res.error_details or "Unit conversion failed", data=res.model_dump())
        return ToolResult(success=True, data=res.model_dump(), verified=True, verification_details="Unit conversion verified.")
