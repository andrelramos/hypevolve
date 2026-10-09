import pytest
from icontract.errors import ViolationError

from hypevolve.config import ExperimentConfig
from hypevolve.contracts import is_valid_session_transition
from hypevolve.hypothesis_tracker import HypothesisTracker


def test_terminal_session_cannot_return_to_running():
    assert not is_valid_session_transition("completed", "running")
    assert is_valid_session_transition("completed", "completed")


def test_config_rejects_impossible_evolution_limits():
    with pytest.raises(ValueError, match="invalid evolution limits"):
        ExperimentConfig(
            name="bad", source_path=".", test_cmd="true", bench_cmd="echo 1",
            agent_name="fake", agents={"fake": {"kind": "fake"}},
            population_size=1, elite_count=2, tournament_k=1,
        )


def test_tracker_rejects_blank_hypothesis():
    with pytest.raises(ViolationError):
        HypothesisTracker().add("   ")
