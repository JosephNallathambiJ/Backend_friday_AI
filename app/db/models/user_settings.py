"""User Settings persistence database model."""

from typing import Any

from sqlalchemy import JSON, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class UserSettingsRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    locale: Mapped[str] = mapped_column(String(32), default="en-US", nullable=False)
    theme: Mapped[str] = mapped_column(String(64), default="stark_cyan", nullable=False)
    selected_ai_provider: Mapped[str] = mapped_column(String(64), default="ollama", nullable=False)
    selected_model: Mapped[str] = mapped_column(String(128), default="gemma4:12b", nullable=False)
    voice_provider: Mapped[str] = mapped_column(String(64), default="local", nullable=False)
    selected_voice: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    speech_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    voice_input_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    voice_output_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    realtime_events_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    terminal_profile: Mapped[str] = mapped_column(String(64), default="system_check", nullable=False)
    custom_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
