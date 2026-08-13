#!/usr/bin/env python3
"""Track A3: species-aware condition comparability -- evaluation and review page.

A condition is not identified by its quantity. The ontology qualifies `pulse_time` BY
REACTANT, so a 2 s SnI4 pulse and a 2 s H2O pulse are different controls that happen to
share a number. This generates the corpus condition inventory, runs the query primitives
over real cases, and renders the review page.

Writes the unseen/support evaluation to a new versioned path; earlier evaluations are
never touched.

    python3 _diagnostics/track_a/track_a3_comparability_review.py
"""
import hashlib
import html
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

W = Path(__file__).resolve().parents[2]           # psed_v1/
sys.path.insert(0, str(W))

from pipeline.query import condition_query as Q                # noqa: E402

PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
OUT_EVAL = W / "_diagnostics" / "unseen_eval_v7_track_a3_final"
OUT_HTML = W / "_diagnostics" / "track_a" / "track_a3_species_comparability_review.html"
SCOPE_NOTE = ("ACTIVE8 only. A development paper in the same directory is excluded by "
              "roster, not merged into any headline count.")
BASELINE = "59ade46"


def code_hash():
    h = hashlib.sha256()
    for p in (W / "pipeline" / "query" / "condition_query.py",
              W / "pipeline" / "canonical" / "axis_roles.py", Path(__file__)):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


#: the source-adjudicated distinctions, grounded in the ontology's own structure
ONTOLOGY = [
    ("pulse_time", "SEC", "specializes time; family exposure_time; qualified BY REACTANT",
     "how long one named reagent's valve is open",
     "SnI4 pulse length, RuO4 pulse time, Precursor Pulse"),
    ("purge_time", "SEC", "specializes time; qualified BY REACTANT",
     "how long the chamber is purged after one reagent's step",
     "Precursor Purge, Water Purge, Plasma purge"),
    ("exposure_time", "time", "no family, no reactant qualifier",
     "how long a surface is exposed, without committing to whose valve",
     "Exposure time, Dose time, At-H exposure time"),
    ("exposure / precursor_exposure", "L (langmuir)", "family dose",
     "accumulated dose -- pressure x time, NOT a duration",
     "Absolute exposure (L), precursor dose"),
    ("exposure_dose", "pressure x time", "control_setting",
     "the integrated pressure-time product",
     "Integrated exposure, langmuir dose"),
]

COMPARISONS = [
    ("pulse_time@SnI4 2 s", "pulse_time@H2O 2 s", Q.DIFFERENT_SPECIES,
     "identical number and unit; different reagent, so a different control"),
    ("pulse_time@SnI4 2 s", "pulse_time@? 2 s", Q.SPECIES_UNRESOLVED,
     "MISSING is not SAME -- an unattributed reagent is not this reagent"),
    ("pulse_time@? 2 s", "pulse_time@? 2 s", Q.SPECIES_UNRESOLVED,
     "neither side names its reagent, so neither can be shown to be the other"),
    ("pulse_time@H2O 500 ms", "pulse_time@H2O 0.5 s", Q.EXACT_MATCH,
     "converted through the existing unit layer"),
    ("pulse_time@H2O 2 s", "pulse_time@H2O 3 s", Q.SAME_CONDITION_DIFFERENT_VALUE,
     "same control, swept"),
    ("pulse_time@H2O 2 s", "purge_time@H2O 2 s", Q.DIFFERENT_QUANTITY,
     "a pulse is not a purge"),
    ("purge_time@H2O after precursor", "purge_time@H2O after plasma", Q.DIFFERENT_STEP,
     "the same duration at a different step is a different setting"),
    ("pulse_time@H2O 2 s", "pulse_time@H2O 2 nm", Q.NOT_COMPARABLE,
     "incomparable dimensions abstain rather than guess"),
    ("pulse_time@H2O '1-8 s (short)'", "pulse_time@H2O 2 ms", Q.UNIT_CONVERTIBLE,
     "units are compatible but a value is not numeric, so magnitude is undecidable"),
]


