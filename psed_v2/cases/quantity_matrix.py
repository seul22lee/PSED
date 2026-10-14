#!/usr/bin/env python3
"""Exploration: writes cases/quantity_matrix.csv: for each in-scope paper with a PDF, where each quantity a conformality comparison may
need is found (figure, table, text). Figures come from figures.csv; tables and text by keyword; cells for the conformality papers
are replaced by a hand-read pass (dict H). Keyword cells say "text (keyword)": a mention, not a checked value.

    python3 psed_v2/cases/quantity_matrix.py
"""
import csv, json, re, collections
V2 = "/home/ftk3187/github/PSED/psed_v2/"
man = {r["paper_id"]: r for r in csv.DictReader(open(V2 + "corpus/manifest.csv", encoding="utf-8"))}
papers = sorted(p for p, r in man.items() if r["in_scope"] == "yes" and r["pdf_status"] == "ok")
F = collections.defaultdict(list)
for r in csv.DictReader(open(V2 + "cases/figures.csv", encoding="utf-8")):
    F[r["paper_id"]].append(r)
MEAS = lambda r: "measured" in r["data_kind"] or "cited" in r["data_kind"]
def figs(pid, test):
    out = []
    for r in F[pid]:
        if r["kind"] == "plot" and test(r):
            f = f"Fig. {r['figure']}" if not str(r["figure"]).startswith("Table") else r["figure"]
            if f not in out: out.append(f)
    return out
