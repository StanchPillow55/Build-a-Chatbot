"""Ingestion: rebuild the MVP Chroma collection from scratch.

The index is DERIVED data. Running this module performs a full rebuild:

    drop/recreate collection -> parse corpus -> normalize -> chunk ->
    embed -> populate fresh collection

There is no incremental sync and no reliance on upserts to clean stale chunks.
Deleting ./index/ never destroys authoritative information; this rebuilds it.

Usage:
    python -m src.ingest                       # defaults to data/raw
    python -m src.ingest --input-dir data/sample   # smoke test
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

from . import config
from .schema import Chunk, chunk_id_from, document_id_from_path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


# ---------------------------------------------------------------------------
# Parsing: each parser yields (page_number, text) pairs.
# page_number is None for non-paginated sources.
# ---------------------------------------------------------------------------


@dataclass
class ParsedPage:
    page_number: Optional[int]
    text: str


def parse_pdf(path: Path) -> list[ParsedPage]:
    """Parse a PDF page-by-page so page provenance is retained."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[ParsedPage] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(ParsedPage(page_number=i, text=text))
    return pages


def parse_docx(path: Path) -> list[ParsedPage]:
    from docx import Document

    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs)
    return [ParsedPage(page_number=None, text=text)]


def parse_text(path: Path) -> list[ParsedPage]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [ParsedPage(page_number=None, text=text)]


def parse_file(path: Path) -> list[ParsedPage]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf(path)
    if ext == ".docx":
        return parse_docx(path)
    if ext in {".txt", ".md"}:
        return parse_text(path)
    raise ValueError(f"unsupported extension: {ext}")


# ---------------------------------------------------------------------------
# Normalize + chunk
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Light normalization: collapse whitespace, strip. Keeps it debuggable."""
    lines = [line.strip() for line in text.splitlines()]
    collapsed = "\n".join(line for line in lines if line)
    return collapsed.strip()


def build_chunks(
    root: Path,
    path: Path,
    pages: list[ParsedPage],
    splitter: RecursiveCharacterTextSplitter,
) -> list[Chunk]:
    document_id = document_id_from_path(root, path)
    document_name = path.name
    source = path.resolve().relative_to(root.resolve()).as_posix()

    chunks: list[Chunk] = []
    ordinal = 0
    for page in pages:
        normalized = normalize(page.text)
        if not normalized:
            continue
        for piece in splitter.split_text(normalized):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                Chunk(
                    text=piece,
                    document_id=document_id,
                    document_name=document_name,
                    source=source,
                    chunk_id=chunk_id_from(document_id, page.page_number, ordinal),
                    page_number=page.page_number,
                )
            )
            ordinal += 1
    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Embed texts in batches using the configured embedding model."""
    embeddings: list[list[float]] = []
    batch_size = 128
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        resp = client.embeddings.create(
            model=config.OPENAI_EMBEDDING_MODEL, input=batch
        )
        embeddings.extend(item.embedding for item in resp.data)
    return embeddings


# ---------------------------------------------------------------------------
# Main ingest routine
# ---------------------------------------------------------------------------


def ingest(input_dir: Path) -> int:
    """Run the full rebuild. Returns a process exit code (0 == success)."""
    if not input_dir.exists():
        print(f"ERROR: input directory does not exist: {input_dir}")
        return 1

    all_files = sorted(p for p in input_dir.rglob("*") if p.is_file())
    # The data/raw .gitignore is not corpus content; never ingest it.
    all_files = [p for p in all_files if p.name != ".gitignore"]

    supported = [p for p in all_files if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    unsupported = [p for p in all_files if p.suffix.lower() not in SUPPORTED_EXTENSIONS]

    # Report unsupported files loudly — never silently ignored.
    parsed_by_type: dict[str, int] = {}
    parse_failures: list[tuple[str, str]] = []
    documents_processed = 0
    all_chunks: list[Chunk] = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )

    for path in supported:
        ext = path.suffix.lower()
        try:
            pages = parse_file(path)
            chunks = build_chunks(input_dir, path, pages, splitter)
        except Exception as exc:  # parse failure for this file only
            parse_failures.append((path.name, str(exc)))
            continue

        if not chunks:
            parse_failures.append((path.name, "no extractable text"))
            continue

        parsed_by_type[ext] = parsed_by_type.get(ext, 0) + 1
        documents_processed += 1
        all_chunks.extend(chunks)

    # Fail clearly rather than producing an empty index silently.
    if not all_chunks:
        print_summary(
            input_dir,
            parsed_by_type,
            unsupported,
            parse_failures,
            documents_processed,
            chunks_created=0,
        )
        print(
            "\nERROR: no usable documents were found. Nothing was indexed.\n"
            f"Add supported files ({', '.join(sorted(SUPPORTED_EXTENSIONS))}) "
            f"to {input_dir} and try again."
        )
        return 1

    # Embed.
    if not config.OPENAI_API_KEY:
        print(
            "ERROR: OPENAI_API_KEY is not set. Copy .env.example to .env and add "
            "your key before ingesting."
        )
        return 1

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    texts = [c.text for c in all_chunks]
    print(f"Embedding {len(texts)} chunks with {config.OPENAI_EMBEDDING_MODEL} ...")
    embeddings = embed_texts(client, texts)

    # Drop/recreate the collection, then populate fresh.
    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=str(config.INDEX_DIR))
    try:
        chroma.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass  # collection may not exist yet; a full rebuild follows regardless
    collection = chroma.create_collection(config.COLLECTION_NAME)

    collection.add(
        ids=[c.chunk_id for c in all_chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[c.metadata() for c in all_chunks],
    )

    print_summary(
        input_dir,
        parsed_by_type,
        unsupported,
        parse_failures,
        documents_processed,
        chunks_created=len(all_chunks),
    )
    print(f"\nIndex written to {config.INDEX_DIR} (collection: {config.COLLECTION_NAME}).")
    return 0


def print_summary(
    input_dir: Path,
    parsed_by_type: dict[str, int],
    unsupported: list[Path],
    parse_failures: list[tuple[str, str]],
    documents_processed: int,
    chunks_created: int,
) -> None:
    print("\n==================== Ingestion summary ====================")
    print(f"Input directory: {input_dir}")

    print("\nSupported files parsed, by type:")
    if parsed_by_type:
        for ext in sorted(parsed_by_type):
            print(f"  {ext}: {parsed_by_type[ext]}")
    else:
        print("  (none)")

    print("\nUnsupported files skipped:")
    if unsupported:
        for p in unsupported:
            print(f"  {p.name}  (reason: unsupported extension '{p.suffix.lower()}')")
    else:
        print("  (none)")

    print("\nParse failures:")
    if parse_failures:
        for name, reason in parse_failures:
            print(f"  {name}  (reason: {reason})")
    else:
        print("  (none)")

    print(f"\nDocuments processed: {documents_processed}")
    print(f"Chunks created:      {chunks_created}")
    print("===========================================================")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the MVP RAG index.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=config.DEFAULT_INPUT_DIR,
        help="Directory to ingest (default: data/raw).",
    )
    args = parser.parse_args(argv)
    return ingest(args.input_dir)


if __name__ == "__main__":
    sys.exit(main())
