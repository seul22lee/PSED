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


# ------------------------------------------------------------------ the comparison layer: the join
def vtext(T, e):
    return {k: "; ".join(dict.fromkeys(t for t in (fmt(f) for f in fs) if t)) for k, fs in T.vector(e).items()}


def same_experiment(T, ent, tolerate=()):
    """The entities (with observations) that are the same experiment as `ent` for a result comparison: both state the same
    process-defining settings (lists.PRIMARY), their condition vectors agree on every key both state, except keys whose quantity is
    tolerated (a substrate, a cycle count, a thickness target). Returns [(entity, {key: (this value, that value)} over the
    tolerated keys that differ, keys only one of the two states)]."""
    v0 = vtext(T, ent); out = []
    for e in T.entities():
        if e == ent:
            continue
        v = vtext(T, e)
        only = sorted(set(v0) ^ set(v))
        if any(k.split("{")[0] in L.PRIMARY for k in only):
            continue
        diff = {k: (v0[k], v[k]) for k in sorted(set(v0) & set(v)) if v0[k] != v[k]}
        if all(k.split("{")[0] in tolerate for k in diff):
            out.append((e, diff, only))
    return out


def join_text(joins):
    keys = sorted({k.split("{")[0] for _, d, _ in joins for k in d})
    return f"joined tolerating {', '.join(keys)}" if keys else "joined on equal condition vectors"


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
                ra = L.convert(val(a), a["unit"], b["unit"]) / val(b) if a["unit"] != b["unit"] and a["quantity"] == b["quantity"] else val(a) / val(b)
            except (ValueError, KeyError):
                continue                                                        # units of different dimensions (a count and a length): not two routes to one value
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
        if f["quantity"] == "other" and "standard deviation" in f["label_as_printed"] and f["value"]:
            words = set(re.findall(r"[a-z]+", f["label_as_printed"].lower()))
            names = {L.LABELS.get(key, ""), L.LABELS.get(key.split("{")[0], ""), key.split("{")[0].replace("_", " ")}
            if T.results(ms[0]).get(key, [{"unit": None}])[0]["unit"] == f["unit"] and any(w in n.lower().split() for n in names for w in words):
                return val(f), f["fact_id"]
    vs = [val(T.results(m)[key][0]) for m in ms if key in T.results(m) and val(T.results(m)[key][0]) is not None]
    if len(vs) >= 2:
        mean = sum(vs) / len(vs)
        return (sum((v - mean) ** 2 for v in vs) / (len(vs) - 1)) ** 0.5, f"computed over {len(vs)} members"
    return None, None


def scale(ref_x, ref_y, x, exponent):
    """y predicted from a reference point by a power law y ∝ x^exponent."""
    return ref_y * (x / ref_x) ** exponent


def ratios_between(T, a, b):
    """Every result both entities (with their pieces and runs) carry: [(key, fa, fb, ratio)]."""
    ra, rb = results_deep(T, a), results_deep(T, b); out = []
    for k in ra:
        if k in rb:
            fa, fb = ra[k][0], rb[k][0]
            if val(fa) is not None and val(fb):
                out.append((k, fa, fb, L.convert(val(fa), fa["unit"], fb["unit"]) / val(fb) if fa["unit"] != fb["unit"] else val(fa) / val(fb)))
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


def names_phase(T, m, marker):
    """Whether an observation on the specimen or a piece of it states the phase (the marker word, not negated), as a phase or
    composition statement rather than a peak position."""
    pieces = [m] + [x["fact_id"] for x in T.rows if x["type"] == "entity" and m in T.chain(x["fact_id"])[1:]]
    return any(re.search(r"(?<!no )" + marker, f["statement"]) and f["quantity"] in ("", "composition", "crystallinity") and (f["value"] or f["value_text"] or not f["quantity"])
               for e in pieces for f in T.below(e) if f["type"] == "observation")


def contrast(T, comp, key, marker):
    """Within a stated comparison, the specimens whose observations (their pieces' included) state the phase against the others,
    on one result, the others in the order of the comparison's varied setting: (marked [(entity, value, fact)], others [...])."""
    marked, others = [], []
    xkey = comp["quantity"].split(";")[0]
    for m in T.member_entities(comp):
        if T.byid[T.byid[m]["parent"]]["type"] != "activity":
            continue                                                            # the specimens, not the pieces (their facts count below)
        r = results_deep(T, m)
        if key not in r or val(r[key][0]) is None:
            continue
        x = next((val(fs[0]) for k, fs in T.vector(m).items() if k.split("{")[0] == xkey), None)
        (marked if names_phase(T, m, marker) else others).append((m, val(r[key][0]), r[key][0], x))
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
    pools.append(("assumed", [u for u in ASSUMED if not u["links"] or any(l.split(":")[0] == T.key for l in u["links"].split(";"))]))   # an assumed fact serves the papers its links name; a constant without links serves all
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
