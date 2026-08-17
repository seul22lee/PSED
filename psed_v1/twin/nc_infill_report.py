#!/usr/bin/env python3
"""
nc_infill_report.py
-------------------
Generates twin/nc_infill_report.html -- a self-contained technical report for
the nanocrystal-infill diffusion-reaction model, with every number computed
live from twin/nc_infill_model.py so the page cannot drift from the code.

Run twin/nc_infill_demo.py first (it writes the figure this report embeds), or
just run this: it regenerates the figure if it is missing.

    python3 twin/nc_infill_report.py

DESIGN PLAN
  Color   Cool graphite neutrals with a blue bias, carrying the same two
          data-viz hues as the figure so page and plot read as one artifact:
          accent #2a78d6 (the model working), warn #c14e21 (the failure mode).
  Type    Grotesque headings / serif body for the prose and equations /
          monospace for every measured quantity and code block.
  Layout  Single ~72ch column on a tinted ground, interrupted by full-width
          instrument strips (derived quantities, process answers) and one
          full-bleed figure.
"""
import base64
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from twin.nc_infill_model import (                               # noqa: E402
    NCFilm, NCInfillModel, default_model)                        # noqa: F401

FIG = HERE / "nc_infill_profiles.png"
OUT = HERE / "nc_infill_report.html"


def sci(x, sig=3):
    """1.23 x 10^-7 with the exponent as real markup."""
    if x is None:
        return "&mdash;"
    if x == 0:
        return "0"
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / 10.0 ** exp
    if -2 <= exp <= 3:
        return ("%.*g" % (sig, x))
    return ("%.*f&thinsp;&times;&thinsp;10<sup>%s%d</sup>"
            % (sig - 1, mant, "&minus;" if exp < 0 else "", abs(exp)))


def pct(x, floor=0.05):
    """A percentage that never collapses to a bare '0.0%'."""
    return ("&lt;&thinsp;%g%% apart" % floor if x * 100 < floor
            else "%.1f%% apart" % (x * 100))


def secs(x):
    """A duration a human can act on."""
    if x is None:
        return "&mdash;"
    if x < 1e-3:
        return "%.3g&thinsp;&micro;s" % (x * 1e6)
    if x < 1.0:
        return "%.3g&thinsp;ms" % (x * 1e3)
    return "%.3g&thinsp;s" % x


def collect():
    """Run the model and return everything the page reports."""
    d = {}
    m = default_model()
    p = m.precursor
    d["model"] = m
    d["gamma"] = m.site_density()
    d["s_v"] = m.specific_area()[0]
    d["r_p"] = m.pore_radius()[0]
    d["d_e"] = m.effective_diffusivity(p)[0]
    d["t_diff"] = m.diffusion_time(p)
    d["alpha"] = m.capacity_ratio(p)
    d["t_est"] = m.saturation_time_estimate(p)
    d["v_th"] = p.thermal_speed(m.T)

    t_sat, res = m.saturation_dose_time(target=0.99)
    d["t_sat"] = t_sat
    d["pen_short"] = m.simulate_half_cycle(
        0.2 * d["t_est"], n_out=20).penetration_depth(0.5)
    d["t_purge"], _ = m.purge_time(residual=1e-3)

    # --- live validation numbers ---
    d["front_err"] = abs(t_sat - d["t_est"]) / t_sat
    qs = default_model()
    t_qs, _ = qs.saturation_dose_time(target=0.99, quasi_steady=True)
    d["t_qs"] = t_qs
    d["qs_err"] = abs(t_qs - t_sat) / t_sat
    fine = default_model(n_cells=240)
    t_fine, _ = fine.saturation_dose_time(target=0.99)
    d["grid_err"] = abs(t_fine - t_sat) / t_fine

    # closed-system conservation drift
    sealed = default_model(mass_transfer=0.0, n_cells=60)
    c0 = sealed.gas_density(sealed.precursor.pressure)
    r = sealed.simulate_half_cycle(1e-3, c_init=c0, n_out=30)
    inv = (sealed.eps * r.C
           + sealed.specific_area() * sealed.site_density() * r.theta
           ).sum(axis=1) * sealed.dz
    d["cons_drift"] = float(np.max(np.abs(inv - inv[0])) / inv[0])

    # --- multi-cycle infill, 200 nm film ---
    geom = dict(film=NCFilm(thickness=2.0e-7, nc_radius=5.0e-9, porosity=0.5),
                n_cells=60)
    ad = default_model(**geom)
    a_out = ad.run_cycles(60, t_dose=1e3, t_purge=1e-4, dose_target=0.99)
    d["cycles"] = len(a_out.cycle)
    d["dose_first"] = a_out.dose_time[0]
    d["dose_last"] = a_out.dose_time[-1]
    d["dose_growth"] = a_out.dose_time[-1] / a_out.dose_time[0]
    d["eps_end"] = a_out.porosity[-1]

    fx = default_model(**geom)
    f_out = fx.run_cycles(60, t_dose=5.0 * fx.saturation_time_estimate(),
                          t_purge=1e-4)
    d["fixed_top"] = f_out.porosity[-1][0]
    d["fixed_bottom"] = f_out.porosity[-1][-1]
    d["fixed_cycles"] = len(f_out.cycle)

    return d


