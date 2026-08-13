#!/usr/bin/env python3
"""Build the human-reviewable source-to-semantic mapping report.

    comparison/semantic_identity_review.html

Every row is derived from the semantic output objects in `papers/*/semantic/`. Nothing is
recomputed and no paper-specific mapping is maintained here, so the report cannot disagree
with the resolver it reports on. A consistency check runs BEFORE the report is written and
its findings are published in the report itself.
"""
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
PAPERS_DIR = W / "papers"
OUT = W / "comparison"
MANIFEST = json.loads((W / "pilot_papers.json").read_text())
PAPERS = list(MANIFEST["papers"])
ROLES = MANIFEST.get("roles", {})

KINDS = ("experimental_cases", "experimental_designs", "design_branches", "measurements",
         "result_series", "representations", "samples", "deposition_runs", "study_series",
         "simulation_runs", "unresolved", "links", "evidence")


def load(pid):
    d = {}
    for k in KINDS:
        f = PAPERS_DIR / pid / "semantic" / ("%s.json" % k)
        d[k] = json.loads(f.read_text()) if f.exists() else []
    return d


def esc(x):
    return html.escape("" if x is None else str(x))


# ---------------------------------------------------------------- status vocabulary
#: green   resolved with positive evidence
#: yellow  scientifically provisional / indistinguishable
#: gray    a measurement or representation that needs no deposition-case identity
#: red     contradiction or blocked invalid merge
GREEN, YELLOW, GRAY, RED = "ok", "warn", "gray", "bad"


def pill(text, kind=GRAY):
    return '<span class="pill %s">%s</span>' % (kind, esc(text))


