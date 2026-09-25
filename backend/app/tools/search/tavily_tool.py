"""Tavily Search tool — deep web search
"""

import asyncio
import os
from typing import Any, Dict, List

from loguru import logger
from tavily import AsyncTavilyClient

_tavily_client = None
_logged_no_key = False


def _get_client():
    global _tavily_client, _logged_no_key
    if _tavily_client is not None:
        return _tavily_client
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        if not _logged_no_key:
            _logged_no_key = True
            logger.info("TAVILY_API_KEY chưa cấu hình — search trả rỗng.")
        return None
    try:
        _tavily_client = AsyncTavilyClient(api_key=api_key)
        return _tavily_client
    except Exception as e:
        logger.warning(f"Tavily init failed: {e}")
        return None


async def search_tavily(
    query: str,
    max_results: int = 3,
    search_depth: str | None = None,
    timeout: float = 20.0,
) -> List[Dict[str, Any]]:
    """Search 1 query via Tavily, return list of {url, title, content, score, source, query}.

    search_depth: "basic" (1 credit/query) or "advanced" (2 credits/query).
    Defaults to TAVILY_SEARCH_DEPTH, falling back to "basic" to save demo quota.
    """
    query = (query or "").strip()
    if not query:
        return []
    depth = search_depth or os.getenv("TAVILY_SEARCH_DEPTH", "basic")
    client = _get_client()
    if client is None:
        return []
    try:
        res = await asyncio.wait_for(
            client.search(query=query, search_depth=depth, max_results=max_results),
            timeout=timeout,
        )
        docs: List[Dict[str, Any]] = []
        for r in (res or {}).get("results", []):
            url = (r.get("url") or "").strip()
            if not url:
                continue
            docs.append(
                {
                    "url": url,
                    "title": (r.get("title") or "").strip(),
                    "content": (r.get("content") or "").strip(),
                    "score": r.get("score"),
                    "source": "tavily",
                    "region": "global",
                    "published_at": r.get("published_date"),
                    "query": query,
                }
            )
        return docs
    except Exception as e:
        logger.warning(f"Tavily search failed query={query!r}: {e}")
        return []
