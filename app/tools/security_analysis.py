"""Static security analysis and secret detection tool."""

import os
import re
import time
from pathlib import Path
from typing import Any

from app.domain.enums import FindingSeverity, ToolRiskLevel
from app.security.path_validation import validate_path_in_roots
from app.tools.base import BaseTool, ToolResult

SECRET_PATTERNS = [
    (
        re.compile(
            r"""(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['"][a-zA-Z0-9_\-]{8,}['"]"""
        ),
        "Hardcoded Credential / Secret",
        FindingSeverity.HIGH,
    ),
    (
        re.compile(r"""ghp_[A-Za-z0-9]{36}"""),
        "GitHub Personal Access Token",
        FindingSeverity.CRITICAL,
    ),
    (
        re.compile(r"""-----BEGIN (?:RSA|OPENSSH|DSA|EC)? PRIVATE KEY-----"""),
        "Exposed Private Key",
        FindingSeverity.CRITICAL,
    ),
    (
        re.compile(r"""(?i)eval\s*\("""),
        "Unsafe Dynamic Code Execution (eval)",
        FindingSeverity.HIGH,
    ),
    (
        re.compile(r"""(?i)shell\s*=\s*True"""),
        "Unsafe Subprocess Shell Execution",
        FindingSeverity.HIGH,
    ),
]


class SecurityScanTool(BaseTool):
    name = "security_scan"
    description = "Analyze project files for security vulnerabilities, hardcoded secrets, and unsafe patterns."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    parameters_schema = {
        "type": "object",
        "properties": {
            "target_path": {"type": "string", "default": "."},
        },
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        target_path_str = parameters.get("target_path", ".")

        try:
            target = validate_path_in_roots(target_path_str)
            findings: list[dict[str, Any]] = []

            # Traverse directory
            for root, dirs, files in os.walk(target):
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".") and d not in {"node_modules", ".venv", "__pycache__"}
                ]
                for file in files:
                    if file.startswith(".") or file.endswith(
                        (".pyc", ".png", ".jpg", ".db", ".sqlite")
                    ):
                        continue

                    file_path = Path(root) / file
                    if file_path.stat().st_size > 2 * 1024 * 1024:
                        continue  # Skip large files

                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, start=1):
                                for regex, title, severity in SECRET_PATTERNS:
                                    if regex.search(line):
                                        findings.append(
                                            {
                                                "title": title,
                                                "severity": severity.value,
                                                "file": str(file_path.relative_to(target)),
                                                "line": idx,
                                                "evidence": line.strip()[:100],
                                                "remediation": "Move secret to environment variables or remove unsafe invocation.",
                                            }
                                        )
                    except Exception:
                        continue

            elapsed = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=True,
                data={
                    "scanned_path": str(target),
                    "findings_count": len(findings),
                    "findings": findings,
                },
                execution_time_ms=elapsed,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
