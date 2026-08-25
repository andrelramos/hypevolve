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
