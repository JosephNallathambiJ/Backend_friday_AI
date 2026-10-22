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
from app.tools.device import (
    GetSystemInfoTool,
    LaunchApplicationTool,
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
        self.register(SearchContactsTool())
        self.register(CreateContactTool())
        self.register(DeleteContactTool())

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

    def get_tool(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if not tool or not self.is_tool_enabled(name):
            raise NotFoundError(f"Tool '{name}' is not registered or is disabled.")
        return tool

    def list_tools(self) -> list[BaseTool]:
        return [tool for name, tool in self._tools.items() if self.is_tool_enabled(name)]

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

        # 2. Policy Engine Evaluation (Capabilities + Risk Level)
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

        # 3. Execution
        result = await tool.execute(validated_params, dry_run=dry_run)

        # 4. Audit & History Record
        if session:
            record = ToolExecutionRecord(
                task_id=task_id,
                tool_name=name,
                parameters_redacted=validated_params,
                result_data=result.data if result.success else None,
                error_message=result.error if not result.success else None,
                execution_time_ms=result.execution_time_ms,
                dry_run=dry_run,
                approval_id=approval_id,
            )
            session.add(record)
            await session.commit()

        return result


tool_registry = ToolRegistry()
