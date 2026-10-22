"""Policy Engine for FRIDAY AI.

Decides whether a tool operation is ALLOWED, REQUIRES_APPROVAL, or is DENIED.
Integrates CapabilityManager, PathValidator, and CommandPolicy.
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import PolicyOutcome, ToolRiskLevel
from app.security.permissions import CapabilityManager


class PolicyEvaluationResult(BaseModel):
    outcome: PolicyOutcome
    reason: str
    required_capabilities: list[str]
    missing_capabilities: list[str] = []
    requires_approval: bool = False


class PolicyEngine:
    """Evaluates requested tool actions against system policy and user grants."""

    @staticmethod
    async def evaluate_action(
        db: AsyncSession,
        tool_name: str,
        risk_level: ToolRiskLevel,
        required_capabilities: list[str],
        parameters: dict[str, Any],
        requires_approval: bool = False,
        scope_type: str = "global",
        scope_value: str = "*",
    ) -> PolicyEvaluationResult:
        """Evaluate a tool action and return ALLOW, REQUIRE_APPROVAL, or DENY."""
        missing = []

        # 1. Capability Verification
        for cap in required_capabilities:
            granted = await CapabilityManager.is_capability_granted(
                db, capability=cap, scope_type=scope_type, scope_value=scope_value
            )
            if not granted:
                missing.append(cap)

        if missing:
            return PolicyEvaluationResult(
                outcome=PolicyOutcome.DENY,
                reason=f"Action denied: missing required capabilities: {', '.join(missing)}",
                required_capabilities=required_capabilities,
                missing_capabilities=missing,
                requires_approval=False,
            )

        # 2. If tool inherently requires approval or is DESTRUCTIVE
        if requires_approval or risk_level == ToolRiskLevel.DESTRUCTIVE:
            return PolicyEvaluationResult(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                reason=f"Action '{tool_name}' requires explicit human approval before execution.",
                required_capabilities=required_capabilities,
                requires_approval=True,
            )

        # 3. High impact operations (e.g. process execution or file deletion) require approval
        if "filesystem.delete" in required_capabilities:
            return PolicyEvaluationResult(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                reason=f"Deletion operation via '{tool_name}' requires human approval.",
                required_capabilities=required_capabilities,
                requires_approval=True,
            )

        if "process.execute" in required_capabilities:
            # Check if command has consequential arguments or mutations
            command_str = str(parameters.get("command", "")).lower()
            if any(mut in command_str for mut in ["install", "build", "commit", "push", "deploy"]):
                return PolicyEvaluationResult(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    reason=f"Command '{command_str}' has meaningful side effects and requires approval.",
                    required_capabilities=required_capabilities,
                    requires_approval=True,
                )

        if "browser.interact" in required_capabilities:
            action = str(parameters.get("action", "")).lower()
            if action in ["submit", "purchase", "delete", "post"]:
                return PolicyEvaluationResult(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    reason=f"Browser action '{action}' modifies remote state and requires human approval.",
                    required_capabilities=required_capabilities,
                    requires_approval=True,
                )

        if "contacts.write" in required_capabilities:
            action = str(parameters.get("action", "")).lower()
            if action in ["delete", "bulk_update"]:
                return PolicyEvaluationResult(
                    outcome=PolicyOutcome.REQUIRE_APPROVAL,
                    reason=f"Contacts action '{action}' requires explicit approval.",
                    required_capabilities=required_capabilities,
                    requires_approval=True,
                )

        # Safe read-only or authorized local mutation
        return PolicyEvaluationResult(
            outcome=PolicyOutcome.ALLOW,
            reason="Action permitted by policy and authorized capabilities.",
            required_capabilities=required_capabilities,
            requires_approval=False,
        )
