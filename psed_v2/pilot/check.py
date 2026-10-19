#!/usr/bin/env python3
"""The one check of the pilot; prints the summary and exits 1 on any failure.

    python3 psed_v2/pilot/check.py

Facts (per paper, <paper_id>.*): fact ids unique; evidence ids and inputs resolve; vocabularies (type, quantity, qualifiers, data_kind, method,
censor; material and structure value_texts from lists.MATERIALS and STRUCTURES; a claim's stance from lists.STANCES; cause and effect quantity ids or mechanism tokens); a quantity of "other" carries label_as_printed; a value, value_text or points_ref has a quantity, a value or points_ref
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
            bad(f"variable {t!r} is not an entry id or a mechanism id (P54)")
        if f["type"] == "claim" and f["cause"] and f["effect"] and f["relation"] not in L.RELATIONS:
            bad(f"claim with a cause and an effect without a relation from lists.RELATIONS (P54)")
        if f["type"] == "claim" and f["relation"] and f["relation"] not in L.RELATIONS:
            bad(f"relation {f['relation']!r} not in lists.RELATIONS (P54)")
        if f["quantity"] and any(q not in L.QUANTITIES for q in (f["quantity"].split(";") if f["type"] == "caveat" else [f["quantity"]])):
            bad(f"quantity {f['quantity']}")
        if f["quantity"] == "other" and not f["label_as_printed"]:
            bad("quantity other without label_as_printed")
        if f["quantity"] == "material" and f["value_text"] not in L.MATERIALS:
            bad(f"material {f['value_text']!r} not in lists.MATERIALS")
        if f["quantity"] == "structure" and f["value_text"] not in L.STRUCTURES:
            bad(f"structure {f['value_text']!r} not in lists.STRUCTURES")
        if f["quantity"] == "substrate" and f["type"] != "cited" and f["value_text"] not in L.MATERIALS:
            bad(f"substrate {f['value_text']!r} is not a material species id (the growth surface; P50)")
        if f["quantity"] in ("reactant_A", "reactant_B") and f["value_text"] not in L.SPECIES:
            bad(f"{f['quantity']} {f['value_text']!r} is not a species id (P50)")
        if L.substance_scoped(f) and not ("species=" in f["qualifiers"] or "gas=" in f["qualifiers"]):
            bad(f"{f['quantity']} setting without species= or gas=: which substance it is about lives only in prose (P50)")
        for q in L.qualifiers_ok(f["qualifiers"]):
            bad(f"qualifier {q}")
        if f["data_kind"] and f["data_kind"] not in L.KINDS:
            bad(f"kind {f['data_kind']!r} is not in the kind vocabulary (Sec. 18.5; P57)")
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
            bad("points_ref in a facts file: figure points enter the knowledge base only through kb/figures_import.py (P88)")
        if f["type"] == "definition" and f["quantity"] and not f.get("term"):
            bad("a definition that names a quantity has no term (the symbol or phrase as printed; P89)")
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
    for p in sorted(set() - used_points):
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
            for dk in (set(L.DEFAULT_DEFINITION.get(r["quantity"], {})) | ({"over"} if "x=growth_per_cycle" in r["qualifiers"] else set())):
                if dk not in qd and "stat" not in qd:                             # a quantity with a default definition states its definition key (P5, P4)
                    err.append(f"{i}: {r['quantity']} without {dk}= (its definition key; P5)")
            if r["quantity"] in ("phase_fraction", "mass_gain", "porosity", "plasma_gas_ratio") and r["type"] != "cited" and "relative_to" not in qd:
                err.append(f"{i}: {r['quantity']} without relative_to= (what it is a fraction of; P4)")
            if r["quantity"] == "element_ratio" and not ("element" in qd and "reference_element" in qd):
                err.append(f"{i}: element_ratio without element= and reference_element= (atoms of what per atom of what; P52)")
            if r["quantity"] == "element_fraction" and "element" not in qd:
                err.append(f"{i}: element_fraction without element= (P52)")
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
        ids = [f for f in T.rows if f["type"] == "identity"]
        for e in T.entities():
            for o in Q.same_experiment(T, e):
                if e < o and e not in T.chain(o) and o not in T.chain(e) and not any({e, o} <= set(f["links"].split(";")) for f in ids):
                    err.append(f"{e} and {o}: equal conditions and no identity fact (same, different or not stated; P23)")
        for f in ids:
            if f["kind"] not in L.IDENTITY_KINDS or len(f["links"].split(";")) < 2:
                err.append(f"{f['fact_id']}: identity kind {f['kind']!r} or fewer than two entities (P23)")
        for c in T.comps:
            if len({Q.role(T, m) for m in T.member_entities(c)}) > 1:
                err.append(f"{c['fact_id']}: members of different roles (P21)")
    for k, T in Q.TREES.items():                                                # P45: a caveat qualifies some value, setting or entity
        for c in [r for r in T.rows if r["type"] == "caveat"]:
            if not Q.caveat_targets(T, c):
                err.append(f"{c['fact_id']}: caveat qualifies nothing")
    return err


def check_figures_import():
    """P84-P87: for every paper of the knowledge base with a kb/<id>.figures.json: every data panel whose verdict is ok is imported or
    listed in ontology/unmapped.csv (or kb/import_panels.csv) with a reason; every curve's axes resolve to entries whose dimension is
    the unit's (units.yaml); every set from a panel has its varied condition resolved (a replicate set none); the counts of
    kb/import_report.csv equal the records on disk; the kinds and bases of the records are in the ontology's tables."""
    import query as Q, yaml
    err = []
    KB = HERE.parent / "kb"
    units = yaml.safe_load((HERE.parent / "ontology" / "units.yaml").read_text(encoding="utf-8"))["units"]
    dim = {}
    for u in units:
        dim[u["symbol"]] = u["dimension"]
    report = {r["paper_id"]: r for r in rd(KB / "import_report.csv")}
    panels = rd(KB / "import_panels.csv")
    unm = rd(HERE.parent / "ontology" / "unmapped.csv")
    n_curves = n_sets = n_panels = 0
    for k, T in Q.TREES.items():
        pid = Q.KEY[k]
        p = KB / f"{pid}.figures.json"
        if not p.exists():
            err.append(f"{k}: no kb/{pid}.figures.json (run kb/figures_import.py) (P84)"); continue
        F = json.loads(p.read_text(encoding="utf-8"))
        for row in [x for x in panels if x["paper"] == pid and x["verdict"] == "ok"]:
            n_panels += 1
            if row["outcome"] == "imported":
                continue
            listed = any(u["paper"] == pid and u["figure"] == row["figure"] and u["panel"] == row["panel"] for u in unm) or row["reason"].startswith("flag")
            if not listed:
                err.append(f"{k} Fig. {row['figure']}{row['panel']}: verdict ok, not imported and not in unmapped.csv ({row['reason']}) (P84)")
        for c in F["curves"]:
            n_curves += 1
            for ax in ("x", "y"):
                q, u = c[ax]["quantity"], c[ax]["unit"]
                e = L.ENTRIES.get(q)
                if not e:
                    err.append(f"{c['id']}: {ax} quantity {q!r} is no entry (P84a)"); continue
                if u not in dim:
                    err.append(f"{c['id']}: {ax} unit {u!r} is not in units.yaml (P84b)"); continue
                if dim[u] != e.get("dimension") and not (e.get("dimension") == "signal" and dim[u] in ("signal", "dimensionless")):
                    err.append(f"{c['id']}: {ax} unit {u} ({dim[u]}) against {q} ({e.get('dimension')}) (P84b)")
            if c["kind"] not in L.KINDS:
                err.append(f"{c['id']}: kind {c['kind']} not in the kind table (P87)")
            if c["kind"] == "read_from_figure" and (c.get("uncertainty") or {}).get("basis") not in L.BASES:
                err.append(f"{c['id']}: basis {(c.get('uncertainty') or {}).get('basis')!r} not in the basis table (P87)")
        for st in F["sets"]:
            n_sets += 1
            if st["kind"] == "replicate":
                continue
            for q in st["varied"].split(";"):
                if q not in L.ENTRIES:
                    err.append(f"{st['id']}: varied condition {q!r} unresolved (P85)")
        for v in F["values"]:
            if v.get("quantity") and v["basis"] not in L.BASES:
                err.append(f"{v['id']}: basis {v['basis']!r} not in the basis table (P87)")
        for d in F["derived"]:                                                   # P91b: a derived value carries its quantity's canonical unit
            if d["unit"] != L.ENTRIES.get(d["quantity"], {}).get("unit", d["unit"]):
                err.append(f"{d['id']}: unit {d['unit']!r} is not the canonical unit {L.ENTRIES.get(d['quantity'], {}).get('unit')!r} of {d['quantity']} (P91b)")
        r = report.get(pid)
        if not r:
            err.append(f"{k}: no row in kb/import_report.csv (P84)")
        else:
            disk = dict(curves=len(F["curves"]), cells=sum(1 for v in F["values"] if v["kind"] == "cell"), peaks=sum(1 for v in F["values"] if v["kind"] == "peak"), sets=len(F["sets"]),
                        derived=len(F["derived"]), inventory_records=len(F["inventory"]))
            for col, n in disk.items():
                if int(r[col]) != n:
                    err.append(f"{k}: import_report.csv {col} {r[col]} against {n} records on disk (P84)")
    print(f"== figures import (P84-P87): {n_panels} ok panels, {n_curves} curves, {n_sets} sets over {len(Q.TREES)} papers; import report, unmapped.csv and units checked")
    return err


def check_figure_derived():
    """P86: the cross-check of every scalar derived from a curve against a stated value of the same quantity under the same conditions in
    the same paper: a stated fact of the quantity (same qualifiers) that cites the panel (figure_ref) and names the series label; a
    difference over max(10 % of the stated value, 2 % of the axis range) is a problem, listed in kb/problems.txt (a finding about the
    data, not a failure of the build)."""
    import query as Q
    probs, n_checked, n_pairs = [], 0, 0
    for k, T in Q.TREES.items():
        F = getattr(T, "figures", None)
        if not F:
            continue
        for d in F["derived"]:
            n_checked += 1
            c = T.curves[d["source"]]
            panel = f"fig{d['figure']}{d['panel']}"
            conds = {q: cc for q, cc in (c.get("conditions") or {}).items() if cc.get("value") is not None}
            def same_conditions(e):                                             # every numeric condition of the curve that the entity states agrees within 1 %
                vt, n_hit = T.vector(e), 0
                for q, cc in conds.items():
                    fs = next((fs for kk, fs in vt.items() if kk.split("{")[0] == q), None)
                    if not fs:
                        continue
                    v = Q.val(fs[0])
                    if v is None:
                        return False
                    try:
                        v = L.convert(v, fs[0]["unit"], cc["unit"]) if fs[0]["unit"] and cc.get("unit") and fs[0]["unit"] != cc["unit"] else v
                    except (ValueError, KeyError):
                        return False
                    if abs(v - cc["value"]) > 0.01 * max(abs(cc["value"]), 1e-12):
                        return False
                    n_hit += 1
                return n_hit >= 1
            anchored = [e for e in (T.byid[c["id"]]["links"] or "").split(";") if e]     # P88: the entity the curve is bound to, else every entity with the same conditions
            same = (lambda e: e in anchored) if anchored else same_conditions
            stated = [f for f in T.rows if "#" in f["fact_id"] and f["quantity"] == d["quantity"] and f["type"] in ("observation", "derived", "setting")
                      and f["data_kind"] not in ("computed_by_kb",) and f["value"] and not f["points_ref"] and f["fact_id"] not in T.curves
                      and set(p for p in f["qualifiers"].split(";") if p and p.split("=")[0] in ("position", "level")) == set(p for p in d.get("qualifiers", "").split(";") if p)
                      and T.ent_of(f["fact_id"]) and same(T.ent_of(f["fact_id"]))]
            for f in stated:
                n_pairs += 1
                sv = C.num(f["value"])
                if sv is None:
                    continue
                try:
                    sv = L.convert(sv, f["unit"], d["unit"]) if f["unit"] and f["unit"] != d["unit"] else sv
                except (ValueError, KeyError):
                    continue
                axis = "y" if d["quantity"] == c["y"]["quantity"] else "x"
                vals = [p[1] if axis == "y" else p[0] for p in c["points"]]
                rng = (max(vals) - min(vals)) if vals else 0.0
                tol = max(0.1 * abs(sv), 0.02 * rng)
                if abs(d["value"] - sv) > tol:
                    probs.append(f"P86 {d['id']} ({d['method']}): derived {Q.g(d['value'], 4)} {d['unit']} against stated {f['value']} {f['unit']} [{f['fact_id']}]; tolerance {Q.g(tol, 3)} {d['unit']}")
    (HERE.parent / "kb" / "problems.txt").write_text("\n".join(probs) + ("\n" if probs else ""), encoding="utf-8")
    print(f"== figure derived (P86): {n_checked} derived scalars, {n_pairs} stated counterparts found, {len(probs)} outside tolerance (listed in kb/problems.txt, a finding, not a failure)")
    return []


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
        if r["quantity"] and r["type"] != "caveat" and r["quantity"] not in L.QUANTITIES:
            bad(f"quantity {r['quantity']}")
        for q in [q for alt in (r["qualifiers"].split("|") if r["type"] == "caveat" else [r["qualifiers"]]) for q in L.qualifiers_ok(alt)]:
            bad(f"qualifier {q}")                                                # a caveat's qualifiers may list alternatives (a|b)
        if not r["statement"].strip() or "\n" in r["statement"]:
            bad("statement empty or not one line")
        if r["type"] == "claim" and not r["links"]:
            bad("claim without links")
        if r["type"] == "claim" and r["stance"] not in L.STANCES:
            bad(f"claim stance {r['stance']!r}")
        for t in L.variables_ok(r["cause"]) + L.variables_ok(r["effect"]):
            bad(f"variable {t!r} is not an entry id or a mechanism id (P54)")
        if r["type"] == "claim" and r["cause"] and r["effect"] and r["relation"] not in L.RELATIONS:
            bad("claim with a cause and an effect without a relation from lists.RELATIONS (P54)")
        for l in filter(None, r["links"].split(";")):
            if l not in all_ids and l not in ids:
                bad(f"link {l} does not exist")
        if r.get("sized_by"):                                                    # P46: a claim sized by facts with a value
            if r["type"] != "claim":
                bad("sized_by on a row that is not a claim")
            for l in r["sized_by"].split(";"):
                if l not in ids:
                    bad(f"sized_by {l} does not exist")
        if r["type"] == "caveat":                                                # P45
            if not r["links"]:
                bad("caveat without links")
            if any(q not in L.QUANTITIES for q in filter(None, r["quantity"].split(";"))):
                bad(f"caveat quantity {r['quantity']}")
            if len(r["statement"]) > 200:
                bad("caveat statement over 200 characters")
        if r["type"] == "bridge":
            if len([l for l in r["links"].split(";") if l]) != 2:
                bad("bridge without exactly two links")
            if not r["value_text"] or any(t not in L.QUANTITIES or t == "other" for t in re.split(r"[*/]", r["value_text"])):
                bad(f"bridge factor {r['value_text']!r} is not a quotient of quantity ids")
    return err


