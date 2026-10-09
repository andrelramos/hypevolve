"""Correctness + performance evaluation with a statistical significance gate."""
import statistics
import subprocess
from dataclasses import dataclass

from scipy.stats import mannwhitneyu

from hypevolve.models import EvaluationResult


@dataclass
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int | None


def _run(cmd: str, cwd: str, timeout: int) -> CommandResult:
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return CommandResult(False, "", f"command timed out after {timeout}s", None)
    return CommandResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)


def _last_float(stdout: str) -> float:
    lines = [ln.strip() for ln in stdout.strip().splitlines() if ln.strip()]
    if not lines:
        raise ValueError("benchmark produced no output")
    return float(lines[-1])


def compare(
    times: list[float], reference_times: list[float], alpha: float
) -> tuple[float | None, float, bool]:
    """Mann-Whitney one-sided gate on medians. Returns (p_value, ratio, significant)."""
    if not times or not reference_times:
        return None, 1.0, False
    p_value = float(mannwhitneyu(times, reference_times, alternative="less").pvalue)
    c_med, r_med = statistics.median(times), statistics.median(reference_times)
    significant = p_value < alpha and c_med < r_med
    ratio = r_med / c_med if c_med > 0 else 1.0
    return p_value, ratio, significant


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
        self.last_test_result = CommandResult(False, "", "not run", None)

    def measure(self, workspace: str) -> list[float] | None:
        """Run tests then the benchmark `repeats` times. None means the patch is broken."""
        self.last_test_result = _run(self.test_cmd, workspace, self.timeout)
        if not self.last_test_result.ok:
            return None
        for _ in range(self.warmup):
            _run(self.bench_cmd, workspace, self.timeout)
        times: list[float] = []
        for _ in range(self.repeats):
            bench = _run(self.bench_cmd, workspace, self.timeout)
            if not bench.ok:
                return None
            times.append(_last_float(bench.stdout))
        return times

    def measure_paired(
        self, workspace: str, reference_workspace: str
    ) -> tuple[list[float], list[float]] | None:
        """Time the patch and the pristine reference ALTERNATELY, in one pass.

        Machine load drifts (other agents, other arms, thermal). A baseline captured once
        at the start of a run and compared against patches measured 20 minutes later
        measures the machine, not the patch. Interleaving puts both sides under the same
        conditions sample by sample.
        """
        self.last_test_result = _run(self.test_cmd, workspace, self.timeout)
        if not self.last_test_result.ok:
            return None
        for _ in range(self.warmup):
            _run(self.bench_cmd, workspace, self.timeout)
            _run(self.bench_cmd, reference_workspace, self.timeout)

        times: list[float] = []
        ref_times: list[float] = []
        for i in range(self.repeats):
            first, second = (workspace, reference_workspace) if i % 2 == 0 else (reference_workspace, workspace)
            out = {}
            for ws in (first, second):
                bench = _run(self.bench_cmd, ws, self.timeout)
                if not bench.ok:
                    return None
                out[ws] = _last_float(bench.stdout)
            times.append(out[workspace])
            ref_times.append(out[reference_workspace])
        return times, ref_times

    def evaluate_paired(
        self,
        workspace: str,
        reference_workspace: str,
        parent_times: list[float],
    ) -> EvaluationResult:
        """Fitness from an interleaved head-to-head against the pristine reference."""
        measured = self.measure_paired(workspace, reference_workspace)
        if measured is None:
            return self._failed(parent_times)
        times, ref_times = measured

        p_base, ratio_base, sig_base = compare(times, ref_times, self.alpha)
        p_parent, ratio_parent, sig_parent = compare(times, list(parent_times), self.alpha)
        fitness = ratio_parent if sig_parent else 1.0
        return EvaluationResult(
            True, times, list(parent_times), p_parent, sig_parent, ratio_parent, fitness,
            speedup_vs_base=ratio_base,
            p_value_vs_base=p_base,
            significant_vs_base=sig_base,
            reference_times=ref_times, **self._test_fields()
        )

    def evaluate(
        self,
        workspace: str,
        parent_times: list[float],
        base_times: list[float] | None = None,
    ) -> EvaluationResult:
        times = self.measure(workspace)
        if times is None:
            return self._failed(parent_times)

        p_base, ratio_base, sig_base = compare(times, list(base_times or []), self.alpha)

        if not parent_times:
            return EvaluationResult(
                True, times, [], None, False, 1.0, 1.0,
                speedup_vs_base=ratio_base,
                p_value_vs_base=p_base,
                significant_vs_base=sig_base, **self._test_fields()
            )

        p_value, ratio, significant = compare(times, list(parent_times), self.alpha)
        fitness = ratio if significant else 1.0
        return EvaluationResult(
            True, times, list(parent_times), p_value, significant, ratio, fitness,
            speedup_vs_base=ratio_base,
            p_value_vs_base=p_base,
            significant_vs_base=sig_base, **self._test_fields()
        )

    def _test_fields(self) -> dict:
        return {
            "test_stdout": self.last_test_result.stdout,
            "test_stderr": self.last_test_result.stderr,
            "test_returncode": self.last_test_result.returncode,
        }

    def _failed(self, parent_times: list[float]) -> EvaluationResult:
        return EvaluationResult(
            False, [], list(parent_times), None, False, 0.0, 0.0, **self._test_fields()
        )
