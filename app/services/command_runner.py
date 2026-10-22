"""Command Runner Service for controlled subprocess execution.

Enforces execution profiles, argument array execution, environment filtering,
timeout handling, output limits, and process cancellation.
"""

import asyncio
import os
import time

from pydantic import BaseModel, Field

from app.core.exceptions import ValidationError
from app.security.command_policy import CommandPolicy, CommandPolicyError

# Safe environment variables to inherit
ALLOWED_ENV_VARS = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM"}


class CommandProfile(BaseModel):
    name: str
    description: str
    allowed_executables: list[str]
    default_timeout_seconds: int = 30
    max_output_bytes: int = 100 * 1024  # 100 KB max


class CommandExecutionResult(BaseModel):
    executable: str
    args: list[str]
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: int
    timed_out: bool = False
    cancelled: bool = False
    profile_name: str = "default"


COMMAND_PROFILES: dict[str, CommandProfile] = {
    "git_inspect": CommandProfile(
        name="git_inspect",
        description="Inspect Git repository status, branch, or diffs",
        allowed_executables=["git"],
        default_timeout_seconds=20,
    ),
    "python_test": CommandProfile(
        name="python_test",
        description="Run test suite via pytest or python unittest",
        allowed_executables=["pytest", "python", "python3", "uv"],
        default_timeout_seconds=60,
    ),
    "code_lint": CommandProfile(
        name="code_lint",
        description="Run formatting or linting checks",
        allowed_executables=["ruff", "mypy", "flake8"],
        default_timeout_seconds=30,
    ),
    "system_check": CommandProfile(
        name="system_check",
        description="Read basic system or directory information",
        allowed_executables=["ls", "pwd", "uname", "whoami"],
        default_timeout_seconds=10,
    ),
}


class CommandRunnerService:
    """Executes validated commands within explicit profiles."""

    @staticmethod
    def filter_environment() -> dict[str, str]:
        """Filter host environment to only pass safe variables."""
        return {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_VARS}

    @classmethod
    async def run_command(
        cls,
        executable: str,
        args: list[str] = Field(default_factory=list),
        cwd: str | None = None,
        profile_name: str = "system_check",
        timeout_seconds: int | None = None,
    ) -> CommandExecutionResult:
        """Run an approved executable using argument arrays without shell expansion."""
        t0 = time.time()

        # Validate with CommandPolicy
        if not CommandPolicy.is_executable_allowed(executable):
            raise CommandPolicyError(f"Executable '{executable}' is not in the system allowlist.")

        # Validate against profile if specified
        profile = COMMAND_PROFILES.get(profile_name)
        if profile and executable not in profile.allowed_executables:
            raise ValidationError(
                f"Executable '{executable}' is not allowed under profile '{profile_name}'. "
                f"Allowed: {profile.allowed_executables}"
            )

        # Validate argument safety (no shell metacharacters)
        for arg in args:
            for char in [";", "&", "|", "`", "$", "(", ")"]:
                if char in arg:
                    raise CommandPolicyError(
                        f"Argument contains unsafe shell metacharacter '{char}': {arg}"
                    )

        effective_timeout = timeout_seconds or (profile.default_timeout_seconds if profile else 30)
        max_bytes = profile.max_output_bytes if profile else 100 * 1024
        env = cls.filter_environment()

        try:
            proc = await asyncio.create_subprocess_exec(
                executable,
                *args,
                cwd=cwd or os.getcwd(),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    proc.communicate(), timeout=float(effective_timeout)
                )
                elapsed = int((time.time() - t0) * 1000)

                stdout_str = stdout_data[:max_bytes].decode("utf-8", errors="replace")
                stderr_str = stderr_data[:max_bytes].decode("utf-8", errors="replace")

                return CommandExecutionResult(
                    executable=executable,
                    args=args,
                    exit_code=proc.returncode if proc.returncode is not None else 0,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    execution_time_ms=elapsed,
                    timed_out=False,
                    profile_name=profile_name,
                )
            except TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                elapsed = int((time.time() - t0) * 1000)
                return CommandExecutionResult(
                    executable=executable,
                    args=args,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {effective_timeout}s.",
                    execution_time_ms=elapsed,
                    timed_out=True,
                    profile_name=profile_name,
                )
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            return CommandExecutionResult(
                executable=executable,
                args=args,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time_ms=elapsed,
                profile_name=profile_name,
            )
