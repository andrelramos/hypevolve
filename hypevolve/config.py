"""Experiment configuration loading and validation."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .contracts import has_valid_evolution_limits


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
        "max_parallel_agents": 1,
        "fitness_mode": "relative",
        "max_hypotheses": 0,
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
    max_parallel_agents: int = 1
    fitness_mode: str = "relative"
    protected_files: list[str] = field(default_factory=list)
    init_prompt: str = ""
    mutation_prompt: str = ""
    max_hypotheses: int = 0

    def __post_init__(self) -> None:
        if not has_valid_evolution_limits(
            self.generations, self.population_size, self.elite_count,
            self.tournament_k, self.max_hypotheses,
        ):
            raise ValueError("invalid evolution limits")

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
