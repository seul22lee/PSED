#!/usr/bin/env python3
"""P144: the input a pass sees, rendered for pass 0 and (P148) pass 1. No model call.

    python3 psed_v2/kb/extract/render.py yli18          # prints the pass-0 input sizes

Parts: CODEBOOK.md whole; document.md whole; TABLES (each table's markdown as ingested, then its cell-id map "r<i>c<j> = <element
id>"); FIGURES (each figure's caption id, panel ids and every figures.json entry of it, one line each, P145: curves "curve id | panel | series
label | x | y | conditions" (no point data), cells "cell id | panel | at coordinates | quantity = value or value_text | unit |
conditions", peaks "peak id | panel | quantity = value | unit | label | conditions", sets "set id | panel | kind | varied | members",
derived "derived id | panel | quantity = value unit | from | method"); the element index; the example: the gold units and layouts of another dev paper in the pass-0 form, with the text of
the table rows and captions they come from beside them. gold_units() and gold_layouts() derive the gold side; the P144 report uses them.
P148: table() and figure() are the per-table and per-figure blocks of TABLES and FIGURES; group() renders one pass-1 group with them.
"""
import collections
import csv
import json
import re

import common as C

E = C.E


def codebook():
    return (C.SCHEMA / "CODEBOOK.md").read_text(encoding="utf-8")


def document(pid):
    return (C.V2 / "ingest" / "final" / pid / "document.md").read_text(encoding="utf-8")


def _tables(pid):
    """[(table id, caption id or '', markdown)] in elements.py order (numbered tab<n>, then unnumbered tabu<k>)."""
    st = json.loads((C.V2 / "ingest" / "final" / pid / "structure.json").read_text(encoding="utf-8"))
    out, k = [], 0
    for c in st["captions"]:
        if c["kind"] == "table" and c.get("number"):                            # P195 (user) A5: a decided header as the elements carry it
            out.append((f"tab{c['number']}", f"tab{c['number']}.cap", E.decided_table(pid, f"tab{c['number']}", c.get("table") or "")))
    for c in st["captions"]:
        if c["kind"] == "table" and not c.get("number") and c.get("table"):
            k += 1
            out.append((f"tabu{k}", "", c["table"]))
    return out


def table(tid, cap, md, ids):
    """One table: "TABLE <id> (caption <id>)", its markdown as ingested, its cell-id map (P148: one block, shared by pass 0 and pass 1)."""
    cells = []
    for i, line in enumerate(E.table_lines(md)):
        for j, cell in enumerate([x.strip() for x in line.strip().strip("|").split("|")]):
            if cell and f"{tid}.r{i}c{j}" in ids:
                cells.append(f"r{i}c{j} = {tid}.r{i}c{j}")
    return f"TABLE {tid}" + (f" (caption {cap})" if cap in ids else "") + "\n" + md.strip() + "\ncell ids: " + ", ".join(cells)


def tables(pid):
    ids = {r["element_id"] for r in E.load(pid)}
    return "\n\n".join(table(tid, cap, md, ids) for tid, cap, md in _tables(pid)) or "(no tables)"


def _figures_json(pid):
    p = C.V2 / "kb" / f"{pid}.figures.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _by_figure(pid):
    """figures.json entries by figure number: (curves, values, sets, derived, inventory); P184: the inventory (every panel, its type and
    what it shows)."""
    Fj = _figures_json(pid)
    by_fig, vals, sets, der, inv = (collections.defaultdict(list) for _ in range(5))
    for c in Fj.get("curves", []):
        by_fig[str(c["figure"])].append(c)
    for sec, d in (("values", vals), ("sets", sets), ("derived", der), ("inventory", inv)):
        for x in Fj.get(sec) or []:
            d[str(x["figure"])].append(x)
    return by_fig, vals, sets, der, inv


def figures(pid):
    rows = E.load(pid)
    text = E.texts(pid)
    F = _by_figure(pid)
    return "\n\n".join(figure(r["element_id"], text[r["element_id"]], rows, F) for r in rows
                        if r["kind"] == "caption" and r["element_id"].startswith("fig")) or "(no figures)"


