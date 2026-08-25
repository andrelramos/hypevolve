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
