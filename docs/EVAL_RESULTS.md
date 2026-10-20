# Evaluation results — Fall 2025 corpus

Lightweight human + harness table for the ~10-question MVP set in
`eval/questions.yaml`. Re-run with:

```bash
python -m src.ingest
python -m eval.run_eval
```

Paste harness summary lines below after each run. Semantic correctness is
**human-graded** (no LLM judge).

## Provider note (this run)

No funded OpenAI API key was available locally (Algoverse `sk-proj` authenticates
but has zero credits; other sibling keys invalid; Codex OAuth hits the same
billing/quota wall). This recorded run used the **OpenAI Python SDK** against a
**local Ollama** OpenAI-compatible endpoint (`OPENAI_BASE_URL=http://localhost:11434/v1`,
`OPENAI_CHAT_MODEL=llama3.2`, `OPENAI_EMBEDDING_MODEL=nomic-embed-text`). Locked
stack and code path are unchanged — restore a funded OpenAI key by removing
`OPENAI_BASE_URL` and setting `OPENAI_CHAT_MODEL=gpt-4o-mini` (or `gpt-6-luna` if
available) plus `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`, then re-ingest.

## Harness summary (latest run)

```
Retrieval success: 8/8
Refusal success:   2/2
```

## Per-question table

| Test | Relevant source retrieved? | Answer correct? | Citation/source correct? | Failure stage | Notes |
|------|----------------------------|-----------------|--------------------------|---------------|-------|
| q01 meetings | yes | yes | yes (`Fall_2025_Meetings.md`) | none | Thu 6:00–7:30 PM, SU 210; backup Eng 301 mentioned correctly |
| q02 join | yes | yes | yes (`Fall_2025_Membership.txt`) | none | Sign-up form + Discord |
| q03 fee | yes | yes | yes (`Fall_2025_Membership.txt`) | none | No Fall 2025 fee; optional merch noted |
| q04 officer roles | yes | yes | yes (`Fall_2025_Officer_Handoff.docx`) | none | President, VP, Treasurer, Events Coordinator |
| q05 elections | yes | yes (minor phrasing) | yes (`Fall_2025_Officer_Handoff.docx`) | none | Fact correct (end of Spring for following year); local model wording slightly awkward |
| q06 workshops | yes | yes | yes (`Fall_2025_Events_Workshops.pdf`) | none | Python ML, PyTorch NN, intro RAG; PDF page 1 retrieved |
| q07 projects | yes | yes | yes (`Fall_2025_Events_Workshops.pdf`) | none | CV demos, chatbots, data-viz dashboards |
| q08 room booking | yes | yes | yes (`Fall_2025_Meetings.md`) | none | Events Coordinator books; backup Eng 301 |
| q09 president 2035 (unanswerable) | n/a | yes (refusal) | n/a | none | `insufficient_context=True`; canonical refusal |
| q10 annual budget (unanswerable) | n/a | yes (refusal) | n/a | none | Correctly refused; docs only have $100 vote threshold |

Failure stage key: `parsing` → `chunking` → `retrieval` → `generation` (or
`none` if pass).

## Tuning decisions

Default knobs in `src/config.py`: `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=150`,
`TOP_K=4`. **No changes.** Retrieval hit every expected source; refusals were
clean. Observed Chroma distances on good hits were roughly ~0.48–0.90 with no
clean gap that would justify a distance threshold (unanswerable queries still
retrieve *something*; refusal is generation-driven via the sentinel). Revisit
only after swapping back to OpenAI embeddings if distance distributions change.
