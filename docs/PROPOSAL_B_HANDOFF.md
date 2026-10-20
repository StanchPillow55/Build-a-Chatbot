# Proposal B handoff notes (from Proposal A)

Reusable outputs from the consulting MVP. **Do not** assume the Python /
Chroma / Streamlit stack must be reused in production.

## Provenance conventions

Every chunk metadata includes:

| Field | Meaning |
|-------|---------|
| `document_id` | Deterministic id from path relative to the corpus root |
| `document_name` | Basename (e.g. `Fall_2025_Handoff.pdf`) |
| `source` | Relative path within the corpus root |
| `chunk_id` | Deterministic id from document + page + ordinal |
| `page_number` | Present for PDFs; omitted (not null) when unavailable |

The LLM only sees opaque `[S#]` labels. The application resolves citations
against trusted retrieved metadata.

## Evaluation question set

See `eval/questions.yaml` (10 questions, 2 deliberately unanswerable). Recorded
results live in `docs/EVAL_RESULTS.md`.

**Harness (Ollama temporary provider run):** Retrieval **8/8**, Refusal **2/2**.
Human grading: all answerable answers factually correct; q05 had slightly awkward
phrasing from the local chat model. No distance threshold added.

## Corpus inventory (current stand-in)

Until the approved Google Drive Fall 2025 folder is copied into `data/raw/`,
the MVP uses this non-sensitive stand-in:

| File | Format | Topics |
|------|--------|--------|
| `Fall_2025_Membership.txt` | TXT | Join process, fees, attendance, contact |
| `Fall_2025_Meetings.md` | Markdown | Weekly meeting time/place, backups, officer planning |
| `Fall_2025_Officer_Handoff.docx` | DOCX | Roles, elections, handoff, spend norms |
| `Fall_2025_Events_Workshops.pdf` | PDF (3 pages) | Workshops, speakers, project teams |

Ingest summary for the stand-in: 4 documents processed, 6 chunks, 0 skips, 0
parse failures. PDF provenance spot-check: workshop query retrieved
`Fall_2025_Events_Workshops.pdf` pages 1–2 with correct `document_name` /
`page_number`.

Replace these with approved Drive documents and re-run `python -m src.ingest`.

## Retrieval experiments

- Default `TOP_K=4`, chunk size 1000 / overlap 150 — **kept as-is** after eval
- Temporary provider: `nomic-embed-text` via Ollama OpenAI-compat API (see
  `docs/EVAL_RESULTS.md` provider note). Production target remains
  `text-embedding-3-small` once a funded OpenAI key exists.
- Good-hit distances roughly ~0.48–0.90; no clear good/bad gap for a threshold
- Unanswerable questions still retrieve chunks; refusal depends on the
  generation sentinel, not distance filtering

## Failure cases

From the recorded eval run: **no parsing / chunking / retrieval failures.**
Minor generation phrasing quirk on q05 (elections wording) with the local
`llama3.2` model — re-check after restoring OpenAI chat. Capture officer
interview issues here after demos using `docs/DEMO.md`.

## Prompting lessons

Current behavior (see `src/rag.py`):

- System prompt requires grounding in provided `[S#]` context only
- Deterministic refusal sentinel → canonical `INSUFFICIENT_CONTEXT_MESSAGE`
- Citations validated; hallucinated `[S#]` labels discarded
- Local smaller models may paraphrase awkwardly but still refuse correctly when
  the sentinel path is followed

## Provider / ops note for Proposal B

Proposal A exhausted local OpenAI key sources (sibling project `.env` files,
Codex OAuth). Until billing is funded, demos can use Ollama via
`OPENAI_BASE_URL` without code changes. Proposal B should assume a **funded**
OpenAI (or other) account rather than relying on this temporary path.

## Stakeholder feedback

_To fill after demo interviews using `docs/DEMO.md`._
