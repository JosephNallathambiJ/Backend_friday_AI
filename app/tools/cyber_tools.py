"""Modular Cybersecurity and Reconnaissance Tools for FRIDAY AI.

Supports:
- Passive OSINT & Domain Intelligence (via Omni OSINT Power adapter)
- HTTP/TLS and Security Header Auditing
- Authorized Port and Service Discovery (enforcing TargetAuthorization)
- Dependency Vulnerability Scanning
- Secret Detection and Codebase Hardening
- Structured Security Report Generation
"""

import asyncio
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import TechniqueType, ToolRiskLevel
from app.integrations.omni_osint import OSINTQueryRequest, omni_osint_adapter
from app.security.target_authorization import target_auth_manager
from app.tools.base import BaseTool, ToolResult


class PassiveDomainReconInput(BaseModel):
    domain: str = Field(..., description="Target domain to inspect via passive intelligence")
    include_subdomains: bool = Field(default=True)
    include_whois: bool = Field(default=True)
    include_certificates: bool = Field(default=True)


class PassiveDomainReconTool(BaseTool):
    """Gathers passive DNS, certificate transparency, and WHOIS intelligence."""

    name = "passive_domain_recon"
    description = "Gathers passive public domain intelligence without active network scanning."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        validated = PassiveDomainReconInput(**parameters)
        req = OSINTQueryRequest(
            target=validated.domain,
            target_type="domain",
            include_subdomains=validated.include_subdomains,
            include_whois=validated.include_whois,
            include_certificates=validated.include_certificates,
        )
        res = await omni_osint_adapter.query(req)
        return ToolResult(
            success=True,
            data={
                "target": res.target,
                "status": res.status.value,
                "is_mock": res.is_mock,
                "records_count": len(res.records),
                "summary": res.summary,
                "records": [r.model_dump() for r in res.records],
                "warnings": res.warnings,
            },
        )


class HttpSecurityAuditInput(BaseModel):
    url_or_host: str = Field(..., description="HTTP/HTTPS endpoint or hostname to analyze")
    timeout_seconds: float = Field(default=5.0, ge=1.0, le=15.0)


