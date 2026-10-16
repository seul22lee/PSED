#!/usr/bin/env python3
"""The 26 questions that test the schema: each a function computing its answer from the facts (the three papers' facts.csv and
user.facts.csv), no numbers typed in. Writes questions.csv (id, question, kind, status, answer, how, changed) and prints a summary.

    python3 psed_v2/pilot/questions.py

A question is answered when the computation reaches the hand answer's content, wrong when it reaches a different one, unanswerable
when a fact is missing, a fact sits in the wrong place, no join rule, derived quantity, operation or assumed fact exists; the `how`
column says which. The library below reads the trees only (condition vectors, results, comparisons, members); every rule the
questions needed beyond that was added class by class (see HANDOFF, Comparison layer).
"""
import collections, csv, json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
from elements import PAPERS  # noqa: E402
from facts import FIELDS, num  # noqa: E402

from query import *  # noqa: E402,F401,F403  (the query layer)
from query import _candidates, _matches  # noqa: E402,F401

# ------------------------------------------------------------------ the questions
def q1():
    """PD50 against TMA pulse time over Series E, with every other setting that differs listed."""
    T = TREES["yim20"]; c = T.comp("E"); ms = T.member_entities(c)
    rows = []
    for m in ms:
        v, r = T.vector(m), T.results(m)
        pulse = v.get("pulse_time{species=TMA;step=reactant_A}"); pd = r.get("penetration_depth{level=50%;origin=entrance}")
        rows.append((T.label(m), pulse and val(pulse[0]), pd and val(pd[0])))
    diff = differing(T, ms, exclude={"pulse_time{species=TMA;step=reactant_A}"})
    text = "; ".join(f"{lab}: pulse {g(p)} s, PD50 {g(d)} µm" for lab, p, d in rows) + (f" · also differs: {diff}" if diff else "")
    pts = [(p, d) for _, p, d in rows if p and d]
    if len(pts) < 3 or any(p is None for p, _ in pts):
        return unanswerable(text, "fewer than three members with a pulse time and a PD50")
    b, a, res = power_fit(pts)
    text += f" · fit PD50 ∝ pulse^{g(b, 2)} (rms residual {g(res, 2)} in log10)"
    ykey, xkey = "penetration_depth{level=50%;origin=entrance}", "pulse_time{species=TMA;step=reactant_A}"
    for k, m in [(k, m) for k, m in {k: {e: "; ".join(fmt(f) for f in fs) for e in ms for kk, fs in T.vector(e).items() if kk == k} for k in {kk for e in ms for kk in T.vector(e)}}.items()
                 if k != xkey and len(m) == len(ms) and len(set(m.values())) > 1]:
        common = max(set(m.values()), key=list(m.values()).count)
        for e, v in m.items():
            if v != common:
                fac, c = correction(T, k, ykey, v, common)
                if fac:
                    corrected = [(p, d * fac if lab == T.label(e) else d) for lab, p, d in rows]
                    b2, _, res2 = power_fit(corrected)
                    text += f" · {T.label(e)} corrected for {k} {v}→{common} by {g(fac, 3)} from {c['label_as_printed']}: PD50 {g(dict(corrected)[next(p for lab, p, _ in rows if lab == T.label(e))])} µm, fit exponent {g(b2, 2)} (residual {g(res2, 2)})"
    return answered(text, "series_xy over Series E (pulse from the vectors, PD50 from the results), differing() for the confounders, power_fit (log-log least squares), correction() from the stated comparison that varies only the confounder (Series A), and the fit again")


def q2():
    """Over Series D, PD50 against the effective channel height H − 2·S_IIb."""
    T = TREES["yim20"]; rows = []
    for m in T.member_entities(T.comp("D")):
        h = derive(T, m, "effective_channel_height"); pd = T.results(m).get("penetration_depth{level=50%;origin=entrance}")
        if "error" in h or not pd:
            return unanswerable("", f"{T.label(m)}: {h.get('error', 'no PD50')}")
        rows.append((T.label(m), h["value"], val(pd[0]), pd[0]))
    ref = max(rows, key=lambda r: r[1])
    text = "; ".join(f"{lab}: H_eff {g(h)} nm, PD50 {fmt(pd)}, √H_eff scaling from {ref[0]} predicts {g(scale(ref[1], ref[2], h, 0.5))} µm" for lab, h, _, pd in rows)
    return answered(text, "lists.DERIVED effective_channel_height per member of Series D (its design height and plateau thickness), scale() by a square-root law from the member with the largest H_eff, against the measured PD50")


