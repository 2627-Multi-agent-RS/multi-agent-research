"""Gemini model factory with bounded retry and fallback behavior."""

from collections.abc import Sequence
from typing import TypeVar, overload

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

T = TypeVar("T", bound=BaseModel)

RETRYABLE_LLM_ERRORS = (ResourceExhausted, ServiceUnavailable)


class LLMFactory:
    """Central factory for instantiating configured Google Gemini LLM models."""

    @staticmethod
    def get_primary_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
        """Initialize primary model (Gemini 2.0 Flash) with standard timeout."""
        api_key = settings.GEMINI_API_KEY or "mock-key-for-dev"
        return ChatGoogleGenerativeAI(
            model=settings.PRIMARY_LLM_MODEL,
            google_api_key=api_key,
            temperature=temperature,
            timeout=30,
            max_retries=2,
        )

    @staticmethod
    def get_fallback_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
        """Initialize fallback model (Gemini 1.5 Flash) with extended timeout."""
        api_key = settings.GEMINI_API_KEY or "mock-key-for-dev"
        return ChatGoogleGenerativeAI(
            model=settings.FALLBACK_LLM_MODEL,
            google_api_key=api_key,
            temperature=temperature,
            timeout=45,
            max_retries=2,
        )


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
]
