"""Build the HypEvolve report artifact from results/analysis.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report.charts import (
    decision_table,
    comparison_chart,
    esc,
    lineage_tree,
    parent_usage_chart,
    solo_vs_lineage_chart,
    strip_chart,
    trajectory_chart,
)
from report.tokens import CSS, FONTS, TOOLTIP_JS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hypevolve/reports/data/2026-09-17/relatorio.html"

TARGET_META = {
    "tornado-4d4c1e0": {
        "title": "tornado · Future.set_exception",
        "commit": "a42b028c (4d4c1e0^)",
        "api": "Future.set_exception sobre 10.000 futures",
        "agent": "Claude CLI · Sonnet",
        "ga_label": "GA · Claude Sonnet",
        "public_source": "https://github.com/gso-bench/gso-experiments/tree/main/results/reports",
    },
    "pydantic-c2647ab": {
        "title": "pydantic · TypeAdapter.validate_strings",
        "commit": "9783bc8f2 (c2647ab^)",
        "api": "validate_strings sobre 10.000 strings numéricas",
        "agent": "Codex CLI · gpt-5.6-sol",
        "ga_label": "GA · Codex gpt-5.6-sol",
        "public_source": "https://github.com/gso-bench/gso-experiments/tree/main/results/reports",
    },
}


def f(x, n=3):
    return f"{x:.{n}f}".replace(".", ",")


def tile(label, value, note, rule="var(--ga)"):
    return (
        f'<div class="metric" style="--rule:{rule}">'
        f'<span class="metric-label">{esc(label)}</span>'
        f'<span class="metric-value">{value}</span>'
        f'<span class="metric-note">{note}</span></div>'
    )


def ledger(arm, limit=None):
    rows = arm["individuals"]
    if limit:
        rows = rows[:limit]
    out = [
        '<div class="chart-scroll"><table><thead><tr>'
        "<th>#</th><th>ger</th><th>pai</th><th>hipótese</th><th>status</th>"
        '<th class="num">vs base</th><th class="num">p</th><th class="num">ms</th>'
        "</tr></thead><tbody>"
    ]
    for r in rows:
        if r.get("agent_error"):
            status = '<span class="tag dead">erro de agente</span>'
        elif r["cheated"]:
            status = '<span class="tag refuted">burla</span>'
        elif not r["passed"]:
            status = '<span class="tag dead">quebrou testes</span>'
        elif r["significant_vs_base"] and r["speedup_vs_base"] > 1.0:
            status = '<span class="tag confirmed">✓ confirmada</span>'
        else:
            status = '<span class="tag refuted">✗ refutada</span>'
        hyp = r["hypothesis"] or "—"
        mech = r.get("mechanism") or ""
        tip = f'<b>#{r["individual_id"]}</b><br>{esc(hyp)}' + (f"<br><br>{esc(mech)}" if mech else "")
        p = r["p_value_vs_base"]
        out.append(
            "<tr>"
            f'<td class="num">{r["individual_id"]}</td>'
            f'<td class="num">{r["generation"]}</td>'
            f'<td class="num">{"—" if r["parent_id"] is None else "#" + str(r["parent_id"])}</td>'
            f'<td class="hyp" data-tip="{tip}">{esc(hyp[:118])}{"…" if len(hyp) > 118 else ""}</td>'
            f"<td>{status}</td>"
            f'<td class="num">{f(r["speedup_vs_base"], 3) if r["passed"] else "—"}</td>'
            f'<td class="num">{f(p, 5) if p is not None else "—"}</td>'
            f'<td class="num">{f(r["median_time"] * 1000, 3) if r["median_time"] else "—"}</td>'
            "</tr>"
        )
    out.append("</tbody></table></div>")
    return "".join(out)


def legend(*items):
    spans = "".join(
        f'<span><i class="swatch{" line" if kind == "line" else ""}" style="background:{color}"></i>{esc(label)}</span>'
        for label, color, kind in items
    )
    return f'<div class="legend">{spans}</div>'


def target_section(name, arms, narrative, public_bundle):
    meta = TARGET_META[name]
    ga, sa = arms["ga"], arms["sampling"]
    gs, ss = ga["summary"], sa["summary"]
    ga_valid = bool(gs.get("n_valid", 0))
    ga_best = ga["best_ever_speedup_vs_base"] if ga_valid else 0.0
    agent_note = esc(meta["agent"]) if ga_valid else "interrompido por falta de créditos"
    sa_best = ss["best_speedup_vs_base"]
    bok = sa["best_of_k"][-1]["mean"] if sa["best_of_k"] else 1.0
    delta = (ga_best / sa_best - 1) * 100 if ga_valid else 0.0
    public_results = public_bundle["targets"].get(name, [])
    public_note = (
        f'{len(public_results)} execuções públicas · métrica <code>{esc(public_bundle["metric"])}</code>'
        if public_results
        else "nenhuma execução pública por tarefa encontrada"
    )
    chart_note = narrative.get(
        "trajectory",
        "Speedup relativo ao baseline local; a linha tracejada é a referência pública do GSO quando disponível.",
    )
    solo_note = narrative.get(
        "solo",
        "Comparação do melhor resultado acumulado por chamada entre evolução e tentativas independentes.",
    )
    strip_note = narrative.get(
        "strip",
        "Cada ponto representa um indivíduo válido; execuções inválidas permanecem visíveis nos registros da rodada.",
    )
    lineage_note = narrative.get("lineage", "Linhagem dos indivíduos produzidos pelo braço evolutivo.")
    parents_note = narrative.get("parents", "Distribuição das escolhas de pais durante a evolução.")
    ga_legend_items = ((f"indivíduos · {meta['agent']}", "var(--ga)", "swatch"), (f"GA · melhor até agora · {meta['agent']}", "var(--ga)", "line")) if ga_valid else ()
    trajectory_legend_items = ((f"GA · melhor até agora · {meta['agent']}", "var(--ga)", "line"),) if ga_valid else ()
    evolution_detail = (
        f'''<div class="grid grid-2" style="margin-top:1.1rem">
      <figure class="panel"><h3>Linhagem e a cadeia vencedora</h3><div class="chart-scroll">{lineage_tree(ga)}</div><figcaption>{lineage_note}</figcaption></figure>
      <figure class="panel"><h3>Onde a busca se concentrou</h3><div class="chart-scroll">{parent_usage_chart(ga)}</div><figcaption style="margin-bottom:1.2rem">{parents_note}</figcaption>{decision_table(ga)}</figure>
    </div>
    <div class="panel" style="margin-top:1.1rem"><h3>Livro de hipóteses · braço evolutivo</h3><p style="color:var(--ink-2);font-size:var(--step--1);margin:.2rem 0 1rem">Passe o mouse sobre a hipótese para ver o mecanismo declarado pelo agente.</p>{ledger(ga)}</div>'''
        if ga_valid else
        '''<div class="panel" style="margin-top:1.1rem"><h3>pydantic GA · execução interrompida</h3><p class="prose" style="color:var(--ink-2)">O braço Codex foi interrompido por falta de créditos. Seus indivíduos não são resultados válidos e foram removidos dos gráficos, métricas e comparações desta seção.</p></div>'''
    )
    if ga_valid:
        verdict = (
            '<div class="verdict">'
            + tile("evolução · melhor", f(ga_best, 3) + "×", f"indivíduo #{ga['best_ever_id']} · {gs['agent_calls']} chamadas", "var(--ga)")
            + tile("amostragem · melhor de " + str(ss["agent_calls"]), f(sa_best, 3) + "×", f"esperado de k={ss['agent_calls']}: {f(bok, 3)}×", "var(--sampling)")
            + tile("diferença", ("+" if delta >= 0 else "") + f(delta, 1) + "%", "evolução sobre a melhor amostra, mesmo orçamento", "var(--ga)" if delta >= 0 else "var(--sampling)")
            + "</div>"
        )
    else:
        verdict = (
            '<div class="verdict">'
            + tile("evolução · status", "interrompida", "pydantic GA não entrou nas métricas: limite de créditos atingido", "var(--muted)")
            + tile("amostragem · melhor de " + str(ss["agent_calls"]), f(sa_best, 3) + "×", f"esperado de k={ss['agent_calls']}: {f(bok, 3)}×", "var(--sampling)")
            + tile("referência pública", str(len(public_results)), "execuções GSO disponíveis para comparação", "var(--public)")
            + "</div>"
        )

    return f"""
