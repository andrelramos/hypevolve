"""Pure, symbolically-checkable invariants for execution state transitions."""
from typing import Literal

import icontract

SessionStatus = Literal["queued", "running", "completed", "failed"]
TERMINAL_STATES: frozenset[SessionStatus] = frozenset({"completed", "failed"})


@icontract.require(lambda current: current is None or current in {"queued", "running", "completed", "failed"})
@icontract.require(lambda next_status: next_status in {"queued", "running", "completed", "failed"})
@icontract.ensure(
    lambda result, current, next_status: result == (
        current not in TERMINAL_STATES or next_status != "running"
    )
)
def is_valid_session_transition(current: str | None, next_status: str) -> bool:
    """Terminal executions are immutable with respect to a new running state."""
    return current not in TERMINAL_STATES or next_status != "running"


@icontract.require(lambda generations, population_size, elite_count, tournament_k, max_hypotheses: all(
    isinstance(value, int) for value in (generations, population_size, elite_count, tournament_k, max_hypotheses)
))
@icontract.ensure(
    lambda result, generations, population_size, elite_count, tournament_k, max_hypotheses: result == (
        generations >= 0
        and population_size >= 1
        and 0 <= elite_count <= population_size
        and 1 <= tournament_k <= population_size
        and max_hypotheses >= 0
    )
)
def has_valid_evolution_limits(
    generations: int, population_size: int, elite_count: int, tournament_k: int, max_hypotheses: int
) -> bool:
    """The GA cannot start with an impossible population or budget."""
    return (
        generations >= 0
        and population_size >= 1
        and 0 <= elite_count <= population_size
        and 1 <= tournament_k <= population_size
        and max_hypotheses >= 0
    )


@icontract.ensure(lambda result, text: result == bool(text.strip()))
def has_hypothesis_text(text: str) -> bool:
    """A hypothesis must have content beyond whitespace."""
    return bool(text.strip())
