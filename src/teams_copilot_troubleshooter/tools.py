from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from .config import RULES_PATH


def build_search_tool(rag_subgraph: Any):
    @tool(
        "search_official_docs",
        description=(
            "Search the local index of curated Microsoft Support and Microsoft Learn content. "
            "Returns evidence excerpts with source IDs and links."
        ),
    )
    def search_official_docs(
        query: str,
        feature: str = "unknown",
        subqueries: list[str] | None = None,
        force_broad: bool = False,
    ) -> str:
        result = rag_subgraph.invoke(
            {
                "query": query,
                "feature": feature,
                "subqueries": subqueries or [],
                "force_broad": force_broad,
            }
        )
        return json.dumps(result.get("evidence", []), ensure_ascii=False)

    return search_official_docs


def _meeting_scenario_precheck(
    feature: str,
    meeting_type: str,
    transcript_state: str,
    license_state: str,
    organizer_role: str,
    client_platform: str,
    hosted_by_external_org: str,
    meeting_option: str,
    asks_about_after_meeting: bool,
    asks_about_license: bool,
    asks_about_agenda: bool,
) -> list[dict[str, Any]]:
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    feature_rules = rules.get(feature, {})
    source_ids = feature_rules.get("source_ids", [])
    findings: list[dict[str, Any]] = []

    def add(status: str, message: str, sources: list[str] | None = None) -> None:
        findings.append(
            {
                "status": status,
                "message": message,
                "source_ids": sources or source_ids,
            }
        )

    meeting_type = meeting_type.casefold()
    transcript_state = transcript_state.casefold()
    license_state = license_state.casefold()
    organizer_role = organizer_role.casefold()
    client_platform = client_platform.casefold()
    hosted_by_external_org = hosted_by_external_org.casefold()
    meeting_option = meeting_option.casefold()

    unsupported_types = feature_rules.get("unsupported_meeting_types", [])
    if meeting_type in unsupported_types:
        add(
            "blocker",
            f"The reported meeting type ({meeting_type.replace('_', ' ')}) is documented as unsupported for {feature}.",
        )

    if feature == "interpreter" and meeting_type == "pstn":
        add("blocker", "Interpreter is not supported in PSTN calls.", ["MS-INTERPRETER"])
    elif feature == "interpreter" and meeting_type == "call" and meeting_type != "pstn":
        add(
            "check",
            "For calls, verify that this is a one-to-one Teams-to-Teams VoIP call; PSTN calls are unsupported.",
            ["MS-INTERPRETER"],
        )

    if feature == "meeting_copilot" and hosted_by_external_org == "yes":
        add(
            "blocker",
            "Copilot is documented as unavailable in meetings hosted outside the participant's organization.",
            ["MS-COPILOT-MEETINGS"],
        )

    if feature == "meeting_copilot" and meeting_option == "off":
        add(
            "check",
            "With Allow Copilot set to Off, live Copilot is unavailable and recording/transcription are disabled; meeting-chat Copilot can still be available for chat content only.",
            ["MS-COPILOT-MEETINGS", "MS-COPILOT-ADMIN"],
        )
    elif feature == "recap" and meeting_option == "off":
        add(
            "blocker",
            "The meeting-level Allow Copilot option is Off, so Copilot and recap features are disabled for that meeting.",
            ["MS-MEETING-OPTIONS", "MS-COPILOT-MEETINGS"],
        )

    if feature == "facilitator":
        if asks_about_agenda:
            add(
                "check",
                "Facilitator looks for an agenda in the meeting description or Loop meeting notes. If only the organizer has joined, it cannot read the organizer's copy of the meeting invite; the agenda may become available after a non-organizer joins. It also cannot read encrypted or sensitivity-labeled invite or notes content.",
                ["MS-FACILITATOR"],
            )
        if meeting_type not in unsupported_types:
            if license_state in {"teams_premium", "teams_rooms_pro"}:
                add(
                    "blocker",
                    "The Facilitator guidance lists a Microsoft Copilot license as the requirement; ask an administrator to confirm that license is assigned.",
                )
            elif license_state in {"none", "no", "absent"}:
                add("blocker", "A Microsoft Copilot license is required to add or turn on Facilitator.")
            elif license_state in {"unknown", ""} and asks_about_license:
                add(
                    "check",
                    "A Microsoft Copilot license is required to add or turn on Facilitator. Ask an administrator to confirm that it is assigned.",
                    ["MS-FACILITATOR"],
                )
        if client_platform == "mobile" and organizer_role in {"organizer", "presenter"}:
            add(
                "info",
                "Mobile participants can view live notes, but turning Facilitator on or off requires Teams web or desktop.",
                ["MS-FACILITATOR"],
            )
        if asks_about_after_meeting and transcript_state in {"no", "false", "off"}:
            add(
                "check",
                "Post-meeting prompts to Facilitator require transcription to have been enabled before or during the meeting.",
                ["MS-FACILITATOR"],
            )

    if feature in {"meeting_copilot", "recap"}:
        if feature == "meeting_copilot" and meeting_option == "only_during" and asks_about_after_meeting:
            add(
                "check",
                "Only during the meeting allows live Copilot use without a saved transcript. After the meeting, spoken content requires an available transcript; without one, only meeting chat content is available.",
                ["MS-COPILOT-MEETINGS", "MS-MEETING-OPTIONS"],
            )
        if (
            feature == "recap"
            and meeting_type == "scheduled"
            and transcript_state in {"no", "false", "off"}
            and asks_about_after_meeting
        ):
            add(
                "check",
                "A scheduled meeting can have an intelligent recap without a saved transcript when the feature is enabled and licensing and organization policy allow it. This no-transcription recap path is not supported for instant meetings.",
                ["MS-INTELLIGENT-RECAP-NO-TRANSCRIPT", "MS-MEETING-RECAP-APP"],
            )
        if feature_rules.get("meeting_option_check"):
            if meeting_option == "unknown" and not any(
                item["status"] == "blocker" for item in findings
            ):
                add(
                    "check",
                    "Verify the meeting's Allow Copilot and Facilitator option; an organization policy may set or restrict it.",
                    ["MS-MEETING-OPTIONS", "MS-COPILOT-ADMIN"],
                )
        if feature == "meeting_copilot" and asks_about_after_meeting and transcript_state in {"no", "false", "off"}:
            add(
                "check",
                "Standard Copilot questions about spoken content after a meeting need a transcript. A separate no-transcription intelligent recap path may apply to scheduled meetings, subject to license and policy.",
                ["MS-COPILOT-MEETINGS", "MS-INTELLIGENT-RECAP-NO-TRANSCRIPT"],
            )

    if feature == "interpreter":
        if license_state in {"none", "no", "absent"}:
            add(
                "admin_check",
                "Ask an administrator to verify an eligible Microsoft 365 base license and Teams license, plus a Copilot license. For Teams Rooms devices, verify the Teams Rooms Pro license path instead of the Copilot license. Copilot and Teams Rooms Pro include 20 interpretation hours per user per month; additional access depends on available capacity.",
                ["MS-INTERPRETER-ADMIN"],
            )
        elif license_state in {"unknown", ""} and asks_about_license:
            add(
                "admin_check",
                "Ask an administrator to verify an eligible Microsoft 365 base license and Teams license, plus a Copilot license. For Teams Rooms devices, verify the Teams Rooms Pro license path instead of the Copilot license. Copilot and Teams Rooms Pro include 20 interpretation hours per user per month; additional access depends on available capacity.",
                ["MS-INTERPRETER-ADMIN"],
            )

    if not findings:
        add(
            "check",
            "No known blocker was identified from the supplied details. Confirm the meeting type, feature setting, license, and any transcript requirement using the cited documentation.",
        )
    return findings


@tool(
    "meeting_scenario_precheck",
    description=(
        "Apply a small, auditable rule set to user-provided meeting details. "
        "This does not access or change tenant settings."
    ),
)
def meeting_scenario_precheck(
    feature: str,
    meeting_type: str = "unknown",
    transcript_state: str = "unknown",
    license_state: str = "unknown",
    organizer_role: str = "unknown",
    client_platform: str = "unknown",
    hosted_by_external_org: str = "unknown",
    meeting_option: str = "unknown",
    asks_about_after_meeting: bool = False,
    asks_about_license: bool = False,
    asks_about_agenda: bool = False,
) -> str:
    findings = _meeting_scenario_precheck(
        feature=feature,
        meeting_type=meeting_type,
        transcript_state=transcript_state,
        license_state=license_state,
        organizer_role=organizer_role,
        client_platform=client_platform,
        hosted_by_external_org=hosted_by_external_org,
        meeting_option=meeting_option,
        asks_about_after_meeting=asks_about_after_meeting,
        asks_about_license=asks_about_license,
        asks_about_agenda=asks_about_agenda,
    )
    return json.dumps(findings, ensure_ascii=False)
