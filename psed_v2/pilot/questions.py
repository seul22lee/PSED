#!/usr/bin/env python3
"""The 26 questions that test the schema: each a function computing its answer from the facts (the three papers' facts.csv and
user.facts.csv), no numbers typed in. Writes questions.csv (id, question, kind, status, answer, how, changed) and prints a summary.

    python3 psed_v2/pilot/questions.py

A question is answered when the computation reaches the hand answer's content, wrong when it reaches a different one, unanswerable
when a fact is missing, a fact sits in the wrong place, no join rule, derived quantity, operation or assumed fact exists; the `how`
column says which. The library below reads the trees only (condition vectors, results, comparisons, members); every rule the
questions needed beyond that was added class by class (see HANDOFF, Comparison layer).
"""
import collections, csv, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
from elements import PAPERS  # noqa: E402
from facts import FIELDS, num  # noqa: E402

KEY = {k: pid for pid, k in PAPERS.items()}
NODE = ("activity", "entity", "comparison", "paper", "cited")
RESULT_TYPES = ("observation", "derived", "model")


class Tree:
    """One paper's facts as a tree: condition vectors, results, comparisons."""

    def __init__(self, key):
        self.key = key
        self.rows = list(csv.DictReader((HERE / f"{KEY[key]}.facts.csv").open(encoding="utf-8")))
        self.byid = {r["fact_id"]: r for r in self.rows}
        self.kids = collections.defaultdict(list)
        for r in self.rows:
            if r["parent"]:
                self.kids[r["parent"]].append(r)
        self.comps = [r for r in self.rows if r["type"] == "comparison"]

    def chain(self, i):
        out = []
        while i in self.byid:
            out.append(i); i = self.byid[i]["parent"]
        return out

    def own(self, i):                       # a node's own facts: its subtree, not crossing another node
        out = []
        for c in self.kids.get(i, []):
            if c["type"] in NODE:
                continue
            if "#" in c["fact_id"]:
                out.append(c)
            out += self.own(c["fact_id"])
        return out

    def below(self, i):                     # an entity's facts, its activities included, not a piece cut from it
        out = []
        for c in self.kids.get(i, []):
            if c["type"] in ("entity", "comparison", "cited"):
                continue
            if "#" in c["fact_id"]:
                out.append(c)
            out += self.below(c["fact_id"])
        return out

    def is_cond(self, i):
        n = self.byid.get(i)
        return bool(n) and ((n["type"] == "activity" and n["kind"] != "measurement") or n["type"] == "entity")

    def vector(self, i):
        """The condition vector of a node: {ckey: [facts]} from the entity's own settings and the non-measurement activities above,
        nearest first (a key already seen is not overridden)."""
        out = {}
        for x in self.chain(i):
            if not self.is_cond(x):
                continue
            level = collections.defaultdict(list)
            for f in self.own(x):
                if f["type"] == "setting" and f["quantity"]:
                    level[ckey(f)].append(f)
            for k, fs in level.items():
                out.setdefault(k, fs)
        return out

    def results(self, ent):
        out = collections.defaultdict(list)
        for f in self.below(ent):
            if f["type"] in RESULT_TYPES and f["quantity"]:
                out[ckey(f)].append(f)
        return out

    def entities(self):
        return [r["fact_id"] for r in self.rows if r["type"] == "entity" and any(f["type"] in RESULT_TYPES for f in self.below(r["fact_id"]))]

    def ent_of(self, i):
        return next((x for x in self.chain(i) if self.byid[x]["type"] == "entity"), None)

    def dep_of(self, i):
        return next((x for x in self.chain(i) if self.byid[x]["type"] == "activity" and self.byid[x]["kind"] in ("deposition", "simulation")), None)

    def members(self, c):
        return [l for l in c["links"].split(";")[1:] if l in self.byid and "#" not in l]

    def member_entities(self, c):
        out = []
        for m in self.members(c):
            n = self.byid[m]
            if n["type"] == "entity":
                out.append(m)
            elif n["type"] == "activity":
                out += [e for e in self.entities() if m in self.chain(e)]
        return list(dict.fromkeys(out))

    def run_results(self, ent):
        """What was measured on the deposition that made the entity (its process monitor): the deposition's measurement activities."""
        dep = self.dep_of(ent)
        out = collections.defaultdict(list)
        if dep:
            for a in self.kids.get(dep, []):
                if a["type"] == "activity" and a["kind"] == "measurement":
                    for f in self.own(a["fact_id"]):
                        if f["type"] in RESULT_TYPES and f["quantity"]:
                            out[ckey(f)].append(f)
        return out

    def inputs_of(self, ent):
        """The input entities named by the activities above the entity (the chips it was cut from, the compacts, the plasma)."""
        out = []
        for x in self.chain(ent):
            n = self.byid[x]
            if n["type"] == "activity":
                out += [i for i in n["inputs"].split(";") if i in self.byid]
        return list(dict.fromkeys(out))

    def material(self, ent):
        m = self.vector(ent).get("material")
        return m[0]["value_text"] if m else ""

    def reactant_A(self, ent):
        for k, fs in self.vector(ent).items():
            if k.startswith("pulse_time") and quals(fs[0]).get("step") == "reactant_A" and quals(fs[0]).get("species"):
                return quals(fs[0])["species"]
        return ""

    def comp(self, name):
        return self.byid[f"{self.key}:cmp:{name}"]

    def comps_of(self, i):
        ch = set(self.chain(i))
        return [c for c in self.comps if set(self.members(c)) & ch]

    def label(self, i):
        n = self.byid.get(i, {})
        return n.get("label_as_printed") or i

    def facts(self, **kw):
        """Facts matching every given column (quantity, qualifiers, type, method, ...); qualifiers compared as sets."""
        out = []
        for r in self.rows:
            if "#" not in r["fact_id"]:
                continue
            ok = True
            for k, v in kw.items():
                if k == "qualifiers":
                    ok = ok and set(filter(None, r["qualifiers"].split(";"))) == set(filter(None, v.split(";")))
                else:
                    ok = ok and r[k] == v
            if ok:
                out.append(r)
        return out


