from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from .config import EMBEDDING_BACKEND, LLM_BACKEND, MAX_CONTEXT_CHARS, MODEL_NAME
from .llm import LocalAnswerModel, is_source_list_answer
from .rag_subgraph import build_rag_subgraph
from .retrieval import KnowledgeIndex
from .state import AssistantState
from .tools import build_search_tool, meeting_scenario_precheck


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _detect_feature(query: str) -> tuple[str, str]:
    text = query.casefold()
    if _has_any(text, ("interpreter", "interpretation", "tolmács", "tolmacs", "tolmácsol", "fordított beszéd")):
        return "interpreter", "Interpreter-related term found."
    if "facilitator" in text:
        return "facilitator", "Facilitator named explicitly."
    if _has_any(
        text,
        ("recap", "meeting summary", "meeting recap", "after the meeting", "meeting utáni", "összefoglaló", "recap tab"),
    ):
        return "recap", "A recap or post-meeting summary was requested."
    if _has_any(text, ("copilot", "transcription", "transcript", "meeting", "teams-meeting", "teams meeting")):
        return "meeting_copilot", "Teams meeting Copilot-related term found."
    return "unknown", "The question does not identify one of the supported feature areas."


def _detect_scenario(query: str, feature: str) -> dict[str, str]:
    text = query.casefold()
    meeting_type = "unknown"
    if _has_any(text, ("pstn", "public switched telephone", "phone network")):
        meeting_type = "pstn"
    elif _has_any(text, ("teams rooms", "teams room")) and _has_any(text, ("personal device", "personal devices")):
        meeting_type = "teams_rooms_personal_device"
    elif _has_any(text, ("town hall", "townhall")):
        meeting_type = "town_hall"
    elif _has_any(text, ("webinar", "webinárium", "webinarium")):
        meeting_type = "webinar"
    elif _has_any(text, ("teams free", "free teams")):
        meeting_type = "teams_free"
    elif _has_any(
        text,
        ("channel meeting", "channel-meeting", "csatorna meeting", "csatornaértekezlet"),
    ):
        meeting_type = "channel"
    elif _has_any(text, ("instant meeting", "ad-hoc meeting", "ad hoc meeting", "meet now", "azonnali meeting")):
        meeting_type = "instant" if feature == "facilitator" else "adhoc"
    elif _has_any(text, ("scheduled meeting", "scheduled teams meeting")):
        meeting_type = "scheduled"
    elif _has_any(text, ("one-to-one call", "1:1 call", "teams call", "in a call")):
        meeting_type = "call"

    transcript_state = "unknown"
    if _has_any(
        text,
        (
            "no transcript",
            "without a transcript",
            "without transcription",
            "transcription is off",
            "transcription was off",
            "transcription is disabled",
            "transcription was disabled",
            "not transcribed",
            "nobody saved a transcript",
            "no saved transcript",
            "transcript was not saved",
            "transcript wasn't saved",
            "only chat content",
            "only the chat",
            "nem volt bekapcsolva a transzkripció",
            "nem volt bekapcsolva a transzkripcio",
            "nem volt transzkripció",
            "nem volt transzkripcio",
            "csak a chat tartalmát",
            "csak a chat tartalmat",
            "csak az értekezlet csevegését",
            "csak az ertekezlet csevegeset",
        ),
    ):
        transcript_state = "no"
    elif _has_any(text, ("transcript is available", "transcription is on", "transcription was on", "transcript exists", "recorded and transcribed")):
        transcript_state = "yes"

    license_state = "unknown"
    if _has_any(
        text,
        (
            "no copilot license",
            "without a copilot license",
            "don't have a copilot license",
            "do not have a copilot license",
            "not assigned a copilot license",
            "unlicensed",
            "no license",
        ),
    ):
        license_state = "none"
    elif _has_any(text, ("teams rooms pro", "rooms pro license")):
        license_state = "teams_rooms_pro"
    elif "teams premium" in text:
        license_state = "teams_premium"
    elif _has_any(
        text,
        (
            "licensed for copilot",
            "has a copilot license",
            "have a copilot license",
            "copilot license is assigned",
            "assigned a copilot license",
        ),
    ):
        license_state = "copilot"

    role = "unknown"
    if "organizer" in text:
        role = "organizer"
    elif "presenter" in text:
        role = "presenter"
    elif _has_any(text, ("attendee", "participant")):
        role = "participant"

    platform = "unknown"
    if _has_any(text, ("mobile", "iphone", "ipad", "android", "phone app")):
        platform = "mobile"
    elif "web" in text or "browser" in text:
        platform = "web"
    elif _has_any(text, ("desktop", "windows app", "mac app")):
        platform = "desktop"

    external_host = "yes" if _has_any(
        text,
        (
            "hosted outside my organization",
            "hosted outside the organization",
            "hosted by another organization",
            "hosted by another org",
            "hosted by an external organization",
            "hosted by another company",
            "hosted by a different organization",
            "external organization hosted",
        ),
    ) else "unknown"
    meeting_option = "unknown"
    if _has_any(text, ("allow copilot is off", "allow copilot set to off", "meeting option is off", "copilot option is off")):
        meeting_option = "off"
    elif "only during the meeting" in text:
        meeting_option = "only_during"
    elif "during and after the meeting" in text:
        meeting_option = "during_and_after"
    asks_after = _has_any(
        text,
        (
            "after the meeting",
            "after a meeting",
            "after a teams meeting",
            "after teams meeting",
            "after the teams meeting",
            "after the meeting ends",
            "when the meeting ends",
            "when a teams meeting ends",
            "meeting has ended",
            "post-meeting",
            "afterwards",
            "recap",
            "meeting utáni",
            "meeting után",
            "értekezlet után",
        ),
    )
    asks_about_license = _has_any(
        text,
        ("license", "licence", "licensing", "licenc", "licencelés", "licenceles", "jogosultság", "jogosultsag"),
    )
    asks_about_agenda = _has_any(text, ("agenda", "napirend"))
    return {
        "meeting_type": meeting_type,
        "transcript_state": transcript_state,
        "license_state": license_state,
        "organizer_role": role,
        "client_platform": platform,
        "hosted_by_external_org": external_host,
        "meeting_option": meeting_option,
        "asks_about_after_meeting": "true" if asks_after else "false",
        "asks_about_license": "true" if asks_about_license else "false",
        "asks_about_agenda": "true" if asks_about_agenda else "false",
    }


