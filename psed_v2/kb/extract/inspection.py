#!/usr/bin/env python3
"""P174 step 5 (user): the no-gold inspection of one paper (0 calls), a standard section of every run report (grow.py run). It reads what
the run wrote (kb/records, kb/compiled, kb/<pid>.figures.json, kb/import_panels.csv, ontology/) and writes kb/reports/<prefix>.5a.csv ...:
  5a coverage by element: every element of elements.csv with its group (section, figure or table), the pass-1 answer (its records, or
     the NK reason), the facts compiled at it (coverage.csv), the records dropped at it (dropped.csv) and a class: covered / records
     dropped (step: reason) / records, no fact here (merged, or placed at another element) / no record (the NK reason) / not answered.
  5b drops by step: every dropped.csv row.
  5c unmapped by kind: every open label of compile's unmapped.csv (quantity, species, material, structure, method, model, axis, unit,
     categorical value) with its evidence (element, label, definition) and the never.csv category that covers it, if any.
  5d units: the pass-0 units and the units derived from curves (compile.curve_units) per panel; the panel consistency (pass0_paper:
     unbound items); the simulation and its model link; the units no record is about; the records about the paper.
  5e figures: per data panel the verdict and flags, every label and how it resolved, curves and values, the units that hold them, facts.
  5f check.py problems: every problem with its class (score.err_class).
  5g partial gold: every ontology.yaml evidence item citing the paper (entry, the paper's locator: 'Sec. II D', 'Fig. 12', 'Table I')
     read as elements (a section by the numbering of its heading elements, a figure or a table by its element ids), and whether a compiled
     fact of that entry sits at those elements: yes / other entry / none.
  5h gaps seen first: every value of 5a-5f that no other compiled paper showed (unmapped field and action, drop step and reason, figure
     flag and label outcome, compile step counter, check.py problem class).

    python3 psed_v2/kb/extract/inspection.py <paper> [--prefix RUN_<key>]
"""
import argparse
import collections
import csv
import json
import re
import sys

import yaml

import common as C
import compile as K
import pass0_paper as P0
import score as S

REPORTS = C.V2 / "kb" / "reports"
SECTIONS = ("5a", "5b", "5c", "5d_units", "5d_consistency", "5d_simulation", "5d_no_record", "5d_about_paper", "5e", "5f", "5g", "5h")
TITLES = {"5a": "5a. Coverage by element (every element)", "5b": "5b. Drops by step (every dropped record)", "5c": "5c. Unmapped by kind (every open label)",
          "5d_units": "5d. Units: pass 0 and derived from curves", "5d_consistency": "5d. Units: panel consistency (pass0_paper)",
          "5d_simulation": "5d. Units: the simulation and its model link", "5d_no_record": "5d. Units no record is about",
          "5d_about_paper": "5d. Records whose about is the paper", "5e": "5e. Figures: per data panel", "5f": "5f. check.py problems by class (every row)",
          "5g": "5g. The pilot's evidence as a partial gold", "5h": "5h. Gaps seen first in this paper"}
