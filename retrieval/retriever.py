from config import TOP_K
from ingestion.embedder import load_vector_store


class Retriever:
    def __init__(self, collection_name: str):
        self.vector_store = load_vector_store(collection_name)
        self.collection_name = collection_name

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Search for relevant code chunks."""

        if not query or not query.strip():
            return []

        try:
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
        except Exception as e:
            raise RuntimeError(
                f"Search failed for '{self.collection_name}': {e}. "
                "The index may be corrupted — try re-indexing the repository."
            ) from e

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

    def search_with_filter(self, query: str, file_type: str = None, top_k: int = TOP_K) -> list[dict]:
        """Search with optional file type filter."""

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
