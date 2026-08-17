#!/usr/bin/env python3
"""
model_comparison_report.py
--------------------------
Generates twin/model_comparison_report.html -- the side-by-side comparison of

  [A] A. Yanguas-Gil & J. W. Elam, "Simple model for atomic layer deposition
      precursor reaction and transport in a viscous-flow tubular reactor",
      J. Vac. Sci. Technol. A 30, 01A159 (2012).  doi:10.1116/1.3670396
      -> psed_v1/01a159_1_online.pdf  (intact, equations transcribed)

  [B] A. Cendejas, D. Moher & E. Thimsen, "Modeling atomic layer deposition
      process parameters to achieve dense nanocrystal-based nanocomposites",
      J. Vac. Sci. Technol. A 39, 012406 (2021).  doi:10.1116/6.0000588
      -> psed_v1/012406_1_online.pdf  (corrupt; model reconstructed)

and the numerical demonstration that they are the same equation in different
regimes.  Every number is computed live, and the page reuses the design system
of nc_infill_report.py so the two artifacts read as one set.

    python3 twin/model_comparison_report.py
"""
import base64
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from twin.nc_infill_model import default_model                   # noqa: E402
from twin.nc_infill_report import CSS, sci, secs                 # noqa: E402
from twin.nc_infill_vs_yanguas import groups                     # noqa: E402
import twin.yanguas_gil_reactor as yg                            # noqa: E402

FIG = HERE / "nc_infill_vs_yanguas.png"
OUT = HERE / "model_comparison_report.html"

EXTRA_CSS = """
.papers{display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
        margin:0 0 8px}
.paper{background:var(--surface); border:1px solid var(--rule); border-radius:4px;
       padding:22px; box-shadow:var(--shadow); border-top:2px solid var(--accent)}
.paper.broken{border-top-color:var(--warn)}
.paper .tagline{font-family:ui-sans-serif,system-ui,sans-serif; font-size:10.5px;
   letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:10px}
.paper.broken .tagline{color:var(--warn)}
.paper h4{font-family:ui-sans-serif,system-ui,sans-serif; font-size:15.5px;
   font-weight:620; color:var(--ink); margin:0 0 8px; line-height:1.32}
.paper .meta{font-size:13.5px; color:var(--muted); margin:0 0 12px; line-height:1.45}
.paper p{font-size:14.5px; color:var(--ink-2); margin:0; line-height:1.55}
.sbs{display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
     margin:0 0 20px}
.sbs .eqcard{margin:0}
.sbs .who{font-family:ui-sans-serif,system-ui,sans-serif; font-size:10.5px;
   letter-spacing:.1em; text-transform:uppercase; color:var(--accent);
   margin:0 0 14px; font-weight:600}
.verdict{background:var(--accent-soft); border:1px solid var(--rule);
   border-left:3px solid var(--accent); border-radius:3px; padding:22px 24px;
   margin:0 0 8px}
.verdict .label{display:block; font-family:ui-sans-serif,system-ui,sans-serif;
   font-size:11px; letter-spacing:.13em; text-transform:uppercase;
   color:var(--accent); font-weight:600; margin-bottom:10px}
.verdict p{margin:0 0 12px; font-size:16px; color:var(--ink-2)}
.verdict p:last-child{margin:0}
.verdict b{color:var(--ink); font-weight:620}
td.same{color:var(--accent); font-weight:600}
td.diff{color:var(--warn); font-weight:600}
"""