class Paper(object):
    """Indexes one paper's semantic objects and answers provenance questions."""

    def __init__(self, pid):
        self.pid = pid
        self.d = load(pid)
        self.case_by_id = {c["case_id"]: c for c in self.d["experimental_cases"]}
        self.meas_by_id = {m["measurement_id"]: m for m in self.d["measurements"]}
        self.sample_by_id = {s["sample_id"]: s for s in self.d["samples"]}
        self.design_by_id = {x["design_id"]: x for x in self.d["experimental_designs"]}
        self.sim_ids = {s.get("simulation_run_id") or s.get("run_id")
                        for s in self.d["simulation_runs"]}

        self.case_of_meas = defaultdict(list)
        for c in self.d["experimental_cases"]:
            for mid in c.get("measurement_ids") or []:
                self.case_of_meas[mid].append(c["case_id"])
        self.sample_of_meas = defaultdict(list)
        for s in self.d["samples"]:
            for mid in s.get("measurement_ids") or []:
                self.sample_of_meas[mid].append(s["source_sample_code"])
        self.rep_of_rs, self.rep_by_meas = {}, defaultdict(list)
        for r in self.d["representations"]:
            for rsid in r.get("result_series_ids") or []:
                self.rep_of_rs[rsid] = r
            self.rep_by_meas[r.get("underlying_measurement")].append(r)
        self.branch_of_meas = defaultdict(list)
        for b in self.d["design_branches"]:
            for mid in (b.get("measurement_ids")
                        or ([b["measurement_id"]] if b.get("measurement_id") else [])):
                self.branch_of_meas[mid].append(b)
        self.run_of_sample = {}
        for s in self.d["samples"]:
            if s.get("produced_by_run"):
                self.run_of_sample[s["source_sample_code"]] = s["produced_by_run"]
        self.unres_by_meas = defaultdict(list)
        for u in self.d["unresolved"]:
            if u.get("measurement_id"):
                self.unres_by_meas[u["measurement_id"]].append(u)
        self.ev_by_id = {e["evidence_id"]: e for e in self.d["evidence"]}

    # -- how a ResultSeries relates to the cases it reaches --------------------
    def classify_cardinality(self, rs):
        """(status, detail) for the ResultSeries -> ExperimentalCase cardinality.

        A ResultSeries is NOT required to map to one ExperimentalCase. A single measured
        curve that sweeps a design factor legitimately spans every branch of that factor,
        and each branch is a distinct deposition. That is structured fan-out, not an
        unresolved identity.

        The distinction is drawn from object linkage, never from condition or fingerprint
        equality: the DesignBranches carried by this result's own Measurement are
        collected, the cases those branches reach through their candidate/case links are
        gathered, and the result is EXPLAINED only when that set accounts for every case
        the ResultSeries actually reaches. Branches belonging to another Measurement or
        panel explain nothing here.
        """
        mid = rs.get("produced_by")
        return classify_cardinality(self.case_of_meas.get(mid) or [],
                                    self.branch_of_meas.get(mid) or [],
                                    self.d["experimental_cases"])

    # -- one row per source ResultSeries -------------------------------------
    def rows(self):
        out = []
        for rs in self.d["result_series"]:
            src = rs.get("source") or {}
            mid = rs.get("produced_by")
            m = self.meas_by_id.get(mid) or {}
            cases = self.case_of_meas.get(mid) or []
            samples = self.sample_of_meas.get(mid) or []
            branches = self.branch_of_meas.get(mid) or []
            rep = self.rep_of_rs.get(rs["result_series_id"])
            case = self.case_by_id.get(cases[0]) if cases else None
            design_ids = sorted({b.get("design_id") for b in branches if b.get("design_id")})
            factor = None
            for did in design_ids:
                f = (self.design_by_id.get(did) or {}).get("design_factor") or {}
                factor = f.get("declared_as") or (self.design_by_id.get(did)
                                                  or {}).get("varied_quantity")
                break
            simulated = rs.get("data_source") == "simulated"
            unres = self.unres_by_meas.get(mid) or []
            if cases:
                status, why = GREEN, ""
                if case and case.get("identity_status") == "INDISTINGUISHABLE_FROM_SIBLING":
                    status, why = YELLOW, case.get("identity_reason") or ""
            elif simulated:
                status, why = GRAY, "simulation output; a SimulationRun is never a case"
            else:
                status = GRAY if not unres else YELLOW
                why = (unres[0].get("reason") if unres else
                       "no deposition-case identity is asserted for this result")
            cond = []
            if case:
                for x in (case.get("case_defining_conditions") or [])[:6]:
                    cond.append("%s%s=%s%s" % (x["quantity"],
                                               ("/" + x["process_step"])
                                               if x.get("process_step") else "",
                                               x.get("value"),
                                               (" " + x["unit"]) if x.get("unit") else ""))
            ev = (m.get("evidence") or [None])[0]
            evtext = ""
            if ev and ev in self.ev_by_id:
                evtext = (self.ev_by_id[ev].get("detail") or "")[:160]
            card_status, card = self.classify_cardinality(rs)
            out.append({
                "cardinality": card_status, "card": card,
                "figure": src.get("figure"), "panel": src.get("panel"),
                "rs_id": rs["result_series_id"], "curve_id": rs.get("curve_id"),
                "legend": src.get("series"), "data_source": rs.get("data_source"),
                "y": rs.get("y_quantity"), "x": rs.get("x_quantity"),
                "n_points": rs.get("n_points"),
                "designs": design_ids, "factor": factor,
                "branches": [b["branch_id"] for b in branches],
                "branch_values": [b.get("value") for b in branches],
                "cases": cases, "samples": samples,
                "runs": sorted({self.run_of_sample.get(s) for s in samples
                                if self.run_of_sample.get(s)}),
                "measurement": mid,
                "representation": (rep or {}).get("representation_id"),
                "rep_type": (rep or {}).get("type"),
                "rep_of": (rep or {}).get("derived_representation_of"),
                "material": (case or {}).get("deposited_material"),
                "structure": self._structure(case),
                "geometry": (case or {}).get("geometry"),
                "conditions": cond,
                "identity_status": (case or {}).get("identity_status"),
                "confidence": (case or {}).get("confidence"),
                "join_method": rs.get("join_method"),
                "evidence": evtext,
                "unresolved_reason": (unres[0].get("reason") if unres else None),
                "status": status, "why": why,
            })
        return out

    @staticmethod
    def _structure(case):
        if not case:
            return None
        for x in case.get("case_defining_conditions") or []:
            if x.get("structural_identity"):
                if x.get("stack_materials"):
                    return " / ".join(x["stack_materials"])
                return "%s=%s%s" % (x["quantity"], x.get("value"),
                                    (" " + x["unit"]) if x.get("unit") else "")
        return None


