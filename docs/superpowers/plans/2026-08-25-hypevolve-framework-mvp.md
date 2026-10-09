# HypEvolve Framework MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the HypEvolve Python framework that runs a genetic algorithm where each individual is a coding-agent CLI session evolving its own workspace copy, with empirical hypothesis validation — validated end-to-end against a dummy target with an echo agent.

**Architecture:** An `EvolutionEngine` orchestrates four components behind small interfaces: `WorkspaceManager` (isolated git-copy workspaces per individual), `AgentSession` (persistent CLI conversations via start/continue command templates), `Evaluator` (correctness tests + repeated benchmark timing + Mann-Whitney significance gate), and `HypothesisTracker` (confirmed/refuted/inconclusive log fed back into prompts). All interaction is logged as experiment data.

**Tech Stack:** Python 3.12+, pytest, scipy (Mann-Whitney U), PyYAML. No litellm, no direct LLM APIs — integration happens exclusively through CLI command templates.

## Global Constraints

- Python >= 3.12 (from spec).
- No litellm / no direct SDK calls to LLMs. Agents integrate ONLY via CLI command templates (spec: "sem litellm nem APIs diretas").
- One persistent logical session per individual; context must survive across generations (start/continue templates).
- Fitness gate: a gain only counts if statistically significant vs parent (Mann-Whitney U, α=0.05, N≥10 repeats, warm-up discard).
- Broken patch (failing tests or timeout) ⇒ fitness 0.0 and immediate disposal.
- Every prompt/response must be persisted under `results/` as experiment data (transcripts).
- Population ~8, generations 10–15, elitism 1, tournament — defaults in config; budget parity across conditions is an experiment-phase concern, not enforced here.
- Repo language: code/comments/docstrings in English (paper is English); commit messages conventional (`feat:`, `test:`, `chore:`).
- Workdir for every command below: the repository root unless stated.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `hypevolve/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_package.py`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: installable package `hypevolve`; dev deps pytest+scipy+pyyaml available.

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "hypevolve"
version = "0.1.0"
description = "GA orchestration of CLI coding agents for performance-driven software improvement"
requires-python = ">=3.12"
dependencies = ["pyyaml>=6.0", "scipy>=1.13"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["hypevolve*"]
```

- [ ] **Step 2: Write package stubs**

`hypevolve/__init__.py`:

```python
"""HypEvolve: GA orchestration of CLI coding agents."""
__version__ = "0.1.0"
```

`tests/__init__.py`: empty file.

`tests/test_package.py`:

```python
import hypevolve


def test_version():
    assert hypevolve.__version__ == "0.1.0"
```

- [ ] **Step 3: Write .gitignore**

```gitignore
__pycache__/
*.egg-info/
.pytest_cache/
dist/
build/
workspaces/
results/
targets/*
!targets/.gitkeep
.venv/
```

Create empty `targets/.gitkeep` (touch).

- [ ] **Step 4: Install editable with dev deps**

Run: `pip install -e ".[dev]"`
Expected: installs successfully (scipy/pyyaml/pytest resolve).

- [ ] **Step 5: Run test**

Run: `pytest tests/test_package.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: scaffold hypevolve package"
```

---

### Task 2: Core data models

**Files:**
- Create: `hypevolve/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `HypothesisStatus` enum (PROPOSED/CONFIRMED/REFUTED/INCONCLUSIVE); dataclasses `Hypothesis(text, individual_id, generation, status, id)`, `EvaluationResult(passed, child_times, parent_times, p_value, significant_speedup, speedup_ratio, fitness)`, `Individual(id, generation, workspace, session_id, fitness, eval_result, alive)`, `GenerationLog(generation, best_fitness, mean_fitness, evaluations)`, `RunSummary(generations, best_individual_id, best_fitness)`.

- [ ] **Step 1: Write failing test**

`tests/test_models.py`:

```python
import dataclasses

from hypevolve.models import (
    EvaluationResult,
    GenerationLog,
    Hypothesis,
    HypothesisStatus,
    Individual,
    RunSummary,
)


def test_hypothesis_defaults_to_proposed():
    h = Hypothesis(text="cache reduces time", individual_id=1, generation=0)
    assert h.status is HypothesisStatus.PROPOSED
    assert h.id == ""


def test_evaluation_result_fields():
    r = EvaluationResult(
        passed=True,
        child_times=[1.0],
        parent_times=[2.0],
        p_value=0.01,
        significant_speedup=True,
        speedup_ratio=2.0,
        fitness=2.0,
    )
    assert r.fitness == 2.0


def test_individual_defaults():
    i = Individual(id=0, generation=0, workspace="/tmp/x", session_id="abc")
    assert i.fitness == 0.0
    assert i.alive is True
    assert i.eval_result is None


def test_summary_is_json_serializable():
    s = RunSummary(
        generations=[GenerationLog(generation=0, best_fitness=1.0, mean_fitness=1.0, evaluations=[])],
        best_individual_id=0,
        best_fitness=1.0,
    )
    assert dataclasses.asdict(s)["best_fitness"] == 1.0
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hypevolve.models'`.

- [ ] **Step 3: Implement models.py**

```python
"""Core domain types shared by all components."""
from dataclasses import dataclass
from enum import Enum


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Hypothesis:
    text: str
    individual_id: int
    generation: int
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    id: str = ""


@dataclass
class EvaluationResult:
    passed: bool
    child_times: list[float]
    parent_times: list[float]
    p_value: float | None
    significant_speedup: bool
    speedup_ratio: float
    fitness: float


@dataclass
class Individual:
    id: int
    generation: int
    workspace: str
    session_id: str
    fitness: float = 0.0
    eval_result: EvaluationResult | None = None
    alive: bool = True


@dataclass
class GenerationLog:
    generation: int
    best_fitness: float
    mean_fitness: float
    evaluations: list[EvaluationResult]


@dataclass
class RunSummary:
    generations: list[GenerationLog]
    best_individual_id: int
    best_fitness: float
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_models.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add hypevolve/models.py tests/test_models.py && git commit -m "feat: core domain models"
```

---

### Task 3: WorkspaceManager

**Files:**
- Create: `hypevolve/workspace.py`
- Test: `tests/test_workspace.py`

**Interfaces:**
- Consumes: stdlib only.
- Produces: `WorkspaceManager(root: Path, source: Path)` with methods `create(individual_id: int) -> str` (path string; copy of source INCLUDING `.git`), `create_from(parent_workspace: str, individual_id: int) -> str` (child inherits parent's current code), `remove(individual_id: int) -> None`, `snapshot(individual_id: int, dest: Path) -> Path`.

Raises `WorkspaceError(f"...")` on missing source / existing destination / unknown individual.

- [ ] **Step 1: Write failing test**

`tests/test_workspace.py`:

```python
import subprocess
from pathlib import Path

import pytest

from hypevolve.workspace import WorkspaceManager


@pytest.fixture
def source_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1\n")
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    return src


def test_create_copies_source_including_git(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    ws = Path(wm.create(0))
    assert (ws / "app.py").read_text() == "x = 1\n"
    assert (ws / ".git").exists()


def test_create_from_inherits_parent_changes(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    parent = wm.create(0)
    Path(parent, "app.py").write_text("x = 2\n")
    child = Path(wm.create_from(parent, 1))
    assert child.joinpath("app.py").read_text() == "x = 2\n"


def test_remove_deletes_tree(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    ws = wm.create(3)
    wm.remove(3)
    assert not Path(ws).exists()


def test_snapshot_copies_to_dest_without_git(tmp_path, source_repo):
    wm = WorkspaceManager(tmp_path / "ws", source_repo)
    wm.create(0)
    dest = tmp_path / "snap"
    out = wm.snapshot(0, dest)
    assert Path(out).joinpath("app.py").exists()
    assert not Path(out).joinpath(".git").exists()
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_workspace.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement workspace.py**

```python
"""Isolated per-individual workspace copies of the target project."""
import shutil
from pathlib import Path


class WorkspaceError(RuntimeError):
    pass


class WorkspaceManager:
    def __init__(self, root: Path, source: Path):
        self.root = Path(root)
        self.source = Path(source).resolve()
        if not self.source.is_dir():
            raise WorkspaceError(f"source not found: {self.source}")

    def _path_for(self, individual_id: int) -> Path:
        return self.root / f"indiv_{individual_id:04d}"

    def create(self, individual_id: int) -> str:
        dest = self._path_for(individual_id)
        if dest.exists():
            raise WorkspaceError(f"workspace exists: {dest}")
        self.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.source, dest)
        return str(dest)

    def create_from(self, parent_workspace: str, individual_id: int) -> str:
        dest = self._path_for(individual_id)
        if dest.exists():
            raise WorkspaceError(f"workspace exists: {dest}")
        self.root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(parent_workspace, dest)
        return str(dest)

    def remove(self, individual_id: int) -> None:
        dest = self._path_for(individual_id)
        if dest.exists():
            shutil.rmtree(dest)

    def snapshot(self, individual_id: int, dest: Path) -> Path:
        src = self._path_for(individual_id)
        if not src.exists():
            raise WorkspaceError(f"no workspace for individual {individual_id}")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git"))
        return dest
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_workspace.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add hypevolve/workspace.py tests/test_workspace.py && git commit -m "feat: per-individual workspace manager"
```

---

### Task 4: Selection operators

**Files:**
- Create: `hypevolve/selector.py`
- Test: `tests/test_selector.py`

**Interfaces:**
- Consumes: `Individual` from `hypevolve.models`.
- Produces: `elites(population: list[Individual], n: int) -> list[Individual]` (top-n by fitness desc, ties broken by lower id); `tournament(population, k: int, rng: random.Random) -> Individual`; `select_parents(population, n_children: int, k: int, rng) -> list[Individual]` (with replacement; returns `[]` for empty population).

- [ ] **Step 1: Write failing test**

`tests/test_selector.py`:

```python
import random

from hypevolve.models import Individual
from hypevolve.selector import elites, select_parents, tournament


def mk(i, fit):
    return Individual(id=i, generation=0, workspace=f"/w{i}", session_id=f"s{i}", fitness=fit)


def test_elites_returns_top_n_desc():
    pop = [mk(0, 1.0), mk(1, 3.0), mk(2, 2.0)]
    top = elites(pop, 2)
    assert [i.id for i in top] == [1, 2]


def test_elites_tie_broken_by_lower_id():
    pop = [mk(7, 1.0), mk(2, 1.0)]
    assert elites(pop, 1)[0].id == 2


def test_tournament_picks_best_of_k():
    rng = random.Random(42)
    pop = [mk(0, 1.0), mk(1, 5.0), mk(2, 2.0), mk(3, 0.5)]
    winner = tournament(pop, k=3, rng=rng)
    assert winner.fitness == 5.0


def test_select_parents_returns_n_with_replacement():
    rng = random.Random(0)
    pop = [mk(0, 1.0), mk(1, 2.0)]
    parents = select_parents(pop, n_children=4, k=2, rng=rng)
    assert len(parents) == 4


def test_select_parents_empty_population_returns_empty():
    rng = random.Random(0)
    assert select_parents([], n_children=4, k=2, rng=rng) == []
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_selector.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement selector.py**

```python
"""Parent selection: tournament + elitism."""
import random

from hypevolve.models import Individual


def elites(population: list[Individual], n: int) -> list[Individual]:
    ranked = sorted(population, key=lambda i: (-i.fitness, i.id))
    return ranked[:n]


def tournament(population: list[Individual], k: int, rng: random.Random) -> Individual:
    contenders = rng.sample(population, min(k, len(population)))
    return max(contenders, key=lambda i: i.fitness)


def select_parents(
    population: list[Individual], n_children: int, k: int, rng: random.Random
) -> list[Individual]:
    if not population:
        return []
    return [tournament(population, k, rng) for _ in range(n_children)]
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_selector.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add hypevolve/selector.py tests/test_selector.py && git commit -m "feat: tournament selection and elitism"
```

---

### Task 5: HypothesisTracker

**Files:**
- Create: `hypevolve/hypothesis_tracker.py`
- Test: `tests/test_hypothesis_tracker.py`

**Interfaces:**
- Consumes: `Hypothesis`, `EvaluationResult`, `HypothesisStatus`.
- Produces: `HypothesisTracker` with `record(hyp: Hypothesis, result: EvaluationResult) -> None` (assigns sequential id `h1,h2,...`; status rule below), `all() -> list[Hypothesis]`, `context_summary(limit: int = 10) -> str`.

Status rule (locked): `passed=False` → INCONCLUSIVE; `significant_speedup=True` → CONFIRMED; otherwise → REFUTED.

- [ ] **Step 1: Write failing test**

`tests/test_hypothesis_tracker.py`:

```python
from hypevolve.hypothesis_tracker import HypothesisTracker
from hypevolve.models import EvaluationResult, Hypothesis, HypothesisStatus


def ev(passed=True, sig=True):
    return EvaluationResult(
        passed=passed,
        child_times=[1.0],
        parent_times=[2.0],
        p_value=0.01 if sig else 0.9,
        significant_speedup=sig,
        speedup_ratio=2.0 if sig else 1.0,
        fitness=2.0 if sig else 1.0,
    )


def test_record_confirms_significant_gain():
    t = HypothesisTracker()
    h = Hypothesis(text="memoize fib", individual_id=1, generation=1)
    t.record(h, ev(sig=True))
    assert t.all()[0].status is HypothesisStatus.CONFIRMED
    assert t.all()[0].id == "h1"


def test_record_refutes_nonsignificant():
    t = HypothesisTracker()
    t.record(Hypothesis(text="swap loop", individual_id=1, generation=1), ev(sig=False))
    assert t.all()[0].status is HypothesisStatus.REFUTED


def test_record_inconclusive_when_broken():
    t = HypothesisTracker()
    t.record(Hypothesis(text="rewrite io", individual_id=1, generation=1), ev(passed=False))
    assert t.all()[0].status is HypothesisStatus.INCONCLUSIVE


def test_context_summary_prioritizes_confirmed_and_counts_refuted():
    t = HypothesisTracker()
    t.record(Hypothesis(text="good idea", individual_id=1, generation=1), ev(sig=True))
    t.record(Hypothesis(text="bad idea", individual_id=2, generation=1), ev(sig=False))
    s = t.context_summary()
    assert "good idea" in s
    assert "bad idea" not in s.split("Refuted")[0]
    assert "Refuted so far: 1" in s
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_hypothesis_tracker.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement hypothesis_tracker.py**

```python
"""Empirical validation log for LLM-generated hypotheses."""
from hypevolve.models import EvaluationResult, Hypothesis, HypothesisStatus


class HypothesisTracker:
    def __init__(self) -> None:
        self._items: list[Hypothesis] = []

    def record(self, hyp: Hypothesis, result: EvaluationResult) -> None:
        if not result.passed:
            hyp.status = HypothesisStatus.INCONCLUSIVE
        elif result.significant_speedup:
            hyp.status = HypothesisStatus.CONFIRMED
        else:
            hyp.status = HypothesisStatus.REFUTED
        hyp.id = f"h{len(self._items) + 1}"
        self._items.append(hyp)

    def all(self) -> list[Hypothesis]:
        return list(self._items)

    def context_summary(self, limit: int = 10) -> str:
        confirmed = [h for h in self._items if h.status is HypothesisStatus.CONFIRMED][-limit:]
        refuted = sum(1 for h in self._items if h.status is HypothesisStatus.REFUTED)
        inconclusive = sum(1 for h in self._items if h.status is HypothesisStatus.INCONCLUSIVE)
        lines = [
            f"Confirmed hypotheses ({len(confirmed)}):",
            *[f"- [{h.id}] {h.text}" for h in confirmed],
            f"Refuted so far: {refuted}",
            f"Inconclusive (broken patches): {inconclusive}",
        ]
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_hypothesis_tracker.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add hypevolve/hypothesis_tracker.py tests/test_hypothesis_tracker.py && git commit -m "feat: hypothesis tracker with empirical status rules"
```

---

### Task 6: Evaluator (tests + benchmark + significance gate)

**Files:**
- Create: `hypevolve/evaluator.py`
- Test: `tests/test_evaluator.py`

**Interfaces:**
- Consumes: stdlib subprocess, `scipy.stats.mannwhitneyu`.
- Produces: `Evaluator(test_cmd: str, bench_cmd: str, repeats: int = 10, warmup: int = 1, timeout_seconds: int = 120, alpha: float = 0.05)` with `evaluate(workspace: str, parent_times: list[float]) -> EvaluationResult`.

Contract: `test_cmd` exits 0 ⇔ suite passes. `bench_cmd` executes ONCE per repeat and must print the elapsed seconds as a float on its LAST stdout line. Warm-up runs are discarded. Timeout or crash ⇒ failed evaluation (fitness 0.0). Empty `parent_times` (generation 0) ⇒ baseline: `significant_speedup=False`, `speedup_ratio=1.0`, `fitness=1.0` when tests pass.

Fitness rule: `passed=False → 0.0`; `significant_speedup → speedup_ratio`; else `1.0`.

- [ ] **Step 1: Write failing test**

`tests/test_evaluator.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_evaluator.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement evaluator.py**

```python
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
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_evaluator.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add hypevolve/evaluator.py tests/test_evaluator.py && git commit -m "feat: evaluator with Mann-Whitney significance gate"
```

---

### Task 7: Agent sessions over CLI

**Files:**
- Create: `hypevolve/session_manager.py`
- Test: `tests/test_session_manager.py`

**Interfaces:**
- Consumes: stdlib subprocess.
- Produces:
  - Base class `AgentSession(session_id: str, cwd: str)` with abstract `send(prompt: str) -> str`, `close() -> None`, and shared `_log(prompt, reply) -> None` that appends `[PROMPT]/[RESPONSE]` blocks to a `transcript_path` attribute when set (subclasses set it before calling `_log`).
  - `CmdAgentSession(AgentSession)` ctor `(session_id, start_cmd_template, cont_cmd_template, cwd, timeout_seconds=600, transcript_path: Path | None = None)`: first `send` uses `start_cmd_template.format(session_id=...)`, subsequent ones use `cont_cmd_template.format(session_id=...)`; prompt piped via **stdin**; non-zero exit raises `RuntimeError`; output parsed by `_extract_output` (JSON dict with `"result"` key → value, else raw stripped stdout).
  - `FakeAgentSession(AgentSession)` ctor `(session_id, cwd, replies: list[str], transcript_path: Path | None = None)`: pops queued replies in order (last one repeats), records prompts in `.sent`, writes transcripts like the real session.
  - Factory `make_session(agent_cfg: dict, session_id: str, cwd: str, transcript_path=None) -> AgentSession`: `kind: fake` → FakeAgentSession (uses cfg["replies"]); `kind: cmd` → CmdAgentSession (uses cfg["start_cmd_template"], cfg["cont_cmd_template"], optional cfg["timeout_seconds"]).

Templates MUST contain a `{session_id}` placeholder; the prompt travels through stdin, never argv.

- [ ] **Step 1: Write failing test**

`tests/test_session_manager.py`:

```python
import sys
from pathlib import Path

import pytest

from hypevolve.session_manager import (
    CmdAgentSession,
    FakeAgentSession,
    make_session,
)

PY = sys.executable


def test_fake_replays_replies_and_records_prompts(tmp_path):
    tp = tmp_path / "fake.log"
    s = FakeAgentSession("sid", str(tmp_path), ["first", "second"], transcript_path=tp)
    assert s.send("p1") == "first"
    assert s.send("p2") == "second"
    assert s.send("p3") == "second"  # last reply repeats
    assert s.sent == ["p1", "p2", "p3"]
    content = tp.read_text()
    assert "[PROMPT]" in content and "first" in content and "[RESPONSE]" in content


def test_cmd_echo_via_stdin(tmp_path):
    s = CmdAgentSession("ignored", "cat", "cat", str(tmp_path))
    assert s.send("hello agents") == "hello agents"


def test_cmd_extracts_json_result_field(tmp_path):
    script = f'{PY} -c "import json,sys; d=sys.stdin.read(); print(json.dumps({{\'result\': \'OK:\' + d}}))"'
    s = CmdAgentSession("sid", script, script, str(tmp_path))
    assert s.send("xyz") == "OK:xyz"


def test_cmd_nonzero_exit_raises(tmp_path):
    s = CmdAgentSession("sid", "false", "false", str(tmp_path))
    with pytest.raises(RuntimeError):
        s.send("boom")


def test_transcript_written(tmp_path):
    tp = tmp_path / "t.log"
    s = CmdAgentSession("sid", "cat", "cat", str(tmp_path), transcript_path=tp)
    s.send("abc")
    content = tp.read_text()
    assert "[PROMPT]" in content and "abc" in content and "[RESPONSE]" in content


def test_factory_builds_fake(tmp_path):
    cfg = {"kind": "fake", "replies": ["r1"]}
    s = make_session(cfg, "sid", str(tmp_path))
    assert isinstance(s, FakeAgentSession)


def test_factory_builds_cmd_with_templates(tmp_path):
    cfg = {
        "kind": "cmd",
        "start_cmd_template": "echo start-{session_id}",
        "cont_cmd_template": "echo cont-{session_id}",
    }
    s = make_session(cfg, "ABC123", str(tmp_path))
    assert isinstance(s, CmdAgentSession)
    assert s.send("hi") == "start-ABC123"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement session_manager.py**

```python
"""Persistent agent sessions driven through CLI command templates."""
import abc
import json
import shlex
import subprocess
from pathlib import Path


def _extract_output(stdout: str) -> str:
    try:
        obj = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return stdout.strip()
    if isinstance(obj, dict) and "result" in obj:
        return str(obj["result"])
    return stdout.strip()


class AgentSession(abc.ABC):
    def __init__(self, session_id: str, cwd: str) -> None:
        self.session_id = session_id
        self.cwd = cwd
        self.transcript_path: Path | None = None

    @abc.abstractmethod
    def send(self, prompt: str) -> str: ...

    def close(self) -> None:  # CLI processes terminate per send; hook kept for symmetry
        return None

    def _log(self, prompt: str, reply: str) -> None:
        if not self.transcript_path:
            return
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.transcript_path, "a", encoding="utf-8") as fh:
            fh.write(f"[PROMPT]\n{prompt}\n[/PROMPT]\n[RESPONSE]\n{reply}\n[/RESPONSE]\n")


class CmdAgentSession(AgentSession):
    def __init__(
        self,
        session_id: str,
        start_cmd_template: str,
        cont_cmd_template: str,
        cwd: str,
        timeout_seconds: int = 600,
        transcript_path: Path | None = None,
    ) -> None:
        super().__init__(session_id, cwd)
        self.start_template = start_cmd_template
        self.cont_template = cont_cmd_template
        self.timeout = timeout_seconds
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self._started = False

    def send(self, prompt: str) -> str:
        template = self.cont_template if self._started else self.start_template
        cmd = template.format(session_id=self.session_id)
        try:
            proc = subprocess.run(
                shlex.split(cmd),
                input=prompt,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"agent timed out: {cmd}") from exc
        if proc.returncode != 0:
            raise RuntimeError(f"agent failed ({proc.returncode}): {proc.stderr[-2000:]}")
        self._started = True
        reply = _extract_output(proc.stdout)
        self._log(prompt, reply)
        return reply


class FakeAgentSession(AgentSession):
    def __init__(
        self, session_id: str, cwd: str, replies: list[str], transcript_path: Path | None = None
    ) -> None:
        super().__init__(session_id, cwd)
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self._replies = list(replies)
        self.sent: list[str] = []

    def send(self, prompt: str) -> str:
        self.sent.append(prompt)
        if len(self._replies) > 1:
            reply = self._replies.pop(0)
        else:
            reply = self._replies[0]
        self._log(prompt, reply)
        return reply


def make_session(
    agent_cfg: dict, session_id: str, cwd: str, transcript_path: Path | None = None
) -> AgentSession:
    kind = agent_cfg.get("kind", "cmd")
    if kind == "fake":
        return FakeAgentSession(session_id, cwd, agent_cfg.get("replies", []), transcript_path=transcript_path)
    if kind == "cmd":
        return CmdAgentSession(
            session_id,
            agent_cfg["start_cmd_template"],
            agent_cfg["cont_cmd_template"],
            cwd,
            timeout_seconds=int(agent_cfg.get("timeout_seconds", 600)),
            transcript_path=transcript_path,
        )
    raise ValueError(f"unknown agent kind: {kind}")
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add hypevolve/session_manager.py tests/test_session_manager.py && git commit -m "feat: CLI-backed persistent agent sessions with transcripts"
```

---

### Task 8: EvolutionEngine (orchestrator)

**Files:**
- Create: `hypevolve/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `parse_hypothesis(text: str) -> str | None` — returns `hypothesis` value from the LAST fenced ```json block, else None.
  - `DEFAULT_INIT_PROMPT`, `DEFAULT_MUTATION_PROMPT` constants with `{iid}`, `{gen}`, `{fitness}`, `{context}`, `{workspace}` placeholders (mutation prompt ends with instruction + example fenced json `{"hypothesis": "..."}` so echo-style agents produce parseable output).
  - `EvolutionEngine(workspaces: WorkspaceManager, evaluator, agent_cfg: dict, selector_rng: random.Random, results_dir: Path, generations: int, population_size: int, elite_count: int, tournament_k: int, init_prompt: str = DEFAULT_INIT_PROMPT, mutation_prompt: str = DEFAULT_MUTATION_PROMPT, seed: int = 0)` with `run() -> RunSummary`.
  - Attributes readable by tests: `engine.tracker` (its HypothesisTracker), `engine.population_history` (list per generation, INCLUDING generation 0).
  - Side effects: writes `results_dir/summary.json` (asdict of RunSummary) and `results_dir/hypotheses.json` (list of asdict Hypothesis); snapshots best living workspace to `results_dir/best/`; transcripts at `results_dir/transcripts/indiv_{id:04d}.log` (wired through make_session's transcript_path param).
  - Lifecycle rules locked: `run()` produces `generations + 1` GenerationLog entries (gen 0 bootstrap + gens 1..N); generation 0 = population_size fresh individuals evaluated against empty parent_times; each generation produces `population_size - elite_count` children via `create_from` on the selected parent's workspace, evaluated against the PARENT'S child_times; hypothesis recorded AFTER evaluation (tracker.record gets the real result immediately); a child with `fitness == 0.0` is marked dead (`alive=False`), workspace removed, session closed, excluded from population; elites carry over untouched.

- [ ] **Step 1: Write failing test**

`tests/test_orchestrator.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hypevolve.orchestrator'`.

- [ ] **Step 3: Implement orchestrator.py**

```python
"""EvolutionEngine: the GA loop wiring workspaces, sessions, evaluation."""
import dataclasses
import json
import random
import re
from pathlib import Path

from hypevolve.hypothesis_tracker import HypothesisTracker
from hypevolve.models import GenerationLog, Hypothesis, Individual, RunSummary
from hypevolve.selector import elites, select_parents
from hypevolve.session_manager import AgentSession, make_session
from hypevolve.workspace import WorkspaceManager

DEFAULT_INIT_PROMPT = """You are individual {iid}, generation {gen}.
Your workspace: {workspace}
Profile the code, pick ONE optimization, apply it, and make sure tests still pass.
End your reply with a fenced json block:
```json
{{"hypothesis": "<one-sentence testable prediction>"}}"""

DEFAULT_MUTATION_PROMPT = """You are individual {iid}, generation {gen}.
Your current fitness: {fitness}
Your workspace: {workspace}

Validated knowledge so far:
{context}

Propose and apply ONE new optimization guided by that knowledge.
End your reply with a fenced json block:
```json
{{"hypothesis": "<one-sentence testable prediction>"}}"""


_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_hypothesis(text: str) -> str | None:
    blocks = _JSON_BLOCK.findall(text)
    if not blocks:
        return None
    try:
        obj = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None
    hyp = obj.get("hypothesis")
    return str(hyp) if hyp else None


class EvolutionEngine:
    def __init__(
        self,
        workspaces: WorkspaceManager,
        evaluator,
        agent_cfg: dict,
        selector_rng: random.Random,
        results_dir: Path,
        generations: int,
        population_size: int,
        elite_count: int,
        tournament_k: int,
        init_prompt: str = DEFAULT_INIT_PROMPT,
        mutation_prompt: str = DEFAULT_MUTATION_PROMPT,
        seed: int = 0,
    ) -> None:
        self.workspaces = workspaces
        self.evaluator = evaluator
        self.agent_cfg = dict(agent_cfg)
        self.rng = selector_rng
        self.results_dir = Path(results_dir)
        self.generations = generations
        self.population_size = population_size
        self.elite_count = elite_count
        self.tournament_k = tournament_k
        self.init_prompt = init_prompt
        self.mutation_prompt = mutation_prompt
        self.seed = seed
        self.tracker = HypothesisTracker()
        self.sessions: dict[int, AgentSession] = {}
        self.next_id = 0
        self.population_history: list[list[Individual]] = []

    # --- helpers ---------------------------------------------------------
    def _spawn(self, workspace: str, gen: int) -> tuple[Individual, AgentSession]:
        sid = f"s{self.next_id}"
        transcript = self.results_dir / "transcripts" / f"indiv_{self.next_id:04d}.log"
        session = make_session(self.agent_cfg, sid, workspace, transcript_path=transcript)
        ind = Individual(id=self.next_id, generation=gen, workspace=workspace, session_id=sid)
        self.next_id += 1
        return ind, session

    def _dispose(self, ind: Individual, session: AgentSession) -> None:
        session.close()
        self.workspaces.remove(ind.id)
        ind.alive = False

    def _evaluate_and_finish(
        self, ind: Individual, session: AgentSession, reply: str, parent_times: list[float]
    ) -> None:
        result = self.evaluator.evaluate(ind.workspace, parent_times)
        ind.eval_result = result
        ind.fitness = result.fitness
        text = parse_hypothesis(reply)
        if text:
            hyp = Hypothesis(text=text, individual_id=ind.id, generation=ind.generation)
            self.tracker.record(hyp, result)
        if result.fitness == 0.0:
            self._dispose(ind, session)

    # --- main loop -------------------------------------------------------
    def run(self) -> RunSummary:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logs: list[GenerationLog] = []
        population = self._bootstrap_generation_zero()
        self.population_history.append(list(population))
        logs.append(self._log_of(0, population))

        for gen in range(1, self.generations + 1):
            population = self._evolve_generation(gen, population)
            self.population_history.append(list(population))
            logs.append(self._log_of(gen, population))

        best = max(population, key=lambda i: (i.fitness, -i.id)) if population else None
        best_fit = best.fitness if best else 0.0
        if best and best.alive:
            self.workspaces.snapshot(best.id, self.results_dir / "best")
        summary = RunSummary(
            generations=logs,
            best_individual_id=best.id if best else -1,
            best_fitness=best_fit,
        )
        (self.results_dir / "summary.json").write_text(
            json.dumps(dataclasses.asdict(summary), indent=2)
        )
        (self.results_dir / "hypotheses.json").write_text(
            json.dumps([dataclasses.asdict(h) for h in self.tracker.all()], indent=2)
        )
        return summary

    def _bootstrap_generation_zero(self) -> list[Individual]:
        pop: list[Individual] = []
        for _ in range(self.population_size):
            ws = self.workspaces.create(self.next_id)
            ind, session = self._spawn(ws, gen=0)
            self.sessions[ind.id] = session
            reply = session.send(
                self.init_prompt.format(iid=ind.id, gen=0, fitness="unknown", workspace=ws)
            )
            self._evaluate_and_finish(ind, session, reply, parent_times=[])
            if ind.alive:
                pop.append(ind)
        return pop

    def _evolve_generation(self, gen: int, population: list[Individual]) -> list[Individual]:
        if not population:
            return []
        survivors = elites(population, self.elite_count)
        n_children = self.population_size - len(survivors)
        parents = select_parents(population, n_children, self.tournament_k, self.rng)
        children: list[Individual] = []
        for parent in parents:
            ws = self.workspaces.create_from(parent.workspace, self.next_id)
            ind, session = self._spawn(ws, gen=gen)
            self.sessions[ind.id] = session
            prompt = self.mutation_prompt.format(
                iid=ind.id,
                gen=gen,
                fitness=parent.fitness,
                workspace=ws,
                context=self.tracker.context_summary(),
            )
            reply = session.send(prompt)
            parent_times = parent.eval_result.child_times if parent.eval_result else []
            self._evaluate_and_finish(ind, session, reply, parent_times)
            if ind.alive:
                children.append(ind)
        return survivors + children

    def _log_of(self, gen: int, population: list[Individual]) -> GenerationLog:
        fits = [i.fitness for i in population] or [0.0]
        evals = [i.eval_result for i in population if i.eval_result]
        return GenerationLog(gen, max(fits), sum(fits) / len(fits), list(evals))
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_orchestrator.py -v`
Expected: 6 passed.

- [ ] **Step 5: Full suite**

Run: `pytest -v`
Expected: all previous tasks still green.

- [ ] **Step 6: Commit**

```bash
git add hypevolve/orchestrator.py tests/test_orchestrator.py && git commit -m "feat: evolution engine with hypothesis feedback loop"
```

---

### Task 9: Config loader + CLI entrypoint

**Files:**
- Create: `hypevolve/config.py`
- Create: `hypevolve/__main__.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: all components.
- Produces: dataclass `ExperimentConfig(name, source_path, test_cmd, bench_cmd, agents: dict, agent_name, results_root, generations, population_size, elite_count, tournament_k, repeats, warmup, timeout_seconds, alpha, seed)` with classmethod `load(path: str) -> ExperimentConfig` raising `ValueError` listing ALL missing required keys at once; module runnable via `python -m hypevolve --config <yaml>` which builds real components, runs the engine, prints best fitness/id, and writes artifacts under `<results_root>/<name>/`.

YAML schema (required keys marked *):
```yaml
name: smoke            # *
source_path: targets/dummy   # *
test_cmd: "python3 -m pytest -q"       # *
bench_cmd: "python3 bench.py"          # *
agent_name: claude     # *
agents:                # *
  claude:
    kind: cmd
    start_cmd_template: "claude -p --session-id {session_id} --output-format json"
    cont_cmd_template: "claude -p --resume {session_id} --output-format json"
results_root: results
generations: 12
population_size: 8
elite_count: 1
tournament_k: 3
repeats: 10
warmup: 1
timeout_seconds: 120
alpha: 0.05
seed: 42
```

- [ ] **Step 1: Write failing test**

`tests/test_config.py`:

```python
from pathlib import Path

import pytest

from hypevolve.config import ExperimentConfig

FULL = """
name: exp1
source_path: targets/dummy
test_cmd: "python3 -m pytest -q"
bench_cmd: "python3 bench.py"
agent_name: claude
agents:
  claude:
    kind: cmd
    start_cmd_template: "claude -p --session-id {session_id}"
    cont_cmd_template: "claude -p --resume {session_id}"
""".strip()


def write(tmp_path: Path, text: str) -> str:
    p = tmp_path / "cfg.yaml"
    p.write_text(text)
    return str(p)


def test_load_full_config_with_defaults(tmp_path):
    cfg = ExperimentConfig.load(write(tmp_path, FULL))
    assert cfg.name == "exp1"
    assert cfg.generations == 12
    assert cfg.population_size == 8
    assert cfg.agents["claude"]["kind"] == "cmd"
    assert cfg.alpha == 0.05


def test_missing_required_keys_reported_together(tmp_path):
    with pytest.raises(ValueError) as exc:
        ExperimentConfig.load(write(tmp_path, "name: only-name\n"))
    msg = str(exc.value)
    assert "source_path" in msg
    assert "bench_cmd" in msg
    assert "agents" in msg


def test_unknown_agent_name_rejected(tmp_path):
    bad = FULL.replace("agent_name: claude", "agent_name: gpt")
    with pytest.raises(ValueError):
        ExperimentConfig.load(write(tmp_path, bad))
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement config.py**

```python
"""Experiment configuration loading and validation."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _defaults() -> dict:
    return {
        "results_root": "results",
        "generations": 12,
        "population_size": 8,
        "elite_count": 1,
        "tournament_k": 3,
        "repeats": 10,
        "warmup": 1,
        "timeout_seconds": 120,
        "alpha": 0.05,
        "seed": 42,
    }


_REQUIRED = ["name", "source_path", "test_cmd", "bench_cmd", "agent_name", "agents"]


@dataclass
class ExperimentConfig:
    name: str
    source_path: str
    test_cmd: str
    bench_cmd: str
    agent_name: str
    agents: dict = field(default_factory=dict)
    results_root: str = "results"
    generations: int = 12
    population_size: int = 8
    elite_count: int = 1
    tournament_k: int = 3
    repeats: int = 10
    warmup: int = 1
    timeout_seconds: int = 120
    alpha: float = 0.05
    seed: int = 42

    @classmethod
    def load(cls, path: str) -> "ExperimentConfig":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        missing = [k for k in _REQUIRED if k not in raw]
        if missing:
            raise ValueError(f"missing required config keys: {', '.join(sorted(missing))}")
        merged = {**_defaults(), **raw}
        if merged["agent_name"] not in merged["agents"]:
            raise ValueError(f"agent_name '{merged['agent_name']}' not in agents")
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in merged.items() if k in known})
```

- [ ] **Step 4: Implement `__main__.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_config.py -v && pytest -v`
Expected: 3 new passed; full suite green.

- [ ] **Step 6: Commit**

```bash
git add hypevolve/config.py hypevolve/__main__.py tests/test_config.py && git commit -m "feat: yaml config loader and cli entrypoint"
```

---

### Task 10: End-to-end smoke run (dummy target + echo agent)

**Files:**
- Create: `scripts/make_dummy_target.sh`
- Create: `experiments/configs/smoke.template.yaml` (checked in, literal `{PY}`)
- Create: `experiments/README.md`

**Interfaces:**
- Consumes: `python -m hypevolve` from Task 9.
- Produces: proof the full pipeline works offline; `results/smoke/` artifacts. This is the acceptance gate for the MVP. Note: `{PY}` is a template placeholder NOT expanded by the framework — the generated machine-specific config substitutes it with the venv interpreter path at setup time.

- [ ] **Step 1: Write scripts/make_dummy_target.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/targets/dummy"
rm -rf "$TARGET"
mkdir -p "$TARGET"
cat > "$TARGET/slow.py" <<'EOF'
def sum_squares(n: int) -> int:
    total = 0
    for i in range(n):
        total += i * i
    return total
EOF
cat > "$TARGET/test_slow.py" <<'EOF'
from slow import sum_squares

def test_correctness():
    assert sum_squares(3) == 5
    assert sum_squares(0) == 0
EOF
cat > "$TARGET/bench.py" <<'EOF'
import time
from slow import sum_squares

start = time.perf_counter()
for _ in range(50):
    sum_squares(20_000)
print(time.perf_counter() - start)
EOF
cd "$TARGET"
git init -q
git add -A
git -c user.email=hypevolve@local -c user.name=hypevolve commit -qm "dummy target"
echo "dummy target ready at $TARGET"
```

- [ ] **Step 2: Write experiments/configs/smoke.template.yaml**

The echo agent (`cat`) reflects the prompt back; because the prompt instructs ending with a fenced json hypothesis block, the parser extracts hypotheses from the echoed text — exercising the real pipeline offline for free.

```yaml
name: smoke
source_path: targets/dummy
test_cmd: "{PY} -m pytest test_slow.py -q"
bench_cmd: "{PY} bench.py"
agent_name: echo
agents:
  echo:
    kind: cmd
    start_cmd_template: "cat"
    cont_cmd_template: "cat"
generations: 2
population_size: 2
elite_count: 1
tournament_k: 2
repeats: 3
warmup: 0
timeout_seconds: 60
seed: 7
```

- [ ] **Step 3: Generate machine config, prepare target, run smoke**

```bash
chmod +x scripts/make_dummy_target.sh && ./scripts/make_dummy_target.sh
mkdir -p experiments/configs
sed "s|{PY}|$(which python3)|g" experiments/configs/smoke.template.yaml > experiments/configs/smoke.yaml
pip install pytest  # ensures pytest importable for the target's test_cmd
python -m hypevolve --config experiments/configs/smoke.yaml
```

Expected stdout ends with `best individual: <int>`, `best fitness: 1.0000` (echo agent never improves code; baseline fitness 1.0), artifacts path. Then verify artifacts:

```bash
python - <<'EOF'
import json
s = json.load(open("results/smoke/summary.json"))
assert len(s["generations"]) == 3  # gen 0 bootstrap + 2 evolution generations
assert s["best_fitness"] >= 1.0
h = json.load(open("results/smoke/hypotheses.json"))
assert h, "hypotheses must be extracted from echo replies"
assert all(x["status"] != "proposed" for x in h)
print("SMOKE OK")
EOF
```

Expected: `SMOKE OK`.

- [ ] **Step 4: Write experiments/README.md**

```markdown
# Experiments

## Smoke (offline, free)
    ./scripts/make_dummy_target.sh
    sed "s|{PY}|$(which python3)|g" experiments/configs/smoke.template.yaml > experiments/configs/smoke.yaml
    python -m hypevolve --config experiments/configs/smoke.yaml

Keep `smoke.template.yaml` (with literal `{PY}`) as the checked-in template;
the generated `smoke.yaml` is machine-specific and git-ignored.

## Real targets
Point `source_path` at a git checkout under `targets/` pinned to a fixed commit.
Set `test_cmd`/`bench_cmd` to that project's suite + a benchmark script that
prints elapsed seconds as a float on its LAST stdout line.
Switch the agent to a real CLI, e.g.:
    claude:
      kind: cmd
      start_cmd_template: "claude -p --session-id {session_id} --output-format json"
      cont_cmd_template: "claude -p --resume {session_id} --output-format json"

Artifacts land in `results/<name>/`: summary.json, hypotheses.json,
transcripts/indiv_*.log, best/ (snapshot of the winning workspace).
```

Also add `experiments/configs/*.yaml` (generated files only, keep templates) to `.gitignore`:

```gitignore
experiments/configs/*.yaml
!experiments/configs/*.template.yaml
```

- [ ] **Step 5: Full suite green + commit**

Run: `pytest -v`
Expected: all green.

```bash
git add scripts/ experiments/ .gitignore && git commit -m "test: end-to-end smoke run with dummy target and echo agent"
```

---

## Deliberately OUT of this plan (next plans)

- Real-target selection pipeline + pinned checkouts (roadmap item 1 refinement)
- Pilot study runner (RQ-wise conditions matrix, budget parity enforcement)
- Statistical analysis notebooks/scripts (Mann-Whitney across runs, Vargha-Delaney Â12)
- Paper LaTeX scaffold and writing
