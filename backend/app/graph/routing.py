"""Routing logic and conditional guardrails for the LangGraph research workflow."""

from typing import Final, Literal

from app.graph.state import AgentState

RESEARCHER_NODE: Final = "researcher"
WRITER_NODE: Final = "writer"
MAX_RESEARCH_RETRIES: Final[int] = 1

RouteDestination = Literal["researcher", "writer"]


def should_continue_research(state: AgentState) -> RouteDestination:
    """
    Conditional edge router determining the next step after the Analyst node.

    Evaluates whether more research is requested and whether the retry budget
    has not been exhausted. Strictly caps research iterations to MAX_RESEARCH_RETRIES
    to prevent runaway execution loops.

    Args:
        state: The current AgentState snapshot.

    Returns:
        "researcher" if follow-up research is requested and retry_count < MAX_RESEARCH_RETRIES,
        otherwise "writer".
    """
    retry_count = state.get("retry_count") or 0
    if retry_count >= MAX_RESEARCH_RETRIES:
        return WRITER_NODE

    analysis = state.get("analysis")
    if analysis is None:
        return WRITER_NODE

    if analysis.status == "needs_more_research":
        return RESEARCHER_NODE

    return WRITER_NODE


__all__ = [
    "MAX_RESEARCH_RETRIES",
    "RESEARCHER_NODE",
    "WRITER_NODE",
    "RouteDestination",
    "should_continue_research",
]