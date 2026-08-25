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
