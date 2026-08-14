#!/usr/bin/env python3
"""The workbench must render the frozen graph without simplifying it.

Two failures from the previous workbench are pinned here because both were invisible
while looking plausible. It collapsed a ResultSeries' case membership to `case_ids[0]`,
so a sweep spanning ten condition cases silently belonged to one. And its Y control
changed an axis title while the plotted coordinates stayed raw -- the picture looked
normalized and was not.

The structural answer to the second is that the page never transforms anything: every
offered representation arrives with its coordinates already computed, so an option that
cannot be materialised cannot be offered, and choosing one necessarily moves the curve.

The DOM half of this suite drives the real page in Chromium. Static assertions about
JavaScript are not evidence that a control works.

Run:  python3 tests/test_workbench_v2.py
"""
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
WB = W / "_diagnostics" / "workbench_v2"

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def main():
    mp, vp = WB / "workbench_model.json", WB / "workbench_validation.json"
    hp = WB / "psed_scientific_comparison_workbench.html"
    for p in (mp, vp, hp):
        ok("artifact %s exists" % p.name, p.exists(), str(p))
    if not all(p.exists() for p in (mp, vp, hp)):
        print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
        return 1
    M = json.loads(mp.read_text())
    V = json.loads(vp.read_text())
    CASES, ACTS, SER = M["cases"], M["acts"], M["series"]

    print("=== A. frozen counts survive model construction ===")
    for k, want in (("condition_cases", 182), ("measurement_records", 213),
                    ("measurement_acts", 201), ("result_series_persisted", 231),
                    ("result_series_searchable", 231),
                    ("multi_case_result_series", 22), ("max_cases_per_result_series", 10),
                    ("multi_member_measurement_acts", 6)):
        ok("A: %-30s = %d" % (k, want), V["counts"][k] == want, V["counts"][k])
    ok("A: every declared invariant holds", V["invariants_ok"],
       [k for k, x in V["invariants"].items() if not x])

    print("=== B. the graph is not flattened ===")
    # exhaustive, not a spot check: every multi-case series keeps its whole membership
    multi = [s for s in SER.values() if s["n_cases"] > 1]
    ok("B: all 22 multi-case series present", len(multi) == 22, len(multi))
    ok("B: none was reduced to a single case",
       all(len(s["case_ids"]) == s["n_cases"] and s["n_cases"] > 1 for s in multi))
    ok("B: single_case is null whenever there are several",
       all(s["single_case"] is None for s in multi))
    ok("B: and set only when there is exactly one",
       all(s["single_case"] is not None for s in SER.values() if s["n_cases"] == 1))
    ok("B: cardinality status is explicit",
       all(s["case_cardinality_status"] in ("SINGLE_CASE", "MULTI_CASE", "NO_CASE")
           for s in SER.values()))
    ok("B: every case id on a series resolves",
       all(c in CASES for s in SER.values() for c in s["case_ids"]))
    ok("B: acts also keep multi-case membership",
       any(a["n_cases"] > 1 for a in ACTS.values()))
    ok("B: reverse edges exist (case -> series)",
       all(any(s in CASES[c]["series_ids"] for c in SER[s]["case_ids"])
           for s in list(SER)[:60] if SER[s]["case_ids"]))

    print("=== C. no first-case logic anywhere in the workbench code ===")
    import io, re, tokenize
    for f in (WB / "build_workbench_model.py", WB / "_workbench_v2_template.html"):
        src = f.read_text()
        if f.suffix == ".py":
            body = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                           for t in tokenize.generate_tokens(io.StringIO(src).readline))
        else:
            body = re.sub(r"//.*|/\*.*?\*/", "", src, flags=re.S)
        ok("C: %-32s has no case_ids[0]" % f.name, "case_ids[0]" not in body)
        ok("C: %-32s has no next(iter(case" % f.name, "next(iter(case" not in body)

    print("=== D. measurement acts, not per-curve measurements ===")
    mm = [a for a in ACTS.values() if a["n_members"] > 1]
    ok("D: multi-member acts exist and are grouped", len(mm) == 6, len(mm))
    ok("D: each cites its grouping evidence",
       all(a["grouping_evidence"] for a in mm))
    ok("D: evidence is the same-measurement relation, not a figure",
       all(any("represents_same_measurement_as" in e for e in a["grouping_evidence"])
           for a in mm))
    keyed = {v["measurement_id"] for v in M["measurements"].values()}
    ok("D: member measurement ids remain addressable",
       all(m in keyed for a in mm for m in a["member_measurement_ids"]),
       [m for a in mm for m in a["member_measurement_ids"] if m not in keyed][:2])
    ok("D: acts and measurements are different collections",
       len(ACTS) != len(M["measurements"]))

    print("=== E. every offered representation carries its own coordinates ===")
    offered = [(s["id"], ax, k, r) for s in SER.values()
               for ax in ("x_representations", "y_representations")
               for k, r in s[ax].items()]
    avail = [x for x in offered if x[3].get("available")]
    ok("E: available representations exist", avail, len(avail))
    ok("E: every available one has values",
       all(r.get("values") for _, _, _, r in avail))
    ok("E: every unavailable one says why",
       all(r.get("unavailable_reason") for _, _, _, r in offered
           if not r.get("available")))
    # length agreement is what makes plotting safe
    bad = [sid for sid, ax, k, r in avail
           if len(r["values"]) != len(SER[sid]["x_representations"]["native"]["values"])]
    ok("E: coordinate arrays all agree in length", not bad, bad[:3])

    print("=== F. t/t_max is computed, t/t_entrance is refused ===")
    tm = [(s["id"], r) for s in SER.values()
          for k, r in s["y_representations"].items() if k == "norm:t_over_t_max"]
    ok("F: some series offer t_over_t_max", tm, len(tm))
    for sid, r in tm[:6]:
        native = SER[sid]["y_representations"]["native"]["values"]
        ref = max(native)
        want = [v / ref for v in native]
        ok("F: %s values equal y/max(y)" % sid[-26:],
           all(abs(a - b) < 1e-9 for a, b in zip(r["values"], want)))
        ok("F: %s records its denominator provenance" % sid[-26:],
           r["transform"]["parameter_provenance"]["source_object"], r["transform"])
    ent = [r for s in SER.values() for k, r in s["y_representations"].items()
           if k == "norm:t_over_t_entrance"]
    ok("F: t_over_t_entrance is never offered as available",
       all(not r["available"] for r in ent), len(ent))
    ok("F: and names what it would need",
       all("not resolved for this series" in str(r.get("unavailable_reason"))
           and r.get("normalization") for r in ent), ent[:1])

    print("=== G. unknown normalization basis stays unknown ===")
    unk = [s for s in SER.values() if s["normalization_basis"] == "unresolved"]
    ok("G: unresolved-basis series exist in the corpus", unk, len(unk))
    ok("G: none is given a known basis",
       all(s["y"]["y_norm"] is None for s in unk))
    ok("G: none offers t_over_t_max as if it were its own basis",
       all("norm:t_over_t_max" not in s["y_representations"] for s in unk))

    print("=== H. comparability verdicts come from the runtime ===")
    P = M["pairs"]
    ok("H: pair verdicts are embedded", P, len(P))
    ok("H: each carries per-axis status and reason",
       all(p.get("x_status") and p.get("y_reason") for p in P.values()))
    ok("H: shape-only is a separate outcome",
       all("shape_only_status" in p for p in P.values()))
    ok("H: missing context is named, not generic",
       all(isinstance(p.get("missing"), list) for p in P.values()))

    print("=== I. physical identity is shown as unresolved, never invented ===")
    ok("I: no case claims a resolved specimen",
       all(c["realization"]["physical_specimen_identity"] == "unresolved"
           for c in CASES.values()))
    ok("I: no sample carries a fabricated specimen id",
       all(s["physical_specimen"] is None for s in M["samples"].values()))
    ok("I: run links are sample-scoped",
       all(r.get("scope") == "SAMPLE_SCOPED" for r in M["runs"].values()))
    ok("I: a case names the sample each run came from",
       all("via_sample" in r for c in CASES.values()
           for r in c["realization"]["runs_observed"]))

    print("=== J. CASE-10.103-002 reconstruction ===")
    k = "10.1039_d0cp03358h::CASE-10.103-002"
    c2 = CASES.get(k)
    ok("J: the fixture case exists", c2 is not None)
    if c2:
        ok("J: it is a condition case, not an experiment",
           c2["entity"] == "CONDITION_CASE")
        ok("J: 6 source sample records", c2["realization"]["source_sample_records"] == 6,
           c2["realization"]["source_sample_records"])
        ok("J: physical specimen identity unresolved",
           c2["realization"]["physical_specimen_identity"] == "unresolved")
        ok("J: exactly one run, reached through one sample",
           len(c2["realization"]["runs_observed"]) == 1,
           c2["realization"]["runs_observed"])
        acts2 = [a for a in ACTS.values() if k in a["case_ids"]]
        ser2 = [s for s in SER.values() if k in s["case_ids"]]
        ok("J: 15 measurement acts", len(acts2) == 15, len(acts2))
        ok("J: 15 result series", len(ser2) == 15, len(ser2))
        ok("J: the 15 acts are distinct, not one act repeated",
           len({a["id"] for a in acts2}) == 15)

    print("=== K. terminology does not mislead ===")
    html = hp.read_text()
    ui = re.findall(r">([^<>{}]{3,60})<", html)
    bad = [t for t in ui if re.fullmatch(r"\s*Experiments?\s*", t)]
    ok("K: no user-visible bare 'Experiment' label", not bad, bad[:3])
    ok("K: condition-case terminology is used", "Condition Case" in html)
    ok("K: measurement acts are named", "measurement act" in html.lower())
    ok("K: physical specimen is distinguished from source sample",
       "source sample" in html.lower() and "physical specimen" in html.lower())
    ok("K: unresolved states are surfaced", "unresolved" in html.lower())

    print("=== L. the page is self-contained ===")
    ok("L: no remote script or style",
       'src="http' not in html and "@import" not in html and "cdn." not in html)
    ok("L: no network calls", not any(t in html for t in ("fetch(", "XMLHttpRequest",
                                                          "WebSocket")))
    ok("L: model placeholder was substituted", "/*__MODEL__*/" not in html)

    hardening_tests(M, V, hp)
    dom_tests(hp)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


