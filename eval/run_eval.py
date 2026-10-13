"""Evaluation harness for the RAG MVP.

Runs each question in eval/questions.yaml through the RAG pipeline and reports,
per question:

    - id
    - question
    - expected source retrieved?   (programmatic, via expected_sources)
    - retrieved sources
    - truncated answer
    - expected answerability
    - insufficient_context         (from RAGResult)
    - correct refusal for unanswerable question?
    - latency

Retrieval correctness is determined programmatically from expected_sources:
retrieving at least one listed source counts as success. Refusal correctness
is determined from RAGResult.insufficient_context. No LLM judges semantic
correctness — a human reviews whether answers are actually right.

Usage:
    python -m eval.run_eval
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import yaml
from openai import OpenAI

from src import config
from src.rag import answer_query

QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.yaml"


def load_questions() -> list[dict]:
    with QUESTIONS_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, list):
        raise ValueError("questions.yaml must be a list of question entries.")
    return data


def retrieved_source_names(result) -> list[str]:
    """Distinct document_name / source values across retrieved chunks."""
    names: list[str] = []
    for chunk in result.retrieved_chunks:
        for key in ("document_name", "source"):
            value = chunk.metadata.get(key)
            if value and value not in names:
                names.append(value)
    return names


def expected_source_retrieved(expected: list[str], result) -> bool:
    """True if at least one expected source appears among retrieved chunks."""
    if not expected:
        return False  # not applicable; reported as "n/a" for unanswerables
    retrieved = retrieved_source_names(result)
    for want in expected:
        for got in retrieved:
            # match on basename so "sample.txt" matches "sample.txt" or a path
            if want == got or Path(got).name == Path(want).name:
                return True
    return False


def truncate(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> int:
    if not config.OPENAI_API_KEY:
        print(
            "ERROR: OPENAI_API_KEY is not set. Copy .env.example to .env and add "
            "your key before running evaluation."
        )
        return 1

    try:
        questions = load_questions()
    except Exception as exc:
        print(f"ERROR loading questions: {exc}")
        return 1

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    retrieval_hits = 0
    retrieval_total = 0
    refusal_hits = 0
    refusal_total = 0

    for q in questions:
        qid = q.get("id", "?")
        question = q.get("question", "")
        expected = q.get("expected_sources", []) or []
        answerable = bool(q.get("answerable", True))

        start = time.perf_counter()
        try:
            result = answer_query(question, client=client)
            latency = time.perf_counter() - start
            err = None
        except Exception as exc:
            latency = time.perf_counter() - start
            result = None
            err = f"{type(exc).__name__}: {exc}"

        print("=" * 70)
        print(f"ID:                  {qid}")
        print(f"Question:            {question}")

        if err:
            print(f"ERROR:               {err}")
            print(f"Latency:             {latency:.2f}s")
            continue

        retrieved = retrieved_source_names(result)

        # Retrieval correctness (only meaningful for answerable questions).
        if answerable and expected:
            retrieval_total += 1
            hit = expected_source_retrieved(expected, result)
            if hit:
                retrieval_hits += 1
            retrieval_display = "yes" if hit else "NO"
        else:
            retrieval_display = "n/a"

        # Refusal correctness (only meaningful for unanswerable questions).
        if not answerable:
            refusal_total += 1
            correct_refusal = result.insufficient_context
            if correct_refusal:
                refusal_hits += 1
            refusal_display = "yes" if correct_refusal else "NO"
        else:
            refusal_display = "n/a"

        print(f"Expected source retrieved?  {retrieval_display}  "
              f"(expected: {expected or '—'})")
        print(f"Retrieved sources:   {retrieved or '—'}")
        print(f"Answer (truncated):  {truncate(result.answer)}")
        print(f"Expected answerable: {answerable}")
        print(f"insufficient_context:{result.insufficient_context}")
        print(f"Correct refusal?     {refusal_display}")
        print(f"Latency:             {latency:.2f}s")

    print("=" * 70)
    print("SUMMARY")
    if retrieval_total:
        print(
            f"  Retrieval success: {retrieval_hits}/{retrieval_total} "
            f"answerable questions retrieved an expected source."
        )
    if refusal_total:
        print(
            f"  Refusal success:   {refusal_hits}/{refusal_total} "
            f"unanswerable questions were correctly refused."
        )
    print("  (Human review required for semantic answer correctness.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
