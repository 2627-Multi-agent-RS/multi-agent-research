# app/agents/analyst/agent.py
"""Analyst Agent node implementation."""

from typing import Any, TYPE_CHECKING, TypedDict

from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.schemas.research import AnalystOutput, Finding
from app.tools.llm.factory import LLMFactory

if TYPE_CHECKING:
    from app.graph.state import AgentState


class AnalystUpdate(TypedDict, total=False):
    analysis: AnalystOutput
    retry_count: int
    errors: list[str]


async def _invoke_temp(
    model: Any, prompt_messages: list[dict[str, str]], structured_schema: Any
) -> Any:
    """use primary model, fallback to secondary if fails."""
    try:
        target = model.with_structured_output(structured_schema)
        return await target.ainvoke(prompt_messages)
    except Exception:
        fallback = LLMFactory.get_fallback_model()
        target = fallback.with_structured_output(structured_schema)
        return await target.ainvoke(prompt_messages)


async def run_analyst(state: "AgentState") -> AnalystUpdate:
    """Execute analysis, verification, and conflict detection on collected findings."""
    retry_count = state.get("retry_count", 0)
    raw_findings = state.get("findings", [])
    findings = [Finding(**f) if isinstance(f, dict) else f for f in raw_findings]

    if not findings:
        fallback = AnalystOutput(
            status="needs_more_research",
            confidence_score=0.0,
            verified_findings=[],
            conclusions=[],
            insights=[],
            limitations=["Không có dữ liệu findings đầu vào để phân tích."],
        )
        return AnalystUpdate(
            analysis=fallback,
            retry_count=retry_count,
            errors=list(state.get("errors", [])),
        )

    model = LLMFactory.get_primary_model(temperature=0.1, timeout=30)
    topic = state.get("topic", "") if isinstance(state, dict) else ""
    prompt = [
        {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
        {"role": "user", "content": f"Đề tài gốc: {topic}\n\nFindings:\n{[f.model_dump() for f in findings]}"},
    ]

    try:
        result: AnalystOutput = await _invoke_temp(
            model, prompt, structured_schema=AnalystOutput
        )
    except Exception as e:  # noqa: BLE001
        result = AnalystOutput(
            status="needs_more_research",
            confidence_score=0.0,
            verified_findings=[],
            conclusions=[],
            insights=[],
            limitations=[f"Lỗi khi gọi LLM: {e!s}"],
        )

    return AnalystUpdate(
        analysis=result,
        retry_count=retry_count,
        errors=list(state.get("errors", [])),
    )


__all__ = ["AnalystUpdate", "run_analyst"]
