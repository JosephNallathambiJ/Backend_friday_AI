"""Quick-Action Registry and Execution Service for the HUD interface."""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.providers.registry import provider_registry
from app.services.activity_service import activity_service
from app.services.system_service import SystemService
from app.services.task_service import TaskService


class QuickActionDefinition(BaseModel):
    """Metadata schema for HUD quick-actions."""

    id: str
    label: str
    description: str
    category: str
    required_capability: str | None = None
    requires_approval: bool = False
    is_enabled: bool = True
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class QuickActionService:
    """Registry and executor for HUD tactical quick actions."""

    _actions: dict[str, QuickActionDefinition] = {}

    @classmethod
    def register(cls, action: QuickActionDefinition) -> None:
        cls._actions[action.id] = action

    @classmethod
    def list_actions(cls) -> list[QuickActionDefinition]:
        return list(cls._actions.values())

    @classmethod
    def get_action(cls, action_id: str) -> QuickActionDefinition:
        if action_id not in cls._actions:
            raise NotFoundError(f"Quick action '{action_id}' not found.")
        return cls._actions[action_id]

    @classmethod
    async def execute_action(
        cls,
        session: AsyncSession,
        action_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute registered action handler with normal system permissions."""
        action = cls.get_action(action_id)
        if not action.is_enabled:
            raise ValidationError(f"Quick action '{action_id}' is currently disabled.")

        if action_id == "diagnostics.run":
            diagnostics = await SystemService.get_diagnostics(session)
            return {"action_id": action_id, "result": diagnostics}

        elif action_id == "system.status_summary":
            status_data = await SystemService.get_system_status(session)
            return {"action_id": action_id, "result": status_data}

        elif action_id == "capabilities.list":
            caps = await SystemService.get_capabilities(session)
            return {"action_id": action_id, "result": {"total": len(caps), "capabilities": caps}}

        elif action_id == "model.info":
            ollama = provider_registry.get("ollama")
            healthy = await ollama.check_health()
            models = await ollama.list_models() if healthy else []
            return {
                "action_id": action_id,
                "result": {
                    "provider": "ollama",
                    "base_url": settings.OLLAMA_BASE_URL,
                    "connected": healthy,
                    "configured_default_model": settings.DEFAULT_LOCAL_MODEL,
                    "available_models": models,
                },
            }

        elif action_id == "agent.activity":
            state = activity_service.get_state()
            return {"action_id": action_id, "result": state.model_dump(mode="json")}

        elif action_id == "tasks.recent_history":
            tasks = await TaskService.list_tasks(session=session, limit=10)
            return {
                "action_id": action_id,
                "result": [
                    {
                        "id": t.id,
                        "type": t.task_type,
                        "summary": t.summary,
                        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in tasks
                ],
            }

        elif action_id == "assistant.explain":
            return {
                "action_id": action_id,
                "result": {
                    "name": settings.APP_NAME,
                    "identity": "Tactical Defense HUD Personal AI Assistant",
                    "architecture": "Cyber AI Architecture with Local LLM Orchestration",
                    "version": settings.APP_VERSION,
                    "description": (
                        "FRIDAY is a production-minded personal AI assistant operating on "
                        "a local-first cyber architecture. It executes tactical commands, manages "
                        "controlled terminal sessions, verifies security policies, and streams "
                        "real-time HUD telemetry."
                    ),
                },
            }

        elif action_id == "assistant.help":
            return {
                "action_id": action_id,
                "result": {
                    "supported_interfaces": [
                        "Tactical natural language commands via /api/v1/commands",
                        "Controlled terminal commands via /api/v1/terminal/sessions",
                        "Real-time HUD event stream via WS /api/v1/events",
                        "Voice audio transcription & synthesis via /api/v1/voice/*",
                        "Configurable settings and options via /api/v1/settings",
                    ],
                    "example_commands": [
                        "system status",
                        "list files in workspace",
                        "run test suite",
                        "search documents for deployment",
                        "git status",
                    ],
                },
            }

        raise NotFoundError(f"No execution handler registered for '{action_id}'.")


# Seed predefined HUD quick-actions
QuickActionService.register(
    QuickActionDefinition(
        id="diagnostics.run",
        label="Run Diagnostics",
        description="Execute full component latency, health, and configuration diagnostics.",
        category="System",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="system.status_summary",
        label="Status Summary",
        description="Summarize overall backend, AI model, and database status.",
        category="System",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="capabilities.list",
        label="List Capabilities",
        description="Inspect all registered tools, risk levels, and permission policies.",
        category="Security",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="model.info",
        label="Model Info",
        description="Inspect configured local LLM provider, weights, and readiness.",
        category="AI",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="agent.activity",
        label="Agent Activity",
        description="Retrieve current visualizer activity state and ongoing step.",
        category="Agent",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="tasks.recent_history",
        label="Recent Tasks",
        description="Retrieve recent task execution history and outcomes.",
        category="Tasks",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="assistant.explain",
        label="Explain FRIDAY",
        description="Return overview of FRIDAY AI cyber architecture and capabilities.",
        category="Help",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="assistant.help",
        label="Commands & Help",
        description="Display supported tactical command syntax and execution modes.",
        category="Help",
    )
)
