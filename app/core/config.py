"""Core application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    APP_NAME: str = "FRIDAY-AI-Backend"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_KEY: str | None = None

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///friday.db"
    DATABASE_ECHO: bool = False

    # Ollama / Local AI
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_LOCAL_MODEL: str = "gemma4:12b"
    OLLAMA_REQUEST_TIMEOUT: float = 120.0

    # Cloud AI (Opt-in only)
    CLOUD_AI_ENABLED: bool = False
    CLOUD_PROVIDER: str | None = None
    CLOUD_API_KEY: str | None = None
    CLOUD_MODEL: str | None = None

    # Security & Permissions
    MAX_INPUT_LENGTH: int = 32768
    MAX_ORCHESTRATION_STEPS: int = 10
    COMMAND_TIMEOUT_SECONDS: float = 30.0
    APPROVED_ROOTS: list[str] = Field(default_factory=lambda: [str(Path.cwd().resolve())])
    ALLOWED_COMMANDS: list[str] = Field(
        default_factory=lambda: ["git", "pytest", "ruff", "python3", "ls", "pwd", "echo"]
    )

    # Scheduler & Background Tasks
    SCHEDULER_ENABLED: bool = True
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT_SECONDS: float = 300.0

    # GitHub Integration
    GITHUB_TOKEN: str | None = None

    # Storage paths
    DATA_DIR: Path = Field(default_factory=lambda: Path.cwd() / "data")

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        valid_envs = {"development", "testing", "production", "staging"}
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Invalid APP_ENV: {v}. Must be one of {valid_envs}")
        return v_lower

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_for_production(cls, v: bool, info) -> bool:
        env = info.data.get("APP_ENV", "development")
        if env == "production" and v is True:
            raise ValueError("DEBUG mode must not be enabled in production environment.")
        return v


# Global settings instance
settings = AppSettings()
