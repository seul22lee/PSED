#!/usr/bin/env python3
"""The one check of the pilot; prints the summary and exits 1 on any failure.

    python3 psed_v2/pilot/check.py

Facts (per paper, <paper_id>.*): fact ids unique; evidence ids and inputs resolve; vocabularies (type, quantity, qualifiers, data_kind, method,
censor; material and structure_type value_texts from lists.MATERIALS and STRUCTURES; a claim's stance from lists.STANCES; cause and effect quantity ids or mechanism tokens); a quantity of "other" carries label_as_printed; a value, value_text or points_ref has a quantity, a value or points_ref
also a data_kind; values are numbers; a value read off a colour-bar panel (lists.COLOUR_PANELS) says "read from colour"; every points_ref names a curve of <paper_id>.points.json, carries x= (its abscissa) and every curve is used; no two facts
state the same thing (same type, quantity, qualifiers, value, range, unit, value_text, points and mentions; or the same statement); no statement repeats eight or
more words of its element in a row (own words); coverage.csv lists every element once, nothing is "missed", covered
elements list facts that cite them, "no knowledge" has a reason.
Tree (stage 3, papers with a type=paper row): one root; every other row has a parent that exists; links resolve; no cycles;
an activity has a kind from lists.ACTIVITY_KINDS and how stated or inferred, an entity how; every entity has a deposition above it
(or sits under the recipe, before any deposition); every observation sits under a measurement activity or under the comparison it
spans; every setting under an activity or an entity (its own properties), never under a comparison; every comparison (the authors' intent: a series, a grid, a replicate set)
has a purpose fact as its first link, two or more members and a varied quantity id (none for a replicate set); what a comparison
varies is never "other"; every number with a unit in a comparison's label is in a member's condition vector; every claim has a link;
tree rows (ids without "#") are not counted as facts.
Experiments: <paper_id>.experiments.csv (experiments.py) has one run row per run of the tree (cited works are extra rows, kind cited).
User facts (user.facts.csv, user_facts.py): the facts schema; author user; ids user:<name>, unique; types from the lists; vocabularies as
for a paper's facts; every link resolves to a fact of the three papers or of the user file; a claim has links; a bridge links exactly
two facts and carries its factor in value_text (a quotient of quantity ids).
Cases: paper_case.csv has no "candidate, not used" cell in Cases 1 to 13 (every candidate is used or excluded with a reason).
"""
import collections, csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts as C  # noqa: E402
import lists as L  # noqa: E402
import elements  # noqa: E402
from elements import PAPERS as KEYS  # noqa: E402


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def words(t):
    return re.findall(r"[a-z0-9]+", re.sub(r"\$|\\text\{|\\mathrm\{|[{}^_]", " ", t.lower()))


