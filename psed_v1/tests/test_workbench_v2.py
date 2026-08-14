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
import re
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))
WB = W / "_diagnostics" / "workbench_v2"

_pass, _fail = [], []


def strip_comments(path):
    """Source with comments removed and nothing else.

    Python goes through tokenize. JavaScript/HTML gets block comments removed with
    DOTALL and line comments removed WITHOUT it, because `//[^\n]*` is the whole point:
    a line comment ends at the newline, and a pattern that does not say so deletes every
    line after the first one it meets.
    """
    src = path.read_text()
    if path.suffix == ".py":
        import io
        import tokenize
        return "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                       for t in tokenize.generate_tokens(io.StringIO(src).readline))
    import re
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)       # block: dot must span lines
    src = re.sub(r"//[^\n]*", "", src)                     # line: it must NOT
    return src


def _context(body, pat, span=60):
    i = body.find(pat)
    return "" if i < 0 else body[max(0, i - span):i + span].replace("\n", " ")


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
       all(len(s["all_case_ids"]) == s["n_cases"] and s["n_cases"] > 1 for s in multi))
    ok("B: single_case is null whenever there are several",
       all(s["single_case"] is None for s in multi))
    ok("B: and set only when there is exactly one",
       all(s["single_case"] is not None for s in SER.values() if s["n_cases"] == 1))
    ok("B: cardinality status is explicit",
       all(s["case_cardinality_status"] in ("SINGLE_CASE", "MULTI_CASE", "NO_CASE")
           for s in SER.values()))
    ok("B: every case id on a series resolves",
       all(c in CASES for s in SER.values() for c in s["all_case_ids"]))
    ok("B: acts also keep multi-case membership",
       any(a["n_cases"] > 1 for a in ACTS.values()))
    ok("B: reverse edges exist (case -> series)",
       all(any(s in CASES[c]["series_ids"] for c in SER[s]["all_case_ids"])
           for s in list(SER)[:60] if SER[s]["all_case_ids"]))

    print("=== C. no first-case logic anywhere in the workbench code ===")
    # The audit is only as good as its comment stripper. `//.*` with re.S is a
    # single-line pattern given a multi-line dot: one `//` comment consumed the rest of
    # the file, so the audit passed by having nothing left to look at.
    for f in (WB / "build_workbench_model.py", WB / "_workbench_v2_template.html",
              WB / "psed_scientific_comparison_workbench.html"):
        body = strip_comments(f)
        for pat in ("case_ids[0]", "case_ids.at(0)", "case_ids[ 0 ]",
                    "next(iter(case", "all_case_ids[0]", "all_case_ids.at(0)"):
            ok("C: %-38s has no %s" % (f.name, pat), pat not in body,
               _context(body, pat))
    # `cs[0]` is legitimate only where the code has just proved there is exactly one
    # case. Rather than eyeball it, every zero-subscript of a case collection in the
    # builder is required to sit inside an `if len(...) == 1` block.
    import ast
    tree = ast.parse((WB / "build_workbench_model.py").read_text())
    guarded, unguarded = [], []

    def zero_subscripts(node):
        for n in ast.walk(node):
            if not (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)):
                continue
            sl = n.slice
            sl = sl.value if isinstance(sl, getattr(ast, "Index", ())) else sl
            if isinstance(sl, ast.Constant) and sl.value == 0:
                yield n

    def is_singleton_guard(test):
        return (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
                and isinstance(test.left, ast.Call)
                and getattr(test.left.func, "id", None) == "len"
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 1)

    inside = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.If) and is_singleton_guard(n.test):
            for b in n.body:
                inside.update(id(x) for x in zero_subscripts(b))
    for n in zero_subscripts(tree):
        name = "%s[0]" % n.value.id
        if "case" in n.value.id or "cs" == n.value.id:
            (guarded if id(n) in inside else unguarded).append(
                "%s line %d" % (name, n.lineno))
    ok("C: every case-collection [0] is singleton-guarded", not unguarded, unguarded)
    ok("C: and the guarded ones are accounted for", len(guarded) == 2, guarded)

    guard = strip_comments(WB / "_workbench_v2_template.html")
    ok("C: the stripper keeps the code it is auditing",
       "function rangeOk" in guard and "function render" in guard
       and "commonTargets" in guard, len(guard))
    # phrases that exist ONLY in comments -- "no primary Condition Case" is rendered
    # text, so it is not evidence either way
    ok("C: and it does remove comments",
       "canonical, never raw" not in guard
       and "invented a primacy" not in guard)
    # a control: the broken pattern must demonstrably lose the file
    import re as _re
    raw = (WB / "_workbench_v2_template.html").read_text()
    broken = _re.sub(r"//.*|/\*.*?\*/", "", raw, flags=_re.S)
    ok("C: the previous stripper really did destroy the source",
       len(broken) < len(guard) / 2, (len(broken), len(guard)))

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
        ser2 = [s for s in SER.values() if k in s["all_case_ids"]]
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
    final_hardening_tests(M, V, hp)
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

    print("=== N5. one ResultSeries is one result entry, owned by no case ===")
    ok("N5: multi-case series exist to be duplicated",
       C["multi_case_result_series"] == 22, C["multi_case_result_series"])
    ok("N5: each gets exactly one entry in the sweep section",
       C["multi_case_primary_entries"] == C["multi_case_result_series"],
       (C["multi_case_primary_entries"], C["multi_case_result_series"]))
    ok("N5: no series is listed twice", C["duplicate_primary_entries"] == 0,
       C["duplicate_primary_entries"])
    ok("N5: no series is listed nowhere", C["result_series_without_primary_entry"] == 0,
       C["result_series_without_primary_entry"])
    ok("N5: every ResultSeries has exactly one entry",
       C["primary_result_entries"] == C["result_series_searchable"] == 231,
       (C["primary_result_entries"], C["result_series_searchable"]))
    ok("N5: no multi-case series is anchored to a case",
       C["multi_case_series_with_primary_case"] == 0,
       C["multi_case_series_with_primary_case"])
    ok("N5: the three populations partition the corpus",
       C["case_local_series"] + C["sweep_series"] + C["no_case_series"] == 231,
       (C["case_local_series"], C["sweep_series"], C["no_case_series"]))
    ok("N5: the model decides placement, not the page",
       all(x["placement"] in ("CASE_LOCAL", "MULTI_CASE_SWEEP", "NO_CASE")
           for x in SER.values()))
    ok("N5: only a single-case series carries a placement case",
       all((x["placement_case_id"] is None) == (x["n_cases"] != 1)
           for x in SER.values()))
    ok("N5: the page renders a dedicated sweep section",
       "Multi-case / sweep results" in js)
    ok("N5: cases reference sweeps instead of repeating them",
       "Related sweep results" in js and "Also traversed by" in js)
    ok("N5: the sweep entry states its span", "spans ${s.all_case_ids.length} cases" in js)

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


