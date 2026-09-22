"""Gemini model factory with bounded retry and fallback behavior."""
from collections.abc import Sequence
from typing import Any

from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.core.config import settings

RETRYABLE_LLM_ERRORS = (ResourceExhausted, ServiceUnavailable)


class LLMFactory:
    """Create configured Gemini chat models for research agents."""

    @staticmethod
    def _create(model_name: str, temperature: float = 0.2, timeout: int = 30, max_retries: int = 2) -> Any:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required before invoking an LLM")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError("langchain-google-genai is not installed") from exc

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
        )

    @classmethod
    def get_primary_model(cls, temperature: float = 0.2) -> Any:
        """Khởi tạo model chính gemini-2.0-flash."""
        return cls._create(
            model_name=settings.primary_llm_model,
            temperature=temperature,
            timeout=30,
            max_retries=2,
        )

    @classmethod
    def get_fallback_model(cls, temperature: float = 0.2) -> Any:
        """Khởi tạo model dự phòng gemini-1.5-flash."""
        return cls._create(
            model_name=settings.fallback_llm_model,
            temperature=temperature,
            timeout=45,
            max_retries=2,
        )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=10),
    retry=retry_if_exception_type(RETRYABLE_LLM_ERRORS),
)
async def _invoke_with_retry(model: Any, messages: Sequence[Any], structured_schema: Any | None = None) -> Any:
    target = model.with_structured_output(structured_schema) if structured_schema else model
    return await target.ainvoke(messages)


async def invoke_with_resilience(
    model: Any,
    prompt_messages: Sequence[Any] | None = None,
    structured_schema: Any | None = None,
    fallback_model: Any | None = None,
    messages: Sequence[Any] | None = None,
) -> Any:
    """Gọi LLM an toàn chống sập khi dính mã lỗi HTTP 429 hoặc 503 với Tenacity Backoff & Fallback.

    Hỗ trợ cả tham số `prompt_messages` và `messages` để tương thích 100% với tài liệu đặc tả.
    Nếu mô hình chính cạn kiệt 3 lượt retry khi gặp mã lỗi 429/503, tự động chuyển tiếp sang mô hình fallback.
    """
    input_messages = prompt_messages if prompt_messages is not None else messages
    if input_messages is None:
        raise ValueError("Either 'prompt_messages' or 'messages' must be provided.")

    try:
        return await _invoke_with_retry(model, input_messages, structured_schema)
    except RETRYABLE_LLM_ERRORS:
        logger.warning("primary_llm_exhausted_retries_switching_to_fallback")
        fallback = fallback_model or LLMFactory.get_fallback_model()
        return await _invoke_with_retry(fallback, input_messages, structured_schema)
