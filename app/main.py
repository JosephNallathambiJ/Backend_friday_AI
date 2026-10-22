"""FRIDAY AI Backend entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.automation.scheduler import scheduler
from app.core.config import settings
from app.core.logging import logger
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.init_db import init_database, seed_default_tools
from app.db.session import async_session_factory, engine
from app.providers.registry import provider_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and graceful shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]...")

    # 1. Initialize SQLite tables and FTS5 full-text index
    await init_database()

    # 2. Seed default tool definitions
    async with async_session_factory() as session:
        await seed_default_tools(session)

    # 3. Check Ollama local AI provider availability
    ollama = provider_registry.get("ollama")
    if await ollama.check_health():
        models = await ollama.list_models()
        logger.info(f"Ollama connected. Available local models: {models}")
    else:
        logger.warning(
            f"Ollama is not responding at {settings.OLLAMA_BASE_URL}. "
            "Local AI chat will be unavailable until Ollama is started."
        )

    # 4. Start background scheduler
    if settings.SCHEDULER_ENABLED:
        await scheduler.start()

    logger.info("FRIDAY AI Backend startup complete.")
    yield

    # Shutdown
    logger.info("Initiating graceful shutdown...")
    if settings.SCHEDULER_ENABLED:
        await scheduler.stop()
    await engine.dispose()
    logger.info("FRIDAY AI Backend shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-minded, local-first backend for personal AI work assistant FRIDAY AI.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Defensive middleware: Security headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS: Restricted to local loopback origins by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Include versioned API routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
