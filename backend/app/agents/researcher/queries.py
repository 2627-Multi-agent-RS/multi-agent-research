from typing import Any, Dict, List

MAX_QUERIES = 5

def resolve_queries(state: Dict[str, Any]) -> List[str]:
    analysis = state.get("analysis") or {}
    follow_up = analysis.get("follow_up_request") or {}
    retry_count = state.get("retry_count", 0) or 0

    if follow_up.get("questions") and retry_count > 0:
        queries: List[str] = follow_up.get("questions", [])
    else:
        plan = state.get("plan") or {}
        queries = plan.get("sub_queries") or []
        if not queries:
            topic = (state.get("topic") or "").strip()
            queries = [topic] if topic else []

    seen, out = set(), []
    for q in queries:
        q = (q or "").strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out[:MAX_QUERIES]
