from config import TOP_K
from ingestion.embedder import load_vector_store
from retrieval.hybrid_retriever import HybridRetriever, merge_results
from retrieval.reranker import rerank

# Fetch more candidates than we need — reranker will cut them down to TOP_K
CANDIDATE_MULTIPLIER = 3


class Retriever:
    def __init__(self, collection_name: str):
        self.vector_store = load_vector_store(collection_name)
        self.collection_name = collection_name
        self._hybrid = None  # built lazily on first search

    def _get_all_chunks(self) -> list[dict]:
        """Fetch all chunks from ChromaDB to build the BM25 index."""
        try:
            collection = self.vector_store._collection
            result = collection.get(include=["documents", "metadatas"])
            chunks = []
            for doc, meta in zip(result["documents"], result["metadatas"]):
                chunks.append({
                    "content": doc,
                    "file_path": meta.get("file_path", ""),
                    "type": meta.get("type", ""),
                    "name": meta.get("name", ""),
                    "start_line": meta.get("start_line", 0),
                    "end_line": meta.get("end_line", 0),
                    "score": 0.0,
                })
            return chunks
        except Exception:
            return []

    def _get_hybrid(self) -> HybridRetriever:
        """Build BM25 index lazily — only on first search."""
        if self._hybrid is None:
            all_chunks = self._get_all_chunks()
            self._hybrid = HybridRetriever(all_chunks) if all_chunks else None
        return self._hybrid

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """
        Full hybrid search pipeline:
        1. Vector search (semantic similarity)
        2. BM25 search (keyword matching)
        3. Merge via Reciprocal Rank Fusion
        4. Rerank with cross-encoder
        5. Return top_k
        """
        if not query or not query.strip():
            return []

        candidates = top_k * CANDIDATE_MULTIPLIER  # fetch more, rerank down

        # Step 1: Vector search
        try:
            vector_results = self.vector_store.similarity_search_with_score(query, k=candidates)
            vector_chunks = []
            for doc, score in vector_results:
                vector_chunks.append({
                    "content": doc.page_content,
                    "file_path": doc.metadata["file_path"],
                    "type": doc.metadata["type"],
                    "name": doc.metadata["name"],
                    "start_line": doc.metadata["start_line"],
                    "end_line": doc.metadata["end_line"],
                    "score": score,
                })
        except Exception as e:
            raise RuntimeError(
                f"Search failed for '{self.collection_name}': {e}. "
                "The index may be corrupted — try re-indexing the repository."
            ) from e

        # Step 2: BM25 search
        hybrid = self._get_hybrid()
        if hybrid:
            bm25_chunks = hybrid.bm25_search(query, top_k=candidates)
        else:
            bm25_chunks = []

        # Step 3: Merge via RRF
        merged = merge_results(vector_chunks, bm25_chunks, top_k=candidates)

        # Step 4: Rerank — cross-encoder scores (query, chunk) pairs precisely
        reranked = rerank(query, merged, top_n=top_k)

        return reranked

    def search_with_filter(self, query: str, file_type: str = None, top_k: int = TOP_K) -> list[dict]:
        """Search with optional file type filter (vector only — BM25 doesn't support filters)."""

        filter_dict = None
        if file_type:
            filter_dict = {"type": file_type}

        results = self.vector_store.similarity_search_with_score(
            query,
            k=top_k,
            filter=filter_dict
        )

        chunks = []
        for doc, score in results:
            chunks.append({
                "content": doc.page_content,
                "file_path": doc.metadata["file_path"],
                "type": doc.metadata["type"],
                "name": doc.metadata["name"],
                "start_line": doc.metadata["start_line"],
                "end_line": doc.metadata["end_line"],
                "score": score
            })

        return chunks
