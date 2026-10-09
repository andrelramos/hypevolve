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
