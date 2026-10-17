"""Evaluate OpenEvolve Tornado candidates with HypEvolve's paired GSO gate."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import uuid
from pathlib import Path

from hypevolve.evaluator import Evaluator, compare
from openevolve.evaluation_result import EvaluationResult


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable is missing: {name}")
    path = Path(value).resolve()
    if not path.exists():
        raise RuntimeError(f"configured path does not exist: {name}={path}")
    return path


def _quote(path: Path) -> str:
    return shlex.quote(str(path))


def evaluate(program_path: str) -> EvaluationResult:
    """Run correctness checks and paired timings for one generated module."""
    baseline = _required_path("GSO_TORNADO_BASELINE")
    workspace_root = _required_path("GSO_TORNADO_EVALUATION_ROOT")
    target_python = _required_path("GSO_TORNADO_PYTHON")
    scope_guard = _required_path("GSO_TORNADO_SCOPE_GUARD")

    candidate_source = Path(program_path).read_text(encoding="utf-8")
    workspace = workspace_root / f"candidate-{uuid.uuid4().hex}"
    shutil.copytree(baseline, workspace)
    (workspace / "tornado/concurrent.py").write_text(candidate_source, encoding="utf-8")

    test_cmd = " && ".join(
        (
            f"python3 {_quote(scope_guard)} --candidate . --baseline {_quote(baseline)}",
            f"{_quote(target_python)} gso_check.py",
            f"{_quote(target_python)} -m tornado.test.runtests tornado.test.concurrent_test",
        )
    )
    bench_cmd = f"{_quote(target_python)} gso_bench.py"
    evaluator = Evaluator(
        test_cmd=test_cmd,
        bench_cmd=bench_cmd,
        repeats=9,
        warmup=1,
        timeout_seconds=180,
        alpha=0.05,
    )

    measured = evaluator.measure_paired(str(workspace), str(baseline))
    if measured is None:
        test_result = evaluator.last_test_result
        return EvaluationResult(
            metrics={
                "combined_score": 0.0,
                "speedup_vs_baseline": 1.0,
                "p_value_vs_baseline": 1.0,
                "significant_vs_baseline": 0.0,
                "correct": 0.0,
            },
            artifacts={
                "validation": (
                    f"returncode={test_result.returncode}\n"
                    f"stdout:\n{test_result.stdout}\nstderr:\n{test_result.stderr}"
                )
            },
        )

    candidate_times, reference_times = measured
    p_value, speedup, significant = compare(candidate_times, reference_times, 0.05)
    fitness = speedup if significant else 1.0
    return EvaluationResult(
        metrics={
            "combined_score": fitness,
            "speedup_vs_baseline": speedup,
            "p_value_vs_baseline": p_value if p_value is not None else 1.0,
            "significant_vs_baseline": float(significant),
            "correct": 1.0,
        },
        artifacts={
            "candidate_times_seconds": json.dumps(candidate_times),
            "reference_times_seconds": json.dumps(reference_times),
            "scope_and_correctness": "scope guard, gso_check.py, and concurrent_test passed",
        },
    )