def check_vocabulary():
    """P49: the ontology is the one vocabulary source. vocab.py is what export.py generates from it now; every quantity id, method
    id, material and structure value, qualifier key and curve abscissa used in the facts of the three papers and the user file is in
    the generated vocabulary (a pilot id still to absorb is in it provisionally and is counted); the hand tables of lists.py key
    only vocabulary ids."""
    import subprocess
    err = []
    r = subprocess.run([sys.executable, str(HERE.parent / "ontology" / "export.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        err.append(r.stdout.strip() or "vocab.py stale")
    used = collections.defaultdict(set)
    for pid in list(KEYS) + ["user"]:
        for f in rd(HERE / (f"{pid}.facts.csv" if pid != "user" else "user.facts.csv")):
            for q in filter(None, f["quantity"].split(";")):
                used["quantity"].add(q)
            if f["method"]:
                used["method"].add(f["method"])
            if f["quantity"] == "material" and f["value_text"]:
                used["material"].add(f["value_text"])
            if f["quantity"] == "structure" and f["value_text"]:
                used["structure"].add(f["value_text"])
            for alt in f["qualifiers"].split("|"):
                for part in filter(None, alt.split(";")):
                    k, _, v = part.partition("=")
                    used["qualifier key"].add(k)
                    if k == "x":
                        used["quantity"].add(v)
            for t_ in (f["cause"] + ";" + f["effect"]).split(";"):
                if t_ and t_ not in L.MECHANISMS:
                    used["quantity"].add(t_)
    voc = {"quantity": set(L.QUANTITIES), "method": set(L.METHODS), "material": set(L.MATERIALS), "structure": set(L.STRUCTURES), "qualifier key": set(L.QUALIFIERS)}
    for k, vs in used.items():
        for v in sorted(vs - voc[k]):
            err.append(f"{k} {v!r} used in the data is not in the generated vocabulary (vocab.py)")
    absorbed = used["quantity"] & set(L.TO_ABSORB)
    print(f"== vocabulary: {len(used['quantity'])} quantity ids, {len(used['method'])} methods, {len(used['material'])} materials, {len(used['structure'])} structures, "
          f"{len(used['qualifier key'])} qualifier keys in use; {len(L.TO_ABSORB)} pilot ids still to absorb ({len(absorbed)} in use); "
          f"materials to absorb {L.TO_ABSORB_VALUES['material']}, structures {L.TO_ABSORB_VALUES['structure']}")
    return err


def check_mechanisms():
    """P82: a mechanism is not a quantity: no mechanism entry carries a unit, and no fact of the data uses a mechanism id as its quantity."""
    import query as Q
    err = [f"{m}: a mechanism entry with a unit {L.ENTRIES[m].get('unit')!r} (P82)" for m in L.MECHANISMS if L.ENTRIES.get(m, {}).get("unit")]
    err += [f"{f['fact_id']}: a value under the mechanism id {f['quantity']} (P82)" for T in Q.TREES.values() for f in T.rows if f["quantity"] in L.MECHANISMS]
    print(f"== mechanisms (P82): {len(L.MECHANISMS)} mechanisms, none with a unit or a value")
    return err


def check_claims():
    """P54: every claim's cause and effect are entry ids or mechanism ids (variables_ok, above); here the counts: claims, free
    strings (always 0 once variables_ok holds), mechanisms named, and mechanisms named by claims of two or more papers."""
    used = collections.defaultdict(set)
    n = 0
    for pid in KEYS:
        for f in rd(HERE / f"{pid}.facts.csv"):
            if f["type"] == "claim":
                n += 1
                for t in (f["cause"] + ";" + f["effect"]).split(";"):
                    if t in L.MECHANISMS:
                        used[t].add(KEYS[pid])
    shared = sorted(m for m, ps in used.items() if len(ps) >= 2)
    print(f"== claims (P54): {n} claims; {len(used)} mechanisms named; {len(shared)} named by two or more papers: {', '.join(shared)}")
    return []


def check_search():
    """P64: the tiered ranking on the stored probes (search_probes.csv): the first hit's type (and id, when given), and a value or claim
    before any record of the types named in value_before."""
    import query as Q
    err = []
    for p in rd(HERE / "search_probes.csv"):
        hits = Q.search(p["words"])
        if not hits:
            err.append(f"search {p['words']!r}: no hits (P64)"); continue
        if hits[0]["type"] != p["first_type"] or (p["first_id"] and hits[0]["id"] != p["first_id"]):
            err.append(f"search {p['words']!r}: first hit {hits[0]['type']} {hits[0]['id']}, expected {p['first_type']} {p['first_id']} (P64)")
        first_val = next((n for n, h in enumerate(hits) if h["type"] in ("value", "claim")), None)
        for t in p["value_before"].split(";"):
            n = next((n for n, h in enumerate(hits) if h["type"] == t), None)
            if first_val is not None and n is not None and n < first_val:
                err.append(f"search {p['words']!r}: a {t} ranks above the first value or claim (P64)")
    import tools
    for p in rd(HERE / "search_probes.csv"):                                    # P93: the cross-paper view: at most SEARCH_PAPERS paper lines, under 800 tokens
        hits = Q.search(p["words"])
        papers = {h["paper"] for h in hits if h["paper"]}
        lines, e = tools.run_tool("search", {"words": p["words"]})
        if e:
            err.append(f"search {p['words']!r}: {e} (P93)"); continue
        paper_lines = [i for i, t in lines if i in Q.TREES and not t.startswith("… ")]
        if len(paper_lines) != len(set(paper_lines)):
            err.append(f"search {p['words']!r}: a paper takes more than one line in the cross-paper view (P93)")
        if len(papers) >= 8 and len(paper_lines) > tools.SEARCH_PAPERS:
            err.append(f"search {p['words']!r}: {len(paper_lines)} paper lines for {len(papers)} papers hit, at most {tools.SEARCH_PAPERS} (P93)")
        if sum(len(t) for _, t in lines) // 4 > 800:
            err.append(f"search {p['words']!r}: the cross-paper view takes {sum(len(t) for _, t in lines) // 4} tokens, over 800 (P93)")
    kinds = {}                                                                  # P84e: one probe per record kind any index can return: the tool renders every hit, one line each, no exception
    for r in Q.search_records():
        kinds.setdefault(r["type"], r)
    for t, r in sorted(kinds.items()):
        words = " ".join(w for w in Q.tokens(r["line"])[:6] if len(w) > 2) or r["id"]
        args = {"words": words, "paper": r["paper"]} if r["paper"] else {"words": words}
        lines, offset, e = [], 0, ""
        try:
            for _ in range(40):                                                 # every page: a tier-3 kind can sit far down the ranking
                page, e = tools.run_tool("search", dict(args, offset=offset) if offset else args)
                if e:
                    break
                lines += page
                more = next((x for i, x in page if i == "more"), "")
                if not more:
                    break
                offset = int(more.split("offset=")[1])
        except Exception as ex:
            err.append(f"search for a {t} record ({r['id']}): {type(ex).__name__}: {ex} (P84e)"); continue
        if e:
            err.append(f"search for a {t} record ({r['id']}, words {words!r}): {e} (P84e)"); continue
        ids = {i for i, _ in lines}
        hits = Q.search(words, r["paper"] or None)
        grouped = t in ("value", "setting") and any(x.startswith(f"{t}s of ") for _, x in lines)   # values and settings render as one grouped line per paper and quantity
        if not grouped and not any(h["id"] in ids for h in hits if h["type"] == t):
            err.append(f"search for a {t} record ({r['id']}): no hit of that kind rendered as a line (P84e)")
    print(f"== search (P64): {len(rd(HERE / 'search_probes.csv'))} probes, tiers 1 concept / 2 claims, values, sets / 3 the rest; check_search: {len(kinds)} record kinds probed, each hit rendered as one line (P84e)")
    return err


def check_records():
    """P62: no value record with empty text reaches a value listing: every result record of every experiment and every record a
    values() group returns has printable text (a curve reads 'curve, N points'); the curve records are counted."""
    import query as Q
    err, curves, n = [], 0, 0
    for k, T in Q.TREES.items():
        for e in Q.experiments(T):
            for key, x in Q.result_records(T, e).items():
                r = x["record"]; n += 1
                if not r.get("text"):
                    err.append(f"{e} {key}: a value record with empty text reaches the listing (P62)")
                elif r["text"].startswith("curve, "):
                    curves += 1
    print(f"== records (P62): {n} result records on the experiments, {curves} of them curve references, none empty")
    return err


def check_bases_sec19():
    """P60 (Sec. 19): every nonempty uncertainty and every spread fact carries a basis from the closed list, or the paper does not say
    (uncertainty_kind not_stated) and the fact is listed here; counts per basis."""
    err, counts, empty = [], collections.Counter(), []
    for pid in list(KEYS) + ["user"]:
        for f in rd(HERE / (f"{pid}.facts.csv" if pid != "user" else "user.facts.csv")):
            q = dict(p.split("=", 1) for p in f["qualifiers"].split(";") if "=" in p)
            if "#" not in f["fact_id"] or not (f["uncertainty"] or "stat" in q):
                continue
            b = f.get("basis", "")
            if b and b not in L.BASES:
                err.append(f"{f['fact_id']}: basis {b!r} outside the Sec. 19 list (P60)")
            elif b:
                counts[b] += 1
            elif f["uncertainty_kind"] == "not_stated" or (not f["uncertainty_kind"] and "stat" in q):
                empty.append(f"{f['fact_id']} ({f['evidence'].split(';')[0]})")
            else:
                err.append(f"{f['fact_id']}: uncertainty without a basis although its kind is {f['uncertainty_kind']!r} (P60)")
    print(f"== uncertainty bases (P60): " + ", ".join(f"{b} {n}" for b, n in sorted(counts.items())) + f"; no basis (the paper does not say) {len(empty)}: " + ", ".join(empty))
    return err


DEICTIC = ("computed here", "derived here", "calculated here", "computed by us", "our calculation", "estimated here")   # tool wording, never from the tables


def check_structure():
    """P78: every specimen and input entity carries structure_class = the class (lists.STRUCTURE_CLASS) of its structure, a class of
    the ontology's taxonomy (lists.STRUCTURE_CLASSES); a model run carries none. No other[...] record that the re-keying rule covers
    remains (facts.slot_for over the records that describe the structure); the residual free labels with a length or area-per-mass
    unit are listed for the report. A slot categorical's value is in its vocabulary (lists.CATEGORICAL_VALUES). In a paper with a
    porous body, body_thickness agrees with feature_depth × entry_sides within the stated uncertainty (else half of the last digit)."""
    import query as Q
    err, resid, n_ent, n_slot, checked = [], [], 0, 0, 0
    slots = {x for c in L.STRUCTURE_CLASSES.values() for x in c["slots"]}
    for k, T in Q.TREES.items():
        byid = T.byid
        for r in T.rows:
            if r["type"] == "entity":
                sc = dict(p.split("=", 1) for p in r["qualifiers"].split(";") if "=" in p).get("structure_class", "")
                st = T.vector(r["fact_id"]).get("structure")
                want = L.STRUCTURE_CLASS.get(st[0]["value_text"], "") if st else ""
                if Q.role(T, r["fact_id"]) in ("specimen", "input"):
                    n_ent += 1
                    if not sc or sc != want or sc not in L.STRUCTURE_CLASSES:
                        err.append(f"{r['fact_id']}: structure_class {sc!r}, its structure gives {want!r} (P78)")
                elif sc:
                    err.append(f"{r['fact_id']}: a model run with structure_class {sc!r} (P78)")
            if "#" not in r["fact_id"]:
                continue
            if r["quantity"] in slots and L.ENTRIES[r["quantity"]]["type"] == "categorical":
                n_slot += 1
                if r["value_text"] not in L.CATEGORICAL_VALUES.get(r["quantity"], [r["value_text"]]):
                    err.append(f"{r['fact_id']}: {r['quantity']} value {r['value_text']!r} not in its vocabulary (P78)")
            elif r["quantity"] in slots:
                n_slot += 1
            if r["quantity"] == "other":
                node = C._node_of(r["fact_id"], byid); n = byid.get(node, {})
                ent = node
                while ent in byid and byid[ent]["type"] not in ("entity", "paper", "cited", "comparison"):
                    ent = byid[ent]["parent"]
                describes = (byid.get(ent, {}).get("type") == "entity" and not C._made(ent, byid)) or n.get("type") == "cited" \
                    or (r["type"] == "setting" and (n.get("type") == "paper" or (n.get("type") == "activity" and n.get("kind") == "recipe")))
                if C.slot_for(r["label_as_printed"], r["unit"], describes):
                    err.append(f"{r['fact_id']}: other[{r['label_as_printed']}] names the slot {C.slot_for(r['label_as_printed'], r['unit'], describes)} but was not re-keyed (P78)")
                if L.UNIT_BASE.get(L.UNIT_ALIAS.get(r["unit"], r["unit"]), ("",))[0] in ("length", "area_per_mass"):
                    resid.append(f"{r['fact_id']} [{r['label_as_printed']}]")
        # the porous-body transform: body_thickness = feature_depth × entry_sides
        bt = [f for f in T.rows if f["quantity"] == "body_thickness" and f["value"]]
        sides = [f for f in T.rows if f["quantity"] == "entry_sides" and f["value_text"]]
        for b in bt:
            e = T.ent_of(b["fact_id"]) or next((x for x in T.chain(b["fact_id"]) if T.byid[x]["type"] == "activity"), None)
            vec = T.vector(e) if e else {}
            L_ = [g for kk, gs in vec.items() if kk.split("{")[0] == "feature_depth" for g in gs if g["value"]]
            if not L_:                                                          # no depth on the same entity or activity: nothing to pair (a membrane as made)
                continue
            if not sides:
                err.append(f"{b['fact_id']}: body_thickness and feature_depth without entry_sides to relate them (P78)"); continue
            n_sides = {"one": 1, "two": 2}[sides[0]["value_text"]]
            depth = L.convert(C.num(L_[0]["value"]), L_[0]["unit"], b["unit"])
            tol = C.num(b["uncertainty"]) if b["uncertainty"] else 0.5 * 10 ** -len(b["value"].split(".")[1]) if "." in b["value"] else 0.5
            tol += C.num(L_[0]["uncertainty"]) * n_sides if L_[0]["uncertainty"] else 0
            checked += 1
            if abs(C.num(b["value"]) - depth * n_sides) > tol + 1e-9:
                err.append(f"{b['fact_id']}: body_thickness {b['value']} {b['unit']} against feature_depth × {n_sides} = {depth * n_sides:g} {b['unit']} (P78)")
    print(f"== structure (P78): {len(L.STRUCTURE_CLASSES)} structure classes, {len(slots)} slot entries; {n_ent} specimen and input entities with a structure_class; "
          f"{n_slot} slot records; {checked} body_thickness values checked against feature_depth × entry_sides; residual free labels with a length or area-per-mass unit: {len(resid)}")
    for x in resid:
        print("   ", x)
    return err


def check_cards():
    """P81: for every entry and paper, the card's per-paper numbers (concept.per_paper) equal the counts computed directly from the page
    data: value records (D sources[*].values, by fact id and the tree's home), settings, claims (D claims' cause and effect) and derived
    records (D details' results computed by this knowledge base); 'not studied in: p' never appears for an (entry, paper) with any
    record or with every input of a transform present (concept.derivable)."""
    import concept as CN, query as Q
    err, n_pairs, n_lines = [], 0, 0
    page = HERE / "reports" / "pilot.html"
    if not page.exists():
        print("== cards (P81): reports/pilot.html not built, the page comparison skipped"); return err
    D = json.loads(re.search(r"const D=(\{.*?\}), IM=", page.read_text(encoding="utf-8"), re.S).group(1))
    ref = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    seen = set()
    for src in D["sources"].values():
        for v in src["values"]:
            f = v.get("fact")
            if not f or f in seen:
                continue
            seen.add(f); k = f.split(":")[0]; T = Q.TREES[k]; row = T.byid[f]
            if row["quantity"] in L.ENTRIES:
                if row["type"] == "setting":
                    ref[row["quantity"]][k]["settings"] += 1
                else:
                    ref[row["quantity"]][k][CN.home_of(T, row)] += 1; ref[row["quantity"]][k]["values"] += 1
    for k, T in Q.TREES.items():                                                 # cited works' values and curves are not in the page's sources
        for f in T.rows:
            if "#" in f["fact_id"] and f["fact_id"] not in seen and f["quantity"] in L.ENTRIES and (f["type"] == "cited" or (f["type"] in Q.RESULT_TYPES and f["points_ref"] and not Q.text_of(f))):
                ref[f["quantity"]][k][CN.home_of(T, f)] += 1; ref[f["quantity"]][k]["values"] += 1
    for q in list(ref):                                                          # P86: a scalar derived from a curve (kind computed_by_kb) is a derived record, never the paper's value
        for k, T in Q.TREES.items():
            for f in T.rows:
                if "#" in f["fact_id"] and f["quantity"] == q and f["data_kind"] == "computed_by_kb" and f["fact_id"] in seen:
                    ref[q][k][CN.home_of(T, f)] -= 1; ref[q][k]["values"] -= 1; ref[q][k]["derived"] += 1
    for c in D["claims"]:                                                        # the page gives a claim's cause and effect in words; its ids come from the claim's row
        k = c["id"].split(":")[0]
        if k in Q.TREES and c["id"] in Q.TREES[k].byid:
            row = Q.TREES[k].byid[c["id"]]
            for t in (row["cause"] + ";" + row["effect"]).split(";"):
                if t:
                    ref[t][k]["claims"] += 1
    for i, d in D["details"].items():
        for r in d.get("results", []):
            if (r.get("record") or {}).get("kind") == "computed_by_kb" and d.get("paper") in Q.TREES:
                ref[r["key"].split("{")[0].split("[")[0]][d["paper"]]["derived"] += 1
    for q in sorted(L.ENTRIES):
        if L.ENTRIES[q]["type"] not in ("quantity", "categorical") or L.ENTRIES[q].get("replaced_by"):
            continue
        line = CN.per_paper([q]); n_lines += 1
        for k in Q.TREES:
            n_pairs += 1
            d = ref[q][k]
            m = re.search(rf"(?:^|; ){k} (.*?)(?:;|$| · )", line)
            seg = m.group(1) if m else ""
            got = {x: int(n) for n, x in re.findall(r"(\d+) (values|settings|claims|mentions)", seg)}
            got["derived"] = int(re.search(r"derived (\d+)", seg).group(1)) if re.search(r"derived (\d+)", seg) else 0
            homes = {h: int(n) for h, n in re.findall(r"(specimen|input|aggregate|set-level|paper|cited) (\d+)", seg)}
            for x in ("values", "settings", "claims", "derived"):
                if got.get(x, 0) != d.get(x, 0):
                    err.append(f"card {q} / {k}: {x} {got.get(x, 0)} on the card, {d.get(x, 0)} in the page data (P81)")
            for h in CN.HOMES:
                if homes.get(h, 0) != d.get(h, 0):
                    err.append(f"card {q} / {k}: {h} {homes.get(h, 0)} on the card, {d.get(h, 0)} in the page data (P81)")
            absent = re.search(r"not studied in: ([^·]*)$", line)
            if absent and k in [x.strip() for x in absent.group(1).split(",")] and (any(d.values()) or CN.derivable(q, k)):
                err.append(f"card {q}: 'not studied in {k}' although the paper holds a record or every transform input (P81)")
    print(f"== cards (P81): {n_lines} concept cards, {n_pairs} (entry, paper) pairs against the page data; counts by home {', '.join(CN.HOMES)}, settings, claims, derived")
    return err


QUALIFIER_PHRASES = [                                                           # P105: (phrase, quantity id) — a qualifier phrase resolves to the quantity, that qualifier's counts first
    ("growth per cycle in the channel", "growth_per_cycle"), ("phase (metallic Mo)", "phase"), ("initial porosity", "porosity"), ("MoS2 crystallinity", "crystallinity"),
    ("thickness in the channel", "film_thickness"), ("penetration depth (50%)", "penetration_depth"), ("step coverage (bottom)", "step_coverage"), ("exposure (H2O)", "exposure"),
    ("partial pressure (TMA)", "partial_pressure"), ("initial sticking coefficient (TiCl4)", "initial_sticking_coefficient"), ("molar mass (N2)", "molar_mass"),
    ("source temperature (DEZ)", "source_temperature"), ("binding energy (Mo)", "binding_energy"), ("element fraction (Cl)", "element_fraction"), ("thickness (sidewall)", "film_thickness"),
    ("coated aspect ratio (front end)", "coated_aspect_ratio"), ("H2O exposure", "exposure"), ("TMA partial pressure", "partial_pressure"), ("sidewall thickness", "film_thickness"),
    ("front-end penetration depth", "penetration_depth"),
    # P111: a species or material in parentheses is a qualifier of the quantity (a data key that carries it, else the experiments of that material)
    ("initial sticking coefficient (TMA)", "initial_sticking_coefficient"), ("resistivity (MoS2)", "resistivity"), ("growth per cycle (ZnO)", "growth_per_cycle"),
    ("penetration depth (Al2O3)", "penetration_depth"), ("partial pressure (H2O)", "partial_pressure"), ("molar mass (TMA)", "molar_mass"),
    ("saturation density (H2O)", "saturation_density"), ("recombination probability (atomic O, Al2O3)", "recombination_probability"), ("film thickness (ZnO)", "film_thickness"),
    ("exposure (DEZ)", "exposure")]
SPECIES_PHRASES = QUALIFIER_PHRASES[20:]
MISSES = [("concept", {"words": "zzz qqq"}), ("concept", {"words": "banana curvature"}), ("values", {"result": "no such result"}),
          ("values", {"result": "growth per cycle", "paper": "Mattinen"}), ("search", {"words": "growth", "paper": "nosuch"})]


def check_resolution():
    """P105: every concept entry's label, name and alias and the 20 qualifier phrases resolve through concept() to the entry (an
    ambiguous alias lists it among its candidates; a qualifier phrase puts the qualifier's counts first); the misses return a
    'nearest' line and no error; only a malformed call errors. Prints the calls and tokens of this battery."""
    import tools, concept as CN, query as Q
    err, calls, chars = [], 0, 0

    def run(name, args):
        nonlocal calls, chars
        lines, e = tools.run_tool(name, args)
        calls += 1; chars += sum(len(i) + len(t) + 4 for i, t in lines)
        return lines, e
    amb = {CN_norm(a) for a in L.AMBIGUOUS}
    for q in sorted(L.ENTRIES):
        e = L.ENTRIES[q]
        if e["type"] not in ("quantity", "categorical") or e.get("replaced_by"):
            continue
        for w in dict.fromkeys([e.get("label", ""), e.get("name", "")] + list(e.get("aliases", []))):
            if not w or CN_norm(w) in amb:
                continue
            lines, er = run("concept", {"words": w})
            ids = {i for i, _ in lines}
            if er or q not in ids:
                err.append(f"resolution: concept({w!r}) should name {q}, got {sorted(ids)[:4]} {er} (P105)")
    for ph, q in QUALIFIER_PHRASES:
        lines, er = run("concept", {"words": ph})
        ids = {i for i, _ in lines}
        if er or q not in ids or not lines or not lines[0][1].startswith("qualifier "):
            err.append(f"resolution: concept({ph!r}) should put the qualifier's counts first and name {q}, got {lines[:1]} {er} (P105)")
    for ph, q in SPECIES_PHRASES:                                                # P111: the same phrase through values(result=…): no error, no nearest line, rows present
        lines, er = run("values", {"result": ph})
        if er or not lines or any("nearest" in t for _, t in lines[:1]):
            err.append(f"resolution: values(result={ph!r}) should return the quantity's records with the species as a qualifier, got {lines[:1]} {er} (P111)")
    for name, args in MISSES:
        lines, er = run(name, args)
        if er or not any("nearest" in t for _, t in lines):
            err.append(f"resolution: {name}({args}) should return a nearest line without error, got {lines[:1]} {er} (P105)")
    for i_ in ("penetration_depth", "crystallinity", "ylilammi_diffusion_reaction", "run_variation", "tma", "pillarhall_3", "family:conformality"):   # P110: one probe per id kind
        lines, er = run("detail", {"ids": [i_]})
        if er or not lines or lines[0][0] != i_ or not any(lines[0][1].startswith(x) for x in ("quantity ", "categorical ", "model ", "mechanism ", "species ", "structure ", "family ")):
            err.append(f"detail(ids=[{i_!r}]) should return the card as concept() would, got {lines[:1]} {er} (P110)")
    _, er = run("detail", {"ids": ["no_such_id"]})
    if not er:
        err.append("detail(ids=['no_such_id']) must be an error: an id of no kind (P110)")
    lines, er = run("papers", {"process": "plasma"})                             # P112: a process mode
    got = {i for i, _ in lines if i in Q.TREES}
    want = {k for k, s_ in CN.summaries().items() if "plasma" in s_.get("modes", [])}
    if er or got != want:
        err.append(f"papers(process='plasma') returned {sorted(got)}, the plasma papers are {sorted(want)} (P112)")
    lines, er = run("papers", {"material": "MoS2"})
    if er or {i for i, _ in lines if i in Q.TREES} != {k for k, s_ in CN.summaries().items() if "MoS2" in s_["materials"]}:
        err.append(f"papers(material='MoS2') should resolve the formula (P112) {er}")
    lines, er = run("search", {"words": "purge growth per cycle"})              # P113: a paper's sets by word overlap with the query
    y = next((t for i, t in lines if i == "yim20"), "")
    first = re.search(r"sets: \[([^\]]+)\]", y)
    if not first or "purge" not in (Q.TREES["yim20"].byid[first.group(1)]["statement"] + Q.TREES["yim20"].byid[first.group(1)].get("label_as_printed", "")).lower():
        err.append(f"search('purge growth per cycle'): yim20's first set should be a purge series, got {first.group(1) if first else None} (P113)")
    _, er = run("values", {"result": "penetration depth", "no_such_argument": 1})
    if not er:
        err.append("resolution: a malformed call must still be an error (P105)")
    print(f"== resolution (P105, P110–P113): {calls} calls ({len(QUALIFIER_PHRASES)} qualifier phrases of which {len(SPECIES_PHRASES)} species, {len(MISSES)} misses, 7 detail ids, papers and search probes), {chars // 4:,} tokens; a miss suggests the nearest three, only a malformed call errors")
    return err


def CN_norm(w):
    import concept as CN
    return CN.norm(w)


def check_edges():
    """P101: every concept card has at most MAX_EDGES edge lines, each of a known form, and every target resolves: a quantity, model
    or family member to an entry, a transform to lists.TRANSFORMS, a paper key to a tree; the number of cards with edges is printed."""
    import concept as CN, query as Q
    err, n_cards, n_edges = [], 0, 0
    tids = {t["id"] for t in L.TRANSFORMS}
    for q in sorted(L.ENTRIES):
        if L.ENTRIES[q]["type"] not in ("quantity", "categorical") or L.ENTRIES[q].get("replaced_by"):
            continue
        ed = CN.edges(q)
        if len(ed) > CN.MAX_EDGES:
            err.append(f"card {q}: {len(ed)} edges (P101)")
        n_cards += bool(ed); n_edges += len(ed)
        for t in ed:
            if m := re.match(r"converts to (\S+) given (\S+) \(", t):
                bad = [x for x in (m.group(1), m.group(2)) if x not in L.ENTRIES]
            elif m := re.match(r"ratio of (.+)$", t):
                bad = [x for x in m.group(1).split(" / ") if x.split("{")[0] not in L.ENTRIES]
            elif m := re.match(r"derived from (.+) \((\S+)\)$", t):
                bad = [x for x in m.group(1).split(", ") if x.split("{")[0] not in L.ENTRIES and not x.startswith("other:") and not x.startswith("@")] + ([m.group(2)] if m.group(2) not in tids else [])
            elif m := re.match(r"input of model (.+)$", t):
                bad = [x for x in m.group(1).split(", ") if L.ENTRIES.get(x, {}).get("type") != "model"]
            elif m := re.match(r"same family (\S+): (.+?) · the family across papers: ", t):
                bad = ([m.group(1)] if m.group(1) not in L.FAMILIES else []) + [x for x in m.group(2).split(", ") if x not in L.ENTRIES]
            elif m := re.match(r"defined by paper (.+)$", t):
                bad = [x for x in re.findall(r"(\w+)(?: \([^)]*\))?(?:, |$)", m.group(1)) if x not in Q.TREES]
            else:
                bad = [t]
            err += [f"card {q}: edge target {b!r} does not resolve (P101): {t[:80]}" for b in bad]
    print(f"== card edges (P101): {n_cards} cards with edges, {n_edges} edges")
    return err


def check_grids():
    """P80: for every grid set, values(result=q, paper) renders it as a matrix from its full member list: the tested cells of every
    matrix equal len(all) (the untested combinations are counted as n.t.); every child series' members lie in the cells or the variants
    (query.grid_info); no child series is printed as a group of its own. Token sizes against ask-v3.1 (values_sizes_baseline.csv,
    recorded before any change): a call whose quantity was then repeated over two or more child views must not exceed its own size
    (the views are no longer repeated), and the total over the grid paper's calls must not exceed the ask-v3.1 total; a call with no
    repeated view (a quantity on one series or on variants only) gains the grid's header and the P79 homes, and its delta is printed."""
    import tools, query as Q
    err, n_grids, n_calls, base = [], 0, 0, {(r["result"], r["paper"]): int(r["tokens"]) for r in rd(HERE / "values_sizes_baseline.csv")}
    deltas = []
    for k, T in Q.TREES.items():
        for c in T.comps:
            if c["kind"] != "grid":
                continue
            n_grids += 1
            gi = Q.grid_info(T, c)
            allowed = set(gi["cells"]) | set(gi["candidates"])
            for cid in gi["children"]:
                bad = [m for m in T.member_entities(T.byid[cid]) if m not in allowed]
                if bad:
                    err.append(f"{cid}: a child series of {c['fact_id']} with members outside its cells and variants: {bad[:3]} (P80)")
            tot_b = tot_n = 0
            for (q, kp), tokens in sorted(base.items()):
                if kp != k:
                    continue
                n_calls += 1
                lines, e_ = tools.run_tool("values", {"result": q, "paper": k})
                size = sum(len(t) + len(i) + 4 for i, t in lines) // 4
                tot_b += tokens; tot_n += size
                views = sum(1 for cid in gi["children"] if any(kk.split("{")[0].split("[")[0] == q for m in T.member_entities(T.byid[cid]) if m in gi["cells"] for kk in Q.result_records(T, m)))
                deltas.append(f"{q} {tokens}->{size} ({views} views)")
                if views >= 2 and size > tokens:
                    err.append(f"values({q}, {k}): {size} tokens, {tokens} at ask-v3.1 although its {views} child views are no longer repeated (P80)")
            if tot_n > tot_b:
                err.append(f"values(result, {k}) over the grid paper: {tot_n} tokens in all, {tot_b} at ask-v3.1 (P80)")
                js = joined(lines)
                if any(i in gi["children"] and t.startswith("set [") for i, t in js):
                    err.append(f"values({q}, {k}): a child series of the grid printed as a group (P80)")
                for n, (i, t) in enumerate(js):                                  # every matrix: shown + left out = every cell of the grid; the shown ones counted in its rows
                    m = re.match(r"(.+?) · (\d+) of (\d+) cells shown \((\d+) in rows or columns left out\)", t)
                    if i != c["fact_id"] or not m:
                        continue
                    shown, total, left = int(m.group(2)), int(m.group(3)), int(m.group(4))
                    counted = 0
                    for i2, t2 in js[n + 1:]:
                        if i2 != c["fact_id"] or " cells shown (" in t2 or " · " not in t2 or t2.startswith(("variants of", "child series", "rows ", "set-level", "no cell holds")):
                            break
                        counted += sum(1 for x in t2.split(" · ", 1)[1].split(" | ") if x.strip() != "n.t.")
                    folded = any(t2.startswith("rows ") and t2.split(": ", 1)[0].endswith("budget") and m.group(1) in t2 for _, t2 in js[n + 1:])
                    if total != len(gi["cells"]) or shown + left != total or (counted != shown and not folded):
                        err.append(f"values({q}, {k}): matrix of {m.group(1)}: {counted} cells in its rows, {shown} shown + {left} left out, the grid {len(gi['cells'])} (P80)")
    print(f"== grids (P80): {n_grids} grid sets; {n_calls} values(result, paper) calls on grid papers against their ask-v3.1 sizes: " + "; ".join(deltas))
    return err


def check_homes():
    """P79: every value record of the page data with an entry (homeless.records) is rendered by values(result=<its entry>, paper=<its
    paper>) in full (an input row, an aggregate row, a set's own row, a paper-level row, a specimen row with every record of its key,
    or a level of a settings table with every fact that states it): the homeless count is 0."""
    import homeless
    miss = homeless.report(verbose=False)
    recs, src = homeless.records()
    by = collections.Counter((v[0], homeless.home_needed(f)) for f, v in miss.items())
    print(f"== homes (P79): {len(recs)} value records with an entry (from the {src}); {len(miss)} homeless" + (": " + ", ".join(f"{k} {h} {n}" for (k, h), n in sorted(by.items())) if miss else ""))
    return [f"{f}: {q} ({kind}) has no home in values(result={q}, paper={k}); needs a {homeless.home_needed(f)} row (P79)" for f, (k, q, kind) in sorted(miss.items())]


def check_calls():
    """P75, P119: call accounting, scripted without a model (ask.answer_call, run_metrics.process). Walls: a question's calls end when the
    delivered tool output of its executed calls reaches the token budget (chars/4; the refusal names it, every executed result ends with a
    'budget left' line that decreases monotonically and never goes negative, an error call leaves it unchanged), after five error calls
    (error wall), or at the executed-call ceiling (--max-calls, total wall twice it). Run at the default budget and at 80,000 tokens, the
    ceiling test at 10 and 20."""
    import ask, concept as CN, query as Q, run_metrics as RM
    err = []
    pc = CN.counts()
    valid = [("values", {"result": q}) for q in sorted(L.OUTPUTS) if any(d.get("values") for d in pc.get(q, {}).values())]
    valid += [("values", {"result": q, "paper": k}) for q in sorted(L.OUTPUTS) for k in Q.TREES if pc.get(q, {}).get(k, {}).get("values")]
    bad = lambda n: [("values", {"result": "penetration depth", "no_such_argument": i}) for i in range(n)]   # P105: only a malformed call errors; an unknown name suggests

    def play(calls):
        tool_calls, given, seen = [], {}, {}
        res = [ask.answer_call(dict(id=str(n), name=name, arguments=dict(args)), tool_calls, given, seen) for n, (name, args) in enumerate(calls, 1)]
        return res, RM.process(tool_calls), tool_calls

    def scripted(cap):
        """The ceiling and the error and total walls at one cap (ask.set_max_calls), the token budget out of the way."""
        ask.set_max_tokens(10 ** 9); C = ask.set_max_calls(cap)
        cap_msg = f"error: the ceiling of {C['cap']} executed tool calls is reached; answer from what you have"
        res, p, _ = play(bad(4) + valid[:C["cap"] + 1])                         # four errors, then cap + 1 valid calls
        if not all(r["error"] for r in res[:4]) or p["errors"] != 4:
            err.append(f"calls (cap {cap}): four malformed calls should be four error calls, got errors {p['errors']} (P75)")
        if any(r["error"] for r in res[4:4 + C["cap"]]) or p["executed"] != C["cap"]:
            err.append(f"calls (cap {cap}): {C['cap']} executed calls must remain available after four errors, got executed {p['executed']} (P75)")
        if res[4 + C["cap"]]["content"] != cap_msg or p["wall_hit"] != "none":
            err.append(f"calls (cap {cap}): the call after {C['cap']} executed ones should get the ceiling message, got {res[4 + C['cap']]['content'][:80]!r}, wall {p['wall_hit']} (P75)")
        res, p, _ = play(bad(C["errors"]) + valid[:1])                            # five errors, then a valid call: the error wall
        if f"wall of {C['errors']} calls that returned an error" not in res[-1]["content"] or p["wall_hit"] != "errors" or p["executed"] != 0 or C["errors"] != 5:
            err.append(f"calls (cap {cap}): the call after {C['errors']} errors should be refused naming the error wall (5 whatever the cap), got {res[-1]['content'][:80]!r}, wall {p['wall_hit']} (P75)")
        n_id = C["total"] - 4 - C["cap"]
        res, p, _ = play(bad(4) + valid[:C["cap"]] + valid[:n_id] + valid[C["cap"]:C["cap"] + 1])   # 4 errors + cap executed + identical up to 2·cap, then one more
        if C["total"] != 2 * C["cap"] or p["identical"] != n_id or p["calls"] != C["total"] + 1 or f"wall of {C['total']} calls" not in res[-1]["content"] or p["wall_hit"] != "total":
            err.append(f"calls (cap {cap}): the call after {C['total']} calls in all should be refused naming the total wall (2 × cap), got {res[-1]['content'][:80]!r}, wall {p['wall_hit']}, identical {p['identical']} (P75)")
        return C

    def token_wall(budget):
        """P119: values on large outputs (every paper) until the token wall is named; an error call in the middle; the budget-left line."""
        ask.set_max_calls(200); C = ask.set_max_tokens(budget)                  # the ceiling out of the way: the token wall must come first
        calls = valid[:3] + bad(1) + valid[3:len(valid)]
        res, p, tc = play(calls)
        lefts, prev = [], budget
        for r, c in zip(res, tc):
            m = re.search(r"budget left: ([\d,]+) tokens$", r["content"])
            if c.get("error"):
                if m or c.get("delivered_tokens"):
                    err.append(f"tokens ({budget}): an error or refused call carries a budget line or delivered tokens (P119)")
                continue
            if not m:
                err.append(f"tokens ({budget}): an executed result without its 'budget left' line (P119): {r['content'][-80:]!r}"); break
            left = int(m.group(1).replace(",", ""))
            if left < 0 or left > prev or left != max(prev - c["delivered_tokens"], 0):   # monotone, never negative, and exactly this call's cost (an error in between cost nothing)
                err.append(f"tokens ({budget}): budget left {left} after {prev} with {c['delivered_tokens']} delivered (P119)")
            lefts.append(left); prev = left
        hit = next((i for i, c in enumerate(tc) if c.get("error") == "wall:tokens"), None)
        if hit is None or p["wall_hit"] != "tokens" or f"budget of {budget:,} tool tokens is spent" not in res[hit]["content"]:
            err.append(f"tokens ({budget}): the token wall was not named (wall {p['wall_hit']}) (P119)")
        else:
            spent = sum(c.get("delivered_tokens") or 0 for c in tc[:hit] if not c.get("error"))
            if spent < budget or lefts[-1] != 0:
                err.append(f"tokens ({budget}): the wall came at {spent} delivered tokens, budget left {lefts[-1] if lefts else None} (P119)")
            if p["tool_tokens_delivered"] != spent:
                err.append(f"tokens ({budget}): run_metrics counts {p['tool_tokens_delivered']} delivered tokens, {spent} were (P119)")
        return dict(budget=budget, executed=p["executed"], spent=p["tool_tokens_delivered"], transcript=[r["content"] for r in res[max(0, (hit or 0) - 2):(hit or 0) + 1]])
    def malformed_turn():
        """P124: a turn whose call carries broken JSON is an error call (record error 'malformed', the raw string kept, chars 0), the question
        continues, and the error wall still fires at five."""
        ask.set_max_calls(ask.TOOL_CAP); ask.set_max_tokens(ask.TOKEN_BUDGET)
        tool_calls, given, seen = [], {}, {}
        broken = dict(id="1", name="values", arguments='{"result": "penetration depth", "paper": ', malformed="JSONDecodeError: Expecting value: line 1 column 42 (char 41)")
        r1 = ask.answer_call(broken, tool_calls, given, seen)
        r2 = ask.answer_call(dict(id="2", name="nosuchtool", arguments={"x": 1}), tool_calls, given, seen)
        r3 = ask.answer_call(dict(id="3", name="values", arguments={"result": "penetration depth", "paper": "yim20"}), tool_calls, given, seen)
        p = RM.process(tool_calls)
        if not (r1["error"] and "not valid JSON" in r1["content"] and "send the call again" in r1["content"]):
            err.append(f"malformed: the model-facing text should name the JSON error and ask again, got {r1['content'][:80]!r} (P124)")
        if tool_calls[0].get("error") != "malformed" or tool_calls[0].get("arguments") != broken["arguments"] or tool_calls[0].get("chars") != 0:
            err.append(f"malformed: the record should hold error 'malformed', the raw argument string and chars 0, got {tool_calls[0]} (P124)")
        if not (r2["error"] and tool_calls[1].get("error") == "malformed" and "unknown tool" in r2["content"]):
            err.append(f"malformed: an unknown tool name should be an error call too, got {r2['content'][:80]!r} (P124)")
        if r3["error"] or p["executed"] != 1 or p["errors"] != 2 or p["malformed"] != 2:
            err.append(f"malformed: the question should continue (executed 1, errors 2, malformed 2), got {p['executed']}, {p['errors']}, {p['malformed']} (P124)")
        for n in range(3):
            ask.answer_call(dict(id=str(10 + n), name="values", arguments="{", malformed="JSONDecodeError"), tool_calls, given, seen)
        r = ask.answer_call(dict(id="20", name="values", arguments={"result": "growth per cycle", "paper": "yim20"}), tool_calls, given, seen)
        if "wall of 5 calls that returned an error" not in r["content"]:
            err.append(f"malformed: five malformed calls should fire the error wall, got {r['content'][:80]!r} (P124)")
        return [r1["content"], r3["content"][-300:]]

    try:
        c10 = scripted(10); c20 = scripted(20)                                     # the ceiling and the walls scale (cap N, total 2N, errors 5)
        t40 = token_wall(ask.TOKEN_BUDGET); t80 = token_wall(80_000)              # P119 at the default budget and at 80,000
        mal = malformed_turn()                                                   # P124
    finally:
        ask.set_max_calls(ask.TOOL_CAP); ask.set_max_tokens(ask.TOKEN_BUDGET)
    check_calls.transcript = t40["transcript"]; check_calls.malformed = mal
    print(f"== calls (P75, P119): token budget {t40['budget']:,} spent after {t40['executed']} executed calls ({t40['spent']:,} tokens delivered), {t80['budget']:,} after {t80['executed']} ({t80['spent']:,}); "
          f"ceiling {c10['cap']} / {c20['cap']} executed calls, total walls {c10['total']} / {c20['total']}, error wall {c10['errors']}; {len(valid)} valid probes; "
          f"a malformed call is an error call and the question goes on (P124)")
    return err


def settings_probes():
    """[(entry, paper)] for every settings entry of the data (query.settings_entries, P78a: whatever node) with stated conditions in a paper (P76)."""
    import query as Q
    return [(S, k) for S in sorted(Q.settings_entries()) for k, T in Q.TREES.items() if any(Q.setting_matches(T, e, S, S) for e in Q.experiments(T))]


def joined(lines):
    """Tool lines with their wrapped continuations ('… ', P44) joined back: [(id, text)]."""
    out = []
    for i, t in lines:
        if t.startswith("… ") and out:
            out[-1] = (out[-1][0], out[-1][1] + " " + t[2:])
        else:
            out.append((i, t))
    return out


def check_settings():
    """P76: for every settings entry with stated conditions in a paper, values(entry, paper) is a settings table: no line is a specimen
    row (no line id is an experiment of the paper), the table header is present, the level rows (tools.SETTINGS_ROW) are as many as
    the distinct levels in the data (the experiments' condition records of the entry, keyed by the cell wording: text, kind mark, ±
    with its basis), and no output of a settings entry carries a k3 mark or column (a value computed by this knowledge base)."""
    import tools, query as Q
    err, probes, size = [], settings_probes(), 0
    for S, k in probes:
        T = Q.TREES[k]
        levels = {tuple(sorted((kk, tools._cells(rec, set(), fact=False)) for kk, _, rec in m)) for e in Q.experiments(T) + Q.inputs(T) for m in [Q.setting_matches(T, e, S, S)] if m}   # inputs are level rows too (P79)
        lines, e_ = tools.run_tool("values", {"result": S, "paper": k})
        if e_:
            err.append(f"values({S}, {k}): {e_} (P76)"); continue
        js = joined(lines)
        size = max(size, sum(len(t) + len(i) + 4 for i, t in lines) // 4)
        spec = [i for i, _ in js if i in set(Q.experiments(T))]
        if spec:
            err.append(f"values({S}, {k}): specimen rows {spec[:3]} in a settings output (P76)")
        if not any(i == f"{k}:settings" and t.startswith("settings table") for i, t in js):
            err.append(f"values({S}, {k}): no settings-table header (P76)")
        n_rows = sum(1 for _, t in js if tools.SETTINGS_ROW.search(t))
        if n_rows != len(levels):
            err.append(f"values({S}, {k}): {n_rows} level rows against {len(levels)} distinct levels in the data (P76)")
        if f"({tools.KIND_MARK['computed_by_kb']})" in "\n".join(t for _, t in js):
            err.append(f"values({S}, {k}): a value computed by this knowledge base (k3) in a settings output (P76)")
    print(f"== settings tables (P76): {len(Q.settings_entries())} settings entries in the data (whatever node, P78a); {len(probes)} (entry, paper) pairs with stated conditions; max {size} tokens per table")
    return err


def check_sets():
    """P77: for every comparison set of every paper, values(set=id) runs within the budget (no 'more' line), has one row per member of
    the full list (query.set_members_all) and the 'set' row exactly when the set owns records, and the fact ids of its table (a
    collapsed column counted through the cells it names) are exactly the fact ids values(result=q, paper=p) lists for those rows over
    every result name of the vocabulary, plus the set's own records; detail(ids=[set], parts=["table"]) prints the same rows."""
    import run_metrics as RM, tools, query as Q
    err, n_sets, size, collapsed = [], 0, 0, 0
    for k, T in Q.TREES.items():
        ref, deep = collections.defaultdict(set), {}                             # per experiment: the result facts values() lists, over every result name
        for q in sorted(Q.vocabulary()["result"]):                               # (a model run's inputs, listed by values as its conditions, are not results)
            S = Q.settings_entry(q)
            rows = [(r["record"], r["entity"]) for g in Q.values(q, k) for r in g["rows"]]
            if S:                                                                # a settings entry: values lists its results as 'result, not a setting' lines (P76), the same facts
                rows += [(rec, e) for e, kk, nm, rec in Q.setting_extras(S, q, k).get(k, {}).get("results", [])]
            for rec, e in rows:
                    if e not in deep:
                        deep[e] = {f["fact_id"] for fs in Q.results_deep(T, e).values() for f in fs} if e in T.byid and T.byid[e]["type"] == "entity" else set()
                    for rr in [rec] + list(rec.get("alternatives") or []):      # P79: a cell lists every record of its key, the alternatives included
                        if rr.get("fact") in deep[e] and rr.get("kind") != "computed_by_kb":
                            ref[e].add(rr["fact"])
        for c in T.comps:
            cid = c["fact_id"]; n_sets += 1
            d = Q.set_table(cid)
            members = set(d["members"])
            lines, e_ = tools.run_tool("values", {"set": cid})
            if e_:
                err.append(f"values(set={cid}): {e_} (P77)"); continue
            if lines[-1][0] == "more":
                err.append(f"values(set={cid}): over the budget (P77)")
            js = joined(lines)
            size = max(size, sum(len(t) + len(i) + 4 for i, t in lines) // 4)
            rows = [i for i, _ in js if i in members]
            if sorted(rows) != sorted(members):
                err.append(f"values(set={cid}): {len(rows)} member rows against {len(members)} members of the full list (P77)")
            set_rows = [t for i, t in js if i == cid and t.startswith("set (values stated for the set")]
            if bool(set_rows) != ("set" in d["cells"]) and not T.is_figset(cid):   # P85: a figure set's own records are its rows
                err.append(f"values(set={cid}): the set row is {'missing' if not set_rows else 'there'} while the set {'owns' if 'set' in d['cells'] else 'owns no'} records (P77)")
            table = {m for i, t in js if i in members or (i == cid and t.startswith("set (values stated")) for m in RM.ID.findall(t)}
            table = {i for i in table if not (i in T.byid and T.byid[i]["type"] == "caveat")}
            hidden = next((t for _, t in js if " more quantities not shown" in t), "")
            if hidden:
                collapsed += 1
                hidden_names = {x.strip() for x in hidden.split(": ", 1)[1].split(" — open")[0].split(", ")}
                table |= {rr["fact"] for key, name in d["columns"] if name in hidden_names for row in d["cells"].values() for r in row.get(key, []) for rr in [r] + list(r.get("alternatives") or []) if rr.get("fact")}
            expected = set().union(*(ref[m] for m in members)) | {f["fact_id"] for f in T.own(cid) if f["type"] in Q.RESULT_TYPES and f["quantity"] and (Q.text_of(f) or f["points_ref"])}
            if table != expected:
                err.append(f"values(set={cid}): the table's fact ids differ from values(result=q)'s: missing {sorted(expected - table)[:4]}, extra {sorted(table - expected)[:4]} (P77)")
            lines2, _ = tools.run_tool("detail", {"ids": [cid], "parts": ["table"]})
            if [t for i, t in joined(lines2) if i in members] != [t for i, t in js if i in members]:
                err.append(f"detail(ids=[{cid}], parts=[table]) does not print the rows of values(set={cid}) (P77)")
    print(f"== set tables (P77): {n_sets} comparison sets, each one call within the budget; {collapsed} with columns collapsed; max {size} tokens per table")
    return err


PROBE_PAPER = {}                                                               # P97: (tool, json args) -> the paper a probe belongs to ('' = cross-paper)
BATTERY = {}                                                                    # P97: paper -> (calls, tokens) after check_kinds


def paper_probes(k):
    """P97: the fixed probe list of one paper: concept on its most populated quantity; values on its three most populated quantities;
    values on two of its comparison sets (facts-level first); one curve; detail on a paragraph and a panel location; one search with
    the paper filter from its figure inventory; the settings tables of its first two settings entries (P76); source on one element;
    detail on two facts sharing a caveat (P68)."""
    import concept as CN, query as Q
    T = Q.TREES[k]; s = CN.summaries()[k]
    probes = []
    qs = [q for _, q in s["outcomes"]]
    if qs:
        probes.append(("concept", {"words": L.NAMES.get(qs[0], qs[0])}))
    probes += [("values", {"result": q, "paper": k}) for q in qs[:3]]
    if len(qs) >= 2:
        probes.append(("values", {"result": qs[:3], "paper": k}))                  # P121: the three most populated quantities in one call
    comps = sorted((c["fact_id"] for c in T.comps), key=lambda c: (T.is_figset(c), c))
    probes += [("values", {"set": cid}) for cid in comps[:2]]
    if T.curves:
        probes.append(("curve", {"id": next(iter(T.curves))}))
    locs = {}
    for f in T.rows:
        if "#" not in f["fact_id"]:
            continue
        for e in f["evidence"].split(";"):
            if re.match(r"^s\d+\.p\d+$", e):
                locs.setdefault("paragraph", f"{k}:{e}")
            elif re.match(r"^fig\d+[a-zA-Z]$", e):
                locs.setdefault("panel", f"{k}:{e}")
    probes += [("detail", {"ids": [i]}) for i in locs.values()]
    inv = next((i for i in T.inventory if i.get("content")), None)
    if inv:
        probes.append(("search", {"words": " ".join(w for w in Q.tokens(inv["content"])[:5] if len(w) > 2), "paper": k}))
    probes += [("values", {"result": S, "paper": kk}) for S, kk in settings_probes() if kk == k][:2]
    first = next((f["evidence"].split(";")[0] for f in T.rows if "#" in f["fact_id"] and f["evidence"]), "")
    if first:
        probes.append(("source", {"id": f"{k}:{first}"}))
    c = next((c for c in Q.caveats_of(T) if len(c["facts"]) >= 2), None)
    shared = (c["f"]["fact_id"], sorted(c["facts"])[:2]) if c else None
    if shared:
        probes.append(("detail", {"ids": shared[1]}))
    return probes, shared


def tool_probes():
    """The probe battery whose outputs check_kinds scans (P68), defined per paper (P97): paper_probes for every paper, plus the cross-paper
    probes once: values on every output concept that has values, concept and search (no paper filter) on the stored search probes, and
    detail on one id of every record type of every paper, eight per call. Returns (probes, shared); PROBE_PAPER maps each probe to its paper."""
    import concept as CN, query as Q
    PROBE_PAPER.clear()
    probes, shared = [], []
    for k in Q.TREES:
        ps, sh = paper_probes(k)
        for name, args in ps:
            PROBE_PAPER[(name, json.dumps(args, sort_keys=True))] = k
        probes += ps
        if sh:
            shared.append(sh)
    cross = [("values", {"result": q}) for q in sorted(L.OUTPUTS) if any(d.get("values") for d in CN.counts().get(q, {}).values())]
    for p in rd(HERE / "search_probes.csv"):
        cross += [("concept", {"words": p["words"]}), ("search", {"words": p["words"]})]
    first = {}
    for r in Q.search_records():
        if r["type"] != "concept":
            first.setdefault((r["paper"], r["type"]), r["id"])
    ids = list(first.values())
    cross += [("detail", {"ids": ids[n:n + 8], "parts": ["what", "differs", "results", "recipe", "claims", "computed"]}) for n in range(0, len(ids), 8)]
    for name, args in cross:
        PROBE_PAPER.setdefault((name, json.dumps(args, sort_keys=True)), "")
    return probes + cross, shared


def check_kinds():
    """P57, P68: every provenance or basis word a tool prints is in the ontology's tables: 'kind: <phrase>' (or 'kinds: a; b') from the
    phrase table, a mark (kN) bound to a phrase by the output's legend, a ± followed by a basis phrase, by a basis id the legend
    binds, or by the one 'not stated' wording; a legend's basis phrase equals the table's; no deictic provenance ('computed here')
    in any tool description, tool output or page text; a caveat's text once per output; the two-fact probe prints its shared
    caveat's text once and its id on both facts."""
    import tools, query as Q
    err = []
    phrases, bases = set(L.PHRASES.values()), set(L.BASES.values())
    probes, shared = tool_probes()
    outputs, outputs_ids = {}, {}
    for name, args in probes:
        lines, e = tools.run_tool(name, args)
        joined, jids = [], []
        for i_, t in lines:                                                     # a wrapped line continues the previous one (P44)
            if t.startswith("… ") and joined:
                joined[-1] += " " + t[2:]
            else:
                joined.append(t); jids.append(i_)
        outputs[(name, json.dumps(args, sort_keys=True))] = joined + ([e] if e else [])
        outputs_ids[(name, json.dumps(args, sort_keys=True))] = list(zip(jids, joined))
    texts = [t["description"] for t in tools.TOOLS]
    slots = {}                                                                   # P107: derived structure slots (a fact with inputs) and their value texts
    for k, T in Q.TREES.items():
        for f in T.rows:
            if "#" in f["fact_id"] and f["quantity"] in Q.SLOTS and f.get("inputs") and Q.text_of(f):
                slots[f["fact_id"]] = Q.text_of(f)
    for key, out in outputs_ids.items():
        for i_, t in out:
            for fid, vt in slots.items():
                if (i_ == fid or f"[{fid}]" in t) and vt in t and not t.startswith("claim") and "entry from" not in t and "from " not in t.split(vt, 1)[1][:200]:   # a claim's statement is the paper's wording
                    err.append(f"{key[0]} {key[1]}: the derived slot {fid} ({vt}) prints without its source (P107): {t[:100]}")
    for key, out in outputs.items():
        marks = dict(re.findall(r"\((k\d+)\) ([^;]+)", next((t for t in out if t.startswith("kinds: (")), "")))
        legend = {m.group(1): m.group(2) for t in out for m in [re.match(r"basis (\w+): (.+)$", t)] if m}
        for b, ph in legend.items():
            if L.BASES.get(b) != ph:
                err.append(f"{key[0]} {key[1]}: legend 'basis {b}: {ph[:40]}' is not the table's (P68)")
        for t in out:
            texts.append(t)
            if "0 curves of this quantity" in t:                                  # P96: no empty figure-set line
                err.append(f"{key[0]} {key[1]}: an empty figure-set line ('0 curves of this quantity') (P96)")
            if t.startswith("kinds: (k"):                                          # the legend binds the marks to the table's phrases
                continue
            for m in re.finditer(r"(?<!set )kinds?: ([^·\)\]]+)", t):
                for ph in m.group(1).split(";"):
                    if ph.strip().rstrip(":") not in phrases:
                        err.append(f"{key[0]} {key[1]}: provenance phrase {ph.strip()!r} is not in the phrase table (P57, P68)")
            for m in re.finditer(r"\((k\d+)\)", t):
                if marks.get(m.group(1), "").strip() not in phrases:
                    err.append(f"{key[0]} {key[1]}: mark ({m.group(1)}) is not bound to a phrase of the table by the legend (P68)")
            for m in re.finditer(r"± \S+ \(", t.split(" · statement: ")[0]):      # a fact's own statement is the paper's wording, not the tool's basis phrase
                after = t[m.end():]
                head = re.match(r"[^;)]*", after).group(0).strip()
                if not (any(after.startswith(ph) for ph in bases) or head == Q.NO_BASIS or head == "basis not stated" or (head in L.BASES and legend.get(head) == L.BASES[head])):
                    err.append(f"{key[0]} {key[1]}: basis wording {head!r} is outside the basis table (P68)")
        cav = [t for t in out if t.startswith("caveat · ")]
        if len(cav) != len(set(cav)):
            err.append(f"{key[0]} {key[1]}: a caveat's text is printed twice (P68)")
    for cid, (a, b) in shared:
        out = outputs[("detail", json.dumps({"ids": [a, b]}, sort_keys=True))]
        text = "\n".join(out)
        tx = Q.TREES[cid.split(":")[0]].byid[cid]["statement"]
        if text.count(f"caveat · {tx}") != 1 or text.count(f"[{cid}]") < 2:
            err.append(f"detail({a}, {b}): the shared caveat {cid} should print its id on both facts and its text once (P68)")
    for t in texts:
        for w in DEICTIC:
            if w in t:
                err.append(f"{w!r} printed: {t[:80]!r} (P57, P68)")
    page = HERE / "reports" / "pilot.html"
    if page.exists() and "computed here" in page.read_text(encoding="utf-8"):
        err.append("'computed here' appears in reports/pilot.html (P57)")
    BATTERY.clear()                                                             # P97: the battery per paper (tokens = chars / 4), '' = the cross-paper probes
    for key, out in outputs.items():
        pk = PROBE_PAPER.get(key, "")
        c, tk = BATTERY.get(pk, (0, 0))
        BATTERY[pk] = (c + 1, tk + sum(len(t) for t in out) // 4)
    with (HERE / "battery_per_paper.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["paper", "calls", "tokens"])
        for pk in list(Q.TREES) + [""]:
            if pk in BATTERY:
                w.writerow([pk or "cross-paper", *BATTERY[pk]])
        w.writerow(["total", sum(c for c, _ in BATTERY.values()), sum(t for _, t in BATTERY.values())])
    print("== battery per paper (P97): " + "; ".join(f"{pk or 'cross-paper'} {c} calls {tk:,} tokens" for pk, (c, tk) in BATTERY.items()))
    print(f"== kinds (P57, P68): {len(L.KINDS)} kinds with phrases, {len(L.BASES)} bases; {len(probes)} probe calls, {len(texts)} tool texts scanned; max {max(sum(len(t) for t in o) // 4 for o in outputs.values())} tokens per output, "
          f"{sum(sum(len(t) for t in o) for o in outputs.values()) // 4:,} tokens over the battery")
    return err


def check_map():
    """P70: the L0 map of the knowledge base is generated from the data and holds counts and names only: every number is a count
    (concept.map_numbers_are_counts), it stays within concept.MAP_BUDGET tokens, and no claim's statement (a paper's conclusion)
    appears in it."""
    import concept as CN, query as Q
    err = []
    m = CN.l0_map()
    bad = CN.map_numbers_are_counts(m)
    if bad:
        err.append(f"map: numbers that are not counts: {bad} (P70)")
    if len(m) / 4 > CN.MAP_BUDGET:
        err.append(f"map: {len(m) / 4:.0f} tokens, over {CN.MAP_BUDGET} (P70)")
    low = m.lower()
    for k, T in Q.TREES.items():
        for f in T.rows:
            if f["type"] == "claim" and f["statement"] and " ".join(f["statement"].lower().split()[:6]) in low:
                err.append(f"map: carries the claim {f['fact_id']} (P70)")
    summ = CN.summaries()
    fake = {}
    for i in range(5):                                                          # P97: 58 papers simulated from the 12 by replication; a check, not stored data
        for k, sm in summ.items():
            if len(fake) < 58:
                fake[f"{k}_{i}"] = dict(sm, key=f"{k}_{i}")
    m58 = CN.l0_map(fake)
    if len(m58) / 4 > CN.MAP_BUDGET:
        err.append(f"map: {len(m58) / 4:.0f} tokens at 58 simulated papers, over {CN.MAP_BUDGET} (P97)")
    pc = CN.counts()                                                             # P120: the compact paper index of the kb prompt, from the same counts as the cards (P95)
    block = CN.prompt_index()
    for line in block.splitlines()[1:]:
        k = line.split(" ")[0]
        if len(line) / 4 > CN.PROMPT_INDEX_BUDGET:
            err.append(f"paper index: {k} takes {len(line) / 4:.0f} tokens, over {CN.PROMPT_INDEX_BUDGET} (P120)")
        got = {q: int(n) for q, n in re.findall(r"(\w+) (\d+)(?:,| ·)", line.split(" · ", 1)[1].split(" · claims")[0] + " ·")}
        want = {q: d[k]["values"] for q, d in pc.items() if q in L.ENTRIES and L.ENTRIES[q]["type"] in ("quantity", "categorical") and d.get(k, {}).get("values")}
        if "+" not in line and got != want:
            err.append(f"paper index: {k} counts differ from the cards: {sorted(set(got.items()) ^ set(want.items()))[:4]} (P120, P95)")
    fake_pc = {q: {kk: pc[q][kk.rsplit("_", 1)[0]] for kk in fake if kk.rsplit("_", 1)[0] in pc[q]} for q in pc}   # the 12 papers' counts replicated to 58 keys
    block58 = CN.prompt_index(None, fake_pc, list(fake))
    if len(block58) / 4 > 20_000:
        err.append(f"paper index: {len(block58) / 4:.0f} tokens at 58 simulated papers, over 20,000 (P120)")
    print(f"== map (P70, P97, P120): {len(m) / 4:.0f} tokens of at most {CN.MAP_BUDGET}, {m.count(chr(10)) + 1} lines, every number a count; {len(m58) / 4:.0f} tokens at 58 simulated papers; "
          f"paper index {len(block) / 4:.0f} tokens at 12 papers, {len(block58) / 4:.0f} at 58 simulated (at most 20,000), counts equal the cards'")
    return err


def check_cards_values():
    """P95: for every (quantity, paper) pair a concept card lists with one value or more, values(result=<the quantity's id>, paper)
    returns value rows, and the distinct value facts it renders in full (no budget) number the card's count."""
    import concept as CN, query as Q, tools
    err, n = [], 0
    old = tools.BUDGET, tools.BUDGET_CHARS
    tools.BUDGET, tools.BUDGET_CHARS = False, 10 ** 9
    try:
        for q, d in sorted(CN.counts().items()):
            if q not in L.ENTRIES or L.ENTRIES[q]["type"] not in ("quantity", "categorical"):
                continue
            for k, c in d.items():
                if not c.get("values"):
                    continue
                n += 1
                T = Q.TREES[k]
                lines, e = tools.run_tool("values", {"result": q, "paper": k})
                if e:
                    err.append(f"card {q} / {k}: {c['values']} values on the card, values(result={q!r}, paper={k!r}) answers {e} (P95)"); continue
                ids = {i for _, t in lines for i in re.findall(r"\[([a-z0-9]+:[^\]\s]+)\]", t)} | {i for i, _ in lines}
                rows = {i for i in ids if i in T.byid and "#" in i and T.byid[i]["quantity"] == q and T.byid[i]["type"] in Q.RESULT_TYPES + ("cited",)
                        and (Q.text_of(T.byid[i]) or T.byid[i]["points_ref"]) and T.byid[i]["data_kind"] != "computed_by_kb"}
                if len(rows) != c["values"]:
                    err.append(f"card {q} / {k}: {c['values']} values on the card, {len(rows)} value rows in values(result={q!r}, paper={k!r}) (P95)")
    finally:
        tools.BUDGET, tools.BUDGET_CHARS = old
    print(f"== card–values (P95): {n} (quantity, paper) pairs with values on a card, each against values(result, paper)")
    return err


def check_caveats():
    """P56: a caveat's text is stored once in the dataset (no two caveat facts with one statement); no caveat is attached to a fact
    that already inherits it through its inputs; the counts: unique caveats, direct attachments (links and node targets), the
    facts and entities reached, the stored text volume."""
    import query as Q
    err, texts, links, reached, vol = [], collections.Counter(), 0, 0, 0
    for k, T in Q.TREES.items():
        for c in Q.caveats_of(T):
            texts[" ".join(c["f"]["statement"].lower().split())] += 1
            links += len(c["facts"]) + len(c["nodes"]); vol += len(c["f"]["statement"])
            reached += len(Q.caveat_targets(T, c["f"]))
            for l in c["facts"]:
                f = T.byid.get(l)
                if f and f.get("inputs") and any(c["f"] in Q.caveats_for(T, T.byid[i], T.ent_of(i)) for i in f["inputs"].split(";") if i in T.byid):
                    err.append(f"{c['f']['fact_id']}: attached to {l}, which inherits it through its inputs (P56)")
    err += [f"caveat text stored {n} times: {t[:60]!r} (P56)" for t, n in texts.items() if n > 1]
    print(f"== caveats (P56): {sum(texts.values())} caveats, {len(texts)} unique texts ({vol:,} characters stored once), {links} direct attachments, {reached} facts and entities reached")
    return err


def check_bases():
    """P52: the stored values of one entry id carry at most one unit dimension (plus unitless) and at most one stated basis
    (relative_to; not_stated beside one stated basis is allowed), over the whole dataset; spread facts (stat=) and quantity other
    are outside. Returns the problems and prints the counts."""
    err, units, bases = [], collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for pid in list(KEYS) + ["user"]:
        for f in rd(HERE / (f"{pid}.facts.csv" if pid != "user" else "user.facts.csv")):
            q = f["quantity"]
            if "#" not in f["fact_id"] or not q or q == "other" or f["type"] in ("caveat", "claim") or "stat=" in f["qualifiers"] or L.ENTRIES.get(q, {}).get("definitions"):
                continue                                                        # P108 (b): an entry with definitions carries one dimension per definition (check_dimensions)
            if f["value"] or f["value_min"] or f["value_max"]:
                u = L.UNIT_ALIAS.get(f["unit"], f["unit"])
                if u and u not in L.UNIT_BASE:
                    err.append(f"{f['fact_id']}: unit {f['unit']!r} is not in lists.UNIT_BASE, so its dimension cannot be checked (P52)")
                    continue
                units[q][L.UNIT_BASE[u][0] if u else ""] += 1
                qd = dict(p.split("=", 1) for p in f["qualifiers"].split(";") if "=" in p)
                if "relative_to" in qd:
                    bases[q][qd["relative_to"]] += 1
    for q, c in units.items():
        dims = [d for d in c if d and d != "dimensionless"] + (["dimensionless"] if "dimensionless" in c else [])
        if len([d for d in c if d]) > 1:
            err.append(f"{q}: values in more than one unit dimension: {dict(c)} (P52)")
    for q, c in bases.items():
        if len([b for b in c if b != "not_stated"]) > 1:
            err.append(f"{q}: values on more than one basis: {dict(c)} (P52)")
    print(f"== bases: {len(units)} quantity ids with values; bases stated on {len(bases)} ({', '.join(f'{q} {dict(c)}' for q, c in sorted(bases.items()))})")
    return err


def unit_dimensions():
    """{unit symbol or variant: dimension} from ontology/units.yaml (P108)."""
    import yaml
    out = {}
    for u in yaml.safe_load((HERE.parent / "ontology" / "units.yaml").read_text(encoding="utf-8"))["units"]:
        for v in [u["symbol"]] + list(u["variants"]):
            out.setdefault(str(v), u["dimension"])
    return out


def dimension_problem(q, unit, quals, dims):
    """P108: '' when a record's unit fits its quantity, else the mismatch. % and '1' (or no unit) are dimensionless; a signal quantity takes
    signal or dimensionless units; a count takes a count or no unit; a categorical takes no unit; a relative spread (stat relative_sd) is
    dimensionless whatever the quantity; an entry with definitions (P108 b) is checked against the definition the record's qualifier names,
    and a record without that qualifier is a problem."""
    e = L.ENTRIES.get(q)
    if not e:
        return f"no entry {q}"
    u = L.UNIT_ALIAS.get(unit, unit) if unit else ""                             # no unit stays no unit (the generated alias would read '' as the dimensionless '1')
    d = dims.get(u) if u else "dimensionless"
    if e["type"] == "categorical":
        return "" if not u else f"unit {unit!r} on a categorical"
    if quals.get("stat") in ("relative_sd",) and d == "dimensionless":
        return ""
    ed = e.get("dimension")
    if e.get("definitions"):
        did = quals.get("definition")
        dd = next((x for x in e["definitions"] if x["id"] == did), None)
        if not dd:
            return f"no definition qualifier (the entry has definitions {[x['id'] for x in e['definitions']]})"
        ed = dd.get("dimension") or dims.get(str(dd.get("unit", "")), "")
    if d is None:
        return f"unit {unit!r} not in units.yaml"
    if d == ed or (ed == "signal" and d in ("signal", "dimensionless")) or (ed == "count" and d in ("count", "dimensionless")):
        return ""
    return f"{d} vs {ed}"


def check_unit_table():
    """P122: every unit spelling the knowledge base uses resolves through the generated table (vocab.UNIT_BASE from ontology/units.yaml):
    every entry unit, every stored record unit on an ontology quantity (facts, cells, peaks, derived scalars, curve axes), every
    lists.DERIVED unit and every lists.UNITS value; the hand tables are gone from lists.py."""
    import json
    err, seen = [], set()
    ok = lambda u: (not u) or L.UNIT_ALIAS.get(u, u) in L.UNIT_BASE
    for q, e in L.ENTRIES.items():
        if e.get("unit") and not ok(str(e["unit"])):
            err.append(f"entry {q}: unit {e['unit']!r} is not in the unit table (P122)")
        for d in e.get("definitions") or []:
            if d.get("unit") and not ok(str(d["unit"])):
                err.append(f"entry {q}: definition unit {d['unit']!r} is not in the unit table (P122)")
    for pid in list(KEYS) + ["user"]:
        for f in rd(HERE / (f"{pid}.facts.csv" if pid != "user" else "user.facts.csv")):
            if "#" in f["fact_id"] and f["quantity"] in L.ENTRIES and f["unit"] and (f["value"] or f["value_min"] or f["value_max"]):
                seen.add(f["unit"])
                if not ok(f["unit"]):
                    err.append(f"{f['fact_id']}: unit {f['unit']!r} is not in the unit table (P122)")
    for pid in KEYS:
        p = HERE.parent / "kb" / f"{pid}.figures.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            for v in d.get("values", []) + d.get("derived", []):
                if v.get("quantity") in L.ENTRIES and v.get("unit") and not ok(v["unit"]):
                    err.append(f"{v['id']}: unit {v['unit']!r} is not in the unit table (P122)")
            for c in d.get("curves", []):
                for ax in ("x", "y"):
                    if c[ax].get("quantity") in L.ENTRIES and c[ax].get("unit") and not ok(c[ax]["unit"]):
                        err.append(f"{c['id']}: {ax} unit {c[ax]['unit']!r} is not in the unit table (P122)")
    for did, D in L.DERIVED.items():
        for u in [D["unit"]] + [i["unit"] for i in D["inputs"]]:
            if not ok(u):
                err.append(f"DERIVED {did}: unit {u!r} is not in the unit table (P122)")
    for q, u in L.UNITS.items():
        if not ok(u):
            err.append(f"UNITS[{q}]: {u!r} is not in the unit table (P122)")
    src = (HERE / "lists.py").read_text(encoding="utf-8")
    if "UNIT_BASE = {" in src or "UNIT_ALIAS = {" in src:
        err.append("lists.py still carries a hand unit table (P122)")
    print(f"== unit table (P122): {len(L.UNIT_BASE)} spellings in {len(L.DIMENSION_OF)} dimensions generated from units.yaml; {len(seen)} record spellings, {len(L.DERIVED)} derived definitions, {len(L.UNITS)} default units resolve")
    return err


def check_dimensions():
    """P108: every value record's unit matches its quantity's dimension (units.yaml): the facts' values (spread facts included), the
    imported figure values (cells, peaks), the derived scalars and both axes of every curve. A mismatch is fixed in the facts (rule a) or by
    an entry's definitions with their own units and the records' definition qualifier (rule b); never by a forced unit."""
    import json
    dims = unit_dimensions()
    err, n = [], 0
    for pid in list(KEYS) + ["user"]:
        for f in rd(HERE / (f"{pid}.facts.csv" if pid != "user" else "user.facts.csv")):
            q = f["quantity"]
            if "#" not in f["fact_id"] or not q or q == "other" or f["type"] in ("caveat", "claim") or not (f["value"] or f["value_min"] or f["value_max"]):
                continue
            n += 1
            m = dimension_problem(q, f["unit"], dict(p.split("=", 1) for p in f["qualifiers"].split(";") if "=" in p), dims)
            if m:
                err.append(f"{f['fact_id']}: {q} in {f['unit']!r}: {m} (P108)")
    for pid in KEYS:
        p = HERE.parent / "kb" / f"{pid}.figures.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for v in d.get("values", []) + d.get("derived", []):
            if v.get("quantity"):
                n += 1
                m = dimension_problem(v["quantity"], v.get("unit", ""), dict(x.split("=", 1) for x in str(v.get("qualifiers", "")).split(";") if "=" in x), dims)
                if m:
                    err.append(f"{v['id']}: {v['quantity']} in {v.get('unit')!r}: {m} (P108)")
        for c in d.get("curves", []):
            for ax in ("x", "y"):
                if c[ax].get("quantity"):
                    n += 1
                    m = dimension_problem(c[ax]["quantity"], c[ax].get("unit", ""), {}, dims)
                    if m:
                        err.append(f"{c['id']}: {ax} {c[ax]['quantity']} in {c[ax].get('unit')!r}: {m} (P108)")
    print(f"== dimensions (P108): {n} value records (facts, cells, peaks, derived, curve axes) against units.yaml; {sum(1 for e in L.ENTRIES.values() if e.get('definitions'))} entries with definitions")
    return err


def check_cycle():
    """P106: every experiment whose conditions state a hold (step=hold_A or hold_B) renders it on its dose line in detail(parts=recipe)
    ('…, then hold …') and in the settings table of pulse_time (values(result='pulse_time', paper)); no hold is a cycle step of its own."""
    import query as Q, tools
    err, n_ents, papers = [], 0, set()
    for k, T in Q.TREES.items():
        for e in Q.experiments(T):
            cond = Q.condition_records(T, e)
            if not any("step=hold_" in kk for kk in cond):
                continue
            n_ents += 1; papers.add(k)
            lines, er = tools.run_tool("detail", {"ids": [e], "parts": ["recipe"]})
            js = joined(lines)
            if er or not any(t.startswith("cycle step") and ", then hold " in t for _, t in js):
                err.append(f"detail({e}, recipe): the hold is not on its dose line (P106) {er}")
            if any(t.startswith("cycle step") and t.split(" · ", 1)[-1].startswith("hold") for _, t in js):
                err.append(f"detail({e}, recipe): a hold as a cycle step of its own (P106)")
        if k in papers:
            lines, er = tools.run_tool("values", {"result": "pulse_time", "paper": k})
            if er or not any(", then hold " in t for _, t in lines):
                err.append(f"values(pulse_time, {k}): no dose cell carries its hold (P106) {er}")
    print(f"== cycle (P106): {n_ents} experiments with a stated hold in {len(papers)} paper(s); the hold on the dose line in detail(recipe) and in the pulse_time settings table")
    return err


def check_multi_values():
    """P121: for every paper, values(result=[its three most populated quantities], paper) equals, block by block, the single calls' outputs
    without their legend and footer lines — or a block (never the first) is the one folded line naming how to open it; the legends and the
    footer come once at the end; a list with an unresolvable item renders the others and gives that item its nearest line."""
    import concept as CN, query as Q, tools
    err, n_folded, n_blocks = [], 0, 0
    pc = CN.counts()
    for k in Q.TREES:
        qs = [q for _, q in sorted(((d[k]["values"], q) for q, d in pc.items() if q in L.OUTPUTS and d.get(k, {}).get("values")), reverse=True)][:3]
        if len(qs) < 2:
            continue
        lines, e = tools.run_tool("values", {"result": qs, "paper": k})
        if e:
            err.append(f"values({qs}, {k}): {e} (P121)"); continue
        combined = [x for x in joined(lines) if x[0] != "more"]                 # wrapped continuations joined back (P44)
        texts = {t for _, t in combined}
        folded = {i + str(n): t for n, (i, t) in enumerate(combined) if i.endswith(":folded") and " — open with values(result=" in t}
        if any(i == "more" for i, _ in lines) and len(folded) < len(qs) - 1:
            err.append(f"values({qs}, {k}): over the budget with {len(qs) - 1 - len(folded)} block(s) still unfolded (P121)")
        singles = {}
        tools._CALL_BUDGET.append(tools.BUDGET_CHARS * min(len(qs), tools.LIST_BUDGET_MAX))   # P121b: the single calls under the list call's budget
        try:
            for q in qs:
                blocks, e1 = tools._run("values", {"result": q, "paper": k})
                singles[q], _ = tools.split_tail(tools.flat_lines(blocks))
        finally:
            tools._CALL_BUDGET.pop()
        budget = tools.BUDGET_TOKENS * min(len(qs), tools.LIST_BUDGET_MAX)       # P121b: k × the per-call budget; a block folds only when unfolding it would exceed the budget
        size = sum(len(t) + len(i) + 4 for i, t in lines) // 4
        if folded and not any(i == "more" for i, _ in lines):
            unfolded = size + sum(sum(len(t) + len(i) + 4 for i, t in singles[q]) // 4 for q in qs if any(t.startswith(f"{q}:") for t in folded.values()))
            if unfolded <= budget * 0.95:                                        # within 5 %: the page margin and the tail paginate reserves
                err.append(f"values({qs}, {k}): {len(folded)} block(s) folded although unfolded the call would be {unfolded} tokens, within its budget of {budget} (P121b)")
        if size > budget + 60:
            err.append(f"values({qs}, {k}): {size} tokens over the call's budget of {budget} (P121b)")
        for n, q in enumerate(qs):                                               # each block: the single call's lines (a text once per page, P44) or, past the first, one folded line
            n_blocks += 1
            if any(t.startswith(f"{q}:") for t in folded.values()):
                if n == 0:
                    err.append(f"values({qs}, {k}): the first block folded (P121)")
                n_folded += 1; continue
            if any(i == "more" for i, _ in lines) and n > 0:
                continue                                                        # beyond the first page
            missing = [t for _, t in joined(singles[q]) if t not in texts]
            if missing:
                err.append(f"values({qs}, {k}): block {n + 1} ({q}) lacks {len(missing)} line(s) of the single call (P121): {missing[0][:80]!r}")
        allowed = {t for b in singles.values() for _, t in joined(b)} | set(folded.values())
        stray = [t for i, t in combined if i not in ("legend", "between") and not t.startswith("caveat · ") and not t.startswith("kinds: (") and t not in allowed]
        if stray:
            err.append(f"values({qs}, {k}): {len(stray)} line(s) in no single call's output (P121): {stray[0][:80]!r}")
        if sum(1 for _, t in combined if t.startswith("kinds: (")) > 1 or sum(1 for i, _ in combined if i == "between") > 1:
            err.append(f"values({qs}, {k}): the legend or the footer appears more than once (P121)")
    lines, e = tools.run_tool("values", {"result": ["penetration depth", "no such thing"], "paper": "yim20"})
    if e or not any("nearest" in t for _, t in lines) or not any(i.startswith("yim20:") and i != "yim20:folded" for i, _ in lines):
        err.append(f"values(['penetration depth', 'no such thing'], yim20): the unresolvable item should get its nearest line and the other render (P121) {e}")
    print(f"== multi-quantity values (P121, P121b): {n_blocks} blocks over {len(Q.TREES)} papers' top-3 lists, {n_folded} folded to one line (18 of 36 before P121b); a list call's budget is k × {tools.BUDGET_TOKENS} tokens, at most {tools.LIST_BUDGET_MAX}×; legends and footer once")
    return err


def check_compare_runs():
    """P126: compare_runs.report on the repo's own small run file (pilot/runs/asks.jsonl) gives a markdown report with all six sections and
    no exception; a synthetic verdicts file joins on (file, arm, run, question order) and counts correctly, with the Wilson interval."""
    import compare_runs as CR, tempfile, csv as _csv
    err = []
    path = HERE / "runs" / "asks.jsonl"
    if not path.exists():
        print("== compare_runs (P126): pilot/runs/asks.jsonl missing, skipped"); return err
    try:
        md = CR.report([str(path)])
    except Exception as e:
        return [f"compare_runs: {type(e).__name__}: {e} (P126)"]
    for sec in ("## 1. Runs", "## 2. Cost and process", "## 3. Number and kind checks", "## 4. Stability", "## 5. Per question", "## 6. Summary"):
        if sec not in md:
            err.append(f"compare_runs: section {sec!r} missing (P126)")
    recs = CR.load(str(path)); qno = CR.question_numbers(recs)
    arms = sorted({r["arm"] for r in recs})
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=["question_no", "run_file", "arm", "run", "verdict", "note"]); w.writeheader()
        keys = list(dict.fromkeys((r["_file"], r["arm"], r.get("run", 1), qno[r["question"].strip()]) for r in recs))   # one verdict per join key (file, arm, run, question)
        verd = {k: CR.VERDICTS[n % len(CR.VERDICTS)] for n, k in enumerate(keys)}
        for k, v in verd.items():
            w.writerow(dict(question_no=k[3], run_file=k[0], arm=k[1], run=k[2], verdict=v, note="synthetic"))
        vpath = f.name
    try:
        md2 = CR.report([str(path)], vpath)
    except Exception as e:
        return err + [f"compare_runs with verdicts: {type(e).__name__}: {e} (P126)"]
    if "## 5b. Verdicts" not in md2 or "Wilson" not in md2:
        err.append("compare_runs: the verdict section or the Wilson interval is missing (P126)")
    want = collections.Counter(verd[(r["_file"], r["arm"], r.get("run", 1), qno[r["question"].strip()])] for r in recs)   # every record of a key carries its verdict
    row_sum = {v: 0 for v in CR.VERDICTS}
    for line in md2.split("## 5b. Verdicts", 1)[1].splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 + len(CR.VERDICTS) and cells[0].endswith(".jsonl"):
            for v, c in zip(CR.VERDICTS, cells[2:2 + len(CR.VERDICTS)]):
                row_sum[v] += int(c)
    if row_sum != dict(want):
        err.append(f"compare_runs: verdict counts {row_sum} against the synthetic file's {dict(want)} (P126)")
    if any(len(r.get("answer") or "") > 200 and (r.get("answer") or "")[:200] in md2 for r in recs):
        err.append("compare_runs: an answer body is copied into the report (P126)")
    if {"kb", "text"} <= set(arms):                                              # P127: anchor columns and one kb × text grid per run, summing to its questions
        runs = sorted({r.get("run", 1) for r in recs if r["arm"] in ("kb", "text")})
        if "anchors both / kb only / text only · papers both / kb only / text only" not in md2 or "## 5c. Per-question verdict agreement" not in md2:
            err.append("compare_runs: the anchor columns or section 5c is missing (P127)")
        else:
            blocks = md2.split("## 5c. Per-question verdict agreement", 1)[1].split("## 6.", 1)[0].split("(rows kb, columns text)")[1:]
            for run, b in zip(runs, blocks):
                total = sum(int(c) for l in b.splitlines() if l.startswith("| ") and not l.startswith("| kb") for c in l.strip("|").split("|")[1:])
                want = len({r["question"].strip() for r in recs if r["arm"] in ("kb", "text") and r.get("run", 1) == run})
                if total != want:
                    err.append(f"compare_runs: run {run} verdict grid counts {total} questions, {want} have a kb or text record (P127)")
            if len(blocks) != len(runs):
                err.append(f"compare_runs: {len(blocks)} verdict grids for {len(runs)} runs (P127)")
    print(f"== compare_runs (P126): report on {path.name} ({len(recs)} records, {len(qno)} questions, arms {', '.join(arms)}): six sections; synthetic verdicts join and count; anchor columns and one kb × text verdict grid per run (P127)")
    return err


def check_paper_index():
    """P117: every paper's quantity index (values(paper=k), detail(ids=[k])) is within the budget (no 'more' line), lists every quantity the
    concept cards count values for in the paper with the same count (P95 both ways), prints no value with an id, and ends with the two
    count lines."""
    import concept as CN, query as Q, tools
    err, size = [], 0
    pc = CN.counts()
    for k in Q.TREES:
        lines, e = tools.run_tool("values", {"paper": k})
        if e:
            err.append(f"values(paper={k}): {e} (P117)"); continue
        js = joined(lines)
        size = max(size, sum(len(t) + len(i) + 4 for i, t in lines) // 4)
        if any(i == "more" for i, _ in lines):
            err.append(f"values(paper={k}): over the budget (P117)")
        got = {m.group(1): int(m.group(2)) for _, t in js for m in [re.search(r"^\S.*? \((\w+)\) · (\d+) values", t)] if m}
        tail = next((t for _, t in js if t.startswith("+")), "")
        tail_ids = set(re.findall(r"\b([a-z0-9_]+)\b", tail.split(":", 1)[1])) if ":" in tail else set()
        want = {q: d[k]["values"] for q, d in pc.items() if q in L.ENTRIES and L.ENTRIES[q]["type"] in ("quantity", "categorical") and d.get(k, {}).get("values")}
        for q, n in want.items():
            if q in got and got[q] != n:
                err.append(f"values(paper={k}): {q} {got[q]} values in the index, {n} on the card (P117, P95)")
            if q not in got and q not in tail_ids:
                err.append(f"values(paper={k}): {q} has {n} values on the card and is not in the index (P117, P95)")
        for q in got:
            if q not in want:
                err.append(f"values(paper={k}): {q} in the index but no values on the card (P117, P95)")
        if any(re.search(r"\[\w+:\S+#\S+\]", t) for _, t in js):
            err.append(f"values(paper={k}): a value with its fact id in the index (P117)")
        for _, t in js:                                                          # P123: a single home holding every counted record prefixes the range
            m = re.search(r" · \d+ values \(([a-z-]+) \d+\)(?:, derived \d+)? · ([^·]+) · ", t)
            if m and m.group(1) in ("cited", "paper", "input") and not m.group(2).startswith(m.group(1) + ": ") and m.group(2).strip() not in ("categorical", "no numeric value"):
                err.append(f"values(paper={k}): {t[:60]!r}: the one home {m.group(1)} should prefix the range (P123)")
            if m and m.group(2).startswith(("cited: ", "paper: ", "input: ")) and not m.group(2).startswith(m.group(1) + ": "):
                err.append(f"values(paper={k}): {t[:60]!r}: the range names a home that is not the only one (P123)")
        if any("no numeric value" in t for _, t in js if not t.endswith("categorical")):
            for _, t in js:
                if "no numeric value" in t:
                    q = re.search(r"\((\w+)\) · ", t).group(1)
                    if any(Q.val(f) is not None for f in Q.TREES[k].rows if "#" in f["fact_id"] and f["quantity"] == q and f["type"] in Q.RESULT_TYPES + ("cited",)
                           and "stat=" not in f["qualifiers"] and f.get("data_kind") != "computed_by_kb"):   # the counted records: not a spread, not KB-computed
                        err.append(f"values(paper={k}): {q} reads 'no numeric value' although it has a numeric record (P122)")
        if not (js[-2][1].startswith("figure panels") and js[-1][1].startswith("model inputs")):
            err.append(f"values(paper={k}): the two closing count lines are missing (P117)")
        d_lines, e2 = tools.run_tool("detail", {"ids": [k]})
        if e2 or [t for _, t in d_lines] != [t for _, t in lines]:
            err.append(f"detail(ids=[{k}]) should return the same index as values(paper={k}) (P117) {e2}")
    print(f"== paper index (P117): {len(Q.TREES)} papers, max {size} tokens per index, at most {CN.INDEX_LINES} quantity lines; counts equal the concept cards' (P95 both ways)")
    return err


def check_conversions():
    """P109: every converts_to target and required quantity is an entry; every converted series of the imported curves cites a context
    record that exists in its paper's facts and names the required quantity; values() never renders a converted value."""
    import json, query as Q, tools
    err, n_decl, n_conv = [], 0, 0
    for q, e in L.ENTRIES.items():
        ct = e.get("converts_to")
        if ct:
            n_decl += 1
            err += [f"{q}: converts_to {x!r} is no entry (P109)" for x in (ct.get("target"), ct.get("requires")) if x not in L.ENTRIES]
    for pid, k in KEYS.items():
        p = HERE.parent / "kb" / f"{pid}.figures.json"
        if not p.exists():
            continue
        T = Q.TREES[k]
        for c in json.loads(p.read_text(encoding="utf-8")).get("curves", []):
            cv = c.get("converted")
            if not cv or not cv.get("context"):
                continue
            n_conv += 1
            f = T.byid.get(cv["context"])
            own = cv["context"] == c["id"] and cv["requires"] in (c.get("conditions") or {})   # the curve's own condition (series label) is its context
            if not own and (not f or f.get("quantity") != cv["requires"]):
                err.append(f"{c['id']}: converted series cites {cv['context']!r}, not a {cv['requires']} record of the paper (P109)")
            if cv.get("kind") != "computed_by_kb":
                err.append(f"{c['id']}: converted series kind {cv.get('kind')!r} (P109)")
        if n_conv:
            for q in {c["converted"]["quantity"] for c in json.loads(p.read_text(encoding="utf-8")).get("curves", []) if (c.get("converted") or {}).get("context")}:
                lines, _ = tools.run_tool("values", {"result": q, "paper": k})
                if any("converted" in t for _, t in lines):
                    err.append(f"values({q}, {k}) renders a converted series (P109)")
    print(f"== conversions (P109): {n_decl} entries with converts_to, {n_conv} converted curve series citing their context")
    return err


def check_comparability():
    """P53 (Sec. 18.4): for every output quantity, every pair of values of the same entry from two papers is judged by
    query.incomparable: comparable, or not with the axes named. A pair that cannot be judged (a specimen with no specimen class,
    a method with no class) is an error. Prints the counts per quantity."""
    import query as Q
    err, pairs = [], collections.defaultdict(lambda: [0, 0])
    vals = collections.defaultdict(list)                                        # entry id -> [(paper, key, record)]
    for k, T in Q.TREES.items():
        for e in Q.experiments(T):
            if Q.role(T, e) == "specimen" and not Q.specimen_class_of(T, e):
                err.append(f"{e}: a specimen without specimen_class (P53)")
            for key, x in Q.result_records(T, e).items():
                r = x["record"]
                if r.get("value") is None and not r.get("curve"):
                    continue
                q = key.split("{")[0].split("[")[0]
                if q in L.OUTPUTS:
                    if r.get("method") and r["method"] not in L.METHOD_CLASS:
                        err.append(f"{r.get('fact') or e}: method {r['method']!r} has no class (P53)")
                    vals[q].append((k, key, r))
    for q, vs in vals.items():
        for n, (pa, ka, ra) in enumerate(vs):
            for pb, kb, rb in vs[n + 1:]:
                if pa != pb and ka.split("{")[0] == kb.split("{")[0]:
                    pairs[q][1 if Q.incomparable(ka, ra, kb, rb) else 0] += 1
    print("== comparability (P53): cross-paper value pairs per output quantity, comparable / not: " +
          "; ".join(f"{q} {c[0]}/{c[1]}" for q, c in sorted(pairs.items())))
    return err


def check_cases():
    rows = rd(HERE / "paper_case.csv")
    left = [(k, r["paper_id"]) for r in rows for k in (f"c{i}" for i in range(1, 14)) if r.get(k, "").startswith("candidate")]
    return [f"paper_case.csv: {k} {p} is a candidate not resolved" for k, p in left] + ([] if rows else ["no paper_case.csv"])


if __name__ == "__main__":
    bad = 0
    err = check_vocabulary()
    print(f"== vocabulary: {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    check_claims()
    import sentence_only
    err = [f"{i}: {k} {x!r} only in prose (structure it, or allow it in sentence_only_allow.csv with a reason)" for i, k, x in sentence_only.report()]
    print(f"== sentence-only (P55): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_search()
    print(f"== search (P64): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_records()
    print(f"== records (P62): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_bases_sec19()
    print(f"== uncertainty bases (P60): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_mechanisms()
    print(f"== mechanisms (P82): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_structure()
    print(f"== structure (P78): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_cards()
    print(f"== cards (P81): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_cards_values()
    print(f"== card–values (P95): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_resolution()
    print(f"== resolution (P105): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_edges()
    print(f"== card edges (P101): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_grids()
    print(f"== grids (P80): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_homes()
    print(f"== homes (P79): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_calls()
    print(f"== calls (P75): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_settings()
    print(f"== settings tables (P76): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_sets()
    print(f"== set tables (P77): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_kinds()
    print(f"== kinds (P57, P68): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_map()
    print(f"== map (P70): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_caveats()
    print(f"== caveats (P56): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_comparability()
    print(f"== comparability (P53): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_bases()
    print(f"== bases (P52): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_unit_table()
    print(f"== unit table (P122): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_dimensions()
    print(f"== dimensions (P108): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_cycle()
    print(f"== cycle (P106): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_multi_values()
    print(f"== multi-quantity values (P121): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_compare_runs()
    print(f"== compare_runs (P126): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_paper_index()
    print(f"== paper index (P117): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    err = check_conversions()
    print(f"== conversions (P109): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
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
    err = check_figures_import()
    print(f"== figures import (P84-P87): {'OK' if not err else f'{len(err)} problems'}")
    for e in err[:40]:
        print("  ", e)
    bad += bool(err)
    check_figure_derived()
    import metrics
    metrics.report()                                                             # P59: the representation metrics, from the data
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
