"""Common specialist agent interface and schemas for FRIDAY AI."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SecurityPolicyError, ValidationError
from app.domain.enums import PolicyOutcome
from app.security.policy_engine import SecurityPolicyEngine
from app.tools.registry import tool_registry


class SpecialistExecutionResult(BaseModel):
    """Normalized output schema from a specialist agent."""

    agent_name: str
    task_id: str
    success: bool
    summary: str
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class BaseSpecialistAgent(ABC):
    """Base class for all specialist capabilities coordinated by the Central Brain."""

    agent_id: str
    name: str
    description: str
    supported_task_types: list[str]
    available_tool_names: list[str]
    required_capabilities: list[str] = []
    compatible_skills: list[str] = []
    input_schema: dict[str, Any] = {"type": "object", "properties": {"goal": {"type": "string"}}}
    output_schema: dict[str, Any] = {"type": "object", "properties": {"success": {"type": "boolean"}, "summary": {"type": "string"}}}
    timeout_seconds: int = 60
    budget_steps: int = 5

    def check_availability(self) -> dict[str, Any]:
        """Return live capability and tool availability status."""
        available_tools = [t for t in self.available_tool_names if tool_registry.get(t) is not None]
        return {
            "agent_id": getattr(self, "agent_id", self.name.lower().replace(" ", "_")),
            "name": self.name,
            "status": "available" if len(available_tools) > 0 or len(self.available_tool_names) == 0 else "degraded",
            "available_tools": available_tools,
            "total_tools": len(self.available_tool_names),
        }

    def health_status(self) -> dict[str, Any]:
        """Health diagnostics."""
        avail = self.check_availability()
        return {
            "healthy": avail["status"] in {"available", "degraded"},
            "status": avail["status"],
            "timeout_seconds": self.timeout_seconds,
            "budget_steps": self.budget_steps,
        }

    @abstractmethod
    async def execute(
        self,
        task_id: str,
        goal: str,
        parameters: dict[str, Any],
        session: AsyncSession,
        context: dict[str, Any] | None = None,
    ) -> SpecialistExecutionResult:
        """Execute delegated specialist work using registered tools under common policy."""
        pass

    async def execute_tool_safely(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        session: AsyncSession,
        user_id: str = "local_user",
    ) -> dict[str, Any]:
        """Execute a tool strictly through the common registry and policy engine."""
        if tool_name not in self.available_tool_names and tool_name not in tool_registry.list_tools():
            raise ValidationError(
                f"Tool '{tool_name}' is not allowed or registered for specialist '{self.name}'."
            )

        # 1. Enforce common policy engine
        policy_eval = await SecurityPolicyEngine.evaluate(
            tool_name=tool_name,
            parameters=parameters,
            session=session,
            user_id=user_id,
        )

        if policy_eval.outcome == PolicyOutcome.DENY:
            raise SecurityPolicyError(
                f"Policy denied execution of '{tool_name}' by specialist '{self.name}': {policy_eval.reason}"
            )

        if policy_eval.outcome == PolicyOutcome.REQUIRE_APPROVAL:
            return {
                "tool": tool_name,
                "status": "waiting_for_approval",
                "approval_id": policy_eval.approval_request_id,
                "summary": policy_eval.reason,
            }

        # 2. Execute through tool registry
        tool_result = await tool_registry.execute_tool(
            name=tool_name,
            parameters=parameters,
            session=session,
        )
        return {
            "tool": tool_name,
            "status": "success" if tool_result.success else "failed",
            "output": tool_result.data if tool_result.success else tool_result.error,
        }
