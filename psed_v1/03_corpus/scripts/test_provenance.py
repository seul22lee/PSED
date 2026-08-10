#!/usr/bin/env python3
"""Tests for the provenance layer (Phase 1): paper card -> resolved condition -> recipe.

The invariant under test throughout: provenance is CREATED where the value is created
and PROPAGATED with it. No stage may reconstruct a source by looking at the number.

  python3 scripts/test_provenance.py
"""
import importlib.util as u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

spec = u.spec_from_file_location("kb6", HERE / "06_to_kb.py")
kb6 = u.module_from_spec(spec)
spec.loader.exec_module(kb6)
import recipe as recipe_mod                       # 06_to_kb put 02_extraction on sys.path

base_card = kb6.base_card
FAIL = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")
    if not ok:
        FAIL.append(name)


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


# --------------------------------------------------------------- paper level
print("1) non-degenerate window: range provenance, NO scalar provenance")
c = base_card({"temperature_window_C": [175, 300]})
fp = c["_field_provenance"]
check("temperature_C absent", c["temperature_C"], None)
check("window prov origin", fp["temperature_window_C"]["origin"], "scout_window")
check("window prov status", fp["temperature_window_C"]["status"], "range")
check("no scalar provenance", "temperature_C" in fp, False)

print("2) degenerate window: derived scalar provenance")
c = base_card({"temperature_window_C": [225, 225]})
fp = c["_field_provenance"]
check("scalar value", c["temperature_C"], 225)
check("scalar origin", fp["temperature_C"]["origin"], "derived")
check("scalar status", fp["temperature_C"]["status"], "derived")
check("transformation named", fp["temperature_C"]["transformation"], "degenerate_range_to_scalar")
check("window still range", fp["temperature_window_C"]["status"], "range")

print("3) direct methods scalar: paper provenance")
# emulate methods_fill's merge for a paper with no window (the d0cp shape)
base = base_card({"temperature_window_C": None})
m = {"temperature_C": 300, "purge_time_s": 4.0}
prov = base["_field_provenance"]
for k in kb6.CARD_MERGE_FIELDS:
    if base.get(k) in (None, "unknown", []) and m.get(k) not in (None, ""):
        base[k] = m[k]
        prov[k] = kb6._pprov("methods_prose", "direct")
check("value merged", base["temperature_C"], 300)
check("origin methods_prose", prov["temperature_C"]["origin"], "methods_prose")
check("status direct", prov["temperature_C"]["status"], "direct")

print("4) merge transfers value AND provenance together")
ok("every merged field has provenance",
   all(k in prov for k in ("temperature_C", "purge_time_s")), sorted(prov))
ok("no provenance for unmerged fields",
   "pressure_Pa" not in prov and base["pressure_Pa"] is None)
# per-field table attribution when the model supplies it
base2 = base_card({})
prov2 = base2["_field_provenance"]
prov2["purge_time_s"] = kb6._pprov("table", "direct", evidence="Table 4")
check("table origin", prov2["purge_time_s"]["origin"], "table")
check("table evidence", prov2["purge_time_s"]["evidence"], "Table 4")

print("5) legacy backfill never claims an origin it cannot prove")
legacy = {"temperature_C": 300, "purge_time_s": 4.0, "temperature_window_C": None,
          "_from_table": "Table 0, Table 1"}
kb6.backfill_card_provenance(legacy, {})
check("legacy temperature origin", legacy["_field_provenance"]["temperature_C"]["origin"], "unknown")
check("legacy keeps table evidence",
      legacy["_field_provenance"]["temperature_C"]["evidence"], "Table 0, Table 1")
legacy2 = {"temperature_C": 225, "temperature_window_C": [225, 225]}
kb6.backfill_card_provenance(legacy2, {"temperature_window_C": [225, 225]})
check("legacy degenerate -> derived (rule, not value)",
      legacy2["_field_provenance"]["temperature_C"]["origin"], "derived")

