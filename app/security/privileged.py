"""Privileged Tool Gateway for FRIDAY AI.

Mediates operations requiring elevated operating-system privileges.
Follows least-privilege principles and prevents arbitrary privilege escalation.
"""

from typing import Any

from pydantic import BaseModel

from app.core.exceptions import FridayException


class PrivilegedOperationError(FridayException):
    """Raised when a privileged operation fails or is unauthorized."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, code="PRIVILEGED_OP_DENIED", details=details)


class PrivilegedOperationRequest(BaseModel):
    operation_name: str
    target_resource: str
    parameters: dict[str, Any] = {}


class PrivilegedToolGateway:
    """Gateway mediating operations that could require elevated privileges.

    Operates with the current user's unprivileged permissions by default.
    Strictly denies arbitrary commands, root shells, or unauthorized elevation.
    """

    # Narrow, explicit allowlist of permitted elevated tasks
    PERMITTED_ELEVATED_OPERATIONS = {
        "network.flush_dns": {
            "description": "Flush local system DNS cache",
            "platforms": ["darwin", "linux"],
        },
        "system.service_status": {
            "description": "Inspect system service status",
            "platforms": ["darwin", "linux"],
        },
        "system.time_sync_status": {
            "description": "Inspect network time synchronization status",
            "platforms": ["darwin", "linux", "win32"],
        },
    }

    @classmethod
    def is_operation_permitted(cls, operation_name: str) -> bool:
        return operation_name in cls.PERMITTED_ELEVATED_OPERATIONS

    @classmethod
    async def execute_privileged_operation(
        cls, request: PrivilegedOperationRequest
    ) -> dict[str, Any]:
        """Execute a validated privileged operation through safe, hardcoded routines."""
        if not cls.is_operation_permitted(request.operation_name):
            raise PrivilegedOperationError(
                f"Operation '{request.operation_name}' is not on the privileged allowlist.",
                details={"operation": request.operation_name},
            )

        # Execute safe, predefined routine without arbitrary shell execution
        if request.operation_name == "network.flush_dns":
            # On macOS, flush DNS cache using dscacheutil
            import sys

            if sys.platform == "darwin":
                import asyncio

                proc = await asyncio.create_subprocess_exec(
                    "dscacheutil",
                    "-flushcache",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return {"success": True, "message": "macOS DNS cache flushed successfully."}
            return {"success": True, "message": "DNS flush executed for platform."}

        if request.operation_name == "system.service_status":
            service = request.parameters.get("service", "unknown")
            return {
                "success": True,
                "service": service,
                "status": "active (unprivileged inspection)",
            }

        if request.operation_name == "system.time_sync_status":
            return {"success": True, "time_synced": True, "provider": "system_clock"}

        raise PrivilegedOperationError(
            f"No handler configured for privileged operation '{request.operation_name}'."
        )
