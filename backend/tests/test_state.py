import pytest
from app.graph.state import AgentState
from app.schemas.research import (
    AnalystOutput,
    Citation,
    Finding,
    ResearchPlan,
    WriterOutput,
)
from pydantic import ValidationError


def test_agent_state_initialization() -> None:
    """Kiểm tra khởi tạo AgentState hợp lệ với đầy đủ các kiểu dữ liệu cụ thể."""
    plan = ResearchPlan(
        topic="Xe điện toàn cầu",
        sub_queries=["Thực trạng thị trường", "Dự báo tăng trưởng"],
        expected_metrics=["Thị phần", "Doanh số"],
    )

    finding = Finding(
        claim="Doanh số xe điện tăng trưởng 25%",
        evidence="Theo IEA, doanh số đạt 17 triệu xe trong năm 2024.",
        source_url="https://iea.org/ev-report",
        source_title="IEA Global EV Outlook",
    )

    state: AgentState = {
        "thread_id": "thread-001",
        "topic": "Xe điện toàn cầu",
        "plan": plan,
        "findings": [finding],
        "search_queries": ["Thực trạng thị trường"],
        "analysis": None,
        "final_report": None,
        "retry_count": 0,
        "errors": [],
    }

    assert state["thread_id"] == "thread-001"
    assert state["plan"].topic == "Xe điện toàn cầu"
    assert len(state["plan"].sub_queries) == 2
    assert len(state["findings"]) == 1
    assert state["findings"][0].claim == "Doanh số xe điện tăng trưởng 25%"
    assert state["retry_count"] == 0


def test_research_plan_sub_queries_validation() -> None:
    """Kiểm tra ràng buộc sub_queries từ 1 đến 5 câu."""
    # Hợp lệ với 1 sub-query
    plan = ResearchPlan(topic="AI", sub_queries=["AI xu hướng"])
    assert len(plan.sub_queries) == 1

    # Không hợp lệ khi rỗng
    with pytest.raises(ValidationError):
        ResearchPlan(topic="AI", sub_queries=[])

    # Không hợp lệ khi vượt quá 5 sub-queries
    with pytest.raises(ValidationError):
        ResearchPlan(
            topic="AI",
            sub_queries=["q1", "q2", "q3", "q4", "q5", "q6"],
        )


def test_analyst_output_confidence_score_range() -> None:
    """Kiểm tra ràng buộc confidence_score trong khoảng [0.0, 1.0]."""
    valid_output = AnalystOutput(
        status="complete",
        confidence_score=0.85,
    )
    assert valid_output.confidence_score == 0.85

    # Vượt quá 1.0
    with pytest.raises(ValidationError):
        AnalystOutput(
            status="complete",
            confidence_score=1.5,
        )

    # Nhỏ hơn 0.0
    with pytest.raises(ValidationError):
        AnalystOutput(
            status="complete",
            confidence_score=-0.1,
        )


def test_writer_output_and_citations() -> None:
    """Kiểm tra khởi tạo WriterOutput và danh mục trích dẫn Citation."""
    citation = Citation(
        id=1,
        title="Báo cáo Năng lượng",
        url="https://example.com/report",
        snippet="Tóm tắt nghiên cứu",
    )

    report = WriterOutput(
        title="Báo cáo Xe điện",
        content="# Nội dung báo cáo...",
        citations=[citation],
        warnings=[],
    )

    assert report.status == "complete"
    assert len(report.citations) == 1
    assert report.citations[0].id == 1
