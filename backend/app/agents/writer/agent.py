"""Writer Agent node implementation (Stub for StateGraph wiring)."""

from typing import TypedDict

from app.graph.state import AgentState
from app.schemas.research import Citation, WriterOutput


class WriterUpdate(TypedDict, total=False):
    final_report: WriterOutput
    errors: list[str]


async def run_writer(state: AgentState) -> WriterUpdate:
    """
    Synthesize findings and analysis into a comprehensive scientific research report.
    (Stub implementation for graph compilation and integration testing).
    """
    topic = state.get("topic", "Research Topic")
    findings = state.get("findings", [])
    analysis = state.get("analysis")

    citations = [
        Citation(
            id=idx + 1,
            title=f.source_title,
            url=f.source_url,
            snippet=f.evidence[:120],
        )
        for idx, f in enumerate(findings)
    ]

    report_content = (
        f"# Research Report: {topic}\n\n"
        f"## Executive Summary\n"
        f"This report synthesizes {len(findings)} findings on {topic}.\n\n"
        f"## Key Conclusions\n"
    )
    if analysis and analysis.conclusions:
        for c in analysis.conclusions:
            report_content += f"- {c}\n"
    else:
        report_content += "- Initial preliminary observations synthesized.\n"

    report = WriterOutput(
        status="complete",
        title=f"Comprehensive Analysis: {topic}",
        content=report_content,
        citations=citations,
        warnings=analysis.conflicts if analysis else [],
    )

    return WriterUpdate(
        final_report=report,
        errors=list(state.get("errors", [])),
    )


__all__ = ["WriterUpdate", "run_writer"]
