"""Central tool registry with capability policy checking and execution tracking."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, SecurityPolicyError
from app.db.models.approval import ApprovalRequest
from app.db.models.tool import ToolExecutionRecord
from app.domain.enums import ApprovalStatus, PolicyOutcome
from app.security.policy import PolicyEngine
from app.tools.base import BaseTool, ToolResult
from app.tools.browser import (
    BrowserCloseTool,
    BrowserInteractTool,
    BrowserNavigateTool,
    BrowserReadTool,
    FetchWebpageTool,
    WebSearchTool,
)
from app.tools.contacts import (
    CreateContactTool,
    DeleteContactTool,
    SearchContactsTool,
)
from app.tools.cyber_tools import (
    AuthorizedPortDiscoveryTool,
    DependencyAuditTool,
    HttpSecurityAuditTool,
    PassiveDomainReconTool,
    SecretDetectionTool,
    SecurityReportTool,
)
from app.tools.device import (
    GetSystemInfoTool,
    LaunchApplicationTool,
    RunDiagnosticsTool,
    SendNotificationTool,
)
from app.tools.document_search import SearchProjectFilesTool
from app.tools.filesystem import (
    CopyFileTool,
    DeleteFileTool,
    GetFileMetadataTool,
    ListFilesTool,
    MoveFileTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)
from app.tools.git import GitDiffTool, GitStatusTool
from app.tools.math_tools import (
    AnalyzeStatisticsTool,
    CalculateTool,
    ComputeMatrixTool,
    ConvertUnitsTool,
    DifferentiateTool,
    IntegrateTool,
    SimplifyTool,
    SolveEquationTool,
)
from app.tools.security_analysis import SecurityScanTool
from app.tools.terminal import RunTerminalCommandTool


class ToolRegistry:
    """Registry maintaining available tools, checking permissions, and tracking executions."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._enabled_state: dict[str, bool] = {}

        # Filesystem tools
        self.register(ListFilesTool())
        self.register(ReadFileTool())
        self.register(SearchFilesTool())
        self.register(GetFileMetadataTool())
        self.register(WriteFileTool())
        self.register(CopyFileTool())
        self.register(MoveFileTool())
        self.register(DeleteFileTool())

        # Git tools
        self.register(GitStatusTool())
        self.register(GitDiffTool())

        # Terminal & Security tools
        self.register(RunTerminalCommandTool())
        self.register(SecurityScanTool())
        self.register(SearchProjectFilesTool())

        # Mathematical tools (Master Prompt 7)
        self.register(CalculateTool())
        self.register(SimplifyTool())
        self.register(SolveEquationTool())
        self.register(DifferentiateTool())
        self.register(IntegrateTool())
        self.register(ComputeMatrixTool())
        self.register(AnalyzeStatisticsTool())
        self.register(ConvertUnitsTool())

        # Web & Browser tools
        self.register(WebSearchTool())
        self.register(FetchWebpageTool())
        self.register(BrowserNavigateTool())
        self.register(BrowserReadTool())
        self.register(BrowserInteractTool())
        self.register(BrowserCloseTool())

        # Device & Contacts tools
        self.register(GetSystemInfoTool())
        self.register(LaunchApplicationTool())
        self.register(SendNotificationTool())
        self.register(RunDiagnosticsTool())
        self.register(SearchContactsTool())
        self.register(CreateContactTool())
        self.register(DeleteContactTool())

        # Cyber & Intelligence tools (Master Prompt 8)
        self.register(PassiveDomainReconTool())
        self.register(HttpSecurityAuditTool())
        self.register(AuthorizedPortDiscoveryTool())
        self.register(DependencyAuditTool())
        self.register(SecretDetectionTool())
        self.register(SecurityReportTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        self._enabled_state[tool.name] = True

    def enable_tool(self, name: str) -> None:
        if name in self._tools:
            self._enabled_state[name] = True

    def disable_tool(self, name: str) -> None:
        if name in self._tools:
            self._enabled_state[name] = False

    def is_tool_enabled(self, name: str) -> bool:
        return self._enabled_state.get(name, True)

    def get(self, name: str, available_only: bool = False) -> BaseTool | None:
        if not self.is_tool_enabled(name):
            return None
        tool = self._tools.get(name)
        if tool and available_only:
            avail = tool.check_availability()
            if not avail.get("available", True):
                return None
        return tool

    def get_tool(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if not tool or not self.is_tool_enabled(name):
            raise NotFoundError(f"Tool '{name}' is not registered or is disabled.")
        return tool

    def list_tools(self, available_only: bool = False) -> list[BaseTool]:
        tools = [tool for name, tool in self._tools.items() if self.is_tool_enabled(name)]
        if available_only:
            tools = [t for t in tools if t.check_availability().get("available", True)]
        return tools

    def diagnose_all_tools(self) -> list[dict[str, Any]]:
        """Return truthful capability inventory and diagnostics for every registered tool."""
        results = []
        for name, tool in self._tools.items():
            enabled = self.is_tool_enabled(name)
            avail = tool.check_availability()
            is_avail = avail.get("available", True)
            status_tag = (
                "IMPLEMENTED_AND_TESTED"
                if (enabled and is_avail and not tool.is_mock)
                else ("NOT_CONFIGURED" if not is_avail else "DISABLED")
            )
            if tool.is_mock:
                status_tag = "MOCKED"

            results.append({
                "name": name,
                "description": tool.description,
                "enabled": enabled,
                "available": is_avail,
                "capability_status": status_tag,
                "reason": avail.get("reason"),
                "risk_level": tool.risk_level.value if hasattr(tool.risk_level, "value") else str(tool.risk_level),
                "is_mock": tool.is_mock,
                "requires_approval": tool.requires_approval,
                "required_capabilities": tool.required_capabilities,
                "timeout_seconds": tool.timeout_seconds,
                "idempotent": tool.idempotent,
            })
        return results

    async def execute_tool(
        self,
        name: str,
        parameters: dict[str, Any],
        session: AsyncSession | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        dry_run: bool = False,
        scope_type: str = "global",
        scope_value: str = "*",
    ) -> ToolResult:
        """Execute a tool with full validation, capability policy check, approval gating, and audit logging."""
        tool = self.get_tool(name)

        # 1. Parameter Schema Validation
        validated_params = tool.validate_parameters(parameters)

        # 2. Check Tool Capability Availability
        avail = tool.check_availability()
        if not avail.get("available", True) and not dry_run:
            return ToolResult(
                success=False,
                error=f"Capability unavailable: {avail.get('reason', 'Integration not configured.')}",
                execution_time_ms=0,
                verified=False,
                verification_details=f"Availability check failed: {avail.get('status', 'NOT_CONFIGURED')}",
            )

        # 3. Policy Engine Evaluation (Capabilities + Risk Level)
        if session:
            eval_result = await PolicyEngine.evaluate_action(
                db=session,
                tool_name=name,
                risk_level=tool.risk_level,
                required_capabilities=tool.required_capabilities,
                parameters=validated_params,
                requires_approval=tool.requires_approval,
                scope_type=scope_type,
                scope_value=scope_value,
            )

            if eval_result.outcome == PolicyOutcome.DENY:
                raise SecurityPolicyError(eval_result.reason)

            if eval_result.outcome == PolicyOutcome.REQUIRE_APPROVAL and not dry_run:
                if not approval_id:
                    raise SecurityPolicyError(
                        f"Action '{name}' requires human approval: {eval_result.reason}"
                    )

                # Validate approval in database
                from sqlalchemy import select

                stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
                approval = (await session.execute(stmt)).scalars().first()

                if not approval:
                    raise NotFoundError(f"Approval request '{approval_id}' not found.")
                if approval.status != ApprovalStatus.APPROVED:
                    raise SecurityPolicyError(
                        f"Approval request status is '{approval.status}', not 'approved'."
                    )
                if approval.tool_name != name:
                    raise SecurityPolicyError(
                        f"Approval was granted for '{approval.tool_name}', not '{name}'."
                    )

                # Mark as executed race-safely
                approval.status = ApprovalStatus.EXECUTED
                await session.commit()

        # 4. Execution
        result = await tool.execute(validated_params, dry_run=dry_run)

        # 5. Result Validation (verify expected outcome on disk / process / network)
        result = tool.validate_result(result, validated_params)

        # 6. Audit & History Record
        if session:
            record_data = None
            if result.success and result.data is not None:
                if isinstance(result.data, dict):
                    record_data = {
                        **result.data,
                        "_verified": result.verified,
                        "_verification_details": result.verification_details,
                        "_resource_references": result.resource_references,
                    }
                else:
                    record_data = {
                        "output": result.data,
                        "_verified": result.verified,
                        "_verification_details": result.verification_details,
                        "_resource_references": result.resource_references,
                    }

            import json

            if record_data is not None:
                record_data = json.loads(json.dumps(record_data, default=str))

            safe_params = json.loads(json.dumps(validated_params, default=str)) if validated_params else {}

            record = ToolExecutionRecord(
                task_id=task_id,
                tool_name=name,
                parameters_redacted=safe_params,
                result_data=record_data,
                error_message=result.error if not result.success else None,
                execution_time_ms=result.execution_time_ms,
                dry_run=dry_run,
                approval_id=approval_id,
            )
            session.add(record)
            await session.commit()

        return result


tool_registry = ToolRegistry()
