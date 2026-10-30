# Knowledge-card and answer audit

**Review date:** 2026-10-30  
**Scope:** 18 English knowledge cards, their 18 Hungarian paraphrases, nine official Microsoft pages, and the newest supplied 15-question functional-evaluation JSON generated on 2026-10-30 at 12:41:44 UTC.

## Result

The card set has 18 English cards and 18 Hungarian counterparts, each mapped to one of nine official Microsoft pages. The existing source review found no remaining factual contradiction in the card claims. The reviewed card text clarifies Copilot Off behavior, policy modes, no-transcript recap conditions, Facilitator prerequisites, and Interpreter licensing. The files are data/knowledge_cards.jsonl and data/knowledge_cards.hu.json.

The latest supplied 15-question run reports 100% expected-source, expected-card, expected-term, and citation-marker coverage, with no truncated answers. Manual relevance review of every saved answer found that it addresses the corresponding question and includes a citation. Q01 and Q09 now pass in this full supplied run. Retrieval and citation metrics do not independently establish factual accuracy against live Microsoft documentation.

## Card-by-card review

| Card | Review result | Correction or confirmation |
| --- | --- | --- |
| C01 | Clarified | Distinguishes all three meeting choices, transcription requirements, and chat-only behavior when no transcript is available or the meeting option is Off. |
| C02 | Clarified | States the transcript requirement for spoken content and the chat-only behavior for both `Only during the meeting` without a transcript and `Off`. |
| C03 | Verified | Keeps the documented restriction for meetings hosted outside the participant's organization. |
| C04 | Verified | Correctly describes the meeting option and Facilitator dependency. |
| C05 | Clarified | Lists the four current policy values and explains that `On with saved transcript required` is enforced; the Hungarian version now includes the same policy labels and behavior. |
| C06 | Clarified | States that organizer options and organization policy determine availability, and includes multi-tenant users treated as external. |
| C07 | Clarified | Identifies the scheduled-meeting scope, no-transcription path, Copilot-license requirement for attendees, and the requirement that the meeting end for everyone. |
| C08 | Verified | Correctly distinguishes intelligent, audio, and video recap licensing and access permissions. |
| C09 | Verified | Correctly states the Copilot license and supported meeting-type limits for Facilitator. |
| C10 | Verified | Correctly states the role and web/desktop requirements for toggling Facilitator, and what mobile participants can view. |
| C11 | Verified | Correctly states the transcription prerequisite for post-meeting Facilitator prompts. |
| C12 | Verified | Correctly describes agenda discovery, the organizer-only join case, and protected invite/notes content. |
| C13 | Clarified | Removed duplicate webinar wording and aligned the Hungarian wording for Teams Rooms with the personal-device/peripheral limitation. |
| C14 | Verified | Correctly limits call support to one-to-one Teams-to-Teams VoIP and excludes PSTN calls. |
| C15 | Clarified | Keeps the official output-language list and preserves `Taiwanese` as Microsoft's language label so the Hungarian wording does not imply a vague nationality adjective. |
| C16 | Verified | Correctly states that recordings retain original meeting audio, translated transcripts are live-only, and the post-meeting transcript shows the original spoken language. |
| C17 | Clarified | Makes the Microsoft 365 listening-license requirement and eligible Microsoft 365, Teams, Copilot, and Teams Rooms Pro paths explicit; includes 20 hours per user per month and capacity limits. |
| C18 | Verified | Correctly states the verified-account and license requirement for external participants and the restriction for anonymous/guest users. |

All nine source entries are official Microsoft Support or Microsoft Learn pages. Their `reviewed_on` date is set to 2026-10-30 in `data/source_manifest.json`.

## Review of the latest supplied 15-question answers

