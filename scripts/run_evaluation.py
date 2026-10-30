from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and citation coverage.")
    parser.add_argument("--backend", choices=["ollama", "mock"], default=None)
    parser.add_argument("--embedding-backend", choices=["fastembed", "hash"], default=None)
    parser.add_argument(
        "--questions",
        type=Path,
        default=ROOT / "evaluation" / "questions.jsonl",
    )
    args = parser.parse_args()
    if args.backend:
        os.environ["LLM_BACKEND"] = args.backend
    if args.embedding_backend:
        os.environ["EMBEDDING_BACKEND"] = args.embedding_backend

    from teams_copilot_troubleshooter.graph import ask
    from teams_copilot_troubleshooter.config import MAX_ANSWER_TOKENS, MODEL_NAME

    questions = load_questions(args.questions)
    results: list[dict[str, Any]] = []
    source_hits = 0
    card_hits = 0
    term_hits = 0
    citation_hits = 0
    generation_truncated_answers = 0
    final_truncated_answers = 0
    fallback_answers = 0
    answer_methods: Counter[str] = Counter()
    answerable_count = 0
    for item in questions:
        result = ask(item["query"], embedding_backend=args.embedding_backend)
        evidence = result.get("evidence", [])
        retrieved_card_ids = {doc.get("id") for doc in evidence}
        retrieved_ids = {doc.get("source_id") for doc in evidence}
        expected_ids = set(item.get("expected_source_ids", []))
        expected_cards = set(item.get("expected_card_ids", []))
        source_hit = bool(expected_ids & retrieved_ids)
        card_hit = bool(expected_cards & retrieved_card_ids)
        retrieved_text = " ".join(doc.get("text", "") for doc in evidence).casefold()
        expected_terms = [term.casefold() for term in item.get("expected_terms", [])]
        term_hit = not expected_terms or any(term in retrieved_text for term in expected_terms)
        has_citation = "[S" in result.get("answer", "")
        generation_truncated = bool(result.get("generation_truncated", False))
        answer_truncated = bool(result.get("answer_truncated", False))
        answer_fallback_used = bool(result.get("answer_fallback_used", False))
        answer_method = str(result.get("answer_method", "unknown"))
        answerable = bool(item.get("answerable", True))

        source_hits += int(source_hit)
        card_hits += int(card_hit)
        term_hits += int(term_hit)
        citation_hits += int(has_citation)
        generation_truncated_answers += int(generation_truncated)
        final_truncated_answers += int(answer_truncated)
        fallback_answers += int(answer_fallback_used)
        answer_methods[answer_method] += 1
        answerable_count += int(answerable)
        results.append(
            {
                "id": item["id"],
                "query": item["query"],
                "expected_source_ids": sorted(expected_ids),
                "retrieved_source_ids": sorted(retrieved_ids),
                "expected_card_ids": sorted(expected_cards),
                "retrieved_card_ids": sorted(retrieved_card_ids),
                "source_hit": source_hit,
                "card_hit": card_hit,
                "expected_term_hit": term_hit,
                "citation_present": has_citation,
                "generation_done_reason": result.get("generation_done_reason", "unknown"),
                "generation_truncated": generation_truncated,
                "answer_truncated": answer_truncated,
                "answer_fallback_used": answer_fallback_used,
                "answer_method": answer_method,
                "answerable": answerable,
                "answer": result.get("answer", ""),
            }
        )

    denominator = max(1, len(questions))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_backend": os.getenv("LLM_BACKEND", "ollama"),
        "embedding_backend": os.getenv("EMBEDDING_BACKEND", "fastembed"),
        "model_name": MODEL_NAME if os.getenv("LLM_BACKEND", "ollama").strip().lower() == "ollama" else "dummy",
        "max_answer_tokens": MAX_ANSWER_TOKENS,
        "question_count": len(questions),
        "source_hit_rate_at_k": round(source_hits / denominator, 4),
        "expected_card_hit_rate_at_k": round(card_hits / denominator, 4),
        "expected_term_hit_rate": round(term_hits / denominator, 4),
        "citation_presence_rate": round(citation_hits / denominator, 4),
        "truncated_answer_count": generation_truncated_answers,
        "generation_truncated_count": generation_truncated_answers,
        "final_truncated_answer_count": final_truncated_answers,
        "fallback_answer_count": fallback_answers,
        "answer_method_counts": dict(answer_methods),
        "answerable_question_count": answerable_count,
        "results": results,
    }
    output_dir = ROOT / "reports" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "evaluation_results.json"
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
    print(f"Detailed results: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