X = lambda r: r["x_id"]; Y = lambda r: r["y_id"]; XY = lambda r: r["x_id"] + " " + r["y_id"]
FIG = {
 "measured_profile": lambda r: MEAS(r) and ((X(r).startswith(("distance", "dimensionless_distance")) and Y(r).startswith(("film_thickness", "normalized_thickness", "growth_per_cycle{position=local}"))) or (X(r).startswith("film_thickness") and Y(r) == "distance")),
 "pd50_or_coated_ar": lambda r: MEAS(r) and ("coated_aspect_ratio" in Y(r) or "penetration_depth" in Y(r)),
 "structure_dims": lambda r: MEAS(r) and ("feature_width" in XY(r) or "aspect_ratio" in X(r)),
 "exposure_or_pp_and_pulse": lambda r: MEAS(r) and ("pulse_time" in X(r) or "exposure" in X(r) or "partial_pressure" in X(r)),
 "deposition_temperature": lambda r: MEAS(r) and "deposition_temperature" in X(r),
 "cycles": lambda r: MEAS(r) and "cycle_number" in X(r),
 "planar_gpc": lambda r: MEAS(r) and "growth_per_cycle{position=planar" in Y(r),
 "sticking_or_reaction_prob": lambda r: "initial_sticking_coefficient" in XY(r) and ("fit" in r["data_kind"] or "measured" in r["data_kind"]),
 "recombination_prob": lambda r: "recombination_probability" in Y(r),
 "step_coverage": lambda r: "step_coverage" in Y(r),
 "front_slope_or_width": lambda r: MEAS(r) and ("slope" in Y(r).lower() or "broadness" in Y(r).lower()),
 "pore_or_channel_width": lambda r: MEAS(r) and "feature_width" in XY(r),
}
TXT = {
 "measured_profile": r"thickness profile|as a function of (the )?depth|along the (depth|channel|trench|hole|pore)|line scan",
 "pd50_or_coated_ar": r"PD ?\^?\{?50|PD50|half[- ]thickness|50 ?% ?(thickness )?penetration|penetration depth of|coated (equivalent )?aspect ratio|x_?\{?50",
 "structure_class": r"\b(trench(es)?|holes?|pores?|nanopores?|channels?|LHAR|PillarHall|cavit(y|ies)|AAO|nanotubes?|nanowires?|pillars?|porous|membrane|non-?woven|particles?|powder|forest)\b",
 "structure_dims": r"aspect ratio (of|was|is|=)|\bAR ?(=|of|~|≈)|\d+(\.\d+)? ?(nm|µm|μm|um|mm)[ -](deep|wide|long|high|in diameter|thick)|(depth|diameter|width|height|length) of (about |approximately |~)?\d",
 "exposure_or_pp_and_pulse": r"Langmuir|\d ?\(?L\)? (exposure|of exposure)|\d+(\.\d+)? ?(m?Torr|Pa|mbar) ?·? ?s\b|exposure of \d|partial pressures? of (the )?(TMA|DEZ|TDMAT|TiCl4|precursor|H2O|water|ozone|O3|oxygen)|(TMA|DEZ|precursor|H2O|water|ozone) (partial )?pressure (of|was|=|≈|~)|pressures? of (\d|about|approximately|~)[^.]{0,40}(TMA|DEZ|precursor|H2O|water)",
 "deposition_temperature": r"\d{2,3} ?°C|\d{2,3} ?\^\{?\\circ|deposition temperature|substrate temperature",
 "cycles": r"\d+ (ALD |AB |deposition )?cycles",
 "planar_gpc": r"growth per cycle|growth-per-cycle|\bGPC\b|Å ?/ ?cycle|nm ?/ ?cycle|growth rate",
 "sticking_or_reaction_prob": r"sticking (coefficient|probability)|reaction probability|reactive sticking|\bs_?\{?0\}?\b ?=|S\(0\)",
 "recombination_prob": r"recombination (probability|coefficient|loss probability)",
 "step_coverage": r"step coverage|conformality of \d|\d+ ?% conformal|bottom[- ]to[- ]top",
 "front_slope_or_width": r"slope (of|at) the|front (width|broadness)|broadness|width of the (reaction|adsorption) front",
 "pore_or_channel_width": r"pore (diameter|size|width)|channel (height|width)|gap height|cavity height|opening (width|diameter)|trench width|hole diameter|diameter of the (hole|pore)",
 "process_mode": r"plasma|ozone|\bO_?\{?3\b|spatial|atmospheric[- ]pressure|thermal ALD",
}
COLS = list(TXT.keys())
rows = []
for pid in papers:
    st = json.load(open(V2 + f"ingest/final/{pid}/structure.json"))
    doc = open(V2 + f"ingest/final/{pid}/document.md", encoding="utf-8").read()
    i = max(doc.rfind("\n## References"), doc.rfind("\n# References"), doc.rfind("REFERENCES"), doc.rfind("\nReferences\n"))
    body = doc[:i] if i > len(doc) * 0.4 else doc
    tabs = [(c["number"], (c.get("caption") or "") + " " + (c.get("table") or "")) for c in st["captions"] if c["kind"] == "table"]
    row = {"paper_id": pid, "year": man[pid]["year"]}
    for col in COLS:
        where = figs(pid, FIG[col]) if col in FIG else []
        rx = re.compile(TXT[col], re.I)
        where += [f"Table {n}" for n, t in tabs if rx.search(t)]
        if rx.search(body): where.append("text")
        row[col] = "; ".join(where) if where else "no"
    rows.append(row)
w = csv.DictWriter(open(V2 + "cases/quantity_matrix.csv", "w", newline="", encoding="utf-8"), fieldnames=["paper_id", "year"] + COLS)
w.writeheader(); w.writerows(rows)
miss = {c: sum(1 for r in rows if r[c] == "no") for c in COLS}
print(len(rows), "papers x", len(COLS), "quantities"); print(sorted(miss.items(), key=lambda x: -x[1]))
fig_or_tab = {c: sum(1 for r in rows if ("Fig" in r[c] or "Table" in r[c])) for c in COLS}; print("in a figure or table:", fig_or_tab)