def check(pid):
    err = []
    els = {r["element_id"]: r for r in rd(HERE / f"{pid}.elements.csv")}
    rows = rd(HERE / f"{pid}.facts.csv")
    facts = [r for r in rows if "#" in r["fact_id"]]                 # tree rows (stage 3) have ids without "#"
    cov = rd(HERE / f"{pid}.coverage.csv")
    pts = json.loads((HERE / f"{pid}.points.json").read_text(encoding="utf-8")) if (HERE / f"{pid}.points.json").exists() else {}
    if not facts:
        return ["no facts.csv"], {}
    ids = [f["fact_id"] for f in facts]
    for i in {i for i in ids if ids.count(i) > 1}:
        err.append(f"duplicate fact_id {i}")
    F = {f["fact_id"]: f for f in facts}
    texts = elements.texts(pid)
    seen_key, seen_stmt = {}, {}
    used_points = set()
    for f in facts:
        fid = f["fact_id"]
        bad = lambda m: err.append(f"{fid}: {m}")
        ev = f["evidence"].split(";")
        for e in ev:
            if e not in els:
                bad(f"evidence {e} not an element")
        for i in filter(None, f["inputs"].split(";")):
            if i not in F:
                bad(f"input {i} not a fact")
        if f["type"] not in L.TYPES:
            bad(f"type {f['type']}")
        if f["type"] == "claim" and f["stance"] not in L.STANCES:
            bad(f"claim stance {f['stance']!r} (lists.STANCES)")
        for t in L.variables_ok(f["cause"]) + L.variables_ok(f["effect"]):
            bad(f"variable {t} (a quantity id or mechanism:<token> of lists.MECHANISMS)")
        if f["quantity"] and f["quantity"] not in L.QUANTITIES:
            bad(f"quantity {f['quantity']}")
        if f["quantity"] == "other" and not f["label_as_printed"]:
            bad("quantity other without label_as_printed")
        if f["quantity"] == "material" and f["value_text"] not in L.MATERIALS:
            bad(f"material {f['value_text']!r} not in lists.MATERIALS")
        if f["quantity"] == "structure_type" and f["value_text"] not in L.STRUCTURES:
            bad(f"structure_type {f['value_text']!r} not in lists.STRUCTURES")
        for q in L.qualifiers_ok(f["qualifiers"]):
            bad(f"qualifier {q}")
        if f["data_kind"] and f["data_kind"] not in L.DATA_KINDS:
            bad(f"data_kind {f['data_kind']}")
        if f["method"] and f["method"] not in L.METHODS:
            bad(f"method {f['method']}")
        if f["censor"] not in L.CENSOR:
            bad(f"censor {f['censor']}")
        for k in ("value", "value_min", "value_max"):
            if f[k] and C.num(f[k]) is None:
                bad(f"{k} {f[k]!r} is not a number")
        if (f["value"] or f["value_min"] or f["value_max"] or f["points_ref"] or f["value_text"]) and not f["quantity"]:
            bad("value without quantity")
        if (f["value"] or f["value_min"] or f["value_max"] or f["points_ref"]) and not f["data_kind"]:
            bad("value without data_kind")
        if ev[0] in L.COLOUR_PANELS.get(KEYS[pid], {}) and (f["value"] or f["value_min"] or f["value_max"] or f["value_text"]) \
                and "read from colour" not in f["statement"]:                      # the fact's own element is a colour-bar panel
            bad("a value from a colour-bar panel must say 'read from colour'")
        if f["points_ref"]:
            used_points.add(f["points_ref"])
            if f["points_ref"] not in pts:
                bad(f"points_ref {f['points_ref']} not in {pid}.points.json")
            if "x=" not in f["qualifiers"]:
                bad("points without an x= qualifier (the curve's abscissa)")
        if not f["statement"].strip() or "\n" in f["statement"]:
            bad("statement empty or not one line")
        if f["value"] or f["value_min"] or f["value_max"] or f["points_ref"] or f["value_text"]:
            key = tuple(f[k] for k in ("type", "quantity", "qualifiers", "label_as_printed", "value", "value_min", "value_max",
                                       "censor", "unit", "value_text", "points_ref", "data_kind")) + \
                (tuple(sorted(m.strip().lower() for m in f["mentions"].split(";"))),)
            if key in seen_key:
                bad(f"same as {seen_key[key]}")
            seen_key[key] = fid
        s = " ".join(words(f["statement"]))
        if s in seen_stmt:
            bad(f"same statement as {seen_stmt[s]}")
        seen_stmt[s] = fid
        sw = words(f["statement"])
        grams = {tuple(sw[i:i + 8]) for i in range(len(sw) - 7)}
        for e in ev:
            tw = words(texts.get(e, ""))
            if any(tuple(tw[i:i + 8]) in grams for i in range(len(tw) - 7)):
                bad(f"statement repeats eight words of {e} in a row")
    for p in sorted(set(pts) - used_points):
        err.append(f"points {p} not referenced")
    cids = [c["element_id"] for c in cov]
    if sorted(cids) != sorted(els):
        err.append(f"coverage.csv elements differ from elements.csv ({len(set(els) - set(cids))} missing, {len(set(cids) - set(els))} extra)")
    for c in cov:
        if c["status"] == "missed":
            err.append(f"{c['element_id']}: missed (no fact, no reason)")
        elif c["status"] == "covered":
            for i in c["fact_ids"].split(";"):
                if i not in F or c["element_id"] not in F[i]["evidence"].split(";"):
                    err.append(f"{c['element_id']}: covered by {i}, which does not cite it")
        elif c["status"] == "no knowledge" and not c["reason"]:
            err.append(f"{c['element_id']}: no knowledge without a reason")
    err += check_tree(rows, els)
    if any(r["type"] == "paper" for r in rows):
        ex = [r for r in rd(HERE / f"{pid}.experiments.csv") if r.get("kind") != "cited"]
        want = {r["fact_id"] for r in rows if r["type"] == "run"} | set(experiment_entities(rows))
        if {r["run"] for r in ex} != want:
            err.append(f"{pid}.experiments.csv: {len(ex)} rows for {len(want)} experiments (rerun experiments.py)")
    s = summary(els, facts, cov)
    s["tree"] = tree_summary(rows) if any(r["type"] == "paper" for r in rows) else {}
    return err, s


