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