def figure(cap, captext, rows, F):
    """One figure: its caption id and text, its panel ids, every figures.json entry of it (P148: one block, shared by pass 0 and
    pass 1)."""
    by_fig, vals, sets, der = F[:4]
    n = cap[3:].split(".")[0]
    panels = [x["element_id"] for x in rows if x["kind"] == "panel" and re.fullmatch(rf"fig{n}[a-z]*", x["element_id"])]
    lines = [f"FIGURE fig{n}: caption {cap}: {captext}", "panels: " + ", ".join(panels)]
    for inv in F[4].get(n, []) if len(F) > 4 else []:                       # P184 (user): every panel of figures.json, image panels included
        lines.append(f"panel fig{n}{inv.get('panel', '')} | {inv.get('panel_type', '')} | {inv.get('content', '')}")
    for c in by_fig.get(n, []):
        lines.append(f"curve {c['id']} | fig{n}{c.get('panel', '')} | {c.get('series', {}).get('label_raw', '')} | {c['x'].get('quantity', '')} | "
                     f"{c['y'].get('quantity', '')} | {_conds(c)}")
    for v in vals.get(n, []):                                               # P145: cells and peaks
        if v.get("kind") == "cell":
            at = "; ".join(f"{q}={x}" for q, x in (v.get("at") or {}).items())
            lines.append(f"cell {v['id']} | fig{n}{v.get('panel', '')} | at {at} | {v.get('quantity', '')} = "
                         f"{v['value'] if v.get('value') is not None else v.get('value_text', '')} | {v.get('unit', '')} | {_conds(v)}")
        else:
            lines.append(f"{v.get('kind', 'value')} {v['id']} | fig{n}{v.get('panel', '')} | {v.get('quantity', '')} = {v.get('value')} | {v.get('unit', '')} | "
                         f"label {v.get('label', '')} | {_conds(v)}")
    for st in sets.get(n, []):                                              # P145: sets (series, grid) with their members
        lines.append(f"set {st['id']} | fig{n}{st.get('panel', '')} | {st['kind']} | varied {st.get('varied', '')} ({st.get('varied_raw', '')}) | "
                     f"members {', '.join(st.get('members') or [])}")
    for d in der.get(n, []):                                                # P145: derived entries
        lines.append(f"derived {d['id']} | fig{n}{d.get('panel', '')} | {d.get('quantity', '')} = {d.get('value')} {d.get('unit', '')} | "
                     f"from {d.get('source', '')} | {d.get('method', '')}")
    return "\n".join(lines)


