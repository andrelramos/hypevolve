# Rinha de Backend 2026: hypothesis-generation research progress

Date: 2026-10-13
Status: exploratory evidence; no competition result or p99 target achieved.

## Research question

Can HypEvolve's objective-led interview, research plan, and hypothesis portfolio help an agent find a better exact vector-search implementation than an unsupervised one-shot prompt, while preserving correctness and meeting the Rinha p99 objective (<0.4227 ms)?

The answer is currently split: the lightweight kernel comparison favors the implementation produced in the HypEvolve run, but the design does not isolate the hypothesis-generation method, and the only end-to-end measurement is slower than baseline. The experiment is therefore useful methodological evidence, not proof that HypEvolve improves contest outcomes.

## Evidence ledger

### Earlier isolated HypEvolve run (2026-10-12)

This Claude Opus run started from a fresh target and used a researched portfolio of 13 proposals. Across generations 0–2, seven implementations were evaluated; H3 was retained as the best checkpoint candidate. H3 combined a flat structure-of-arrays representation with four independent reference-distance sums per loop iteration.

The H3 transcript reports the following Go microbenchmarks on synthetic data, with `-count 10`:

| Synthetic reference count | Original scan | H3 (SoA, four at a time) | Reported ratio |
| ---: | ---: | ---: | ---: |
| 100,000 | 648 µs | 228 µs | 2.84× faster |
| 1,000,000 | 6.68 ms | 2.76 ms | 2.42× faster |

The same transcript reports zero output mismatches over about 20,000 random queries across ten reference counts, including tie/duplicate cases, and a heap reduction at one million references from 60.0 MB to 56.1 MB. These are candidate-reported synthetic kernel results, not measurements against the official reference distribution or the full service workload. The reported 2×2 benchmark also found dimension-wise early abandonment about 2× slower on uniform data, a useful negative result.

The small fixture HTTP benchmark does **not** confirm an end-to-end gain. Its five baseline timings have a 4.798 ms median; the selected H3 checkpoint's five timings have a 5.736 ms median (about 19.5% slower across these separate runs). H3's stored `speedup_vs_base` (1.067) conflicts with that raw cross-run comparison, and the local script processed only 20 fixture requests serially. Do not interpret its timing or selected fitness as an official p99 result. The run did advance through two GA generations, unlike the later blind official-workload attempt, but it does not demonstrate an end-to-end Rinha improvement.

### Matched search-kernel microbenchmark (2026-10-13)

Both arms used `gpt-5.6-luna`, the same post-interview h1 prompt, the same Apple M4/macOS ARM64 host, `GOMAXPROCS=2`, and the same benchmark harness. The harness read the first 100,000 official reference records, retained every tenth record (10,000 vectors), used the same midpoint query, ran three 200 ms trials, and compared each implementation to the same array-of-structures (AoS) exact-scan helper. A separate differential test checked 64 queries.

| Arm | AoS median | Candidate median | Change vs AoS | Sample decisions matching oracle |
| --- | ---: | ---: | ---: | ---: |
| HypEvolve h1 | 62.848 µs | 45.381 µs | 27.8% faster | 64/64 |
| Direct Codex h1 | 62.627 µs | 60.016 µs | 4.2% faster | 64/64 |

The baseline medians differ by about 0.4%, which supports a reasonably matched local comparison. HypEvolve h1 used separated labels/vectors and explicitly unrolled the 14-dimensional distance calculation. Direct Codex used a flat `[]float32` index, separate labels, and a dimension loop. Both remained exact linear scans; neither introduced a sublinear search algorithm.

**Causal limitation:** the direct Codex arm was deliberately given the exact same h1 prompt as the HypEvolve individual, and each arm had one model call. The measured gap therefore compares two single generated implementations, not HypEvolve hypothesis generation against a prompt that independently invents hypotheses. With one candidate per arm, nondeterministic generation and implementation details are confounders. The result is a promising implementation comparison, not evidence that the HypEvolve method caused the 23.6 percentage-point difference.

### End-to-end Rinha workload attempt

| Measurement | Recorded result |
| --- | ---: |
| Baseline p99 | 2.007521075 s (2,007.521 ms) |
| HypEvolve h1 p99 | 2.119657054 s (2,119.657 ms) |
| Change | about 5.6% slower |
| Target | p99 < 0.4227 ms |

The benchmark wrapper reads the official `p99` value in milliseconds and emits seconds as its scalar fitness, so the recorded values correspond to p99 latencies of roughly 2.01 s and 2.12 s. This is one p99 observation for each configuration, not a replicated comparison. The run reported many HTTP errors (over 16,000), did not complete its planned genetic search, and stopped at generation 0 after a disk-full error while creating the next workspace. The checkpoint's stored `speedup_vs_base` value (1.084) contradicts the recorded p99 values; recomputing baseline/candidate from those values gives about 0.947. The speedup field must not be used as a result.

The direct Codex arm could not bind the local socket needed by the HTTP benchmark, so it has no comparable end-to-end result. The earlier HypEvolve baseline/candidate run attempted the official Docker/k6 workload, but was not repeated and produced many errors; it is not a clean validation. **The p99 target was not met:** the measured candidate p99 (2,119.657 ms) was about 5,015 times the 0.4227 ms target. The official Linux/amd64 environment was not reproduced on the Apple Silicon host, and errors compromise the workload result.

### Correctness and sample scope

The matched arms each passed 64 sampled differential decisions against the AoS oracle; the direct Codex archive also records `go test ./...`, race tests, and `go vet ./...` passing. These are useful smoke checks, not proof for every valid input. Sampling used a deterministic prefix and is potentially biased. No representative randomized/stratified sample or exhaustive input-equivalence proof was completed.