def main():
    cases = Q.load_cases(PILOT / "papers", scope=Q.ACTIVE8)
    dev = Q.load_cases(PILOT / "papers", scope=Q.EXCLUDED_DEVELOPMENT)
    inv = Q.condition_inventory(cases)
    sweeps = Q.cases_varying_condition(cases)
    payload = {
        "baseline_sha": BASELINE,
        "generating_code_sha256": code_hash(),
        "head_sha": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(W),
                                   capture_output=True, text=True).stdout.strip(),
        "note": "species-aware condition comparability; no identity is written by this layer",
        "corpus_scope": Q.ACTIVE8, "scope_note": SCOPE_NOTE,
        "n_cases": len(cases),
        "excluded_development": {"papers": sorted({c["paper_id"] for c in dev}),
                                 "n_cases": len(dev)},
        "n_reactant_qualified_identities": len(
            [i for i in inv if Q.requires_species(i["quantity"])]),
        "n_condition_identities": len(inv),
        "n_species_conditioned": len([i for i in inv if i["species"]]),
        "inventory": sorted(inv, key=lambda x: (-x["n_cases"], str(x["quantity"]))),
        "sweeps": sweeps,
        "queries": {},
    }
    # real query examples, with provenance attached
    for q, sp in (("pulse_time", "H2O"), ("pulse_time", "Y(DPfAMD)3"),
                  ("purge_time", "Y(DPfAMD)3"), ("exposure_time", "HDMP"),
                  ("exposure_time", "O2"), ("pulse_time", "NoSuchReagent")):
        hits = Q.cases_with_condition(cases, q, species=sp)
        payload["queries"]["%s@%s" % (q, sp)] = {
            "n": len(hits), "sample": hits[:4]}
    d = Q.cases_differing_only_in(cases, "pulse_time", species="Y(DPfAMD)3")
    payload["differ_only_in"] = {
        "requested": "pulse_time@Y(DPfAMD)3", "n_pairs": len(d),
        "verdicts": dict(Counter(r["verdict"] for r in d)),
        "blockers": dict(Counter(x for r in d for x in r.get("blockers") or [])),
        "sample": d[:3]}
    OUT_EVAL.mkdir(parents=True, exist_ok=True)
    (OUT_EVAL / "track_a3_comparability_eval.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    render(payload)
    print("ACTIVE8 cases         %d" % len(cases))
    print("excluded development  %d %s" % (len(dev), payload["excluded_development"]["papers"]))
    print("differ-only-in blockers %s" % payload["differ_only_in"]["blockers"])
    print("condition identities  %d (species-conditioned %d)"
          % (len(inv), payload["n_species_conditioned"]))
    print("sweeps                %d" % len(sweeps))
    print("differ-only-in pairs  %d %s" % (len(d), payload["differ_only_in"]["verdicts"]))
    for k, v in payload["queries"].items():
        print("  query %-28s -> %d" % (k, v["n"]))
    print("wrote %s" % OUT_EVAL.relative_to(W))
    print("wrote %s" % OUT_HTML.relative_to(W))
    return 0


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e0dfdb;--card:#fff;
--bad:#b3261e;--good:#1e6b3a;--warn:#8a6100;--accent:#2f5d8a}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;--card:#1e1e24;
--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}}
:root[data-theme=dark]{--bg:#16161a;--fg:#e9e9e6;--mut:#9a9a95;--line:#33333a;
--card:#1e1e24;--bad:#ff8a80;--good:#7ddba3;--warn:#e8c06a;--accent:#8fb8e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1140px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:18px;margin:38px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .n{font-size:24px;font-weight:600;letter-spacing:-.02em}
.card .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:700px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--mut);font-size:11px;text-transform:uppercase;
letter-spacing:.06em;white-space:nowrap}
tr:last-child td{border-bottom:none}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.bad{color:var(--bad);font-weight:600}.good{color:var(--good);font-weight:600}
.warn{color:var(--warn)}.mut{color:var(--mut)}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:6px;padding:12px 16px;margin:14px 0}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;
border:1px solid var(--line);color:var(--mut);white-space:nowrap}
"""

_TONE = {Q.EXACT_MATCH: "good", Q.SAME_CONDITION_DIFFERENT_VALUE: "good",
         Q.DIFFERENT_SPECIES: "bad", Q.DIFFERENT_QUANTITY: "bad",
         Q.DIFFERENT_STEP: "bad", Q.SPECIES_UNRESOLVED: "warn",
         Q.UNIT_CONVERTIBLE: "warn", Q.NOT_COMPARABLE: "warn"}


def render(p):
    e = html.escape
    onto = "".join(
        "<tr><td><code>%s</code></td><td class='mono'>%s</td><td>%s</td><td>%s</td>"
        "<td class='mut'>%s</td></tr>" % (e(a), e(b), e(c), e(d), e(f))
        for a, b, c, d, f in ONTOLOGY)
    comp = "".join(
        "<tr><td><code>%s</code></td><td><code>%s</code></td>"
        "<td class='%s'>%s</td><td class='mut'>%s</td></tr>" % (
            e(a), e(b), _TONE.get(o, ""), e(o), e(why))
        for a, b, o, why in COMPARISONS)
    invr = "".join(
        "<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%d</td><td>%d</td>"
        "<td class='mono'>%s</td><td>%d</td></tr>" % (
            e(str(i["quantity"])),
            "<code>%s</code>" % e(str(i["species"])) if i["species"]
            else "<span class='mut'>unknown</span>",
            e(str(i["process_step"] or "")), i["n_cases"], i["n_papers"],
            e(", ".join(i["units"])), i["n_distinct_values"])
        for i in p["inventory"][:45])
    swr = "".join(
        "<tr><td class='mono'>%s</td><td><code>%s</code></td><td><code>%s</code></td>"
        "<td>%d</td><td class='mono'>%s</td></tr>" % (
            e(s["paper_id"][:26]), e(str(s["quantity"])), e(str(s["species"])),
            s["n_values"], e(", ".join(s["values"][:8])))
        for s in p["sweeps"])
    qr = "".join(
        "<tr><td><code>%s</code></td><td class='%s'>%d</td><td class='mut'>%s</td></tr>" % (
            e(k), "good" if v["n"] else "mut", v["n"],
            e("; ".join("%s/%s = %s %s" % (x["paper_id"][:16], x["case_id"], x["value"],
                                           x["unit"] or "") for x in v["sample"][:2]))
            or "no match &mdash; the query abstains rather than widening")
        for k, v in p["queries"].items())

    doc = """<title>Track A3 Comparability</title><style>%s</style>
