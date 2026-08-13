#!/usr/bin/env python3
"""The workbench data model: three levels, real links, and no invented parentage.

A researcher asks "which experiments used this chemistry", then "what was measured on
them", then "which of those results can I put on one axis". Each of those is a different
entity, and flattening ExperimentalCase to a single selectable curve destroys the two
joins that make the question answerable. So these tests pin the hierarchy itself:
Measurement belongs to a Case, ResultSeries belongs to a producer, and selection happens
at the ResultSeries level.

They also pin the things that would be easy to fake: a case id is only unique within its
paper, a Measurement the KG never linked to a case must not be attached to one, and a
canonical value must never be shown against a raw unit.

Run:  python3 tests/test_workbench_model.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

FR = W / "_diagnostics" / "final_review"
_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def main():
    dp = FR / "workbench_data.json"
    if not dp.exists():
        ok("workbench data exists", False, str(dp))
        print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
        return 1
    D = json.loads(dp.read_text())
    E, M, S = D["experiments"], D["measurements"], D["series"]
    A = D["audit"]

    print("=== A. three levels exist and are distinct ===")
    ok("A: experiments, measurements and series are separate collections",
       len(E) and len(M) and len(S) and not (set(E) & set(M)) and not (set(M) & set(S)))
    ok("A: the case count matches the frozen stack", len(E) == 182, len(E))
    ok("A: the series count matches the frozen stack", len(S) == 231, len(S))
    ok("A: measurements and simulation runs are both producers",
       A["measurements"] == 213 and A["simulation_runs"] == 34,
       (A["measurements"], A["simulation_runs"]))
    ok("A: no series is its own experiment",
       all("measurement_ids" not in s for s in S.values()))

    print("=== B. a case id alone is not unique; the key carries its paper ===")
    raw = [e["case_id"] for e in E.values()]
    ok("B: raw case ids collide across papers", len(set(raw)) < len(raw),
       (len(set(raw)), len(raw)))
    ok("B: the keyed collection does not", len(set(E)) == len(E))
    ok("B: every key names its paper",
       all(k.startswith(e["paper_id"] + "::") for k, e in E.items()))

    print("=== C. parent links resolve, and unresolved ones say so ===")
    dangling_case = [c for m in M.values() for c in m["case_ids"] if c not in E]
    ok("C: every measurement->case link resolves", not dangling_case, dangling_case[:3])
    dangling_prod = [s["series_id"] for s in S.values()
                     if s["producer_status"] == "LINKED" and s["producer_id"] not in M]
    ok("C: every series->producer link resolves", not dangling_prod, dangling_prod[:3])
    ok("C: a measurement with no case link is marked, not attached",
       all(m["case_link_status"] == "MEASUREMENT_CASE_LINK_UNRESOLVED"
           for m in M.values() if not m["case_ids"]))
    unlinked = [m for m in M.values() if not m["case_ids"]]
    ok("C: the corpus really does contain unlinked measurements", unlinked, len(unlinked))
    ok("C: and they are not silently listed under some case",
       not [m for m in unlinked
            if any(m["measurement_id"] in e["measurement_ids"] for e in E.values())])

    print("=== D. one case can expose several measurements ===")
    multi = [k for k, e in E.items() if len(e["measurement_ids"]) > 1]
    ok("D: multi-measurement cases exist", multi, len(multi))
    ok("D: the audit agrees", A["cases_2plus_measurements"] == len(multi),
       (A["cases_2plus_measurements"], len(multi)))
    ok("D: the deepest case is reported", A["max_measurements_per_case"] >= 2,
       A["max_measurements_per_case"])
    if multi:
        e = E[max(multi, key=lambda k: len(E[k]["measurement_ids"]))]
        ok("D: its measurements are distinct entities",
           len(set(e["measurement_ids"])) == len(e["measurement_ids"]))
        ok("D: each resolves to a real measurement",
           all(m in M for m in e["measurement_ids"]))

    print("=== E. producer -> series cardinality is reported, not assumed ===")
    per = [len(m["series_ids"]) for m in M.values()]
    ok("E: the audit records the real maximum",
       A["max_series_per_producer"] == (max(per) if per else 0), A["max_series_per_producer"])
    # this corpus happens to model one curve per producer; the model must not depend on it
    ok("E: series_ids is a list, so >1 is representable",
       all(isinstance(m["series_ids"], list) for m in M.values()))
    ok("E: the limitation is stated rather than hidden",
       any("more than one ResultSeries" in x for x in A["known_limitations"]),
       A["known_limitations"])

    print("=== F. selection happens at the series level ===")
    ok("F: every series carries the identity a tray row needs",
       all(s.get("series_id") and s.get("paper_id") is not None
           and "figure" in s for s in S.values()))
    ok("F: a series knows its producer, and through it its case",
       all(s["producer_id"] for s in S.values()))
    # a case exposes its series only THROUGH measurements, never directly
    ok("F: cases do not carry series ids directly",
       all("series_ids" not in e for e in E.values()))

    print("=== G. conditions live on the case, measurement metadata on the measurement ===")
    ok("G: cases carry conditions", any(e["conditions"] for e in E.values()))
    ok("G: measurements do not carry case conditions",
       all("conditions" not in m for m in M.values()))
    ok("G: measurements carry their own technique/settings fields",
       all("technique" in m and "settings" in m for m in M.values()))
    withc = [e for e in E.values() if e["conditions"]]
    ok("G: a condition keeps quantity, value and provenance",
       all(set(("quantity", "value", "provenance_type")) <= set(c)
           for e in withc[:20] for c in e["conditions"]))

    print("=== H. filter facets are derivable from the data alone ===")
    mats = {e["material"] for e in E.values() if e["material"]}
    ok("H: material facet is non-empty and comes from cases", mats, sorted(mats)[:6])
    prec = {p for e in E.values() for p in e["chemistry"].get("precursor", [])}
    core = {p for e in E.values() for p in e["chemistry"].get("coreactant", [])}
    ok("H: precursor and co-reactant stay separate roles",
       prec and core is not None, (sorted(prec)[:4], sorted(core)[:4]))
    yq = {s["y"]["quantity"] for s in S.values() if s["y"]["quantity"]}
    ok("H: result-quantity facet comes from series y quantities", yq, sorted(yq)[:6])
    tech = {m["technique"] for m in M.values() if m["technique"]}
    ok("H: technique is a single hashable label, not a list",
       all(m["technique"] is None or isinstance(m["technique"], str)
           for m in M.values()))
    ok("H: technique facet comes from measurements", tech, sorted(tech)[:4])

    print("=== I. result-quantity filtering joins through the real links ===")
    # the join a filter must make: case -> measurements -> series
    def series_of_case(k):
        return [sid for mid in E[k]["measurement_ids"] for sid in M[mid]["series_ids"]]
    hits = [k for k in E if any(S[s]["y"]["quantity"] == "film_thickness"
                                for s in series_of_case(k))]
    ok("I: cases can be found by a linked result quantity", hits, len(hits))
    ok("I: and every hit really owns such a series",
       all(any(S[s]["y"]["quantity"] == "film_thickness" for s in series_of_case(k))
           for k in hits))
    ok("I: the count is of cases, not of series",
       len(hits) <= len([s for s in S.values() if s["y"]["quantity"] == "film_thickness"]))

    print("=== J. canonical values are never shown against a raw unit ===")
    mism = [s["series_id"] for s in S.values()
            if s["points"] and s["x"]["raw_unit"] and s["x"]["unit"]
            and s["x"]["raw_unit"] != s["x"]["unit"]
            and max(abs(p[0]) for p in s["points"]) < 1e-9]
    ok("J: no profile carries suspiciously unscaled canonical values", not mism, mism[:3])
    ok("J: raw and canonical units are both retained, separately",
       all("raw_unit" in s["x"] and "unit" in s["x"] for s in S.values()))
    # the mm/um trap: a mm-printed profile must be carried in canonical um
    mm = [s for s in S.values() if s["points"] and s["x"]["raw_unit"] == "mm"]
    for s in mm[:3]:
        ok("J: %s printed in mm is carried in %s" % (s["series_id"][-28:], s["x"]["unit"]),
           max(abs(p[0]) for p in s["points"]) > 100, s["x"]["unit"])

    print("=== K. comparability comes from the frozen runtime, as data ===")
    pairs, tgts = D["pairs"], D["targets"]
    ok("K: pair decisions are embedded", pairs, len(pairs))
    ok("K: every pair states a profile status and both axis reasons",
       all(p.get("status") and p["x"].get("reason") and p["y"].get("reason")
           for p in pairs.values()))
    ok("K: shape-only is carried as a separate outcome, not the default",
       all("shape_only_status" in p for p in pairs.values()))
    ok("K: default and shape-only statuses differ for at least one pair",
       any(p["status"] != p["shape_only_status"] for p in pairs.values()))
    ok("K: representation targets are precomputed per series", tgts, len(tgts))
    ok("K: every target states availability and how it is reached",
       all("available" in t and "how" in t
           for v in tgts.values() for ax in ("x", "y") for t in v[ax]))
    unavailable = [t for v in tgts.values() for t in v["y"] if not t["available"]]
    ok("K: an unavailable target names what it would require",
       all(t.get("requires") or t.get("note") for t in unavailable), unavailable[:2])

    print("=== L. normalization identity is explicit ===")
    norms = {t.get("normalization") for v in tgts.values() for t in v["y"]}
    ok("L: distinct normalization definitions are offered separately",
       len({n for n in norms if n}) >= 2, sorted(n for n in norms if n))
    ok("L: t_over_t_max and t_over_t_entrance are never one option",
       not [t for v in tgts.values() for t in v["y"]
            if t.get("normalization") == "t_over_t_max" and "entrance" in str(t.get("label"))])
    # only the self-derivable basis is offered as available
    ent = [t for v in tgts.values() for t in v["y"]
           if t.get("normalization") == "t_over_t_entrance"]
    ok("L: an entrance basis is not offered as available without a reference",
       all(not t["available"] for t in ent), ent[:1])
    unknown = [s for s in S.values()
               if s["y"]["quantity"] == "normalized_thickness" and not s["y"]["norm"]]
    ok("L: normalized series with no recorded basis exist and keep norm=None",
       unknown, len(unknown))

    print("=== M. the page is self-contained and offline ===")
    hp = FR / "psed_experiment_comparison_workbench.html"
    ok("M: the workbench html exists", hp.exists())
    h = hp.read_text()
    ok("M: no remote script or style", "src=\"http" not in h and "@import" not in h
       and "cdn." not in h)
    ok("M: no fetch/XHR/websocket", not any(t in h for t in ("fetch(", "XMLHttpRequest",
                                                             "WebSocket")))
    ok("M: the data placeholder was substituted", "/*__DATA__*/" not in h)
    ok("M: it embeds the three collections",
       '"experiments"' in h and '"measurements"' in h and '"series"' in h)
    ok("M: the unresolved-parentage bucket is rendered",
       "unresolved parentage" in h)
    ok("M: the default landing view is the experiment explorer",
       h.index('id="v-explore"') < h.index('id="v-compare"')
       and 'class="view on" id="v-explore"' in h)

    print("=== N. the audit reports the hierarchy honestly ===")
    for k in ("experimental_cases", "measurements", "result_series",
              "cases_2plus_measurements", "max_measurements_per_case",
              "max_series_per_producer", "measurements_without_case"):
        ok("N: audit reports %s" % k, k in A, k)
    ok("N: unresolved producer links are zero", A["series_without_producer"] == 0)
    ok("N: the case-link gap is reported, not zeroed",
       A["measurements_without_case"] > 0, A["measurements_without_case"])

    print("=== O. the faceted filter engine, executed as shipped ===")
    # These run the page's OWN javascript under node against the embedded corpus, so the
    # contract is checked on the code that ships rather than on a Python restatement of it.
    facets = FR / "facet_contract_assertions.js"
    node = shutil.which("node")
    if not node:
        ok("O: node is unavailable, facet contract not executed", False, "install node")
    elif not facets.exists():
        ok("O: facet assertion script exists", False, str(facets))
    else:
        import re as _re
        h = (FR / "psed_experiment_comparison_workbench.html").read_text()
        js = _re.findall(r"<script>(.*?)</script>", h, _re.S)[-1]
        blob = _re.search(r'<script id="d" type="application/json">(.*?)</script>',
                          h, _re.S).group(1)
        head = js[:js.index("// ---- facet UI")].replace("const sel = [];", "")
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "run.js"
            run.write_text(
                "const DOC=" + blob + ";\n"
                "const document={getElementById:()=>({textContent:JSON.stringify(DOC)}),"
                "addEventListener:()=>{},querySelector:()=>null,querySelectorAll:()=>[]};\n"
                "const sel=[];\n" + head + "\n" + facets.read_text())
            r = subprocess.run([node, str(run)], capture_output=True, text=True)
        if r.returncode:
            ok("O: the shipped facet engine runs", False, r.stderr[:200])
        else:
            for x in json.loads(r.stdout):
                ok("O: " + x["name"], x["ok"], x.get("detail"))

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
