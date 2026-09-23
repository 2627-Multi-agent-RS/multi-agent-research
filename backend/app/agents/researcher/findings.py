"""Findings heuristic spec-compatible: 1 doc -> 1 finding."""

from typing import Any, Dict, List

EVIDENCE_CHARS = 500


def build_heuristic_findings(search_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    1 doc -> 1 finding {
        claim, 
        evidence, 
        source_url, 
        source_title
    }.
    """
    findings = []
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
            {
                "claim": claim,
                "evidence": content[:EVIDENCE_CHARS],
                "source_url": url,
                "source_title": title or url,
                "published_at": doc.get("published_at"),
            }
        )
    return findings


def merge_findings(
    existing: List[Dict[str, Any]], new: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    seen = {(f.get("claim"), f.get("source_url")) for f in existing if isinstance(f, dict)}
    merged = list(existing)
    for f in new:
        if (f.get("claim"), f.get("source_url")) not in seen:
            seen.add((f.get("claim"), f.get("source_url")))
            merged.append(f)
    return merged
