import os

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from config import EMBEDDING_MODEL, OPENAI_API_KEY, STORAGE_DIR


def get_embeddings():
    """Get embedding model instance."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set. "
            "Copy .env.example to .env and add your OpenAI API key."
        )

    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=OPENAI_API_KEY
    )


def create_vector_store(chunks: list[dict], collection_name: str) -> Chroma:
    """Embed chunks and store in ChromaDB."""

    if not chunks:
        raise ValueError("No code chunks to embed. The repository might be empty or contain no supported files.")

    embeddings = get_embeddings()

    # Prepare documents and metadata
    texts = []
    metadatas = []

    for chunk in chunks:
        # Create rich text for embedding
        text = f"File: {chunk['file_path']}\n"
        text += f"Type: {chunk['type']} | Name: {chunk['name']}\n"
        if chunk['docstring']:
            text += f"Docstring: {chunk['docstring']}\n"
        text += f"\n{chunk['content']}"

        texts.append(text)
        metadatas.append({
            "file_path": chunk["file_path"],
            "type": chunk["type"],
            "name": chunk["name"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"]
        })

    # Create persist directory
    persist_dir = os.path.join(STORAGE_DIR, collection_name)

    print(f"Embedding {len(texts)} chunks...")

    try:
        vector_store = Chroma.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas,
            persist_directory=persist_dir,
            collection_name=collection_name
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to create embeddings: {e}. "
            "Check your OpenAI API key and internet connection."
        ) from e

    print(f"Stored in {persist_dir}")
    return vector_store


def load_vector_store(collection_name: str) -> Chroma:
    """Load existing vector store."""

    persist_dir = os.path.join(STORAGE_DIR, collection_name)

    if not os.path.exists(persist_dir):
        raise FileNotFoundError(
            f"No index found for '{collection_name}'. "
            "Please load and index the repository first."
        )

    embeddings = get_embeddings()

    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name=collection_name
    )
