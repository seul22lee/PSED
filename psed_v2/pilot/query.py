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
        pj = HERE / f"{KEY[key]}.points.json"
        self.points = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}

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

    def vector(self, i, _keyed=True):
        """The condition vector of a node: {ckey: [facts]} from the entity's own settings and the non-measurement activities above,
        nearest first (a key already seen is not overridden). A keyed setting (lists.KEYED: a Table 2 flow for one H2 ratio) is
        inherited only when the node's own value of the setting it names matches (P17)."""
        out, plain = {}, (self.vector(i, _keyed=False) if _keyed else {})
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
            for f in self.own(x):
                if f["type"] == "setting" and f["quantity"] and matches(f):
                    level[ckey(f)].append(f)
            for k, fs in level.items():
                fs = inheritable(fs, own=(x == i))
                if fs:
                    out.setdefault(k, ranked(fs))                               # nearest level first, then ranked (P10)
        return out

    def results(self, ent):
        out = collections.defaultdict(list)
        for f in self.below(ent):
            if f["type"] in RESULT_TYPES and f["quantity"]:
                out[ckey(f)].append(f)
        return {k: ranked(fs) for k, fs in out.items()}

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


ELEMENT_KIND = {}


def element_kind(key, eid):
    """The kind of an element (panel, caption, paragraph, table_cell, ...) from <paper_id>.elements.csv."""
    if key not in ELEMENT_KIND:
        p = HERE / f"{KEY[key]}.elements.csv"
        ELEMENT_KIND[key] = {r["element_id"]: r["kind"] for r in csv.DictReader(p.open(encoding="utf-8"))} if p.exists() else {}
    return ELEMENT_KIND[key].get(eid, "")


def kind(f):
    """What a value is (the value record's kind): assumed (a user's assumption), cited (from another work), model (a model input or
    output), computed (calculated from other values), read from figure (a value whose first element is a figure panel), measured
    (an observation stated in text or a table), stated (a setting the paper states)."""
    if f.get("data_kind") == "assumed" or f.get("author") == "user":
        return "assumed"
    if f["type"] == "cited" or f.get("data_kind") == "literature":
        return "cited"
    if f["type"] == "model":
        return "model"
    if f["type"] == "derived" or f.get("data_kind") in ("calculated", "fit"):
        return "computed"
    key = f["fact_id"].split(":")[0]
    if element_kind(key, f["evidence"].split(";")[0]) == "panel":
        return "read from figure"
    return "measured" if f["type"] == "observation" else "stated"


def rank_key(f):
    """Among candidates at one distance from the entity (P9-P13): exact before a range before censored; printed in text or a table
    before read from a figure before computed by this layer; measured before a model input."""
    exact = 2 if f["censor"] else (0 if f["value"] else 1)
    src = {"read from figure": 1}.get(kind(f), 0)
    return (exact, src, 1 if kind(f) == "model" else 0)


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
        x, y = T.vector(m).get(xkey), T.results(m).get(ykey)
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
    ents = [m for m in T.member_entities(comp) if key in T.results(m) and val(T.results(m)[key][0]) is not None]
    if len(ents) < 2:
        return None
    vals = [val(T.results(m)[key][0]) for m in ents]
    unit = T.results(ents[0])[key][0]["unit"]
    eff, kind = max(vals) - min(vals), member_kind(T, ents)
    out = dict(effect=eff, n=len(vals), unit=unit, kind=kind, sd=None, sd_n=None, sd_source=None)
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
    out["sentence"] = f"{word} the scatter between {noun} at the base condition ({n_} {noun.split()[0]}, sd {g(sd, 2)} {unit})"
    return out


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
    """The stated comparisons a claim's links reach: a link under a comparison names it; a link under an entity names the
    comparisons that entity is in."""
    out = []
    for l in filter(None, claim["links"].split(";")):
        if l not in T.byid:
            continue
        for x in T.chain(l):
            if T.byid[x]["type"] == "comparison":
                out.append(x)
            if T.byid[x]["type"] == "entity":
                out += [c["fact_id"] for c in T.comps_of(x)]
                break
    return list(dict.fromkeys(out))


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


METALS = {"Mo", "W", "Ti", "Zn", "Al"}


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
    facts excluded."""
    fs = [f for fs in list(T.results(ent).values()) + list(T.run_results(ent).values()) + list(T.vector(ent).values()) for f in fs]
    return [f for f in fs if f["quantity"] == q and (f["value"] or f["value_min"] or f["value_max"]) and "stat" not in quals(f)]


def derive(T, ent, did, _stack=()):
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
        if not cands and spec["q"].split("|")[0] in L.DERIVED and spec["q"].split("|")[0] not in stack:
            sub = derive(T, ent, spec["q"].split("|")[0], _stack=stack)
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
