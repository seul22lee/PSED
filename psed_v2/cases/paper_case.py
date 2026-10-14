#!/usr/bin/env python3
"""Exploration: writes cases/paper_case.csv, one row per in-scope paper with a PDF (58) and one column per case of cases.html
(1 to 11) and per part E candidate not built yet (S4, S5, S7 to S11).

    python3 psed_v2/cases/paper_case.py        (then make_cases.py and make_matrix_html.py, which read the CSV)

A cell is "used: <figures>" when the case draws on the paper (figure crops shown, points read, values in the case's CSV),
"excluded: <reason>" when the case's own rule, applied to figures.csv and quantity_matrix.csv, selects the paper but it was
judged not to belong (case_decisions.csv), "candidate, not used: <reason>" when selected and not yet decided (none for
Cases 1 to 11), and empty otherwise. "Used" is recorded by running the case functions of make_cases.py
with the crop call instrumented, so it follows the page as built.
"""
import csv, importlib.util, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
rd = lambda p: list(csv.DictReader((HERE / p).open(newline="", encoding="utf-8")))
MAN = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus/manifest.csv").open(newline="", encoding="utf-8"))}
PAPERS = sorted(p for p, r in MAN.items() if r["in_scope"] == "yes" and r["pdf_status"] == "ok")
FIG = rd("figures.csv")
QM = {r["paper_id"]: r for r in rd("quantity_matrix.csv")}
PTS = json.loads((HERE / "points.json").read_text(encoding="utf-8"))["series"]
HAND = {p for p, r in QM.items() if r["read_by_hand"] == "yes"}

COLS = [("c1", "Case 1 profiles across papers"), ("c2", "Case 2 O-radical recombination"), ("c3", "Case 3 one sample, several measurements"),
        ("c4", "Case 4 one experiment through the literature, fit against prediction"), ("c5", "Case 5 one symbol, several meanings"),
        ("c6", "Case 6 reactor-scale uniformity"), ("c7", "Case 7 samples across figures and methods"), ("c8", "Case 8 the review read as data"),
        ("c9", "Case 9 one method for every sticking value (S1)"), ("c10", "Case 10 coated EAR against limiting-step exposure (S2)"),
        ("c11", "Case 11 recombination against temperature and pressure, Knudsen break (S3, S6)"),
        ("S4", "S4 thermal against plasma depth"), ("S5", "S5 channel narrowing"), ("S7", "S7 planar saturation exposure of TMA"),
        ("S8", "S8 planar growth per cycle against temperature"), ("S9", "S9 pore-closure cycle"), ("S10", "S10 Arrhenius of sticking and recombination"),
        ("S11", "S11 growth above the planar value near the entrance")]


def figlab(fig, panel=""):
    f = str(fig)
    return (f if f.startswith("Table") else f"Fig. {f}") + (str(panel) if panel and not str(panel).startswith(" ") else (str(panel) if panel else ""))


def measured(r):
    return r["kind"] == "plot" and "measured" in r["data_kind"]


def profile_rule(r):
    """The case 1 panel rule: a measured plot of a thickness-like quantity against distance (either axis)."""
    if not measured(r):
        return False
    x, y = r["x_id"], r["y_id"]
    if x.startswith("film_thickness") and y == "distance":
        return True
    return re.sub(r"\{.*", "", x) in ("distance", "dimensionless_distance") and y.startswith(
        ("film_thickness", "normalized_thickness", "growth_per_cycle{position=local}", "coated_aspect_ratio"))


def hand_profile_rule(r):
    """A measured plot named, with its panel, in the hand-read measured_profile cell: catches depth profiles whose y is a
    diameter, counts, a signal or a composition, which the axis-id rule misses."""
    q = QM.get(r["paper_id"])
    if not measured(r) or not q or q["read_by_hand"] != "yes" or q["measured_profile"].startswith("no"):
        return False
    for f, pa in re.findall(r"Fig\. ?(\d+)([a-z](?:-[a-z])?)?", q["measured_profile"].split("model only")[0]):
        if f != str(r["figure"]):
            continue
        if not pa or not r["panel"]:
            return True
        lo, hi = (pa.split("-") + [pa])[:2]
        if lo <= r["panel"][:1] <= hi:
            return True
    return False


def is_profile(r):
    return profile_rule(r) or hand_profile_rule(r)


