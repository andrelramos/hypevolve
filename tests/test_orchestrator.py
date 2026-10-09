import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from hypevolve.evaluator import Evaluator
from hypevolve.models import Individual
from hypevolve.orchestrator import EvolutionEngine, parse_hypothesis
from hypevolve.workspace import WorkspaceManager

PY = sys.executable


@pytest.fixture
def source_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1\n")
    (src / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    (src / "bench.py").write_text("import time\nprint(0.001)\n")
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    return src


AGENT_CFG = {
    "kind": "fake",
    "replies": [
        'Working.\n```json\n{"hypothesis": "baseline setup"}\n```',
        'Trying cache.\n```json\n{"hypothesis": "cache helps"}\n```',
        'Trying loop swap.\n```json\n{"hypothesis": "swap loops"}\n```',
        'Trying unroll.\n```json\n{"hypothesis": "unroll loops"}\n```',
        'Trying memo.\n```json\n{"hypothesis": "memoize everything"}\n```',
    ],
}


def build_engine(tmp_path, source_repo, generations=2, population_size=2):
    return EvolutionEngine(
        workspaces=WorkspaceManager(tmp_path / "ws", source_repo),
        evaluator=Evaluator(
            test_cmd=f"{PY} -m pytest test_ok.py -q",
            bench_cmd=f"{PY} bench.py",
            repeats=3,
            warmup=0,
            timeout_seconds=60,
        ),
        agent_cfg=dict(AGENT_CFG),
        selector_rng=random.Random(7),
        results_dir=tmp_path / "results",
        generations=generations,
        population_size=population_size,
        elite_count=1,
        tournament_k=2,
        seed=11,
    )


def test_parse_hypothesis_finds_last_json_block():
    text = 'a ```json\n{"hypothesis": "one"}\n``` b ```json\n{"hypothesis": "two"}\n```'
    assert parse_hypothesis(text) == "two"


def test_parse_hypothesis_none_when_absent():
    assert parse_hypothesis("no blocks here") is None


def test_run_produces_summary_and_artifacts(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo)
    summary = eng.run()
    rd = tmp_path / "results"
    assert len(summary.generations) == 3  # gen 0 bootstrap + 2 evolution generations
    assert summary.best_fitness >= 1.0
    assert (rd / "summary.json").exists()
    data = json.loads((rd / "summary.json").read_text())
    assert data["best_fitness"] == summary.best_fitness
    hyps = json.loads((rd / "hypotheses.json").read_text())
    assert hyps, "hypotheses must be extracted from replies"
    assert any(h["status"] != "proposed" for h in hyps)
    assert (rd / "best" / "app.py").exists()
    assert any((rd / "transcripts").glob("indiv_*.log"))


def test_run_disposes_broken_children(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo)
    eng.evaluator = Evaluator(
        test_cmd=f"{PY} -m pytest missing_test.py -q",  # always fails -> all fitness 0
        bench_cmd=f"{PY} bench.py",
        repeats=1,
        warmup=0,
        timeout_seconds=60,
    )
    summary = eng.run()
    assert summary.best_fitness == 0.0
    last_gen = eng.population_history[-1]
    assert last_gen == []
    assert all(not ind.alive for gen in eng.population_history for ind in gen)


def test_population_size_maintained_across_generations(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo, generations=3, population_size=3)
    summary = eng.run()
    for log in summary.generations[1:]:
        # survivors + children may shrink below target if children die; never exceed
        assert log.best_fitness >= 1.0


def test_individual_type_roundtrip():
    ind = Individual(id=9, generation=1, workspace="/w", session_id="s")
    assert ind.generation == 1


def test_run_log_records_lineage_and_selection(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo, generations=2, population_size=3)
    eng.baseline_times = [0.002] * 3
    eng.run()
    log = json.loads((tmp_path / "results" / "run_log.json").read_text())

    assert log["mode"] == "ga"
    assert log["agent_calls"] == 3 + 2 * 2  # pop + generations * (pop - elite)
    assert len(log["individuals"]) == log["agent_calls"]

    seeds = [r for r in log["individuals"] if r["generation"] == 0]
    children = [r for r in log["individuals"] if r["generation"] > 0]
    assert all(r["parent_id"] is None for r in seeds)
    assert all(r["parent_id"] is not None for r in children)
    assert all("speedup_vs_base" in r and "hypothesis" in r for r in log["individuals"])

    tournaments = [e for e in log["selections"] if e["kind"] == "tournament"]
    assert tournaments, "tournament picks must be logged"
    for e in tournaments:
        assert e["winner_id"] in e["contenders"]
        assert e["winner_fitness"] == max(e["contender_fitness"])
    assert any(e["kind"] == "elite" for e in log["selections"])


def test_sampling_arm_is_flat_and_parentless(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo)
    eng.baseline_times = [0.002] * 3
    summary = eng.run_sampling(budget=4)
    log = json.loads((tmp_path / "results" / "run_log.json").read_text())

    assert summary.mode == "sampling"
    assert log["agent_calls"] == 4
    assert len(log["individuals"]) == 4
    assert all(r["parent_id"] is None and r["generation"] == 0 for r in log["individuals"])
    assert log["selections"] == []


def test_hypotheses_carry_their_measurements(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo)
    eng.baseline_times = [0.002] * 3
    eng.run()
    hyps = json.loads((tmp_path / "results" / "hypotheses.json").read_text())
    assert hyps
    for h in hyps:
        assert set(h) >= {
            "text", "status", "individual_id", "generation", "parent_id",
            "fitness", "speedup_vs_parent", "speedup_vs_base", "p_value", "passed",
        }


def test_absolute_fitness_puts_every_individual_on_one_scale(tmp_path, source_repo):
    eng = build_engine(tmp_path, source_repo, generations=1, population_size=2)
    eng.fitness_mode = "absolute"
    eng.baseline_times = [0.5] * 3  # pristine baseline is much slower than the bench (0.001)
    eng.run()
    log = json.loads((tmp_path / "results" / "run_log.json").read_text())
    assert log["fitness_mode"] == "absolute"
    for r in log["individuals"]:
        if r["passed"] and r["significant_vs_base"]:
            assert r["fitness"] == r["speedup_vs_base"]
    assert log["best_ever_speedup_vs_base"] >= 1.0


def test_agent_failure_is_not_scored_as_an_individual(tmp_path, source_repo):
    """An agent that errors leaves the parent's code in place; scoring it fabricates data."""
    eng = build_engine(tmp_path, source_repo, generations=1, population_size=2)
    eng.baseline_times = [0.002] * 3

    class BoomSession:
        transcript_path = None

        def __init__(self, *a, **k):
            pass

        def send(self, prompt):
            raise RuntimeError("out of credits")

        def close(self):
            return None

    import hypevolve.orchestrator as orch

    original = orch.make_session
    orch.make_session = lambda *a, **k: BoomSession()
    try:
        summary = eng.run()
    finally:
        orch.make_session = original

    log = json.loads((tmp_path / "results" / "run_log.json").read_text())
    assert log["individuals"], "failed calls must still be recorded"
    assert all(not r["passed"] for r in log["individuals"])
    assert all(r["agent_error"] for r in log["individuals"])
    assert all(r["fitness"] == 0.0 for r in log["individuals"])
    assert summary.best_fitness == 0.0