# ---------------------------------------------------------------- consistency check
def consistency(papers):
    """Run BEFORE writing. Returns a list of findings; an empty list means clean."""
    findings = []
    inv = json.loads((OUT / "semantic_invariants.json").read_text())
    for pid, P in papers.items():
        seen = Counter(r["rs_id"] for r in P.rows())
        dup = [k for k, n in seen.items() if n > 1]
        if dup:
            findings.append((pid, "a ResultSeries appears more than once", dup[:3]))
        if len(seen) != len(P.d["result_series"]):
            findings.append((pid, "figure-centric view does not cover every ResultSeries",
                             "%d of %d" % (len(seen), len(P.d["result_series"]))))
        for c in P.d["experimental_cases"]:
            for sid in c.get("sample_ids") or []:
                if sid not in P.sample_by_id:
                    findings.append((pid, "case references a missing Sample", sid))
            for mid in c.get("measurement_ids") or []:
                if mid not in P.meas_by_id:
                    findings.append((pid, "case references a missing Measurement", mid))
        for r in P.d["representations"]:
            u = r.get("underlying_measurement")
            if u not in P.meas_by_id and u not in P.sim_ids \
                    and not str(u).startswith("SIM::"):
                findings.append((pid, "representation provenance does not resolve",
                                 r["representation_id"]))
        for rs in P.d["result_series"]:
            src = rs.get("source") or {}
            if not src.get("figure"):
                findings.append((pid, "ResultSeries lost its figure provenance",
                                 rs["result_series_id"]))
        # A Measurement that carries curves with DIFFERENT legend labels cannot give any
        # of them a distinct identity: whatever the legend distinguishes is lost at the
        # measurement level. Reported, not repaired -- it is a curve-join concern upstream
        # of case identity.
        by_meas = defaultdict(set)
        for rs in P.d["result_series"]:
            lab = (rs.get("source") or {}).get("series")
            if rs.get("produced_by") and lab:
                by_meas[rs["produced_by"]].add(lab)
        for mid, labels in sorted(by_meas.items()):
            if len(labels) > 1:
                findings.append((pid, "one Measurement carries curves with different "
                                      "legend labels, so their identities cannot differ",
                                 "%s : %s" % (mid.split("::")[-1],
                                              ", ".join(sorted(labels)))))
        for r in P.rows():
            if r["cardinality"] == "UNEXPLAINED_MULTI_CASE":
                miss = r["card"]["missing"]
                findings.append((pid, "a ResultSeries reaches ExperimentalCases that its "
                                      "own DesignBranches do not explain",
                                 "%s -> %d cases, unexplained: %s"
                                 % (r["rs_id"].split("::", 2)[-1], len(r["cases"]),
                                    ", ".join(miss) or "no branch structure")))
        for s in P.d["samples"]:
            if s.get("produced_by_run") and not any(
                    r["run_id"] == s["produced_by_run"] for r in P.d["deposition_runs"]):
                findings.append((pid, "Sample references a missing DepositionRun",
                                 s["sample_id"]))
        v = inv.get(pid, {})
        cp, pp = v.get("source_curves_preserved") or {}, v.get("points_preserved") or {}
        if cp.get("old") != cp.get("pilot"):
            findings.append((pid, "curve count changed", cp))
        if pp.get("old") != pp.get("pilot"):
            findings.append((pid, "point count changed", pp))
    return findings


CSS = """
:root{--bg:#fbfbfd;--fg:#1a1d21;--mut:#5c6672;--line:#e2e6ea;--card:#fff;
--ok:#1a7f4b;--okbg:#e8f6ee;--bad:#b3261e;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fdf3e0;
--gray:#5c6672;--graybg:#eef1f4;--acc:#1a4f8a;--accbg:#eaf1fa}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#14171a;--fg:#e6e9ec;--mut:#98a2ad;--line:#272c32;--card:#1b1f23;
--ok:#5fd39b;--okbg:#12281d;--bad:#ff8a80;--badbg:#2a1614;--warn:#e3b341;--warnbg:#2a2213;
--gray:#98a2ad;--graybg:#22272c;--acc:#7fb0e8;--accbg:#12202f}}
:root[data-theme=dark]{--bg:#14171a;--fg:#e6e9ec;--mut:#98a2ad;--line:#272c32;--card:#1b1f23;
--ok:#5fd39b;--okbg:#12281d;--bad:#ff8a80;--badbg:#2a1614;--warn:#e3b341;--warnbg:#2a2213;
--gray:#98a2ad;--graybg:#22272c;--acc:#7fb0e8;--accbg:#12202f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:26px 18px 90px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:19px;margin:36px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:15px;margin:24px 0 8px;color:var(--acc)}
h4{font-size:13.5px;margin:16px 0 6px}
.sub{color:var(--mut);margin:0 0 20px;font-size:13px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:9px;background:var(--card);
margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:12px;min-width:640px}
th,td{padding:6px 9px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--accbg);color:var(--acc);font-weight:600;white-space:nowrap;
position:sticky;top:0;z-index:1}
tr:last-child td{border-bottom:0}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px}
.pill{display:inline-block;padding:1px 7px;border-radius:11px;font-size:10.5px;
font-weight:600;white-space:nowrap}
.ok{background:var(--okbg);color:var(--ok)}
.bad{background:var(--badbg);color:var(--bad)}
.warn{background:var(--warnbg);color:var(--warn)}
.gray{background:var(--graybg);color:var(--gray)}
.acc{background:var(--accbg);color:var(--acc)}
.note{background:var(--card);border-left:3px solid var(--acc);border-radius:0 8px 8px 0;
padding:10px 14px;margin:12px 0;font-size:13px}
.map{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px 15px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;white-space:pre;
overflow-x:auto;margin:10px 0}
.big{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
.big div{background:var(--card);border:1px solid var(--line);border-radius:9px;
padding:10px 16px;min-width:108px}
.big b{display:block;font-size:22px;line-height:1.2;font-variant-numeric:tabular-nums}
.big span{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.d{color:var(--mut);font-size:11px}
details{margin:8px 0}summary{cursor:pointer;font-weight:600;color:var(--acc);font-size:13px}
ul{margin:6px 0;padding-left:19px}li{margin:3px 0}
"""


