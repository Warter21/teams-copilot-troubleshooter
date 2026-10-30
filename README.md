# Teams Copilot Troubleshooter

A local Agentic RAG prototype for troubleshooting Microsoft Teams meeting Copilot/Recap, Facilitator, and Interpreter. The project uses LangGraph, Streamlit, Ollama, and a local multilingual embedding model. It does not call a paid API or connect to a Microsoft tenant.

## Scope

The assistant helps an employee or first-line support colleague identify likely causes and the next checks. It uses public Microsoft Support and Microsoft Learn documentation plus details provided in the question.

It can explain a documented license, meeting type, transcription, client, or policy prerequisite. It cannot see the user's actual license, assigned policy, device, meeting, or tenant. It does not change administrator settings; it identifies when an administrator should verify them.

The Streamlit interface and project documentation are in English. The answer model is prompted to respond in the language of the question. The evaluation set includes English and Hungarian queries to check cross-language retrieval against the English source notes.

## Problem and rationale

**Problem and objective.** Employees and first-line support colleagues can have difficulty diagnosing why a Teams meeting feature such as Copilot/Recap, Facilitator, or Interpreter is unavailable or behaves differently. The required checks depend on details such as meeting type, transcript availability, meeting options, role, client, and licensing. The objective is to turn a short problem description into a concise set of likely checks, grounded in official Microsoft guidance and clearly identifying when an administrator must verify tenant-specific settings.

**Why the problem is relevant.** These features have several prerequisites and policy-dependent behaviors. When users cannot tell which prerequisite applies, troubleshooting takes longer and support teams may repeat the same checks. A focused assistant can make the first diagnostic step faster and more consistent while keeping the guidance tied to published Microsoft sources.

**User need.** An employee or first-line support colleague needs to describe the symptom in ordinary language, learn which checks apply to the reported scenario, see the supporting Microsoft sources, and know what information or administrator confirmation is still needed. The prototype supports that flow without claiming access to the user's license, policy, device, meeting, or tenant.

**Why agentic RAG fits.** A single symptom can require independent checks for feature eligibility, meeting settings, transcription, and the meeting scenario. The graph identifies the feature, breaks the issue into focused checks, retrieves relevant source passages, runs a deterministic precheck on details supplied in the question, and combines both results into a cited answer. Conditional routing asks for clarification outside the supported scope and retries once if the first search has no evidence. This makes the investigation traceable and lets the retrieval and deterministic checks run as separate workflow branches.

## Architecture

The main LangGraph contains exactly five nodes. The RAG subgraph is a separately compiled graph called by the retrieval node and is not included in that count.

| Main node | Responsibility |
| --- | --- |
| 1. Triage | Identify the feature and extract meeting details from the question. Ask a clarification when the feature is outside the supported scope. |
| 2. Plan | Split the issue into independent eligibility, meeting-setting, transcript, or feature-specific checks. |
| 3. RAG subgraph | Search the local index of official Microsoft sources using multilingual dense retrieval and BM25-style keyword scoring. |
| 4. Diagnostic tool | Apply a small deterministic rule set to the details the user supplied. It does not retrieve documents or inspect a tenant. |
| 5. Evidence review and answer | Combine the search evidence and diagnostic findings, cite source IDs, and either answer, ask for a missing detail, or retry a broad search once. |

The workflow uses two tools: `search_official_docs` retrieves evidence through the RAG subgraph, and `meeting_scenario_precheck` applies auditable rules to user-provided meeting details. The latter is a non-retrieval tool and does not access tenant state.

After planning, the RAG search and diagnostic tool run as independent branches. The graph joins their results before the final answer. Its state carries the original question, feature, scenario fields, subtasks, evidence, diagnostics, retry count, node trace, and timings.

The RAG subgraph has three internal steps:

1. Prepare a small set of search queries from the original question and planned checks.
2. Retrieve candidate source passages with multilingual embeddings and keyword scoring.
3. Merge duplicate hits and return passages with document title, section, URL, and source ID.

### Design decisions