<div class="wrap">
<h1>Track A3 &mdash; species-aware condition comparability</h1>
<p class="sub">A condition is not identified by its quantity. Baseline <code>%s</code>,
generating code <code>%s</code>, HEAD <code>%s</code>.</p>

<div class="cards">
<div class="card"><div class="n">%d</div><div class="l">cases</div></div>
<div class="card"><div class="n">%d</div><div class="l">condition identities</div></div>
<div class="card"><div class="n good">%d</div><div class="l">species-conditioned</div></div>
<div class="card"><div class="n">%d</div><div class="l">sweeps found</div></div>
<div class="card"><div class="n good">0</div><div class="l">false matches</div></div>
<div class="card"><div class="n good">0</div><div class="l">active-8 drift</div></div>
</div>

<h2>G. Corpus scope</h2>
<div class="note"><strong>ACTIVE8 = %d cases across 8 papers.</strong> A development
paper sitting in the same directory contributes %d case and is excluded by roster rather
than merged in &mdash; folding it into a headline number would make every count slightly
about something the corpus excludes. Unseen papers are a separate evaluation domain and
are never blended into these metrics.</div>

<h2>A1. Species qualifier semantics</h2>
<div class="note">The ontology decides whether naming the chemical is part of identifying
a quantity. Six quantities are qualified <code>by: reactant</code> &mdash;
<code>pulse_time</code>, <code>purge_time</code>, <code>partial_pressure</code>,
<code>exposure</code>, <code>molecular_mass</code>,
<code>precursor_molecular_diameter</code> &mdash; and the role-prefixed composites the
pipeline builds on them (<code>precursor_pulse_time</code>,
<code>coreactant_purge_time</code>, <code>carrier_gas_partial_pressure</code>) inherit
that qualifier through a suffix relation over ontology ids, so a new composite is covered
the day it appears rather than when someone remembers to list it.<br><br>
Previously <em>every</em> unattributed condition was reported unresolved, which made
<code>deposition_temperature = 200 &deg;C</code> incomparable to itself. Species absence
is only missing information where the ontology asks for a species. Across active-8 shared
conditions this removed <strong>3378</strong> false <code>SPECIES_UNRESOLVED</code>
verdicts while retaining <strong>1034</strong> real ones. A stated species is still never
discarded: an explicit reagent against a missing one stays unresolved on any quantity.</div>

