"""Chat endpoints for non-streaming, SSE streaming, and cancellation."""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.core.config import settings
from app.domain.enums import MessageRole, TaskStatus
from app.domain.protocols import ChatMessage
from app.domain.schemas import APIResponse, ChatRequest
from app.providers.registry import provider_registry
from app.services.conversation_service import ConversationService
from app.services.orchestration_service import OrchestrationService
from app.services.task_service import TaskService

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat & Orchestration"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=APIResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute non-streaming chat turn through bounded orchestrator."""
    result = await OrchestrationService.process_chat(session=db, request=payload)
    return APIResponse(data=result)


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream model response using Server-Sent Events (SSE)."""
    conversation = await ConversationService.get_conversation(db, payload.conversation_id)

    # Create task
    task = await TaskService.create_task(
        session=db,
        task_type="chat_stream",
        summary=f"Streaming: {payload.message[:50]}",
        project_id=conversation.project_id,
    )

    # Persist user message
    await ConversationService.add_message(
        session=db,
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=payload.message,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        accumulated_text = []
        yield f"event: message_start\ndata: {json.dumps({'task_id': task.id, 'conversation_id': conversation.id})}\n\n"

        try:
            # Build messages
            recent_msgs = await ConversationService.get_messages(db, conversation.id, limit=8)
            messages = [ChatMessage(role=m.role, content=m.content) for m in recent_msgs]

            provider = provider_registry.get()
            model_name = payload.model or settings.DEFAULT_LOCAL_MODEL

            async for chunk in provider.stream_chat(
                messages=messages,
                model=model_name,
                temperature=payload.temperature or 0.7,
            ):
                if chunk.content_delta:
                    accumulated_text.append(chunk.content_delta)
                    yield f"event: text_delta\ndata: {json.dumps({'delta': chunk.content_delta})}\n\n"

            final_text = "".join(accumulated_text)

            # Persist assistant response
            await ConversationService.add_message(
                session=db,
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=final_text,
            )
            await TaskService.update_status(
                session=db,
                task_id=task.id,
                status=TaskStatus.SUCCEEDED,
                current_step="Stream completed",
            )

            yield f"event: message_completed\ndata: {json.dumps({'total_length': len(final_text)})}\n\n"

        except Exception as e:
            try:
                await TaskService.update_status(
                    session=db,
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error_message=str(e),
                )
            except Exception:
                pass
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{task_id}/cancel", response_model=APIResponse)
async def cancel_chat(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Request immediate cancellation of a running task/chat generation."""
    task = await TaskService.cancel_task(db, task_id)
    return APIResponse(data={"cancelled": True, "task_id": task.id, "status": task.status})
