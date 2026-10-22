"""Git inspection tools using subprocess argument arrays without shell injection."""

import asyncio
import time
from typing import Any

from app.domain.enums import ToolRiskLevel
from app.security.path_validation import validate_path_in_roots
from app.tools.base import BaseTool, ToolResult


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Inspect git working tree status, branch, and staged/unstaged changes."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    parameters_schema = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "default": "."},
        },
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        repo_path_str = parameters.get("repo_path", ".")

        try:
            target_dir = validate_path_in_roots(repo_path_str)
            proc = await asyncio.create_subprocess_exec(
                "git",
                "status",
                "--porcelain",
                "-b",
                cwd=str(target_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)

            elapsed = int((time.time() - start_time) * 1000)
            if proc.returncode != 0:
                return ToolResult(
                    success=False,
                    error=stderr.decode("utf-8", errors="replace"),
                    execution_time_ms=elapsed,
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            lines = output.splitlines() if output else []
            branch = lines[0] if lines else "unknown"
            files = lines[1:] if len(lines) > 1 else []

            return ToolResult(
                success=True,
                data={
                    "branch": branch,
                    "changes_count": len(files),
                    "changes": files,
                },
                execution_time_ms=elapsed,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "View unstaged or staged git diff within an approved repository."
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False
    parameters_schema = {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "default": "."},
            "cached": {"type": "boolean", "default": False},
        },
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        repo_path_str = parameters.get("repo_path", ".")
        cached = parameters.get("cached", False)

        try:
            target_dir = validate_path_in_roots(repo_path_str)
            cmd = ["git", "diff"]
            if cached:
                cmd.append("--cached")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(target_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)

            elapsed = int((time.time() - start_time) * 1000)
            if proc.returncode != 0:
                return ToolResult(
                    success=False,
                    error=stderr.decode("utf-8", errors="replace"),
                    execution_time_ms=elapsed,
                )

            diff_text = stdout.decode("utf-8", errors="replace")
            # Truncate if diff is huge (> 100KB)
            if len(diff_text) > 100000:
                diff_text = diff_text[:100000] + "\n...[DIFF TRUNCATED AT 100KB]"

            return ToolResult(
                success=True,
                data={"diff": diff_text, "cached": cached},
                execution_time_ms=elapsed,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
