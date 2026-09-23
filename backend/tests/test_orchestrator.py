import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.agents.orchestrator.agent import run_orchestrator
from app.agents.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.schemas.research import ResearchPlan


def test_orchestrator_prompt_structure() -> None:
    """Kiểm tra cấu trúc và các chỉ thị bắt buộc trong System Prompt."""
    assert "sub-queries" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "expected_metrics" in ORCHESTRATOR_SYSTEM_PROMPT
    assert "ResearchPlan" in ORCHESTRATOR_SYSTEM_PROMPT


def test_run_orchestrator_success() -> None:
    """Kiểm tra run_orchestrator phân rã chủ đề thành công và cập nhật State."""

    async def _test() -> None:
        mock_plan = ResearchPlan(
            topic="Thị trường xe điện 2025",
            sub_queries=[
                "Thực trạng và doanh số xe điện toàn cầu 2025",
                "Chính sách trợ giá và rào cản thuế quan pin xe điện",
                "Dự báo thị phần xe điện tại Đông Nam Á 2030",
            ],
            expected_metrics=["Doanh số bán ra", "Tỷ lệ tăng trưởng CAGR"],
        )

        initial_state: AgentState = {
            "thread_id": "session-101",
            "topic": "Thị trường xe điện 2025",
            "plan": None,
            "findings": [],
            "search_queries": [],
            "analysis": None,
            "final_report": None,
            "retry_count": 0,
            "errors": [],
        }

        with patch(
            "app.agents.orchestrator.agent.invoke_with_resilience",
            new_callable=AsyncMock,
        ) as mock_invoke:
            mock_invoke.return_value = mock_plan

            update = await run_orchestrator(initial_state)

            assert update["plan"] == mock_plan
            assert update["search_queries"] == mock_plan.sub_queries
            assert len(update["search_queries"]) == 3
            mock_invoke.assert_awaited_once()

    asyncio.run(_test())


def test_run_orchestrator_empty_topic_raises_value_error() -> None:
    """Kiểm tra cơ chế phòng vệ: Báo lỗi ngay lập tức khi chủ đề rỗng."""

    async def _test() -> None:
        invalid_state: AgentState = {
            "thread_id": "session-102",
            "topic": "   ",  # Chỉ chứa khoảng trắng
            "plan": None,
            "findings": [],
            "search_queries": [],
            "analysis": None,
            "final_report": None,
            "retry_count": 0,
            "errors": [],
        }

        with pytest.raises(
            ValueError, match="Research topic cannot be empty or whitespace"
        ):
            await run_orchestrator(invalid_state)

    asyncio.run(_test())
