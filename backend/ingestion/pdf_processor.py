"""
PDF ingestion pipeline: parse → chunk → embed → store in ChromaDB.

Chunking strategy:
  1. Attempt to split pages on EASA-style question boundaries (numbered items).
  2. Fall back to fixed-size overlapping chunks for dense paragraph text.

Embeddings use Google gemini-embedding-001 with task_type=RETRIEVAL_DOCUMENT
via the google-genai (v1beta) SDK, which is the package bundled with ADK.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.errors import NotFoundError
from google import genai as google_genai
from google.genai import types as genai_types
from pypdf import PdfReader

from backend.config import (
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    GOOGLE_API_KEY,
)

# ── Embedding function ─────────────────────────────────────────────────────

class _DocumentEmbeddingFn(EmbeddingFunction[Documents]):
    """Wraps Google gemini-embedding-001 for ChromaDB ingestion (batch-aware)."""

    # Gemini embedding batch endpoint accepts up to 100 documents per call
    _BATCH_SIZE = 100

    def __init__(self) -> None:
        self._client = google_genai.Client(api_key=GOOGLE_API_KEY)

    def __call__(self, documents: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for i in range(0, len(documents), self._BATCH_SIZE):
            batch = list(documents[i : i + self._BATCH_SIZE])
            result = self._client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
                config=genai_types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT"
                ),
            )
            embeddings.extend([e.values for e in result.embeddings])
        return embeddings


# ── PDF extraction ─────────────────────────────────────────────────────────

def _extract_pages(pdf_path: Path) -> list[dict]:
    """Return a list of {page_number, text} dicts from a PDF."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append({"page_number": i, "text": text})
    return pages


# ── Chunking ───────────────────────────────────────────────────────────────

_QUESTION_BOUNDARY = re.compile(
    r"(?=(?:^|\n)\s*\d{1,3}[\.\)]\s+[A-Z])", re.MULTILINE
)


def _chunk_page(page_text: str, page_num: int, chunk_size: int, overlap: int) -> Iterator[dict]:
    """Yield chunks from a single page."""
    # Attempt question-boundary split first
    splits = [s.strip() for s in _QUESTION_BOUNDARY.split(page_text) if s.strip()]

    if len(splits) > 1:
        for split in splits:
            yield {"text": split, "page": page_num, "type": "question_block"}
        return

    # Fixed-size overlapping fallback
    start = 0
    while start < len(page_text):
        end = min(start + chunk_size, len(page_text))

        # Snap to last sentence boundary within the window
        if end < len(page_text):
            boundary = page_text.rfind(".", start, end)
            if boundary > start + chunk_size // 2:
                end = boundary + 1

        chunk = page_text[start:end].strip()
        if chunk:
            yield {"text": chunk, "page": page_num, "type": "text_block"}

        next_start = end - overlap
        if next_start <= start:  # guard against infinite loop on tiny pages
            break
        start = next_start


def _build_chunks(
    pages: list[dict],
    chunk_size: int = 1_000,
    overlap: int = 200,
) -> list[dict]:
    """Flatten all page chunks into a single list with stable IDs."""
    chunks: list[dict] = []
    for page_data in pages:
        for chunk in _chunk_page(page_data["text"], page_data["page_number"], chunk_size, overlap):
            chunk["id"] = f"chunk_{len(chunks):05d}"
            chunks.append(chunk)
    return chunks


# ── ChromaDB persistence ───────────────────────────────────────────────────

def _persist_to_chroma(chunks: list[dict]) -> int:
    """Store chunks in ChromaDB and return the number of stored documents."""
    embedding_fn = _DocumentEmbeddingFn()

    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

    # Drop existing collection so we can re-index cleanly
    try:
        client.delete_collection(COLLECTION_NAME)
    except NotFoundError:
        pass  # Collection does not exist yet — nothing to delete

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 50  # Keep batches small to stay within embedding API limits
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{"page": c["page"], "type": c["type"]} for c in batch],
        )
        stored = min(i + batch_size, len(chunks))
        print(f"  [{stored}/{len(chunks)}] chunks indexed…")

    return collection.count()


# ── Public entry point ─────────────────────────────────────────────────────

def run_ingestion_pipeline(pdf_path: Path | None = None) -> None:
    """
    Full ingestion pipeline:
      PDF → pages → chunks → Google embeddings → ChromaDB.

    Args:
        pdf_path: Override default DATA_SOURCE_PATH for testing.
    """
    from backend.config import DATA_SOURCE_PATH  # avoid circular at module level

    target = pdf_path or DATA_SOURCE_PATH
    if not target.exists():
        raise FileNotFoundError(f"PDF not found: {target}")

    print("\n=== Ingestion pipeline started ===")
    print(f"Source: {target}")

    print("\n[1/3] Extracting text from PDF…")
    pages = _extract_pages(target)
    print(f"      {len(pages)} pages extracted")

    print("\n[2/3] Chunking text…")
    chunks = _build_chunks(pages)
    print(f"      {len(chunks)} chunks created")

    print("\n[3/3] Embedding & storing in ChromaDB…")
    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    count = _persist_to_chroma(chunks)
    print(f"\n=== Ingestion complete: {count} documents stored ===\n")
