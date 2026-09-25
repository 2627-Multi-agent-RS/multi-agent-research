"""Researcher Agent node — parallel Tavily search + full-text scraping.

Receives queries from Orchestrator (plan.sub_queries) or Analyst (follow_up_request),
fans out to Tavily, scrapes top-N, returns Pydantic findings.

Submodules:
    queries.py  — resolve_queries / get_follow_up_questions
    context.py  — build_context (merge snippets + full-text for Analyst/debug)
    findings.py — build_heuristic_findings / merge_findings / coerce_finding
    extract.py  — extract_findings_llm (LLM structured, heuristic fallback)
    prompts.py  — RESEARCHER_EXTRACTION_PROMPT
"""

import time
from typing import Any, TYPE_CHECKING, TypedDict

from loguru import logger

from app.agents.researcher.context import build_context
from app.agents.researcher.extract import extract_findings_llm
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
    """Partial state update returned to the StateGraph (matches the original demo stub)."""

    findings: list[Finding]
    search_queries: list[str]
    retry_count: int
    errors: list[str]


async def research_topic(
    queries: list[str],
    scrape_top_n: int = SCRAPE_TOP_N,
    max_results_per_query: int = 3,
    search_depth: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Take queries -> search + scrape -> return full info (findings are Pydantic).

    Return: {search_docs, scraped, combined_context, findings, search_queries, limitations}
    """
    log = logger.bind(thread_id=thread_id or "-")
    clean = [q.strip() for q in (queries or []) if q and q.strip()][:MAX_QUERIES]
    if not clean:
        log.warning("research_topic: no_queries_provided.")
        return {
            "search_docs": [],
            "scraped": {},
            "combined_context": "",
            "findings": [],
            "search_queries": [],
            "limitations": ["no_queries_provided"],
        }

    log.info(f"research_start: {len(clean)} queries.")
    t0 = time.perf_counter()
    search_docs = await parallel_search(
        clean, max_results_per_query=max_results_per_query, search_depth=search_depth
    )
    by_source: dict[str, int] = {}
    for d in search_docs:
        by_source[d.get("source", "?")] = by_source.get(d.get("source", "?"), 0) + 1
    log.info(
        f"search_done: {len(search_docs)} docs {by_source} ({time.perf_counter() - t0:.1f}s)."
    )
    if not search_docs:
        log.warning("research_topic: no_docs_found (Tavily rỗng).")
        return {
            "search_docs": [],
            "scraped": {},
            "combined_context": "",
            "findings": [],
            "search_queries": clean,
            "limitations": ["no_docs_found: Tavily rỗng, kiểm tra mạng/API key"],
        }

    limitations: list[str] = []
    top_urls = [d["url"] for d in search_docs[:scrape_top_n] if d.get("url")]
    t1 = time.perf_counter()
    scraped_with_dates = await scrape_articles_with_dates(top_urls) if top_urls else {}
    scraped = {url: info["text"] for url, info in scraped_with_dates.items()}
    log.info(
        f"scrape_done: {len(scraped)}/{len(top_urls)} urls ({time.perf_counter() - t1:.1f}s)."
    )
    if top_urls and not scraped:
        log.warning("research_topic: scrape_empty — chỉ dùng snippet search.")
        limitations.append("scrape_empty: không cào được full-text, chỉ dùng snippet search")

    combined_context = build_context(search_docs, scraped)
    findings = build_heuristic_findings(search_docs)

    llm_findings = await extract_findings_llm(combined_context, clean)
    origin = "heuristic"
    if llm_findings:
        findings = llm_findings
        origin = "llm"
    log.info(
        f"research_done: {len(findings)} findings (nguồn: {origin}), "
        f"total {time.perf_counter() - t0:.1f}s."
    )

    # Backfill publish dates from scraped page metadata (take it when present, skip otherwise)
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
    """Node wrapper: state -> ResearcherUpdate (Pydantic findings, accumulated across retries)."""
    thread_id = state.get("thread_id", "-") if isinstance(state, dict) else "-"
    is_follow_up = bool(get_follow_up_questions(state))
    result = await research_topic(resolve_queries(state), thread_id=thread_id)

    retry_count = state.get("retry_count", 0) or 0
    if is_follow_up:
        # Researcher owns the retry increment (Analyst keeps it, routing caps at 1).
        retry_count += 1
    logger.bind(thread_id=thread_id).info(
        f"researcher_node: follow_up={is_follow_up} retry_count={retry_count} "
        f"errors={len(result['limitations'])}."
    )

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
    "extract_findings_llm",
    "merge_findings",
    "research_topic",
    "resolve_queries",
    "run_researcher",
]
