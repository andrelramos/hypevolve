import sys
from pathlib import Path

from hypevolve.evaluator import Evaluator

PY = sys.executable


def make_project(tmp_path: Path, test_code: str, bench_code: str) -> str:
    (tmp_path / "test_ok.py").write_text(test_code)
    (tmp_path / "bench.py").write_text(bench_code)
    return str(tmp_path)


PASS_TEST = "def test_ok():\n    assert True\n"
FAIL_TEST = "def test_ok():\n    assert False\n"


def bench_printing(value: float) -> str:
    return (
        "import time\n"
        f"time.sleep({value})\n"
        f"print({value})\n"
    )


def test_significant_improvement_yields_ratio_fitness(tmp_path):
    ws = make_project(tmp_path, PASS_TEST, bench_printing(0.01))
    e = Evaluator(
        test_cmd=f"{PY} -m pytest test_ok.py -q",
        bench_cmd=f"{PY} bench.py",
        repeats=10,
        warmup=1,
        timeout_seconds=60,
    )
    parent = [0.02] * 10
    r = e.evaluate(ws, parent)
    assert r.passed
    assert r.significant_speedup
    assert r.fitness > 1.5
    assert len(r.child_times) == 10


def test_no_change_scores_neutral_one(tmp_path):
    ws = make_project(tmp_path, PASS_TEST, bench_printing(0.01))
    e = Evaluator(f"{PY} -m pytest test_ok.py -q", f"{PY} bench.py", repeats=10, warmup=1, timeout_seconds=60)
    r = e.evaluate(ws, [0.01] * 10)
    assert r.passed
    assert not r.significant_speedup
    assert r.fitness == 1.0


def test_failing_tests_score_zero(tmp_path):
    ws = make_project(tmp_path, FAIL_TEST, bench_printing(0.01))
    e = Evaluator(f"{PY} -m pytest test_ok.py -q", f"{PY} bench.py", repeats=3, warmup=0, timeout_seconds=60)
    r = e.evaluate(ws, [0.02] * 10)
    assert not r.passed
    assert r.fitness == 0.0


def test_timeout_counts_as_failure(tmp_path):
    slow_test = "import time\ndef test_ok():\n    time.sleep(30)\n"
    ws = make_project(tmp_path, slow_test, bench_printing(0.01))
    e = Evaluator(f"{PY} -m pytest test_ok.py -q", f"{PY} bench.py", repeats=2, warmup=0, timeout_seconds=2)
    r = e.evaluate(ws, [])
    assert r.fitness == 0.0


def test_empty_parent_times_is_baseline(tmp_path):
    ws = make_project(tmp_path, PASS_TEST, bench_printing(0.01))
    e = Evaluator(f"{PY} -m pytest test_ok.py -q", f"{PY} bench.py", repeats=3, warmup=0, timeout_seconds=60)
    r = e.evaluate(ws, [])
    assert r.fitness == 1.0
    assert r.p_value is None