def q3():
    """For sample 11, every penetration depth value by method."""
    T = TREES["yim20"]; e = "yim20:ent:11"
    pds = [f for k, fs in T.results(e).items() for f in fs if f["quantity"] == "penetration_depth"]
    text = "; ".join(f"{fmt(f)} by {f['method']} ({f['qualifiers'] or 'no qualifier'}, {f['fact_id']})" for f in pds)
    rs = routes(pds)
    if not rs:
        return unanswerable(text, "fewer than two penetration depth facts on sample 11")
    return answered(text + " · " + "; ".join(f"ratio {g(r, 3)} ({a['method']} over {b['method']}): {w}" for a, b, r, w in rs), "routes(): every pair of facts reaching one (entity, quantity) as a ratio, with a warning naming what differs in their definitions")


def q4():
    """Over Series F, the ratio GPC_I / GPC_IIb against purge time."""
    T = TREES["yim20"]; c = T.comp("F")
    rows = sorted(((val(T.vector(m)["purge_time{step=purge_A}"][0]), T.label(m), res(T, m, "growth_per_cycle", position="outside")[0], res(T, m, "growth_per_cycle", position="plateau")[0])
                   for m in T.member_entities(c)), key=lambda r: r[0])
    text = "; ".join(f"{lab}: purge {g(p)} s, GPC_I/GPC_IIb = {fmt(a)} / {fmt(b)} = {g(val(a) / val(b), 3)}" for p, lab, a, b in rows)
    return answered(text, "the members of Series F ordered by purge time (vector), the ratio of two results on each (routes on one entity)")


def q5():
    """Which stated comparisons in yim20 have an effect smaller than the reproducibility sd, per result quantity."""
    T = TREES["yim20"]; out = []
    for c in [c for c in T.comps if c["kind"] == "series"]:
        keys = sorted({k for m in T.member_entities(c) for k in T.results(m) if k.split("{")[0] in ("penetration_depth", "film_thickness", "growth_per_cycle") and "stat=" not in k})
        parts = [f"{L.LABELS.get(k, k)} range {g(j['effect'], 2)} {j['unit']}: {j['sentence']}" for k in keys for j in [judge(T, c, k)] if j]
        out.append(f"{c['label_as_printed']}: " + ("; ".join(parts) if parts else "no shared result"))
    return answered(" · ".join(out), "judge(): the range over each series' members against the range expected from run-to-run scatter of the same kind (d2 × sd) at the base condition")


def q6():
    """TMA exposure per pulse and per run, in Torr·s."""
    T = TREES["yim20"]; per_pulse, per_run, assumed = {}, {}, set()
    for e in T.entities():
        if T.dep_of(e) is None or T.byid[T.dep_of(e)]["kind"] != "deposition":
            continue
        a, b = derive(T, e, "exposure"), derive(T, e, "exposure_per_run")
        if "error" in a or "error" in b:
            continue
        per_pulse.setdefault(g(a["value"], 2), []).append(T.label(e)); per_run.setdefault(g(b["value"], 2), []).append(T.label(e)); assumed |= set(a["assumed"]) | set(b["assumed"])
    if not per_pulse:
        return unanswerable("", "no entity yields an exposure: the TMA partial pressure or the pulse time is missing")
    ex = derive(T, T.entities()[0], "exposure")
    text = "per pulse: " + "; ".join(f"{v} Torr s ({', '.join(ls[:4])}{'…' if len(ls) > 4 else ''})" for v, ls in per_pulse.items()) + " · per run: " + \
        "; ".join(f"{v} Torr s ({', '.join(ls[:4])}{'…' if len(ls) > 4 else ''})" for v, ls in per_run.items()) + \
        f" · from an assumed fact: {', '.join(sorted(assumed))} (the model input 65 Pa stands in for the TMA pressure, which the paper does not state)"
    return answered(text, "lists.DERIVED exposure (p_A × pulse time) and exposure_per_run (× cycles) per entity; the pressure from user.facts.csv (data_kind assumed), named in the answer")


def q7():
    """c_TMA of this work against Ylilammi 2018 in Table 2, with the film density each assumed."""
    T = TREES["yim20"]
    own_ = one("yim20", quantity="lumped_sticking_coefficient", qualifiers="species=TMA", type="derived")
    yli = [f for f in T.facts(quantity="lumped_sticking_coefficient", qualifiers="species=TMA", type="cited") if "Ylilammi" in f["statement"]]
    d_own = one("yim20", quantity="film_density", type="model"); d_yli = [f for f in T.facts(quantity="film_density", type="cited") if "Ylilammi" in f["statement"]]
    if not (own_ and yli and d_own and d_yli):
        return unanswerable("", "missing fact: a sticking coefficient or a density")
    r1, r2 = val(yli[0]) / val(own_), val(d_yli[0]) / val(d_own)
    return answered(f"c_TMA {fmt(own_)} (this work) vs {fmt(yli[0])} (Ylilammi 2018), ratio {g(r1)}; density {fmt(d_own)} vs {fmt(d_yli[0])}, ratio {g(r2)}",
                    "lookup of four facts, two ratios")


