from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .config import RETRIEVAL_TOP_K
from .retrieval import KnowledgeIndex
from .state import RAGState


HU_EN_QUERY_TERMS = {
    "transzkripció": "transcription",
    "transzkripcio": "transcription",
    "meeting után": "after the meeting",
    "meeting utan": "after the meeting",
    "meeting utáni": "post-meeting",
    "meeting utani": "post-meeting",
    "webináriumon": "in a webinar",
    "webinariumon": "in a webinar",
    "lefordított átirat": "translated transcript",
    "leforditott atirat": "translated transcript",
    "hangfelvétel": "recording audio",
    "hangfelvetel": "recording audio",
    "nem volt bekapcsolva": "was not enabled",
    "támogatott": "supported",
    "tamogatott": "supported",
}


def expand_hungarian_query(query: str) -> str:
    expanded = query
    for source, target in HU_EN_QUERY_TERMS.items():
        expanded = expanded.replace(source, target)
        expanded = expanded.replace(source.title(), target)
    return " ".join(expanded.split())


def build_rag_subgraph(index: KnowledgeIndex):
    def prepare_queries(state: RAGState) -> dict[str, Any]:
        candidates = [state.get("query", "")]
        expanded = expand_hungarian_query(state.get("query", ""))
        if expanded.casefold() != state.get("query", "").casefold():
            candidates.append(expanded)
        candidates.extend(state.get("subqueries", []))
        queries: list[str] = []
        seen: set[str] = set()
        for query in candidates:
            normalized = " ".join(query.split())
            key = normalized.casefold()
            if normalized and key not in seen:
                seen.add(key)
                queries.append(normalized)
        return {"queries": queries[:4]}

    def retrieve_hybrid(state: RAGState) -> dict[str, Any]:
        combined: dict[str, dict[str, Any]] = {}
        for query in state.get("queries", []):
            hits = index.search(
                query=query,
                feature=state.get("feature", "unknown"),
                top_k=max(RETRIEVAL_TOP_K, 5),
                force_broad=state.get("force_broad", False),
            )
            for rank, hit in enumerate(hits, start=1):
                card_id = hit["id"]
                current = combined.get(card_id)
                contribution = 1.0 / (60 + rank)
                if current is None:
                    hit["query_rrf"] = contribution
                    combined[card_id] = hit
                else:
                    current["query_rrf"] += contribution
                    current["dense_score"] = max(
                        current.get("dense_score", 0.0), hit.get("dense_score", 0.0)
                    )
                    current["bm25_score"] = max(
                        current.get("bm25_score", 0.0), hit.get("bm25_score", 0.0)
                    )
        ordered = sorted(
            combined.values(),
            key=lambda item: (item.get("query_rrf", 0.0), item.get("dense_score", 0.0)),
            reverse=True,
        )
        return {"evidence": ordered[:RETRIEVAL_TOP_K]}

    def pack_evidence(state: RAGState) -> dict[str, Any]:
        output: list[dict[str, Any]] = []
        for item in state.get("evidence", []):
            output.append(
                {
                    "id": item["id"],
                    "source_id": item["source_id"],
                    "title": item["title"],
                    "source_url": item["source_url"],
                    "section": item["section"],
                    "area": item["area"],
                    "text": item["text"],
                    "text_hu": item.get("text_hu", ""),
                    "dense_score": item.get("dense_score", 0.0),
                    "rank_score": item.get("query_rrf", item.get("rank_score", 0.0)),
                }
            )
        return {"evidence": output}

    graph = StateGraph(RAGState)
    graph.add_node("prepare_queries", prepare_queries)
    graph.add_node("retrieve_hybrid", retrieve_hybrid)
    graph.add_node("pack_evidence", pack_evidence)
    graph.add_edge(START, "prepare_queries")
    graph.add_edge("prepare_queries", "retrieve_hybrid")
    graph.add_edge("retrieve_hybrid", "pack_evidence")
    graph.add_edge("pack_evidence", END)
    return graph.compile()