| Decision | Rationale |
| --- | --- |
| Five-node main workflow with a separate RAG subgraph | Keeps triage, planning, evidence retrieval, deterministic diagnostics, and answer review visible as distinct steps while isolating reusable retrieval logic. |
| Parallel retrieval and scenario precheck | Searches official guidance and checks user-provided scenario details independently, then combines both results before answering. The precheck is auditable and does not access tenant state. |
| Curated Microsoft source allowlist and local knowledge cards | Keeps the prototype's evidence bounded, attributable to official pages, and easy to refresh without requiring a large document corpus. |
| Local multilingual embeddings and Ollama models | Supports Hungarian questions against English source notes without a paid API. Qwen3 0.6B is the CPU-oriented choice for the 8 GB target; Dummy mode provides a deterministic, no-download workflow path. |
| Streamlit with Docker Compose | Provides a small UI that exposes the answer and diagnostic evidence, with a repeatable local runtime for Ollama and the application. |

The UI shows the answer, source links, deterministic checks, and the five-node workflow trace. Diagnostic checks, Microsoft sources, and workflow steps appear in collapsed expanders below each answer so the user can inspect how the prototype reached its result without crowding the answer itself. Each response also shows whether it came from the local model, a deterministic diagnostic, curated Hungarian source text, or an extractive fallback.

## Data sources and processing

The initial source allowlist is in data/source_manifest.json. It contains nine official Microsoft Support or Microsoft Learn pages reviewed on 2026-10-30. The bundled English knowledge cards and their 18 Hungarian paraphrases were checked against those pages; see `reports/knowledge_card_audit.md` for the card-by-card review. The corpus contains no tenant or user data.

The local index preserves source and section metadata. Retrieval combines multilingual dense similarity with BM25-style term scoring; this helps match both natural-language questions and product terms such as Facilitator, Recap, or PSTN. The embedding model uses its query- and passage-specific embedding methods.

To refresh from the allowlisted Microsoft pages, run:

    python scripts/refresh_sources.py

The script checks the source hosts, removes navigation and page chrome, groups text by headings, and writes a timestamped local snapshot under data/cache. That snapshot is ignored by Git and is not required to run the bundled knowledge cards. Refreshing requires network access; page changes should be reviewed before relying on a refreshed snapshot.

## Models and local runtime

- The Streamlit sidebar provides three answer-model choices: deterministic Dummy, Qwen3 0.6B, and Qwen3 1.7B. Each answer records which choice produced it.
- Dummy uses deterministic answer formatting and hash embeddings. It needs no Ollama service or model download and is intended for workflow checks; its results are not an LLM quality measurement.
- Qwen3 0.6B through Ollama is the recommended option for the target CPU-only machine with 8 GB RAM and integrated graphics. The Qwen team releases this size under Apache 2.0. Its smaller footprint trades answer quality for local CPU compatibility; the system constrains answers to retrieved evidence and deterministic checks.
- Qwen3 1.7B is available as an experimental choice. A previous run on the target setup exceeded the 300-second response timeout. It is not pulled automatically by Docker Compose. When Ollama is reachable, the sidebar offers a **Download** button for an uninstalled Qwen model and streams its download progress. The terminal commands remain available as a fallback: `ollama pull qwen3:1.7b` locally, or `docker compose exec ollama ollama pull qwen3:1.7b` when using Compose.
- Embeddings: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 through FastEmbed/ONNX Runtime. FastEmbed lists it as a multilingual model with a 384-dimensional output, Apache 2.0 license, and an approximately 0.22 GB download. It is a compact choice for matching Hungarian queries to the English Microsoft documentation in this prototype.
- Hungarian answers use curated Hungarian paraphrases mapped to retrieved English source cards. When a fallback is needed, the matching Hungarian card is selected by query-term relevance, including common inflected forms. This avoids relying on free-form Hungarian generation from the small local model; the cited Microsoft pages remain the authoritative source.
- No paid model or embedding API is used. With either Qwen option, answer generation and embeddings run locally; their model files are downloaded on first use. Dummy mode uses deterministic hash vectors and does not download models.
- The main graph uses deterministic routing and a single answer-generation call when a direct rule-based answer is not available. The local model receives at most three evidence passages and is asked for a direct answer of up to 70 words. Definite diagnostic findings take precedence. A truncated answer, source-list response, missing citation, or malformed citation is replaced with a short cited evidence extract. The UI distinguishes model-draft truncation from the complete fallback shown to the user. The request timeout is 300 seconds; timeout errors identify Ollama explicitly.

The target machine is Debian Linux with 8 GB RAM and integrated graphics. The configuration is intentionally small and sequential. CPU inference may be slow; use the load-test report from that target machine for representative latency.

