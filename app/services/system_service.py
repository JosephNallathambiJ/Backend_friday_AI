"""System Status, Diagnostics, Capabilities, and Information Service."""

import importlib.util
import shutil
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.lifecycle import get_uptime_seconds
from app.core.time import utc_now
from app.providers.registry import provider_registry
from app.realtime.connection_manager import connection_manager


class SystemService:
    """Computes comprehensive health, telemetry, diagnostics, and capabilities."""

    @classmethod
    async def get_system_status(cls, session: AsyncSession) -> dict[str, Any]:
        """Return truthful structured status for all system components."""
        now = utc_now()

        # 1. Database Connectivity & Latency
        t0 = time.perf_counter()
        db_status = "offline"
        db_latency_ms: float | None = None
        try:
            await session.execute(text("SELECT 1"))
            db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            db_status = "online"
        except Exception:
            db_status = "offline"

        # 2. AI Provider (Ollama)
        t0 = time.perf_counter()
        ollama = provider_registry.get("ollama")
        ollama_healthy = await ollama.check_health()
        ai_latency_ms = round((time.perf_counter() - t0) * 1000, 2) if ollama_healthy else None

        models = []
        if ollama_healthy:
            try:
                models = await ollama.list_models()
            except Exception:
                models = []

        default_model = settings.DEFAULT_LOCAL_MODEL
        model_ready = any(default_model in m for m in models)

        if not ollama_healthy:
            ai_status = "offline"
            model_readiness = "offline"
        elif not model_ready:
            ai_status = "degraded"
            model_readiness = "not_pulled"
        else:
            ai_status = "online"
            model_readiness = "ready"

        # 3. Voice Provider
        whisper_installed = shutil.which("whisper") is not None
        tts_installed = shutil.which("say") is not None or shutil.which("espeak") is not None
        if whisper_installed and tts_installed:
            voice_status = "online"
        elif whisper_installed or tts_installed:
            voice_status = "degraded"
        else:
            voice_status = "not_configured"

        # 4. Browser Automation
        has_playwright = importlib.util.find_spec("playwright") is not None
        browser_status = "online" if has_playwright else "not_configured"

        # 5. Filesystem Tool
        fs_status = "online" if settings.APPROVED_ROOTS else "not_configured"

        # 6. Terminal Tool
        terminal_status = "online" if settings.ALLOWED_COMMANDS else "not_configured"

        # 7. Realtime / WebSocket Service
        ws_status = "online"
        ws_connections = connection_manager.connection_count

        # 8. Agent Runtime
        agent_runtime_status = "online" if db_status == "online" else "degraded"

        # 9. Overall Backend Status
        if db_status == "offline":
            overall_status = "offline"
        elif ai_status == "online" and model_readiness == "ready":
            overall_status = "online"
        else:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "application": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.APP_ENV,
                "uptime_seconds": get_uptime_seconds(),
            },
            "components": {
                "database": {
                    "status": db_status,
                    "engine": "sqlite",
                    "latency_ms": db_latency_ms,
                },
                "ai_provider": {
                    "status": ai_status,
                    "provider": "ollama",
                    "base_url": settings.OLLAMA_BASE_URL,
                    "latency_ms": ai_latency_ms,
                    "default_model": default_model,
                    "model_readiness": model_readiness,
                    "available_models": models,
                },
                "agent_runtime": {
                    "status": agent_runtime_status,
                    "max_steps": settings.MAX_ORCHESTRATION_STEPS,
                },
                "voice_provider": {
                    "status": voice_status,
                    "stt_engine": "whisper" if whisper_installed else "none",
                    "tts_engine": "say/espeak" if tts_installed else "none",
                },
                "browser_integration": {
                    "status": browser_status,
                    "engine": "playwright" if has_playwright else "missing",
                },
                "filesystem_tool": {
                    "status": fs_status,
                    "approved_roots_count": len(settings.APPROVED_ROOTS),
                },
                "terminal_tool": {
                    "status": terminal_status,
                    "allowed_executables_count": len(settings.ALLOWED_COMMANDS),
                },
                "websocket_service": {
                    "status": ws_status,
                    "active_connections": ws_connections,
                },
            },
            "timestamp": now.isoformat(),
        }

    @classmethod
    async def get_diagnostics(cls, session: AsyncSession) -> dict[str, Any]:
        """Return deep system diagnostics, configuration inspection, and actionable advice."""
        status_data = await cls.get_system_status(session)
        components = status_data["components"]

        missing_configs = []
        actionable_recommendations = []

        if components["ai_provider"]["status"] == "offline":
            missing_configs.append("Local Ollama service is unreachable.")
            actionable_recommendations.append(
                f"Start Ollama on the host via 'ollama serve' at {settings.OLLAMA_BASE_URL}."
            )
        elif components["ai_provider"]["model_readiness"] == "not_pulled":
            missing_configs.append(f"Model '{settings.DEFAULT_LOCAL_MODEL}' is not pulled.")
            actionable_recommendations.append(
                f"Run 'ollama pull {settings.DEFAULT_LOCAL_MODEL}' to download the weights."
            )

        if components["voice_provider"]["status"] == "not_configured":
            actionable_recommendations.append(
                "Install 'whisper' and 'say' / 'espeak' to enable local voice speech recognition and synthesis."
            )

        if components["browser_integration"]["status"] == "not_configured":
            actionable_recommendations.append(
                "Install Playwright via 'pip install playwright && playwright install chromium' for web interaction."
            )

        return {
            "overall_status": status_data["status"],
            "uptime_seconds": status_data["application"]["uptime_seconds"],
            "component_diagnostics": components,
            "missing_configurations": missing_configs,
            "actionable_recommendations": actionable_recommendations,
            "timestamp": status_data["timestamp"],
        }

    @classmethod
    async def get_capabilities(cls, session: AsyncSession) -> list[dict[str, Any]]:
        """List registered system tools and capability inventory states."""
        from app.tools.registry import tool_registry

        return tool_registry.diagnose_all_tools()

    @classmethod
    def get_system_info(cls) -> dict[str, Any]:
        """Return static system identity and configuration metadata without sensitive secrets."""
        return {
            "application_name": settings.APP_NAME,
            "application_version": settings.APP_VERSION,
            "assistant_identity": "FRIDAY AI - Tactical Defense HUD",
            "environment_type": settings.APP_ENV,
            "api_version": "v1",
            "supported_features": [
                "tactical_command_execution",
                "central_ai_visualizer_telemetry",
                "realtime_hud_events",
                "controlled_terminal_sessions",
                "speech_to_text_transcription",
                "text_to_speech_synthesis",
                "quick_actions_registry",
                "sandboxed_browser_automation",
                "fts5_document_search",
                "rbac_capability_grants",
                "self_extending_skill_ecosystem",
                "github_skill_discovery",
                "isolated_skill_quarantine",
            ],
            "enabled_integrations": [
                "ollama_local_llm",
                "sqlite_fts5",
                "playwright_browser",
                "local_whisper_tts",
                "github_skill_discovery",
            ],
        }

    @classmethod
    async def get_hud_telemetry(cls, session: AsyncSession) -> dict[str, Any]:
        """Return real-time HUD telemetry matching the tactical top-bar and HUD telemetry panels."""
        status_data = await cls.get_system_status(session)
        from app.integrations.omni_osint import omni_osint_adapter
        from app.services.audio import audio_service
        from app.services.task_service import TaskService

        tasks = await TaskService.list_tasks(session=session, limit=10)
        running_count = len([t for t in tasks if getattr(t, "status", None) and str(t.status) == "running"])

        return {
            "systems_status": "ONLINE" if status_data.get("status") == "online" else "DEGRADED",
            "frequency": "1420.405 MHz",
            "quantum_matrix": "SYNCED",
            "grid_protocol": "v8.4",
            "voice_capture_status": "paused",
            "mic_state": "MIC OFF",
            "swipe_state": "SWIPE ON",
            "active_tasks_count": running_count,
            "cpu_percent": status_data.get("system_metrics", {}).get("cpu_percent", 0.0),
            "memory_percent": status_data.get("system_metrics", {}).get("memory_percent", 0.0),
            "uptime_seconds": status_data.get("application", {}).get("uptime_seconds", 0),
            "dual_brain": {
                "left_model": getattr(settings, "FRIDAY_LEFT_MODEL", settings.DEFAULT_LOCAL_MODEL),
                "right_model": getattr(settings, "FRIDAY_RIGHT_MODEL", "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M"),
                "ready": status_data.get("ai_provider", {}).get("connected", False),
            },
            "audio_service": {
                "ready": audio_service.is_ready,
                "transcription_provider": audio_service.provider_name,
            },
            "osint_service": {
                "ready": omni_osint_adapter.is_configured,
                "mode": "live" if omni_osint_adapter.is_configured else "mock",
            },
        }