def ckey(f):
    qs = ";".join(sorted(p for p in f["qualifiers"].split(";") if p and not p.startswith("x=")))
    return f"{f['quantity']}{'{' + qs + '}' if qs else ''}" + (f"[{f['label_as_printed']}]" if f["quantity"] == "other" else "")


def val(f):
    v, lo, hi = num(f["value"]), num(f["value_min"]), num(f["value_max"])
    if v is None and lo is not None and hi is not None:
        v = (lo + hi) / 2
    return v if v is not None else (lo if lo is not None else hi)


def quals(f):
    return dict(p.split("=", 1) for p in f["qualifiers"].split(";") if "=" in p)


def fmt(f):
    return f"{f['censor']}{f['value'] or (f['value_min'] + '–' + f['value_max'] if f['value_min'] and f['value_max'] else f['value_min'] or f['value_max'])}{' ' + f['unit'] if f['unit'] else ''}" if (f["value"] or f["value_min"] or f["value_max"]) else f["value_text"]


def g(x, d=3):
    return f"{x:.{d}g}"


TREES = {k: Tree(k) for k in KEY}
USER = list(csv.DictReader((HERE / "user.facts.csv").open(encoding="utf-8")))


def one(key, **kw):
    fs = TREES[key].facts(**kw)
    return fs[0] if len(fs) == 1 else None


# ------------------------------------------------------------------ the comparison layer: derived quantities (lists.DERIVED)
ASSUMED = [u for u in USER if u["data_kind"] == "assumed"]


def _matches(f, q, need):
    """A fact serves an input when its quantity is q (other:<label> by label) and its qualifiers carry every required one."""
    if q.startswith("other:"):
        if f["quantity"] != "other" or f["label_as_printed"] != q[6:]:
            return False
    elif f["quantity"] != q:
        return False
    have = quals(f)
    return all(have.get(k) == v for k, v in need.items())


