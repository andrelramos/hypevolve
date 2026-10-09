"""EvolutionEngine: the GA loop wiring workspaces, sessions, evaluation."""
import dataclasses
import json
import random
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hypevolve.evaluator import Evaluator
from hypevolve.contracts import has_valid_evolution_limits
from hypevolve.hypothesis_tracker import HypothesisTracker
from hypevolve.models import (
    GenerationLog,
    EvaluationResult,
    Hypothesis,
    Individual,
    RunSummary,
    SelectionEvent,
)
from hypevolve.selector import elites, tournament_with_log
from hypevolve.session_manager import AgentSession, make_session
from hypevolve.workspace import WorkspaceManager

DEFAULT_INIT_PROMPT = """You are individual {iid}, generation {gen}.
Your workspace: {workspace}
Profile the code, pick ONE optimization, apply it, and make sure tests still pass.
End your reply with a fenced json block:
```json
{{"hypothesis": "<one-sentence testable prediction>"}}
```"""

DEFAULT_MUTATION_PROMPT = """You are individual {iid}, generation {gen}.
Your current fitness: {fitness}
Your workspace: {workspace}

Validated knowledge so far:
{context}

Propose and apply ONE new optimization guided by that knowledge.
End your reply with a fenced json block:
```json
{{"hypothesis": "<one-sentence testable prediction>"}}
```"""


_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

AGENT_ERROR_MARKER = "[agent error]"


def parse_reply(text: str) -> dict:
    """Last fenced json block of the agent reply, as a dict ({} when absent/invalid)."""
    blocks = _JSON_BLOCK.findall(text or "")
    if not blocks:
        return {}
    try:
        obj = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def parse_hypothesis(text: str) -> str | None:
    hyp = parse_reply(text).get("hypothesis")
    return str(hyp) if hyp else None


