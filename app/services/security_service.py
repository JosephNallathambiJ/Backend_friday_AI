"""Security analysis service for vulnerability scanning and report generation."""

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.security import SecurityFinding, SecurityReport
from app.domain.enums import FindingSeverity
from app.security.path_validation import validate_path_in_roots
from app.tools.security_analysis import SecurityScanTool


class SecurityService:
    @staticmethod
    async def run_scan(
        session: AsyncSession,
        target_path: str | None = None,
    ) -> SecurityReport:
        """Run security scanner across target path and store report."""
        target = validate_path_in_roots(target_path or Path.cwd())

        scanner = SecurityScanTool()
        result = await scanner.execute({"target_path": str(target)})

        findings_data: list[dict[str, Any]] = (
            result.data.get("findings", []) if result.success else []
        )

        # Count severities
        summary: dict[str, int] = {
            FindingSeverity.CRITICAL.value: 0,
            FindingSeverity.HIGH.value: 0,
            FindingSeverity.MEDIUM.value: 0,
            FindingSeverity.LOW.value: 0,
            FindingSeverity.INFO.value: 0,
        }
        for f in findings_data:
            sev = f.get("severity", "info")
            summary[sev] = summary.get(sev, 0) + 1

        # Generate markdown report
        md_lines = [
            f"# Security Analysis Report: {target.name}",
            f"**Path**: `{target}`",
            f"**Total Findings**: {len(findings_data)}",
            "",
            "## Summary by Severity",
            f"- **Critical**: {summary.get('critical', 0)}",
            f"- **High**: {summary.get('high', 0)}",
            f"- **Medium**: {summary.get('medium', 0)}",
            f"- **Low**: {summary.get('low', 0)}",
            f"- **Info**: {summary.get('info', 0)}",
            "",
            "## Detailed Findings",
        ]

        if not findings_data:
            md_lines.append("No security vulnerabilities or secret leaks identified.")
        else:
            for idx, item in enumerate(findings_data, start=1):
                md_lines.extend(
                    [
                        f"### {idx}. [{item.get('severity', 'info').upper()}] {item.get('title')}",
                        f"- **File**: `{item.get('file')}:{item.get('line')}`",
                        f"- **Evidence**: `{item.get('evidence')}`",
                        f"- **Remediation**: {item.get('remediation')}",
                        "",
                    ]
                )

        markdown_content = "\n".join(md_lines)

        report = SecurityReport(
            target_path=str(target),
            summary_counts=summary,
            markdown_content=markdown_content,
        )
        session.add(report)
        await session.flush()

        for item in findings_data:
            sev_str = item.get("severity", "info").lower()
            finding = SecurityFinding(
                report_id=report.id,
                title=item.get("title", "Finding"),
                severity=FindingSeverity(sev_str)
                if sev_str in [s.value for s in FindingSeverity]
                else FindingSeverity.INFO,
                category="static_analysis",
                file_path=item.get("file", ""),
                line_number=item.get("line"),
                evidence=item.get("evidence", ""),
                explanation=item.get("title", ""),
                remediation=item.get("remediation", ""),
            )
            session.add(finding)

        await session.commit()
        await session.refresh(report)
        return report

    @staticmethod
    async def get_report(session: AsyncSession, report_id: str) -> SecurityReport:
        stmt = select(SecurityReport).where(SecurityReport.id == report_id)
        report = (await session.execute(stmt)).scalars().first()
        if not report:
            raise NotFoundError(f"Security report '{report_id}' not found.")
        return report

    @staticmethod
    async def list_reports(session: AsyncSession, limit: int = 20) -> list[SecurityReport]:
        stmt = select(SecurityReport).order_by(SecurityReport.created_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars().all())
