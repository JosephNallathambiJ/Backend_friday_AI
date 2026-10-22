"""Terminal command tool with security policy and profile enforcement."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import CapabilityType, ToolRiskLevel
from app.security.path_validation import validate_path_in_roots
from app.services.command_runner import CommandRunnerService
from app.tools.base import BaseTool, ToolResult


class RunTerminalCommandInput(BaseModel):
    command: str = Field(description="The executable command to run (e.g. git, pytest, ruff)")
    args: list[str] = Field(
        default_factory=list, description="Argument list array without shell interpolation"
    )
    cwd: str = Field(default=".", description="Working directory inside permitted roots")
    profile: str = Field(
        default="system_check",
        description="Execution profile (git_inspect, python_test, code_lint, system_check)",
    )
    timeout_seconds: int | None = Field(
        default=None, description="Optional custom timeout in seconds"
    )


class RunTerminalCommandTool(BaseTool):
    name = "run_terminal_command"
    description = "Execute an authorized system command within a predefined execution profile and working directory."
    input_schema = RunTerminalCommandInput
    required_capabilities = [CapabilityType.PROCESS_EXECUTE.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = True
    supports_dry_run = True

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        start_time = time.time()
        try:
            params = self.validate_parameters(parameters)
            cmd = params["command"].strip()
            args = params.get("args", [])
            cwd_str = params.get("cwd", ".")
            profile = params.get("profile", "system_check")
            timeout_sec = params.get("timeout_seconds")

            # Validate working directory against project roots
            target_cwd = validate_path_in_roots(cwd_str)

            if dry_run:
                return ToolResult(
                    success=True,
                    data={
                        "dry_run": True,
                        "executable": cmd,
                        "args": args,
                        "cwd": str(target_cwd),
                        "profile": profile,
                    },
                    dry_run=True,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            res = await CommandRunnerService.run_command(
                executable=cmd,
                args=args,
                cwd=str(target_cwd),
                profile_name=profile,
                timeout_seconds=timeout_sec,
            )

            return ToolResult(
                success=(res.exit_code == 0),
                data={
                    "executable": res.executable,
                    "args": res.args,
                    "exit_code": res.exit_code,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "timed_out": res.timed_out,
                },
                execution_time_ms=res.execution_time_ms,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
