#!/usr/bin/env python3
"""The 26 questions, now a regression test of the query layer: each is a short composition of the five operations of query.py
(find, detail, compare, claims, source) with at most simple arithmetic on the values they return; no question has a helper of its
own. Writes questions.csv (id, question, kind, status, answer, how, changed) and prints a summary.

    python3 psed_v2/pilot/questions.py

A question is answered when the composition reaches the hand answer's content, unanswerable when the layer or the data lacks
something; the `how` column names the operations used, or the problems.csv row that records what is lacking.
"""
import csv, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from query import find, detail, compare, claims, source, g  # noqa: E402,F401

KW = {"read from figure": "read from figure", "computed by the authors": "computed by the authors", "computed here": "computed here", "assumed": "assumed", "model": "model", "cited": "cited"}


def vt(rec):
    """A value record as text: the value, its non-default definition and its kind word (generic, used by every answer)."""
    extra = [x for x in ((rec.get("definition") if rec.get("kind") != "computed here" else ""), KW.get(rec.get("kind"), "")) if x]
    return rec["text"] + (f" ({'; '.join(extra)})" if extra else "")


def group(paper, label):
    """The authors' comparison whose label starts with the given words, from find()."""
    return next(x for x in find(paper=paper)["groups"] if x["label"].startswith(label))


def res(d, quantity, **need):
    """The result lines of a detail() whose key names the quantity and qualifiers."""
    return [r for r in d["results"] if r["key"].split("{")[0] == quantity and all(f"{k}={v}" in r["key"] for k, v in need.items())]


def cond(d, quantity):
    """The condition line of a detail() for a quantity."""
    return next((c for c in d["recipe"] if c["key"].split("{")[0] == quantity), None)


def answered(text, how):
    return dict(status="answered", answer=text, how=how)


def unanswerable(text, how):
    return dict(status="unanswerable", answer=text, how=how)


# ------------------------------------------------------------------ within yim20
def q1():
    """PD50 against TMA pulse time over Series E, with every other setting that differs listed."""
    E = detail(group("yim20", "Series E")["id"])
    c = compare(E["members"], result="penetration_depth")
    pts = sorted((p["x"], p["y"], p["name"]) for p in c["plot"]["points"])
    fit = next(f for f in E["fits"] if f["key"].startswith("penetration_depth{level=50%"))
    diff = [d for d in c["differing"] if d["name"] != c["plot"]["x_name"]]
    cor = "; ".join(f"with {x['condition']} corrected to {x['to']} ({', '.join(f'{ch['frm']} × {ch['factor']} from {ch['by']} → {ch['value']} µm' for ch in x['changes'])}): "
                    f"exponent {x['exponent']} (residual {x['residual']})" for x in fit["corrected"])
    return answered("; ".join(f"{n}: pulse {g(x)} s, PD50 {g(y)} µm" for x, y, n in pts) + f" · fit PD50 ∝ pulse^{fit['exponent']} (residual {fit['residual']}) · also differs: " +
                    "; ".join(f"{d['name']} " + ", ".join(d["values"].values()) for d in diff) + (f" · {cor}" if cor else ""),
                    "find (Series E) → detail(E).fits with the confounder corrected from the comparison that varies only it → compare(E members).plot and .differing")


def q2():
    """Over Series D, PD50 against the effective channel height H − 2·S_IIb."""
    D = detail(group("yim20", "Series D")["id"])
    rows = []
    for m in D["members"]:
        d = detail(m)
        h = res(d, "feature_width", stage="final"); pd = res(d, "penetration_depth", level="50%")
        if h and pd:
            rows.append((d["name"], h[0]["record"]["value"], pd[0]["record"]["value"]))
    if len(rows) < 2:
        return unanswerable("", "detail() of the Series D members lacks H_eff or PD50")
    ref = max(rows, key=lambda r: r[1])
    return answered("; ".join(f"{n}: H_eff {g(h)} nm (computed), PD50 {g(p)} µm, √H_eff from {ref[0]} predicts {g(ref[2] * math.sqrt(h / ref[1]))} µm" for n, h, p in rows),
                    "find (Series D) → detail(members).results: effective channel height (computed) and PD50; the square-root scaling as arithmetic")


