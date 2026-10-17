#!/usr/bin/env python3
"""The query layer of the pilot: the only place that selects, derives or compares values. The page (report.py), the regression
test (questions.py) and any later reader use it. It reads the three trees (<paper_id>.facts.csv, .points.json) and user.facts.csv.
"""
import collections, csv, json, math, re, sys
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
        self._cache = {}
        pj = HERE / f"{KEY[key]}.points.json"
        self.points = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}

    def chain(self, i):
        if ("chain", i) in self._cache:
            return self._cache[("chain", i)]
        out = self._cache[("chain", i)] = []
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
        if ("below", i) in self._cache:
            return self._cache[("below", i)]
        out = self._cache[("below", i)] = []
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

    def vector(self, i, _keyed=True):
        """The condition vector of a node: {ckey: [facts]} from the entity's own settings and the non-measurement activities above,
        nearest first (a key already seen is not overridden). A keyed setting (lists.KEYED: a Table 2 flow for one H2 ratio) is
        inherited only when the node's own value of the setting it names matches (P17)."""
        if ("vector", i, _keyed) in self._cache:
            return self._cache[("vector", i, _keyed)]
        out, plain = {}, (self.vector(i, _keyed=False) if _keyed else {})
        self._cache[("vector", i, _keyed)] = out
        def matches(f):
            for qk, qv in quals(f).items():
                if qk in L.KEYED:
                    if not _keyed:
                        return False
                    own = [g for k, gs in plain.items() if k.split("{")[0] == L.KEYED[qk] for g in gs]
                    if not any(num(g["value"]) is not None and num(qv) is not None and abs(num(g["value"]) - num(qv)) < 1e-9 for g in own):
                        return False
            return True
        for x in self.chain(i):
            if not self.is_cond(x):
                continue
            level = collections.defaultdict(list)
            sim = self.byid[x]["type"] == "activity" and self.byid[x]["kind"] == "simulation"
            for f in self.own(x):
                if f["quantity"] and matches(f) and (f["type"] == "setting" or (sim and f["type"] == "model" and f["data_kind"] == "model_input")):
                    level[ckey(f)].append(f)                                    # a simulation's chosen model inputs are its runs' conditions
            for k, fs in level.items():
                fs = inheritable(fs, own=(x == i))
                if fs:
                    out.setdefault(k, ranked(fs))                               # nearest level first, then ranked (P10)
        return out

    def results(self, ent):
        if ("results", ent) in self._cache:
            return self._cache[("results", ent)]
        out = collections.defaultdict(list)
        for f in self.below(ent):
            if f["type"] in RESULT_TYPES and f["quantity"]:
                out[ckey(f)].append(f)
        self._cache[("results", ent)] = {k: ranked(fs) for k, fs in out.items()}
        return self._cache[("results", ent)]

    def entities(self):
        if "entities" in self._cache:
            return self._cache["entities"]
        self._cache["entities"] = [r["fact_id"] for r in self.rows if r["type"] == "entity" and any(f["type"] in RESULT_TYPES for f in self.below(r["fact_id"]))]
        return self._cache["entities"]

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


ELEMENT_KIND = {}


def element_kind(key, eid):
    """The kind of an element (panel, caption, paragraph, table_cell, ...) from <paper_id>.elements.csv."""
    if key not in ELEMENT_KIND:
        p = HERE / f"{KEY[key]}.elements.csv"
        ELEMENT_KIND[key] = {r["element_id"]: r["kind"] for r in csv.DictReader(p.open(encoding="utf-8"))} if p.exists() else {}
    return ELEMENT_KIND[key].get(eid, "")


def kind(f):
    """The kind of a value (Sec. 18.5, P57): the stored data_kind, one of lists.KINDS; a user's fact is assumed, a cited work's fact
    cited, a stated fact without a data_kind stated. A value this layer derives (lists.DERIVED) is computed_by_kb (derived_record).
    Printed words come only from lists.PHRASES."""
    if f.get("author") == "user":
        return "assumed"
    if f["type"] == "cited":
        return "cited"
    if f.get("data_kind"):
        return f["data_kind"]
    return "measured" if f["type"] == "observation" else "stated"


def rank_key(f):
    """Among candidates at one distance from the entity (P9-P13): exact before a range before censored; printed in text or a table
    before read from a figure before computed by this layer; measured before a model input."""
    exact = 2 if f["censor"] else (0 if f["value"] else 1)
    src = {"read_from_figure": 1}.get(kind(f), 0)
    return (exact, src, 1 if kind(f) == "model_input" else 0)


def ranked(fs):
    return sorted(fs, key=rank_key)


def exact_values(fs):
    """The distinct exact values among facts of one key (value or value_text); a bound or a range is not exact."""
    return {f["value"] or f["value_text"] for f in fs if (f["value"] and not f["censor"]) or (f["value_text"] and not f["value_min"])}


def inheritable(fs, own=False):
    """The facts of one key at one level that a node below inherits (P16): a value marked option is never inherited; when the
    level states several mutually exclusive values (a list of substrates), only one marked default is, or none. A node's own
    settings are kept whole."""
    if own:
        return fs
    fs = [f for f in fs if quals(f).get("kind") != "option"]
    if len(exact_values(fs)) > 1:
        fs = [f for f in fs if quals(f).get("kind") == "default"]
    return fs


def res(T, ent, quantity, **need):
    """An entity's result facts of one quantity whose qualifiers include every one given (a GPC whatever it is averaged over)."""
    return [f for fs in T.results(ent).values() for f in fs if f["quantity"] == quantity and all(quals(f).get(k) == v for k, v in need.items())]


KEYLESS = {"x", "mode"} | set(L.KEYED)                   # qualifiers that describe a value's provenance, axis or key setting, not the quantity


def ckey(f):
    qs = ";".join(sorted(p for p in f["qualifiers"].split(";") if p and p.split("=")[0] not in KEYLESS and p not in ("kind=default", "kind=option")))
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


# ------------------------------------------------------------------ the comparison layer: the join
def vtext(T, e):
    return {k: "; ".join(dict.fromkeys(t for t in (fmt(f) for f in fs) if t)) for k, fs in T.vector(e).items()}


def role(T, ent):
    """What an entity is (P21): 'specimen' (made by a deposition: a film, a sample, a piece cut from one), 'input' (a thing that ends
    up in or under a film, measured before any deposition: chips, compacts) or 'model run' (a simulation's output)."""
    d = T.dep_of(ent)
    if d is None:
        return "input"
    return "model run" if T.byid[d]["kind"] == "simulation" else "specimen"


def specimens(T):
    """The specimens of a paper without the pieces cut from them (a piece counts through its specimen)."""
    return [e for e in T.entities() if role(T, e) == "specimen" and T.byid[T.byid[e]["parent"]]["type"] == "activity"]


def same_experiment(T, ent):
    """The entities (with observations) of the same role that are the same experiment as `ent`: equal condition vectors, nothing
    tolerated (P20). Near-equal entities are found by filtering on conditions (matching) and their differences shown side by side
    (differing). Entities of different roles are never compared as experiments (P21)."""
    v0, r0 = vtext(T, ent), role(T, ent)
    return [e for e in T.entities() if e != ent and role(T, e) == r0 and vtext(T, e) == v0]


def matching(T, roles=("specimen",), **conds):
    """The entities of the given roles whose condition vector states every given condition: {quantity: value text} matched on the
    key's quantity and the value as printed (a filter, P20)."""
    out = []
    for e in T.entities():
        if role(T, e) not in roles:
            continue
        v = vtext(T, e)
        if all(any(k.split("{")[0] == q and val_eq(t, want) for k, t in v.items()) for q, want in conds.items()):
            out.append(e)
    return out


def val_eq(text, want):
    a, b = num(re.sub(r"[^\d.eE+-].*$", "", text.strip())), num(str(want))
    return (a is not None and b is not None and abs(a - b) <= 1e-9 * max(1, abs(b))) or text.strip() == str(want)


# ------------------------------------------------------------------ the comparison layer: operations
def results_deep(T, ent):
    """An entity's results with those of the pieces cut from it and of the run that made it: {ckey: [facts]}."""
    out = collections.defaultdict(list)
    for e in [ent] + [r["fact_id"] for r in T.rows if r["type"] == "entity" and ent in T.chain(r["fact_id"])[1:]]:
        for k, fs in T.results(e).items():
            out[k] += fs
    for k, fs in T.run_results(ent).items():
        out[k] += fs
    return out


def input_quantities(T, f, _seen=None):
    """The quantities a fact is computed from, followed through the inputs column (P25)."""
    _seen = _seen if _seen is not None else set()
    out = set()
    for i in filter(None, f["inputs"].split(";")):
        if i in T.byid and i not in _seen:
            _seen.add(i); g_ = T.byid[i]
            out.add(g_["quantity"]); out |= input_quantities(T, g_, _seen)
    return out


def fittable(T, comp, xkey, ykey):
    """A result may be fitted against the comparison's varied setting unless one of its facts is computed from that setting (P25)."""
    xq = xkey.split("{")[0]
    return not any(xq in input_quantities(T, f) for m in T.member_entities(comp) for f in T.results(m).get(ykey, []))


def power_fit(pairs):
    """y = a x^b by least squares in log-log: (b, a, rms residual of log10 y)."""
    pts = [(math.log10(x), math.log10(y)) for x, y in pairs if x > 0 and y > 0]
    n = len(pts); mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts); b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx else float("nan")
    a = 10 ** (my - b * mx); res = (sum((p[1] - (math.log10(a) + b * p[0])) ** 2 for p in pts) / n) ** 0.5
    return b, a, res


def series_xy(T, comp, xkey, ykey):
    """The members of a stated comparison as (entity, x from its condition vector, y from its results), where y exists; x is
    None when the member states that setting without a number (a cycled temperature)."""
    out = []
    for m in T.member_entities(comp):
        x, y = T.vector(m).get(xkey), results_deep(T, m).get(ykey)            # the member's results, its pieces' and its run's monitor (P26)
        if x and y and val(y[0]) is not None:
            out.append((m, val(x[0]), val(y[0])))
    return out


def correction(T, key, ykey, frm, to):
    """A factor that corrects y for a confounding setting: from a stated comparison that varies only that setting, the ratio of y
    at the value `to` over y at `frm`; None when no such comparison exists."""
    for c in T.comps:
        if c["quantity"] == key.split("{")[0]:
            by = {}
            for m in T.member_entities(c):
                v, y = T.vector(m).get(key), T.results(m).get(ykey)
                if v and y:
                    by.setdefault(fmt(v[0]) or v[0]["value_text"], []).append(val(y[0]))
            if frm in by and to in by:
                return (sum(by[to]) / len(by[to])) / (sum(by[frm]) / len(by[frm])), c
    return None, None


def relate(q, a, b):
    """Two values of one quantity set side by side (P24): ('ratio', a/b) on a ratio-scale quantity with both values positive,
    else ('difference', a - b)."""
    if q not in L.NOT_RATIO_SCALE and a is not None and b and a > 0 and b > 0:
        return "ratio", a / b
    return "difference", (a - b) if a is not None and b is not None else None


def routes(facts):
    """Several facts reaching one (entity, quantity): each pair as a ratio with a warning when their definitions (qualifiers,
    method, quantity) differ: [(fa, fb, ratio, warning)]."""
    out = []
    for i, a in enumerate(facts):
        for b in facts[i + 1:]:
            if val(a) is None or val(b) is None or not val(b):
                continue
            why = [w for w, ok in (("quantities", a["quantity"] == b["quantity"] and (a["quantity"] != "other" or a["label_as_printed"] == b["label_as_printed"])), ("qualifiers", a["qualifiers"] == b["qualifiers"]),
                                   ("methods", a["method"] == b["method"])) if not ok]
            try:
                va = L.convert(val(a), a["unit"], b["unit"]) if a["unit"] != b["unit"] and a["quantity"] == b["quantity"] else val(a)
            except (ValueError, KeyError):
                continue                                                        # units of different dimensions (a count and a length): not two routes to one value
            how, ra = relate(a["quantity"], va, val(b))
            if how != "ratio":
                continue                                                        # routes are reported as ratios; a signed or interval value is not
            out.append((a, b, ra,
                        ("different " + " and ".join(why) + ": a ratio of two routes, not a contradiction") if why else "same definition: a replicate pair"))
    return out


def effect(T, comp, key):
    """The effect of a stated comparison on a result: max − min of the members' values (one value per member)."""
    vs = [(m, val(T.results(m)[key][0])) for m in T.member_entities(comp) if key in T.results(m) and val(T.results(m)[key][0]) is not None]
    return (max(v for _, v in vs) - min(v for _, v in vs), vs) if len(vs) >= 2 else (None, vs)


