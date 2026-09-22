"""Routing logic and loop guardrail for LangGraph workflow."""
from typing import Literal

from app.graph.state import AgentState


def should_continue_research(state: AgentState) -> Literal["researcher", "writer"]:
    """Quyết định nhánh rẽ sau bước Analyst.

    Ràng buộc thép: Chỉ cho phép lặp lại tối đa 1 lần (retry_count < 1).
    """
    analysis = state.get("analysis") or {}
    status = analysis.get("status", "complete")
    retry_count = state.get("retry_count", 0)

    # Nếu phát hiện thiếu dữ liệu VÀ chưa từng retry
    if status == "needs_more_research" and retry_count < 1:
        return "researcher"

    # Mọi trường hợp còn lại đều chuyển tiếp sang Writer
    return "writer"
