"""Trích queries cần search từ state: follow-up của Analyst được ưu tiên,
ngược lại dùng plan.sub_queries của Orchestrator, fallback về topic gốc."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.graph.state import AgentState

MAX_QUERIES = 5


def _val(obj: Any, key: str, default: Any = None) -> Any:
    """Đọc key từ dict lẫn Pydantic model (state merge dùng object, test dùng dict)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_follow_up_questions(state: "AgentState") -> list[str]:
    """Câu hỏi tra cứu bổ sung của Analyst (rỗng nếu không có)."""
    questions = _val(_val(_val(state, "analysis"), "follow_up_request"), "questions")
    return [q.strip() for q in (questions or []) if q and str(q).strip()]


def resolve_queries(state: "AgentState") -> list[str]:
    """Trả về tối đa MAX_QUERIES query đã dedup, giữ thứ tự.

    Follow-up được dùng ngay khi tồn tại (vòng loop-back retry_count vẫn là 0,
    vì researcher mới là node tăng retry — theo routing MAX_RESEARCH_RETRIES).
    """
    queries = get_follow_up_questions(state)
    if not queries:
        sub = _val(_val(state, "plan"), "sub_queries") or []
        queries = [q for q in (str(q).strip() for q in sub) if q]
        if not queries:
            topic = _val(state, "topic") or ""
            topic = topic.strip() if isinstance(topic, str) else ""
            queries = [topic] if topic else []

    seen, out = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:MAX_QUERIES]