def q8():
    """The effective channel height of the 500 nm design from the fabrication tolerances."""
    T = TREES["yim20"]
    pieces = [e["fact_id"] for e in T.rows if e["type"] == "entity" and T.byid.get(e["parent"], {}).get("type") == "entity" and T.dep_of(e["fact_id"]) is None]
    chip = next((e for e in pieces if fmt(T.vector(e).get("feature_height", [{}])[0] or {"value": "", "value_min": "", "value_max": "", "censor": "", "unit": "", "value_text": ""}) == "500 nm"), None)
    if not chip:
        return unanswerable("", "no input entity (a piece of the chips as fabricated) carries the 500 nm design height as its own setting")
    H, r = T.vector(chip)["feature_height"][0], T.results(chip)
    tol = [f for fs in r.values() for f in fs if quals(f).get("stat") == "tolerance" and f["quantity"] == "feature_height"] or None
    bend = r.get("other[membrane bending displacement]")
    step = T.results(T.byid[chip]["parent"]).get("other[nanostep height]")                 # the chip type's observation, above the piece
    if not (tol and bend and step):
        return unanswerable("", "the tolerance, the bending or the nanostep is not an observation on the chip entities")
    return answered(f"design {fmt(H)} ± {fmt(tol[0])}, membrane bending {fmt(bend[0])}, entrance nanostep {fmt(step[0])} → effective height ≈ {g(val(H) - val(bend[0]) - val(step[0]))} nm "
                    f"({g(val(H) - val(bend[0]))} nm before the nanostep); all three observed on the chips before deposition",
                    "the chip piece's own setting (design height) and its order-0 observations (tolerance, bending), the nanostep from the chip type above it; the subtraction in the question")


def q9():
    """GPC at ratio 0.20 implied by the cycle numbers chosen to give 10 nm, per temperature, against the Fig. 7b colour-read GPC."""
    T = TREES["mat22"]
    out = []
    for e in T.entities():
        v = T.vector(e)
        if v.get("plasma_gas_ratio{gas=H2}") and fmt(v["plasma_gas_ratio{gas=H2}"][0]) == "0.20" and re.fullmatch(r"mat22:ent:T\d+_R0\.20", e) and v.get("cycle_number") and v.get("film_thickness{kind=target}"):
            n, th = val(v["cycle_number"][0]), val(v["film_thickness{kind=target}"][0])
            gpc = res(T, e, "growth_per_cycle")
            if n and th and gpc:
                out.append((val(v["deposition_temperature"][0]), f"{fmt(v['deposition_temperature'][0])}: {g(n, 3)} cycles for {fmt(v['film_thickness{kind=target}'][0])} target → {g(10 * th / n, 2)} Å implied vs {fmt(gpc[0])} read from colour"))
    if not out:
        return unanswerable("", "no cell carries its cycle count, thickness target and a GPC")
    return answered("; ".join(t for _, t in sorted(out, reverse=True)), "per ratio-0.20 cell: the deposition's cycle count and 10 nm target (settings) against the colour-read GPC on the cell film")


def q10():
    """Thickness against cycles at 150 °C, ratio 0.80, from every source."""
    T = TREES["mat22"]
    ents = matching(T, deposition_temperature=150, plasma_gas_ratio=0.80, material="MoS2")
    rows = []
    for e in ents:
        v = T.vector(e); N = val(v["cycle_number"][0]) if v.get("cycle_number") else None
        for f in res(T, e, "film_thickness"):                                    # a stated thickness, or the last point of a thickness-vs-cycles curve
            if quals(f).get("stat"):
                continue
            if f["value"]:
                rows.append((N, val(f), f"{T.label(e)}: {fmt(f)} at {g(N)} cycles ({f['fact_id']}, {kind(f)})"))
            elif f["points_ref"] and quals(f).get("x") == "cycle_number" and f["points_ref"] in T.points:
                x, y = T.points[f["points_ref"]]["points"][-1]
                rows.append((x, y, f"{T.label(e)}: curve {f['points_ref']} ends at {g(y)} nm after {g(x)} cycles"))
        for f in res(T, e, "growth_per_cycle"):
            if f["value"]:
                rows.append((None, None, f"{T.label(e)}: GPC {fmt(f)} (averaged over {quals(f).get('over', 'the run').replace('_', ' ')})"))
    gpc = [10 * t / n for n, t, _ in rows if n and t]
    diff = differing(T, ents)
    return (answered("; ".join(x for _, _, x in rows) + f" · thickness/cycles from {g(min(gpc), 2)} to {g(max(gpc), 2)} Å/cycle · these {len(ents)} films differ in: {diff}",
                     "matching(): every entity at 150 °C and ratio 0.80 (a filter, no join); their thicknesses, curve ends and GPCs with definitions; differing() lists what else differs")
            if rows else unanswerable("", "no thickness at 150 °C, ratio 0.80"))