def spread(T, comp, key):
    """The spread a replicate comparison gives for a result: its stated standard deviation fact for that result, else the
    standard deviation computed over its members' values; (sd, source)."""
    ms = T.member_entities(comp)
    for f in T.own(comp["fact_id"]):
        q = quals(f)
        if q.get("stat") == "sd" and f["value"] and spread_key(f) == key:
            return val(f), f["fact_id"]
    vs = [val(T.results(m)[key][0]) for m in ms if key in T.results(m) and val(T.results(m)[key][0]) is not None]
    if len(vs) >= 2:
        mean = sum(vs) / len(vs)
        return (sum((v - mean) ** 2 for v in vs) / (len(vs) - 1)) ** 0.5, f"computed over {len(vs)} members"
    return None, None


D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}   # expected range of n normal draws, in sd


def member_kind(T, ents):
    """What varies between a comparison's members: 'runs' when each was made in its own deposition, 'pieces' when they share
    one, 'model runs' for simulations."""
    deps = [T.dep_of(e) for e in ents]
    if any(d and T.byid[d]["kind"] == "simulation" for d in deps):
        return "model runs"
    return "pieces" if len(set(deps)) < len(deps) else "runs"


def judge(T, comp, key):
    """Can the effect of a stated comparison on one result be told from noise (P3)? Noise counts only when it is of the same kind
    as what varies between the members (runs against runs, pieces against pieces): a spread fact of that kind for the same result
    key (stat=sd), else the sd over a stated replicate comparison of that kind. The noise's condition is the replicate set's, and
    the sentence says so. The range of the n member values is set against the range expected from n draws of that noise
    (d2 × sd). Returns dict(effect, n, unit, sd, sd_n, sd_source, kind, sentence) or None when fewer than two members carry the
    result."""
    specs = [m for m in T.member_entities(comp) if T.byid[T.byid[m]["parent"]]["type"] != "entity"]     # specimens: a piece counts through its specimen
    rd = {m: results_deep(T, m) for m in specs}
    ents = [m for m in specs if key in rd[m] and val(rd[m][key][0]) is not None]
    if len(ents) < 2:
        return None
    vals = [val(rd[m][key][0]) for m in ents]
    unit = rd[ents[0]][key][0]["unit"]
    eff, kind = max(vals) - min(vals), member_kind(T, ents)
    lo, hi = ents[vals.index(min(vals))], ents[vals.index(max(vals))]
    end = lambda m: dict(id=m, name=T.label(m), value=val(rd[m][key][0]), text=text_of(rd[m][key][0]), fact=rd[m][key][0]["fact_id"])
    out = dict(effect=eff, n=len(vals), unit=unit, kind=kind, sd=None, sd_n=None, sd_source=None, low=end(lo), high=end(hi),
               between=endpoint_settings(T, lo, hi))
    if kind == "model runs":
        out["sentence"] = "model runs: no scatter to compare with"
        return out
    sd = None
    for f in T.rows:                                                            # a stated spread of the same result between the same kind
        q = quals(f)
        if "#" in f["fact_id"] and q.get("stat") == "sd" and q.get("between") == kind and spread_key(f) == key and f["value"]:
            sd, n_, src = val(f), q.get("n", "not_stated"), f["fact_id"]
            break
    if sd is None:                                                              # else the sd over a stated replicate set of that kind
        for r in [c for c in T.comps if c["kind"] == "replicate"]:
            rm = [m for m in T.member_entities(r) if key in T.results(m) and val(T.results(m)[key][0]) is not None]
            if len(rm) >= 2 and member_kind(T, rm) == kind:
                rv = [val(T.results(m)[key][0]) for m in rm]; mean = sum(rv) / len(rv)
                sd, n_, src = (sum((v - mean) ** 2 for v in rv) / (len(rv) - 1)) ** 0.5, str(len(rv)), f"computed over {r['label_as_printed']}"
                break
    noun = {"runs": "runs", "pieces": "pieces of one run"}[kind]
    if sd is None or not sd:
        out["sentence"] = f"no repeated {noun}; the size of the difference cannot be judged"
        return out
    out.update(sd=sd, sd_n=n_, sd_source=src)
    if len(vals) not in D2:
        out["sentence"] = f"{len(vals)} members: no expected range tabulated"
        return out
    exp = D2[len(vals)] * sd
    word = "smaller than" if eff < exp else "larger than"
    out["expected"] = exp
    out["sentence"] = f"{word} the scatter between {noun} at the base condition ({n_} {noun.split()[0]}, sd {g(sd, 2)}{' ' + unit if unit else ''})"
    return out


def endpoint_settings(T, a, b, n=4):
    """The settings that differ between two entities (P43), both values each: process-defining first, at most n; a setting keyed to
    another (P17) follows that one and is left out."""
    va, vb = vtext(T, a), vtext(T, b)
    keyed = {k for e in (a, b) for k, fs in T.vector(e).items() if any(set(quals(f)) & set(L.KEYED) for f in fs)}
    keys = [k for k in va if k in vb and va[k] != vb[k] and k not in keyed]
    keys.sort(key=lambda k: (L.PRIMARY.index(k.split("{")[0]) if k.split("{")[0] in L.PRIMARY else len(L.PRIMARY), k))
    return [dict(key=k, name=name_of(k, T.vector(a)[k][0]), low=va[k], high=vb[k]) for k in keys[:n]]


SPREAD_KEYS = ("stat", "between", "n")


def spread_key(f):
    """The result key a spread fact is about: its quantity and qualifiers without stat, between and n."""
    qs = ";".join(sorted(p for p in f["qualifiers"].split(";") if p and p.split("=")[0] not in SPREAD_KEYS + ("x",)))
    return f"{f['quantity']}{'{' + qs + '}' if qs else ''}"


def scale(ref_x, ref_y, x, exponent):
    """y predicted from a reference point by a power law y ∝ x^exponent."""
    return ref_y * (x / ref_x) ** exponent


def ratios_between(T, a, b):
    """Every result both entities (with their pieces and runs) carry, related by relate(): [(key, fa, fb, 'ratio'|'difference', x)]."""
    ra, rb = results_deep(T, a), results_deep(T, b); out = []
    for k in ra:
        if k in rb and "stat=" not in k:
            fa, fb = ra[k][0], rb[k][0]
            if val(fa) is not None and val(fb) is not None:
                va = L.convert(val(fa), fa["unit"], fb["unit"]) if fa["unit"] != fb["unit"] else val(fa)
                how, x = relate(fa["quantity"], va, val(fb))
                out.append((k, fa, fb, how, x))
    return out


def scope_comparisons(T, claim):
    """The stated comparisons a claim's links reach (P26): a link at or under a comparison names it; a link at or under a node that
    is a member of a comparison (an entity, or a deposition when the comparison's members are runs) names that comparison."""
    out = []
    members = {c["fact_id"]: set(T.members(c)) for c in T.comps}
    out += [c["fact_id"] for c in T.comps if c["links"].split(";")[0] == claim["fact_id"]]    # the claim is the comparison's purpose
    for l in filter(None, claim["links"].split(";")):
        if l not in T.byid:
            continue
        if T.byid[l]["type"] == "claim" and l not in _seen_claims(claim):
            out += scope_comparisons(T, dict(T.byid[l], _seen=_seen_claims(claim) | {claim["fact_id"]}))   # a claim resting on a claim
            continue
        for x in T.chain(l):
            if T.byid[x]["type"] == "comparison":
                out.append(x)
            out += [c for c, ms in members.items() if x in ms]
    return list(dict.fromkeys(out))


def _seen_claims(claim):
    return claim.get("_seen", set()) | {claim["fact_id"]}


def rests_on(T, claim):
    """The results a claim rests on (P26): the linked facts that carry a value, and the results of the entities and comparison members
    its links reach; [(fact, entity or '')]."""
    out = []
    for l in filter(None, claim["links"].split(";")):
        f = T.byid.get(l)
        if not f:
            continue
        if "#" in l and f["type"] in RESULT_TYPES and (f["value"] or f["value_min"] or f["value_max"] or f["value_text"] or f["points_ref"]):
            out.append((f, T.ent_of(l) or ""))
        elif f["type"] == "entity":
            out += [(g, l) for fs in T.results(l).values() for g in fs]
    for c in scope_comparisons(T, claim):
        for m in T.member_entities(T.byid[c]):
            out += [(g, m) for fs in T.results(m).values() for g in fs] + [(g, m) for fs in T.run_results(m).values() for g in fs]
    seen, uniq = set(), []
    for f, e in out:
        if f["fact_id"] not in seen:
            seen.add(f["fact_id"]); uniq.append((f, e))
    return uniq


def phases(T, m):
    """The phases found in a specimen or the pieces cut from it (P15): {species: 'detected' | 'not detected'}, the detected one winning."""
    pieces = [m] + [x["fact_id"] for x in T.rows if x["type"] == "entity" and m in T.chain(x["fact_id"])[1:]]
    out = {}
    for e in pieces:
        for f in T.below(e):
            if f["quantity"] == "phase" and f["value_text"]:
                sp = quals(f).get("species", "")
                if out.get(sp) != "detected":
                    out[sp] = f["value_text"]
    return out


METALS = {i for i, s in L.SPECIES.items() if s["kind"] == "material" and s["material_class"] == "element"}   # the metallic phases (P15, P50)


def contrast(T, comp, key, species=METALS):
    """Within a stated comparison, the specimens in which a phase of the given species was detected (a measured quantity, P15)
    against the others, on one result, the others in the order of the comparison's varied setting:
    (marked [(entity, value, fact, x)], others [...])."""
    marked, others = [], []
    xkey = comp["quantity"].split(";")[0]
    for m in T.member_entities(comp):
        if T.byid[T.byid[m]["parent"]]["type"] != "activity":
            continue                                                            # the specimens, not the pieces (their facts count through phases())
        r = results_deep(T, m)
        if key not in r or val(r[key][0]) is None:
            continue
        x = next((val(fs[0]) for k, fs in T.vector(m).items() if k.split("{")[0] == xkey), None)
        hit = any(sp in species and v == "detected" for sp, v in phases(T, m).items())
        (marked if hit else others).append((m, val(r[key][0]), r[key][0], x))
    others.sort(key=lambda t: (t[3] is None, t[3]))
    return marked, others


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
    if "reference" in have and need.get("reference") != have["reference"]:
        return False                                                            # a reference value serves only an input that asks for it (P8)
    if have.get("kind") == "target" and need.get("kind") != "target":
        return False                                                            # a target is not a result (P18)
    return all(have.get(k) == v for k, v in need.items())


def _candidates(T, ent, spec, need):
    """The facts that can serve an input, nearest first: the entity's results and its run's, its condition vector, its input
    entities' results and settings, then (scope paper) every fact of the paper, then the assumed facts; each as (fact, source)."""
    pools = [("result", [f for fs in T.results(ent).values() for f in fs] + [f for fs in T.run_results(ent).values() for f in fs])]
    for i in T.inputs_of(ent):                                                  # what the entity was made from: the same physical thing (P9)
        pools.append((f"input {T.label(i)}", [f for fs in T.results(i).values() for f in fs] + [f for f in T.own(i) if f["type"] == "setting"]))
    pools.append(("setting", [f for fs in T.vector(ent).values() for f in fs]))
    if spec["scope"] == "paper":
        pools.append(("paper", [f for f in T.rows if "#" in f["fact_id"] and f["type"] in ("setting", "observation", "derived", "model", "cited")]))
    pools.append(("assumed", [u for u in ASSUMED if not u["links"] or any(l.split(":")[0] == T.key for l in u["links"].split(";"))]))   # an assumed fact serves the papers its links name; a constant without links serves all
    out = []
    for src, pool in pools:
        for q in spec["q"].split("|"):
            hits = ranked([f for f in pool if _matches(f, q, need) and (f["value"] or f["value_min"] or f["value_max"]) and "stat" not in quals(f)])
            exact = [f for f in hits if set(quals(f).items()) == set(need.items())]
            out += [(f, src) for f in exact] + [(f, src) for f in hits if f not in exact]
        if out and not spec["all"]:
            return out
    return out


def has_own(T, ent, q):
    """The entity's own measured or stated facts of a quantity (its results, its run's monitor, its condition vector), spread
    facts excluded; q may be a DERIVED key with qualifiers ('exposure{over=run}'), which the fact must then carry."""
    qid, need = L.derived_key(q)
    fs = [f for fs in list(T.results(ent).values()) + list(T.run_results(ent).values()) + list(T.vector(ent).values()) for f in fs]
    return [f for f in fs if f["quantity"] == qid and (f["value"] or f["value_min"] or f["value_max"]) and "stat" not in quals(f)
            and all(quals(f).get(k) == v for k, v in need.items())]


