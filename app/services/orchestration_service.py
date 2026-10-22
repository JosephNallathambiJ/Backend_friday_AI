"""Bounded AI Orchestration service coordinating model, tools, and memory."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import MessageRole, TaskStatus
from app.domain.protocols import ChatMessage
from app.domain.schemas import ChatRequest
from app.services.brain_service import FridayBrain
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.task_service import TaskService


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

        # 5. Execute unified reasoning & tool execution via FridayBrain
        brain_result = await FridayBrain.execute_tool_calling_loop(
            session=session,
            initial_prompt=request.message,
            conversation_id=conversation.id,
            task_id=task.id,
            max_iterations=settings.MAX_ORCHESTRATION_STEPS,
        )

        final_content = brain_result.get("final_response", "Operation completed.")
        approval_request_info = None
        if brain_result.get("approval_required"):
            approval_request_info = {
                "approval_id": brain_result.get("approval_id"),
                "tool_name": brain_result.get("tool"),
                "status": "awaiting_approval",
            }
            await TaskService.update_status(
                session,
                task.id,
                TaskStatus.AWAITING_APPROVAL,
                f"Awaiting approval for {brain_result.get('tool')}",
            )

        # 6. Persist assistant message
        assistant_msg = await ConversationService.add_message(
            session=session,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=final_content,
            metadata_json={"steps": brain_result.get("iterations", 1), "task_id": task.id},
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
            "steps": brain_result.get("iterations", 1),
        }
