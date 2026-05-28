"""Centralised configuration loaded from environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = _PROJECT_ROOT
CHROMA_DB_PATH = PROJECT_ROOT / "chroma_db"
DATA_SOURCE_PATH = PROJECT_ROOT / "data_source" / "easa_propulsao.pdf"

# ── Google / Gemini ────────────────────────────────────────────────────────
GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL: str = "models/gemini-embedding-001"

# ── ChromaDB ───────────────────────────────────────────────────────────────
COLLECTION_NAME: str = "easa_propulsao"

# ── Quiz ───────────────────────────────────────────────────────────────────
QUESTIONS_PER_QUIZ: int = 5
CHUNKS_PER_RETRIEVAL: int = 3
