# Officer interview demo script

Local-only demo for Proposal A. Do **not** rely on a public URL — the real
corpus in `data/raw/` is gitignored.

**Provider:** prefer a funded OpenAI key (`gpt-4o-mini` or `gpt-6-luna` +
`text-embedding-3-small`). If none is available, the current `.env` may point
the OpenAI SDK at local Ollama (`OPENAI_BASE_URL`); keep Ollama running before
ingest/UI. See `docs/EVAL_RESULTS.md` for the recorded temporary-provider run.

## Cold start (under 5 minutes)

```bash
source .venv/bin/activate
# If the index is missing or stale:
python -m src.ingest
streamlit run app.py
```

Walkthrough order for each question: **answer → Sources → Debug panel**.

## Script (6 questions)

Use these in order. The last failure-shaped question is optional but useful for
soliciting feedback.

| # | Question | Expected behavior |
|---|----------|-------------------|
| 1 | When and where does the AI & ML Club meet? | Grounded answer; cite `Fall_2025_Meetings.md` |
| 2 | What topics does the Fall 2025 workshop series cover? | Grounded answer; cite `Fall_2025_Events_Workshops.pdf` (page ~1) |
| 3 | What officer roles lead the club? | Grounded answer; cite `Fall_2025_Officer_Handoff.docx` |
| 4 | Who was the club president in 2035? | Clean refusal (`insufficient_context`); no fabricated name |
| 5 | Is there a membership fee for Fall 2025? | Grounded answer; cite `Fall_2025_Membership.txt` |
| 6 | *(optional)* What is the club's annual operating budget in dollars? | Refusal — docs only mention a $100 vote threshold, not a total budget |

## Debug panel talking points

Use Debug to show how you localize failures:

| If you see… | Likely stage |
|-------------|--------------|
| Empty / garbled chunk text | Parsing |
| Oddly split sentences / missing neighbors | Chunking |
| Wrong documents or high distances for an easy fact | Retrieval |
| Good chunks, wrong or empty prose | Generation |

Distances are **distances** (smaller = more similar), not confidence scores.

## Interview framing

Do **not** ask “what should an AI chatbot have?” Show the demo, then ask:

1. What information is missing?
2. What answers are wrong?
3. What would actually save officers time?

Capture answers in `docs/PROPOSAL_B_HANDOFF.md` after the session.
