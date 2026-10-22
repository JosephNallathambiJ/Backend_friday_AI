"""Quick-Action Registry and Execution Service for the HUD interface."""

from typing import Any
from uuid import uuid4

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
        if action_id in cls._actions:
            return cls._actions[action_id]

        norm = action_id.lower().replace("-", "_").replace("?", "").replace(" ", "_").strip()
        if norm in cls._actions:
            return cls._actions[norm]

        for act in cls._actions.values():
            if act.label.lower() == action_id.lower() or act.id.lower() == norm:
                return act

        raise NotFoundError(f"Quick action '{action_id}' not found.")

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

        elif action.id in {"arc_telemetry", "arc-telemetry"}:
            status_data = await SystemService.get_system_status(session)
            tasks = await TaskService.list_tasks(session=session, limit=10)
            running_tasks = [t for t in tasks if getattr(t, "status", None) and str(t.status) == "running"]
            return {
                "action_id": action.id,
                "label": "Arc Telemetry",
                "result": {
                    "frequency": "1420.405 MHz",
                    "quantum_matrix": "SYNCED",
                    "grid_protocol": "v8.4",
                    "system_status": status_data.get("status", "online").upper(),
                    "uptime_seconds": status_data.get("application", {}).get("uptime_seconds", 0),
                    "active_tasks_count": len(running_tasks),
                    "ai_provider": status_data.get("ai_provider", {}),
                    "memory_percent": status_data.get("system_metrics", {}).get("memory_percent", 0.0),
                    "cpu_percent": status_data.get("system_metrics", {}).get("cpu_percent", 0.0),
                },
            }

        elif action.id in {"who_made_you", "who-made-you"}:
            return {
                "action_id": action.id,
                "label": "Who Made You?",
                "result": {
                    "identity": "FRIDAY (GOJO Enterprise Edition)",
                    "creator": "GOJO",
                    "system": "GOJO OS v8.4.2 (Gojo Enterprise Edition)",
                    "host": "Gojo Technologies Hub",
                    "user": "gojo (UID: 1000 • Standard User Session)",
                    "founder": "GOJO",
                    "architecture": "Dual-Brain Tactical AI Cyber Architecture",
                    "left_brain": "LiquidAI/lfm2.5-2.6b:q4_k_m (Tactical Planning & General Tasks)",
                    "right_brain": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M (Defensive Cybersecurity)",
                    "statement": (
                        "I am FRIDAY, created by GOJO for the GOJO Enterprise Tactical Defense HUD. "
                        "I operate on an advanced Dual-Brain AI Cyber Architecture providing tactical command "
                        "execution, system diagnostics, and autonomous defensive cybersecurity."
                    ),
                },
            }

        elif action.id in {"blue_team", "blue-team"}:
            from app.agents.cyber_agent import cyber_agent

            res = await cyber_agent.execute(
                task_id=f"blue-team-{uuid4().hex[:6]}",
                goal="Execute Blue Team defensive perimeter audit and security posture review",
                parameters={"target": "127.0.0.1", "action": "defensive_posture"},
                session=session,
            )
            report_str = res.data.get("markdown_report", "") if isinstance(res.data, dict) else str(res.data)
            findings_list = res.data.get("findings", []) if isinstance(res.data, dict) else []
            return {
                "action_id": action.id,
                "label": "Blue Team",
                "result": {
                    "status": "completed",
                    "posture": "defensive",
                    "summary": res.summary,
                    "findings_count": len(findings_list),
                    "findings": findings_list,
                    "report": report_str,
                    "actionable_recommendations": [
                        "Enforce strict target authorization policies",
                        "Maintain loopback isolation on internal API ports",
                        "Redact secrets and sensitive tokens from terminal audit logs",
                    ],
                },
            }

        elif action.id in {"nmap_recon", "nmap-recon"}:
            from app.agents.cyber_agent import cyber_agent
            from app.security.target_authorization import target_auth_manager

            target = (parameters or {}).get("target", "127.0.0.1")
            is_authorized = target_auth_manager.is_authorized(target)
            if not is_authorized:
                return {
                    "action_id": action.id,
                    "label": "Nmap Recon",
                    "result": {
                        "status": "authorization_required",
                        "target": target,
                        "error": (
                            f"Target '{target}' is not in authorized reconnaissance scope. "
                            "Active network discovery requires explicit target authorization."
                        ),
                        "remediation": "Add target scope authorization via /api/v1/security/target-authorizations before scanning.",
                        "policy_compliant": True,
                    },
                }

            res = await cyber_agent.execute(
                task_id=f"nmap-recon-{uuid4().hex[:6]}",
                goal=f"Execute authorized network reconnaissance on {target}",
                parameters={"target": target, "action": "port_scan"},
                session=session,
            )
            return {
                "action_id": action.id,
                "label": "Nmap Recon",
                "result": {
                    "status": "completed",
                    "target": target,
                    "summary": res.summary,
                    "open_ports": res.data.get("open_ports", []) if isinstance(res.data, dict) else [],
                    "findings": res.data.get("findings", []) if isinstance(res.data, dict) else [],
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
# HUD Screenshot Quick-Action Buttons
QuickActionService.register(
    QuickActionDefinition(
        id="arc_telemetry",
        label="Arc Telemetry",
        description="Stream real-time HUD telemetry, frequency, quantum matrix, and active metrics.",
        category="HUD",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="who_made_you",
        label="Who Made You?",
        description="Truthful disclosure of FRIDAY AI origin, founder GOJO, and dual-brain architecture.",
        category="Identity",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="blue_team",
        label="Blue Team",
        description="Execute automated defensive security posture audit and perimeter inspection.",
        category="Cybersecurity",
    )
)
QuickActionService.register(
    QuickActionDefinition(
        id="nmap_recon",
        label="Nmap Recon",
        description="Execute authorized network reconnaissance and port discovery with policy enforcement.",
        category="Cybersecurity",
    )
)
