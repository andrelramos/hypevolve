# Experiments

## Smoke (offline, free)
    ./scripts/make_dummy_target.sh
    sed "s|{PY}|$(which python3)|g" experiments/configs/smoke.template.yaml > experiments/configs/smoke.yaml
    python -m hypevolve --config experiments/configs/smoke.yaml

Keep `smoke.template.yaml` (with literal `{PY}`) as the checked-in template;
the generated `smoke.yaml` is machine-specific and git-ignored.

## Real targets
Point `source_path` at a git checkout under `targets/` pinned to a fixed commit.
Set `test_cmd`/`bench_cmd` to that project's suite + a benchmark script that
prints elapsed seconds as a float on its LAST stdout line.
Switch the agent to a real CLI, e.g.:
    claude:
      kind: cmd
      start_cmd_template: "claude -p --session-id {session_id} --output-format json"
      cont_cmd_template: "claude -p --resume {session_id} --output-format json"

Artifacts land in `results/<name>/`: summary.json, hypotheses.json,
transcripts/indiv_*.log, best/ (snapshot of the winning workspace).
