# app/agents/analyst/agent.py
import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.schemas.research import AnalystOutput, Finding


# ============================================================
# TẠM THỜI — thay bằng import từ app.tools.llm.factory khi Dũng push xong
# ============================================================
def _get_temp_model(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
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


async def run_analyst(state: dict[str, Any]) -> dict[str, Any]:
    """Node Analyst: nhận findings từ state, trả về AnalystOutput đã kiểm định."""
    raw_findings = state.get("findings", [])
    findings = [Finding(**f) for f in raw_findings]

    if not findings:
        # Không có dữ liệu đầu vào -> trả về ngay, không gọi LLM tốn phí
        fallback = AnalystOutput(
            status="needs_more_research",
            confidence_score=0.0,
            verified_findings=[],
            conclusions=[],
            insights=[],
            limitations=["Không có dữ liệu findings đầu vào để phân tích."],
        )
        return {"analysis": fallback.model_dump()}

    model = _get_temp_model(temperature=0.1)
    prompt = [
        {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
        {"role": "user", "content": f"Findings:\n{[f.model_dump() for f in findings]}"},
    ]

    try:
        result: AnalystOutput = await _invoke_temp(
            model, prompt, structured_schema=AnalystOutput
        )
    except Exception as e:  # noqa: BLE001
        # Chưa có retry thật (chờ Dũng), nên tạm bắt lỗi để không sập cả graph
        fallback = AnalystOutput(
            status="needs_more_research",
            confidence_score=0.0,
            verified_findings=[],
            conclusions=[],
            insights=[],
            limitations=[f"Lỗi khi gọi LLM: {e!s}"],
        )
        return {"analysis": fallback.model_dump()}

    return {"analysis": result.model_dump()}
