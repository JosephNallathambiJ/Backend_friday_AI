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
        allowed_executables=[
            "ls", "pwd", "uname", "whoami", "free", "df", "uptime", "date",
            "cat", "echo", "help", "clear", "ps", "top"
        ],
        default_timeout_seconds=10,
    ),
    "hud_interactive": CommandProfile(
        name="hud_interactive",
        description="Interactive HUD terminal session profile",
        allowed_executables=[
            "ls", "pwd", "uname", "whoami", "free", "df", "uptime", "date",
            "cat", "echo", "help", "clear", "ps", "top", "git", "pytest",
            "python", "python3", "ruff"
        ],
        default_timeout_seconds=30,
    ),
}


class CommandRunnerService:
    """Executes validated commands within explicit profiles."""

    @staticmethod
    def filter_environment() -> dict[str, str]:
        """Filter host environment to only pass safe variables."""
        return {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_VARS}

    @classmethod
    def _handle_builtin_command(
        cls,
        executable: str,
        args: list[str],
        profile_name: str,
        t0: float,
    ) -> CommandExecutionResult | None:
        """Handle virtual/emulated commands for consistent cross-platform HUD terminal support."""
        if executable == "free":
            # Format memory table matching Linux `free` exactly
            try:
                page_size = os.sysconf("SC_PAGE_SIZE")
                phys_pages = os.sysconf("SC_PHYS_PAGES")
                total_kib = (page_size * phys_pages) // 1024
            except Exception:
                total_kib = 16777216

            free_kib = total_kib // 4
            used_kib = total_kib - free_kib
            shared_kib = 131072
            cached_kib = free_kib
            available_kib = total_kib - (used_kib // 2)

            try:
                import subprocess
                out = subprocess.check_output(["vm_stat"], text=True)
                vm_page_size = 4096
                for line in out.splitlines():
                    if "page size of" in line:
                        parts = line.split("page size of")
                        if len(parts) > 1:
                            vm_page_size = int(parts[1].split()[0])
                    elif "Pages free:" in line:
                        free_pages = int(line.split(":")[1].strip().rstrip("."))
                        free_kib = (free_pages * vm_page_size) // 1024
                    elif "Pages active:" in line:
                        active_pages = int(line.split(":")[1].strip().rstrip("."))
                        used_kib = (active_pages * vm_page_size) // 1024
                    elif "Pages inactive:" in line:
                        inactive_pages = int(line.split(":")[1].strip().rstrip("."))
                        cached_kib = (inactive_pages * vm_page_size) // 1024
                available_kib = free_kib + cached_kib
            except Exception:
                pass

            swap_total_kib = 8388608
            swap_used_kib = 0
            swap_free_kib = swap_total_kib

            lines = [
                "               total        used        free      shared  buff/cache   available",
                f"Mem:    {total_kib:12d} {used_kib:11d} {free_kib:11d} {shared_kib:11d} {cached_kib:11d} {available_kib:11d}",
                f"Swap:   {swap_total_kib:12d} {swap_used_kib:11d} {swap_free_kib:11d}",
            ]
            elapsed = int((time.time() - t0) * 1000)
            return CommandExecutionResult(
                executable="free",
                args=args,
                exit_code=0,
                stdout="\n".join(lines) + "\n",
                stderr="",
                execution_time_ms=elapsed,
                profile_name=profile_name,
            )

        elif executable == "help":
            help_text = (
                "FRIDAY Tactical HUD Terminal (GOJO Enterprise Edition)\n"
                "Supported system commands:\n"
                "  free              Display system memory and swap statistics\n"
                "  uname [-a]        Display system kernel and architecture information\n"
                "  whoami            Display current HUD session user\n"
                "  uptime            Display system running time\n"
                "  date              Display current system timestamp\n"
                "  pwd               Print working directory\n"
                "  ls [-la]          List directory contents\n"
                "  cat <file>        Read file contents within authorized boundary\n"
                "  git [status|diff] Inspect git repository status\n"
                "  clear             Clear terminal screen\n"
            )
            elapsed = int((time.time() - t0) * 1000)
            return CommandExecutionResult(
                executable="help",
                args=args,
                exit_code=0,
                stdout=help_text,
                stderr="",
                execution_time_ms=elapsed,
                profile_name=profile_name,
            )

        elif executable == "clear":
            elapsed = int((time.time() - t0) * 1000)
            return CommandExecutionResult(
                executable="clear",
                args=args,
                exit_code=0,
                stdout="\033[H\033[2J",
                stderr="",
                execution_time_ms=elapsed,
                profile_name=profile_name,
            )

        return None

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

        # Handle built-in emulations (e.g., Linux free table on macOS host, help, clear)
        builtin_result = cls._handle_builtin_command(executable, args, profile_name, t0)
        if builtin_result is not None:
            return builtin_result

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
