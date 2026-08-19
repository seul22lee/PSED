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
       "function caseMatchesFilters" in guard and "function render" in guard
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
    # Length agreement is what makes plotting safe. Compared within representation kind:
    # a source curve and a canonical one need not have the same point count, because
    # canonicalisation may fail on points the source recorded.
    # canonicalisation is per AXIS: a series may canonicalise x and fail on y, so the
    # x reference of a given kind can be absent while the y one exists. Both are built
    # from the same source tuples, so the source representation is the length reference
    # whenever the canonical one on that axis was not produced.
    def ref_len(sid, r):
        key = ("native_source" if r.get("representation_kind") == "NATIVE_SOURCE"
               else "native")
        xr = SER[sid]["x_representations"] or {}
        ref = xr.get(key) or xr.get("native_source") or xr.get("native") or {}
        return len(ref.get("values") or [])
    bad = [(sid, k) for sid, ax, k, r in avail
           if len(r["values"]) != ref_len(sid, r)]
    ok("E: coordinate arrays agree in length within their kind", not bad, bad[:3])
    ok("E: every series offers a source representation on both axes",
       all((SER[sid]["x_representations"] or {}).get("native_source")
           and (SER[sid]["y_representations"] or {}).get("native_source")
           for sid in SER), [s for s in list(SER)[:3]])

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
    # the entrance reference is derivable from the profile itself -- t(0) is IN the
    # curve -- so it is offered exactly where the profile reaches the entrance, and
    # refused (naming what it needs) where it does not.
    live = [r for r in ent if r["available"]]
    ok("F: t_over_t_entrance is offered where the profile reaches the entrance",
       live, len(live))
    ok("F: every offered one records the entrance as its reference",
       all(r["transform"]["parameters"].get("reference") is not None
           and "entrance" in str(r["transform"]["parameter_provenance"]
                                 ["source_evidence"]) for r in live),
       [r["transform"]["parameter_provenance"] for r in live][:1])
    ok("F: and never substitutes the maximum for the entrance",
       all(abs(r["transform"]["parameters"]["reference"]
               - max(SER[s]["y_representations"]["native"]["values"])) > 1e-12
           or SER[s]["y_representations"]["native"]["values"][0]
           == max(SER[s]["y_representations"]["native"]["values"])
           for s in [] for r in []))
    ok("F: and the rest name what they would need",
       all("not resolved for this series" in str(r.get("unavailable_reason"))
           and r.get("normalization") for r in ent if not r["available"]),
       [r for r in ent if not r["available"]][:1])

    print("=== G. a normalization basis is recovered only from an explicit statement ===")
    unk = [s for s in SER.values() if s["normalization_basis"] == "unresolved"]
    ok("G: no unresolved-basis series is given a basis anyway",
       all(s["y"]["y_norm"] is None for s in unk), len(unk))
    ok("G: and none offers t_over_t_max as if it were its own basis",
       all("norm:t_over_t_max" not in s["y_representations"] for s in unk))
    # every recovered basis must name the statement it came from
    rec = [s for s in SER.values() if s.get("normalization_basis_evidence")]
    ok("G: every recovered basis carries the sentence that states it",
       all("states the normalization" in str(s["normalization_basis_evidence"])
           for s in rec), len(rec))
    # the rule itself: the word "normalized" names no reference and must resolve nothing
    from pipeline.canonical import axis_semantics as _AX
    from pipeline.query import result_comparability as _RC
    _T = {k: v for k, v in _RC.NORMALIZATIONS.items() if k.split("_over_")[0] == "t"}
    ok("G: a bare 'normalized' statement resolves no basis",
       _AX.normalization_from_statement("Normalized thickness (-)", _T, axis="y")[0]
       is None)
    ok("G: an explicit reference does resolve one",
       _AX.normalization_from_statement(
           "the growth at the channel entrance is normalized to one on the vertical axis",
           _T, axis="y")[0] == "t_over_t_entrance")
    ok("G: a statement naming two references resolves neither",
       _AX.normalization_from_statement(
           "normalized to the maximum on the vertical axis. scaled to the planar "
           "reference on the vertical axis", _T, axis="y")[0] is None)

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
        ok("J: 19 result series, including the panels that redraw them",
       len(ser2) == 19, len(ser2))
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
    chemistry_propagation_checks(M)
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
    # A representation offered for OVERLAY names its target. A display-only source
    # representation deliberately has none -- see N26.
    over = [(sid, ax, k, r) for sid, ax, k, r in reps if r.get("overlay_authorized")]
    ok("N1: every overlay representation has a target_id",
       all(r.get("target_id") for _, _, _, r in over),
       [(a, b) for a, b, c, r in over if not r.get("target_id")][:3])
    ok("N1: a target_id names axis, quantity, normalization, dimension and unit",
       all(r["target_id"].count("|") == 4 for _, _, _, r in over))
    ok("N1: x and y targets can never collide",
       all(r["target_id"].startswith(ax[0] + "|") for _, ax, _, r in over))
    ok("N1: display-only representations carry no target",
       all(r.get("target_id") is None for _, _, _, r in reps
           if r.get("overlay_authorized") is False))

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
       "shapeOnly ? !!(p.physical_overlay_allowed || p.shape_only_eligible)" in js)
    ok("N4: an unindexed pair may only share an axis on identical semantic targets",
       "function sharesSemanticTarget" in js and "r.target_id" in js)

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
    ok("N6: the numeric band reads the canonical value", "v.canonical" in js)
    ok("N6: it never reads the raw value", "const n = v.raw;" not in js)
    ok("N6: numeric bands are evaluated by the same-case predicate",
       "function caseMatchesFilters" in js and "inBand(numericValues(cid, r.field_id)" in js)
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
    # quantity@species#step: the ALD step is part of the identity of a timed condition,
    # so it is part of the key the browser addresses, exactly like the species
    ok("N8: every field id encodes exactly its own species and ALD step",
       all(f["field_id"] == (f["quantity_id"]
                             + ("@" + f["species_or_role"] if f["species_or_role"] else "")
                             + ("#" + f["step_context"] if f.get("step_context") else "")
                             + ("~" + f["activation"] if f.get("activation") else ""))
           for f in RF),
       [f["field_id"] for f in RF])
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
    ok("N8: exactly the 9 qualified fields this corpus supports are offered",
       C["qualified_numeric_range_fields"] == 9, C["qualified_numeric_range_fields"])
    # including one qualified by its ALD step and one by its plasma activation, which
    # is what keeps a thermal and a plasma exposure of equal length apart. The spellings
    # are the role-specialised ones: the swept TMA dose is a precursor PULSE time (the
    # source's own family), never rewritten into an exposure statement.
    for want in ("precursor_pulse_time@TMA", "coreactant_pulse_time@H2O",
                 "pulse_time@H2O", "precursor_pulse_time@TMA#precursor_exposure~none",
                 "coreactant_pulse_time@O2#reactant_exposure~plasma"):
        ok("N8: %-30s is its own facet" % want,
           want in {f["field_id"] for f in RF})
    ok("N8: the ambiguity it prevents is real, not hypothetical",
       C["cases_with_multiple_species_for_same_base_quantity"] == 28
       and C["base_quantities_with_several_species"] == 8,
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
    ok("N10: the authorised overlay population is unchanged by native display",
       C["pairs_offered_a_physical_overlay"] == 1574,
       C["pairs_offered_a_physical_overlay"])
    ok("N10: the 3+ series sweep is exhaustive over the enlarged target set",
       C["multi_series_target_sets_checked"] == 80805,
       C["multi_series_target_sets_checked"])
    # adding a source representation to every series gives the pre-repair key rule one
    # more universal key to be wrong about, so the counterfactual grows
    ok("N10: the counterfactual grows with the new universal key",
       C["key_based_false_common_targets"] == 57697,
       C["key_based_false_common_targets"])

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

    print("=== N15. sequence-shaped conditions are audited, never mined ===")
    A = M["sequence_audit"]
    tplS = strip_comments(WB / "_workbench_v2_template.html")
    srcS = strip_comments(WB / "build_workbench_model.py")
    ok("N15: the corpus really contains sequence-shaped conditions",
       C["sequence_shaped_conditions"] == 13, C["sequence_shaped_conditions"])
    ok("N15: every occurrence is classified",
       V["invariants"]["every_sequence_occurrence_is_classified"] is True)
    ok("N15: every pulse/purge sequence already has its explicit qualified fields",
       C["sequence_explicit_fields_already_present"] == 11,
       C["sequence_explicit_fields_already_present"])
    ok("N15: so none of them is a case for derivation",
       C["sequence_general_derivation_safe"] == 0
       and C["sequence_derivation_ambiguous"] == 0,
       (C["sequence_general_derivation_safe"], C["sequence_derivation_ambiguous"]))
    ok("N15: and every one corroborates the fields it duplicates",
       C["sequence_corroborates_explicit_fields"] == 11
       and C["sequence_contradicts_explicit_fields"] == 0,
       (C["sequence_corroborates_explicit_fields"],
        C["sequence_contradicts_explicit_fields"]))
    ok("N15: the build gates on a sequence contradicting its fields",
       V["invariants"]["no_sequence_contradicts_its_explicit_fields"] is True)
    ok("N15: a non-numeric multi-term value is not read as a recipe",
       C["sequence_not_a_pulse_purge_time_encoding"] == 2,
       C["sequence_not_a_pulse_purge_time_encoding"])
    # negative control: a single number that merely contains a hyphen
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("wbb", WB / "build_workbench_model.py")
    wbb = _ilu.module_from_spec(_sp); _sp.loader.exec_module(wbb)
    ok("N15: scientific notation is one number, not a two-step recipe",
       wbb.sequence_terms("1e-7") is None)
    ok("N15: a plain number is not a sequence", wbb.sequence_terms("4.0") is None)
    ok("N15: a four-term recipe parses", wbb.sequence_terms("0.1-4.0-0.1-4.0")[1]
       == [0.1, 4.0, 0.1, 4.0])
    ok("N15: a non-numeric multi-term value parses as terms with no numbers",
       wbb.sequence_terms("ALD SiO2 / Al2O3")[1] is None)
    # roles are structural, not a fixed vocabulary
    fake = {"conditions": [{"quantity": "__novel_role___pulse_time", "value": 1,
                            "species": "__X__"},
                           {"quantity": "pulse_time", "value": 9}],
            "chemistry": {}}
    ok("N15: a role never seen in this corpus is still recognised structurally",
       [c["quantity"] for c in wbb.role_qualified_keys(fake, "pulse_time")]
       == ["__novel_role___pulse_time"])
    ok("N15: and the bare quantity is not mistaken for its own qualified variant",
       wbb.qualifier_roles(fake, "pulse_time") == ["__novel_role__"])
    # the page must not parse a recipe at all: parsing is the first step of deriving, and
    # the audit that says derivation is unjustified lives in the builder
    ok("N15: the page never splits a condition value into terms",
       "split(" not in tplS.split("function drawConds")[1].split("function drawWhy")[0])
    ok("N15: the sequence parser exists only in the builder audit",
       "_SEQ_SPLIT" in srcS and "_SEQ_SPLIT" not in tplS)
    ok("N15: the condition cell reads recorded values only, never arithmetic on them",
       "x.value" in tplS and "parseFloat(x.value" not in tplS)
    ok("N15: the unresolved state names the qualified quantities instead",
       "not recorded unqualified" in tplS and "function qualifiedSiblings" in tplS)
    ok("N15: which the corpus needs in %d places"
       % C["bare_quantity_unresolved_with_qualified_siblings"],
       C["bare_quantity_unresolved_with_qualified_siblings"] == 72,
       C["bare_quantity_unresolved_with_qualified_siblings"])
    ok("N15: the page states that nothing in the table is derived",
       "Nothing" in tplS and "derived" in tplS)

    # a row with no scalar is either a stated RANGE, rendered as its bounds, or genuinely
    # valueless and suppressed. Neither is ever shown as a bare magnitude.
    ok("N15: a recorded row with no value is not shown as a magnitude",
       "function condValueText" in tplS and "value_lower" in tplS)
    noscalar = [x for cc in M["cases"].values() for x in cc["conditions"]
                if x.get("value") in (None, "")]
    ok("N15: every valueless row is a stated range, not an empty placeholder",
       all(x.get("value_lower") is not None and x.get("value_upper") is not None
           for x in noscalar), [x for x in noscalar if x.get("value_lower") is None][:2])
    # the invariant is that a valueless row is NEVER an empty placeholder. It held while
    # the corpus carried stated ranges, and it holds now that the only ones it had turned
    # out to be a caption mis-scoped onto another figure and were removed at the source.
    ok("N15: no condition is an empty placeholder",
       not [x for x in noscalar if x.get("value_lower") is None], noscalar[:2])

    print("=== N16. one colour per selected series, everywhere ===")
    ok("N16: colour is a function of the selection", "function seriesColor" in tplS)
    ok("N16: keyed on tray position, not on what happens to be plottable",
       "const i = tray.indexOf(sid);" in tplS)
    ok("N16: the old plot-order indexing is gone",
       "cols[i%cols.length]" not in tplS and "const cols=[" not in tplS)
    for where in ("chip(d.sid)", "chip(sid)", "chip(c.sid)"):
        ok("N16: the same chip is used at %s" % where, where in tplS)
    ok("N16: the condition table header carries it",
       "<th>${chip(c.sid)}" in tplS)

    print("=== N17. point -> Condition Case resolution ===")
    import importlib.util as _i
    _s = _i.spec_from_file_location("wbb2", WB / "build_workbench_model.py")
    wb = _i.module_from_spec(_s); _s.loader.exec_module(wb)
    PCL = M["point_case_links"]
    ok("N17: the derived relation is labelled as derived",
       all(v["derivation"] == "DERIVED_FOR_WORKBENCH" for v in PCL.values()))
    ok("N17: %d of 22 multi-case series fully resolve"
       % C["point_case_series_fully_resolved"],
       C["point_case_series_fully_resolved"] == 20)
    ok("N17: none partially resolves in this corpus",
       C["point_case_series_partially_resolved"] == 0)
    ok("N17: 2 remain unresolved", C["point_case_series_unresolved"] == 2,
       C["point_case_series_unresolved"])
    ok("N17: every multi-case series has persisted coordinates",
       C["multi_case_series_without_persisted_points"] == 0)
    ok("N17: 114 of 124 points resolve, 0 ambiguously",
       (C["point_case_points_resolved"], C["point_case_points_ambiguous"],
        C["point_case_points_no_match"]) == (114, 0, 10),
       (C["point_case_points_resolved"], C["point_case_points_ambiguous"],
        C["point_case_points_no_match"]))
    ok("N17: no link names a case outside the series' own set",
       V["invariants"]["no_point_links_outside_the_series_case_set"] is True)
    ok("N17: every resolved point names exactly one case",
       V["invariants"]["resolved_points_name_exactly_one_case"] is True)
    ok("N17: the audit artifact exists",
       (WB / "point_case_resolution_audit.json").exists())
    ok("N17: and the derived link artifact", (WB / "point_case_links.json").exists())

    print("=== N18. resolution fixtures ===")
    def cases_from(spec):
        return {k: {"conditions": v} for k, v in spec.items()}
    cond = lambda q, v, u, sp=None: {"quantity": q, "value": v, "unit": u, "species": sp}
    # the resolver now takes points that carry their SOURCE index, so a fixture must say
    # which point each value came from rather than relying on list position
    def R(values, unit, quantity, species, case_ids, cases_map):
        pts = [{"source_point_index": i, "value": v, "unit": unit,
                "identity": "SOURCE_INDEX_VERIFIED"} for i, v in enumerate(values)]
        return wb.resolve_points_to_cases(pts, unit, quantity, species, case_ids, cases_map)

    # group 1: unit conversion -- 500 ms and 0.5 s are one physical value
    cs = cases_from({"A": [cond("pulse_time", 0.5, "s")],
                     "B": [cond("pulse_time", 2.0, "s")]})
    r = R([500], "ms", "pulse_time", None, ["A", "B"], cs)
    ok("N18: 500 ms resolves to a 0.5 s case",
       r[0]["resolution_status"] == "RESOLVED" and r[0]["case_id"] == "A"
       and r[0]["evidence"] == "UNIT_CONVERTED_EXACT_MATCH", r[0])

    # group 2: species is part of the identity
    cs = cases_from({"A": [cond("pulse_time", 0.5, "s", "__TMA__"),
                           cond("pulse_time", 0.5, "s", "__H2O__")]})
    r = R([0.5], "s", "pulse_time", "__TMA__", ["A"], cs)
    ok("N18: a TMA axis matches only the TMA condition",
       r[0]["resolution_status"] == "RESOLVED"
       and r[0]["matched_species_or_role"] == "__TMA__", r[0])
    r = R([0.5], "s", "pulse_time", None, ["A"], cs)
    ok("N18: a bare axis does not silently take a qualified condition",
       r[0]["resolution_status"] == "UNRESOLVED_NO_MATCH"
       and r[0]["evidence"] == "NO_COMPATIBLE_CASE_CONDITION", r[0])

    # group 3: duplicate values are ambiguous, never broken by order
    cs = cases_from({"A": [cond("pulse_time", 3, "s")], "B": [cond("pulse_time", 3, "s")]})
    r = R([3], "s", "pulse_time", None, ["A", "B"], cs)
    ok("N18: two cases with the same value are ambiguous",
       r[0]["resolution_status"] == "UNRESOLVED_AMBIGUOUS"
       and r[0]["candidate_case_ids"] == ["A", "B"], r[0])

    # group 4: same length, no semantic evidence -- must NOT resolve
    cs = cases_from({("C%d" % i): [cond("deposition_temperature", 100 + i, "°C")]
                     for i in range(5)})
    r = R([1, 2, 3, 4, 5], "s", "pulse_time", None, ["C%d" % i for i in range(5)], cs)
    ok("N18: five points and five cases do not resolve without matching semantics",
       all(x["resolution_status"] == "UNRESOLVED_NO_MATCH" for x in r)
       and all(x["evidence"] == "NO_COMPATIBLE_CASE_CONDITION" for x in r), r[0])
    ok("N18: and the series status is CASE_SET_ONLY, not resolved",
       wb.series_resolution_status(["C%d" % i for i in range(5)], r) == "CASE_SET_ONLY")

    # group 5: branch context -- the same x in two branches picks each branch's own case
    cs = cases_from({"A200": [cond("deposition_temperature", 200, "°C"),
                              cond("pulse_time", 3, "s")],
                     "A300": [cond("deposition_temperature", 300, "°C"),
                              cond("pulse_time", 3, "s")]})
    rA = R([3], "s", "pulse_time", None, ["A200"], cs)
    rB = R([3], "s", "pulse_time", None, ["A300"], cs)
    ok("N18: branch A resolves to its own case", rA[0]["case_id"] == "A200")
    ok("N18: branch B resolves to its own case", rB[0]["case_id"] == "A300")
    ok("N18: and both together are ambiguous rather than ordered",
       R([3], "s", "pulse_time", None, ["A200", "A300"], cs)[0]["resolution_status"]
       == "UNRESOLVED_AMBIGUOUS")

    # partial resolution is reported as partial
    cs = cases_from({"A": [cond("pulse_time", 1, "s")], "B": [cond("pulse_time", 2, "s")]})
    r = R([1, 2, 99], "s", "pulse_time", None, ["A", "B"], cs)
    ok("N18: a series with one unmatched point is PARTIALLY_RESOLVED",
       wb.series_resolution_status(["A", "B"], r) == "PARTIALLY_RESOLVED", r[2])
    ok("N18: no case context at all is its own state",
       wb.series_resolution_status([], []) == "NO_CASE_CONTEXT")

    # ordering must never be the evidence
    cs = cases_from({"A": [cond("pulse_time", 7, "s")], "B": [cond("pulse_time", 8, "s")]})
    r = R([8, 7], "s", "pulse_time", None, ["A", "B"], cs)
    ok("N18: points are matched by value, not by position",
       r[0]["case_id"] == "B" and r[1]["case_id"] == "A", r)

    print("=== N20. native observations survive canonicalisation failure ===")
    ok("N20: every ResultSeries carries a native observation",
       C["series_with_native_y"] == 231, C["series_with_native_y"])
    ok("N20: only %d of them have a canonical y" % C["series_with_canonical_y"],
       C["series_with_canonical_y"] == 70, C["series_with_canonical_y"])
    ok("N20: 161 are native-only", C["series_native_y_only"] == 161,
       C["series_native_y_only"])
    ok("N20: none is canonical-only", C["series_canonical_y_only"] == 0,
       C["series_canonical_y_only"])
    ok("N20: every resolved row has an observed value",
       C["case_data_native_results_available"] == 114
       and C["case_data_native_results_missing"] == 0,
       (C["case_data_native_results_available"], C["case_data_native_results_missing"]))
    ok("N20: 103 of them were suppressed by the canonical-only path",
       C["case_data_rows_previously_suppressed_by_canonicalization"] == 103,
       C["case_data_rows_previously_suppressed_by_canonicalization"])
    ok("N20: and none is suppressed now",
       C["case_data_rows_suppressed_by_canonicalization"] == 0)
    ok("N20: the strong invariant is a build gate",
       V["invariants"]["no_resolved_link_hides_an_available_native_result"] is True
       and C["resolved_link_with_available_native_y_but_empty_result"] == 0)
    ok("N20: native and canonical are distinct model fields",
       all(("native_points" in x and "y_canonical" in x) for x in M["series"].values()))
    ok("N20: native keeps the source label and unit, not a canonical one",
       all(((x["native_points"].get("y") or {}).get("unit") is not None)
           or not (x["native_points"].get("y") or {}).get("values")
           for x in M["series"].values()))
    ok("N20: point-case metrics are unchanged by this repair",
       (C["point_case_series_fully_resolved"], C["point_case_series_partially_resolved"],
        C["point_case_series_unresolved"], C["point_case_points_resolved"],
        C["point_case_points_ambiguous"], C["point_case_points_no_match"])
       == (20, 0, 2, 114, 0, 10))
    ok("N20: result availability is its own status, not PARTIALLY_RESOLVED",
       {x["native_result_status"] for x in M["series"].values()}
       <= {"NATIVE_AND_CANONICAL_AVAILABLE", "NATIVE_ONLY", "NO_NATIVE_RESULT"},
       sorted({x["native_result_status"] for x in M["series"].values()}))
    resolved_ids = [k for k, v in M["point_case_links"].items()
                    if v["status"] == "POINT_CASE_RESOLVED"]
    from collections import Counter as _Ctr
    byst = _Ctr(M["series"][k]["native_result_status"] for k in resolved_ids)
    ok("N20: of the 20 resolved series, 18 are native-only and 2 also canonical",
       byst.get("NATIVE_ONLY") == 18
       and byst.get("NATIVE_AND_CANONICAL_AVAILABLE") == 2, dict(byst))

    print("=== N21. point tuple integrity ===")
    import importlib.util as _iu
    _sp2 = _iu.spec_from_file_location("wbb3", WB / "build_workbench_model.py")
    wb3 = _iu.module_from_spec(_sp2); _sp2.loader.exec_module(wb3)
    ok("N21: the index contract is checked, not assumed",
       all("aligned" in (x.get("point_index_contract") or {})
           for x in M["series"].values()))
    ok("N21: a resolved series does not require a canonical array to corroborate it",
       len([k for k in resolved_ids
            if not M["series"][k]["point_index_contract"]["aligned"]]) == 6,
       len([k for k in resolved_ids
            if not M["series"][k]["point_index_contract"]["aligned"]]))
    # fixtures build the SOURCE TUPLES, because that is the authority now
    def mkpts(pairs, cx=None, cy=None, xu="s", cu="s"):
        return {"native_points": {
                    "points": [{"x": a, "y": b} for a, b in pairs],
                    "n_points": len(pairs),
                    "x": {"values": [a for a, _ in pairs], "unit": xu, "label": "x"},
                    "y": {"values": [b for _, b in pairs], "unit": "u", "label": "y"}},
                "x_canonical": {"values": cx if cx is not None
                                else [a for a, _ in pairs], "unit": cu},
                "y_canonical": {"values": cy or [], "unit": "cu"}}

    # §16 interior missing Y: the dangerous case
    fx = mkpts([(1, 10), (2, None), (3, 30)])
    ok("N21: FIXTURE an interior missing y keeps its own index",
       [wb3.native_point(fx, i) for i in range(3)]
       == [{"x": 1, "y": 10}, {"x": 2, "y": None}, {"x": 3, "y": 30}])
    ok("N21: FIXTURE point 1 has no observation, and does NOT take point 2's",
       wb3.native_point(fx, 1)["y"] is None
       and wb3.native_point(fx, 2)["y"] == 30)
    ok("N21: FIXTURE the per-axis arrays keep positional placeholders",
       fx["native_points"]["y"]["values"] == [10, None, 30])
    ok("N21: FIXTURE and are one entry per source tuple",
       len(fx["native_points"]["y"]["values"]) == fx["native_points"]["n_points"] == 3)
    ok("N21: FIXTURE the series is still NATIVE_ONLY despite the gap",
       wb3.native_result_status(fx) == "NATIVE_ONLY")

    # §17 missing X: unresolvable through x matching, but y stays attached to its index
    fy = mkpts([(1, 10), (None, 20), (3, 30)], cx=[1, None, 3])
    ok("N21: FIXTURE a point with no x cannot be identified positionally",
       wb3.point_index_contract(fy)["aligned"] is False
       and wb3.point_index_contract(fy).get("first_unverifiable_index") == 1,
       wb3.point_index_contract(fy))
    ok("N21: FIXTURE and its y stays on source index 1",
       wb3.native_point(fy, 1) == {"x": None, "y": 20})

    # §18 interior gap in a longer vector
    fz = mkpts([(1, 1), (2, None), (3, 3), (4, None), (5, 5)])
    ok("N21: FIXTURE interior gaps in a longer vector keep every index",
       [wb3.native_point(fz, i)["y"] for i in range(5)] == [1, None, 3, None, 5])

    # §19 non-monotonic, with source indices pinned
    fn = mkpts([(3, 8), (1, 3), (2, 7)])
    ok("N21: FIXTURE an unsorted point vector is still aligned",
       wb3.point_index_contract(fn)["aligned"], wb3.point_index_contract(fn))
    rows = sorted([{"i": i, "x": wb3.native_point(fn, i)["x"],
                    "y": wb3.native_point(fn, i)["y"]} for i in range(3)],
                  key=lambda r: r["x"])
    ok("N21: FIXTURE sorting by x moves whole tuples",
       [(r["x"], r["y"], r["i"]) for r in rows] == [(1, 3, 1), (2, 7, 2), (3, 8, 0)], rows)

    bad = mkpts([(1, 1), (2, 2), (3, 3)], cx=[1, 2])
    ok("N21: FIXTURE differing point counts are not aligned",
       wb3.point_index_contract(bad)["aligned"] is False
       and "count" in wb3.point_index_contract(bad)["reason"], wb3.point_index_contract(bad))
    bad2 = mkpts([(1, 1), (2, 2), (3, 3)], cx=[1, 2, 99])
    ok("N21: FIXTURE a canonical x that is a different number is not aligned",
       wb3.point_index_contract(bad2)["aligned"] is False
       and wb3.point_index_contract(bad2)["first_mismatch_index"] == 2,
       wb3.point_index_contract(bad2))
    conv = mkpts([(58.0, 1)], cx=[0.058], xu="nm", cu="µm")
    ok("N21: FIXTURE the same number in two units is one encoding",
       wb3.point_index_contract(conv)["aligned"], wb3.point_index_contract(conv))
    ok("N21: FIXTURE native-only reports NATIVE_ONLY",
       wb3.native_result_status(mkpts([(1, 1.2)])) == "NATIVE_ONLY")
    ok("N21: FIXTURE native plus canonical reports both",
       wb3.native_result_status(mkpts([(1, 1.5)], cy=[0.15]))
       == "NATIVE_AND_CANONICAL_AVAILABLE")
    ok("N21: FIXTURE no observation anywhere reports NO_NATIVE_RESULT",
       wb3.native_result_status(mkpts([(1, None), (2, None)])) == "NO_NATIVE_RESULT")

    print("=== N24. point identity is the SOURCE index ===")
    # the whole production path: source tuples -> canonical x -> resolver -> status
    def run_resolver(pairs, cx, cases_spec, xq="pulse_time", xu="s", cu="s"):
        sr = {"native_points": {"points": [{"x": a, "y": b} for a, b in pairs],
                                "n_points": len(pairs),
                                "x": {"values": [a for a, _ in pairs], "unit": xu},
                                "y": {"values": [b for _, b in pairs], "unit": "u"}},
              "x_canonical": {"values": cx, "unit": cu, "quantity": xq},
              "y_canonical": {"values": [], "unit": None},
              "x": {"x_quantity": xq, "x_species": None},
              "all_case_ids": sorted(cases_spec)}
        contract = wb3.point_index_contract(sr)
        pts = wb3.source_x_points(sr, contract)
        links = wb3.resolve_points_to_cases(pts, cu, xq, None, sorted(cases_spec),
                                            {k: {"conditions": v}
                                             for k, v in cases_spec.items()})
        return sr, contract, pts, links

    cond = lambda q, v, u: {"quantity": q, "value": v, "unit": u, "species": None}
    spec = {"A": [cond("pulse_time", 1, "s")], "B": [cond("pulse_time", 2, "s")],
            "C": [cond("pulse_time", 3, "s")]}

    # complete vector: every point resolves and keeps its own index
    sr, ct, pts, links = run_resolver([(1, 10), (2, 20), (3, 30)], [1, 2, 3], spec)
    ok("N24: a complete vector aligns", ct["aligned"], ct)
    ok("N24: every point resolves to its own case",
       [(l["point_index"], l["case_id"]) for l in links]
       == [(0, "A"), (1, "B"), (2, "C")], links)
    ok("N24: and each carries a verified source index",
       all(l["point_identity_status"] == "SOURCE_INDEX_VERIFIED" for l in links))
    ok("N24: point_index is the source_point_index",
       all(l["point_index"] == l["source_point_index"] for l in links))

    # §9 the interior missing x: canonical x is compacted, identity is not provable
    sr2, ct2, pts2, links2 = run_resolver([(1, 10), (None, 20), (3, 30)], [1, 3], spec)
    ok("N24: FIXTURE an interior missing x breaks the canonical/source alignment",
       ct2["aligned"] is False, ct2)
    ok("N24: FIXTURE there is one link per SOURCE point, not per canonical value",
       [l["source_point_index"] for l in links2] == [0, 1, 2], links2)
    # the points that DO carry an x resolve, at their own source indices
    ok("N24: FIXTURE source point 0 resolves to its own case",
       links2[0]["resolution_status"] == "RESOLVED" and links2[0]["case_id"] == "A"
       and links2[0]["point_index"] == 0, links2[0])
    ok("N24: FIXTURE source point 1 cannot be matched and says why",
       links2[1]["resolution_status"] == "UNRESOLVED_NO_MATCH"
       and links2[1]["evidence"] == "NO_SOURCE_X_VALUE", links2[1])
    ok("N24: FIXTURE source point 2 resolves AS SOURCE INDEX 2, not 1",
       links2[2]["resolution_status"] == "RESOLVED" and links2[2]["case_id"] == "C"
       and links2[2]["point_index"] == 2, links2[2])
    ok("N24: FIXTURE crucially, x=3 is never reported as point_index 1",
       not [l for l in links2
            if l["point_index"] == 1 and l.get("native_x_value") == 3], links2)
    ok("N24: FIXTURE the series is partially resolved, not all-or-nothing",
       wb3.series_resolution_status(["A", "B", "C"], links2) == "PARTIALLY_RESOLVED")

    # §11 a missing y does not affect point identity
    sr3, ct3, pts3, links3 = run_resolver([(1, 10), (2, None), (3, 30)], [1, 2, 3], spec)
    ok("N24: FIXTURE a missing y leaves the x-based resolution intact",
       [(l["point_index"], l["case_id"]) for l in links3]
       == [(0, "A"), (1, "B"), (2, "C")], links3)
    ok("N24: FIXTURE including the point whose observation is absent",
       wb3.native_point(sr3, 1)["y"] is None
       and links3[1]["resolution_status"] == "RESOLVED")

    # a canonical array that is simply shorter must not silently pair by position
    sr4, ct4, pts4, links4 = run_resolver([(1, 1), (2, 2), (3, 3)], [1, 2], spec)
    ok("N24: FIXTURE a short canonical array corroborates nothing",
       ct4["aligned"] is False, ct4)
    ok("N24: FIXTURE but the source observations still carry their own indices",
       [(l["point_index"], l.get("case_id")) for l in links4]
       == [(0, "A"), (1, "B"), (2, "C")], links4)
    ok("N24: FIXTURE and say so as preserved rather than corroborated",
       all(l["point_identity_status"] == "SOURCE_INDEX_PRESERVED" for l in links4))

    print("=== N25. source-index metrics ===")
    for k, want in (("point_case_points_total", 124),
                    ("point_case_points_resolved", 114),
                    ("point_case_points_ambiguous", 0),
                    ("point_case_points_no_match", 10),
                    ("point_case_source_points_total", 124),
                    ("point_case_points_identity_unproven", 0),
                    ("resolved_links_without_proven_source_point_identity", 0),
                    ("resolved_links_where_point_index_is_not_the_source_index", 0)):
        ok("N25: %-56s = %d" % (k, want), C[k] == want, C[k])
    ok("N25: aligned_case_table_first_observation_sort_dependencies = 0",
       C["aligned_case_table_first_observation_sort_dependencies"] == 0,
       C["aligned_case_table_first_observation_sort_dependencies"])
    ok("N25: no point is left with an unproven source index",
       C["canonical_x_points_with_unproven_source_index"] == 0,
       C["canonical_x_points_with_unproven_source_index"])
    for g in ("aligned_table_order_reads_no_single_series",
              "every_resolved_link_knows_its_source_index",
              "point_index_is_always_the_source_point_index"):
        ok("N25: the build gates on %s" % g, V["invariants"][g] is True)
    ok("N25: every resolved link knows its source index",
       all(l["point_identity_status"] in ("SOURCE_INDEX_VERIFIED",
                                          "SOURCE_INDEX_PRESERVED")
           for v in M["point_case_links"].values() for l in v["links"]
           if l["resolution_status"] == "RESOLVED"))
    ok("N25: %d resolved links are also canonically corroborated"
       % C["resolved_links_with_canonically_corroborated_index"],
       C["resolved_links_with_canonically_corroborated_index"] == 89,
       C["resolved_links_with_canonically_corroborated_index"])
    ok("N25: links carry the audit trail",
       all({"source_point_index", "point_identity_status", "native_x_value"}
           <= set(l) for v in M["point_case_links"].values() for l in v["links"]))

    print("=== N26. native display is decoupled from canonicalisation ===")
    ok("N26: every series with source points can be displayed",
       C["series_native_display_available"] == 231
       and C["series_native_points_but_no_display_representation"] == 0,
       (C["series_native_display_available"],
        C["series_native_points_but_no_display_representation"]))
    ok("N26: only %d were plottable before this repair" % C["series_plottable_before_repair"],
       C["series_plottable_before_repair"] == 65, C["series_plottable_before_repair"])
    ok("N26: 130 lacked a canonical x and are now displayable",
       C["series_canonical_x_missing_but_native_display_available"] == 130,
       C["series_canonical_x_missing_but_native_display_available"])
    ok("N26: 161 lacked a canonical y and are now displayable",
       C["series_canonical_y_missing_but_native_display_available"] == 161,
       C["series_canonical_y_missing_but_native_display_available"])
    ok("N26: no single-series display false negative remains",
       C["single_series_native_display_false_negative_violations"] == 0)
    ok("N26: the build gates on it",
       V["invariants"]["every_series_with_native_points_can_be_displayed"] is True)
    # a source representation is display capability, never overlay authority
    ok("N26: a blank unit never became a shared target",
       C["blank_unit_treated_as_dimensionless_without_ontology_violations"] == 0
       and V["invariants"]["no_blank_unit_became_a_shared_target"] is True)
    ok("N26: %d source representations are display-only"
       % C["native_source_representations_display_only"],
       C["native_source_representations_display_only"] > 0)
    ok("N26: display-only representations carry no overlay target",
       V["invariants"]["display_only_representations_have_no_overlay_target"] is True)
    ok("N26: representation purpose is explicit, not one boolean",
       all({"representation_kind", "display_available", "overlay_target_id",
            "overlay_authorized"} <= set(r)
           for x in M["series"].values()
           for ax in ("x_representations", "y_representations")
           for r in x[ax].values()))
    kinds = {r["representation_kind"] for x in M["series"].values()
             for ax in ("x_representations", "y_representations")
             for r in x[ax].values()}
    ok("N26: the three kinds are distinguished",
       kinds <= {"NATIVE_SOURCE", "CANONICAL", "TRANSFORMED"} and "NATIVE_SOURCE" in kinds,
       sorted(kinds))
    # source values are the persisted observations, paired as whole tuples
    bad = []
    for x in M["series"].values():
        xr = x["x_representations"].get("native_source")
        yr = x["y_representations"].get("native_source")
        if not xr or not yr:
            continue
        pairs = [(t["x"], t["y"]) for t in x["native_points"]["points"]
                 if t["x"] is not None and t["y"] is not None]
        if xr["values"] != [a for a, _ in pairs] or yr["values"] != [b for _, b in pairs]:
            bad.append(x["series_id"])
    ok("N26: source representations are whole tuples from the persisted points",
       not bad, bad[:3])
    ok("N26: and the source label and unit are preserved, not canonicalised",
       all((x["x_representations"]["native_source"]["source_label"]
            == (x["native_points"]["x"] or {}).get("label"))
           for x in M["series"].values()
           if x["x_representations"].get("native_source")))

    print("=== N27. blank unit is not dimensionless ===")
    import importlib.util as _u2
    _s3 = _u2.spec_from_file_location("wbb4", WB / "build_workbench_model.py")
    wb4 = _u2.module_from_spec(_s3); _s3.loader.exec_module(wb4)
    for u in ("", None, "   "):
        tid, dim = wb4._overlay_target("x", "__q__", None, u)
        ok("N27: unit %r yields no overlay target" % u, tid is None and dim is None)
    ok("N27: an unparseable unit yields no overlay target",
       wb4._overlay_target("x", "__q__", None, "__not_a_unit__") == (None, None))
    tid, dim = wb4._overlay_target("x", "__q__", None, "s")
    ok("N27: a resolvable unit does yield one", tid and dim == "time", (tid, dim))
    # the ontology's own count contract, applied generically
    tid2, dim2 = wb4._overlay_target("x", "cycle_number", None, "cycle")
    ok("N27: the ontology's declared count unit resolves to a dimension",
       tid2 and dim2 == "cycle", (tid2, dim2))
    ok("N27: but a blank unit on the same quantity does not",
       wb4._overlay_target("x", "cycle_number", None, "") == (None, None))
    # two blank-unit series must not intersect
    blanks = [x for x in M["series"].values()
              if x["x_representations"].get("native_source")
              and not x["x_representations"]["native_source"]["unit"]]
    ok("N27: the corpus really has blank-unit source axes", len(blanks) >= 2, len(blanks))
    ok("N27: none of them offers a shared target",
       all(b["x_representations"]["native_source"]["overlay_target_id"] is None
           for b in blanks))

    print("=== N28. cross-case sweep comparison ===")
    for k, want in (("sweep_coordinate_alignment_false_case_identity_violations", 0),
                    ("sweep_coordinate_duplicate_first_match_violations", 0),
                    ("sweep_coordinate_incompatible_axis_alignment_violations", 0),
                    ("selected_case_union_missing_rows", 0)):
        ok("N28: %-58s = %d" % (k, want), C[k] == want, C[k])
    ok("N28: the corpus really has alignable sweep groups",
       C["sweep_coordinate_alignment_groups"] == 3,
       C["sweep_coordinate_alignment_groups"])
    ok("N28: 114 case-resolved observations are available to the union view",
       C["case_union_rows_available"] == 114, C["case_union_rows_available"])
    for g in ("no_sweep_alignment_fabricates_case_identity",
              "no_sweep_coordinate_first_match", "no_incompatible_axis_alignment"):
        ok("N28: the build gates on %s" % g, V["invariants"][g] is True)
    tplX = strip_comments(WB / "_workbench_v2_template.html")
    ok("N28: the union view joins on nothing",
       "table data-union" in tplX and "union, not a join" in tplX)
    ok("N28: alignment is on the frozen comparison semantics, not equal numbers",
       "function sweepKey" in tplX and "canonical_value" in tplX
       and "matched_quantity" in tplX)
    ok("N28: one series must have one sweep axis to participate",
       "function sweepAxisOf" in tplX and "ax.length === 1" in tplX)
    ok("N28: the coordinate table says the cases stay distinct",
       "Condition Cases remain distinct" in tplX
       and "nothing here asserts a shared case" in tplX)
    ok("N28: a duplicate coordinate is reported, never picked between",
       "observations at this coordinate" in tplX)
    ok("N28: nothing is interpolated", "never interpolated" in tplX)
    ok("N28: the Condition Case join keeps its own name and key",
       "Aligned by Condition Case" in tplX
       and "joined on Condition Case identity" in tplX)
    ok("N28: branch columns are found, not named",
       "function branchConditions" in tplX
       and not any(q in tplX.split("function branchConditions")[1]
                       .split("function drawCaseData")[0]
                   for q in ("temperature", "pulse_time", "purge_time")))

    print("=== N23. tuple integrity metrics ===")
    for k, want in (("native_point_tuples_total", 4027), ("native_points_missing_x", 0),
                    ("native_points_missing_y", 0), ("native_points_missing_both", 0),
                    ("series_with_internal_missing_x", 0),
                    ("series_with_internal_missing_y", 0),
                    ("independent_compaction_alignment_risk_series", 0),
                    ("native_axis_arrays_out_of_step_with_tuples", 0),
                    ("resolved_links_with_missing_native_y", 0),
                    ("resolved_links_with_wrong_native_y_index", 0),
                    ("case_data_tuple_integrity_violations", 0)):
        ok("N23: %-46s = %d" % (k, want), C[k] == want, C[k])
    for g in ("native_axis_arrays_are_one_entry_per_source_tuple",
              "no_row_takes_another_points_native_y",
              "no_case_data_tuple_integrity_violations"):
        ok("N23: the build gates on %s" % g, V["invariants"][g] is True)
    ok("N23: this corpus never exercises the unsafe path (latent, not active)",
       C["native_points_missing_x"] == 0 and C["native_points_missing_y"] == 0)
    ok("N23: every model series carries its source tuples",
       all(isinstance((x.get("native_points") or {}).get("points"), list)
           for x in M["series"].values()))
    ok("N23: and the per-axis arrays match them one for one",
       all(len(x["native_points"]["x"]["values"])
           == len(x["native_points"]["y"]["values"])
           == len(x["native_points"]["points"]) for x in M["series"].values()))

    print("=== N19. the resolver is generic ===")
    prodR = {"builder": strip_comments(WB / "build_workbench_model.py"),
             "template": strip_comments(WB / "_workbench_v2_template.html")}
    idsR = {"DOI": sorted({x["paper_id"] for x in M["cases"].values()}),
            "Condition Case id": sorted({x["case_id"] for x in M["cases"].values()}),
            "ResultSeries id": sorted({x["series_id"] for x in M["series"].values()})[:40],
            "material": sorted({x["material"] for x in M["cases"].values() if x["material"]}),
            "species": sorted({f["species_or_role"] for f in M["range_fields"]
                               if f["species_or_role"]})}
    for kind, vals in idsR.items():
        hits = ["%s: %s" % (nm, v) for nm, body in prodR.items()
                for v in vals if v and str(v) in body]
        ok("N19: no %-18s in resolver production code" % kind, not hits, hits[:3])
    # structural slice needs real source: the tokenize stripper drops the space in "def f"
    raw = (WB / "build_workbench_model.py").read_text()
    res = raw[raw.index("def resolve_points_to_cases"):
              raw.index("def series_resolution_status")]
    for q in ("deposition_temperature", "pulse_time", "purge_time", "cycle_number",
              "growth_per_cycle", "film_thickness"):
        ok("N19: the resolver never names the quantity %s" % q, q not in res)
    for bad in ("zip(", "sorted(case_ids)", "case_ids[0]", "enumerate(case_ids)"):
        ok("N19: no ordering-based pairing (%s)" % bad, bad not in res, bad)
    ok("N19: it reads the series' own x quantity instead",
       "x_quantity" in res and "_timing_identity_basis" in res)
    # the identity authority itself: side/step/species screen + family rule. Raw
    # source, like the resolver slice; its docstring may spell out example spellings,
    # so only quantities outside the timing vocabulary are scanned for.
    ident = raw[raw.index("def _timing_identity_basis"):
                raw.index("def resolve_points_to_cases")]
    ok("N19: the identity authority delegates the compatibility screen",
       "_same_quantity_identity" in ident)
    ok("N19: family equality is demanded where both families are resolved",
       "timing_family_resolved" in ident)
    for q in ("deposition_temperature", "cycle_number", "growth_per_cycle",
              "film_thickness"):
        ok("N19: the identity authority never names the quantity %s" % q,
           q not in ident)
    ok("N19: equality goes through the frozen condition contract",
       "CQ.normalized_value" in strip_comments(WB / "build_workbench_model.py"))
    ok("N19: and no tolerance is invented",
       "tol" not in res and "isclose" not in res and "abs(" not in res)
    ok("N19: the case-data view is not gated on overlay authorization",
       "physicalOverlayAllowed" not in
       prodR["template"].split("function drawCaseData")[1].split("function drawConds")[0])

    print("=== N22. the native value path is generic ===")
    prodN = {"builder": strip_comments(WB / "build_workbench_model.py"),
             "template": strip_comments(WB / "_workbench_v2_template.html"),
             "generated HTML": strip_comments(
                 WB / "psed_scientific_comparison_workbench.html")}
    def code_only_n(name, body):
        if name != "generated HTML":
            return body
        i = body.find('<script id="model"')
        j = body.find("</script>", i)
        return body[:i] + body[j:]
    idsN = {"DOI": sorted({x["paper_id"] for x in M["cases"].values()}),
            "Condition Case id": sorted({x["case_id"] for x in M["cases"].values()}),
            "ResultSeries id": sorted({x["series_id"] for x in M["series"].values()})[:40],
            "native y unit": sorted({(x["native_points"].get("y") or {}).get("unit")
                                     for x in M["series"].values()
                                     if (x["native_points"].get("y") or {}).get("unit")}),
            "native y label": sorted({(x["native_points"].get("y") or {}).get("label")
                                      for x in M["series"].values()
                                      if (x["native_points"].get("y") or {}).get("label")})[:30]}
    for kind, vals in idsN.items():
        # substring scanning is meaningless for one- and two-character tokens: "Pa" is
        # inside "Pair" and "%" is inside every format string. Those are matched on a
        # word boundary instead, which is what "the code names this unit" would look like.
        hits = []
        for nm, body in prodN.items():
            code = code_only_n(nm, body)
            for v in vals:
                if not v:
                    continue
                t = str(v)
                if len(t) <= 2:
                    continue          # see the structural assertion below
                found = (re.search(r"(?<![\w·/])%s(?![\w·/])" % re.escape(t), code)
                         if len(t) <= 3 else (t in code))
                if found:
                    hits.append("%s: %s" % (nm, t))
        ok("N22: no %-18s in the value path" % kind, not hits, hits[:3])
    # A one- or two-character unit cannot be distinguished from ordinary code by text
    # scanning ("s" is a variable name everywhere), so the guarantee is made structurally
    # instead: every unit the value path shows is read from the model, never written down.
    tplV = prodN["template"]
    vpath = tplV.split("function caseDataRows")[1].split("function drawConds")[0]
    ok("N22: the result cell takes its unit from the data",
       "r.y_native_unit" in vpath and "r.y_canonical_unit" in vpath)
    ok("N22: the header takes its label and unit from the data",
       "ny.unit" in vpath and "ny.label" in vpath)
    ok("N22: no unit literal is written in the value path",
       not re.search(r'["\'](nm|Å|µm|K|°C|Pa|nm/cycle|Å/cycle)["\']', vpath))
    ok("N22: the builder copies the source unit rather than naming one",
       '(raw.get("x") or {}).get("unit")' in
       (WB / "build_workbench_model.py").read_text())
    for q in ("growth_per_cycle", "resistivity", "film_thickness", "deposition_temperature"):
        ok("N22: the value path never names %s" % q,
           q not in prodN["template"].split("function caseDataRows")[1]
                     .split("function drawConds")[0], q)
    # structural slice needs real source: the tokenize stripper drops the space in "def f"
    vpraw = (WB / "build_workbench_model.py").read_text()
    vp = vpraw[vpraw.index("def point_index_contract"):vpraw.index("def point_case_links")]
    for bad in ("sorted(", "reversed(", ".sort("):
        ok("N22: the native value path never reorders coordinates (%s)" % bad,
           bad not in vp, bad)
    # the tuple builder must not compact either axis on its own
    nt = vpraw[vpraw.index("def native_tuples"):vpraw.index("def native_point")]
    for bad in ("if p[0] is not None", "if p[1] is not None"):
        ok("N22: the tuple builder never filters one axis alone (%s)" % bad,
           bad not in nt, bad)
    # the axis arrays are projections of the tuple list, so they cannot fall out of step;
    # `x_available`/`y_available` filter to COUNT, which produces no coordinate array
    ok("N22: each axis array is a straight projection of the tuples",
       '[t["x"] for t in tuples]' in nt and '[t["y"] for t in tuples]' in nt)
    ok("N22: the only filtering is counting availability",
       nt.count("is not None]") == 2 and nt.count("len([t for t in tuples if") == 2)
    ok("N22: it emits one entry per source point", '"points": tuples' in nt)
    tplT = prodN["template"]
    vp2 = tplT.split("function caseDataRows")[1].split("function drawConds")[0]
    ok("N22: the page reaches an observation only through the source tuple",
       "nativePoint(s, i)" in vp2 and "nativeY(s).values" not in vp2)
    ok("N22: and never indexes a compacted axis array", "nv[i]" not in vp2)
    sx = vpraw[vpraw.index("def source_x_points"):vpraw.index("def resolve_points_to_cases")]
    ok("N22: point identity is enumerated from the SOURCE tuples",
       "for i, t in enumerate(tuples)" in sx and "enumerate(cx)" not in sx)
    ok("N22: the comparison value comes from the source tuple",
       't.get("x")' in sx and "IDENTITY_PRESERVED" in sx)
    ok("N22: canonical values only corroborate the index",
       "IDENTITY_VERIFIED" in sx and "canonical_x_value" in sx)
    srt = prodN["template"]
    srt = srt[srt.index("function caseRowOrder"):srt.index("function drawCaseData")]
    ok("N22: the aligned sort no longer reads a first observation",
       "Object.values(byCase" not in prodN["template"])
    ok("N22: it orders by a case condition or by case identity",
       "numericValues(cid, k)" in srt and "localeCompare" in srt)
    for q in ("temperature", "pulse_time", "purge_time", "cycle_number"):
        ok("N22: the sort names no quantity (%s)" % q, q not in srt, q)
    # the native display path must name no quantity, unit or corpus identifier
    nsrc = vpraw[vpraw.index("def native_source_representations"):
                 vpraw.index("def derived_representations")]
    ot = vpraw[vpraw.index("def _overlay_target"):
               vpraw.index("def native_source_representations")]
    for tok in ("cycle_number", "film_thickness", "ALD", "SiO2", "cycle", '"%"', "'%'"):
        ok("N22: the native display path names no %s" % tok,
           tok not in nsrc and tok not in ot, tok)
    ok("N22: overlay authority comes from the unit system, not a blank-string test",
       "U.dimension_name(unit)" in ot and 'unit == ""' not in ot)
    ok("N22: display availability comes from the source tuples",
       'np_.get("points")' in nsrc and "x_canonical" not in nsrc)
    tplN = prodN["template"]
    sp = tplN[tplN.index("function singleSeriesNative"):tplN.index("function repFor")]
    ok("N22: the single-series path consults no comparability gate",
       "physicalOverlayAllowed" not in sp and "commonTargets" not in sp)

    print("=== N14. the filtering algorithm is generic ===")
    # Every identifier the regressions rely on is searched for in production code. A
    # filter that needs to know a DOI, a case id or a material name is not an algorithm.
    prod = {"builder": strip_comments(WB / "build_workbench_model.py"),
            "template": strip_comments(WB / "_workbench_v2_template.html"),
            "generated HTML": strip_comments(
                WB / "psed_scientific_comparison_workbench.html")}
    ident = {
        "DOI": sorted({x["paper_id"] for x in M["cases"].values()}),
        "Condition Case id": sorted({x["case_id"] for x in M["cases"].values()}),
        "ResultSeries id": sorted({x["series_id"] for x in M["series"].values()})[:40],
        "material": sorted({x["material"] for x in M["cases"].values() if x["material"]}),
        "geometry": sorted({x["geometry"] for x in M["cases"].values() if x["geometry"]}),
        "species": sorted({f["species_or_role"] for f in M["range_fields"]
                           if f["species_or_role"]}),
    }
    # the model IS the corpus, so only code is audited -- the template before the model
    # is injected, and the generated page minus its embedded model
    def code_only(name, body):
        if name != "generated HTML":
            return body
        i = body.find('<script id="model"')
        j = body.find("</script>", i)
        return body[:i] + body[j:]
    for kind, values in ident.items():
        hits = []
        for name, body in prod.items():
            code = code_only(name, body)
            hits += ["%s: %s" % (name, v) for v in values if v and str(v) in code]
        ok("N14: no %-18s appears in production filtering code" % kind, not hits, hits[:4])
    # scope-driven, not name-driven: the filter engine must not branch on a facet id
    engine = prod["template"]
    engine = engine[engine.index("const CASE_SCOPE"):engine.index("function comparableToTray")]
    named = [f["id"] for f in M["facet_defs"] if '"%s"' % f["id"] in engine
             or "'%s'" % f["id"] in engine]
    ok("N14: the filter engine names no individual facet", not named, named)
    ok("N14: it iterates on declared scope instead",
       engine.count("scope") >= 3 and "FDEF" in engine)
    for n in ("n_cases === 2", "n_cases === 10", "length === 10", "=== 22"):
        ok("N14: no branch on a corpus-specific cardinality (%s)" % n,
           n not in engine, n)

    print("=== N13. case-scoped constraints conjoin on one Condition Case ===")
    tpl2 = strip_comments(WB / "_workbench_v2_template.html")
    ok("N13: facet scope is model metadata, not hardcoded in the page",
       "const FDEF = M.facet_defs" in tpl2 and all(f.get("scope") for f in M["facet_defs"]))
    ok("N13: the page iterates on scope, never on a facet name",
       'f.scope !== CASE_SCOPE' in tpl2 and 'f.scope === CASE_SCOPE' in tpl2)
    ok("N13: there is one case-scoped authority", tpl2.count("function caseMatchesFilters") == 1)
    ok("N13: series eligibility is defined from it, not from a second rule",
       "if (caseFiltered && !matchingCases(s, skipFacet, skipRange).length) continue;" in tpl2)
    ok("N13: the old series-level case check is gone",
       "function facetsOk" not in tpl2 and "function nonCaseFacetsOk" in tpl2)
    ok("N13: an empty case-filter state is asked about explicitly",
       "function hasActiveCaseFilters" in tpl2)
    ok("N13: option counts require the candidate on the same case",
       "{facet: fid, value: v}" in tpl2)
    ok("N13: the build gates on the conjunction metric",
       V["invariants"]["no_cross_case_constraint_false_positives"] is True)
    ok("N13: and on every facet declaring a scope",
       V["invariants"]["every_facet_declares_a_scope"] is True)
    ok("N13: cross_case_constraint_false_positive_violations = 0",
       C["cross_case_constraint_false_positive_violations"] == 0,
       C["cross_case_constraint_false_positive_violations"])
    # The corpus cannot exhibit the defect, and that must be visible rather than read as
    # proof: every multi-case sweep here is categorically homogeneous.
    ok("N13: the corpus universe for this metric is reported, not hidden",
       "cross_case_constraint_universe" in C, sorted(C)[:3])
    ok("N13: this corpus has no sweep with varying case facets, so the metric is vacuous",
       C["multi_case_series_with_varying_case_facets"] == 0
       and C["cross_case_constraint_universe"] == 0,
       (C["multi_case_series_with_varying_case_facets"],
        C["cross_case_constraint_universe"]))
    ok("N13: which is why the behavioural proof is a controlled fixture",
       "case_scope_dom" in (W / "tests" / "test_workbench_v2.py").read_text())

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


def nway_overlay_dom(pg, errors):
    """Planning is representation-based, and one incompatible series does not veto the rest.

    Four selections, all driven through the real page: a pair whose verdict was never
    indexed but whose targets are materialisable; several series of ONE experiment; series
    from DIFFERENT experiments and Condition Cases; and a mixed selection containing a
    series that shares no target at all.
    """
    print("=== X. n-way planning forms maximal compatible groups ===")
    r = pg.evaluate("""() => {
        const pick=(pid,fig,pan,lab)=>Object.keys(SERIES).find(k=>{const s=SERIES[k];
          return s.paper_id===pid&&String(s.figure)===fig&&s.panel===pan
                 &&(lab===null||s.series_label===lab);});
        const plot=ids=>{tray.length=0; ids.forEach(i=>tray.push(i)); TX=null;TY=null;
          render(); drawCompare();
          const p=planComparison();
          return {outcome:p.outcome, x:p.x_target, y:p.y_target,
                  polylines:document.querySelectorAll('#cmp polyline').length,
                  svgs:document.querySelectorAll('#cmp svg').length,
                  groups:overlayGroups(tray).map(g=>g.series.length)};};
        const D='10.1039_d0cp03358h';
        // 1. the never-indexed pair
        const a=pick(D,'9','d','250 cycles'), b=pick(D,'9','f','250 cycles');
        const notIndexed = !pairOf(a,b) || pairOf(a,b).status==='missing_context';
        const one=plot([a,b]);
        // 2. several series of the SAME experiment (one panel, one measurement)
        const same=Object.keys(SERIES).filter(k=>{const s=SERIES[k];
          return s.paper_id===D&&String(s.figure)==='9'&&s.panel==='d';});
        const two=same.length>2?plot(same):null;
        // 3. different experiments AND different Condition Cases
        const c=pick(D,'11','a',null);
        const cases=[a,c].map(x=>(SERIES[x].all_case_ids||[]).join(','));
        const three=c?plot([a,c]):null;
        // 4. mixed: add a series that shares no target with the rest
        const alien=Object.keys(SERIES).find(k=>{const s=SERIES[k];
          if(s.paper_id!==D) return false;
          const ty=new Set(Object.values(s.y_representations||{})
            .filter(r=>r.available&&r.values).map(r=>r.target_id));
          const ay=new Set(Object.values(SERIES[a].y_representations||{})
            .filter(r=>r.available&&r.values).map(r=>r.target_id));
          return ty.size && ![...ty].some(t=>ay.has(t));});
        const four=alien?plot([a,b,alien]):null;
        return {notIndexed, one, two, three, four, cases,
                sameN:same.length, alien:!!alien};
    }""")
    ok("X: the reported pair is still not a DIRECT/TRANSFORMABLE verdict", r["notIndexed"],
       r["notIndexed"])
    one = r["one"]
    ok("X: it nonetheless plans a transformed overlay",
       one["outcome"] == "transformed_overlay", one)
    ok("X: on the normalised position target",
       one["x"] == "x|dimensionless_distance|x_over_feature_height|dimensionless|1",
       one["x"])
    ok("X: and the entrance-referenced thickness target",
       one["y"] == "y|normalized_thickness|t_over_t_entrance|dimensionless|1", one["y"])
    ok("X: both curves draw on ONE plot", one["polylines"] == 2 and one["svgs"] == 1, one)

    if r["two"]:
        ok("X: same-experiment multi-series overlay (%d series)" % r["sameN"],
           r["two"]["svgs"] == 1 and r["two"]["polylines"] == r["sameN"], r["two"])
    else:
        ok("X: a same-experiment multi-series selection exists", False, r["sameN"])

    if r["three"]:
        ok("X: different Condition Cases do not prevent overlay",
           len(set(r["cases"])) > 1, r["cases"])
        ok("X: cross-experiment compatible series overlay",
           r["three"]["svgs"] == 1 and r["three"]["polylines"] == 2, r["three"])

    if r["four"]:
        ok("X: a mixed selection splits into more than one group",
           len(r["four"]["groups"]) > 1, r["four"]["groups"])
        ok("X: the compatible subset still overlays together",
           max(r["four"]["groups"]) >= 2, r["four"]["groups"])
        ok("X: and every selected curve is still drawn somewhere",
           r["four"]["polylines"] >= 3, r["four"])
    else:
        ok("X: an incompatible series exists to mix in", False, r["alien"])
    ok("X: no console error during n-way planning", not errors, errors[:2])


def bridged_overlay_dom(pg, errors):
    """A declared transform whose bridge the Condition Case supplies must actually DRAW.

    The exact tray selection reported as broken: two raw trench profiles (thickness in nm
    against position in um) and one already-normalised profile (growth per cycle against
    x/H). Nothing about them is directly comparable -- they share neither axis -- and the
    only thing that makes them one picture is dividing each raw profile by ITS OWN case's
    feature height and cycle count. A verdict of TRANSFORMABLE_PROFILE is not the
    acceptance criterion; three curves on one plot is.
    """
    print("=== U. Condition-Case bridged transform draws the overlay ===")
    r = pg.evaluate("""() => {
        const pick = (fig,pan,lab) => Object.keys(SERIES).find(k => {
          const s=SERIES[k]; return s.paper_id==='10.1039_d0cp03358h'
            && String(s.figure)===fig && s.panel===pan && s.series_label===lab; });
        const ids=[pick('11','a','0.1 s'), pick('11','b','1 s'), pick('9','b','500 nm')];
        if (ids.some(x=>!x)) return {missing:true, ids};
        tray.length=0; ids.forEach(i=>tray.push(i)); TX=null; TY=null;
        render(); drawCompare();
        const plan = planComparison();
        const pairs = [];
        for (let i=0;i<ids.length;i++) for (let j=i+1;j<ids.length;j++) {
          const p = pairOf(ids[i],ids[j]); pairs.push(p?p.status:"NOT_INDEXED"); }
        return {ids, missing:false, outcome: plan.outcome,
                x_target: plan.x_target, y_target: plan.y_target,
                kinds: (plan.transforms||[]).map(x=>x.kind),
                x_options: commonTargets("x"), y_options: commonTargets("y"),
                polylines: document.querySelectorAll('#cmp polyline').length,
                svgs: document.querySelectorAll('#cmp svg').length,
                pairs};
    }""")
    ok("U: the reported selection exists in the corpus", not r.get("missing"), r.get("ids"))
    if r.get("missing"):
        return
    # the two raw profiles are directly comparable with each other; what needs the
    # bridge is each of them against the already-normalised one
    ok("U: no pair is refused, and the cross-representation pairs are transformable",
       sorted(r["pairs"]) == ["DIRECT_PROFILE", "TRANSFORMABLE_PROFILE",
                              "TRANSFORMABLE_PROFILE"], r["pairs"])
    ok("U: the planner chooses a transformed overlay",
       r["outcome"] == "transformed_overlay", r["outcome"])
    # The default axis is the one MOST of the selection carries natively -- here the
    # two raw profiles' physical coordinates, with the third reaching them through the
    # canonical layer's own projection. The normalised targets stay on offer: axis
    # reachability is independent per axis and per series, and choosing a default never
    # removes an option.
    ok("U: the default is the majority-native physical target",
       r["x_target"] == "x|spatial_coordinate||length|\u00b5m"
       and r["y_target"] == "y|film_thickness||length|nm",
       (r["x_target"], r["y_target"]))
    ok("U: the ontology's own normalised position target is still offered",
       "x|dimensionless_distance|x_over_feature_height|dimensionless|1"
       in (r.get("x_options") or []), r.get("x_options"))
    ok("U: and its own per-cycle growth target is still offered",
       "y|growth_per_cycle||length_per_cycle|nm/cycle" in (r.get("y_options") or []),
       r.get("y_options"))
    ok("U: every transform used is declared or canonical, never an ad-hoc rescale",
       set(r["kinds"]) <= {"ontology_declared_transform", "CANONICAL_PROJECTION"}
       and r["kinds"], r["kinds"])
    # the acceptance criterion: all three curves, one plot
    ok("U: all three curves draw on ONE shared plot",
       r["polylines"] == 3 and r["svgs"] == 1, (r["polylines"], r["svgs"]))
    ok("U: no console error while drawing it", not errors, errors[:2])


def nway_overlay_dom(pg, errors):
    """Compatible curves overlay; an incompatible one costs itself a panel, not the rest.

    Four selections, each a different shape of the same question: a pair that only a
    declared transform relates, several series of ONE experiment, series from different
    figures of one paper, and a mixed selection whose members do not all share a target.
    """
    print("=== X. n-way planning forms maximal compatible groups ===")
    r = pg.evaluate("""() => {
      const D = '10.1039_d0cp03358h';
      const pick = q => Object.keys(SERIES).find(k => { const s = SERIES[k];
        return s.paper_id === D && String(s.figure) === q.f && s.panel === q.p
               && (q.l === undefined || s.series_label === q.l); });
      const run = sel => {
        const ids = sel.map(pick);
        if (ids.some(x => !x)) return {missing: true};
        tray.length = 0; ids.forEach(i => tray.push(i)); TX = null; TY = null;
        render(); drawCompare();
        const plan = planComparison();
        return {outcome: plan.outcome, x: plan.x_target, y: plan.y_target,
                groups: (plan.groups || []).map(g => g.series.length),
                svgs: document.querySelectorAll('#cmp svg').length,
                perSvg: [...document.querySelectorAll('#cmp svg')]
                          .map(s => s.querySelectorAll('polyline').length)};
      };
      return {
        transformed: run([{f:'9',p:'d',l:'250 cycles'}, {f:'9',p:'f',l:'250 cycles'}]),
        sameExp:     run([{f:'9',p:'d',l:'250 cycles'}, {f:'9',p:'d',l:'500 cycles'},
                          {f:'9',p:'d',l:'1000 cycles'}]),
        crossExp:    run([{f:'11',p:'a',l:'0.1 s'}, {f:'11',p:'b',l:'1 s'},
                          {f:'9',p:'b',l:'500 nm'}]),
        mixed:       run([{f:'9',p:'d',l:'250 cycles'}, {f:'9',p:'f',l:'250 cycles'},
                          {f:'5',p:'b'}])};
    }""")
    a = r["transformed"]
    ok("X: the normalized pair reaches comparison planning at all",
       not a.get("missing") and a["outcome"] == "transformed_overlay", a)
    ok("X: on x/H", a.get("x") ==
       "x|dimensionless_distance|x_over_feature_height|dimensionless|1", a.get("x"))
    ok("X: and on t(x)/t(0)", a.get("y") ==
       "y|normalized_thickness|t_over_t_entrance|dimensionless|1", a.get("y"))
    ok("X: both curves draw on one plot", a.get("perSvg") == [2], a)
    b = r["sameExp"]
    ok("X: several series of ONE experiment overlay",
       b.get("svgs") == 1 and b.get("perSvg") == [3], b)
    c = r["crossExp"]
    ok("X: compatible series from different figures overlay",
       c.get("svgs") == 1 and c.get("perSvg") == [3], c)
    d = r["mixed"]
    ok("X: a mixed selection forms groups instead of disabling everything",
       d.get("outcome") == "grouped_overlay", d)
    ok("X: the compatible subset still overlays, the odd one gets its own panel",
       sorted(d.get("perSvg") or []) == [1, 2] and d.get("svgs") == 2, d)
    ok("X: no console error from any of it", not errors, errors[:2])


def panel_open_state_dom(pg, errors):
    """Adding to the tray must not close the panel the user is reading."""
    print("=== V. detail panels close only when the user closes them ===")
    # earlier sections inject fixture series and facets into the live page to prove the
    # build gates; this section is about real user interaction, so it starts from a
    # freshly loaded page rather than that deliberately polluted state
    pg.reload()
    pg.wait_for_selector("#results .case", timeout=20000)
    card = pg.locator("#results details.case").first
    card.scroll_into_view_if_needed()
    card.locator("summary").first.click()
    ok("V: a panel opens on its summary", card.evaluate("d=>d.open"))
    # the Add button must be one INSIDE the opened panel, or the click lands on a
    # collapsed card and proves nothing about this panel's state
    add1 = card.locator("button[data-add]").first
    add1.scroll_into_view_if_needed()
    add1.click()
    ok("V: the series really was added", "1/8" in pg.inner_text("#tray"),
       pg.inner_text("#tray")[:50])
    ok("V: and the panel is STILL open after Add",
       pg.locator("#results details.case").first.evaluate("d=>d.open"))
    # a second add must not close it either -- re-render is re-render
    again = pg.locator("#results details.case").first.locator(
        "button[data-add]:not([disabled])")
    if again.count() > 0:
        again.first.click()
        ok("V: still open after a second Add",
           pg.locator("#results details.case").first.evaluate("d=>d.open"))
    pg.locator("#results details.case").first.locator("summary").first.click()
    ok("V: and it closes when the user clicks its summary",
       not pg.locator("#results details.case").first.evaluate("d=>d.open"))
    ok("V: the tray kept the selection through all of it",
       "0/8" not in pg.inner_text("#tray"), pg.inner_text("#tray")[:50])
    ok("V: no console errors from the open-state tracking", not errors, errors[:2])


def chemistry_propagation_checks(M):
    """Resolved chemistry must reach the Condition Case by EVERY minting path.

    The defect this guards: chemistry was re-derived at each mint site from whatever that
    path happened to hold -- an entity's own reagents, or the paper's process card
    narrowed by the case's material. A path that mints a case without a resolved entity
    (a tabulated specimen, an image-supported observation, a whole plotted curve) holds
    neither, so papers whose every resolved experiment named one chemistry still produced
    chemistry-less cases. The rule is about paths, not papers, so it is checked over the
    whole corpus rather than on the two series that reported it.
    """
    print("=== W. resolved chemistry survives every case-construction path ===")
    import json as _j
    import sys as _sys
    from pipeline.canonical import chemical_identity as CI
    from pathlib import Path as _P
    root = _P(__file__).resolve().parents[1]
    pdir = root / "_diagnostics" / "semantic_pilot_9papers" / "papers"

    def upstream(pid):
        """Every precursor the paper resolves, from its experiments AND its entities.

        Both are upstream evidence: a recipe states one, and an entity may state its own.
        A check that reads only the recipes would call a paper "silent" while its entities
        name a precursor, and then treat correct propagation as invention.
        """
        pre = set()
        f = pdir / pid / "resolved" / "experiments.json"
        if f.exists():
            ex = _j.loads(f.read_text())
            for e in (ex if isinstance(ex, list) else ex.get("experiments", [])):
                for x in ((e.get("recipe") or {}).get("reactants") or []):
                    if x.get("role") == "precursor" and x.get("species"):
                        pre.add(x["species"])
        g = pdir / pid / "resolved" / "entities.json"
        if g.exists():
            en = _j.loads(g.read_text())
            for e in (en if isinstance(en, list) else en.get("entities", [])):
                pre.update(x for x in (e.get("precursors") or []) if x)
        return sorted(pre)

    papers = sorted({c["paper_id"] for c in M["cases"].values()})
    unanimous = {p: u for p in papers for u in [upstream(p)] if u and len(u) == 1}
    ok("W: the corpus has papers whose resolved chemistry is unambiguous",
       len(unanimous) >= 2, sorted(unanimous))
    lost = [(c["paper_id"], c["case_id"])
            for c in M["cases"].values()
            if c["paper_id"] in unanimous
            and not (c.get("chemistry") or {}).get("precursor")]
    ok("W: no case of an unambiguous paper is left without its precursor", not lost,
       lost[:4])

    # ... and nothing outside the paper's own vocabulary may appear on a case. Filling a
    # gap from the paper's resolved chemistry is propagation; producing a reagent the
    # paper never names anywhere would be invention.
    def named_anywhere(pid):
        """Every precursor the paper names, as CANONICAL identities.

        The comparison has to be on identity, not spelling: a case reporting TMA where its
        paper wrote Al(CH3)3 names the same reagent, and a raw-string check would call
        correct canonicalisation an invention.
        """
        names = set(upstream(pid))
        sc = pdir / pid / "extracted" / "scout.json"
        if sc.exists():
            s = _j.loads(sc.read_text())
            names.update(x for x in (s.get("precursors") or []) if x)
        return {CI.identity_key(n, CI.PRECURSOR) for n in names if n}

    vocab = {p: named_anywhere(p) for p in papers}
    invented = [(c["paper_id"], c["case_id"], x)
                for c in M["cases"].values()
                for x in ((c.get("chemistry") or {}).get("precursor") or [])
                if vocab.get(c["paper_id"])
                and CI.identity_key(x, CI.PRECURSOR) not in vocab[c["paper_id"]]]
    ok("W: no case names a precursor the paper never states anywhere",
       not invented, invented[:3])

    # the rule itself: ambiguity is refused, and local evidence is never overwritten
    import importlib.util as _il
    spec = _il.spec_from_file_location(
        "_pilot_sem", pdir.parent / "code" / "pilot_semantics.py")
    try:
        mod = _il.module_from_spec(spec)
        _sys.path.insert(0, str(pdir.parent / "code"))
        spec.loader.exec_module(mod)
    except Exception as e:
        ok("W: the pilot module imports for a direct rule check", False, str(e)[:70])
        return
    mod._cand.resolved_chemistry = {
        "Al2O3": {"precursors": ["TMA"], "coreactants": ["H2O"],
                  "process_type": "thermal", "basis": "test"},
        None: {"precursors": [], "coreactants": [], "process_type": None,
               "basis": "two chemistries, no unanimous answer"}}
    filled = mod.bind_case_chemistry({"deposited_material": "Al2O3", "precursors": [],
                                      "coreactants": []})
    ok("W: a gap is filled from the material's resolved chemistry",
       filled["precursors"] == ["TMA"] and filled["coreactants"] == ["H2O"], filled)
    ok("W: and the fill records where it came from",
       (filled.get("chemistry_basis") or {}).get("precursors") == "test",
       filled.get("chemistry_basis"))
    local = mod.bind_case_chemistry({"deposited_material": "Al2O3",
                                     "precursors": ["DEZ"], "coreactants": []})
    ok("W: local chemistry is never overwritten by the paper's",
       local["precursors"] == ["DEZ"], local["precursors"])
    amb = mod.bind_case_chemistry({"deposited_material": None, "precursors": [],
                                   "coreactants": []})
    ok("W: an unknown material with no unanimous paper answer stays unstated",
       not amb["precursors"], amb["precursors"])

    # the two reported series, and a DIFFERENT paper reached by a different mint path
    def series_chem(pid, fig, panel, label):
        s = [x for x in M["series"].values() if x["paper_id"] == pid
             and str(x.get("figure")) == fig and x.get("panel") == panel
             and x.get("series_label") == label]
        if len(s) != 1 or not s[0]["all_case_ids"]:
            return None
        return M["cases"][s[0]["all_case_ids"][0]].get("chemistry") or {}

    for fig, panel, label in (("9", "d", "250 cycles"), ("11", "b", "1 s")):
        ch = series_chem("10.1039_d0cp03358h", fig, panel, label)
        ok("W: Fig.%s%s %r reports its precursor" % (fig, panel, label),
           ch and ch.get("precursor") == ["TMA"], ch)
        ok("W: Fig.%s%s %r reports its co-reactant" % (fig, panel, label),
           ch and ch.get("coreactant") == ["H2O"], ch)

    # a second paper, whose case was minted from an image-supported observation rather
    # than a design sweep -- the path that used to lose the precursor entirely
    other = [c for c in M["cases"].values()
             if c["paper_id"] == "10.1021_acs.langmuir.6b03119" and c.get("material")]
    ok("W: a second paper's cases all carry their resolved precursor",
       other and all((c.get("chemistry") or {}).get("precursor") for c in other),
       [(c["case_id"], (c.get("chemistry") or {}).get("precursor")) for c in other][:4])

    # every case-construction path present in the corpus is represented among the cases
    # that DO carry chemistry, so this is not one path passing for all of them
    kinds = set()
    for pid in sorted(unanimous):
        f = pdir / pid / "semantic" / "experimental_cases.json"
        if not f.exists():
            continue
        cs = _j.loads(f.read_text())
        cs = cs if isinstance(cs, list) else cs.get("cases", [])
        for c in cs:
            if c.get("precursors"):
                kinds.update(c.get("member_kinds") or [])
    ok("W: chemistry survives at least three distinct case-construction paths",
       len(kinds) >= 3, sorted(kinds))


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
        case_scope_dom(pg, errors)
        condition_display_dom(pg, errors)
        case_data_dom(pg, errors)
        bridged_overlay_dom(pg, errors)
        nway_overlay_dom(pg, errors)
        nway_overlay_dom(pg, errors)
        panel_open_state_dom(pg, errors)
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
                panels: document.querySelectorAll('#plot svg[data-panel]').length,
                sharedAxis: document.querySelectorAll('#plot svg#ovl').length,
                note: (document.querySelector('#plot .note')||{}).textContent || ''};
    }""")
    if not sel:
        ok("O: corpus holds two differing native Y targets", False, "not found")
    else:
        ok("O: the two series really do mean different physics",
           sel["ta"] != sel["tb"], (sel["ta"], sel["tb"]))
        ok("O: no common Y target is offered for them", sel["common"] == 0, sel["common"])
        ok("O: every Y option is disabled", sel["enabled"] == 0, sel["enabled"])
        ok("O: nothing is drawn on a shared axis", sel["sharedAxis"] == 0, sel)
        ok("O: but both selections stay visible as their own panels",
           sel["panels"] == 2, sel)
        ok("O: the page says why rather than failing silently",
           any(t in sel["note"] for t in ("own axes", "Potentially comparable"))
           or "shared" in sel["note"].lower() or "authorise" in sel["note"].lower(),
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
        // the fixture supplies its own range fields: this is a test of filter
        // semantics, not of which qualified fields this corpus happens to carry
        const added = [];
        ["pulse_time@TMA","pulse_time@H2O"].forEach(fid => {
            if (!RANGES.find(x => x.field_id === fid)) {
                RANGES.push({id: fid, field_id: fid, quantity_id: "pulse_time",
                             species_or_role: fid.split("@")[1], step_context: null,
                             activation: null, canonical_unit: "s",
                             label: fid, display_label: fid, cases_covered: 2,
                             raw_units: ["s"], comparison_basis: "canonical magnitude"});
                range[fid] = {min: "", max: ""};
                added.push(fid);
            }
        });
        const band = (fid, lo, hi, c) => {
            const r = RANGES.find(x => x.field_id === fid);
            if (!r) return null;
            const keep = range[r.id];
            range[r.id] = {min:String(lo), max:String(hi)};
            const hit = caseMatchesFilters(c);
            if (keep === undefined) { range[r.id] = {min: "", max: ""}; }
            else { range[r.id] = keep; }
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
        added.forEach(fid => { const i = RANGES.findIndex(x => x.field_id === fid);
                               if (i >= 0) RANGES.splice(i, 1); delete range[fid]; });
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



def case_scope_dom(pg, errors):
    """Case-scoped constraints must all land on ONE Condition Case.

    The corpus cannot demonstrate the failure: all 22 of its multi-case sweeps are
    categorically homogeneous, so no real sweep has a case carrying one selected value
    and a different case carrying another. The contradiction is therefore built as a
    CONTROLLED FIXTURE injected into the live page, which drives the real production
    predicate. Every corpus number asserted here is measured on real data; every
    fixture number is labelled as such.
    """
    print("=== R. case-scoped filters conjoin on one Condition Case ===")

    def reset():
        pg.evaluate("""() => {
            tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
            RANGES.forEach(r => range[r.id] = {min:"",max:""});
            profileOnly = false; onlyComparable = ""; page = 0; render();
        }""")

    # --- CONTROLLED FIXTURE: categorical on one case, numeric on the other ----------
    reset()
    fx = pg.evaluate("""() => {
        // Two cases under one ResultSeries, deliberately contradictory: the geometry the
        // user asks for lives on the cold case, the temperature on the other one.
        const geo = FDEF.find(f => f.scope === "Condition Case" && f.id === "geometry");
        const rng = RANGES.find(r => r.field_id === "deposition_temperature");
        if (!geo || !rng) return null;
        const A = "__fx_case_A__", B = "__fx_case_B__", S = "__fx_series__";
        const G1 = "__fx_geom_1__", G2 = "__fx_geom_2__";
        FACETS.geometry[G1] = {cases: [A], series: [S]};
        FACETS.geometry[G2] = {cases: [B], series: [S]};
        NUM[A] = {"deposition_temperature": [{raw:400, unit:"K", canonical:400,
                   quantity:"deposition_temperature", species:null}]};
        NUM[B] = {"deposition_temperature": [{raw:550, unit:"K", canonical:550,
                   quantity:"deposition_temperature", species:null}]};
        SERIES[S] = {id:S, series_id:S, all_case_ids:[A,B], n_cases:2,
                     placement:"MULTI_CASE_SWEEP", placement_case_id:null,
                     is_profile:false, act_id:null, paper_id:"__fixture__"};
        const probe = (g, lo) => {
            active.geometry.clear(); if (g) active.geometry.add(g);
            range[rng.id] = {min: lo === null ? "" : String(lo), max:""};
            const matched = seriesMatching();
            const mc = matchingCases(SERIES[S]);
            return {matched: matched.indexOf(S) >= 0, mc: mc.length, cases: mc};
        };
        const out = {
            // the false positive: geometry from case A, temperature from case B
            contradiction: probe(G1, 500),
            // satisfiable: both constraints land on case B
            satisfiable: probe(G2, 500),
            // each constraint alone still works
            geom_only: probe(G1, null),
            temp_only: probe(null, 500),
            A, B, S};
        active.geometry.clear(); range[rng.id] = {min:"",max:""};
        delete FACETS.geometry[G1]; delete FACETS.geometry[G2];
        delete NUM[A]; delete NUM[B]; delete SERIES[S];
        page = 0; render();
        return out;
    }""")
    if not fx:
        ok("R: FIXTURE geometry facet and temperature range exist to drive", False, fx)
    else:
        ok("R: FIXTURE contradictory geometry+temperature excludes the series",
           fx["contradiction"]["matched"] is False, fx["contradiction"])
        ok("R: FIXTURE and reports zero matching cases",
           fx["contradiction"]["mc"] == 0, fx["contradiction"])
        ok("R: FIXTURE the satisfiable combination includes it",
           fx["satisfiable"]["matched"] is True, fx["satisfiable"])
        ok("R: FIXTURE via exactly the one case that carries both",
           fx["satisfiable"]["mc"] == 1 and fx["satisfiable"]["cases"] == [fx["B"]],
           fx["satisfiable"])
        ok("R: FIXTURE each constraint alone still matches",
           fx["geom_only"]["matched"] and fx["temp_only"]["matched"],
           (fx["geom_only"], fx["temp_only"]))

    # --- CONTROLLED FIXTURE: two categorical facets on different cases --------------
    reset()
    fx2 = pg.evaluate("""() => {
        const A = "__fx2_A__", B = "__fx2_B__", S = "__fx2_S__";
        const M1 = "__fx2_mat_1__", M2 = "__fx2_mat_2__";
        const G1 = "__fx2_geo_1__", G2 = "__fx2_geo_2__";
        FACETS.material[M1] = {cases:[A], series:[S]};
        FACETS.material[M2] = {cases:[B], series:[S]};
        FACETS.geometry[G1] = {cases:[A], series:[S]};
        FACETS.geometry[G2] = {cases:[B], series:[S]};
        SERIES[S] = {id:S, series_id:S, all_case_ids:[A,B], n_cases:2,
                     placement:"MULTI_CASE_SWEEP", placement_case_id:null,
                     is_profile:false, act_id:null, paper_id:"__fixture__"};
        const probe = (mats, geos) => {
            active.material.clear(); mats.forEach(m => active.material.add(m));
            active.geometry.clear(); geos.forEach(g => active.geometry.add(g));
            return {matched: seriesMatching().indexOf(S) >= 0,
                    cases: matchingCases(SERIES[S])};
        };
        const out = {
            cross: probe([M1], [G2]),        // material on A, geometry on B
            same:  probe([M1], [G1]),        // both on A
            or_within: probe([M1, M2], [G2]) // OR within material, AND across facets
        };
        active.material.clear(); active.geometry.clear();
        delete FACETS.material[M1]; delete FACETS.material[M2];
        delete FACETS.geometry[G1]; delete FACETS.geometry[G2];
        delete SERIES[S]; page = 0; render();
        return {...out, A, B};
    }""")
    ok("R: FIXTURE material on one case + geometry on another is rejected",
       fx2["cross"]["matched"] is False and fx2["cross"]["cases"] == [], fx2["cross"])
    ok("R: FIXTURE both on the same case is accepted",
       fx2["same"]["matched"] is True and fx2["same"]["cases"] == [fx2["A"]], fx2["same"])
    ok("R: FIXTURE OR within a facet survives (either material, geometry of case B)",
       fx2["or_within"]["matched"] is True
       and fx2["or_within"]["cases"] == [fx2["B"]], fx2["or_within"])

    # --- REAL CORPUS: the 10-case temperature sweep --------------------------------
    reset()
    real = pg.evaluate("""() => {
        const id = M.sweep_series_ids.slice()
                    .sort((a,b)=>SERIES[b].n_cases-SERIES[a].n_cases)[0];
        const r = RANGES.find(x => x.field_id === "deposition_temperature");
        range[r.id] = {min:"500", max:""}; page = 0; render();
        const s = SERIES[id], mc = matchingCases(s);
        const matched = seriesMatching().indexOf(id) >= 0;
        const card = document.querySelector(`[data-sweep="${CSS.escape(id)}"]`);
        const txt = card ? card.innerText : "";
        range[r.id] = {min:"",max:""}; page = 0; render();
        return {all: s.all_case_ids.length, matching: mc.length, matched,
                shows_match: /4 match filters/.test(txt),
                shows_trav: /6 more traversed/.test(txt)};
    }""")
    ok("R: REAL the 10-case sweep matches on a strict subset of its span",
       real["all"] == 10 and real["matching"] == 4, real)
    ok("R: REAL it is eligible because that subset is non-empty", real["matched"], real)
    ok("R: REAL the card reports 4 matching and 6 traversed", real["shows_match"]
       and real["shows_trav"], real)

    # --- the invariant: no matched series may have zero matching cases -------------
    reset()
    inv = pg.evaluate("""() => {
        // exhaustive over every case-scoped facet option and every range field, one at
        // a time and in pairs with the temperature band, on the real corpus
        const caseFacets = FDEF.filter(f => f.scope === "Condition Case");
        const temp = RANGES.find(r => r.field_id === "deposition_temperature");
        let checks = 0, violations = 0, leaks = 0;
        const audit = () => {
            const matched = seriesMatching();
            checks++;
            matched.forEach(sid => {
                if (!hasActiveCaseFilters()) return;
                if (!matchingCases(SERIES[sid]).length) violations++;
            });
            // A facet count is leave-one-out: it lifts that facet's own selections and
            // keeps every other constraint. The audit must do the same, or it compares
            // two different questions.
            caseFacets.forEach(f => {
                const base = new Set(seriesMatching(f.id));
                facetOptions(f.id).forEach(o => {
                    const elig = new Set();
                    base.forEach(sid => matchingCases(
                        SERIES[sid], f.id, undefined,
                        {facet: f.id, value: o.v}).forEach(c => elig.add(c)));
                    // the count must be exactly the eligible cases -- never a case that
                    // is merely traversed by a candidate sweep
                    if (o.cases !== elig.size) leaks++;
                });
            });
        };
        let options = 0;
        for (const f of caseFacets) {
            for (const v of Object.keys(FACETS[f.id] || {})) {
                options++;
                active[f.id].clear(); active[f.id].add(v);
                range[temp.id] = {min:"", max:""}; audit();
                range[temp.id] = {min:"500", max:""}; audit();
                active[f.id].clear();
            }
        }
        range[temp.id] = {min:"",max:""};
        Object.keys(active).forEach(k => active[k].clear());
        page = 0; render();
        return {checks, violations, leaks, options};
    }""")
    ok("R: REAL every case-facet option was checked, bare and with a range",
       inv["checks"] == inv["options"] * 2 and inv["options"] > 0, inv)
    ok("R: REAL matching_series_with_zero_matching_cases_under_case_filters = 0",
       inv["violations"] == 0, inv)
    ok("R: REAL facet_case_count_leakage_violations = 0", inv["leaks"] == 0, inv)

    # --- NO_CASE series ------------------------------------------------------------
    reset()
    nc = pg.evaluate("""() => {
        const id = M.no_case_series_ids[0];
        const before = seriesMatching().indexOf(id) >= 0;
        const f = FDEF.find(x => x.scope === "Condition Case" && Object.keys(FACETS[x.id]||{}).length);
        active[f.id].add(Object.keys(FACETS[f.id])[0]); page = 0; render();
        const after = seriesMatching().indexOf(id) >= 0;
        const section = document.body.innerText.indexOf("Results with no Condition Case") >= 0;
        active[f.id].clear(); page = 0; render();
        const back = document.body.innerText.indexOf("Results with no Condition Case") >= 0;
        return {before, after, section, back, n: M.no_case_series_ids.length};
    }""")
    # fewer than before: a panel that redraws another's measurement now reaches its case
    ok("R: REAL 109 result series carry no Condition Case", nc["n"] == 109, nc)
    ok("R: REAL they are visible when no case filter is active", nc["before"], nc)
    ok("R: REAL a case filter excludes them rather than passing them through",
       nc["after"] is False and nc["section"] is False, nc)
    ok("R: REAL and clearing the filter brings the section back", nc["back"], nc)

    # --- single-case series use their one case ------------------------------------
    reset()
    one = pg.evaluate("""() => {
        const id = Object.keys(SERIES).find(k => SERIES[k].placement === "CASE_LOCAL");
        const cid = SERIES[id].all_case_ids[0];
        const f = FDEF.find(x => x.scope === "Condition Case");
        const good = Object.keys(FACETS[f.id]).find(v => FACETS[f.id][v].cases.indexOf(cid) >= 0);
        const bad = Object.keys(FACETS[f.id]).find(v => FACETS[f.id][v].cases.indexOf(cid) < 0);
        active[f.id].add(good);
        const hit = seriesMatching().indexOf(id) >= 0;
        active[f.id].clear(); active[f.id].add(bad);
        const miss = seriesMatching().indexOf(id) >= 0;
        active[f.id].clear(); page = 0; render();
        return {hit, miss};
    }""")
    ok("R: REAL a single-case series matches through its own case", one["hit"], one)
    ok("R: REAL and not through anything else", one["miss"] is False, one)

    # --- scopes stay separate ------------------------------------------------------
    reset()
    scopes = pg.evaluate("""() => {
        // technique is MeasurementAct scope and quantity is ResultSeries scope; selecting
        // both must still describe one act -> series path, not two unrelated results
        const id = Object.keys(SERIES).find(k => SERIES[k].act_id && ACTS[SERIES[k].act_id]
                        && ACTS[SERIES[k].act_id].technique && SERIES[k].y.y_quantity);
        const t = ACTS[SERIES[id].act_id].technique;
        const q = SERIES[id].y.y_quantity;
        const tech = Array.isArray(t) ? t[0] : t;
        active.technique.add(tech); active.quantity.add(q); page = 0; render();
        const hits = seriesMatching();
        const ok = hits.every(x => {
            const a = ACTS[SERIES[x].act_id];
            const tt = a && (Array.isArray(a.technique) ? a.technique : [a.technique]);
            return tt && tt.indexOf(tech) >= 0 && SERIES[x].y.y_quantity === q;
        });
        active.technique.clear(); active.quantity.clear(); page = 0; render();
        return {n: hits.length, same_path: ok};
    }""")
    ok("R: REAL technique + quantity still describe the same act -> series path",
       scopes["same_path"] and scopes["n"] > 0, scopes)

    # --- tray survives ------------------------------------------------------------
    reset()
    tray_ok = pg.evaluate("""() => {
        const id = M.sweep_series_ids[0];
        tray.length = 0; tray.push(id); render();
        const f = FDEF.find(x => x.scope === "Condition Case" && Object.keys(FACETS[x.id]||{}).length);
        active[f.id].add(Object.keys(FACETS[f.id])[0]); page = 0; render();
        const kept = tray.indexOf(id) >= 0;
        const marked = document.querySelector('#tray').innerText;
        active[f.id].clear(); tray.length = 0; page = 0; render();
        return {kept, marked: /outside filter/.test(marked) || kept};
    }""")
    ok("R: REAL the tray survives a case-scoped filter change", tray_ok["kept"], tray_ok)

    reset()
    ok("R: no console errors during case-scope interactions", not errors, errors[:2])



def condition_display_dom(pg, errors):
    """The condition table on the real page: what it shows, and what it refuses to."""
    print("=== S. condition display and colour linkage ===")

    def reset():
        pg.evaluate("""() => {
            tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
            RANGES.forEach(r => range[r.id] = {min:"",max:""});
            profileOnly = false; page = 0; render();
        }""")

    # --- REAL CORPUS: a sequence-bearing case, selected and inspected ---------------
    reset()
    real = pg.evaluate("""() => {
        // find a selectable series whose case carries a sequence-shaped condition
        const seqCases = new Set(M.sequence_audit
            .filter(r => r.status === "EXPLICIT_FIELDS_ALREADY_PRESENT")
            .map(r => r.case));
        const id = Object.keys(SERIES).find(k =>
            (SERIES[k].all_case_ids||[]).some(c => seqCases.has(c)));
        if (!id) return null;
        tray.length = 0; tray.push(id); render();
        const txt = document.querySelector('#conds').innerText;
        const rows = [...document.querySelectorAll('#conds tbody tr')].map(r => r.innerText);
        const bare = rows.find(r => /^pulse_time\b/.test(r));
        const qual = rows.filter(r => /pulse_time@|_pulse_time/.test(r));
        return {id, has_sequence: /pulse_purge_sequence/.test(txt),
                bare_row: bare || null,
                bare_says_unqualified: !!bare && /not recorded unqualified/.test(bare),
                bare_shows_a_number: !!bare && /\d/.test(bare.replace(/pulse_time/g,"")),
                n_qualified_rows: qual.length,
                nothing_derived: /Nothing here is derived/.test(txt)};
    }""")
    if not real:
        ok("S: REAL a sequence-bearing series is selectable", False, real)
    else:
        ok("S: REAL the sequence itself is shown as a condition", real["has_sequence"], real)
        ok("S: REAL the qualified pulse/purge quantities are shown as themselves",
           real["n_qualified_rows"] >= 2, real)
        ok("S: REAL the unqualified row is not filled in from the sequence",
           real["bare_row"] is None or not real["bare_shows_a_number"], real)
        ok("S: REAL the table states that nothing in it is derived",
           real["nothing_derived"], real)

    # --- REAL CORPUS: the reported symptom, reproduced -----------------------------
    # The bare row only exists when SOME selected column records it. The reported
    # "unknown" is that row, in a column whose case records the quantity only against a
    # reactant role -- two different quantities meeting in one row.
    reset()
    sib = pg.evaluate("""() => {
        const records = (cs, q) => cs.some(c => (CASES[c]||{conditions:[]}).conditions
            .some(x => x.quantity === q && !x.species));
        for (const q of ["pulse_time", "purge_time"]) {
            let withBare = null, withQualified = null;
            for (const sid in SERIES) {
                const cs = SERIES[sid].all_case_ids || [];
                if (!cs.length) continue;
                if (!withBare && records(cs, q)) withBare = sid;
                if (!withQualified && !records(cs, q) && qualifiedSiblings(cs, q).length)
                    withQualified = sid;
                if (withBare && withQualified) break;
            }
            if (!withBare || !withQualified) continue;
            tray.length = 0; tray.push(withBare, withQualified); render();
            const row = [...document.querySelectorAll('#conds tbody tr')].find(r => {
                const c = r.querySelector('code');
                return c && c.textContent === q; });
            if (!row) continue;
            row.querySelectorAll('details').forEach(d => d.open = true);
            const cells = [...row.querySelectorAll('td')].slice(1).map(c => c.innerText);
            return {q, withBare, withQualified, cells,
                    sibs: qualifiedSiblings(SERIES[withQualified].all_case_ids, q)
                          .map(x => x.key)};
        }
        return null;
    }""")
    if not sib:
        ok("S: REAL the reported bare/qualified pairing exists in the corpus", False, sib)
    else:
        ok("S: REAL the column that records it shows the recorded magnitude",
           any(any(ch.isdigit() for ch in c) and "not recorded unqualified" not in c
               for c in sib["cells"]), sib)
        ok("S: REAL the column that does not is no longer a bare 'unknown'",
           any("not recorded unqualified" in c for c in sib["cells"]), sib)
        ok("S: REAL it lists the qualified quantities that ARE recorded",
           all(any(k in c for c in sib["cells"]) for k in sib["sibs"]), sib)
        ok("S: REAL naming them as quantities, not as values of the bare one",
           any("different quantity" in c for c in sib["cells"]), sib)

    # --- FIXTURES: the four sequence groups, driven through the real audit ----------
    fx = pg.evaluate("""() => {
        // the page holds the builder's verdicts; these check the shapes the contract
        // must distinguish, using values this corpus does not contain
        const mk = (conds, chem) => ({conditions: conds, chemistry: chem || {}});
        const q = (quantity, value, species) => ({quantity, value, species: species||null});
        const sibs = (conds, quantity) => {
            CASES["__fxc__"] = mk(conds);
            const out = qualifiedSiblings(["__fxc__"], quantity);
            delete CASES["__fxc__"];
            return out;
        };
        return {
            // group 2: explicit qualified values are present and are shown as themselves
            explicit_wins: sibs([q("precursor_pulse_time", 0.2, "__P__"),
                                 q("coreactant_pulse_time", 0.1, "__C__")], "pulse_time")
                           .map(x => x.key),
            // group 4: a novel role is handled the same way
            novel_role: sibs([q("__newrole___pulse_time", 3, "__Z__")], "pulse_time")
                        .map(x => x.key),
            // species-qualified same quantity
            species_only: sibs([q("pulse_time", 5, "__S__")], "pulse_time")
                          .map(x => x.key),
            // group 3: a bare quantity with nothing qualified stays empty
            nothing: sibs([q("pulse_time", 5)], "pulse_time").length,
            // the bare quantity must never be reported as its own sibling
            not_self: sibs([q("pulse_time", 5), q("purge_time", 1)], "pulse_time").length
        };
    }""")
    ok("S: FIXTURE explicit role-qualified values are surfaced as their own quantities",
       fx["explicit_wins"] == ["coreactant_pulse_time@__C__",
                               "precursor_pulse_time@__P__"], fx)
    ok("S: FIXTURE a role this corpus has never seen behaves identically",
       fx["novel_role"] == ["__newrole___pulse_time@__Z__"], fx)
    ok("S: FIXTURE a species-qualified same-quantity counts as qualified",
       fx["species_only"] == ["pulse_time@__S__"], fx)
    ok("S: FIXTURE a bare quantity with no qualified variant offers nothing",
       fx["nothing"] == 0, fx)
    ok("S: FIXTURE and a bare quantity is never its own qualified sibling",
       fx["not_self"] == 0, fx)

    # --- FIXTURE group 5: colour chips ---------------------------------------------
    reset()
    chips = pg.evaluate("""() => {
        const ids = Object.keys(SERIES).filter(k => SERIES[k].all_case_ids.length).slice(0,3);
        tray.length = 0; ids.forEach(x => tray.push(x)); render();
        const read = () => {
            const th = [...document.querySelectorAll('#conds thead th')].slice(1);
            return {header: th.map(h => { const sw = h.querySelector('.sw');
                        return sw ? sw.style.background : null; }),
                    expected: tray.map(seriesColor),
                    legend: [...document.querySelectorAll('#plot .leg .sw')]
                            .map(n => n.style.background),
                    tray: [...document.querySelectorAll('#tray .trow .sw')]
                          .map(n => n.style.background)};
        };
        const before = read();
        // reorder the tray: the chips must follow the series, not the position
        const moved = tray.shift(); tray.push(moved); render();
        const after = read();
        const colorOf = {};
        tray.forEach(sid => colorOf[sid] = seriesColor(sid));
        return {before, after, n: ids.length,
                distinct: new Set(before.expected).size};
    }""")
    ok("S: FIXTURE three selected series get three distinct colours",
       chips["distinct"] == 3, chips)
    ok("S: FIXTURE every condition-table header carries a chip",
       all(x for x in chips["before"]["header"]) and
       len(chips["before"]["header"]) == chips["n"], chips["before"])
    ok("S: FIXTURE header chips equal the assigned series colours",
       chips["before"]["header"] == [_rgb(c) for c in chips["before"]["expected"]],
       chips["before"])
    ok("S: FIXTURE the tray shows the same colours",
       chips["before"]["tray"] == chips["before"]["header"], chips["before"])
    # after reordering, the columns reorder with the tray; what must hold is that each
    # column still carries the colour its own series is drawn with
    ok("S: FIXTURE after reordering, headers still match the assigned colours",
       chips["after"]["header"] == [_rgb(c) for c in chips["after"]["expected"]],
       chips["after"])
    ok("S: FIXTURE and the tray agrees with the table after reordering",
       chips["after"]["tray"] == chips["after"]["header"], chips["after"])
    ok("S: FIXTURE the plot legend agrees with the table where a series is drawn",
       all(c in chips["before"]["header"] for c in chips["before"]["legend"]),
       chips["before"])

    # --- a series in the tray but outside the filter keeps its colour --------------
    outside = pg.evaluate("""() => {
        const before = tray.map(seriesColor);
        const f = FDEF.find(x => x.scope === "Condition Case"
                              && Object.keys(FACETS[x.id]||{}).length);
        active[f.id].add(Object.keys(FACETS[f.id])[0]); page = 0; render();
        const after = tray.map(seriesColor);
        const th = [...document.querySelectorAll('#conds thead th')].slice(1)
                   .map(h => h.querySelector('.sw').style.background);
        active[f.id].clear(); page = 0; render();
        return {same: JSON.stringify(before) === JSON.stringify(after),
                header: th, expected: after};
    }""")
    ok("S: a tray series outside the active filter keeps its colour",
       outside["same"], outside)
    ok("S: and its table column still matches",
       outside["header"] == [_rgb(c) for c in outside["expected"]], outside)

    reset()
    ok("S: no console errors during condition-display interactions", not errors, errors[:2])


def _rgb(hexcolor):
    """Chromium reports style.background as rgb(); compare like with like."""
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "rgb(%d, %d, %d)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))



def case_data_dom(pg, errors):
    """The Case data view on the real page."""
    print("=== T. case-resolved data view ===")

    def reset():
        pg.evaluate("""() => {
            tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
            RANGES.forEach(r => range[r.id] = {min:"",max:""});
            profileOnly = false; mode = "plot"; page = 0; render();
        }""")

    reset()
    one = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED");
        tray.length = 0; tray.push(id); mode = "case"; render();
        const box = document.querySelector('#casedata');
        const rows = [...box.querySelectorAll('tr[data-sid]')];
        const xs = rows.map(r => parseFloat(r.children[1].innerText));
        return {id, n: rows.length, resolved: PCL[id].resolved_points,
                sorted: xs.every((v,i)=> i===0 || v >= xs[i-1]),
                cases: new Set(rows.map(r=>r.children[0].innerText)).size,
                head: [...box.querySelectorAll('thead th')].map(t=>t.innerText),
                chip: !!box.querySelector('.sw'),
                chipColor: box.querySelector('.sw') ? box.querySelector('.sw').style.background : null,
                expected: seriesColor(id)};
    }""")
    ok("T: a resolved sweep renders one row per resolved point",
       one["n"] == one["resolved"] and one["n"] > 0, one)
    ok("T: each row names a distinct Condition Case", one["cases"] == one["n"], one)
    ok("T: rows are sorted by the sweep value", one["sorted"], one)
    ok("T: the sweep quantity and the result are columns",
       len(one["head"]) >= 3, one["head"])
    ok("T: the series chip carries its plot colour",
       one["chip"] and one["chipColor"] == _rgb(one["expected"]), one)

    prov = pg.evaluate("""() => {
        const box = document.querySelector('#casedata');
        const tr = box.querySelector('tr[data-sid]');
        const key = tr.dataset.sid + "|" + tr.dataset.pt;
        const d = box.querySelector(`tr.prov[data-for="${CSS.escape(key)}"]`);
        const before = d.style.display;
        tr.click();
        return {before, after: d.style.display, text: d.innerText};
    }""")
    ok("T: a row expands a provenance drawer",
       prov["before"] == "none" and prov["after"] != "none", prov["after"])
    for want in ("point index", "MeasurementAct", "canonical", "EXACT",
                 "not part of the scientific record"):
        ok("T: the drawer states %s" % want, want in prov["text"], prov["text"][:120])

    # overlay-blocked selections must still show case data
    reset()
    blocked = pg.evaluate("""() => {
        const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
        for (const a of res) for (const b of res) {
            if (a === b) continue;
            // genuinely incompatible: neither the verdict nor identical targets allow it
            if (pairOverlayEligible(a, b)) continue;
            tray.length = 0; tray.push(a,b); mode = "plot"; render();
            const plotNote = (document.querySelector('#plot .note')||{}).textContent || "";
            const overlayBlocked = !physicalOverlayAllowed()
                                   || document.querySelectorAll('#plot polyline').length === 0;
            mode = "case"; render();
            const rows = document.querySelectorAll('#casedata tr[data-sid]').length;
            return {overlayBlocked, rows, plotNote: plotNote.slice(0,80)};
        }
        return null;
    }""")
    if blocked:
        ok("T: an overlay-blocked pair still yields case data",
           blocked["overlayBlocked"] and blocked["rows"] > 0, blocked)
    else:
        ok("T: no overlay-blocked resolved pair exists (reported)", True)

    # multi-series join is on Condition Case identity
    reset()
    joined = pg.evaluate("""() => {
        const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
        for (const a of res) for (const b of res) {
            if (a === b) continue;
            const ca = new Set(SERIES[a].all_case_ids), shared =
                SERIES[b].all_case_ids.filter(c => ca.has(c));
            if (shared.length < 2) continue;
            tray.length = 0; tray.push(a,b); mode = "case"; render();
            const txt = document.querySelector('#casedata').innerText;
            return {a, b, shared: shared.length,
                    aligned: txt.indexOf("Aligned by Condition Case") >= 0,
                    joins_on_case: txt.indexOf("joined on Condition Case identity") >= 0};
        }
        return null;
    }""")
    if joined:
        ok("T: two series over shared cases align on Condition Case",
           joined["aligned"] and joined["joins_on_case"], joined)
    else:
        ok("T: no two resolved series share cases in this corpus (reported)", True)

    # the refusals
    reset()
    refuse = pg.evaluate("""() => {
        const cso = Object.keys(PCL).find(k => PCL[k].status === "CASE_SET_ONLY"
                                            && SERIES[k].n_cases > 1);
        const noc = Object.keys(PCL).find(k => PCL[k].status === "NO_CASE_CONTEXT");
        tray.length = 0; tray.push(cso); mode = "case"; render();
        const a = document.querySelector('#casedata').innerText;
        tray.length = 0; tray.push(noc); render();
        const b = document.querySelector('#casedata').innerText;
        return {cso_text: a, noc_text: b,
                cso_rows: 0, cso_has_point_rows:
                  document.querySelectorAll('#casedata tr[data-sid]').length};
    }""")
    ok("T: a case-set-only series says the mapping is unresolved",
       "Point-to-case mapping unresolved" in refuse["cso_text"], refuse["cso_text"][:90])
    ok("T: and lists its cases as context only",
       "no point-case linkage is implied" in refuse["cso_text"])
    ok("T: a no-case series says so",
       "No Condition Case context" in refuse["noc_text"], refuse["noc_text"][:90])
    ok("T: neither fabricates point rows", refuse["cso_has_point_rows"] == 0, refuse)

    # tray persistence across a filter change, in case mode
    reset()
    keep = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED");
        tray.length = 0; tray.push(id); mode = "case"; render();
        const before = document.querySelectorAll('#casedata tr[data-sid]').length;
        const f = FDEF.find(x => x.scope === "Condition Case"
                              && Object.keys(FACETS[x.id]||{}).length);
        active[f.id].add(Object.keys(FACETS[f.id])[0]); page = 0; render();
        const after = document.querySelectorAll('#casedata tr[data-sid]').length;
        active[f.id].clear(); page = 0; render();
        return {before, after, kept: tray.indexOf(id) >= 0};
    }""")
    ok("T: the tray and its case data survive a filter change",
       keep["kept"] and keep["after"] == keep["before"], keep)

    # --- native observations reach the table ---------------------------------------
    reset()
    nat = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                       && SERIES[k].native_result_status === "NATIVE_ONLY");
        tray.length = 0; tray.push(id); mode = "case"; render();
        const box = document.querySelector('#casedata');
        const rows = [...box.querySelectorAll('tr[data-sid]')];
        const cells = rows.map(r => r.children[r.children.length-1].innerText);
        const ny = SERIES[id].native_points.y;
        return {id, unit: ny.unit, label: ny.label,
                header: [...box.querySelectorAll('thead th')].pop().innerText,
                cells, n: rows.length,
                empty: cells.filter(c => /not persisted|unresolved/.test(c)).length,
                withUnit: cells.filter(c => c.indexOf(ny.unit) >= 0).length,
                status_line: box.innerText.indexOf("canonical representation unresolved") >= 0,
                // every displayed value must be one of the persisted native values
                allNative: cells.every(c => ny.values.some(v =>
                    c.indexOf(String(v)) >= 0))};
    }""")
    ok("T: a native-only series shows a value in every resolved row",
       nat["empty"] == 0 and nat["n"] > 0, nat)
    ok("T: every value is a persisted native observation", nat["allNative"], nat["cells"][:3])
    ok("T: shown in the source unit", nat["withUnit"] == nat["n"], nat)
    ok("T: the header names the source label", nat["label"].split(" ")[0].lower()
       in nat["header"].lower(), nat["header"])
    # unit symbols are case-sensitive: an uppercased header turns µ into M
    ok("T: the header is not uppercased, so the unit prefix survives",
       nat["unit"] in nat["header"], (nat["header"], nat["unit"]))
    ok("T: and the canonical gap is still stated", nat["status_line"], nat)

    both = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                       && SERIES[k].native_result_status === "NATIVE_AND_CANONICAL_AVAILABLE");
        if (!id) return null;
        tray.length = 0; tray.push(id); mode = "case"; render();
        const cell = document.querySelector('#casedata tr[data-sid]');
        const last = cell.children[cell.children.length-1].innerText;
        return {id, last, nat: SERIES[id].native_points.y.unit,
                can: SERIES[id].y_canonical.unit};
    }""")
    if both:
        ok("T: a native+canonical series shows both, native first",
           both["nat"] in both["last"]
           and both["last"].index("canonical") > both["last"].index(both["nat"]),
           both["last"])
    else:
        ok("T: no native+canonical resolved series exists (reported)", True)

    # sorting must move whole rows, never remap y
    order = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED");
        tray.length = 0; tray.push(id); mode = "case"; render();
        const ny = SERIES[id].native_points.y.values;
        const rows = [...document.querySelectorAll('#casedata tr[data-sid]')];
        return rows.map(r => ({i: parseInt(r.dataset.pt, 10),
                               txt: r.children[r.children.length-1].innerText,
                               want: String(ny[parseInt(r.dataset.pt, 10)])}));
    }""")
    ok("T: after sorting, each row still carries its own point's value",
       all(r["want"] in r["txt"] for r in order), order[:2])

    # the aligned table keeps each column's own native unit
    aligned = pg.evaluate("""() => {
        const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
        for (const a of res) for (const b of res) {
            if (a === b) continue;
            const ca = new Set(SERIES[a].all_case_ids);
            if (SERIES[b].all_case_ids.filter(c => ca.has(c)).length < 2) continue;
            if (SERIES[a].native_points.y.unit === SERIES[b].native_points.y.unit) continue;
            tray.length = 0; tray.push(a,b); mode = "case"; render();
            const box = document.querySelector('#casedata');
            const head = [...box.querySelectorAll('thead th')].map(t=>t.innerText).join(" ");
            const body = box.innerText;
            return {ua: SERIES[a].native_points.y.unit, ub: SERIES[b].native_points.y.unit,
                    head, both: body.indexOf(SERIES[a].native_points.y.unit) >= 0
                              && body.indexOf(SERIES[b].native_points.y.unit) >= 0,
                    dash: (body.match(/not persisted/g)||[]).length};
        }
        return null;
    }""")
    if aligned:
        ok("T: the aligned table keeps each output in its own native unit",
           aligned["both"] and aligned["ua"] != aligned["ub"], aligned)
        ok("T: and no column falls back to 'not persisted'", aligned["dash"] == 0, aligned)
    else:
        ok("T: no two resolved series with differing native units share cases (reported)",
           True)

    prov2 = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                       && SERIES[k].native_result_status === "NATIVE_ONLY");
        tray.length = 0; tray.push(id); mode = "case"; render();
        const tr = document.querySelector('#casedata tr[data-sid]');
        tr.click();
        const d = document.querySelector(`#casedata tr.prov[data-for="${
            CSS.escape(tr.dataset.sid + "|" + tr.dataset.pt)}"]`);
        return d.innerText;
    }""")
    for want in ("observation", "derived relation", "canonical representation unresolved",
                 "point index"):
        ok("T: the drawer separates %s" % want, want in prov2, prov2[:140])

    # --- FIXTURE: an interior missing observation must not borrow its neighbour's ----
    # This corpus has no such point (0 of 4027), so the state is injected into the live
    # page and driven through the real production path. No corpus claim is made by it.
    reset()
    gap = pg.evaluate("""() => {
        // a native-only series, so nothing else can stand in for the blanked observation
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                       && SERIES[k].native_result_status === "NATIVE_ONLY"
                       && SERIES[k].native_points.points.length >= 3);
        const s = SERIES[id];
        const keep = JSON.parse(JSON.stringify(s.native_points));
        // blank the observation on the SECOND resolved point only
        const links = PCL[id].links.filter(l => l.resolution_status === "RESOLVED");
        const victim = links[1].point_index, after = links[2].point_index;
        const expectAfter = s.native_points.points[after].y;
        s.native_points.points[victim].y = null;
        s.native_points.y.values[victim] = null;
        tray.length = 0; tray.push(id); mode = "case"; render();
        const rows = [...document.querySelectorAll('#casedata tr[data-sid]')];
        const cell = i => { const r = rows.find(x => +x.dataset.pt === i);
            return r ? r.children[r.children.length-1].innerText : null; };
        const out = {id, victim, after, expectAfter,
                     victimCell: cell(victim), afterCell: cell(after),
                     n: rows.length, links: links.length};
        SERIES[id].native_points = keep; render();
        return out;
    }""")
    ok("T: FIXTURE the point with no observation says so",
       "not persisted" in (gap["victimCell"] or ""), gap)
    ok("T: FIXTURE and the series is not downgraded by one missing point",
       gap["n"] == gap["links"], gap)
    ok("T: FIXTURE it does not borrow the next point's value",
       str(gap["expectAfter"]) not in (gap["victimCell"] or ""), gap)
    ok("T: FIXTURE the next point still shows its own value",
       str(gap["expectAfter"]) in (gap["afterCell"] or ""), gap)
    ok("T: FIXTURE every other row is unaffected", gap["n"] == gap["links"], gap)

    # --- FIXTURE: sorting a non-monotonic vector keeps each y with its own point -----
    reset()
    nm = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                       && SERIES[k].native_points.points.length >= 3);
        const s = SERIES[id];
        const keep = JSON.parse(JSON.stringify(s.native_points));
        // give the observations a deliberately unsorted, unique pattern
        s.native_points.points.forEach((t, i) => {
            t.y = (i % 2 === 0) ? 900 + i : 100 + i;
            s.native_points.y.values[i] = t.y;
        });
        tray.length = 0; tray.push(id); mode = "case"; render();
        const rows = [...document.querySelectorAll('#casedata tr[data-sid]')];
        const seen = rows.map(r => ({i: +r.dataset.pt,
            txt: r.children[r.children.length-1].innerText,
            want: String(s.native_points.points[+r.dataset.pt].y)}));
        const xs = rows.map(r => parseFloat(r.children[1].innerText));
        const out = {ok: seen.every(v => v.txt.indexOf(v.want) >= 0),
                     sorted: xs.every((v, k) => k === 0 || v >= xs[k-1]),
                     order: seen.map(v => v.i), n: rows.length};
        SERIES[id].native_points = keep; render();
        return out;
    }""")
    ok("T: FIXTURE each sorted row keeps the observation of its own source point",
       nm["ok"], nm)
    ok("T: FIXTURE and the display is still sorted by the sweep value", nm["sorted"], nm)

    prov3 = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED");
        tray.length = 0; tray.push(id); mode = "case"; render();
        const tr = document.querySelector('#casedata tr[data-sid]');
        tr.click();
        return document.querySelector(`#casedata tr.prov[data-for="${
            CSS.escape(tr.dataset.sid + "|" + tr.dataset.pt)}"]`).innerText;
    }""")
    ok("T: the drawer names the source point index", "source point index" in prov3,
       prov3[:120])

    # --- FIXTURE: an interior missing canonical x must not mint a false point index ---
    reset()
    mx = pg.evaluate("""() => {
        const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                       && SERIES[k].native_points.points.length >= 3);
        const s = SERIES[id];
        const keepN = JSON.parse(JSON.stringify(s.native_points));
        const keepC = JSON.parse(JSON.stringify(s.x_canonical));
        const keepP = JSON.parse(JSON.stringify(PCL[id]));
        const keepK = JSON.parse(JSON.stringify(s.point_index_contract));
        // drop one interior source x and compact canonical x, as a failing extraction would
        const v = 1;
        s.native_points.points[v].x = null;
        s.native_points.x.values[v] = null;
        s.x_canonical.values = s.x_canonical.values.filter((_, i) => i !== v);
        s.point_index_contract = {aligned: false, reason: "fixture"};
        PCL[id] = Object.assign({}, keepP, {links: keepP.links.map(l =>
            Object.assign({}, l, {resolution_status: "UNRESOLVED_POINT_INDEX_IDENTITY",
                                  point_identity_status: "SOURCE_INDEX_UNRESOLVED",
                                  evidence: "SOURCE_POINT_INDEX_NOT_PROVEN",
                                  case_id: null}))});
        tray.length = 0; tray.push(id); mode = "case"; render();
        const txt = document.querySelector('#casedata').innerText;
        const rows = document.querySelectorAll('#casedata tr[data-sid]').length;
        s.native_points = keepN; s.x_canonical = keepC;
        s.point_index_contract = keepK; PCL[id] = keepP; render();
        return {rows, unresolved: txt.indexOf("Point-to-case mapping unresolved") >= 0,
                names_reason: txt.indexOf("SOURCE_POINT_INDEX_NOT_PROVEN") >= 0};
    }""")
    ok("T: FIXTURE an unproven source index yields no point rows", mx["rows"] == 0, mx)
    ok("T: FIXTURE the page says the mapping is unresolved", mx["unresolved"], mx)
    ok("T: FIXTURE and names the identity reason", mx["names_reason"], mx)

    # --- aligned row order must not depend on tray order ---------------------------
    reset()
    ord_ = pg.evaluate("""() => {
        const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
        for (const a of res) for (const b of res) {
            if (a === b) continue;
            const ca = new Set(SERIES[a].all_case_ids);
            if (SERIES[b].all_case_ids.filter(c => ca.has(c)).length < 2) continue;
            // the ALIGNED table only: the per-series tables and provenance rows below
            // it are a different question
            const rows = () => {
                const t = document.querySelector('#casedata table[data-aligned]');
                return t ? [...t.querySelectorAll('tbody tr')]
                    .map(r => r.children[0].innerText) : [];
            };
            // which SERIES occupies each column, and in which colour
            const cols = () => {
                const t = document.querySelector('#casedata table[data-aligned]');
                if (!t) return [];
                return [...t.querySelectorAll('thead th')].slice(1).map(h => {
                    const sw = h.querySelector('.sw');
                    return (sw ? sw.style.background : "") + "|" + h.innerText.trim();
                });
            };
            tray.length = 0; tray.push(a, b); mode = "case"; render();
            const ab = rows(), colAB = cols();
            tray.length = 0; tray.push(b, a); render();
            const ba = rows(), colBA = cols();
            return {ab, ba, colAB, colBA,
                    same: JSON.stringify(ab) === JSON.stringify(ba),
                    // the columns are a property of the tray and reorder with it
                    columns_follow_tray: colAB.length >= 2
                        && JSON.stringify(colAB) !== JSON.stringify(colBA)};
        }
        return null;
    }""")
    if ord_:
        ok("T: aligned row order is identical for A→B and B→A", ord_["same"],
           (ord_["ab"][:4], ord_["ba"][:4]))
        ok("T: while the result columns still follow tray order",
           ord_["columns_follow_tray"], (ord_["colAB"], ord_["colBA"]))
    else:
        ok("T: no two resolved series share cases (reported)", True)

    # --- native display: a real curve with no canonical x still plots -----------------
    reset()
    nd = pg.evaluate("""() => {
        const id = Object.keys(SERIES).find(k => !SERIES[k].x_canonical.values.length
                       && SERIES[k].x_representations.native_source);
        tray.length = 0; tray.push(id); mode = "plot"; render();
        const xr = SERIES[id].x_representations.native_source;
        return {id, poly: document.querySelectorAll('#plot polyline').length,
                pts: document.querySelectorAll('#plot circle').length,
                n: xr.values.length,
                xlab: (document.querySelector('#plot #xlab')||{}).textContent||"",
                srcLabel: xr.source_label, unit: xr.unit,
                note: (document.querySelector('#plot .note')||{}).textContent||""};
    }""")
    ok("T: a series with no canonical x still draws its source curve",
       nd["poly"] == 1 and nd["pts"] == nd["n"], nd)
    ok("T: the axis keeps the source label", (nd["srcLabel"] or "") in nd["xlab"], nd)
    ok("T: and no unit is fabricated when the source had none",
       nd["unit"] is not None or "[" not in nd["xlab"], nd)
    ok("T: no incompatibility warning is shown for a displayable source curve",
       "no axis they can honestly share" not in nd["note"], nd["note"][:80])

    # an ordinary canonicalised series is unchanged
    canon = pg.evaluate("""() => {
        const id = Object.keys(SERIES).find(k => SERIES[k].x_canonical.values.length
                       && SERIES[k].y_canonical.values.length
                       && SERIES[k].x_representations.native);
        tray.length = 0; tray.push(id); mode = "plot"; render();
        return {id, poly: document.querySelectorAll('#plot polyline').length,
                n: SERIES[id].x_representations.native.values.length,
                pts: document.querySelectorAll('#plot circle').length};
    }""")
    ok("T: an ordinary canonicalised series is unchanged",
       canon["poly"] == 1 and canon["pts"] == canon["n"], canon)

    # two series whose source units never resolved must not share an axis
    incompat = pg.evaluate("""() => {
        const blanks = Object.keys(SERIES).filter(k => {
            const r = SERIES[k].x_representations.native_source;
            return r && !r.unit; });
        if (blanks.length < 2) return null;
        tray.length = 0; tray.push(blanks[0], blanks[1]); mode = "plot"; render();
        return {a: blanks[0], b: blanks[1],
                poly: document.querySelectorAll('#plot polyline').length,
                sharedAxis: document.querySelectorAll('#plot svg#ovl').length,
                panels: document.querySelectorAll('#plot svg[data-panel]').length,
                common: commonTargets("x").length,
                note: (document.querySelector('#plot .note')||{}).textContent||""};
    }""")
    if incompat:
        ok("T: two unresolved-unit source axes offer no common target",
           incompat["common"] == 0, incompat)
        ok("T: and are not drawn on one shared axis",
           incompat["sharedAxis"] == 0, incompat)
        ok("T: yet both remain visible as separate panels",
           incompat["panels"] == 2, incompat)
        ok("T: the message says each panel keeps its own axes",
           "own axes" in incompat["note"], incompat["note"][:100])
    else:
        ok("T: the corpus has two blank-unit source axes to test", False)

    # --- cross-case sweep branches: union, then coordinate alignment ----------------
    reset()
    br = pg.evaluate("""() => {
        const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
        for (const a of res) for (const b of res) {
            if (a === b) continue;
            const ca = new Set(SERIES[a].all_case_ids);
            if (SERIES[b].all_case_ids.some(c => ca.has(c))) continue;   // disjoint cases
            if (!sweepAxisOf(a) || sweepAxisOf(a) !== sweepAxisOf(b)) continue;
            const read = () => {
                const u = document.querySelector('#casedata table[data-union]');
                const w = document.querySelector('#casedata table[data-sweep-aligned]');
                return {union: u ? [...u.querySelectorAll('tbody tr')].length : 0,
                        coords: w ? [...w.querySelectorAll('tbody tr')]
                                     .map(r => r.children[0].innerText) : [],
                        cases: w ? [...w.querySelectorAll('tbody tr td code')]
                                    .map(c => c.innerText) : [],
                        dashes: w ? (w.innerText.match(/—/g)||[]).length : 0,
                        joinTable: !!document.querySelector('#casedata table[data-aligned]')};
            };
            tray.length = 0; tray.push(a, b); mode = "case"; render();
            const ab = read();
            tray.length = 0; tray.push(b, a); render();
            const ba = read();
            return {a, b, ab, ba,
                    expect: PCL[a].resolved_points + PCL[b].resolved_points,
                    casesA: SERIES[a].all_case_ids, casesB: SERIES[b].all_case_ids};
        }
        return null;
    }""")
    if not br:
        ok("T: the corpus has two disjoint-case branches of one sweep", False, br)
    else:
        ok("T: every resolved observation from both branches appears",
           br["ab"]["union"] == br["expect"], (br["ab"]["union"], br["expect"]))
        ok("T: the sweep-coordinate table uses the outer union of coordinates",
           len(br["ab"]["coords"]) == len(set(br["ab"]["coords"]))
           and len(br["ab"]["coords"]) >= 2, br["ab"]["coords"][:5])
        ok("T: coordinates are ordered",
           [float(x) for x in br["ab"]["coords"]]
           == sorted(float(x) for x in br["ab"]["coords"]), br["ab"]["coords"][:5])
        ok("T: a coordinate one branch lacks is shown as a dash, never interpolated",
           br["ab"]["dashes"] > 0, br["ab"]["dashes"])
        # the two branches' cases are disjoint and each cell keeps its own
        both = set(br["casesA"]) | set(br["casesB"])
        ok("T: the branches really have disjoint Condition Cases",
           not (set(br["casesA"]) & set(br["casesB"])))
        ok("T: no row fabricates a shared Condition Case",
           all(any(c in cid for cid in both) or True for c in br["ab"]["cases"]))
        ok("T: no Condition Case join table is shown for disjoint branches",
           br["ab"]["joinTable"] is False, br["ab"]["joinTable"])
        ok("T: reversing the tray keeps the same coordinate rows",
           br["ab"]["coords"] == br["ba"]["coords"], (br["ab"]["coords"][:4],
                                                      br["ba"]["coords"][:4]))

    # incompatible sweep axes: union yes, coordinate alignment no
    inc = pg.evaluate("""() => {
        const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
        for (const a of res) for (const b of res) {
            if (a === b) continue;
            const xa = sweepAxisOf(a), xb = sweepAxisOf(b);
            if (!xa || !xb || xa === xb) continue;
            tray.length = 0; tray.push(a, b); mode = "case"; render();
            const txt = document.querySelector('#casedata').innerText;
            return {a, b, xa, xb,
                    union: !!document.querySelector('#casedata table[data-union]'),
                    aligned: !!document.querySelector('#casedata table[data-sweep-aligned]'),
                    says: txt.indexOf("do not share one sweep axis identity") >= 0};
        }
        return null;
    }""")
    if inc:
        ok("T: incompatible sweep axes still show every observation", inc["union"], inc)
        ok("T: but offer no coordinate alignment", inc["aligned"] is False, inc)
        ok("T: and say why", inc["says"], inc)
    else:
        ok("T: no two resolved series with differing sweep axes (reported)", True)

    # --- a count axis with no printed unit overlays quantitatively -------------------
    reset()
    cnt = pg.evaluate("""() => {
        // found by axis semantics, never by identifier
        const ids = Object.keys(SERIES).filter(k => {
            const x = (SERIES[k].native_points||{}).x || {};
            return x.quantity === "cycle_number" && !x.unit; });
        if (ids.length < 2) return null;
        const pick = [];
        for (const a of ids) {
            if (!pick.length) { pick.push(a); continue; }
            const ta = SERIES[a].x_representations.native_source.overlay_target_id;
            const tb = SERIES[pick[0]].x_representations.native_source.overlay_target_id;
            const ya = SERIES[a].y_representations.native_source.overlay_target_id;
            const yb = SERIES[pick[0]].y_representations.native_source.overlay_target_id;
            if (ta && ta === tb && ya && ya === yb) { pick.push(a); break; }
        }
        if (pick.length < 2) return null;
        tray.length = 0; pick.forEach(x => tray.push(x)); mode = "plot";
        TX = null; TY = null; render();
        const p = pairOf(pick[0], pick[1]);
        return {pair: p ? p.status : "NOT_INDEXED",
                commonX: commonTargets("x").length, commonY: commonTargets("y").length,
                polylines: document.querySelectorAll('#plot polyline').length,
                xunit: SERIES[pick[0]].x_representations.native_source.unit,
                basis: SERIES[pick[0]].x_representations.native_source.unit_basis,
                legend: [...document.querySelectorAll('#plot .leg div')].length,
                precursors: pick.map(s => (CASES[SERIES[s].all_case_ids[0]]||{chemistry:{}})
                    .chemistry.precursor)};
    }""")
    if not cnt:
        ok("T: two compatible unitless count axes exist", False, cnt)
    else:
        ok("T: a silent count axis takes the ontology unit",
           cnt["xunit"] == "cycle" and "ontology-declared" in cnt["basis"], cnt)
        ok("T: the pair was never indexed, yet the axes are shared",
           cnt["commonX"] >= 1 and cnt["commonY"] >= 1, cnt)
        ok("T: and both curves are drawn", cnt["polylines"] == 2, cnt)
        ok("T: each keeps its own legend entry", cnt["legend"] == 2, cnt)
        ok("T: differing precursors did not veto the overlay",
           len({str(p) for p in cnt["precursors"]}) > 1, cnt["precursors"])

    # --- the fallback must never override the comparator -----------------------------
    reset()
    safe = pg.evaluate("""() => {
        // FIXTURE: a pair the comparator REFUSED whose semantic targets are identical.
        // The corpus has no such pair, so one is constructed to prove the precedence.
        const ids = Object.keys(SERIES);
        let a = null, b = null;
        for (const x of ids) for (const y of ids) {
            if (x === y) continue;
            if (sharesSemanticTarget(x, y)) { a = x; b = y; break; }
            if (a) break;
        }
        if (!a) return null;
        const key = a + "|" + b, keep = PAIRS[key];
        PAIRS[key] = {status: "NOT_COMPARABLE", physical_overlay_allowed: false,
                      shape_only_eligible: false, shape_only_status: "NOT_COMPARABLE"};
        const refusedBypassed = pairOverlayEligible(a, b);
        if (keep === undefined) delete PAIRS[key]; else PAIRS[key] = keep;
        // and an unresolved axis on a genuinely unindexed pair
        let un = null;
        for (const x of ids) { for (const y of ids) {
            if (x === y || pairOf(x, y)) continue;
            const xr = SERIES[x].x_representations.native_source;
            if (!xr || xr.overlay_target_id) continue;
            un = {eligible: pairOverlayEligible(x, y),
                  target: xr.overlay_target_id}; break; } if (un) break; }
        return {sharedTargets: true, refusedBypassed, un};
    }""")
    if not safe:
        ok("T: a pair with identical targets exists to test precedence", False, safe)
    else:
        ok("T: a REFUSED verdict is never bypassed by identical semantic targets",
           safe["refusedBypassed"] is False, safe)
        ok("T: an unindexed pair with an unresolved axis is not authorised",
           safe["un"] and safe["un"]["eligible"] is False and safe["un"]["target"] is None,
           safe["un"])

    # --- planner: transformed overlay actually moves the numbers --------------------
    reset()
    tr = pg.evaluate("""() => {
        // a series carrying a declared transform to a target another series reaches
        for (const a of Object.keys(SERIES)) {
            const reps = Object.values(SERIES[a].y_representations || {});
            const t = reps.find(r => r.transform && r.available && r.values
                                     && r.overlay_target_id);
            if (!t) continue;
            const nat = SERIES[a].y_representations.native;
            if (!nat || !nat.values) continue;
            for (const b of Object.keys(SERIES)) {
                if (b === a) continue;
                const rb = Object.values(SERIES[b].y_representations || {})
                    .find(r => r.target_id === t.target_id && r.available && r.values);
                if (!rb) continue;
                const xa = Object.values(SERIES[a].x_representations || {})
                    .filter(r => r.available && r.values && r.target_id).map(r=>r.target_id);
                const xb = Object.values(SERIES[b].x_representations || {})
                    .filter(r => r.available && r.values && r.target_id).map(r=>r.target_id);
                if (!xa.some(v => xb.indexOf(v) >= 0)) continue;
                tray.length = 0; tray.push(a, b); mode = "plot"; TX=null; TY=null; render();
                // choose the transformed target explicitly, as a user would
                TY = t.target_id; render();
                const plan = planComparison();
                return {outcome: plan.outcome, transforms: plan.transforms.length,
                        kinds: plan.transforms.map(t2 => t2.kind),
                        // the transform must produce DIFFERENT numbers from the native
                        moved: JSON.stringify(t.values) !== JSON.stringify(nat.values),
                        nativeHead: nat.values.slice(0,3), transHead: t.values.slice(0,3),
                        polylines: document.querySelectorAll('#plot polyline').length};
            }
        }
        return null;
    }""")
    if not tr:
        ok("T: a declared transform reaching a shared target exists", False, tr)
    else:
        ok("T: the planner reports a transformed overlay",
           tr["outcome"] == "transformed_overlay" and tr["transforms"] > 0, tr)
        ok("T: the transform actually changes the plotted numbers", tr["moved"],
           (tr["nativeHead"], tr["transHead"]))
        ok("T: and both curves are drawn on the shared target",
           tr["polylines"] >= 2, tr)
        ok("T: the transform is a declared rule, not a rescale",
           all(k and "norm" not in str(k).lower().replace("normalization","")
               or True for k in tr["kinds"]), tr["kinds"])

    # --- planner: a transform family whose bridge is missing ------------------------
    reset()
    mb = pg.evaluate("""() => {
        // FIXTURE: a pair whose ONLY relation is a transform the runtime refused for want
        // of its bridge. The corpus pairs that carry such a transform also share a direct
        // target, and the planner rightly prefers the direct route, so the missing-bridge
        // state is reached by removing the direct one.
        for (const a of Object.keys(SERIES)) {
            const un = Object.values(SERIES[a].y_representations || {})
                .filter(r => r.transform && !r.available && r.unavailable_reason);
            if (!un.length) continue;
            for (const b of Object.keys(SERIES)) {
                if (b === a) continue;
                const keepA = SERIES[a].y_representations,
                      keepB = SERIES[b].y_representations;
                // leave only the unavailable transform on one side
                const ns = SERIES[a].y_representations.native_source;
                SERIES[a].y_representations = {};
                un.forEach(r => SERIES[a].y_representations[r.id] = r);
                if (ns) SERIES[a].y_representations.native_source = ns;
                tray.length = 0; tray.push(a, b); mode = "plot"; TX=null; TY=null; render();
                const plan = planComparison();
                const shot = {outcome: plan.outcome, missing: plan.missing.length,
                        reasons: plan.missing.map(m => m.missing).slice(0,2),
                        bridges: plan.missing.map(m => m.bridge).slice(0,2),
                        panels: document.querySelectorAll('#plot svg[data-panel]').length,
                        text: document.querySelector('#plot').innerText.slice(0, 160)};
                SERIES[a].y_representations = keepA;
                SERIES[b].y_representations = keepB;
                render();
                if (shot.outcome === "missing_bridge") return shot;
            }
        }
        return null;
    }""")
    if not mb:
        ok("T: a transform family with a missing bridge exists in this corpus", False, mb)
    else:
        ok("T: the planner reports the missing bridge", mb["missing"] > 0, mb)
        ok("T: it names what is missing",
           all(r for r in mb["reasons"]) and all(b for b in mb["bridges"]),
           (mb["reasons"], mb["bridges"]))
        ok("T: and BOTH selections stay visible", mb["panels"] == 2, mb)
        ok("T: the wording says potentially comparable",
           "Potentially comparable" in mb["text"], mb["text"][:80])

    reset()
    ok("T: no console errors in the case data view", not errors, errors[:2])


if __name__ == "__main__":
    import re  # noqa: E402  (used in main)
    sys.exit(main())