def derived_keys(q, need=None):
    """The DERIVED keys that give a quantity id, most specific first, whose qualifiers the requirement `need` carries (a plain
    'exposure' is not served by 'exposure{over=run}')."""
    need = need or {}
    ks = [k for k in L.DERIVED if L.derived_key(k)[0] == q and all(need.get(a) == b for a, b in L.derived_key(k)[1].items())]
    return sorted(ks, key=lambda k: -len(L.derived_key(k)[1]))


_DERIVE_CACHE = {}


def derive(T, ent, did, _stack=()):
    if not _stack and (T.key, ent, did) in _DERIVE_CACHE:
        return _DERIVE_CACHE[(T.key, ent, did)]
    out = _derive(T, ent, did, _stack)
    if not _stack:
        _DERIVE_CACHE[(T.key, ent, did)] = out
    return out


def _derive(T, ent, did, _stack=()):
    """A derived quantity of an entity: {value, unit, inputs: [(name, fact id, value as used, unit, source)], assumed: [ids],
    notes: [...], chain: [derived ids used]} or {error}. Never derived when the entity already has the quantity as a measured or
    stated value (P7): then {error, stated: the fact}. An input that is itself a derived quantity is derived in turn, unless that
    quantity is already being derived up the chain: no derivation feeds back into its own inputs (P7)."""
    D = L.DERIVED[did]
    own = has_own(T, ent, did)
    if own:
        return dict(error=f"stated: {own[0]['fact_id']} {fmt(own[0])}", stated=own[0])
    stack = _stack + (did,)
    subs = {"@material": T.material(ent), "@A": T.reactant_A(ent)}
    args, used, assumed, notes, readings, chain = {}, [], [], [], {}, [did]
    for spec in D["inputs"]:
        if spec["q"] == "@formula_metals":                                      # from the film's chemical formula (lists.FORMULA_METALS)
            if subs["@material"] not in L.FORMULA_METALS:
                return dict(error=f"no formula for {subs['@material'] or 'the material'}")
            args[spec["name"]] = L.FORMULA_METALS[subs["@material"]]; continue
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
        dk = next((k for k in derived_keys(spec["q"].split("|")[0], need) if k not in stack), None)
        if not cands and dk:
            sub = derive(T, ent, dk, _stack=stack)
            chain += sub.get("chain", [])
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
        if spec.get("basis") and f["quantity"] in L.BASIS:                     # a fraction: expressed on the basis the definition needs (P4)
            fb = quals(f).get("relative_to", "not_stated")
            conv = L.BASIS[f["quantity"]]
            if fb == "not_stated":
                readings[spec["name"]] = (L.LABELS.get(f["quantity"], f["quantity"]), [(b, conv[(b, spec["basis"])](v)) for (b, to) in conv if to == spec["basis"]])
                v = readings[spec["name"]][1][0][1]
            elif (fb, spec["basis"]) in conv:
                v = conv[(fb, spec["basis"])](v)
        args[spec["name"]] = v; used.append((spec["name"], f["fact_id"], v, spec["unit"], src))
        if src == "assumed":
            assumed.append(f["fact_id"])
    out = dict(value=D["fn"](**args), unit=D["unit"], qualifiers=D.get("qualifiers", ""), inputs=used, assumed=list(dict.fromkeys(assumed)), notes=notes, readings=[], chain=chain)
    for name, (lab, rs) in readings.items():                                    # one value per basis when the paper does not state it
        out["readings"] = [(f"{lab} is relative to the {b.replace('_', ' ')}", D["fn"](**{**args, name: v})) for b, v in rs]
    return out


def collect(T, ents, qid):
    """Every value of a quantity over a set of entities (P27): the entity's own fact, else a derived value (lists.DERIVED); never a
    representative. Returns dict(values=[(entity, value, unit, source: fact id or 'computed', assumed ids)], low, high, unit,
    missing=[entities without a value])."""
    vals, missing = [], []
    for e in ents:
        own = has_own(T, e, qid)
        if own:
            f = own[0]
            v = val(f)
            if v is not None:
                vals.append((e, v, f["unit"], f["fact_id"], [])); continue
        for dk in derived_keys(qid):
            d = derive(T, e, dk)
            if "error" not in d:
                vals.append((e, d["value"], d["unit"], "computed", d["assumed"])); break
        else:
            missing.append(e)
    unit = vals[0][2] if vals else ""
    conv = [L.convert(v, u, unit) if u != unit else v for _, v, u, _, _ in vals] if vals else []
    return dict(values=vals, low=min(conv) if conv else None, high=max(conv) if conv else None, unit=unit, missing=missing)


def ctext(T, c, digits=2):
    """collect() as text: the range, then every value with its entity."""
    if not c["values"]:
        return "no value"
    rng = f"{g(c['low'], digits)}–{g(c['high'], digits)} {c['unit']}" if c["low"] != c["high"] else f"{g(c['low'], digits)} {c['unit']}"
    return f"{rng} over {len(c['values'])}: " + "; ".join(f"{T.label(e)} {g(v, digits)}{' (' + L.PHRASES['computed_by_kb'] + ')' if src == 'computed' else ''}" for e, v, u, src, _ in c["values"])


def dtext(d, digits=3):
    """A derived result as text: the value, its unit, the inputs with their sources, the assumed facts named."""
    if "error" in d:
        return d["error"]
    ins = ", ".join(f"{n}={g(v, digits)} {u} ({fid}{'' if src in ('result', 'setting') else ', ' + src})".replace(" (", " (") for n, fid, v, u, src in d["inputs"])
    if d.get("readings"):                                                       # both readings in one line (P4)
        return " or ".join(f"{g(v, digits)} {d['unit']} if {lab}" for lab, v in d["readings"]) + (f" [{ins}]" if ins else "") + \
            (f" assumed: {', '.join(d['assumed'])}" if d["assumed"] else "")
    return f"{g(d['value'], digits)} {d['unit']}".rstrip() + (f" [{ins}]" if ins else "") + (f" assumed: {', '.join(d['assumed'])}" if d["assumed"] else "") + \
        ("; " + "; ".join(d["notes"]) if d["notes"] else "")



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


# ================================================================== the five operations (Part B): find, detail, compare, claims, source
# Every value returned is a value record (record()): value, low, high, censor, unit, text, kind, definition (only when not the
# default), source (element id), fact (id), alternatives (the records it was chosen over), uncertainty, mode, method.
DEF_KEYS = {"over", "relative_to", "kind", "reference", "mode"}


def tree_of(any_id):
    return TREES[any_id.split(":")[0]]


def name_of(key, f=None):
    """The plain English name of a result or condition key (lists.NAMES), else the quantity's name with its qualifier values."""
    if key in L.NAMES:
        return L.NAMES[key]
    q, qs = key.split("{")[0].split("[")[0], key.split("{")[1].split("}")[0] if "{" in key else ""
    if q == "other":
        return (f or {}).get("label_as_printed") or (key.split("[")[1].rstrip("]") if "[" in key else "other")
    qd = dict(p.split("=", 1) for p in qs.split(";") if "=" in p)
    if "stat" in qd:                                                            # a spread fact: named by its statistic (P1)
        inner = ";".join(sorted(f"{k}={v}" for k, v in qd.items() if k not in ("stat", "between", "n")))
        return f"{STAT_WORDS.get(qd['stat'], qd['stat'])} of {name_of(q + ('{' + inner + '}' if inner else ''), f)}"
    base = L.NAMES.get(q, q.replace("_", " "))
    vals = [L.species_text(p.split("=", 1)[1]) if p.split("=")[0] in ("species", "gas", "surface", "phase") else p.split("=")[1].replace("_", " ")
            for p in qs.split(";") if p and p.split("=")[0] not in DEF_KEYS | {"x"}]
    return f"{base} ({', '.join(vals)})" if vals else base


STAT_WORDS = {"sd": "standard deviation", "relative_sd": "relative standard deviation", "half_range": "half range", "tolerance": "tolerance",
              "minimum": "minimum", "maximum": "maximum"}


def definition_of(f):
    """Words for the qualifiers that define a value differently from the default (lists.DEF_WORDS, lists.DEFAULT_DEFINITION)."""
    out = []
    for k, v in quals(f).items():
        if k in DEF_KEYS and k != "mode" and L.DEFAULT_DEFINITION.get(f["quantity"], {}).get(k) != v and (k, v) in L.DEF_WORDS:
            out.append(L.DEF_WORDS[(k, v)])
    return "; ".join(out)


def text_of(f):
    """A fact's value as written on the screen: censor and value, a range, or the value text, with the unit."""
    u = f" {f['unit']}" if f["unit"] and f["unit"] not in ("",) else ""
    if f["value"]:
        return f"{f['censor'].replace('dl', '')}{f['value']}{u}".strip()
    if f["value_min"] and f["value_max"]:
        return f"{f['value_min']}–{f['value_max']}{u}"
    if f["value_min"]:
        return f"≥ {f['value_min']}{u}"
    if f["value_max"]:
        return f"≤ {f['value_max']}{u}"
    return L.species_text(f["value_text"])                                      # a species id prints as its formula (P50)


def mode_of(T, f):
    """In situ or ex situ: the mode of the measurement activity above a fact, or the fact's own mode qualifier."""
    m = quals(f).get("mode")
    if m:
        return m
    for x in T.chain(f["fact_id"])[1:]:
        n = T.byid[x]
        if n["type"] == "activity" and n["kind"] == "measurement":
            return quals(n).get("mode", "")
    return ""


def caveats_of(T):
    """The paper's caveats (P45), with their links split into facts and nodes and their quantities."""
    if "cavs" not in T._cache:
        T._cache["cavs"] = [dict(f=c, facts={l for l in c["links"].split(";") if "#" in l}, nodes={l for l in c["links"].split(";") if l and "#" not in l},
                                 quantities=set(filter(None, c["quantity"].split(";"))),
                                 quals=[{tuple(p.split("=", 1)) for p in alt.split(";") if "=" in p} for alt in c["qualifiers"].split("|")] if c["qualifiers"] else [set()])
                            for c in T.rows if c["type"] == "caveat"]
    return T._cache["cavs"]


def caveats_for(T, f, ent=None, _seen=()):
    """The caveats that apply to a value or setting f, seen on entity ent (P45): those linking f, those whose quantity and qualifiers
    f carries and that link a node at or above f or ent; for a result, also those linking its entity (or the entity it is cut from)
    without a quantity; and, for a fact computed from other facts (its inputs column), the caveats of its inputs, reached at query
    time and never copied (P56)."""
    anc = set(T.chain(f["fact_id"])) | (set(T.chain(ent)) if ent else set()) | {T.key}
    out = []
    for c in caveats_of(T):
        if f["fact_id"] in c["facts"] or (c["quantities"] and f["quantity"] in c["quantities"] and any(alt <= set(quals(f).items()) for alt in c["quals"])
                                          and c["nodes"] & anc):
            out.append(c["f"])
        elif not c["quantities"] and f["type"] in RESULT_TYPES and ent and c["nodes"] & {x for x in T.chain(ent) if T.byid[x]["type"] == "entity"}:
            out.append(c["f"])
    for i in filter(None, f.get("inputs", "").split(";")):
        if i in T.byid and i not in _seen:
            out += [c for c in caveats_for(T, T.byid[i], T.ent_of(i), _seen + (f["fact_id"],)) if c not in out]
    return out


def direct_caveats(T, f, ent=None):
    """The caveats a fact carries without its inputs (for the P56 check)."""
    g = dict(f, inputs="")
    return caveats_for(T, g, ent)


def entity_caveats(T, ent):
    """The caveats that qualify an entity as a whole (linked without a quantity), its own or those of the entity it is cut from."""
    ents = {x for x in T.chain(ent) if T.byid[x]["type"] == "entity"}
    return [c["f"] for c in caveats_of(T) if not c["quantities"] and c["nodes"] & ents]


def caveat_targets(T, c):
    """What a caveat qualifies: the facts and entities it reaches (check.py: a caveat must qualify something)."""
    hit = [f["fact_id"] for f in T.rows if "#" in f["fact_id"] and f["type"] in ("setting", "cited", "claim") + RESULT_TYPES
           and c in caveats_for(T, f, T.ent_of(f["fact_id"]))]
    hit += [e for e in T.entities() if c in entity_caveats(T, e)]
    for e in T.entities():                                                      # settings an entity inherits from the activities above it
        for fs in T.vector(e).values():
            if c in caveats_for(T, fs[0], e):
                hit.append(fs[0]["fact_id"])
    return list(dict.fromkeys(hit))


def cav_list(cs):
    """Caveats as [dict(id, text)], each once."""
    return [dict(id=c["fact_id"], text=c["statement"]) for c in {c["fact_id"]: c for c in cs}.values()]


def specimen_class_of(T, ent):
    """The specimen class (Sec. 18.4) of the entity an id names, or of the entity above a fact."""
    e = ent if ent in T.byid and T.byid[ent]["type"] == "entity" else T.ent_of(ent) if ent else None
    return quals(T.byid[e]).get("specimen_class", "") if e else ""