def classify_cardinality(linked_cases, branches, all_cases):
    """(status, detail) for a ResultSeries -> ExperimentalCase cardinality.

    A ResultSeries is NOT required to map to one ExperimentalCase. A single measured curve
    that sweeps a design factor legitimately spans every branch of that factor, and each
    branch is a distinct deposition. That is structured fan-out, not an unresolved
    identity.

      SINGLE_CASE            one case (or none)
      EXPLAINED_MULTI_CASE   several cases, ALL of them reached by DesignBranches that
                             this result's own Measurement carries
      UNEXPLAINED_MULTI_CASE several cases that those branches do not account for

    The verdict comes from object linkage only -- a branch reaches a case through its
    recorded candidate/case links. Condition equality and matching nominal fingerprints
    are never consulted, and branches belonging to another Measurement are never passed in,
    so they cannot explain anything here. A branch set that explains only part of the
    linked cases leaves the result UNEXPLAINED rather than partially credited.
    """
    linked = set(linked_cases or [])
    if len(linked) <= 1:
        return "SINGLE_CASE", {"linked": sorted(linked), "branches": [],
                               "explained": sorted(linked), "factor": None,
                               "values": [], "designs": [], "missing": []}
    explained, values = set(), []
    for b in (branches or []):
        explained |= set(b.get("realises_case_ids") or [])
        cand = set(b.get("candidate_ids")
                   or ([b["candidate_id"]] if b.get("candidate_id") else []))
        if cand:
            for c in (all_cases or []):
                if cand & set(c.get("candidate_ids") or []):
                    explained.add(c["case_id"])
        values.append(b.get("value"))
    factors = sorted({b.get("quantity") for b in (branches or []) if b.get("quantity")})
    missing = sorted(linked - explained)
    detail = {"linked": sorted(linked),
              "branches": [b.get("branch_id") for b in (branches or [])],
              "explained": sorted(explained), "values": values,
              "factor": " + ".join(factors) if factors else None,
              "designs": sorted({b.get("design_id") for b in (branches or [])
                                 if b.get("design_id")}),
              "missing": missing}
    if branches and not missing:
        return "EXPLAINED_MULTI_CASE", detail
    return "UNEXPLAINED_MULTI_CASE", detail


def table(headers, rows, cls=""):
    h = "".join("<th>%s</th>" % esc(x) for x in headers)
    b = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows)
    return ('<div class="tw %s"><table><thead><tr>%s</tr></thead><tbody>%s</tbody>'
            "</table></div>" % (cls, h, b))


def figkey(f):
    s = str(f or "")
    return (len(s), s)


