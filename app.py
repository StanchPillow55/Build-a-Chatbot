"""Streamlit chat UI for the AI & ML Club RAG MVP.

Shows the generated answer, a sources section derived from validated [S#]
citations (document name + page number where available), and a collapsible
debug panel. The debug panel exists to localize failures:
    parsing failure -> no/garbled retrieved text
    chunking failure -> oddly shaped chunks
    retrieval failure -> wrong or empty chunks for an answerable question
    generation failure -> good context but bad/empty answer

Local execution is the target. Do not assume Streamlit Community Cloud works
with the private, gitignored corpus.
"""

from __future__ import annotations

import time

import streamlit as st

from src import config
from src.rag import answer_query

st.set_page_config(page_title="AI & ML Club — RAG MVP", page_icon="🤖")

st.title("AI & ML Club — RAG MVP")
st.caption(
    f"Chat model: `{config.OPENAI_CHAT_MODEL}`  •  "
    f"Embeddings: `{config.OPENAI_EMBEDDING_MODEL}`  •  "
    f"top_k: {config.TOP_K}"
)

if not config.OPENAI_API_KEY:
    st.error(
        "OPENAI_API_KEY is not set. Copy `.env.example` to `.env`, add your key, "
        "and restart the app."
    )

query = st.chat_input("Ask a question about the club documents...")

if query:
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        start = time.perf_counter()
        try:
            result = answer_query(query)
            latency = time.perf_counter() - start
            error: str | None = None
        except Exception as exc:  # surface failures instead of crashing silently
            latency = time.perf_counter() - start
            result = None
            error = f"{type(exc).__name__}: {exc}"

        if error:
            st.error(f"Request failed: {error}")
            st.info(
                "Common causes: missing index (run `python -m src.ingest`), "
                "missing/invalid API key, or network issues."
            )
        else:
            # Answer
            st.write(result.answer)

            # Sources (validated [S#] -> trusted metadata)
            st.subheader("Sources")
            if result.insufficient_context:
                st.write("_No sources: the model declined for insufficient context._")
            elif result.sources:
                for src in result.sources:
                    page = (
                        f", page {src.page_number}"
                        if src.page_number is not None
                        else ""
                    )
                    st.markdown(f"- **[{src.label}]** {src.document_name}{page}")
            else:
                st.write("_The answer cited no sources._")

            # Debug panel
            with st.expander("Debug panel", expanded=False):
                st.markdown(f"**Approximate latency:** {latency:.2f}s")
                st.markdown(
                    f"**insufficient_context:** `{result.insufficient_context}`"
                )
                st.markdown(f"**Retrieved chunks:** {len(result.retrieved_chunks)}")

                for i, chunk in enumerate(result.retrieved_chunks, start=1):
                    dist = (
                        f"{chunk.distance:.4f}"
                        if chunk.distance is not None
                        else "n/a"
                    )
                    st.markdown(
                        f"---\n**[S{i}]** `{chunk.document_name}` "
                        f"(distance: {dist})"
                    )
                    st.json(chunk.metadata)
                    st.text(
                        chunk.text[:1000]
                        + ("…" if len(chunk.text) > 1000 else "")
                    )
