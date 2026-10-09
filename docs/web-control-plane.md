# HypEvolve web panel and CLI

The FastAPI server is the single source of truth for the web panel and can be used by external agents through REST. Results remain portable JSON files under `results/<session>/`, so an execution can be resumed for analysis without a database.

```bash
# Prepare the environment from the committed lock file.
uv sync --extra dev

# The test command determines whether a change is valid. The benchmark must
# print a numeric duration in seconds on its last line.
uv run hypevolve run \
  --target /path/to/repository \
  --test-cmd 'python -m pytest -q' \
  --bench-cmd 'python bench.py' \
  --generations 10 \
  --max-hypotheses 40 \
  --harness codex \
  --initial-prompt 'Focus on the critical parser.'

uv run hypevolve serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The panel displays generations horizontally; each dot represents a tested individual. Selecting a dot shows the prompt, harness stdout, and stdout/stderr/exit code from the deterministic test.

The terminal returns JSON so agents can operate it easily:

```bash
hypevolve sessions
hypevolve generations run-20260924T120000Z
hypevolve individual run-20260924T120000Z 3
hypevolve hypotheses run-20260924T120000Z
hypevolve hypothesis-add run-20260924T120000Z 'Memoize the parser result.'
hypevolve hypothesis-edit run-20260924T120000Z manual-... 'New formulation.'
hypevolve hypothesis-remove run-20260924T120000Z manual-...
```

Main REST routes are `GET /api/sessions`, `GET /api/sessions/{id}`, `GET /api/sessions/{id}/generations`, `GET /api/sessions/{id}/individuals/{n}`, and CRUD under `/api/sessions/{id}/hypotheses`. `POST /api/sessions` accepts the same fields as the `run` subcommand and starts the execution in the background.
