"""LLM extraction: combined_context -> standard findings via the Gemini singleton.

Success -> list[Finding] following RESEARCHER_EXTRACTION_PROMPT.
Any failure (missing key, 404, schema error) -> None, caller keeps the heuristic
so the pipeline survives running without an LLM.
"""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.researcher.prompts import RESEARCHER_EXTRACTION_PROMPT
from app.schemas.research import Finding, ResearcherOutput
from app.tools.llm.factory import LLMFactory, invoke_with_resilience


async def extract_findings_llm(
    combined_context: str, queries: list[str]
) -> list[Finding] | None:
    if not (combined_context or "").strip():
        return None
    try:
        model = LLMFactory.get_primary_model(temperature=0.1, timeout=30)
        messages = [
            SystemMessage(content=RESEARCHER_EXTRACTION_PROMPT),
            HumanMessage(content=f"Truy vấn: {queries}\n\nTài liệu:\n{combined_context}"),
        ]
        out = await invoke_with_resilience(
            model,
            messages,
            ResearcherOutput,
            fallback_model=LLMFactory.get_fallback_model(temperature=0.1),
        )
        if not isinstance(out, ResearcherOutput) or not out.findings:
            return None
        logger.info(f"LLM extraction OK: {len(out.findings)} findings.")
        return list(out.findings)
    except Exception as e:  # noqa: BLE001 — any LLM error falls back to heuristic
        logger.warning(f"LLM extraction failed, giữ heuristic: {e}")
        return None


__all__ = ["extract_findings_llm"]
