from typing import Any, Dict, List

MAX_SNIPPET_CHARS = 800
MAX_CONTEXT_CHARS = 22000 


def build_context(
    search_docs: List[Dict[str, Any]],
    scraped: Dict[str, str],
) -> str:
    chunks: List[str] = []
    for doc in search_docs:
        snippet = (doc.get("content") or "")[:MAX_SNIPPET_CHARS]
        chunks.append(f"Title: {doc.get('title', '')}\nURL: {doc.get('url', '')}\nSummary: {snippet}")
    for url, text in scraped.items():
        if text:
            chunks.append(f"Full Text URL ({url}):\n{text}")
    return ("\n\n---\n\n".join(chunks))[:MAX_CONTEXT_CHARS]