def collect():
    d = {}
    m = default_model()
    d["model"] = m
    g = groups(m)
    d.update(g)
    d["alpha"] = m.capacity_ratio()
    d["paper"] = yg.PAPER_TMA
    d["t_est"] = m.saturation_time_estimate()

    # numerical equivalence at matched groups
    t_phys = 0.35 * d["t_est"]
    d["t_phys"] = t_phys
    d["tau"] = t_phys * g["tau_per_second"]
    th_mine = m.simulate_half_cycle(t_phys, n_out=3).theta_final
    xi_mine = m.z / m.film.thickness
    d["err"] = {}
    for key, eps in (("published", 1.0), ("matched", m.film.porosity)):
        r = yg.solve(Pe=0.0, Da=g["Da"], gamma=g["gamma"], tau_end=d["tau"],
                     xi_max=1.0, n_xi=1200, epsilon=eps, outlet="noflux")
        d["err"][key] = float(np.max(np.abs(
            th_mine - np.interp(xi_mine, r.xi, r.growth_profile()))))
        d["front_" + key] = float(np.interp(0.5, r.growth_profile()[::-1],
                                            r.xi[::-1]))
    d["front_mine"] = float(np.interp(0.5, th_mine[::-1], xi_mine[::-1]))

    # reactor scale, from the paper's own Eq. (14)
    d["u_reactor"] = yg.axial_velocity(300.0, 1.0, 473.0, 0.025)
    d["D_reactor"] = d["u_reactor"] * 0.45 / yg.PAPER_TMA["Pe"]
    d["D_film"] = m.effective_diffusivity(m.precursor)[0]
    d["S_v_film"] = m.specific_area()[0]
    d["S_v_reactor"] = 2.0 / 0.025

    # Time to drive the front the full length, t = L^2 / (2 gamma D), for each
    # system.  This is where the length scale pays back the gamma difference.
    d["t_sat_film"] = m.film.thickness ** 2 / (2 * d["gamma"] * d["D_film"])
    d["t_sat_reactor"] = 0.45 ** 2 / (2 * yg.PAPER_TMA["gamma"] * d["D_reactor"])
    return d


