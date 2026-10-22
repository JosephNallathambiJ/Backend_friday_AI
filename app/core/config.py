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

    # Ollama / Local AI Central Brain (Dual-Brain Architecture)
    FRIDAY_MODEL_PROVIDER: str = "ollama"
    FRIDAY_MODEL_NAME: str = "LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M"
    DEFAULT_LOCAL_MODEL: str = "LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M"

    # Dual-Brain Configuration (Master Prompt 7)
    FRIDAY_LEFT_MODEL: str = "LiquidAI/lfm2.5-2.6b:q4_k_m"
    FRIDAY_RIGHT_MODEL: str = "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q4_K_M"
    FRIDAY_DEFAULT_BRAIN: str = "left"  # "left", "right"
    FRIDAY_CYBER_BRAIN_ENABLED: bool = True
    FRIDAY_DUAL_BRAIN_MODE: str = "selective"  # "selective", "collaborative", "single"
    FRIDAY_ALLOW_CLOUD_FALLBACK: bool = False

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_REQUEST_TIMEOUT: float = 120.0
    MODEL_REQUEST_TIMEOUT: float = 120.0
    LEFT_MODEL_TIMEOUT: float = 120.0
    RIGHT_MODEL_TIMEOUT: float = 120.0
    MODEL_MAX_TOKENS: int = 4096
    MODEL_TEMPERATURE: float = 0.7
    LEFT_MODEL_TEMPERATURE: float = 0.7
    RIGHT_MODEL_TEMPERATURE: float = 0.4
    MODEL_CONTEXT_LIMIT: int = 16384
    MODEL_MAX_CONCURRENCY: int = 4
    MAX_MATH_COMPUTATION_TIMEOUT: float = 10.0

    # Cloud AI (Opt-in only - never used as unauthorized fallback)
    CLOUD_AI_ENABLED: bool = False
    CLOUD_PROVIDER: str | None = None
    CLOUD_API_KEY: str | None = None
    CLOUD_MODEL: str | None = None

    # Integration Providers & Capabilities
    CONTACTS_PROVIDER: str = "none"  # "none", "local_sqlite", "macos_addressbook", "google_contacts"
    BROWSER_AUTOMATION_ENABLED: bool = False

    # Security & Permissions
    MAX_INPUT_LENGTH: int = 32768
    MAX_ORCHESTRATION_STEPS: int = 10
    COMMAND_TIMEOUT_SECONDS: float = 30.0
    APPROVED_ROOTS: list[str] = Field(default_factory=lambda: [str(Path.cwd().resolve())])
    ALLOWED_COMMANDS: list[str] = Field(
        default_factory=lambda: [
            "git",
            "pytest",
            "ruff",
            "python",
            "python3",
            "ls",
            "pwd",
            "echo",
            "uname",
            "whoami",
            "free",
            "df",
            "uptime",
            "date",
            "cat",
            "help",
            "clear",
            "ps",
            "top",
        ]
    )

    # Scheduler & Background Tasks
    SCHEDULER_ENABLED: bool = True
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT_SECONDS: float = 300.0

    # GitHub Integration
    GITHUB_TOKEN: str | None = None

    # Omni OSINT Power Integration (Master Prompt 8)
    OMNI_OSINT_ENDPOINT: str = "http://127.0.0.1:8888"
    OMNI_OSINT_API_KEY: str | None = None
    OMNI_OSINT_ENABLED: bool = False
    OMNI_OSINT_MOCK_MODE: bool = True
    OMNI_OSINT_TIMEOUT: float = 15.0
    OMNI_OSINT_RATE_LIMIT: int = 10

    # Audio & Microphone Services (Master Prompt 8)
    AUDIO_ENABLED: bool = True
    AUDIO_MAX_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    AUDIO_RETENTION_ENABLED: bool = False  # Privacy first: ephemeral by default
    AUDIO_MAX_RECORDING_SECONDS: int = 300  # 5 minutes
    AUDIO_TEMP_DIR: Path = Field(default_factory=lambda: Path.cwd() / "storage" / "audio_temp")

    # Diagnostics & Security
    SECURITY_SCAN_MAX_TARGETS: int = 50
    DEFAULT_PORT_SCAN_TIMEOUT: float = 3.0
    DIAGNOSTICS_REPORT_DIR: Path = Field(default_factory=lambda: Path.cwd() / "storage" / "diagnostics")

    # Storage paths
    DATA_DIR: Path = Field(default_factory=lambda: Path.cwd() / "data")
    SKILLS_DIRECTORY: Path = Field(default_factory=lambda: Path.cwd() / "storage" / "skills")
    QUARANTINE_DIRECTORY: Path = Field(default_factory=lambda: Path.cwd() / "storage" / "quarantine")
    MAX_SKILL_REPO_SIZE_MB: int = 50
    SKILL_CLONE_TIMEOUT_SECONDS: float = 30.0
    MAX_SKILL_FILES: int = 1000

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
