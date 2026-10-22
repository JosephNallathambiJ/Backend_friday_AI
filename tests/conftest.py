"""Pytest configuration and shared test fixtures."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db
from app.db.base import Base
from app.db.init_db import seed_default_tools
from app.domain.protocols import (
    ChatCompletionResponse,
    ChatMessage,
    StreamChunk,
)
from app.main import app
from app.providers.base import BaseAIProvider
from app.providers.registry import provider_registry

# Test SQLite in-memory or temp file
TEST_DB_PATH = Path("./test_friday.db").resolve()
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30.0},
)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class MockAIProvider(BaseAIProvider):
    """Deterministic mock provider for automated tests."""

    name = "mock"

    def __init__(
        self, response_text: str = "Mocked model response", tool_calls: list[dict] | None = None
    ):
        self.response_text = response_text
        self.tool_calls = tool_calls

    async def check_health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["mock-model-v1"]

    async def chat_complete(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
    ) -> ChatCompletionResponse:
        return ChatCompletionResponse(
            content=self.response_text,
            tool_calls=self.tool_calls,
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
    ):
        yield StreamChunk(content_delta="Hello ", finish_reason=None)
        yield StreamChunk(content_delta="from ", finish_reason=None)
        yield StreamChunk(content_delta="FRIDAY!", finish_reason="stop")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create test database schema, FTS5 virtual table, and default tools."""
    # Ensure test DB file is removed before run
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # FTS5
        from sqlalchemy import text

        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
                    chunk_id UNINDEXED,
                    project_id UNINDEXED,
                    file_path,
                    content,
                    tokenize = 'porter unicode61'
                );
                """
            )
        )

    async with test_session_factory() as session:
        await seed_default_tools(session)

    yield

    # Teardown
    await test_engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with overridden database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Register mock provider for deterministic tests
    mock_provider = MockAIProvider()
    provider_registry.register(mock_provider)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
