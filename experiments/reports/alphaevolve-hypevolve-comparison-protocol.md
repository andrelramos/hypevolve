# AlphaEvolve and HypEvolve comparison: access and execution ledger

Status: **OpenEvolve/HypEvolve matched pilot complete; official Google AlphaEvolve not run**. The pilot used OpenEvolve as a named open-source, AlphaEvolve-inspired implementation. It does not establish a result for Google's managed AlphaEvolve service.

## Requested comparison

Compare Google DeepMind AlphaEvolve with HypEvolve on an existing repository challenge, using the same task prompt and Codex Luna, one system at a time. Preserve step-by-step execution logs and enough artifacts to audit the result. The practical question is whether the hypothesis-generation and evolution workflow used by HypEvolve produces a more useful solution under a controlled budget.

## AlphaEvolve availability and model constraint

AlphaEvolve became generally available on Google Cloud on 2026-07-09. Google publishes the client-side Python library, examples, and experiment skills in [Google-Cloud-AI/alphaevolve-on-googlecloud](https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud). Google explicitly describes that repository as a client and examples for its managed service, not an open-source reimplementation. The service generates candidates through a configurable mixture of Gemini Enterprise models; its current API reference enumerates Gemini models and states an unsupported model name returns `INVALID_ARGUMENT`. Codex Luna cannot be selected for an official run. Evaluators run in the user's environment and can compile/evaluate native code, so a Go challenge can use a custom evaluator even though the supplied AlphaEvolve skills currently document Python-only evolution.