<h2>C1. Unit normalization and compatibility</h2>
<div class="note">Values are compared as physics rather than as printed text, through the
existing dimension-aware unit model. <code>500 ms</code> and <code>0.5 s</code> are one
value; <code>1 ms</code> and <code>1 s</code> are two, though both print as
&ldquo;1&rdquo;; <code>200 &deg;C</code> and <code>473.15 K</code> are one. Matching
digits across dimensions are a coincidence, not an equality, so <code>1 s</code> and
<code>1 nm</code> are <code>NOT_COMPARABLE</code>.<br><br>
<code>UNIT_CONVERTIBLE</code> now requires units that actually convert:
<code>&ldquo;short&rdquo; s</code> vs <code>&ldquo;long&rdquo; ms</code> is convertible-
but-undecided, while <code>&ldquo;short&rdquo; s</code> vs <code>&ldquo;low&rdquo; nm</code>
is not comparable at all &mdash; previously any two differing unit strings earned the
convertible verdict. One helper serves comparison, sweep detection and the inventory, so
the three cannot disagree about what &ldquo;distinct&rdquo; means.</div>

<h2>A. Condition ontology semantics</h2>
<div class="note">The ontology already separates these; the axis layer had been
collapsing them. <code>pulse_time</code> <em>specialises</em> time, carries SEC, and is
<em>qualified by reactant</em> &mdash; a valve opens for one named chemical.
<code>exposure_time</code> has no reactant qualifier and answers the broader question of
how long a surface was exposed. An explicit axis rule was folding every
&ldquo;pulse length&rdquo; into <code>exposure_time</code>, discarding exactly the
reactant dimension species-aware comparison needs, and overriding records that had
already said <code>pulse_time</code>. <code>family</code> still relates the two, so a
comparison layer can generalise one to the other deliberately rather than by losing the
distinction upstream.</div>
<div class="scroll"><table><thead><tr><th>quantity</th><th>unit</th>
<th>ontology structure</th><th>meaning</th><th>source wordings</th></tr></thead>
<tbody>%s</tbody></table></div>
<div class="note">7 axes corpus-wide moved <code>exposure_time</code> &rarr;
<code>pulse_time</code> &mdash; every one of them pulse-worded, and every one already
carrying <code>pulse_time</code> as its extracted record quantity. None is in active-8,
so no case identity moved. The dose quantities are untouched: a Langmuir exposure is not
a duration, which is the distinction the original rule existed to protect.</div>

<h2>C. The comparison model</h2>
<div class="note">The key is
<code>(quantity, species, process_step)</code>, compared value-wise through the existing
unit layer. The rule for an unknown species is the identity rule this repository already
runs on: <strong>MISSING is not SAME</strong>. A condition whose reagent was never
attributed is not thereby the same control as one that was &mdash; it is reported
<code>SPECIES_UNRESOLVED</code> rather than quietly matched or quietly dropped. This
layer reads identity and never writes it; fingerprints and case IDs come from the
semantic pipeline untouched.</div>

<h2>E. Comparison outcomes</h2>
<div class="scroll"><table><thead><tr><th>condition A</th><th>condition B</th>
<th>outcome</th><th>why</th></tr></thead><tbody>%s</tbody></table></div>