SUBTASKS = {
    "meeting_copilot": [
        "Check the meeting's Allow Copilot mode, transcription behavior, and organization policy.",
        "Check whether the question concerns a meeting hosted by another organization or access after the meeting.",
    ],
    "recap": [
        "Check recap access, meeting transcript availability, and the scheduled-meeting no-transcription recap path.",
        "Check relevant license and organization policy prerequisites.",
    ],
    "facilitator": [
        "Check supported meeting type, Copilot license, and who can toggle Facilitator.",
        "Check transcription and agenda behavior when the issue occurs after the meeting or with meeting notes.",
    ],
    "interpreter": [
        "Check supported meeting or call type, languages, and interpretation limitations.",
        "Check license and account eligibility requirements that may need administrator confirmation.",
    ],
}


def _is_hungarian_query(query: str) -> bool:
    text = query.casefold()
    if any(char in text for char in "áéíóöőúüű"):
        return True
    return _has_any(
        text,
        ("miert", "miért", "melyik", "milyen", "tudom", "támogatott", "tamogatott", "licenc"),
    )


def _citation_suffix(evidence: list[dict[str, Any]], source_ids: set[str] | None = None) -> str:
    citations = [
        item.get("citation_id", "")
        for item in evidence
        if not source_ids or item.get("source_id") in source_ids
    ]
    citations = [citation for citation in citations if citation]
    if not citations and evidence:
        citations = [evidence[0].get("citation_id", "")]
    return " ".join(f"[{citation}]" for citation in citations[:2] if citation)


def _decisive_diagnostic_answer(
    diagnostics: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    asks_about_license: bool,
) -> str | None:
    specific_checks = (
        "a microsoft copilot license is required",
        "with allow copilot set to off",
        "only during the meeting allows",
        "post-meeting prompts to facilitator require",
        "a scheduled meeting can have an intelligent recap",
        "standard copilot questions about spoken content",
        "facilitator looks for an agenda",
    )
    selected = next(
        (
            item
            for item in diagnostics
            if item.get("status") in {"blocker", "info"}
            or any(str(item.get("message", "")).casefold().startswith(prefix) for prefix in specific_checks)
            or (asks_about_license and item.get("status") == "admin_check")
        ),
        None,
    )
    if not selected:
        return None
    sources = set(selected.get("source_ids", []))
    citation = _citation_suffix(evidence, sources)
    return f"{selected.get('message', '').strip()} {citation}".strip()


