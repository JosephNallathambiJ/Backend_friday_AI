"""Conversation management API endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import (
    APIResponse,
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
)
from app.services.conversation_service import ConversationService

router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Conversations"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    conv = await ConversationService.create_conversation(
        session=db,
        title=payload.title or "New Conversation",
        project_id=payload.project_id,
    )
    return APIResponse(
        data=ConversationRead(
            id=conv.id,
            title=conv.title,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=0,
        )
    )


@router.get("", response_model=APIResponse)
async def list_conversations(
    project_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    convs = await ConversationService.list_conversations(
        session=db,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    data = [
        ConversationRead(
            id=c.id,
            title=c.title,
            project_id=c.project_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=len(c.messages) if hasattr(c, "messages") and c.messages else 0,
        )
        for c in convs
    ]
    return APIResponse(data=data)


@router.get("/{conversation_id}", response_model=APIResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    conv = await ConversationService.get_conversation(db, conversation_id)
    return APIResponse(
        data=ConversationRead(
            id=conv.id,
            title=conv.title,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(conv.messages) if hasattr(conv, "messages") and conv.messages else 0,
        )
    )


@router.patch("/{conversation_id}", response_model=APIResponse)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    conv = await ConversationService.update_conversation(
        session=db,
        conversation_id=conversation_id,
        title=payload.title or "Untitled",
    )
    return APIResponse(
        data=ConversationRead(
            id=conv.id,
            title=conv.title,
            project_id=conv.project_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
    )


@router.delete("/{conversation_id}", response_model=APIResponse)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    await ConversationService.delete_conversation(db, conversation_id)
    return APIResponse(data={"deleted": True, "conversation_id": conversation_id})


@router.get("/{conversation_id}/messages", response_model=APIResponse)
async def get_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
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
    return APIResponse(data=data)


@router.post(
    "/{conversation_id}/messages", response_model=APIResponse, status_code=status.HTTP_201_CREATED
)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    msg = await ConversationService.add_message(
        session=db,
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
        tool_call_id=payload.tool_call_id,
        name=payload.name,
    )
    return APIResponse(
        data=MessageRead(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            metadata_json=msg.metadata_json,
        )
    )
