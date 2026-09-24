"""Application-scoped dependencies for the realtime gateway."""

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.services.connection_mgr import ConnectionManager


@lru_cache
def get_connection_manager() -> ConnectionManager:
    """Singleton ConnectionManager dùng để quản lý các kết nối WebSocket và broadcast theo thread_id."""
    return ConnectionManager()


@lru_cache
def get_research_graph() -> Any | None:
    """Khởi tạo và biên dịch StateGraph đồ thị nghiên cứu kèm SQLite Checkpointer.

    Nếu bật cờ USE_MOCK_RESEARCH (phục vụ test hoặc phát triển giao diện khi chưa tích hợp graph),
    hàm sẽ trả về None để stream_research kích hoạt mock stream.
    """
    if settings.use_mock_research:
        return None

    try:
        from app.graph.build import build_research_graph, get_sqlite_checkpointer
    except ImportError as exc:
        raise RuntimeError(
            "The LangGraph research pipeline is unavailable. Install backend "
            "dependencies and provide app.graph.build.build_research_graph."
        ) from exc

    # Dùng factory chung (đã gắn serde allowlist + mkdir + setup).
    checkpointer = get_sqlite_checkpointer(settings.checkpoint_db_path)
    return build_research_graph(checkpointer=checkpointer)