def build(d):
    fig_b64 = base64.b64encode(FIG.read_bytes()).decode("ascii")
    p = d["paper"]
    out = []
    A = out.append

    A("<title>Two Papers, One Equation</title>")
    A("<style>%s%s</style>" % (CSS, EXTRA_CSS))
    A('<div class="wrap">')

    # ---------------- masthead ----------------
    A('<header><div class="col">')
    A('<p class="eyebrow">PSED &middot; digital twin &middot; model comparison</p>')
    A("<h1>A reactor tube and a nanocrystal film solve the same equation</h1>")
    A('<p class="standfirst">Two ALD transport models, twelve years and six '
      'orders of magnitude of length scale apart. Written side by side they '
      'turn out to be the same advection&ndash;diffusion&ndash;reaction system '
      '&mdash; and the &ldquo;excess number&rdquo; of the 2012 reactor paper '
      'is exactly the reciprocal of the capacity ratio that governs infill. '
      'Here is the algebra, and the numerical check.</p>')
    A("</div></header>")

    # ---------------- the two papers ----------------
    A("<section>")
    A('<div class="col"><h2>The two models</h2>')
    A('<p class="sub">One paper is readable; the other had to be reconstructed'
      '</p></div>')
    A('<div class="papers">')
    A('<div class="paper"><div class="tagline">A &middot; transcribed from the PDF</div>'
      '<h4>Simple model for ALD precursor reaction and transport in a '
      'viscous-flow tubular reactor</h4>'
      '<p class="meta">Yanguas-Gil &amp; Elam &middot; <i>JVST A</i> <b>30</b>, '
      '01A159 (2012)<br>'
      '<a href="https://doi.org/10.1116/1.3670396">10.1116/1.3670396</a></p>'
      '<p>A 45&nbsp;cm heated tube with nitrogen flowing through it at '
      '%.1f&nbsp;m/s. The question is film thickness <i>uniformity along the '
      'reactor</i>. Transport is molecular diffusion plus bulk flow, and the '
      'wall area per unit volume is small.</p></div>' % d["u_reactor"])
    A('<div class="paper broken"><div class="tagline">B &middot; PDF corrupt, model '
      'reconstructed</div>'
      '<h4>Modeling ALD process parameters to achieve dense nanocrystal-based '
      'nanocomposites</h4>'
      '<p class="meta">Cendejas, Moher &amp; Thimsen &middot; <i>JVST A</i> '
      '<b>39</b>, 012406 (2021)<br>'
      '<a href="https://doi.org/10.1116/6.0000588">10.1116/6.0000588</a></p>'
      '<p>A 1&nbsp;&micro;m film of packed nanocrystals. The question is '
      '<i>whether the pores fill</i>. Transport is Knudsen diffusion with no '
      'bulk flow, and the internal area per unit volume is enormous.</p></div>')
    A("</div>")
    A('<div class="col"><p class="strip-note">Paper&nbsp;B could not be read: a '
      'UTF-8 round-trip replaced 1.83&nbsp;million binary bytes of '
      '<code>012406_1_online.pdf</code> with U+FFFD, destroying every '
      'compressed stream, and the article is paywalled. Its model here is the '
      'standard porous-medium formulation, not a transcription &mdash; which '
      'makes the comparison below a useful check on the reconstruction rather '
      'than a claim about what that paper wrote.</p></div>')
    A("</section>")

    # ---------------- equations side by side ----------------
    A('<section><div class="col">')
    A("<h2>The equations</h2>")
    A('<p class="sub">Written in each paper&rsquo;s own notation</p>')
    A("<p>The only notational trap is the coverage variable: Yanguas-Gil&rsquo;s "
      "<span class=\"sym\">&theta;</span> counts sites still <i>available</i> "
      "and falls from 1 to 0; the infill model&rsquo;s counts sites "
      "<i>consumed</i> and rises from 0 to 1.</p>")
    A("</div>")
    A('<div class="sbs">')
    A('<div class="eqcard"><p class="who">A &middot; reactor, Eqs. (7)&ndash;(8)</p>'
      '<p class="eq">&part;n/&part;t + u&thinsp;&part;n/&part;z &minus; '
      'D&thinsp;&part;<sup>2</sup>n/&part;z<sup>2</sup><br>'
      '&nbsp;&nbsp;&nbsp;= &minus;(1/2R)&thinsp;v&#773;&thinsp;'
      '&beta;<sub>0</sub>&thinsp;&theta;&thinsp;n</p>'
      '<p class="eq" style="margin-top:14px">d&theta;/dt = &minus;(1/4)&thinsp;'
      's<sub>0</sub>&thinsp;v&#773;&thinsp;&beta;<sub>0</sub>&thinsp;n&thinsp;'
      '&theta;</p>'
      '<p class="cap"><span class="sym">&theta;</span> = available sites, '
      '<span class="sym">s<sub>0</sub></span> = area per site, '
      '<span class="sym">R</span> = tube radius.</p></div>')
    A('<div class="eqcard"><p class="who">B &middot; nanocrystal film</p>'
      '<p class="eq">&epsilon;&thinsp;&part;C/&part;t &minus; &part;/&part;z'
      '(D<sub>e</sub>&thinsp;&part;C/&part;z)<br>'
      '&nbsp;&nbsp;&nbsp;= &minus;S<sub>v</sub>&thinsp;&Gamma;&thinsp;'
      '&part;&theta;/&part;t</p>'
      '<p class="eq" style="margin-top:14px">&part;&theta;/&part;t = '
      '&beta;<sub>0</sub>(1&minus;&theta;)&thinsp;(v&#773;/4)&thinsp;C&thinsp;/'
      '&thinsp;&Gamma;</p>'
      '<p class="cap"><span class="sym">&theta;</span> = consumed sites, '
      '<span class="sym">&Gamma;</span> = sites per area, '
      '<span class="sym">S<sub>v</sub></span> = internal area per volume.</p>'
      '</div>')
    A("</div>")

    A('<div class="col">')
    A("<h3>Three substitutions collapse one into the other</h3>")
    A("</div>")
    A('<div class="tbl-wrap"><table><thead><tr>'
      "<th>Substitution</th><th>Why it holds</th></tr></thead><tbody>")
    for a, b in [
        ('<span class="sym">&theta;<sub>A</sub> = 1 &minus; &theta;<sub>B</sub>'
         '</span>',
         "Bookkeeping only &mdash; available sites versus consumed sites."),
        ('<span class="sym">s<sub>0</sub> = 1/&Gamma;</span>',
         "Area per adsorption site is the reciprocal of sites per unit area."),
        ('<span class="sym">1/(2R) = S<sub>v</sub>/4</span>',
         "A tube of radius R has S<sub>v</sub> = 2/R of wall per unit volume, "
         "so the reactor sink is the general S<sub>v</sub> sink written for "
         "one geometry."),
    ]:
        A("<tr><td>%s</td><td>%s</td></tr>" % (a, b))
    A("</tbody></table></div>")
    A('<div class="col"><p class="strip-note">Make those three swaps and the '
      'surface equations become character-for-character identical, and the gas '
      'sinks become the same expression. What is left over is a single term: '
      'the reactor has advection <span class="sym">u&thinsp;&part;n/&part;z'
      '</span>, the film does not.</p></div>')
    A("</section>")

    # ---------------- dimensionless groups ----------------
    A('<section><div class="col">')
    A("<h2>Dimensionless form</h2>")
    A('<p class="sub">Normalising the film model reproduces the reactor '
      'paper&rsquo;s Eqs. (9)&ndash;(10)</p>')
    A("<p>With <span class=\"sym\">x = C/C<sub>0</sub></span>, "
      "<span class=\"sym\">&xi; = z/L</span> and "
      "<span class=\"sym\">&tau; = tD/L<sup>2</sup></span>, both models are:</p>")
    A('<div class="eqcard"><p class="eq">'
      '&epsilon;&thinsp;&part;x/&part;&tau; + Pe&thinsp;&part;x/&part;&xi; '
      '&minus; &part;<sup>2</sup>x/&part;&xi;<sup>2</sup> = &minus;Da&thinsp;'
      '&theta;&thinsp;x<span class="n">(9)</span></p>'
      '<p class="eq" style="margin-top:12px">&part;&theta;/&part;&tau; = '
      '&minus;&gamma;&thinsp;Da&thinsp;&theta;&thinsp;x'
      '<span class="n">(10)</span></p>'
      '<p class="cap">The reactor paper has '
      '<span class="sym">&epsilon; = 1</span> (an open tube is all void); the '
      'film carries its porosity. Everything else is shared.</p></div>')
    A("</div>")
    A('<div class="tbl-wrap"><table><thead><tr>'
      "<th>Group</th><th>Definition</th><th>Reactor (01A159)</th>"
      "<th>Nanocrystal film</th></tr></thead><tbody>")
    A('<tr><td>Peclet <span class="sym">Pe</span></td>'
      '<td>uL / D &mdash; convection vs diffusion</td>'
      '<td class="num">%g</td><td class="num">0 <span style="color:var(--muted)">'
      '(no bulk flow)</span></td></tr>' % p["Pe"])
    A('<tr><td>Damk&ouml;hler <span class="sym">Da</span></td>'
      '<td>(S<sub>v</sub>/4)(L<sup>2</sup>/D) v&#773; &beta;<sub>0</sub> '
      '&mdash; reaction vs transport</td>'
      '<td class="num">%g</td><td class="num">%.0f</td></tr>'
      % (p["Da"], d["Da"]))
    A('<tr><td>Excess <span class="sym">&gamma;</span></td>'
      '<td>C<sub>0</sub> / (S<sub>v</sub>&Gamma;) &mdash; molecules per site'
      '</td><td class="num">%g</td><td class="num">%s</td></tr>'
      % (p["gamma"], sci(d["gamma"])))
    A("</tbody></table></div>")
    A('<div class="col"><p class="strip-note">The infill model&rsquo;s capacity '
      'ratio <span class="sym">&alpha; = S<sub>v</sub>&Gamma;/C<sub>0</sub></span> '
      'is <b>exactly</b> <span class="sym">1/&gamma;</span>: '
      '%s versus %s, equal to machine precision. Two papers named the same '
      'group from opposite ends &mdash; one counting molecules per site, the '
      'other sites per molecule.</p></div>'
      % (sci(d["alpha"]), sci(1.0 / d["gamma"])))
    A("</section>")

    # ---------------- the numerical check ----------------
    A("<section>")
    A('<div class="col"><h2>The check</h2>')
    A('<p class="sub">Same groups in, same profile out</p>')
    A("<p>Both solvers were run at "
      "<span class=\"sym\">Pe = 0</span>, "
      "<span class=\"sym\">Da = %.0f</span>, "
      "<span class=\"sym\">&gamma; = %s</span> to "
      "<span class=\"sym\">&tau; = %s</span> "
      "(a %s dose on the 1&nbsp;&micro;m film) &mdash; the infill solver on its "
      "physical finite-volume grid, and a direct implementation of "
      "Eqs.&nbsp;(9)&ndash;(10) on a dimensionless one.</p></div>"
      % (d["Da"], sci(d["gamma"]), sci(d["tau"]), secs(d["t_phys"])))
    A('<figure><div class="fig-frame">'
      '<img src="data:image/png;base64,%s" '
      'alt="Four panels comparing the two models: overlaid coverage profiles '
      'that coincide; the effect of the excess number on timescale; the effect '
      'of the Peclet number sweeping the front downstream; and the effect of '
      'the Damkoehler number on front sharpness.">' % fig_b64)
    A("</div>")
    A('<figcaption><div class="col" style="margin-left:0">'
      '<b>(a)</b> The two solutions lie on top of each other, max |&Delta;&theta;| '
      '= %.1e, front position %.4f vs %.4f. '
      '<b>(b)</b> <span class="sym">&gamma;</span> rescales time and nothing '
      'else &mdash; until it approaches 1, where the dose gets short enough '
      'that gas-phase transients stop being negligible. '
      '<b>(c)</b> The one term that genuinely differs: advection carries the '
      'growth front downstream, which is why a reactor can be starved at the '
      'exit while a film is starved at depth. '
      '<b>(d)</b> <span class="sym">Da</span> alone sets how sharp the front '
      'is &mdash; and both systems sit at Da of order 10<sup>3</sup>, which is '
      'why both show a step rather than a gradient.</div></figcaption></figure>'
      % (d["err"]["published"], d["front_mine"], d["front_published"]))
    A("</section>")

    # ---------------- what actually differs ----------------
    A('<section><div class="col">')
    A("<h2>Where they part company</h2>")
    A('<p class="sub">Five terms, one of which is structural</p>')
    A("</div>")
    A('<div class="tbl-wrap"><table><thead><tr>'
      "<th>Term</th><th>Reactor</th><th>Nanocrystal film</th><th></th>"
      "</tr></thead><tbody>")
    for term, a, b, same in [
        ("Surface kinetics", "&beta;<sub>0</sub>&theta;, first order",
         "&beta;<sub>0</sub>(1&minus;&theta;)<sup>n</sup>, n adjustable",
         "identical at n = 1"),
        ("Gas sink", "1/(2R) &middot; v&#773;&beta;<sub>0</sub>&theta;n",
         "S<sub>v</sub>/4 &middot; v&#773;&beta;<sub>0</sub>&theta;C",
         "same expression"),
        ("Advection", "u&thinsp;&part;n/&part;z, Pe = %g" % p["Pe"],
         "none, Pe = 0", None),
        ("Diffusivity", "molecular, %.3g m<sup>2</sup>/s" % d["D_reactor"],
         "Knudsen, %s m<sup>2</sup>/s" % sci(d["D_film"]), None),
        ("Area per volume", "2/R = %.0f m<sup>&minus;1</sup>" % d["S_v_reactor"],
         "3(1&minus;&epsilon;)/r = %s m<sup>&minus;1</sup>" % sci(d["S_v_film"]),
         None),
        ("Geometry over time", "fixed",
         "S<sub>v</sub>, r<sub>p</sub>, D<sub>e</sub> shrink every cycle", None),
    ]:
        cls, txt = ("same", same) if same else ("diff", "differs")
        A('<tr><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td></tr>'
          % (term, a, b, cls, txt))
    A("</tbody></table></div>")
    A('<div class="col"><p class="strip-note">Only the advection term changes '
      'the mathematics. The rest are the same equation evaluated at different '
      'coefficients &mdash; and the last row is the one the reactor model has '
      'no analogue for, because a reactor tube does not fill itself in.</p>'
      '</div>')
    A("</section>")

    # ---------------- verdict ----------------
    A('<section><div class="col">')
    A("<h2>Verdict</h2>")
    A('<p class="sub">Same equation, different regime</p>')
    A('<div class="verdict"><span class="label">Do they boil down to the same '
      'result?</span>')
    A('<p><b>The equations: yes.</b> Up to the coverage convention and the '
      'advection term, they are one system. Fed the same '
      '<span class="sym">(Pe, Da, &gamma;)</span> the two independent solvers '
      'return the same profile to %.1e in coverage &mdash; and the porosity '
      'term that appears in one and not the other changes the answer by '
      'less than %.0e, because at '
      '<span class="sym">&gamma; &lt;&lt; 1</span> gas-phase accumulation is '
      'negligible either way.</p>'
      % (d["err"]["published"], abs(d["err"]["matched"] - d["err"]["published"])
         + 1e-9))
    A('<p><b>The regimes: far apart, and not where you would guess.</b> '
      '<span class="sym">Da</span> is comparable (%.0f vs %g), so both show a '
      'sharp front rather than a gradient. '
      '<span class="sym">&gamma;</span> differs by a factor of %s &mdash; a '
      'reactor tube holds a couple of precursor molecules per surface site, a '
      'nanocrystal film about one per hundred thousand. Yet the dose times '
      'come out within an order of magnitude of each other: <b>%s</b> to drive '
      'the front through the film against <b>%s</b> through the reactor. Both '
      'scale as <span class="sym">L<sup>2</sup>/(2&gamma;D)</span>, and the '
      'film being %s shorter very nearly repays its %s deficit in '
      '<span class="sym">&gamma;</span>.</p>'
      % (d["Da"], p["Da"], sci(p["gamma"] / d["gamma"], 2),
         secs(d["t_sat_film"]), secs(d["t_sat_reactor"]),
         sci(0.45 / d["model"].film.thickness, 2),
         sci(p["gamma"] / d["gamma"], 2)))
    A('<p>What does <i>not</i> cancel is the last row of the table above. A '
      'reactor tube has the same radius on cycle 500 as on cycle 1; a '
      'nanocrystal film is busy sealing its own pores, so '
      '<span class="sym">S<sub>v</sub></span>, '
      '<span class="sym">r<sub>p</sub></span> and '
      '<span class="sym">D<sub>e</sub></span> all collapse as it densifies and '
      'the dose requirement climbs by orders of magnitude across a run. That '
      'is the one question the reactor model structurally cannot be asked.</p>')
    A('<p>Practically: the reactor paper&rsquo;s three groups are the right '
      'coordinates for the infill problem too, and the reconstruction of '
      'paper&nbsp;B lands inside the family paper&nbsp;A defined. That is '
      'reassuring, but it is not the same as knowing what paper&nbsp;B wrote '
      '&mdash; a readable copy would still settle the closures it chose for '
      '<span class="sym">S<sub>v</sub>(&epsilon;)</span> and pore closure.</p>')
    A("</div></div>")
    A("</section>")

    A('<footer><div class="col">')
    A("Generated by <code>twin/model_comparison_report.py</code>. Models: "
      "<code>twin/yanguas_gil_reactor.py</code> (transcribed from 01A159) and "
      "<code>twin/nc_infill_model.py</code>. Figure: "
      "<code>twin/nc_infill_vs_yanguas.py</code>. Equivalence is checked in "
      "<code>tests/test_nc_infill_model.py</code> &sect;I. SI units throughout.")
    A("</div></footer>")
    A("</div>")
    return "\n".join(out)


def main():
    if not FIG.exists():
        print("figure missing; generating it first")
        subprocess.check_call([sys.executable,
                               str(HERE / "nc_infill_vs_yanguas.py")])
    print("running both models for the comparison ...")
    d = collect()
    print("  Pe=0 Da=%.4g gamma=%.4g  vs  paper Pe=%g Da=%g gamma=%g"
          % (d["Da"], d["gamma"], d["paper"]["Pe"], d["paper"]["Da"],
             d["paper"]["gamma"]))
    print("  max|d(theta)| = %.3e" % d["err"]["published"])
    OUT.write_text(build(d), encoding="utf-8")
    print("wrote %s (%.0f kB)" % (OUT, OUT.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
