# Painel web e CLI do HypEvolve

O servidor FastAPI é a fonte única de consulta para o painel e pode ser usado
por agentes externos por REST. Os resultados permanecem em JSON dentro de
`results/<sessão>/`, portanto uma execução pode ser retomada para análise sem
depender de banco de dados.

```bash
# Prepare o ambiente a partir do lock versionado.
uv sync --extra dev

# O comando de teste determina se uma alteração é válida. O benchmark deve
# terminar imprimindo uma duração numérica (em segundos) na última linha.
uv run hypevolve run \
  --target /caminho/do/repositorio \
  --test-cmd 'python -m pytest -q' \
  --bench-cmd 'python bench.py' \
  --generations 10 \
  --max-hypotheses 40 \
  --harness codex \
  --initial-prompt 'Concentre-se no parser crítico.'

uv run hypevolve serve --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000`. O painel mostra gerações na horizontal; cada
bolinha representa um indivíduo testado. Ao selecioná-la, aparecem o prompt,
a resposta (stdout) do harness e stdout/stderr/exit code do teste determinístico.

O terminal retorna JSON para facilitar a operação por agentes:

```bash
hypevolve sessions
hypevolve generations run-20260924T120000Z
hypevolve individual run-20260924T120000Z 3
hypevolve hypotheses run-20260924T120000Z
hypevolve hypothesis-add run-20260924T120000Z 'Memoizar o resultado do parser.'
hypevolve hypothesis-edit run-20260924T120000Z manual-... 'Nova formulação.'
hypevolve hypothesis-remove run-20260924T120000Z manual-...
```

Principais rotas REST: `GET /api/sessions`, `GET /api/sessions/{id}`,
`GET /api/sessions/{id}/generations`, `GET /api/sessions/{id}/individuals/{n}`
e CRUD em `/api/sessions/{id}/hypotheses`. `POST /api/sessions` aceita os mesmos
campos do subcomando `run` e inicia a execução em segundo plano.
