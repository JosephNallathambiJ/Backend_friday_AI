"""Audit logging service for security-relevant operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.audit import AuditEvent
from app.security.redaction import redact_dictionary


async def log_audit_event(
    session: AsyncSession,
    event_type: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    status: str = "success",
    actor: str = "system",
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Record an immutable audit event in the database and structured logger."""
    redacted_details = redact_dictionary(details or {})

    event = AuditEvent(
        event_type=event_type,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        status=status,
        details_redacted=redacted_details,
    )
    session.add(event)
    await session.commit()

    logger.info(
        f"[AUDIT] {event_type} - {action} on {resource_type}:{resource_id or 'none'} -> {status}"
    )
    return event
