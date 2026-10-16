"""Stage 2 helpers, shared by the per-paper <paper_id>.facts.py scripts and by check.py.

A <paper_id>.facts.py reads the paper itself (element texts from elements.py --text, figure crops) and states each fact:

    F(K, "s3.p2;fig9c.cap", "observation", "film thickness at the channel entrance is about 50 nm after 500 cycles",
      quantity="film_thickness", qualifiers="position=entrance", value="50", unit="nm", data_kind="measured",
      method="reflectometry", mentions="sample 8;H 500 nm")
    NK("s0.p1", "citation line")                 # an element with no knowledge, with the reason
    write(K, PID)                                # <pid>.facts.csv, <pid>.coverage.csv, <pid>.points.json

<pid>.facts.csv columns (one row per piece of knowledge; a fact stated in several elements is one row citing all of them):
  fact_id      <key>:<first evidence id>#<n>, stable while the element's facts keep their order
  type         lists.TYPES: setting | observation | derived | model | definition | claim | cited | comparison (tree rows: paper, activity, entity)
  kind         an activity's kind (lists.ACTIVITY_KINDS: recipe, deposition, anneal, plasma_treatment, measurement, simulation) or a
               comparison's kind (lists.COMPARISON_KINDS: series, grid, replicate)
  order        an activity's order among the activities applied to one entity (0 = before the deposition above it)
  how          stated | inferred, for an activity or an entity: whether the paper names it or the reader inferred it
  evidence     element ids, ";"-separated (the first one names the fact)
  statement    one line, own words
  quantity     an id of lists.QUANTITIES, or "other" with label_as_printed; blank for a claim without one
  qualifiers   k=v;k=v from lists.QUALIFIERS; a curve (points_ref) carries x=<quantity id>, its abscissa
  label_as_printed  the quantity's label or symbol as printed, when quantity is other (else optional)
  value, value_min, value_max, censor, unit   as printed in the element (no unit conversion in stage 2)
  value_text   a categorical value (pillar layout v2a, a substrate, a crystallinity class, a reactor name, an LHAR type) when the
               value is a name, not a number; the statement then names the setting without repeating the value
  points_ref   the name of a digitized curve in <pid>.points.json (only from points.json or accepted v1 points)
  data_kind    lists.DATA_KINDS (required with a value or points)
  method       a short id from lists.METHODS
  mentions     sample, series, condition, figure and reference labels written in the element, as printed, ";"-separated
  inputs       fact_ids this fact is computed or fitted from, when the element says so
  parent       (stage 3) one id: the row without which this fact would not exist; blank only for the paper row
  links        (stage 3) ids of a second home, ";"-separated: a claim's supporting facts, the same data shown twice
  stance       a claim's stance, lists.STANCES (asserted, hedged, open, limitation), from the paper's own wording
  cause, effect  a claim's variables, ";"-separated quantity ids or mechanism:<token> (lists.MECHANISMS); blank when the claim has none
  author       who wrote the fact down: the paper id for a paper's facts (write() fills it), "user" in user.facts.csv

Stage 3 makes each paper one tree inside its facts file. Tree rows have ids without "#" and are added with N():
  <key>                    type=paper, the root
  <key>:process            type=process, conditions shared by every run
  <key>:grp:<name>         type=group, a set of runs the paper names (a series, a reproducibility set, the simulations)
  <key>:run<n>, :sim:<k>   type=run, a deposition, a specimen or a simulation; qualifiers run=<kind>;how=stated|inferred;<key>=<v>
  <key>:refs:<n>           type=cited, a cited work (reference number n)
Tree rows do not count as facts and do not enter coverage.csv. A group row's first link is its purpose: the fact (the
paper's own sentence, a claim, observation, setting or model) that says what the group was made to test; purpose(gid, fid)
sets it.
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import elements  # noqa: E402

FIELDS = ["fact_id", "type", "kind", "order", "how", "evidence", "statement", "quantity", "qualifiers", "label_as_printed", "value", "value_min",
          "value_max", "censor", "unit", "value_text", "points_ref", "data_kind", "method", "mentions", "inputs", "parent", "links", "stance", "cause", "effect", "author"]
COV_FIELDS = ["element_id", "kind", "status", "fact_ids", "reason", "n_numbers", "n_numbers_reached"]

_facts, _nk, _count, _points = [], {}, {}, {}


def F(key, evidence, type_, statement, **kw):
    """Add one fact; returns its fact_id (use it in inputs= of later facts)."""
    ev = [e.strip() for e in evidence.split(";") if e.strip()]
    n = _count[ev[0]] = _count.get(ev[0], 0) + 1
    fid = f"{key}:{ev[0]}#{n}"
    row = {k: "" for k in FIELDS}
    row.update(fact_id=fid, type=type_, evidence=";".join(ev), statement=statement)
    for k, v in kw.items():
        if k not in FIELDS:
            raise KeyError(k)
        row[k] = ";".join(v) if isinstance(v, (list, tuple)) else str(v)
    _facts.append(row)
    return fid


def N(fid, type_, statement, parent, evidence="", **kw):
    """Add a tree row (paper, process, group, run or cited work); returns its id."""
    row = {k: "" for k in FIELDS}
    row.update(fact_id=fid, type=type_, statement=statement, parent=parent, evidence=evidence)
    for k, v in kw.items():
        if k not in FIELDS:
            raise KeyError(k)
        row[k] = ";".join(v) if isinstance(v, (list, tuple)) else str(v)
    _facts.append(row)
    return fid


def purpose(gid, fid):
    """Make fact fid the purpose of group row gid (its first link); the row and the fact must already exist."""
    row = next(r for r in _facts if r["fact_id"] == gid)
    assert any(r["fact_id"] == fid for r in _facts), fid
    rest = [l for l in row["links"].split(";") if l and l != fid]
    row["links"] = ";".join([fid] + rest)
    return fid


def facts():
    """The rows added so far (for a paper script's stage-3 pass)."""
    return _facts


# measurement methods: a setting or an observation with one of these sits under a measurement activity, never in a condition vector
MEAS_METHODS = {"reflectometry", "ellipsometry", "sem", "sem_eds", "tem", "xps", "raman", "xrd", "afm", "electrical", "rbs", "gravimetry",
                "photograph", "optical_microscopy", "process_monitor"}


def retree(key, process, deps, ents, sims=None, group_facts_to=None, drop_groups=(), extra=()):
    """Rebuild a paper's stage-3 tree under the activity/entity model from the old placement (process, runs, groups):
    paper -> recipe activity (the old process) -> deposition activities -> entities -> measurement activities -> facts.
      deps:  {dep_id: dict(statement, label, how, evidence[, parent, kind])}: the deposition (or other) activities to create; parent
             defaults to the recipe.
      ents:  {old_run_id: dict(dep, ent, parent, statement, label, how, evidence[, via])}: each old run maps to an activity `dep`
             (its settings go there) and, unless ent is None (the run was itself a deposition), to an entity `ent` under `parent`
             (a deposition or another entity: a piece); `via` = (activity id, kind) puts the run's measurement activities under a
             later treatment activity of the entity (an anneal).
      sims:  {old_run_id: dict(act, ent, parent, statement, label, evidence)}: a simulation activity with its model-run entity.
      group_facts_to: {group_id: node_id}: facts under that group move to the node (a group's shared inputs to a simulation activity,
             a cell group's ratio setting to its deposition); drop_groups: group rows deleted (their members merged into one entity).
      extra: rows to add as (id, type, statement, parent, kw).
    A setting with a measurement method, or any observation, derived or model fact under a run, goes under the entity's
    measurement activity of that method (<key>:meas:<entity>:<method>; "measurement" when the fact names none); a setting without
    one goes to the run's activity, or to the entity itself when several entities share that activity (the per-sample settings of
    one run that coated three samples: an entity's own settings are its properties and count in its condition vector). Shared settings and observations under the old process with a measurement method go to
    <key>:method:<method> (a measurement activity under the paper); the rest stay in the recipe. Group rows survive with
    parent = paper and links = purpose + members (old member runs mapped to their entities or activities); the old process and run
    rows are deleted."""
    sims = sims or {}
    group_facts_to = group_facts_to or {}
    byid = {r["fact_id"]: r for r in _facts}
    old_kids = {}                                        # the old parents and types, before any row is converted or re-parented
    old_type = {r["fact_id"]: r["type"] for r in _facts}
    for r in _facts:
        old_kids.setdefault(r["parent"], []).append(r["fact_id"])
    recipe = f"{key}:recipe"
    proc = byid[process]
    N(recipe, "activity", proc["statement"], key, evidence=proc["evidence"], kind="recipe", how="stated", label_as_printed=proc["label_as_printed"] or "recipe")
    made = set()

    def node(fid, type_, statement, parent, **kw):
        if fid not in made and fid not in byid:
            made.add(fid)
            N(fid, type_, statement, parent, **kw)
        return fid

    def meas(ent_or_act, suffix, method, under):
        return node(f"{key}:meas:{suffix}:{method}", "activity", f"{method} on {ent_or_act}", under, kind="measurement", how="stated",
                    label_as_printed=method.replace("_", " "))

    for d, spec in deps.items():
        if d in byid:                                        # an old run row that was itself the deposition: converted in place
            byid[d].update(type="activity", kind=spec.get("kind", "deposition"), how=spec["how"], label_as_printed=spec["label"],
                           parent=spec.get("parent", recipe), qualifiers=spec.get("qualifiers", ""), order=spec.get("order", ""))
            made.add(d)
        else:
            node(d, "activity", spec["statement"], spec.get("parent", recipe), evidence=spec.get("evidence", ""), kind=spec.get("kind", "deposition"),
                 how=spec["how"], label_as_printed=spec["label"], qualifiers=spec.get("qualifiers", ""), order=spec.get("order", ""))
    for r, spec in ents.items():
        if spec.get("ent"):
            node(spec["ent"], "entity", spec["statement"], spec["parent"], evidence=spec.get("evidence", ""), how=spec["how"], label_as_printed=spec["label"])
            if spec.get("via"):
                node(spec["via"][0], "activity", spec["via"][2], spec["ent"], kind=spec["via"][1], how="stated", label_as_printed=spec["via"][1],
                     evidence=spec.get("evidence", ""))
    for r, spec in sims.items():
        node(spec["act"], "activity", spec["statement"], spec.get("parent", key), evidence=spec.get("evidence", ""), kind="simulation", how="stated",
             label_as_printed=spec["label"], qualifiers=spec.get("qualifiers", ""))
        node(spec["ent"], "entity", f"model run of {spec['label']}", spec["act"], evidence=spec.get("evidence", ""), how="inferred", label_as_printed=spec["label"])
    for fid, type_, statement, parent, kw in extra:
        node(fid, type_, statement, parent, **kw)
    shared = {}
    for spec in ents.values():
        if spec.get("ent"):
            shared[spec["dep"]] = shared.get(spec["dep"], 0) + 1
    # re-parent the facts
    for f in _facts:
        if "#" not in f["fact_id"] or f["fact_id"] in made:
            continue
        par = f["parent"]
        if par == process:
            m = f["method"]
            if m in MEAS_METHODS and f["type"] in ("setting", "observation", "derived", "model"):
                f["parent"] = node(f"{key}:method:{m}", "activity", f"{m.replace('_', ' ')}: the shared measurement settings", key, kind="measurement",
                                   how="stated", label_as_printed=m.replace("_", " ") + " (method)")
            else:
                f["parent"] = recipe
        elif par in ents:
            spec = ents[par]
            m = f["method"] if f["method"] in MEAS_METHODS else ""
            if f["type"] == "setting" and not m:                     # a setting of the run: its deposition, or the entity itself when several entities share the deposition
                f["parent"] = spec["ent"] if spec.get("ent") and shared.get(spec["dep"], 0) > 1 else spec["dep"]
            else:
                suffix = (spec["ent"] or spec["dep"]).split(":", 1)[1]
                under = spec["via"][0] if spec.get("via") else (spec["ent"] or spec["dep"])
                f["parent"] = meas(spec["label"], suffix, m or "measurement", under)
        elif par in sims:
            spec = sims[par]
            f["parent"] = spec["act"] if f["type"] == "setting" else spec["ent"]
        elif par in group_facts_to:
            f["parent"] = group_facts_to[par]
    # groups: under the paper, members mapped
    old_runs = set(ents) | set(sims)

    def member(i):
        """An old member (a run, a group) as a new node: the run's entity or activity; a dropped group's entities; a group itself."""
        if i in ents:
            if ents[i]["ent"]:
                return [ents[i]["ent"]]
            return [s["ent"] for s in ents.values() if s.get("ent") and s["dep"] == i and s["parent"] == i] or [ents[i]["dep"]]   # a deposition: its entities
        if i in sims:
            return [sims[i]["ent"]]
        if i in drop_groups:
            return [m for c in old_kids.get(i, []) if old_type.get(c) in ("run", "group") for m in member(c)]
        return [i] if old_type.get(i) == "group" else []
    for g in [r for r in _facts if r["type"] == "group"]:
        if g["fact_id"] in drop_groups:
            continue
        links = [l for l in g["links"].split(";") if l]
        purpose_, rest = (links[:1], links[1:]) if links and "#" in links[0] else ([], links)
        members = [m for c in old_kids.get(g["fact_id"], []) if old_type.get(c) in ("run", "group") for m in member(c)] + [m for l in rest for m in member(l)]
        members = list(dict.fromkeys(m for m in members if m))
        g["parent"] = key
        g["links"] = ";".join(purpose_ + members)
    # links that named an old node now name its entity (or activity); the old process names the recipe
    remap = {process: recipe}
    for r, spec in ents.items():
        remap[r] = spec["ent"] or spec["dep"]
    for r, spec in sims.items():
        remap[r] = spec["ent"]
    for row in _facts:
        if row["links"]:
            row["links"] = ";".join(dict.fromkeys(remap.get(l, l) for l in row["links"].split(";") if l and l not in drop_groups))
    # delete the old process, run and dropped group rows
    gone = ({process} | old_runs | set(drop_groups)) - made
    _facts[:] = [r for r in _facts if r["fact_id"] not in gone]
    for r in _facts:
        if r["parent"] in gone:
            raise ValueError(f"{r['fact_id']} still under {r['parent']}")


def points():
    """The curves kept so far (name -> dict with points and the printed axis labels)."""
    return _points


def spread(fid, parents, labels):
    """A setting that governs several activities (a cycle count stated per temperature row, a thickness target stated for a set of
    films) goes on the first activity it governs; the others get a copy, a new fact citing the same elements, its statement and
    mentions prefixed by that activity's label (labels: {activity id: label}). A comparison holds no setting."""
    byid = {r["fact_id"]: r for r in _facts}
    src = byid[fid]
    src["parent"] = parents[0]
    key, ev0 = fid.split(":", 1)[0], src["evidence"].split(";")[0]
    for p in parents[1:]:
        row = dict(src)
        n = _count[ev0] = _count.get(ev0, 0) + 1
        row.update(fact_id=f"{key}:{ev0}#{n}", parent=p, statement=f"{labels.get(p, p)}: {src['statement']}",
                   mentions=";".join(filter(None, [src["mentions"], labels.get(p, p)])), links="")
        _facts.append(row)


def comparisons(key, table, members=None):
    """Turn the surviving group rows into comparison facts: id :grp: -> :cmp:, type comparison, kind and the varied quantity ids
    from table {group id: (kind, varied)}; links stay purpose + members (members={group id: [...]} overrides them); facts under the
    group go under the comparison; parents and links naming the group are remapped. An observation, derived or model fact under
    the recipe whose links name a member of a comparison moves under that comparison, as a fact spanning its members."""
    byid = {r["fact_id"]: r for r in _facts}
    remap, mem = {}, {}
    for g, (kind, varied) in table.items():
        row, new = byid[g], g.replace(":grp:", ":cmp:")
        links = [l for l in row["links"].split(";") if l]
        if members and g in members:
            links = links[:1] + list(members[g])
        row.update(fact_id=new, type="comparison", kind=kind, quantity=varied, parent=key, links=";".join(links), how="stated", qualifiers="")
        remap[g] = new
    for r in _facts:
        if r["parent"] in remap:
            r["parent"] = remap[r["parent"]]
        if r["links"]:
            r["links"] = ";".join(dict.fromkeys(remap.get(l, l) for l in r["links"].split(";") if l))
    for new in remap.values():
        mem[new] = set(byid[[g for g in remap if remap[g] == new][0]]["links"].split(";")[1:])
    recipe = f"{key}:recipe"
    for r in _facts:
        if r["parent"] == recipe and r["type"] in ("observation", "derived", "model") and r["links"]:
            ls = set(r["links"].split(";"))
            for c, ms in mem.items():
                if ls & ms:
                    r["parent"] = c
                    break


def NK(element_ids, reason):
    """Elements that hold no knowledge, with the reason; element_ids may be ';'-separated."""
    for e in element_ids.split(";"):
        if e.strip():
            _nk[e.strip()] = reason


def P(pid, name, points, source, x_label="", y_label="", note=""):
    """Keep a digitized curve for <pid>.points.json under its name; returns the points_ref (the name)."""
    if name in _points:
        raise KeyError(f"points {name} given twice")
    _points[name] = dict(source=source, x_label_as_printed=x_label, y_label_as_printed=y_label, note=note, points=points)
    return name


def cases_points(pid, figure, panel, series):
    """The points of one series of points.json (first match on paper, figure, panel and series label)."""
    for s in json.loads((HERE / "points.json").read_text(encoding="utf-8"))["series"]:
        if s["paper"] == pid and str(s["figure"]) == str(figure) and s["panel"] == panel and s["series"] == series:
            return s
    raise KeyError((figure, panel, series))


def v1_points(series_id):
    """Points of an accepted v1 curve (v1_points.json, accepted in v1_points_check.csv)."""
    ok = {r["pilot_series_id"] for r in csv.DictReader((HERE / "v1_points_check.csv").open(encoding="utf-8"))
          if r["decision"] == "accept"}
    if series_id not in ok:
        raise KeyError(f"{series_id} is not an accepted v1 curve")
    return json.loads((HERE / "v1_points.json").read_text(encoding="utf-8"))["series"][series_id]


def num(x):
    try:
        return float(str(x).replace("−", "-").replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def nums_of(text):
    out = set()
    for t in re.findall(r"[-−]?\d+(?:[.,]\d+)?(?:[eE][-−+]?\d+)?", text or ""):
        v = num(t.replace(",", ".") if re.fullmatch(r"[-−]?\d+,\d{1,2}", t) else t)
        if v is not None:
            out.add(round(abs(v), 9))
    return out


def reached(element_text, facts):
    """Numbers of an element (elements.numbers) and how many appear in a fact citing it (value, range, statement,
    mentions or label)."""
    have = set()
    for f in facts:
        for k in ("value", "value_min", "value_max", "statement", "mentions", "label_as_printed", "qualifiers"):
            have |= nums_of(f[k])
    ns = elements.numbers(element_text)
    hit = 0
    for t in ns:
        t2 = re.sub(r"\s*[×x]\s*10\^?\{?([-−]?\d+)\}?", r"e\1", t)
        v = num(t2) if num(t2) is not None else num(t2.replace(",", "."))
        if v is not None and round(abs(v), 9) in have:
            hit += 1
    return len(ns), hit


def write(key, pid):
    """<pid>.facts.csv, <pid>.coverage.csv and <pid>.points.json; elements without facts and without an NK reason are 'missed'."""
    for r in _facts:
        r["author"] = r["author"] or pid
    with (HERE / f"{pid}.facts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(_facts)
    (HERE / f"{pid}.points.json").write_text(json.dumps(_points, ensure_ascii=False, indent=0), encoding="utf-8")
    els = elements.load(pid)
    texts = elements.texts(pid)
    by_el = {}
    for r in _facts:
        if "#" not in r["fact_id"]:
            continue                                          # tree rows are not facts
        for e in r["evidence"].split(";"):
            by_el.setdefault(e, []).append(r)
    rows = []
    for e in els:
        eid = e["element_id"]
        fs = by_el.get(eid, [])
        nn, nr = reached(texts.get(eid, ""), fs) if e["kind"] != "panel" else ("", "")
        status = "covered" if fs else ("no knowledge" if eid in _nk else "missed")
        rows.append(dict(element_id=eid, kind=e["kind"], status=status, fact_ids=";".join(r["fact_id"] for r in fs),
                         reason=_nk.get(eid, "") if not fs else "", n_numbers=nn, n_numbers_reached=nr))
    with (HERE / f"{pid}.coverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COV_FIELDS); w.writeheader(); w.writerows(rows)
    import collections
    fs = [r for r in _facts if "#" in r["fact_id"]]
    print(pid, len(fs), "facts", dict(collections.Counter(r["type"] for r in fs)), "| tree rows", len(_facts) - len(fs),
          dict(collections.Counter(r["status"] for r in rows)))
