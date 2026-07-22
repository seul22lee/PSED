#!/usr/bin/env python3
"""Build a self-contained HTML gallery for the Ylilammi channel model.

Reads the three generated figures, base64-embeds them (so the page is fully
standalone / CSP-safe), and writes ylilammi_gallery.html.
"""
import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _img(name):
    return "data:image/png;base64," + base64.b64encode((HERE / name).read_bytes()).decode()

SAMPLES = _img("ylilammi_samples.png")
DYNAMICS = _img("ylilammi_dynamics.png")
WINDOW = _img("ylilammi_window.png")

HTML = f"""<title>Virtual ALD channel-coating model — Ylilammi et al. 2018</title>
<style>
  :root {{
    --bg:#f5f7f9; --surface:#ffffff; --figframe:#ffffff;
    --ink:#10151b; --muted:#566575; --faint:#8695a4;
    --line:#dce3ea; --accent:#0e7c86; --accent-soft:#e2f1f2; --hot:#c1440e;
    --shadow:0 1px 2px rgba(16,21,27,.05), 0 8px 24px rgba(16,21,27,.06);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg:#0d1117; --surface:#151b23; --figframe:#f3f5f7;
      --ink:#e6edf3; --muted:#95a4b4; --faint:#63717f;
      --line:#232c36; --accent:#39bfcb; --accent-soft:#0f2a2d; --hot:#ff8351;
      --shadow:0 1px 2px rgba(0,0,0,.3), 0 10px 30px rgba(0,0,0,.35);
    }}
  }}
  :root[data-theme="dark"] {{
    --bg:#0d1117; --surface:#151b23; --figframe:#f3f5f7;
    --ink:#e6edf3; --muted:#95a4b4; --faint:#63717f;
    --line:#232c36; --accent:#39bfcb; --accent-soft:#0f2a2d; --hot:#ff8351;
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 10px 30px rgba(0,0,0,.35);
  }}
  :root[data-theme="light"] {{
    --bg:#f5f7f9; --surface:#ffffff; --figframe:#ffffff;
    --ink:#10151b; --muted:#566575; --faint:#8695a4;
    --line:#dce3ea; --accent:#0e7c86; --accent-soft:#e2f1f2; --hot:#c1440e;
    --shadow:0 1px 2px rgba(16,21,27,.05), 0 8px 24px rgba(16,21,27,.06);
  }}

  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--bg); color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    line-height:1.6; -webkit-font-smoothing:antialiased;
  }}
  .mono {{ font-family:ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace; }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:clamp(28px,5vw,64px) clamp(18px,4vw,40px) 72px; }}

  /* header */
  .eyebrow {{
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
    font-size:12px; letter-spacing:.16em; text-transform:uppercase;
    color:var(--accent); margin:0 0 18px;
  }}
  h1 {{
    font-size:clamp(28px,4.4vw,44px); line-height:1.1; font-weight:680;
    letter-spacing:-.01em; text-wrap:balance; margin:0 0 18px; max-width:20ch;
  }}
  .thesis {{ font-size:clamp(16px,2vw,19px); color:var(--muted); max-width:64ch; margin:0 0 30px; }}
  .thesis b {{ color:var(--ink); font-weight:600; }}

  .specstrip {{ display:flex; flex-wrap:wrap; gap:10px; margin:0 0 8px; }}
  .chip {{
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:12.5px;
    padding:7px 12px; border:1px solid var(--line); border-radius:8px;
    background:var(--surface); color:var(--muted); white-space:nowrap;
  }}
  .chip b {{ color:var(--ink); font-weight:600; }}
  .chip.io {{ border-color:var(--accent); color:var(--accent); background:var(--accent-soft); }}

  .rule {{ height:1px; background:var(--line); border:0; margin:44px 0; }}

  /* plates */
  .plate {{ margin:0 0 8px; }}
  .kicker {{
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
    font-size:12px; letter-spacing:.14em; text-transform:uppercase;
    color:var(--faint); margin:0 0 6px;
  }}
  h2 {{ font-size:clamp(20px,2.6vw,26px); font-weight:640; letter-spacing:-.01em; margin:0 0 12px; text-wrap:balance; }}
  .cap {{ color:var(--muted); max-width:70ch; margin:0 0 20px; }}
  .cap b {{ color:var(--ink); font-weight:600; }}
  .cap .m {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.92em; color:var(--ink); }}

  figure {{ margin:0; }}
  .figcard {{
    background:var(--figframe); border:1px solid var(--line); border-radius:12px;
    padding:14px; box-shadow:var(--shadow); overflow-x:auto;
    transition:transform .18s ease, box-shadow .18s ease;
  }}
  .figcard:hover {{ transform:translateY(-2px); box-shadow:0 2px 4px rgba(16,21,27,.06), 0 16px 40px rgba(16,21,27,.12); }}
  .figcard img {{ display:block; width:100%; height:auto; min-width:640px; border-radius:4px; }}

  /* mechanism + table */
  .mech {{
    background:var(--surface); border:1px solid var(--line); border-radius:12px;
    padding:22px 24px; box-shadow:var(--shadow);
  }}
  .mech h3 {{ margin:0 0 14px; font-size:15px; font-weight:640; }}
  .chain {{
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-size:13.5px;
    color:var(--ink); overflow-x:auto; white-space:nowrap; padding-bottom:6px;
  }}
  .chain .arw {{ color:var(--accent); padding:0 10px; }}
  .chain .var {{ color:var(--hot); }}

  table {{ border-collapse:collapse; width:100%; margin-top:20px; font-size:14.5px; }}
  th, td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); }}
  th {{
    font-family:ui-monospace,Menlo,Consolas,monospace; font-size:11.5px;
    letter-spacing:.08em; text-transform:uppercase; color:var(--faint); font-weight:600;
  }}
  td.num {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-variant-numeric:tabular-nums; }}
  td .ok {{ color:var(--accent); font-weight:600; }}

  footer {{ margin-top:40px; color:var(--faint); font-size:13px; }}
  footer .mono {{ color:var(--muted); }}
  a {{ color:var(--accent); text-decoration:none; border-bottom:1px solid transparent; }}
  a:hover {{ border-bottom-color:var(--accent); }}

  main {{ animation:rise .5s ease both; }}
  @keyframes rise {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}
  @media (prefers-reduced-motion:reduce) {{
    main {{ animation:none; }} .figcard {{ transition:none; }}
  }}
</style>

<main class="wrap">
  <p class="eyebrow">Digital twin · ALD in lateral high-aspect-ratio channels</p>
  <h1>A virtual channel-coating model, built from the equations up</h1>
  <p class="thesis">Give it a precursor <b>pulse time</b> and <b>partial pressure</b>; it returns the
    film <b>thickness profile</b> down a narrow silicon channel — the same diffusion-plus-Langmuir
    physics Ylilammi, Ylivaara &amp; Puurunen published in 2018, re-derived from their equations and
    checked against their own measured fits.</p>

  <div class="specstrip">
    <span class="chip io">INPUT&nbsp;&nbsp;t<sub>p</sub> · p<sub>A0</sub></span>
    <span class="chip io">OUTPUT&nbsp;&nbsp;s(x)</span>
    <span class="chip">Al<sub>2</sub>O<sub>3</sub> plateau <b>52.8 nm</b> · paper ~53</span>
    <span class="chip">penetration x<sub>p</sub> <b>134 µm</b> · paper 130–160</span>
    <span class="chip">x<sub>p</sub> ∝ <b>√(p<sub>A0</sub>·t<sub>p</sub>)</b></span>
  </div>

  <hr class="rule">

  <section class="plate">
    <p class="kicker">Profiles · sweeps · scaling</p>
    <h2>What the two knobs do to the coating</h2>
    <p class="cap">The model reproduces the paper's <b>Al<sub>2</sub>O<sub>3</sub></b> and
      <b>TiO<sub>2</sub></b> fits <b>(a)</b>: a flat plateau with a sharp cliff for strongly-saturating
      Al<sub>2</sub>O<sub>3</sub> (<span class="m">K=219</span>), a gradual taper for
      TiO<sub>2</sub> (<span class="m">K=0.25</span>). Longer pulses <b>(b)</b> and higher precursor
      pressure <b>(c)</b> each push the coating deeper. Plot every penetration depth against
      <span class="m">√(p<sub>A0</sub>·t<sub>p</sub>)</span> and they collapse onto one line
      <b>(d)</b> — the diffusion-limited signature.</p>
    <figure class="figcard"><img src="{SAMPLES}" alt="Thickness profiles, pulse-time and pressure sweeps, and penetration-depth scaling collapse"></figure>
  </section>

  <hr class="rule">

  <section class="plate">
    <p class="kicker">Mechanism · one pulse, then the whole run</p>
    <h2>Inside a pulse, and across the cycles</h2>
    <p class="cap">Zooming into the physics: within a single pulse the reactant-pressure front advances
      as <span class="m">x<sub>s</sub>=√(D·t)</span> <b>(a)</b> and surface coverage fills in behind it
      <b>(b)</b> — the paper's Fig 2 and Fig 3. Thickness then accumulates cycle by cycle <b>(c)</b>, and
      a narrower channel starves its own tail: the <b>0.2 µm</b> gap plugs at its mouth before the front
      ever reaches the end <b>(d)</b>, reproducing the paper's Fig 4.</p>
    <figure class="figcard"><img src="{DYNAMICS}" alt="Pressure front and coverage front during a pulse, thickness build-up over cycles, and channel-height sweep"></figure>
  </section>

  <hr class="rule">

  <section class="plate">
    <p class="kicker">Design · reachable depth</p>
    <h2>The process window</h2>
    <p class="cap">Sweep both knobs at once and the reachable penetration depth maps out. Equal-depth
      contours are straight diagonals of slope <span class="m">−1</span> in log–log — lines of constant
      <span class="m">p<sub>A0</sub>·t<sub>p</sub></span> — so doubling the pressure buys the same reach
      as doubling the pulse. Read a target depth off a white contour to size a recipe.</p>
    <figure class="figcard"><img src="{WINDOW}" alt="Process-window heatmap of penetration depth versus pulse time and precursor pressure"></figure>
  </section>

  <hr class="rule">

  <div class="mech">
    <h3>The model in one line</h3>
    <div class="chain mono">
      D<span class="var">eff</span> = Bosanquet(D<span class="var">bulk</span>, D<span class="var">Knudsen</span>)
      <span class="arw">→</span> x<span class="var">s</span> = √(D·t)
      <span class="arw">→</span> dθ/dt = (cQ/q)·p<span class="var">A</span>·(1−θ) − P<span class="var">d</span>·θ
      <span class="arw">→</span> s(x) = Σ θ<span class="var">i</span> · gpc<span class="var">sat</span>
    </div>

    <table>
      <thead><tr><th>process</th><th>mouth / plateau</th><th>penetration x<sub>p</sub></th><th>paper</th></tr></thead>
      <tbody>
        <tr>
          <td>Al<sub>2</sub>O<sub>3</sub> · TMA/H<sub>2</sub>O · 500 cyc</td>
          <td class="num"><span class="ok">52.8 nm</span></td>
          <td class="num"><span class="ok">134 µm</span></td>
          <td class="num">~53 nm · drop 130–160 µm</td>
        </tr>
        <tr>
          <td>TiO<sub>2</sub> · TiCl<sub>4</sub>/H<sub>2</sub>O · 1000 cyc</td>
          <td class="num"><span class="ok">47.1 nm</span></td>
          <td class="num">51 µm</td>
          <td class="num">~47 nm · gradual to ~100 µm</td>
        </tr>
      </tbody>
    </table>
    <p class="cap" style="margin:16px 0 0; font-size:13.5px;">Al<sub>2</sub>O<sub>3</sub> — the paper's
      primary TMA validation — lands essentially exact. TiO<sub>2</sub>'s low-K gradual profile is more
      approximate in absolute penetration but captures the right shape and mouth thickness.</p>
  </div>

  <footer>
    <p class="mono">model&nbsp;ylilammi_twin.py&nbsp;·&nbsp;figures&nbsp;ylilammi_samples.py,&nbsp;ylilammi_viz.py</p>
    <p>Source: M. Ylilammi, O. M. E. Ylivaara, R. L. Puurunen, <i>J. Appl. Phys.</i> <b>123</b>, 205301 (2018),
      doi:10.1063/1.5028178. Every constant is taken from the paper's Table I, Experimental section, and
      Fig 2–7 captions; the desorption probability is derived from the paper's Eq 13, not fitted.</p>
  </footer>
</main>
"""

out = HERE / "ylilammi_gallery.html"
out.write_text(HTML)
print(f"wrote {out}  ({len(HTML)//1024} KB)")