_HUNGARIAN_STOPWORDS = {
    "az", "egy", "és", "hogy", "miért", "mikor", "melyik", "milyen", "csak",
    "nem", "van", "volt", "lehet", "benne", "tudom", "funkció", "funkciót",
    "kérdezni", "kérdezhetek", "teams", "meeting", "interpreter",
}


def _common_prefix_length(left: str, right: str) -> int:
    length = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        length += 1
    return length


def _hungarian_card_relevance(query: str, item: dict[str, Any]) -> int:
    """Rank curated Hungarian cards by query-term overlap, including inflections."""
    query_terms = re.findall(r"[^\W\d_]+", query.casefold())
    card_text = " ".join(
        str(item.get(field, ""))
        for field in ("title", "section", "text", "text_hu")
    ).casefold()
    card_terms = re.findall(r"[^\W\d_]+", card_text)
    score = 0
    for term in set(query_terms):
        if len(term) < 4 or term in _HUNGARIAN_STOPWORDS:
            continue
        if term in card_text:
            score += 2
            continue
        if any(
            min(len(term), len(card_term)) >= 4
            and _common_prefix_length(term, card_term) >= 4
            for card_term in card_terms
        ):
            score += 1
    if (
        item.get("id") == "C02"
        and "chat" in query_terms
        and any(term in query_terms for term in ("után", "utólag"))
        and any(term.startswith("elhangzott") for term in query_terms)
    ):
        score += 4
    return score


def _evidence_fallback_answer(
    evidence: list[dict[str, Any]],
    query: str,
) -> tuple[str, str]:
    if _is_hungarian_query(query):
        curated = [candidate for candidate in evidence if candidate.get("text_hu")]
        if curated:
            item = max(
                enumerate(curated),
                key=lambda pair: (_hungarian_card_relevance(query, pair[1]), -pair[0]),
            )[1]
            return f"{item['text_hu']} {_citation_suffix([item])}", "curated_hungarian"
        item = evidence[0]
        text = str(item.get("text", "")).strip()
        prefix = "Nem sikerült megbízható magyar választ előállítani. Az elérhető Microsoft-forrás angolul: "
        return f"{prefix}{text} {_citation_suffix([item])}", "english_evidence_fallback"

    item = evidence[0]
    text = str(item.get("text", "")).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    snippet = " ".join(sentences[:2]).strip() or text
    return f"{snippet} {_citation_suffix([item])}".strip(), "evidence_fallback"


