"""Approval request management and state transitions."""

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, SecurityPolicyError
from app.core.time import utc_now
from app.db.models.approval import ApprovalRequest
from app.domain.enums import ApprovalStatus, ToolRiskLevel
from app.security.redaction import redact_dictionary


class ApprovalService:
    @staticmethod
    async def create_approval_request(
        session: AsyncSession,
        task_id: str,
        tool_name: str,
        action_description: str,
        risk_level: ToolRiskLevel,
        arguments: dict[str, Any],
        expires_in_minutes: int = 15,
    ) -> ApprovalRequest:
        redacted = redact_dictionary(arguments)
        expires_at = utc_now() + timedelta(minutes=expires_in_minutes)

        approval = ApprovalRequest(
            task_id=task_id,
            tool_name=tool_name,
            action_description=action_description,
            risk_level=risk_level,
            arguments_redacted=redacted,
            raw_arguments=arguments,
            status=ApprovalStatus.PENDING,
            expires_at=expires_at,
        )
        session.add(approval)
        await session.commit()
        await session.refresh(approval)
        return approval

    @staticmethod
    async def get_approval(session: AsyncSession, approval_id: str) -> ApprovalRequest:
        result = await session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        approval = result.scalars().first()
        if not approval:
            raise NotFoundError(f"Approval request '{approval_id}' not found.")
        return approval

    @staticmethod
    async def list_pending(session: AsyncSession) -> list[ApprovalRequest]:
        now = utc_now()
        stmt = (
            select(ApprovalRequest)
            .where(
                ApprovalRequest.status == ApprovalStatus.PENDING,
                ApprovalRequest.expires_at > now,
            )
            .order_by(ApprovalRequest.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def decide_approval(
        session: AsyncSession,
        approval_id: str,
        decision: ApprovalStatus,
        reason: str | None = None,
    ) -> ApprovalRequest:
        approval = await ApprovalService.get_approval(session, approval_id)

        # Check expiration
        if utc_now() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            await session.commit()
            raise SecurityPolicyError(f"Approval request '{approval_id}' has expired.")

        if approval.status != ApprovalStatus.PENDING:
            raise SecurityPolicyError(
                f"Cannot decide approval: current status is '{approval.status}', must be 'pending'."
            )

        if decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise SecurityPolicyError(
                f"Invalid approval decision '{decision}'. Must be approved or rejected."
            )

        approval.status = decision
        approval.decision_reason = reason
        approval.decision_time = utc_now()
        await session.commit()
        await session.refresh(approval)
        return approval
