"""CyberAgent — Central Cybersecurity Specialist for FRIDAY AI.

Performs authorized security analysis, asset attack-surface inventory,
passive OSINT collection, DNS/cert/HTTP header auditing, scoped port discovery,
dependency audits, secret detection, incident triage, and structured reporting.
Enforces mandatory TargetAuthorization scoping rules.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.specialists.base import BaseSpecialistAgent, SpecialistExecutionResult
from app.tools.registry import ToolRegistry

logger = logging.getLogger("friday.cyber_agent")


class SecurityFinding(BaseModel):
    """Structured security finding."""

    id: str = Field(default_factory=lambda: f"find-{uuid4().hex[:8]}")
    severity: str = Field(..., description="INFO, LOW, MEDIUM, HIGH, CRITICAL")
    category: str = Field(..., description="OSINT, Network, Dependency, Secret, Configuration, Header")
    title: str
    description: str
    evidence: Any = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    target: str
    remediation: str
    rollback_guidance: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CyberAnalysisReport(BaseModel):
    """Complete structured cyber analysis output."""

    job_id: str
    target: str
    target_type: str
    authorization_id: str | None = None
    started_at: datetime
    completed_at: datetime
    overall_status: str
    passive_osint_summary: str | None = None
    findings: list[SecurityFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    markdown_report: str = ""
    json_data: dict[str, Any] = Field(default_factory=dict)


class CyberAgent(BaseSpecialistAgent):
    """Central cybersecurity and threat intelligence agent."""

    agent_id = "cyber_agent"
    name = "Cybersecurity Specialist Agent"
    description = (
        "Authorized cybersecurity specialist performing attack surface discovery, "
        "passive OSINT, security header audits, dependency vulnerability scans, "
        "secret detection, authorized port scans, and structured mitigation reporting."
    )
    supported_task_types = [
        "cyber_scan",
        "security_audit",
        "osint_recon",
        "vulnerability_scan",
        "attack_surface_inventory",
        "secret_audit",
        "dependency_check",
        "cybersecurity",
    ]
    available_tool_names = [
        "passive_domain_recon",
        "http_security_audit",
        "authorized_port_discovery",
        "dependency_audit",
        "secret_detection_scan",
        "generate_security_report",
        "run_security_scan",
        "read_file",
        "search_files",
    ]
    timeout_seconds = 120
    budget_steps = 8

    def __init__(self, tool_registry: ToolRegistry | None = None):
        self.tool_registry = tool_registry

    async def execute(
        self,
        task_id: str,
        goal: str,
        parameters: dict[str, Any],
        session: AsyncSession,
        context: dict[str, Any] | None = None,
    ) -> SpecialistExecutionResult:
        """Execute cyber mission with scoping, tool orchestration, and reporting."""
        target = parameters.get("target") or "localhost"
        target_type_str = parameters.get("target_type", "domain")
        auth_id = parameters.get("authorization_id")
        action = parameters.get("action", "full_scan")
        started_at = datetime.now(UTC)
        job_id = f"cyber-{uuid4().hex[:8]}"

        findings: list[SecurityFinding] = []
        tool_results: list[dict[str, Any]] = []

        # 1. Passive Domain / OSINT Reconnaissance (default public intelligence)
        if action in {"full_scan", "osint_recon", "passive_recon"} and target_type_str in {"domain", "url"}:
            clean_domain = target.replace("https://", "").replace("http://", "").split("/")[0]
            osint_res = await self.execute_tool_safely(
                tool_name="passive_domain_recon",
                parameters={"domain": clean_domain},
                session=session,
            )
            tool_results.append(osint_res)
            if osint_res.get("status") == "success":
                records = osint_res.get("output", {}).get("records", [])
                for rec in records:
                    if rec.get("category") == "Enumeration":
                        findings.append(
                            SecurityFinding(
                                severity="INFO",
                                category="OSINT",
                                title=f"Discovered Subdomain: {rec.get('indicator')}",
                                description="Public DNS enumeration identified active sub-infrastructure.",
                                evidence=rec.get("details"),
                                target=target,
                                remediation="Review exposed subdomains and verify access control policies.",
                            )
                        )

        # 2. HTTP Security Header Analysis
        if action in {"full_scan", "header_audit", "http_audit"} and target_type_str in {"domain", "url"}:
            http_res = await self.execute_tool_safely(
                tool_name="http_security_audit",
                parameters={"url_or_host": target},
                session=session,
            )
            tool_results.append(http_res)
            if http_res.get("status") == "success":
                for f in http_res.get("output", {}).get("findings", []):
                    if f.get("severity") in {"MEDIUM", "HIGH"}:
                        findings.append(
                            SecurityFinding(
                                severity=f.get("severity", "MEDIUM"),
                                category="Header",
                                title=f.get("issue", "Missing Security Header"),
                                description=f.get("description", "Recommended HTTP defense missing."),
                                evidence=f,
                                target=target,
                                remediation=f.get("remediation", "Add missing header to reverse proxy."),
                            )
                        )

        # 3. Static Code and Secret Detection
        if action in {"full_scan", "secret_scan", "local_audit"}:
            secret_res = await self.execute_tool_safely(
                tool_name="secret_detection_scan",
                parameters={"path": parameters.get("path", ".")},
                session=session,
            )
            tool_results.append(secret_res)
            if secret_res.get("status") == "success":
                for sec in secret_res.get("output", {}).get("findings", []):
                    findings.append(
                        SecurityFinding(
                            severity="HIGH",
                            category="Secret",
                            title=f"Potential Secret Detected: {sec.get('type')}",
                            description=f"File {sec.get('file')} line {sec.get('line')} contains potential credential.",
                            evidence=sec.get("preview"),
                            target=sec.get("file", target),
                            remediation="Move credential to .env or secret manager and revoke compromised keys.",
                        )
                    )

        # 4. Dependency Vulnerability Audit
        if action in {"full_scan", "dependency_check", "local_audit"}:
            dep_res = await self.execute_tool_safely(
                tool_name="dependency_audit",
                parameters={},
                session=session,
            )
            tool_results.append(dep_res)
            if dep_res.get("status") == "success":
                for vuln in dep_res.get("output", {}).get("findings", []):
                    findings.append(
                        SecurityFinding(
                            severity=vuln.get("severity", "MEDIUM"),
                            category="Dependency",
                            title=f"Vulnerable Dependency: {vuln.get('package')}",
                            description=vuln.get("advisory", "Dependency security warning."),
                            evidence=vuln,
                            target="pyproject.toml",
                            remediation="Upgrade package to latest patched version.",
                        )
                    )

        # 5. Authorized Port Probing (Strict Target Authorization Required)
        if action in {"full_scan", "port_scan", "active_scan"}:
            port_res = await self.execute_tool_safely(
                tool_name="authorized_port_discovery",
                parameters={
                    "target": target,
                    "authorization_id": auth_id,
                    "ports": parameters.get("ports", [80, 443, 8000, 8080, 22]),
                },
                session=session,
            )
            tool_results.append(port_res)
            if port_res.get("status") == "failed" and "PORT PROBING REJECTED" in port_res.get("error", ""):
                findings.append(
                    SecurityFinding(
                        severity="INFO",
                        category="Network",
                        title="Active Port Scan Restricted",
                        description=port_res.get("error", "Target authorization absent."),
                        target=target,
                        remediation="Active network probing was safely suppressed. Authorize target if scanning is required.",
                    )
                )
            elif port_res.get("status") == "success":
                open_ports = port_res.get("output", {}).get("open_ports", [])
                for p in open_ports:
                    findings.append(
                        SecurityFinding(
                            severity="LOW" if p in [80, 443] else "MEDIUM",
                            category="Network",
                            title=f"Open Port Identified: {p}",
                            description=f"Port {p} responded to TCP handshake.",
                            evidence={"port": p},
                            target=target,
                            remediation="Ensure only essential services are exposed and protected by authentication.",
                        )
                    )

        # 6. Generate Consolidated Security Report
        report_res = await self.execute_tool_safely(
            tool_name="generate_security_report",
            parameters={
                "title": f"FRIDAY Cyber Analysis Report: {target}",
                "target": target,
                "findings": [f.model_dump(mode="json") for f in findings],
            },
            session=session,
        )
        tool_results.append(report_res)

        markdown_report = report_res.get("output", {}).get("report_markdown", "")
        completed_at = datetime.now(UTC)

        report = CyberAnalysisReport(
            job_id=job_id,
            target=target,
            target_type=target_type_str,
            authorization_id=auth_id,
            started_at=started_at,
            completed_at=completed_at,
            overall_status="COMPLETED",
            findings=findings,
            recommendations=[f.remediation for f in findings],
            markdown_report=markdown_report,
            json_data={"findings": [f.model_dump() for f in findings], "job_id": job_id},
        )

        return SpecialistExecutionResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=f"Cyber analysis completed for {target}: {len(findings)} findings identified.",
            tool_results=tool_results,
            data=report.model_dump(),
        )


# Global singleton instance
cyber_agent = CyberAgent()