# ---------------------------------------------------------- experiment level
CARD = {"precursors": ["TMA"], "coreactants": ["H2O"], "process_type": "thermal",
        "temperature_C": 300, "temperature_window_C": None, "pressure_Pa": None,
        "pulse_time_s": {"precursor": 0.1, "coreactant": 0.1}, "purge_time_s": 4.0,
        "ncycles": 500, "carrier_gas": "N2",
        "_field_provenance": {"temperature_C": kb6._pprov("methods_prose", "direct"),
                              "purge_time_s": kb6._pprov("table", "direct", evidence="Table 4"),
                              "ncycles": kb6._pprov("methods_prose", "direct"),
                              "pulse_time_s": kb6._pprov("methods_prose", "direct")}}
SCOUT = {"precursors": ["TMA"], "coreactants": ["H2O"], "materials": ["Al2O3"]}
RECORDS = [{
    "material": "Al2O3", "measurand": {"quantity": "thickness", "unit": "nm"},
    "coordinate": "depth", "points": [[0, 1], [1, 2]],
    "controlled": {"temperature": "225 C"},
    "series_kind": "numeric_sweep", "series_axis": "pulse_time",
    "series_value_num": 2.0, "series_unit": "s", "series_value": "2 s",
    "source": "measured",
    "provenance": {"figure": "Fig 9", "panel": "a"}}]
pid, exps = kb6.to_experiments("10.0000_test", SCOUT, RECORDS, CARD)
e = exps[0]
byq = {(c["quantity"], c.get("of_reactant")): c for c in e["controlled"]}

print("6) caption condition keeps an experiment-level origin")
cap = byq[("temperature", None)]
check("source label unchanged", cap["source"], "caption")
check("origin level", cap["origin"]["level"], "experiment")
check("origin from", cap["origin"]["from"], "caption")
check("figure retained", cap["origin"]["figure"], "Fig 9")
check("panel retained", cap["origin"]["panel"], "a")
check("experiment id retained", cap["origin"]["experiment_id"], e["exp_id"])
check("paper id retained", cap["origin"]["paper_id"], pid)

print("7) series condition keeps an experiment-level origin")
ser = byq[("pulse_time", None)]
check("source label unchanged", ser["source"], "series")
check("series value", ser["value"], 2.0)
check("origin from", ser["origin"]["from"], "series")
check("origin level", ser["origin"]["level"], "experiment")

print("8) methods condition references the originating card field")
cyc = byq[("cycle_number", None)]
check("source label unchanged", cyc["source"], "methods")
check("origin level", cyc["origin"]["level"], "paper")
check("origin from", cyc["origin"]["from"], "card")
check("card field named", cyc["origin"]["card_field"], "ncycles")
check("card provenance copied", cyc["origin"]["card_provenance"]["origin"], "methods_prose")
purge = byq[("purge_time", None)]
check("table evidence propagates", purge["origin"]["card_provenance"]["evidence"], "Table 4")

# -------------------------------------------------------------- recipe level
print("9) extracted recipe fields receive param_sources")
e["_pid"] = pid
rec = recipe_mod.from_experiment(e)
ps = rec.param_sources
# Selection is UNCHANGED: `_cond` takes the first matching condition and base_ctrl
# (paper) precedes panel_ctrl (caption), so a paper that states one temperature wins
# over a caption value. Provenance now makes that choice legible instead of implicit.
check("temperature source", ps["temperature::"]["source"], "paper")
check("temperature from", ps["temperature::"]["from"], "methods_prose")
check("temperature value == recipe", ps["temperature::"]["value"], rec.temperature)
check("ncycles source", ps["cycle_number::"]["source"], "paper")
check("ncycles from", ps["cycle_number::"]["from"], "methods_prose")
check("ncycles card field", ps["cycle_number::"]["card_field"], "ncycles")
check("purge from table", ps["purge_time::A"]["from"], "table")
check("purge ref", ps["purge_time::A"]["ref"], "Table 4")
check("material recorded", ps["material::"]["from"], "experiment_record")
ok("values agree with the recipe fields",
   ps["temperature::"]["value"] == rec.temperature and ps["cycle_number::"]["value"] == rec.ncycles)