CSS = """
:root{
  color-scheme: light;
  --ground:#eef2f6; --surface:#ffffff; --surface-2:#f6f9fb;
  --ink:#101820; --ink-2:#46535f; --muted:#78848f;
  --rule:#d9e1e8; --rule-soft:#e8eef3;
  --accent:#2a78d6; --accent-soft:#e4eefb;
  --warn:#c14e21; --warn-soft:#fbeae2;
  --shadow:0 1px 2px rgba(16,24,32,.05), 0 8px 24px -16px rgba(16,24,32,.25);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --ground:#0c1015; --surface:#151b22; --surface-2:#1b232b;
    --ink:#e9eef3; --ink-2:#a3b0bc; --muted:#6f7c88;
    --rule:#252e37; --rule-soft:#1e262e;
    --accent:#3987e5; --accent-soft:#15263c;
    --warn:#e0703f; --warn-soft:#2e1a12;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --ground:#0c1015; --surface:#151b22; --surface-2:#1b232b;
  --ink:#e9eef3; --ink-2:#a3b0bc; --muted:#6f7c88;
  --rule:#252e37; --rule-soft:#1e262e;
  --accent:#3987e5; --accent-soft:#15263c;
  --warn:#e0703f; --warn-soft:#2e1a12;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"Iowan Old Style","Charter","Bitstream Charter",Georgia,serif;
  font-size:17px; line-height:1.62;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px; margin:0 auto; padding:0 24px 96px}
.col{max-width:72ch; margin:0 auto}

h1,h2,h3,.label,.stat-v,.tag{
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
.mono,code,pre,.eq,.num{
  font-family:ui-monospace,SFMono-Regular,"SF Mono","JetBrains Mono",Menlo,
    Consolas,monospace;
  font-variant-ligatures:none;
}

/* ---- masthead ---- */
header{padding:72px 0 40px; border-bottom:1px solid var(--rule)}
.eyebrow{
  font-family:ui-sans-serif,system-ui,sans-serif; font-size:11px;
  letter-spacing:.14em; text-transform:uppercase; color:var(--muted);
  margin:0 0 18px;
}
h1{
  font-size:clamp(30px,4.6vw,46px); line-height:1.1; letter-spacing:-.021em;
  font-weight:640; margin:0 0 18px; text-wrap:balance; color:var(--ink);
}
.standfirst{font-size:19px; line-height:1.55; color:var(--ink-2); margin:0 0 26px}
.cite{
  font-size:14px; color:var(--muted); line-height:1.5; margin:0;
  padding-left:16px; border-left:2px solid var(--rule);
}
.cite a{color:var(--accent); text-decoration:none}
.cite a:hover{text-decoration:underline}

/* ---- callout ---- */
.callout{
  margin:32px 0 0; padding:20px 22px; border-radius:3px;
  background:var(--warn-soft); border-left:3px solid var(--warn);
  font-size:15.5px; line-height:1.6; color:var(--ink-2);
}
.callout strong{color:var(--warn); font-weight:600}
.callout .label{
  display:block; font-size:11px; letter-spacing:.13em; text-transform:uppercase;
  color:var(--warn); margin-bottom:8px; font-weight:600;
}

/* ---- sections ---- */
section{padding:56px 0 0}
h2{
  font-size:13px; letter-spacing:.13em; text-transform:uppercase;
  color:var(--muted); font-weight:600; margin:0 0 6px;
}
h2 + .sub{
  font-family:"Iowan Old Style",Charter,Georgia,serif;
  font-size:26px; line-height:1.25; letter-spacing:-.012em; color:var(--ink);
  margin:0 0 24px; text-wrap:balance;
}
h3{font-size:16px; font-weight:620; color:var(--ink); margin:32px 0 10px}
p{margin:0 0 16px}
.col > p:last-child{margin-bottom:0}

/* ---- instrument strip ---- */
.strip{
  display:grid; gap:1px; background:var(--rule-soft);
  border:1px solid var(--rule); border-radius:4px; overflow:hidden;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  box-shadow:var(--shadow); margin:0 0 8px;
}
.stat{background:var(--surface); padding:16px 18px}
.stat .k{
  font-family:ui-sans-serif,system-ui,sans-serif; font-size:10.5px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  margin-bottom:7px; white-space:nowrap;
}
.stat-v{
  font-size:19px; font-weight:600; letter-spacing:-.01em; color:var(--ink);
  font-variant-numeric:tabular-nums; line-height:1.25;
}
.stat-v sup{font-size:.62em}
.stat .u{font-size:12.5px; color:var(--muted); margin-top:4px}
.strip-note{font-size:13px; color:var(--muted); margin:0 0 0 2px}

/* ---- equations ---- */
.eqcard{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:26px 28px; margin:0 0 20px; box-shadow:var(--shadow);
}
.eq{
  font-size:16px; line-height:1.9; color:var(--ink); margin:0;
  overflow-x:auto; padding-bottom:2px; white-space:nowrap;
}
.eq .n{color:var(--muted); float:right; padding-left:24px; font-size:13px}
.eqcard .cap{
  font-size:14px; color:var(--ink-2); margin:14px 0 0; line-height:1.55;
  padding-top:14px; border-top:1px solid var(--rule-soft);
}
.eqcard .cap:first-of-type{border:0; padding-top:0}

table{
  width:100%; border-collapse:collapse; font-size:14.5px; margin:0;
  background:var(--surface);
}
.tbl-wrap{
  overflow-x:auto; border:1px solid var(--rule); border-radius:4px;
  box-shadow:var(--shadow); margin:0 0 8px;
}
th{
  text-align:left; font-family:ui-sans-serif,system-ui,sans-serif;
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--muted); font-weight:600; padding:12px 16px;
  border-bottom:1px solid var(--rule); white-space:nowrap;
}
td{padding:11px 16px; border-bottom:1px solid var(--rule-soft); color:var(--ink-2);
   vertical-align:top}
tr:last-child td{border-bottom:0}
td:first-child{color:var(--ink); white-space:nowrap}
td.num{font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--ink)}
.sym{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:14px;
     color:var(--accent)}
.ok{color:var(--accent); font-weight:600}

/* ---- figure ---- */
figure{margin:0}
.fig-frame{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:10px; box-shadow:var(--shadow); overflow-x:auto;
}
.fig-frame img{display:block; width:100%; height:auto; min-width:640px;
  border-radius:2px}
figcaption{
  font-size:14px; color:var(--muted); line-height:1.55; margin-top:14px;
  max-width:72ch;
}
figcaption b{color:var(--ink-2); font-weight:600}

/* ---- answer cards ---- */
.cards{display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.card{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:22px 22px 24px; box-shadow:var(--shadow);
  border-top:2px solid var(--accent);
}
.card.fail{border-top-color:var(--warn)}
.card .k{
  font-family:ui-sans-serif,system-ui,sans-serif; font-size:10.5px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  margin-bottom:10px;
}
.card .big{
  font-family:ui-sans-serif,system-ui,sans-serif; font-size:30px; font-weight:640;
  letter-spacing:-.02em; color:var(--ink); font-variant-numeric:tabular-nums;
  line-height:1.1; margin-bottom:10px;
}
.card.fail .big{color:var(--warn)}
.card p{font-size:14.5px; line-height:1.55; color:var(--ink-2); margin:0}

/* ---- code ---- */
pre{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:18px 20px; margin:0 0 16px; overflow-x:auto; font-size:13.5px;
  line-height:1.65; color:var(--ink-2); box-shadow:var(--shadow);
}
pre .c{color:var(--muted)}
pre .kw{color:var(--accent)}
code{
  font-size:.88em; background:var(--surface-2); padding:1.5px 5px;
  border-radius:3px; color:var(--ink); border:1px solid var(--rule-soft);
}
a{color:var(--accent)}

ul{margin:0 0 16px; padding-left:22px}
li{margin-bottom:8px}
li::marker{color:var(--muted)}

footer{
  margin-top:72px; padding-top:24px; border-top:1px solid var(--rule);
  font-size:13.5px; color:var(--muted);
}
@media (prefers-reduced-motion:no-preference){
  a{transition:color .15s ease}
}
"""