def q3():
    """For sample 11, every penetration depth value by method."""
    s11 = next(r for r in find(paper="yim20", result="penetration_depth")["rows"].values() if r["name"] == "sample 11")
    pds = [r["record"] for r in res(detail(s11["id"]), "penetration_depth")]
    if len(pds) < 2:
        return unanswerable("", "detail(sample 11) lists fewer than two penetration depths")
    a, b = pds[0], pds[1]
    return answered("; ".join(f"{vt(p)} by {p['method']} ({p['fact']})" for p in pds) + f" · ratio {g(a['value'] / b['value'], 3)}: two definitions (the 50 % level of the reflectometer profile, the EDS front), not a contradiction",
                    "find(yim20, penetration depth) → detail(sample 11).results: one line per definition, each with its method")


def q4():
    """Over Series F, the ratio GPC_I / GPC_IIb against purge time."""
    F = detail(group("yim20", "Series F")["id"])
    c = compare(F["members"], result="growth_per_cycle")
    out_ = next(r for r in c["results"] if "outside" in r["key"]); in_ = next(r for r in c["results"] if "plateau" in r["key"])
    purge = next(d for d in c["differing"] if d["name"].startswith("purge"))
    rows = sorted((float(purge["values"][i].split()[0]), purge["values"][i], out_["cells"][i]["value"] / in_["cells"][i]["value"]) for i in F["members"])
    return answered("; ".join(f"purge {p}: GPC outside / in the channel = {g(r, 3)}" for _, p, r in rows),
                    "find (Series F) → compare(members, growth per cycle): the two definitions per member; the ratio as arithmetic")


def q5():
    """Which stated comparisons in yim20 have an effect smaller than the reproducibility sd, per result quantity."""
    out = []
    for gr in find(paper="yim20")["groups"]:
        if not gr["label"].startswith("Series"):
            continue
        d = detail(gr["id"])
        out.append(f"{d['label']}: " + "; ".join(f"{e['name']} range {e['effect']} {e['unit']}: {e['sentence']}" for e in d["effects"]))
    return answered(" · ".join(out), "find(yim20).groups → detail(each series).effects: the range against the scatter of the same kind at the base condition")


def q6():
    """TMA exposure per pulse and per run, in Torr·s."""
    rows = {i: r for i, r in find(paper="yim20", result="exposure")["rows"].items() if r["role"] == "specimen"}
    pick = lambda r, key: dict(r, result=[x for x in r["result"] if x["key"] == key])
    a = {i: pick(r, "exposure") for i, r in rows.items() if any(x["key"] == "exposure" for x in r["result"])}
    b = {i: pick(r, "exposure{over=run}") for i, r in rows.items() if any(x["key"] == "exposure{over=run}" for x in r["result"])}
    if not a:
        return unanswerable("", "no yim20 experiment has an exposure")
    per = sorted({r["result"][0]["record"]["text"] for r in a.values()}); run = sorted({r["result"][0]["record"]["text"] for r in b.values()})
    ass = sorted({x for r in a.values() for x in r["result"][0]["record"].get("assumed", [])})
    return answered(f"per pulse {', '.join(per)} over {len(a)} samples; per run {', '.join(run)} · computed from an assumed fact: {', '.join(ass)} (the model input 65 Pa stands in for the TMA pressure)",
                    "find(yim20, exposure) and find(yim20, exposure per run): every sample's computed value, the assumed input named")


def q7():
    """c_TMA of this work against Ylilammi 2018 in Table 2, with the film density each assumed."""
    rep = detail(group("yim20", "sample 2, 4, 8")["id"])
    own = next(v for v in rep["values"] if "sticking" in v["statement"] or v["fact"].startswith("yim20:tab2"))
    yli = next(r for r in find(paper="yim20", result="initial_sticking_coefficient")["rows"].values() if r["name"].startswith("Ylilammi"))
    y_c = next(x["record"] for x in yli["result"] if "TMA" in x["name"])
    y_d = next(x["record"] for x in detail(yli["id"])["results"] if x["key"].startswith("film_density"))
    dens = next(c["record"] for c in detail(group("yim20", "model simulations")["members"][0])["recipe"] if c["key"].startswith("film_density"))
    return answered(f"c_TMA {vt(own)} (this work, replicate set) against {vt(y_c)} ({yli['name']}): ratio {g(y_c['value'] / own['value'], 3)}; "
                    f"density {vt(dens)} (this work's model input) against {vt(y_d)}: ratio {g(y_d['value'] / dens['value'], 3)}",
                    "detail(replicate set).values → find(yim20, sticking coefficient) cited rows → detail(Ylilammi) → detail(model run).recipe for the density")


