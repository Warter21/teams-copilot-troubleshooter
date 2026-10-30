# Assignment compliance checklist

Assessment date: 2026-10-30. This checklist maps the project package to the attached Senior AI Engineer assignment and the latest supplied test results.

| Assignment requirement | Package evidence | Status |
| --- | --- | --- |
| Choose a real problem and explain relevance, user need, and why Agentic RAG fits | README.md, Problem and rationale | Complete |
| Use LangGraph with at least five main workflow nodes | src/teams_copilot_troubleshooter/graph.py | Exactly five main nodes |
| Include conditional routing, decomposition, independent work, and intermediate state | graph.py, state.py | Implemented |
| Integrate at least two tools, including a non-retrieval tool | src/teams_copilot_troubleshooter/tools.py | Retrieval plus deterministic diagnostic precheck |
| Keep RAG in a modular subgraph | src/teams_copilot_troubleshooter/rag_subgraph.py | Implemented separately from the five main nodes |
| Use a text data source and provide an integration path | data/source_manifest.json, 18 knowledge cards, scripts/refresh_sources.py | Present for prototype scope |
| Avoid paid model APIs; explain local model trade-offs | Ollama Qwen3 0.6B/1.7B and Dummy mode; README.md | Complete |
| Provide a Streamlit prototype UI | app.py | Model selection/download, answer, diagnostics, Microsoft sources, and workflow trace |
| Containerize and provide a Dockerfile | Dockerfile, compose.yaml, compose.dummy.yaml | Present |
| Evaluate 10–20 questions | evaluation/questions.jsonl, scripts/run_evaluation.py, reports/evaluation_results.json | 15 questions; all retrieval/citation indicators 100%; zero truncations; all saved answers reviewed for relevance |
| Run a 50–200 request load scenario and report latency, bottleneck, and optimizations | scripts/load_test.py, reports/load_test_50_requests.json, reports/performance_summary.md | Final-build 50-request result included: 50/50 success, zero truncations, latency percentiles, stage timings, bottleneck, and baseline comparison |
| Provide a README with problem, architecture, decisions, results, and run instructions | README.md | Complete and updated |
| Deliver source code in a Git repository | Project source tree and .git metadata | Local Git repository included in the archive; no hosted remote is configured |

## Final checks

- Latest supplied smoke record passes and contains a complete cited answer; model-draft and final-answer truncation flags are false.
- Latest supplied 15-question run reports 100% expected-source, expected-card, expected-term, and citation-marker metrics, with zero truncations.
- Manual review found all 15 saved answers relevant to their questions and cited. Q01 and Q09 are responsive in this full evaluation.
- The evaluation output retains 10 deterministic diagnostics, four curated Hungarian answers, and one evidence fallback; no free-form local-model answer was retained as final output.
- The final-build 50-request load result completed 50/50 at concurrency 1 with no errors or truncation. Mean latency was 3.11 s, p50 0.28 s, p95 12.27 s, and maximum 94.89 s.
- Compared with the previous baseline, mean latency fell by 97.4% and throughput increased 37.8 times. Answer generation remains the slowest stage and the maximum latency remains an outlier worth further investigation.
- The final supplied smoke, evaluation, and load-test JSON files are preserved. The previous-build load-test baseline is retained in reports/history/ for the documented performance comparison.