ok("every param_sources entry uses the controlled vocabulary",
   all(m["source"] in recipe_mod.PARAM_SOURCES and m.get("from") in recipe_mod.PARAM_FROM
       for k, m in ps.items() if k != "_exp_id"),
   {k: (m.get("source"), m.get("from")) for k, m in ps.items() if k != "_exp_id"})

print("9b) when the paper states no scalar, the caption value carries through")
wcard = dict(CARD, temperature_C=None, temperature_window_C=[175, 300],
             _field_provenance={k: v for k, v in CARD["_field_provenance"].items()
                                if k != "temperature_C"})
_, wexps = kb6.to_experiments("10.0000_win", SCOUT, RECORDS, wcard)
wexps[0]["_pid"] = "10.0000_win"
wps = recipe_mod.from_experiment(wexps[0]).param_sources
check("window paper temperature source", wps["temperature::"]["source"], "experiment")
check("window paper temperature from", wps["temperature::"]["from"], "caption")
check("window paper temperature figure", wps["temperature::"]["figure"], "Fig 9")
check("window paper temperature value", wps["temperature::"]["value"], 225.0)

print("10) a degenerate-window scalar surfaces as derived/degenerate_range")
dcard = dict(CARD, temperature_C=225, temperature_window_C=[225, 225],
             _field_provenance=dict(CARD["_field_provenance"],
                                    temperature_C=kb6._pprov(
                                        "derived", "derived",
                                        transformation="degenerate_range_to_scalar")))
_, dexps = kb6.to_experiments("10.0000_deg", SCOUT, [dict(RECORDS[0], controlled={})], dcard)
dexps[0]["_pid"] = "10.0000_deg"
dps = recipe_mod.from_experiment(dexps[0]).param_sources
check("derived source", dps["temperature::"]["source"], "derived")
check("derived from", dps["temperature::"]["from"], "degenerate_range")
check("transformation carried", dps["temperature::"]["transformation"], "degenerate_range_to_scalar")

print("11) KB and model fills keep their metadata and gain a `from`")
r2 = recipe_mod.Recipe(material="Al2O3", reactants=[recipe_mod.Reactant("A", "precursor", "TMA")])
recipe_mod.fill_gaps(
    r2,
    lambda q, r=None: ({"value": 80.0, "sd": 3.0, "ci_lo": 77.0, "ci_hi": 83.0,
                        "n_eff": 4, "n_donors": 9, "donors": [{"exp_id": "x-1", "sim": 0.9}],
                        "method": "similarity"} if q == "temperature" else None),
    {"ncycles": 500, "t_p": 0.1})
kbm = r2.param_sources["temperature::"]
check("kb source", kbm["source"], "kb")
check("kb from", kbm["from"], "kb_imputation")
check("kb donors preserved", kbm["donors"], [{"exp_id": "x-1", "sim": 0.9}])
check("kb ci preserved", kbm["ci"], [77.0, 83.0])
check("kb n_eff preserved", kbm["n_eff"], 4)
mdm = r2.param_sources["cycle_number::"]
check("model source", mdm["source"], "model")
check("model from", mdm["from"], "model_default")
check("model value", mdm["value"], 500)

print("12) artifacts WITHOUT provenance still load (backward compatibility)")
old_exp = {"exp_id": "old-1", "material": "ZnO", "cycle_sequence": "AB",
           "reactants": [{"label": "A", "role": "precursor", "species": "DEZ"}],
           "controlled": [{"quantity": "temperature", "value": 150, "unit": "C",
                           "source": "methods"},          # no `origin` key at all
                          {"quantity": "pulse_time", "value": 0.2, "of_reactant": "A"}]}