def strip_markup(t):
    """P148 (A2, C3): markup tags removed, their text kept (<sup>2</sup> -> 2; an autolink <https://...> is not a tag), ** removed."""
    return re.sub(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>", "", t).replace("**", "")


EQ_REF = r"(?:Eqs?\.?|Equations?)\s*\(?\s*{n}\s*\)?(?!\d)"                       # a paragraph that mentions printed equation n


def group(pid, key, rows, text, all_rows=None):
    """P148 (A2): one pass-1 group as the model reads it; the same table() and figure() blocks as pass 0. A section group: every
    element "id: text" (markup stripped). A table group: its caption "id: text", the table's markdown as ingested, the cell-id map
    and the legend line. A figure group: the figure block (caption id and text, panel ids, the figures.json entries, no points).
    An equation group: the equation "id: text", the paragraphs of its section that mention it, the symbol tables (tabu*) of the
    paper when there are any."""
    all_rows = all_rows or E.load(pid)
    line = lambda e: f"{e}: {strip_markup(text[e])}"                            # noqa: E731
    head = key.split(".")[0]
    if head.startswith("tab"):
        tb = {tid: (cap, md) for tid, cap, md in _tables(pid)}
        cap, md = tb[head]
        ids = {r["element_id"] for r in all_rows}
        caps = [line(r["element_id"]) for r in rows if r["kind"] == "caption"]
        return "\n".join(caps + [table(head, cap, md, ids), "r = row, c = column, r0 = header"])
    if re.fullmatch(r"fig\d+", head):
        cap = next(r["element_id"] for r in rows if r["kind"] == "caption")
        return figure(cap, strip_markup(text[cap]), all_rows, _by_figure(pid))
    if re.fullmatch(r"eq\d+", head):
        r0 = rows[0]
        m = re.search(r"printed \((\d+)\)", r0["locator"])
        num = m.group(1) if m else head[2:]
        paras = [r["element_id"] for r in all_rows if r["section"] == r0["section"] and r["kind"] == "paragraph"
                 and re.search(EQ_REF.format(n=num), text[r["element_id"]])]
        ids = {r["element_id"] for r in all_rows}
        sym = [table(tid, cap, md, ids) for tid, cap, md in _tables(pid) if tid.startswith("tabu")]
        return "\n".join([line(r["element_id"]) for r in rows] + (["paragraphs that mention it:"] + [line(e) for e in paras] if paras else [])
                         + (["symbol table:", *sym, "r = row, c = column, r0 = header"] if sym else []))
    return "\n".join(line(r["element_id"]) for r in rows)


def _conds(x):
    return "; ".join(f"{v.get('key_raw', q)}={v.get('raw', '')}" for q, v in (x.get("conditions") or {}).items())


def index(pid):
    return "\n".join(f"{r['element_id']}\t{r['kind']}\t{r['locator']}" for r in E.load(pid))


# ---------------------------------------------------------------------------------------------------------------- the gold side
def _gold(pid):
    return list(csv.DictReader((C.V2 / "kb" / "pilot" / f"{pid}.facts.csv").open(encoding="utf-8")))


def gold_units(pid):
    """The gold tree's experiment units: run = a deposition activity; specimen = an entity with a deposition above it; simulation = a
    simulation activity; model_run = an entity with a simulation above it. P145: a simulation under another simulation is collapsed
    into the top one (its model runs go to the top simulation; the top one is flagged gold_shape); a unit whose evidence is in no
    element of the paper is esi_only. [dict(gid, role, name, evidence, parent gid, esi_only, gold_shape)]."""
    rows = [r for r in _gold(pid) if "#" not in r["fact_id"]]
    R = {r["fact_id"]: r for r in rows}
    els = {r["element_id"] for r in E.load(pid)}

    def ups(r, kind):
        out, x = [], r["parent"]
        while x in R:
            if R[x]["type"] == "activity" and R[x]["kind"] == kind:
                out.append(x)
            x = R[x]["parent"]
        return out
    out, collapsed = [], collections.Counter()
    for r in rows:
        sims, deps = ups(r, "simulation"), ups(r, "deposition")
        if r["type"] == "activity" and r["kind"] == "simulation" and sims:
            collapsed[sims[-1]] += 1
            continue
        role = ("run" if r["type"] == "activity" and r["kind"] == "deposition" else "simulation" if r["type"] == "activity" and r["kind"] == "simulation"
                else "model_run" if r["type"] == "entity" and sims else "specimen" if r["type"] == "entity" and deps else "")
        if role:
            ev = [e for e in r["evidence"].split(";") if e]
            out.append(dict(gid=r["fact_id"], role=role, name=r["label_as_printed"], evidence=ev,
                            parent=deps[0] if role == "specimen" else sims[-1] if role == "model_run" else "", esi_only=bool(ev) and not (set(ev) & els)))
    for u in out:
        u["gold_shape"] = f"{collapsed[u['gid']]} nested simulation(s) collapsed" if collapsed.get(u["gid"]) else ""
    return out


def gold_curve_units(key):
    """{figures.json curve id: gold entity id} from the pilot tree (query.Tree binds a curve to the entity whose facts name its panel and
    series, P88). Note: importing query builds the trees of every paper of the index."""
    import query as Q
    T = Q.TREES[key]
    return {cid: T.byid[cid]["links"] for cid in T.curves if T.byid.get(cid, {}).get("links")}


def gold_layouts(pid, key):
    """The layouts the gold tree implies. Table: the gold entity (nearest entity above a fact) of every cell a fact cites; one entity
    per row, two or more rows -> row_per_unit; one per column -> column_per_unit; one per cell -> cell_per_unit; no entity -> not_units;
    else mixed. Panel: its curves' gold entities (gold_curve_units); all distinct -> curve_per_unit; all one -> panel_one_unit; map cells
    -> point_per_unit; no entity -> unbound."""
    G = _gold(pid)
    R = {r["fact_id"]: r for r in G}

    def ent(fid):
        x = R[fid]["parent"]
        while x in R:
            if R[x]["type"] == "entity":
                return x
            x = R[x]["parent"]
        return ""
    cell = collections.defaultdict(set)
    for f in G:
        if "#" not in f["fact_id"]:
            continue
        for e in f["evidence"].split(";"):
            m = re.fullmatch(r"(tabu?\w+?)\.r(\d+)c(\d+)", e)
            if m:
                cell[(m.group(1), int(m.group(2)), int(m.group(3)))].add(ent(f["fact_id"]))
    tl = []
    for tid, _, _ in _tables(pid):
        cs = {(i, j): es - {""} for (t, i, j), es in cell.items() if t == tid}
        withe = {k: v for k, v in cs.items() if v}
        minority = []
        if not withe:
            layout = "not_units"
        else:                                                                   # P145: the majority layout, the cells that do not fit it listed
            one = {k: next(iter(v)) for k, v in withe.items() if len(v) == 1}
            by_r, by_c = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
            for (i, j), e in one.items():
                by_r[i][e] += 1; by_c[j][e] += 1
            fit = {"row_per_unit": {k for k, e in one.items() if by_r[k[0]].most_common(1)[0][0] == e},
                   "column_per_unit": {k for k, e in one.items() if by_c[k[1]].most_common(1)[0][0] == e},
                   "cell_per_unit": {k for k, e in one.items() if sum(1 for x in one.values() if x == e) == 1}}
            if len(set(one.values())) < 2:
                fit = {"row_per_unit": set(one)}
            layout = max(fit, key=lambda x: (len(fit[x]), x == "row_per_unit"))
            minority = sorted(f"{tid}.r{i}c{j}" for (i, j) in withe if (i, j) not in fit[layout])
            if minority:
                layout += " (majority)"
        tl.append(dict(table=tid, layout=layout, units=sorted({e for v in withe.values() for e in v}) if withe else [], minority_cells=minority))
    cu = gold_curve_units(key)
    Fj = _figures_json(pid)
    by_panel = collections.defaultdict(list)
    for c in Fj.get("curves", []):
        by_panel[f"fig{c['figure']}{c.get('panel', '')}"].append(c["id"])
    cells = {f"fig{v['figure']}{v.get('panel', '')}" for v in Fj.get("values", []) if v.get("kind") == "cell"}
    pl = []
    for panel in sorted(set(by_panel) | cells):
        es = [cu.get(c, "") for c in by_panel.get(panel, [])]
        bound = [e for e in es if e]
        layout = ("point_per_unit" if panel in cells else "unbound" if not bound else "panel_one_unit" if len(set(bound)) == 1 and len(es) > 1
                  else "curve_per_unit" if len(set(bound)) == len(bound) else "mixed")
        pl.append(dict(panel=panel, layout=layout, units=sorted(set(bound))))
    return tl, pl


def _data_ids(y):
    return [d.get("id") if isinstance(d, dict) else d for d in (y.get("data") or y.get("curves") or [])]


def gold_run_conditions(pid):
    """{gold run id: {quantity: value}}: the settings on the run and on the entities below it (canonical units; value_text for a
    categorical value)."""
    import compile as K
    rows = _gold(pid)
    R = {r["fact_id"]: r for r in rows}

    def run_of(i):
        while i in R:
            if R[i]["type"] == "activity" and R[i]["kind"] == "deposition":
                return i
            i = R[i]["parent"]
        return ""
    out = collections.defaultdict(dict)
    for r in rows:
        if r["type"] == "setting" and r["quantity"] and (r["value"] or r["value_text"]):
            run = run_of(r["parent"])
            if run:
                out[run].setdefault(r["quantity"], K.canon(r) if r["value"] else r["value_text"].lower())
    return out


def unit_conditions(y, values):
    """A pass-0 unit's conditions from the figures.json cells its data names: the cell's at coordinates (canonical units of the
    quantity entry) and the cell's conditions (a range kept as (low, high))."""
    import compile as K
    import lists as L
    out = {}
    for c in _data_ids(y):
        v = values.get(c) or {}
        for q, x in (v.get("at") or {}).items():
            out.setdefault(q, K.canon(dict(value=str(x), unit=L.ENTRIES.get(q, {}).get("unit", ""), quantity=q)))
        for q, cd in (v.get("conditions") or {}).items():
            if cd.get("value") is None:
                continue
            lo = K.canon(dict(value=str(cd["value"]), unit=cd.get("unit") or "", quantity=q))
            hi = K.canon(dict(value=str(cd["value_max"]), unit=cd.get("unit") or "", quantity=q)) if cd.get("value_max") is not None else None
            out.setdefault(q, (lo, hi) if hi else lo)
    return out


def _agree(u, g):
    """A unit's condition (a canonical value, or a (low, high) range of canonical values) against a gold run's value."""
    try:
        if isinstance(u, tuple) and u and isinstance(u[0], tuple):              # a range
            lo, hi = u
            return lo[0] == g[0] and float(lo[1]) <= float(g[1]) <= float(hi[1])
        if isinstance(u, tuple) and isinstance(g, tuple):
            return u[0] == g[0] and abs(float(u[1]) - float(g[1])) <= 1e-6 * max(abs(float(g[1])), 1e-30)
        return u == g
    except (TypeError, ValueError, IndexError):
        return False


def compiled_units(pid, rows=None):
    """P186 (user): the experiment units of kb/compiled/<pid>.facts.csv in the pass-0 unit form, for pair_units: a run (a deposition
    activity), a specimen (an entity under a deposition or under a specimen; the compiler's films included), a simulation (a simulation
    activity), a model run (an entity under a simulation), a measurement (a measurement activity under one of those entities); name =
    the label, introduced_in = its evidence elements, parent = the nearest unit above, data = the points_ref of the facts under it (a
    run's or specimen's measurements included), method of a measurement; own = its settings (quantity, value)."""
    rows = list(csv.DictReader((C.V2 / "kb" / "compiled" / f"{pid}.facts.csv").open(encoding="utf-8"))) if rows is None else rows   # P188: or the rows given
    R = {r["fact_id"]: r for r in rows}
    kids = collections.defaultdict(list)
    for r in rows:
        kids[r["parent"]].append(r)
    role = {}
    for r in rows:
        if r["type"] == "activity" and r["kind"] == "deposition":
            role[r["fact_id"]] = "run"
        elif r["type"] == "activity" and r["kind"] == "simulation":
            role[r["fact_id"]] = "simulation"
    for r in rows:                                                              # entities: by the nearest activity above
        if r["type"] == "entity" and ":unit:" not in r["fact_id"]:
            x = r["parent"]
            while x in R and R[x]["type"] == "entity":
                x = R[x]["parent"]
            if role.get(x) == "run":
                role[r["fact_id"]] = "specimen"
            elif role.get(x) == "simulation":
                role[r["fact_id"]] = "model_run"
    for r in rows:
        if r["type"] == "activity" and r["kind"] == "measurement" and role.get(r["parent"]) in ("specimen", "model_run", "run"):
            role[r["fact_id"]] = "measurement"

    def up(i):
        x = R[i]["parent"]
        while x in R and x not in role:
            x = R[x]["parent"]
        return x if x in role else None

    def data(i):
        out = [c["points_ref"] for c in kids.get(i, []) if c["points_ref"]]
        for c in kids.get(i, []):
            if role.get(c["fact_id"]) == "measurement" and role[i] != "measurement":
                out += [x["points_ref"] for x in kids.get(c["fact_id"], []) if x["points_ref"]]
        return [dict(id=x, role=None) for x in dict.fromkeys(out)]
    return [dict(id=i, role=ro, name_as_printed=R[i]["label_as_printed"], parent=up(i), introduced_in=[e for e in R[i]["evidence"].split(";") if e],
                 data=data(i), method=R[i]["method"] or (i.split(":meas:")[-1] if ro == "measurement" else ""),
                 own=sorted({(c["quantity"], c["value"] or c["value_text"]) for c in kids.get(i, []) if c["type"] == "setting" and c["quantity"]}))
            for i, ro in role.items()]


def gold_measurements(pid, units):
    """P186: the gold measurement activities under a gold unit (gold_units) as units of role measurement: gid, name (the label), evidence
    (its own and that of the facts under it), parent (the unit), method."""
    rows = _gold(pid)
    ids = {u["gid"] for u in units}
    kids = collections.defaultdict(list)
    for r in rows:
        kids[r["parent"]].append(r)
    return [dict(gid=r["fact_id"], role="measurement", name=r["label_as_printed"], parent=r["parent"], esi_only=False, gold_shape="",
                 evidence=list(dict.fromkeys([e for e in r["evidence"].split(";") if e] + [e for c in kids.get(r["fact_id"], []) for e in c["evidence"].split(";") if e])),
                 method=r["method"] or (r["fact_id"].split(":")[-1] if ":meas:" in r["fact_id"] else r["label_as_printed"].replace(" ", "_")))   # P189: the id's method
            for r in rows if r["type"] == "activity" and r["kind"] == "measurement" and "#" not in r["fact_id"] and r["parent"] in ids]


def pair_units(pid, key, units, measurements=False):
    """P145-P147: gold units vs pass-0 units, per role, in stages; a unit linked at one stage is not linked again:
      data      a pass-0 unit whose data names a curve the gold binds to an entity (gold_curve_units) pairs with that entity;
      cell      P147: a pass-0 unit with figures.json cells pairs with the gold run whose every condition setting agrees with the
                unit's conditions or is absent from them (unit_conditions, gold_run_conditions); one to one, the best match first (the
                most agreeing conditions), so several gold runs at one grid point never merge into one unit;
      evidence  gold evidence and introduced_in share an element;
      tree      P147 (replaces equal names): a gold run and a pass-0 run pair when a specimen of one is paired with a specimen of the
                other; a gold simulation and a pass-0 simulation when one of their model runs is; both directions.
    ESI-only gold units are left out (listed apart). Returns dict(comps={role: [(gold units, pass-0 units, stages)]}, esi, pair_of,
    status_g, status_p, links)."""
    gc = gold_curve_units(key)
    bound = collections.defaultdict(set)
    for c, e in gc.items():
        bound[e].add(c)
    G = gold_units(pid)
    esi = [g for g in G if g["esi_only"]]
    G = [g for g in G if not g["esi_only"]]
    if measurements:                                                            # P186: the gold's measurements too (compiled units)
        G += gold_measurements(pid, G)
    Fj = _figures_json(pid)
    values = {v["id"]: v for v in Fj.get("values", [])}
    gcond = gold_run_conditions(pid)
    P = [y for y in units if y.get("role") in ("run", "specimen", "simulation", "model_run") + (("measurement",) if measurements else ())]
    edges, linked_g, linked_p = [], set(), set()

    def link(g, y, stage):
        edges.append((g["gid"], y["id"], stage))
    for stage in ("data", "cell", "evidence"):
        new_g, new_p = set(), set()
        if stage == "cell":
            cand = []
            for g in G:
                if g["role"] != "run" or g["gid"] in linked_g:
                    continue
                gv = gcond.get(g["gid"], {})
                for y in P:
                    if y["role"] != "run" or y["id"] in linked_p:
                        continue
                    uv = unit_conditions(y, values)
                    if not uv or not any(q in gv for q in uv):
                        continue
                    if all(q not in uv or _agree(uv[q], gv[q]) for q in gv):
                        cand.append((-sum(1 for q in gv if q in uv), g["gid"], y["id"], g, y))
            for _, gi, yi, g, y in sorted(cand, key=lambda x: (x[0], x[1], x[2])):
                if gi not in new_g and yi not in new_p:
                    link(g, y, "cell"); new_g.add(gi); new_p.add(yi)
        else:
            for g in G:
                if g["gid"] in linked_g:
                    continue
                for y in P:
                    if y["id"] in linked_p or y["role"] != g["role"]:
                        continue
                    hit = (bound.get(g["gid"], set()) & set(_data_ids(y))) if stage == "data" else (set(g["evidence"]) & set(y.get("introduced_in") or []))
                    if hit:
                        link(g, y, stage); new_g.add(g["gid"]); new_p.add(y["id"])
        linked_g |= new_g; linked_p |= new_p
    # tree: parents through paired children
    gpar = {g["gid"]: g["parent"] for g in G}
    ppar = {y["id"]: y.get("parent") for y in P}
    Gb, Pb = {g["gid"]: g for g in G}, {y["id"]: y for y in P}
    for gi, yi, st in list(edges):
        a, b = gpar.get(gi), ppar.get(yi)
        if a in Gb and b in Pb and Gb[a]["role"] == Pb[b]["role"] and a not in linked_g and b not in linked_p:
            link(Gb[a], Pb[b], "tree"); linked_g.add(a); linked_p.add(b)
    # P186 (user): parent + distinguishing condition: an unpaired gold unit pairs with the one unpaired unit of its role under a unit its
    # parent is paired with; among several, the one whose method (a measurement) or own settings (quantity, value) agree with the gold's
    gown = collections.defaultdict(set)
    for r in _gold(pid):
        if r["type"] == "setting" and r["quantity"]:
            gown[r["parent"]].add((r["quantity"], r["value"] or r["value_text"]))
    grew = True
    while grew:
        grew = False
        partners = collections.defaultdict(set)
        for gi, yi, _ in edges:
            partners[gi].add(yi)
        for g in G:
            if g["gid"] in linked_g or gpar.get(g["gid"]) not in partners:
                continue
            cands = [y for y in P if y["role"] == g["role"] and y["id"] not in linked_p and ppar.get(y["id"]) in partners[gpar[g["gid"]]]]
            if len(cands) > 1:
                cands = ([y for y in cands if y.get("method") and y["method"] == g.get("method")] if g["role"] == "measurement" else
                         [y for y in cands if set(map(tuple, y.get("own") or [])) & gown[g["gid"]]])
            if len(cands) == 1:
                link(g, cands[0], "parent"); linked_g.add(g["gid"]); linked_p.add(cands[0]["id"]); grew = True
    # components per role
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for gi, yi, _ in edges:
        parent[find(("g", gi))] = find(("p", yi))
    comps = collections.defaultdict(list)
    groups = collections.defaultdict(lambda: ([], [], set()))
    for g in G:
        groups[find(("g", g["gid"]))][0].append(g)
    for y in P:
        groups[find(("p", y["id"]))][1].append(y)
    for gi, yi, st in edges:
        groups[find(("g", gi))][2].add(st)
    pair_of, status_g, status_p, links = {}, {}, {}, []
    for gs, ps, sts in groups.values():
        role = (gs or ps)[0]["role"]
        kind = ("matched" if len(gs) == 1 and len(ps) == 1 else "missing" if not ps else "extra" if not gs else
                "merged" if len(ps) == 1 else "split" if len(gs) == 1 else "merged+split")
        comps[role].append((gs, ps, sorted(sts), kind))
        for g in gs:
            pair_of[g["gid"]] = [y["id"] for y in ps]; status_g[g["gid"]] = kind
        for y in ps:
            status_p[y["id"]] = kind
            links += [(y["id"], g["gid"]) for g in gs]
    return dict(comps=comps, esi=esi, pair_of=pair_of, status_g=status_g, status_p=status_p, links=links, bound=bound, gc=gc)


EXAMPLE_PER_ROLE = 3                                                            # P206b (user): the compact example's units per role
EXAMPLE_ROLES = ("run", "simulation", "specimen", "model_run", "measurement")    # parents before children


def example_units(U):
    """P206b (user): the compact example's gold units: per role (EXAMPLE_ROLES order) the first EXAMPLE_PER_ROLE units in gold order whose
    parent is none or a kept unit; returned in gold order."""
    keep = set()
    for role in EXAMPLE_ROLES:
        keep |= {u["gid"] for u in [u for u in U if u["role"] == role and (not u["parent"] or u["parent"] in keep)][:EXAMPLE_PER_ROLE]}
    return [u for u in U if u["gid"] in keep]


def example(pid, form):
    """One example in the pass-0 form: the gold units and layouts of the last dev paper in index order other than pid (never held-out)
    whose gold has runs, specimens, a simulation and model runs; ids role prefix + number; curves from gold_curve_units; then SOURCES:
    each unit's first evidence element with its text (a table row's cells joined, a caption), at most 40 words. Validated against
    form_pass0.json. P202 (user): every unit and layout is built from form_pass0.json's own item schema (every property present, the
    gold's value where the gold gives it, else null), so the example follows any later form version: a unit's id, role, name_as_printed,
    parent, introduced_in, data (its gold curves, simulated for a model run, else measured) and evidence_quote (the words of its first
    evidence element, as SOURCES gives them; the form never takes a null quote); a table layout's table, layout and units; a panel
    layout's panel, layout and unit. P204 (user, B1): also the gold's measurement units (gold_measurements: role measurement, method,
    parent); a unit whose gold label is not printed in its evidence elements has name_as_printed null and distinguished_by = its own
    settings whose values differ among its siblings (same parent, same role; all its own settings when it has none); a specimen's
    specimen_class and structure_class from the gold row's qualifiers; a run's recipe fields (reactant_A, reactant_B, carrier_gas,
    process_mode, material) from its own setting, else the nearest ancestor's single value (P190), each with a quote
    (pass1_elements._quote, else the words of the setting's evidence element as SOURCES gives them). A field is null only where the
    gold states nothing, or states it in no value the form takes (a quantity other, a method outside the form's list). P206b (user):
    compact: per role at most EXAMPLE_PER_ROLE units of the gold paper (example_units: parents before children, a unit only under a kept
    parent, gold order), every field present as before (distinguished_by still against all its gold siblings), the SOURCES lines of those
    units only, the layouts of those units' tables and panels only (a layout's units: the kept ones)."""
    from jsonschema import Draft202012Validator
    import compile as K
    import pass1_elements as P1
    PRE = {"run": "r", "simulation": "sim", "specimen": "s", "model_run": "m", "measurement": "meas"}
    item = lambda k: next(x for x in form["properties"][k].get("anyOf", [form["properties"][k]]) if x.get("type") == "array")["items"]["properties"]   # noqa: E731  P206b: units a plain array
    build = lambda k, gold: {f: gold.get(f) for f in item(k)}                    # noqa: E731
    for p in [p for p in reversed(list(E.PAPERS)) if p != pid and p not in C.HELD_OUT]:
        if not (C.V2 / "kb" / "pilot" / f"{p}.facts.csv").exists():             # P201: a paper with no gold (wer21, P171) gives no example
            continue
        U = gold_units(p)
        if not {"run", "specimen", "simulation", "model_run"} <= {u["role"] for u in U}:
            continue
        U = U + gold_measurements(p, U)                                         # P204 (user, B1)
        sib = collections.defaultdict(list)
        for u in U:
            sib[(u["parent"], u["role"])].append(u["gid"])
        U = example_units(U)                                                    # P206b (user): compact
        G = {r["fact_id"]: r for r in _gold(p)}
        own = collections.defaultdict(list)
        for r in G.values():
            if "#" in r["fact_id"] and r["type"] == "setting" and r["quantity"] and (r["value"] or r["value_text"]):
                own[r["parent"]].append(r)
        key = E.PAPERS[p]
        n, ids = collections.Counter(), {}
        for u in U:
            n[u["role"]] += 1
            ids[u["gid"]] = f"{PRE[u['role']]}{n[u['role']]}"
        cu = gold_curve_units(key)
        curves = collections.defaultdict(list)
        for c, e in cu.items():
            curves[e].append(c)
        text = E.texts(p)
        check = lambda e, q: K.normalize(q) in K.normalize(text.get(e, ""))   # noqa: E731  (as pass 1's examples)
        quals = lambda r: dict(x.split("=", 1) for x in (r.get("qualifiers") or "").split(";") if "=" in x)   # noqa: E731
        qids, methods = set(form["$defs"]["quantity_id"]["enum"]), set(next(x for x in item("units")["method"]["anyOf"] if "enum" in x)["enum"])

        def printed(u):
            return bool(u["name"]) and any(K.normalize(u["name"]).lower() in K.normalize(text.get(e, "")).lower() for e in u["evidence"])

        def distinguished(u):
            others = [g for g in sib[(u["parent"], u["role"])] if g != u["gid"]]
            vals = lambda g, q: {(r["value"] or r["value_text"], r["unit"]) for r in own[g] if r["quantity"] == q}   # noqa: E731
            out = [{"quantity": r["quantity"], "value": r["value"] or r["value_text"], "unit": r["unit"] or None} for r in own[u["gid"]]
                   if r["quantity"] in qids and (not others or any(vals(g, r["quantity"]) != vals(u["gid"], r["quantity"]) for g in others))]
            return out or None

        def recipe(gid):
            out = {}
            for f in ("reactant_A", "reactant_B", "carrier_gas", "process_mode", "material"):
                x, row = gid, None
                while x in G and row is None:
                    held = [r for r in own[x] if r["quantity"] == f]
                    if held:
                        row = held[0] if len({r["value_text"] or r["value"] for r in held}) == 1 else False
                    x = G[x]["parent"]
                if row:
                    out.update({f: row["value_text"] or row["value"], f + "_quote": P1._quote(row, text, check) or src(row["evidence"].split(";")[0])})
            return out

        def src(e):
            m = re.fullmatch(r"(tabu?\w+?)\.r(\d+)c\d+", e)
            t = " | ".join(text[x] for x in sorted(text, key=lambda x: x) if m and re.fullmatch(rf"{m.group(1)}\.r{m.group(2)}c\d+", x)) if m else text.get(e, "")
            return " ".join(t.split()[:40])
        unit_item = lambda u: build("units", {"id": ids[u["gid"]], "role": u["role"], "name_as_printed": u["name"] if printed(u) else None,   # noqa: E731
                                              "distinguished_by": None if printed(u) else distinguished(u), "parent": ids.get(u["parent"]),
                                              "introduced_in": u["evidence"] or None, "evidence_quote": src(u["evidence"][0]) if u["evidence"] else None,
                                              "data": [{"id": c, "role": "simulated" if u["role"] == "model_run" else "measured"} for c in curves.get(u["gid"], [])] or None,
                                              "method": u.get("method") if u["role"] == "measurement" and u.get("method") in methods else None,
                                              **({k: quals(G[u["gid"]]).get(k) for k in ("specimen_class", "structure_class")} if u["role"] == "specimen" else {}),
                                              **(recipe(u["gid"]) if u["role"] == "run" else {})})
        tl, pl = gold_layouts(p, key)
        obj = {"units": [unit_item(u) for u in U],
               "table_layouts": [build("table_layouts", {"table": t["table"], "layout": t["layout"].split()[0], "units": [ids[x] for x in t["units"] if x in ids] or None})
                                 for t in tl if not t["minority_cells"] and set(t["units"]) & set(ids)] or None,   # P206b: the kept units' tables only
               "panel_layouts": [build("panel_layouts", {"panel": x["panel"], "layout": x["layout"],
                                                         "unit": ids.get(x["units"][0]) if x["layout"] == "panel_one_unit" and x["units"] else None})
                                 for x in pl if x["layout"] in ("curve_per_unit", "panel_one_unit", "point_per_unit") and set(x["units"]) & set(ids)] or None}   # P206b: their panels only
        errs = list(Draft202012Validator(form).iter_errors(obj))
        if errs:
            continue
        sources = "\n".join(f"{ids[u['gid']]} <- {u['evidence'][0]}: {src(u['evidence'][0])}" for u in U if u["evidence"])
        return f"(paper {key})\n" + json.dumps(obj, ensure_ascii=False) + "\nSOURCES (the element each unit comes from):\n" + sources
    return "(no example)"


if __name__ == "__main__":
    import sys
    pid, key = C.resolve(sys.argv[1])
    form = C.schema("form_pass0.json")
    for name, t in (("codebook", codebook()), ("document", document(pid)), ("tables", tables(pid)), ("figures", figures(pid)), ("index", index(pid)),
                    ("example", example(pid, form))):
        print(f"{name}: {len(t)} chars, ~{len(t) // 4} tokens")
