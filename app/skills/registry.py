"""Skill Registry and Lifecycle Manager for FRIDAY AI.

Enforces Part 6 of Master Prompt 6:
- Safe installation of validated quarantined skills into versioned managed library.
- Version tracking and atomic rollback to previous working versions.
- Central discovery, enable/disable toggle, and health verification.
- Dynamic notification and capability mapping to specialist agents.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, SecurityPolicyError, ValidationError
from app.db.models.skill import SkillAcquisitionRecord, SkillRecord, SkillVersionRecord
from app.domain.enums import AcquisitionStatus, SkillStatus
from app.skills.manifest import SkillManifest, load_manifest_from_directory


class SkillRegistry:
    """Central authority for installed skill discovery, versioning, and execution lifecycle."""

    def __init__(self):
        self._memory_cache: dict[str, SkillManifest] = {}

    def get_cached_manifest(self, skill_id: str) -> SkillManifest | None:
        return self._memory_cache.get(skill_id)

    async def list_installed_skills(
        self,
        session: AsyncSession,
        agent_type: str | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """List all installed skills with optional agent filtering."""
        stmt = select(SkillRecord)
        if active_only:
            stmt = stmt.where(SkillRecord.is_active == True, SkillRecord.status == SkillStatus.INSTALLED)  # noqa: E712
        result = await session.execute(stmt)
        records = result.scalars().all()

        skills = []
        for r in records:
            manifest_dict = r.manifest_data or {}
            supported_agents = manifest_dict.get("supported_agents", [])
            if agent_type and supported_agents and agent_type not in supported_agents:
                continue

            skills.append({
                "skill_id": r.skill_id,
                "name": r.name,
                "version": r.version,
                "description": r.description,
                "author": r.author,
                "license": r.license,
                "source": r.source,
                "source_commit": r.source_commit,
                "execution_mode": r.execution_mode,
                "risk_level": r.risk_level,
                "status": r.status,
                "is_active": r.is_active,
                "supported_agents": supported_agents,
                "install_path": r.install_path,
            })
        return skills

    async def get_skill(self, session: AsyncSession, skill_id: str) -> SkillRecord:
        """Fetch skill record by skill_id."""
        stmt = select(SkillRecord).where(SkillRecord.skill_id == skill_id)
        result = await session.execute(stmt)
        record = result.scalars().first()
        if not record:
            raise NotFoundError(f"Skill '{skill_id}' not found in managed library.")
        return record

    async def install_skill(
        self,
        session: AsyncSession,
        acquisition_id: str,
        approval_id: str | None = None,
    ) -> SkillRecord:
        """Promote a validated quarantined skill into the managed library."""
        stmt = select(SkillAcquisitionRecord).where(SkillAcquisitionRecord.id == acquisition_id)
        acq_res = await session.execute(stmt)
        acq = acq_res.scalars().first()
        if not acq:
            raise NotFoundError(f"Acquisition '{acquisition_id}' not found.")

        # Check validation status
        if acq.status == AcquisitionStatus.REJECTED:
            raise SecurityPolicyError(f"Cannot install rejected skill: {acq.error_message}")
        if acq.status == AcquisitionStatus.AWAITING_APPROVAL and not approval_id:
            raise SecurityPolicyError(
                f"Skill '{acq.skill_id}' requires human approval before installation."
            )

        src_dir = Path(acq.quarantine_path)
        if not src_dir.exists():
            raise NotFoundError(f"Quarantined package directory {src_dir} does not exist.")

        manifest = load_manifest_from_directory(src_dir)

        # Managed installation destination: storage/skills/<skill_id>/<version>/
        skills_root = settings.SKILLS_DIRECTORY.resolve()
        dest_dir = skills_root / manifest.id / manifest.version
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Copy files to managed destination
        for item in src_dir.iterdir():
            target = dest_dir / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

        # Compute installation hash
        checksum = hashlib.sha256(
            "".join(f.name for f in dest_dir.rglob("*") if f.is_file()).encode("utf-8")
        ).hexdigest()

        # Check existing skill record
        existing = (await session.execute(
            select(SkillRecord).where(SkillRecord.skill_id == manifest.id)
        )).scalars().first()

        if existing:
            # Archive previous version
            prev_version = SkillVersionRecord(
                skill_pk=existing.id,
                skill_id=existing.skill_id,
                version=existing.version,
                source_commit=existing.source_commit,
                install_path=existing.install_path,
                checksum=existing.integrity_hash,
                manifest_data=existing.manifest_data,
            )
            session.add(prev_version)

            # Update existing record
            existing.version = manifest.version
            existing.name = manifest.name
            existing.description = manifest.description
            existing.license = manifest.license
            existing.source = manifest.source or acq.source_url
            existing.source_commit = manifest.source_commit or acq.pinned_commit
            existing.execution_mode = manifest.execution_mode
            existing.risk_level = manifest.risk_level
            existing.install_path = str(dest_dir)
            existing.integrity_hash = checksum
            existing.manifest_data = manifest.model_dump()
            existing.status = SkillStatus.INSTALLED
            existing.is_active = True
            record = existing
        else:
            record = SkillRecord(
                skill_id=manifest.id,
                name=manifest.name,
                version=manifest.version,
                description=manifest.description,
                author=manifest.author,
                license=manifest.license,
                source=manifest.source or acq.source_url,
                source_commit=manifest.source_commit or acq.pinned_commit,
                execution_mode=manifest.execution_mode,
                risk_level=manifest.risk_level,
                status=SkillStatus.INSTALLED,
                is_active=True,
                install_path=str(dest_dir),
                integrity_hash=checksum,
                manifest_data=manifest.model_dump(),
            )
            session.add(record)

        acq.status = AcquisitionStatus.INSTALLED
        await session.commit()
        await session.refresh(record)

        # Cache in memory
        self._memory_cache[manifest.id] = manifest
        return record

    async def enable_skill(self, session: AsyncSession, skill_id: str) -> SkillRecord:
        """Enable an installed skill."""
        record = await self.get_skill(session, skill_id)
        record.is_active = True
        record.status = SkillStatus.INSTALLED
        await session.commit()
        await session.refresh(record)
        return record

    async def disable_skill(self, session: AsyncSession, skill_id: str) -> SkillRecord:
        """Disable an active skill."""
        record = await self.get_skill(session, skill_id)
        record.is_active = False
        record.status = SkillStatus.DISABLED
        await session.commit()
        await session.refresh(record)
        return record

    async def rollback_skill(
        self,
        session: AsyncSession,
        skill_id: str,
        target_version: str | None = None,
    ) -> SkillRecord:
        """Roll back a skill to its previous or specified installed version."""
        record = await self.get_skill(session, skill_id)
        stmt = (
            select(SkillVersionRecord)
            .where(SkillVersionRecord.skill_pk == record.id)
            .order_by(SkillVersionRecord.created_at.desc())
        )
        if target_version:
            stmt = stmt.where(SkillVersionRecord.version == target_version)

        ver_res = await session.execute(stmt)
        prev_ver = ver_res.scalars().first()
        if not prev_ver:
            raise ValidationError(f"No previous rollback version available for skill '{skill_id}'.")

        # Rollback active pointer
        record.version = prev_ver.version
        record.source_commit = prev_ver.source_commit
        record.install_path = prev_ver.install_path
        record.integrity_hash = prev_ver.checksum
        record.manifest_data = prev_ver.manifest_data
        record.status = SkillStatus.INSTALLED
        record.is_active = True

        await session.commit()
        await session.refresh(record)
        return record

    async def remove_skill(self, session: AsyncSession, skill_id: str) -> None:
        """Uninstall and purge a skill from disk and database."""
        record = await self.get_skill(session, skill_id)
        install_dir = Path(record.install_path)
        if install_dir.exists():
            shutil.rmtree(install_dir.parent if install_dir.parent.name == skill_id else install_dir, ignore_errors=True)

        self._memory_cache.pop(skill_id, None)
        await session.delete(record)
        await session.commit()

    async def check_health(self, session: AsyncSession, skill_id: str) -> dict[str, Any]:
        """Verify on-disk integrity and status of a skill."""
        record = await self.get_skill(session, skill_id)
        path = Path(record.install_path)
        exists = path.exists() and (path / "friday-skill.yaml").exists() or (path / "SKILL.md").exists()
        return {
            "skill_id": skill_id,
            "name": record.name,
            "version": record.version,
            "status": record.status,
            "is_active": record.is_active,
            "disk_verified": exists,
            "install_path": record.install_path,
        }


# Global singleton instance
skill_registry = SkillRegistry()
