# AI & ML Club @ SJSU — Standalone RAG MVP

A small, standalone Retrieval-Augmented-Generation (RAG) chatbot over a static
set of AI & ML Club documents. This is a one-week, hackathon-style learning and
consulting prototype — **not** the production club platform — and it is meant to
be replaced later. It optimizes for simplicity, demonstrability, debuggability,
and regenerable artifacts.

> **This repository is Proposal A: a standalone consulting MVP.** The future
> integrated club system (Proposal B) will be designed only after we have access
> to the real website repository, its technology stack, its deployment
> environment, and stakeholder requirements. Nothing here claims that this
> Python / Chroma / Streamlit implementation must be reused in Proposal B. The
> genuinely reusable outputs are the **provenance conventions**, the
> **evaluation questions**, **corpus knowledge**, **retrieval experiments**,
> **failure cases**, **prompting lessons**, and **stakeholder feedback**.

---

## Problem

Club officers and members have institutional knowledge scattered across PDFs,
Word docs, and notes (meeting logistics, membership, officer handoffs, events).
We want to ask natural-language questions and get answers that are **grounded in
those documents** and **cite their source**, instead of hoping someone remembers
where a fact lives. The MVP must also **refuse** when the documents don't
contain the answer, rather than making something up.

## Architecture

```
                PROPOSAL A

        Static club documents
                 │
                 ▼
        Python ingestion
      pypdf / python-docx
                 │
                 ▼
       Normalize + provenance
                 │
                 ▼
RecursiveCharacterTextSplitter
                 │
                 ▼
 text-embedding-3-small
                 │
                 ▼
       Local Chroma index
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    Retriever       Debug/evaluation
        │
        ▼
   gpt-6-luna
        │
        ▼
 Grounded answer + [S#]
        │
        ▼
Trusted metadata resolves
citations to actual sources
        │
        ▼
       Streamlit
```

The data flow in code:

```
query
  → OpenAI embedding          (src/retrieve.py)
  → Chroma query (top-k)      (src/retrieve.py)
  → build [S1], [S2], ... context   (src/rag.py)
  → OpenAI generation call    (src/rag.py)
  → parse [S#] citations      (src/rag.py)
  → resolve against trusted metadata   (src/rag.py)
```

Module map:

| File              | Responsibility                                                      |
|-------------------|---------------------------------------------------------------------|
| `src/config.py`   | **All** model literals and tunables (nothing hard-coded elsewhere)  |
| `src/schema.py`   | Provenance helpers + `Chunk`, `RetrievedChunk`, `Source`, `RAGResult` |
| `src/ingest.py`   | Full index rebuild: parse → normalize → chunk → embed → populate    |
| `src/retrieve.py` | Embed a query, return top-k chunks + raw Chroma distance            |
| `src/rag.py`      | Retrieve, prompt, generate, validate `[S#]` citations               |
| `app.py`          | Streamlit chat UI with sources + debug panel                        |
| `eval/`           | YAML question set + custom evaluation harness                       |

## Data

```
data/
  sample/        committed smoke-test corpus (tiny, non-sensitive)
    sample.txt
  raw/           real club documents (gitignored, never committed)
    .gitignore   (ignores everything but itself)
index/           generated Chroma DB (gitignored, regenerable)
```

- **Authoritative:** `data/raw/`. The real documents live here and are never
  committed. The folder survives a fresh clone (its `.gitignore` is tracked),
  but its contents are ignored.
- **Derived:** `index/`. Generated from the corpus. **Deleting `index/` is
  always safe**; `python -m src.ingest` rebuilds it from scratch.
- **Committed smoke test:** `data/sample/sample.txt` lets a fresh clone run the
  whole pipeline with no private data.

Supported file types: `.pdf` (page-by-page via pypdf), `.docx` (python-docx),
`.txt` / `.md` (stdlib). Unsupported files are **reported and skipped**, never
silently dropped.

## Setup

Requires Python 3.11+ (initialized and verified on Python 3.12).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and add your `OPENAI_API_KEY`. The other two values are
pre-filled:

```
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-6-luna
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Running

```bash
# 1. Build the index (smoke-test corpus)
python -m src.ingest --input-dir data/sample

#    …or the real corpus (default is data/raw)
python -m src.ingest

# 2. Launch the chat UI
streamlit run app.py

