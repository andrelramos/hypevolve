"""Inline-SVG charts for the HypEvolve report. No external libraries."""
import html
import statistics


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def _fmt(x: float, n: int = 3) -> str:
    return f"{x:.{n}f}"


class Scale:
    def __init__(self, d0, d1, r0, r1):
        self.d0, self.d1, self.r0, self.r1 = d0, d1, r0, r1
        self.span = (d1 - d0) or 1.0

    def __call__(self, v):
        return self.r0 + (v - self.d0) / self.span * (self.r1 - self.r0)


def _ticks(lo, hi, count=5):
    raw = (hi - lo) / max(count - 1, 1)
    if raw <= 0:
        return [lo]
    mag = 10 ** (len(str(int(abs(raw)))) - 1) if abs(raw) >= 1 else 0.1
    for step in (mag * 0.1, mag * 0.2, mag * 0.25, mag * 0.5, mag, mag * 2, mag * 2.5, mag * 5, mag * 10):
        if step >= raw:
            break
    start = (lo // step) * step
    out, v = [], start
    while v <= hi + step * 0.5:
        if v >= lo - 1e-9:
            out.append(round(v, 6))
        v += step
    return out


def trajectory_chart(ga, sampling, public_results=None, ga_label="evolução", sampling_label="amostragem", width=600, height=330):
    """Best speedup reached so far, with public GSO runs as a separate series.

    Public observations use the official ``gm_speedup_patch_base`` metric. They
    are shown as an orange range plus individual horizontal traces, never as
    HypEvolve calls.
    """
    m = dict(t=18, r=118, b=44, l=52)
    traj = ga["trajectory"] if ga["summary"].get("n_valid", 0) else []
    bok = sampling["best_of_k"]
    n = max(len(traj), len(bok)) or 1

    ys = [p["best_so_far"] for p in traj] + [p["p90"] for p in bok] + [1.0]
    public_runs = list(public_results or [])
    public_values = [float(r["speedup"]) for r in public_runs]
    ys.extend(public_values)
    lo, hi = 1.0, max(ys) * 1.06
    x = Scale(1, n, m["l"], width - m["r"])
    y = Scale(lo, hi, height - m["b"], m["t"])

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Melhor speedup alcançado por chamada de LLM">']
    # grid + y axis
    for t in _ticks(lo, hi, 5):
        yy = y(t)
        parts.append(f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{m["l"]-9}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)" font-family="IBM Plex Mono, monospace">{_fmt(t,2)}x</text>')
    # x axis
    for t in [1] + [v for v in (5, 10, 15, 20, 25) if v <= n]:
        xx = x(t)
        parts.append(f'<text x="{xx:.1f}" y="{height-m["b"]+18}" text-anchor="middle" font-size="11" fill="var(--muted)" font-family="IBM Plex Mono, monospace">{t}</text>')
    parts.append(f'<text x="{(m["l"]+width-m["r"])/2:.1f}" y="{height-6}" text-anchor="middle" font-size="11" fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">chamadas de LLM gastas</text>')
    parts.append(f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{y(1.0):.1f}" y2="{y(1.0):.1f}" stroke="var(--hairline)" stroke-width="1.5"/>')

    if public_values:
        public_lo, public_hi = min(public_values), max(public_values)
        public_med = statistics.median(public_values)
        parts.append(
            f'<rect x="{m["l"]}" y="{y(public_hi):.1f}" width="{width-m["l"]-m["r"]}" '
            f'height="{max(2.0, y(public_lo)-y(public_hi)):.1f}" fill="var(--public)" fill-opacity=".10"/>'
        )
        for run in public_runs:
            value = float(run["speedup"])
            yy = y(value)
            parts.append(
                f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" '
                'stroke="var(--public)" stroke-width="1" stroke-opacity=".35" stroke-dasharray="2 5" '
                f'data-tip="<b>{esc(run["model"])}</b> · GSO público<br>{_fmt(value, 3)}x vs baseline"/>'
            )
        yy = y(public_med)
        parts.append(
            f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" '
            'stroke="var(--public)" stroke-width="2" stroke-dasharray="7 5"/>'
        )
        parts.append(
            f'<text x="{width-m["r"]-4:.1f}" y="{yy-7:.1f}" text-anchor="end" '
            'font-size="11" fill="var(--public)" font-family="IBM Plex Sans Condensed, sans-serif" '
            f'font-weight="600">GSO público · mediana {_fmt(public_med, 2)}x · n={len(public_values)}</text>'
        )

    # sampling: p10-p90 band + expected best-of-k
    if bok:
        up = " ".join(f'{x(p["k"]):.1f},{y(p["p90"]):.1f}' for p in bok)
        dn = " ".join(f'{x(p["k"]):.1f},{y(p["p10"]):.1f}' for p in reversed(bok))
        parts.append(f'<polygon points="{up} {dn}" fill="var(--sampling)" fill-opacity="0.13"/>')
        line = " ".join(f'{x(p["k"]):.1f},{y(p["mean"]):.1f}' for p in bok)
        parts.append(f'<polyline points="{line}" fill="none" stroke="var(--sampling)" stroke-width="2" stroke-linejoin="round"/>')
        last = bok[-1]
        parts.append(f'<circle cx="{x(last["k"]):.1f}" cy="{y(last["mean"]):.1f}" r="4.5" fill="var(--sampling)"/>')
        parts.append(f'<text x="{x(last["k"])+10:.1f}" y="{y(last["mean"])+1:.1f}" font-size="12" fill="var(--sampling)" font-family="IBM Plex Sans Condensed, sans-serif" font-weight="600">{esc(sampling_label)}</text>')
        parts.append(f'<text x="{x(last["k"])+10:.1f}" y="{y(last["mean"])+15:.1f}" font-size="12" fill="var(--sampling)" font-family="IBM Plex Mono, monospace">{_fmt(last["mean"],2)}x</text>')

    # GA: step line of best-so-far, generation boundaries marked
    if traj:
        pts, prev = [], None
        for p in traj:
            xx, yy = x(p["call"]), y(p["best_so_far"])
            if prev is not None:
                pts.append(f'{xx:.1f},{prev:.1f}')
            pts.append(f'{xx:.1f},{yy:.1f}')
            prev = yy
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="var(--ga)" stroke-width="2.5" stroke-linejoin="round"/>')
        seen = set()
        for p in traj:
            if p["generation"] in seen:
                continue
            seen.add(p["generation"])
            if p["generation"] == 0:
                continue
            xx = x(p["call"])
            parts.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{m["t"]}" y2="{height-m["b"]}" stroke="var(--ga)" stroke-opacity=".22" stroke-width="1" stroke-dasharray="3 3"/>')
            parts.append(f'<text x="{xx+3:.1f}" y="{m["t"]+11}" font-size="10" fill="var(--muted)" font-family="IBM Plex Mono, monospace">g{p["generation"]}</text>')
        last = traj[-1]
        parts.append(f'<circle cx="{x(last["call"]):.1f}" cy="{y(last["best_so_far"]):.1f}" r="4.5" fill="var(--ga)"/>')
        parts.append(f'<text x="{x(last["call"])+10:.1f}" y="{y(last["best_so_far"])+1:.1f}" font-size="12" fill="var(--ga)" font-family="IBM Plex Sans Condensed, sans-serif" font-weight="600">{esc(ga_label)}</text>')
        parts.append(f'<text x="{x(last["call"])+10:.1f}" y="{y(last["best_so_far"])+15:.1f}" font-size="12" fill="var(--ga)" font-family="IBM Plex Mono, monospace">{_fmt(last["best_so_far"],2)}x</text>')
    parts.append("</svg>")
    return "".join(parts)


def comparison_chart(ga, sampling, public_results=None, ga_label="HypEvolve GA", width=600, height=300):
    """Compare local maxima with every available public per-task result."""
    values = [sampling["summary"]["best_speedup_vs_base"]]
    labels = ["amostragem local"]
    colors = ["var(--sampling)"]
    origins = ["resultado local"]
    if ga["summary"].get("n_valid", 0):
        values.insert(0, ga["best_ever_speedup_vs_base"])
        labels.insert(0, ga_label)
        colors.insert(0, "var(--ga)")
        origins.insert(0, "resultado local")
    for public in public_results or []:
        values.append(float(public["speedup"]))
        labels.append(str(public["model"]))
        colors.append("var(--public)")
        origins.append("execução pública GSO")
    width = max(width, 92 * len(values) + 70)
    m = dict(t=22, r=18, b=100, l=52)
    lo, hi = 0.0, max(values + [1.0]) * 1.15
    y = Scale(lo, hi, height - m["b"], m["t"])
    band = (width - m["l"] - m["r"]) / len(values)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Comparação entre HypEvolve, amostragem local e referência pública GSO">']
    for tick in _ticks(1.0, hi, 4):
        yy = y(tick)
        parts.append(f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{m["l"]-8}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)" font-family="IBM Plex Mono, monospace">{_fmt(tick, 1)}x</text>')
    for i, (value, label, color, origin) in enumerate(zip(values, labels, colors, origins)):
        cx = m["l"] + band * (i + 0.5)
        bar_w = min(110, band * 0.62)
        top = y(value)
        parts.append(f'<rect x="{cx-bar_w/2:.1f}" y="{top:.1f}" width="{bar_w:.1f}" height="{y(0)-top:.1f}" rx="4" fill="{color}" fill-opacity=".88" data-tip="<b>{esc(label)}</b> · {esc(origin)}<br>{_fmt(value, 3)}x vs baseline"/>')
        parts.append(f'<text x="{cx:.1f}" y="{top-7:.1f}" text-anchor="middle" font-size="12" fill="{color}" font-family="IBM Plex Mono, monospace" font-weight="600">{_fmt(value, 2)}x</text>')
        label_y = height - m["b"] + 18
        parts.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" transform="rotate(-32 {cx:.1f} {label_y:.1f})" text-anchor="end" font-size="11" fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">{esc(label)}</text>')
    if not public_results:
        parts.append(f'<text x="{width-m["r"]}" y="{m["t"]+4}" text-anchor="end" font-size="11" fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">referência pública por tarefa: não publicada</text>')
    parts.append('</svg>')
    return "".join(parts)


def strip_chart(ga, sampling, width=600, height=320):
    """Every individual as one dot: evolution grouped by generation, sampling as one pool."""
    m = dict(t=16, r=18, b=46, l=52)
    ga_ind = ga["individuals"] if ga["summary"].get("n_valid", 0) else []
    sa_ind = sampling["individuals"]
    gens = sorted({r["generation"] for r in ga_ind})
    cols = [("g%d" % g, [r for r in ga_ind if r["generation"] == g], "var(--ga)") for g in gens]
    cols.append(("amostragem", sa_ind, "var(--sampling)"))

    vals = [r["speedup_vs_base"] for r in ga_ind + sa_ind if r["passed"]] + [1.0]
    lo, hi = min(min(vals), 1.0) * 0.98, max(vals) * 1.06
    y = Scale(lo, hi, height - m["b"], m["t"])
    band = (width - m["l"] - m["r"]) / len(cols)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Distribuição de speedup por geração e no braço de amostragem">']
    for t in _ticks(lo, hi, 5):
        yy = y(t)
        parts.append(f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{m["l"]-9}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="var(--muted)" font-family="IBM Plex Mono, monospace">{_fmt(t,2)}x</text>')
    parts.append(f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{y(1.0):.1f}" y2="{y(1.0):.1f}" stroke="var(--hairline)" stroke-width="1.5"/>')

    for i, (label, rows, color) in enumerate(cols):
        cx = m["l"] + band * (i + 0.5)
        parts.append(f'<text x="{cx:.1f}" y="{height-m["b"]+18}" text-anchor="middle" font-size="11" fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">{esc(label)}</text>')
        ok = [r for r in rows if r["passed"]]
        dead = [r for r in rows if not r["passed"]]
        if ok:
            med = sorted(r["speedup_vs_base"] for r in ok)[len(ok) // 2]
            parts.append(f'<line x1="{cx-band*0.3:.1f}" x2="{cx+band*0.3:.1f}" y1="{y(med):.1f}" y2="{y(med):.1f}" stroke="{color}" stroke-width="2" stroke-opacity=".45"/>')
        for j, r in enumerate(sorted(rows, key=lambda r: r["speedup_vs_base"])):
            jitter = ((j % 5) - 2) * (band * 0.11)
            if r["passed"]:
                cy = y(r["speedup_vs_base"])
                tip = (f'<b>#{r["individual_id"]}</b> · geração {r["generation"]}<br>'
                       f'<b>{_fmt(r["speedup_vs_base"])}x</b> vs base · p={_fmt(r["p_value_vs_base"] or 1, 5)}<br>'
                       f'{esc(r["hypothesis"][:150] or "—")}')
                parts.append(f'<circle cx="{cx+jitter:.1f}" cy="{cy:.1f}" r="5" fill="{color}" fill-opacity=".8" stroke="var(--panel)" stroke-width="2" data-tip="{tip}"/>')
            else:
                cy = height - m["b"] - 9
                why = "erro de agente" if r.get("agent_error") else ("burlou arquivos protegidos" if r["cheated"] else "quebrou os testes")
                tip = f'<b>#{r["individual_id"]}</b> · geração {r["generation"]}<br>descartado: {why}'
                parts.append(f'<path d="M{cx+jitter-4:.1f},{cy-4:.1f} l8,8 M{cx+jitter+4:.1f},{cy-4:.1f} l-8,8" stroke="var(--muted)" stroke-width="1.6" data-tip="{tip}"/>')
        if dead:
            parts.append(f'<text x="{cx:.1f}" y="{m["t"]+2:.1f}" text-anchor="middle" font-size="10" fill="var(--muted)" font-family="IBM Plex Mono, monospace">{len(dead)}✗</text>')
    parts.append("</svg>")
    return "".join(parts)


def lineage_tree(ga, width=560, height=430):
    """Who descended from whom, and which tournament pick produced each child."""
    ind = {r["individual_id"]: r for r in ga["individuals"]}
    gens = sorted({r["generation"] for r in ga["individuals"]})
    m = dict(t=30, r=22, b=26, l=44)
    colw = (width - m["l"] - m["r"]) / max(len(gens), 1)

    pos = {}
    for gi, g in enumerate(gens):
        rows = [r for r in ga["individuals"] if r["generation"] == g]
        rows.sort(key=lambda r: -r["speedup_vs_base"])
        step = (height - m["t"] - m["b"]) / max(len(rows), 1)
        for ri, r in enumerate(rows):
            pos[r["individual_id"]] = (m["l"] + colw * gi + colw * 0.34, m["t"] + step * (ri + 0.5))

    best = max(ga["individuals"], key=lambda r: r["speedup_vs_base"])
    path, cur = set(), best
    while cur is not None:
        path.add(cur["individual_id"])
        cur = ind.get(cur["parent_id"]) if cur["parent_id"] is not None else None

    mx = max(r["speedup_vs_base"] for r in ga["individuals"]) or 1.0
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Árvore de linhagem: pais, filhos e a cadeia vencedora">']
    for gi, g in enumerate(gens):
        parts.append(f'<text x="{m["l"]+colw*gi+colw*0.34:.1f}" y="{m["t"]-12}" text-anchor="middle" font-size="11" fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">geração {g}</text>')
    # edges
    for r in ga["individuals"]:
        if r["parent_id"] is None or r["parent_id"] not in pos or r["individual_id"] not in pos:
            continue
        x1, y1 = pos[r["parent_id"]]
        x2, y2 = pos[r["individual_id"]]
        on = r["individual_id"] in path and r["parent_id"] in path
        parts.append(
            f'<path d="M{x1:.1f},{y1:.1f} C{(x1+x2)/2:.1f},{y1:.1f} {(x1+x2)/2:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="{"var(--ga)" if on else "var(--hairline)"}" stroke-width="{2.4 if on else 1.2}" '
            f'stroke-opacity="{1 if on else .9}"/>'
        )
    # nodes
    for iid, (cx, cy) in pos.items():
        r = ind[iid]
        alive = r["passed"]
        rad = 5 + 9 * max(0.0, (r["speedup_vs_base"] - 1.0) / max(mx - 1.0, 0.001)) if alive else 4
        fill = "var(--ga)" if alive else "var(--panel-2)"
        op = ".9" if iid in path else (".42" if alive else ".9")
        why = "erro de agente" if r.get("agent_error") else ("burlou arquivos protegidos" if r["cheated"] else "quebrou os testes")
        tip = (f'<b>#{iid}</b> · geração {r["generation"]}'
               + (f' · filho de #{r["parent_id"]}' if r["parent_id"] is not None else " · semente")
               + "<br>" + (f'<b>{_fmt(r["speedup_vs_base"])}x</b> vs base' if alive else f"descartado: {why}")
               + "<br>" + esc((r["hypothesis"] or "—")[:160]))
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{fill}" fill-opacity="{op}" stroke="var(--panel)" stroke-width="2" data-tip="{tip}"/>')
        if iid in path:
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad+3.5:.1f}" fill="none" stroke="var(--ga)" stroke-width="1.5"/>')
            parts.append(f'<text x="{cx:.1f}" y="{cy-rad-7:.1f}" text-anchor="middle" font-size="10" fill="var(--ga)" font-family="IBM Plex Mono, monospace" font-weight="600">{_fmt(r["speedup_vs_base"],2)}x</text>')
        parts.append(f'<text x="{cx:.1f}" y="{cy+3.5:.1f}" text-anchor="middle" font-size="9" fill="var(--panel)" font-family="IBM Plex Mono, monospace" pointer-events="none">{iid}</text>')
    parts.append("</svg>")
    return "".join(parts)


def parent_usage_chart(ga, width=560, height=200):
    """How often each individual was picked as a parent — shows where the search concentrated."""
    counts = {}
    for e in ga["selections"]:
        if e["kind"] == "tournament":
            counts[e["winner_id"]] = counts.get(e["winner_id"], 0) + 1
    if not counts:
        return ""
    ind = {r["individual_id"]: r for r in ga["individuals"]}
    rows = sorted(counts.items(), key=lambda kv: -kv[1])
    m = dict(t=14, r=26, b=32, l=54)
    mx = max(counts.values())
    x = Scale(0, mx, m["l"], width - m["r"])
    barh = min(22, (height - m["t"] - m["b"]) / max(len(rows), 1))
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Quantas vezes cada indivíduo foi escolhido como pai">']
    for i, (iid, c) in enumerate(rows):
        yy = m["t"] + i * barh
        w = x(c) - m["l"]
        r = ind.get(iid, {})
        tip = (f'<b>#{iid}</b> venceu <b>{c}</b> torneio{"s" if c > 1 else ""}<br>'
               f'fitness {_fmt(r.get("fitness", 0), 3)} · {_fmt(r.get("speedup_vs_base", 1))}x vs base')
        parts.append(f'<rect x="{m["l"]}" y="{yy+2:.1f}" width="{max(w,2):.1f}" height="{barh-6:.1f}" rx="3" fill="var(--ga)" fill-opacity=".85" data-tip="{tip}"/>')
        parts.append(f'<text x="{m["l"]-8}" y="{yy+barh/2+1:.1f}" text-anchor="end" font-size="11" fill="var(--ink-2)" font-family="IBM Plex Mono, monospace">#{iid}</text>')
        parts.append(f'<text x="{m["l"]+max(w,2)+7:.1f}" y="{yy+barh/2+1:.1f}" font-size="11" fill="var(--muted)" font-family="IBM Plex Mono, monospace">{c}</text>')
    parts.append(f'<text x="{m["l"]:.1f}" y="{height-8}" font-size="11" fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">torneios vencidos (de {sum(counts.values())})</text>')
    parts.append("</svg>")
    return "".join(parts)


def decision_table(ga):
    """Generation by generation: which elite was kept, which parents won, what the children scored."""
    ind = {r["individual_id"]: r for r in ga["individuals"]}
    gens = sorted({e["generation"] for e in ga["selections"]})
    rows = []
    for g in gens:
        evs = [e for e in ga["selections"] if e["generation"] == g]
        elite = [e for e in evs if e["kind"] == "elite"]
        tours = [e for e in evs if e["kind"] == "tournament"]
        kids = [ind[e["child_id"]] for e in tours if e["child_id"] in ind]
        best_kid = max(kids, key=lambda r: r["speedup_vs_base"]) if kids else None
        elite_txt = ", ".join(
            f'#{e["winner_id"]} <span class="mono">{_fmt(ind[e["winner_id"]]["speedup_vs_base"], 2)}x</span>'
            for e in elite if e["winner_id"] in ind
        ) or "—"
        parent_txt = ", ".join(
            f'<span data-tip="torneio entre {", ".join("#" + str(c) for c in e["contenders"])}">'
            f'#{e["winner_id"]}→#{e["child_id"]}</span>'
            for e in tours
        )
        rows.append(
            f"<tr><td>g{g}</td><td>{elite_txt}</td>"
            f'<td class="mono" style="font-size:.72rem">{parent_txt}</td>'
            + (
                f'<td class="num">#{best_kid["individual_id"]} · {_fmt(best_kid["speedup_vs_base"], 2)}x</td>'
                if best_kid
                else '<td class="num">—</td>'
            )
            + "</tr>"
        )
    return (
        '<div class="chart-scroll"><table><thead><tr><th>ger</th><th>elite mantido</th>'
        "<th>pai → filho (torneio)</th><th>melhor filho</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def solo_vs_lineage_chart(ga, sampling, public_results=None, ga_label="evolução", sampling_label="amostragem local", width=980, height=430):
    """Local arms over the same x axis, plus a separate public reference series."""
    m = dict(t=44, r=160, b=60, l=58)
    ga_ind = sorted(ga["individuals"], key=lambda r: r["individual_id"]) if ga["summary"].get("n_valid", 0) else []
    sa_ind = sorted(sampling["individuals"], key=lambda r: r["individual_id"])
    n = max(len(ga_ind), len(sa_ind)) or 1

    vals = [r["speedup_vs_base"] for r in ga_ind + sa_ind if r["passed"]] + [1.0]
    public_runs = list(public_results or [])
    public_values = [float(r["speedup"]) for r in public_runs]
    vals.extend(public_values)
    top = max(vals) * 1.10
    x = Scale(1, n, m["l"], width - m["r"])
    y = Scale(1.0, top, height - m["b"], m["t"])
    base_y = y(1.0)

    def best_so_far(rows):
        out, best = [], 1.0
        for i, r in enumerate(rows, start=1):
            if r["passed"]:
                best = max(best, r["speedup_vs_base"])
            out.append((i, best))
        return out

    def step_path(points):
        d = []
        for i, (cx, v) in enumerate(points):
            px, py = x(cx), y(v)
            if i == 0:
                d.append(f"M{px:.1f},{py:.1f}")
            else:
                d.append(f"L{px:.1f},{y(points[i-1][1]):.1f} L{px:.1f},{py:.1f}")
        return " ".join(d)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Ganho por chamada gasta: linhagem evolutiva contra tentativas independentes">'
    ]
    for t in _ticks(1.0, top, 5):
        if t > top:  # _ticks overshoots by half a step; that label would sit off-canvas
            continue
        yy = y(t)
        parts.append(
            f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{m["l"]-10}" y="{yy+4:.1f}" text-anchor="end" font-size="11" '
            f'fill="var(--muted)" font-family="IBM Plex Mono, monospace">{_fmt(t,1)}x</text>'
        )
    parts.append(
        f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{base_y:.1f}" y2="{base_y:.1f}" '
        f'stroke="var(--hairline)" stroke-width="1.5"/>'
    )
    if public_values:
        public_lo, public_hi = min(public_values), max(public_values)
        public_med = statistics.median(public_values)
        parts.append(
            f'<rect x="{m["l"]}" y="{y(public_hi):.1f}" width="{width-m["l"]-m["r"]}" '
            f'height="{max(2.0, y(public_lo)-y(public_hi)):.1f}" fill="var(--public)" fill-opacity=".10"/>'
        )
        for run in public_runs:
            value = float(run["speedup"])
            public_y = y(value)
            parts.append(
                f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{public_y:.1f}" y2="{public_y:.1f}" '
                'stroke="var(--public)" stroke-width="1" stroke-opacity=".35" stroke-dasharray="2 5" '
                f'data-tip="<b>{esc(run["model"])}</b> · GSO público<br>{_fmt(value, 3)}x vs baseline"/>'
            )
        public_y = y(public_med)
        parts.append(
            f'<line x1="{m["l"]}" x2="{width-m["r"]}" y1="{public_y:.1f}" y2="{public_y:.1f}" '
            'stroke="var(--public)" stroke-width="2" stroke-dasharray="8 5"/>'
        )
        parts.append(
            f'<text x="{width-m["r"]-4:.1f}" y="{public_y-8:.1f}" text-anchor="end" '
            'font-size="11" fill="var(--public)" font-family="IBM Plex Sans Condensed, sans-serif" '
            f'font-weight="600">GSO público · mediana {_fmt(public_med, 2)}x · n={len(public_values)}</text>'
        )

    # generation boundaries: the evolutionary arm only gets feedback when a generation closes
    gens = sorted({r["generation"] for r in ga_ind})
    for g in gens:
        rows = [r for r in ga_ind if r["generation"] == g]
        x0 = x(rows[0]["individual_id"] + 1)
        x1 = x(rows[-1]["individual_id"] + 1)
        if g:
            edge = x0 - (x(2) - x(1)) / 2
            parts.append(
                f'<line x1="{edge:.1f}" x2="{edge:.1f}" y1="{m["t"]-16}" y2="{base_y:.1f}" '
                f'stroke="var(--hairline)" stroke-width="1" stroke-dasharray="3 4"/>'
            )
        parts.append(
            f'<text x="{(x0+x1)/2:.1f}" y="{m["t"]-20:.1f}" text-anchor="middle" font-size="10.5" '
            f'fill="var(--muted)" font-family="IBM Plex Sans Condensed, sans-serif">geração {g}</text>'
        )

    # best held after each call
    ga_bsf, sa_bsf = best_so_far(ga_ind), best_so_far(sa_ind)
    parts.append(
        f'<path d="{step_path(sa_bsf)}" fill="none" stroke="var(--sampling)" stroke-width="2" '
        f'stroke-linejoin="round"/>'
    )
    if ga_ind:
        parts.append(
            f'<path d="{step_path(ga_bsf)}" fill="none" stroke="var(--ga)" stroke-width="2" '
            f'stroke-linejoin="round"/>'
        )

    # the winning lineage, drawn parent to child across the calls that produced it
    chain_ids = set()
    if ga_ind:
        ind = {r["individual_id"]: r for r in ga_ind}
        best = max(ga_ind, key=lambda r: r["speedup_vs_base"])
        chain, cur = [], best
        while cur is not None:
            chain.append(cur)
            cur = ind.get(cur["parent_id"]) if cur["parent_id"] is not None else None
        chain.reverse()
        chain_ids = {r["individual_id"] for r in chain}
        for a, b in zip(chain, chain[1:]):
            parts.append(
                f'<line x1="{x(a["individual_id"]+1):.1f}" y1="{y(a["speedup_vs_base"]):.1f}" '
                f'x2="{x(b["individual_id"]+1):.1f}" y2="{y(b["speedup_vs_base"]):.1f}" '
                f'stroke="var(--ga)" stroke-width="1.5" stroke-opacity=".55" stroke-dasharray="4 3"/>'
            )

    # every call, both arms
    for rows, color, arm, dodge in ((sa_ind, "var(--sampling)", "tentativa independente", -2.5),
                                    (ga_ind, "var(--ga)", "indivíduo da evolução", 2.5)):
        for r in rows:
            cx = x(r["individual_id"] + 1) + dodge
            if not r["passed"]:
                why = "erro de agente" if r.get("agent_error") else (
                    "burlou arquivos protegidos" if r["cheated"] else "quebrou os testes"
                )
                tip = f'<b>#{r["individual_id"]}</b> · {arm}<br>descartado: {why}'
                parts.append(
                    f'<path d="M{cx-4:.1f},{base_y-9:.1f} l8,8 M{cx+4:.1f},{base_y-9:.1f} l-8,8" '
                    f'stroke="var(--muted)" stroke-width="1.6" data-tip="{tip}"/>'
                )
                continue
            cy = y(r["speedup_vs_base"])
            on_chain = arm.startswith("indiv") and r["individual_id"] in chain_ids
            tip = (
                f'<b>chamada {r["individual_id"]+1}</b> · {arm}'
                + (f' · geração {r["generation"]}' if arm.startswith("indiv") else "")
                + f'<br><b>{_fmt(r["speedup_vs_base"])}x</b> vs base · '
                f'p={_fmt(r["p_value_vs_base"] or 1, 5)}<br>'
                f'{esc((r["hypothesis"] or "—")[:150])}'
            )
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{6 if on_chain else 4.5}" fill="{color}" '
                f'fill-opacity="{1 if on_chain else .7}" stroke="var(--panel)" stroke-width="2" '
                f'data-tip="{tip}"/>'
            )

    # end labels, so the two curves never depend on the legend alone
    end_series = [(sampling_label, sa_bsf, "var(--sampling)")]
    if ga_ind:
        end_series.insert(0, (ga_label, ga_bsf, "var(--ga)"))
    if public_values:
        end_series.append(("mediana pública GSO", [(n, statistics.median(public_values))], "var(--public)"))
    for label, pts, color in end_series:
        v = pts[-1][1]
        parts.append(
            f'<line x1="{width-m["r"]:.1f}" x2="{width-m["r"]+10:.1f}" y1="{y(v):.1f}" '
            f'y2="{y(v):.1f}" stroke="{color}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{width-m["r"]+16:.1f}" y="{y(v)-2:.1f}" font-size="12.5" fill="var(--ink)" '
            f'font-family="IBM Plex Sans Condensed, sans-serif" font-weight="600">{_fmt(v,3)}x</text>'
        )
        parts.append(
            f'<text x="{width-m["r"]+16:.1f}" y="{y(v)+13:.1f}" font-size="11" fill="var(--muted)" '
            f'font-family="IBM Plex Sans Condensed, sans-serif">{esc(label)}</text>'
        )

    for t in range(1, n + 1):
        if t == 1 or t % 5 == 0:
            parts.append(
                f'<text x="{x(t):.1f}" y="{height-m["b"]+20:.1f}" text-anchor="middle" font-size="11" '
                f'fill="var(--muted)" font-family="IBM Plex Mono, monospace">{t}</text>'
            )
    parts.append(
        f'<text x="{m["l"]:.1f}" y="{height-m["b"]+42:.1f}" font-size="11.5" fill="var(--muted)" '
        f'font-family="IBM Plex Sans Condensed, sans-serif">chamadas de LLM gastas · '
        f'mesmo orçamento nos dois braços</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