def _candidates(T, ent, spec, need):
    """The facts that can serve an input, nearest first: the entity's results and its run's, its condition vector, its input
    entities' results and settings, then (scope paper) every fact of the paper, then the assumed facts; each as (fact, source)."""
    pools = [("result", [f for fs in T.results(ent).values() for f in fs] + [f for fs in T.run_results(ent).values() for f in fs]),
             ("setting", [f for fs in T.vector(ent).values() for f in fs])]
    for i in T.inputs_of(ent):
        pools.append((f"input {T.label(i)}", [f for fs in T.results(i).values() for f in fs] + [f for f in T.own(i) if f["type"] == "setting"]))
    if spec["scope"] == "paper":
        pools.append(("paper", [f for f in T.rows if "#" in f["fact_id"] and f["type"] in ("setting", "observation", "derived", "model", "cited")]))
    pools.append(("assumed", ASSUMED))
    out = []
    for src, pool in pools:
        for q in spec["q"].split("|"):
            hits = [f for f in pool if _matches(f, q, need) and (f["value"] or f["value_min"] or f["value_max"])]
            exact = [f for f in hits if set(quals(f).items()) == set(need.items())]
            out += [(f, src) for f in exact] + [(f, src) for f in hits if f not in exact]
        if out and not spec["all"]:
            return out
    return out


def derive(T, ent, did, route=False, _depth=0):
    """A derived quantity of an entity: {value, unit, inputs: [(name, fact id, value as used, unit, source)], assumed: [ids],
    notes: [...]} or {error}. The stated fact wins when the entity or its run carries the quantity (route=True asks for the
    computed route anyway); an input that is itself a derived quantity is derived in turn."""
    D = L.DERIVED[did]
    if not route:
        stated = [f for fs in list(T.results(ent).values()) + list(T.run_results(ent).values()) for f in fs if f["quantity"] == did and (f["value"] or f["value_min"])]
        stated += [f for fs in T.vector(ent).values() for f in fs if f["quantity"] == did and (f["value"] or f["value_min"])]
        if stated:
            f = stated[0]
            return dict(value=val(f), unit=f["unit"], stated=f, inputs=[], assumed=[], notes=[f"stated: {f['fact_id']} {fmt(f)}" + (f" (and {len(stated) - 1} more)" if len(stated) > 1 else "")])
    subs = {"@material": T.material(ent), "@A": T.reactant_A(ent)}
    args, used, assumed, notes = {}, [], [], []
    for spec in D["inputs"]:
        need = {k: subs.get(v, v) for k, v in (p.split("=", 1) for p in spec["quals"].split(";") if "=" in p)}
        cands = _candidates(T, ent, spec, need)
        if spec["all"]:
            vals = []
            for f, src in cands:
                vals.append(L.convert(val(f), f["unit"], spec["unit"])); used.append((spec["name"], f["fact_id"], vals[-1], spec["unit"], src))
            if not vals:
                return dict(error=f"no fact for {spec['name']} ({spec['q']})")
            args[spec["name"]] = vals
            continue
        if not cands and spec["q"].split("|")[0] in L.DERIVED and spec["q"] != did and _depth < 3:
            sub = derive(T, ent, spec["q"].split("|")[0], _depth=_depth + 1)
            if "error" in sub:
                return dict(error=f"{spec['name']}: {sub['error']}")
            args[spec["name"]] = L.convert(sub["value"], sub["unit"], spec["unit"])
            used += [(f"{spec['name']}.{n}",) + tuple(rest) for n, *rest in sub["inputs"]]; assumed += sub["assumed"]; notes += [f"{spec['name']} derived: " + "; ".join(sub["notes"])]
            continue
        if not cands:
            if spec["default"] is not None:
                args[spec["name"]] = spec["default"]; notes.append(f"{spec['name']} not stated, taken as {spec['default']}"); continue
            return dict(error=f"no fact for {spec['name']} ({spec['q']}{' ' + spec['quals'] if spec['quals'] else ''}); an assumed fact would serve")
        f, src = cands[0]
        if spec["pick"] and len({x[0]["fact_id"] for x in cands}) > 1:
            for want in spec["pick"]:
                w = {k: v for k, v in (p.split("=", 1) for p in want.split(";") if "=" in p)}
                hit = [c for c in cands if set(quals(c[0]).items()) == set(w.items()) | set(need.items())]
                if hit:
                    f, src = hit[0]; break
        others = [c[0] for c in cands if c[0]["fact_id"] != f["fact_id"]]
        if others and src != "assumed":
            notes.append(f"{spec['name']}: {f['fact_id']} used, also " + ", ".join(f"{o['fact_id']} {fmt(o)}" for o in others[:3]))
        v = L.convert(val(f), f["unit"], spec["unit"])
        args[spec["name"]] = v; used.append((spec["name"], f["fact_id"], v, spec["unit"], src))
        if src == "assumed":
            assumed.append(f["fact_id"])
    return dict(value=D["fn"](**args), unit=D["unit"], inputs=used, assumed=list(dict.fromkeys(assumed)), notes=notes)