class HttpSecurityAuditTool(BaseTool):
    """Audits HTTP security headers and TLS configuration."""

    name = "http_security_audit"
    description = "Analyzes HTTP response headers (CSP, HSTS, X-Frame-Options) and TLS posture."
    risk_level = ToolRiskLevel.NETWORK_ACCESS
    requires_approval = False

    RECOMMENDED_HEADERS = {
        "strict-transport-security": "Enforces HTTPS connections and prevents SSL stripping.",
        "content-security-policy": "Restricts sources of executable scripts and resource loading.",
        "x-content-type-options": "Prevents MIME-sniffing attacks (should be 'nosniff').",
        "x-frame-options": "Protects against clickjacking attacks (DENY or SAMEORIGIN).",
        "referrer-policy": "Controls referrer information leakage across origins.",
        "permissions-policy": "Restricts browser feature access (camera, microphone, geolocation).",
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        validated = HttpSecurityAuditInput(**parameters)
        target = validated.url_or_host.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://{target}"

        import httpx

        findings = []
        headers_found = {}
        status_code = None

        try:
            async with httpx.AsyncClient(timeout=validated.timeout_seconds, verify=False) as client:
                resp = await client.get(target)
                status_code = resp.status_code
                headers_found = {k.lower(): v for k, v in resp.headers.items()}
        except Exception as e:
            # Fallback for offline or unreachable environments
            findings.append({
                "severity": "INFO",
                "issue": f"Could not perform live HTTP fetch: {str(e)}",
                "recommendation": "Verify network connectivity or endpoint availability.",
            })

        for header_name, description in self.RECOMMENDED_HEADERS.items():
            if header_name not in headers_found:
                findings.append({
                    "severity": "MEDIUM",
                    "header": header_name,
                    "issue": f"Missing security header: '{header_name}'",
                    "description": description,
                    "remediation": f"Configure web server to return '{header_name}'.",
                })
            else:
                findings.append({
                    "severity": "INFO",
                    "header": header_name,
                    "status": "PRESENT",
                    "value": headers_found[header_name],
                })

        return ToolResult(
            success=True,
            data={
                "target": target,
                "status_code": status_code,
                "total_findings": len(findings),
                "findings": findings,
            },
        )


class AuthorizedPortDiscoveryInput(BaseModel):
    target: str = Field(..., description="Target hostname or IP address")
    ports: list[int] = Field(default_factory=lambda: [80, 443, 8000, 8080, 22, 5432, 27017, 11434])
    authorization_id: str | None = Field(
        default=None,
        description="Mandatory TargetAuthorization reference ID for active port probing",
    )
    timeout_seconds: float = Field(default=1.5, ge=0.5, le=5.0)


class AuthorizedPortDiscoveryTool(BaseTool):
    """Discovers open ports on authorized targets with strict scoping."""

    name = "authorized_port_discovery"
    description = "Probes network ports on explicitly authorized targets. Fails without valid authorization."
    risk_level = ToolRiskLevel.NETWORK_ACCESS
    requires_approval = True

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        validated = AuthorizedPortDiscoveryInput(**parameters)
        target = validated.target.strip()

        # Strict target authorization check
        is_auth, reason, auth_record = target_auth_manager.validate_action(
            target=target,
            technique=TechniqueType.AUTHORIZED_PORT_SCAN,
            authorization_id=validated.authorization_id,
        )

        if not is_auth:
            return ToolResult(
                success=False,
                error=f"PORT PROBING REJECTED: {reason}",
                data={
                    "target": target,
                    "authorized": False,
                    "action_taken": "BLOCKED",
                    "reason": reason,
                    "recommendation": (
                        "Create a valid TargetAuthorization record with active_recon_permitted=True "
                        "and pass its authorization_id."
                    ),
                },
            )

        open_ports = []
        closed_ports = []

        for port in validated.ports:
            # Respect rate limit
            await asyncio.sleep(1.0 / (auth_record.rate_limit_rps if auth_record else 2.0))
            is_open = await self._check_port(target, port, validated.timeout_seconds)
            if is_open:
                open_ports.append(port)
            else:
                closed_ports.append(port)

        return ToolResult(
            success=True,
            data={
                "target": target,
                "authorization_id": validated.authorization_id,
                "open_ports": open_ports,
                "closed_ports": closed_ports,
                "total_scanned": len(validated.ports),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @staticmethod
    async def _check_port(host: str, port: int, timeout: float) -> bool:
        loop = asyncio.get_event_loop()

        def _probe() -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    return s.connect_ex((host, port)) == 0
            except Exception:
                return False

        return await loop.run_in_executor(None, _probe)


class DependencyAuditTool(BaseTool):
    """Audits local package dependencies for known outdated patterns or vulnerabilities."""

    name = "dependency_audit"
    description = "Checks project dependencies for security vulnerabilities and known advisories."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        findings = []
        pyproject_path = Path.cwd() / "pyproject.toml"

        if not pyproject_path.exists():
            return ToolResult(success=False, error="pyproject.toml not found in workspace.")

        content = pyproject_path.read_text(encoding="utf-8")
        deps_found = []

        for line in content.splitlines():
            line = line.strip().strip('"').strip("'")
            if any(k in line for k in [">=", "==", "~="]) and not line.startswith("#"):
                deps_found.append(line)

        # Baseline security checks on dependencies
        for dep in deps_found:
            if "pydantic<2" in dep:
                findings.append({
                    "severity": "MEDIUM",
                    "package": dep,
                    "advisory": "Legacy Pydantic v1 has reached end of life. Migrate to Pydantic v2.",
                })
            elif "urllib3<1.26.18" in dep:
                findings.append({
                    "severity": "HIGH",
                    "package": dep,
                    "advisory": "CVE-2023-45803: Request body leak on redirect.",
                })

        return ToolResult(
            success=True,
            data={
                "total_dependencies_checked": len(deps_found),
                "vulnerabilities_detected": len(findings),
                "findings": findings,
                "status": "PASS" if not findings else "ATTENTION_REQUIRED",
            },
        )


class SecretDetectionTool(BaseTool):
    """Scans code files or text buffers for accidental credentials and tokens."""

    name = "secret_detection_scan"
    description = "Identifies unmasked credentials, API keys, private keys, and passwords in files."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    PATTERNS = [
        ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("Private RSA Key", re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----")),
        ("GitHub Personal Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),
        ("Generic High-Entropy API Key", re.compile(r"(?:api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", re.IGNORECASE)),
    ]

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        path_str = parameters.get("path", ".")
        target_dir = Path(path_str).resolve()
        findings = []

        # Only scan text files, skipping virtualenvs and git metadata
        extensions = {".py", ".env", ".toml", ".yaml", ".json", ".md"}
        exclude_dirs = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}

        if target_dir.is_file():
            scan_files = [target_dir]
        else:
            scan_files = [
                f for f in target_dir.rglob("*")
                if f.is_file() and f.suffix in extensions and not any(ex in f.parts for ex in exclude_dirs)
            ][:100]

        for file_path in scan_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(content.splitlines(), start=1):
                    for name, pat in self.PATTERNS:
                        if pat.search(line):
                            # Mask matched secret
                            masked = pat.sub("[REDACTED_SECRET]", line)
                            findings.append({
                                "file": str(file_path.relative_to(Path.cwd())),
                                "line": line_no,
                                "type": name,
                                "preview": masked[:100],
                            })
            except Exception:
                continue

        return ToolResult(
            success=True,
            data={
                "files_scanned": len(scan_files),
                "secrets_found": len(findings),
                "findings": findings,
            },
        )


class SecurityReportTool(BaseTool):
    """Compiles findings into Markdown and JSON security reports."""

    name = "generate_security_report"
    description = "Formats audit, recon, and vulnerability findings into standardized security reports."
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        title = parameters.get("title", "FRIDAY Security Assessment Report")
        target = parameters.get("target", "System")
        findings = parameters.get("findings", [])

        # Build Markdown report
        lines = [
            f"# {title}",
            f"**Target:** `{target}`  ",
            f"**Generated At:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Total Findings:** {len(findings)}  \n",
            "## Summary of Findings\n",
        ]

        if not findings:
            lines.append("No security vulnerabilities or unmasked secrets detected. Posture verified.\n")
        else:
            lines.append("| Severity | Finding / Indicator | File / Line / Target | Remediation |")
            lines.append("|---|---|---|---|")
            for f in findings:
                sev = f.get("severity", "MEDIUM")
                desc = f.get("issue") or f.get("type") or f.get("advisory", "Security Note")
                loc = f.get("file", target)
                rem = f.get("remediation") or f.get("recommendation", "Review and apply security patch.")
                lines.append(f"| **{sev}** | {desc} | `{loc}` | {rem} |")

        report_md = "\n".join(lines)
        report_json = {
            "title": title,
            "target": target,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_findings": len(findings),
            "findings": findings,
        }

        return ToolResult(
            success=True,
            data={
                "report_markdown": report_md,
                "report_json": report_json,
            },
        )
