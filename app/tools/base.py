"""Base tool contract and execution context."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.domain.enums import ToolRiskLevel


class ToolResult(BaseModel):
    success: bool
    data: Any | None = None
    error: str | None = None
    execution_time_ms: int = 0
    dry_run: bool = False


class BaseTool(ABC):
    """Abstract contract for all FRIDAY backend tools."""

    name: str
    description: str
    risk_level: ToolRiskLevel
    requires_approval: bool = False
    parameters_schema: dict[str, Any]

    @abstractmethod
    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
