"""
ChromaDB retriever for the EASA propulsion knowledge base.

Query embeddings use task_type=RETRIEVAL_QUERY (distinct from the
RETRIEVAL_DOCUMENT task used at ingestion time) as recommended by
Google for asymmetric semantic retrieval.
"""
from __future__ import annotations

import chromadb
from google import genai as google_genai
from google.genai import types as genai_types

from backend.config import (
    CHROMA_DB_PATH,
    CHUNKS_PER_RETRIEVAL,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    GOOGLE_API_KEY,
)

_genai_client = google_genai.Client(api_key=GOOGLE_API_KEY)

# Lazy-initialised ChromaDB client and collection
_chroma_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        _collection = _chroma_client.get_collection(name=COLLECTION_NAME)
    return _collection


def _embed_query(text: str) -> list[float]:
    result = _genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return list(result.embeddings[0].values)


def is_knowledge_base_ready() -> bool:
    """Return True if ChromaDB collection exists and contains documents."""
    try:
        col = _get_collection()
        return col.count() > 0
    except Exception:
        return False


def search_knowledge_base(
    query: str, n_results: int = CHUNKS_PER_RETRIEVAL
) -> str:
    """
    Retrieve the most semantically relevant passages for *query*.

    Args:
        query: Natural-language search query.
        n_results: Number of chunks to return (default CHUNKS_PER_RETRIEVAL).

    Returns:
        Formatted string with page references and passage text, ready for
        injection into an LLM prompt.

    Raises:
        RuntimeError: If the collection does not exist (ingestion not run yet).
    """
    try:
        collection = _get_collection()
    except Exception as exc:
        raise RuntimeError(
            "ChromaDB collection not found. "
            "Run `python scripts/ingest.py` first."
        ) from exc

    query_embedding = _embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents: list[str] = results["documents"][0]
    metadatas: list[dict] = results["metadatas"][0]

    if not documents:
        return "No relevant content found for this query."

    sections: list[str] = []
    for doc, meta in zip(documents, metadatas):
        sections.append(f"[Página {meta.get('page', '?')}]\n{doc}")

    return "\n\n---\n\n".join(sections)
