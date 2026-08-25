"""CLI entrypoint: python -m hypevolve --config experiments/configs/foo.yaml"""
import argparse
import random
from pathlib import Path

from .config import ExperimentConfig
from .evaluator import Evaluator
from .orchestrator import EvolutionEngine
from .workspace import WorkspaceManager


def main() -> None:
    ap = argparse.ArgumentParser(prog="hypevolve")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = ExperimentConfig.load(args.config)
    results_dir = Path(cfg.results_root) / cfg.name
    engine = EvolutionEngine(
        workspaces=WorkspaceManager(results_dir / "workspaces", Path(cfg.source_path)),
        evaluator=Evaluator(
            test_cmd=cfg.test_cmd,
            bench_cmd=cfg.bench_cmd,
            repeats=cfg.repeats,
            warmup=cfg.warmup,
            timeout_seconds=cfg.timeout_seconds,
            alpha=cfg.alpha,
        ),
        agent_cfg=cfg.agents[cfg.agent_name],
        selector_rng=random.Random(cfg.seed),
        results_dir=results_dir,
        generations=cfg.generations,
        population_size=cfg.population_size,
        elite_count=cfg.elite_count,
        tournament_k=cfg.tournament_k,
        seed=cfg.seed,
    )
    summary = engine.run()
    print(f"best individual: {summary.best_individual_id}")
    print(f"best fitness:    {summary.best_fitness:.4f}")
    print(f"artifacts:       {results_dir}")


if __name__ == "__main__":
    main()
