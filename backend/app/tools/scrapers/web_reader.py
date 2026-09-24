import asyncio
from typing import Dict, List

from loguru import logger
from trafilatura import extract, fetch_url


def _sync_fetch_extract(url: str) -> tuple:
    """Trả về (clean_text, published_date). Date có thể None nếu trang không ghi ngày."""
    downloaded = fetch_url(url)
    if not downloaded:
        return "", None
    text = extract(downloaded, include_comments=False, include_tables=True) or ""
    date = None
    try:
        meta_json = extract(
            downloaded,
            output_format="json",
            with_metadata=True,
            include_comments=False,
            include_tables=False,
        )
        if meta_json:
            import json as _json

            date = _json.loads(meta_json).get("date")
    except Exception:
        pass
    return text, date


async def extract_clean_article(url: str, max_chars: int = 4000, timeout: float = 25.0) -> str:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return ""
    try:
        text, _ = await asyncio.wait_for(
            asyncio.to_thread(_sync_fetch_extract, url),
            timeout=timeout,
        )
        return (text or "")[:max_chars]
    except Exception as e:
        logger.warning(f"Scrape failed {url!r}: {e}")
        return ""


async def scrape_articles(
    urls: List[str],
    max_chars: int = 4000,
    max_concurrency: int = 3,
) -> Dict[str, str]:
    """Crawl top-N URLs in parallel, return dict {url: clean_text}"""
    clean = [u.strip() for u in (urls or []) if u and u.strip()]
    if not clean:
        return {}
    sem = asyncio.Semaphore(max_concurrency)

    async def _one(url: str):
        async with sem:
            return url, await extract_clean_article(url, max_chars=max_chars)

    results = await asyncio.gather(*[_one(u) for u in clean], return_exceptions=True)
    out: Dict[str, str] = {}
    for r in results:
        if isinstance(r, tuple):
            url, text = r
            if isinstance(text, str) and text.strip():
                out[url] = text
    return out


async def scrape_articles_with_dates(
    urls: list,
    max_chars: int = 4000,
    max_concurrency: int = 3,
) -> Dict[str, dict]:
    clean = [u.strip() for u in (urls or []) if u and u.strip()]
    if not clean:
        return {}
    sem = asyncio.Semaphore(max_concurrency)

    async def _one(url: str):
        async with sem:
            if not url.startswith(("http://", "https://")):
                return url, ("", None)
            try:
                text, date = await asyncio.wait_for(
                    asyncio.to_thread(_sync_fetch_extract, url),
                    timeout=25.0,
                )
                return url, ((text or "")[:max_chars], date)
            except Exception as e:
                logger.warning(f"Scrape failed {url!r}: {e}")
                return url, ("", None)

    results = await asyncio.gather(*[_one(u) for u in clean], return_exceptions=True)
    out: Dict[str, dict] = {}
    for r in results:
        if isinstance(r, tuple):
            url, (text, date) = r
            if isinstance(text, str) and text.strip():
                out[url] = {"text": text, "date": date}
    return out
