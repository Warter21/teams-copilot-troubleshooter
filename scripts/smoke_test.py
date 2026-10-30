from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one end-to-end Teams Copilot troubleshooting request."
    )
    parser.add_argument("--backend", choices=["ollama", "mock"], default=None)
    parser.add_argument(
        "--embedding-backend", choices=["fastembed", "hash"], default=None
    )
    parser.add_argument(
        "--question",
        default="Which languages can Interpreter translate into in a Teams meeting?",
    )
    args = parser.parse_args()
    if args.backend:
        os.environ["LLM_BACKEND"] = args.backend
    if args.embedding_backend:
        os.environ["EMBEDDING_BACKEND"] = args.embedding_backend

    from teams_copilot_troubleshooter.graph import ask

    started = time.perf_counter()
    result = ask(args.question, embedding_backend=args.embedding_backend)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    answer = result.get("answer", "").strip()
    answer_truncated = result.get("answer_truncated", False)
    generation_truncated = result.get("generation_truncated", False)
    answer_fallback_used = result.get("answer_fallback_used", False)
    answer_method = result.get("answer_method", "")
    evidence = result.get("evidence", [])
    node_names = {item.get("node", "") for item in result.get("trace", [])}

    if not answer:
        raise SystemExit("Smoke test failed: the workflow returned an empty answer.")
    if answer_truncated:
        raise SystemExit(
            "Smoke test failed: the final user-facing answer is still truncated."
        )
    if generation_truncated and not answer_fallback_used:
        raise SystemExit(
            "Smoke test failed: the model draft reached its token limit without a fallback answer."
        )
    if not answer_method:
        raise SystemExit("Smoke test failed: the workflow did not record its response method.")
    if not re.search(r"\[S\d+\]", answer):
        raise SystemExit("Smoke test failed: the final answer has no source citation.")
    if not evidence:
        raise SystemExit("Smoke test failed: the workflow retrieved no evidence.")
    required_nodes = {
        "1. Triage",
        "2. Plan",
        "3. RAG subgraph",
        "4. Diagnostic tool",
        "5. Evidence review and answer",
    }
    missing_nodes = sorted(required_nodes - node_names)
    if missing_nodes:
        raise SystemExit(
            "Smoke test failed: missing workflow trace nodes: "
            + ", ".join(missing_nodes)
        )

    print(
        json.dumps(
            {
                "status": "passed",
                "llm_backend": os.getenv("LLM_BACKEND", "ollama"),
                "embedding_backend": os.getenv("EMBEDDING_BACKEND", "fastembed"),
                "model_name": (
                    os.getenv("MODEL_NAME", "qwen3:0.6b")
                    if os.getenv("LLM_BACKEND", "ollama").strip().lower() == "ollama"
                    else "dummy"
                ),
                "max_answer_tokens": int(os.getenv("MAX_ANSWER_TOKENS", "256")),
                "generation_done_reason": result.get("generation_done_reason", "unknown"),
                "generation_truncated": generation_truncated,
                "answer_truncated": answer_truncated,
                "answer_fallback_used": answer_fallback_used,
                "answer_method": answer_method,
                "elapsed_ms": elapsed_ms,
                "answer_char_count": len(answer),
                "evidence_count": len(evidence),
                "diagnostic_count": len(result.get("diagnostics", [])),
                "workflow_nodes": sorted(node_names),
                "answer": answer,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
