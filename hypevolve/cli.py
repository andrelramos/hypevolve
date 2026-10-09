"""Human- and agent-friendly terminal interface for HypEvolve."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from .runtime import config_from_options, run_experiment
from .store import ExecutionStore


def _dump(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hypevolve", description="Run and inspect HypEvolve executions")
    parser.add_argument("--results-root", default="results")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sessions", help="list executions")
    show = commands.add_parser("show", help="show an execution")
    show.add_argument("session_id")
    generations = commands.add_parser("generations", help="show timeline data")
    generations.add_argument("session_id")
    individual = commands.add_parser("individual", help="show agent stdout, prompt and test result")
    individual.add_argument("session_id")
    individual.add_argument("individual_id", type=int)
    hypotheses = commands.add_parser("hypotheses", help="list hypotheses")
    hypotheses.add_argument("session_id")
    hyp_add = commands.add_parser("hypothesis-add", help="add a curated hypothesis")
    hyp_add.add_argument("session_id")
    hyp_add.add_argument("text")
    hyp_edit = commands.add_parser("hypothesis-edit", help="edit a hypothesis")
    hyp_edit.add_argument("session_id")
    hyp_edit.add_argument("hypothesis_id")
    hyp_edit.add_argument("text")
    hyp_remove = commands.add_parser("hypothesis-remove", help="remove a hypothesis")
    hyp_remove.add_argument("session_id")
    hyp_remove.add_argument("hypothesis_id")
    run = commands.add_parser("run", help="start an evolution against a local project")
    run.add_argument("--target", required=True, help="folder of the repository to optimize")
    run.add_argument("--test-cmd", required=True, help="deterministic Bash command; non-zero rejects a patch")
    run.add_argument("--bench-cmd", required=True, help="Bash command whose final stdout line is a duration in seconds")
    run.add_argument("--generations", required=True, type=int)
    run.add_argument("--max-hypotheses", required=True, type=int)
    run.add_argument("--harness", required=True, choices=["codex", "claude"])
    run.add_argument("--initial-prompt", default="")
    run.add_argument("--model")
    run.add_argument("--population-size", type=int, default=4)
    run.add_argument("--name")
    serve = commands.add_parser("serve", help="start the web panel and REST API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    store = ExecutionStore(args.results_root)
    if args.command == "sessions": _dump(store.list_sessions()); return
    if args.command == "show": _dump(store.session(args.session_id)); return
    if args.command == "generations": _dump(store.generations(args.session_id)); return
    if args.command == "individual": _dump(store.individual(args.session_id, args.individual_id)); return
    if args.command == "hypotheses": _dump(store.hypotheses(args.session_id)); return
    if args.command == "hypothesis-add": _dump(store.add_hypothesis(args.session_id, args.text)); return
    if args.command == "hypothesis-edit": _dump(store.update_hypothesis(args.session_id, args.hypothesis_id, args.text)); return
    if args.command == "hypothesis-remove": store.delete_hypothesis(args.session_id, args.hypothesis_id); return
    if args.command == "serve":
        import uvicorn
        from .server import create_app
        uvicorn.run(create_app(args.results_root), host=args.host, port=args.port)
        return
    if args.command == "run":
        session_id = args.name or datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")
        cfg = config_from_options(name=session_id, source_path=args.target, test_cmd=args.test_cmd,
                                  bench_cmd=args.bench_cmd, harness=args.harness, model=args.model,
                                  generations=args.generations, max_hypotheses=args.max_hypotheses,
                                  initial_prompt=args.initial_prompt, population_size=args.population_size)
        store.create_session(session_id, {"name": session_id, "source_path": cfg.source_path,
                                          "config": {"harness": args.harness, "test_cmd": args.test_cmd,
                                                     "bench_cmd": args.bench_cmd, "generations": args.generations,
                                                     "max_hypotheses": args.max_hypotheses}})
        summary = run_experiment(cfg, store.root / session_id, store)
        _dump({"session_id": session_id, "best_individual_id": summary.best_individual_id,
               "best_speedup_vs_base": summary.best_speedup_vs_base})
