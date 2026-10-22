"""Terminal command tool with security policy enforcement."""

import asyncio
import os
import time
from typing import Any

from app.core.config import settings
from app.domain.enums import ToolRiskLevel
from app.security.command_policy import validate_command
from app.security.path_validation import validate_path_in_roots
from app.tools.base import BaseTool, ToolResult


class RunTerminalCommandTool(BaseTool):
    name = "run_terminal_command"
    description = (
        "Execute an authorized system command with argument array and explicit working directory."
    )
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = True
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "args": {"type": "array", "items": {"type": "string"}, "default": []},
            "cwd": {"type": "string", "default": "."},
        },
        "required": ["command"],
    }

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        cmd = parameters.get("command", "").strip()
        args: list[str] = parameters.get("args", [])
        cwd_str = parameters.get("cwd", ".")

        if not cmd:
            return ToolResult(success=False, error="Command is required.")

        try:
            # Policy enforcement
            validate_command(cmd, args)
            target_cwd = validate_path_in_roots(cwd_str)

            if dry_run:
                return ToolResult(
                    success=True,
                    data={"preview": f"{cmd} {' '.join(args)}", "cwd": str(target_cwd)},
                    dry_run=True,
                )

            # Build minimal sanitized environment
            clean_env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LANG": "en_US.UTF-8",
                "LC_ALL": "en_US.UTF-8",
                "HOME": os.environ.get("HOME", "/tmp"),
            }

            proc = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                cwd=str(target_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=clean_env,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=settings.COMMAND_TIMEOUT_SECONDS,
            )

            elapsed = int((time.time() - start_time) * 1000)
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Limit output to 64KB
            if len(stdout_str) > 65536:
                stdout_str = stdout_str[:65536] + "\n...[OUTPUT TRUNCATED]"

            return ToolResult(
                success=(proc.returncode == 0),
                data={
                    "returncode": proc.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                },
                execution_time_ms=elapsed,
            )
        except TimeoutError:
            return ToolResult(
                success=False,
                error=f"Command execution timed out after {settings.COMMAND_TIMEOUT_SECONDS}s.",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
