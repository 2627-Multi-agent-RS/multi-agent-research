"""Unit tests for the LangGraph conditional routing logic."""

from app.graph.routing import (
    MAX_RESEARCH_RETRIES,
    RESEARCHER_NODE,
    WRITER_NODE,
    should_continue_research,
)
from app.graph.state import AgentState
from app.schemas.research import AnalystOutput, FollowUpRequest


def _make_dummy_state(
    status: str | None = None,
    retry_count: int = 0,
) -> AgentState:
    """Helper to build a minimal AgentState for testing routing rules."""
    analysis = None
    if status is not None:
        follow_up = (
            FollowUpRequest(
                questions=["What are the latest benchmarks?"],
                preferred_sources=["arxiv.org"],
            )
            if status == "needs_more_research"
            else None
        )
        analysis = AnalystOutput(
            status=status,  # type: ignore[arg-type]
            confidence_score=0.85 if status == "complete" else 0.4,
            verified_findings=[],
            conclusions=["Sample conclusion"] if status == "complete" else [],
            insights=[],
            conflicts=[],
            limitations=[],
            follow_up_request=follow_up,
        )

    return AgentState(
        thread_id="test-thread-001",
        topic="Evaluating Multi-Agent Systems in 2026",
        plan=None,
        findings=[],
        search_queries=[],
        analysis=analysis,
        final_report=None,
        retry_count=retry_count,
        errors=[],
    )


def test_routing_constants() -> None:
    """Ensure routing constants match expected node identifiers and retry ceiling."""
    assert RESEARCHER_NODE == "researcher"
    assert WRITER_NODE == "writer"
    assert MAX_RESEARCH_RETRIES == 1


def test_should_continue_research_when_needs_more_research_and_zero_retries() -> None:
    """Routes back to researcher if analyst requests more research and retry ceiling not met."""
    state = _make_dummy_state(status="needs_more_research", retry_count=0)
    decision = should_continue_research(state)
    assert decision == RESEARCHER_NODE


def test_should_continue_research_exhausted_retries_at_limit() -> None:
    """Routes to writer when retry_count equals MAX_RESEARCH_RETRIES even if research is needed."""
    state = _make_dummy_state(
        status="needs_more_research", retry_count=MAX_RESEARCH_RETRIES
    )
    decision = should_continue_research(state)
    assert decision == WRITER_NODE


def test_should_continue_research_exhausted_retries_above_limit() -> None:
    """Routes to writer when retry_count exceeds MAX_RESEARCH_RETRIES."""
    state = _make_dummy_state(status="needs_more_research", retry_count=2)
    decision = should_continue_research(state)
    assert decision == WRITER_NODE


def test_should_route_to_writer_on_complete_analysis() -> None:
    """Routes to writer when analyst finishes analysis successfully."""
    state = _make_dummy_state(status="complete", retry_count=0)
    decision = should_continue_research(state)
    assert decision == WRITER_NODE


def test_should_route_to_writer_when_analysis_is_none() -> None:
    """Routes safely to writer when analysis object is None."""
    state = _make_dummy_state(status=None, retry_count=0)
    decision = should_continue_research(state)
    assert decision == WRITER_NODE


def test_should_route_safely_on_empty_or_malformed_state() -> None:
    """Defensive fallback safely routes to writer when state dictionary is empty."""
    empty_state: AgentState = {}  # type: ignore[typeddict-item]
    decision = should_continue_research(empty_state)
    assert decision == WRITER_NODE
