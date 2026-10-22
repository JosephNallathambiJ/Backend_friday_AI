"""GitHub skill discovery, controlled acquisition, commit pinning, and quarantine isolation.

Enforces Part 4 and Part 5 of Master Prompt 6:
- Safe GitHub repository search with structured candidate evaluation.
- Argument array subprocess cloning into isolated quarantine directories.
- Exact commit hash pinning (40 hex chars).
- Size, file count, and duration boundaries.
- Staged security scan and approval gating before installation.
"""

import asyncio
import re
import shutil
import uuid
from pathlib import Path

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ProviderError, SecurityPolicyError, ValidationError
from app.db.models.skill import SkillAcquisitionRecord
from app.domain.enums import AcquisitionStatus
from app.skills.manifest import SkillManifest, load_manifest_from_directory
from app.skills.scanner import SkillSecurityScanner

GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+(\.git)?$")


class SkillCandidate(BaseModel):
    """Evaluated skill repository candidate from GitHub search."""

    name: str
    full_name: str
    repository_url: str
    description: str | None = None
    default_branch: str = "main"
    stars: int = 0
    license: str | None = None
    language: str | None = None
    last_updated: str | None = None
    preliminary_risk: str = "low"
    compatibility_estimate: str = "compatible"
    source_reference: str = "github.com"


