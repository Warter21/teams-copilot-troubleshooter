from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile_value
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a sequential 50-200 request workflow load scenario."
    )
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--backend", choices=["ollama", "mock"], default=None)
    parser.add_argument("--embedding-backend", choices=["fastembed", "hash"], default=None)
    parser.add_argument(
        "--questions",
        type=Path,
        default=ROOT / "evaluation" / "questions.jsonl",
    )
    args = parser.parse_args()
    if not 50 <= args.requests <= 200:
        parser.error("--requests must be between 50 and 200.")
    if args.backend:
        os.environ["LLM_BACKEND"] = args.backend
    if args.embedding_backend:
        os.environ["EMBEDDING_BACKEND"] = args.embedding_backend

    from teams_copilot_troubleshooter.graph import ask
    from teams_copilot_troubleshooter.config import MAX_ANSWER_TOKENS, MODEL_NAME

    questions = load_questions(args.questions)
    if not questions:
        parser.error("The evaluation question file is empty.")

    warmup_started = time.perf_counter()
    for warmup_index in range(max(0, args.warmup)):
        item = questions[warmup_index % len(questions)]
        ask(item["query"], embedding_backend=args.embedding_backend)
    cold_start_ms = (time.perf_counter() - warmup_started) * 1000 if args.warmup else None

    latencies: list[float] = []
    stage_times: dict[str, list[float]] = {}
    failures: list[dict[str, Any]] = []
    generation_truncated_responses = 0
    final_truncated_responses = 0
    fallback_responses = 0
    answer_methods: Counter[str] = Counter()
    total_started = time.perf_counter()

    for request_number in range(args.requests):
        item = questions[request_number % len(questions)]
        started = time.perf_counter()
        try:
            result = ask(item["query"], embedding_backend=args.embedding_backend)
            generation_truncated_responses += int(bool(result.get("generation_truncated", False)))
            final_truncated_responses += int(bool(result.get("answer_truncated", False)))
            fallback_responses += int(bool(result.get("answer_fallback_used", False)))
            answer_methods[str(result.get("answer_method", "unknown"))] += 1
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies.append(elapsed_ms)
            for stage, value in result.get("timings_ms", {}).items():
                stage_times.setdefault(stage, []).append(float(value))
        except Exception as exc:
            failures.append({"request": request_number + 1, "error": str(exc)})

    wall_seconds = time.perf_counter() - total_started
    successful = len(latencies)
    sorted_stages = sorted(
        (
            (stage, statistics.mean(values))
            for stage, values in stage_times.items()
            if values
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "llm_backend": os.getenv("LLM_BACKEND", "ollama"),
        "embedding_backend": os.getenv("EMBEDDING_BACKEND", "fastembed"),
        "model_name": MODEL_NAME if os.getenv("LLM_BACKEND", "ollama").strip().lower() == "ollama" else "dummy",
        "max_answer_tokens": MAX_ANSWER_TOKENS,
        "request_count": args.requests,
        "warmup_requests": max(0, args.warmup),
        "first_warmup_elapsed_ms": round(cold_start_ms, 2) if cold_start_ms is not None else None,
        "successful_requests": successful,
        "failed_requests": len(failures),
        "truncated_responses": generation_truncated_responses,
        "generation_truncated_responses": generation_truncated_responses,
        "final_truncated_responses": final_truncated_responses,
        "fallback_responses": fallback_responses,
        "answer_method_counts": dict(answer_methods),
        "concurrency": 1,
        "wall_time_seconds": round(wall_seconds, 3),
        "throughput_requests_per_second": round(successful / wall_seconds, 4) if wall_seconds else 0,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
            "p50": round(percentile(latencies, 0.50), 2) if latencies else None,
            "p95": round(percentile(latencies, 0.95), 2) if latencies else None,
            "max": round(max(latencies), 2) if latencies else None,
        },
        "mean_stage_latency_ms": {
            stage: round(mean_ms, 2) for stage, mean_ms in sorted_stages
        },
        "slowest_mean_stage": sorted_stages[0][0] if sorted_stages else None,
        "failures": failures,
        "interpretation": (
            "The selected backend is recorded above. Use backend=ollama for end-to-end "
            "model latency; backend=mock is an orchestration-only baseline."
        ),
    }
    output_dir = ROOT / "reports" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"load_test_{args.requests}_requests.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Detailed results: {output_path}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
