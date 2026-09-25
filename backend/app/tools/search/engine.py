"""Parallel search engine — fan-out Tavily across N queries.

Tavily is the single search backend (DuckDuckGo removed: persistently
rate-limited under parallel load, zero successful responses in production logs).
"""

import asyncio
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.tools.search.tavily_tool import search_tavily

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def normalize_url(url: str) -> str:
    try:
        p = urlparse((url or "").strip())
        if not p.scheme or not p.netloc:
            return (url or "").strip()
        netloc = p.netloc.lower()
        path = p.path.rstrip("/") or ""
        query = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in _TRACKING_PARAMS]
        return urlunparse((p.scheme.lower(), netloc, path, "", urlencode(query), ""))
    except Exception:
        return (url or "").strip()


async def parallel_search(
    queries: List[str],
    max_results_per_query: int = 3,
    max_concurrency: int = 8,
    timeout_per_query: float = 20.0,
    search_depth: str | None = None,
) -> List[Dict[str, Any]]:
    """Fan out Tavily search for N queries in parallel, deduped by normalized URL."""
    clean = [q.strip() for q in (queries or []) if q and q.strip()]
    if not clean:
        return []

    sem = asyncio.Semaphore(max_concurrency)

    async def _guarded(coro):
        async with sem:
            return await coro

    tasks = [
        _guarded(
            search_tavily(
                q,
                max_results_per_query,
                search_depth=search_depth,
                timeout=timeout_per_query,
            )
        )
        for q in clean
    ]

    nested = await asyncio.gather(*tasks, return_exceptions=True)

    flat: List[Dict[str, Any]] = []
    seen: set = set()
    for item in nested:
        if not isinstance(item, list):
            continue
        # Prefer higher-scored docs within the same batch
        try:
            item = sorted(item, key=lambda d: (d.get("score") is None, -(d.get("score") or 0)))
        except Exception:
            pass
        for doc in item:
            url = (doc.get("url") or "").strip()
            if not url:
                continue
            key = normalize_url(url)
            if key in seen:
                continue
            seen.add(key)
            if not doc.get("content") and not doc.get("title"):
                continue
            flat.append(doc)
    return flat