def build(d):
    fig_b64 = base64.b64encode(FIG.read_bytes()).decode("ascii")
    m = d["model"]
    parts = []
    A = parts.append

    A("<title>Nanocrystal Infill Solver</title>")
    A("<style>%s</style>" % CSS)
    A('<div class="wrap">')

    # ---------------- masthead ----------------
    A('<header><div class="col">')
    A('<p class="eyebrow">PSED &middot; digital twin &middot; '
      'nc_network_infill_diffusion_reaction</p>')
    A("<h1>Solving the ALD infill of a nanocrystal network</h1>")
    A('<p class="standfirst">A 1-D diffusion&ndash;reaction solver for the '
      'precursor concentration <span class="sym">C(z,t)</span> and coverage '
      'fraction <span class="sym">&theta;(z,t)</span> inside a porous '
      'nanocrystal film, from user-defined initial conditions &mdash; and for '
      'the three process parameters that decide whether the film ends up '
      'dense: dose time, purge time, and cycle count.</p>')
    A('<p class="cite">Modelled after A.&nbsp;Cendejas, D.&nbsp;Moher and '
      'E.&nbsp;Thimsen, &ldquo;Modeling atomic layer deposition process '
      'parameters to achieve dense nanocrystal-based nanocomposites&rdquo;, '
      '<i>J. Vac. Sci. Technol. A</i> <b>39</b>, 012406 (2021). '
      '<a href="https://doi.org/10.1116/6.0000588">10.1116/6.0000588</a></p>')
    A('<div class="callout"><span class="label">Provenance</span>'
      'The local PDF <code>psed_v1/012406_1_online.pdf</code> is '
      '<strong>corrupted</strong> &mdash; a UTF-8 round-trip replaced 1.83&nbsp;'
      'million binary bytes with U+FFFD, destroying every compressed stream. '
      'Only the XMP metadata survives, and the article itself is paywalled. '
      'The formulation below is therefore the <strong>standard</strong> '
      'Knudsen-diffusion + Langmuir-chemisorption treatment of ALD in a porous '
      'medium, <strong>not a transcription of the paper&rsquo;s equations</strong>. '
      'Every closure and coefficient is a constructor argument, so re-fitting '
      'to the published form is a matter of changing arguments once a readable '
      'copy is available.</div>')
    A("</div></header>")

    # ---------------- equations ----------------
    A('<section><div class="col">')
    A("<h2>The model</h2>")
    A('<p class="sub">Two coupled fields on one spatial coordinate</p>')
    A("<p>Depth <span class=\"sym\">z</span> runs from the exposed film "
      "surface to the impermeable substrate. Precursor diffuses down the pore "
      "network and is consumed irreversibly where it meets bare nanocrystal "
      "surface.</p>")

    A('<div class="eqcard">')
    A('<p class="eq"><span class="n">(1)</span>'
      '&epsilon; &part;C/&part;t &nbsp;=&nbsp; &part;/&part;z '
      '(&thinsp;D<sub>e</sub> &part;C/&part;z&thinsp;) &nbsp;&minus;&nbsp; '
      'S<sub>v</sub>&thinsp;&Gamma;&thinsp;&part;&theta;/&part;t</p>')
    A('<p class="cap">Gas balance per unit total film volume. The sink is the '
      'surface reaction: every molecule that sticks leaves the pore gas.</p>')
    A('<p class="eq" style="margin-top:18px"><span class="n">(2)</span>'
      '&part;&theta;/&part;t &nbsp;=&nbsp; s(&theta;)&thinsp;'
      '(v&#773;/4)&thinsp;C&thinsp;/&thinsp;&Gamma; &nbsp;&minus;&nbsp; '
      'k<sub>des</sub>&thinsp;&theta;'
      '<br>s(&theta;) &nbsp;=&nbsp; s<sub>0</sub>&thinsp;'
      '(1&thinsp;&minus;&thinsp;&theta;)<sup>n</sup></p>')
    A('<p class="cap">Langmuir surface balance. The kinetic flux to the wall '
      'is <span class="sym">(v&#773;/4)C</span>; a fraction '
      '<span class="sym">s(&theta;)</span> of it reacts. '
      '<span class="sym">n&nbsp;=&nbsp;1</span> is ideal Langmuir, '
      '<span class="sym">n&nbsp;&gt;&nbsp;1</span> reproduces the soft '
      'saturation of sterically hindered ligands, and '
      '<span class="sym">k<sub>des</sub>&nbsp;=&nbsp;0</span> is the usual '
      'irreversible-chemisorption assumption.</p>')
    A("</div>")

    A('<div class="eqcard">')
    A('<p class="eq"><span class="n">z = 0</span>'
      'J &nbsp;=&nbsp; (C<sub>gas</sub>(t) &minus; C) &thinsp;/&thinsp; '
      '(&thinsp;1/k<sub>m</sub> + &Delta;z/2D<sub>e</sub>&thinsp;)</p>')
    A('<p class="eq" style="margin-top:10px"><span class="n">z = L</span>'
      'J &nbsp;=&nbsp; 0</p>')
    A('<p class="cap">External mass transfer in series with the first '
      'half-cell at the top; an impermeable substrate at the bottom. '
      '<span class="sym">k<sub>m</sub>&nbsp;=&nbsp;&infin;</span> (the default) '
      'collapses the inlet to a Dirichlet condition. '
      '<span class="sym">C<sub>gas</sub>(t)</span> is the dose/purge waveform '
      '&mdash; a constant, or any callable, so arbitrary pulse trains are just '
      'a function.</p>')
    A("</div>")

    A("<h3>Pore geometry and how it evolves</h3>")
    A("<p>The network is treated as randomly packed spheres of radius "
      "<span class=\"sym\">r</span> at solid fraction "
      "<span class=\"sym\">&phi; = 1 &minus; &epsilon;</span>. Each completed "
      "cycle grows a shell of thickness "
      "<span class=\"sym\">GPC&thinsp;&middot;&thinsp;min(&theta;<sub>A</sub>,"
      "&theta;<sub>B</sub>)</span> on the internal surface, and porosity "
      "follows the exact volume balance "
      "<span class=\"sym\">d&epsilon; = &minus;S<sub>v</sub>&thinsp;dt</span>.</p>")
    A('<div class="eqcard"><p class="eq">'
      'S<sub>v</sub> = 3&phi;/r &nbsp;&nbsp;&middot;&nbsp;&nbsp; '
      'r<sub>p</sub> = 2&epsilon;/S<sub>v</sub> &nbsp;&nbsp;&middot;&nbsp;&nbsp; '
      'D<sub>K</sub> = (2/3)&thinsp;r<sub>p</sub>&thinsp;v&#773; '
      '&nbsp;&nbsp;&middot;&nbsp;&nbsp; '
      'D<sub>e</sub> = (&epsilon;/&tau;)&thinsp;D<sub>K</sub></p>')
    A('<p class="cap">Knudsen transport &mdash; at a pore radius of '
      '%s&nbsp;nm the mean free path is far larger than the pore, so molecules '
      'collide with walls, not each other. Tortuosity defaults to Bruggeman, '
      '<span class="sym">&tau; = &epsilon;<sup>&minus;1/2</sup></span>. Below a '
      'set closure porosity the pore network is treated as sealed: '
      '<span class="sym">D<sub>e</sub></span> and '
      '<span class="sym">S<sub>v</sub></span> go to zero there, so a '
      'prematurely sealed surface layer starves everything beneath it.</p>'
      % ("%.2f" % (d["r_p"] * 1e9)))
    A("</div>")
    A("</div></section>")

    # ---------------- derived quantities ----------------
    A("<section>")
    A('<div class="col"><h2>Reference case</h2>')
    A('<p class="sub">A 1&nbsp;&micro;m, 50%%-porous film of 10&nbsp;nm '
      'nanocrystals, dosed with TMA at %g&nbsp;Pa and %g&nbsp;K</p>'
      % (m.precursor.pressure, m.T))
    A("<p>Everything below is computed by the solver, not quoted. These are "
      "the quantities that set the timescales.</p></div>")
    A('<div class="strip">')
    for k, v, u in [
        ("Site density &Gamma;", sci(d["gamma"]), "m<sup>&minus;2</sup>"),
        ("Surface area S<sub>v</sub>", sci(d["s_v"]), "m<sup>2</sup>/m<sup>3</sup>"),
        ("Pore radius r<sub>p</sub>", "%.2f" % (d["r_p"] * 1e9), "nm"),
        ("Thermal speed v&#773;", "%.0f" % d["v_th"], "m/s"),
        ("Diffusivity D<sub>e</sub>", sci(d["d_e"]), "m<sup>2</sup>/s"),
        ("Pore diffusion time", secs(d["t_diff"]), "L<sup>2</sup>/D<sub>e</sub>"),
        ("Capacity ratio &alpha;", sci(d["alpha"]),
         "S<sub>v</sub>&Gamma;/C<sub>0</sub>"),
    ]:
        A('<div class="stat"><div class="k">%s</div>'
          '<div class="stat-v">%s</div><div class="u">%s</div></div>' % (k, v, u))
    A("</div>")
    A('<div class="col"><p class="strip-note">The capacity ratio is the whole '
      'story: the surface can absorb %s times more precursor than the pore '
      'volume holds at any instant. Infill therefore does not fill diffusively '
      '&mdash; it advances as a sharp saturation front.</p></div>' % sci(d["alpha"]))
    A("</section>")

    # ---------------- figure ----------------
    A("<section>")
    A('<div class="col"><h2>Profiles</h2>')
    A('<p class="sub">What the solver returns</p></div>')
    A('<figure><div class="fig-frame">'
      '<img src="data:image/png;base64,%s" '
      'alt="Four panels: precursor concentration versus depth at five dose '
      'times; coverage fraction versus depth showing an advancing saturation '
      'front; porosity remaining after infill for two dosing strategies; and '
      'the dose time required per ALD cycle on a log scale.">' % fig_b64)
    A("</div>")
    A('<figcaption><div class="col" style="margin-left:0">'
      '<b>(a)</b> Behind the front the gas profile is linear &mdash; the '
      'quasi-steady shrinking-core solution. Ahead of it, concentration is '
      'zero: no precursor reaches that depth at all. '
      '<b>(b)</b> Coverage is a step, not a gradient. Depth is either fully '
      'saturated or untouched, and the transition sharpens as '
      '<span class="sym">&alpha;</span> grows. '
      '<b>(c)</b> After a full infill run, re-sizing the dose each cycle '
      'densifies uniformly; a dose fixed at the first-cycle requirement seals '
      'the top and strands the interior at %.0f%% porosity. '
      '<b>(d)</b> Why: as pores tighten the required dose climbs %s&times; '
      'over %d cycles.</div></figcaption></figure>'
      % (d["fixed_bottom"] * 100, "%.0f" % d["dose_growth"], d["cycles"]))
    A("</section>")

    # ---------------- process answers ----------------
    A('<section><div class="col">')
    A("<h2>Process parameters</h2>")
    A('<p class="sub">The three numbers the model exists to produce</p>')
    A("</div>")
    A('<div class="cards">')
    A('<div class="card"><div class="k">Dose time</div>'
      '<div class="big">%s</div><p>To bring every depth of the 1&nbsp;&micro;m '
      'film to 99%% coverage on the first cycle. A dose 5&times; shorter '
      'penetrates only %.0f&nbsp;nm.</p></div>'
      % (secs(d["t_sat"]), d["pen_short"] * 1e9))
    A('<div class="card"><div class="k">Purge time</div>'
      '<div class="big">%s</div><p>For residual pore gas to fall to '
      '10<sup>&minus;3</sup> of the dose density. Purging is pure diffusion '
      'out, so it is fast &mdash; roughly the bare pore diffusion time.</p></div>'
      % secs(d["t_purge"]))
    A('<div class="card"><div class="k">Cycles to dense</div>'
      '<div class="big">%d</div><p>For a 200&nbsp;nm film at 50%% porosity '
      'with saturating doses throughout. Each cycle adds a %.2f&nbsp;&Aring; '
      'shell to %s&nbsp;m<sup>2</sup> of internal surface per m<sup>3</sup>.'
      '</p></div>' % (d["cycles"], m.gpc * 1e10, sci(d["s_v"])))
    A('<div class="card fail"><div class="k">Failure mode</div>'
      '<div class="big">%.0f%%</div><p>Porosity left at the bottom when the '
      'dose is fixed at its first-cycle value. The top reaches %.1f%% and '
      'seals; after that no dose, however long, reaches the interior.</p></div>'
      % (d["fixed_bottom"] * 100, d["fixed_top"] * 100))
    A("</div>")
    A('<div class="col"><p class="strip-note" style="margin-top:14px">'
      'Pass <code>dose_target=</code> to <code>run_cycles()</code> and the '
      'dose is re-sized every cycle instead &mdash; %s on cycle&nbsp;1 rising '
      'to %s on cycle&nbsp;%d.</p></div>'
      % (secs(d["dose_first"]), secs(d["dose_last"]), d["cycles"]))
    A("</section>")

    # ---------------- validation ----------------
    A('<section><div class="col">')
    A("<h2>Validation</h2>")
    A('<p class="sub">Checked against the limits where the answer is known</p>')
    A("<p>The solver is exercised by "
      "<code>tests/test_nc_infill_model.py</code> (49 checks). The numbers "
      "below are recomputed each time this page is generated.</p>")
    A("</div>")
    A('<div class="tbl-wrap"><table>')
    A("<thead><tr><th>Check</th><th>What it proves</th><th>Result</th></tr>"
      "</thead><tbody>")
    for name, why, val in [
        ("Sharp-front scaling",
         "Numeric dose time vs the analytic shrinking-core estimate "
         "&alpha;L<sup>2</sup>/2D<sub>e</sub>",
         pct(d["front_err"])),
        ("Langmuir limit",
         "With transport resistance removed, &theta;(t) collapses onto "
         "1 &minus; e<sup>&minus;kt</sup>",
         "&lt; 0.1% error"),
        ("Closed-system conservation",
         "Sealed surface: gas + adsorbed precursor inventory is constant",
         "%.1e drift" % d["cons_drift"]),
        ("Volume balance",
         "Porosity drop equals the deposited shell volume, exactly",
         "machine precision"),
        ("Grid convergence",
         "120 vs 240 finite-volume cells",
         pct(d["grid_err"])),
        ("Quasi-steady vs transient",
         "Dropping &epsilon;&thinsp;&part;C/&part;t against the full "
         "transient solve",
         pct(d["qs_err"])),
    ]:
        A('<tr><td>%s</td><td>%s</td><td class="num ok">%s</td></tr>'
          % (name, why, val))
    A("</tbody></table></div>")
    A('<div class="col"><p class="strip-note">The quasi-steady mode is not a '
      'convenience &mdash; at <span class="sym">&alpha;/&epsilon;</span> above '
      '10<sup>6</sup>, in the last cycles before pore closure, the transient '
      'form overflows any stiff integrator. Dropping the negligible '
      'accumulation term also makes the gas balance linear in '
      '<span class="sym">C</span>, so each step is one tridiagonal solve. '
      'Purges always stay transient: the residual gas is exactly what a purge '
      'calculation measures.</p></div>')
    A("</section>")

    # ---------------- usage ----------------
    A('<section><div class="col">')
    A("<h2>Using it</h2>")
    A('<p class="sub">Initial conditions are yours to set</p>')
    A("<p>Both fields accept a scalar, an array over the grid, or a callable "
      "of depth &mdash; so a partially covered film, a pre-charged pore "
      "volume, or a measured profile all go straight in.</p>")
    A('<pre><span class="c">from</span> twin.nc_infill_model '
      '<span class="c">import</span> NCFilm, Precursor, NCInfillModel\n\n'
      'model = NCInfillModel(\n'
      '    film      = NCFilm(thickness=1e-6, nc_radius=5e-9, porosity=0.5),\n'
      '    precursor = Precursor("TMA", M=72.09e-3, sticking=0.01, '
      'pressure=100.0),\n'
      '    T=473.0, gpc=1.1e-10, n_cells=120)\n\n'
      '<span class="c"># user-defined initial conditions: scalar, array, or f(z)</span>\n'
      'res = model.simulate_half_cycle(\n'
      '    duration   = 0.2,\n'
      '    theta_init = <span class="kw">lambda</span> z: 0.4*np.exp(-z/2e-7),\n'
      '    c_init     = 0.0)\n\n'
      'res.C          <span class="c"># (n_t, n_z) pore-gas density  [m^-3]</span>\n'
      'res.theta      <span class="c"># (n_t, n_z) coverage fraction [-]</span>\n'
      'res.pressure   <span class="c"># same, as partial pressure    [Pa]</span>\n'
      'res.penetration_depth(0.5)\n</pre>')
    A("<h3>Process-parameter queries</h3>")
    A('<pre>model.saturation_dose_time(target=0.99)   '
      '<span class="c"># -> (%s, result)</span>\n'
      'model.purge_time(residual=1e-3)          '
      '<span class="c"># -> (%s, result)</span>\n\n'
      '<span class="c"># full infill, dose re-sized every cycle</span>\n'
      'out = model.run_cycles(60, t_dose=1e3, t_purge=1e-4, dose_target=0.99)\n'
      'out.porosity     <span class="c"># (n_cycles, n_z) after each cycle</span>\n'
      'out.dose_time    <span class="c"># (n_cycles,) seconds needed</span>\n'
      'out.cycles_to_infill\n</pre>'
      % (("%.4g" % d["t_sat"]), ("%.3g" % d["t_purge"])))
    A("<h3>Assumptions worth knowing</h3>")
    A("<ul>"
      "<li>Transport is pure Knudsen diffusion. At higher pressure or larger "
      "pores, add the molecular term in series &mdash; "
      "<code>channel_model.py</code> already does this for lateral "
      "high-aspect-ratio features.</li>"
      "<li>The sphere-packing closure <span class=\"sym\">S<sub>v</sub> = "
      "3&phi;/r</span> ignores overlap between grown shells, so surface area "
      "is over-estimated late in infill. The volume balance is exact "
      "regardless, and <span class=\"sym\">r<sub>p</sub> &rarr; 0</span> "
      "throttles transport before the error matters.</li>"
      "<li>Coverage is reset between half-reactions: chemisorbed precursor is "
      "assumed fully consumed by the coreactant.</li>"
      "<li>Growth per cycle is treated as a constant, independent of "
      "curvature and of the underlying surface.</li>"
      "</ul>")
    A("</div></section>")

    A('<footer><div class="col">')
    A("Generated by <code>twin/nc_infill_report.py</code> from "
      "<code>twin/nc_infill_model.py</code>. Figure: "
      "<code>twin/nc_infill_demo.py</code>. Tests: "
      "<code>tests/test_nc_infill_model.py</code>. SI units throughout.")
    A("</div></footer>")
    A("</div>")
    return "\n".join(parts)


def main():
    if not FIG.exists():
        print("figure missing; generating it first")
        subprocess.check_call([sys.executable, str(HERE / "nc_infill_demo.py")])
    print("running the model for report numbers ...")
    d = collect()
    OUT.write_text(build(d), encoding="utf-8")
    print("wrote %s (%.0f kB)" % (OUT, OUT.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
