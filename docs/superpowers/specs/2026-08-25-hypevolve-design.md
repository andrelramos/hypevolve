# HypEvolve — Design do Experimento

**Data:** 2026-08-25
**Status:** Aprovado pelo usuário
**Tipo:** Experimento empírico (paper científico) + framework de pesquisa

## Visão Geral

Framework que combina **algoritmos genéticos (AG)** com **agentes LLM via CLI**
(Claude Code, Codex, etc.) para otimizar o desempenho de software real. Cada
indivíduo da população é uma variante do código mantida por uma sessão
persistente de agente; o AG atua como validador empírico de hipóteses geradas
pelo LLM.

**Objetivo:** experimento sério com potencial de publicação internacional
(arXiv, ASE, GECCO, SBES), sem compromisso inicial. O framework também serve de
infraestrutura para um futuro agente autônomo de melhoria contínua de software
(paper 2 / produto).

## Posicionamento na literatura

Trabalhos relacionados a citar e diferenciar:

| Trabalho | O que faz | Diferencial do HypEvolve |
|---|---|---|
| Genetic Improvement (Petke et al.) | Evolução de código por mutações sintáticas | Mutações guiadas por hipóteses de LLM, não aleatórias |
| FunSearch (DeepMind 2023) | LLM + evolução descobre funções/matemática nova | Foco em melhoria de software real existente + hipóteses explícitas |
| AlphaEvolve (DeepMind 2025) | Agente evolutivo para descoberta de algoritmos | Sessões persistentes com contexto acumulado por indivíduo; validação explícita de hipóteses |
| EoH / ReEvo | LLM evolui heurísticas | Domínio: otimização de código existente, não heurísticas |

**Diferenciais reivindicados:**
1. Hipóteses textuais explícitas anexadas a cada patch, validadas empiricamente e realimentadas na busca.
2. Indivíduo = sessão persistente de agente CLI com workspace próprio (contexto acumula entre gerações).
3. Avaliação sob mesmo orçamento contra baselines fortes (LLM one-shot, busca aleatória).

## Perguntas de Pesquisa

- **RQ1:** O loop evolutivo AG+LLM com hipóteses explícitas melhora o desempenho
  mais do que otimização direta por LLM (one-shot/few-shot) e busca aleatória,
  sob o mesmo orçamento de avaliações?
- **RQ2:** O ganho observado é independente do LLM/agente usado como gerador?
  (Claude vs Codex vs outro)
- **RQ3:** O rastreamento de hipóteses acelera a convergência da busca? (ablação
  com/sem hypothesis tracker)

## Métricas

- **Primária:** speedup relativo no tempo de execução dos benchmarks-alvo.
- **Secundárias:**
  - Nº de avaliações até atingir limiares de ganho (ex: 10%, 20%);
  - Taxa de patches funcionais (passam suíte de testes);
  - Custo (tokens/US$) por ponto percentual de ganho;
  - Convergência: melhor fitness por geração (curvas).

## Arquitetura

```
Orchestrator (loop GA)
├── Agent Session Manager   — 1 sessão CLI persistente POR INDIVÍDUO;
│                             prompts incrementais; sessão vive enquanto o
│                             indivíduo está na população
├── Workspace Manager       — cópia isolada do projeto por indivíduo
├── Evaluator               — sandbox: aplica patch, roda testes (corretude)
│                             + benchmark (fitness), com timeout e limites
├── Fitness + Stats         — ganho só vale se estatisticamente significativo
│                             vs pai: Mann-Whitney U (α=0,05) sobre N≥10
│                             repetições do benchmark com warm-up
├── Selector                — elitismo (1) + torneio; população ~8
└── Hypothesis Tracker      — log de hipóteses confirmadas/refutadas/
                              inconclusivas; confirmações priorizadas no
                              contexto das próximas mutações
```

### Fluxo por geração

1. **Selector** escolhe pais.
2. **Prompt de mutação** enviado à sessão CLI do pai: estado atual, fitness,
   hotspots de profiling, hipóteses já testadas, instrução de propor mudança +
   hipótese explícita em formato estruturado (`{"hypothesis": "...", "patch": ...}`).
3. Agente edita o próprio workspace.
4. **Evaluator** valida corretude (testes) e mede desempenho (benchmark).
   Patch quebrado = fitness 0.