def q8():
    """The effective channel height of the 500 nm design from the fabrication tolerances."""
    s8 = next(r for r in find(paper="yim20")["rows"].values() if r["name"] == "sample 8")
    piece = detail(detail(s8["id"])["what"]["input_ids"][0]); parent = detail(piece["what"]["parent"])
    h = cond(piece, "feature_width")["record"]
    bend = next(r["record"] for r in piece["results"] if "bending" in r["name"])
    step = next(r["record"] for r in parent["results"] if "nanostep" in r["name"])
    return answered(f"design {h['text']} ± {h['uncertainty']['value']} nm ({h['uncertainty']['stat']} between {h['uncertainty']['kind']}), membrane bending {bend['text']}, entrance nanostep {step['text']} → "
                    f"effective height ≈ {g(h['value'] - bend['value'] - step['high'])}–{g(h['value'] - bend['value'] - step['low'])} nm; all measured on the chips before deposition",
                    "find(yim20) → detail(sample 8).what.input_ids → detail(the 500 nm chip): height with tolerance, bending → detail(chip type): nanostep")


# ------------------------------------------------------------------ within mat22
def q9():
    """GPC at ratio 0.20 implied by the cycle numbers chosen to give 10 nm, per temperature, against the Fig. 7b colour-read GPC."""
    rows = find(paper="mat22", result="growth_per_cycle", conditions={"plasma_gas_ratio": (0.2, 0.2)})["rows"]
    out = []
    for r in rows.values():
        d = detail(r["id"]); tg = [x for x in r["result"] if x["key"] == "growth_per_cycle{kind=target;over=run}"]
        if not tg:
            continue
        imp = tg[0]["record"]; read = [x for x in res(d, "growth_per_cycle") if "kind=target" not in x["key"]]
        t = cond(d, "deposition_temperature")["record"]["value"]
        out.append((t, f"{g(t)} °C: {cond(d, 'cycle_number')['record']['text']} cycles → {g(imp['value'] * 10, 2)} Å implied" + (f" vs {vt(read[0]['record'])}" if read else "")))
    return answered("; ".join(x for _, x in sorted(out, reverse=True)), "find(mat22, GPC implied by the thickness target, ratio 0.20) → detail(each).recipe and results") if out \
        else unanswerable("", "no ratio-0.20 film with a thickness target")


def q10():
    """Thickness against cycles at 150 °C, ratio 0.80, from every source."""
    rows = find(paper="mat22", material="mos2", result="film_thickness", conditions={"deposition_temperature": (150, 150), "plasma_gas_ratio": (0.8, 0.8)})["rows"]
    c = compare(list(rows), result="film_thickness")
    p = c["plot"]
    pts = "; ".join(f"{x['name']}: {g(x['y'])} nm at {g(x['x'])} cycles ({x['kind']}, {x['mode'].replace('_', ' ')})" for x in sorted(p["points"], key=lambda x: x["x"]))
    cur = "; ".join(f"{x['name']}: curve of {len(x['points'])} points to {g(x['points'][-1][1])} nm after {g(x['points'][-1][0])} cycles ({x['mode'].replace('_', ' ')})" for x in p["curves"])
    gpc = [y / x * 10 for x, y in [(q["x"], q["y"]) for q in p["points"]] + [(cu["points"][-1][0], cu["points"][-1][1]) for cu in p["curves"]] if x]
    return answered(f"{pts}; {cur} · thickness/cycles {g(min(gpc), 2)}–{g(max(gpc), 2)} Å · they differ in: " + ", ".join(d["name"] for d in c["differing"]),
                    "find(mat22, MoS2, thickness, 150 °C, 0.80) → compare(rows, thickness).plot: points and the in situ curve on one axis, x = cycles")


