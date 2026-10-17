# Seven-batch repeatability check: Rinha and GSO Tornado

Date: 2026-10-17

## Design

Repeated the selected candidates from the earlier Rinha OpenEvolve/HypEvolve pilot and from the existing GSO Tornado evolution-versus-sampling experiment. Each run was serialized. Every repetition interleaved candidate and reference measurements; the first candidate order alternated across repetitions. Candidate copies were placed under the current worktree's ignored `results/` directory. The existing `/Users/andreramos/Dev/algoritmos-geneticos-com-llm` checkout and its dirty worktree were read-only inputs and were not edited.

The original one-sided Mann-Whitney test (`candidate < reference`, alpha 0.05) was retained per repetition. I also report a one-sided paired Wilcoxon test across the interleaved pairs. Pooled results combine all pairs from the seven repetitions; treat the paired test as the more relevant pooled check because each candidate timing has an adjacent reference timing.

## Rinha de Backend 2026 local fixture

The benchmark is the repository's `./scripts/benchmark.sh` against the frozen fixture target at commit `9c98e0ce1c69bd171351705912032f604d6e399c`. It is a local proxy, not the official Rinha score. Each candidate was tested with `go test ./...` and measured in seven evaluator runs, each containing one warmup per arm and five paired timings (35 pairs per candidate). All 21 candidate evaluations passed their correctness tests.

| Candidate | Original best result | Significant repetitions (MW) | Pooled median speedup | Pooled MW p | Pooled paired Wilcoxon p | Repeat conclusion |
|---|---:|---:|---:|---:|---:|---|
| OpenEvolve selected seed | 1.0000x fitness (seed retained) | 0/7 | 0.9366x | 0.9917 | 0.9843 | No speedup |
| OpenEvolve highest observed candidate | 1.1389x, p=0.1548 | 0/7 | 0.9616x | 0.3935 | 0.4010 | Initial best did not reproduce |
| HypEvolve candidate 3 | 1.1783x, p=0.0476 | 0/7 | 1.0356x | 0.1426 | 0.2354 | Initial significant result did not reproduce |

The HypEvolve candidate's new pooled median was 0.005936 s versus 0.006147 s for the paired reference. The earlier independent 30-pair check was also nonsignificant (`p=0.1452`). Across the seven new five-pair checks, none of the three candidates passed the original gate. The slight pooled HypEvolve median difference is not statistically established.

## GSO Tornado task `tornado-4d4c1e0`

Used the exact local task benchmark `gso_bench.py` and its stored reference workspace. The baseline source's `tornado/concurrent.py` SHA-256 was `514cea1a0dd13a6f43f1f3c19c4f7a1d66df9d0c838096ee003dd7b2ba4eca58`, matching `targets/tornado-base` at commit `62a38b2b23c7dabe6e2974e7dafe9147ddd7023f`. The original GSO config uses nine timings; therefore each of seven repeated evaluations per candidate contains one warmup per arm and nine paired timings (63 pairs per candidate total).

Before timing, the baseline and both candidate copies passed `gso_check.py` and `python -m tornado.test.runtests tornado.test.concurrent_test` (return code 0 for all six checks). The evolved patch changed only `tornado/concurrent.py` and `tornado/gen.py` after normalization. Its stored best snapshot also contained an extra `.tool-versions` file (`python 3.7.16`) that was absent from the reference and outside the task's allowed `tornado/` subtree. The first preflight rejected it before candidate tests or timings. I left the source snapshot untouched and excluded that metadata file only from the isolated rerun copy; this is logged in `gso-tornado/preflight-integrity-attempt-1.json` and `gso-tornado/summary.json`.

| Candidate | Original best result | Significant repetitions (MW / paired Wilcoxon) | Pooled median speedup | Pooled MW p | Pooled paired Wilcoxon p | Repeat conclusion |
|---|---:|---:|---:|---:|---:|---|
| HypEvolve evolution best, individual 24 | 3.2316x | 7/7 / 7/7 | 3.0176x | < 2e-22 | < 3e-12 | Gain reproduced in every batch |
| Independent sampling best, individual 11 | 1.5726x | 7/7 / 7/7 | 1.5330x | < 2e-22 | < 3e-12 | Gain reproduced in every batch |

The evolved candidate's per-batch speedups ranged from 2.9829x to 3.0496x; sampling ranged from 1.4929x to 1.6023x. In these reruns, evolution remained approximately 1.97x faster than the best independent-sampling candidate by pooled medians. The measured gains are stable on this local Tornado task and host; this does not establish performance across all GSO tasks or machines.

## Audit artifacts

- `results/alphaevolve-inspired-openevolve-rinha-20261017/repeatability-20261017/run_repeatability.py`: runner and exact sequential procedure.
- `.../rinha/summary.json` and `.../rinha/evaluation-logs/`: seven repetitions per candidate, all raw candidate/reference timings, test outputs, and pooled statistics.
- `.../gso-tornado/summary.json`: seven batches per arm, 126 candidate/reference pairs (252 timed benchmark invocations), preflight test output, medians, p-values, source integrity record, and environment-marker normalization.
- `.../gso-tornado/preflight-integrity-attempt-1.json`: first integrity rejection, retained as part of the execution log.
- `.../run-manifest.json`: start/end time and run artifact index.
