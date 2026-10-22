"""Diagnostic data models, check results, and structured reports."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.enums import DiagnosticJobType, DiagnosticSeverity, DiagnosticStatus


class DiagnosticFinding(BaseModel):
    """Specific diagnostic finding with location, severity, and remediation."""

    id: str = Field(default_factory=lambda: f"diag-{uuid4().hex[:8]}")
    category: str = Field(..., description="Syntax, Configuration, Route, Migration, Secret, Model, Runtime, Tool")
    severity: DiagnosticSeverity
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    confirmed_evidence: str
    root_cause_hypothesis: str | None = None
    suggested_fix: str | None = None
    suggested_regression_test: str | None = None
    fix_applied: bool = False
    fix_verified: bool = False


class DiagnosticCheckResult(BaseModel):
    """Individual test/check result."""

    check_name: str
    category: str
    status: str = Field(..., description="PASSED, FAILED, SKIPPED, BLOCKED")
    duration_ms: float = 0.0
    details: str
    findings: list[DiagnosticFinding] = Field(default_factory=list)


class DiagnosticJobReport(BaseModel):
    """Complete diagnostic job report."""

    job_id: str = Field(default_factory=lambda: f"job-{uuid4().hex[:8]}")
    job_type: DiagnosticJobType = DiagnosticJobType.DIAGNOSE
    status: DiagnosticStatus = DiagnosticStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    skipped_checks: int = 0
    blocked_checks: int = 0
    checks: list[DiagnosticCheckResult] = Field(default_factory=list)
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    summary: str = ""
    markdown_report: str = ""
    remaining_risks: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class DiagnosticRunRequest(BaseModel):
    """Payload to start a diagnostic run."""

    job_type: DiagnosticJobType = DiagnosticJobType.DIAGNOSE
    target_module: str | None = None
    run_static_checks: bool = True
    run_runtime_checks: bool = True
    run_model_checks: bool = True
    run_migration_checks: bool = True
    run_security_audit: bool = True
    run_regression_tests: bool = False
