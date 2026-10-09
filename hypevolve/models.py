"""Core domain types shared by all components."""
from dataclasses import dataclass, field
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
    parent_id: int | None = None
    fitness: float = 0.0
    speedup_vs_parent: float = 1.0
    speedup_vs_base: float = 1.0
    p_value: float | None = None
    p_value_vs_base: float | None = None
    passed: bool = False
    cheated: bool = False
    median_time: float | None = None


@dataclass
class EvaluationResult:
    passed: bool
    child_times: list[float]
    parent_times: list[float]
    p_value: float | None
    significant_speedup: bool
    speedup_ratio: float
    fitness: float
    speedup_vs_base: float = 1.0
    p_value_vs_base: float | None = None
    significant_vs_base: bool = False
    cheated: bool = False
    reference_times: list[float] = field(default_factory=list)
    test_stdout: str = ""
    test_stderr: str = ""
    test_returncode: int | None = None


@dataclass
class Individual:
    id: int
    generation: int
    workspace: str
    session_id: str
    fitness: float = 0.0
    eval_result: EvaluationResult | None = None
    alive: bool = True
    parent_id: int | None = None
    hypothesis: str = ""
    role: str = "child"
    agent_error: str = ""


@dataclass
class SelectionEvent:
    """One selection decision: who competed, who won, who got copied forward."""

    generation: int
    kind: str  # "elite" | "tournament"
    winner_id: int
    winner_fitness: float
    child_id: int | None = None
    contenders: list[int] = field(default_factory=list)
    contender_fitness: list[float] = field(default_factory=list)


@dataclass
class GenerationLog:
    generation: int
    best_fitness: float
    mean_fitness: float
    evaluations: list[EvaluationResult]
    individual_ids: list[int] = field(default_factory=list)
    elite_ids: list[int] = field(default_factory=list)
    selections: list[SelectionEvent] = field(default_factory=list)


@dataclass
class RunSummary:
    generations: list[GenerationLog]
    best_individual_id: int
    best_fitness: float
    mode: str = "ga"
    baseline_times: list[float] = field(default_factory=list)
    best_speedup_vs_base: float = 1.0
