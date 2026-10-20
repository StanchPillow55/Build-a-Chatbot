# Data

This directory holds the corpus the chatbot indexes.

## Layout

```
data/
  sample/   committed smoke-test corpus (tiny, non-sensitive)
  raw/      real club documents (ignored by Git, never committed)
```

## Authoritative vs. derived

- `data/raw/` is **authoritative**. Put the real AI & ML Club documents here
  (PDF, DOCX, TXT, MD). Everything in this folder is gitignored except its own
  `.gitignore`, so the directory survives a fresh clone but no club document is
  ever committed.
- **Current consulting stand-in:** until the approved Fall 2025 Google Drive
  folder is available, `data/raw/` may hold non-sensitive multi-format
  placeholders (`Fall_2025_*.{txt,md,docx,pdf}`) so ingestion, provenance,
  eval, and demos can proceed. Replace them with approved documents and
  re-ingest when Drive access is ready.
- `data/sample/` is a committed smoke-test corpus so a fresh clone can run the
  full pipeline end-to-end without any private data.
- `index/` (at the repo root) is **derived** data generated from the corpus.
  Deleting `index/` is always safe; `python -m src.ingest` regenerates it.

## Supported file types

| Extension | Parser        | Provenance            |
|-----------|---------------|-----------------------|
| `.pdf`    | pypdf         | per-page (page_number)|
| `.docx`   | python-docx   | whole document        |
| `.txt`    | stdlib        | whole document        |
| `.md`     | stdlib        | whole document        |

Unsupported files (e.g. `.pptx`, `.xlsx`, images) are **skipped and reported**
by the ingester, never silently ignored. If a presentation holds a fact you
need this week, export that one file to PDF rather than building a general
presentation parser.

## Usage

```bash
# Default: index the real corpus in data/raw/
python -m src.ingest

# Smoke test against the committed sample corpus
python -m src.ingest --input-dir data/sample
```
