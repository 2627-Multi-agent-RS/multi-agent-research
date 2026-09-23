"""Researcher Agent — điều phối: nhận queries -> search song song -> scrape -> trả info.
"""

from typing import Any, Dict, List

from app.agents.researcher.context import build_context
from app.agents.researcher.findings import build_heuristic_findings, merge_findings
from app.agents.researcher.queries import MAX_QUERIES, resolve_queries
from app.tools.scrapers.web_reader import scrape_articles_with_dates
from app.tools.search.engine import parallel_search

SCRAPE_TOP_N = 5

async def research_topic(
    queries: List[str],
    scrape_top_n: int = SCRAPE_TOP_N,
    max_results_per_query: int = 3,
    search_depth: str | None = None,
) -> Dict[str, Any]:
    """Research a topic by resolving queries -> search + scrape -> return full info for Analyst.

    Return: {
        search_docs, 
        scraped, 
        combined_context, 
        findings, 
        search_queries, 
        limitations
    }
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
            "limitations": [
                "no_docs_found: Tavily + DDG are empty, check your API key or network",
            ],
        }

    limitations: List[str] = []
    top_urls = [d["url"] for d in search_docs[:scrape_top_n] if d.get("url")]
    scraped_with_dates = await scrape_articles_with_dates(top_urls) if top_urls else {}
    scraped = {url: info["text"] for url, info in scraped_with_dates.items()}
    if top_urls and not scraped:
        limitations.append("scrape_empty: cannot scrape any of the top URLs")

    combined_context = build_context(search_docs, scraped)
    findings = build_heuristic_findings(search_docs)

    for f in findings:
        if not f.get("published_at"):
            info = scraped_with_dates.get(f.get("source_url", "") or "") or {}
            if info.get("date"):
                f["published_at"] = info["date"]

    return {
        "search_docs": search_docs,
        "scraped": scraped,
        "combined_context": combined_context,
        "findings": findings,
        "search_queries": clean,
        "limitations": limitations,
    }


async def run_researcher(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node wrapper spec-compatible: state -> {findings, search_queries}."""
    result = await research_topic(resolve_queries(state))

    prev_q = state.get("search_queries", []) or []
    merged_q = list(dict.fromkeys([*prev_q, *result["search_queries"]]))

    out: Dict[str, Any] = {
        "findings": merge_findings(state.get("findings", []) or [], result["findings"]),
        "search_queries": merged_q,
    }
    if result["limitations"]:
        out["errors"] = [*state.get("errors", []), *result["limitations"]]
    return out


__all__ = [
    "SCRAPE_TOP_N",
    "build_context",
    "build_heuristic_findings",
    "merge_findings",
    "research_topic",
    "resolve_queries",
    "run_researcher",
]
