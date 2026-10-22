"""Device context and system integration tools for FRIDAY AI."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import CapabilityType, ToolRiskLevel
from app.services.device_context_service import DeviceContextService
from app.tools.base import BaseTool, ToolResult


class GetSystemInfoInput(BaseModel):
    pass


class LaunchAppInput(BaseModel):
    app_name: str = Field(
        description="Name of the permitted application to launch (e.g. Calculator, TextEdit)"
    )
    arguments: list[str] = Field(
        default_factory=list, description="Optional command-line arguments"
    )


class SendNotificationInput(BaseModel):
    title: str = Field(description="Title of notification")
    message: str = Field(description="Message body")
    subtitle: str | None = Field(default=None, description="Optional subtitle")


class GetSystemInfoTool(BaseTool):
    name = "get_system_info"
    description = (
        "Read system telemetry, OS version, architecture, CPU count, and platform adapters."
    )
    input_schema = GetSystemInfoInput
    required_capabilities = [CapabilityType.SYSTEM_INFO_READ.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            info = DeviceContextService.get_system_info()
            return ToolResult(
                success=True, data=info, execution_time_ms=int((time.time() - t0) * 1000)
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class LaunchApplicationTool(BaseTool):
    name = "launch_application"
    description = "Launch an explicitly permitted local desktop application."
    input_schema = LaunchAppInput
    required_capabilities = [CapabilityType.APPLICATIONS_LAUNCH.value]
    risk_level = ToolRiskLevel.LOCAL_MUTATION
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            if dry_run:
                return ToolResult(
                    success=True, data={"dry_run": True, "app": params["app_name"]}, dry_run=True
                )

            res = await DeviceContextService.launch_application(
                app_name=params["app_name"],
                arguments=params.get("arguments"),
            )
            return ToolResult(
                success=True, data=res, execution_time_ms=int((time.time() - t0) * 1000)
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )


class SendNotificationTool(BaseTool):
    name = "send_notification"
    description = "Dispatch a local desktop notification to the user."
    input_schema = SendNotificationInput
    required_capabilities = [CapabilityType.NOTIFICATIONS_SEND.value]
    risk_level = ToolRiskLevel.READ_ONLY
    requires_approval = False

    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        t0 = time.time()
        try:
            params = self.validate_parameters(parameters)
            res = await DeviceContextService.send_notification(
                title=params["title"],
                message=params["message"],
                subtitle=params.get("subtitle"),
            )
            return ToolResult(
                success=True, data=res, execution_time_ms=int((time.time() - t0) * 1000)
            )
        except Exception as e:
            return ToolResult(
                success=False, error=str(e), execution_time_ms=int((time.time() - t0) * 1000)
            )
