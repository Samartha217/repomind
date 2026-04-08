"""
Hybrid Retriever — combines BM25 keyword search with ChromaDB vector search.

Why hybrid?
- Vector search: finds semantically similar code ("how does authentication work?")
- BM25 search: finds exact keyword matches ("find the load_repo function")
- Together: catches what either alone would miss
"""

from rank_bm25 import BM25Okapi

from config import TOP_K


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on whitespace and common code separators."""
    import re
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


class HybridRetriever:
    def __init__(self, chunks: list[dict]):
        """
        Build BM25 index from a list of chunks.
        chunks: list of dicts with at least {"content", "file_path", "type", "name", ...}
        """
        self.chunks = chunks
        corpus = [_tokenize(c["content"]) for c in chunks]
        self.bm25 = BM25Okapi(corpus)

    def bm25_search(self, query: str, top_k: int = None) -> list[dict]:
        """Return top-k chunks by BM25 keyword score."""
        if top_k is None:
            top_k = TOP_K * 2  # fetch more candidates for reranking

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        # Get indices of top scores
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # only include actual matches
                chunk = dict(self.chunks[idx])
                chunk["bm25_score"] = float(scores[idx])
                results.append(chunk)

        return results


def merge_results(vector_chunks: list[dict], bm25_chunks: list[dict], top_k: int = None) -> list[dict]:
    """
    Merge vector and BM25 results using Reciprocal Rank Fusion (RRF).
    RRF gives each chunk a score based on its rank in each list, then combines them.
    This is better than just concatenating because it handles different score scales.
    """
    if top_k is None:
        top_k = TOP_K * 2

    RRF_K = 60  # standard constant for RRF

    scores = {}  # chunk key -> rrf score
    chunks_by_key = {}

    # Score vector results
    for rank, chunk in enumerate(vector_chunks):
        key = f"{chunk['file_path']}:{chunk['start_line']}"
        scores[key] = scores.get(key, 0) + 1 / (RRF_K + rank + 1)
        chunks_by_key[key] = chunk

    # Score BM25 results
    for rank, chunk in enumerate(bm25_chunks):
        key = f"{chunk['file_path']}:{chunk['start_line']}"
        scores[key] = scores.get(key, 0) + 1 / (RRF_K + rank + 1)
        chunks_by_key[key] = chunk

    # Sort by combined score, return top_k
    sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
    return [chunks_by_key[k] for k in sorted_keys[:top_k]]
