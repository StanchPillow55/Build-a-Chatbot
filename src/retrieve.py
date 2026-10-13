"""Retrieval: embed a query and return the top-k chunks from Chroma.

Returns the chunk text, trusted metadata, and the actual retrieval metric the
installed Chroma API exposes (a vector *distance*, where smaller is closer).
The metric is labeled accurately as a distance, never as "confidence".
"""

from __future__ import annotations

from typing import Optional

import chromadb
from openai import OpenAI

from . import config
from .schema import RetrievedChunk


def _embed_query(client: OpenAI, query: str) -> list[float]:
    resp = client.embeddings.create(
        model=config.OPENAI_EMBEDDING_MODEL, input=[query]
    )
    return resp.data[0].embedding


def get_collection():
    """Open the persistent collection. Raises if the index is missing."""
    if not config.INDEX_DIR.exists():
        raise RuntimeError(
            f"No index found at {config.INDEX_DIR}. Run `python -m src.ingest` first."
        )
    chroma = chromadb.PersistentClient(path=str(config.INDEX_DIR))
    try:
        return chroma.get_collection(config.COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            f"Collection '{config.COLLECTION_NAME}' not found in {config.INDEX_DIR}. "
            "Run `python -m src.ingest` to build it."
        ) from exc


def retrieve(
    query: str,
    top_k: Optional[int] = None,
    client: Optional[OpenAI] = None,
) -> list[RetrievedChunk]:
    """Return the top-k retrieved chunks for a query.

    top_k defaults to config.TOP_K. The returned distance is Chroma's raw
    metric (smaller == more similar).
    """
    k = top_k if top_k is not None else config.TOP_K
    client = client or OpenAI(api_key=config.OPENAI_API_KEY)

    collection = get_collection()
    query_embedding = _embed_query(client, query)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns a list-per-query; we issued a single query.
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    retrieved: list[RetrievedChunk] = []
    for text, meta, distance in zip(documents, metadatas, distances):
        retrieved.append(
            RetrievedChunk(
                text=text,
                metadata=dict(meta or {}),
                distance=distance,
            )
        )
    return retrieved
