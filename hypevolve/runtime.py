"""One execution entrypoint shared by the REST API and terminal CLI."""
from __future__ import annotations

import json
import random
import shutil
import statistics
from pathlib import Path

from .config import ExperimentConfig
from .evaluator import Evaluator
from .orchestrator import EvolutionEngine
from .store import ExecutionStore
from .workspace import WorkspaceManager


def run_experiment(cfg: ExperimentConfig, results_dir: Path, store: ExecutionStore | None = None):
    """Execute one run and leave complete, inspectable artifacts in ``results_dir``."""
    results_dir.mkdir(parents=True, exist_ok=True)
    session_id = results_dir.name
    if store:
        store.update_session(session_id, status="running", started_at=store.now())
    try:
        evaluator = Evaluator(cfg.test_cmd, cfg.bench_cmd, cfg.repeats, cfg.warmup,
                              cfg.timeout_seconds, cfg.alpha)
        reference_ws = results_dir / "reference"
        if reference_ws.exists():
            shutil.rmtree(reference_ws)
        shutil.copytree(cfg.source_path, reference_ws)
        baseline = evaluator.measure(str(reference_ws))
        if baseline is None:
            raise RuntimeError(f"baseline failed: tests or benchmark broken in {cfg.source_path}")
        (results_dir / "baseline.json").write_text(json.dumps({
            "source": cfg.source_path, "times": baseline,
            "median": statistics.median(baseline),
        }, indent=2), encoding="utf-8")
        engine = EvolutionEngine(
            workspaces=WorkspaceManager(results_dir / "workspaces", Path(cfg.source_path)),
            evaluator=evaluator, agent_cfg=cfg.agents[cfg.agent_name], selector_rng=random.Random(cfg.seed),
            results_dir=results_dir, generations=cfg.generations, population_size=cfg.population_size,
            elite_count=cfg.elite_count, tournament_k=cfg.tournament_k, seed=cfg.seed,
            protected_files=cfg.protected_files, baseline_times=baseline,
            max_parallel=cfg.max_parallel_agents, fitness_mode=cfg.fitness_mode,
            reference_workspace=str(reference_ws), max_hypotheses=cfg.max_hypotheses,
            **({"init_prompt": cfg.init_prompt} if cfg.init_prompt else {}),
            **({"mutation_prompt": cfg.mutation_prompt} if cfg.mutation_prompt else {}),
        )
        summary = engine.run()
        if store:
            store.update_session(session_id, status="completed", completed_at=store.now(),
                                 best_individual_id=summary.best_individual_id,
                                 best_speedup_vs_base=summary.best_speedup_vs_base)
        return summary
    except Exception as exc:
        if store:
            store.update_session(session_id, status="failed", completed_at=store.now(), error=str(exc))
        raise


def config_from_options(*, name: str, source_path: str, test_cmd: str, bench_cmd: str,
                        harness: str, model: str | None, generations: int,
                        max_hypotheses: int, initial_prompt: str = "", population_size: int = 4) -> ExperimentConfig:
    """Build a safe local-run config without forcing users to author YAML."""
    agent: dict[str, object] = {"kind": harness}
    if model:
        agent["model"] = model
    if harness not in {"codex", "claude"}:
        raise ValueError("harness must be 'codex' or 'claude'")
    effective_population = min(population_size, max_hypotheses) if max_hypotheses else population_size
    return ExperimentConfig(
        name=name, source_path=str(Path(source_path).resolve()), test_cmd=test_cmd, bench_cmd=bench_cmd,
        agent_name=harness, agents={harness: agent}, generations=generations,
        population_size=effective_population, elite_count=1,
        tournament_k=min(2, effective_population), max_hypotheses=max_hypotheses,
        init_prompt=initial_prompt,
    )
