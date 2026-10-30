from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "source_manifest.json"
CARDS_PATH = DATA_DIR / "knowledge_cards.jsonl"
HUNGARIAN_CARDS_PATH = DATA_DIR / "knowledge_cards.hu.json"
RULES_PATH = DATA_DIR / "diagnostic_rules.json"
SNAPSHOT_PATH = DATA_DIR / "cache" / "official_docs_snapshot.jsonl"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:0.6b")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "fastembed").strip().lower()
FASTEMBED_CACHE_DIR = Path(
    os.getenv("FASTEMBED_CACHE_DIR", str(PROJECT_ROOT / ".cache" / "fastembed"))
).expanduser()
MAX_CONTEXT_CHARS = _int_env("MAX_CONTEXT_CHARS", 6000)
MAX_ANSWER_TOKENS = _int_env("MAX_ANSWER_TOKENS", 256)
RETRIEVAL_TOP_K = _int_env("RETRIEVAL_TOP_K", 5)
OLLAMA_TIMEOUT_SECONDS = _int_env("OLLAMA_TIMEOUT_SECONDS", 300)
EMBEDDING_THREADS = _int_env("EMBEDDING_THREADS", 2)