Model references: [Qwen3 0.6B in Ollama](https://ollama.com/library/qwen3:0.6b), [Qwen3 model family and Apache 2.0 license](https://qwenlm.github.io/blog/qwen3/), and [multilingual MiniLM model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).

## Run locally

Requirements: Python 3.11+, Ollama, and enough disk space for the model and local caches.

1. Start the Ollama service if it is not already running.
2. Download the answer model:

       ollama pull qwen3:0.6b

3. Install and start the application:

       python3 -m venv .venv
       . .venv/bin/activate
       python -m pip install -r requirements.txt
       export PYTHONPATH=src
       streamlit run app.py

Open http://localhost:8501. The embedding model is downloaded on first use and cached locally.

Run one end-to-end functional smoke check before the longer evaluation or load test:

    docker compose run --rm app python scripts/smoke_test.py --backend ollama --embedding-backend fastembed

The smoke script sends one question through the workflow and has no separate overall runtime limit. A single Ollama answer request is limited to 300 seconds by OLLAMA_TIMEOUT_SECONDS; model startup and first-use embedding downloads can add time before the answer is produced.

The final supplied smoke result passed with Qwen3 0.6B + FastEmbed in 108.29 seconds. It returned a complete 282-character answer ending in citation [S1], included five evidence items and one diagnostic, and reached all five main workflow nodes. The Ollama finish reason was stop; neither the generated draft nor final answer was marked truncated. The final response method was evidence fallback. This smoke run verifies end-to-end behavior; performance conclusions use the separate 50-request final-build load test.

The Qwen3 1.7B option exceeded the 300-second response timeout on the target CPU. Use the 0.6B model or Dummy mode for a quick workflow check. A container shown as created has not started the smoke script yet. In the default Compose setup, the app waits for the model-pull service to finish successfully; check docker compose ps -a and docker compose logs -f ollama model-pull while the initial model is being downloaded. If the model-pull service has completed but the one-off app container remains created, inspect its state and error with docker inspect --format '{{.State.Status}} {{.State.Error}}' <container-name>.

## Run with Docker Compose

The compose file starts Ollama and Streamlit, pulls the selected local model, and keeps model and embedding caches in named volumes:

    docker compose up --build

Open http://localhost:8501. The first startup downloads the model and embedding files. On an 8 GB host, allow some time for first initialization and keep other memory-heavy applications closed.

The Dockerfile is also provided for building the Streamlit application image separately.

If the local model remains too slow, start the offline dummy configuration without Ollama:

    docker compose -f compose.dummy.yaml up --build -d

The dummy UI is available at http://localhost:8502. This path still exercises the LangGraph workflow, local knowledge retrieval, deterministic diagnostic tool, citations, and UI; only LLM answer generation and learned embeddings are replaced by deterministic mock/hash implementations.

Run the same smoke check with dummy/hash mode:

    docker compose -f compose.dummy.yaml run --rm app-dummy python scripts/smoke_test.py --backend mock --embedding-backend hash

## Functional evaluation

The 15-question evaluation set is in evaluation/questions.jsonl. It covers meeting Copilot/Recap, Facilitator, and Interpreter, including English and Hungarian queries. The evaluator reports:

- source hit rate at K: whether at least one expected source was retrieved;
- expected knowledge-card hit rate at K;
- expected-term hit rate in retrieved evidence;
- citation presence in the final answer;
- Ollama finish reason and whether the answer reached the configured output-token limit.

The latest supplied 15-question run used Qwen3 0.6B + FastEmbed and was generated at 2026-10-30 12:41:44 UTC. It reported 15/15 expected-source hits at K=5, 15/15 expected-card hits, 15/15 expected-term hits in retrieved evidence, and 15/15 answers with a citation marker. No generated draft or final answer was marked truncated. The final-answer methods were 10 deterministic diagnostics, four curated Hungarian responses, and one evidence fallback. No free-form local-model answer was retained in the final output. The result file does not record total evaluation duration, so it cannot support a speed comparison.

Manual relevance review of the 15 saved answers found that each addressed its question and included a citation. In particular, Q01 explains the post-meeting effect of Only during the meeting, and Q09 explains why Facilitator may not find an agenda until another participant joins. The evaluation was generated after these answer-relevance fixes were committed. The JSON does not contain a source commit hash, so it does not independently pin the tested source revision. Retrieval and citation metrics measure evidence coverage and citation presence; the manual review checks relevance, not independent factual correctness against live Microsoft pages. See reports/evaluation_results.json, reports/knowledge_card_audit.md, and reports/final_assessment.md. New runs are written under reports/generated/.

Run the evaluation against the local models:

    python scripts/run_evaluation.py --backend ollama --embedding-backend fastembed

When using Compose, run the same evaluation in a one-off application container:

    docker compose run --rm app python scripts/run_evaluation.py --backend ollama --embedding-backend fastembed

For an offline orchestration smoke run, use the deterministic mock answerer and hash embedding:

    python scripts/run_evaluation.py --backend mock --embedding-backend hash

The mock run checks graph flow and the measurement scripts only. It is not an LLM or embedding quality result.

## Load scenario and performance report

The load runner accepts 50–200 sequential measured requests, cycles through the evaluation questions, and reports mean, p50, p95, and maximum latency, throughput, errors, and mean latency for each graph stage. One warm-up request is run by default and reported separately from measured latency. It also identifies the slowest measured stage.

Run 50 end-to-end requests on the target Debian machine:

    python scripts/load_test.py --requests 50 --backend ollama --embedding-backend fastembed

With Compose:

    docker compose run --rm app python scripts/load_test.py --requests 50 --backend ollama --embedding-backend fastembed

For the dummy/hash baseline:

    docker compose -f compose.dummy.yaml run --rm app-dummy python scripts/run_evaluation.py --backend mock --embedding-backend hash
    docker compose -f compose.dummy.yaml run --rm app-dummy python scripts/load_test.py --requests 50 --backend mock --embedding-backend hash

Run a quick orchestration-only baseline:

    python scripts/load_test.py --requests 50 --backend mock --embedding-backend hash

Generated JSON reports are written to `reports/generated/`. Always report the backend, model, machine, request count, and concurrency with the numbers. The mock baseline excludes local model and embedding inference and must not be presented as end-to-end performance.

The final-build 50-request end-to-end run (Ollama Qwen3 0.6B + FastEmbed, concurrency 1, plus one separately reported warm-up request) was generated on 2026-10-30. It completed all 50 measured requests without failures or truncation. Mean latency was 3.11 s, p50 0.28 s, p95 12.27 s, and maximum 94.89 s. The measured requests took 155.46 s in total, with throughput of 0.3216 requests/s. Mean answer-stage time was 2.80 s, compared with 0.29 s for RAG and 0.007 s for diagnostics. Of the 50 final answers, 34 were deterministic diagnostics, 13 curated Hungarian answers, and three evidence fallbacks.

Compared with the previous-build baseline, mean latency fell by 97.4%, p50 by 99.7%, p95 by 93.9%, and wall time by 97.4%; throughput increased by 37.8 times. Answer generation remains the slowest mean stage and the 94.89-second maximum shows that model-backed fallback requests can still be outliers. Raw final-build results are in reports/load_test_50_requests.json; the previous baseline is retained under reports/history/.

The measured optimization was to keep deterministic or curated answers for supported, well-defined scenarios and reserve model-backed fallback for unresolved questions. This preserved the successful functional-evaluation result while reducing mean load-test latency by 97.4%. A next optimization would target the remaining fallback outliers through response caching, tighter fallback evidence, or an explicit timeout with a complete extractive response. Streaming can improve perceived wait time but does not reduce total inference time.

### Bottleneck and optimization approach

Answer generation accounts for approximately 90.2% of mean final-build latency and remains the main measured bottleneck. The low 0.28-second median reflects the deterministic and curated paths, while the 12.27-second p95 and 94.89-second maximum expose the smaller set of model-backed fallback requests. Future optimization should therefore focus on fallback generation rather than retrieval or orchestration.

## Limitations

- Microsoft documentation changes; the bundled cards represent a reviewed snapshot and include source links for verification.
- The deterministic precheck only evaluates fields it can extract from the user's question. Unknown license or policy state is routed to an administrator.
- This is a prototype, not a tenant-connected support service. It does not access meeting transcripts, calendars, Teams settings, or user identities.
- Evaluation keyword and citation metrics are reproducible indicators, not a substitute for human review of answer correctness.
- The supplied final Ollama smoke and 15-question evaluation passed and are included as raw JSON. In this packaging workspace, Python compilation and JSON consistency checks were run; the local LangGraph, Streamlit, FastEmbed, Docker, and Ollama runtime is unavailable for another end-to-end execution.
