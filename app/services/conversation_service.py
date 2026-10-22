"""Conversation and message management service."""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.conversation import Conversation, Message
from app.domain.enums import MessageRole


class ConversationService:
    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        title: str = "New Conversation",
        project_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(title=title, project_id=project_id)
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def list_conversations(
        session: AsyncSession,
        project_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        query = (
            select(Conversation).order_by(desc(Conversation.updated_at)).offset(offset).limit(limit)
        )
        if project_id:
            query = query.where(Conversation.project_id == project_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_conversation(session: AsyncSession, conversation_id: str) -> Conversation:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()
        if not conversation:
            raise NotFoundError(f"Conversation '{conversation_id}' not found.")
        return conversation

    @staticmethod
    async def update_conversation(
        session: AsyncSession,
        conversation_id: str,
        title: str,
    ) -> Conversation:
        conversation = await ConversationService.get_conversation(session, conversation_id)
        conversation.title = title
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(session: AsyncSession, conversation_id: str) -> None:
        conversation = await ConversationService.get_conversation(session, conversation_id)
        await session.delete(conversation)
        await session.commit()

    @staticmethod
    async def add_message(
        session: AsyncSession,
        conversation_id: str,
        role: MessageRole,
        content: str,
        tool_call_id: str | None = None,
        name: str | None = None,
        metadata_json: dict | None = None,
    ) -> Message:
        await ConversationService.get_conversation(session, conversation_id)
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            name=name,
            metadata_json=metadata_json,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        session: AsyncSession,
        conversation_id: str,
        limit: int = 100,
    ) -> list[Message]:
        await ConversationService.get_conversation(session, conversation_id)
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