def q11():
    """Mo atoms per cycle from RBS against GPC from SE at 150 °C, ratio 0.80, with the density."""
    rows = find(paper="mat22", material="mos2", result="growth_per_cycle", conditions={"deposition_temperature": (150, 150), "plasma_gas_ratio": (0.8, 0.8)})["rows"]
    c = compare(list(rows), result="growth_per_cycle")
    lines = [(r["key"], i, cell) for r in c["results"] for i, cell in r["cells"].items() if cell]
    rbs = next(x for x in lines if x[2]["kind"] == "computed here"); se = next(x for x in lines if x[2]["kind"] != "computed here")
    name = {it["id"]: it["name"] for it in c["items"]}
    return answered(f"{name[rbs[1]]}: {vt(rbs[2])} from Mo atoms per cycle at its own density (assumed: {', '.join(rbs[2]['assumed'])}); "
                    f"{name[se[1]]}: {vt(se[2])}; ratio {g(rbs[2]['value'] / (se[2]['value'] / 10), 2)} · {next(r['note'] for r in c['results'] if r['note'])} · the films differ in: " +
                    "; ".join(f"{d['name']} " + " vs ".join(str(v) for v in d["values"].values()) for d in c["differing"] if d["name"] in ("substrate", "cycles")),
                    "find(mat22, GPC, 150 °C, 0.80) → compare(rows, GPC): the computed and the measured value, the definition note and the differing conditions")


def q12():
    """The full composition of the 150 °C, 0.80 film including H, and its density relative to bulk."""
    rows = find(paper="mat22", result="h_per_metal", conditions={"deposition_temperature": (150, 150), "plasma_gas_ratio": (0.8, 0.8)})["rows"]
    if not rows:
        return unanswerable("", "no 150 °C, 0.80 film with H per metal")
    d = detail(next(iter(rows)))
    smo = res(d, "composition", element="S")[0]["record"]; hm = res(d, "h_per_metal")[0]["record"]; rr = res(d, "density_relative_to_bulk")[0]["record"]
    return answered(f"{d['name']}: MoS{smo['text']}H{g(hm['value'], 2)} (H per Mo computed from at.%), density {vt(rr)} of bulk", "find(mat22, H per metal, 150 °C, 0.80) → detail(film).results")


def q13():
    """The H2 fraction of the total plasma feed (Ar included) for each ratio."""
    per = {}
    for r in find(paper="mat22", material="mos2", result="plasma_gas_ratio")["rows"].values():
        share = [x for x in r["result"] if x["key"] == "plasma_gas_ratio{gas=h2;relative_to=all_gases}"]
        if not share:
            continue
        ratio = cond(detail(r["id"]), "plasma_gas_ratio")["record"]["text"]
        per.setdefault(ratio, set()).add(share[0]["record"]["text"])
    return answered("; ".join(f"ratio {k}: {', '.join(sorted(v))}" for k, v in sorted(per.items(), key=lambda x: float(x[0]))),
                    "find(mat22, H2 share of the plasma feed): every film's computed share, listed by its ratio")


def q14():
    """Sheet resistance of the PET film."""
    rows = find(paper="mat22", result="sheet_resistance")["rows"]
    return answered("; ".join(f"{r['name']}: {vt(r['result'][0]['record'])}" for r in rows.values()), "find(mat22, sheet resistance): every film with a resistivity and a measured thickness") \
        if rows else unanswerable("", "no film with a sheet resistance")


# ------------------------------------------------------------------ within gre23
def q15():
    """For 120 vs 120/160 °C, the ratio of every quantity measured on both."""
    gr = group("gre23", "120, 160"); rows = find(paper="gre23")["rows"]
    a = next(i for i in gr["members"] if rows[i]["name"].startswith("120 °C")); b = next(i for i in gr["members"] if rows[i]["name"].startswith("120/160"))
    c = compare([a, b])
    return answered("; ".join(f"{r['name']} {r['cells'][a]['text']} vs {r['cells'][b]['text']}: {r['relation']['how']} {r['relation']['value']}{(' ' + r['relation']['unit']) if r['relation']['unit'] else ''}"
                              for r in c["results"] if r["relation"]),
                    "find (the schedules) → compare(120 °C pair, 120/160 °C pair): every shared result, a ratio on ratio-scale quantities, a difference otherwise")


