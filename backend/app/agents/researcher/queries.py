"""Extract search queries from state: Analyst follow-up takes priority,
falling back to Orchestrator plan.sub_queries, then the raw topic."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.graph.state import AgentState

MAX_QUERIES = 5


def _val(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from either a dict or a Pydantic model (merged state uses objects, tests use dicts)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_follow_up_questions(state: "AgentState") -> list[str]:
    """Analyst follow-up questions (empty when absent)."""
    questions = _val(_val(_val(state, "analysis"), "follow_up_request"), "questions")
    return [q.strip() for q in (questions or []) if q and str(q).strip()]


def resolve_queries(state: "AgentState") -> list[str]:
    """Return at most MAX_QUERIES deduped queries, preserving order.

    Follow-up is honored as soon as it exists (the loop-back pass still has
    retry_count == 0, since researcher is the node that increments retry —
    see routing MAX_RESEARCH_RETRIES).
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
