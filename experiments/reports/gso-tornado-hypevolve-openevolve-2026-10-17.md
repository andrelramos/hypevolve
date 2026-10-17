# GSO Tornado: HypEvolve vs. OpenEvolve with Codex GPT-6 Luna

**Date:** 2026-10-17 · **Challenge:** GSO `tornado-4d4c1e0`, `Future.set_exception` workload
**Conclusion:** Both tools produced correct, significantly faster candidates under the same 26-call budget. Champion remeasurement found nearly identical speedups; the direct comparison did not establish a statistically significant winner.

## Results

| Measure | HypEvolve | OpenEvolve |
|---|---:|---:|
| Search budget | 26 model calls | 26 model calls |
| Valid evaluated candidates | 26/26 | 22/26 (4 calls returned no applicable diff) |
| Best search result vs. pristine baseline | 1.537× | 1.494× |
| Best candidate p-value vs. baseline | 0.000206 | 0.000206 |
| Champion remeasurement speedup (63 timings) | 1.521× | 1.511× |
| Champion remeasurement p-value vs. baseline | 3.53e-21 | 1.83e-22 |

The direct, one-sided Mann–Whitney U comparison of the two champions used 63 candidate timings per tool. HypEvolve’s measured candidate time was numerically lower, but the difference was not statistically significant (U=1789, p=0.171, α=0.05). The appropriate conclusion for this task and seed is a tie within the resolution of this experiment, not HypEvolve superiority.

Each of the seven remeasurement blocks for both champions independently passed the candidate-versus-baseline significance threshold. These are repeated measurements of two selected programs, not seven independent evolutionary searches.

## What was run

Both methods used Codex `gpt-6-luna`, reasoning effort `medium`, Codex CLI codex-cli 0.162.1, seed 42, the same GSO baseline, the same evaluator, and 26 model calls. The common task instructions are in [`gso-tornado-common.md`](../prompts/gso-tornado-common.md), SHA-256 `216f8e24ac76093e79d4a62846a97c707b45c2390d6baede80afc12712d2a804`. Candidate edits were restricted to `tornado/concurrent.py`. The baseline source SHA-256 was `514cea1a0dd13a6f43f1f3c19c4f7a1d66df9d0c838096ee003dd7b2ba4eca58` at GSO commit `62a38b2b23c7dabe6e2974e7dafe9147ddd7023f`.

- **HypEvolve:** genetic algorithm, population 6, one elite, tournament size 3, four generations. All 26 generated candidates passed scope and correctness checks. The winning parent lineage was candidate 0 → 6 → 15 → 20 → 25, with observed speedup increasing from 1.106× to 1.537×. This is a selected parent path; it does not mean only the global champion was evaluated in each generation.
- **OpenEvolve:** official OpenEvolve at commit `a1e9d91eecde612f0efc8e8e31f59b36998248c0`, using its MAP-Elites database, one island, population 6, and `speedup_vs_baseline` as the feature dimension. It made 26 model calls; 22 returned applicable diffs and were evaluated, while four responses produced no valid diff. All 22 evaluated candidates passed scope and correctness checks. The winning program was found at iteration 25 with 1.494× speedup; its parent was an earlier evolved program, confirming that OpenEvolve did perform evolutionary search.

Both winning patches used a fast path for `Future.set_exception`; their final code differs in callback handling. See the [HypEvolve patch](data/gso-tornado-codex-2026-10-17/hypevolve.patch) and [OpenEvolve patch](data/gso-tornado-codex-2026-10-17/openevolve.patch).

## Evaluation and repeatability

The pristine baseline was checked with the GSO correctness checker and `tornado.test.concurrent_test` (37 tests). Candidate evaluation used the same correctness checks and scope guard, then one warm-up and nine timing repetitions. The search fitness used the ratio of baseline median to candidate median only when the one-sided Mann–Whitney U test found a significant improvement at α=0.05.

After both searches, we remeasured each selected champion in seven alternating blocks. Every block contained nine candidate/reference timing pairs, interleaved sample by sample. This produced 63 candidate and 63 baseline timings for each tool. Aggregate medians were 0.001854000s for HypEvolve and 0.001866250s for OpenEvolve. The paired ordering helps reduce timing drift; raw values and per-block results are in [`champion-repeatability.json`](data/gso-tornado-codex-2026-10-17/champion-repeatability.json). Machine-readable search results, protocol, and caveats are in [`results.json`](data/gso-tornado-codex-2026-10-17/results.json).

## Fairness and limits

The task prompt text and evaluation budget were shared, but the full model context was not byte-identical: HypEvolve supplied the candidate through an editable workspace, while OpenEvolve embedded the current source in its prompt and requested a textual diff. Codex sandbox settings also differed to match those interaction modes. OpenEvolve’s four non-applicable diffs count against its fixed call budget.

This is one evolutionary search per tool on one task with one seed. Repeated champion timings assess measurement stability, not search-to-search repeatability. The result does not establish general tool superiority, and the local Python 3.9.6 timing is not an official GSO leaderboard score. The metric is the local speedup ratio against the pristine baseline.

An earlier Claude Sonnet attempt stopped before candidate evaluation after six authentication failures and is excluded. Two OpenEvolve startup attempts were also excluded; they made no evolution-model calls. The reported OpenEvolve result comes from the later clean 26-call run after correcting its setup.
