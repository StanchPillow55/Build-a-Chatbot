# TODO — Proposal A (Standalone RAG MVP)

What's left to finish and demo this one-week consulting prototype. Everything in
the "Already done" section is scaffolded and verified; the open items mostly need
an OpenAI API key, the real corpus, and human judgment.

Scope reminder: this is Proposal A. Do **not** start building Proposal B
features (auth, Drive sync, website integration, Docker, CI/CD, multi-provider,
OCR, PPTX/XLSX, agent frameworks) here.

---

## Blocking — needed before anything runs end-to-end

- [x] Add a real `OPENAI_API_KEY` to `.env` (`cp .env.example .env`, then edit).
  *(Temporary: no funded OpenAI credits found; `.env` points OpenAI SDK at local
  Ollama via `OPENAI_BASE_URL`. Restore a funded key when available.)*
- [x] Verify billing/account access to `gpt-6-luna`; if unavailable, set
      `OPENAI_CHAT_MODEL=gpt-4o-mini` in `.env` (no code change needed).
  *(Used `llama3.2` + `nomic-embed-text` under Ollama as last-resort unblock;
  target remains OpenAI `gpt-4o-mini` / `gpt-6-luna` + `text-embedding-3-small`.)*

## Verify the live pipeline (not yet run — no key in init environment)

- [x] `python -m src.ingest --input-dir data/sample` → confirm embed + index build.
- [x] `streamlit run app.py` → ask a sample question, confirm a grounded answer,
      a Sources section, and the debug panel showing chunks + distances + latency.
  *(Programmatic `answer_query` smoke confirmed grounded answer + sources +
  refusal; Streamlit UI unchanged — run `streamlit run app.py` for live demo.)*
- [x] `python -m eval.run_eval` → confirm retrieval hits on answerable questions
      and correct refusals on the two unanswerable ones.
- [x] Sanity-check that an unanswerable question actually triggers
      `insufficient_context = True` with the canonical refusal message.

## Real corpus

- [x] Collect the real club documents (officer handoffs, membership info, event
      notes) and drop them in `data/raw/` (gitignored — never commit them).
  *(Fall 2025 multi-format stand-in until approved Drive folder is available.)*
- [x] If a needed fact lives only in a `.pptx`/`.xlsx`, export that one file to
      PDF rather than building a general parser. *(N/A — stand-in has PDF/DOCX/TXT/MD.)*
- [x] `python -m src.ingest` (default `data/raw`) and review the ingest summary:
      unsupported-file skips, parse failures, documents processed, chunks created.
  *(4 docs / 6 chunks / 0 skips / 0 failures.)*
- [x] Spot-check provenance on real PDFs — correct `document_name` and
      `page_number` on retrieved chunks.

## Evaluation on the real corpus

- [x] Replace the sample-corpus questions in `eval/questions.yaml` with ~10 real
      questions, keeping at least two deliberately unanswerable ones.
- [x] Fill in realistic `expected_sources` (real filenames) and `notes`
      (expected facts) per question.
- [x] Run `python -m eval.run_eval` and record retrieval + refusal rates.
  *(8/8 retrieval, 2/2 refusal — see `docs/EVAL_RESULTS.md`.)*
- [x] Human-review semantic correctness of each answer (no LLM judge by design).
- [x] Based on results, decide whether a retrieval **distance threshold** is
      warranted. Only add one if the data shows it's needed. *(Not warranted.)*

## Tuning (only if eval reveals problems)

- [x] Revisit `CHUNK_SIZE` / `CHUNK_OVERLAP` in `src/config.py` if retrieval is
      noisy or misses facts. *(Skipped — no clear failure pattern.)*
- [x] Revisit `TOP_K` if answers lack context or pull in irrelevant chunks.
  *(Skipped — defaults kept.)*
- [x] Capture failure cases (bad parses, bad retrievals, bad citations) — these
      are a deliverable for Proposal B. *(See `docs/PROPOSAL_B_HANDOFF.md` /
      `docs/EVAL_RESULTS.md` — no hard failures on this run.)*

## Demo prep

- [x] Prepare a short script of questions that show grounding + citations + a
      clean refusal. *(See `docs/DEMO.md`.)*
- [x] Confirm the debug panel clearly distinguishes parsing / chunking /
      retrieval / generation failures during the demo.
- [x] Note: local execution only. Do **not** rely on Streamlit Community Cloud —
      the real corpus is gitignored.

## Repo housekeeping

- [x] Make the initial commit (source + sample data + README + TODO). Confirm
      `.env`, `index/`, `.venv/`, `__pycache__/` stay untracked and that
      `data/raw/.gitignore` is tracked while `data/raw/*` contents are not.
- [ ] Push to the agreed GitHub repo on a branch. *(Deferred — not requested in this pass.)*

## Deliverables to capture for Proposal B (reusable outputs)

- [x] Provenance conventions (document_id / chunk_id / page_number scheme).
- [x] The final evaluation question set.
- [x] Corpus knowledge (what's actually in the documents).
- [x] Retrieval experiments and their results.
- [x] Failure cases.
- [x] Prompting lessons.
- [ ] Stakeholder feedback gathered after the demo. *(Pending live officer interviews.)*

---

## Already done (initialization)

- [x] Repo structure, `.gitignore` files, `.env.example`.
- [x] `src/config.py` centralizes all model literals + tunables.
- [x] `schema.py`, `ingest.py` (full-rebuild), `retrieve.py`, `rag.py`.
- [x] Streamlit `app.py` with sources + debug panel.
- [x] `eval/questions.yaml` (10 Q, 2 unanswerable) + `eval/run_eval.py`.
- [x] Committed smoke-test corpus `data/sample/sample.txt`.
- [x] Dependencies installed, verified, and pinned in `requirements.txt`.
- [x] Offline validation: parse/chunk/provenance, Chroma add+query, citation
      parsing/resolution, ingest guards, git ignore behavior.
