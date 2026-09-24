"""Heuristic findings: 1 search doc -> 1 Finding (Pydantic, matches AgentState)."""

from typing import Any

from app.schemas.research import Finding

EVIDENCE_CHARS = 500


def coerce_finding(f: Finding | dict[str, Any]) -> Finding:
    """Coerce a state finding into a Pydantic Finding (merged state uses objects, tests use dicts)."""
    if isinstance(f, Finding):
        return f
    return Finding(**f)


def build_heuristic_findings(search_docs: list[dict[str, Any]]) -> list[Finding]:
    """Turn each search doc into 1 Finding {claim, evidence, source_url, source_title, published_at}."""
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
    """Merge previous-round + new findings, dedup on (claim, source_url), preserve order."""
    merged: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for f in list(existing or []) + list(new or []):
        finding = coerce_finding(f)
        key = (finding.claim, finding.source_url)
        if key not in seen:
            seen.add(key)
            merged.append(finding)
    return merged
