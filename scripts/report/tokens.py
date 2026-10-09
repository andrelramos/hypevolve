"""Design tokens + page chrome for the HypEvolve report artifact."""

CSS = """
:root {
  --ga:        #6D4BD6;
  --sampling:  #0F8F7E;
  --public:    #B36B00;
  --confirmed: #2E7D4F;
  --refuted:   #B23A48;
  --ground:    #F5F4F8;
  --panel:     #FFFFFF;
  --panel-2:   #EEECF4;
  --ink:       #17152B;
  --ink-2:     #45415C;
  --muted:     #6E6987;
  --hairline:  #DFDCEA;
  --grid:      #E8E5F0;
  --shadow:    0 1px 2px rgba(23,21,43,.05), 0 8px 24px -12px rgba(23,21,43,.18);
  --measure:   68ch;
  --step--1:   clamp(.78rem, .76rem + .12vw, .84rem);
  --step-0:    clamp(1rem, .97rem + .15vw, 1.08rem);
  --step-1:    clamp(1.2rem, 1.1rem + .4vw, 1.4rem);
  --step-2:    clamp(1.5rem, 1.3rem + .9vw, 2rem);
  --step-3:    clamp(2rem, 1.6rem + 1.9vw, 3.1rem);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ga:        #8B6BE8;
    --sampling:  #23A992;
    --public:    #E5A642;
    --confirmed: #4FB07B;
    --refuted:   #E0697A;
    --ground:    #131120;
    --panel:     #1B1829;
    --panel-2:   #232037;
    --ink:       #EDEBF5;
    --ink-2:     #C3BFD4;
    --muted:     #918BA8;
    --hairline:  #2E2A44;
    --grid:      #272341;
    --shadow:    0 1px 2px rgba(0,0,0,.4), 0 10px 30px -14px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"] {
  --ga:        #8B6BE8;
  --sampling:  #23A992;
  --public:    #E5A642;
  --confirmed: #4FB07B;
  --refuted:   #E0697A;
  --ground:    #131120;
  --panel:     #1B1829;
  --panel-2:   #232037;
  --ink:       #EDEBF5;
  --ink-2:     #C3BFD4;
  --muted:     #918BA8;
  --hairline:  #2E2A44;
  --grid:      #272341;
  --shadow:    0 1px 2px rgba(0,0,0,.4), 0 10px 30px -14px rgba(0,0,0,.7);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "IBM Plex Serif", Georgia, serif;
  font-size: var(--step-0);
  line-height: 1.62;
  -webkit-font-smoothing: antialiased;
}
.wrap { width: min(1160px, 92vw); margin-inline: auto; }
.prose { max-width: var(--measure); }
h1, h2, h3, .eyebrow, .metric, th, .tag, .legend, figcaption {
  font-family: "IBM Plex Sans Condensed", "IBM Plex Sans", system-ui, sans-serif;
}
h1 { font-size: var(--step-3); line-height: 1.02; margin: 0; letter-spacing: -.02em; text-wrap: balance; font-weight: 600; }
h2 { font-size: var(--step-2); line-height: 1.1; margin: 0 0 .4em; letter-spacing: -.01em; text-wrap: balance; font-weight: 600; }
h3 { font-size: var(--step-1); margin: 0 0 .3em; font-weight: 600; letter-spacing: -.005em; }
p { margin: 0 0 1em; }
a { color: inherit; text-underline-offset: .18em; text-decoration-thickness: 1px; }
code, .mono, td.num, .metric-value { font-family: "IBM Plex Mono", ui-monospace, monospace; font-variant-numeric: tabular-nums; }
code { font-size: .88em; background: var(--panel-2); padding: .1em .35em; border-radius: 3px; }

.eyebrow {
  font-size: var(--step--1); text-transform: uppercase; letter-spacing: .12em;
  color: var(--muted); font-weight: 600;
}
header.masthead { border-bottom: 1px solid var(--hairline); padding: clamp(2.5rem, 6vw, 5rem) 0 2.2rem; }
.masthead .lede { font-size: var(--step-1); color: var(--ink-2); max-width: 58ch; margin-top: 1.2rem; }
.runstamp { display: flex; flex-wrap: wrap; gap: .4rem 1.4rem; margin-top: 1.6rem; font-family: "IBM Plex Mono", monospace; font-size: var(--step--1); color: var(--muted); }

section { padding: clamp(2.2rem, 5vw, 3.6rem) 0; border-bottom: 1px solid var(--hairline); }
section:last-of-type { border-bottom: 0; }
.section-head { display: flex; flex-direction: column; gap: .2rem; margin-bottom: 1.6rem; }

.panel {
  background: var(--panel); border: 1px solid var(--hairline); border-radius: 10px;
  padding: clamp(1rem, 2.4vw, 1.6rem); box-shadow: var(--shadow);
}
.grid { display: grid; gap: 1.1rem; }
@media (min-width: 900px) { .grid-2 { grid-template-columns: 1fr 1fr; } }

.verdict { display: grid; gap: .9rem; margin-top: 1.8rem; }
@media (min-width: 820px) { .verdict { grid-template-columns: repeat(3, 1fr); } }
.metric { border-left: 3px solid var(--rule, var(--ga)); padding: .7rem 0 .7rem 1rem; background: var(--panel); }
.metric-label { font-size: var(--step--1); text-transform: uppercase; letter-spacing: .1em; color: var(--muted); }
.metric-value { font-size: var(--step-2); line-height: 1.1; display: block; margin-top: .15rem; font-weight: 500; }
.metric-note { font-size: var(--step--1); color: var(--ink-2); font-family: "IBM Plex Sans Condensed", sans-serif; }

figure { margin: 0; }
figcaption { font-size: var(--step--1); color: var(--muted); margin-top: .7rem; line-height: 1.5; }
.chart-scroll { overflow-x: auto; }
svg { display: block; max-width: 100%; height: auto; }
.legend { display: flex; flex-wrap: wrap; gap: .3rem 1.2rem; font-size: var(--step--1); color: var(--ink-2); margin-bottom: .9rem; }
.legend span { display: inline-flex; align-items: center; gap: .42rem; }
.swatch { width: 11px; height: 11px; border-radius: 2px; display: inline-block; }
.swatch.line { height: 3px; border-radius: 2px; width: 16px; }

table { border-collapse: collapse; width: 100%; font-size: var(--step--1); }
th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--hairline); vertical-align: top; }
th { font-size: var(--step--1); text-transform: uppercase; letter-spacing: .07em; color: var(--muted); font-weight: 600; white-space: nowrap; }
td.num { text-align: right; white-space: nowrap; }
tbody tr:hover { background: var(--panel-2); }
.tag { display: inline-flex; align-items: center; gap: .3rem; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; padding: .12rem .42rem; border-radius: 3px; border: 1px solid currentColor; white-space: nowrap; }
.tag.confirmed { color: var(--confirmed); }
.tag.refuted   { color: var(--refuted); }
.tag.dead      { color: var(--muted); }
.hyp { font-family: "IBM Plex Serif", serif; line-height: 1.4; }

.tooltip {
  position: fixed; pointer-events: none; opacity: 0; transition: opacity .1s;
  background: var(--panel); color: var(--ink); border: 1px solid var(--hairline);
  border-radius: 6px; padding: .5rem .6rem; font-family: "IBM Plex Sans Condensed", sans-serif;
  font-size: var(--step--1); line-height: 1.4; box-shadow: var(--shadow); z-index: 50; max-width: 320px;
}
.tooltip.on { opacity: 1; }
.tooltip b { font-family: "IBM Plex Mono", monospace; font-weight: 600; }

.callout { border-left: 3px solid var(--refuted); background: var(--panel); padding: 1rem 1.2rem; }
.callout.good { border-left-color: var(--confirmed); }
.callout .eyebrow { color: var(--refuted); }
.callout.good .eyebrow { color: var(--confirmed); }

footer { padding: 2.5rem 0 4rem; color: var(--muted); font-size: var(--step--1); }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
:focus-visible { outline: 2px solid var(--ga); outline-offset: 2px; }
"""

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=IBM+Plex+Sans+Condensed:wght@400;500;600&"
    "family=IBM+Plex+Serif:ital,wght@0,400;0,500;1,400&display=swap\">"
)

TOOLTIP_JS = """
<script>
(function () {
  const tip = document.createElement('div');
  tip.className = 'tooltip';
  document.body.appendChild(tip);
  function show(e) {
    const t = e.target.closest('[data-tip]');
    if (!t) return;
    tip.innerHTML = t.getAttribute('data-tip');
    tip.classList.add('on');
    move(e);
  }
  function move(e) {
    const pad = 14;
    let x = e.clientX + pad, y = e.clientY + pad;
    const r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = e.clientY - r.height - pad;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  document.addEventListener('mouseover', show);
  document.addEventListener('mousemove', function (e) { if (tip.classList.contains('on')) move(e); });
  document.addEventListener('mouseout', function (e) {
    if (e.target.closest('[data-tip]')) tip.classList.remove('on');
  });
})();
</script>
"""
