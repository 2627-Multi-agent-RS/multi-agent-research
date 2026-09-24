"""Application-scoped dependencies for the realtime gateway."""

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.services.connection_mgr import ConnectionManager


@lru_cache
def get_connection_manager() -> ConnectionManager:
    """Singleton ConnectionManager dùng để quản lý các kết nối WebSocket và broadcast theo thread_id."""
    return ConnectionManager()


_cached_graph: Any | None = None


async def get_research_graph() -> Any | None:
    """Khởi tạo và biên dịch StateGraph đồ thị nghiên cứu kèm SQLite Checkpointer.

    Dùng AsyncSqliteSaver (bản sync SqliteSaver không chạy được với
    astream_events bất đồng bộ). Graph được build 1 lần và cache process-wide.
    Nếu bật cờ USE_MOCK_RESEARCH, trả về None để stream_research kích hoạt mock stream.
    """
    global _cached_graph
    if settings.use_mock_research:
        return None
    if _cached_graph is not None:
        return _cached_graph

    try:
        from app.graph.build import build_research_graph, get_async_sqlite_checkpointer
    except ImportError as exc:
        raise RuntimeError(
            "The LangGraph research pipeline is unavailable. Install backend "
            "dependencies and provide app.graph.build.build_research_graph."
        ) from exc

    checkpointer = await get_async_sqlite_checkpointer(settings.checkpoint_db_path)
    _cached_graph = build_research_graph(checkpointer=checkpointer)
    return _cached_graph