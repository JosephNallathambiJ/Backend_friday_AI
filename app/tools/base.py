"""Base tool contract and execution context."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import ToolRiskLevel


class ToolResult(BaseModel):
    success: bool
    data: Any | None = None
    error: str | None = None
    execution_time_ms: int = 0
    dry_run: bool = False
    audit_metadata: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract contract for all FRIDAY backend tools according to Master Prompt 2."""

    name: str
    description: str
    input_schema: type[BaseModel] | dict[str, Any] = dict
    output_schema: type[BaseModel] | dict[str, Any] = ToolResult
    required_capabilities: list[str] = []
    risk_level: ToolRiskLevel = ToolRiskLevel.READ_ONLY
    requires_approval: bool = False
    supports_dry_run: bool = True
    timeout_seconds: int = 30
    idempotent: bool = True

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate input parameters against input_schema."""
        if isinstance(self.input_schema, type) and issubclass(self.input_schema, BaseModel):
            validated = self.input_schema.model_validate(parameters)
            return validated.model_dump()
        return parameters

    def audit_metadata(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Extract sanitized metadata for security audit logging."""
        return {"tool_name": self.name, "parameters_count": len(parameters)}

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """Backward-compatible JSON schema for LLM tool calling."""
        if isinstance(self.input_schema, type) and issubclass(self.input_schema, BaseModel):
            return self.input_schema.model_json_schema()
        if isinstance(self.input_schema, dict):
            return self.input_schema
        return {"type": "object", "properties": {}}

    @abstractmethod
    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        """Execute the tool with given validated parameters."""
        pass
