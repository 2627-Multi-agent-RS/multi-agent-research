"""Runtime settings loaded from environment variables and ``.env``."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Validated application configuration."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
        extra="ignore",
    )

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    primary_llm_model: str = Field(
        default="gemini-2.0-flash", validation_alias="PRIMARY_LLM_MODEL"
    )
    fallback_llm_model: str = Field(
        default="gemini-1.5-flash", validation_alias="FALLBACK_LLM_MODEL"
    )
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, ge=1, le=65535, validation_alias="PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_dir: Path = Field(default=Path("./storage/logs"), validation_alias="LOG_DIR")
    checkpoint_db_path: str = Field(
        default="./storage/checkpoints.db", validation_alias="CHECKPOINT_DB_PATH"
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        validation_alias="ALLOWED_ORIGINS",
    )
    use_mock_research: bool = Field(default=False, validation_alias="USE_MOCK_RESEARCH")

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_dir", mode="after")
    @classmethod
    def resolve_log_dir(cls, value: Path | str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else BACKEND_DIR / p

    # Uppercase aliases for seamless interoperability with other agent modules and spec docs
    @property
    def GEMINI_API_KEY(self) -> str:
        return self.gemini_api_key

    @property
    def TAVILY_API_KEY(self) -> str:
        return self.tavily_api_key

    @property
    def PRIMARY_LLM_MODEL(self) -> str:
        return self.primary_llm_model

    @property
    def FALLBACK_LLM_MODEL(self) -> str:
        return self.fallback_llm_model

    @property
    def ENVIRONMENT(self) -> str:
        return self.environment

    @property
    def LOG_LEVEL(self) -> str:
        return self.log_level

    @property
    def LOG_DIR(self) -> Path:
        return self.log_dir

    @property
    def CHECKPOINT_DB_PATH(self) -> str:
        return self.checkpoint_db_path

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return self.allowed_origins

    @property
    def USE_MOCK_RESEARCH(self) -> bool:
        return self.use_mock_research


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""
    return Settings()


settings = get_settings()
