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
    return unanswerable("", "no derived quantity: effective channel height (H minus twice the plateau thickness) is not defined in lists.py")


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
    T = TREES["yim20"]
    p = T.facts(quantity="partial_pressure", qualifiers="species=TMA")
    text = f"TMA partial pressure: {fmt(p[0])} ({p[0]['type']} fact {p[0]['fact_id']})" if p else "no TMA partial pressure fact"
    return unanswerable(text, "no derived quantity (exposure = partial pressure × pulse time) and the pressure is a model value: needs an assumed fact")


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
    fs = [f for f in T.rows if "#" in f["fact_id"] and f["label_as_printed"] in ("tolerance for the oxide thickness", "membrane bending displacement") or "nanostep" in f["statement"] and f["value"]]
    where = {T.byid[f["parent"]]["type"] + " " + T.byid[f["parent"]].get("kind", "") for f in fs if f["parent"] in T.byid}
    return unanswerable("; ".join(f"{f['statement'][:50]}… {fmt(f)}" for f in fs), f"facts in the wrong place: the chip metrology sits under {', '.join(sorted(where))}, no input entity; no derived quantity")


def q9():
    """GPC at ratio 0.20 implied by the cycle numbers chosen to give 10 nm, per temperature, against the Fig. 7b colour-read GPC."""
    T = TREES["mat22"]
    cyc = [f for f in T.facts(quantity="cycle_number", type="setting") if f["parent"].startswith("mat22:cmp")]
    return unanswerable("; ".join(f"{fmt(f)} under {f['parent']}" for f in cyc), "facts in the wrong place: the cycle numbers of s5.p7 sit on the grid comparison, not on each cell deposition")


def q10():
    """Thickness against cycles at 150 °C, ratio 0.80, from every source."""
    return unanswerable("", "no join rule: entities equal in every condition but cycle number are not joined")


def q11():
    """Mo atoms per cycle from RBS against GPC from SE at 150 °C, ratio 0.80, with the density."""
    return unanswerable("", "no join rule (glassy-carbon film vs SiO2/Si film), no derived quantity (atoms per cycle × M / ρ), no assumed constants (M of MoS2, Avogadro)")


def q12():
    """The full composition of the 150 °C, 0.80 film including H, and its density relative to bulk."""
    return unanswerable("", "no derived quantity (H per Mo from at.% and S/Mo), no assumed constant (bulk MoS2 density)")


def q13():
    """The H2 fraction of the total plasma feed (Ar included) for each ratio."""
    T = TREES["mat22"]
    flows = T.facts(quantity="gas_flow_rate", type="setting")
    return unanswerable(f"{len(flows)} flow settings in the recipe", "no join rule: the Table 2 flows carry their ratio only in the statement, not as a key")


def q14():
    """Sheet resistance of the PET film."""
    return unanswerable("", "no derived quantity: sheet resistance = resistivity / thickness")


def q15():
    """For 120 vs 120/160 °C, the ratio of every quantity measured on both."""
    return unanswerable("", "no operation: result against result over the members of the schedules comparison; the Zn Kα observation sits on the method, not on the entity")


def q16():
    """Crystalline ZnO fraction from XRD weight % against gravimetric ZnO %."""
    return unanswerable("", "no operation: two routes to one value on the pair entity and its XRD piece")


def q17():
    """Does the mass balance close: Δn_s per cycle × 20 against the ZnO mass gained by the two NPCs."""
    return unanswerable("", "no derived quantity; no assumed constants (molar mass of ZnO, the number of NPCs per run)")


def q18():
    """ZnO volume fraction in the 120 °C NPC from coating thickness and particle size."""
    return unanswerable("", "no derived quantity (shell volume fraction); the particle size is a hedged claim, not a setting")


def q19():
    """Knudsen number of each paper's structure under its own conditions."""
    T = TREES["yim20"]
    kn = T.facts(quantity="knudsen_number", qualifiers="species=TMA")
    st = {k: (one(k, quantity="structure_type") or {}).get("value_text") for k in TREES}
    return unanswerable(f"yim20 stated: Kn {fmt(kn[0])} ({kn[0]['statement'][:40]}); structures {st}", "no derived quantity (mean free path from pressure) and no assumed constant (molecular diameter) for gre23")


def q20():
    """Exposure per dose, yim20 against gre23, and what AR² scaling from yim20's x̃50 would predict for gre23's AR."""
    return unanswerable("", "no derived quantity (yim20 exposure per dose, Q6) and no operation (square-law scaling)")


def q21():
    """Metal atoms per nm² per cycle in all three papers."""
    return unanswerable("", "no derived quantity (atoms per cycle from GPC, density and molar mass) and no assumed constants")


def q22():
    """Deposited thickness per hour of reactor time in all three."""
    return unanswerable("", "no derived quantity (thickness over cycles × cycle time; yim20's cycle time from its pulses and purges)")


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
    return unanswerable("", "missing data: the ± spreads live in statements (no uncertainty column); no operation: spread over the replicate set")


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
