"""Parent selection: tournament + elitism."""
import random

from hypevolve.models import Individual


def elites(population: list[Individual], n: int) -> list[Individual]:
    ranked = sorted(population, key=lambda i: (-i.fitness, i.id))
    return ranked[:n]


def tournament(population: list[Individual], k: int, rng: random.Random) -> Individual:
    contenders = rng.sample(population, min(k, len(population)))
    return max(contenders, key=lambda i: i.fitness)


def select_parents(
    population: list[Individual], n_children: int, k: int, rng: random.Random
) -> list[Individual]:
    if not population:
        return []
    return [tournament(population, k, rng) for _ in range(n_children)]
