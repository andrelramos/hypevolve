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
