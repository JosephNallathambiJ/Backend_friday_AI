"""Diagnostic job runner coordinating static and runtime system audits."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import settings
from app.domain.enums import DiagnosticStatus
from app.services.diagnostics.checker import SystemDiagnosticChecker
from app.services.diagnostics.models import (
    DiagnosticCheckResult,
    DiagnosticFinding,
    DiagnosticJobReport,
    DiagnosticRunRequest,
)

logger = logging.getLogger("friday.diagnostics_runner")


class DiagnosticJobRunner:
    """Manages diagnostic test runs, background execution, cancellation, and report export."""

    def __init__(self):
        self._jobs: dict[str, DiagnosticJobReport] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def get_job(self, job_id: str) -> DiagnosticJobReport | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[DiagnosticJobReport]:
        return list(self._jobs.values())

    async def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            job.status = DiagnosticStatus.CANCELLED
            job.summary = "Job cancelled by operator."
            job.completed_at = datetime.now(UTC)
            return True
        return False

    async def run_diagnostics(self, request: DiagnosticRunRequest) -> DiagnosticJobReport:
        """Execute a full diagnostic evaluation across the system."""
        job_id = f"diag-{uuid4().hex[:8]}"
        job = DiagnosticJobReport(
            job_id=job_id,
            job_type=request.job_type,
            status=DiagnosticStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._jobs[job_id] = job

        checks: list[DiagnosticCheckResult] = []
        all_findings: list[DiagnosticFinding] = []

        try:
            # 1. Python Syntax & AST
            if request.run_static_checks:
                res = await SystemDiagnosticChecker.check_python_syntax()
                checks.append(res)
                all_findings.extend(res.findings)

            # 2. Critical Imports
            if request.run_static_checks:
                res = await SystemDiagnosticChecker.check_critical_imports()
                checks.append(res)
                all_findings.extend(res.findings)

            # 3. Configuration & Environment
            if request.run_static_checks:
                res = await SystemDiagnosticChecker.check_configuration_and_env()
                checks.append(res)
                all_findings.extend(res.findings)

            # 4. API Routes
            if request.run_runtime_checks:
                res = await SystemDiagnosticChecker.check_api_routes()
                checks.append(res)
                all_findings.extend(res.findings)

            # 5. Database Connectivity
            if request.run_runtime_checks:
                res = await SystemDiagnosticChecker.check_database_connectivity()
                checks.append(res)
                all_findings.extend(res.findings)

            # 6. Tool & Specialist Registry
            if request.run_runtime_checks:
                res = await SystemDiagnosticChecker.check_tool_and_agent_registries()
                checks.append(res)
                all_findings.extend(res.findings)

            # 7. Dual-Brain Model & Ollama
            if request.run_model_checks:
                res = await SystemDiagnosticChecker.check_dual_brain_model_status()
                checks.append(res)
                all_findings.extend(res.findings)

            # 8. Audio & Speech Subsystem
            if request.run_runtime_checks:
                res = await SystemDiagnosticChecker.check_audio_subsystem_health()
                checks.append(res)
                all_findings.extend(res.findings)

            # Calculate metrics
            passed = sum(1 for c in checks if c.status == "PASSED")
            failed = sum(1 for c in checks if c.status == "FAILED")
            skipped = sum(1 for c in checks if c.status == "SKIPPED")
            blocked = sum(1 for c in checks if c.status == "BLOCKED")

            job.total_checks = len(checks)
            job.passed_checks = passed
            job.failed_checks = failed
            job.skipped_checks = skipped
            job.blocked_checks = blocked
            job.checks = checks
            job.findings = all_findings
            job.status = DiagnosticStatus.PASSED if failed == 0 else DiagnosticStatus.FAILED
            job.completed_at = datetime.now(UTC)

            # Generate Markdown report
            job.markdown_report = self._generate_markdown_report(job)
            job.summary = (
                f"Diagnostic run completed: {passed}/{len(checks)} checks passed, {failed} failed. "
                f"{len(all_findings)} findings identified."
            )

            job.remaining_risks = [
                "Local Ollama model download required for offline LLM inference.",
                "Ensure live Omni OSINT credentials if public intelligence queries are needed.",
            ]
            job.recommended_next_steps = [
                "Address any HIGH or CRITICAL severity findings.",
                "Run test suite via `pytest tests/` for complete regression coverage.",
            ]

            # Save report to storage if directory exists
            try:
                report_dir = settings.DIAGNOSTICS_REPORT_DIR
                report_dir.mkdir(parents=True, exist_ok=True)
                report_file = report_dir / f"{job_id}.md"
                report_file.write_text(job.markdown_report, encoding="utf-8")
            except Exception as e:
                logger.warning("Could not write diagnostic report to disk: %s", str(e))

            return job

        except asyncio.CancelledError:
            job.status = DiagnosticStatus.CANCELLED
            job.summary = "Diagnostic job was cancelled."
            job.completed_at = datetime.now(UTC)
            return job
        except Exception as e:
            logger.exception("Diagnostic job failure")
            job.status = DiagnosticStatus.FAILED
            job.summary = f"Diagnostic runner encountered an unexpected error: {str(e)}"
            job.completed_at = datetime.now(UTC)
            return job

    def generate_markdown_report(self, job: DiagnosticJobReport) -> str:
        """Render high-fidelity Markdown diagnostics report."""
        return self._generate_markdown_report(job)

    def _generate_markdown_report(self, job: DiagnosticJobReport) -> str:
        """Render high-fidelity Markdown diagnostics report."""
        lines = [
            "# FRIDAY AI — System Diagnostics & Health Audit Report",
            f"**Job ID:** `{job.job_id}` | **Job Type:** `{job.job_type.value.upper()}`",
            f"**Execution Timestamp:** {job.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Overall Status:** **{job.status.value.upper()}**",
            f"**Checks Summary:** {job.passed_checks} Passed | {job.failed_checks} Failed | {job.skipped_checks} Skipped | {job.blocked_checks} Blocked\n",
            "## 1. Executive Summary",
            job.summary or "All diagnostic health checks completed.",
            "",
            "## 2. Check Results Breakdown",
            "| Check Name | Category | Status | Duration (ms) | Details |",
            "|---|---|---|---|---|",
        ]

        for c in job.checks:
            badge = "✅ PASS" if c.status == "PASSED" else "❌ FAIL"
            lines.append(f"| `{c.check_name}` | {c.category} | {badge} | {c.duration_ms} | {c.details} |")

        lines.extend([
            "",
            "## 3. Severity-Ranked Findings",
        ])

        if not job.findings:
            lines.append("No active errors, vulnerabilities, or configuration failures detected.")
        else:
            lines.append("| Severity | Category | Title | Location | Confirmed Evidence | Suggested Fix |")
            lines.append("|---|---|---|---|---|---|")
            for f in sorted(job.findings, key=lambda x: x.severity.value, reverse=True):
                loc = f"{f.file_path}:{f.line_number}" if f.file_path else "System/Runtime"
                lines.append(
                    f"| **{f.severity.value.upper()}** | {f.category} | {f.title} | `{loc}` | {f.confirmed_evidence} | {f.suggested_fix or 'N/A'} |"
                )

        lines.extend([
            "",
            "## 4. Remaining Risks and Recommendations",
        ])
        for risk in job.remaining_risks:
            lines.append(f"- **Risk:** {risk}")
        for step in job.recommended_next_steps:
            lines.append(f"- **Action:** {step}")

        return "\n".join(lines)


# Global singleton runner
diagnostic_job_runner = DiagnosticJobRunner()