class EvolutionEngine:
    def __init__(
        self,
        workspaces: WorkspaceManager,
        evaluator: Evaluator,
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
        protected_files: list[str] | None = None,
        baseline_times: list[float] | None = None,
        max_parallel: int = 1,
        fitness_mode: str = "relative",
        reference_workspace: str | None = None,
        max_hypotheses: int = 0,
    ) -> None:
        if not has_valid_evolution_limits(
            generations, population_size, elite_count, tournament_k, max_hypotheses
        ):
            raise ValueError("invalid evolution limits")
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
        self.protected_files = protected_files or []
        self.baseline_times = list(baseline_times or [])
        self.max_parallel = max(1, int(max_parallel))
        self.fitness_mode = fitness_mode
        self.reference_workspace = reference_workspace
        self.max_hypotheses = max(0, int(max_hypotheses))
        self.tracker = HypothesisTracker()
        self.sessions: dict[int, AgentSession] = {}
        self.next_id = 0
        self.population_history: list[list[Individual]] = []
        self.records: list[dict] = []
        self.selection_events: list[SelectionEvent] = []
        self.agent_calls = 0
        self._calls_lock = threading.Lock()

    # --- helpers ---------------------------------------------------------
    def _spawn(
        self, workspace: str, gen: int, parent_id: int | None = None, role: str = "child"
    ) -> tuple[Individual, AgentSession]:
        sid = f"s{self.next_id}"
        transcript = self.results_dir / "transcripts" / f"indiv_{self.next_id:04d}.log"
        session = make_session(self.agent_cfg, sid, workspace, transcript_path=transcript)
        ind = Individual(
            id=self.next_id,
            generation=gen,
            workspace=workspace,
            session_id=sid,
            parent_id=parent_id,
            role=role,
        )
        self.next_id += 1
        return ind, session

    def _dispose(self, ind: Individual, session: AgentSession) -> None:
        session.close()
        self.workspaces.remove(ind.id)
        ind.alive = False

    def _record(
        self, ind: Individual, reply_meta: dict, elapsed: float, prompt: str, reply: str
    ) -> None:
        r = ind.eval_result
        times = list(r.child_times) if r else []
        self.records.append(
            {
                "individual_id": ind.id,
                "generation": ind.generation,
                "parent_id": ind.parent_id,
                "role": ind.role,
                "hypothesis": ind.hypothesis,
                "mechanism": reply_meta.get("mechanism", ""),
                "builds_on": reply_meta.get("builds_on", ""),
                "files_touched": reply_meta.get("files_touched", ""),
                "agent_error": ind.agent_error,
                "agent_prompt": prompt,
                "agent_stdout": reply,
                "transcript_path": str(self.results_dir / "transcripts" / f"indiv_{ind.id:04d}.log"),
                "passed": bool(r.passed) if r else False,
                "cheated": bool(r.cheated) if r else False,
                "fitness": ind.fitness,
                "speedup_vs_parent": r.speedup_ratio if r else 0.0,
                "significant_vs_parent": bool(r.significant_speedup) if r else False,
                "p_value_vs_parent": r.p_value if r else None,
                "speedup_vs_base": r.speedup_vs_base if r else 0.0,
                "significant_vs_base": bool(r.significant_vs_base) if r else False,
                "p_value_vs_base": r.p_value_vs_base if r else None,
                "median_time": statistics.median(times) if times else None,
                "times": times,
                "reference_times": list(r.reference_times) if r else [],
                "reference_median": (
                    statistics.median(r.reference_times) if r and r.reference_times else None
                ),
                "agent_seconds": round(elapsed, 2),
                "test_stdout": r.test_stdout if r else "",
                "test_stderr": r.test_stderr if r else "",
                "test_returncode": r.test_returncode if r else None,
                "alive": ind.alive,
            }
        )

    def _evaluate_and_finish(
        self,
        ind: Individual,
        session: AgentSession,
        reply: str,
        parent_times: list[float],
    ) -> None:
        from hypevolve.models import EvaluationResult

        if reply.startswith(AGENT_ERROR_MARKER):
            # The agent never produced a patch. Scoring this workspace would score its
            # PARENT's code and silently fabricate an individual.
            result = EvaluationResult(
                passed=False, child_times=[], parent_times=list(parent_times),
                p_value=None, significant_speedup=False, speedup_ratio=0.0, fitness=0.0,
            )
            ind.eval_result = result
            ind.fitness = 0.0
            ind.agent_error = reply[:500]
            self._dispose(ind, session)
            return

        text = parse_hypothesis(reply)
        ind.hypothesis = text or ""

        if self.protected_files:
            ok, _changed = self.workspaces.integrity_check(ind.id, self.protected_files)
            if not ok:
                result = EvaluationResult(
                    passed=False, child_times=[], parent_times=list(parent_times),
                    p_value=None, significant_speedup=False, speedup_ratio=1.0, fitness=0.0,
                    cheated=True,
                )
                ind.eval_result = result
                ind.fitness = 0.0
                if text:
                    self._track(ind, text, result)
                self._dispose(ind, session)
                return

        if self.reference_workspace:
            result = self.evaluator.evaluate_paired(
                ind.workspace, self.reference_workspace, parent_times
            )
        else:
            result = self.evaluator.evaluate(ind.workspace, parent_times, self.baseline_times)
        if self.fitness_mode == "absolute" and result.passed:
            # One scale for everyone: speedup over the pristine baseline. Relative fitness
            # makes a gen-0 seed (scored vs base) incomparable to a child (scored vs parent).
            result.fitness = result.speedup_vs_base if result.significant_vs_base else 1.0
        ind.eval_result = result
        ind.fitness = result.fitness
        if text:
            self._track(ind, text, result)
        if result.fitness == 0.0:
            self._dispose(ind, session)

    def _track(self, ind: Individual, text: str, result: EvaluationResult) -> None:
        hyp = Hypothesis(
            text=text,
            individual_id=ind.id,
            generation=ind.generation,
            parent_id=ind.parent_id,
            fitness=result.fitness,
            speedup_vs_parent=result.speedup_ratio,
            speedup_vs_base=result.speedup_vs_base,
            p_value=result.p_value,
            p_value_vs_base=result.p_value_vs_base,
            passed=result.passed,
            cheated=result.cheated,
            median_time=statistics.median(result.child_times) if result.child_times else None,
        )
        self.tracker.record(hyp, result)

    def _ask(self, session: AgentSession, prompt: str) -> tuple[str, float]:
        start = time.perf_counter()
        try:
            reply = session.send(prompt)
        except RuntimeError as exc:
            reply = f"{AGENT_ERROR_MARKER} {exc}"
        with self._calls_lock:
            self.agent_calls += 1
        return reply, time.perf_counter() - start

    def _ask_batch(self, jobs: list[tuple[Individual, AgentSession, str]]) -> dict:
        """Run agent calls concurrently; evaluation stays serial so timings stay clean."""
        if not jobs:
            return {}
        if self.max_parallel == 1 or len(jobs) == 1:
            return {ind.id: self._ask(sess, prompt) for ind, sess, prompt in jobs}
        with ThreadPoolExecutor(max_workers=min(self.max_parallel, len(jobs))) as pool:
            futures = {
                pool.submit(self._ask, sess, prompt): ind.id for ind, sess, prompt in jobs
            }
            return {futures[f]: f.result() for f in futures}

    # --- main loop -------------------------------------------------------
    def run(self) -> RunSummary:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logs: list[GenerationLog] = []
        population = self._bootstrap_generation_zero()
        self.population_history.append(list(population))
        logs.append(self._log_of(0, population, [], []))

        self._checkpoint("ga", gen=0)
        for gen in range(1, self.generations + 1):
            population, elite_ids, events = self._evolve_generation(gen, population)
            self.population_history.append(list(population))
            logs.append(self._log_of(gen, population, elite_ids, events))
            self._checkpoint("ga", gen=gen)

        return self._finish(logs, population, mode="ga")

    def run_sampling(self, budget: int) -> RunSummary:
        """Control arm: `budget` independent single-shot agents, no lineage, no shared knowledge.

        Same number of LLM calls as the GA arm; every individual starts from the pristine
        source and is scored against the same baseline.
        """
        self.results_dir.mkdir(parents=True, exist_ok=True)
        pop: list[Individual] = []
        jobs = self._seed_jobs(budget, role="sample")
        replies = self._ask_batch(jobs)
        for ind, session, prompt in jobs:
            reply, elapsed = replies[ind.id]
            self._evaluate_and_finish(ind, session, reply, parent_times=self.baseline_times)
            self._record(ind, parse_reply(reply), elapsed, prompt=prompt, reply=reply)
            if ind.alive:
                pop.append(ind)
        self.population_history.append(list(pop))
        logs = [self._log_of(0, pop, [], [])]
        return self._finish(logs, pop, mode="sampling")

    def _checkpoint(self, mode: str, gen: int) -> None:
        """Partial trace on disk: a killed run still shows what it had reached."""
        ranked = sorted(
            [r for r in self.records if r["passed"] and not r["cheated"]],
            key=lambda r: -r["speedup_vs_base"],
        )
        (self.results_dir / "checkpoint.json").write_text(
            json.dumps(
                {
                    "mode": mode,
                    "through_generation": gen,
                    "agent_calls": self.agent_calls,
                    "baseline_times": list(self.baseline_times),
                    "baseline_median": (
                        statistics.median(self.baseline_times) if self.baseline_times else None
                    ),
                    "fitness_mode": self.fitness_mode,
                    "max_hypotheses": self.max_hypotheses,
                    "individuals": self.records,
                    "selections": [dataclasses.asdict(e) for e in self.selection_events],
                    "best_ever_id": ranked[0]["individual_id"] if ranked else None,
                    "best_ever_speedup_vs_base": ranked[0]["speedup_vs_base"] if ranked else 1.0,
                },
                indent=2,
            )
        )

    def _finish(
        self, logs: list[GenerationLog], population: list[Individual], mode: str
    ) -> RunSummary:
        alive = [i for i in population if i.alive]

        def _abs(i: Individual) -> float:
            return i.eval_result.speedup_vs_base if i.eval_result else 0.0

        best = max(alive, key=lambda i: (_abs(i), -i.id)) if alive else None
        if best is None:
            ranked = sorted(self.records, key=lambda r: -r["speedup_vs_base"])
            best_id = ranked[0]["individual_id"] if ranked else -1
            best_fit = ranked[0]["fitness"] if ranked else 0.0
            best_speedup = ranked[0]["speedup_vs_base"] if ranked else 1.0
        else:
            best_id, best_fit = best.id, best.fitness
            best_speedup = best.eval_result.speedup_vs_base if best.eval_result else 1.0
            self.workspaces.snapshot(best.id, self.results_dir / "best")

        summary = RunSummary(
            generations=logs,
            best_individual_id=best_id,
            best_fitness=best_fit,
            mode=mode,
            baseline_times=list(self.baseline_times),
            best_speedup_vs_base=best_speedup,
        )
        (self.results_dir / "summary.json").write_text(
            json.dumps(dataclasses.asdict(summary), indent=2)
        )
        # Preserve human-curated hypotheses added through the API while a run is active.
        hypotheses_path = self.results_dir / "hypotheses.json"
        try:
            existing = json.loads(hypotheses_path.read_text()) if hypotheses_path.exists() else []
        except json.JSONDecodeError:
            existing = []
        manual = [item for item in existing if item.get("manual")]
        hypotheses_path.write_text(
            json.dumps([dataclasses.asdict(h) for h in self.tracker.all()] + manual, indent=2)
        )
        ranked_all = sorted(
            [r for r in self.records if r["passed"] and not r["cheated"]],
            key=lambda r: -r["speedup_vs_base"],
        )
        best_ever = ranked_all[0] if ranked_all else None
        (self.results_dir / "run_log.json").write_text(
            json.dumps(
                {
                    "mode": mode,
                    "seed": self.seed,
                    "population_size": self.population_size,
                    "generations": self.generations,
                    "elite_count": self.elite_count,
                    "tournament_k": self.tournament_k,
                    "agent_calls": self.agent_calls,
                    "baseline_times": list(self.baseline_times),
                    "baseline_median": (
                        statistics.median(self.baseline_times) if self.baseline_times else None
                    ),
                    "individuals": self.records,
                    "selections": [dataclasses.asdict(e) for e in self.selection_events],
                    "best_individual_id": best_id,
                    "best_fitness": best_fit,
                    "best_speedup_vs_base": best_speedup,
                    "fitness_mode": self.fitness_mode,
                    "max_hypotheses": self.max_hypotheses,
                    "best_ever_id": best_ever["individual_id"] if best_ever else None,
                    "best_ever_speedup_vs_base": (
                        best_ever["speedup_vs_base"] if best_ever else 1.0
                    ),
                },
                indent=2,
            )
        )
        return summary

    def _seed_jobs(self, count: int, role: str) -> list[tuple[Individual, AgentSession, str]]:
        jobs = []
        if self.max_hypotheses:
            count = min(count, max(0, self.max_hypotheses - self.agent_calls))
        for _ in range(count):
            ws = self.workspaces.create(self.next_id)
            ind, session = self._spawn(ws, gen=0, role=role)
            self.sessions[ind.id] = session
            prompt = self.init_prompt.format(
                iid=ind.id, gen=0, fitness="unknown", workspace=ws
            )
            jobs.append((ind, session, prompt))
        return jobs

    def _bootstrap_generation_zero(self) -> list[Individual]:
        jobs = self._seed_jobs(self.population_size, role="seed")
        replies = self._ask_batch(jobs)
        pop: list[Individual] = []
        for ind, session, prompt in jobs:
            reply, elapsed = replies[ind.id]
            # gen 0 is scored against the pristine baseline, so seeds carry real fitness
            self._evaluate_and_finish(ind, session, reply, parent_times=self.baseline_times)
            self._record(ind, parse_reply(reply), elapsed, prompt=prompt, reply=reply)
            if ind.alive:
                pop.append(ind)
        return pop

    def _evolve_generation(
        self, gen: int, population: list[Individual]
    ) -> tuple[list[Individual], list[int], list[SelectionEvent]]:
        if not population:
            return [], [], []
        events: list[SelectionEvent] = []
        survivors = elites(population, self.elite_count)
        for e in survivors:
            e.role = "elite"
            ev = SelectionEvent(
                generation=gen, kind="elite", winner_id=e.id, winner_fitness=e.fitness
            )
            events.append(ev)
            self.selection_events.append(ev)

        n_children = self.population_size - len(survivors)
        if self.max_hypotheses:
            n_children = min(n_children, max(0, self.max_hypotheses - self.agent_calls))
        context = self.tracker.context_summary()
        jobs: list[tuple[Individual, AgentSession, str]] = []
        parents: dict[int, Individual] = {}
        for _ in range(n_children):
            parent, contenders = tournament_with_log(population, self.tournament_k, self.rng)
            ws = self.workspaces.create_from(parent.workspace, self.next_id)
            ind, session = self._spawn(ws, gen=gen, parent_id=parent.id, role="child")
            ev = SelectionEvent(
                generation=gen,
                kind="tournament",
                winner_id=parent.id,
                winner_fitness=parent.fitness,
                child_id=ind.id,
                contenders=[c.id for c in contenders],
                contender_fitness=[c.fitness for c in contenders],
            )
            events.append(ev)
            self.selection_events.append(ev)
            self.sessions[ind.id] = session
            parents[ind.id] = parent
            prompt = self.mutation_prompt.format(
                iid=ind.id,
                gen=gen,
                fitness=parent.fitness,
                workspace=ws,
                context=context,
            )
            jobs.append((ind, session, prompt))

        replies = self._ask_batch(jobs)
        children: list[Individual] = []
        for ind, session, prompt in jobs:
            reply, elapsed = replies[ind.id]
            parent = parents[ind.id]
            parent_times = parent.eval_result.child_times if parent.eval_result else []
            self._evaluate_and_finish(ind, session, reply, parent_times)
            self._record(ind, parse_reply(reply), elapsed, prompt=prompt, reply=reply)
            if ind.alive:
                children.append(ind)
        return survivors + children, [e.id for e in survivors], events

    def _log_of(
        self,
        gen: int,
        population: list[Individual],
        elite_ids: list[int],
        events: list[SelectionEvent],
    ) -> GenerationLog:
        fits = [i.fitness for i in population] or [0.0]
        evals = [i.eval_result for i in population if i.eval_result]
        return GenerationLog(
            generation=gen,
            best_fitness=max(fits),
            mean_fitness=sum(fits) / len(fits),
            evaluations=list(evals),
            individual_ids=[i.id for i in population],
            elite_ids=list(elite_ids),
            selections=list(events),
        )