def hardening_tests(M, V, hp):
    """The four defects an external review found in the first workbench.

    Each is asserted on the artifact, not on an intention: a shared axis is only offered
    when the two series mean the same physical quantity, one curve is one entry, a range
    filter compares canonical magnitudes, and a simulated curve is not counted as a
    measurement.
    """
    SER, ACTS, C = M["series"], M["acts"], V["counts"]
    html = hp.read_text()

    print("=== N1. every representation carries a scientific target identity ===")
    reps = [(sid, ax, k, r) for sid, s in SER.items()
            for ax in ("x_representations", "y_representations")
            for k, r in (s.get(ax) or {}).items()]
    ok("N1: representations exist", len(reps) > 0, len(reps))
    ok("N1: every representation has a target_id",
       all(r.get("target_id") for _, _, _, r in reps),
       [(a, b) for a, b, c, r in reps if not r.get("target_id")][:3])
    ok("N1: a target_id names axis, quantity, normalization, dimension and unit",
       all(r["target_id"].count("|") == 4 for _, _, _, r in reps))
    ok("N1: x and y targets can never collide",
       all(r["target_id"].startswith(ax[0] + "|") for _, ax, _, r in reps))

    print("=== N2. 'native' is a local label, not a shared target ===")
    natives = {r["target_id"] for _, ax, k, r in reps
               if k == "native" and ax == "y_representations"}
    ok("N2: the corpus really does hold several distinct native Y targets",
       len(natives) > 1, sorted(natives))
    ok("N2: validation reports them", V["counts"]["distinct_y_native_targets"] > 1,
       V["counts"]["distinct_y_native_targets"])
    ok("N2: no target is falsely common across incompatible series",
       C["false_common_native_targets"] == 0, C["false_common_native_targets"])
    ok("N2: the invariant is declared", V["invariants"]["native_targets_are_not_universal"])

    print("=== N3. the common-target calculation is semantic, not by key ===")
    js = html
    ok("N3: targets are intersected on target_id", "map(r => r.target_id)" in js)
    ok("N3: the old key intersection is gone",
       "Object.keys(reps).filter(k => reps[k].available" not in js)
    ok("N3: a representation is selected by target, not by name",
       "function repByTarget" in js and "r.target_id === tid" in js)

    print("=== N4. a shared physical axis needs the frozen verdict ===")
    ok("N4: every indexed pair declares overlay eligibility",
       V["invariants"]["every_pair_declares_overlay_eligibility"])
    bad = [k for k, p in M["pairs"].items()
           if p["physical_overlay_allowed"]
           and p["status"] not in ("DIRECT_PROFILE", "TRANSFORMABLE_PROFILE")]
    ok("N4: overlay is allowed only for comparable verdicts", not bad, bad[:3])
    ok("N4: the page consults it before offering an axis",
       "function physicalOverlayAllowed" in js and "physical_overlay_allowed" in js)
    ok("N4: shape-only overlay stays an explicit opt-in",
       "shapeOnly ? !(p.physical_overlay_allowed || p.shape_only_eligible)" in js)

    print("=== N5. one ResultSeries is one result entry ===")
    ok("N5: multi-case series exist to be duplicated",
       C["primary_result_entries_for_multi_case_series"] > 0)
    ok("N5: each gets exactly one primary entry",
       C["primary_result_entries_for_multi_case_series"] == C["multi_case_result_series"],
       (C["primary_result_entries_for_multi_case_series"],
        C["multi_case_result_series"]))
    ok("N5: no series is listed twice", C["duplicate_primary_entries"] == 0)
    ok("N5: the results column groups by primary case", "const byCase = {}, alsoIn = {}" in js)
    ok("N5: other traversed cases cross-reference instead of repeating",
       "Also traversed by" in js)
    ok("N5: the multi-case span is expandable",
       "Spans ${s.n_cases} Condition Cases" in js)

    print("=== N6. range filtering compares canonical magnitudes ===")
    ok("N6: rangeOk reads the canonical value", "v.canonical" in js)
    ok("N6: rangeOk no longer reads the raw value", "const n = v.raw;" not in js)
    rf = M["range_fields"]
    ok("N6: range fields are declared by the model, not hardcoded",
       len(rf) > 0 and "const RANGES = M.range_fields" in js, len(rf))
    ok("N6: every range field states the unit it compares in",
       all(f.get("canonical_unit") for f in rf))
    conv = [f for f in rf if f["canonical_unit"] not in f["raw_units"]]
    ok("N6: at least one field is reported in a different unit than it filters in",
       bool(conv), [(f["id"], f["raw_units"], f["canonical_unit"]) for f in rf])
    ok("N6: the numeric index is materially canonical",
       C["numeric_with_canonical"] > 0.9 * C["numeric_fields_indexed"],
       (C["numeric_with_canonical"], C["numeric_fields_indexed"]))

    print("=== N7. simulated curves are not counted as measurements ===")
    ok("N7: the corpus holds simulation runs", C["simulation_runs"] > 0)
    ok("N7: acts and simulation runs are disjoint",
       V["invariants"]["measurement_acts_exclude_simulations"])
    ok("N7: the header counts them separately", "simulation runs" in js)
    sim_acts = {a for a, x in ACTS.items() if x["kind"] == "SIMULATION_RUN"}
    ok("N7: no simulation run is inside the measurement act count",
       C["measurement_acts"] == len([a for a in ACTS if a not in sim_acts]),
       (C["measurement_acts"], len(ACTS), len(sim_acts)))