# ----------------------------------------------------------------------------- used: run the cases with crop() recorded
def used_by_case():
    spec = importlib.util.spec_from_file_location("make_cases", HERE / "make_cases.py")
    mc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mc)
    U = {k: {} for k, _ in COLS}
    real = mc.crop
    cur = {"k": None}

    def rec(pid, fig):
        U[cur["k"]].setdefault(pid, []).append(figlab(fig))
        return ""
    mc.crop = rec
    for i in range(1, 12):
        cur["k"] = f"c{i}"
        getattr(mc, f"case{i}")()
    mc.crop = real
    for sr in mc.case1_series():                          # case 1: every profile it plots, from its own points or from Case 9's
        U["c1"].setdefault(sr["p"]["paper"], []).append(figlab(sr["p"]["figure"], sr["p"].get("panel", "")))
    for pid, fig, sym, *_ in mc.N3:                       # case 5: rows of its label table
        U["c5"].setdefault(pid, []).append(f"Fig. {fig} ({sym})")
    for p in PTS:                                         # points read by eye belong to their case
        U[f"c{p['case']}"].setdefault(p["paper"], []).append(figlab(p["figure"], p.get("panel", "")))
    for r in rd("cremers/source_checks.csv"):             # case 8: rows of the review checked against the source
        if r["paper_id"]:
            U["c8"].setdefault(r["paper_id"], []).append(f"source check ({r['where']})")
    for r in rd("sticking_reported.csv"):                 # case 9 lists the reported value of every S1 paper, also without a profile read
        U["c9"].setdefault(r["paper_id"], []).append(f"reported value ({r['where']})")
    for r in rd("exposure_ear.csv"):
        U["c10"].setdefault(r["paper_id"], []).append(r["where"])
    for r in rd("recombination.csv"):
        if r["use"] == "plotted":
            U["c11"].setdefault(r["paper_id"], []).append(r["where"])
    return {k: {p: "; ".join(dict.fromkeys(v)) for p, v in d.items()} for k, d in U.items()}


# ----------------------------------------------------------------------------- candidates: each case's own rule
def rows_of(pid, test):
    return [r for r in FIG if r["paper_id"] == pid and test(r)]


def figs(rows):
    return ", ".join(dict.fromkeys(figlab(r["figure"], r["panel"]) for r in rows))


def no(v):
    return not v or v.startswith("no") or v == "not read"