def q11():
    """Mo atoms per cycle from RBS against GPC from SE at 150 °C, ratio 0.80, with the density."""
    T = TREES["mat22"]
    ents = matching(T, deposition_temperature=150, plasma_gas_ratio=0.80)
    gc = [e for e in ents if res(T, e, "atoms_per_cycle", element="Mo")]
    se = [e for e in ents if res(T, e, "growth_per_cycle")]
    if not (gc and se):
        return unanswerable("", "no 150 °C, 0.80 film with RBS atoms per cycle, or none with an SE GPC")
    d = derive(T, gc[0], "growth_per_cycle")
    if "error" in d:
        return unanswerable("", f"derived GPC from atoms per cycle fails: {d['error']}")
    f = res(T, se[0], "growth_per_cycle")[0]
    ratio = d["value"] / L.convert(val(f), f["unit"], "nm")
    defs = f"definitions differ: the RBS value is over the run, the SE value over the {quals(f).get('over', 'run').replace('_', ' ')}" if quals(f).get("over") != "run" else "same definition"
    return answered(f"{T.label(gc[0])}: GPC from RBS {dtext(d, 2)} vs SE GPC {fmt(f)} on {T.label(se[0])} ({f['fact_id']}): ratio {g(ratio, 2)}; {defs} · the two films differ in: {differing(T, [gc[0], se[0]])}",
                    "matching() at 150 °C and 0.80; lists.DERIVED growth_per_cycle on the RBS film (assumed M, its own density); the SE GPC of the cell film; differing() names what differs, for the reader to judge")


def q12():
    """The full composition of the 150 °C, 0.80 film including H, and its density relative to bulk."""
    T = TREES["mat22"]
    es = [e for e in T.entities() if any(f["quantity"] == "composition" and quals(f).get("element") == "H" for fs in T.results(e).values() for f in fs) and fmt(T.vector(e)["plasma_gas_ratio{gas=H2}"][0]) == "0.80" and fmt(T.vector(e)["deposition_temperature"][0]) == "150 °C"]
    if not es:
        return unanswerable("", "no 150 °C, ratio 0.80 entity carries an H content")
    e = es[0]; h, r = derive(T, e, "h_per_metal"), derive(T, e, "density_relative_to_bulk")
    if "error" in h or "error" in r:
        return unanswerable("", f"{h.get('error', '')} {r.get('error', '')}".strip())
    smo = next(v for n, _, v, _, _ in h["inputs"] if n == "SMo")
    return answered(f"{T.label(e)}: MoS{g(smo, 2)}H{g(h['value'], 2)} [{dtext(h)}]; density {dtext(r, 2)} of bulk", "lists.DERIVED h_per_metal (H at.% over Mo at.% from S/Mo and the other at.%) and density_relative_to_bulk (the paper's cited bulk density, reference=bulk)")


def q13():
    """The H2 fraction of the total plasma feed (Ar included) for each ratio."""
    T = TREES["mat22"]
    by = collections.defaultdict(dict)
    for f in T.facts(quantity="gas_flow_rate", type="setting"):
        q = quals(f)
        if q.get("step") == "plasma" and q.get("ratio") and q.get("gas"):
            by[q["ratio"]][q["gas"]] = val(f)
    out = []
    for r, gases in sorted(by.items(), key=lambda x: float(x[0])):
        tot = sum(gases.values())
        out.append(f"ratio {r}: H2 {g(gases.get('H2', 0))} of {g(tot)} sccm = {g(100 * gases.get('H2', 0) / tot, 2)} %")
    return answered("; ".join(out), "the recipe's Table 2 flows keyed by their ratio= qualifier, H2 over the sum of H2S, H2 and Ar") if out else unanswerable("", "no flows keyed by ratio")


def q14():
    """Sheet resistance of the PET film."""
    T = TREES["mat22"]
    es = [e for e in T.entities() if "PET" in T.vector(e).get("substrate", [{"value_text": ""}])[0]["value_text"] and T.results(e).get("resistivity")]
    if not es:
        return unanswerable("", "no entity on a PET substrate with a resistivity")
    d = derive(T, es[0], "sheet_resistance")
    return answered(f"{T.label(es[0])}: {dtext(d, 2)}", "lists.DERIVED sheet_resistance (resistivity / film thickness, units normalised)") if "error" not in d else unanswerable("", d["error"])


def q15():
    """For 120 vs 120/160 °C, the ratio of every quantity measured on both."""
    T = TREES["gre23"]; c = T.comp("schedules")
    tops = {fmt(T.vector(m)["deposition_temperature"][0]): m for m in T.member_entities(c) if T.byid[T.byid[m]["parent"]]["type"] == "activity"}
    a = next((m for t, m in tops.items() if t == "120 °C"), None); b = next((m for t, m in tops.items() if "/" in T.label(m)), None)
    if not (a and b):
        return unanswerable("", "the 120 °C and 120/160 °C pair entities are not both members of the schedules comparison")
    rs = ratios_between(T, a, b)
    text = "; ".join(f"{L.LABELS.get(k, k)} {fmt(fa)} / {fmt(fb)} = {g(x, 3)}" if how == "ratio" else f"{L.LABELS.get(k, k)} {fmt(fa)} − {fmt(fb)} = {g(x, 3)} {fb['unit']}" for k, fa, fb, how, x in rs)
    rel = [f for k, fs in results_deep(T, a).items() for f in fs if "relative to" in f["label_as_printed"] and f["value"]]
    text += " · stated relative: " + "; ".join(f"{f['label_as_printed']} {fmt(f)} → {g(1 + val(f) / 100, 3)}" for f in rel)
    return answered(text, "ratios_between(): every result both pairs carry, their pieces' and their runs' monitors included; a stated relative count on one section reported as the third route")