def dtext(d, digits=3):
    """A derived result as text: the value, its unit, the inputs with their sources, the assumed facts named."""
    if "error" in d:
        return d["error"]
    ins = ", ".join(f"{n}={g(v, digits)} {u} ({fid}{'' if src in ('result', 'setting') else ', ' + src})".replace(" (", " (") for n, fid, v, u, src in d["inputs"])
    return f"{g(d['value'], digits)} {d['unit']}".rstrip() + (f" [{ins}]" if ins else "") + (f" assumed: {', '.join(d['assumed'])}" if d["assumed"] else "") + \
        ("; " + "; ".join(d["notes"]) if d["notes"] else "")


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
    return unanswerable(text, "no operation: a power-law fit over the series (exponent, residual) and the Series A correction")


def q2():
    """Over Series D, PD50 against the effective channel height H − 2·S_IIb."""
    T = TREES["yim20"]; rows = []
    for m in T.member_entities(T.comp("D")):
        h = derive(T, m, "effective_channel_height"); pd = T.results(m).get("penetration_depth{level=50%;origin=entrance}")
        if "error" in h or not pd:
            return unanswerable("", f"{T.label(m)}: {h.get('error', 'no PD50')}")
        rows.append((T.label(m), h["value"], val(pd[0]), pd[0]))
    text = "; ".join(f"{lab}: H_eff {g(h)} nm, PD50 {fmt(pd)}" for lab, h, _, pd in rows)
    return unanswerable(text, "no operation: a power-law scaling (PD ∝ √H_eff) from a reference member against the measured values")


def q3():
    """For sample 11, every penetration depth value by method."""
    T = TREES["yim20"]; e = "yim20:ent:11"
    pds = [f for k, fs in T.results(e).items() for f in fs if f["quantity"] == "penetration_depth"]
    text = "; ".join(f"{fmt(f)} by {f['method']} ({f['qualifiers'] or 'no qualifier'})" for f in pds)
    return unanswerable(text, "no operation: two routes to one (entity, quantity) reported as a ratio with a warning when the qualifiers differ")


def q4():
    """Over Series F, the ratio GPC_I / GPC_IIb against purge time."""
    T = TREES["yim20"]; c = T.comp("F")
    text = "; ".join(f"{T.label(m)}: purge {fmt(T.vector(m)['purge_time{step=purge_A}'][0])}, GPC_I {fmt(T.results(m)['growth_per_cycle{position=outside}'][0])}, "
                     f"GPC_IIb {fmt(T.results(m)['growth_per_cycle{position=plateau}'][0])}" for m in T.member_entities(c))
    return unanswerable(text, "no operation: a ratio of two results on one entity over a series")


def q5():
    """Which stated comparisons in yim20 have an effect smaller than the reproducibility sd, per result quantity."""
    return unanswerable("", "no operation: effect (max − min over a comparison's members) against the replicate set's sd")


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
    tol, bend = r.get("other[tolerance for the oxide thickness]"), r.get("other[membrane bending displacement]")
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
        if v.get("plasma_gas_ratio{gas=H2}") and fmt(v["plasma_gas_ratio{gas=H2}"][0]) == "0.20" and re.fullmatch(r"mat22:ent:T\d+_R0\.20", e) and v.get("cycle_number") and v.get("film_thickness"):
            n, th = val(v["cycle_number"][0]), val(v["film_thickness"][0])
            gpc = T.results(e).get("growth_per_cycle")
            if n and th and gpc:
                out.append((val(v["deposition_temperature"][0]), f"{fmt(v['deposition_temperature'][0])}: {g(n, 3)} cycles for {fmt(v['film_thickness'][0])} → {g(10 * th / n, 2)} Å implied vs {fmt(gpc[0])} read from colour"))
    if not out:
        return unanswerable("", "no cell carries its cycle count, thickness target and a GPC")
    return answered("; ".join(t for _, t in sorted(out, reverse=True)), "per ratio-0.20 cell: the deposition's cycle count and 10 nm target (settings) against the colour-read GPC on the cell film")


