# Functional test and performance summary

Assessment date: 2026-10-30. This summary uses the final supplied smoke, 15-question functional evaluation, and final-build 50-request load test.

## Latest smoke result

| Item | Result |
| --- | --- |
| Backend | Ollama + FastEmbed |
| Answer model | Qwen3 0.6B |
| Status | Passed |
| Elapsed time | 108.29 s |
| Answer length | 282 characters |
| Evidence / diagnostics | 5 / 1 |
| Main workflow nodes reached | 5 of 5 |
| Ollama finish reason | stop |
| Model draft truncated / final answer truncated | No / No |
| Final response method | Evidence fallback |

The stored answer is complete and ends with citation [S1]. This smoke result verifies end-to-end behavior; performance comparisons use the 50-request final-build load test and retained previous-build load baseline. The 1.7B model previously exceeded the 300-second response timeout on the target CPU.

## Latest 15-question functional evaluation

The record was generated at 2026-10-30 12:41:44 UTC using Ollama, FastEmbed, Qwen3 0.6B, and a 256-token answer cap.

| Metric | Result |
| --- | ---: |
| Questions | 15 |
| Expected source hit rate at K=5 | 15/15 (100%) |
| Expected knowledge-card hit rate at K=5 | 15/15 (100%) |
| Expected-term hit rate in retrieved evidence | 15/15 (100%) |
| Citation marker present | 15/15 (100%) |
| Model drafts reaching output limit | 0/15 |
| Final answers marked truncated | 0/15 |
| Deterministic diagnostic answers | 10/15 |
| Curated Hungarian answers | 4/15 |
| Evidence fallbacks | 1/15 |
| Free-form local-model answers retained as final answers | 0/15 |

Manual relevance review of the saved answers found that all 15 address their questions and include citations. The previously problematic answers now pass in this supplied full evaluation:

- Q01 explains that Only during the meeting permits live use without a saved transcript, while post-meeting questions about spoken content require an available transcript.
- Q09 explains that Facilitator may not read the organizer's copy of the invite until another participant joins, and also notes protected invite or notes content.

The evaluation timestamp is after the answer-relevance fixes were committed. The JSON does not embed the tested source commit hash, so the source revision is not independently pinned by the test artifact. The output-method counts show that the evaluation exercised the hybrid answer path; no free-form local-model answer was retained. Q13 used the evidence fallback. The retrieval and citation metrics establish evidence coverage and citation-marker presence, not independent factual accuracy against live Microsoft documentation. The JSON does not record total evaluation duration, so it cannot verify a speed claim.

## Final-build load test

The final-build 50-request end-to-end run was generated on 2026-10-30 using Ollama, FastEmbed, Qwen3 0.6B, a 256-token answer cap, and concurrency 1. One warm-up request was reported separately.

| Metric | Final-build result |
| --- | ---: |
| Backend | Ollama + FastEmbed |
| Requests | 50 measured + 1 warm-up |
| Concurrency | 1 |
| Successful / failed | 50 / 0 |
| Truncated responses | 0 |
| Total measured time | 155.46 s |
| Mean latency | 3.11 s |
| p50 latency | 0.28 s |
| p95 latency | 12.27 s |
| Maximum latency | 94.89 s |
| Throughput | 0.3216 requests/s |
| Warm-up latency | 11.85 s |
| Answer methods | 34 deterministic, 13 curated Hungarian, 3 evidence fallback |

### Mean stage latency in the final build

| Stage | Mean latency |
| --- | ---: |
| Answer generation | 2.804 s |
| RAG retrieval | 0.292 s |
| Diagnostic checks | 0.007 s |
| Triage | 0.00008 s |
| Planning | Below 0.001 s |

Answer generation was approximately 90.2% of mean end-to-end latency and remains the primary measured bottleneck. The low median reflects the 47 deterministic or curated answers; the three evidence fallbacks account for model-backed work and contribute to the long tail.

## Baseline comparison

| Metric | Previous build | Final build | Change |
| --- | ---: | ---: | ---: |
| Mean latency | 117.67 s | 3.11 s | 97.4% lower |
| p50 latency | 98.77 s | 0.28 s | 99.7% lower |
| p95 latency | 199.96 s | 12.27 s | 93.9% lower |
| Maximum latency | 204.20 s | 94.89 s | 53.5% lower |
| Wall time | 5,883.28 s | 155.46 s | 97.4% lower |
| Throughput | 0.0085 req/s | 0.3216 req/s | 37.8x higher |
| Mean answer stage | 117.23 s | 2.80 s | 97.6% lower |
| Mean RAG stage | 0.419 s | 0.292 s | 30.3% lower |

The comparison shows that routing known scenarios to deterministic or curated answers materially improved end-to-end performance while the final functional evaluation remained successful. It is not solely a model-speed improvement: the final system invokes model-backed fallback for only a small minority of the evaluation workload.

## Optimization recommendations

1. Preserve the deterministic and curated paths for supported scenarios and add regression tests whenever a new rule is introduced.
2. Investigate the 94.89-second maximum with per-request timing records. For model-backed fallback, consider caching repeated questions, reducing evidence further, or enforcing a shorter generation timeout followed by a complete extractive fallback. Streaming can make the wait visible but does not reduce total inference time.

## Raw records

- reports/smoke_results.json: latest supplied smoke result, including the complete answer, node trace, and truncation flags.
- reports/evaluation_results.json: latest supplied 15-question result, including per-question answers, retrieval metrics, methods, and truncation flags.
- reports/load_test_50_requests.json: final-build 50-request load result.
- reports/history/load_test_50_requests_2026-10-29_baseline.json: previous-build load-test baseline retained for the measured performance comparison.