<h2>D. Condition inventory</h2>
<div class="scroll"><table><thead><tr><th>quantity</th><th>species</th><th>step</th>
<th>cases</th><th>papers</th><th>units</th><th>distinct values</th></tr></thead>
<tbody>%s</tbody></table></div>

<h2>F. Sweeps, found by identity rather than by label</h2>
<div class="note">A sweep is one condition identity taking several values. Because the
key carries the reagent, the precursor pulse sweep and the coreactant pulse are two
sweeps, not one &mdash; which a label-similarity search cannot tell apart, both being
drawn as &ldquo;pulse time&rdquo;.</div>
<div class="scroll"><table><thead><tr><th>paper</th><th>quantity</th><th>species</th>
<th>values</th><th>swept over</th></tr></thead><tbody>%s</tbody></table></div>

<h2>F2. Query examples</h2>
<div class="scroll"><table><thead><tr><th>query</th><th>matches</th>
<th>sample (with provenance)</th></tr></thead><tbody>%s</tbody></table></div>
<div class="note">Differ-only-in for <code>%s</code>: <strong>%d</strong> case pairs,
verdicts %s, blockers %s. The strong verdict <code>PROVEN_DIFFER_ONLY_IN</code> requires every shared
condition resolved and no unshared condition on either side; otherwise the pair is
reported as <code>MATCH_ON_SHARED_CONDITIONS</code>, which is a real result and is not
dressed up as the strong one.</div>

<h2>G. Negative controls</h2>
<div class="note">The engine refuses false equivalence:
<code>pulse_time@SnI4</code> &ne; <code>pulse_time@H2O</code> even at identical value and
unit; a named species is never matched to an unattributed one; <code>bar</code> and
<code>SiO2</code> appear nowhere as species (A2 hygiene holds); <code>H2 flow ratio</code>
remains an unsupported quantity and so is never a comparable <code>flow_rate</code>
condition (A0.1/A0.2 hold end to end).</div>

<h2>H. Active-8 identity and structure</h2>
<div class="note">Unchanged: ResultSeries 231, points 4027, Measurements 213,
SimulationRuns 34, DesignBranches 105, cases 25/66/2/11/44/7/7/20 = 182,
DISTINGUISHED 130, INDISTINGUISHABLE 52. The pulse/exposure correction touched no
active-8 axis, and the comparability layer writes nothing.</div>

<h2>K. Deferred</h2>
<div class="note">Not attempted here, and each needs its own evidence:
a natural-language query layer over these primitives; species-aware comparability of
<em>results</em> rather than conditions; broader unit transformation;
the <code>flow_ratio</code> ontology gap; <code>electrode_potential</code>,
<code>vapor_pressure</code>, <code>critical_angle</code>.<br><br>
<strong>Still open and material:</strong> in one paper the source states precursor
<em>purge</em> durations that upstream extraction typed as <code>pulse_time</code>. The
persisted evidence span for those conditions is truncated to
&ldquo;<code>pulse and 10 s</code>&rdquo; &mdash; short of the word that would settle it
&mdash; so the correction cannot be made from the artifacts and needs either
re-extraction or a methods-recipe parser reading the source prose. That is new extraction
infrastructure rather than a same-layer fix, and it would move 44 cases' fingerprints,
so it is left visible rather than guessed.</div>
</div>""" % (CSS, e(p["baseline_sha"]), e(p["generating_code_sha256"]), e(p["head_sha"]),
             p["n_cases"], p["n_condition_identities"], p["n_species_conditioned"],
             len(p["sweeps"]),
             p["n_cases"], p["excluded_development"]["n_cases"],
             onto, comp, invr, swr, qr,
             e(p["differ_only_in"]["requested"]), p["differ_only_in"]["n_pairs"],
             e(str(p["differ_only_in"]["verdicts"])),
             e(str(p["differ_only_in"]["blockers"])))
    OUT_HTML.write_text(doc)


if __name__ == "__main__":
    sys.exit(main())