5. **Fitness + Stats** compara vs pai com teste de significância.
6. **Hypothesis Tracker** registra resultado da hipótese.
7. Indivíduo eliminado → sessão encerrada. Novo indivíduo → herda resumo do
   pai via prompt inicial (crossover textual).

### Decisões técnicas

- Python 3.12+.
- Integração LLM **via CLIs de agentes em terminais persistentes** (claude,
  codex...), um terminal por indivíduo — sem litellm nem APIs diretas. O
  experimento orquestra os clientes; a integração de cada modelo é
  responsabilidade do CLI.
- Workspaces isolados por indivíduo; subprocessos com timeout e limites de
  recursos (proteção contra loops infinitos/comportamento perigoso).
- Logging completo: todos os prompts, respostas e transcripts das sessões são
  salvos como dados do experimento (compensam a menor previsibilidade de custo/
  tokens dos CLIs).
- Reprodutibilidade: versões exatas dos CLIs/modelos pinadas nos configs.

## Protocolo Experimental

- **Projetos-alvo:** 4–6 repositórios Python open-source conhecidos, pequenos/
  médios (<50k linhas), com suíte de testes própria rodando <2min e hotspots
  identificáveis. Seleção final documentada com critério objetivo no paper.
- **Configuração do AG:** população ~8, gerações 10–15, elitismo 1, torneio.
- **Orçamento fixo:** ~100 avaliações por execução, idêntico para todas as condições.
- **Condições** (por projeto × agente):
  | Condição | Descrição |
  |---|---|
  | Baseline 1 | LLM one-shot + 3 refinamentos few-shot |
  | Baseline 2 | Busca aleatória de mutações sintáticas |
  | Tratamento | GA+LLM completo com hipóteses |
  | Ablação RQ3 | GA+LLM sem hypothesis tracker |
- **Rigor estatístico:**
  - 30 execuções independentes por condição (fase piloto: 15);
  - Mann-Whitney U / Kruskal-Wallis + correção de Bonferroni;
  - Effect size Vargha-Delaney Â12 ou Cliff's delta;
  - Benchmark: média de N repetições com warm-up, outliers tratados e documentados.
- **Custo estimado:** algumas centenas de dólares no total (orçamento flexível);
  piloto reduz à metade.

## Estrutura do Repositório

```
algoritmos-geneticos-com-llm/
├── docs/
│   ├── superpowers/specs/        # specs (esta doc)
│   └── research/                 # notas, referências
├── paper/                        # LaTeX, template ACM (acmart)
│   ├── main.tex
│   ├── sections/                 # intro, related-work, method, results...
│   └── figures/
├── hypevolve/                    # framework (pacote Python)
│   ├── orchestrator.py           # loop GA
│   ├── session_manager.py        # sessões CLI persistentes
│   ├── workspace.py              # workspaces isolados
│   ├── evaluator.py              # sandbox, testes, benchmark
│   ├── selector.py
│   └── hypothesis_tracker.py
├── experiments/
│   ├── configs/                  # YAML por condição experimental
│   ├── runners/                  # scripts por RQ
│   └── analysis/                 # análise estatística
├── targets/                      # projetos-alvo (commit pinado)
└── results/                      # dados brutos JSON + transcripts
```

## Estrutura do Paper (inglês)

1. Abstract
2. Introduction — agentes autônomos de melhoria contínua; contribuições
3. Background & Related Work — GI, FunSearch/AlphaEvolve, agentes LLM; tabela comparativa
4. Approach — arquitetura, loop de hipóteses, protocolo CLI
5. Study Design — RQs, objetos, baselines, métricas, estatística
6. Results — uma seção por RQ
7. Discussion — implicações, ameaças à validade (interna, externa, construto, reprodutibilidade)
8. Conclusion & Future Work — multi-objetivo (custo, qualidade), agente autônomo contínuo

## Roadmap de Alto Nível

1. Setup do repo + seleção dos projetos-alvo (critério objetivo)
2. Implementar framework mínimo (loop GA + sessões CLI + evaluator)
3. Piloto (1 projeto, 15 runs) — validar pipeline e custo
4. Execução completa das condições
5. Análise estatística
6. Escrita do paper

## Fora de escopo (deste paper)

- Multi-objetivo (custo, qualidade de código) → future work / paper 2
- Ciclo autônomo contínuo em produção → visão de produto, não deste experimento