def experiment_entities(rows):
    """Entities with observations: an entity whose subtree, not crossing another entity, holds an observation, derived or model fact."""
    K = collections.defaultdict(list)
    for r in rows:
        if r.get("parent"):
            K[r["parent"]].append(r)
    out = []
    for e in rows:
        if e["type"] != "entity":
            continue
        stack, found = [e["fact_id"]], False
        while stack and not found:
            for c in K.get(stack.pop(), []):
                if c["type"] == "entity":
                    continue
                if "#" in c["fact_id"] and c["type"] in ("observation", "derived", "model"):
                    found = True; break
                stack.append(c["fact_id"])
        if found:
            out.append(e["fact_id"])
    return out


def check_tree(rows, els):
    """Stage 3, for a paper that has its tree (a type=paper row): one root; every other row has a parent that exists; links resolve;
    no cycles; tree rows use the node types; an activity has a kind and how, an entity how; every entity has a deposition (a model run: a simulation) above it
    (or is an input entity: under the recipe, or a piece of one, with activities of order 0 only, before any deposition, and named in
    the `inputs` of an activity); every observation sits under a measurement activity or under the comparison it spans, never with
    a setting quantity, and one with a measured quantity never on the paper's method activity; every setting under an activity or
    an entity;
    every comparison has a purpose fact as its first link, two or more members that exist, and a varied quantity id unless it is a
    replicate set; what a comparison varies is never "other"; a comparison's label states no value that no member's condition
    vector carries; every claim has a link."""
    if not any(r["type"] == "paper" for r in rows):
        return []
    err = []
    R = {r["fact_id"]: r for r in rows}
    roots = [r["fact_id"] for r in rows if not r.get("parent")]
    if [R[i]["type"] for i in roots] != ["paper"]:
        err.append(f"tree: roots {roots[:5]} (want one paper row)")
    for r in rows:
        i, p = r["fact_id"], r.get("parent", "")
        if p and p not in R:
            err.append(f"{i}: parent {p} does not exist")
        for l in filter(None, r.get("links", "").split(";")):
            if l not in R:
                err.append(f"{i}: link {l} does not exist")
        if "#" not in i:
            if r["type"] not in L.NODE_TYPES + ["cited", "comparison"]:
                err.append(f"{i}: tree row type {r['type']}")
            for e in filter(None, r["evidence"].split(";")):
                if e not in els:
                    err.append(f"{i}: evidence {e} not an element")
            for q in L.qualifiers_ok(r["qualifiers"]):
                err.append(f"{i}: qualifier {q}")
        if r["type"] == "activity" and r["kind"] == "measurement" and "mode=" not in r["qualifiers"]:
            err.append(f"{i}: measurement activity without mode= (in situ or ex situ; P6)")
        if r["type"] == "activity" and r["kind"] not in L.ACTIVITY_KINDS:
            err.append(f"{i}: activity kind {r['kind']!r} (lists.ACTIVITY_KINDS)")
        if r["type"] in ("activity", "entity") and r["how"] not in L.HOW:
            err.append(f"{i}: {r['type']} how {r['how']!r} (stated or inferred)")
        if r["order"] and not r["order"].isdigit():
            err.append(f"{i}: order {r['order']!r} is not a whole number")
        if r["type"] == "claim" and not r.get("links"):
            err.append(f"{i}: claim without links")
    for r in rows:                                                      # walk up: must reach the root without a repeat
        seen, i = set(), r["fact_id"]
        while i in R and R[i].get("parent"):
            if i in seen:
                err.append(f"{r['fact_id']}: cycle through {i}"); break
            seen.add(i); i = R[i]["parent"]
    K = collections.defaultdict(list)
    for r in rows:
        if r.get("parent"):
            K[r["parent"]].append(r)
    NODES = ("activity", "entity", "comparison")

    def above(i):
        out, x = [], R[i].get("parent", "")
        while x in R:
            out.append(x); x = R[x].get("parent", "")
        return out

    def node_of(i):                                                     # the nearest tree row at or above a fact
        x = R[i].get("parent", "")
        while x in R and "#" in x:
            x = R[x].get("parent", "")
        return x

    def own(i):                                                         # a node's own facts: its subtree, not crossing another node
        out = []
        for ch in K.get(i, []):
            if ch["type"] in NODES or ch["type"] in ("paper", "cited"):
                continue
            if "#" in ch["fact_id"]:
                out.append(ch)
            out += own(ch["fact_id"])
        return out

    def vector(i):                                                      # the condition vector of a node: settings of the non-measurement activities and entities at or above it
        out = []
        for a in [i] + above(i):
            if (R[a]["type"] == "activity" and R[a]["kind"] != "measurement") or R[a]["type"] == "entity":
                out += [f for f in own(a) if f["type"] == "setting" and f["quantity"]]
        return out
    for r in rows:
        i = r["fact_id"]
        if r["type"] == "entity":
            ok = any(R[a]["type"] == "activity" and R[a]["kind"] in ("deposition", "simulation") for a in above(i))   # a model run: its simulation
            acts = [a for a in above(i) if R[a]["type"] == "activity"]
            before = not ok and bool(acts) and R[acts[0]]["kind"] == "recipe" and all(c["order"] == "0" for c in K.get(i, []) if c["type"] == "activity")
            if not ok and not before:
                err.append(f"{i}: entity without a deposition above it")
            if before and R[r["parent"]]["type"] == "activity" and not any(i in x["inputs"].split(";") for x in rows if x["type"] == "activity"):
                err.append(f"{i}: input entity that no activity names in its inputs column")
        if r["type"] == "activity":
            for x in filter(None, r["inputs"].split(";")):
                if x not in R or R[x]["type"] != "entity":
                    err.append(f"{i}: inputs names {x}, not an entity")
        if r["type"] == "comparison":
            if r["kind"] not in L.COMPARISON_KINDS:
                err.append(f"{i}: comparison kind {r['kind']!r} (lists.COMPARISON_KINDS)")
            links = [l for l in r["links"].split(";") if l]
            first = links[0] if links else ""
            if not first or first not in R or "#" not in first or R[first]["type"] not in ("claim", "observation", "setting", "model"):
                err.append(f"{i}: comparison without a purpose fact as its first link")
            members = [l for l in links[1:] if l in R and "#" not in l]
            if len(members) < 2:
                err.append(f"{i}: comparison with {len(members)} members (want two or more)")
            if r["kind"] != "replicate" and not all(q in L.QUANTITIES and q != "other" for q in r["quantity"].split(";")):
                err.append(f"{i}: comparison varies {r['quantity']!r} (quantity ids)")
            per = collections.defaultdict(dict)                         # what the members vary is never other; label values carried
            have = set()
            for m in members:
                if R[m]["type"] == "comparison":
                    continue
                for f in vector(m):
                    key = (f["quantity"], f["qualifiers"], f["label_as_printed"] if f["quantity"] == "other" else "")
                    v = f["censor"] + f["value"] + f["unit"] if f["value"] else f["value_text"] or f["statement"].split(": ", 1)[-1]
                    per[key][m] = per[key].get(m, "") + "|" + v
                    have |= {C.num(f[k]) for k in ("value", "value_min", "value_max") if f[k]}
            for key, m in per.items():
                if key[0] == "other" and len(set(m.values())) > 1:
                    err.append(f"{i}: varies setting other '{key[2]}' among its members; give it an id in lists.py")
            for v in label_values(r["label_as_printed"]):
                if v not in have:
                    err.append(f"{i}: label '{r['label_as_printed']}' states {v:g} but no member's condition vector carries it")
        if "#" in i and r["type"] in ("observation", "setting"):
            n = node_of(i)
            nt, nk = (R[n]["type"], R[n]["kind"]) if n in R else ("", "")
            if r["type"] == "observation" and not (nt == "comparison" or (nt == "activity" and nk == "measurement")):
                err.append(f"{i}: observation under {n or 'nothing'} ({nt} {nk}), not under a measurement activity or a comparison")
            qd = dict(p.split("=", 1) for p in r["qualifiers"].split(";") if "=" in p)
            if (r["quantity"] in L.DEFAULT_DEFINITION or "x=growth_per_cycle" in r["qualifiers"]) and "over" not in qd and "stat" not in qd:
                err.append(f"{i}: {r['quantity']} without over= (what it is averaged over; P5)")
            if r["quantity"] in ("composition", "mass_gain", "porosity") and r["type"] != "cited" and "relative_to" not in qd:
                err.append(f"{i}: {r['quantity']} without relative_to= (what it is a fraction of; P4)")
            if (r["type"] != "claim" and r["value"] and not r["censor"] and "stat" not in qd
                    and re.search(r"\b(down to|up to|at most|as low as|as high as)\b", r["statement"])):
                err.append(f"{i}: '{re.search(r'(down to|up to|at most|as low as|as high as)', r['statement']).group(1)}' stored as a plain value (a bound or a stat=minimum/maximum; P12)")
            if r["value_min"] and r["value_max"]:                                # a stored range is a range the statement prints (P14)
                lo, hi = C.num(r["value_min"]), C.num(r["value_max"])
                if not any(abs(a - lo) <= 0.01 * abs(lo or 1) and abs(b - hi) <= 0.01 * abs(hi or 1) for a, b in C.parse_ranges(r["statement"] + " " + r["label_as_printed"])):
                    err.append(f"{i}: range {r['value_min']}–{r['value_max']} is not a range its statement prints (P14)")
            if r["type"] == "setting" and r["quantity"] == "film_thickness" and qd.get("kind") != "target":
                err.append(f"{i}: a film thickness setting that is not a target (thickness is a result; P18)")
            if r["quantity"] == "phase" and (r["value_text"] not in L.PHASE_VALUES or "species" not in qd):
                err.append(f"{i}: phase without species= or with value_text not in lists.PHASE_VALUES (P15)")
            if r["uncertainty"] and r["uncertainty_kind"] not in L.UNCERTAINTY_KINDS:
                err.append(f"{i}: uncertainty {r['uncertainty']} without a kind from lists.UNCERTAINTY_KINDS (P2)")
            if r["uncertainty"] and not re.fullmatch(r"\d+(\.\d+)?(e-?\d+)?", r["uncertainty"]):
                err.append(f"{i}: uncertainty {r['uncertainty']!r} is not a number (P2)")
            if "stat" in qd and not ("between" in qd and "n" in qd):
                err.append(f"{i}: a spread fact (stat=) without between= and n= (P1)")
            if r["type"] == "observation" and r["quantity"] in L.SETTING_QUANTITIES and "stat" not in qd:
                err.append(f"{i}: observation with the setting quantity {r['quantity']} (lists.SETTING_QUANTITIES)")
            if (r["type"] == "observation" and nt == "activity" and nk == "measurement" and R[R[n]["parent"]]["type"] == "paper"
                    and r["quantity"] not in ("", "other")):
                err.append(f"{i}: {r['quantity']} measured on the paper's method activity {n}, not on an entity")
            if r["type"] == "setting" and nt not in ("activity", "entity"):
                err.append(f"{i}: setting under {n or 'nothing'} ({nt}), not under an activity or an entity (a comparison holds no setting)")
    return err