# 3. Run the evaluation harness
python -m eval.run_eval
```

The ingester prints a summary (files parsed by type, unsupported files skipped
with reasons, parse failures, documents processed, chunks created) and exits
with a clear message if it finds no usable documents — it never writes an empty
index silently.

The Streamlit UI shows the grounded answer, a **Sources** section (document name
+ page number where available, derived only from validated `[S#]` citations),
and a collapsible **Debug panel** with each retrieved chunk, its metadata, its
raw Chroma distance, and approximate latency.

## Evaluation

`eval/questions.yaml` holds ~10 questions, including deliberately unanswerable
ones. `python -m eval.run_eval` reports, per question: id, question, whether an
expected source was retrieved, retrieved sources, a truncated answer, expected
answerability, `insufficient_context`, whether an unanswerable question was
correctly refused, and latency.

- **Retrieval correctness** is programmatic: retrieving at least one listed
  `expected_source` counts as success.
- **Refusal correctness** uses `RAGResult.insufficient_context` (set
  deterministically), so the harness never guesses refusal from prose.
- **No LLM judges semantic correctness.** A human reviews whether answers are
  actually right — for ten questions, anything fancier is wasted effort.

## Design decisions

- **Model literals centralized in `src/config.py`.** Swapping `gpt-6-luna` for
  `gpt-4o-mini` (or anything else) is an `.env` change, not a code change.
- **The index is derived data.** Ingestion drops and recreates the collection on
  every run (no incremental sync, no upsert-based cleanup), so stale chunks can
  never linger and deleting `index/` is harmless.
- **The system owns provenance, not the LLM.** Every chunk carries a
  deterministic `document_id` (from its relative path), `document_name`,
  `source`, deterministic `chunk_id`, and `page_number` for paginated sources.
  The LLM only ever sees opaque labels like `[S1]`; the application resolves
  those back to trusted metadata. The LLM is never trusted for filenames/URLs.
- **Citations are validated.** Only `[S#]` markers the model actually emitted
  **and** that point at a real retrieved chunk become sources; hallucinated or
  out-of-range labels are discarded. All retrieved chunks stay available for
  debugging regardless.
- **Deterministic refusals.** The model is told to emit a sentinel on
  insufficient context; the app converts that into one consistent human-readable
  message and sets `insufficient_context = True`.
- **The retrieval metric is labeled honestly** as a *distance* (smaller = more
  similar), never as "confidence". No relevance-threshold system yet — the
  metrics are exposed so evaluation can tell us whether a threshold is even
  needed.
- **`page_number` is omitted (not null) when unavailable**, so metadata writes
  work regardless of whether the installed Chroma supports null values.
- **Direct code over frameworks.** OpenAI SDK + Chroma + one text splitter, so
  the pipeline is understandable end-to-end instead of hidden behind
  `chain.invoke(...)`.

## Limitations

- Local execution only. The private corpus is gitignored, so Streamlit Community
  Cloud deployment is **not** assumed to work.
- No OCR, no PowerPoint/Excel parsing. If a `.pptx` holds a fact you need this
  week, export that one file to PDF rather than building a general presentation
  parser.
- No authentication, roles, or access control.
- No incremental indexing — every ingest is a full rebuild (fine for a static,
  one-semester corpus).
- No automatic semantic grading; answer correctness needs human review.
- Single OpenAI provider, single collection; no multi-provider abstraction.

## Future work

Deliberately **out of scope** for Proposal A: authentication, role management,
Google Drive sync, agentic editing, website integration, Docker, CI/CD,
multi-provider abstractions, a Makefile, OCR, and PPTX/XLSX parsing. These
belong to a future Proposal B, which will be designed once the real website
repo, stack, deployment environment, and stakeholder needs are known. Likely
next steps once we learn from this prototype: expand and curate the real corpus,
decide whether a retrieval distance threshold is warranted based on eval
results, add presentation ingestion only if the corpus proves it necessary, and
fold in stakeholder feedback from the demo.

---

## Revised Tech Stack — Proposal A

| Concern            | Recommended choice                              | Why |
|--------------------|-------------------------------------------------|-----|
| Language           | Python 3.11+                                    | Best fit for the team's experience and the document/RAG ecosystem |
| Environment        | `venv` + pinned `requirements.txt`              | Lowest conceptual overhead; reproducible enough for an MVP |
| LLM SDK            | Official `openai` Python package                | Direct dependency; no unnecessary orchestration framework |
| Generation model   | `gpt-6-luna` default, env-configurable          | Current inexpensive/fast OpenAI model; a more sensible new-project default than hard-wiring an older generation |
| Generation fallback| `gpt-4o-mini` if needed                         | Still available; useful if credits/account/model availability differ |
| Embeddings         | `text-embedding-3-small`                        | Small, inexpensive, fully adequate for a one-semester corpus |
| Vector store       | Chroma `PersistentClient`, local `./index/`     | No infrastructure, local persistence, fully regenerable |
| PDF parsing        | `pypdf`                                         | Lightweight; page-level provenance |
| DOCX parsing       | `python-docx`                                   | Covers Word docs without a larger framework |
| TXT / Markdown     | Python stdlib                                   | No extra dependency |
| Chunking           | `langchain-text-splitters` only                 | Reuse a proven recursive text splitter without full LangChain |
| UI                 | Streamlit                                       | Fastest route to a presentable chat + citations + debug interface |
| Config/secrets     | `python-dotenv`                                 | Simple local `.env` workflow |
| Eval definitions   | PyYAML                                          | Human-readable ~10-question evaluation set |
| Evaluation         | Custom Python script                            | More transparent than adding an evaluation framework |
| Version control    | Git/GitHub                                      | Existing agreed workflow |
| Deployment         | Local initially                                 | Public hosting is not an MVP requirement; the real corpus stays out of Git |

### Model configuration

```
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-6-luna
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

The application reads these **only** through `src/config.py`, so changing
`gpt-6-luna` to `gpt-4o-mini` (or another model) requires zero application-code
changes. For a ten-question RAG demo you don't need a strong reasoning model —
the quality bottleneck is far more likely to be document parsing → chunking →
retrieval → context quality than raw LLM capability.

### What we explicitly excluded

For Proposal A we intentionally do **not** add: FastAPI, React/Next.js,
TypeScript, PostgreSQL, Supabase, Pinecone, Qdrant, managed Chroma, Docker,
Google Drive API, OAuth, RBAC, Redis, Celery, full LangChain, LlamaIndex, agent
frameworks, LangGraph, observability SaaS, CI/CD, OCR, or PPTX/XLSX support
(unless the real corpus proves it's needed). The stack is intentionally boring,
which is a strength here: it leaves most of a limited week for what we're
actually trying to learn — what's in the documents, whether retrieval works,
which questions fail, and what officers want after seeing the prototype.

### Dependencies

Direct dependencies (pinned in `requirements.txt` to the versions verified
during initialization on Python 3.12):

```
openai==3.29.0
chromadb==1.5.9
streamlit==1.65.0
python-dotenv==1.2.4
pypdf==6.20.1
python-docx==1.2.0
langchain-text-splitters==1.1.3
PyYAML==6.0.3
```