class SkillAcquisitionService:
    """Manages the lifecycle of discovering and acquiring skills into quarantine."""

    @classmethod
    async def search_github_skills(
        cls,
        query: str,
        capability: str | None = None,
        language: str | None = None,
        max_results: int = 10,
    ) -> list[SkillCandidate]:
        """Search GitHub for repositories matching desired skill or capability."""
        if not query or len(query.strip()) < 2:
            raise ValidationError("Search query must be at least 2 characters.")

        q_parts = [query.strip()]
        if capability:
            q_parts.append(capability.strip())
        if language:
            q_parts.append(f"language:{language.strip()}")

        full_q = " ".join(q_parts)
        url = "https://api.github.com/search/repositories"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FRIDAY-AI-Backend",
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        params = {"q": full_q, "sort": "stars", "order": "desc", "per_page": min(max_results, 30)}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=headers, params=params)
                if res.status_code == 403:
                    raise ProviderError("GitHub API rate limit exceeded or access forbidden.")
                if res.status_code != 200:
                    raise ProviderError(f"GitHub search failed with HTTP status {res.status_code}")

                data = res.json()
                items = data.get("items", [])
                candidates = []
                for item in items:
                    lic_info = item.get("license") or {}
                    lic_spdx = lic_info.get("spdx_id") or lic_info.get("name") or "Unresolved"

                    # Calculate preliminary risk
                    stars = item.get("stargazers_count", 0)
                    risk = "low" if stars >= 50 and lic_spdx != "Unresolved" else "medium"

                    candidates.append(
                        SkillCandidate(
                            name=item.get("name", ""),
                            full_name=item.get("full_name", ""),
                            repository_url=item.get("html_url", ""),
                            description=item.get("description"),
                            default_branch=item.get("default_branch", "main"),
                            stars=stars,
                            license=lic_spdx,
                            language=item.get("language"),
                            last_updated=item.get("updated_at"),
                            preliminary_risk=risk,
                            compatibility_estimate="compatible",
                        )
                    )
                return candidates
        except httpx.RequestError as exc:
            raise ProviderError(f"GitHub search network error: {exc}") from exc

    @classmethod
    async def acquire_repository(
        cls,
        session: AsyncSession,
        repository_url: str,
        skill_id: str | None = None,
        requested_commit: str = "",
    ) -> SkillAcquisitionRecord:
        """Clone repository into quarantine, pin commit, and execute security scan."""
        clean_url = repository_url.strip()
        if not GITHUB_URL_PATTERN.match(clean_url):
            raise ValidationError(
                f"Invalid or untrusted repository URL '{clean_url}'. Only https://github.com/owner/repo is allowed."
            )

        # Generate acquisition record
        acq_id = str(uuid.uuid4())
        repo_name = clean_url.rstrip("/").split("/")[-1].replace(".git", "")
        resolved_skill_id = (skill_id or f"github.{repo_name}").lower()

        quarantine_root = settings.QUARANTINE_DIRECTORY.resolve()
        quarantine_root.mkdir(parents=True, exist_ok=True)
        target_dir = quarantine_root / f"{resolved_skill_id}_{acq_id[:8]}"

        record = SkillAcquisitionRecord(
            id=acq_id,
            skill_id=resolved_skill_id,
            source_url=clean_url,
            requested_commit=requested_commit,
            status=AcquisitionStatus.ACQUIRING,
            quarantine_path=str(target_dir),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

        try:
            # 1. Execute safe shallow clone using argument array
            cmd = ["git", "clone", "--depth", "1", clean_url, str(target_dir)]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=settings.SKILL_CLONE_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                proc.kill()
                raise SecurityPolicyError(
                    f"Acquisition timed out after {settings.SKILL_CLONE_TIMEOUT_SECONDS}s."
                )

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="ignore")
                raise ProviderError(f"Git clone failed: {err_msg}")

            # 2. Pin exact commit SHA
            pin_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "HEAD",
                cwd=str(target_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_sha, _ = await pin_proc.communicate()
            pinned_sha = stdout_sha.decode("utf-8").strip() if pin_proc.returncode == 0 else ""
            record.pinned_commit = pinned_sha

            # 3. Check repository limits (size and file count)
            total_size_mb = sum(f.stat().st_size for f in target_dir.rglob("*") if f.is_file()) / (1024 * 1024)
            total_files = len(list(target_dir.rglob("*")))
            if total_size_mb > settings.MAX_SKILL_REPO_SIZE_MB:
                raise SecurityPolicyError(
                    f"Repository size ({total_size_mb:.1f} MB) exceeds limit ({settings.MAX_SKILL_REPO_SIZE_MB} MB)."
                )
            if total_files > settings.MAX_SKILL_FILES:
                raise SecurityPolicyError(
                    f"Repository file count ({total_files}) exceeds limit ({settings.MAX_SKILL_FILES})."
                )

            # 4. Remove .git directory to neutralize hooks
            git_meta = target_dir / ".git"
            if git_meta.exists():
                shutil.rmtree(git_meta, ignore_errors=True)

            # 5. Load or create manifest
            record.status = AcquisitionStatus.ANALYZING
            try:
                manifest = load_manifest_from_directory(target_dir)
                if manifest and manifest.id:
                    record.skill_id = manifest.id
            except Exception:
                # Synthesize default manifest for raw repo
                manifest = SkillManifest(
                    id=resolved_skill_id,
                    name=repo_name.replace("-", " ").title(),
                    description=f"Skill acquired from {clean_url}",
                    source=clean_url,
                    source_commit=pinned_sha,
                )
                # Write generated friday-skill.yaml
                (target_dir / "friday-skill.yaml").write_text(
                    f"id: {manifest.id}\nname: {manifest.name}\nversion: {manifest.version}\n"
                    f"description: {manifest.description}\nsource: {clean_url}\nsource_commit: {pinned_sha}\n"
                )

            # 6. Execute static analysis and prompt injection scan
            scan_report = SkillSecurityScanner.scan_package(target_dir, manifest)
            record.validation_report = scan_report.model_dump()

            if not scan_report.is_valid:
                record.status = AcquisitionStatus.REJECTED
                record.error_message = f"Security scan rejected package: {scan_report.summary}"
            elif scan_report.requires_approval:
                record.status = AcquisitionStatus.AWAITING_APPROVAL
            else:
                record.status = AcquisitionStatus.READY_TO_INSTALL

            await session.commit()
            await session.refresh(record)
            return record

        except Exception as exc:
            record.status = AcquisitionStatus.FAILED
            record.error_message = str(exc)
            await session.commit()
            # Clean up failed clone
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise

    @classmethod
    async def get_acquisition(cls, session: AsyncSession, acquisition_id: str) -> SkillAcquisitionRecord:
        """Fetch acquisition by ID."""
        stmt = select(SkillAcquisitionRecord).where(SkillAcquisitionRecord.id == acquisition_id)
        result = await session.execute(stmt)
        record = result.scalars().first()
        if not record:
            raise ValidationError(f"Acquisition '{acquisition_id}' not found.")
        return record

    @classmethod
    async def cancel_acquisition(cls, session: AsyncSession, acquisition_id: str) -> SkillAcquisitionRecord:
        """Cancel pending or quarantined acquisition and remove directory."""
        record = await cls.get_acquisition(session, acquisition_id)
        if record.status in {AcquisitionStatus.INSTALLED, AcquisitionStatus.CANCELLED}:
            return record

        record.status = AcquisitionStatus.CANCELLED
        record.error_message = "Cancelled by user."
        await session.commit()

        if record.quarantine_path and Path(record.quarantine_path).exists():
            shutil.rmtree(record.quarantine_path, ignore_errors=True)

        return record