def q10():
    """Thickness against cycles at 150 °C, ratio 0.80, from every source."""
    return unanswerable("", "no join rule: entities equal in every condition but cycle number are not joined")


def q11():
    """Mo atoms per cycle from RBS against GPC from SE at 150 °C, ratio 0.80, with the density."""
    T = TREES["mat22"]
    gc = [e for e in T.entities() if T.results(e).get("atoms_per_cycle{element=Mo}") and fmt(T.vector(e)["plasma_gas_ratio{gas=H2}"][0]) == "0.80" and fmt(T.vector(e)["deposition_temperature"][0]) == "150 °C"]
    if not gc:
        return unanswerable("", "no entity at 150 °C, ratio 0.80 carries Mo atoms per cycle")
    d = derive(T, gc[0], "growth_per_cycle", route=True)
    if "error" in d:
        return unanswerable("", f"derived GPC from atoms per cycle fails: {d['error']}")
    return unanswerable(f"{T.label(gc[0])}: GPC from RBS {dtext(d)}", "no join rule: the SE GPC sits on the SiO2/Si cell film, the RBS atoms per cycle on the glassy-carbon film; the join must say which setting it tolerated")


def q12():
    """The full composition of the 150 °C, 0.80 film including H, and its density relative to bulk."""
    T = TREES["mat22"]
    es = [e for e in T.entities() if T.results(e).get("composition{element=H}") and fmt(T.vector(e)["plasma_gas_ratio{gas=H2}"][0]) == "0.80" and fmt(T.vector(e)["deposition_temperature"][0]) == "150 °C"]
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
    return unanswerable("", "no operation: result against result over two members of the schedules comparison (the pair entities, their pieces and the runs' process monitors)")


def q16():
    """Crystalline ZnO fraction from XRD weight % against gravimetric ZnO %."""
    return unanswerable("", "no operation: two routes to one value on the pair entity and its XRD piece")


def q17():
    """Does the mass balance close: Δn_s per cycle × 20 against the ZnO mass gained by the two NPCs."""
    T = TREES["gre23"]; out, assumed = [], set()
    for m in T.member_entities(T.comp("schedules")):
        if T.byid[T.byid[m]["parent"]]["type"] != "activity":
            continue                                                            # the pairs, not the pieces cut from them
        a, b = derive(T, m, "moles_deposited"), derive(T, m, "moles_from_mass_gain")
        if "error" in a or "error" in b:
            return unanswerable("", f"{T.label(m)}: {a.get('error', '')} {b.get('error', '')}".strip())
        out.append(f"{T.label(m)}: Δn_s × N = {g(a['value'], 2)} mmol vs mass gain → {g(b['value'], 2)} mmol, {g(100 * (a['value'] / b['value'] - 1), 2)} % apart"); assumed |= set(a["assumed"]) | set(b["assumed"])
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
    return unanswerable("", "no derived quantity (yim20 exposure per dose, Q6) and no operation (square-law scaling)")


def q21():
    """Metal atoms per nm² per cycle in all three papers."""
    out = []
    for k, T in TREES.items():
        stated = [f for f in T.rows if f["quantity"] in ("atoms_per_cycle", "saturation_density") and f["value"] and f["type"] != "cited"]
        if stated:
            out.append(f"{k}: " + "; ".join(f"{fmt(f)} ({L.LABELS[f['quantity']]}, {f['type']} {f['fact_id']}, {f['data_kind']}{', ' + T.label(T.ent_of(f['fact_id'])) if T.ent_of(f['fact_id']) else ''})" for f in stated)); continue
        es = [e for e in T.entities() if T.results(e).get("growth_per_cycle")]
        d = derive(T, es[0], "atoms_per_cycle", route=True) if es else {"error": "no GPC"}
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
    return unanswerable(f"{len(cs)} claims: " + "; ".join(f"{k} {f['fact_id'].split(':')[1]}" for k, f in cs), "no operation: the quantified effect behind a claim from the comparison in its scope")


def q24():
    """Resistivity drop when a metallic phase appears, per paper."""
    return unanswerable("", "no operation: contrast within a comparison between the member whose observation names a metal and the others")


