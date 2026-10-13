# HypEvolve explainer — storyboard

Audience: technical people who use AI daily but have never worked with a genetic algorithm or orchestrated agents.
Format: 16:9, 1920×1080, 30 fps, on-screen text plus a synthesized soundtrack, one render per site language
(`pt`, `en`, `es`, `zh`, `ja`). On-screen copy lives in `i18n.js`.

Scenes are authored on a 67 s grid and played at `SPEED = 1.3` (≈87 s) so every sentence can be read.

| # | Grid time | Scene | Message |
|---|-----------|-------|---------|
| 1 | 0–9.5 | One prompt in a terminal gives +4.2%; three attempts land on the same gain | Every attempt starts from scratch |
| 2 | 9.5–18 | Question → "Hyp + Evolve" wordmark → generations of dots | A genetic algorithm keeps what measures best |
| 3 | 18–28 | The agent calls the MCP tool `start_evolution` | You only define what is correct (tests) and what is better (benchmark) |
| 4 | 28–36 | Propose → Test → Select → Inherit loop | Every generation is one cycle |
| 4b | 36–43 | Statistical gate: same +5% mean, low vs high spread, 9 runs each | Only p < α = 0.05 advances; luck does not pass |
| 5 | 43–54 | Web panel rebuilt from `hypevolve/server.py`: a cheating individual fails, the winner reaches 3.23× | Every result is auditable |
| 6 | 54–61.5 | GSO tornado 3.23× vs 1.57× (same 26 calls); Rinha −27.8% vs −4.2% | What has been measured so far |
| 7 | 61.5–67 | Possibilities, then `uv run hypevolve mcp` | If you can measure it, you can evolve it |

Sources for the numbers: `docs/index.html` (results section) and
`hypevolve/reports/data/2026-08-26/PILOT_REPORT_V2.md` (anti-cheat case).
Panel individuals (hypotheses, prompts, outputs) and the statistical-gate samples are illustrative;
the gate p-values are real one-sided t-tests on those samples.

Build: `./video/render.sh` (all languages) or `./video/render.sh qc` (review stills only).