def q16():
    """Crystalline ZnO fraction from XRD weight % against gravimetric ZnO %."""
    T = TREES["gre23"]; out = []
    for m in T.member_entities(T.comp("schedules")):
        if T.byid[T.byid[m]["parent"]]["type"] != "activity":
            continue
        r = results_deep(T, m); x = [f for k, fs in r.items() for f in fs if f["quantity"] == "composition" and quals(f).get("species") == "ZnO" and f["value"]]
        d = derive(T, m, "coating_mass_fraction")
        if x and "error" not in d:
            xb = quals(x[0]).get("relative_to", "not_stated").replace("_", " ")
            out.append(f"{T.label(m)}: XRD zincite {fmt(x[0])} ({x[0]['fact_id']}, basis {xb}) against the coating's mass fraction " +
                       " or ".join(f"{g(v, 3)} % if the {lab}" for lab, v in d["readings"]) if d["readings"] else f"{T.label(m)}: {dtext(d)}")
    return answered(" · ".join(out), "lists.DERIVED coating_mass_fraction from the pair's mass gain, one reading per basis (the paper states neither), beside the XRD piece's zincite wt% (its basis not stated either)") if out else unanswerable("", "no pair with both an XRD zincite fraction and a mass gain")


def q17():
    """Does the mass balance close: Δn_s per cycle × 20 against the ZnO mass gained by the two NPCs."""
    T = TREES["gre23"]; out, assumed = [], set()
    for m in T.member_entities(T.comp("schedules")):
        if T.byid[T.byid[m]["parent"]]["type"] != "activity":
            continue                                                            # the pairs, not the pieces cut from them
        a, b = derive(T, m, "moles_deposited"), derive(T, m, "moles_from_mass_gain")
        if "error" in a or "error" in b:
            return unanswerable("", f"{T.label(m)}: {a.get('error', '')} {b.get('error', '')}".strip())
        out.append(f"{T.label(m)}: Δn_s × N = {g(a['value'], 2)} mmol vs mass gain → " + " or ".join(f"{g(v, 2)} mmol ({g(100 * (a['value'] / v - 1), 2)} % apart) if the {lab}" for lab, v in (b["readings"] or [("stated basis", b["value"])])))
        assumed |= set(a["assumed"]) | set(b["assumed"])
    return answered("; ".join(out) + f" · assumed inputs: {', '.join(sorted(assumed))} (molar mass of ZnO, two NPCs per run); the gap is the paper's own: Δn_s is from GPC via the porosity model, the mass gain is weighed",
                    "lists.DERIVED moles_deposited (Δn_s × cycles) and moles_from_mass_gain (mass gain × powder mass × NPCs per run / M) on each pair entity")


def q18():
    """ZnO volume fraction in the 120 °C NPC from coating thickness and particle size."""
    T = TREES["gre23"]
    es = [e for e in T.member_entities(T.comp("schedules")) if fmt(T.vector(e)["deposition_temperature"][0]) == "120 °C"]
    if not es:
        return unanswerable("", "no 120 °C pair entity")
    d = derive(T, es[0], "shell_volume_fraction")
    return answered(f"{T.label(es[0])}: {dtext(d, 2)}", "lists.DERIVED shell_volume_fraction on the pair: φ_i from its vector, d_NP from the compacts input entity, the coating thickness from its results") if "error" not in d else unanswerable("", d["error"])


def q19():
    """Knudsen number of each paper's structure under its own conditions."""
    out = []
    for k, T in TREES.items():
        st = (one(k, quantity="structure_type") or {}).get("value_text", "")
        if st == "planar":
            out.append(f"{k}: planar, no Knudsen number applies"); continue
        es = [e for e in T.entities() if T.dep_of(e) and T.byid[T.dep_of(e)]["kind"] == "deposition"]
        stated = [f for f in T.rows if f["quantity"] == "knudsen_number" and f["value"]]
        if stated:
            out.append(f"{k}: " + "; ".join(f"Kn {fmt(f)} ({f['qualifiers'] or 'no qualifier'}, {f['type']} fact {f['fact_id']})" for f in stated)); continue
        d = derive(T, es[0], "knudsen_number")
        out.append(f"{k}: " + (f"Kn ≈ {dtext(d, 2)}" if "error" not in d else d["error"]))
    return answered(" · ".join(out), "stated Kn where the paper gives it; else lists.DERIVED mean_free_path (k_B T / √2 π d² p, the diameter assumed by analogy with TMA) and knudsen_number (λ over d_NP from the compacts input entity); planar structures excluded")


