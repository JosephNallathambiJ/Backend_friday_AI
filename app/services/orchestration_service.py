"""Bounded AI Orchestration service coordinating model, tools, and memory."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.domain.enums import MessageRole, TaskStatus
from app.domain.protocols import ChatMessage
from app.domain.schemas import ChatRequest
from app.providers.registry import provider_registry
from app.services.approval_service import ApprovalService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.task_service import TaskService
from app.tools.registry import tool_registry


class OrchestrationService:
    @staticmethod
    async def process_chat(
        session: AsyncSession,
        request: ChatRequest,
    ) -> dict[str, Any]:
        """Execute bounded orchestration loop for a conversation turn."""
        conversation = await ConversationService.get_conversation(session, request.conversation_id)

        # 1. Create a tracking task
        task = await TaskService.create_task(
            session=session,
            task_type="chat_orchestration",
            summary=f"Chat message: {request.message[:50]}...",
            project_id=conversation.project_id,
            parameters={"conversation_id": conversation.id},
        )
        await TaskService.update_status(
            session, task.id, TaskStatus.RUNNING, "Starting orchestration loop."
        )

        # 2. Persist user message
        await ConversationService.add_message(
            session=session,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )

        # 3. Retrieve context: project memory & document snippets
        context_snippets: list[str] = []
        if conversation.project_id:
            # Memory
            memories = await MemoryService.list_memories(
                session, project_id=conversation.project_id
            )
            if memories:
                context_snippets.append("PROJECT MEMORY:")
                for m in memories[:3]:
                    context_snippets.append(f"- [{m.key}]: {m.content}")

            # RAG via FTS5
            docs = await RetrievalService.search(
                session, query=request.message, project_id=conversation.project_id, limit=3
            )
            if docs:
                context_snippets.append("RELEVANT PROJECT DOCUMENTS:")
                for d in docs:
                    context_snippets.append(f"- Source {d['file_path']}:\n  {d['content'][:300]}")

        # 4. Prepare message history
        recent_msgs = await ConversationService.get_messages(session, conversation.id, limit=10)
        messages: list[ChatMessage] = []

        # System prompt
        system_content = (
            request.system_prompt
            or "You are FRIDAY AI, an intelligent, security-first work assistant."
        )
        if context_snippets:
            system_content += "\n\n" + "\n".join(context_snippets)

        messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_content))

        for msg in recent_msgs:
            messages.append(
                ChatMessage(
                    role=msg.role,
                    content=msg.content,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                )
            )

        # 5. Format available tools for Ollama/provider
        tools_spec: list[dict[str, Any]] | None = None
        if request.enable_tools:
            available_tools = tool_registry.list_tools()
            tools_spec = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters_schema,
                    },
                }
                for t in available_tools
            ]

        # 6. Execute bounded loop (max steps)
        provider = provider_registry.get()
        model_name = request.model or settings.DEFAULT_LOCAL_MODEL
        step = 0
        final_content = ""
        approval_request_info = None

        while step < settings.MAX_ORCHESTRATION_STEPS:
            step += 1
            await TaskService.update_status(
                session,
                task.id,
                TaskStatus.RUNNING,
                f"Orchestration step {step}: calling model {model_name}",
            )

            response = await provider.chat_complete(
                messages=messages,
                model=model_name,
                temperature=request.temperature or 0.7,
                tools=tools_spec,
            )

            # Check if model proposed a tool call
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                fn = tool_call.get("function", {})
                tool_name = fn.get("name")
                tool_args = fn.get("arguments", {})

                logger.info(f"Model proposed tool: {tool_name} with args: {tool_args}")
                tool_instance = tool_registry.get_tool(tool_name)

                # Check if approval is required
                if tool_instance.requires_approval:
                    approval = await ApprovalService.create_approval_request(
                        session=session,
                        task_id=task.id,
                        tool_name=tool_name,
                        action_description=f"Model proposed executing {tool_name} with parameters: {tool_args}",
                        risk_level=tool_instance.risk_level,
                        arguments=tool_args,
                    )
                    await TaskService.update_status(
                        session,
                        task.id,
                        TaskStatus.AWAITING_APPROVAL,
                        f"Awaiting approval for {tool_name} (ID: {approval.id})",
                    )
                    approval_request_info = {
                        "approval_id": approval.id,
                        "tool_name": tool_name,
                        "status": "awaiting_approval",
                    }
                    final_content = (
                        f"Action required: The tool '{tool_name}' requires approval before execution. "
                        f"Approval request ID: {approval.id}"
                    )
                    break

                # Execute tool directly if read-only
                tool_res = await tool_registry.execute_tool(
                    name=tool_name,
                    parameters=tool_args,
                    session=session,
                    task_id=task.id,
                )

                # Append assistant tool call proposal and tool result to messages
                messages.append(
                    ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content="",
                        tool_calls=[tool_call],
                    )
                )
                messages.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        content=str(
                            tool_res.data if tool_res.success else f"Tool Error: {tool_res.error}"
                        ),
                        name=tool_name,
                    )
                )
                continue

            # Model produced a text response
            final_content = response.content
            break

        # 7. Persist assistant message
        assistant_msg = await ConversationService.add_message(
            session=session,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=final_content,
            metadata_json={"steps": step, "task_id": task.id},
        )

        if not approval_request_info:
            await TaskService.update_status(
                session=session,
                task_id=task.id,
                status=TaskStatus.SUCCEEDED,
                current_step="Completed successfully.",
                result_data={"response_message_id": assistant_msg.id},
            )

        return {
            "conversation_id": conversation.id,
            "message_id": assistant_msg.id,
            "content": final_content,
            "task_id": task.id,
            "approval_required": approval_request_info,
            "steps": step,
        }