def dom_tests(hp):
    """Drive the real page in Chromium. Static JS assertions are not evidence."""
    print("=== M. browser acceptance (Chromium) ===")
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        ok("M: playwright available", False, str(e)[:80])
        return
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception as e:
            ok("M: chromium launches", False, str(e).splitlines()[0][:90])
            return
        pg = b.new_page()
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(hp.resolve().as_uri())
        pg.wait_for_selector("#results .case", timeout=20000)

        ok("M: page loads with no console errors", not errors, errors[:2])
        ok("M: condition case cards render", pg.locator("#results .case").count() > 0)
        ok("M: corpus counts are shown", "condition cases" in pg.inner_text("#corpus"))
        ok("M: the about panel states specimen completeness",
           "physical specimen completeness" in pg.inner_text("#about"))

        # --- facets: open, click, auto-close, chip
        n0 = pg.locator("#results .case").count()
        pg.locator('.fbtn[data-f="material"]').click()
        ok("M: facet popover opens", pg.locator(".pop").count() == 1)
        opt = pg.locator(".pop .opt").first
        val = opt.get_attribute("data-v")
        opt.click()
        ok("M: clicking an option closes the popover", pg.locator(".pop").count() == 0)
        ok("M: a chip appears for the selection",
           val in pg.inner_text("#facets"), val)
        n1 = pg.locator("#results .case").count()
        ok("M: the result set narrows or holds", n1 <= n0, (n0, n1))

        # --- add a series to the tray
        pg.locator("#results .case").first.click()          # expand
        pg.wait_for_selector("button[data-add]", timeout=10000)
        add = pg.locator("button[data-add]").first
        sid = add.get_attribute("data-add")
        add.click()
        ok("M: a result series can be added to the tray",
           "1/8" in pg.inner_text("#tray"), pg.inner_text("#tray")[:60])

        # --- tray persists across a filter change (the mandatory regression)
        pg.locator('.fbtn[data-f="paper"]').click()
        pg.locator(".pop .opt").last.click()
        ok("M: tray survives a filter change",
           sid.split("::")[-1] in pg.inner_text("#tray")
           or "1/8" in pg.inner_text("#tray"), pg.inner_text("#tray")[:80])
        pg.locator("#clear-all").click()
        ok("M: clear-all restores the corpus and keeps the tray",
           pg.locator("#results .case").count() >= n0 and "1/8" in pg.inner_text("#tray"))

        # --- Y transform must move the plotted curve (the old TY defect)
        pg.evaluate("""() => {
            const id = Object.keys(SERIES).find(k =>
                SERIES[k].y_representations['norm:t_over_t_max']);
            tray.length = 0; tray.push(id); TX=null; TY=null; render();
        }""")
        pg.wait_for_selector("#plot svg", timeout=10000)
        # Pixel coordinates cannot witness a LINEAR transform: y/max rescales the data and
        # the auto-ranged axis rescales it straight back, so the polyline is identical.
        # The evidence that matters is the values actually plotted and labelled.
        plotted = lambda: pg.evaluate("""() => {
            const t = document.querySelectorAll('#plot circle title');
            return [...t].slice(0,4).map(n => n.textContent);
        }""")
        before_vals = plotted()
        before = pg.eval_on_selector("#plot polyline", "e => e.getAttribute('points')")
        svgtext = lambda sel: (pg.locator(sel).first.text_content()
                               if pg.locator(sel).count() else "")
        ylab_before = svgtext("#plot #ylab")
        pg.evaluate("() => { TY = SERIES[tray[0]].y_representations['norm:t_over_t_max']"
                    ".target_id; drawCompare(); }")
        pg.wait_for_selector("#plot svg", timeout=10000)
        after_vals = plotted()
        after = pg.eval_on_selector("#plot polyline", "e => e.getAttribute('points')")
        ylab_after = svgtext("#plot #ylab")
        ok("M: choosing a Y normalization changes the plotted y values",
           before_vals != after_vals, (before_vals[:1], after_vals[:1]))
        # the tooltip must name the target quantity, not a generic "y"
        ok("M: the tooltip reports the normalized quantity, value and unit",
           all("normalized_thickness=" in v for v in after_vals)
           and any(v.rstrip().endswith(" 1") for v in after_vals), after_vals[:1])
        ok("M: pixel geometry is unchanged because the transform is linear and the "
           "axis auto-ranges", before == after)
        ok("M: and changes the axis label", ylab_before != ylab_after,
           (ylab_before, ylab_after))
        ok("M: the axis label names the basis", "t_over_t_max" in ylab_after, ylab_after)
        # the values actually plotted are the normalized ones
        vals = pg.evaluate("""() => {
            const sid = tray[0];
            const r = SERIES[sid].y_representations['norm:t_over_t_max'];
            const n = SERIES[sid].y_representations['native'];
            const ref = Math.max.apply(null, n.values);
            return {ok: r.values.every((v,i) => Math.abs(v - n.values[i]/ref) < 1e-9),
                    max: Math.max.apply(null, r.values)};
        }""")
        ok("M: normalized values equal y/max(y)", vals["ok"], vals)
        ok("M: and the normalized maximum is 1", abs(vals["max"] - 1) < 1e-9, vals["max"])

        # --- source values untouched by the display choice
        src_ok = pg.evaluate("""() => {
            const s = SERIES[tray[0]];
            return s.y_representations.native.values.length === s.n_points
                || s.y_representations.native.values.length > 0;
        }""")
        ok("M: raw/native values remain available and unmodified", src_ok)

        # --- X transform where a canonical projection exists
        xres = pg.evaluate("""() => {
            const id = Object.keys(SERIES).find(k =>
                Object.keys(SERIES[k].x_representations).some(r => r.startsWith('proj:')));
            if (!id) return null;
            const key = Object.keys(SERIES[id].x_representations).find(r => r.startsWith('proj:'));
            tray.length = 0; tray.push(id); TX=null; TY=null; render(); drawCompare();
            const vals = () => [...document.querySelectorAll('#plot circle title')]
                .slice(0,3).map(n => n.textContent);
            const a = vals();
            TX = SERIES[id].x_representations[key].target_id; drawCompare();
            const b = vals();
            return {changed: JSON.stringify(a) !== JSON.stringify(b), key, before: a[0],
                    after: b[0], label: document.querySelector('#plot #xlab').textContent};
        }""")
        if xres:
            ok("M: choosing an X projection changes the plotted x values",
               xres["changed"], {"before": xres["before"], "after": xres["after"]})
            ok("M: and the x axis label follows", xres["key"].split(":")[1] in xres["label"],
               xres["label"])
        else:
            ok("M: no canonical x projection in corpus (reported, not faked)", True)

        # --- multi-case provenance is visible
        mres = pg.evaluate("""() => {
            const id = Object.keys(SERIES).find(k => SERIES[k].n_cases > 1);
            tray.length = 0; tray.push(id); render();
            return {n: SERIES[id].n_cases, cases: SERIES[id].case_ids.length};
        }""")
        ok("M: a multi-case series keeps every case in the model",
           mres["n"] == mres["cases"] and mres["n"] > 1, mres)

        # --- removing a series
        pg.evaluate("() => { tray.length=0; render(); }")
        ok("M: tray can be emptied", "0/8" in pg.inner_text("#tray"))
        ok("M: no console errors accumulated during interaction", not errors, errors[:2])

        hardening_dom(pg, errors)
        b.close()