def q20():
    """Exposure per dose, yim20 against gre23, and what AR² scaling from yim20's x̃50 would predict for gre23's AR."""
    Y, G = TREES["yim20"], TREES["gre23"]
    rep_ = next(c for c in Y.comps if c["kind"] == "replicate"); ms = Y.member_entities(rep_)
    ey = derive(Y, ms[0], "exposure")
    xs = [val(Y.results(m)["dimensionless_distance{by=H;level=50%}"][0]) for m in ms if "dimensionless_distance{by=H;level=50%}" in Y.results(m)]
    gp = [m for m in G.member_entities(G.comp("schedules")) if G.byid[G.byid[m]["parent"]]["type"] == "activity"][0]
    eg = [f for f in G.vector(gp).get("exposure", []) if f["value"] and not f["censor"]]
    ar = [f for fs in results_deep(G, G.inputs_of(gp)[0]).values() for f in fs if f["quantity"] == "aspect_ratio"] if G.inputs_of(gp) else []
    if "error" in ey or not xs or not eg or not ar:
        return unanswerable("", "missing: yim20 exposure, x̃50, gre23 exposure or aspect ratio")
    arY = sum(xs) / len(xs); pred = scale(arY, ey["value"], val(ar[0]), 2); egv = L.convert(val(eg[0]), eg[0]["unit"], "Torr s")
    return answered(f"yim20 exposure per dose {g(ey['value'], 2)} Torr s ({dtext(ey, 2)}) vs gre23 {g(egv, 3)} Torr s ({eg[0]['fact_id']}); yim20 reaches x̃50 ≈ {g(arY, 3)} (mean over the replicate set), "
                    f"gre23's AR {fmt(ar[0])} ({ar[0]['fact_id']}): AR² scaling predicts {g(pred, 2)} Torr s, gre23 used {g(egv / pred, 2)}× that",
                    "lists.DERIVED exposure on yim20's replicate set (assumed TMA pressure), its x̃50 as the aspect ratio reached, gre23's stated exposure and the compacts' aspect ratio; scale() by a square law")


def q21():
    """Metal atoms per nm² per cycle in all three papers."""
    out = []
    for k, T in TREES.items():
        stated = [f for f in T.rows if f["quantity"] in ("atoms_per_cycle", "saturation_density") and f["value"] and f["type"] != "cited"]
        if stated:
            out.append(f"{k}: " + "; ".join(f"{fmt(f)} ({L.LABELS[f['quantity']]}, {f['type']} {f['fact_id']}, {f['data_kind']}{', ' + T.label(T.ent_of(f['fact_id'])) if T.ent_of(f['fact_id']) else ''})" for f in stated)); continue
        es = [e for e in T.entities() if res(T, e, "growth_per_cycle")]
        d = derive(T, es[0], "atoms_per_cycle") if es else {"error": "no GPC"}
        out.append(f"{k}: " + (f"{dtext(d, 2)} ({T.label(es[0])})" if "error" not in d else d["error"]))
    return answered(" · ".join(out), "stated atoms per cycle or the model's saturation density where a paper gives one; else lists.DERIVED atoms_per_cycle (GPC × ρ_bulk N_A / M) with assumed ρ and M named")


def q22():
    """Deposited thickness per hour of reactor time in all three."""
    out = []
    for k, T in TREES.items():
        vals = {}
        for e in T.entities():
            d = derive(T, e, "deposition_rate")
            if "error" not in d:
                vals.setdefault(g(d["value"], 2), []).append((T.label(e), d))
        if not vals:
            out.append(f"{k}: no entity with a GPC and a cycle time"); continue
        lo, hi, common = min(vals, key=float), max(vals, key=float), max(vals, key=lambda v: len(vals[v]))
        out.append(f"{k}: {common} nm/h for {len(vals[common])} of {sum(len(v) for v in vals.values())} entities ({vals[common][0][0]}: {dtext(vals[common][0][1], 2)})" +
                   (f", {lo}–{hi} nm/h over all (purge and pulse times vary)" if lo != hi else ""))
    return answered(" · ".join(out), "lists.DERIVED deposition_rate (GPC × 3600 / cycle time) per entity; the cycle time stated (mat22, gre23) or derived as the sum of pulse and purge times (yim20)")


