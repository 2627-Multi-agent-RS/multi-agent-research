"""Analyst Agent node implementation (Stub for StateGraph wiring)."""

from typing import TypedDict

from app.graph.state import AgentState
from app.schemas.research import AnalystOutput, FollowUpRequest


class AnalystUpdate(TypedDict, total=False):
    analysis: AnalystOutput
    retry_count: int
    errors: list[str]


async def run_analyst(state: AgentState) -> AnalystUpdate:
    """
    Execute analysis, verification, and conflict detection on collected findings.
    (Stub implementation for graph compilation and integration testing).
    """
    retry_count = state.get("retry_count", 0)
    findings = state.get("findings", [])

    if retry_count == 0 and len(findings) < 2:
        analysis = AnalystOutput(
            status="needs_more_research",
            confidence_score=0.45,
            verified_findings=findings,
            conclusions=[],
            insights=[],
            conflicts=["Initial evidence lacks sufficient cross-source validation."],
            limitations=["Limited initial search coverage."],
            follow_up_request=FollowUpRequest(
                questions=[f"Deeper investigation into {state.get('topic', '')}"],
                preferred_sources=["academic_journals"],
            ),
        )
        return AnalystUpdate(
            analysis=analysis,
            retry_count=retry_count,
            errors=list(state.get("errors", [])),
        )

    analysis = AnalystOutput(
        status="complete",
        confidence_score=0.92,
        verified_findings=findings,
        conclusions=["All claims cross-verified across empirical sources."],
        insights=["Key trend demonstrates significant performance gains."],
        conflicts=[],
        limitations=[],
        follow_up_request=None,
    )
    return AnalystUpdate(
        analysis=analysis,
        retry_count=retry_count,
        errors=list(state.get("errors", [])),
    )


__all__ = ["AnalystUpdate", "run_analyst"]