AXES = ("entry", "definition", "method class", "specimen class")


def axes_of(key, rec):
    """The four comparability axes of a value (Sec. 18.4): the entry id, the definition (the qualifiers that define the value: over,
    relative_to, kind, reference, reference_element, basis), the method class, the specimen class."""
    q, _, rest = key.partition("{")
    qd = dict(p.split("=", 1) for p in rest.rstrip("}").split(";") if "=" in p)
    definition = ";".join(f"{k}={v}" for k, v in sorted(qd.items()) if k in DEF_KEYS | {"reference_element", "basis"})
    return dict(zip(AXES, (q, definition or "the default", rec.get("method_class") or (rec.get("method") or "none"), rec.get("specimen_class") or "none")))


def incomparable(key_a, rec_a, key_b, rec_b):
    """The axes on which two values differ, as 'axis (a vs b)' texts; empty when they are comparable (same entry, definition, method
    class and specimen class, Sec. 18.4). One rule for every quantity; no quantity-specific branch."""
    a, b = axes_of(key_a, rec_a), axes_of(key_b, rec_b)
    return [f"{x} ({a[x]} vs {b[x]})" for x in AXES if a[x] != b[x]]


def record(T, f, alternatives=(), ent=None):
    """The value record of a fact; caveats: those that apply to it as seen on ent (default: the entity it belongs to). A fact whose
    value is a curve (points_ref, no scalar) gets the text 'curve, N points' (P62): a record either has printable text or is a curve
    reference, never an empty line."""
    q = quals(f)
    lo, hi = num(f["value_min"]), num(f["value_max"])
    text = text_of(f) or (f"curve, {len(T.points.get(f['points_ref'], {}).get('points', []))} points" if f["points_ref"] else "")
    return dict(value=val(f), low=lo, high=hi, censor=f["censor"], unit=f["unit"], text=text, kind=kind(f), definition=definition_of(f),
                source=f["evidence"].split(";")[0], paper=f["fact_id"].split(":")[0], fact=f["fact_id"], method=f["method"], mode=mode_of(T, f),
                method_class=L.METHOD_CLASS.get(f["method"], ""), specimen_class=specimen_class_of(T, ent or f["fact_id"]),
                uncertainty=(dict(value=f["uncertainty"], kind=f["uncertainty_kind"], n=f["uncertainty_n"], basis=f.get("basis") or L.basis_of(f["uncertainty_kind"])) if f["uncertainty"] else None),
                stat=q.get("stat", ""), statement=f["statement"], alternatives=[record(T, a) for a in alternatives],
                caveats=cav_list(caveats_for(T, f, ent or T.ent_of(f["fact_id"]))))


def derived_record(T, ent, did, d):
    """The value record of a derived value (lists.DERIVED): kind computed_by_kb (P34, P57), its formula as definition, its inputs and assumed facts."""
    rs = d.get("readings") or []
    text = " or ".join(f"{g(v, 3)} {d['unit']} if {lab}" for lab, v in rs) if rs else f"{g(d['value'], 3)} {d['unit']}".strip()
    return dict(value=d["value"], low=None, high=None, censor="", unit=d["unit"], text=text, kind="computed_by_kb", definition=L.DERIVED[did]["formula"],
                source="", paper=T.key, fact="", method="calculation", mode="", uncertainty=None, stat="", statement="",
                method_class=L.METHOD_CLASS.get("calculation", "calculation"), specimen_class=specimen_class_of(T, ent),
                inputs=[dict(name=n, fact=fid, value=g(v, 3), unit=u, source=src) for n, fid, v, u, src in d["inputs"]],
                assumed=d["assumed"], readings=[dict(label=lab, value=g(v, 3)) for lab, v in rs], alternatives=[],
                caveats=cav_list([c for _, fid, *_ in d["inputs"] if fid in T.byid for c in caveats_for(T, T.byid[fid], ent)]))   # its inputs' caveats


def condition_records(T, ent):
    """The condition vector as {key: dict(name, record)}: the chosen fact (ranked) with the others as alternatives; a spread fact of
    the entity about a condition (a fabrication tolerance) becomes that record's uncertainty."""
    out = {k: dict(name=name_of(k, fs[0]), record=record(T, fs[0], fs[1:], ent=ent)) for k, fs in T.vector(ent).items() if text_of(fs[0])}
    for fs in T.results(ent).values():
        for f in fs:
            if quals(f).get("stat") and spread_key(f) in out and not out[spread_key(f)]["record"]["uncertainty"]:
                q = quals(f); out[spread_key(f)]["record"]["uncertainty"] = dict(value=f["value"], kind=q.get("between", ""), n=q.get("n", ""), stat=q.get("stat", ""), basis=f.get("basis") or L.basis_of("", q.get("between", ""), q.get("stat", "")), fact=f["fact_id"])
    return out


def result_records(T, ent):
    """An entity's results as {key: dict(name, record, settings)}: its own, its pieces' and its run's (results_deep), the chosen
    fact first (ranked: P9-P13) with the others as alternatives; spread facts become the record's uncertainty; then its derived
    values (lists.DERIVED; never one it has, P7)."""
    out = {}
    deep = results_deep(T, ent)
    for k, fs in deep.items():
        fs = ranked([f for f in fs if text_of(f) or f["points_ref"]])
        if not fs or "stat=" in k:
            continue
        r = record(T, fs[0], fs[1:], ent=ent)
        sp = [f for kk, gs in deep.items() if "stat=" in kk for f in gs if spread_key(f) == k]
        if sp and not r["uncertainty"]:
            q = quals(sp[0]); r["uncertainty"] = dict(value=sp[0]["value"], kind=q.get("between", ""), n=q.get("n", ""), stat=q.get("stat", ""), basis=sp[0].get("basis") or L.basis_of("", q.get("between", ""), q.get("stat", "")), fact=sp[0]["fact_id"])
        r["curve"] = dict(ref=fs[0]["points_ref"], x=quals(fs[0]).get("x", ""), points=T.points.get(fs[0]["points_ref"], {}).get("points", [])) if fs[0]["points_ref"] else None
        act = T.byid.get(fs[0]["parent"], {})
        r["settings"] = [dict(name=name_of(ckey(s), s), text=text_of(s)) for s in T.own(act["fact_id"]) if s["type"] == "setting" and text_of(s)] if act.get("kind") == "measurement" else []
        out[k] = dict(name=name_of(k, fs[0]), record=r)
    used = {(x["record"].get("uncertainty") or {}).get("fact") for x in out.values()}
    for k, fs in deep.items():                                                  # P79: a spread stated as its own fact that no record absorbed (the record has its own ±) stays a record of its own
        fs = ranked([f for f in fs if text_of(f)])
        if "stat=" in k and fs and fs[0]["fact_id"] not in used:
            out[k] = dict(name=name_of(k, fs[0]), record=record(T, fs[0], fs[1:], ent=ent))
    for did, D in L.DERIVED.items():
        d = derive(T, ent, did)
        if "error" in d:
            continue
        k = L.derived_key(did)[0] + ("{" + ";".join(sorted(D["qualifiers"].split(";"))) + "}" if D.get("qualifiers") else "")
        if k not in out:
            out[k] = dict(name=name_of(k), record=derived_record(T, ent, did, d))
    return out


def experiments(T):
    """The rows of find: specimens without their pieces, and model runs."""
    return [e for e in T.entities() if (role(T, e) == "specimen" and T.byid[T.byid[e]["parent"]]["type"] == "activity") or role(T, e) == "model run"]


def inputs(T):
    """The input entities of a paper (P79): things measured before any deposition (chips as fabricated, compacts as pressed), pieces of them included."""
    return [r["fact_id"] for r in T.rows if r["type"] == "entity" and role(T, r["fact_id"]) == "input"]


def distinguishing(T, ent, peers, n=2):
    """The 1-2 conditions that tell an entity from its peers: the condition keys whose values differ among them, process-defining
    first (lists.PRIMARY), then the rest."""
    vt = {e: vtext(T, e) for e in peers}
    keyed = {k for k, fs in T.vector(ent).items() if any(set(quals(f)) & set(L.KEYED) for f in fs)}     # a flow keyed to the ratio follows the ratio
    keys = [k for k in vt.get(ent, {}) if k not in keyed and all(k in vt[e] for e in peers) and len({vt[e].get(k) for e in peers}) > 1]
    keys.sort(key=lambda k: (L.PRIMARY.index(k.split("{")[0]) if k.split("{")[0] in L.PRIMARY else len(L.PRIMARY), k))
    cr = condition_records(T, ent)
    out = [dict(key=k, name=cr[k]["name"], text=cr[k]["record"]["text"]) for k in keys if k in cr][:n]
    if not out:                                                                 # peers differ only in how they were measured (Series B: the objective)
        ms = {e: measurement_settings(T, e) for e in peers}
        mk = [k for k in ms.get(ent, {}) if len({ms[e].get(k, (None,))[0] for e in peers}) > 1]
        out = [dict(key=k, name=name_of(k, ms[ent][k][1]), text=ms[ent][k][0]) for k in sorted(mk)][:n]
    return out


def measurement_settings(T, ent):
    """The settings of an entity's own measurement activities: {key: (text, fact)}."""
    out = {}
    for a in T.rows:
        if a["type"] == "activity" and a["kind"] == "measurement" and T.ent_of(a["fact_id"]) == ent:
            for f in T.own(a["fact_id"]):
                if f["type"] == "setting" and f["quantity"] and text_of(f):
                    out.setdefault(ckey(f), (text_of(f), f))
    return out


def comparison_label(T, c):
    """'Series F — purge time': the comparison's label and what it varies, in words."""
    varies = [L.NAMES.get(q, q.replace("_", " ")) for q in c["quantity"].split(";") if q]
    lab = c["label_as_printed"]
    if not varies or all(v.lower()[:5] in lab.lower() for v in varies):         # the label already says what it varies
        return lab
    return f"{lab} — {', '.join(varies)}"


def cited_name(T, w):
    """A cited work's name: its first author as the citing paper's facts give it ('Arts et al.'), and the reference number."""
    for f in T.kids.get(w, []):
        m = re.match(r"(?:follow-up )?([A-Z][a-z]+(?: [a-z]+)? et al\.?)", f["statement"])
        if m:
            return f"{m.group(1).rstrip('.')}. ({T.label(w)})"
    return T.label(w)


def cited_records(T, w):
    """A cited work's facts split into conditions (quantities the papers use as settings) and results, as records."""
    fs = [f for f in T.kids.get(w, []) if "#" in f["fact_id"] and f["quantity"] and text_of(f)]
    cond = {ckey(f): dict(name=name_of(ckey(f), f), record=record(T, f)) for f in fs if f["quantity"] in L.SETTING_QUANTITIES or L.ENTRIES.get(f["quantity"], {}).get("category") == "test_structure"}   # a test-structure dimension is a condition (P78)
    res = {ckey(f): dict(name=name_of(ckey(f), f), record=record(T, f)) for f in fs if ckey(f) not in cond}
    return cond, res


