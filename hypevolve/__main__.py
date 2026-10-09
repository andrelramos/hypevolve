"""Legacy config runner plus the command-oriented HypEvolve CLI."""
import argparse
import json
import random
import shutil
import statistics
import sys
from pathlib import Path

from .config import ExperimentConfig
from .evaluator import Evaluator
from .orchestrator import EvolutionEngine
from .workspace import WorkspaceManager


def main() -> None:
    command_names = {"sessions", "show", "generations", "individual", "hypotheses", "hypothesis-add", "hypothesis-edit", "hypothesis-remove", "run", "serve"}
    if len(sys.argv) > 1 and sys.argv[1] in command_names:
        from .cli import main as cli_main
        cli_main(sys.argv[1:])
        return
    ap = argparse.ArgumentParser(prog="hypevolve")
    ap.add_argument("--config", required=True)
    ap.add_argument(
        "--mode",
        choices=["ga", "sampling"],
        default="ga",
        help="ga: evolution with lineage. sampling: N independent single-shot agents (control arm).",
    )
    ap.add_argument(
        "--budget",
        type=int,
        default=0,
        help="sampling mode only: number of agents. 0 = match the GA call budget.",
    )
    ap.add_argument("--suffix", default="", help="appended to the results directory name")
    ap.add_argument(
        "--fitness-mode",
        choices=["relative", "absolute"],
        default=None,
        help="relative: child scored against its parent. absolute: everyone scored against the baseline.",
    )
    args = ap.parse_args()

    cfg = ExperimentConfig.load(args.config)
    results_dir = Path(cfg.results_root) / (cfg.name + args.suffix)
    results_dir.mkdir(parents=True, exist_ok=True)

    evaluator = Evaluator(
        test_cmd=cfg.test_cmd,
        bench_cmd=cfg.bench_cmd,
        repeats=cfg.repeats,
        warmup=cfg.warmup,
        timeout_seconds=cfg.timeout_seconds,
        alpha=cfg.alpha,
    )

    # A pristine copy that never gets patched: every individual is timed against it,
    # interleaved, so machine drift cancels instead of being scored as a speedup.
    reference_ws = results_dir / "reference"
    if reference_ws.exists():
        shutil.rmtree(reference_ws)
    shutil.copytree(cfg.source_path, reference_ws)

    baseline = evaluator.measure(str(reference_ws))
    if baseline is None:
        raise SystemExit(f"baseline failed: tests or benchmark broken in {cfg.source_path}")
    print(f"baseline median: {statistics.median(baseline):.6f}s over {len(baseline)} runs")
    (results_dir / "baseline.json").write_text(
        json.dumps({"source": cfg.source_path, "times": baseline}, indent=2)
    )

    engine = EvolutionEngine(
        workspaces=WorkspaceManager(results_dir / "workspaces", Path(cfg.source_path)),
        evaluator=evaluator,
        agent_cfg=cfg.agents[cfg.agent_name],
        selector_rng=random.Random(cfg.seed),
        results_dir=results_dir,
        generations=cfg.generations,
        population_size=cfg.population_size,
        elite_count=cfg.elite_count,
        tournament_k=cfg.tournament_k,
        seed=cfg.seed,
        protected_files=cfg.protected_files,
        baseline_times=baseline,
        max_parallel=cfg.max_parallel_agents,
        fitness_mode=args.fitness_mode or cfg.fitness_mode,
        reference_workspace=str(reference_ws),
        max_hypotheses=cfg.max_hypotheses,
        **({"init_prompt": cfg.init_prompt} if cfg.init_prompt else {}),
        **({"mutation_prompt": cfg.mutation_prompt} if cfg.mutation_prompt else {}),
    )

    if args.mode == "sampling":
        budget = args.budget or (
            cfg.population_size + cfg.generations * (cfg.population_size - cfg.elite_count)
        )
        print(f"sampling arm: {budget} independent agents")
        summary = engine.run_sampling(budget)
    else:
        summary = engine.run()

    print(f"mode:              {summary.mode}")
    print(f"agent calls:       {engine.agent_calls}")
    print(f"best individual:   {summary.best_individual_id}")
    print(f"best fitness:      {summary.best_fitness:.4f}")
    print(f"best vs baseline:  {summary.best_speedup_vs_base:.4f}x")
    log = json.loads((results_dir / "run_log.json").read_text())
    print(f"best ever:         indiv {log['best_ever_id']} at {log['best_ever_speedup_vs_base']:.4f}x vs base")
    print(f"artifacts:         {results_dir}")


if __name__ == "__main__":
    main()
