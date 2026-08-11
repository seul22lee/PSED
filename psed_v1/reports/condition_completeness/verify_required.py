#!/usr/bin/env python3
"""The explicitly required regression conditions, checked on the REGENERATED
entities with their provenance. Prints PASS/FAIL per condition."""
import paths as P
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KB = P.PAPERS
FAIL = []


def ents(doi):
    return json.loads((P.resolved_json(doi, "entities")).read_text())


def find(doi, fig, panel=None, label=None):
    for e in ents(doi):
        if str(e["printed_figure_number"]) != str(fig):
            continue
        if panel is not None and (e["panel"] or "") != panel:
            continue
        if label is not None and label not in str(e["source_series"]):
            continue
        return e
    return None


def has(e, q, val=None, unit=None, scope=None, species=None, react=None):
    for b in (e or {}).get("bound_conditions") or []:
        if b["quantity"] != q:
            continue
        if val is not None and abs(float(b["value"]) - float(val)) > 1e-6 * max(1, abs(float(val))):
            continue
        if unit is not None and str(b["unit"]).replace(" ", "") != unit.replace(" ", ""):
            continue
        if scope is not None and b.get("bound_at_scope") != scope:
            continue
        if species is not None and b.get("species") != species:
            continue
        if react is not None and b.get("of_reactant") != react:
            continue
        return b
    return None


def ok(name, cond, detail=""):
    print("  %s  %s%s" % ("PASS" if cond else "FAIL", name, (" — " + str(detail)) if detail else ""))
    if not cond:
        FAIL.append(name)


print("10.1039_d0cp03358h — methods conditions on Fig. 11 experimental profiles")
a = find("10.1039_d0cp03358h", "11", "a")
b = find("10.1039_d0cp03358h", "11", "b")
for e, tag in ((a, "F11a"), (b, "F11b")):
    ok("%s 300 °C" % tag, has(e, "deposition_temperature", 300, "°C"))
    ok("%s 500 cycles" % tag, has(e, "cycle_number", 500, "cycle"))
    ok("%s ~3 hPa working pressure" % tag, has(e, "working_pressure", 3, "hPa"))
    ok("%s N2 150 sccm" % tag, has(e, "flow_rate", 150, "sccm", species="N2"))
    ok("%s channel height 500 nm" % tag, has(e, "feature_height", 500, "nm"))
p = has(a, "pulse_time", 0.1, "s", scope="series")
ok("F11a pulse time 0.1 s at series scope", p)
ok("F11a pulse time bound to TMA / reactant A", p and p.get("species") == "TMA" and p.get("of_reactant") == "A",
   (p or {}).get("species"))
ok("F11a pulse provenance retained", p and p.get("raw_evidence") and p.get("evidence_locator"))
for v in (0.2, 0.4):
    e2 = find("10.1039_d0cp03358h", "11", "a", label="%s s" % v)
    ok("F11a pulse %s s on its own entity" % v, has(e2, "pulse_time", v, "s", scope="series"))
for v in (1, 4, 10):
    e3 = find("10.1039_d0cp03358h", "11", "b", label="%s s" % v)
    ok("F11b purge %s s at series scope" % v, has(e3, "purge_time", v, "s", scope="series"))
ok("F11b does NOT inherit panel (a)'s 0.4 s pulse",
   not has(b, "pulse_time", 0.4), "leak" if has(b, "pulse_time", 0.4) else "withheld")

print("\n10.1016_j.sse.2022.108584 Fig. 4 — per-series and literature conditions")
for t in (150, 220, 310):
    e = find("10.1016_j.sse.2022.108584", "4", "a", label="Arts 2019, %d" % t)
    ok("Arts %d °C per series" % t, has(e, "deposition_temperature", t, "°C", scope="series"))
    ok("Arts %d 400 cycles" % t, has(e, "cycle_number", 400, "cycle"))
    ok("Arts %d 750 mTorr·s as EXPOSURE" % t, has(e, "exposure", 750, "mTorr*s"))
    ok("Arts %d GPC 1.12 Å/cycle" % t, has(e, "growth_per_cycle", 1.12))
    ok("Arts %d d = 0.5 µm" % t, has(e, "feature_height", 0.5))
    ok("Arts %d L = 5000 µm" % t, has(e, "feature_length", 5000))
    ex = has(e, "exposure", 750)
    ok("Arts %d exposure is NOT a pressure" % t, ex and "pressure" not in ex["quantity"])
    e2 = find("10.1016_j.sse.2022.108584", "4", "a", label="Model, %d" % t)
    ok("Model %d °C per series" % t, has(e2, "deposition_temperature", t, "°C", scope="series"))
    ok("Model %d does not carry Arts' exposure" % t, not has(e2, "exposure", 750))
lit = find("10.1016_j.sse.2022.108584", "4", "a", label="Arts 2019, 310")
ok("Arts series kept as imported literature, not a current-paper experiment",
   lit and lit["classification"] == "imported_literature_data"
   and not lit["is_current_paper_experiment"])
ok("Arts series records originally_reported_in", lit and lit.get("originally_reported_in"))

print("\n10.1002_pssa.201532305 Fig. 4 — standard values + per-panel setting")
for pan, q, val, sp in (("a", "hot_wire_temperature", 1800, None),
                        ("b", "flow_rate", 10, "H2"),
                        ("c", "flow_rate", 10, "WF6"),
                        ("d", "flow_rate", 10, "Ar")):
    e = find("10.1002_pssa.201532305", "4", pan)
    ok("F4%s panel-specific %s at series scope" % (pan, q),
       has(e, q, scope="series") is not None,
       (has(e, q, scope="series") or {}).get("value"))
for pan in ("a", "b", "c", "d"):
    e = find("10.1002_pssa.201532305", "4", pan)
    ok("F4%s 0.01 mbar" % pan, has(e, "working_pressure", 0.01, "mbar"))
    ok("F4%s 325 °C substrate" % pan, has(e, "deposition_temperature", 325, "°C"))
    ok("F4%s 1 min WF6 pre-exposure" % pan, has(e, "pulse_time", 1, "min", species="WF6"))
    ok("F4%s 2 min purge" % pan, has(e, "purge_time", 2, "min"))
    ok("F4%s continuous trace, one case" % pan,
       e and e["classification"] == "continuous_trace" and e["experimental_case_count"] == 1)

print("\n%s" % ("ALL REQUIRED CONDITIONS PRESENT" if not FAIL
                else "%d FAILURE(S): %s" % (len(FAIL), FAIL[:8])))
sys.exit(1 if FAIL else 0)
