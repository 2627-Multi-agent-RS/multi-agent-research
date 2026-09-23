import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import settings
from app.schemas.research import ResearchPlan
from app.tools.llm.factory import LLMFactory, invoke_with_resilience
from google.api_core.exceptions import ResourceExhausted
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def test_llm_factory_get_models() -> None:
    """Kiểm tra khởi tạo primary và fallback model với cấu hình chính xác."""
    primary = LLMFactory.get_primary_model(temperature=0.3)
    assert isinstance(primary, ChatGoogleGenerativeAI)
    assert primary.model == settings.PRIMARY_LLM_MODEL
    assert primary.temperature == 0.3

    fallback = LLMFactory.get_fallback_model(temperature=0.1)
    assert isinstance(fallback, ChatGoogleGenerativeAI)
    assert fallback.model == settings.FALLBACK_LLM_MODEL
    assert fallback.temperature == 0.1


def test_invoke_with_resilience_structured_output() -> None:
    """Kiểm tra gọi LLM thành công với schema Pydantic có cấu trúc."""

    async def _test() -> None:
        mock_model = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_target = MagicMock()
        expected_plan = ResearchPlan(
            topic="Công nghệ Pin Thể Rắn",
            sub_queries=["Thực trạng", "Xu hướng 2025"],
        )
        mock_target.ainvoke = AsyncMock(return_value=expected_plan)
        mock_model.with_structured_output.return_value = mock_target

        messages = [HumanMessage(content="Phân tích pin thể rắn")]
        result = await invoke_with_resilience(
            model=mock_model,
            prompt_messages=messages,
            structured_schema=ResearchPlan,
        )

        mock_model.with_structured_output.assert_called_once_with(ResearchPlan)
        mock_target.ainvoke.assert_awaited_once_with(messages)
        assert result == expected_plan
        assert result.topic == "Công nghệ Pin Thể Rắn"

    asyncio.run(_test())


def test_invoke_with_resilience_unstructured() -> None:
    """Kiểm tra gọi LLM thông thường khi không truyền structured_schema."""

    async def _test() -> None:
        mock_model = MagicMock(spec=ChatGoogleGenerativeAI)
        expected_response = AIMessage(content="Kết quả phân tích")
        mock_model.ainvoke = AsyncMock(return_value=expected_response)

        messages = [HumanMessage(content="Xin chào")]
        result = await invoke_with_resilience(
            model=mock_model,
            prompt_messages=messages,
        )

        mock_model.ainvoke.assert_awaited_once_with(messages)
        assert result == expected_response

    asyncio.run(_test())


def test_invoke_with_resilience_retry_on_429() -> None:
    """Kiểm tra cơ chế retry tự động phục hồi khi gặp lỗi HTTP 429 ResourceExhausted."""

    async def _test() -> None:
        mock_model = MagicMock(spec=ChatGoogleGenerativeAI)
        expected_response = AIMessage(content="Phục hồi thành công sau lỗi 429")

        # Lần 1 ném lỗi ResourceExhausted, Lần 2 thành công
        mock_model.ainvoke = AsyncMock(
            side_effect=[
                ResourceExhausted("Resource has been exhausted (e.g. rate limit)."),
                expected_response,
            ]
        )

        messages = [HumanMessage(content="Thử nghiệm retry")]
        result = await invoke_with_resilience(
            model=mock_model,
            prompt_messages=messages,
        )

        assert mock_model.ainvoke.await_count == 2
        assert result == expected_response

    asyncio.run(_test())


def test_invoke_with_resilience_fail_fast_on_non_retryable_error() -> None:
    """Kiểm tra cơ chế fail-fast: không retry đối với lỗi không thể phục hồi (như ValueError)."""

    async def _test() -> None:
        mock_model = MagicMock(spec=ChatGoogleGenerativeAI)
        mock_model.ainvoke = AsyncMock(side_effect=ValueError("Tham số không hợp lệ"))

        messages = [HumanMessage(content="Lỗi")]
        with pytest.raises(ValueError, match="Tham số không hợp lệ"):
            await invoke_with_resilience(
                model=mock_model,
                prompt_messages=messages,
            )

        # Đảm bảo chỉ gọi đúng 1 lần, không lãng phí retry
        assert mock_model.ainvoke.await_count == 1

    asyncio.run(_test())
