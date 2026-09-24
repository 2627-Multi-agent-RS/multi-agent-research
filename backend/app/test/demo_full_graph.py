"""Demo full MAS graph: orchestrator -> researcher -> analyst -> writer.

Chạy từ repo root:
    ./backend/.venv/bin/python backend/app/test/demo_full_graph.py [topic]

Kết quả: in tiến trình từng node + tóm tắt báo cáo, lưu JSON vào backend/output/.
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.graph.build import build_research_graph, get_async_sqlite_checkpointer
from app.services.research_service import build_initial_state

DEFAULT_TOPIC = "Tiến trình phát triển xe điện toàn cầu năm 2025"
OUTPUT_DIR = BACKEND_DIR / "output"


def _output_file(topic: str) -> Path:
    """output/demo_<slug>_<UTC-timestamp>.json — mỗi lần chạy 1 file riêng."""
    slug = re.sub(r"[^\w]+", "-", topic.strip().lower()).strip("-")[:50] or "demo"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"demo_{slug}_{stamp}.json"


async def main() -> None:
    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC
    thread_id = "demo-thread-1"

    checkpointer = await get_async_sqlite_checkpointer(":memory:")
    graph = build_research_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    state = build_initial_state(thread_id, topic)

    print(f"Topic: {topic}\n")
    final = None
    async for event in graph.astream(state, config=config):
        for node, update in event.items():
            keys = list((update or {}).keys())
            print(f"[node xong] {node}: {keys}")
            final = update

    snap = await graph.aget_state(config)
    s = snap.values
    report = s.get("final_report")
    print("\n===== KẾT QUẢ =====")
    print("retry_count:", s.get("retry_count"))
    print("findings:", len(s.get("findings", [])))
    analysis = s.get("analysis")
    if analysis is not None:
        print("analyst status:", analysis.status, "| confidence:", analysis.confidence_score)
        print("conflicts:", analysis.conflicts)
    if report is not None:
        print("report title:", report.title)
        print("citations:", len(report.citations), "| warnings:", report.warnings)
        print("\n--- content (500 ký tự đầu) ---\n" + report.content[:500])

    def _dump(obj):
        return obj.model_dump() if hasattr(obj, "model_dump") else obj

    out = {
        "topic": topic,
        "retry_count": s.get("retry_count"),
        "errors": s.get("errors", []),
        "plan": _dump(s.get("plan")),
        "findings": [_dump(f) for f in s.get("findings", [])],
        "analysis": _dump(analysis),
        "final_report": _dump(report),
    }
    output_file = _output_file(topic)
    output_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGhi xong: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