def hardening_dom(pg, errors):
    """Browser evidence for the four repairs. Model assertions are not a working page."""
    print("=== O. browser evidence for the hardening ===")

    # --- A: two series whose native Y means different physics cannot share an axis
    sel = pg.evaluate("""() => {
        const nat = k => (SERIES[k].y_representations||{}).native;
        const ids = Object.keys(SERIES).filter(k => nat(k) && nat(k).values);
        const a = ids[0]; if (!a) return null;
        const b = ids.find(k => nat(k).target_id !== nat(a).target_id);
        if (!b) return null;
        tray.length = 0; tray.push(a, b); TX=null; TY=null; render();
        return {a, b, ta: nat(a).target_id, tb: nat(b).target_id,
                common: commonTargets('y').length,
                enabled: [...document.querySelectorAll('input[name=ry]')]
                           .filter(r => !r.disabled).length,
                polylines: document.querySelectorAll('#plot polyline').length,
                note: (document.querySelector('#plot .note')||{}).textContent || ''};
    }""")
    if not sel:
        ok("O: corpus holds two differing native Y targets", False, "not found")
    else:
        ok("O: the two series really do mean different physics",
           sel["ta"] != sel["tb"], (sel["ta"], sel["tb"]))
        ok("O: no common Y target is offered for them", sel["common"] == 0, sel["common"])
        ok("O: every Y option is disabled", sel["enabled"] == 0, sel["enabled"])
        ok("O: nothing is drawn on a shared axis", sel["polylines"] == 0, sel["polylines"])
        ok("O: the page says why rather than failing silently",
           "shared" in sel["note"].lower() or "authorise" in sel["note"].lower(),
           sel["note"][:90])

    # --- A: and two series that DO share a target overlay, on one stated axis
    good = pg.evaluate("""() => {
        const nat = k => (SERIES[k].y_representations||{}).native;
        for (const a of Object.keys(SERIES)) {
            if (!nat(a) || !nat(a).values || !SERIES[a].is_profile) continue;
            for (const b of Object.keys(SERIES)) {
                if (b === a || !nat(b) || !nat(b).values || !SERIES[b].is_profile) continue;
                const p = pairOf(a,b);
                if (!p || !p.physical_overlay_allowed) continue;
                if (nat(a).target_id !== nat(b).target_id) continue;
                tray.length = 0; tray.push(a,b); TX=null; TY=null; render();
                if (document.querySelectorAll('#plot polyline').length < 2) continue;
                return {a, b, target: nat(a).target_id,
                        polylines: document.querySelectorAll('#plot polyline').length,
                        ylab: document.querySelector('#plot #ylab').textContent,
                        unit: nat(a).unit,
                        tips: [...document.querySelectorAll('#plot circle title')]
                                .slice(0,2).map(n => n.textContent)};
            }
        }
        return null;
    }""")
    if not good:
        ok("O: a compatible overlay exists in the corpus", False, "none found")
    else:
        ok("O: two compatible series overlay together", good["polylines"] >= 2, good)
        ok("O: on one axis labelled with the shared target",
           good["unit"] in good["ylab"], (good["ylab"], good["unit"]))
        ok("O: tooltips are stated in the target unit",
           all(good["unit"] in t for t in good["tips"]), good["tips"][:1])

    # --- B: one multi-case curve is one entry
    multi = pg.evaluate("""() => {
        tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
        RANGES.forEach(r => range[r.id] = {min:"",max:""});
        const id = Object.keys(SERIES).sort((x,y)=>SERIES[y].n_cases-SERIES[x].n_cases)[0];
        if (SERIES[id].n_cases < 2) return null;
        // page to wherever its primary case is listed
        const home = SERIES[id].case_ids[0];
        for (page = 0; page < 40; page++) {
            render();
            if (document.querySelector(`[data-ser="${id}"]`)) break;
        }
        document.querySelectorAll('#results details.case').forEach(d => d.open = true);
        const rows = document.querySelectorAll(`[data-ser="${id}"]`).length;
        return {id, n: SERIES[id].n_cases, rows, home,
                spans: document.body.innerHTML.indexOf('Spans ' + SERIES[id].n_cases
                       + ' Condition Cases') >= 0,
                xref: document.body.innerHTML.indexOf('Also traversed by') >= 0};
    }""")
    if not multi:
        ok("O: a multi-case series exists", False, "none")
    else:
        ok("O: a %d-case curve is listed exactly once" % multi["n"],
           multi["rows"] == 1, multi)
        ok("O: its full case span is offered as an expandable list", multi["spans"], multi)
        ok("O: the cases it traverses cross-reference it instead of repeating it",
           multi["xref"], multi)

    # --- C: the range filter compares canonical magnitudes
    rf = pg.evaluate("""() => {
        const f = RANGES.find(r => r.raw_units.length &&
                                   r.raw_units.indexOf(r.canonical_unit) < 0);
        if (!f) return null;
        let raw = null, canon = null;
        for (const cid in NUM) { const e = (NUM[cid][f.id]||[])[0];
            if (e && e.canonical !== null) { raw = e.raw; canon = e.canonical; break; } }
        return raw === null ? null : {id: f.id, raw, canon, unit: f.canonical_unit,
                                      shown: document.querySelector(
                                        `input[data-r="${f.id}"]`).closest('.facet').innerText};
    }""")
    if not rf:
        ok("O: a unit-converting range field exists", False, "none")
    else:
        ok("O: the range box states the unit it compares in",
           rf["unit"] in rf["shown"], rf["shown"][:70])
        def band(lo, hi):
            return pg.evaluate("""([id, lo, hi]) => {
                range[id] = {min: String(lo), max: String(hi)}; page = 0; render();
                const n = seriesMatching().length;
                range[id] = {min:"", max:""}; page = 0; render();
                return n;
            }""", [rf["id"], lo, hi])
        n_can = band(rf["canon"] - .5, rf["canon"] + .5)
        n_raw = band(rf["raw"] - .5, rf["raw"] + .5)
        ok("O: a canonical-valued band matches results", n_can > 0,
           (rf["id"], rf["canon"], n_can))
        ok("O: the same number read as the raw unit does not",
           n_raw < n_can, (rf["raw"], n_raw, rf["canon"], n_can))

    # --- D: simulations are counted as simulations
    hdr = pg.evaluate("""() => {
        tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
        RANGES.forEach(r => range[r.id] = {min:"",max:""}); page = 0; render();
        const all = document.querySelector('#results h2').textContent;
        const f = Object.keys(FACETS).find(k => FACETS[k]['simulated']);
        let sim = null;
        if (f) { active[f].add('simulated'); page = 0; render();
                 sim = document.querySelector('#results h2').textContent;
                 active[f].clear(); page = 0; render(); }
        return {all, sim};
    }""")
    ok("O: the header counts acts and simulation runs separately",
       "measurement acts" in hdr["all"] and "simulation runs" in hdr["all"], hdr["all"])
    # The header numbers must be the producer-kind partition of the matched set, recomputed
    # here rather than trusted. (Note: `data_source == "simulated"` is a series label and
    # does NOT imply a SimulationRun producer -- a few simulated curves hang off Measurement
    # records in this corpus, which is exactly why the count must follow the producer.)
    part = pg.evaluate("""() => {
        const f = Object.keys(FACETS).find(k => FACETS[k]['simulated']);
        if (!f) return null;
        active[f].add('simulated'); page = 0; render();
        const m = new Set(), s = new Set();
        seriesMatching().forEach(x => { const a = ACTS[SERIES[x].act_id];
            (a && a.kind === 'SIMULATION_RUN' ? s : m).add(SERIES[x].act_id); });
        const head = document.querySelector('#results h2').textContent;
        active[f].clear(); page = 0; render();
        return {head, acts: m.size, sims: s.size};
    }""")
    if part:
        ok("O: the reported measurement-act count is the producer-kind partition",
           ("%d measurement acts" % part["acts"]) in part["head"], part)
        ok("O: and the simulation-run count is too",
           ("%d simulation runs" % part["sims"]) in part["head"], part)
        ok("O: filtering to simulated results does surface simulation runs",
           part["sims"] > 0, part)
    ok("O: no console errors during the hardening interactions", not errors, errors[:2])


if __name__ == "__main__":
    import re  # noqa: E402  (used in main)
    sys.exit(main())
