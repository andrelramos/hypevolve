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

## MCP for coding agents

HypEvolve also includes a dependency-free MCP server over stdio. This is the
lowest-friction integration for an agent: it does not require a web server or a
new database. Register this command in the agent's MCP configuration:

```json
{
  "mcpServers": {
    "hypevolve": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/algoritmos-geneticos-com-llm", "hypevolve", "mcp"]
    }
  }
}
```

The available tools are `start_evolution`, `list_executions`,
`get_execution`, `get_generations`, `get_individual`, `list_hypotheses`, and
`add_hypothesis`. `start_evolution` returns immediately with a `session_id`;
the agent can poll `get_execution` or `list_executions` until the status is
`completed` or `failed`.

The run still needs an honest correctness command and a benchmark command. The
benchmark's final stdout line must be a duration in seconds, and a non-zero
test exit rejects the candidate. Results are stored under `results/` unless a
different `--results-root` is placed before the `mcp` command.
