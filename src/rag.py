"""RAG orchestration: retrieve, prompt, generate, and validate citations.

Flow:
    retrieve top-k chunks
    -> label them [S1], [S2], ... and build a context block
    -> ask the LLM to answer using only that context and cite with [S#]
    -> parse the [S#] markers the model actually produced
    -> map those markers back to TRUSTED retrieved metadata

The LLM is never trusted to supply filenames or URLs. Only [S#] labels that
the model emitted AND that correspond to a real retrieved chunk become sources.
All retrieved chunks remain available separately for debugging.
"""

from __future__ import annotations

import re
from typing import Optional

from openai import OpenAI

from . import config
from .retrieve import retrieve
from .schema import RAGResult, RetrievedChunk, Source

# Marker emitted by the model to signal it cannot answer from the context.
# We translate it into the single canonical refusal message so downstream
# code (and the evaluation harness) can detect refusals deterministically.
_INSUFFICIENT_MARKER = "INSUFFICIENT_CONTEXT"

_SYSTEM_PROMPT = (
    "You are a careful assistant for the AI & ML Club. Answer ONLY using the "
    "provided context passages. Each passage is labeled like [S1], [S2]. "
    "When you use information from a passage, cite it inline with its label, "
    "e.g. [S1]. Do not invent file names, URLs, page numbers, or facts that "
    "are not in the context. If the context does not contain enough "
    "information to answer the question, reply with exactly the token "
    f"{_INSUFFICIENT_MARKER} and nothing else."
)

_LABEL_RE = re.compile(r"\[S(\d+)\]")


def _build_context(chunks: list[RetrievedChunk]) -> str:
    """Build the labeled context block given to the model."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(f"[S{i}]\n{chunk.text}")
    return "\n\n".join(blocks)


def _parse_labels(answer: str, num_chunks: int) -> list[int]:
    """Return the distinct, in-range 1-based indices cited in the answer."""
    seen: list[int] = []
    for match in _LABEL_RE.finditer(answer):
        idx = int(match.group(1))
        if 1 <= idx <= num_chunks and idx not in seen:
            seen.append(idx)
    return seen


def _resolve_sources(
    cited_indices: list[int], chunks: list[RetrievedChunk]
) -> list[Source]:
    """Map validated [S#] indices back to trusted metadata."""
    sources: list[Source] = []
    for idx in cited_indices:
        chunk = chunks[idx - 1]
        sources.append(
            Source(
                label=f"S{idx}",
                document_name=chunk.document_name,
                source=chunk.source,
                page_number=chunk.page_number,
            )
        )
    return sources


def answer_query(
    query: str,
    top_k: Optional[int] = None,
    client: Optional[OpenAI] = None,
) -> RAGResult:
    """Run the full RAG pipeline for a single query."""
    client = client or OpenAI(api_key=config.OPENAI_API_KEY)

    retrieved = retrieve(query, top_k=top_k, client=client)

    # No context at all: deterministic refusal.
    if not retrieved:
        return RAGResult(
            answer=config.INSUFFICIENT_CONTEXT_MESSAGE,
            sources=[],
            retrieved_chunks=[],
            insufficient_context=True,
        )

    context = _build_context(retrieved)
    user_prompt = (
        f"Context passages:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the context above and cite with [S#] labels."
    )

    completion = client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw_answer = (completion.choices[0].message.content or "").strip()

    # Deterministic refusal detection via the sentinel token.
    if _INSUFFICIENT_MARKER in raw_answer:
        return RAGResult(
            answer=config.INSUFFICIENT_CONTEXT_MESSAGE,
            sources=[],
            retrieved_chunks=retrieved,
            insufficient_context=True,
        )

    cited_indices = _parse_labels(raw_answer, len(retrieved))
    sources = _resolve_sources(cited_indices, retrieved)

    return RAGResult(
        answer=raw_answer,
        sources=sources,
        retrieved_chunks=retrieved,
        insufficient_context=False,
    )