<section id="{esc(name)}">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">alvo · {esc(meta["commit"])}</span>
      <h2>{esc(meta["title"])}</h2>
      <p class="prose" style="color:var(--ink-2);margin:.4rem 0 0">{esc(meta["api"])} · baseline {f(gs["baseline_median"] * 1000)} ms · braço GA: <strong>{agent_note}</strong> · {public_note} · <a href="{esc(meta["public_source"])}">fonte pública</a></p>
    </div>

    {verdict}

    <figure class="panel" style="margin-top:1.6rem">
      <h3>Comparação direta: local × dado público</h3>
      <div class="chart-scroll">{comparison_chart(ga, sa, public_results, meta["ga_label"])}</div>
      <figcaption>As barras laranja são execuções individuais publicadas pelo GSO; as duas primeiras barras são resultados locais. Métrica pública: média geométrica do speedup do patch contra o baseline oficial.</figcaption>
    </figure>

    <figure class="panel" style="margin-top:1.6rem">
      <h3>Rodada a rodada: a linhagem contra as tentativas do zero</h3>
      {legend(*ga_legend_items, (f"tentativas locais · {meta['agent']}", "var(--sampling)", "swatch"), ("amostragem local · melhor até agora", "var(--sampling)", "line"), (f"execuções públicas GSO (n={len(public_results)})", "var(--public)", "line") if public_results else ("sem execução pública por tarefa", "var(--muted)", "swatch"))}
      <div class="chart-scroll">{solo_vs_lineage_chart(ga, sa, public_results, meta["ga_label"], "amostragem local")}</div>
      <figcaption>{solo_note}</figcaption>
    </figure>

    <div class="grid grid-2" style="margin-top:1.6rem">
      <figure class="panel">
        <h3>Ganho acumulado por chamada gasta</h3>
        {legend(*trajectory_legend_items, (f"amostragem local · melhor de k", "var(--sampling)", "line"), ("faixa p10–p90 da amostragem", "var(--sampling)", "swatch"), (f"execuções públicas GSO (n={len(public_results)})", "var(--public)", "line") if public_results else ("sem execução pública por tarefa", "var(--muted)", "swatch"))}
        <div class="chart-scroll">{trajectory_chart(ga, sa, public_results, meta["ga_label"], "amostragem local")}</div>
        <figcaption>{chart_note}</figcaption>
      </figure>
      <figure class="panel">
        <h3>Cada indivíduo, um ponto</h3>
        {legend(("indivíduo da evolução", "var(--ga)", "swatch"), ("indivíduo da amostragem", "var(--sampling)", "swatch"), ("descartado", "var(--muted)", "swatch"))}
        <div class="chart-scroll">{strip_chart(ga, sa)}</div>
        <figcaption>{strip_note}</figcaption>
      </figure>
    </div>

    {evolution_detail}

    <div class="panel" style="margin-top:1.1rem">
      <h3>Livro de hipóteses · braço de controle (amostragem)</h3>
      {ledger(sa)}
    </div>
  </div>
