"""Researcher Agent node implementation (Stub for StateGraph wiring)."""

from typing import TypedDict

from app.graph.state import AgentState
from app.schemas.research import Finding


class ResearcherUpdate(TypedDict, total=False):
    findings: list[Finding]
    search_queries: list[str]
    retry_count: int
    errors: list[str]


async def run_researcher(state: AgentState) -> ResearcherUpdate:
    """
    Execute research gathering for the given research plan or follow-up questions.
    (Stub implementation for graph compilation and integration testing).
    """
    findings = list(state.get("findings", []))
    search_queries = list(state.get("search_queries", []))
    retry_count = state.get("retry_count", 0)

    analysis = state.get("analysis")
    if analysis and analysis.follow_up_request:
        retry_count += 1
        search_queries.extend(analysis.follow_up_request.questions)
        for q in analysis.follow_up_request.questions:
            findings.append(
                Finding(
                    claim=f"Follow-up evidence addressing: {q}",
                    evidence="Deep research verification evidence collected.",
                    source_url="https://arxiv.org/abs/example",
                    source_title="Follow-Up Research Paper",
                )
            )
    elif not findings:
        for query in search_queries:
            findings.append(
                Finding(
                    claim=f"Primary finding for query: {query}",
                    evidence="Primary empirical evidence retrieved from literature.",
                    source_url="https://example.com/research",
                    source_title="Primary Research Source",
                )
            )

    return ResearcherUpdate(
        findings=findings,
        search_queries=search_queries,
        retry_count=retry_count,
        errors=list(state.get("errors", [])),
    )


__all__ = ["ResearcherUpdate", "run_researcher"]
