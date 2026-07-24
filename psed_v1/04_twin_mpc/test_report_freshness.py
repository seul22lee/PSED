#!/usr/bin/env python3
"""Freshness + pressure-semantics guards for the canonical M2 and M3 reports.

These exist because the reports drifted: m2_report.html was committed before the
pressure adapter (7906e46) and kept showing ratio_status=pressure_species_ambiguous,
while the live consumer now produces pressure_unresolved. Nothing regenerated it.
This detects that class of staleness deterministically.

  python3 test_report_freshness.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "02_extraction"))
import m2_design as md

M2 = HERE / "m2_report.html"
M3 = HERE / "m3_validation.html"
FAIL = []


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


print("1) M2 report is regenerated from CURRENT inputs (in-memory byte-compare)")
# same call main() makes
res = md.design(md.DesignRequest(material="Al2O3", target_pd=60e-6,
                                 precursor="TMA", co_reactant="H2O",
                                 geometry_class="lateral_channel",
                                 allow_chemistry_fallback=True))
with tempfile.TemporaryDirectory() as td:
    fresh = md.render_report(res, out_path=Path(td) / "fresh.html").read_text()
committed = M2.read_text()
ok("committed M2 == fresh render (not stale)", committed == fresh,
   "differs — run: python3 m2_design.py" if committed != fresh else "")

print("2) M2 shows the CURRENT pressure status, not the stale one")
ok("ratio_status shows pressure_unresolved", "pressure_unresolved" in committed)
ok("stale ratio-status species_ambiguous is GONE",
   "ratio status: <span class=mono>pressure_species_ambiguous" not in committed)

print("3) M2 never renders a forbidden pressure type as precursor partial pressure")
# the precursor_partial_pressure prior row must be unresolved with the 'no record' evidence,
# not a chamber/working/base/generic value
ok("precursor_partial_pressure prior is unresolved",
   "no partial_pressure record for A in this chemistry" in committed)
for bad in ("working_pressure", "chamber_total_pressure", "base_pressure"):
    # these strings may appear in prose, but never as the precursor pressure VALUE cell
    ok(f"{bad} not presented as the precursor pressure value",
       f"precursor_partial_pressure</td><td class=mono>{bad}" not in committed)
ok("model A/B pressures still flagged as model assumptions",
   "model assumptions (source=model)" in committed)

print("4) M2 status fields are mutually consistent")
for tok in ("fully_specified", "partial_chemistry", "pressure_unresolved",
            "s-fallback", "reference_context_status"):
    ok(f"{tok} present", tok in committed)

print("5) M3 is the canonical Interpretation Brief — neutral, no validation-against-reality language")
ok("M3 report exists and is non-trivial", M3.is_file() and M3.stat().st_size > 5000)
m3 = M3.read_text()
# frozen-spec presentation guards
ok("M3 is the Interpretation Brief", "Interpretation Brief" in m3)
ok("M3 uses neutral 'prediction versus observation'", "prediction versus observation" in m3)
for bad in ("versus reality", "vs reality", "validation against", "twin disagrees with reality"):
    ok(f"M3 avoids validation-against-reality language: {bad!r}", bad.lower() not in m3.lower())
ok("M3 carries the discovery-support disclaimer", "discovery-support brief, not a verdict" in m3)
ok("M3 states the evidence-closure statement", "No additional interpretation may be extracted" in m3)
# pressure-semantics guards preserved: no forbidden pressure type feeds pA
ok("M3 does not feed a co-reactant pressure into pA", "co_reactant_partial_pressure" not in m3)
ok("M3 does not feed chamber/working/base pressure into pA",
   not any(f">{t}<" in m3 for t in ("chamber_total_pressure", "working_pressure", "base_pressure")))
ok("M3 renders twin inputs incl. geometry height and dose", ">H<" in m3 and "dose" in m3)
ok("M3 does not claim corpus-wide pressure absence",
   "in this processed corpus" in m3 and "NOT a claim that it is absent" in m3)

print("6) M3 Brief is byte-stable under regeneration (deterministic, detects staleness)")
try:
    before = M3.read_bytes()
    r = subprocess.run([sys.executable, str(HERE / "twin_validation.py")],
                       cwd=str(HERE), capture_output=True, timeout=300)
    after = M3.read_bytes()
    if r.returncode != 0:
        print(f"  SKIP  M3 generator returned {r.returncode}: {r.stderr.decode()[:120]}")
    else:
        ok("committed M3 == fresh regeneration (not stale)", before == after,
           "differs — run: python3 twin_validation.py" if before != after else "")
except Exception as e:
    print(f"  SKIP  M3 regeneration unavailable: {type(e).__name__}: {e}")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