def q23():
    """Every claim that puts water desorption or surface OH as a cause, with the quantified effect behind each."""
    toks = {"mechanism:surface_OH", "mechanism:residual_H2O", "mechanism:desorption", "mechanism:water_readsorption"}
    cs = [(k, f) for k, T in TREES.items() for f in T.rows if f["type"] == "claim" and set(f["cause"].split(";")) & toks]
    out = []
    for k, f in cs:
        T = TREES[k]; parts = []
        for c in scope_comparisons(T, f):
            comp = T.byid[c]
            for q in [q for q in f["effect"].split(";") if q and not q.startswith("mechanism:")]:
                linked = [e for e in (T.ent_of(l) for l in f["links"].split(";") if l in T.byid) if e]
                for key in sorted({kk for m in T.member_entities(comp) for kk in T.results(m) if kk.split("{")[0] == q}):
                    pts = series_xy(T, comp, next((vk for vk in T.vector(T.member_entities(comp)[0]) if vk.split("{")[0] == comp["quantity"].split(";")[0]), ""), key)
                    if len([p for p in pts if p[0] in linked]) >= 2:
                        pts = [p for p in pts if p[0] in linked]                     # the members the claim's links reach
                    if len(pts) >= 2:
                        pts.sort(key=lambda p: (p[1] is None, p[1])); m0, x0, y0 = pts[0]
                        parts.append(f"{comp['label_as_printed']}: {L.LABELS.get(key, key)} {g(y0, 3)} at {T.label(m0)} ({L.LABELS.get(comp['quantity'].split(';')[0], comp['quantity'])} {g(x0) if x0 is not None else 'cycled'}) → " +
                                     ", ".join(f"{g(y1, 3)} at {T.label(m1)} ({g(x1) if x1 is not None else 'cycled'}): {g(100 * (y1 / y0 - 1), 2)} %" for m1, x1, y1 in pts[1:]))
        out.append(f"{f['fact_id']} ({f['cause']} → {f['effect']}): " + ("; ".join(parts) if parts else "no quantified effect: its links reach no comparison with that result"))
    return answered(" · ".join(out), "claims by cause token; scope_comparisons() from their links; series_xy over the comparison's varied setting and the claim's effect quantity; the change from first to last member")


def q24():
    """Resistivity drop when a metallic phase appears, per paper."""
    out = []
    for k, T in TREES.items():
        parts = []
        done = set()
        for c in sorted(T.comps, key=lambda c: len(T.member_entities(c))):          # the smallest comparison holding a marked specimen: its row
            marked, others = contrast(T, c, "resistivity")
            marked = [t for t in marked if t[0] not in done]
            if marked and others:
                done |= {t[0] for t in marked}
                near = min(others, key=lambda t: abs((t[3] or 0) - (marked[0][3] or 0)))
                parts.append(f"{c['label_as_printed']}: {', '.join(f'{T.label(m)} {fmt(f)}' for m, _, f, _ in marked)} (a metallic phase detected) vs "
                             + ", ".join(f"{T.label(m)} {fmt(f)}" for m, _, f, _ in others) + f": {g(near[1] / marked[0][1], 2)}× lower than its neighbour {T.label(near[0])}")
        marked_all = {m for c in T.comps for m, *_ in contrast(T, c, "resistivity")[0]}
        text_ = [f"{quals(f)['stat']} {fmt(f)} over {len(f['links'].split(';'))} films ({f['fact_id']})" for f in T.rows if f["quantity"] == "resistivity" and quals(f).get("stat") and set(f["links"].split(";")) & marked_all]
        out.append(f"{k}: " + ("; ".join(parts) if parts else "no comparison with a member naming a metallic phase") + (f" · the text: {'; '.join(text_)}" if text_ else ""))
    return answered(" · ".join(out), "contrast() within each stated comparison: the specimens whose observations (pieces included) name a metallic phase against the others, on resistivity; the paper's own resistivity statements naming a metal beside it")


