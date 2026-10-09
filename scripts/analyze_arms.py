"""Turn the four arm run_logs into one analysis bundle (JSON) for the report."""
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARMS = [
    ("tornado-4d4c1e0", "ga", "results/tornado-4d4c1e0"),
    ("tornado-4d4c1e0", "sampling", "results/tornado-4d4c1e0-sampling"),
    ("tornado-4d4c1e0", "ga_rel_codex", "results/tornado-4d4c1e0-codex-rel"),
    ("pydantic-c2647ab", "ga", "results/pydantic-c2647ab"),
    ("pydantic-c2647ab", "sampling", "results/pydantic-c2647ab-sampling"),
]


def load(path: Path) -> dict | None:
    f = path / "run_log.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


def best_of_k_curve(values: list[float], trials: int = 4000, seed: int = 7) -> list[dict]:
    """Expected best-of-k when drawing k independent single-shot agents (with replacement)."""
    rng = random.Random(seed)
    out = []
    for k in range(1, len(values) + 1):
        maxima = [max(rng.choice(values) for _ in range(k)) for _ in range(trials)]
        maxima.sort()
        out.append(
            {
                "k": k,
                "mean": statistics.mean(maxima),
                "p10": maxima[int(0.10 * trials)],
                "p90": maxima[int(0.90 * trials)],
            }
        )
    return out


def ga_trajectory(log: dict) -> list[dict]:
    """Best speedup-vs-base reached after each agent call, in call order."""
    best = 1.0
    out = []
    for n, rec in enumerate(log["individuals"], start=1):
        if rec["passed"] and not rec["cheated"]:
            best = max(best, rec["speedup_vs_base"])
        out.append({"call": n, "best_so_far": best, "generation": rec["generation"]})
    return out


def arm_summary(log: dict) -> dict:
    ind = log["individuals"]
    valid = [r for r in ind if r["passed"] and not r["cheated"]]
    speedups = [r["speedup_vs_base"] for r in valid]
    wins = [r for r in valid if r["significant_vs_base"] and r["speedup_vs_base"] > 1.0]
    return {
        "agent_calls": log["agent_calls"],
        "baseline_median": log["baseline_median"],
        "n_individuals": len(ind),
        "n_broken": sum(1 for r in ind if not r["passed"] and not r["cheated"]),
        "n_agent_errors": sum(1 for r in ind if r.get("agent_error")),
        "n_cheated": sum(1 for r in ind if r["cheated"]),
        "n_valid": len(valid),
        "n_significant_wins": len(wins),
        "best_speedup_vs_base": max(speedups) if speedups else 1.0,
        "median_speedup_vs_base": statistics.median(speedups) if speedups else 1.0,
        "mean_speedup_vs_base": statistics.mean(speedups) if speedups else 1.0,
        "agent_seconds_total": sum(r["agent_seconds"] for r in ind),
    }


def main() -> int:
    bundle: dict = {"targets": {}}
    for target, mode, rel in ARMS:
        log = load(ROOT / rel)
        if log is None:
            print(f"missing: {rel}", file=sys.stderr)
            continue
        node = bundle["targets"].setdefault(target, {})
        valid = [
            r["speedup_vs_base"]
            for r in log["individuals"]
            if r["passed"] and not r["cheated"]
        ]
        node[mode] = {
            "summary": arm_summary(log),
            "individuals": log["individuals"],
            "selections": log["selections"],
            "trajectory": ga_trajectory(log),
            "best_of_k": best_of_k_curve(valid) if valid else [],
            "generations": sorted({r["generation"] for r in log["individuals"]}),
        }
        hyps = json.loads((ROOT / rel / "hypotheses.json").read_text())
        node[mode]["hypotheses"] = hyps
        node[mode]["fitness_mode"] = log.get("fitness_mode", "relative")
        node[mode]["best_ever_id"] = log.get("best_ever_id")
        node[mode]["best_ever_speedup_vs_base"] = log.get("best_ever_speedup_vs_base", 1.0)

    out = ROOT / "results/analysis.json"
    out.write_text(json.dumps(bundle, indent=2))
    print(f"wrote {out}")
    for target, arms in bundle["targets"].items():
        print(f"\n== {target}")
        for mode, data in arms.items():
            s = data["summary"]
            print(
                f"  {mode:9} calls={s['agent_calls']:3} valid={s['n_valid']:3} "
                f"broken={s['n_broken']:2} cheat={s['n_cheated']:2} "
                f"best={s['best_speedup_vs_base']:.4f}x median={s['median_speedup_vs_base']:.4f}x "
                f"wins={s['n_significant_wins']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
