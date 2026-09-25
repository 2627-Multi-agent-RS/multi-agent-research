"""Application-scoped dependencies for the realtime gateway."""

from functools import lru_cache
from typing import Any

from loguru import logger

from app.core.config import settings
from app.services.connection_mgr import ConnectionManager


@lru_cache
def get_connection_manager() -> ConnectionManager:
    """Singleton ConnectionManager dùng để quản lý các kết nối WebSocket và broadcast theo thread_id."""
    return ConnectionManager()


_cached_graph: Any | None = None
_cached_conn: Any | None = None


async def get_research_graph() -> Any | None:
    """Khởi tạo và biên dịch StateGraph đồ thị nghiên cứu kèm SQLite Checkpointer.

    Dùng AsyncSqliteSaver (bản sync SqliteSaver không chạy được với
    astream_events bất đồng bộ). Graph được build 1 lần và cache process-wide.
    Nếu bật cờ USE_MOCK_RESEARCH, trả về None để stream_research kích hoạt mock stream.
    """
    global _cached_graph, _cached_conn
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
    _cached_conn = checkpointer.conn
    _cached_graph = build_research_graph(checkpointer=checkpointer)
    return _cached_graph


async def close_research_graph() -> None:
    """Đóng connection SQLite của graph đã cache (gọi từ lifespan shutdown).

    Không đóng thì Ctrl+C treo ở teardown: interpreter dọn thread pool trong khi
    connection vẫn mở, dễ ăn KeyboardInterrupt lần 2 và traceback xấu.
    """
    global _cached_graph, _cached_conn
    _cached_graph = None
    conn, _cached_conn = _cached_conn, None
    if conn is None:
        return
    try:
        await conn.close()
        logger.info("research_graph_closed")
    except Exception as exc:  # noqa: BLE001 — shutdown không được fail vì lỗi dọn dẹp
        logger.warning(f"research_graph_close_failed: {exc}")