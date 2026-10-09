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