</section>
"""


def build(bundle, narrative, public_bundle):
    targets = bundle["targets"]
    failures = narrative["failures"].replace(
        "Tudo o que está neste relatório vale para tornado.\n        A réplica em pydantic está agendada para hoje, 21h.",
        "O gráfico do pydantic permanece visível para comparação; o braço GA Codex foi interrompido por falta de créditos e foi removido dos resultados.",
    )
    sections = "".join(
        target_section(name, targets[name], narrative.get(name, {}), public_bundle)
        for name in TARGET_META
        if name in targets and "ga" in targets[name] and "sampling" in targets[name]
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{narrative["title"]}</title>
{FONTS}
<style>{CSS}</style>
</head>
<body>

<header class="masthead">
  <div class="wrap">
    <span class="eyebrow">HypEvolve · rodada de 17 de setembro de 2026</span>
    <h1>{narrative["h1"]}</h1>
    <p class="lede">{narrative["lede"]}</p>
    <div class="runstamp">{narrative["stamp"]}</div>
  </div>
</header>

{narrative["method"]}
{sections}
{failures}
{narrative["verdict"]}

<footer><div class="wrap">{narrative["footer"]}</div></footer>
{TOOLTIP_JS}
</body>
</html>
"""


def main():
    bundle = json.loads((ROOT / "results/analysis.json").read_text())
    narrative = json.loads((ROOT / "scripts/report/narrative.json").read_text())
    public_bundle = json.loads((ROOT / "scripts/report/public_gso.json").read_text())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(bundle, narrative, public_bundle), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