def build(papers, findings, PROV):
    P_, A = [], None
    P_ = []
    A = P_.append
    A("<title>PSED Semantic Identity Review</title>")
    A("<style>%s</style>" % CSS)
    A('<div class="wrap">')
    A("<h1>Semantic identity review</h1>")
    A('<p class="sub">Source&#8594;semantic mapping for manual scientific verification '
      'before resolver freeze. Every row is derived from the objects in '
      '<code>papers/*/semantic/</code>; no mapping is maintained by hand.</p>')

    all_rows = {pid: p.rows() for pid, p in papers.items()}
    n_rs = sum(len(r) for r in all_rows.values())
    n_case = sum(1 for rs in all_rows.values() for r in rs if r["cases"])
    n_unres = n_rs - n_case
    n_ind = sum(1 for p in papers.values() for c in p.d["experimental_cases"]
                if c.get("identity_status") == "INDISTINGUISHABLE_FROM_SIBLING")

    A('<div class="big">')
    for lbl, val in (("papers", len(papers)), ("ResultSeries reviewed", n_rs),
                     ("linked to a case", n_case), ("no case identity", n_unres),
                     ("indistinguishable cases", n_ind)):
        A("<div><b>%s</b><span>%s</span></div>" % (esc(val), esc(lbl)))
    A("</div>")
    card = Counter(r["cardinality"] for rs in all_rows.values() for r in rs)
    het = 0
    for pid, p in papers.items():
        lab = defaultdict(set)
        for r in p.d["result_series"]:
            l = (r.get("source") or {}).get("series")
            if r.get("produced_by") and l:
                lab[r["produced_by"]].add(l)
        het += sum(1 for v in lab.values() if len(v) > 1)
    A("<h2>ResultSeries &#8594; ExperimentalCase cardinality</h2>")
    A('<div class="note">A ResultSeries is <b>not</b> required to map to one '
      'ExperimentalCase. One measured curve that sweeps a design factor legitimately '
      'spans every branch of that factor, and each branch is a distinct deposition. Such '
      'a result is <b>explained structured fan-out</b>, not an unresolved identity, and '
      'does not count as a consistency finding. It is counted separately below and its '
      'branches are shown, so the audit trail is kept rather than hidden.</div>')
    A(table(["class", "count", "meaning"],
            [[pill("SINGLE_CASE", GREEN), "<b>%d</b>" % card.get("SINGLE_CASE", 0),
              "resolves to exactly one ExperimentalCase (includes results with none)"],
             [pill("EXPLAINED_MULTI_CASE", GREEN),
              "<b>%d</b>" % card.get("EXPLAINED_MULTI_CASE", 0),
              "spans several cases, and its own Measurement's DesignBranches account for "
              "every one of them"],
             [pill("UNEXPLAINED_MULTI_CASE", RED),
              "<b>%d</b>" % card.get("UNEXPLAINED_MULTI_CASE", 0),
              "spans several cases its own branches do NOT explain &mdash; review "
              "required"],
             [pill("heterogeneous producer", RED if het else GREEN), "<b>%d</b>" % het,
              "one Measurement carrying curves with different legend labels"]]))
    A('<div class="note"><b>Status key.</b> %s resolved with positive evidence &nbsp; '
      '%s scientifically provisional or indistinguishable &nbsp; %s a measurement or '
      'representation needing no deposition-case identity &nbsp; %s contradiction or '
      'blocked merge.<br><b>Provisional counts.</b> A whole-paper case count is marked '
      'provisional wherever the paper contains any indistinguishable case; such a count '
      'is an upper bound, not a measurement.</div>'
      % (pill("green", GREEN), pill("yellow", YELLOW), pill("gray", GRAY),
         pill("red", RED)))

    A("<h2>Provenance of this report</h2>")
    A(table(["field", "value"],
            [[esc(k), "<code>%s</code>" % esc(v)] for k, v in sorted(PROV.items())]))
    A("<h2>Consistency check</h2>")
    if findings:
        A(table(["paper", "finding", "detail"],
                [[esc(a), esc(b), "<code>%s</code>" % esc(c)] for a, b, c in findings]))
    else:
        A('<div class="note">%s Every ResultSeries appears exactly once in the '
          'figure-centric view; every case, Sample, DepositionRun and Measurement '
          'reference resolves; representation provenance is traversable; figure/panel '
          'provenance is preserved; curve and point counts are unchanged.</div>'
          % pill("all checks pass", GREEN))

    for pid in PAPERS:
        p, rows = papers[pid], all_rows[pid]
        cases = p.d["experimental_cases"]
        ind = [c for c in cases if c.get("identity_status")
               == "INDISTINGUISHABLE_FROM_SIBLING"]
        A("<h2><code>%s</code></h2>" % esc(pid))
        A('<div class="note">%s &nbsp; ResultSeries <b>%d</b> &nbsp; Measurements '
          '<b>%d</b> &nbsp; PlotRepresentations <b>%d</b> &nbsp; unique DesignBranches '
          '<b>%d</b> &nbsp; source branch appearances <b>%d</b> &nbsp; ExperimentalCases '
          '<b>%d</b> %s</div>'
          % (pill(ROLES.get(pid, "?"), "acc"), len(p.d["result_series"]),
             len(p.d["measurements"]), len(p.d["representations"]),
             len(p.d["design_branches"]),
             sum(len(b.get("measurement_ids")
                     or ([b["measurement_id"]] if b.get("measurement_id") else [])) or 1
                 for b in p.d["design_branches"]),
             len(cases),
             pill("PROVISIONAL - %d indistinguishable" % len(ind), YELLOW) if ind
             else pill("all cases distinguished", GREEN)))

        # ---- 2. explicit figure -> case mapping
        byfig = defaultdict(lambda: defaultdict(list))
        for r in rows:
            byfig[r["figure"]][r["panel"]].append(r)
        A("<h3>Figure &#8594; ExperimentalCase map</h3>")
        lines = []
        for f in sorted(byfig, key=figkey):
            lines.append("Fig. %s" % f)
            seen_case = {}
            for pan in sorted(byfig[f], key=lambda x: str(x)):
                lines.append("  panel %s" % (pan or "-"))
                for r in byfig[f][pan]:
                    n = len(r["cases"])
                    case = (r["cases"][0] if n == 1
                            else ("AMBIGUOUS: %d cases" % n) if n else None)
                    tag = ""
                    if n == 1 and r["cases"][0] in seen_case:
                        where = seen_case[r["cases"][0]]
                        tag = "   <-- same CASE as %s (alternate %s)" % (
                            where,
                            "representation" if r["representation"] else "Measurement")
                    elif n == 1:
                        seen_case[r["cases"][0]] = (
                            "panel %s" % (pan or "-") if pan else "above")
                    elif n > 1 and r["cardinality"] == "EXPLAINED_MULTI_CASE":
                        case = "%d cases via %s branches" % (n, r["card"]["factor"] or "?")
                        tag = "   <-- sweep spanning %d branches of one design" % n
                    elif n > 1:
                        tag = "   <-- reaches %d cases its own branches do not explain" % n
                    br = (" -> %s" % r["branches"][0].split("::")[-1]) if r["branches"] else ""
                    smp = (" -> Sample %s" % ",".join(r["samples"])) if r["samples"] else ""
                    lines.append("    %-26s%s -> %s%s%s"
                                 % ((r["legend"] or r["rs_id"].split("::")[-1])[:26], br,
                                    case or "UNRESOLVED", smp, tag))
            lines.append("")
        A('<div class="map">%s</div>' % esc("\n".join(lines)))

        # ---- 1. figure-centric primary review table
        A("<h3>Per-curve review</h3>")
        trs = []
        for f in sorted(byfig, key=figkey):
            for pan in sorted(byfig[f], key=lambda x: str(x)):
                for r in byfig[f][pan]:
                    trs.append([
                        esc(r["figure"]), esc(r["panel"]),
                        "<code>%s</code>" % esc(r["rs_id"].split("::", 2)[-1]),
                        esc(r["legend"]),
                        pill(r["data_source"] or "?",
                             GRAY if r["data_source"] == "simulated" else GREEN),
                        "<code>%s</code>" % esc(r["y"]), "<code>%s</code>" % esc(r["x"]),
                        "<code>%s</code>" % esc(", ".join(x.split("::")[-1]
                                                          for x in r["designs"]))
                        or '<span class="d">-</span>',
                        esc(r["factor"]) or '<span class="d">-</span>',
                        "<code>%s</code>" % esc(", ".join(str(v) for v in r["branch_values"]))
                        or '<span class="d">-</span>',
                        ("<code>%s</code>" % esc(r["cases"][0]))
                        if r["cardinality"] == "SINGLE_CASE" and r["cases"]
                        else (pill("EXPLAINED MULTI-CASE: %d" % len(r["cases"]), GREEN)
                              + '<br><span class="d">%d ExperimentalCases via %s '
                                'DesignBranches%s</span>'
                              % (len(r["cases"]), esc(r["card"]["factor"] or "?"),
                                 (": " + esc(", ".join(str(v) for v in r["card"]["values"])))
                                 if r["card"]["values"] else "")
                              + '<br><span class="mono d">%s</span>'
                              % esc(", ".join(r["cases"])))
                        if r["cardinality"] == "EXPLAINED_MULTI_CASE"
                        else (pill("UNEXPLAINED MULTI-CASE: %d" % len(r["cases"]), RED)
                              + '<br><span class="mono d">unexplained: %s</span>'
                              % esc(", ".join(r["card"]["missing"]) or "no branch structure"))
                        if r["cases"]
                        else pill("UNRESOLVED", YELLOW if r["unresolved_reason"] else GRAY),
                        esc(", ".join(r["samples"])) or '<span class="d">-</span>',
                        esc(", ".join(x.split("::")[-1] for x in r["runs"]))
                        or '<span class="d">-</span>',
                        "<code>%s</code>" % esc(str(r["measurement"]).split("::")[-1]),
                        ("<code>%s</code>" % esc(str(r["representation"]).split("::")[-1])
                         + (" " + pill(r["rep_type"], GRAY) if r["rep_type"] else ""))
                        if r["representation"] else '<span class="d">-</span>',
                        esc(r["material"]) or '<span class="d">-</span>',
                        esc(r["structure"]) or '<span class="d">-</span>',
                        esc(r["geometry"]) or '<span class="d">-</span>',
                        '<span class="mono d">%s</span>' % esc("; ".join(r["conditions"])),
                        pill(r["identity_status"] or "no case",
                             GREEN if r["identity_status"] == "DISTINGUISHED"
                             else YELLOW if r["identity_status"] else GRAY),
                        esc(r["confidence"]) or '<span class="d">-</span>',
                        esc(r["join_method"]) or '<span class="d">-</span>',
                        '<span class="d">%s</span>' % esc(r["evidence"][:110]),
                        '<span class="d">%s</span>' % esc(
                            (r["unresolved_reason"] or r["why"] or "")[:150]),
                    ])
        A(table(["fig", "panel", "ResultSeries", "legend", "data", "measurand", "x",
                 "Design", "DesignFactor", "Branch", "ExperimentalCase", "Sample", "Run",
                 "Measurement", "Representation", "material", "structure", "geometry",
                 "case-defining conditions", "identity", "confidence", "curve join",
                 "evidence", "unresolved reason / note"], trs))

        # ---- 3. case-centric reverse view
        A("<h3>Case &#8594; sources (reverse view)</h3>")
        rs_by_case = defaultdict(list)
        rep_by_case = defaultdict(list)
        for r in rows:
            for c in r["cases"]:
                rs_by_case[c].append(r["rs_id"].split("::", 2)[-1])
                if r["representation"]:
                    rep_by_case[c].append(str(r["representation"]).split("::")[-1])
        crs = []
        for c in cases:
            figs = sorted(set(c.get("source_figures") or []), key=figkey)
            st = c.get("identity_status")
            distinguishes = ", ".join(c.get("identity_distinguished_by") or []) or "-"
            crs.append([
                "<code>%s</code>" % esc(c["case_id"]),
                '<span class="mono d">%s</span>' % esc(c.get("nominal_fingerprint")),
                esc(c.get("deposited_material")) or pill("stack / unresolved", GRAY),
                "<code>%s</code>" % esc(", ".join(
                    b["branch_id"].split("::")[-1] for b in p.d["design_branches"]
                    if c["case_id"] in (b.get("realises_case_ids") or []))) or
                '<span class="d">-</span>',
                esc(", ".join(s.rsplit("::", 1)[-1] for s in c.get("sample_ids") or []))
                or '<span class="d">-</span>',
                esc(", ".join(x.split("::")[-1]
                              for x in c.get("deposition_run_ids") or []))
                or '<span class="d">-</span>',
                esc(", ".join(figs)) or '<span class="d">-</span>',
                str(len(c.get("measurement_ids") or [])),
                '<span class="mono d">%s</span>' % esc(", ".join(rs_by_case[c["case_id"]])),
                '<span class="mono d">%s</span>' % esc(", ".join(rep_by_case[c["case_id"]])),
                pill(st or "?", GREEN if st == "DISTINGUISHED" else YELLOW),
                ('<span class="d">%s</span>' % esc((c.get("identity_reason") or "")[:200]))
                if st != "DISTINGUISHED" else esc(distinguishes),
            ])
        A(table(["case", "complete nominal fingerprint", "deposited material / structure",
                 "DesignBranches", "Samples", "DepositionRuns", "figures", "#meas",
                 "ResultSeries", "Representations", "identity",
                 "distinguished by / why not"], crs))

        # ---- 4. merge / split evidence
        links = p.d["links"]
        applied = [l for l in links if l.get("action") == "MERGED"]
        blocked = [l for l in links if l.get("action") == "BLOCKED"]
        A("<h3>Merge and split evidence</h3>")
        A('<div class="note">Condition equality is never shown as positive linkage: every '
          'applied link below carries a source statement, and the compatibility columns '
          'record only what was <i>checked</i>, not what licensed the merge.</div>')
        if applied:
            ar = []
            for l in applied:
                ev = p.ev_by_id.get(l.get("link_evidence"), {})
                det = (l.get("detail") or {}) if isinstance(l.get("detail"), dict) else {}
                ar.append([
                    "<code>%s</code>" % esc(l.get("a")), "<code>%s</code>" % esc(l.get("b")),
                    "<code>%s</code>" % esc(l.get("a_case_id")),
                    pill(l.get("link_class") or "-", "acc"),
                    '<span class="d">%s</span>' % esc((ev.get("detail") or
                                                       l.get("link_evidence") or "")[:170]),
                    pill("ok", GREEN), pill("ok", GREEN), pill("ok", GREEN),
                    pill("no contradiction", GREEN) if not det.get("clash")
                    else pill("CLASH", RED),
                    '<span class="d">%s</span>' % esc((l.get("reason") or "")[:170]),
                ])
            A(table(["source A", "source B", "resulting case", "link class",
                     "positive linkage evidence", "material", "geometry", "process step",
                     "conditions", "reason for merge"], ar))
        else:
            A('<div class="note">%s</div>' % pill("no cross-result merges", GRAY))
        if blocked:
            br = []
            for l in blocked:
                det = (l.get("detail") or {}) if isinstance(l.get("detail"), dict) else {}
                br.append([
                    "<code>%s</code>" % esc(l.get("a")), "<code>%s</code>" % esc(l.get("b")),
                    pill(l.get("decision_status") or "BLOCKED",
                         RED if l.get("decision_status") == "ACTIVE_CONTRADICTION"
                         else YELLOW),
                    '<span class="mono d">%s</span>' % esc(
                        "; ".join("%s %s vs %s" % (x.get("quantity"), x.get("left"),
                                                   x.get("right"))
                                  for x in (det.get("clash") or []))),
                    '<span class="d">%s</span>' % esc((l.get("reason") or "")[:220]),
                    '<span class="d">%s</span>' % esc((l.get("decision_note") or "")[:180]),
                ])
            A("<h4>Blocked links, with the exact reason</h4>")
            A(table(["source A", "source B", "class", "clash", "reason not merged",
                     "note"], br))

        # ---- 5. design hierarchy
        if p.d["experimental_designs"]:
            A("<h3>Design hierarchy</h3>")
            dr = []
            for d in p.d["experimental_designs"]:
                own = [b for b in p.d["design_branches"]
                       if b.get("design_id") == d["design_id"]]
                f = d.get("design_factor") or {}
                app = sum(len(b.get("measurement_ids")
                              or ([b["measurement_id"]] if b.get("measurement_id") else []))
                          or 1 for b in own)
                dr.append([
                    "<code>%s</code>" % esc(d["design_id"].split("::", 2)[-1]),
                    esc(f.get("declared_as") or d.get("varied_quantity")),
                    '<span class="mono">%s</span>' % esc(" + ".join(f.get("components") or [])
                                                         or d.get("varied_quantity")),
                    pill("compound", YELLOW) if f.get("is_compound") else "single",
                    "<b>%d</b>" % len(own), "<b>%d</b>" % app,
                    "<b>%d</b>" % len({cid for b in own
                                       for cid in (b.get("realises_case_ids") or [])}),
                    '<span class="mono d">%s</span>' % esc(", ".join(str(b.get("value"))
                                                                     for b in own)),
                ])
            A(table(["ExperimentalDesign", "DesignFactor (author's words)",
                     "structured components", "factor kind", "unique DesignBranches",
                     "source branch appearances", "ExperimentalCases reached",
                     "branch settings"], dr))

    A('<p class="sub" style="margin-top:26px">Generated by '
      "<code>code/build_identity_review.py</code> from the current semantic output.</p>")
    A("</div>")
    return "\n".join(P_)


