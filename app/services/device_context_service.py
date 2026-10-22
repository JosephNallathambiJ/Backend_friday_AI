"""Device capability and operating system integration service."""

import asyncio
import os
import platform
import sys
from typing import Any

from app.core.exceptions import SecurityPolicyError, ValidationError

# Explicit allowlist of applications that may be launched
PERMITTED_APPLICATIONS = {
    "Calculator",
    "TextEdit",
    "Notes",
    "Terminal",
    "Calendar",
}


class DeviceContextService:
    """Discovers device capabilities and runs authorized system integrations."""

    @staticmethod
    def get_system_info() -> dict[str, Any]:
        """Collect permitted system hardware and OS information."""
        cpu_count = os.cpu_count() or 1
        return {
            "os_name": platform.system(),
            "os_version": platform.release(),
            "platform": sys.platform,
            "architecture": platform.machine(),
            "cpu_count": cpu_count,
            "python_version": platform.python_version(),
            "supported_adapters": [
                "macos_notifications",
                "application_launcher",
                "device_telemetry",
            ],
        }

    @staticmethod
    async def launch_application(
        app_name: str, arguments: list[str] | None = None
    ) -> dict[str, Any]:
        """Launch an explicitly approved local application on macOS."""
        if app_name not in PERMITTED_APPLICATIONS:
            raise SecurityPolicyError(
                f"Application '{app_name}' is not in the permitted application allowlist. "
                f"Permitted: {sorted(list(PERMITTED_APPLICATIONS))}"
            )

        if sys.platform != "darwin":
            return {
                "success": False,
                "message": f"Application launching not supported on platform '{sys.platform}'.",
            }

        cmd = ["open", "-a", app_name]
        if arguments:
            cmd.extend(arguments)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ValidationError(
                f"Failed to launch '{app_name}': {stderr.decode('utf-8', errors='replace')}"
            )

        return {
            "success": True,
            "app_name": app_name,
            "message": f"Application '{app_name}' launched successfully.",
        }

    @staticmethod
    async def send_notification(
        title: str, message: str, subtitle: str | None = None
    ) -> dict[str, Any]:
        """Send a local desktop notification on macOS via osascript."""
        if sys.platform != "darwin":
            return {
                "success": False,
                "message": f"Notifications not supported on platform '{sys.platform}'.",
            }

        # Sanitize single and double quotes
        clean_title = title.replace('"', '\\"').replace("'", "\\'")
        clean_msg = message.replace('"', '\\"').replace("'", "\\'")
        script = f'display notification "{clean_msg}" with title "{clean_title}"'
        if subtitle:
            clean_sub = subtitle.replace('"', '\\"').replace("'", "\\'")
            script += f' subtitle "{clean_sub}"'

        proc = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        return {
            "success": True,
            "title": title,
            "message": "Desktop notification dispatched.",
        }