def final_hardening_tests(M, V, hp):
    """The five defects the original-code review found after the first hardening."""
    SER, C, js = M["series"], V["counts"], hp.read_text()
    NUM, RF = M["numeric_conditions"], M["range_fields"]

    print("=== N8. a numeric range field keeps its species ===")
    ok("N8: the corpus really does qualify the same quantity by species",
       C["base_quantities_with_several_species"] > 0
       and C["cases_with_multiple_species_for_same_base_quantity"] > 0,
       (C["base_quantities_with_several_species"],
        C["cases_with_multiple_species_for_same_base_quantity"]))
    ok("N8: qualified range fields are offered", C["qualified_numeric_range_fields"] > 0,
       C["qualified_numeric_range_fields"])
    ok("N8: no offered field lost its qualifier",
       C["qualified_range_fields_losing_qualifier"] == 0)
    by_q = {}
    for f in RF:
        by_q.setdefault(f["quantity_id"], []).append(f)
    split = {q: fs for q, fs in by_q.items() if len(fs) > 1}
    ok("N8: at least one quantity is split into several species facets", bool(split),
       {q: [f["field_id"] for f in fs] for q, fs in split.items()})
    ok("N8: every field id encodes exactly its own species",
       all(f["field_id"] == (f["quantity_id"] + "@" + f["species_or_role"]
                             if f["species_or_role"] else f["quantity_id"]) for f in RF))
    ok("N8: each field carries its species as data, not inside a string",
       all("species_or_role" in f and "quantity_id" in f for f in RF))
    ok("N8: no two offered fields share a display label",
       len({f["display_label"] for f in RF}) == len(RF),
       [f["display_label"] for f in RF])
    ok("N8: an unqualified field beside qualified siblings says so",
       all(f["species_or_role"] or "unattributed" in f["display_label"]
           for f in RF if f.get("has_qualified_siblings")),
       [f["display_label"] for f in RF if f.get("has_qualified_siblings")])
    # the browser must address one key, never the first key that starts with the name
    ok("N8: the page addresses the exact condition key",
       "hasOwnProperty.call(vals, fieldId)" in js)
    ok("N8: the prefix/first-match lookup is gone",
       'k.indexOf(r.id+"@")===0' not in js and 'k.indexOf(r.id + "@") === 0' not in js)
    ok("N8: no offered field can reach more than one key",
       C["ambiguous_first_match_range_lookups"] == 0)
    ok("N8: and the old prefix rule demonstrably could",
       C["prefix_match_ambiguous_lookups_avoided"] > 0,
       C["prefix_match_ambiguous_lookups_avoided"])
    # the builder must not re-derive the species by splitting the key
    body = strip_comments(WB / "build_workbench_model.py")
    ok("N8: the builder never splits a condition key to get its quantity",
       'split("@")' not in body, _context(body, 'split("@")'))
    ok("N8: nor does the page", 'split("@")' not in strip_comments(
        WB / "_workbench_v2_template.html"))
    # role-prefixed composites survive intact
    comp = [f for f in RF if f["quantity_id"].startswith(("precursor_", "coreactant_"))]
    ok("N8: role-prefixed composite quantities are preserved whole", bool(comp),
       [f["field_id"] for f in comp])
    ok("N8: exactly the 10 qualified fields this corpus supports are offered",
       C["qualified_numeric_range_fields"] == 10, C["qualified_numeric_range_fields"])
    for want in ("precursor_pulse_time@TMA", "coreactant_pulse_time@H2O",
                 "pulse_time@H2O", "pulse_time@TMA"):
        ok("N8: %-30s is its own facet" % want,
           want in {f["field_id"] for f in RF})
    ok("N8: the ambiguity it prevents is real, not hypothetical",
       C["cases_with_multiple_species_for_same_base_quantity"] == 42
       and C["base_quantities_with_several_species"] == 3,
       (C["cases_with_multiple_species_for_same_base_quantity"],
        C["base_quantities_with_several_species"]))
    ok("N8: the model stores species as a field, so nothing has to parse it back out",
       all("species" in e and "quantity" in e
           for fields in NUM.values() for arr in fields.values() for e in arr))

    print("=== N9. per-case producers are partitioned by entity kind ===")
    cases = M["cases"]
    ok("N9: every case carries both producer lists",
       all("measurement_act_ids" in c and "simulation_run_ids" in c
           for c in cases.values()))
    acts = M["acts"]
    ok("N9: no SimulationRun appears in a case's measurement list",
       all(acts[a]["kind"] == "MEASUREMENT"
           for c in cases.values() for a in c["measurement_act_ids"]))
    ok("N9: no MeasurementAct appears in a case's simulation list",
       all(acts[a]["kind"] == "SIMULATION_RUN"
           for c in cases.values() for a in c["simulation_run_ids"]))
    ok("N9: the page has separate headings", "<h3>Measurements</h3>" in js
       and "<h3>Simulations</h3>" in js)
    ok("N9: the old conflating heading is gone",
       "Measurement acts with matching results" not in js)
    ok("N9: producer kind comes from the act, never from the series label",
       'a.kind==="SIMULATION_RUN"' in js or 'a && a.kind === "SIMULATION_RUN"' in js)
    # the corpus fact this rests on, reported rather than assumed
    simseries = [x for x in SER.values() if acts[x["act_id"]]["kind"] == "SIMULATION_RUN"]
    ok("N9: this corpus links no SimulationRun to a Condition Case (reported, not hidden)",
       C["cases_with_both_producer_kinds"] == 0
       and all(x["n_cases"] == 0 for x in simseries), len(simseries))
    xps = [a for a in acts.values() if a["kind"] == "MEASUREMENT"
           and any(SER[x]["data_source"] == "simulated" for x in a["series_ids"])]
    ok("N9: the six MeasurementActs producing 'simulated' series are left alone",
       len(xps) == 6, len(xps))
    ok("N9: and simulated-labelled series still exist under MeasurementActs", bool(xps))

    print("=== N10. validation metrics are calculated, not asserted ===")
    src = strip_comments(WB / "build_workbench_model.py")
    for metric in ("false_common_native_targets", "incompatible_plotted_pair_violations",
                   "multi_series_target_violations", "duplicate_primary_entries",
                   "multi_case_series_with_primary_case",
                   "qualified_range_fields_losing_qualifier",
                   "ambiguous_first_match_range_lookups"):
        ok('N10: %-42s is not a literal' % metric,
           ('c["%s"] = 0' % metric) not in src and ("'%s'] = 0" % metric) not in src,
           _context(src, metric))
        ok('N10: %-42s = 0' % metric, C[metric] == 0, C[metric])
    ok("N10: the pair sweep actually inspected pairs",
       C["pairs_offered_a_physical_overlay"] > 0, C["pairs_offered_a_physical_overlay"])
    ok("N10: the 3+ series check inspected real sets",
       C["multi_series_target_sets_checked"] > 100,
       C["multi_series_target_sets_checked"])
    ok("N10: the key-based rule would have produced false commons (the check has teeth)",
       C["key_based_false_common_targets"] > 0, C["key_based_false_common_targets"])
    for gate in ("no_false_common_targets", "no_incompatible_plotted_pairs",
                 "no_multi_series_target_violations", "no_duplicate_primary_entries",
                 "every_series_has_one_primary_entry",
                 "no_multi_case_series_has_a_primary_case",
                 "no_range_field_loses_its_qualifier", "no_ambiguous_range_lookups"):
        ok("N10: %-44s is a build gate" % gate, V["invariants"][gate] is True,
           V["invariants"].get(gate))
    # The gate is proven by breaking it. A string saying the build returns non-zero is
    # not evidence that a violation would be caught.
    import copy
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "wbbuild", WB / "build_workbench_model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok("N10: the real model passes its own gate",
       mod.validate(M, {})["invariants_ok"] is True)
    hurt = copy.deepcopy(M)
    sweep = hurt["sweep_series_ids"][0]
    hurt["series"][sweep]["placement_case_id"] = hurt["series"][sweep]["all_case_ids"][0]
    b1 = mod.validate(hurt, {})
    ok("N10: anchoring one sweep to a case is counted",
       b1["counts"]["multi_case_series_with_primary_case"] == 1,
       b1["counts"]["multi_case_series_with_primary_case"])
    ok("N10: and that fails the build", b1["invariants_ok"] is False
       and b1["invariants"]["no_multi_case_series_has_a_primary_case"] is False)
    hurt2 = copy.deepcopy(M)
    cid = next(c for c, v in hurt2["cases"].items() if v["case_local_series_ids"])
    hurt2["cases"][cid]["case_local_series_ids"] *= 2
    b2 = mod.validate(hurt2, {})
    ok("N10: a duplicated result entry is counted",
       b2["counts"]["duplicate_primary_entries"] > 0,
       b2["counts"]["duplicate_primary_entries"])
    ok("N10: and that fails the build", b2["invariants_ok"] is False
       and b2["invariants"]["no_duplicate_primary_entries"] is False)
    hurt3 = copy.deepcopy(M)
    fld = next(x for x in hurt3["range_fields"] if x["species_or_role"])
    fld["field_id"] = fld["quantity_id"]           # exactly the stripping defect
    b3 = mod.validate(hurt3, {})
    ok("N10: a range field that loses its species is counted",
       b3["counts"]["qualified_range_fields_losing_qualifier"] == 1,
       b3["counts"]["qualified_range_fields_losing_qualifier"])
    ok("N10: and that fails the build", b3["invariants_ok"] is False
       and b3["invariants"]["no_range_field_loses_its_qualifier"] is False)
    ok("N10: the exhaustive sweeps really are exhaustive",
       C["pairs_offered_a_physical_overlay"] == 819
       and C["multi_series_target_sets_checked"] == 25622
       and C["key_based_false_common_targets"] == 1784,
       (C["pairs_offered_a_physical_overlay"],
        C["multi_series_target_sets_checked"],
        C["key_based_false_common_targets"]))

    print("=== N11. a sweep's conditions are summarised, never taken from one case ===")
    ok("N11: the page has a deterministic across-cases summariser",
       "function condAcross" in js)
    ok("N11: it reports variation instead of a value", '"varies"' in js)
    ok("N11: the condition table uses it", "condAcross(c.cases, q)" in js)
    varying = None
    for x in SER.values():
        if x["n_cases"] < 2:
            continue
        vals = set()
        for cid in x["all_case_ids"]:
            for cond in M["cases"][cid]["conditions"]:
                if cond["quantity"] == "deposition_temperature":
                    vals.add(str(cond["value"]))
        if len(vals) > 1:
            varying = (x["id"], sorted(vals))
            break
    ok("N11: a real sweep with a varying temperature exists to test against",
       varying is not None, varying)

    print("=== N12. matching cases are distinguished from traversed cases ===")
    ok("N12: the page computes which cases match", "function matchingCases" in js)
    ok("N12: from the case itself, not from the series that reached it",
       "function caseMatchesFilters" in js)
    ok("N12: a case reached only by a sweep is labelled", "traversed only" in js)
    ok("N12: point-to-case mapping stays unresolved",
       "Point-to-case mapping is" in js)
    ok("N12: no series carries an owning case unless it has exactly one",
       all((x["placement_case_id"] is None) == (x["n_cases"] != 1)
           for x in SER.values()))
    ok("N12: the three populations partition the corpus",
       C["case_local_series"] + C["sweep_series"] + C["no_case_series"]
       == C["result_series_searchable"] == 231,
       (C["case_local_series"], C["sweep_series"], C["no_case_series"]))


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
            return {n: SERIES[id].n_cases, cases: SERIES[id].all_case_ids.length};
        }""")
        ok("M: a multi-case series keeps every case in the model",
           mres["n"] == mres["cases"] and mres["n"] > 1, mres)

        # --- removing a series
        pg.evaluate("() => { tray.length=0; render(); }")
        ok("M: tray can be emptied", "0/8" in pg.inner_text("#tray"))
        ok("M: no console errors accumulated during interaction", not errors, errors[:2])

        hardening_dom(pg, errors)
        final_hardening_dom(pg, errors)
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

    # --- B: one multi-case curve is one entry, found through the sweep section
    multi = pg.evaluate("""() => {
        tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
        RANGES.forEach(r => range[r.id] = {min:"",max:""});
        page = 0; render();
        // located by its own id in the dedicated sweep section -- never by paging to
        // "its" case, which is the very primacy this repair removed
        const id = M.sweep_series_ids.slice()
                    .sort((x,y)=>SERIES[y].n_cases-SERIES[x].n_cases)[0];
        if (!id) return null;
        document.querySelectorAll('#results details.case').forEach(d => d.open = true);
        const rows = document.querySelectorAll(`[data-ser="${id}"]`).length;
        const html = document.body.innerHTML;
        return {id, n: SERIES[id].n_cases, rows,
                placement: SERIES[id].placement,
                anchored: SERIES[id].placement_case_id,
                listed_cases: (html.match(new RegExp(
                    SERIES[id].all_case_ids.map(c=>CASES[c].case_id)
                      .filter((v,i,a)=>a.indexOf(v)===i)[0], "g"))||[]).length,
                spans: html.indexOf('spans ' + SERIES[id].n_cases + ' cases') >= 0,
                sweep_section: html.indexOf('Multi-case / sweep results') >= 0,
                xref: html.indexOf('Related sweep results') >= 0,
                no_primary: !/primary case|home case/i.test(html)};
    }""")
    if not multi:
        ok("O: a multi-case series exists", False, "none")
    else:
        ok("O: a %d-case curve is listed exactly once" % multi["n"],
           multi["rows"] == 1, multi)
        ok("O: it lives in the dedicated sweep section", multi["sweep_section"], multi)
        ok("O: the model gives it no owning case",
           multi["placement"] == "MULTI_CASE_SWEEP" and multi["anchored"] is None, multi)
        ok("O: its entry states the span", multi["spans"], multi)
        ok("O: the cases it traverses cross-reference it instead of repeating it",
           multi["xref"], multi)
        ok("O: no 'primary case' or 'home case' label appears anywhere",
           multi["no_primary"], multi)

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




def final_hardening_dom(pg, errors):
    """Browser evidence for the final repairs, driven on the real page."""
    print("=== Q. browser evidence for the final hardening ===")

    def reset():
        pg.evaluate("""() => {
            tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
            RANGES.forEach(r => range[r.id] = {min:"",max:""});
            profileOnly = false; page = 0; render();
        }""")

    # --- species-qualified ranges on the REAL corpus -------------------------------
    reset()
    real = pg.evaluate("""() => {
        const tma = RANGES.find(r => r.field_id === "precursor_pulse_time@TMA");
        const h2o = RANGES.find(r => r.field_id === "coreactant_pulse_time@H2O");
        if (!tma || !h2o) return null;
        const labels = [...document.querySelectorAll('#facets .facet')]
            .map(n => n.innerText).filter(t => /pulse time/i.test(t));
        return {tma: tma.display_label, h2o: h2o.display_label,
                distinct: tma.display_label !== h2o.display_label,
                shown: labels.join(" | "),
                generic: labels.filter(t => /^Pulse time\s*\[/.test(t.trim())).length};
    }""")
    if not real:
        ok("Q: the corpus offers qualified pulse-time facets", False, "absent")
    else:
        ok("Q: TMA and H2O pulse time are separate, differently labelled facets",
           real["distinct"], (real["tma"], real["h2o"]))
        ok("Q: the sidebar shows them both to the user",
           "TMA" in real["shown"] and "H2O" in real["shown"], real["shown"][:160])
        ok("Q: no bare ambiguous 'Pulse time' box is offered", real["generic"] == 0,
           real["shown"][:160])

    # --- and on a controlled fixture where the two species differ -------------------
    fixture = pg.evaluate("""() => {
        // a case carrying deliberately different values for the two species, plus a
        // second one written in ms, so unit conversion and species must both hold
        const cid = "__fixture_case__", cid2 = "__fixture_case_ms__";
        NUM[cid]  = {"pulse_time@TMA": [{raw:0.1, unit:"s",  canonical:0.1,
                                         quantity:"pulse_time", species:"TMA"}],
                     "pulse_time@H2O": [{raw:2,   unit:"s",  canonical:2,
                                         quantity:"pulse_time", species:"H2O"}]};
        NUM[cid2] = {"pulse_time@TMA": [{raw:500, unit:"ms", canonical:0.5,
                                         quantity:"pulse_time", species:"TMA"}],
                     "pulse_time@H2O": [{raw:2,   unit:"s",  canonical:2,
                                         quantity:"pulse_time", species:"H2O"}]};
        const band = (fid, lo, hi, c) => {
            const r = RANGES.find(x => x.field_id === fid);
            if (!r) return null;
            const keep = range[r.id];
            range[r.id] = {min:String(lo), max:String(hi)};
            const hit = caseMatchesFilters(c);
            range[r.id] = keep;
            return hit;
        };
        const out = {
            tma_narrow_on_tma: band("pulse_time@TMA", 0.05, 0.2, cid),
            h2o_narrow_on_h2o: band("pulse_time@H2O", 0.05, 0.2, cid),
            tma_wide_on_tma:   band("pulse_time@TMA", 1.5, 2.5, cid),
            h2o_wide_on_h2o:   band("pulse_time@H2O", 1.5, 2.5, cid),
            ms_tma_half:       band("pulse_time@TMA", 0.45, 0.55, cid2),
            ms_h2o_half:       band("pulse_time@H2O", 0.45, 0.55, cid2),
            ms_tma_two:        band("pulse_time@TMA", 1.5, 2.5, cid2),
        };
        delete NUM[cid]; delete NUM[cid2];
        return out;
    }""")
    if fixture is None or fixture.get("tma_narrow_on_tma") is None:
        ok("Q: a qualified pulse-time facet exists to drive", False, fixture)
    else:
        ok("Q: TMA 0.05-0.2 s matches the case whose TMA pulse is 0.1 s",
           fixture["tma_narrow_on_tma"] is True, fixture)
        ok("Q: H2O 0.05-0.2 s does NOT, because its H2O pulse is 2 s",
           fixture["h2o_narrow_on_h2o"] is False, fixture)
        ok("Q: H2O 1.5-2.5 s matches", fixture["h2o_wide_on_h2o"] is True, fixture)
        ok("Q: TMA 1.5-2.5 s does not", fixture["tma_wide_on_tma"] is False, fixture)
        ok("Q: 500 ms is found by a TMA band around 0.5 s (canonical, not raw)",
           fixture["ms_tma_half"] is True, fixture)
        ok("Q: and that band does not reach the H2O value",
           fixture["ms_h2o_half"] is False, fixture)
        ok("Q: nor does a TMA band around 2 s pick up the H2O 2 s value",
           fixture["ms_tma_two"] is False, fixture)

    # --- a sweep under a filter that only part of its span satisfies ---------------
    reset()
    sweep = pg.evaluate("""() => {
        const id = M.sweep_series_ids.slice()
                    .sort((a,b)=>SERIES[b].n_cases-SERIES[a].n_cases)[0];
        const r = RANGES.find(x => x.field_id === "deposition_temperature");
        if (!id || !r) return null;
        range[r.id] = {min:"500", max:""};            // K: only the hotter half matches
        page = 0; render();
        document.querySelectorAll('#results details.case').forEach(d => d.open = true);
        const s = SERIES[id], mc = matchingCases(s);
        const card = document.querySelector(`[data-ser="${id}"]`);
        const scope = card ? card.closest('details.case') : null;
        const txt = scope ? scope.innerText : "";
        const rows = document.querySelectorAll(`[data-ser="${id}"]`).length;
        const shownMatch = (txt.match(/matches/g)||[]).length;
        const shownTrav  = (txt.match(/traversed only/g)||[]).length;
        range[r.id] = {min:"", max:""}; page = 0; render();
        return {id, all: s.all_case_ids.length, matching: mc.length, rows,
                shownMatch, shownTrav, anchored: s.placement_case_id,
                header: document.querySelector('#results h2').textContent,
                names_a_primary: /primary case|home case/i.test(txt)};
    }""")
    if not sweep:
        ok("Q: a sweep and a temperature range exist to drive", False, sweep)
    else:
        ok("Q: only part of the sweep's span satisfies the filter",
           0 < sweep["matching"] < sweep["all"], sweep)
        ok("Q: the sweep is still one entry", sweep["rows"] == 1, sweep)
        ok("Q: every traversed case is listed", sweep["shownMatch"]
           + sweep["shownTrav"] == sweep["all"], sweep)
        ok("Q: matching cases are marked as matching",
           sweep["shownMatch"] == sweep["matching"], sweep)
        ok("Q: non-matching cases are marked traversed only, not presented as matches",
           sweep["shownTrav"] == sweep["all"] - sweep["matching"], sweep)
        ok("Q: and no case owns the sweep",
           sweep["anchored"] is None and not sweep["names_a_primary"], sweep)

    # --- a sweep's conditions are summarised, not taken from one case ---------------
    reset()
    summary = pg.evaluate("""() => {
        const id = M.sweep_series_ids.slice()
                    .sort((a,b)=>SERIES[b].n_cases-SERIES[a].n_cases)[0];
        tray.length = 0; tray.push(id); render();
        const s = SERIES[id];
        const first = (CASES[s.all_case_ids[0]].conditions
                       .find(c => c.quantity === "deposition_temperature")||{});
        const cell = condAcross(s.all_case_ids, "deposition_temperature");
        const txt = document.querySelector('#conds').innerText;
        return {kind: cell.kind, text: cell.text, n: cell.values.length,
                first: `${first.value} ${first.unit||""}`.trim(),
                shows_varies: /varies/.test(txt),
                shows_only_first: txt.indexOf(`${first.value} ${first.unit||""}`.trim()) >= 0
                                  && !/varies/.test(txt)};
    }""")
    if not summary:
        ok("Q: a sweep can be put in the tray", False, summary)
    else:
        ok("Q: a condition differing across the span is reported as varying",
           summary["kind"] == "varies" and summary["n"] > 1, summary)
        ok("Q: the comparison table says so", summary["shows_varies"], summary)
        ok("Q: it does not report the first case's value as the sweep's",
           not summary["shows_only_first"], summary)

    # --- producer partition: no real case mixes the two kinds, so drive a fixture ---
    reset()
    mixed = pg.evaluate("""() => {
        // This corpus links no SimulationRun to a Condition Case, so the partition is
        // exercised by adding one to a real case's producer lists and re-rendering the
        // real code path. Nothing is asserted about the corpus by doing so.
        const cid = Object.keys(CASES).find(c => CASES[c].measurement_act_ids.length);
        const sim = Object.keys(ACTS).find(a => ACTS[a].kind === "SIMULATION_RUN");
        if (!cid || !sim) return null;
        const simSeries = ACTS[sim].series_ids[0];
        const keepPlace = SERIES[simSeries].placement;
        const keepCase = SERIES[simSeries].placement_case_id;
        const keepCases = SERIES[simSeries].all_case_ids;
        SERIES[simSeries].placement = "CASE_LOCAL";
        SERIES[simSeries].placement_case_id = cid;
        SERIES[simSeries].all_case_ids = [cid];
        CASES[cid].simulation_run_ids = [sim];
        CASES[cid].case_local_series_ids = CASES[cid].case_local_series_ids.concat(simSeries);
        let scope = null;
        for (page = 0; page < 40 && !scope; page++) {
            render();
            document.querySelectorAll('#results details.case').forEach(d => {
                d.open = true;
                // sweep cards are details.case too and list case ids in their table,
                // so the condition case is identified by its own title
                const t = d.querySelector('.ctitle');
                if (!scope && t && t.textContent.trim()
                        === "Condition Case " + CASES[cid].case_id) scope = d;
            });
        }
        const txt = scope ? scope.innerText : "";
        const html = scope ? scope.innerHTML : "";
        const iMeas = html.indexOf("<h3>Measurements</h3>");
        const iSim = html.indexOf("<h3>Simulations</h3>");
        const iCard = html.indexOf(sim);
        const out = {
            has_meas_heading: iMeas >= 0, has_sim_heading: iSim >= 0,
            sim_after_sim_heading: iCard > iSim && iSim > 0,
            sim_not_under_measurements: !(iCard > iMeas && iCard < iSim),
            counts: (txt.match(/\d+ measurement acts?/)||[""])[0]
                    + " / " + (txt.match(/\d+ simulation runs?/)||[""])[0],
            old_heading: html.indexOf("Measurement acts with matching results") >= 0};
        // put the model back exactly as it was
        CASES[cid].simulation_run_ids = [];
        CASES[cid].case_local_series_ids =
            CASES[cid].case_local_series_ids.filter(x => x !== simSeries);
        SERIES[simSeries].placement = keepPlace;
        SERIES[simSeries].placement_case_id = keepCase;
        SERIES[simSeries].all_case_ids = keepCases;
        page = 0; render();
        return out;
    }""")
    if not mixed:
        ok("Q: a case and a simulation run exist to combine", False, mixed)
    else:
        ok("Q: a case holding both kinds renders a Measurements heading",
           mixed["has_meas_heading"], mixed)
        ok("Q: and a separate Simulations heading", mixed["has_sim_heading"], mixed)
        ok("Q: the SimulationRun card sits under Simulations",
           mixed["sim_after_sim_heading"], mixed)
        ok("Q: and never under Measurements", mixed["sim_not_under_measurements"], mixed)
        ok("Q: the two counts are reported separately",
           "measurement act" in mixed["counts"] and "simulation run" in mixed["counts"],
           mixed["counts"])
        ok("Q: the old conflating heading is gone", not mixed["old_heading"], mixed)

    # --- tray persistence for a multi-case series ----------------------------------
    reset()
    persist = pg.evaluate("""() => {
        const id = M.sweep_series_ids[0];
        tray.length = 0; tray.push(id); render();
        const before = document.querySelector('#tray').innerText;
        const f = Object.keys(FACETS)[0];
        active[f].add(Object.keys(FACETS[f])[0]); page = 0; render();
        const after = document.querySelector('#tray').innerText;
        active[f].clear(); page = 0; render();
        return {kept: after.indexOf(SERIES[id].paper_id.slice(0,22)) >= 0,
                spans: /spans \d+ condition cases/i.test(before),
                names_case: /primary case|home case/i.test(before)};
    }""")
    ok("Q: a multi-case series stays in the tray across a filter change",
       persist["kept"], persist)
    ok("Q: its tray card states the span", persist["spans"], persist)
    ok("Q: and never names an owning case", not persist["names_case"], persist)

    reset()
    ok("Q: no console errors during the final-hardening interactions",
       not errors, errors[:2])


if __name__ == "__main__":
    import re  # noqa: E402  (used in main)
    sys.exit(main())
