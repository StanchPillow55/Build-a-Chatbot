"""Centralized configuration for the RAG MVP.

All model literals and tunable constants live here so that changing a model
or a retrieval parameter requires zero changes to application code. The rest
of the codebase imports from this module; it never hard-codes model names.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repository root (one level above src/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# OpenAI configuration
# ---------------------------------------------------------------------------

# Secret. Loaded from .env; never committed. May be empty for ingest/eval
# code paths that only need to validate structure, but is required to make
# live API calls.
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Generation model. Default is gpt-6-luna (current cheap/fast OpenAI model).
# Set OPENAI_CHAT_MODEL=gpt-4o-mini in .env as a fallback if account/model
# availability differs. Changing the model is an env change, not a code change.
OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-6-luna")

# Embedding model. Small and inexpensive; adequate for a one-semester corpus.
OPENAI_EMBEDDING_MODEL: str = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
)

# ---------------------------------------------------------------------------
# Vector store (Chroma)
# ---------------------------------------------------------------------------

# Local persistent Chroma directory. This is DERIVED data: deleting it is safe,
# and `python -m src.ingest` regenerates it from the authoritative corpus.
INDEX_DIR: Path = PROJECT_ROOT / "index"

# Single MVP collection name.
COLLECTION_NAME: str = "aiml_club_mvp"

# ---------------------------------------------------------------------------
# Corpus locations
# ---------------------------------------------------------------------------

# Default input directory for ingestion (the real, gitignored corpus).
DEFAULT_INPUT_DIR: Path = PROJECT_ROOT / "data" / "raw"

# Committed smoke-test corpus for `--input-dir data/sample`.
SAMPLE_INPUT_DIR: Path = PROJECT_ROOT / "data" / "sample"

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 150

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

# Number of chunks to retrieve per query. Tunable here only.
TOP_K: int = 4

# ---------------------------------------------------------------------------
# RAG behavior
# ---------------------------------------------------------------------------

# One consistent, human-readable refusal message. When the model cannot answer
# from the supplied context it must return exactly this string, which lets the
# evaluation harness detect refusals deterministically instead of parsing prose.
INSUFFICIENT_CONTEXT_MESSAGE: str = (
    "I don't have enough information in the provided club documents to answer "
    "that question."
)