def q16():
    """Crystalline ZnO fraction from XRD weight % against gravimetric ZnO %."""
    out = []
    for i in group("gre23", "120, 160")["members"]:
        d = detail(i)
        x = res(d, "composition", species="zno"); m = res(d, "coating_mass_fraction")
        if x and m:
            out.append(f"{d['name']}: XRD zincite {vt(x[0]['record'])} against the coating's mass fraction {m[0]['record']['text']}")
    return answered(" · ".join(out), "find (the schedules) → detail(each pair).results: the XRD value and the computed mass fraction, one reading per basis since the paper states neither")


def q17():
    """Does the mass balance close: Δn_s per cycle × 20 against the ZnO mass gained by the two NPCs."""
    out = []
    for i in group("gre23", "120, 160")["members"]:
        d = detail(i)
        a = res(d, "moles_deposited"); b = res(d, "moles_from_mass_gain")
        if a and b:
            out.append(f"{d['name']}: solid deposited per cycle × cycles {a[0]['record']['text']} against {b[0]['record']['text']} from the mass gain (assumed: {', '.join(b[0]['record']['assumed'])})")
    return answered(" · ".join(out), "find (the schedules) → detail(each pair).results: the two computed amounts, the mass-gain one in both readings, the assumed inputs named")


def q18():
    """ZnO volume fraction in the 120 °C NPC from coating thickness and particle size."""
    d = detail(next(i for i in group("gre23", "120, 160")["members"] if detail(i)["name"].startswith("120 °C")))
    r = res(d, "shell_volume_fraction")
    return answered(f"{d['name']}: {r[0]['record']['text']} (computed) from " + ", ".join(f"{x['name']} {x['value']} {x['unit']} ({x['fact']})" for x in r[0]["record"]["inputs"]),
                    "find (the schedules) → detail(120 °C pair).results: the computed coating volume fraction with its inputs") if r else unanswerable("", "no coating volume fraction")


# ------------------------------------------------------------------ across the papers
def q19():
    """Knudsen number of each paper's structure under its own conditions."""
    yim = [r for c in claims(paper="yim20", variable="knudsen_number") for r in c["rests_on"] if "Knudsen" in r["statement"]]
    yim += [r for c in claims(paper="yim20") if c["id"] == "yim20:s19.p3#7" for r in c["rests_on"] if "Knudsen" in r["statement"]]
    gre = find(paper="gre23", result="knudsen_number")["rows"]
    mat = {cond(detail(r["id"]), "structure")["record"]["text"] for r in find(paper="mat22")["rows"].values() if r["role"] == "specimen"}
    ass = sorted({a for r in gre.values() for a in r["result"][0]["record"].get("assumed", [])})
    return answered(f"yim20: {'; '.join(dict.fromkeys(vt(r) + ' (' + r['statement'][:40] + ')' for r in yim))} · mat22: {', '.join(sorted(mat))} films, no Knudsen number applies · gre23: " +
                    "; ".join(f"{r['name']} {vt(r['result'][0]['record'])}" for r in gre.values()) + f" (assumed: {', '.join(ass)})",
                    "claims(yim20).rests_on: the stated Knudsen numbers · detail(mat22 films).recipe structure · find(gre23, Knudsen number): computed per run")


def q20():
    """Exposure per dose, yim20 against gre23, and what AR² scaling from yim20's x̃50 would predict for gre23's AR."""
    rep = detail(group("yim20", "sample 2, 4, 8")["id"])
    ex = find(paper="yim20", result="exposure")["rows"][rep["members"][0]]["result"][0]["record"]
    x50 = [res(detail(m), "coated_aspect_ratio", basis="AR")[0]["record"]["value"] for m in rep["members"]]
    pair = detail(group("gre23", "120, 160")["members"][0])
    eg = cond(pair, "exposure")["record"]; ar = res(detail(pair["what"]["input_ids"][0]), "aspect_ratio")[0]["record"]
    pred = ex["value"] * (ar["value"] / (sum(x50) / len(x50))) ** 2
    return answered(f"yim20 exposure per dose {vt(ex)} (assumed: {', '.join(ex.get('assumed', []))}) against gre23 {vt(eg)} (chosen over {', '.join(a['text'] for a in eg['alternatives'])}); "
                    f"yim20 reaches x̃50 ≈ {g(sum(x50) / len(x50), 3)} on its replicate set, gre23's aspect ratio {vt(ar)}: AR² scaling predicts {g(pred, 2)} Torr s, gre23 used {g(eg['value'] / pred, 2)}× that",
                    "detail(replicate set) → find(yim20, exposure) and detail(members) x̃50 · detail(gre23 pair).recipe exposure → detail(its input).results aspect ratio; the square law as arithmetic")


