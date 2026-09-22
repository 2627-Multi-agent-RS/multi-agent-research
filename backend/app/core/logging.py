"""Structured Loguru configuration."""
import sys

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    """Configure console output and rotating JSON logs without duplicate handlers."""
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        serialize=settings.environment == "production",
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        settings.log_dir / "backend.jsonl",
        level=settings.log_level.upper(),
        serialize=True,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        backtrace=False,
        diagnose=False,
    )