def q25():
    """The reproducibility figure of each paper and what it is a reproducibility of."""
    out, kinds = [], []
    for k, T in TREES.items():
        parts = []
        for c in [c for c in T.comps if c["kind"] == "replicate"]:                 # a replicate comparison: its standard deviations against the members' means
            ms = T.member_entities(c)
            for f in T.own(c["fact_id"]):
                if quals(f).get("stat") == "sd" and f["value"]:
                    for key in [spread_key(f)]:
                        vals = [val(T.results(m)[key][0]) for m in ms if key in T.results(m)]
                        if len(vals) == len(ms):
                            mean = abs(sum(vals) / len(vals))
                            parts.append(f"{L.LABELS.get(key, key)}: sd {fmt(f)} = {g(100 * val(f) / mean, 2)} % of the mean over {len(ms)} ({c['statement'].split(':')[-1].strip()})")
            if parts:
                kinds.append(f"{k}: between samples ({c['label_as_printed']})")
        for f in [f for f in T.rows if quals(f).get("between") == "position" and f["value"]]:   # a spread over positions: within one film
            e = T.ent_of(f["fact_id"]); parts.append(f"thickness nonuniformity {fmt(f)} within one film ({T.label(e)}: {f['statement'][:60]}…)"); kinds.append(f"{k}: within one film")
        if not parts:                                                               # the ± between the pieces of one run (the uncertainty column)
            for e in T.entities():
                if T.byid[T.byid[e]["parent"]]["type"] != "activity":
                    continue
                for key, fs in T.results(e).items():
                    f = fs[0]
                    if f["uncertainty"] and f["uncertainty_kind"] in ("pieces", "runs"):
                        parts.append(f"{L.LABELS.get(key, key)} {fmt(f)} ± {f['uncertainty']} {f['unit']} = {g(100 * num(f['uncertainty']) / val(f), 2) if val(f) else '?'} % ({T.label(e)}: {f['statement'].split('(')[-1].rstrip(')')})")
            if parts:
                kinds.append(f"{k}: between the pieces of one run")
        out.append(f"{k}: " + ("; ".join(parts) if parts else "no reproducibility figure"))
    bridged = [u for u in USER if u["type"] == "bridge" and u["quantity"] in ("thickness_nonuniformity", "film_thickness", "mass_gain")]
    out.append("not merged: " + "; ".join(kinds) + " are three definitions" + ("" if bridged else " and no bridge in user.facts.csv relates them"))
    return answered(" · ".join(out), "the replicate comparison's standard deviations against the members' means (yim20), a nonuniformity fact (mat22), the ± of one run's pair values from the uncertainty column (gre23); merged only through a bridge, of which there is none")


def q26():
    """All lumped sticking coefficients of TMA with temperature and source."""
    from forest import Forest
    F = Forest()
    ls = [l for l in F.leaves({"lumped_sticking_coefficient"}) if l["quals"].get("species") == "TMA"]
    def src(l):
        return "cited work " + l["scope"].split(":")[-1] if l["cited"] else ("this work, model input" if kind(l["row"]) == "model" else "this work")
    def T_(l):
        t = l["ctx"].get("deposition_temperature"); return "T ambiguous" if t == "ambiguous" else (f"{t['value'] or t['value_min'] + '–' + t['value_max']} °C" if t else "no T in scope")
    text = "; ".join(f"{l['key']} {l['row']['censor']}{l['row']['value'] or l['row']['value_min'] + '–' + l['row']['value_max']} ({src(l)}, {T_(l)}, {l['row']['data_kind']})" for l in ls)
    vals = [l["value"] for l in ls]
    return answered(text + f" · span {g(max(vals) / min(vals))}×", "the forest's leaves of the quantity, their scope and context")


# ------------------------------------------------------------------ helpers for answers
def answered(text, how):
    return dict(status="answered", answer=text, how=how)


def wrong(text, how):
    return dict(status="wrong", answer=text, how=how)


def unanswerable(text, how):
    return dict(status="unanswerable", answer=text, how=how)


QUESTIONS = [("Q1", "yim20", q1), ("Q2", "yim20", q2), ("Q3", "yim20", q3), ("Q4", "yim20", q4), ("Q5", "yim20", q5), ("Q6", "yim20", q6), ("Q7", "yim20", q7),
             ("Q8", "yim20", q8), ("Q9", "mat22", q9), ("Q10", "mat22", q10), ("Q11", "mat22", q11), ("Q12", "mat22", q12), ("Q13", "mat22", q13), ("Q14", "mat22", q14),
             ("Q15", "gre23", q15), ("Q16", "gre23", q16), ("Q17", "gre23", q17), ("Q18", "gre23", q18), ("Q19", "across", q19), ("Q20", "across", q20),
             ("Q21", "across", q21), ("Q22", "across", q22), ("Q23", "across", q23), ("Q24", "across", q24), ("Q25", "across", q25), ("Q26", "across", q26)]

if __name__ == "__main__":
    prev = {r["id"]: r for r in csv.DictReader((HERE / "questions.csv").open(encoding="utf-8"))} if (HERE / "questions.csv").exists() else {}
    rows, counts = [], collections.Counter()
    for qid, qkind, fn in QUESTIONS:
        try:
            a = fn()
        except Exception as e:                                                  # a failing computation is an unanswerable question, with the error
            a = unanswerable("", f"computation failed: {type(e).__name__}: {e}")
        counts[a["status"]] += 1
        changed = prev.get(qid, {}).get("changed", "")
        if prev.get(qid) and prev[qid]["status"] != a["status"]:
            changed = (changed + "; " if changed else "") + f"{prev[qid]['status']} -> {a['status']}"
        rows.append(dict(id=qid, question=fn.__doc__.strip(), kind=qkind, status=a["status"], answer=a["answer"], how=a["how"], changed=changed))
        print(f"{qid:4s} {a['status']:12s} {a['answer'][:110]}{' | ' + a['how'][:90] if a['how'] else ''}")
    with (HERE / "questions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "question", "kind", "status", "answer", "how", "changed"]); w.writeheader(); w.writerows(rows)
    print("summary:", dict(counts))
