"""Findings heuristic: 1 search doc -> 1 Finding (Pydantic, khớp AgentState)."""

from typing import Any

from app.schemas.research import Finding

EVIDENCE_CHARS = 500


def coerce_finding(f: Finding | dict[str, Any]) -> Finding:
    """Ép finding từ state về Pydantic Finding (state merge dùng object, test dùng dict)."""
    if isinstance(f, Finding):
        return f
    return Finding(**f)


def build_heuristic_findings(search_docs: list[dict[str, Any]]) -> list[Finding]:
    """Mỗi doc search thành 1 Finding {claim, evidence, source_url, source_title, published_at}."""
    findings: list[Finding] = []
    for doc in search_docs:
        title = (doc.get("title") or "").strip()
        content = (doc.get("content") or "").strip()
        url = (doc.get("url") or "").strip()
        if not url:
            continue
        claim = title or content[:120]
        if not claim:
            continue
        findings.append(
            Finding(
                claim=claim,
                evidence=content[:EVIDENCE_CHARS],
                source_url=url,
                source_title=title or url,
                published_at=doc.get("published_at"),
            )
        )
    return findings


def merge_findings(
    existing: list[Finding | dict[str, Any]],
    new: list[Finding | dict[str, Any]],
) -> list[Finding]:
    """Gộp findings vòng trước + vòng mới, dedup theo (claim, source_url), giữ thứ tự."""
    merged: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for f in list(existing or []) + list(new or []):
        finding = coerce_finding(f)
        key = (finding.claim, finding.source_url)
        if key not in seen:
            seen.add(key)
            merged.append(finding)
    return merged
