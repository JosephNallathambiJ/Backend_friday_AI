"""Security Policy Engine adapter unifying CapabilityManager, PolicyEngine, and Approvals."""

from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import PolicyOutcome
from app.security.policy import PolicyEngine
from app.services.approval_service import ApprovalService
from app.tools.registry import tool_registry


class UnifiedPolicyEvaluation(BaseModel):
    outcome: PolicyOutcome
    reason: str
    approval_request_id: str | None = None


class SecurityPolicyEngine:
    """Unified policy gateway enforcing capabilities, risk evaluation, and human approvals."""

    @classmethod
    async def evaluate(
        cls,
        tool_name: str,
        parameters: dict[str, Any],
        session: AsyncSession,
        user_id: str = "local_user",
        task_id: str | None = None,
    ) -> UnifiedPolicyEvaluation:
        tool = tool_registry.get(tool_name)
        if not tool:
            return UnifiedPolicyEvaluation(
                outcome=PolicyOutcome.DENY,
                reason=f"Tool '{tool_name}' is not registered or disabled.",
            )

        # Evaluate through core PolicyEngine
        eval_result = await PolicyEngine.evaluate_action(
            db=session,
            tool_name=tool_name,
            risk_level=tool.risk_level,
            required_capabilities=tool.required_capabilities,
            parameters=parameters,
            requires_approval=tool.requires_approval,
        )

        if eval_result.outcome == PolicyOutcome.REQUIRE_APPROVAL:
            approval = await ApprovalService.create_approval_request(
                session=session,
                task_id=task_id or "security_eval",
                tool_name=tool_name,
                action_description=f"Action '{tool_name}' requires security approval: {eval_result.reason}",
                risk_level=tool.risk_level,
                arguments=parameters,
            )
            return UnifiedPolicyEvaluation(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                reason=eval_result.reason,
                approval_request_id=approval.id,
            )

        return UnifiedPolicyEvaluation(
            outcome=eval_result.outcome,
            reason=eval_result.reason,
            approval_request_id=None,
        )
