"""Unit tests for SQLAlchemy models, foreign keys, and FTS5 search."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message
from app.db.models.project import Project, ProjectDirectoryGrant
from app.domain.enums import MessageRole


@pytest.mark.asyncio
async def test_conversation_and_message_cascade(db_session: AsyncSession):
    conv = Conversation(title="Architecture Chat")
    db_session.add(conv)
    await db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content="What is FRIDAY architecture?",
    )
    msg2 = Message(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content="It is a modular, local-first backend.",
    )
    db_session.add_all([msg1, msg2])
    await db_session.commit()

    # Query back
    stmt = select(Conversation).where(Conversation.id == conv.id)
    saved_conv = (await db_session.execute(stmt)).scalars().first()
    assert saved_conv is not None
    assert len(saved_conv.messages) == 2
    assert saved_conv.messages[0].content == "What is FRIDAY architecture?"

    # Delete conversation and ensure messages cascade delete
    await db_session.delete(saved_conv)
    await db_session.commit()

    remaining_msgs = (
        (await db_session.execute(select(Message).where(Message.conversation_id == conv.id)))
        .scalars()
        .all()
    )
    assert len(remaining_msgs) == 0


@pytest.mark.asyncio
async def test_project_and_grants(db_session: AsyncSession):
    project = Project(name="Project-Alpha", root_path="/tmp/project-alpha")
    db_session.add(project)
    await db_session.flush()

    grant = ProjectDirectoryGrant(
        project_id=project.id,
        approved_path="/tmp/project-alpha/docs",
        read_only=True,
    )
    db_session.add(grant)
    await db_session.commit()

    stmt = select(Project).where(Project.name == "Project-Alpha")
    saved = (await db_session.execute(stmt)).scalars().first()
    assert saved is not None
    assert len(saved.directory_grants) == 1
    assert saved.directory_grants[0].read_only is True


@pytest.mark.asyncio
async def test_fts5_virtual_table_search(db_session: AsyncSession):
    # Insert test chunk into FTS5
    await db_session.execute(
        text(
            """
            INSERT INTO document_fts (chunk_id, project_id, file_path, content)
            VALUES (:chunk_id, :project_id, :file_path, :content)
            """
        ),
        {
            "chunk_id": "chunk-101",
            "project_id": "proj-1",
            "file_path": "docs/architecture.md",
            "content": "FRIDAY uses SQLite with FTS5 for lightning fast local full-text document search.",
        },
    )
    await db_session.commit()

    # Query using MATCH
    stmt = text(
        "SELECT chunk_id, file_path FROM document_fts WHERE document_fts MATCH 'lightning AND search'"
    )
    res = await db_session.execute(stmt)
    rows = res.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "chunk-101"
    assert rows[0][1] == "docs/architecture.md"