Sources, checked 2026-10-17: [Google Cloud GA announcement](https://cloud.google.com/blog/products/ai-machine-learning/alphaevolve-is-available-for-everyone), [AlphaEvolve developer guide](https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/developer-guide/use-alphaevolve), [service architecture](https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/developer-guide/architecture-and-workflows), [Google's client repository FAQ](https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud#faq), and [API model support and validation](https://docs.cloud.google.com/gemini/enterprise/docs/alphaevolve/reference-guide/api-reference?hl=en#supported_models).

This creates two distinct experiments that must not be conflated:

1. **Official AlphaEvolve vs HypEvolve:** can run only with a provisioned Google Cloud AlphaEvolve environment. The model cannot be held constant: the managed arm uses Gemini, while HypEvolve uses Codex Luna. This estimates the practical difference between the available systems, with model as a confounder.
2. **Same Codex Luna on both arms:** requires replacing AlphaEvolve's managed generator with Codex, which would no longer be official AlphaEvolve. It must be labeled as an AlphaEvolve-inspired implementation.

There is no supported configuration that satisfies both “official Google AlphaEvolve” and “Codex Luna”. The user has reaffirmed that matching Luna is part of the requested experiment, so the Gemini-backed managed run is not authorized by that objective. The completed OpenEvolve pilot is the nearest valid same-model comparison; it must remain labeled as an open implementation. No cloud session or experiment has been created.

No official AlphaEvolve run has been started or represented as completed. A read-only check on 2026-10-17 found an existing authenticated `gcloud` account with access to project `pontotel-tools`; the Discovery Engine and Vertex AI APIs were enabled and the queried session/AlphaEvolve permissions were present. The project exposed a default collection and existing engines, but no AlphaEvolve sessions or assistants. Application Default Credentials were absent. These observations do not establish that AlphaEvolve is licensed or provisioned in the project. The prepared runner can use an ephemeral token from the existing gcloud account, but the model deviation still requires user acceptance before creating a session. The official runner has not been launched.

## Open-source alternative and Codex Luna compatibility

The strongest fit found is [OpenEvolve](https://github.com/algorithmicsuperintelligence/openevolve), an Apache-2.0 community implementation inspired by the AlphaEvolve paper. Its current upstream documents a `codex_app_server` provider that uses the Codex CLI's authenticated ChatGPT subscription without an API key. The adapter passes the configured model name directly to `thread/start`; a single-model config with weight `1.0` can therefore request the same model as HypEvolve. OpenEvolve supports evaluators that compile and run native code; using it on the Rinha Go target requires a custom evaluator and a Go source block, not the out-of-box Python-only AlphaEvolve skills.

Local compatibility checks on 2026-10-17: Codex CLI `0.162.1`; `codex login status` reports authenticated; `codex debug models` lists `gpt-5.6-luna` with default reasoning effort `medium`; OpenEvolve upstream HEAD inspected at `a1e9d91eecde612f0efc8e8e31f59b36998248c0` (`2026-10-14`) contains the Codex App Server adapter. Its adapter's `account/read` preflight timed out locally, so the pilot used a small local adapter around `codex exec`; all seven generation calls then completed with `gpt-5.6-luna`, reasoning effort `medium`. This demonstrates a working OpenEvolve plus Codex CLI setup, not a working stock App Server adapter. The result remains **OpenEvolve, an AlphaEvolve-inspired open implementation, not Google AlphaEvolve**.

Sources: [OpenEvolve repository and Codex App Server setup](https://github.com/algorithmicsuperintelligence/openevolve), its [`codex_app_server` implementation](https://github.com/algorithmicsuperintelligence/openevolve/blob/main/openevolve/llm/codex_app_server.py), and its [license](https://github.com/algorithmicsuperintelligence/openevolve/blob/main/LICENSE).

## Current repository and prior artifacts inspected

- This worktree is `/Users/andreramos/orca/workspaces/algoritmos-geneticos-com-llm/main-2`, at the repository state available on 2026-10-17. Its `targets/` directory contains only `.gitkeep`; the Rinha target and prior results are not present here.
- A separate checkout exists at `/Users/andreramos/Dev/algoritmos-geneticos-com-llm`, repository HEAD `62a38b2b23c7dabe6e2974e7dafe9147ddd7023f`, currently four commits behind its remote and dirty. Its Rinha target checkout is at `9c98e0ce1c69bd171351705912032f604d6e399c` and is dirty (`docker-compose.yml` modified; `.claude-flow/best/` untracked). These existing user files were left untouched.
- That checkout contains `experiments/configs/rinha_backend_2026_gpt_luna.yaml` and `results/rinha-backend-2026-gpt-56-luna/`, including `summary.json`, `run_log.json`, `checkpoint.json`, `hypotheses.json`, transcripts, and `EXPERIMENT_REPORT.md`.
- The prior HypEvolve config specifies Codex `gpt-5.6-luna`, two generations, population size three, five paired repetitions, one warmup, seed `20261012`, and serial agent execution. This is prior evidence, not a fresh matched run for the current request.
- The old summary records seven candidate evaluations. Its best-ever individual reports 1.1371× versus baseline, but `p_value_vs_base` is 0.1111 and `significant_vs_base` is false; its selected final best reports 1.0646× with `p_value_vs_base` 0.5794 and `significant_vs_base` false. The existing research-progress report also documents an earlier paired kernel microbenchmark and a flawed end-to-end workload attempt. Those results are not evidence about AlphaEvolve.

## Matched OpenEvolve/HypEvolve pilot (2026-10-17)

- Challenge snapshot: nested target commit `9c98e0ce1c69bd171351705912032f604d6e399c`; isolated under ignored `results/alphaevolve-inspired-openevolve-rinha-20261017/`. The dirty source checkout was not modified. Both arms used `gpt-5.6-luna`, reasoning effort `medium`, the same task prompt (SHA-256 recorded in `hypevolve/config_metadata.json`), serial generation, and seven model calls. The benchmark is a local fixture proxy, not an official Rinha score.
- OpenEvolve used upstream commit `a1e9d91eecde612f0efc8e8e31f59b36998248c0`, a custom Go evaluator, one island, and seven iterations. All seven generated candidates passed `go test ./...`. The fitness gate returned the unchanged seed as best; no generated candidate had a significant speedup at `alpha=0.05`. Highest observed candidate speedup was `1.1389x`, with one-sided Mann-Whitney `p=0.1548`.
- HypEvolve used two generations, population three, absolute fitness, and seven hypotheses. All seven candidates passed `go test ./...`. Individual 3 reached `1.1783x` with `p=0.0476` on five paired timing repetitions, narrowly crossing the significance threshold. An independent confirmation with 30 paired repetitions gave `1.1464x`, `p=0.1452`, so the gain did not reproduce as statistically significant.
- The timing samples are only a few milliseconds and visibly noisy. Both systems alternate candidate and reference runs, but their configured significance gate applies a one-sided Mann-Whitney test to the two samples; candidate selection also examines seven attempts without a multiple-comparison correction. Treat the five-repeat result as exploratory. The longer confirmation is the more reliable evidence here: no confirmed speedup.
- HypEvolve's Codex agent reported that its own attempt to run the local HTTP benchmark was blocked by its workspace sandbox. The external evaluator did run the benchmark successfully for each candidate; this distinction is preserved in the individual transcripts and run log. OpenEvolve's agent/evaluator context also differs by framework. Model, reasoning effort, task text, call count, target snapshot, test command, benchmark command, and scoring threshold were held constant; token and wall-clock budgets were not.
- **Practical HypEvolve objective (qualitative artifact review):** HypEvolve logged seven explicit one-sentence predictions and marked each confirmed/refuted alongside correctness and measured speedup; later prompts referred to validated knowledge. The predictions mostly explored related micro-optimizations in the same small top-five/14-dimensional loop, and the best apparent gain did not reproduce. OpenEvolve retained candidate descriptions, parentage, diffs, and metrics, while its run prompt centered on fitness/diversity rather than an explicit hypothesis lifecycle. This supports a limited conclusion that HypEvolve's representation is more useful for reviewing and communicating research claims in this pilot; neither arm showed a repeatable gain. It is an artifact-based assessment, not a blinded or statistically powered measure of practical usefulness.
- **Seven-batch repeatability follow-up:** repeated the OpenEvolve selected seed, its 1.1389x best observed candidate, and HypEvolve candidate 3 seven times each (five paired timings per repetition). None passed the original significance gate in any batch; pooled speedups were 0.9366x, 0.9616x, and 1.0356x. The GSO Tornado evolution best and sampling best were also repeated seven times each with nine pairs per batch; both preserved significant gains in all seven batches. Full detail and raw logs: [repeatability report](repeatability-rinha-gso-tornado-20261017.md).
- Audit files, traces, raw timings, and prompts are under `results/alphaevolve-inspired-openevolve-rinha-20261017/`. A concise result summary is `results/alphaevolve-inspired-openevolve-rinha-20261017/experiment-summary.md`.

## GSO Tornado: HypEvolve evolution vs OpenEvolve-style sampling control

This is a separate comparison from the Rinha pilot above. It uses the GSO task `tornado-4d4c1e0` and the existing same-budget Tornado run. **The GSO logs identify the two arms as HypEvolve `ga` and `sampling`; they do not show an execution of the OpenEvolve software.** The sampling arm is therefore an OpenEvolve-style independent-sampling control, not an OpenEvolve tool result. OpenEvolve itself was run in the separate Rinha pilot above. This distinction matters because OpenEvolve can also run evolutionary search.

### Matched setup and measured outcome

| Item | HypEvolve | Independent-sampling control |
| --- | --- | --- |
| Search configuration | Genetic selection, four offspring generations, one elite retained | Independent candidate sampling from the pristine baseline (OpenEvolve-style control) |
| Model and call budget | Claude Sonnet; 26 calls | Claude Sonnet; 26 calls |
| Valid candidates | 26/26 | 25/26; one timeout |
| Best original speedup vs pristine baseline | **3.2316x** (individual 24) | **1.5726x** (individual 11) |
| Seven-batch champion remeasurement | **3.0176x** pooled median; significant in 7/7 batches | **1.5330x** pooled median; significant in 7/7 batches |

Both arms used the same Tornado challenge and benchmark. Candidate correctness was checked with `gso_check.py` and `tornado.test.concurrent_test`; both checks passed for the baseline and the two selected candidates before repeat timings. The evolutionary candidate's changes were confined to `tornado/concurrent.py` and `tornado/gen.py` after normalization. The stored snapshot contained an unrelated `.tool-versions` file; integrity preflight rejected that snapshot before timing, and the file was excluded only from the isolated repeat copy. The source snapshot was preserved.

### Where the evolutionary advantage appeared

The recorded best-of-lineage path rose through five selected checkpoints: individual #5 at 1.41x, #6 at 1.77x, #11 at 2.11x, #17 at 2.32x, and #24 at 3.23x. The independent-sampling arm's best candidate reached 1.57x and did not build on a previous candidate's workspace. With the same number of model calls, the HypEvolve champion was 2.05x the independent-sampling control champion by original best scores. In the separate seven-batch remeasurement, the champion medians were about 1.97x apart (3.0176x / 1.5330x).

| Search step | HypEvolve evolutionary lineage | Independent-sampling control |
| --- | --- | --- |
| Initial search | Best seed #5: 1.41x | First strong candidate: 1.49x |
| Mid-search | Selected descendants raised the lineage through 1.77x and 2.11x | A later attempt reached 1.51x; candidates still restarted from baseline |
| Later generations | Lineage checkpoints reached 2.32x, then 3.23x | Best reached 1.57x at call 12; the remaining 14 calls did not improve it |
| Search behavior | Best code and evidence could become the starting point for later hypotheses | Independent attempts revisited first-layer optimizations rather than extending a parent |

These are best-so-far checkpoints, not the mean score of a generation. The values show where the observed gap opened: after the initial seed phase, when later evolutionary calls could work from selected parent code. The sampling control found a competitive first-layer improvement early, then plateaued.

The result is consistent with a benefit from selecting promising hypotheses and letting later generations continue from inherited code and recorded evidence: independent attempts repeatedly returned to first-layer optimizations, while descendants could explore further changes on top of a faster parent. The logs show a cumulative lineage, not that every mutation helped; some proposals were refuted or failed to improve their parent. The final score is the effect of the accumulated patch, so this run cannot isolate the causal contribution of any one hypothesis. Since the control was the local sampling mode rather than the OpenEvolve software, this is not a direct tool-to-tool GSO comparison.

### Scope and interpretation

The seven repetitions remeasured the already selected champions; they did not repeat the full search with seven fresh random seeds. They establish that these two patches retained their speedups on this local task and host, not that HypEvolve will win on every new search, GSO task, or machine. The arms were matched on model-call count, model, target, and benchmark, but not on token usage: evolutionary prompts include inherited code and evidence. A separate Rinha/OpenEvolve pilot in this report did not show a repeatable HypEvolve speedup, so the Tornado result should remain task-specific.

Detailed raw measurements and integrity notes: [`repeatability-rinha-gso-tornado-20261017.md`](repeatability-rinha-gso-tornado-20261017.md), with run traces under `results/alphaevolve-inspired-openevolve-rinha-20261017/repeatability-20261017/gso-tornado/`.

## Limitations and controls for a larger follow-up

1. Freeze the exact challenge target commit, benchmark command, data, test command, resource limits, and host/runtime details. Do not use the dirty target checkout without first preserving and resolving its current changes.
2. Save one immutable task prompt and pass the same text, target context, tools, and allowed workspace to both arms. Log any context differences imposed by the systems.
3. Fix the model and call/token/time budget. If the official AlphaEvolve service is used, record that model equality is impossible and treat model/system effects as confounded. If an open replica is used with Codex Luna, call it an AlphaEvolve-inspired replica.
4. Run arms sequentially against isolated copies of the same frozen target. Keep all candidate edits, prompts, transcripts, evaluator output, raw timings, errors, and resource measurements outside the benchmark hot path.
5. Use repeated paired benchmark trials and independent seeds. Require correctness and zero unexplained evaluator/infrastructure errors before comparing performance. Report raw values, medians, uncertainty, failed attempts, and total model calls; do not rank from one best-of-many score alone.
6. Analyze practical HypEvolve objectives as well as fitness: whether the method elicits a measurable objective and constraints, produces testable and refutable hypotheses, identifies useful research directions, preserves correctness, and yields a repeatable end-to-end improvement within budget.

## Execution log

| Step | State | Evidence |
| --- | --- | --- |
| Inspect current worktree and benchmark inventory | Complete | `targets/` has no challenge checkout; existing Rinha report is `experiments/reports/rinha-backend-2026-research-progress.md`. |
| Verify current AlphaEvolve availability, API prerequisites, and model path | Complete | Official repository confirms it contains only the client/examples for the managed Gemini service, not the engine implementation. Current API supports listed Gemini models and rejects unsupported model names; Codex Luna is not selectable. |
| Locate prior HypEvolve target and artifacts | Complete | Separate dirty `Dev` checkout and its Rinha result directory listed above. |
| Verify local AlphaEvolve cloud prerequisites | Partial | Existing account access, API enablement, and queried IAM permissions confirmed for `pontotel-tools`; no existing AlphaEvolve sessions or assistants, no ADC, and service entitlement remains unverified. No cloud resource has been created. |
| Identify an open-source implementation compatible with Codex Luna | Complete | OpenEvolve upstream has a Codex App Server provider; local Codex login is authenticated and its model catalog lists `gpt-5.6-luna` (default effort: medium). |
| Verify an actual OpenEvolve generation on the challenge | Complete | Seven OpenEvolve iterations ran via the local Codex CLI adapter; seven transcripts and the evolution trace are retained. |
| Run the matched OpenEvolve/HypEvolve challenge comparison | Complete (pilot) | Both arms used seven Codex Luna calls on isolated copies of the same pinned target and exact shared task text. HypEvolve's best candidate did not pass an independent 30-pair significance check. |
| Prepare and preflight the official Google AlphaEvolve evaluator | Complete (local only) | Go candidate integrity checks, `go test ./...`, and five paired benchmark calls passed on the seed; evaluator log is retained under `results/.../google-alphaevolve/logs/evaluations/`. This does not prove cloud entitlement or model execution. |
| Run the official Google AlphaEvolve comparison | Incompatible constraints | User's objective requires Codex Luna and same-model comparison. Google's official managed API accepts only supported Gemini models. No session or experiment was created because using Gemini would violate the stated comparison design. |
