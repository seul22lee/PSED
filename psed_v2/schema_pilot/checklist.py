#!/usr/bin/env python3
"""Writes <paper>/checklist.md: the same core list for every paper (the 14 quantity_matrix columns plus saturation_checked),
then paper-specific extras. Status: found (ids) / not stated / not in document (SI) / not read. Ids are found in the final
tables by rule; where none are found, the status and reason come from NOTE below (decided by reading the paper).

    python3 psed_v2/schema_pilot/checklist.py
"""
import csv, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
from convert import PAPERS

CORE = ["measured_profile", "pd50_or_coated_ar", "structure_class", "structure_dims", "exposure_or_pp_and_pulse", "deposition_temperature",
        "cycles", "planar_gpc", "sticking_or_reaction_prob", "recombination_prob", "step_coverage", "front_slope_or_width",
        "pore_or_channel_width", "process_mode", "saturation_checked"]
NOTE = {  # (paper key, item): (status, reason) when the tables hold no id for it, or to qualify what they hold
    ("yim20", "recombination_prob"): ("not stated", "thermal process; no radicals"),
    ("yim20", "step_coverage"): ("not stated", "profiles and PD50 instead of a step coverage"),
    ("yim20", "saturation_checked"): ("found", "Series E pulse 0.1/0.2/0.4 s and purge series (Fig. 11, Table 1 samples 12-16); planar S1/N nearly constant"),
    ("yim20", "exposure_or_pp_and_pulse"): ("found", "pulse and purge times per sample; partial pressure only as a model input (Fig. 10)"),
    ("mat22", "measured_profile"): ("not stated", "planar films only; the series shown is a lateral thickness map over a 4 inch wafer, not a depth profile"),
    ("mat22", "structure_dims"): ("not stated", "planar substrates (Si with thermal SiO2, glassy carbon, PET foil); no 3D structure"),
    ("mat22", "pd50_or_coated_ar"): ("not stated", "planar films only"),
    ("mat22", "front_slope_or_width"): ("not stated", "planar films only"),
    ("mat22", "pore_or_channel_width"): ("not stated", "planar films only"),
    ("mat22", "sticking_or_reaction_prob"): ("not stated", ""),
    ("mat22", "recombination_prob"): ("not stated", "H2S/H2/Ar plasma; no radical loss reported"),
    ("mat22", "step_coverage"): ("not stated", "planar films only"),
    ("mat22", "exposure_or_pp_and_pulse"): ("found", "pulse times and pressures of the cycle recipe; no precursor partial pressure"),
    ("mat22", "saturation_checked"): ("not in document (SI)", "saturation curves stated to be in SI Figure S1 (Results, Concept para)"),
    ("gre23", "pd50_or_coated_ar"): ("found", "no front: the compacts are coated through, coated AR = full AR"),
    ("gre23", "planar_gpc"): ("not stated", "no planar witness; growth per cycle only inside the compacts, from mass gain"),
    ("gre23", "sticking_or_reaction_prob"): ("not in document (SI)", "design inputs of Eq. 1 are in Note S1"),
    ("gre23", "recombination_prob"): ("not stated", "thermal process"),
    ("gre23", "step_coverage"): ("not stated", "EDS signal ratio only (not a thickness)"),
    ("gre23", "front_slope_or_width"): ("not stated", "no front"),
    ("gre23", "saturation_checked"): ("found", "static holds sized by a diffusion design (Sec. II B); pressure traces show completion"),
}


def ids(rows, test, key, n=8):
    out = [r[key] for r in rows if test(r)]
    return (", ".join(out[:n]) + (f" (+{len(out) - n})" if len(out) > n else "")) if out else ""


def make(pid, key):
    T = {t: list(csv.DictReader((HERE / pid / f"{t}.csv").open(encoding="utf-8"))) for t in ("sample", "condition", "series", "value")}
    V, C, S, SA = T["value"], T["condition"], T["series"], T["sample"]
    q = lambda *qs: (lambda r: r["quantity"] in qs)
    lab = lambda rx: (lambda r: r["quantity"] == "other" and re.search(rx, r["label_as_printed"], re.I))
    find = {
        "measured_profile": ids(S, lambda r: r["data_kind"] == "measured" and r["kind"] in ("plot", "map") and (r["x_id"] in ("distance", "dimensionless_distance") or re.search(r"distance|position|depth", r["x_label"] + r["y_label"], re.I)), "series_id"),
        "pd50_or_coated_ar": ids(V, q("penetration_depth", "coated_aspect_ratio"), "value_id"),
        "structure_class": ids(SA, lambda r: r["structure_class"] and r["kind"] != "group", "sample_id", 3),
        "structure_dims": ids(V, q("feature_width", "feature_depth", "aspect_ratio", "equivalent_aspect_ratio"), "value_id"),
        "exposure_or_pp_and_pulse": ids(C, q("exposure", "partial_pressure", "pulse_time"), "condition_id"),
        "deposition_temperature": ids(C, q("deposition_temperature"), "condition_id"),
        "cycles": ids(C, q("cycle_number"), "condition_id"),
        "planar_gpc": ids(V, lambda r: r["quantity"] == "growth_per_cycle" and "position=local" not in r["qualifiers"], "value_id"),
        "sticking_or_reaction_prob": ids(V, q("initial_sticking_coefficient", "lumped_sticking_coefficient"), "value_id"),
        "recombination_prob": ids(V, q("recombination_probability"), "value_id"),
        "step_coverage": ids(V, q("step_coverage"), "value_id"),
        "front_slope_or_width": ids(V, q("front_slope"), "value_id"),
        "pore_or_channel_width": ids(V + C, lambda r: r["quantity"] == "feature_width" or (r["quantity"] == "other" and re.search(r"pore|gap|channel_height", r["label_as_printed"], re.I)), "value_id") or ids(C, q("feature_width"), "condition_id"),
        "process_mode": ids(SA, lambda r: r["process_mode"] and r["kind"] not in ("group", "model_run"), "sample_id", 3),
        "saturation_checked": "",
    }
    rows = []
    for it in CORE:
        found = find[it]
        st, why = NOTE.get((key, it), ("found" if found else "not read", ""))
        if found and st not in ("found",) and not NOTE.get((key, it)):
            st = "found"
        rows.append(f"| {it} | {st} | {found or '—'} | {why} |")
    extras = []
    draft = (HERE / pid / "checklist_draft.md")
    if draft.exists():
        core_rx = r"structure dims|pore|aspect|temperature|partial pressure|exposure|cycles|planar gpc|thickness profile|profile|pd50|step coverage|sticking|recombination|front|process mode|saturation"
        for line in draft.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and not line.startswith("| Key") and not line.startswith("|---") and not re.search(core_rx, line.split("|")[1], re.I):
                extras.append(line)
    text = (f"# Checklist: {pid} ({key})\n\nCore list (the 14 quantity_matrix columns plus saturation_checked). Status: found (ids in the tables) / "
            "not stated / not in document (SI) / not read. Ids are found in the final tables by rule; the reason column says what a status means here.\n\n"
            "| Core item | Status | Ids | Note |\n|---|---|---|---|\n" + "\n".join(rows) +
            "\n\n## Paper-specific extras (from the first pass)\n\n| Key quantity | Status | Where |\n|---|---|---|\n" + "\n".join(extras) + "\n")
    (HERE / pid / "checklist.md").write_text(text, encoding="utf-8")
    return [r.split("|")[2].strip() for r in rows]


if __name__ == "__main__":
    for pid, key in PAPERS.items():
        st = make(pid, key)
        print(pid, {s: st.count(s) for s in set(st)})
