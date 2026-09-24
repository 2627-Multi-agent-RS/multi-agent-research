"""Tavily Search tool — deep web search
"""

import asyncio
import os
from typing import Any, Dict, List

from loguru import logger
from tavily import AsyncTavilyClient

_tavily_client = None


def _get_client():
    global _tavily_client
    if _tavily_client is not None:
        return _tavily_client
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
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
    """Tìm kiếm 1 query qua Tavily, trả về list {url, title, content, score, source, query}.

    search_depth: "basic" (1 credit/query) hoặc "advanced" (2 credits/query).
    Mặc định đọc TAVILY_SEARCH_DEPTH, fallback "basic" để tiết kiệm quota demo.
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
