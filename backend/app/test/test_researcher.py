"""Test runner RIÊNG cho Researcher agent — KHÔNG phải main toàn hệ thống.

- main hệ thống sau này nằm ở backend/app/main.py (FastAPI + LangGraph).
- File này chỉ phục vụ dev/test Researcher:
  TOPIC -> resolve_queries -> research_topic -> ghi JSON + in tóm tắt.

Chạy từ repo root:
    ./backend/.venv/bin/python backend/app/test/test_researcher.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# SETTING TEST — sửa ở đây để test case khác
# ---------------------------------------------------------------------------
TOPIC = "Tổng hợp thông tin thị trường game trên tất cả các nền tảng trên toàn thế giới vào năm 2026"

# Để trống -> dùng [TOPIC]. Điền tay để giả lập sub-queries của Orchestrator,
# nên kèm 1-2 query tiếng Anh để Tavily lấy nguồn ngoại.
SUB_QUERIES: list = []

MAX_RESULTS_PER_QUERY = 3  # số doc mỗi engine mỗi query
SCRAPE_TOP_N = 5  # số link cào full-text
SEARCH_DEPTH = None  # None = theo TAVILY_SEARCH_DEPTH (mặc định "basic"); "advanced" tốn 2 credit/query
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/app/test/ -> backend/
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

OUTPUT_FILE = BACKEND_DIR / "researcher_output.json"


def _load_dotenv() -> None:
    import os

    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def _smoke_check(result: Dict[str, Any]) -> None:
    """Check nhanh output researcher có đúng contract cho Analyst không."""
    assert isinstance(result["search_docs"], list)
    assert isinstance(result["findings"], list)
    for doc in result["search_docs"]:
        assert doc.get("url", "").startswith("http"), f"doc thiếu URL: {doc}"
        assert "region" in doc, f"doc thiếu region: {doc.get('url')}"
    for f in result["findings"]:
        assert f.get("source_url", "").startswith("http"), f"finding thiếu source_url: {f}"


def _print_summary(payload: Dict[str, Any]) -> None:
    print(f"Topic: {payload['topic']}")
    print(f"Queries ({len(payload['queries'])}): {payload['queries']}")
    print(f"Docs: {payload['stats']['search_docs']}, "
          f"scraped: {payload['stats']['scraped']}, "
          f"findings: {payload['stats']['findings']}")
    for doc in payload["search_docs"]:
        print(f"  - [{doc['source']}/{doc.get('region')}] {doc['url'][:70]} "
              f"| date={doc.get('published_at')}")
    if payload["limitations"]:
        print(f"Limitations: {payload['limitations']}")
    print(f"Ghi xong: {OUTPUT_FILE}")


async def main() -> dict:
    from app.agents.researcher.agent import research_topic, resolve_queries

    _load_dotenv()

    # Giả lập state như Orchestrator trả về
    state = {
        "topic": TOPIC,
        "plan": {"sub_queries": SUB_QUERIES or [TOPIC]},
        "retry_count": 0,
    }
    queries = resolve_queries(state)
    result = await research_topic(
        queries,
        scrape_top_n=SCRAPE_TOP_N,
        max_results_per_query=MAX_RESULTS_PER_QUERY,
        search_depth=SEARCH_DEPTH,
    )
    _smoke_check(result)

    payload = {
        "topic": TOPIC,
        "queries": queries,
        "settings": {
            "max_results_per_query": MAX_RESULTS_PER_QUERY,
            "scrape_top_n": SCRAPE_TOP_N,
            "search_depth": SEARCH_DEPTH,
        },
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "search_docs": len(result["search_docs"]),
            "scraped": len(result["scraped"]),
            "findings": len(result["findings"]),
            "context_chars": len(result["combined_context"]),
        },
        **result,
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_summary(payload)
    return payload


if __name__ == "__main__":
    asyncio.run(main())