def build_main_graph(
    index: KnowledgeIndex,
    llm_backend: str | None = None,
    model_name: str | None = None,
):
    rag_subgraph = build_rag_subgraph(index)
    search_tool = build_search_tool(rag_subgraph)
    answer_model = LocalAnswerModel(backend=llm_backend, model_name=model_name)

    def triage(state: AssistantState) -> dict[str, Any]:
        started = time.perf_counter()
        query = state.get("query", "").strip()
        feature, reason = _detect_feature(query)
        scenario = _detect_scenario(query, feature)
        clarification = ""
        if feature == "unknown":
            clarification = (
                "I can help with meeting Copilot/Recap, Facilitator, or Interpreter. "
                "Which of these features is missing or not working?"
            )
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "feature": feature,
            "classification_reason": reason,
            "scenario": scenario,
            "needs_clarification": bool(clarification),
            "clarification": clarification,
            "trace": [
                {
                    "node": "1. Triage",
                    "status": "clarification_needed" if clarification else "complete",
                    "detail": f"Feature={feature}; {reason}",
                    "elapsed_ms": elapsed,
                }
            ],
            "timings_ms": {"triage": elapsed},
        }

    def plan(state: AssistantState) -> dict[str, Any]:
        started = time.perf_counter()
        feature = state.get("feature", "unknown")
        subqueries = list(SUBTASKS.get(feature, []))
        scenario = state.get("scenario", {})
        if (
            feature == "facilitator"
            and scenario.get("transcript_state") == "no"
            and scenario.get("asks_about_after_meeting") == "true"
        ):
            subqueries.insert(
                0,
                "Facilitator post-meeting prompts require transcription before or during the meeting.",
            )
        if feature == "interpreter" and scenario.get("meeting_type") not in {"unknown", ""}:
            subqueries.insert(
                0,
                f"Interpreter support for {scenario['meeting_type'].replace('_', ' ')} meetings or calls.",
            )
        if state.get("force_broad"):
            subqueries = [
                f"Microsoft Teams {feature.replace('_', ' ')} availability and troubleshooting",
                *subqueries,
            ]
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "subqueries": subqueries,
            "trace": [
                {
                    "node": "2. Plan",
                    "status": "complete",
                    "detail": f"Split the issue into {len(subqueries)} checks for {feature}.",
                    "elapsed_ms": elapsed,
                }
            ],
            "timings_ms": {"plan": elapsed},
        }

    def retrieve(state: AssistantState) -> dict[str, Any]:
        started = time.perf_counter()
        raw = search_tool.invoke(
            {
                "query": state.get("query", ""),
                "feature": state.get("feature", "unknown"),
                "subqueries": state.get("subqueries", []),
                "force_broad": state.get("force_broad", False),
            }
        )
        evidence = json.loads(raw) if isinstance(raw, str) else raw
        evidence = evidence or []
        for number, item in enumerate(evidence, start=1):
            item["citation_id"] = f"S{number}"
            item["text"] = item.get("text", "")[:MAX_CONTEXT_CHARS]
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        detail = f"Retrieved {len(evidence)} evidence chunks from the local official-doc index."
        return {
            "evidence": evidence,
            "trace": [
                {
                    "node": "3. RAG subgraph",
                    "status": "complete" if evidence else "no_evidence",
                    "detail": detail,
                    "elapsed_ms": elapsed,
                }
            ],
            "timings_ms": {"rag": elapsed},
        }

    def diagnose(state: AssistantState) -> dict[str, Any]:
        started = time.perf_counter()
        scenario = state.get("scenario", {})
        raw = meeting_scenario_precheck.invoke(
            {
                "feature": state.get("feature", "unknown"),
                "meeting_type": scenario.get("meeting_type", "unknown"),
                "transcript_state": scenario.get("transcript_state", "unknown"),
                "license_state": scenario.get("license_state", "unknown"),
                "organizer_role": scenario.get("organizer_role", "unknown"),
                "client_platform": scenario.get("client_platform", "unknown"),
                "hosted_by_external_org": scenario.get("hosted_by_external_org", "unknown"),
                "meeting_option": scenario.get("meeting_option", "unknown"),
                "asks_about_after_meeting": scenario.get("asks_about_after_meeting") == "true",
                "asks_about_license": scenario.get("asks_about_license") == "true",
                "asks_about_agenda": scenario.get("asks_about_agenda") == "true",
            }
        )
        diagnostics = json.loads(raw) if isinstance(raw, str) else raw
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "diagnostics": diagnostics,
            "trace": [
                {
                    "node": "4. Diagnostic tool",
                    "status": "complete",
                    "detail": f"Applied deterministic prechecks; returned {len(diagnostics)} findings.",
                    "elapsed_ms": elapsed,
                }
            ],
            "timings_ms": {"diagnostic": elapsed},
        }

    def review_and_answer(state: AssistantState) -> dict[str, Any]:
        started = time.perf_counter()
        generation_done_reason = "not_applicable"
        generation_truncated = False
        answer_truncated = False
        answer_fallback_used = False
        answer_method = ""
        if state.get("needs_clarification"):
            answer = state.get("clarification", "Please identify the Teams feature.")
            status = "clarification"
            answer_method = "clarification"
            should_retry = False
        elif not state.get("evidence"):
            retries = state.get("retry_count", 0)
            if retries < 1:
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                return {
                    "should_retry": True,
                    "retry_count": retries + 1,
                    "force_broad": True,
                    "trace": [
                        {
                            "node": "5. Evidence review and answer",
                            "status": "retry",
                            "detail": "No evidence was found in the feature-filtered search; retrying once across the full corpus.",
                            "elapsed_ms": elapsed,
                        }
                    ],
                    "timings_ms": {"answer": elapsed},
                }
            answer = (
                "I could not find supporting material in the local Microsoft documentation set. "
                "Please add more detail or verify the issue directly with your Teams administrator."
            )
            status = "no_evidence"
            answer_method = "no_evidence"
            should_retry = False
        else:
            query = state.get("query", "")
            evidence = state.get("evidence", [])
            diagnostics = state.get("diagnostics", [])
            scenario = state.get("scenario", {})
            diagnostic_answer = _decisive_diagnostic_answer(
                diagnostics,
                evidence,
                asks_about_license=scenario.get("asks_about_license") == "true",
            )
            if _is_hungarian_query(query):
                answer, answer_method = _evidence_fallback_answer(evidence, query)
            elif diagnostic_answer:
                answer = diagnostic_answer
                answer_method = "deterministic_diagnostic"
            else:
                answer = answer_model.answer(
                    question=query,
                    evidence=evidence,
                    diagnostics=diagnostics,
                )
                generation_done_reason = answer_model.last_done_reason
                generation_truncated = generation_done_reason in {"length", "max_tokens"}
                valid_citations = {f"S{index}" for index, _ in enumerate(evidence, start=1)}
                citation_ids = re.findall(r"\[(S\d+)\]", answer)
                invalid_citation = any(item not in valid_citations for item in citation_ids)
                invalid_format = (
                    is_source_list_answer(answer)
                    or len(answer) > 900
                    or len(answer.split()) > 100
                    or len(answer.splitlines()) > 5
                    or not citation_ids
                    or invalid_citation
                )
                if generation_truncated or invalid_format:
                    answer, answer_method = _evidence_fallback_answer(evidence, query)
                    answer_fallback_used = True
                else:
                    answer_method = "local_model" if answer_model.backend == "ollama" else "dummy"
            status = "complete"
            should_retry = False

        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {
            "answer": answer,
            "generation_done_reason": generation_done_reason,
            "generation_truncated": generation_truncated,
            "answer_truncated": answer_truncated,
            "answer_fallback_used": answer_fallback_used,
            "answer_method": answer_method,
            "should_retry": should_retry,
            "trace": [
                {
                    "node": "5. Evidence review and answer",
                    "status": status,
                    "detail": (
                        f"Response method={answer_method}; finish={generation_done_reason}; "
                        f"fallback_used={answer_fallback_used}."
                    ),
                    "elapsed_ms": elapsed,
                }
            ],
            "timings_ms": {"answer": elapsed},
        }

    def route_after_triage(state: AssistantState) -> str:
        return "review_and_answer" if state.get("needs_clarification") else "plan"

    def route_after_answer(state: AssistantState) -> str:
        return "plan" if state.get("should_retry") else END

    graph = StateGraph(AssistantState)
    graph.add_node("triage", triage)
    graph.add_node("plan", plan)
    graph.add_node("rag_search", retrieve)
    graph.add_node("diagnose", diagnose)
    graph.add_node("review_and_answer", review_and_answer)

    graph.add_edge(START, "triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"plan": "plan", "review_and_answer": "review_and_answer"},
    )
    graph.add_edge("plan", "rag_search")
    graph.add_edge("plan", "diagnose")
    graph.add_edge(["rag_search", "diagnose"], "review_and_answer")
    graph.add_conditional_edges(
        "review_and_answer",
        route_after_answer,
        {"plan": "plan", END: END},
    )
    return graph.compile()


@lru_cache(maxsize=2)
def _get_index(embedding_backend: str):
    return KnowledgeIndex(embedding_backend=embedding_backend)


@lru_cache(maxsize=6)
def _get_cached_assistant(
    embedding_backend: str,
    llm_backend: str,
    model_name: str,
):
    return build_main_graph(
        _get_index(embedding_backend),
        llm_backend=llm_backend,
        model_name=model_name,
    )


def get_assistant(
    embedding_backend: str | None = None,
    llm_backend: str | None = None,
    model_name: str | None = None,
):
    return _get_cached_assistant(
        (embedding_backend or EMBEDDING_BACKEND).strip().lower(),
        (llm_backend or LLM_BACKEND).strip().lower(),
        model_name or MODEL_NAME,
    )


def ask(
    question: str,
    embedding_backend: str | None = None,
    llm_backend: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    graph = get_assistant(embedding_backend, llm_backend, model_name)
    result = graph.invoke(
        {
            "query": question,
            "retry_count": 0,
            "force_broad": False,
            "trace": [],
            "timings_ms": {},
        }
    )
    return result
