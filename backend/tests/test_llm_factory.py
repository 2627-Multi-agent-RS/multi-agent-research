from unittest.mock import AsyncMock, MagicMock

import pytest
from google.api_core.exceptions import ResourceExhausted
from pydantic import BaseModel

from app.core.config import settings
from app.tools.llm.factory import LLMFactory, invoke_with_resilience


class SimpleOutput(BaseModel):
    summary: str


def test_llm_factory_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is required"):
        LLMFactory.get_primary_model()


def test_llm_factory_creates_models(monkeypatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    primary = LLMFactory.get_primary_model(temperature=0.3)
    assert "gemini-2.0-flash" in primary.model
    assert primary.temperature == 0.3

    fallback = LLMFactory.get_fallback_model(temperature=0.1)
    assert "gemini-1.5-flash" in fallback.model
    assert fallback.temperature == 0.1


@pytest.mark.asyncio
async def test_invoke_with_resilience_success() -> None:
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(return_value="Kết quả nghiên cứu")

    result = await invoke_with_resilience(
        model=mock_model,
        prompt_messages=[{"role": "user", "content": "Xin chào"}],
    )
    assert result == "Kết quả nghiên cứu"
    mock_model.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_invoke_with_resilience_with_structured_output() -> None:
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=SimpleOutput(summary="Tóm tắt"))
    mock_model.with_structured_output.return_value = mock_structured

    result = await invoke_with_resilience(
        model=mock_model,
        messages=[{"role": "user", "content": "Tóm tắt"}],
        structured_schema=SimpleOutput,
    )
    assert result.summary == "Tóm tắt"
    mock_model.with_structured_output.assert_called_once_with(SimpleOutput)


@pytest.mark.asyncio
async def test_invoke_with_resilience_retries_and_recovers() -> None:
    mock_model = MagicMock()
    # Lần 1 ném ResourceExhausted (429), Lần 2 thành công
    mock_model.ainvoke = AsyncMock(
        side_effect=[
            ResourceExhausted("Rate limit exceeded 429"),
            "Thành công sau retry",
        ]
    )

    result = await invoke_with_resilience(
        model=mock_model,
        prompt_messages=["test"],
    )
    assert result == "Thành công sau retry"
    assert mock_model.ainvoke.await_count == 2


@pytest.mark.asyncio
async def test_invoke_with_resilience_falls_back_when_exhausted() -> None:
    mock_primary = MagicMock()
    mock_primary.ainvoke = AsyncMock(
        side_effect=ResourceExhausted("Primary exhausted")
    )

    mock_fallback = MagicMock()
    mock_fallback.ainvoke = AsyncMock(return_value="Kết quả từ fallback model")

    result = await invoke_with_resilience(
        model=mock_primary,
        prompt_messages=["test"],
        fallback_model=mock_fallback,
    )
    assert result == "Kết quả từ fallback model"
    assert mock_primary.ainvoke.await_count == 3  # 3 attempts from tenacity
    mock_fallback.ainvoke.assert_awaited_once()