def q21():
    """Metal atoms per nm² per cycle in all three papers."""
    out = []
    for k in ("yim20", "mat22", "gre23"):
        rows = {i: r for i, r in find(paper=k, result="atoms_per_cycle")["rows"].items() if r["role"] != "cited"}
        if rows:
            out.append(f"{k}: " + "; ".join(f"{r['name']} {vt(r['result'][0]['record'])}" + (f" (assumed: {', '.join(r['result'][0]['record']['assumed'])})" if r["result"][0]["record"].get("assumed") else "")
                                            for r in rows.values()))
        else:
            sims = [c["record"] for c in detail(group(k, "model simulations")["members"][0])["recipe"] if c["key"] == "saturation_density"]
            out.append(f"{k}: " + "; ".join(f"{vt(r)} (the model's saturation density)" for r in sims))
    return answered(" · ".join(out), "find(each paper, metal atoms per cycle): measured or computed, assumed inputs named · detail(yim20 model run).recipe where no experiment has a value")


def q22():
    """Deposited thickness per hour of reactor time in all three."""
    out = []
    for k in ("yim20", "mat22", "gre23"):
        vals = [(r["name"], r["result"][0]["record"]) for r in find(paper=k, result="deposition_rate")["rows"].values() if r["role"] == "specimen"]
        if vals:
            v = [x["value"] for _, x in vals]
            out.append(f"{k}: {g(min(v), 2)}–{g(max(v), 2)} nm/h over {len(vals)} experiments: " + "; ".join(f"{n} {g(x['value'], 2)}" for n, x in vals))
    return answered(" · ".join(out), "find(each paper, thickness per hour): every experiment's computed value and the range, no representative")


def q23():
    """Every claim that puts water desorption or surface OH as a cause, with the quantified effect behind each."""
    out = []
    for tok in ("mechanism:surface_OH", "mechanism:residual_H2O", "mechanism:desorption", "mechanism:water_readsorption"):
        for c in claims(variable=tok):
            effs = [f"{e['name']} range {e['effect']} {e['unit']} ({detail(cid)['label']}; {e['sentence']})" for cid in c["comparisons"] for e in detail(cid)["effects"]
                    if any(n in e["name"] for n in c["effect"])]
            out.append(f"{c['id']} ({', '.join(c['cause'])} → {', '.join(c['effect'])}): " + ("; ".join(effs) if effs else "no comparison it reaches quantifies that effect"))
    return answered(" · ".join(dict.fromkeys(out)), "claims(variable = each water or OH mechanism) → detail(each comparison it reaches).effects on its effect quantity")


def q24():
    """Resistivity drop when a metallic phase appears, per paper."""
    out = []
    for k in ("yim20", "mat22", "gre23"):
        hits = []
        for gr in find(paper=k)["groups"]:
            if gr["kind"] == "cited":
                continue
            ds = [detail(m) for m in gr["all_members"]]
            metal = [d for d in ds if any(r["key"].startswith("phase") and r["record"]["text"] == "detected" and ("species=mo" in r["key"] or "species=zn" in r["key"]) for r in d["results"])]
            other = [d for d in ds if d not in metal and res(d, "resistivity")]
            if metal and other and all(res(d, "resistivity") for d in metal):
                hits.append(f"{gr['label']}: " + ", ".join(f"{d['name']} {vt(res(d, 'resistivity')[0]['record'])}" for d in metal) + " (metal phase detected) against " +
                            ", ".join(f"{d['name']} {vt(res(d, 'resistivity')[0]['record'])}" for d in other))
        mins = [v for gr in find(paper=k)["groups"] if gr["kind"] != "cited" for v in detail(gr["id"])["values"] if v["stat"] == "minimum" and "resistivit" in v["statement"]]
        out.append(f"{k}: " + (" · ".join(hits[:2]) if hits else "no comparison with a metallic phase") + (f" · the text: minimum {', '.join(dict.fromkeys(vt(m) for m in mins))}" if mins else ""))
    return answered(" · ".join(out), "find(each paper).groups → detail(members).results: the measured phase and the resistivity side by side · detail(group).values: the stated minimum")