def find(paper=None, material=None, structure=None, result=None, conditions=None, cited=True):
    """Experiments that pass the filters, grouped by the authors' comparisons. conditions = {quantity: (low, high)} in lists.UNITS.
    Returns dict(groups=[dict(id, paper, label, members)], rows={id: row}, other=[ids]); a row: id, paper, name, inferred, role,
    distinguish (1-2 conditions), result (every record of the requested result quantity), groups (the comparisons it is in)."""
    rows, groups, other = {}, [], []
    for k, T in TREES.items():
        if paper and k != paper:
            continue
        exps = experiments(T)
        keep = []
        for e in exps:
            v = T.vector(e)
            if material and not any(fmt(f) == material or f["value_text"] == material for f in v.get("material", [])):
                continue
            if structure and not any(f["value_text"] == structure for f in v.get("structure", [])):
                continue
            ok = True
            for q, (lo, hi) in (conditions or {}).items():
                vals = [L.convert(val(f), f["unit"], L.UNITS.get(q, f["unit"])) for kk, fs in v.items() if kk.split("{")[0] == q for f in fs[:1] if val(f) is not None]
                if not any((lo is None or x >= lo) and (hi is None or x <= hi) for x in vals):
                    ok = False
            res = []
            if result:
                rr = result_records(T, e)
                res = [dict(key=kk, name=x["name"], record=x["record"]) for kk, x in rr.items() if kk.split("{")[0].split("[")[0] == result]
                if not res:                                                     # a setting quantity the entity states (gre23's exposure), where another derives it as a result
                    res = [dict(key=kk, name=x["name"], record=x["record"]) for kk, x in condition_records(T, e).items() if kk.split("{")[0].split("[")[0] == result
                           and quals(T.byid.get(x["record"]["fact"], {"qualifiers": ""})).get("kind") != "target"]      # a target is not a result (P18)
                if not res:
                    ok = False
            if ok:
                keep.append((e, res))
        comps = [c for c in T.comps]
        size = {c["fact_id"]: len(T.member_entities(c)) for c in comps}
        kept = {e for e, _ in keep}
        for e, res in keep:
            mine = sorted([c for c in comps if e in T.member_entities(c)], key=lambda c: size[c["fact_id"]])
            peers = T.member_entities(mine[0]) if mine else [x for x in exps if role(T, x) == role(T, e)]
            rows[e] = dict(id=e, paper=k, name=T.label(e), inferred=T.byid[e]["how"] == "inferred", role=role(T, e),
                           distinguish=distinguishing(T, e, [p for p in peers if p in exps] or [e]), result=res, groups=[c["fact_id"] for c in mine],
                           home=mine[0]["fact_id"] if mine else "")
            if not mine:
                other.append(e)
        if cited and not (material or structure or conditions):                  # the cited works the paper gives values for, as rows of their own
            cw = []
            for w in [r["fact_id"] for r in T.rows if r["type"] == "cited" and "#" not in r["fact_id"]]:
                cond, res_ = cited_records(T, w)
                hits = [dict(key=kk, name=x["name"], record=x["record"]) for kk, x in res_.items() if not result or kk.split("{")[0].split("[")[0] == result]
                if (result and hits) or (not result and (cond or res_)):
                    rows[w] = dict(id=w, paper=k, name=cited_name(T, w), inferred=False, role="cited", distinguish=[dict(key=kk, name=x["name"], text=x["record"]["text"]) for kk, x in list(cond.items())[:2]],
                                   result=hits, groups=[f"{k}:cited"], home=f"{k}:cited")
                    cw.append(w)
            if cw:
                groups.append(dict(id=f"{k}:cited", paper=k, label="cited works", kind="cited", members=cw, all_members=cw))
        for c in comps:
            ms = [m for m in T.member_entities(c) if m in kept and rows[m]["home"] == c["fact_id"]]
            if ms or any(m in kept for m in T.member_entities(c)):
                groups.append(dict(id=c["fact_id"], paper=k, label=comparison_label(T, c), kind=c["kind"], members=ms,
                                   all_members=[m for m in T.member_entities(c) if m in kept]))
    return dict(groups=groups, rows=rows, other=other)


def claims_of(T, ids):
    """The claims pointing directly at any of the ids (an entity, a comparison, or a fact under them)."""
    ids = set(ids)
    out = []
    for c in T.rows:
        if c["type"] != "claim":
            continue
        hit = False
        for l in filter(None, c["links"].split(";")):
            if l in ids or (l in T.byid and (set(T.chain(l)) & ids)):
                hit = True
        if hit or set(scope_comparisons(T, c)) & ids:
            out.append(c)
    return out


def claim_record(T, c):
    """A claim as returned by claims(): statement, stance, cause and effect in words, the entities and comparisons it reaches, the
    results it rests on (records) and its scope in words."""
    ents = list(dict.fromkeys([e for f, e in rests_on(T, c) if e] + [l for l in c["links"].split(";") if l in T.byid and T.byid[l]["type"] == "entity"]))
    var = lambda s: [L.MECHANISMS[t]["name"] if t in L.MECHANISMS else L.NAMES.get(t, t.replace("_", " ")) for t in s.split(";") if t]
    return dict(id=c["fact_id"], paper=T.key if T else "", author=c.get("author", ""), statement=c["statement"], stance=c["stance"],
                cause=var(c["cause"]), effect=var(c["effect"]), relation=c.get("relation", "").replace("_", " "), cause_ids=[t for t in c["cause"].split(";") if t], effect_ids=[t for t in c["effect"].split(";") if t], comparisons=scope_comparisons(T, c) if T else [], entities=ents,
                rests_on=[record(T, f) for f, e in rests_on(T, c) if text_of(f)][:12], scope=scope_text(T, ents),
                caveats=cav_list(caveats_for(T, c)) if T else [],
                sized_by=[record(T, T.byid[i]) for i in c.get("sized_by", "").split(";") if T and i in T.byid],     # P46
                source=c["evidence"].split(";")[0])


def scope_text(T, ents):
    """The range a claim covers in words: the number of experiments and the ranges of the process-defining conditions they span."""
    if not ents:
        return "no condition"
    parts = []
    for q in L.PRIMARY:
        u = L.UNITS.get(q, "")                                                 # every value in the quantity's one unit
        vals = [L.convert(val(fs[0]), fs[0]["unit"], u) if fs[0]["unit"] and u else val(fs[0]) for e in ents for k, fs in T.vector(e).items() if k == q and val(fs[0]) is not None]
        texts = {fmt(fs[0]) for e in ents for k, fs in T.vector(e).items() if k == q}
        if vals:
            lo, hi = min(vals), max(vals)
            parts.append(f"{L.NAMES[q]} {g(lo)}{'–' + g(hi) if hi != lo else ''}{' ' + u if u else ''}")
        elif len(texts) == 1:
            parts.append(f"{L.NAMES[q]} {texts.pop()}")
    return f"{len(ents)} experiment{'s' if len(ents) > 1 else ''}" + (" · " + " · ".join(parts[:3]) if parts else "")


def claims(paper=None, variable=None, linked=None, author=None):
    """Claims with stance, cause → effect, scope and the results they rest on. variable: a quantity id or mechanism token in cause or
    effect; linked: an entity or comparison id the claim points at; author 'user' for the user's claims (user.facts.csv)."""
    out = []
    for k, T in TREES.items():
        if paper and k != paper or author == "user":
            continue
        pool = claims_of(T, [linked]) if linked and linked.split(":")[0] == k else ([] if linked else [c for c in T.rows if c["type"] == "claim"])
        for c in pool:
            if variable and variable not in c["cause"].split(";") + c["effect"].split(";"):
                continue
            out.append(claim_record(T, c))
    if author in (None, "user") and not paper and not linked:
        for u in USER:
            if u["type"] == "claim" and (not variable or variable in u["cause"].split(";") + u["effect"].split(";")):
                out.append(dict(id=u["fact_id"], paper="user", author="user", statement=u["statement"], stance=u["stance"],
                                cause=[L.NAMES.get(t, t) for t in u["cause"].split(";") if t], effect=[L.NAMES.get(t, t) for t in u["effect"].split(";") if t], relation=u.get("relation", "").replace("_", " "),
                                comparisons=[], entities=[], rests_on=[], scope=f"{len(u['links'].split(';'))} facts across papers", source=""))
    return out


def detail(any_id):
    """An experiment, an input or a comparison. For an entity: what (name, role, substrate, inputs), differs (its distinguishing
    conditions), recipe (the full condition vector), results (one record per result key, derived included), claims (pointing at it
    or its comparisons directly), comparisons, identity. For a comparison: varies, members, main results with their effect and the
    noise sentence (judge), fits (fittable series), confounders, claims."""
    T = tree_of(any_id); n = T.byid[any_id]
    if n["type"] == "cited":
        cond, res_ = cited_records(T, any_id)
        return dict(type="cited", id=any_id, paper=T.key, name=cited_name(T, any_id), statement=n["statement"], recipe=[dict(key=k, **v) for k, v in cond.items()],
                    results=[dict(key=k, **v) for k, v in res_.items()], claims=[claim_record(T, c) for c in claims_of(T, [any_id])])
    if n["type"] == "comparison":
        ms = T.member_entities(n)
        specs = [m for m in ms if role(T, m) != "specimen" or T.byid[T.byid[m]["parent"]]["type"] == "activity"]
        cl = claims_of(T, [any_id])
        mains = [q for c in cl for q in c["effect"].split(";") if q and q not in L.MECHANISMS]
        keys = sorted({k for m in specs for k in results_deep(T, m) if "stat=" not in k})
        shared = [k for k in keys if all(k in results_deep(T, m) for m in specs)]
        main = [k for k in keys if k.split("{")[0] in mains] or shared
        effects = [dict(key=k, name=name_of(k), main=k in main, **{x: (g(v, 3) if isinstance(v, float) else v) for x, v in j.items()})
                   for k in shared for j in [judge(T, n, k)] if j]
        xkey = next((k for m in ms for k in T.vector(m) if k.split("{")[0] == n["quantity"].split(";")[0]), None)
        fits = []
        if xkey and n["kind"] == "series":
            for k in shared:
                pts = [(x, y) for _, x, y in series_xy(T, n, xkey, k) if x and y and x > 0 and y > 0]
                if fittable(T, n, xkey, k) and len(pts) >= 3 and len({x for x, _ in pts}) >= 3:
                    b, a, r = power_fit(pts)
                    fit = dict(key=k, name=name_of(k), x=name_of(xkey), exponent=g(b, 2), residual=g(r, 2), n=len(pts), main=k in main, corrected=[])
                    # a confounder (a condition that differs among the members besides the varied one) corrected from a stated comparison
                    # that varies only it, and the fit redone (the correction and its source named)
                    xy = series_xy(T, n, xkey, k)
                    for ck in {kk for m, _, _ in xy for kk in T.vector(m) if kk != xkey}:
                        vals = {m: fmt(T.vector(m)[ck][0]) or T.vector(m)[ck][0]["value_text"] for m, _, _ in xy if ck in T.vector(m)}
                        if len(vals) != len(xy) or len(set(vals.values())) < 2:
                            continue
                        common = max(set(vals.values()), key=list(vals.values()).count)
                        new = []
                        for m, x, y in xy:
                            fac, src = (1.0, None) if vals[m] == common else correction(T, ck, k, vals[m], common)
                            if fac is None:
                                new = []; break
                            new.append((x, y * fac, m, vals[m], fac, src))
                        if new and len({p[0] for p in new}) >= 3:
                            b2, _, r2 = power_fit([(x, y) for x, y, *_ in new])
                            fit["corrected"].append(dict(condition=name_of(ck), to=common, exponent=g(b2, 2), residual=g(r2, 2),
                                                         changes=[dict(id=m, frm=v, factor=g(f_, 3), value=g(y, 3), by=comparison_label(T, c_)) for x, y, m, v, f_, c_ in new if c_]))
                    fits.append(fit)
        conf = differing(T, specs, exclude={k for m in specs for k in T.vector(m) if k.split("{")[0] in n["quantity"].split(";")})
        own_vals = [record(T, f) for f in T.own(any_id) if f["type"] in RESULT_TYPES and text_of(f)]
        return dict(type="comparison", id=any_id, paper=T.key, label=comparison_label(T, n), kind=n["kind"], statement=n["statement"], values=own_vals,
                    varies=[L.NAMES.get(q, q) for q in n["quantity"].split(";") if q], members=specs, main=main, more=max(0, len(main) - 3),
                    effects=effects, fits=fits, confounders=conf, claims=[claim_record(T, c) for c in cl],
                    purpose=T.byid[n["links"].split(";")[0]]["statement"] if n["links"].split(";")[0] in T.byid else "")
    ent = any_id
    comps = T.comps_of(ent)
    size = {c["fact_id"]: len(T.member_entities(c)) for c in comps}
    home = sorted(comps, key=lambda c: size[c["fact_id"]])
    peers = T.member_entities(home[0]) if home else [x for x in experiments(T) if role(T, x) == role(T, ent)]
    cond = condition_records(T, ent)
    sub = cond.get("substrate", {}).get("record", {}).get("text", "")
    ins = [T.label(i) for i in T.inputs_of(ent)]
    ids = [f for f in T.rows if f["type"] == "identity" and ent in f["links"].split(";")]
    return dict(type="entity", id=ent, paper=T.key, name=T.label(ent), inferred=T.byid[ent]["how"] == "inferred", role=role(T, ent),
                statement=T.byid[ent]["statement"], what=dict(substrate=sub, inputs=ins, input_ids=T.inputs_of(ent), parent=T.byid[ent]["parent"] if T.byid[T.byid[ent]["parent"]]["type"] == "entity" else "",
                                                               material=cond.get("material", {}).get("record", {}).get("text", ""),
                                                               reactants=[cond[k]["record"]["text"] for k in ("reactant_A", "reactant_B") if k in cond]),   # P50
                differs=distinguishing(T, ent, peers or [ent], n=6), recipe=[dict(key=k, **v) for k, v in cond.items()],
                results=[dict(key=k, **v) for k, v in result_records(T, ent).items()],
                claims=[claim_record(T, c) for c in claims_of(T, [ent] + [c["fact_id"] for c in comps])],
                comparisons=[dict(id=c["fact_id"], label=comparison_label(T, c)) for c in home], caveats=cav_list(entity_caveats(T, ent)),
                identity=[dict(kind=f["kind"], statement=f["statement"], others=[o for o in f["links"].split(";") if o != ent]) for f in ids])


