"""Shared data structures and provenance helpers.

The *system* owns provenance metadata, not the LLM. These dataclasses and
helpers define the trusted metadata attached to every chunk and the structured
RAG result consumed by the UI and the evaluation harness.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def document_id_from_path(root: Path, path: Path) -> str:
    """Deterministic document id derived from the relative source path.

    Using the relative path (not an absolute path or a random uuid) means the
    same document always produces the same id across machines and rebuilds.
    """
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


def chunk_id_from(document_id: str, page_number: Optional[int], ordinal: int) -> str:
    """Deterministic chunk id derived from document id, page, and ordinal."""
    page_part = "na" if page_number is None else str(page_number)
    return f"{document_id}:p{page_part}:c{ordinal:04d}"


@dataclass
class Chunk:
    """A single indexed chunk and its trusted metadata.

    page_number is Optional: it is populated for paginated sources (PDFs) and
    left as None for whole-document sources (txt/md/docx). When writing to
    Chroma we omit the key entirely if it is None, because some Chroma versions
    reject null metadata values.
    """

    text: str
    document_id: str
    document_name: str
    source: str
    chunk_id: str
    page_number: Optional[int] = None

    def metadata(self) -> dict:
        """Trusted metadata dict for storage/retrieval.

        Omits page_number when it is None rather than storing a null, so this
        works regardless of whether the installed Chroma supports null values.
        """
        meta = {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "source": self.source,
            "chunk_id": self.chunk_id,
        }
        if self.page_number is not None:
            meta["page_number"] = self.page_number
        return meta


@dataclass
class RetrievedChunk:
    """A chunk returned from retrieval, with its raw retrieval metric.

    `distance` is the actual metric exposed by the installed Chroma API
    (a vector distance, where smaller means more similar). It is deliberately
    NOT called "confidence": it is a distance, not a probability.
    """

    text: str
    metadata: dict
    distance: Optional[float]

    @property
    def document_name(self) -> str:
        return self.metadata.get("document_name", "unknown")

    @property
    def source(self) -> str:
        return self.metadata.get("source", "unknown")

    @property
    def page_number(self) -> Optional[int]:
        return self.metadata.get("page_number")


@dataclass
class Source:
    """A validated citation that maps an [S#] label to trusted metadata."""

    label: str  # e.g. "S1"
    document_name: str
    source: str
    page_number: Optional[int] = None


@dataclass
class RAGResult:
    """Structured result of a RAG query.

    - answer: the generated answer (or the refusal message).
    - sources: validated citations, derived from [S#] markers the model
      actually produced AND mapped back to trusted retrieved metadata.
    - retrieved_chunks: every retrieved chunk, kept separately for debugging.
    - insufficient_context: True when the model refused for lack of context,
      set deterministically so evaluation never has to infer it from prose.
    """

    answer: str
    sources: list = field(default_factory=list)
    retrieved_chunks: list = field(default_factory=list)
    insufficient_context: bool = False
