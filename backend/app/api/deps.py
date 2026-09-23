"""Application-scoped dependencies for the realtime gateway."""
from functools import lru_cache
from pathlib import Path
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
        from langgraph.checkpoint.sqlite import SqliteSaver

        from app.graph.build import create_research_graph
    except ImportError as exc:
        raise RuntimeError(
            "The LangGraph research pipeline is unavailable. Install backend "
            "dependencies and provide app.graph.build.create_research_graph."
        ) from exc

    checkpoint_path = Path(settings.checkpoint_db_path)
    if settings.checkpoint_db_path != ":memory:":
        checkpoint_path = checkpoint_path if checkpoint_path.is_absolute() else Path.cwd() / checkpoint_path
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        database = str(checkpoint_path)
    else:
        database = ":memory:"

    checkpointer = SqliteSaver.from_conn_string(database)
    return create_research_graph(checkpointer=checkpointer)
