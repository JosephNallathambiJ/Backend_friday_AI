"""Unit tests for Backend Diagnostics, System Checkers, and Diagnostics Agent."""

import pytest

from app.agents.backend_diagnostics_agent import (
    BackendDiagnosticsAgent,
)
from app.domain.enums import DiagnosticJobType, DiagnosticStatus
from app.services.diagnostics import (
    DiagnosticRunRequest,
    SystemDiagnosticChecker,
    diagnostic_job_runner,
)


@pytest.mark.asyncio
async def test_python_syntax_and_critical_imports():
    """Verify AST parsing on project files and critical module imports."""
    syntax_res = await SystemDiagnosticChecker.check_python_syntax()
    assert syntax_res.status == "PASSED"
    assert "Parsed" in syntax_res.details
    assert len(syntax_res.findings) == 0

    imports_res = await SystemDiagnosticChecker.check_critical_imports()
    assert imports_res.status == "PASSED"
    assert "critical module imports" in imports_res.details


@pytest.mark.asyncio
async def test_configuration_and_api_routes():
    """Verify configuration validation and FastAPI routes inspection."""
    config_res = await SystemDiagnosticChecker.check_configuration_and_env()
    assert config_res.status == "PASSED"

    routes_res = await SystemDiagnosticChecker.check_api_routes()
    assert routes_res.status == "PASSED"
    assert "registered API routes" in routes_res.details


@pytest.mark.asyncio
async def test_database_and_registry_checks():
    """Verify database connectivity query and tool/agent registrations."""
    db_res = await SystemDiagnosticChecker.check_database_connectivity()
    assert db_res.status == "PASSED"

    reg_res = await SystemDiagnosticChecker.check_tool_and_agent_registries()
    assert reg_res.status == "PASSED"
    assert "registered tools" in reg_res.details


@pytest.mark.asyncio
async def test_model_and_audio_checks():
    """Verify dual-brain models and audio subsystem diagnostics."""
    model_res = await SystemDiagnosticChecker.check_dual_brain_model_status()
    assert model_res.status == "PASSED"
    assert "Dual-brain status checked" in model_res.details

    audio_res = await SystemDiagnosticChecker.check_audio_subsystem_health()
    assert audio_res.status == "PASSED"
    assert "Audio subsystem ready" in audio_res.details


@pytest.mark.asyncio
async def test_diagnostic_job_runner_full_run():
    """Verify end-to-end execution of diagnostic job runner with Markdown generation."""
    req = DiagnosticRunRequest(
        job_type=DiagnosticJobType.DIAGNOSE,
        run_static_checks=True,
        run_runtime_checks=True,
        run_model_checks=True,
    )
    job = await diagnostic_job_runner.run_diagnostics(req)

    assert job.status in {DiagnosticStatus.PASSED, DiagnosticStatus.FAILED}
    assert job.total_checks >= 5
    assert job.passed_checks >= 5
    assert len(job.markdown_report) > 100
    assert "System Diagnostics & Health Audit Report" in job.markdown_report

    # Check job retrieval
    retrieved = diagnostic_job_runner.get_job(job.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job.job_id


@pytest.mark.asyncio
async def test_backend_diagnostics_agent_execution(db_session):
    """Verify BackendDiagnosticsAgent execution wraps runner into specialist response."""
    agent = BackendDiagnosticsAgent()
    result = await agent.execute(
        task_id="task-diag-agent-01",
        goal="Run backend diagnostics audit",
        parameters={"job_type": "audit_backend"},
        session=db_session,
    )

    assert result.success is True
    assert "Diagnostic run completed" in result.summary
    assert "markdown_report" in result.data
    assert len(result.tool_results) >= 5
