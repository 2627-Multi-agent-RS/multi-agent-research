"""Gemini model factory with bounded retry and fallback behavior."""

import os
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import TypeVar, overload

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[3]  # app/tools/llm/ -> backend/


def _load_env() -> None:
    """Nạp backend/.env vào os.environ (không ghi đè biến môi trường thật).

    Tác dụng phụ có chủ ý: các tool đọc os.getenv trực tiếp (Tavily...)
    có key ngay cả khi chạy bằng uvicorn mà không export env.
    """
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
        return
    except ImportError:
        pass
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env()


def _resolve_model_name(explicit: str | None, env_key: str, settings_default: str) -> str:
    """Ưu tiên: tham số truyền vào > env (GEMINI_MODEL / GEMINI_FALLBACK_MODEL) > settings."""
    return explicit or os.getenv(env_key) or settings_default

T = TypeVar("T", bound=BaseModel)

RETRYABLE_LLM_ERRORS = (ResourceExhausted, ServiceUnavailable)


class LLMFactory:
    """Central factory for instantiating configured Google Gemini LLM models.

    get_*_model là singleton theo (temperature, model, timeout) — cùng tham số
    trả về cùng instance, không tạo wrapper mới mỗi lần gọi.
    """

    @staticmethod
    @lru_cache(maxsize=16)
    def get_primary_model(
        temperature: float = 0.2,
        *,
        model: str | None = None,
        timeout: float = 30,
    ) -> ChatGoogleGenerativeAI:
        """Initialize primary model (tên đọc từ GEMINI_MODEL, fallback settings)."""
        api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY or "mock-key-for-dev"
        return ChatGoogleGenerativeAI(
            model=_resolve_model_name(model, "GEMINI_MODEL", settings.PRIMARY_LLM_MODEL),
            google_api_key=api_key,
            temperature=temperature,
            timeout=timeout,
            max_retries=2,
        )

    @staticmethod
    @lru_cache(maxsize=16)
    def get_fallback_model(
        temperature: float = 0.2,
        *,
        model: str | None = None,
        timeout: float = 45,
    ) -> ChatGoogleGenerativeAI:
        """Initialize fallback model (tên đọc từ GEMINI_FALLBACK_MODEL, fallback settings)."""
        api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY or "mock-key-for-dev"
        return ChatGoogleGenerativeAI(
            model=_resolve_model_name(model, "GEMINI_FALLBACK_MODEL", settings.FALLBACK_LLM_MODEL),
            google_api_key=api_key,
            temperature=temperature,
            timeout=timeout,
            max_retries=2,
        )


def list_gemini_models() -> list[str]:
    """Liệt kê model còn sống của key hiện tại — dùng để chốt GEMINI_MODEL."""
    key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY or ""
    if not key:
        raise RuntimeError("Thiếu GEMINI_API_KEY trong backend/.env — không list được models.")
    genai.configure(api_key=key)
    return [m.name.replace("models/", "") for m in genai.list_models()]


@overload
async def _invoke_with_retry(
    model: ChatGoogleGenerativeAI,
    messages: Sequence[BaseMessage],
    structured_schema: type[T],
) -> T: ...


@overload
async def _invoke_with_retry(
    model: ChatGoogleGenerativeAI,
    messages: Sequence[BaseMessage],
    structured_schema: None = None,
) -> BaseMessage: ...


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=10),
    retry=retry_if_exception_type(RETRYABLE_LLM_ERRORS),
)
async def _invoke_with_retry(
    model: ChatGoogleGenerativeAI,
    messages: Sequence[BaseMessage],
    structured_schema: type[T] | None = None,
) -> T | BaseMessage:
    target = (
        model.with_structured_output(structured_schema) if structured_schema else model
    )
    return await target.ainvoke(messages)  # type: ignore[return-value]  # with_structured_output's Runnable output type isn't precisely inferred by mypy


@overload
async def invoke_with_resilience(
    model: ChatGoogleGenerativeAI,
    prompt_messages: Sequence[BaseMessage],
    structured_schema: type[T],
    fallback_model: ChatGoogleGenerativeAI | None = None,
) -> T: ...


@overload
async def invoke_with_resilience(
    model: ChatGoogleGenerativeAI,
    prompt_messages: Sequence[BaseMessage],
    structured_schema: None = None,
    fallback_model: ChatGoogleGenerativeAI | None = None,
) -> BaseMessage: ...


async def invoke_with_resilience(
    model: ChatGoogleGenerativeAI,
    prompt_messages: Sequence[BaseMessage],
    structured_schema: type[T] | None = None,
    fallback_model: ChatGoogleGenerativeAI | None = None,
) -> T | BaseMessage:
    """
    Invoke an LLM asynchronously with exponential backoff retry for transient 429/503 errors.

    If the primary model exhausts its 3 retry attempts while hitting a retryable error
    (429 Resource Exhausted / 503 Service Unavailable), automatically switches to the
    fallback model for one more attempt cycle.

    Returns either a validated Pydantic model instance or a BaseMessage.
    """
    try:
        return await _invoke_with_retry(model, prompt_messages, structured_schema)
    except RETRYABLE_LLM_ERRORS:
        logger.warning("primary_llm_exhausted_retries_switching_to_fallback")
        fallback = fallback_model or LLMFactory.get_fallback_model()
        return await _invoke_with_retry(fallback, prompt_messages, structured_schema)


__all__ = [
    "RETRYABLE_LLM_ERRORS",
    "LLMFactory",
    "invoke_with_resilience",
    "list_gemini_models",
]
