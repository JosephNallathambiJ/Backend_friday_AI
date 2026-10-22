import json
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.api.v1 import (
    agent_state,
    agents,
    approvals,
    audio_api,
    capabilities,
    chat,
    commands,
    contacts,
    conversations,
    cyber_api,
    diagnostics_api,
    dual_brain_api,
    events,
    git,
    github,
    health,
    integrations,
    math_api,
    memory,
    projects,
    quick_actions,
    reports,
    schedules,
    security,
    skills,
    system,
    tasks,
    terminal,
    tools,
    voice,
)
from app.api.v1 import (
    settings as settings_api,
)
from app.domain.schemas import APIResponse, ChatRequest

api_router = APIRouter()

# Health endpoints (at root /health/live, /health/ready, /health, /api/v1/status, /api/v1/health)
api_router.include_router(health.router)

# Version 1 functional endpoints
api_router.include_router(system.router, prefix="/api/v1")
api_router.include_router(system.router, prefix="/api")
api_router.include_router(agent_state.router, prefix="/api/v1")
api_router.include_router(commands.router, prefix="/api/v1")
api_router.include_router(events.router, prefix="/api/v1")
api_router.include_router(terminal.router, prefix="/api/v1")
api_router.include_router(terminal.router, prefix="/api")
api_router.include_router(quick_actions.router, prefix="/api/v1")
api_router.include_router(quick_actions.router, prefix="/api")
api_router.include_router(agents.router, prefix="/api/v1")
api_router.include_router(capabilities.router, prefix="/api/v1")
api_router.include_router(contacts.router, prefix="/api/v1")
api_router.include_router(integrations.router, prefix="/api/v1")
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(projects.router)
api_router.include_router(memory.router)
api_router.include_router(tasks.router)
api_router.include_router(approvals.router)
api_router.include_router(tools.router)
api_router.include_router(git.router)
api_router.include_router(github.router)
api_router.include_router(security.router)
api_router.include_router(reports.router)
api_router.include_router(schedules.router)
api_router.include_router(voice.router)
api_router.include_router(settings_api.router)
api_router.include_router(skills.router)
api_router.include_router(math_api.router)
api_router.include_router(dual_brain_api.router)
api_router.include_router(cyber_api.router)
api_router.include_router(diagnostics_api.router)
api_router.include_router(audio_api.router)


@api_router.post("/api/chat", response_model=APIResponse, tags=["Chat & Orchestration"], dependencies=[Depends(verify_api_key)])
async def api_chat_alias(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute conversational chat through ChatbotAgent ('FRIDAY's Mouth') with specialist routing."""
    from app.agents.chatbot_agent import chatbot_agent

    res = await chatbot_agent.handle_message(
        message=payload.message,
        conversation_id=payload.conversation_id,
        session=db,
    )
    return APIResponse(
        success=True,
        data={
            "response": res.content,
            "content": res.content,
            "summary": res.summary,
            "message_id": res.message_id,
            "conversation_id": res.conversation_id,
            "routing": res.routing.model_dump(),
            "verified_facts": res.verified_facts,
            "hypotheses": res.hypotheses,
            "unknowns": res.unknowns,
            "detailed_data": res.detailed_data,
        },
    )


@api_router.get("/api/chat/conversations/{conversation_id}", response_model=APIResponse, tags=["Chat & Orchestration"])
async def api_get_conversation_alias(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Retrieve conversation details by ID for the HUD chatbot panel."""
    from app.domain.schemas import ConversationRead
    from app.services.conversation_service import ConversationService

    conv = await ConversationService.get_conversation(db, conversation_id)
    return APIResponse(
        success=True,
        data=ConversationRead(
            id=conv.id,
            title=conv.title,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages) if hasattr(conv, "messages") and conv.messages else 0,
        ),
    )


@api_router.get("/api/chat/conversations/{conversation_id}/messages", response_model=APIResponse, tags=["Chat & Orchestration"])
async def api_get_messages_alias(
    conversation_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Retrieve conversation messages for the HUD chatbot panel."""
    from app.domain.schemas import MessageRead
    from app.services.conversation_service import ConversationService

    messages = await ConversationService.get_messages(db, conversation_id, limit=limit)
    data = [
        MessageRead(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            metadata_json=m.metadata_json,
        )
        for m in messages
    ]
    return APIResponse(success=True, data=data)


@api_router.websocket("/api/chat/stream")
@api_router.websocket("/api/v1/chat/stream")
async def api_chat_stream_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    """Bidirectional WebSocket streaming for the right-hand Chatbot panel (ASK ANYTHING · FRIDAY A.I.)."""
    from app.core.config import settings

    if settings.API_KEY and token != settings.API_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    await websocket.accept()
    await websocket.send_json({
        "event": "chat.connected",
        "agent": "ChatbotAgent (FRIDAY's Mouth)",
        "status": "online",
        "title": "ASK ANYTHING · FRIDAY A.I.",
    })

    try:
        while True:
            message = await websocket.receive()
            if "text" not in message or not message["text"]:
                continue

            raw_text = message["text"].strip()
            user_msg = ""
            conv_id = f"conv-{uuid.uuid4().hex[:8]}"

            try:
                payload = json.loads(raw_text)
                if isinstance(payload, dict):
                    user_msg = payload.get("message", "") or payload.get("content", "")
                    conv_id = payload.get("conversation_id", conv_id)
                else:
                    user_msg = str(payload)
            except Exception:
                user_msg = raw_text

            if not user_msg:
                continue

            await websocket.send_json({
                "event": "chat.started",
                "conversation_id": conv_id,
            })

            from app.agents.chatbot_agent import chatbot_agent
            from app.db.session import async_session_factory

            async with async_session_factory() as db:
                res = await chatbot_agent.handle_message(
                    message=user_msg,
                    conversation_id=conv_id,
                    session=db,
                )

            # Stream delta chunk
            await websocket.send_json({
                "event": "chat.delta",
                "conversation_id": conv_id,
                "delta": res.content,
            })

            # Stream completion
            await websocket.send_json({
                "event": "chat.completed",
                "conversation_id": conv_id,
                "content": res.content,
                "summary": res.summary,
                "routing": res.routing.model_dump(),
                "verified_facts": res.verified_facts,
            })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"event": "chat.error", "detail": str(exc)})
            await websocket.close()
        except Exception:
            pass

