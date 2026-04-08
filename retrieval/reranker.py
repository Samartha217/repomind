"""
Reranker — takes merged candidates from hybrid search and scores them precisely.

Why rerank?
- Vector + BM25 retrieves ~20 candidates quickly but imprecisely
- A cross-encoder reads (query, chunk) together and gives a precise relevance score
- We keep only the top 5 after reranking — much better signal/noise ratio

Uses FlashRank: runs on CPU, ~4MB model, no PyTorch/GPU needed.
"""

from flashrank import Ranker, RerankRequest

# Load once at module level — avoids reloading the model on every query
# ms-marco-MiniLM-L-6-v2: 6 layers, ~40% faster than L-12, negligible accuracy loss
# Best choice for real-time chat with small reranking sets (≤30 chunks)
_ranker = None


def _get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-6-v2", cache_dir="/tmp/flashrank_cache")
    return _ranker


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Rerank chunks by relevance to the query. Returns top_n most relevant chunks.

    Args:
        query: the user's question
        chunks: merged candidates from hybrid search (typically 15-20)
        top_n: how many to keep after reranking

    Returns:
        list of chunks sorted by reranker score, capped at top_n
    """
    if not chunks:
        return []

    if len(chunks) <= top_n:
        return chunks

    ranker = _get_ranker()

    # FlashRank expects: [{"id": ..., "text": ..., "meta": ...}]
    passages = []
    for i, chunk in enumerate(chunks):
        # Build a rich text representation for reranking
        text = f"File: {chunk['file_path']}\nType: {chunk['type']} | Name: {chunk['name']}\n\n{chunk['content']}"
        passages.append({"id": i, "text": text[:2000], "meta": chunk})

    request = RerankRequest(query=query, passages=passages)

    try:
        results = ranker.rerank(request)
        # results are sorted by score descending
        reranked = [r["meta"] for r in results[:top_n]]
        return reranked
    except Exception:
        # If reranker fails for any reason, return top_n from original order
        return chunks[:top_n]
