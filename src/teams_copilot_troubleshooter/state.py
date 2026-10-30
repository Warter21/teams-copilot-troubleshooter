from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


def merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class AssistantState(TypedDict, total=False):
    query: str
    feature: str
    scenario: dict[str, str]
    classification_reason: str
    subqueries: list[str]
    force_broad: bool
    retry_count: int
    should_retry: bool
    needs_clarification: bool
    clarification: str
    evidence: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]]
    answer: str
    generation_done_reason: str
    generation_truncated: bool
    answer_truncated: bool
    answer_fallback_used: bool
    answer_method: str
    trace: Annotated[list[dict[str, Any]], add]
    timings_ms: Annotated[dict[str, float], merge_dicts]


class RAGState(TypedDict, total=False):
    query: str
    feature: str
    subqueries: list[str]
    force_broad: bool
    queries: list[str]
    evidence: list[dict[str, Any]]