def q25():
    """The reproducibility figure of each paper and what it is a reproducibility of."""
    out = []
    for k in ("yim20", "mat22", "gre23"):
        parts = []
        for gr in find(paper=k)["groups"]:
            if gr["kind"] == "replicate":
                parts += [f"{v['statement']}" for v in detail(gr["id"])["values"] if v["stat"] == "sd"]
        for r in find(paper=k)["rows"].values():
            if r["role"] != "specimen":
                continue
            for x in detail(r["id"])["results"]:
                u = x["record"].get("uncertainty")
                if u and u.get("kind") in ("pieces", "runs", "position") and x["record"]["kind"] != "computed here":
                    parts.append(f"{r['name']} {x['name']} {x['record']['text']} ± {u['value']}{' %' if u.get('stat') == 'relative_sd' else (' ' + x['record']['unit'])} (between {u['kind']}, n {u.get('n') or 'not stated'})")
        out.append(f"{k}: " + ("; ".join(dict.fromkeys(parts)) if parts else "no reproducibility figure"))
    return answered(" · ".join(out) + " · three definitions (between runs, positions in one film, pieces of one run); not merged",
                    "find(each paper) → detail(replicate set).values and detail(experiments).results: the uncertainty with what varies between the repeats")


def q26():
    """All lumped sticking coefficients of TMA with temperature and source."""
    out = []
    for r in find(result="initial_sticking_coefficient")["rows"].values():
        t = cond(detail(r["id"]), "deposition_temperature")
        for x in r["result"]:
            if "TMA" in x["name"]:
                out.append(f"{r['name']} {vt(x['record'])}" + (f" at {t['record']['text']}" if t else ""))
    rep = detail(group("yim20", "sample 2, 4, 8")["id"])
    out += [f"this work {vt(v)} (replicate set)" for v in rep["values"] if not v["stat"]]
    return answered("; ".join(dict.fromkeys(out)), "find(sticking coefficient): the cited rows and the model runs' input → detail(each).recipe temperature · detail(replicate set).values")


QUESTIONS = [("Q1", "yim20", q1), ("Q2", "yim20", q2), ("Q3", "yim20", q3), ("Q4", "yim20", q4), ("Q5", "yim20", q5), ("Q6", "yim20", q6), ("Q7", "yim20", q7),
             ("Q8", "yim20", q8), ("Q9", "mat22", q9), ("Q10", "mat22", q10), ("Q11", "mat22", q11), ("Q12", "mat22", q12), ("Q13", "mat22", q13), ("Q14", "mat22", q14),
             ("Q15", "gre23", q15), ("Q16", "gre23", q16), ("Q17", "gre23", q17), ("Q18", "gre23", q18), ("Q19", "across", q19), ("Q20", "across", q20),
             ("Q21", "across", q21), ("Q22", "across", q22), ("Q23", "across", q23), ("Q24", "across", q24), ("Q25", "across", q25), ("Q26", "across", q26)]

if __name__ == "__main__":
    import collections
    prev = {r["id"]: r for r in csv.DictReader((HERE / "questions.csv").open(encoding="utf-8"))} if (HERE / "questions.csv").exists() else {}
    rows, counts = [], collections.Counter()
    for qid, qkind, fn in QUESTIONS:
        try:
            a = fn()
        except Exception as e:                                                  # a failing composition is an unanswerable question, with the error
            a = unanswerable("", f"composition failed: {type(e).__name__}: {e}")
        counts[a["status"]] += 1
        changed = prev.get(qid, {}).get("changed", "")
        if prev.get(qid) and prev[qid]["status"] != a["status"]:
            changed = (changed + "; " if changed else "") + f"{prev[qid]['status']} -> {a['status']}"
        rows.append(dict(id=qid, question=fn.__doc__.strip(), kind=qkind, status=a["status"], answer=a["answer"], how=a["how"], changed=changed))
        print(f"{qid:4s} {a['status']:12s} {a['answer'][:110]}{' | ' + a['how'][:90] if a['how'] else ''}")
    with (HERE / "questions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "question", "kind", "status", "answer", "how", "changed"]); w.writeheader(); w.writerows(rows)
    print("summary:", dict(counts))