r3 = recipe_mod.from_experiment(old_exp)
check("legacy temperature still lifted", r3.temperature, 150)
check("legacy dose still lifted", r3.reactants[0].dose_time, 0.2)
check("legacy methods -> paper/unknown", r3.param_sources["temperature::"]["from"], "unknown")
check("legacy no-source -> experiment/unknown",
      r3.param_sources["pulse_time::A"]["source"], "experiment")
old_card = {"temperature_C": 200}
ok("card without _field_provenance loads", kb6.backfill_card_provenance(old_card, None) is old_card)

print("13) provenance is never inferred from the value")
# Two experiments with the SAME number and different recorded origins must not collapse.
def _one(src, origin):
    return {"exp_id": "same-1", "_pid": "p", "material": "Al2O3", "reactants": [],
            "controlled": [{"quantity": "temperature", "value": 175, "unit": "C",
                            "source": src, "origin": origin}]}
a = recipe_mod.from_experiment(_one("methods", {"level": "paper", "from": "card",
                                                "card_field": "temperature_C",
                                                "card_provenance": kb6._pprov("table", "direct",
                                                                              evidence="Table 1")}))
b = recipe_mod.from_experiment(_one("caption", {"level": "experiment", "from": "caption",
                                                "paper_id": "p", "experiment_id": "same-1",
                                                "figure": "Fig 3"}))
check("same value, both lifted", (a.temperature, b.temperature), (175, 175))
check("A resolves to paper/table", (a.param_sources["temperature::"]["source"],
                                    a.param_sources["temperature::"]["from"]), ("paper", "table"))
check("B resolves to experiment/caption", (b.param_sources["temperature::"]["source"],
                                           b.param_sources["temperature::"]["from"]),
      ("experiment", "caption"))

# ------------------------------------------------------------ corpus fixtures
print("14) corpus: d0cp temperature is a genuine paper scalar, not a window endpoint")
OUT = ROOT.parent / "papers"      # papers/<doi>/resolved/


def _card(doi):
    p = ROOT / "extracted" / doi / "card.json"
    return json.loads(p.read_text()) if p.is_file() else None


def _exps(doi):
    p = OUT / doi / "resolved" / "experiments.json"
    return json.loads(p.read_text()) if p.is_file() else None


d0 = _card("10.1039_d0cp03358h")
if d0 is None:
    print("  SKIP  d0cp card not present")
else:
    fpd = d0.get("_field_provenance") or {}
    ok("d0cp has a scalar temperature", d0.get("temperature_C") is not None, d0.get("temperature_C"))
    ok("d0cp has provenance for it", "temperature_C" in fpd, sorted(fpd))
    ok("d0cp temperature is NOT window-derived",
       fpd.get("temperature_C", {}).get("origin") not in ("scout_window", "derived"),
       fpd.get("temperature_C"))
    ok("d0cp status is direct", fpd.get("temperature_C", {}).get("status") == "direct",
       fpd.get("temperature_C"))

print("15) corpus: c6dt keeps a RANGE at paper level; recipe T comes from the experiment")
c6 = _card("10.1039_c6dt03571j")
if c6 is None:
    print("  SKIP  c6dt card not present")
else:
    fpc = c6.get("_field_provenance") or {}
    w = c6.get("temperature_window_C")
    ok("c6dt window is non-degenerate", isinstance(w, list) and len(w) == 2 and w[0] != w[1], w)
    ok("c6dt window has range provenance",
       fpc.get("temperature_window_C", {}).get("status") == "range", fpc.get("temperature_window_C"))
    ok("c6dt has NO paper-level temperature scalar", c6.get("temperature_C") is None,
       c6.get("temperature_C"))
    ok("c6dt has no temperature_C provenance", "temperature_C" not in fpc, sorted(fpc))
    ce = _exps("10.1039_c6dt03571j") or []
    srcs = {c.get("source") for e in ce for c in (e.get("controlled") or [])
            if c.get("quantity") == "temperature"}
    ok("c6dt temperatures come from caption/series only",
       srcs <= {"caption", "series"}, srcs or "none")

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
