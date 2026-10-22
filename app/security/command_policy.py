"""Terminal and command execution security policy."""

from pathlib import Path

from app.core.config import settings
from app.core.exceptions import SecurityPolicyError

# Explicitly prohibited commands
PROHIBITED_COMMANDS = {
    "sudo",
    "su",
    "rm",
    "rmdir",
    "dd",
    "mkfs",
    "fdisk",
    "shutdown",
    "reboot",
    "chmod",
    "chown",
    "nc",
    "netcat",
}

# Dangerous argument combinations
DANGEROUS_PATTERNS = [
    "--no-preserve-root",
    "rm -rf",
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
]


def validate_command(
    executable: str,
    args: list[str] | None = None,
    allowed_commands: list[str] | None = None,
) -> None:
    """Validate that the command executable and argument array satisfy security policies.

    Enforces:
    1. Executable must be in allowed_commands.
    2. Prohibited executables (sudo, rm, dd, etc.) are strictly rejected.
    3. Dangerous argument patterns are rejected.
    """
    exec_name = Path(executable).name.lower()
    allowed = allowed_commands or settings.ALLOWED_COMMANDS

    if exec_name in PROHIBITED_COMMANDS:
        raise SecurityPolicyError(
            f"Command '{exec_name}' is strictly prohibited for security reasons."
        )

    if exec_name not in allowed:
        raise SecurityPolicyError(
            f"Executable '{exec_name}' is not in the list of allowed commands: {allowed}"
        )

    if args:
        full_command_str = f"{exec_name} {' '.join(args)}".lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern in full_command_str:
                raise SecurityPolicyError(f"Argument pattern '{pattern}' is prohibited.")
        for arg in args:
            if ";" in arg or "&&" in arg or "||" in arg or "`" in arg or "$(" in arg:
                raise SecurityPolicyError(
                    "Command chaining and subshell operators are prohibited in arguments."
                )


class CommandPolicyError(SecurityPolicyError):
    """Raised when a command violates the command security policy."""

    pass


class CommandPolicy:
    """Helper for command validation."""

    @staticmethod
    def is_executable_allowed(executable: str) -> bool:
        exec_name = Path(executable).name.lower()
        if exec_name in PROHIBITED_COMMANDS:
            return False
        return exec_name in settings.ALLOWED_COMMANDS

    @staticmethod
    def validate_command(executable: str, args: list[str] | None = None) -> None:
        validate_command(executable, args)
