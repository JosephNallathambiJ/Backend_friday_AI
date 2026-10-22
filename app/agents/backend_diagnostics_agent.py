"""BackendDiagnosticsAgent — System Health, Workflow Auditor & Diagnostics Specialist.

Inspects the entire backend repository and runtime:
- Static syntax, configuration, dependencies, secrets, routes.
- Database, dual-brain models, tool registrations, audio flow.
- Supports jobs: diagnose, debug, test_workflow, audit_backend, verify_fix.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.specialists.base import BaseSpecialistAgent, SpecialistExecutionResult
from app.domain.enums import DiagnosticJobType
from app.services.diagnostics.models import DiagnosticRunRequest
from app.services.diagnostics.runner import diagnostic_job_runner


class BackendDiagnosticsAgent(BaseSpecialistAgent):
    """Specialist agent for static repo auditing, runtime health checks, and workflow diagnosis."""

    agent_id = "backend_diagnostics"
    name = "Backend Diagnostics Specialist Agent"
    description = (
        "Performs complete backend diagnostics, static code analysis, dependency audits, "
        "database integrity checks, model readiness checks, and workflow validation."
    )
    supported_task_types = [
        "diagnose",
        "debug",
        "test_workflow",
        "audit_backend",
        "verify_fix",
        "system_health",
        "backend_diagnostics",
    ]
    available_tool_names = [
        "run_diagnostics",
        "get_system_info",
        "read_file",
        "list_files",
        "search_files",
    ]
    timeout_seconds = 180
    budget_steps = 10

    async def execute(
        self,
        task_id: str,
        goal: str,
        parameters: dict[str, Any],
        session: AsyncSession,
        context: dict[str, Any] | None = None,
    ) -> SpecialistExecutionResult:
        """Run diagnostics and generate a structured report."""
        job_type_str = parameters.get("job_type", "diagnose").lower()
        job_type_map = {
            "diagnose": DiagnosticJobType.DIAGNOSE,
            "debug": DiagnosticJobType.DEBUG,
            "test_workflow": DiagnosticJobType.TEST_WORKFLOW,
            "audit_backend": DiagnosticJobType.AUDIT_BACKEND,
            "verify_fix": DiagnosticJobType.VERIFY_FIX,
        }
        job_type = job_type_map.get(job_type_str, DiagnosticJobType.DIAGNOSE)

        req = DiagnosticRunRequest(
            job_type=job_type,
            run_static_checks=parameters.get("run_static_checks", True),
            run_runtime_checks=parameters.get("run_runtime_checks", True),
            run_model_checks=parameters.get("run_model_checks", True),
            run_migration_checks=parameters.get("run_migration_checks", True),
            run_security_audit=parameters.get("run_security_audit", True),
            run_regression_tests=parameters.get("run_regression_tests", False),
        )

        report = await diagnostic_job_runner.run_diagnostics(req)

        return SpecialistExecutionResult(
            agent_name=self.name,
            task_id=task_id,
            success=report.failed_checks == 0,
            summary=report.summary,
            tool_results=[{"check": c.model_dump()} for c in report.checks],
            data=report.model_dump(),
        )


# Global singleton instance
backend_diagnostics_agent = BackendDiagnosticsAgent()
