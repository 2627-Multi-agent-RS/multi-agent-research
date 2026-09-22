"""AgentState definition for LangGraph workflow."""
from typing import Any, TypedDict


class AgentState(TypedDict):
    """Trạng thái chia sẻ trung tâm của LangGraph."""

    thread_id: str
    topic: str
    plan: dict[str, Any] | None
    findings: list[dict[str, Any]]
    search_queries: list[str]
    analysis: dict[str, Any] | None
    final_report: dict[str, Any] | None
    retry_count: int
    errors: list[str]
