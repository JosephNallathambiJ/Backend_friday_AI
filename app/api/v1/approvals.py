"""Human-in-the-loop approval workflow API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse, ApprovalDecisionRequest, ApprovalRead
from app.services.approval_service import ApprovalService

router = APIRouter(
    prefix="/api/v1/approvals",
    tags=["Human Approval Workflow"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=APIResponse)
async def list_pending_approvals(db: AsyncSession = Depends(get_db)):
    """List all pending, unexpired tool approval requests."""
    approvals = await ApprovalService.list_pending(db)
    return APIResponse(
        data=[
            ApprovalRead(
                id=a.id,
                task_id=a.task_id,
                tool_name=a.tool_name,
                action_description=a.action_description,
                risk_level=a.risk_level,
                arguments_redacted=a.arguments_redacted,
                status=a.status,
                created_at=a.created_at,
                expires_at=a.expires_at,
                decision_reason=a.decision_reason,
            )
            for a in approvals
        ]
    )


@router.get("/{approval_id}", response_model=APIResponse)
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
):
    a = await ApprovalService.get_approval(db, approval_id)
    return APIResponse(
        data=ApprovalRead(
            id=a.id,
            task_id=a.task_id,
            tool_name=a.tool_name,
            action_description=a.action_description,
            risk_level=a.risk_level,
            arguments_redacted=a.arguments_redacted,
            status=a.status,
            created_at=a.created_at,
            expires_at=a.expires_at,
            decision_reason=a.decision_reason,
        )
    )


@router.post("/{approval_id}/decision", response_model=APIResponse)
async def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a pending approval request."""
    a = await ApprovalService.decide_approval(
        session=db,
        approval_id=approval_id,
        decision=payload.decision,
        reason=payload.reason,
    )
    return APIResponse(
        data=ApprovalRead(
            id=a.id,
            task_id=a.task_id,
            tool_name=a.tool_name,
            action_description=a.action_description,
            risk_level=a.risk_level,
            arguments_redacted=a.arguments_redacted,
            status=a.status,
            created_at=a.created_at,
            expires_at=a.expires_at,
            decision_reason=a.decision_reason,
        )
    )