An earlier lightweight report recorded a 29.9% h1 gain using a separate run (124.019 µs vs 86.981 µs). Because the later matched harness produced materially different absolute timings, this report uses only the paired three-trial comparison above for the arm-to-arm claim; the earlier value is retained as historical, non-comparable evidence.

## How the hypothesis method evolved

1. **User-supplied ideas:** the human introduced Rust, parallel graph-region search, vector subdivision, and per-subdivision prefilters. These were useful directions but not yet bounded by the exact nearest-neighbor semantics, workload evidence, or explicit rejection conditions.
2. **Objective-led interview:** the preparation run established the primary objective as p99 below 0.4227 ms, exact top-k Euclidean search, correctness for valid inputs, and rejection of fake/lookup responses. It also elicited that the workload was largely unknown to the user, so the agent had to research rather than assume its shape.
3. **Research before hypothesis selection:** the generated portfolio broadened the search beyond the initial implementation ideas: exact scan layout and 14D distance arithmetic (H1), certified exact indexing with fallback (H2), coarse partitioning with certified expansion (H3), compact representation with equivalence proof (H4), parsing/allocation work (H5), HTTP/proxy/scheduling overhead (H6), and an explicit guard against uncertified shortcuts (H7).
4. **Human-in-the-loop refinement:** questions were changed to be objective-specific and open-ended, and continuation was designed to reuse prior answers to avoid repeating interview questions. The resulting preparation artifact had no unresolved questions and marked the portfolio ready.
5. **Execution and comparison:** H1 yielded a faster sampled exact-search kernel than the direct implementation in this single paired microbenchmark. However, the GA execution did not progress beyond generation 0, so the experiment does not demonstrate multi-generation hypothesis inheritance or selection.

This is a substantive improvement in the *search protocol*: the human contributes goals and constraints, research expands the possibility space, and hypotheses carry predictions, refutation criteria, and measurements. It is not yet demonstrated that this protocol consistently produces better end-to-end outcomes.

## What HypEvolve contributed, and what remains unproven

### Supported by this experiment

- The interview captured an explicit, measurable objective and correctness boundary instead of optimizing an underspecified "make it faster" request.
- Research proposed materially different avenues, including certified exact indexes and end-to-end overhead, not only low-level loop/vector-layout changes.
- The portfolio made correctness, rejection criteria, and measurement part of each hypothesis rather than treating a plausible patch as a result.
- The H1 candidate was measurably faster on the bounded search-kernel sample than the particular direct-call implementation.

### Not supported yet

- That HypEvolve's generation method caused the microbenchmark difference: both arms received the same final h1 prompt, with only one implementation per arm.
- That evolutionary lineage, parent selection, or hypothesis inheritance improved this Rinha result: no child generation ran.
- That the candidate improves official p99, meets 0.4227 ms, handles all valid inputs, or is valid on the contest topology.
- That the Rinha result is a competition success. It is not.

## Method limitations exposed

- Fitness and checkpoint reporting allowed a speedup field that contradicts the raw times; raw measurements must be authoritative and inconsistent checkpoints invalidated.
- HTTP errors were not sufficiently prominent as an automatic rejection signal, and the run produced no trustworthy p99 comparison.
- A single repetition and one deterministic prefix sample are too weak for a performance conclusion.
- Disk capacity and workspace-copy cost interrupted evolution; every candidate and its source need durable, space-bounded archival.
- The direct arm's socket restriction prevented end-to-end symmetry.
- A 64-query oracle sample does not cover all inputs; exactness claims require a more comprehensive independent correctness strategy.
- The host architecture (Apple Silicon/macOS) differs from the official Linux/amd64 evaluation environment.

## Next protocol for a defensible comparison

1. Freeze one target commit, reference data, machine/container, compiler, resource limits, and official harness before either arm runs.
2. Compare at least three arms: (a) direct open-ended Codex prompt with no HypEvolve interview/portfolio, (b) the same model with HypEvolve interview and researched portfolio but no evolution, and (c) full HypEvolve evolution. Keep model, token/call budget, tools, and context disclosure comparable; record deviations.
3. Use multiple independent seeds/calls per arm and paired benchmark repetitions. Report raw samples, medians, p95/p99, errors, throughput, CPU, memory, and confidence/uncertainty; never infer p99 from a kernel microbenchmark.
4. Make correctness and infrastructure validity hard gates: independent oracle/differential tests over adversarial and generated valid inputs, all functional tests, zero unexplained HTTP errors, and successful execution on the official topology.
5. Run cheap representative samples first; run the complete official workload only after candidates pass the gates. Keep per-stage timings to determine whether vector search is actually the end-to-end bottleneck.
6. Persist every prompt, answer, research source, hypothesis, patch, raw measurement, status transition, and checkpoint; verify derived metrics against raw data and fail closed on contradictions or disk exhaustion.

## Reproducibility artifacts

The archived run materials used for this synthesis are under `/Users/andreramos/Dev/hypevolve-rinha-isolated-20261012/results/rinha-backend-2026-isolated-20261012/` and `/Users/andreramos/Dev/hypevolve-rinha-blind-interview-20261012/`: `preparation-codex/round-12/preparation.json`, `results/rinha-backend-2026-blind-execution/{baseline.json,checkpoint.json,light-validation.md}`, and `free-codex-20261013/{manifest.json,status.md,comparison.md,workspace/}`. The isolated run's candidate transcript and saved `best/` tree hold the synthetic microbenchmark claims; the free Codex status/event logs preserve prompt provenance, execution milestones, and the matched comparison. These paths are machine-local archives, not repository-relative portable links.
