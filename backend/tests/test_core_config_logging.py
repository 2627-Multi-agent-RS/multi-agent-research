from pathlib import Path

from app.core.config import Settings
from app.core.logging import configure_logging


def test_settings_defaults_and_properties() -> None:
    settings = Settings(
        GEMINI_API_KEY="test-key",
        TAVILY_API_KEY="tvly-test",
        PRIMARY_LLM_MODEL="gemini-2.0-flash",
        FALLBACK_LLM_MODEL="gemini-1.5-flash",
        ENVIRONMENT="development",
        PORT=8000,
        ALLOWED_ORIGINS="http://localhost:3000, http://localhost:5173",
    )

    assert settings.GEMINI_API_KEY == "test-key"
    assert settings.TAVILY_API_KEY == "tvly-test"
    assert settings.PRIMARY_LLM_MODEL == "gemini-2.0-flash"
    assert settings.FALLBACK_LLM_MODEL == "gemini-1.5-flash"
    assert settings.ENVIRONMENT == "development"
    assert settings.port == 8000
    assert settings.allowed_origins == ["http://localhost:3000", "http://localhost:5173"]
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]
    assert isinstance(settings.LOG_DIR, Path)


def test_settings_allowed_origins_list_input() -> None:
    settings = Settings(
        ALLOWED_ORIGINS=["http://localhost:3000", "https://example.com"]
    )
    assert settings.allowed_origins == ["http://localhost:3000", "https://example.com"]


def test_configure_logging_runs(tmp_path) -> None:
    from app.core.config import settings
    settings.log_dir = tmp_path / "logs"
    configure_logging()
    assert settings.log_dir.exists()
