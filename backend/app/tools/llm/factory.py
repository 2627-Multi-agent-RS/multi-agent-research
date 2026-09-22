from typing import TypeVar, overload

from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


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
async def invoke_with_resilience(
    model: ChatGoogleGenerativeAI,
    prompt_messages: list[BaseMessage],
    structured_schema: type[T],
) -> T: ...


@overload
async def invoke_with_resilience(
    model: ChatGoogleGenerativeAI,
    prompt_messages: list[BaseMessage],
    structured_schema: None = None,
) -> BaseMessage: ...


@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=10),
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable)),
    reraise=True,
)
async def invoke_with_resilience(
    model: ChatGoogleGenerativeAI,
    prompt_messages: list[BaseMessage],
    structured_schema: type[T] | None = None,
) -> T | BaseMessage:
    """
    Invoke an LLM asynchronously with exponential backoff retry for transient 429/503 errors.
    Returns either a validated Pydantic model instance or a BaseMessage.
    """
    if structured_schema is not None:
        target = model.with_structured_output(structured_schema)
        result = await target.ainvoke(prompt_messages)
        return result

    return await model.ainvoke(prompt_messages)