def compare(ids, result=None, x=None):
    """Several experiments side by side: shared conditions (one line), differing conditions, results (records; a cell that cannot be
    set beside the others says why), a plot spec (x = the condition that varies among them, or a curve's abscissa; points and curves
    of the result), the claims linked to two or more of them."""
    by = {i: tree_of(i) for i in ids}
    conds = {i: condition_records(by[i], i) for i in ids}
    keys = list(dict.fromkeys(k for i in ids for k in conds[i]))
    shared, differ = [], []
    for k in keys:
        texts = {i: conds[i][k]["record"]["text"] if k in conds[i] else None for i in ids}
        name = next(conds[i][k]["name"] for i in ids if k in conds[i])
        if len(set(texts.values())) == 1:
            shared.append(dict(key=k, name=name, text=next(iter(texts.values()))))
        else:
            differ.append(dict(key=k, name=name, values=texts))
    differ.sort(key=lambda d: (L.PRIMARY.index(d["key"].split("{")[0]) if d["key"].split("{")[0] in L.PRIMARY else len(L.PRIMARY), d["key"]))
    res = {i: result_records(by[i], i) for i in ids}
    rkeys = list(dict.fromkeys(k for i in ids for k in res[i] if not result or k.split("{")[0] == result))
    results = []
    for k in rkeys:
        cells = {i: res[i][k]["record"] if k in res[i] else None for i in ids}
        have = [(i, cells[i]) for i in ids if cells[i]]
        axes = sorted({x for n_, (i, r) in enumerate(have) for j, s in have[n_ + 1:] for x in incomparable(k, r, k, s)})
        note = f"not comparable: {'; '.join(axes)}" if axes else ""                   # Sec. 18.4, one rule for every quantity
        bases_ = sorted({(r.get("uncertainty") or {}).get("basis") or "" for i, r in have if r.get("uncertainty")})
        if len(bases_) > 1:                                                         # Sec. 19.4: spreads of different bases are not alike
            note = (note + " · " if note else "") + "different basis: " + " vs ".join(b or "not stated" for b in bases_)
        rel = None
        if not axes and len(ids) == 2 and all(cells[i] and cells[i]["value"] is not None for i in ids):
            a, b = (cells[i] for i in ids)
            try:
                va = L.convert(a["value"], a["unit"], b["unit"]) if a["unit"] != b["unit"] else a["value"]
                how, xv_ = relate(k.split("{")[0], va, b["value"]); rel = dict(how=how, value=g(xv_, 3), unit="" if how == "ratio" else b["unit"])
            except (ValueError, KeyError):
                rel = None
        results.append(dict(key=k, name=next(res[i][k]["name"] for i in ids if k in res[i]), cells=cells, note=note, relation=rel))
    # results of one quantity under different keys (definitions) say why they are not one column
    by_q = collections.defaultdict(list)
    for r in results:
        by_q[r["key"].split("{")[0]].append(r)
    for q, rs in by_q.items():
        if len(rs) > 1:
            for r in rs:
                others = [o for o in rs if o is not r]
                r["note"] = r["note"] or f"not comparable with {', '.join(o['name'] for o in others)}: definition"
    xs = [d["key"] for d in differ if all(d["values"][i] and num(re.sub(r"[^\d.eE+-].*$", "", d["values"][i])) is not None for i in ids)]
    xkey = x or (xs[0] if xs else None)
    plot = None
    ykey = next((r["key"] for r in results if result and r["key"].split("{")[0] == result), results[0]["key"] if results else None)
    if ykey:
        pts, curves = [], []
        for i in ids:
            for r in results:
                c = r["cells"].get(i)
                if not c or r["key"].split("{")[0] != ykey.split("{")[0]:
                    continue
                if c.get("curve") and c["curve"]["points"]:
                    curves.append(dict(id=i, paper=c["paper"], mode=c["mode"], x=c["curve"]["x"], points=c["curve"]["points"], name=by[i].label(i)))
                elif c["value"] is not None and xkey and conds[i].get(xkey):
                    xv = conds[i][xkey]["record"]["value"]
                    if xv is not None:
                        pts.append(dict(id=i, paper=c["paper"], mode=c["mode"], x=xv, y=c["value"], kind=c["kind"], name=by[i].label(i)))
        plot = dict(x=xkey, x_name=name_of(xkey) if xkey else "", x_options=xs, y=ykey, y_name=name_of(ykey), points=pts, curves=curves)
    cl = []
    for i in ids:
        for c in claims_of(by[i], [i] + [c["fact_id"] for c in by[i].comps_of(i)]):
            cl.append((c["fact_id"], i))
    cnt = collections.Counter(c for c, _ in cl)
    linked = [claim_record(tree_of(c), tree_of(c).byid[c]) for c, n_ in cnt.items() if n_ >= 2]
    return dict(items=[dict(id=i, paper=by[i].key, name=by[i].label(i)) for i in ids], shared=shared, differing=differ, results=results,
                plot=plot, claims=linked)


def source(any_id):
    """A fact's or an element's source: the element, its kind, its text (paper-derived, read from ingest/final, never stored in a
    tracked file), its crop, its coverage, and the values the facts of that element carry."""
    import elements as E
    key = any_id.split(":")[0] if ":" in any_id else None
    if key and "#" in any_id:
        T = TREES[key]; eid = T.byid[any_id]["evidence"].split(";")[0]
    else:
        key, eid = (any_id.split(":", 1) if ":" in any_id else (None, any_id))
        T = TREES[key]
    pid = KEY[key]
    els = {r["element_id"]: r for r in csv.DictReader((HERE / f"{pid}.elements.csv").open(encoding="utf-8"))}
    cov = {r["element_id"]: r for r in csv.DictReader((HERE / f"{pid}.coverage.csv").open(encoding="utf-8"))}
    e = els.get(eid, {})
    txt = E.texts(pid).get(eid, "") if e.get("kind") != "panel" else ""
    facts = [f for f in T.rows if "#" in f["fact_id"] and eid in f["evidence"].split(";")]
    return dict(paper=key, element=eid, kind=e.get("kind", ""), locator=e.get("locator", ""), text=txt, crop=e.get("crop", ""),
                coverage=cov.get(eid, {}).get("status", ""), values=[record(T, f) for f in facts if text_of(f)],
                statements=[f["statement"] for f in facts if not text_of(f) and f["type"] != "claim"])


# ---------------------------------------------------------------------------------------------------------------- search (P40)
# A lexical search over the text of every record: no embeddings, no synonym list. Tokens: lowercase, _ and - as spaces, plurals
# folded, numbers and units kept. Ranked by BM25. The page ships the same index (report.py) and scores with the same tokens.
TOKEN = re.compile(r"\d+(?:\.\d+)?|°[cfk]?|[^\W\d_][^\W_]*|[%Ω]")