def q25():
    """The reproducibility figure of each paper and what it is a reproducibility of."""
    out, kinds = [], []
    for k, T in TREES.items():
        parts = []
        for c in [c for c in T.comps if c["kind"] == "replicate"]:                 # a replicate comparison: its standard deviations against the members' means
            ms = T.member_entities(c)
            for f in T.own(c["fact_id"]):
                if f["quantity"] == "other" and "standard deviation" in f["label_as_printed"] and f["value"]:
                    words = set(re.findall(r"[a-z]+", f["label_as_printed"].lower()))
                    for key in T.results(ms[0]):
                        names = {L.LABELS.get(key, ""), L.LABELS.get(key.split("{")[0], ""), key.split("{")[0].replace("_", " ")}
                        vals = [val(T.results(m)[key][0]) for m in ms if key in T.results(m) and T.results(m)[key][0]["unit"] == f["unit"]]
                        if len(vals) == len(ms) and any(w in n.lower().split() for n in names for w in words):
                            mean = abs(sum(vals) / len(vals))
                            parts.append(f"{L.LABELS.get(key, key)}: sd {fmt(f)} = {g(100 * val(f) / mean, 2)} % of the mean over {len(ms)} ({c['statement'].split(':')[-1].strip()})")
            if parts:
                kinds.append(f"{k}: between samples ({c['label_as_printed']})")
        for f in [f for f in T.rows if f["quantity"] == "thickness_nonuniformity" and f["value"]]:   # a nonuniformity: within one film
            e = T.ent_of(f["fact_id"]); parts.append(f"thickness nonuniformity {fmt(f)} within one film ({T.label(e)}: {f['statement'][:60]}…)"); kinds.append(f"{k}: within one film")
        if not parts:                                                               # the ± between the pieces of one run (the uncertainty column)
            for e in T.entities():
                if T.byid[T.byid[e]["parent"]]["type"] != "activity":
                    continue
                for key, fs in T.results(e).items():
                    f = fs[0]
                    if f["uncertainty"] and "spread" in f["statement"]:
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
        return "cited work " + l["scope"].split(":")[-1] if l["cited"] else "this work"
    def T_(l):
        t = l["ctx"].get("deposition_temperature"); return "T ambiguous" if t == "ambiguous" else (f"{t['value'] or t['value_min'] + '–' + t['value_max']} °C" if t else "no T in scope")
    text = "; ".join(f"{l['key']} {l['row']['censor']}{l['row']['value'] or l['row']['value_min'] + '–' + l['row']['value_max']} ({src(l)}, {T_(l)}, {l['row']['data_kind']})" for l in ls)
    vals = [l["value"] for l in ls]
    return answered(text + f" · span {g(max(vals) / min(vals))}×", "the forest's leaves of the quantity, their scope and context")


# ------------------------------------------------------------------ helpers for answers
def differing(T, ents, exclude=()):
    """The settings whose values differ among entities (stated by two or more), as text."""
    per = collections.defaultdict(dict)
    for e in ents:
        for k, fs in T.vector(e).items():
            per[k][e] = "; ".join(dict.fromkeys(fmt(f) for f in fs))
    out = []
    for k, m in per.items():
        if k in exclude or len(m) < 2 or len(set(m.values())) < 2:
            continue
        out.append(f"{k}: " + ", ".join(f"{T.label(e)} {v}" for e, v in m.items()))
    return " | ".join(out)


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
    for qid, kind, fn in QUESTIONS:
        try:
            a = fn()
        except Exception as e:                                                  # a failing computation is an unanswerable question, with the error
            a = unanswerable("", f"computation failed: {type(e).__name__}: {e}")
        counts[a["status"]] += 1
        changed = prev.get(qid, {}).get("changed", "")
        if prev.get(qid) and prev[qid]["status"] != a["status"]:
            changed = (changed + "; " if changed else "") + f"{prev[qid]['status']} -> {a['status']}"
        rows.append(dict(id=qid, question=fn.__doc__.strip(), kind=kind, status=a["status"], answer=a["answer"], how=a["how"], changed=changed))
        print(f"{qid:4s} {a['status']:12s} {a['answer'][:110]}{' | ' + a['how'][:90] if a['how'] else ''}")
    with (HERE / "questions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "question", "kind", "status", "answer", "how", "changed"]); w.writeheader(); w.writerows(rows)
    print("summary:", dict(counts))