| Question | Manual relevance review |
| --- | --- |
| Q01 | Pass: explains that Only during the meeting permits live Copilot without a saved transcript, while post-meeting questions about spoken content require an available transcript. |
| Q02 | Pass: describes the scheduled-meeting recap path without a saved transcript and excludes instant meetings. |
| Q03 | Pass: states that Copilot is unavailable in meetings hosted outside the participant's organization. |
| Q04 | Pass: distinguishes unavailable live Copilot from chat-only Copilot when Allow Copilot is Off. |
| Q05 | Pass: explains transcript requirements and chat-only behavior in Hungarian. |
| Q06 | Pass: identifies channel meetings as unsupported for Facilitator. |
| Q07 | Pass: identifies the mobile toggle limitation and web/desktop requirement. |
| Q08 | Pass: explains the transcript requirement for post-meeting Facilitator prompts. |
| Q09 | Pass: explains why Facilitator may not see the organizer's invite agenda until another participant joins and notes protected invite or notes content. |
| Q10 | Pass: states that a Microsoft Copilot license is required to add or enable Facilitator. |
| Q11 | Pass: states that Interpreter is unsupported in webinars and names related meeting-type limits. |
| Q12 | Pass: states that Interpreter is unsupported in PSTN calls. |
| Q13 | Pass: lists the interpretation output languages and accuracy caveat using an evidence fallback. |
| Q14 | Pass: identifies administrator checks for eligible license paths and monthly capacity. |
| Q15 | Pass: explains that recordings retain original audio and translated transcripts are live-only. |

The latest result contains 10 deterministic diagnostic answers, four curated Hungarian answers, and one evidence fallback. No free-form local-model answer was retained as final output. The Q13 generation finish reason was stop, but the answer presented to the user was the cited evidence fallback. The evaluation timestamp is after the answer-relevance fixes were committed; the JSON does not embed a source commit hash. The canonical raw result is reports/evaluation_results.json.

## Official sources reviewed

| Source ID | Official page |
| --- | --- |
| MS-COPILOT-MEETINGS | [Catch up on meetings with Microsoft Copilot in Teams](https://support.microsoft.com/en-us/teams/copilot/catch-up-on-meetings-with-microsoft-365-copilot-in-teams) |
| MS-MEETING-OPTIONS | [Meeting options in Microsoft Teams](https://support.microsoft.com/en-us/teams/meetings/meeting-options-in-microsoft-teams) |
| MS-COPILOT-ADMIN | [Manage Microsoft Copilot in Teams meetings and events](https://learn.microsoft.com/en-us/microsoftteams/copilot-teams-transcription) |
| MS-COPILOT-NO-TRANSCRIPT | [Use Copilot without transcribing or recording a Teams meeting or call](https://support.microsoft.com/en-us/teams/copilot/use-copilot-without-transcribing-or-recording-a-teams-meeting-or-call) |
| MS-INTELLIGENT-RECAP-NO-TRANSCRIPT | [Use intelligent recap in Teams meetings without transcription](https://support.microsoft.com/en-gb/teams/meetings/use-intelligent-recap-microsoft-teams-meetings-without-transcription) |
| MS-MEETING-RECAP-APP | [Get started with the Meeting Recaps app in Teams](https://support.microsoft.com/en-us/teams/meetings/meeting-recap-app-teams) |
| MS-FACILITATOR | [Facilitator in Microsoft Teams meetings](https://support.microsoft.com/en-us/teams/copilot/facilitator-in-microsoft-teams-meetings) |
| MS-INTERPRETER | [Interpreter in Teams meetings and calls](https://support.microsoft.com/en-us/teams/copilot/interpreter-in-microsoft-teams-meetings-and-calls) |
| MS-INTERPRETER-ADMIN | [Manage Interpreter agent for your organization](https://learn.microsoft.com/en-us/microsoftteams/interpreter-agent-teams) |

## Verification limit

The latest smoke, functional-evaluation, and final-build load-test JSON files are preserved exactly as supplied. They were generated in the target Ollama + FastEmbed environment after the answer-relevance fixes. The result files do not embed the tested source commit hash. This workspace can check package contents and Python syntax, but LangGraph, Docker, and Ollama are not available here for another end-to-end run. The previous-build load-test baseline is retained under reports/history/ for comparison.