ROMAN = re.compile(r"^\s*([IVX]+)\.\s")
LETTER = re.compile(r"^\s*([A-H])\.\s")


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def write(prefix, sec, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
    with (REPORTS / f"{prefix}.{sec}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(rows)


def group_of(e):
    m = re.match(r"(fig\d+|tab[A-Za-z0-9]+)", e["element_id"])
    return m.group(1) if e["section"] in ("figures", "tables") and m else e["section"]


def kind_of(field):
    """5c: an unmapped row's kind from its field."""
    if field in ("quantity", "axis", "unit", "model", "method"):
        return field
    return K.SPECIES_KIND.get(field) or ("categorical value" if field in K.VALUES else field)


def fact_entries(f):
    """The ids a fact row names: quantity, method, value_text, qualifier values, cause and effect."""
    ids = {f["quantity"], f["method"], f["value_text"]} | {q.split("=", 1)[1] for q in f["qualifiers"].split(";") if "=" in q}
    ids |= set(f["cause"].split(";")) | set(f["effect"].split(";"))
    return {i for i in ids if i}


def evidence_keys():
    """{evidence key: paper id} from ontology.yaml's header ('Werbrouck2021 = 10.1116_6.0001094')."""
    head = [l for l in (C.V2 / "ontology" / "ontology.yaml").read_text(encoding="utf-8").splitlines()[:8] if l.startswith("#")]
    return {k: v.rstrip(".,") for k, v in re.findall(r"([A-Z][A-Za-z]+\d{4}) = (10\.[^\s,]+)", " ".join(head))}


def locator_elements(loc, els, texts):
    """5g: the elements of a locator: 'Sec. II D' (the section whose heading numbering is II, then D), 'Sec. II', 'Fig. 12',
    'Figs. 11-14', 'Table I'. Returns (element ids, how)."""
    m = re.match(r"Sec\.\s*([IVX]+)(?:\s+([A-H]))?\b", loc)
    if m:
        num, cur, sec_num = {}, ("", ""), {}
        for e in els:
            if e["kind"] == "heading":
                t = texts.get(e["element_id"], "")
                if ROMAN.match(t):
                    cur = (ROMAN.match(t).group(1), "")
                elif LETTER.match(t) and cur[0]:
                    cur = (cur[0], LETTER.match(t).group(1))
                sec_num[e["section"]] = cur
            num[e["element_id"]] = sec_num.get(e["section"], ("", ""))
        want = (m.group(1), m.group(2) or "")
        ids = [i for i, n in num.items() if n[0] == want[0] and (not want[1] or n[1] == want[1])]
        return ids, f"section numbered {' '.join(x for x in want if x)} (heading elements)"
    m = re.match(r"Figs?\.\s*(\d+)(?:\s*[-–]\s*(\d+))?", loc)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        ids = [e["element_id"] for e in els if (k := re.match(r"fig(\d+)(?:[a-z]+)?(?:\.cap)?$", e["element_id"])) and lo <= int(k.group(1)) <= hi]
        return ids, f"figure{'s' if hi > lo else ''} {lo}{'-' + str(hi) if hi > lo else ''} (element ids)"
    m = re.match(r"Table\s+([IVX]+|\d+)", loc)
    if m:
        ids = [e["element_id"] for e in els if re.match(rf"tab{m.group(1)}(\.|$)", e["element_id"])]
        return ids, f"table {m.group(1)} (element ids)"
    return [], "locator not read"


def inspect(pid, prefix):
    out = {}
    els = C.E.load(pid)
    texts = C.E.texts(pid)
    run = K.Run(pid)
    recs = run.read()
    facts = rd(K.OUT / f"{pid}.facts.csv")
    cover = {r["element_id"]: r for r in rd(K.OUT / f"{pid}.coverage.csv")}
    dropped = rd(K.OUT / f"{pid}.dropped.csv")
    unm = rd(K.OUT / f"{pid}.unmapped.csv")
    prom = rd(K.OUT / f"{pid}.promoted.csv")
    drops_at = collections.defaultdict(list)
    for d in dropped:
        drops_at[d["element"]].append(f"{d['step']}: {d['reason']}" + (f" ({d['field']})" if d["field"] else ""))
    # 5a
    rows = []
    for e in els:
        i = e["element_id"]
        a = run.answers.get(i)
        fids = [x for x in (cover.get(i, {}).get("fact_ids") or "").split(";") if x]
        if fids:
            cls = "covered"
        elif a is None:
            cls = "not answered (no pass-1 answer)"
        elif isinstance(a, str):
            cls = f"no record ({a.removeprefix('NK:')})"
        elif not a:
            cls = "no record (empty answer)"
        elif drops_at.get(i):
            cls = "records dropped (" + "; ".join(sorted(set(drops_at[i]))) + ")"
        else:
            cls = "records, no fact here (merged, or placed at another element)"
        rows.append(dict(group=group_of(e), element=i, kind=e["kind"], records=len(a) if isinstance(a, list) else 0, answer="records" if isinstance(a, list) else (a or ""),
                         facts=len(fids), fact_ids=";".join(fids), dropped="; ".join(drops_at.get(i, [])), coverage_status=cover.get(i, {}).get("status", ""), cls=cls))
    out["5a"] = rows
    # 5b, 5c
    out["5b"] = [dict(step=d["step"], reason=d["reason"], field=d["field"], element=d["element"], type=d["type"], quantity=d["quantity"])
                 for d in sorted(dropped, key=lambda d: (d["step"], d["reason"], run.order.get(d["element"], 0)))]
    rows = []
    for u in unm:
        cand = json.loads(u["candidate"]) if u["candidate"].startswith("{") else {}
        rows.append(dict(kind=kind_of(u["field"]), field=u["field"], element=u["element"], label=u["label_as_printed"], unit=u["unit"], id=u["id"],
                         definition=" ".join(str(cand.get("definition_quote") or cand.get("label_raw") or "").split()), action=u["action"],
                         never=u.get("never", "") or "no"))
    out["5c"] = sorted(rows, key=lambda r: (r["kind"], r["label"].casefold(), run.order.get(r["element"], 0)))
    # 5d
    own = [u for u in run.pass0 if isinstance(u, dict) and not str(u.get("origin", "")).startswith("derived")]   # Run.read() appends the derived units
    derived = [u for u in run.pass0 if isinstance(u, dict) and str(u.get("origin", "")).startswith("derived")]
    p0obj = dict(units=own, **run.layouts)
    abouts = collections.Counter(r["rec"].get("about") for r in recs if not r.get("origin"))           # pass-1 records
    conds = collections.Counter(r["rec"].get("about") for r in recs if r.get("origin"))                # the legend conditions compile makes
    out["5d_units"] = [dict(origin="pass 0", unit=u.get("id"), role=u.get("role"), name_as_printed=u.get("name_as_printed") or "", parent=u.get("parent") or "", panel="",
                            data=len(u.get("data") or []), records_about=abouts.get(u.get("id"), 0), conditions_from_legend=0, flag="") for u in own] + \
        [dict(origin=u["origin"], unit=u["id"], role=u["role"], name_as_printed=u["name_as_printed"] or "", parent=u["parent"] or "", panel=u["panel"], data=len(u["data"]),
              records_about=abouts.get(u["id"], 0), conditions_from_legend=conds.get(u["id"], 0), flag="; ".join(x for x in (u.get("flag", ""), u.get("merge", "")) if x)) for u in derived]
    cons = P0.consistency(pid, p0obj)
    out["5d_consistency"] = [{k: (";".join(v) if isinstance(v, list) else v) for k, v in r.items()} for r in cons]
    sims = []
    for u in own:
        if u.get("role") == "simulation":
            nm = (u.get("name_as_printed") or "").strip()
            p = next((x for x in prom if x["field"] == "model" and x["printed"].strip() == nm), None)
            q = next((x for x in unm if x["field"] == "model" and x["label_as_printed"].strip() == nm), None)
            sims.append(dict(unit=u["id"], name_as_printed=nm, model_entry=p["id"] if p else "(no entry)", how=(p or {}).get("lookup", "") or (q or {}).get("action", ""),
                             model_runs=sum(1 for v in own + derived if v.get("parent") == u["id"]), records_about=abouts.get(u["id"], 0)))
    out["5d_simulation"] = sims
    out["5d_no_record"] = [r for r in out["5d_units"] if not r["records_about"]]     # no pass-1 record about it (legend conditions aside)
    out["5d_about_paper"] = [dict(element=r["eid"], type=r["rec"].get("type", ""), quantity=r["rec"].get("quantity", "") if isinstance(r["rec"].get("quantity"), str) else ";".join(r["rec"].get("quantity") or []),
                                  label=r["rec"].get("label_as_printed", "") or "") for r in recs if r["rec"].get("about") == "paper"]
    # 5e
    Fj = json.loads((C.V2 / "kb" / f"{pid}.figures.json").read_text(encoding="utf-8")) if (C.V2 / "kb" / f"{pid}.figures.json").exists() else {}
    panels = {(r["figure"], r["panel"]): r for r in rd(C.V2 / "kb" / "import_panels.csv") if r["paper"] == pid}
    holders = collections.defaultdict(list)
    for u in own + derived:
        for d in u.get("data") or []:
            holders[d.get("id") if isinstance(d, dict) else d].append(u["id"])
    rows = []
    for inv in Fj.get("inventory", []):
        pr = panels.get((inv["figure"], inv["panel"]))
        if not pr:
            continue
        ids = [c["id"] for c in Fj.get("curves", []) + Fj.get("values", []) if c["figure"] == inv["figure"] and c.get("panel", "") == inv["panel"]]
        labs = "; ".join(f"{x['axis']} '{x['key']}' -> {x['quantity']}" + (f" (never: {x['never']})" if x.get("never") else f" (ambiguous: {', '.join(x['ambiguous'])})" if x.get("ambiguous") else "")
                         + (f" [{x['unit_reason']}]" if x.get("unit_reason") else "") for x in inv.get("labels") or [])
        rows.append(dict(panel=inv["id"], type=inv["panel_type"], verdict=pr["verdict"], flags=pr["flags"], flagged=";".join(inv.get("flagged") or []), labels=labs,
                         curves=sum(1 for c in Fj.get("curves", []) if c["figure"] == inv["figure"] and c["panel"] == inv["panel"]),
                         values=sum(1 for c in Fj.get("values", []) if c["figure"] == inv["figure"] and c.get("panel", "") == inv["panel"]),
                         units_holding=";".join(sorted({h for i in ids for h in holders.get(i, [])})), data_no_unit=sum(1 for i in ids if not holders.get(i)),
                         facts=sum(1 for f in facts if f["points_ref"] in ids), outcome=pr["outcome"], reason=pr["reason"]))
    out["5e"] = rows
    # 5f
    errs = S.check_dir(pid)[0]
    out["5f"] = sorted([dict(cls=S.err_class(e), problem=e) for e in errs], key=lambda r: (r["cls"], r["problem"]))
    # 5g
    ek = {v: k for k, v in evidence_keys().items()}.get(pid)
    onto = yaml.safe_load((C.V2 / "ontology" / "ontology.yaml").read_text(encoding="utf-8"))
    rows = []
    for e in onto["entries"] if ek else []:
        for ev in e.get("evidence") or []:
            if not str(ev).startswith(ek + " "):
                continue
            loc = str(ev)[len(ek) + 1:]
            ids, how = locator_elements(loc, els, texts)
            at = [f for f in facts if set(f["evidence"].split(";")) & set(ids)]
            hit = [f for f in at if e["id"] in fact_entries(f)]
            pm = [x for x in prom if x["id"] == e["id"] and x["element"] in ids]
            res = "yes" if hit or pm else "other entry" if at else "none"
            rows.append(dict(entry=e["id"], type=e.get("type", ""), evidence=str(ev), elements=len(ids), read_as=how, result=res,
                             facts=";".join(f["fact_id"] for f in hit) or (";".join(f"promoted {x['field']} at {x['element']}" for x in pm) if pm else ""),
                             other_entries=";".join(sorted({i for f in at for i in fact_entries(f)} - {e["id"]}))[:300] if res == "other entry" else ""))
    out["5g"] = rows
    # 5h
    others = [p for p in C.E.PAPERS if p != pid and (K.OUT / f"{p}.facts.csv").exists()]
    seen = collections.defaultdict(set)
    for p in others:
        for u in rd(K.OUT / f"{p}.unmapped.csv"):
            seen["unmapped field | action"].add(f"{u['field']} | {re.sub(r'[:(].*', '', u['action']).strip()}")
        for d in rd(K.OUT / f"{p}.dropped.csv"):
            seen["drop step: reason"].add(f"{d['step']}: {d['reason']}")
        for r in rd(K.OUT / f"{p}.summary.csv"):
            if r["metric"].startswith("step_"):
                seen["compile step counter"].add(r["metric"])
        F2 = json.loads((C.V2 / "kb" / f"{p}.figures.json").read_text(encoding="utf-8")) if (C.V2 / "kb" / f"{p}.figures.json").exists() else {}
        for inv in F2.get("inventory", []):
            seen["figure flag"] |= set(inv.get("flags") or [])
            for x in inv.get("labels") or []:
                seen["figure label outcome"].add(label_outcome(x))
        cd = sorted(REPORTS.glob(f"*.{C.E.PAPERS[p]}.check_dir.csv"), key=lambda q: q.stat().st_mtime)
        for r in rd(cd[-1]) if cd else []:
            seen["check.py problem class"].add(S.err_class(r["problem"]))
    mine = collections.defaultdict(collections.Counter)
    for u in unm:
        mine["unmapped field | action"][f"{u['field']} | {re.sub(r'[:(].*', '', u['action']).strip()}"] += 1
    for d in dropped:
        mine["drop step: reason"][f"{d['step']}: {d['reason']}"] += 1
    for r in rd(K.OUT / f"{pid}.summary.csv"):
        if r["metric"].startswith("step_"):
            mine["compile step counter"][r["metric"]] += int(r["value"]) if str(r["value"]).isdigit() else 1
    for inv in Fj.get("inventory", []):
        for fl in inv.get("flags") or []:
            mine["figure flag"][fl] += 1
        for x in inv.get("labels") or []:
            mine["figure label outcome"][label_outcome(x)] += 1
    for r in out["5f"]:
        mine["check.py problem class"][r["cls"]] += 1
    out["5h"] = [dict(area=a, value=v, count=n, other_papers_compared=len(others)) for a, c in mine.items() for v, n in sorted(c.items()) if v not in seen[a]]
    for sec in SECTIONS:
        write(prefix, sec, out.get(sec, []))
    return out


def label_outcome(x):
    return f"{x['axis']}: " + ("never" if x.get("never") else "ambiguous" if x.get("ambiguous") else "other" if x["quantity"] == "other" else "resolved") \
        + (f", {x['unit_reason']}" if x.get("unit_reason") else "")


def parts(prefix):
    """(title, path) of each section file, for kb/report.py."""
    return [(TITLES[s], REPORTS / f"{prefix}.{s}.csv") for s in SECTIONS if (REPORTS / f"{prefix}.{s}.csv").exists()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("paper")
    ap.add_argument("--prefix", default="")
    a = ap.parse_args(argv)
    pid, key = C.resolve(a.paper)
    out = inspect(pid, a.prefix or f"RUN_{key}")
    cls = collections.Counter(r["cls"].split(" (")[0] for r in out["5a"])
    print(f"{key} inspection: {len(out['5a'])} elements {dict(cls)}; {len(out['5b'])} drops; {len(out['5c'])} open labels; "
          f"{len(out['5d_units'])} units ({len(out['5d_no_record'])} with no record about them); {len(out['5e'])} data panels; "
          f"{len(out['5f'])} check.py problems; 5g {dict(collections.Counter(r['result'] for r in out['5g']))}; {len(out['5h'])} gaps seen first")
    return 0


if __name__ == "__main__":
    sys.exit(main())