def fold(w):
    """A word's singular: series and process stay, flows -> flow, properties -> property, passes -> pass."""
    if w[0].isdigit() or len(w) <= 3:
        return w
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("sses", "xes", "zes", "ches", "shes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def tokens(text):
    t = re.sub(r"[_\-‐–—]", " ", str(text or "").lower())
    return [fold(w) for w in TOKEN.findall(t)]


def record_type(T, f):
    """The kind of record a tree row is, in search results."""
    t = f["type"]
    if t == "entity":
        return {"input": "input", "model run": "model run"}.get(role(T, f["fact_id"]), "experiment")
    if t == "comparison":
        return "comparison set"
    if t == "activity":
        return "method note" if f["kind"] == "measurement" else "process note"
    if t == "cited":
        return "cited value" if "#" in f["fact_id"] else "cited work"
    if t in ("claim", "definition", "caveat"):
        return t
    if t in ("observation", "setting", "derived", "model"):
        if quals(f).get("stat"):
            return "uncertainty"
        if not text_of(f):
            par = T.byid.get(f["parent"], {})
            return "method note" if par.get("kind") == "measurement" or f["method"] else "note"
        return "setting" if t == "setting" else "value"
    return "note"


SEARCH_TYPES = ["concept", "experiment", "model run", "input", "comparison set", "claim", "definition", "caveat", "uncertainty", "value", "setting",
                "method note", "process note", "cited work", "cited value", "note"]
# P64: tiered ranking. Tier 1 a concept (an entry, species or mechanism matched by name or alias); tier 2 claims, values, comparison
# sets and the experiments; tier 3 settings, method and process notes, definitions, captions and the rest; an attribute quantity's
# records are demoted within their tier. Lexical (BM25) order survives within a tier.
TIER = {"concept": 1, "claim": 2, "value": 2, "comparison set": 2, "experiment": 2, "model run": 2, "input": 2, "cited value": 2, "uncertainty": 2}


def tier_of(r):
    t = TIER.get(r["type"], 3)
    return t + (0.5 if r.get("quantity") in L.ATTRIBUTES else 0)
_SEARCH = {}


def search_records():
    """Every record with its search text and one display line: (id, paper, type, line, tokens)."""
    if "recs" in _SEARCH:
        return _SEARCH["recs"]
    out = []
    import concept as CN
    for i, e in L.ENTRIES.items():                                             # the concepts themselves (P64 tier 1)
        if e.get("replaced_by"):
            continue
        name = e.get("name") or i.replace("_", " ")
        line = f"{name} ({i}): {CN.short_definition(e['definition'], 120)}"
        words = " ".join([i, e.get("label", ""), name, " ".join(e.get("aliases", [])), e.get("family", "")])   # names and aliases only: tier 1 is a name match
        out.append(dict(id=i, paper="", type="concept", line=line, tokens=collections.Counter(tokens(words)), quantity=i))
    for k, T in TREES.items():
        for f in T.rows:
            if f["type"] == "paper" or not (f["statement"] or f["type"] == "entity"):
                continue
            typ = record_type(T, f)
            if f["type"] == "entity":
                head = T.label(f["fact_id"])
            elif f["type"] == "comparison":
                head = comparison_label(T, f)
            elif f["type"] == "cited" and "#" not in f["fact_id"]:
                head = cited_name(T, f["fact_id"])
            elif text_of(f):
                e = T.ent_of(f["fact_id"])
                head = (T.label(e) + " · " if e else "") + f"{name_of(ckey(f), f)}: {text_of(f)}"
            else:
                head = ""
            line = " — ".join(x for x in (head, f["statement"]) if x)
            words = " ".join([line, f["label_as_printed"], L.NAMES.get(f["quantity"], f["quantity"]), f["quantity"], f["qualifiers"], f["method"],
                              f.get("mentions", ""), f["cause"], f["effect"]])
            out.append(dict(id=f["fact_id"], paper=k, type=typ, line=line, tokens=collections.Counter(tokens(words)), quantity=f["quantity"]))
    _SEARCH["recs"] = out
    n = len(out)
    df = collections.Counter(t for r in out for t in r["tokens"])
    _SEARCH["idf"] = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    _SEARCH["avg"] = sum(sum(r["tokens"].values()) for r in out) / max(n, 1)
    return out


def search_weight(r, t, k1=1.2, b=0.75):
    """A record's BM25 weight for one token."""
    tf = r["tokens"].get(t, 0)
    if not tf:
        return 0.0
    ln = sum(r["tokens"].values())
    return _SEARCH["idf"][t] * tf * (k1 + 1) / (tf + k1 * (1 - b + b * ln / _SEARCH["avg"]))


def search(words, paper=None):
    """Records ranked by BM25 over the query's tokens (each token counted once); ties keep the papers' order."""
    recs = search_records()
    q = list(dict.fromkeys(tokens(words)))
    scored = []
    for n, r in enumerate(recs):
        if paper and r["paper"] and r["paper"] != paper:
            continue
        s = sum(search_weight(r, t) for t in q)
        if s > 0:
            scored.append((tier_of(r), -s, n, r))
    return [dict(id=r["id"], paper=r["paper"], type=r["type"], line=r["line"], score=round(-s, 3), tier=t) for t, s, n, r in sorted(scored)]


# ---------------------------------------------------------------------------------------------------------------- vocabulary (P41)
_VOCAB = {}


def vocabulary():
    """Every result name and every setting name in the data, generated from the experiments: {kind: {name: {paper: count}}} with
    kind result or setting (a count is the number of experiments with a value of it), and the keys each name stands for."""
    if _VOCAB:
        return _VOCAB
    out = {"result": collections.defaultdict(collections.Counter), "setting": collections.defaultdict(collections.Counter)}
    keys = collections.defaultdict(set)
    for k, T in TREES.items():
        for e in experiments(T):
            for kk, x in result_records(T, e).items():
                if x["record"].get("text") or x["record"].get("curve"):
                    out["result"][x["name"]][k] += 1; keys[x["name"]].add(kk)
            for kk, x in condition_records(T, e).items():
                out["setting"][x["name"]][k] += 1; keys[x["name"]].add(kk)
    _VOCAB.update(result=dict(out["result"]), setting=dict(out["setting"]), keys={n: sorted(v) for n, v in keys.items()})
    return _VOCAB


# ---------------------------------------------------------------------------------------------------------------- values (P42)
SHOWN_SHARED = ["material", "reactant_A", "reactant_B", "structure", "substrate", "reactor", "reactor_type"]


def result_matches(T, e, result):
    """[(key, name, record)] of an entity for a result given by its name (query.vocabulary) or its quantity id: its results, or,
    for a setting quantity it states (P32), its stated conditions (a target excluded)."""
    qs = {result} | {q for q, n in L.NAMES.items() if n == result and "{" not in q} | set(concept_ids(result))   # a quantity's base name, or any name or alias the ontology knows, stands for all its keys
    hit = lambda kk, name: name == result or kk == result or kk.split("{")[0].split("[")[0] in qs
    out = [(kk, x["name"], x["record"]) for kk, x in result_records(T, e).items() if hit(kk, x["name"]) and (x["record"].get("text") or x["record"].get("curve"))]
    if not out:
        out = [(kk, x["name"], x["record"]) for kk, x in condition_records(T, e).items() if hit(kk, x["name"])
               and quals(T.byid.get(x["record"]["fact"], {"qualifiers": ""})).get("kind") != "target"]
    out += [(kk, x["name"], x["record"]) for kk, x in condition_records(T, e).items() if hit(kk, x["name"])          # P79: a stated target of the result (P18) is a column beside what was reached
            and quals(T.byid.get(x["record"]["fact"], {"qualifiers": ""})).get("kind") == "target" and kk not in {k for k, _, _ in out}]
    return out


def _where_ok(T, e, where):
    """Whether an entity's stated conditions pass where = {setting name or quantity id: value, or [min, max] in the quantity's unit}."""
    cr = condition_records(T, e)
    for s, want in (where or {}).items():
        recs = [x["record"] for kk, x in cr.items() if x["name"] == s or kk.split("{")[0].split("[")[0] == s]
        if not recs:
            return False
        ok = False
        for r in recs:
            q = ckey(T.byid[r["fact"]]).split("{")[0].split("[")[0] if r.get("fact") in T.byid else ""
            v = r["value"]
            if isinstance(want, list):
                if v is not None:
                    try:
                        v = L.convert(v, r["unit"], L.UNITS.get(q, r["unit"])) if r["unit"] else v
                    except (ValueError, KeyError):
                        pass
                    ok |= (want[0] is None or v >= want[0]) and (want[1] is None or v <= want[1])
            elif isinstance(want, (int, float)):
                ok |= v is not None and abs(v - want) <= 1e-9 * max(1, abs(want))
            else:
                ok |= str(want).strip().lower() in (str(r["text"]).lower(), str(fmt(T.byid[r["fact"]]) if r.get("fact") in T.byid else "").lower())
        if not ok:
            return False
    return True


def recipe_of(T, e):
    """The recipe activity above an entity (its process)."""
    return next((a for a in T.chain(e) if T.byid.get(a, {}).get("type") == "activity" and T.byid[a]["kind"] == "recipe" and not a.endswith(":reactor")), "")


def concept_ids(words):
    """The quantity ids the words name by the ontology's rules (concept.resolve), for a result argument given as a name or alias."""
    import concept as CN
    ids, _ = CN.resolve(words)
    return [i for i in ids if i in L.ENTRIES and L.ENTRIES[i]["type"] in ("quantity", "categorical")]


_DERIVED_NAMES = {}


def derived_names():
    """{text: derived id} of the knowledge base's derived definitions (lists.DERIVED): each id and its plain name, for a values request
    that names a derived quantity itself (P76)."""
    if not _DERIVED_NAMES:
        for did in L.DERIVED:
            _DERIVED_NAMES[did] = did; _DERIVED_NAMES[name_of(did)] = did
    return _DERIVED_NAMES


_SETTINGS = set()


def settings_entries():
    """The entries that are settings in the data (P76, P78a): every condition entry of the ontology (role condition) with a stated
    setting fact (type setting) in some paper, whatever node it sits under: materials and reactants, reactor, process parameters, test
    structure and measurement settings (objective, probe spot) alike. An output with a stated target (film_thickness{kind=target}) is
    not a setting entry: its records are results."""
    if not _SETTINGS:
        for T in TREES.values():
            for f in T.rows:
                if f["type"] == "setting" and f["quantity"] in L.ENTRIES and L.ENTRIES[f["quantity"]].get("role") == "condition":
                    _SETTINGS.add(f["quantity"])
    return _SETTINGS


def settings_entry(result):
    """The settings entry a values request names (P76, P78a), else '': an entry that is a setting in the data (settings_entries) given
    by id, key, name, alias or concept resolution. A request that is exactly the id or the name of a derived definition with an id of
    its own (effective channel height, exposure per run) names that derived quantity, not the entry; a derived definition whose id is
    the entry's (cycle_time, exposure: the knowledge base computes the setting itself) is the entry."""
    r = (result or "").strip()
    base = r.split("{")[0].split("[")[0]
    d = derived_names()
    S = settings_entries()
    if r in d and d[r] not in S:
        return ""
    qs = [base] + [q for q, n in L.NAMES.items() if n == r and "{" not in q] + concept_ids(r)
    return next((q for q in qs if q in S), "")


def setting_matches(T, e, result, S):
    """[(key, name, record)] of an entity's stated conditions for a settings entry (P76): its condition records whose key is the entry's
    (or the exact key or name asked), a target excluded; never a result and never a value computed by this knowledge base."""
    hit = lambda kk, name: name == result or kk == result or kk.split("{")[0].split("[")[0] == S
    out = [(kk, x["name"], x["record"]) for kk, x in condition_records(T, e).items() if hit(kk, x["name"])
           and quals(T.byid.get(x["record"]["fact"], {"qualifiers": ""})).get("kind") != "target"]
    seen = {r["fact"] for _, _, r in out} | {a["fact"] for _, _, r in out for a in r.get("alternatives", [])}
    for f in T.below(e):                                                        # P78a, P79: the settings of the entity's own activities (a measurement's objective, an anneal's temperature)
        if f["type"] == "setting" and f["quantity"] and text_of(f) and f["fact_id"] not in seen and hit(ckey(f), name_of(ckey(f), f)):
            out.append((ckey(f), name_of(ckey(f), f), record(T, f, ent=e))); seen.add(f["fact_id"])
    by_key = {}                                                                 # one record per key: a second statement of the same setting is its alternative (one cell lists both)
    for kk, name, rec in out:
        if kk in by_key:
            by_key[kk][2]["alternatives"] = list(by_key[kk][2].get("alternatives") or []) + [rec]
        else:
            by_key[kk] = (kk, name, dict(rec))
    return list(by_key.values())


def setting_extras(S, result, paper=None, where=None):
    """What a settings request leaves out of its table (P76), per paper: the quantity's values computed by this knowledge base on the
    experiments ({derived key: dict(name, formula, entities)}: named in one line, never a column) and its results that are not settings
    (a model's estimate of a purge time: [(entity, key, name, record)])."""
    hit = lambda kk, name: name == result or kk == result or kk.split("{")[0].split("[")[0] == S
    out = {}
    for k, T in TREES.items():
        if paper and k != paper:
            continue
        der, res = {}, []
        for e in experiments(T) + inputs(T):
            if where and not _where_ok(T, e, where):
                continue
            for kk, x in result_records(T, e).items():
                if not hit(kk, x["name"]) or not (x["record"].get("text") or x["record"].get("curve")):
                    continue
                if x["record"]["kind"] == "computed_by_kb":
                    der.setdefault(kk, dict(name=x["name"], formula=x["record"].get("definition", ""), entities=[]))["entities"].append(e)
                else:
                    res.append((e, kk, x["name"], x["record"]))
        for kk, name, rec, lab in paper_records(T, result, S, RESULT_TYPES):    # P79: a result of the setting attached to no entity (a calibration's measured temperature)
            if rec.get("kind") != "computed_by_kb":
                res.append((f"{k}:paper", kk, name, rec))
        if der or res:
            out[k] = dict(derived=der, results=res)
    return out


def _qs(result, S=""):
    """The quantity ids a values request stands for: the settings entry when it names one, else the request itself, any id the
    ontology names that way (a name or alias, concept_ids) and the base of a key."""
    base = result.split("{")[0].split("[")[0]
    return {S} - {""} or ({result, base} | {q for q, n in L.NAMES.items() if n == result and "{" not in q} | set(concept_ids(result)))


def _hit(result, S):
    qs = _qs(result, S)
    return lambda kk, name: name == result or kk == result or kk.split("{")[0].split("[")[0] in qs


def own_records(T, cid, result, S):
    """P79: the set-level records a comparison set owns for a quantity (values stated for the set, replicate statistics): [(key, name, record)]."""
    hit = _hit(result, S)
    return [(ckey(f), name_of(ckey(f), f), record(T, f)) for f in T.own(cid) if f["type"] in RESULT_TYPES and f["quantity"] and (text_of(f) or f["points_ref"]) and hit(ckey(f), name_of(ckey(f), f))]


def paper_records(T, result, S, types=RESULT_TYPES + ("setting",)):
    """P79: the records of a quantity attached to no entity and no set: facts under the paper, its recipe, reactor, method activities or
    a simulation activity (an observation, derived or model value; a setting when no experiment or input inherits it, such as an
    instrument's probe spot or an option): [(key, name, record, owner label)]. types narrows the fact types (the settings table takes
    the settings, its 'result, not a setting' lines the results)."""
    hit = _hit(result, S)
    inherited = {g["fact_id"] for e in experiments(T) + inputs(T) for fs in T.vector(e).values() for g in fs}
    out = []
    for f in T.rows:
        if "#" not in f["fact_id"] or not f["quantity"] or f["type"] not in types or not (text_of(f) or f["points_ref"]):
            continue
        if not hit(ckey(f), name_of(ckey(f), f)) or T.ent_of(f["fact_id"]) or f["fact_id"] in inherited:
            continue
        if any(T.byid[x]["type"] in ("comparison", "cited") for x in T.chain(f["fact_id"])):
            continue
        if f["type"] == "setting" and quals(f).get("kind") == "target":
            continue
        node = next((x for x in T.chain(f["fact_id"])[1:] if "#" not in x), "")
        out.append((ckey(f), name_of(ckey(f), f), record(T, f), T.label(node) if node and T.byid[node]["type"] != "paper" else "the paper"))
    return out


def input_rows(T, result, S, settings):
    """P79: {input entity: [(key, name, record)]} for the input entities (the structures before deposition) that hold a record of the quantity."""
    out = {}
    for e in inputs(T):
        m = setting_matches(T, e, result, S) if settings else result_matches(T, e, result)
        if m:
            out[e] = m
    return out


def slot_settings(T, e):
    """The structure class of an entity and its filled dimension slots, as the conditions of an input row (P78, P79)."""
    sc = quals(T.byid[e]).get("structure_class", "")
    slots = L.STRUCTURE_CLASSES.get(sc, {}).get("slots", [])
    out = [dict(key="structure_class", name="structure class", text=sc)] if sc else []
    cr = condition_records(T, e)
    out += [dict(key=kk, name=x["name"], text=x["record"]["text"]) for kk, x in cr.items() if kk.split("{")[0].split("[")[0] in slots]
    return out


PROCESS_KEYS = ("material", "reactant_A", "reactant_B")                        # what makes two experiments the same process (P80: a variant of a grid cell shares them)


def _num_prefix(t):
    m = re.match(r"\s*([-+]?\d+(?:\.\d+)?)", t or "")
    return (0, float(m.group(1)), t) if m else (1, 0.0, t or "")


def grid_info(T, c):
    """P80: a grid set from its full member list: cells = every member entity ('all'); axes = the two varied quantities; the level of
    every cell on each axis (its condition vector's text); the row and column levels sorted by value; the variant candidates: the
    paper's other experiments of the same process (PROCESS_KEYS) whose two levels match a cell (variant substrates, TEM pieces, a
    cycle series); the child series: the other sets whose members all lie in the cells or the candidates (views of the grid)."""
    cells = T.member_entities(c)
    axes = [q for q in c["quantity"].split(";") if q]
    vt = {m: vtext(T, m) for m in experiments(T)}

    def level(m, q):
        return next((v for kk, v in vt.get(m, {}).items() if kk.split("{")[0] == q and "kind=set_point" not in kk), None)
    level_of = {m: tuple(level(m, q) for q in axes) for m in vt}
    cell_lv = {level_of[m]: m for m in cells}
    proc = {kk: vt[cells[0]].get(kk) for kk in PROCESS_KEYS if cells and kk in vt[cells[0]]}
    cand = [m for m in vt if m not in cells and level_of[m] in cell_lv and all(vt[m].get(kk) == v for kk, v in proc.items())]
    children = [x["fact_id"] for x in T.comps if x is not c and x["kind"] != "grid" and set(T.member_entities(x)) <= set(cells) | set(cand)]
    return dict(cells=cells, axes=[(q, L.NAMES.get(q, q)) for q in axes], level_of={m: level_of[m] for m in list(cells) + cand}, candidates=cand, children=children,
                rows=sorted({level_of[m][0] for m in cells}, key=_num_prefix), cols=sorted({level_of[m][1] for m in cells}, key=_num_prefix) if len(axes) > 1 else [""])


def values(result, paper=None, where=None):
    """Every value of a result (P42), never a representative, grouped by comparison set: each experiment under the smallest set it is
    a member of, the others in one group per paper. A group: paper, set id, label, kind, what the set varies, the conditions its
    members share (material, structure, substrate, reactor, and the process-defining ones), the number of other shared conditions,
    rows (entity, the settings that vary within the set, the value record, its key and name), the claims about the set, its
    material, structure, reactor, process (recipe) and measurement methods for the comparison between groups. For a settings entry
    (settings_entry, P76) the rows are the experiments' stated conditions only (setting_matches): no result, no value computed by
    this knowledge base (setting_extras names those)."""
    groups = []
    S = settings_entry(result)
    for k, T in TREES.items():
        if paper and k != paper:
            continue
        rows = {}
        for e in experiments(T) + (inputs(T) if S else []):
            if where and not _where_ok(T, e, where):
                continue
            m = setting_matches(T, e, result, S) if S else result_matches(T, e, result)
            if m:
                rows[e] = m
        own = {c["fact_id"]: own_records(T, c["fact_id"], result, S) for c in T.comps}
        ins = input_rows(T, result, S, False) if not (where or S) else {}       # for a settings entry the inputs are level rows of the table
        pap = paper_records(T, result, S, ("setting",) if S else RESULT_TYPES + ("setting",)) if not where else []
        if not rows and not any(own.values()) and not ins and not pap:
            continue
        size = {c["fact_id"]: len(T.member_entities(c)) for c in T.comps}
        grids = {c["fact_id"]: grid_info(T, c) for c in T.comps if c["kind"] == "grid"} if not S else {}   # P80: a grid renders from its full member list
        child_ids = {x for gi in grids.values() for x in gi["children"]}
        home, variants = {}, {}
        for e in rows:
            g = next((gid for gid, gi in grids.items() if e in gi["cells"]), None)
            if not g:
                mine = sorted([c for c in T.comps if e in T.member_entities(c) and c["fact_id"] not in child_ids], key=lambda c: size[c["fact_id"]])
                g = mine[0]["fact_id"] if mine else next((gid for gid, gi in grids.items() if e in gi["candidates"]), "")
                if g in grids:
                    variants[e] = g
            home.setdefault(g, []).append(e)
        base = dict(paper=k, varies=[], shared=[], more_shared=0, claims=[], material=[], structure=[], reactor=[], process=[], measurement=[])

        def merged(rs):                                                         # several records of one key on one row: the first carries the others as alternatives (one cell lists all)
            out, at = [], {}
            for r in rs:
                key = (r["entity"], r["key"])
                if key in at:
                    at[key]["record"] = dict(at[key]["record"], alternatives=list(at[key]["record"].get("alternatives") or []) + [r["record"]])
                else:
                    at[key] = r; out.append(r)
            return out
        if ins:                                                                 # P79: the input entities (the structures before deposition), one row each
            rs = merged([dict(entity=e, name=T.label(e), settings=slot_settings(T, e), key=kk, result_name=name, record=rec) for e, m in ins.items() for kk, name, rec in m])
            groups.append(dict(base, id=f"{k}:inputs", label="the structures before deposition (input entities)", kind="inputs", rows=rs,
                               axes={r["key"]: axes_of(r["key"], r["record"]) for r in rs}, roles=["input"]))
        for c in T.comps:                                                       # P79: a set that is no experiment's home (a replicate set) but owns records: one aggregate row
            cid = c["fact_id"]
            if own[cid] and cid not in home and cid not in child_ids:
                rs = merged([dict(entity=cid, name="set", settings=[], key=kk, result_name=name, record=rec) for kk, name, rec in own[cid]])
                groups.append(dict(base, id=cid, label=comparison_label(T, c) + " · members: " + ", ".join(T.label(m) for m in T.member_entities(c)), kind="aggregate",
                                   rows=rs, claims=[x["fact_id"] for x in claims_of(T, [cid])], axes={r["key"]: axes_of(r["key"], r["record"]) for r in rs}, roles=["set"]))
        if pap:                                                                 # P79: records attached to no specimen and no set, one row each
            rs = merged([dict(entity=f"{k}:paper", name="paper-level", settings=[dict(key="under", name="under", text=lab)], key=kk, result_name=name, record=rec) for kk, name, rec, lab in pap])
            groups.append(dict(base, id=f"{k}:paper", label="records attached to no specimen and no set", kind="paper", rows=rs,
                               axes={r["key"]: axes_of(r["key"], r["record"]) for r in rs}, roles=["paper"]))
        for cid in [c["fact_id"] for c in T.comps] + [""]:
            ents = home.get(cid)
            if not ents:
                continue
            crs = {e: condition_records(T, e) for e in ents}
            keys = list(dict.fromkeys(kk for e in ents for kk in crs[e]))
            same = [kk for kk in keys if all(kk in crs[e] for e in ents) and len({crs[e][kk]["record"]["text"] for e in ents}) == 1]
            shown = [kk for kk in same if kk.split("{")[0] in SHOWN_SHARED or kk.split("{")[0] in L.PRIMARY]
            shown.sort(key=lambda kk: (L.PRIMARY.index(kk.split("{")[0]) if kk.split("{")[0] in L.PRIMARY else -1, kk))
            vary = []
            out_rows = []
            for e in ents:
                d = distinguishing(T, e, ents, n=3) if len(ents) > 1 else []
                vary += [x["key"] for x in d if x["key"] not in vary]
                for kk, name, rec in rows[e]:
                    out_rows.append(dict(entity=e, name=T.label(e), settings=d, key=kk, result_name=name, record=rec))
            def order(r):
                vs = []
                for kk in vary:
                    x = crs[r["entity"]].get(kk)
                    v = x["record"]["value"] if x else None
                    vs.append((0, v, "") if isinstance(v, (int, float)) else (1, 0, x["record"]["text"] if x else ""))
                return vs
            out_rows.sort(key=order)
            c = T.byid.get(cid, {})
            gi = grids.get(cid)
            groups.append(dict(paper=k, id=cid, label=comparison_label(T, c) if c else "values outside any comparison set", kind=c.get("kind", ""),
                               own=own.get(cid, []),                            # P79: the set's own records of the quantity, the first row of its block
                               grid=dict(gi, variants=[e for e in ents if e in variants], children=[(x, comparison_label(T, T.byid[x])) for x in gi["children"]],
                                         child_own={x: own[x] for x in gi["children"] if own.get(x)}) if gi else None,     # P80: the matrix layout, the variants, the child views
                               varies=[L.NAMES.get(q, q) for q in c.get("quantity", "").split(";") if q] if c else [],
                               shared=[dict(key=kk, name=crs[ents[0]][kk]["name"], record=crs[ents[0]][kk]["record"]) for kk in shown],
                               more_shared=len(same) - len(shown), rows=out_rows,
                               claims=[x["fact_id"] for x in claims_of(T, [cid])] if cid else [],
                               material=sorted({crs[e]["material"]["record"]["text"] for e in ents if "material" in crs[e]}),
                               structure=sorted({crs[e]["structure"]["record"]["text"] for e in ents if "structure" in crs[e]}),
                               reactor=sorted({crs[e]["reactor"]["record"]["text"] for e in ents if "reactor" in crs[e]}),
                               process=sorted({recipe_of(T, e) for e in ents} - {""}),
                               measurement=sorted({r["record"].get("method") or r["record"]["kind"] for r in out_rows}),
                               axes={r["key"]: axes_of(r["key"], r["record"]) for r in out_rows},          # one entry per result key (Sec. 18.4)
                               roles=sorted({role(T, e) for e in ents})))
    return groups


def set_members_all(T, c):
    """The full member list of a comparison set (P77): its member entities and those of any set nested in its links, every cell of a
    grid, kept to the experiments (specimens made by a deposition and model runs; a piece counts through its specimen, as in values)."""
    out = list(T.member_entities(c))
    for l in T.members(c):
        if T.byid[l]["type"] == "comparison":
            out += set_members_all(T, T.byid[l])
    ex = set(experiments(T))
    return [m for m in dict.fromkeys(out) if m in ex]


def set_table(cid):
    """One table for a comparison set (P77): rows = the set's full member list (set_members_all) and, first, the set itself for the
    records it owns (values stated for the set, replicate statistics); columns = every result key with a record among those rows,
    ordered by the ontology hierarchy of the key's quantity (vocab.HIERARCHY) then by name; cells = the value records as values()
    chooses them (result_records: the ranked fact, spreads folded into its uncertainty); a value computed by this knowledge base is
    counted, not a column. Returns dict(paper, id, label, kind, varies, members, columns [(key, name)], cells {row: {key: [record]}},
    settings {member: distinguishing conditions}, kb)."""
    T = tree_of(cid); c = T.byid[cid]
    ms = set_members_all(T, c)
    cells, names, kb = {}, {}, 0
    own = [f for f in T.own(cid) if f["type"] in RESULT_TYPES and (text_of(f) or f["points_ref"])]
    if own:
        cells["set"] = {}
        for f in own:
            cells["set"].setdefault(ckey(f), []).append(record(T, f)); names.setdefault(ckey(f), name_of(ckey(f), f))
    for m in ms:
        cells[m] = {}
        for k, x in result_records(T, m).items():
            r = x["record"]
            if not (r.get("text") or r.get("curve")):
                continue
            if r["kind"] == "computed_by_kb":
                kb += 1; continue
            cells[m][k] = [r]; names.setdefault(k, x["name"])
    order = [h["id"] for h in L.HIERARCHY]

    def pos(k):
        q = k.split("{")[0].split("[")[0]
        cat = L.ENTRIES.get(q, {}).get("category", "")
        return order.index(cat) if cat in order else len(order)
    columns = sorted({k for row in cells.values() for k in row}, key=lambda k: (pos(k), names[k].lower(), k))
    return dict(paper=T.key, id=cid, label=comparison_label(T, c), kind=c["kind"], varies=[L.NAMES.get(q, q) for q in c["quantity"].split(";") if q],
                members=ms, columns=[(k, names[k]) for k in columns], cells=cells, settings={m: distinguishing(T, m, ms, n=2) if len(ms) > 1 else [] for m in ms}, kb=kb)


def group_verdicts(groups):
    """Between the groups of values(): for every result key two groups share, the axes on which their values differ (Sec. 18.4),
    as [(key, group number a, group number b, [axis texts])]; empty axes = comparable."""
    out = []
    for n, ga in enumerate(groups, 1):
        for m, gb in enumerate(groups[n:], n + 1):
            for k in ga["axes"]:
                if k in gb["axes"]:                                             # the same result key in both sets (same definition by construction)
                    a, b = ga["axes"][k], gb["axes"][k]
                    out.append((k, n, m, [f"{x} ({a[x]} vs {b[x]})" for x in AXES if a[x] != b[x]]))
    return out


# ---------------------------------------------------------------------------------------------------------------- uncertainty words (P48)
BETWEEN = ("pieces", "runs", "position", "repeat_measurement", "items")
NO_BASIS = "basis not stated by the paper"                      # the one wording for a ± whose basis the paper does not give (P68)
UNC_WORDS = {"fit": "fit error", "measurement": "measurement uncertainty", "literature": "from the literature", "propagated": "propagated"}


def unc_note(u):
    """The words after a ± (P48, P60): the basis phrase of the ontology (Sec. 19; lists.BASES) first, then what the number is: 'sd
    between runs, n 4' for a spread between repeats, 'fit error' and the like for the other kinds; 'basis not stated by the paper'
    when the kind is not stated."""
    kind = (u or {}).get("kind")
    basis = (u or {}).get("basis") or L.basis_of(kind or "", kind if kind in BETWEEN else "", (u or {}).get("stat", ""))
    head = L.BASES[basis] if basis in L.BASES else NO_BASIS
    if not kind or kind == "not_stated":
        return f" ({head})"
    n = f", n {u['n']}" if u.get("n") and u.get("n") != "not_stated" else ""
    if kind in BETWEEN:
        return f" ({head}; {u.get('stat') or 'spread'} between {kind.replace('_', ' ')}{n})"
    return f" ({head}; {UNC_WORDS.get(kind, kind.replace('_', ' '))}{n})"
