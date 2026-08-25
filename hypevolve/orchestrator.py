"""EvolutionEngine: the GA loop wiring workspaces, sessions, evaluation."""
import dataclasses
import json
import random
import re
from pathlib import Path

from hypevolve.hypothesis_tracker import HypothesisTracker
from hypevolve.models import GenerationLog, Hypothesis, Individual, RunSummary
from hypevolve.selector import elites, select_parents
from hypevolve.session_manager import AgentSession, make_session
from hypevolve.workspace import WorkspaceManager

DEFAULT_INIT_PROMPT = """You are individual {iid}, generation {gen}.
Your workspace: {workspace}
Profile the code, pick ONE optimization, apply it, and make sure tests still pass.
End your reply with a fenced json block:
```json
{{"hypothesis": "<one-sentence testable prediction>"}}"""

DEFAULT_MUTATION_PROMPT = """You are individual {iid}, generation {gen}.
Your current fitness: {fitness}
Your workspace: {workspace}

Validated knowledge so far:
{context}

Propose and apply ONE new optimization guided by that knowledge.
End your reply with a fenced json block:
```json
{{"hypothesis": "<one-sentence testable prediction>"}}"""


_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_hypothesis(text: str) -> str | None:
    blocks = _JSON_BLOCK.findall(text)
    if not blocks:
        return None
    try:
        obj = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None
    hyp = obj.get("hypothesis")
    return str(hyp) if hyp else None


class EvolutionEngine:
    def __init__(
        self,
        workspaces: WorkspaceManager,
        evaluator,
        agent_cfg: dict,
        selector_rng: random.Random,
        results_dir: Path,
        generations: int,
        population_size: int,
        elite_count: int,
        tournament_k: int,
        init_prompt: str = DEFAULT_INIT_PROMPT,
        mutation_prompt: str = DEFAULT_MUTATION_PROMPT,
        seed: int = 0,
    ) -> None:
        self.workspaces = workspaces
        self.evaluator = evaluator
        self.agent_cfg = dict(agent_cfg)
        self.rng = selector_rng
        self.results_dir = Path(results_dir)
        self.generations = generations
        self.population_size = population_size
        self.elite_count = elite_count
        self.tournament_k = tournament_k
        self.init_prompt = init_prompt
        self.mutation_prompt = mutation_prompt
        self.seed = seed
        self.tracker = HypothesisTracker()
        self.sessions: dict[int, AgentSession] = {}
        self.next_id = 0
        self.population_history: list[list[Individual]] = []

    # --- helpers ---------------------------------------------------------
    def _spawn(self, workspace: str, gen: int) -> tuple[Individual, AgentSession]:
        sid = f"s{self.next_id}"
        transcript = self.results_dir / "transcripts" / f"indiv_{self.next_id:04d}.log"
        session = make_session(self.agent_cfg, sid, workspace, transcript_path=transcript)
        ind = Individual(id=self.next_id, generation=gen, workspace=workspace, session_id=sid)
        self.next_id += 1
        return ind, session

    def _dispose(self, ind: Individual, session: AgentSession) -> None:
        session.close()
        self.workspaces.remove(ind.id)
        ind.alive = False

    def _evaluate_and_finish(
        self, ind: Individual, session: AgentSession, reply: str, parent_times: list[float]
    ) -> None:
        result = self.evaluator.evaluate(ind.workspace, parent_times)
        ind.eval_result = result
        ind.fitness = result.fitness
        text = parse_hypothesis(reply)
        if text:
            hyp = Hypothesis(text=text, individual_id=ind.id, generation=ind.generation)
            self.tracker.record(hyp, result)
        if result.fitness == 0.0:
            self._dispose(ind, session)

    # --- main loop -------------------------------------------------------
    def run(self) -> RunSummary:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logs: list[GenerationLog] = []
        population = self._bootstrap_generation_zero()
        self.population_history.append(list(population))
        logs.append(self._log_of(0, population))

        for gen in range(1, self.generations + 1):
            population = self._evolve_generation(gen, population)
            self.population_history.append(list(population))
            logs.append(self._log_of(gen, population))

        best = max(population, key=lambda i: (i.fitness, -i.id)) if population else None
        best_fit = best.fitness if best else 0.0
        if best and best.alive:
            self.workspaces.snapshot(best.id, self.results_dir / "best")
        summary = RunSummary(
            generations=logs,
            best_individual_id=best.id if best else -1,
            best_fitness=best_fit,
        )
        (self.results_dir / "summary.json").write_text(
            json.dumps(dataclasses.asdict(summary), indent=2)
        )
        (self.results_dir / "hypotheses.json").write_text(
            json.dumps([dataclasses.asdict(h) for h in self.tracker.all()], indent=2)
        )
        return summary

    def _bootstrap_generation_zero(self) -> list[Individual]:
        pop: list[Individual] = []
        for _ in range(self.population_size):
            ws = self.workspaces.create(self.next_id)
            ind, session = self._spawn(ws, gen=0)
            self.sessions[ind.id] = session
            reply = session.send(
                self.init_prompt.format(iid=ind.id, gen=0, fitness="unknown", workspace=ws)
            )
            self._evaluate_and_finish(ind, session, reply, parent_times=[])
            if ind.alive:
                pop.append(ind)
        return pop

    def _evolve_generation(self, gen: int, population: list[Individual]) -> list[Individual]:
        if not population:
            return []
        survivors = elites(population, self.elite_count)
        n_children = self.population_size - len(survivors)
        parents = select_parents(population, n_children, self.tournament_k, self.rng)
        children: list[Individual] = []
        for parent in parents:
            ws = self.workspaces.create_from(parent.workspace, self.next_id)
            ind, session = self._spawn(ws, gen=gen)
            self.sessions[ind.id] = session
            prompt = self.mutation_prompt.format(
                iid=ind.id,
                gen=gen,
                fitness=parent.fitness,
                workspace=ws,
                context=self.tracker.context_summary(),
            )
            reply = session.send(prompt)
            parent_times = parent.eval_result.child_times if parent.eval_result else []
            self._evaluate_and_finish(ind, session, reply, parent_times)
            if ind.alive:
                children.append(ind)
        return survivors + children

    def _log_of(self, gen: int, population: list[Individual]) -> GenerationLog:
        fits = [i.fitness for i in population] or [0.0]
        evals = [i.eval_result for i in population if i.eval_result]
        return GenerationLog(gen, max(fits), sum(fits) / len(fits), list(evals))