NUMBER_LIST = re.compile(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?(?:\s*(?:[,/\u2013-]|,?\s*and)\s*\d+(?:\.\d+)?)*")


def label_values(label):
    """The numbers a label states as values: each number, or list of numbers (10-50, 120/160, 2, 4 and 8), that a unit follows."""
    out = []
    for m in NUMBER_LIST.finditer(label or ""):
        unit = re.match(r"\s*([^\s\d,;:()]+)", label[m.end():])
        if unit and unit.group(1).lower() != "and":
            out += [float(v) for v in re.findall(r"\d+(?:\.\d+)?", m.group())]
    return out


def tree_summary(rows):
    R = {r["fact_id"]: r for r in rows}
    root = next(r["fact_id"] for r in rows if r["type"] == "paper")
    under = [r for r in rows if r.get("parent") == root and "#" in r["fact_id"]]
    runs = collections.Counter(r["kind"] for r in rows if r["type"] == "activity")
    return dict(tree_rows=collections.Counter(r["type"] for r in rows if "#" not in r["fact_id"]), runs=dict(runs), comparisons=dict(collections.Counter(r["kind"] for r in rows if r["type"] == "comparison")),
                under_paper=collections.Counter(r["type"] for r in under),
                claims_unlinked=sum(1 for r in rows if r["type"] == "claim" and not r.get("links")))


def summary(els, facts, cov):
    st = {c["element_id"]: c["status"] for c in cov}
    kinds = collections.Counter((els[e]["kind"], st.get(e, "?")) for e in els)
    by_el = collections.defaultdict(list)
    for f in facts:
        for e in f["evidence"].split(";"):
            by_el[e].append(f)
    panels = collections.Counter()
    for e, r in els.items():
        if r["kind"] != "panel":
            continue
        fs = by_el.get(e, [])
        panels["with points" if any(f["points_ref"] for f in fs) else "stated values only" if any(f["value"] or f["value_min"] or f["value_max"] for f in fs)
               else "facts, no values" if fs else "no knowledge"] += 1
    nn = sum(int(c["n_numbers"] or 0) for c in cov if els[c["element_id"]]["kind"] in ("paragraph", "abstract"))
    nr = sum(int(c["n_numbers_reached"] or 0) for c in cov if els[c["element_id"]]["kind"] in ("paragraph", "abstract"))
    tn = sum(int(c["n_numbers"] or 0) for c in cov if els[c["element_id"]]["kind"] == "table_cell")
    tr = sum(int(c["n_numbers_reached"] or 0) for c in cov if els[c["element_id"]]["kind"] == "table_cell")
    return dict(elements={k: {s: n for (k2, s), n in kinds.items() if k2 == k} for k in sorted({k for k, _ in kinds})},
                facts=dict(collections.Counter(f["type"] for f in facts)), n_facts=len(facts), panels=dict(panels),
                text_numbers=(nr, nn), table_numbers=(tr, tn),
                quantity_other=sum(f["quantity"] == "other" for f in facts))


def check_derived():
    """P7: the query layer never derives a quantity an entity already has as a measured or stated value, and no derivation feeds
    back into its own inputs (no derived id twice in a chain)."""
    import query as Q
    err = []
    for k, T in Q.TREES.items():
        for e in T.entities():
            for did in L.DERIVED:
                d = Q.derive(T, e, did)
                if "error" in d:
                    continue
                if Q.has_own(T, e, did):
                    err.append(f"{e}: {did} derived although the entity has it (P7)")
                if len(d["chain"]) != len(set(d["chain"])):
                    err.append(f"{e}: {did} derivation feeds back: {' -> '.join(d['chain'])} (P7)")
            for o in Q.same_experiment(T, e):
                if Q.role(T, o) != Q.role(T, e):
                    err.append(f"{e}: same experiment as {o}, an entity of another role (P21)")
        for c in T.comps:
            if len({Q.role(T, m) for m in T.member_entities(c)}) > 1:
                err.append(f"{c['fact_id']}: members of different roles (P21)")
    return err


def check_user(all_ids):
    rows = rd(HERE / "user.facts.csv")
    err = []
    if not rows:
        return ["no user.facts.csv (run user_facts.py)"]
    if list(rows[0].keys()) != C.FIELDS:
        err.append("user.facts.csv: columns differ from facts.FIELDS")
    ids = [r["fact_id"] for r in rows]
    for r in rows:
        i = r["fact_id"]
        bad = lambda m: err.append(f"{i}: {m}")
        if not i.startswith("user:") or ids.count(i) > 1:
            bad("id not unique or not user:<name>")
        if r["author"] != "user":
            bad(f"author {r['author']!r}")
        if r["type"] not in L.TYPES:
            bad(f"type {r['type']}")
        if r["quantity"] and r["quantity"] not in L.QUANTITIES:
            bad(f"quantity {r['quantity']}")
        for q in L.qualifiers_ok(r["qualifiers"]):
            bad(f"qualifier {q}")
        if not r["statement"].strip() or "\n" in r["statement"]:
            bad("statement empty or not one line")
        if r["type"] == "claim" and not r["links"]:
            bad("claim without links")
        if r["type"] == "claim" and r["stance"] not in L.STANCES:
            bad(f"claim stance {r['stance']!r}")
        for t in L.variables_ok(r["cause"]) + L.variables_ok(r["effect"]):
            bad(f"variable {t}")
        for l in filter(None, r["links"].split(";")):
            if l not in all_ids and l not in ids:
                bad(f"link {l} does not exist")
        if r["type"] == "bridge":
            if len([l for l in r["links"].split(";") if l]) != 2:
                bad("bridge without exactly two links")
            if not r["value_text"] or any(t not in L.QUANTITIES or t == "other" for t in re.split(r"[*/]", r["value_text"])):
                bad(f"bridge factor {r['value_text']!r} is not a quotient of quantity ids")
    return err


def check_cases():
    rows = rd(HERE / "paper_case.csv")
    left = [(k, r["paper_id"]) for r in rows for k in (f"c{i}" for i in range(1, 14)) if r.get(k, "").startswith("candidate")]
    return [f"paper_case.csv: {k} {p} is a candidate not resolved" for k, p in left] + ([] if rows else ["no paper_case.csv"])


if __name__ == "__main__":
    bad = 0
    err = check_cases()
    print(f"== cases: {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    all_ids = {r["fact_id"] for pid in KEYS for r in rd(HERE / f"{pid}.facts.csv")}
    err = check_user(all_ids)
    print(f"== user facts: {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_derived()
    print(f"== derived values (query layer): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    for pid, k in KEYS.items():
        err, s = check(pid)
        print(f"== {k} {pid}: {'OK' if not err else f'{len(err)} problems'}")
        for e in err[:40]:
            print("  ", e)
        if s:
            print("   elements:", s["elements"])
            print("   facts:", s["n_facts"], s["facts"], "| quantity other:", s["quantity_other"])
            if s.get("tree"):
                t = s["tree"]
                print("   tree rows:", dict(t["tree_rows"]), "| activities:", t["runs"], "| comparisons:", t["comparisons"], "| facts directly under the paper:",
                      sum(t["under_paper"].values()), dict(t["under_paper"]), "| claims without links:", t["claims_unlinked"])
            print("   panels:", s["panels"])
            for lab, (r, n) in (("text", s["text_numbers"]), ("table", s["table_numbers"])):
                print(f"   numbers in {lab} reaching a fact: {r}/{n} ({100 * r / max(n, 1):.0f}%)")
        bad += bool(err)
    sys.exit(1 if bad else 0)
