# Final evaluation — Teams Copilot Troubleshooter

Assessment date: 2026-10-30  
Scope: Check the package against the attached Senior AI Engineer assignment, using the latest supplied smoke and 15-question functional-evaluation records.

## Assessment summary

The package contains the required project categories: a Python/LangGraph prototype with exactly five main workflow nodes, a separate RAG subgraph, two tools including a deterministic non-retrieval diagnostic, a Streamlit UI, local answer-model choices, a Dockerfile and Compose configurations, a 15-question evaluation, a 50-request load-test record, and a README with setup instructions and test summaries.

The latest supplied smoke test passed in 108.29 seconds with a complete cited answer and no truncation. The latest 15-question evaluation reports 100% expected-source, expected-card, expected-term, and citation-marker coverage, with zero truncated answers. Manual relevance review of all saved answers found all 15 on-topic; Q01 and Q09 now return relevant answers in the full supplied evaluation. These metrics do not constitute an independent factual-accuracy review of every answer.

The final-build 50-request load test completed 50/50 successfully with no truncation. Mean latency was 3.11 seconds, p50 was 0.28 seconds, p95 was 12.27 seconds, and throughput was 0.3216 requests per second. Compared with the previous-build baseline, mean latency fell by 97.4% and throughput increased 37.8 times. Answer generation remains the dominant mean bottleneck, and the 94.89-second maximum exposes a remaining fallback outlier.

## Assignment requirement mapping

| Requirement | Package evidence | Assessment |
| --- | --- | --- |
| Choose a real problem and explain relevance, user need, and why Agentic RAG fits | README.md, Problem and rationale | Complete |
| Use LangGraph with at least five main workflow nodes | src/teams_copilot_troubleshooter/graph.py | Exactly five main nodes |
| Include conditional routing, decomposition, independent work, and intermediate state | graph.py and state.py | Implemented |
| Integrate at least two tools, including a non-retrieval tool | tools.py | Official-document retrieval plus deterministic scenario precheck |
| Keep RAG in a modular subgraph | rag_subgraph.py | Present and called by the main workflow |
| Use a text data source and provide a scalable integration path | Nine official Microsoft source entries, 18 knowledge cards, refresh_sources.py | Present for prototype scope |
| Avoid paid APIs and explain local-model trade-offs | Ollama Qwen3 0.6B/1.7B and deterministic Dummy mode; README.md | Complete; the 1.7B option exceeded the 300-second timeout on the target CPU |
| Provide a Streamlit prototype UI | app.py | Includes model selection/download, answer, diagnostics, sources, and workflow trace |
| Containerize the runtime and provide a Dockerfile | Dockerfile, compose.yaml, compose.dummy.yaml | Present |
| Evaluate 10–20 questions | evaluation/questions.jsonl and reports/evaluation_results.json | 15 questions; latest retrieval/citation metrics 100%; no truncation; all answers manually reviewed for relevance |
| Run a 50–200 request load scenario and report latency, bottleneck, and optimizations | scripts/load_test.py, reports/load_test_50_requests.json, reports/performance_summary.md | Final-build 50-request result included with percentiles, throughput, stage timings, baseline comparison, bottleneck, and measured optimization impact |
| Provide README with problem, architecture, decisions, results, and run instructions | README.md | Complete and updated |
| Deliver source code in a Git repository | Project tree and .git metadata in the archive | Local Git repository included; no hosted remote is configured |

## Latest test evidence

- Smoke: Passed in 108.29 seconds with Qwen3 0.6B + FastEmbed. It returned a complete 282-character answer, five evidence items, one diagnostic, all five main workflow nodes, and citation [S1]. Both truncation flags were false. The final response method was evidence fallback.
- Smoke interpretation: the 108.29-second run verifies complete end-to-end behavior. Performance conclusions use the separate 50-request final-build test; the evaluation JSON does not contain an end-to-end duration.
- Functional evaluation: 15/15 expected-source hits, 15/15 expected-card hits, 15/15 expected-term hits, 15/15 citation markers, and 0/15 truncated answers. Final-answer methods: 10 deterministic diagnostic, four curated Hungarian, and one evidence fallback. No free-form local-model answer was retained in the final output.
- Manual answer review: all 15 saved answers address their questions and contain citations. Q01 correctly explains the post-meeting transcript behavior for Only during the meeting. Q09 correctly explains the organizer-only agenda visibility case. The evaluation timestamp is after these answer fixes were committed, but the JSON does not include a source commit hash.
- Load test: the final-build run completed 50/50 at concurrency 1 with no errors or truncation. Mean latency was 3.11 seconds, p50 0.28 seconds, p95 12.27 seconds, maximum 94.89 seconds, and throughput 0.3216 requests per second. Mean answer-stage latency was 2.80 seconds and remains the bottleneck.
- Baseline comparison: mean latency and wall time improved by 97.4%, p95 by 93.9%, and throughput by 37.8 times. The long maximum remains a model-backed fallback outlier.

## Verification performed for this package update

- Preserved the previous-build load-test baseline under reports/history/ for the measured performance comparison. Obsolete intermediate smoke and evaluation records are available through Git history rather than duplicated in the submitted file tree.
- Copied the latest supplied smoke and evaluation JSON files into the package and updated the README, performance summary, knowledge-card audit, package contents, and compliance assessment.
- Python syntax compilation, JSON/JSONL parsing, result-metric assertions, and semantic equality checks against the supplied smoke and evaluation files passed.
- The final smoke and functional evaluation were supplied from the target Ollama environment. This review workspace does not have LangGraph, Streamlit, FastEmbed, Docker, or Ollama available for another end-to-end execution.

## Verdict

The package covers every deliverable category named in the assignment. Smoke and functional-evaluation results pass on the latest supplied run, including the previously problematic Q01 and Q09 prompts. The final-build 50-request performance test also passes and demonstrates a large measured improvement over the retained baseline. The remaining performance limitation is the long-tail maximum on model-backed fallback requests.
