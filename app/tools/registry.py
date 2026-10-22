"""Central tool registry with security policy and execution tracking."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, SecurityPolicyError
from app.db.models.approval import ApprovalRequest
from app.db.models.tool import ToolExecutionRecord
from app.domain.enums import ApprovalStatus
from app.tools.base import BaseTool, ToolResult
from app.tools.document_search import SearchProjectFilesTool
from app.tools.filesystem import ListFilesTool, ReadFileTool
from app.tools.git import GitDiffTool, GitStatusTool
from app.tools.security_analysis import SecurityScanTool
from app.tools.terminal import RunTerminalCommandTool


class ToolRegistry:
    """Registry maintaining available tools and mediating executions."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        # Register standard built-in tools
        self.register(ListFilesTool())
        self.register(ReadFileTool())
        self.register(GitStatusTool())
        self.register(GitDiffTool())
        self.register(RunTerminalCommandTool())
        self.register(SecurityScanTool())
        self.register(SearchProjectFilesTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if not tool:
            raise NotFoundError(f"Tool '{name}' is not registered.")
        return tool

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    async def execute_tool(
        self,
        name: str,
        parameters: dict[str, Any],
        session: AsyncSession | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        dry_run: bool = False,
    ) -> ToolResult:
        """Validate approval requirements, execute tool, and record audit trial."""
        tool = self.get_tool(name)

        # Check if tool requires approval and is not a dry-run
        if tool.requires_approval and not dry_run:
            if not approval_id:
                raise SecurityPolicyError(
                    f"Tool '{name}' requires human approval before execution. Request an approval first."
                )

            # Validate approval in database if session is provided
            if session:
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

        # Execute
        result = await tool.execute(parameters, dry_run=dry_run)

        # Persist execution record
        if session:
            record = ToolExecutionRecord(
                task_id=task_id,
                tool_name=name,
                parameters_redacted=parameters,
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
