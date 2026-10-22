"""Main API router combining all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import (
    approvals,
    chat,
    conversations,
    git,
    github,
    health,
    memory,
    projects,
    reports,
    schedules,
    security,
    tasks,
    tools,
    voice,
)
from app.api.v1 import (
    settings as settings_api,
)

api_router = APIRouter()

# Health endpoints (at root /health/live, /health/ready, /api/v1/status)
api_router.include_router(health.router)

# Version 1 functional endpoints
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
