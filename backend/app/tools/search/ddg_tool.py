"""DuckDuckGo Search tool

note: use asyncio.to_thread to run sync DDGS() in FastAPI/LangGraph event loop.
"""

import asyncio
from typing import Any, Dict, List

import primp
from duckduckgo_search import DDGS
from loguru import logger


def _patch_primp_impersonate() -> None:
    _OrigClient = primp.Client

    def _Client(*args, **kwargs):  # type: ignore[no-untyped-def]
        imp = kwargs.get("impersonate")
        if isinstance(imp, str):
            lowered = imp.lower()
            if lowered.startswith("firefox"):
                kwargs["impersonate"] = "firefox"
            elif lowered.startswith("safari"):
                kwargs["impersonate"] = "safari"
            elif lowered.startswith(("chrome", "edge", "opera")):
                kwargs["impersonate"] = "chrome"
            else:
                kwargs["impersonate"] = "random"
            try:
                return _OrigClient(*args, **kwargs)
            except Exception:
                kwargs["impersonate"] = "random"
                return _OrigClient(*args, **kwargs)
        return _OrigClient(*args, **kwargs)

    primp.Client = _Client  # type: ignore[method-assign]


_patch_primp_impersonate()

def _sync_search(query: str, max_results: int, region: str) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results, region=region):
            url = (r.get("href") or "").strip()
            if not url:
                continue
            docs.append(
                {
                    "url": url,
                    "title": (r.get("title") or "").strip(),
                    "content": (r.get("body") or "").strip(),
                    "score": None,
                    "source": "duckduckgo",
                    "region": region,
                    "published_at": None,
                    "query": query,
                }
            )
    return docs


async def search_duckduckgo(
    query: str,
    max_results: int = 3,
    timeout: float = 20.0,
    region: str = "wt-wt",
) -> List[Dict[str, Any]]:
    """Search 1 query via DuckDuckGo (non-blocking wrapper).

    region: 'wt-wt' international, 'us-en' English sources, 'vn-vi' Vietnamese sources.
    """
    query = (query or "").strip()
    if not query:
        return []
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_search, query, max_results, region),
            timeout=timeout,
        )
    except Exception as e:
        logger.warning(f"DDG search failed query={query!r} region={region!r}: {e}")
        return []