def candidates(pid):
    q = QM.get(pid, {}); hand = pid in HAND; C = {}
    prof = rows_of(pid, is_profile)
    if prof:
        C["c1"] = f"measured depth profile ({figs(prof)})"
    rec = rows_of(pid, lambda r: "coated_aspect_ratio" in r["y_id"] and ("pulse_time" in r["x_id"] or "plasma time" in r["x"].lower()))
    if rec:
        C["c2"] = f"half-thickness depth against plasma time ({figs(rec)})"
    elif hand and not no(q.get("recombination_prob", "")):
        C["c2"] = "recombination probability in the matrix: " + q["recombination_prob"][:80]
    samp, stated = {}, {}                                  # named samples only: "u:<fig>" marks an unnamed sample
    for r in FIG:
        sid = r["sample"].split(":")[0].strip()
        if r["paper_id"] == pid and sid and sid != "u":
            key = re.sub(r"^possibly ", "", sid)
            samp.setdefault(key, []).append(r)
            if not sid.startswith("possibly"):
                stated.setdefault(key, []).append(r)
    imgs = [s for s, rs in stated.items() if any(r["kind"] == "image" for r in rs) and any(is_profile(r) for r in rs)]
    if imgs:
        C["c3"] = f"profile and image of the same named sample, link stated ({', '.join(imgs[:3])})"
    reuse = rows_of(pid, lambda r: r["kind"] == "plot" and "cited" in r["data_kind"])
    if reuse:
        C["c4"] = f"curves of another paper drawn again ({figs(reuse)})"
    words = rows_of(pid, lambda r: r["kind"] == "plot" and re.search(r"coverage|penetration|conformality", r["y"], re.I))
    if words:
        C["c5"] = f"coverage, penetration or conformality word on an axis ({figs(words)})"
    uni = rows_of(pid, lambda r: measured(r) and re.match(r"(growth_per_cycle|film_thickness|normalized_thickness)", r["y_id"]) and not re.sub(r"\{.*", "", r["x_id"]) in ("distance", "dimensionless_distance")
                  and re.search(r"location|position|slot|wafer|point|radius|inlet", r["x"], re.I))
    if uni:
        C["c6"] = f"growth or thickness against position on a part, tube or batch ({figs(uni)})"
    multi = [s for s, rs in stated.items() if len({r["figure"] for r in rs}) >= 2 or len({r["method"] for r in rs if r["method"]}) >= 2]
    if multi and not prof:
        C["c7"] = f"a named sample seen by several figures or methods ({', '.join(multi[:3])})"
    if MAN[pid].get("cremers") == "O":
        C["c8"] = "cited in the review (Cremers 2019 reference list)"
    if prof or (hand and not no(q.get("measured_profile", ""))):
        C["c9"] = "measured depth profile" + (f" ({figs(prof)})" if prof else "")
    if q.get("limiting_step_exposure") == "yes":
        C["c10"] = "limiting_step_exposure = yes"
    if hand and not no(q.get("recombination_prob", "")):
        C["c11"] = "recombination probability in the matrix: " + q["recombination_prob"][:80]
    pm = q.get("process_mode", "")
    if (prof or (hand and not no(q.get("measured_profile", "")))) and re.search(r"plasma", pm, re.I) and re.search(r"thermal|H2O|water|ozone|O3", pm, re.I):
        C["S4"] = "measured profile and both thermal and plasma processes"
    if (prof or (hand and not no(q.get("measured_profile", "")))) and hand and re.search(r"lateral|channel|gap|PillarHall|LHAR|cavity", q.get("structure_class", ""), re.I) and not no(q.get("pore_or_channel_width", "")):
        C["S5"] = "measured profile in a lateral channel with a stated height"
    sat = rows_of(pid, lambda r: measured(r) and ("pulse_time" in r["x_id"] or "exposure" in r["x_id"]) and "growth_per_cycle{position=planar" in r["y_id"])
    if sat and re.search(r"TMA", " ".join(r["precursor"] for r in sat)):
        C["S7"] = f"planar growth against TMA pulse or exposure ({figs(sat)})"
    gt = rows_of(pid, lambda r: measured(r) and "deposition_temperature" in r["x_id"] and "growth_per_cycle" in r["y_id"])
    if gt:
        C["S8"] = f"growth per cycle against temperature ({figs(gt)})"
    elif hand and not no(q.get("planar_gpc", "")) and not no(q.get("deposition_temperature", "")):
        C["S8"] = "planar growth per cycle at a stated temperature (text or table)"
    if hand and not no(q.get("pore_or_channel_width", "")) and re.search(r"pore|AAO|membrane|MOF|particle|powder|porous|forest", q.get("structure_class", ""), re.I) and not no(q.get("cycles", "")):
        C["S9"] = "pore width, porous structure and cycle counts stated"
    arr = rows_of(pid, lambda r: "deposition_temperature" in r["x_id"] and re.search(r"initial_sticking_coefficient|recombination_probability", r["y_id"]))
    reptemps = [r for r in rd("sticking_reported.csv") if r["paper_id"] == pid and len(re.findall(r"\d{2,3} ?°C", r["value"])) >= 2]
    if arr or reptemps:
        C["S10"] = "sticking or recombination at several temperatures" + (f" ({figs(arr)})" if arr else " (reported values)")
    if (prof or (hand and not no(q.get("measured_profile", "")))) and hand and not no(q.get("planar_gpc", "")):
        C["S11"] = "measured profile and a planar reference growth"
    return C


def main():
    U = used_by_case()
    DEC = {(r["case"], r["paper_id"]): r["reason"] for r in rd("case_decisions.csv") if r["decision"] == "excluded"}
    out = []
    for pid in PAPERS:
        m = MAN[pid]
        a = (m.get("authors") or "").split(";")[0].strip()
        row = {"paper_id": pid, "year": m.get("year", ""), "first_author": a.split(" ")[-1] if a else "", "read_by_hand": "yes" if pid in HAND else "no"}
        C = candidates(pid)
        for k, _ in COLS:
            if pid in U[k]:
                row[k] = f"used: {U[k][pid]}"
            elif (k, pid) in DEC:
                row[k] = f"excluded: {DEC[(k, pid)]}"
            else:
                row[k] = f"candidate, not used: {C[k]}" if k in C else ""
        row["in_no_case"] = "yes" if not any(row[f"c{i}"].startswith("used") for i in range(1, 12)) else "no"
        out.append(row)
    with (HERE / "paper_case.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper_id", "year", "first_author", "read_by_hand"] + [k for k, _ in COLS] + ["in_no_case"])
        w.writeheader(); w.writerows(out)
    for k, t in COLS:
        print(f"{k:4s} used {sum(r[k].startswith('used') for r in out):2d}  excluded {sum(r[k].startswith('excluded') for r in out):2d}  candidate {sum(r[k].startswith('candidate') for r in out):2d}  {t}")
    print("papers in no case:", sum(r["in_no_case"] == "yes" for r in out), "of", len(out))
    left = [(k, r["paper_id"]) for r in out for k in (f"c{i}" for i in range(1, 12)) if r[k].startswith("candidate")]
    print("unresolved candidates in Cases 1-11:", len(left), left[:12])


if __name__ == "__main__":
    main()
