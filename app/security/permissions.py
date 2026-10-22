"""Permission and Capability Manager for FRIDAY AI.

Controls fine-grained capability grants and revocations with scope enforcement.
"""

from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.models.capability import CapabilityGrant
from app.domain.enums import CapabilityType, ScopeType

# Registry of all known capabilities with human-readable descriptions
CAPABILITY_DEFINITIONS: dict[str, dict[str, Any]] = {
    CapabilityType.SYSTEM_INFO_READ.value: {
        "description": "Read basic operating system and device information",
        "default_granted": True,
    },
    CapabilityType.FILESYSTEM_READ.value: {
        "description": "Read and search files inside approved directories",
        "default_granted": True,
    },
    CapabilityType.FILESYSTEM_WRITE.value: {
        "description": "Create and edit files inside approved directories",
        "default_granted": True,
    },
    CapabilityType.FILESYSTEM_DELETE.value: {
        "description": "Delete files inside approved directories via trash/recoverable strategy",
        "default_granted": False,
    },
    CapabilityType.PROCESS_EXECUTE.value: {
        "description": "Run controlled development and system commands",
        "default_granted": True,
    },
    CapabilityType.BROWSER_NAVIGATE.value: {
        "description": "Navigate to external websites via isolated browser",
        "default_granted": True,
    },
    CapabilityType.BROWSER_READ.value: {
        "description": "Read text and extract links from webpages",
        "default_granted": True,
    },
    CapabilityType.BROWSER_INTERACT.value: {
        "description": "Click, fill, and interact with website forms",
        "default_granted": False,
    },
    CapabilityType.CONTACTS_READ.value: {
        "description": "Search and view permitted device contacts",
        "default_granted": True,
    },
    CapabilityType.CONTACTS_WRITE.value: {
        "description": "Create, edit, or delete contacts in authorized provider",
        "default_granted": False,
    },
    CapabilityType.NOTIFICATIONS_SEND.value: {
        "description": "Send local operating system notifications",
        "default_granted": True,
    },
    CapabilityType.APPLICATIONS_LAUNCH.value: {
        "description": "Launch explicitly approved local applications",
        "default_granted": True,
    },
    CapabilityType.NETWORK_FETCH.value: {
        "description": "Perform HTTP GET requests to public web resources",
        "default_granted": True,
    },
    CapabilityType.SCHEDULED_TASKS_MANAGE.value: {
        "description": "Create and modify background recurring jobs",
        "default_granted": True,
    },
}


class CapabilityManager:
    """Manages explicit user-granted capabilities, scopes, and revocations."""

    @staticmethod
    async def is_capability_granted(
        db: AsyncSession,
        capability: str,
        scope_type: str = ScopeType.GLOBAL.value,
        scope_value: str = "*",
    ) -> bool:
        """Check if a capability is currently granted for the requested scope.

        Evaluates explicit DB grants/revocations first; falls back to default_granted.
        """
        stmt = (
            select(CapabilityGrant)
            .where(CapabilityGrant.capability == capability)
            .order_by(CapabilityGrant.created_at.desc())
        )
        result = await db.execute(stmt)
        grants = result.scalars().all()

        if grants:
            for grant in grants:
                if not grant.is_granted or grant.revoked_at is not None:
                    # Explicit revocation takes precedence
                    return False
                if grant.scope_value == "*" or grant.scope_value == scope_value:
                    return True
            return False

        # Fall back to definition default
        cap_info = CAPABILITY_DEFINITIONS.get(capability)
        if cap_info:
            return bool(cap_info.get("default_granted", False))
        return False

    @staticmethod
    async def grant_capability(
        db: AsyncSession,
        capability: str,
        scope_type: str = ScopeType.GLOBAL.value,
        scope_value: str = "*",
        granted_by: str = "user",
    ) -> CapabilityGrant:
        """Explicitly grant a capability for a specified scope."""
        # Check if existing active grant exists
        stmt = select(CapabilityGrant).where(
            and_(
                CapabilityGrant.capability == capability,
                CapabilityGrant.scope_type == scope_type,
                CapabilityGrant.scope_value == scope_value,
                CapabilityGrant.revoked_at.is_(None),
            )
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            existing.is_granted = True
            await db.commit()
            await db.refresh(existing)
            return existing

        grant = CapabilityGrant(
            capability=capability,
            scope_type=scope_type,
            scope_value=scope_value,
            is_granted=True,
            granted_by=granted_by,
        )
        db.add(grant)
        await db.commit()
        await db.refresh(grant)
        return grant

    @staticmethod
    async def revoke_capability(
        db: AsyncSession,
        capability: str,
        scope_type: str = ScopeType.GLOBAL.value,
        scope_value: str = "*",
    ) -> bool:
        """Explicitly revoke a capability."""
        stmt = select(CapabilityGrant).where(
            and_(
                CapabilityGrant.capability == capability,
                CapabilityGrant.scope_type == scope_type,
                CapabilityGrant.scope_value == scope_value,
                CapabilityGrant.revoked_at.is_(None),
            )
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            existing.is_granted = False
            existing.revoked_at = utc_now()
            await db.commit()
            return True

        # Record explicit negative grant (revocation record)
        revocation = CapabilityGrant(
            capability=capability,
            scope_type=scope_type,
            scope_value=scope_value,
            is_granted=False,
            granted_by="user",
            revoked_at=utc_now(),
        )
        db.add(revocation)
        await db.commit()
        return True

    @staticmethod
    async def list_capabilities_status(db: AsyncSession) -> list[dict[str, Any]]:
        """List all capabilities with their active status and scopes."""
        stmt = select(CapabilityGrant).where(CapabilityGrant.revoked_at.is_(None))
        active_grants = (await db.execute(stmt)).scalars().all()
        grants_by_cap: dict[str, list[CapabilityGrant]] = {}
        for g in active_grants:
            grants_by_cap.setdefault(g.capability, []).append(g)

        result = []
        for cap, info in CAPABILITY_DEFINITIONS.items():
            grants = grants_by_cap.get(cap, [])
            if grants:
                is_granted = any(g.is_granted for g in grants)
                scopes = [f"{g.scope_type}:{g.scope_value}" for g in grants if g.is_granted]
            else:
                is_granted = bool(info.get("default_granted", False))
                scopes = ["global:*"] if is_granted else []

            result.append(
                {
                    "capability": cap,
                    "description": info["description"],
                    "is_granted": is_granted,
                    "scopes": scopes,
                }
            )
        return result