# ---- second pass: cells read by hand for the papers the part E candidates draw on. A hand cell replaces the keyword cell.
H = {
 "10.1063_1.5028178": dict(pd50_or_coated_ar="Fig. 6, 7 (read off the profile)", exposure_or_pp_and_pulse="text (pulse 0.1 s); Table I (pressure fitted, not measured)", sticking_or_reaction_prob="Table I (fit)", planar_gpc="Table I (model saturation value)", recombination_prob="no", step_coverage="no", front_slope_or_width="no", pore_or_channel_width="Fig. 6, 7 captions; Table I", deposition_temperature="text"),
 "10.1039_d0cp03358h": dict(pd50_or_coated_ar="Table 1", exposure_or_pp_and_pulse="Table 1 (pulse times only); Fig. 10 caption (pressure as model input)", sticking_or_reaction_prob="Table 2 (slope method)", recombination_prob="no", step_coverage="no", front_slope_or_width="Table 1", planar_gpc="Table 1", pore_or_channel_width="Table 1"),
 "10.1116_1.4903941": dict(pd50_or_coated_ar="text (TiO2: aspect ratio at 50%); Fig. 5a (read off)", exposure_or_pp_and_pulse="text (pulse times and reactor pressure; no partial pressure)", step_coverage="Fig. 6 (percentages on the image)", pore_or_channel_width="text; Fig. 1 table"),
 "10.1149_1.3072694": dict(pd50_or_coated_ar="Fig. 5 (read off)", exposure_or_pp_and_pulse="text (TMA about 0.3 Pa, 4 s)", sticking_or_reaction_prob="text (value chosen for the simulation)", step_coverage="no", planar_gpc="text (about 1 Å per cycle)"),
 "10.1149_1.3301664": dict(pd50_or_coated_ar="Figs. 2, 3, 5 (read off)", exposure_or_pp_and_pulse="text (TMA about 0.2 Pa, reactant 0.3 Pa, times; Fig. 3 table)", sticking_or_reaction_prob="text (simulation inputs)", recombination_prob="Fig. 7 (model inputs, no fitted value)", planar_gpc="no", step_coverage="no"),
 "10.1016_j.surfcoat.2012.02.038": dict(pd50_or_coated_ar="Fig. 5 (half-value depths marked)", exposure_or_pp_and_pulse="text; Table 2 (0.08 Pa, times)", sticking_or_reaction_prob="text; Table 2 (picked by comparing simulations)", recombination_prob="Fig. 11; Table 5 (model inputs)", planar_gpc="Fig. 9; text"),
 "10.1021_cm0303080": dict(pd50_or_coated_ar="Fig. 3, 5 (read off; coated or not at three depths)", exposure_or_pp_and_pulse="text (pressures and times); Fig. 5, 13", sticking_or_reaction_prob="text (values used as model inputs)", planar_gpc="text (thickness for 100 cycles)", step_coverage="no"),
 "10.1002_cvde.200390005": dict(pd50_or_coated_ar="Fig. 2 (coated fraction of the hole)", exposure_or_pp_and_pulse="text (in Langmuir)", sticking_or_reaction_prob="text (QCM, a lower limit)", step_coverage="text; Fig. 2", planar_gpc="text (0.1 nm per cycle)"),
 "10.1149_1.3491381": dict(measured_profile="no", sticking_or_reaction_prob="Table I (literature)", recombination_prob="Table II (literature); Figs. 4-9 (model inputs)", exposure_or_pp_and_pulse="no (model doses only)"),
 "10.1116_1.4971196": dict(pd50_or_coated_ar="no", exposure_or_pp_and_pulse="text (pulse times, deposition pressure; no partial pressure)", sticking_or_reaction_prob="text; Figs. 10, 13 (fit)", planar_gpc="text (on test wafers)"),
 "10.1016_j.apsusc.2009.02.055": dict(exposure_or_pp_and_pulse="text (pulse times, source vapour pressure; no partial pressure)", sticking_or_reaction_prob="text; Fig. 4 (fit)", pd50_or_coated_ar="no"),
 "10.1016_j.apsusc.2010.01.025": dict(exposure_or_pp_and_pulse="text (pulse times, process pressure; no partial pressure)", sticking_or_reaction_prob="text; Figs. 2, 4; Table 4 (fit)", pd50_or_coated_ar="Fig. 1 (read off)"),
 "10.1063_1.2714685": dict(exposure_or_pp_and_pulse="text (TMA 0.01 and 0.04 Torr; injection times); Fig. 7, 9", sticking_or_reaction_prob="text; Fig. 8 (fit)", step_coverage="Fig. 7, 9 (bottom over flat)", planar_gpc="Fig. 7"),
 "10.1149_1.2789802": dict(exposure_or_pp_and_pulse="Table II (fitted flux); text (source temperatures)", sticking_or_reaction_prob="Table II; Fig. 7b (fit)", step_coverage="Fig. 5; text", planar_gpc="Figs. 2, 3, 6, 7"),
 "10.1063_1.4972120": dict(step_coverage="Table II, III", recombination_prob="text (quoted value)", exposure_or_pp_and_pulse="text (pulse times, O2 plasma pressure)", planar_gpc="text; Fig. 1"),
 "10.1021_acs.jpcc.9b08176": dict(recombination_prob="Fig. 3; text", pd50_or_coated_ar="Fig. 2A, Fig. 3", exposure_or_pp_and_pulse="text (plasma times, 50 mTorr)"),
 "10.1063_5.0168768": dict(recombination_prob="Fig. 3; Table I", pd50_or_coated_ar="Fig. 3; text", exposure_or_pp_and_pulse="text (plasma exposure times)"),
 "10.1021_acs.jpcc.5c06502": dict(recombination_prob="text", pd50_or_coated_ar="Table 1", exposure_or_pp_and_pulse="Table 1 (precursor exposure in L, plasma times)"),
 "10.1021_acs.jpcc.1c01505": dict(recombination_prob="Fig. 5", exposure_or_pp_and_pulse="text (plasma times, pressures)", step_coverage="no"),
 "10.1116_6.0001094": dict(recombination_prob="text (held fixed in the fit)", sticking_or_reaction_prob="text (fit)", exposure_or_pp_and_pulse="Table I; Figs. 13, 14 (fitted radical pressure)", pd50_or_coated_ar="no"),
 "10.1016_j.sse.2022.108584": dict(sticking_or_reaction_prob="Tables 1, 2 (fit)", exposure_or_pp_and_pulse="text (estimated for the cited data)", measured_profile="Figs. 4, 6, 7 (cited)"),
 "10.1021_acs.jpclett.4c03545": dict(step_coverage="text; Figs. 1, 2", pd50_or_coated_ar="text (deposition depth)", exposure_or_pp_and_pulse="no"),
 "10.1039_c4nr05049e": dict(pore_or_channel_width="Fig. 3, 4; text", planar_gpc="text"),
 "10.3390_separations11010024": dict(pore_or_channel_width="Fig. 6b, 7", planar_gpc="Figs. 3, 4, 5"),
}
for r in rows:
    h = H.get(r["paper_id"], {})
    for c in COLS:
        if c in h:
            r[c] = h[c]
        else:
            r[c] = r[c].replace("Table None", "unnumbered table").replace("text", "text (keyword)") if r[c] != "no" else "no"
    r["read_by_hand"] = "yes" if h else "no"
w = csv.DictWriter(open(V2 + "cases/quantity_matrix.csv", "w", newline="", encoding="utf-8"), fieldnames=["paper_id", "year"] + COLS + ["read_by_hand"])
w.writeheader(); w.writerows(rows)
miss = {c: sum(1 for r in rows if r[c] == "no") for c in COLS}
print("after hand pass, missing:", sorted(miss.items(), key=lambda x: -x[1]))
hand = [r for r in rows if r["read_by_hand"] == "yes"]
print("hand-read papers", len(hand), {c: sum(1 for r in hand if r[c].startswith("no")) for c in COLS})