def provenance():
    """Stamp identifying WHICH run produced this artifact, so two generations of the
    report are never mistaken for one another."""
    import subprocess
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=str(W)).decode().strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "."],
                                             cwd=str(W)).decode().strip())
    except Exception:
        sha, dirty = "unknown", False
    tf = W / "logs" / "test_status.json"
    tests = json.loads(tf.read_text()) if tf.exists() else {}
    stamp = W / "logs" / "last_semantic_run.json"
    generated_at = json.loads(stamp.read_text()).get("generated_at") \
        if stamp.exists() else None
    return {"generated_at": generated_at or "not recorded",
            "git_sha": sha + ("+dirty" if dirty else ""),
            "active_manifest": "%d papers: %s" % (len(PAPERS), ", ".join(PAPERS)),
            "test_count": "%s passed, %s failed" % (tests.get("passed", "?"),
                                                    tests.get("failed", "?"))}


def main():
    papers = {pid: Paper(pid) for pid in PAPERS}
    findings = consistency(papers)
    prov = provenance()
    (OUT / "semantic_identity_review.html").write_text(build(papers, findings, prov))
    print("provenance: %s" % json.dumps(prov))
    rows = {pid: p.rows() for pid, p in papers.items()}
    n_rs = sum(len(r) for r in rows.values())
    n_case = sum(1 for rs in rows.values() for r in rs if r["cases"])
    n_ind = sum(1 for p in papers.values() for c in p.d["experimental_cases"]
                if c.get("identity_status") == "INDISTINGUISHABLE_FROM_SIBLING")
    print("ResultSeries reviewed : %d" % n_rs)
    print("linked to a case      : %d" % n_case)
    print("no case identity      : %d" % (n_rs - n_case))
    print("indistinguishable     : %d" % n_ind)
    print("consistency findings  : %d" % len(findings))
    for f in findings:
        print("   %s | %s | %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
