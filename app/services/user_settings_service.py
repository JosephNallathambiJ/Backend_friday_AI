"""User and System Settings persistence and validation service."""

import shutil
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.db.models.user_settings import UserSettingsRecord
from app.providers.registry import provider_registry
from app.realtime.event_bus import event_bus
from app.services.command_runner import COMMAND_PROFILES

ALLOWED_LANGUAGES = ["en", "es", "fr", "de", "ja", "zh", "hi", "ar"]
ALLOWED_LOCALES = ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "ja-JP", "zh-CN", "hi-IN"]
ALLOWED_THEMES = ["stark_cyan", "tactical_dark", "hud_amber", "stealth_gray"]
ALLOWED_VOICE_PROVIDERS = ["local", "none"]


class UserSettingsService:
    """Manages persistent HUD preferences and server options."""

    @classmethod
    async def get_or_create_settings(
        cls,
        session: AsyncSession,
        user_id: str | None = "local_user",
    ) -> UserSettingsRecord:
        """Fetch user settings or initialize defaults."""
        effective_user_id = user_id or "local_user"
        res = await session.execute(
            select(UserSettingsRecord).where(UserSettingsRecord.user_id == effective_user_id)
        )
        record = res.scalar_one_or_none()
        if not record:
            record = UserSettingsRecord(
                user_id=effective_user_id,
                language="en",
                locale="en-US",
                theme="stark_cyan",
                selected_ai_provider="ollama",
                selected_model=settings.DEFAULT_LOCAL_MODEL,
                voice_provider="local",
                selected_voice="default",
                speech_speed=1.0,
                voice_input_enabled=True,
                voice_output_enabled=True,
                realtime_events_enabled=True,
                terminal_profile="system_check",
                custom_preferences={},
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return record

    @classmethod
    async def get_settings_dict(
        cls,
        session: AsyncSession,
        user_id: str | None = "local_user",
    ) -> dict[str, Any]:
        """Return combined user preferences and safe system settings."""
        effective_user_id = user_id or "local_user"
        record = await cls.get_or_create_settings(session, effective_user_id)
        return {
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "debug": settings.DEBUG,
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "default_local_model": settings.DEFAULT_LOCAL_MODEL,
            "cloud_ai_enabled": settings.CLOUD_AI_ENABLED,
            "approved_roots": settings.APPROVED_ROOTS,
            "allowed_commands": settings.ALLOWED_COMMANDS,
            "max_orchestration_steps": settings.MAX_ORCHESTRATION_STEPS,
            "scheduler_enabled": settings.SCHEDULER_ENABLED,
            "user_id": record.user_id,
            "language": record.language,
            "locale": record.locale,
            "theme": record.theme,
            "selected_ai_provider": record.selected_ai_provider,
            "selected_model": record.selected_model,
            "voice_provider": record.voice_provider,
            "selected_voice": record.selected_voice,
            "speech_speed": record.speech_speed,
            "voice_input_enabled": record.voice_input_enabled,
            "voice_output_enabled": record.voice_output_enabled,
            "realtime_events_enabled": record.realtime_events_enabled,
            "terminal_profile": record.terminal_profile,
            "custom_preferences": record.custom_preferences,
        }

    @classmethod
    async def update_settings(
        cls,
        session: AsyncSession,
        updates: dict[str, Any],
        user_id: str | None = "local_user",
    ) -> dict[str, Any]:
        """Validate and apply partial settings updates."""
        effective_user_id = user_id or "local_user"
        record = await cls.get_or_create_settings(session, effective_user_id)

        if "language" in updates:
            lang = updates["language"]
            if lang not in ALLOWED_LANGUAGES:
                raise ValidationError(f"Invalid language '{lang}'. Allowed: {ALLOWED_LANGUAGES}")
            record.language = lang

        if "locale" in updates:
            loc = updates["locale"]
            if loc not in ALLOWED_LOCALES:
                raise ValidationError(f"Invalid locale '{loc}'. Allowed: {ALLOWED_LOCALES}")
            record.locale = loc

        if "theme" in updates:
            theme = updates["theme"]
            if theme not in ALLOWED_THEMES:
                raise ValidationError(f"Invalid theme '{theme}'. Allowed: {ALLOWED_THEMES}")
            record.theme = theme

        if "selected_model" in updates:
            record.selected_model = updates["selected_model"]

        if "speech_speed" in updates:
            speed = float(updates["speech_speed"])
            if speed < 0.5 or speed > 2.0:
                raise ValidationError("Speech speed must be between 0.5 and 2.0.")
            record.speech_speed = speed

        if "voice_input_enabled" in updates:
            record.voice_input_enabled = bool(updates["voice_input_enabled"])

        if "voice_output_enabled" in updates:
            record.voice_output_enabled = bool(updates["voice_output_enabled"])

        if "realtime_events_enabled" in updates:
            record.realtime_events_enabled = bool(updates["realtime_events_enabled"])

        if "terminal_profile" in updates:
            profile = updates["terminal_profile"]
            if profile not in COMMAND_PROFILES:
                raise ValidationError(f"Invalid terminal profile '{profile}'. Allowed: {list(COMMAND_PROFILES.keys())}")
            record.terminal_profile = profile

        if "custom_preferences" in updates and isinstance(updates["custom_preferences"], dict):
            curr = dict(record.custom_preferences)
            curr.update(updates["custom_preferences"])
            record.custom_preferences = curr

        await session.commit()
        await session.refresh(record)

        # Broadcast settings.updated event
        await event_bus.publish(
            event_type="settings.updated",
            user_id=user_id,
            payload={"updated_keys": list(updates.keys())},
        )

        return await cls.get_settings_dict(session, user_id)

    @classmethod
    async def get_settings_options(cls) -> dict[str, Any]:
        """Return allowed values and dynamic options for HUD dropdowns."""
        ollama = provider_registry.get("ollama")
        healthy = await ollama.check_health()
        available_models = await ollama.list_models() if healthy else [settings.DEFAULT_LOCAL_MODEL]

        voices = ["default"]
        if shutil.which("say"):
            # macOS default voices
            voices.extend(["Samantha", "Alex", "Victoria", "Fred"])

        return {
            "languages": ALLOWED_LANGUAGES,
            "locales": ALLOWED_LOCALES,
            "themes": ALLOWED_THEMES,
            "ai_providers": ["ollama"],
            "models": available_models,
            "voice_providers": ALLOWED_VOICE_PROVIDERS,
            "voices": voices,
            "terminal_profiles": list(COMMAND_PROFILES.keys()),
        }
