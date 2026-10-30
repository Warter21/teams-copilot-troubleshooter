# Teams Copilot Troubleshooter — Package contents

This guide describes the project files in teams-copilot-troubleshooter-final-2026-10-30-complete.zip.

## Workflow at a glance

app.py receives the question and calls the LangGraph in graph.py. The graph classifies the issue, plans checks, then runs document retrieval and deterministic diagnostics as parallel branches. rag_subgraph.py searches the local knowledge index; tools.py supplies both the retrieval tool and the non-retrieval scenario precheck. The graph combines their results, and llm.py creates or selects the cited response. state.py carries the question and intermediate results between nodes.

## Project and runtime files

| File | Purpose and role |
| --- | --- |
| README.md | Problem rationale, architecture and design choices, model trade-offs, latest test results, and setup/run instructions. Main project documentation. |
| app.py | Streamlit interface: model selector and download control, chat, answer, diagnostic checks, Microsoft sources, and workflow trace. |
| requirements.txt | Python dependencies for the UI, LangGraph workflow, local retrieval, and Ollama client. |
| Dockerfile | Builds the application image and installs the Python dependencies. |
| compose.yaml | Runs Ollama and Streamlit, downloads the selected local model, and persists model, embedding, and report data in volumes. |
| compose.dummy.yaml | Runs deterministic Dummy/hash mode without Ollama or model downloads. |
| .dockerignore and .gitignore | Exclude local development files, caches, and generated files from the appropriate build or Git contexts. |

## Workflow implementation

| File | Purpose and role |
| --- | --- |
| src/teams_copilot_troubleshooter/graph.py | Five-node LangGraph: triage, plan, RAG retrieval, diagnostics, and evidence review/answer. Controls conditional routing, parallel branches, retry, and timings. |
| src/teams_copilot_troubleshooter/rag_subgraph.py | Separate three-step retrieval subgraph: prepare queries, retrieve passages, and merge evidence. |
| src/teams_copilot_troubleshooter/state.py | Typed workflow state for the question, scenario, subtasks, evidence, diagnostics, answer, trace, and timing data. |
| src/teams_copilot_troubleshooter/tools.py | Defines official-document retrieval and meeting_scenario_precheck. The precheck applies deterministic rules and does not inspect a tenant. |
| src/teams_copilot_troubleshooter/llm.py | Generates or selects responses with Ollama or deterministic Dummy mode; checks model availability and supports model downloads. |
| src/teams_copilot_troubleshooter/retrieval.py | Builds the local hybrid retrieval index using multilingual embeddings and keyword scoring. |
| src/teams_copilot_troubleshooter/knowledge.py | Loads source metadata and knowledge cards and prepares them for indexing. |
| src/teams_copilot_troubleshooter/config.py | Central runtime settings for model names, embedding backend, paths, retrieval, token limit, and timeouts. |

## Data and evaluation files

| File | Purpose and role |
| --- | --- |
| data/source_manifest.json | Allowlist of official Microsoft Learn and Support URLs used by the source-refresh process. |
| data/knowledge_cards.jsonl | Curated, source-linked evidence cards used by runtime retrieval. |
| data/knowledge_cards.hu.json | Reviewed Hungarian paraphrases linked to English evidence cards. |
| data/diagnostic_rules.json | Deterministic scenario checks applied to information in the question. |
| evaluation/questions.jsonl | Fifteen English and Hungarian questions with expected sources, cards, and terms. |

## Scripts and reports

| File | Purpose and role |
| --- | --- |
| scripts/smoke_test.py | End-to-end workflow check for answer, evidence, required workflow nodes, and truncation. |
| scripts/run_evaluation.py | Runs the 15-question evaluation and reports retrieval, citation, answer-method, and truncation metrics. |
| scripts/load_test.py | Runs 50–200 sequential measured requests and reports latency, stage timings, throughput, and failures. |
| scripts/refresh_sources.py | Refreshes the allowlisted pages into a local, reviewable snapshot. |
| reports/smoke_results.json | Latest supplied smoke record: passed in 108.29 seconds, complete cited answer, five nodes, no truncation. |
| reports/evaluation_results.json | Latest supplied 15-question result: all retrieval/citation indicators are 100%, zero truncations, 10 deterministic answers, four curated Hungarian answers, and one evidence fallback. |
| reports/load_test_50_requests.json | Final-build 50-request result: 50/50 success, zero truncations, latency percentiles, stage timings, answer methods, and environment metadata. |
| reports/performance_summary.md | Smoke, functional-evaluation, and load-test metrics, bottleneck, and optimization recommendations. |
| reports/knowledge_card_audit.md | Card-by-card audit and manual relevance review of all 15 latest saved answers. |
| reports/final_assessment.md | Requirement-by-requirement final evaluation and verification limits. |
| reports/assignment_compliance_checklist.md | Assignment mapping to package evidence and latest test status. |
| reports/history/load_test_50_requests_2026-10-29_baseline.json | Previous-build 50-request baseline retained for the measured performance comparison. |

The archive contains the local Git repository metadata under .git/ so the source tree can be inspected and versioned after extraction. No hosted Git remote is configured.

## Final test interpretation

The smoke and functional results were generated on the target Ollama + FastEmbed runtime. The smoke took 108.29 seconds and had no truncation. The 15-question evaluation reports 100% expected-source, expected-card, expected-term, and citation-marker metrics; manual relevance review found all saved answers responsive and cited. The result JSON does not include the tested commit hash or total evaluation duration.

The final-build load test completed all 50 measured requests successfully with no truncation. Mean latency was 3.11 seconds, p50 0.28 seconds, p95 12.27 seconds, and maximum 94.89 seconds. Throughput was 0.3216 requests per second. The previous-build baseline is retained under reports/history/ for comparison.
