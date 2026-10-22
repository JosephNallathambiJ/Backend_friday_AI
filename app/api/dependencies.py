"""FastAPI request dependencies for database session and security authentication."""

from collections.abc import AsyncGenerator

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional asynchronous database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> str:
    """Validate API key if configured in settings. Local loopback requests can proceed if API_KEY is unset."""
    if settings.API_KEY:
        if not x_api_key or x_api_key != settings.API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key (X-API-Key header required).",
            )
    return "local_user"
