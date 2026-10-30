from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Any

import numpy as np

from .config import (
    EMBEDDING_BACKEND,
    EMBEDDING_MODEL,
    EMBEDDING_THREADS,
    FASTEMBED_CACHE_DIR,
    RETRIEVAL_TOP_K,
)
from .knowledge import load_knowledge_cards


AREA_FILTERS = {
    "meeting_copilot": {"meeting_copilot", "recap"},
    "recap": {"meeting_copilot", "recap"},
    "facilitator": {"facilitator", "meeting_copilot"},
    "interpreter": {"interpreter"},
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w]+", (text or "").casefold(), flags=re.UNICODE)


def _hash_embedding(text: str, dimensions: int = 384) -> np.ndarray:
    vector = np.zeros(dimensions, dtype=np.float32)
    tokens = tokenize(text)
    features = tokens + [text[i : i + 3].casefold() for i in range(max(0, len(text) - 2))]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[bucket] += sign
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


class KnowledgeIndex:
    """Small local hybrid index: multilingual dense vectors plus BM25-style term scoring."""

    def __init__(
        self,
        cards: list[dict[str, Any]] | None = None,
        embedding_backend: str | None = None,
    ) -> None:
        self.cards = cards if cards is not None else load_knowledge_cards()
        if not self.cards:
            raise ValueError("The knowledge base contains no usable documents.")
        self.embedding_backend = (embedding_backend or EMBEDDING_BACKEND).lower()
        self._embedder: Any = None
        self._document_vectors = self._build_document_vectors()
        self._token_lists = [tokenize(card["text"]) for card in self.cards]
        self._doc_lengths = np.array([len(tokens) for tokens in self._token_lists], dtype=np.float32)
        self._avg_doc_length = float(self._doc_lengths.mean()) if len(self.cards) else 0.0
        document_frequency: Counter[str] = Counter()
        for tokens in self._token_lists:
            document_frequency.update(set(tokens))
        self._document_frequency = document_frequency

    def _get_embedder(self) -> Any:
        if self._embedder is None and self.embedding_backend == "fastembed":
            from fastembed import TextEmbedding

            FASTEMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self._embedder = TextEmbedding(
                model_name=EMBEDDING_MODEL,
                cache_dir=str(FASTEMBED_CACHE_DIR),
                threads=EMBEDDING_THREADS,
                cuda=False,
            )
        return self._embedder

    def _build_document_vectors(self) -> np.ndarray:
        passages = [f"{card.get('title', '')}. {card['text']}" for card in self.cards]
        if self.embedding_backend == "hash":
            vectors = [_hash_embedding(text) for text in passages]
        elif self.embedding_backend == "fastembed":
            embedder = self._get_embedder()
            vectors = list(embedder.passage_embed(passages))
        else:
            raise ValueError(
                f"Unsupported EMBEDDING_BACKEND={self.embedding_backend!r}; use fastembed or hash."
            )
        matrix = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.maximum(norms, 1e-12)

    def _query_vector(self, query: str) -> np.ndarray:
        if self.embedding_backend == "hash":
            return _hash_embedding(query)
        vector = np.asarray(list(self._get_embedder().query_embed(query))[0], dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm else vector

    def _bm25(self, query_tokens: list[str], indices: list[int]) -> dict[int, float]:
        if not query_tokens:
            return {idx: 0.0 for idx in indices}
        n_docs = max(1, len(self.cards))
        k1, b = 1.5, 0.75
        scores: dict[int, float] = {}
        for idx in indices:
            frequencies = Counter(self._token_lists[idx])
            length = float(self._doc_lengths[idx])
            score = 0.0
            for term in set(query_tokens):
                term_frequency = frequencies.get(term, 0)
                if not term_frequency:
                    continue
                df = self._document_frequency.get(term, 0)
                inverse_document_frequency = math.log(
                    1 + (n_docs - df + 0.5) / (df + 0.5)
                )
                denominator = term_frequency + k1 * (
                    1 - b + b * length / max(self._avg_doc_length, 1.0)
                )
                score += inverse_document_frequency * (
                    term_frequency * (k1 + 1) / denominator
                )
            scores[idx] = score
        return scores

    def search(
        self,
        query: str,
        feature: str = "unknown",
        top_k: int = RETRIEVAL_TOP_K,
        force_broad: bool = False,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        allowed_areas = None if force_broad else AREA_FILTERS.get(feature)
        indices = [
            idx
            for idx, card in enumerate(self.cards)
            if allowed_areas is None or card.get("area") in allowed_areas
        ]
        if not indices:
            return []

        query_vector = self._query_vector(query)
        dense = self._document_vectors[indices] @ query_vector
        query_tokens = tokenize(query)
        lexical = self._bm25(query_tokens, indices)
        dense_order = sorted(range(len(indices)), key=lambda pos: float(dense[pos]), reverse=True)
        lexical_order = sorted(
            range(len(indices)), key=lambda pos: lexical[indices[pos]], reverse=True
        )
        dense_rank = {indices[pos]: rank + 1 for rank, pos in enumerate(dense_order)}
        lexical_rank = {indices[pos]: rank + 1 for rank, pos in enumerate(lexical_order)}

        ranked: list[tuple[float, int, float, float]] = []
        for pos, idx in enumerate(indices):
            dense_score = float(dense[pos])
            lexical_score = float(lexical[idx])
            rrf = 1 / (60 + dense_rank[idx]) + 1 / (60 + lexical_rank[idx])
            ranked.append((rrf, idx, dense_score, lexical_score))
        ranked.sort(key=lambda item: item[0], reverse=True)

        results: list[dict[str, Any]] = []
        for rrf_score, idx, dense_score, lexical_score in ranked[: max(1, top_k)]:
            card = dict(self.cards[idx])
            card.update(
                {
                    "dense_score": round(dense_score, 4),
                    "bm25_score": round(lexical_score, 4),
                    "rank_score": round(rrf_score, 6),
                }
            )
            results.append(card)
        return results
