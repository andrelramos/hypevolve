"""Correctness + performance evaluation with a statistical significance gate."""
import statistics
import subprocess

from scipy.stats import mannwhitneyu

from hypevolve.models import EvaluationResult


def _run(cmd: str, cwd: str, timeout: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False, ""
    return proc.returncode == 0, proc.stdout


def _last_float(stdout: str) -> float:
    lines = [ln.strip() for ln in stdout.strip().splitlines() if ln.strip()]
    if not lines:
        raise ValueError("benchmark produced no output")
    return float(lines[-1])


class Evaluator:
    def __init__(
        self,
        test_cmd: str,
        bench_cmd: str,
        repeats: int = 10,
        warmup: int = 1,
        timeout_seconds: int = 120,
        alpha: float = 0.05,
    ) -> None:
        self.test_cmd = test_cmd
        self.bench_cmd = bench_cmd
        self.repeats = repeats
        self.warmup = warmup
        self.timeout = timeout_seconds
        self.alpha = alpha

    def evaluate(self, workspace: str, parent_times: list[float]) -> EvaluationResult:
        ok, _ = _run(self.test_cmd, workspace, self.timeout)
        if not ok:
            return EvaluationResult(False, [], list(parent_times), None, False, 0.0, 0.0)

        for _ in range(self.warmup):
            _run(self.bench_cmd, workspace, self.timeout)

        times: list[float] = []
        for _ in range(self.repeats):
            ok_b, out = _run(self.bench_cmd, workspace, self.timeout)
            if not ok_b:
                return EvaluationResult(False, [], list(parent_times), None, False, 0.0, 0.0)
            times.append(_last_float(out))

        if not parent_times:
            return EvaluationResult(True, times, [], None, False, 1.0, 1.0)

        p_value = float(mannwhitneyu(times, parent_times, alternative="less").pvalue)
        c_mean, p_mean = statistics.mean(times), statistics.mean(parent_times)
        significant = p_value < self.alpha and c_mean < p_mean
        ratio = p_mean / c_mean if c_mean > 0 else 1.0
        fitness = ratio if significant else 1.0
        return EvaluationResult(True, times, list(parent_times), p_value, significant, ratio, fitness)
