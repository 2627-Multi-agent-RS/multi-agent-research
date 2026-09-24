"""Researcher Agent node — tìm kiếm song song đa nguồn + cào full-text.

Nhận queries từ Orchestrator (plan.sub_queries) hoặc Analyst (follow_up_request),
gọi Tavily + DuckDuckGo đa region, scrape top-N, trả findings Pydantic cho graph.

Chi tiết nằm ở các module con:
    queries.py  — resolve_queries / get_follow_up_questions
    context.py  — build_context (gộp snippet + full-text cho Analyst/debug)
    findings.py — build_heuristic_findings / merge_findings / coerce_finding
    prompts.py  — RESEARCHER_EXTRACTION_PROMPT (dự phòng khi link LLM)
"""

from typing import Any, TYPE_CHECKING, TypedDict

from app.agents.researcher.context import build_context
from app.agents.researcher.findings import (
    build_heuristic_findings,
    coerce_finding,
    merge_findings,
)
from app.agents.researcher.queries import (
    MAX_QUERIES,
    get_follow_up_questions,
    resolve_queries,
)
from app.schemas.research import Finding
from app.tools.scrapers.web_reader import scrape_articles_with_dates
from app.tools.search.engine import parallel_search

if TYPE_CHECKING:
    from app.graph.state import AgentState

SCRAPE_TOP_N = 5


class ResearcherUpdate(TypedDict, total=False):
    """Partial state update trả về StateGraph (khớp stub demo ban đầu)."""

    findings: list[Finding]
    search_queries: list[str]
    retry_count: int
    errors: list[str]


async def research_topic(
    queries: list[str],
    scrape_top_n: int = SCRAPE_TOP_N,
    max_results_per_query: int = 3,
    search_depth: str | None = None,
) -> dict[str, Any]:
    """Nhận queries -> search + scrape -> trả full info (findings là Pydantic).

    Return: {search_docs, scraped, combined_context, findings, search_queries, limitations}
    """
    clean = [q.strip() for q in (queries or []) if q and q.strip()][:MAX_QUERIES]
    if not clean:
        return {
            "search_docs": [],
            "scraped": {},
            "combined_context": "",
            "findings": [],
            "search_queries": [],
            "limitations": ["no_queries_provided"],
        }

    search_docs = await parallel_search(
        clean, max_results_per_query=max_results_per_query, search_depth=search_depth
    )
    if not search_docs:
        return {
            "search_docs": [],
            "scraped": {},
            "combined_context": "",
            "findings": [],
            "search_queries": clean,
            "limitations": ["no_docs_found: Tavily + DDG đều rỗng, kiểm tra mạng/API key"],
        }

    limitations: list[str] = []
    top_urls = [d["url"] for d in search_docs[:scrape_top_n] if d.get("url")]
    scraped_with_dates = await scrape_articles_with_dates(top_urls) if top_urls else {}
    scraped = {url: info["text"] for url, info in scraped_with_dates.items()}
    if top_urls and not scraped:
        limitations.append("scrape_empty: không cào được full-text, chỉ dùng snippet search")

    combined_context = build_context(search_docs, scraped)
    findings = build_heuristic_findings(search_docs)

    # Backfill ngày xuất bản từ metadata trang đã cào được (có thì lấy, không thì thôi)
    for f in findings:
        if not f.published_at:
            info = scraped_with_dates.get(f.source_url) or {}
            if info.get("date"):
                f.published_at = info["date"]

    return {
        "search_docs": search_docs,
        "scraped": scraped,
        "combined_context": combined_context,
        "findings": findings,
        "search_queries": clean,
        "limitations": limitations,
    }


async def run_researcher(state: "AgentState") -> ResearcherUpdate:
    """Node wrapper: state -> ResearcherUpdate (findings Pydantic, cộng dồn qua retry)."""
    is_follow_up = bool(get_follow_up_questions(state))
    result = await research_topic(resolve_queries(state))

    retry_count = state.get("retry_count", 0) or 0
    if is_follow_up:
        # Researcher là node tăng retry (Analyst giữ nguyên, routing cap 1 lần).
        retry_count += 1

    prev_q = state.get("search_queries", []) or []
    merged_q = list(dict.fromkeys([*prev_q, *result["search_queries"]]))

    errors = list(state.get("errors", []) or [])
    errors.extend(result["limitations"])

    return ResearcherUpdate(
        findings=merge_findings(state.get("findings", []) or [], result["findings"]),
        search_queries=merged_q,
        retry_count=retry_count,
        errors=errors,
    )


__all__ = [
    "SCRAPE_TOP_N",
    "ResearcherUpdate",
    "build_context",
    "build_heuristic_findings",
    "coerce_finding",
    "merge_findings",
    "research_topic",
    "resolve_queries",
    "run_researcher",
]
