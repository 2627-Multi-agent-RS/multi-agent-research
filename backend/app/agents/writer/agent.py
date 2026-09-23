# app/agents/writer/agent.py
"""Writer Agent node implementation."""

import os
from typing import Any, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.writer.prompts import WRITER_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.schemas.research import Citation, Finding, WriterOutput


class WriterUpdate(TypedDict, total=False):
    final_report: WriterOutput
    errors: list[str]


# ============================================================
# TẠM THỜI — thay bằng import từ app.tools.llm.factory khi Dũng push xong
# ============================================================
def _get_temp_model(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=temperature,
        timeout=30,
    )


async def _invoke_temp(
    model: Any, prompt_messages: list[dict[str, str]], structured_schema: Any
) -> Any:
    target = model.with_structured_output(structured_schema)
    return await target.ainvoke(prompt_messages)


# ============================================================


def _build_citations(findings: list[Finding]) -> list[Citation]:
    """Dedupe theo source_url, gán id tuần tự — làm bằng code để đảm bảo chính xác 100%."""
    seen: dict[str, Citation] = {}
    next_id = 1
    for f in findings:
        if f.source_url not in seen:
            seen[f.source_url] = Citation(
                id=next_id,
                title=f.source_title,
                url=f.source_url,
                snippet=f.evidence[:200],
            )
            next_id += 1
    return list(seen.values())


def _apply_warning_block(content: str, analysis: dict[str, Any]) -> tuple[str, list[str]]:
    """Graceful degradation bằng code — không để LLM tự quyết định."""
    warnings: list[str] = []
    needs_warning = (
        analysis.get("status") == "needs_more_research"
        or len(analysis.get("conflicts", [])) > 0
    )

    if needs_warning:
        conflicts = analysis.get("conflicts", [])
        limitations = analysis.get("limitations", [])
        warning_lines = ["## ⚠️ Cảnh báo & Giới hạn dữ liệu\n"]
        if conflicts:
            warning_lines.append("**Mâu thuẫn số liệu phát hiện được:**")
            warning_lines.extend(f"- {c}" for c in conflicts)
        if limitations:
            warning_lines.append("\n**Giới hạn dữ liệu:**")
            warning_lines.extend(f"- {l}" for l in limitations)
        warning_block = "\n".join(warning_lines) + "\n\n---\n\n"
        content = warning_block + content
        warnings = conflicts + limitations

    return content, warnings


def _to_dict(obj: Any) -> dict[str, Any]:
    """analysis trong state có thể là dict (từ node khác serialize) hoặc AnalystOutput object."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj or {}


async def run_writer(state: AgentState) -> WriterUpdate:
    """Node Writer: nhận analysis đã kiểm định, sinh báo cáo Markdown hoàn chỉnh."""
    analysis = _to_dict(state.get("analysis"))
    raw_findings = analysis.get("verified_findings", []) or state.get("findings", [])
    verified_findings = [
        Finding(**f) if isinstance(f, dict) else f for f in raw_findings
    ]

    citations = _build_citations(verified_findings)
    citations_text = "\n".join(f"[{c.id}] {c.title} - {c.url}" for c in citations)

    model = _get_temp_model(temperature=0.3)
    prompt = [
        {"role": "system", "content": WRITER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Conclusions:\n{analysis.get('conclusions', [])}\n\n"
                f"Insights:\n{analysis.get('insights', [])}\n\n"
                f"Verified Findings:\n{[f.model_dump() for f in verified_findings]}\n\n"
                f"Citations có sẵn (dùng đúng số này):\n{citations_text}"
            ),
        },
    ]

    try:
        result: WriterOutput = await _invoke_temp(
            model, prompt, structured_schema=WriterOutput
        )
    except Exception as e:  # noqa: BLE001 — tạm thời bắt mọi lỗi, sẽ thay bằng retry logic của Dũng
        result = WriterOutput(
            status="partial",
            title="Báo cáo chưa hoàn chỉnh",
            content=f"Đã xảy ra lỗi khi sinh báo cáo: {e!s}",
            citations=citations,
            warnings=[],
        )

    final_content, extra_warnings = _apply_warning_block(result.content, analysis)
    result.content = final_content
    result.citations = citations
    result.warnings = extra_warnings

    return WriterUpdate(
        final_report=result,
        errors=list(state.get("errors", [])),
    )


__all__ = ["WriterUpdate", "run_writer"]