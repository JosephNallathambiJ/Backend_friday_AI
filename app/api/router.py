"""Main API router combining all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import (
    agent_state,
    agents,
    approvals,
    capabilities,
    chat,
    commands,
    contacts,
    conversations,
    events,
    git,
    github,
    health,
    integrations,
    memory,
    projects,
    quick_actions,
    reports,
    schedules,
    security,
    system,
    tasks,
    terminal,
    tools,
    voice,
)
from app.api.v1 import (
    settings as settings_api,
)

api_router = APIRouter()

# Health endpoints (at root /health/live, /health/ready, /health, /api/v1/status, /api/v1/health)
api_router.include_router(health.router)

# Version 1 functional endpoints
api_router.include_router(system.router, prefix="/api/v1")
api_router.include_router(agent_state.router, prefix="/api/v1")
api_router.include_router(commands.router, prefix="/api/v1")
api_router.include_router(events.router, prefix="/api/v1")
api_router.include_router(terminal.router, prefix="/api/v1")
api_router.include_router(quick_actions.router, prefix="/api/v1")
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
