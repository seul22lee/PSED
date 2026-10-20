#!/usr/bin/env python3
"""P134 compiler: records/<pid>.jsonl -> compiled/<pid>.facts.csv (facts.FIELDS), with .unmapped.csv, .dropped.csv, .coverage.csv,
.experiments.csv (pilot/experiments.py on the compiled tree, for check.py), .compile.log and .summary.csv. No provider call.

    python3 psed_v2/extract/compile.py yli18          # then: python3 psed_v2/pilot/check.py --dir psed_v2/compiled

Input: the groups of pass1_elements.groups(pid); per group the latest pass-1 line of that section name (lines of a name no group has
are ignored); the latest pass-0 line. Steps, each one drops and logs, never repairs: a schema (form.json), b type rules, c grounding,
d quote, e units, f species/structure ids, g mentions, h tree and parents, i dedupe, j derived (query layer), k statements,
l coverage, m facts.csv. Then the diff against the gold pilot/<pid>.facts.csv (read only).
"""
import collections
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

import common as C
import pass1_elements as P1

import facts as F  # noqa: E402  (pilot/, on the path through common)
import lists as L  # noqa: E402
import vocab as V  # noqa: E402

OUT = C.V2 / "kb" / "compiled"
SPECIES_Q = {"material": L.MATERIALS, "substrate": L.MATERIALS, "reactant_A": list(L.SPECIES), "reactant_B": list(L.SPECIES), "structure": L.STRUCTURES}
VALUE_KEYS = ("value", "value_min", "value_max", "value_text")
DEDUPE_KEY = ("type", "parent", "quantity", "value", "value_min", "value_max", "unit", "qualifiers", "value_text")
FORM_TO_FACT = {"kind": "data_kind", "note": "definition_note"}
UNMAPPED_FIELDS = ["element", "field", "id", "label_as_printed", "unit", "candidate", "action"]
DROPPED_FIELDS = ["element", "step", "field", "reason", "type", "quantity"]


def num_text(v):
    """A number as the facts write it: 500, 0.05, 1e-05."""
    if isinstance(v, bool) or v is None or v == "":
        return ""
    v = float(v)
    return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "x"


def norm_ws(t):
    return re.sub(r"\s+", " ", t or "").strip()


def normalize(t):
    """D10, the one normalization of steps d, e and f: \\text{..} / \\mathrm{..} -> content; unicode NFKC; μ (U+03BC) and \\mu -> µ (U+00B5);
    \\circ / ^\\circ -> °; \\times -> ×; $ _ ^ { } and markdown * dropped; whitespace collapsed. Case is kept (step f lowers it)."""
    t = re.sub(r"\\(?:text|mathrm)\{([^{}]*)\}", r"\1", t or "")
    t = re.sub(r"\^?\{?\\circ\}?\s*", "°", t)                                       # P136 1b: ^\circ C -> °C
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\\mu\s*", "µ", t).replace("\u03bc", "µ")
    t = re.sub(r"\\times\s*", "×", t)                                                  # P136b: 50\times -> 50×
    t = re.sub(r"[$_^{}*]", "", t)
    return norm_ws(t)


UNIT_SYMBOL = {normalize(a): V.UNIT_ALIAS.get(a, a) for a in list(V.UNIT_BASE) + list(V.UNIT_ALIAS) if V.UNIT_ALIAS.get(a, a) in V.UNIT_BASE}


def unit_symbol(u):
    """The canonical spelling of a unit (vocab.UNIT_ALIAS), matched after normalize(); a 'u' prefix reads as µ (D4); None when units.yaml
    does not know it."""
    n = normalize(u)
    return UNIT_SYMBOL.get(n) or UNIT_SYMBOL.get(re.sub(r"^u(?=[A-Za-z])", "µ", n))


def alias_table(ids, entries):
    """{normalized alias lowercased: id} over the ids and their vocab aliases."""
    out = {}
    for i in ids:
        for a in [i] + list(entries.get(i, {}).get("aliases", [])):
            out.setdefault(normalize(a).lower(), i)
    return out


SPECIES_ALIASES = {q: alias_table(ids, L.SPECIES if q != "structure" else L.ENTRIES) for q, ids in SPECIES_Q.items()}


class Run:
    def __init__(self, pid):
        self.pid, self.key = pid, C.E.PAPERS[pid]
        self.log, self.dropped, self.unmapped = [], [], []
        self.steps = collections.OrderedDict()
        self.els = C.E.load(pid)
        self.order = {r["element_id"]: n for n, r in enumerate(self.els)}
        self.kind_of = {r["element_id"]: r["kind"] for r in self.els}
        self.text = C.E.texts(pid)

    def note(self, msg):
        self.log.append(msg)

    def drop(self, step, eid, rec, reason, field=""):
        self.dropped.append(dict(element=eid, step=step, field=field, reason=reason, type=rec.get("type", ""), quantity=rec.get("quantity", "")))
        self.steps.setdefault(step, collections.Counter())[reason] += 1

    def count(self, step, what, n=1):
        self.steps.setdefault(step, collections.Counter())[what] += n

    # ------------------------------------------------------------------------------------------------------------ input
    def read(self):
        lines = [json.loads(x) for x in (C.RECORDS / f"{self.pid}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        self.groups = P1.groups(self.pid)[0]
        latest, p0 = {}, None
        for n, x in enumerate(lines, 1):
            if x["pass"] == 0:
                p0 = n
            elif x["pass"] == 1:
                latest[x["section"]] = n
        used = {latest[g] for g in self.groups if g in latest}
        ignored = [n for n, x in enumerate(lines, 1) if x["pass"] == 1 and n not in used]
        self.lines_used, self.lines_ignored = sorted(used | {p0}), ignored
        self.note(f"input: {len(lines)} lines; pass 0 = line {p0}; {len(used)} pass-1 lines for {len(self.groups)} groups; ignored lines "
                  + ", ".join(f"{n} ({lines[n - 1]['section']})" for n in ignored))
        for g in self.groups:
            if g not in latest:
                self.note(f"input: group {g} has no pass-1 line")
        self.pass0 = C.loads_json(lines[p0 - 1]["response"])
        self.answers = {}                                                       # element id -> [record] | "NK:..."
        for g, rs in self.groups.items():
            if g not in latest:
                continue
            a = P1.answers(C.loads_json(lines[latest[g] - 1]["response"]))
            for r in rs:
                if r["element_id"] in a:
                    self.answers[r["element_id"]] = a[r["element_id"]]
        recs = []
        for eid, a in sorted(self.answers.items(), key=lambda x: self.order[x[0]]):
            if isinstance(a, list):
                for i, rec in enumerate(a):
                    if isinstance(rec.get("variables"), list):                  # rule 3: the provider's list back to {symbol: quantity}
                        rec["variables"] = {v.get("symbol"): v.get("quantity") for v in rec["variables"] if isinstance(v, dict)}
                    recs.append(dict(eid=eid, rec=rec, seq=i))
        self.count("input", "records", len(recs))
        return recs

    # ------------------------------------------------------------------------------------------------------------ a-g
    def validate(self, recs):
        from jsonschema import Draft202012Validator
        form = C.schema("form.json")
        val, qids = Draft202012Validator(form), set(form["$defs"]["quantity_id"]["enum"])
        out = []
        for r in recs:
            vs = r["rec"].get("variables")
            for sym, q in (vs.items() if isinstance(vs, dict) else []):          # D12: a symbol's quantity outside the enum -> null, logged
                if q is not None and q not in qids:
                    vs[sym] = None
                    self.count("a", "variables_unmapped (set to null)")
                    self.note(f"a: {r['eid']}: variables_unmapped {sym!r} -> {q!r}")
            for k_ in form["required"]:                                         # P139: a missing field is a null; only an enum/type violation drops
                r["rec"].setdefault(k_, None)
            if r["rec"].get("type") is None:
                self.drop("a", r["eid"], r["rec"], "type null", "type"); continue
            errs = list(val.iter_errors(r["rec"]))
            if not errs:
                r["rec"] = {k_: (({q: v for q, v in x.items() if v is not None} if k_ == "qualifiers" else x) if isinstance(x, dict) else x)
                            for k_, x in r["rec"].items() if x is not None}     # P139: null = absent
                out.append(r); continue
            e = errs[0]
            field = ".".join(str(p) for p in e.path) or (e.validator if e.validator not in ("required", "dependentRequired") else e.message.split("'")[1])
            self.drop("a", r["eid"], r["rec"], f"schema:{e.validator or 'forbidden'}", field)
            self.count("a_fields", field)
        return out

    def type_rules(self, recs):
        out = []                                                                # P136 1a: definitions from every element (D1 dropped)
        for r in recs:
            rec, eid = r["rec"], r["eid"]
            t = rec["type"]
            if t == "model" and rec.get("quantity") and "value" in rec:
                self.count("b", "model_with_value (kept)")
            if t in ("setting", "observation") and not rec.get("quantity"):
                self.count("b", "statement_only (kept: P138 form)")
            out.append(r)
        return out

    def ground(self, recs):
        out = []
        for r in recs:
            rec, eid = r["rec"], r["eid"]
            q = rec.get("quantity", "")
            bad = [("quantity", x) for x in (q if isinstance(q, list) else [q] if q else []) if x not in L.QUANTITIES]   # P138: a list on caveats
            if rec.get("method") and rec["method"] not in L.METHODS:
                bad.append(("method", rec["method"]))
            if rec.get("kind") and rec["kind"] not in L.KINDS:
                bad.append(("kind", rec["kind"]))
            bad += [("qualifiers", x) for x in L.qualifiers_ok(quals_text(rec))]
            bad += [("cause/effect", x) for x in L.variables_ok(";".join(rec.get("cause", []) + rec.get("effect", [])))]
            if rec.get("relation") and rec["relation"] not in L.RELATIONS:
                bad.append(("relation", rec["relation"]))
            bad += [("variables", x) for x in (rec.get("variables") or {}).values() if x is not None and x not in L.QUANTITIES]   # P136 2c: null = no entry
            if bad:
                for field, x in bad:
                    self.unmapped.append(dict(element=eid, field=field, id=x, label_as_printed=rec.get("label_as_printed", ""), unit=rec.get("unit", ""),
                                              candidate="", action="excluded"))
                self.drop("c", eid, rec, "unresolved_id", bad[0][0]); continue
            if q == "other":
                self.unmapped.append(dict(element=eid, field="quantity", id="other", label_as_printed=rec.get("label_as_printed", ""), unit=rec.get("unit", ""),
                                          candidate=json.dumps(rec.get("candidate", {}), ensure_ascii=False), action="kept"))
                self.count("c", "quantity_other (kept)")
            out.append(r)
        return out

    def quotes(self, recs):
        out = []
        for r in recs:
            ev = [r["eid"]] + [m for m in r["rec"].get("mentions") or [] if m in self.order and m != r["eid"]]   # D11: the record's element and the
            if normalize(r["rec"]["quote"]) in normalize(" ".join(self.text.get(e, "") for e in ev)):        # element ids it mentions, texts joined
                out.append(r)
            else:
                self.drop("d", r["eid"], r["rec"], "quote_not_found", "quote")
        return out

    def units(self, recs):
        out = []
        for r in recs:
            rec = r["rec"]
            if rec.get("unit"):
                s = unit_symbol(rec["unit"])
                if s is None:
                    self.unmapped.append(dict(element=r["eid"], field="unit", id=normalize(rec["unit"]), label_as_printed=rec.get("label_as_printed", ""),
                                              unit=rec["unit"], candidate="", action="excluded"))
                    self.drop("e", r["eid"], rec, "unit_unresolved", "unit"); continue
                r["unit"] = s
            out.append(r)
        return out

    def species(self, recs):
        out = []
        for r in recs:
            rec = r["rec"]
            q = rec.get("quantity", "")
            if q in SPECIES_Q and "value" not in rec:
                table = SPECIES_ALIASES[q]
                hit = next((table[normalize(x).lower()] for x in (rec.get("value_text"), rec.get("label_as_printed"), rec.get("quote"))
                            if x and normalize(x).lower() in table), None)
                if hit is None:
                    self.drop("f", r["eid"], rec, "species_unresolved", "value_text")
                    self.unmapped.append(dict(element=r["eid"], field=q, id=rec.get("value_text", ""), label_as_printed=rec.get("label_as_printed", ""),
                                              unit="", candidate="", action="excluded"))
                    continue
                r["species"] = hit
                self.count("f", "species_resolved")
            out.append(r)
        return out

    def mentions(self, recs):
        self.names = {}                                                         # name as printed -> pass-0 item
        for it in self.pass0:
            if it.get("name_as_printed"):
                self.names.setdefault(it["name_as_printed"], it)
        for r in recs:
            ms = [m for m in r["rec"].get("mentions") or [] if m not in self.order]   # an element id (the prompt lists them) goes to figure_ref
            r["refs"] = [m for m in r["rec"].get("mentions") or [] if m in self.order]
            miss = [m for m in ms if m not in self.names]
            r["named"] = [self.names[m] for m in ms if m in self.names]
            r["unmatched"] = bool(miss)
            if miss:
                self.count("g", "mention_unmatched", len(miss))
                self.note(f"g: {r['eid']}: mention_unmatched {miss}")
        return recs

    # ------------------------------------------------------------------------------------------------------------ h tree
    def tree(self):
        """P138: the tree from the pass-0 items by their ids: the paper; a recipe when there is a run or a specimen; a run -> a
        deposition under the recipe; a simulation -> a simulation activity under the paper; a specimen -> an entity under the run its
        parent names (else under the recipe, logged); a series -> a comparison (kind series) under the paper, filled by figures();
        a cited work has no row. self.node: pass-0 id -> (row id, role)."""
        k, rows = self.key, []
        ok_ev = lambda ids: ";".join(sorted({i for i in ids if i in self.order}, key=self.order.get))   # noqa: E731

        def row(**kw):
            r = {f: "" for f in F.FIELDS}
            r.update(kw)
            r["author"] = self.pid
            return r
        rows.append(row(fact_id=k, type="paper", evidence=self.els[0]["element_id"], statement=f"the paper {self.pid} ({k}) as compiled from its extraction records"))
        items, self.node, self.p0 = [], {}, {}
        for it in self.pass0:
            if not isinstance(it, dict):
                continue
            if not it.get("id") or it["id"] in self.p0:
                self.count("h", "pass-0 item without a unique id (skipped)")
                continue
            self.p0[it["id"]] = it
            items.append(it)
        role = lambda r: [it for it in items if it.get("role") == r]               # noqa: E731
        if role("run") or role("specimen"):
            rows.append(row(fact_id=f"{k}:recipe", type="activity", kind="recipe", how="inferred", parent=k, label_as_printed="recipe",
                            evidence=ok_ev([e for it in role("run") + role("specimen") for e in it.get("introduced_in") or []]),
                            statement=f"the deposition recipe of {k}: the runs and specimens of its first pass"))
        for it in role("run"):
            self.node[it["id"]] = (f"{k}:run:{slug(it['id'])}", "run")
            rows.append(row(fact_id=self.node[it["id"]][0], type="activity", kind="deposition", how="stated", evidence=ok_ev(it.get("introduced_in") or []),
                            parent=f"{k}:recipe", label_as_printed=it.get("name_as_printed") or it["id"], statement=f"deposition run {it['id']} ({it.get('name_as_printed')!r})"))
        for it in role("simulation"):
            self.node[it["id"]] = (f"{k}:sim:{slug(it['id'])}", "simulation")
            rows.append(row(fact_id=self.node[it["id"]][0], type="activity", kind="simulation", how="stated", evidence=ok_ev(it.get("introduced_in") or []),
                            parent=k, label_as_printed=it.get("name_as_printed") or it["id"], statement=f"simulation {it['id']} ({it.get('name_as_printed')!r})"))
        for it in role("specimen"):
            par = self.node.get(it.get("parent", ""), ("", ""))
            if par[1] != "run":
                self.count("h", "specimen without a run parent (under the recipe)")
            self.node[it["id"]] = (f"{k}:ent:{slug(it['id'])}", "specimen")
            q = ";".join(f"{a}={it[a]}" for a in ("specimen_class", "structure_class") if it.get(a))
            rows.append(row(fact_id=self.node[it["id"]][0], type="entity", how="stated", evidence=ok_ev(it.get("introduced_in") or []), qualifiers=q,
                            parent=par[0] if par[1] == "run" else f"{k}:recipe", label_as_printed=it.get("name_as_printed") or it["id"],
                            statement=f"specimen {it['id']} ({it.get('name_as_printed')!r})"))
        for it in role("series"):
            self.node[it["id"]] = (f"{k}:series:{slug(it['id'])}", "series")
            rows.append(row(fact_id=self.node[it["id"]][0], type="comparison", kind="series", how="stated", evidence=ok_ev(it.get("introduced_in") or []),
                            parent=k, label_as_printed=it.get("name_as_printed") or it["id"], statement=f"series {it['id']} ({it.get('name_as_printed')!r})"))
        self.note("h: tree from pass 0: " + ", ".join(f"{r} {len(role(r))}" for r in ("run", "simulation", "specimen", "series", "cited_work"))
                  + "; identity rows: none (pass 0 carries no identity)")
        self.rows_tree = rows
        self.meas = {}
        return rows

    def measurement(self, ent, method):
        i = f"{ent}:meas:{method or 'not_stated'}"
        if i not in self.meas:
            ent_row = next(r for r in self.rows_tree if r["fact_id"] == ent)
            r = {f: "" for f in F.FIELDS}
            r.update(fact_id=i, type="activity", kind="measurement", how="inferred", parent=ent, author=self.pid,
                     qualifiers=f"mode={L.METHOD_MODE.get(method, 'not_stated')}", label_as_printed=f"{method or 'measurement'} of {ent_row['label_as_printed']}",
                     statement=f"the {method.replace('_', ' ') if method else 'unstated'} measurement of the specimen named {ent_row['label_as_printed']!r}")
            self.meas[i] = r
        return i

    def series_base(self, sid):
        """The row a series' entities hang under: its pass-0 parent's row (a simulation, a run or a specimen), else ''."""
        it = self.p0.get(sid, {})
        return self.node.get(it.get("parent", ""), ("", ""))

    def figures(self):
        """P138: kb/<pid>.figures.json curves through the pass-0 series: a curve belongs to the series whose introduced_in names its
        figure (fig<n>, fig<n><panel> or fig<n>.cap); its fields as they are. Under the series' parent row (base): one entity per
        distinct conditions dict of the series' curves; the conditions all of them share go once on the base, the rest on the entity.
        A curve is a model row (under its entity) when the base is a simulation, an observation row (under the entity's measurement
        activity) when it is a run or a specimen; never from the curve's kind. The series comparison: quantity = the one condition
        that differs among its entities (else the figure set's varied, logged), links = the first curve row (purpose), then the
        entities. A curve no series names, or a series without a parent, is logged and left out. Returns (tree rows, fact rows)."""
        p = C.V2 / "kb" / f"{self.pid}.figures.json"
        Fj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        k, tree, facts = self.key, [], []
        series = {i: it for i, it in self.p0.items() if it.get("role") == "series"}

        def els(fig, panel=""):
            return list(dict.fromkeys(e for e in (f"fig{fig}{panel}", f"fig{fig}", f"fig{fig}.cap") if e in self.order))

        def row(**kw):
            r = {x: "" for x in F.FIELDS}
            r.update(kw)
            r["author"] = self.pid
            return r

        def ckey(c):
            return c.get("quantity", ""), c.get("value"), c.get("value_max"), c.get("unit", "")

        def settings(conds, parent, ev, kind, mentions=""):
            for c in conds:
                q, u = c.get("quantity", ""), unit_symbol(c.get("unit") or "") if c.get("unit") else ""
                if q not in L.QUANTITIES or c.get("value") is None:
                    self.count("1c", "condition without a quantity id or a value"); continue
                if u is None:
                    self.count("1c", "condition unit unresolved"); continue
                lo, hi = (num_text(c["value"]), num_text(c["value_max"])) if c.get("value_max") is not None else ("", "")
                facts.append(row(type="setting", quantity=q, label_as_printed=c.get("key_raw", "") or q, value="" if hi else f"{c['value']:.6g}",
                                 value_min=lo, value_max=hi, unit=u, data_kind=kind, mentions=mentions, evidence=ev, parent=parent))
                self.count("1c", "setting")
        sets = {st["id"]: st for st in Fj.get("sets", [])}
        named = dict(series)
        fallback = {}
        for st in Fj.get("sets", []):                                           # P139: the one fallback: a figure set no pass-0 series names
            if any(set(it.get("introduced_in") or []) & set(els(st["figure"], st.get("panel", ""))) for it in named.values()):
                continue
            fid = f"figset:{st['id'].split(':')[-1]}"
            fallback[st["id"]] = fid
            series[fid] = dict(id=fid, role="series", introduced_in=els(st["figure"], st.get("panel", "")), parent=None, _fallback=True)
            self.node[fid] = (f"{k}:series:{slug(fid)}", "series")
            tree.append(row(fact_id=self.node[fid][0], type="comparison", kind="series", how="inferred", evidence=";".join(els(st["figure"], st.get("panel", ""))),
                            parent=k, label_as_printed=st.get("label", "") or fid, statement=f"figure set {st['id']}: no pass-0 series names its figure (fallback)"))
            self.note(f"1c: fallback series {fid} for figure set {st['id']} (no pass-0 series names the figure)")
            self.count("1c", "fallback series (figure set without a pass-0 series)")
        by_series = collections.defaultdict(list)
        for cu in Fj.get("curves", []):
            hit = [sid for sid, it in named.items() if set(it.get("introduced_in") or []) & set(els(cu["figure"], cu.get("panel", "")))]
            if not hit and cu.get("set") in fallback:
                hit = [fallback[cu["set"]]]
            if len(hit) != 1:
                self.count("1c", f"curve not in exactly one series ({len(hit)})"); continue
            by_series[hit[0]].append(cu)
        self.purpose, self.series_members = {}, {}
        for sid, it in series.items():
            cid = self.node[sid][0]
            base, brole = self.series_base(sid)
            if it.get("_fallback"):
                base, brole = k, "paper"                                        # P139: under the paper row; its row type comes from the curve's kind (logged)
            curves = by_series.get(sid, [])
            if not base:
                self.count("1c", "series without a parent (its curves left out)")
                self.series_members[cid] = []
                continue
            ents = {}
            for cu in curves:
                key = tuple(sorted(ckey(c) for c in (cu.get("conditions") or {}).values()))
                ents.setdefault(key, dict(id=f"{cid}:e{len(ents) + 1}", conds=list((cu.get("conditions") or {}).values()), curves=[]))["curves"].append(cu)
            common = set.intersection(*[{ckey(c) for c in e["conds"]} for e in ents.values()]) if len(ents) > 1 else set()
            kind = "model_input" if brole == "simulation" else "stated"
            sev = ";".join(dict.fromkeys(x for cu in curves for x in els(cu["figure"], cu.get("panel", ""))))
            if ents:
                settings([c for c in next(iter(ents.values()))["conds"] if ckey(c) in common], base, sev, kind)
            for e in ents.values():
                eev = ";".join(dict.fromkeys(x for cu in e["curves"] for x in els(cu["figure"], cu.get("panel", ""))))
                lab = e["curves"][0].get("series", {}).get("label_raw", "")
                tree.append(row(fact_id=e["id"], type="entity", how="stated", evidence=eev, parent=base, label_as_printed=lab or e["id"],
                                statement=f"the {'run' if brole == 'simulation' else 'specimen'} of series {sid} with the conditions of curves {', '.join(c['id'] for c in e['curves'])}"))
                settings([c for c in e["conds"] if ckey(c) not in common], e["id"], eev, kind, mentions=lab)
                for cu in e["curves"]:
                    y = cu["y"]
                    if y.get("quantity") not in L.QUANTITIES:
                        self.count("1c", "curve y quantity not an id"); continue
                    ev = ";".join(els(cu["figure"], cu.get("panel", "")))
                    if brole == "paper":
                        self.count("1c", "row type from the curve's kind (fallback series)")
                    if brole == "simulation" or (brole == "paper" and cu["kind"] == "simulated"):
                        facts.append(row(type="model", quantity=y["quantity"], label_as_printed=y.get("label_raw", "") or y["quantity"], data_kind="simulated",
                                         mentions=cu.get("series", {}).get("label_raw", ""), evidence=ev, parent=e["id"]))
                    else:
                        facts.append(row(type="observation", quantity=y["quantity"], label_as_printed=y.get("label_raw", "") or y["quantity"], data_kind="read_from_figure",
                                         mentions=cu.get("series", {}).get("label_raw", ""), evidence=ev, parent="@meas:" + e["id"]))
                    self.purpose.setdefault(cid, facts[-1])
                    self.count("1c", f"curve -> {facts[-1]['type']}")
            self.series_members[cid] = [e["id"] for e in ents.values()]
            differ = [q for q in {c[0] for e in ents.values() for c in (ckey(x) for x in e["conds"])}
                      if len({tuple(sorted(ckey(x) for x in e["conds"] if x.get("quantity") == q)) for e in ents.values()}) > 1]
            varied = differ[0] if len(differ) == 1 else next((sets[cu["set"]]["varied"] for cu in curves if cu.get("set") in sets), "")
            if len(differ) != 1:
                self.count("1c", f"series varied from the figure set ({len(differ)} conditions differ)")
            crow = next(r for r in self.rows_tree + tree if r["fact_id"] == cid)
            crow["quantity"] = varied if varied in L.QUANTITIES else ""
            self.count("1c", "series entities", len(ents))
        return tree, facts

    def parent(self, r):
        """P138: the record's own parent: "paper" -> the paper row; a pass-0 id -> its tree row (a result with a value under a specimen
        -> that specimen's measurement activity by method; a setting under a series -> the series' parent row, a result under a series
        -> the comparison); anything else -> the paper row, logged parent_unknown (never empty)."""
        rec, k = r["rec"], self.key
        p = rec.get("parent", "")
        if p == "paper":
            return k, "paper (record)"
        if not p:
            r["parent_filled"] = True
            return k, "parent_null (paper)"                                     # P139: filled, flagged
        if p not in self.node:
            r["parent_filled"] = True
            return k, "parent_unknown (paper)"
        rid, role = self.node[p]
        result = rec["type"] in ("observation", "derived") and any(rec.get(x) not in (None, "") for x in VALUE_KEYS)
        if role == "specimen" and result:
            return self.measurement(rid, rec.get("method", "")), "specimen measurement (record)"
        if role == "series":
            if rec["type"] == "setting":
                base = self.series_base(p)[0]
                return (base, "series parent (record)") if base else (k, "series without a parent (paper)")
            return rid, "series (record)"
        return rid, f"{role} (record)"

    # ------------------------------------------------------------------------------------------------------------ rows
    def fact_row(self, r, parent):
        rec = r["rec"]
        f = {x: "" for x in F.FIELDS}
        for a in ("type", "label_as_printed", "censor", "value_text", "method", "uncertainty_kind", "relation", "stance"):
            f[a] = str(rec.get(a, "") or "")
        q = rec.get("quantity", "")
        f["quantity"] = ";".join(q) if isinstance(q, list) else str(q or "")    # P138: a caveat's list joined
        if f["quantity"] and not f["label_as_printed"]:                         # P138: filled with the quantity id
            f["label_as_printed"] = f["quantity"]
            self.count("m", "label_as_printed filled with the quantity id")
        for a in ("value", "value_min", "value_max", "uncertainty"):
            f[a] = num_text(rec.get(a))
        f["uncertainty_n"] = str(rec.get("uncertainty_n", "") or "")
        f["unit"] = r.get("unit", "")
        f["qualifiers"] = quals_text(rec)
        for a, b in FORM_TO_FACT.items():
            f[b] = str(rec.get(a, "") or "")
        f["mentions"] = ";".join(m for m in rec.get("mentions") or [] if m not in r["refs"])
        f["figure_ref"] = ";".join(r["refs"])
        f["cause"], f["effect"] = ";".join(rec.get("cause") or []), ";".join(rec.get("effect") or [])
        if "species" in r:                                                     # f: the gold shape of a species / structure setting
            f.update(type="setting", data_kind="", value_text=r["species"])
        if f["type"] == "definition":
            vs = rec.get("variables") or {}
            f["term"] = rec.get("term") or "|".join(s for s, q in vs.items() if q == f["quantity"])
        f["evidence"], f["parent"], f["author"] = r["eid"], parent, self.pid
        f["_statement"] = rec.get("statement") or rec.get("quote", "")          # P138: the extractor's own words; P139: the quote when null
        if not rec.get("statement"):
            self.count("m", "statement filled from the quote")
        f["_parent_filled"] = bool(r.get("parent_filled"))
        f["_links"] = [e for e in rec.get("links") or [] if e in self.order]    # P138: resolved to fact ids after ids()
        f["_quote"] = normalize(rec.get("quote", "")).lower()
        if any(f[x] for x in ("value", "value_min", "value_max")) and not f["data_kind"]:
            f["data_kind"] = "stated"                                           # P138: filled, flagged
            f["_kind_filled"] = True
        return f

    def dedupe(self, items):
        """i (D3): equal DEDUPE_KEY from different elements -> one record, evidence = all element ids in element order. Value records
        only; P136 1a: a definition by its normalized term (term, else label_as_printed, else the first mention)."""
        seen, out = {}, []
        for f in items:
            key = text_key(f)
            if key is not None:                                                 # P138: claims, caveats, definitions: with the quote
                if key in seen:
                    g = seen[key]
                    g["evidence"] = ";".join(sorted(set(g["evidence"].split(";")) | set(f["evidence"].split(";")), key=self.order.get))
                    self.count("i", f"{f['type']} merged")
                    self.note(f"i: {f['type']} {key[1:]!r}: merged {f['evidence']} into {g['evidence']}")
                    continue
                seen[key] = f
                out.append(f); continue
            if not any(f[x] for x in VALUE_KEYS):
                out.append(f); continue
            key = tuple(f[x] for x in DEDUPE_KEY)
            if key in seen and not set(f["evidence"].split(";")) <= set(seen[key]["evidence"].split(";")):
                g = seen[key]
                g["evidence"] = ";".join(sorted(set(g["evidence"].split(";")) | set(f["evidence"].split(";")), key=self.order.get))
                self.count("i", "merged")
                self.note(f"i: merged {f['evidence']} into {g['evidence']} ({f['quantity']} {f['value'] or f['value_text']})")
                continue
            if key in seen and seen[key]["label_as_printed"] == f["label_as_printed"]:     # P136b: the same row again from the same element(s); a
                self.count("i", "duplicate dropped")                                          # label that differs stays (D5)
                continue
            seen.setdefault(key, f)
            out.append(f)
        return out

    def ids(self, items):
        n = collections.Counter()
        for f in items:
            first = f["evidence"].split(";")[0]
            n[first] += 1
            f["fact_id"] = f"{self.key}:{first}#{n[first]}"
        self.id_count = n
        return items

    def derived(self, rows):
        """j: lists.DERIVED through query.derive on the compiled tree, one derived row per entity and derived id when every input is a
        compiled fact (no assumed fact); caveats and claim nodes through query; comparisons not built (D8)."""
        import query as Q
        self.write_facts(rows)
        here, Q.HERE = Q.HERE, OUT
        try:
            T = Q.Tree(self.key)
        finally:
            Q.HERE = here
        ids = {r["fact_id"] for r in rows}
        byid = {r["fact_id"]: r for r in rows}
        out, errors = [], collections.Counter()
        for e in T.entities():
            for did in L.DERIVED:
                try:
                    d = Q.derive(T, e, did)
                except (KeyError, ValueError) as ex:                            # P138: an input query cannot convert (e.g. cycle -> 1): logged
                    errors[f"derive raised: {ex}"[:60]] += 1; continue
                if "error" in d:
                    errors[re.sub(r" \(.*|;.*", "", d["error"])] += 1; continue
                ins = [u[1] for u in d["inputs"]]
                if d["assumed"] or not all(i in ids for i in ins):
                    self.count("j", "derived_needs_outside_fact"); continue
                q, _ = L.derived_key(did)
                f = {x: "" for x in F.FIELDS}
                ev = sorted({x for i in ins for x in byid[i]["evidence"].split(";")}, key=self.order.get)
                f.update(type="derived", quantity=q, qualifiers=L.DERIVED[did].get("qualifiers", ""), value=f"{d['value']:.4g}", unit=d["unit"], data_kind="computed_by_kb",
                         method="calculation", inputs=";".join(dict.fromkeys(ins)), evidence=";".join(ev), parent=e, author=self.pid,
                         mentions=T.byid[e]["label_as_printed"])
                self.id_count[ev[0]] += 1
                f["fact_id"] = f"{self.key}:{ev[0]}#{self.id_count[ev[0]]}"
                out.append(f)
                self.count("j", f"derived {did}")
        self.note(f"j: derived over {len(T.entities())} entities: {len(out)} rows; not derived: {dict(errors)}")
        cav = Q.caveats_of(T)
        self.note(f"j: caveats (query.caveats_of): {len(cav)}, linked to facts {sum(bool(c['facts']) for c in cav)}, to nodes {sum(bool(c['nodes']) for c in cav)}; "
                  f"facts reached through query.caveats_for: {sum(bool(Q.caveats_for(T, f, T.ent_of(f['fact_id']))) for f in T.rows if '#' in f['fact_id'] and f['type'] != 'caveat')}")
        trees, Q.TREES = Q.TREES, {self.key: T}
        Q._NODES.clear()
        try:
            nodes = Q.claim_nodes()
            claims = [f for f in T.rows if f["type"] == "claim"]
            self.note(f"j: claim nodes (query.claim_nodes): {sum(any(m[0] == self.key for m in n['members']) for n in nodes.values())} nodes for {len(claims)} claims; "
                      f"claims without a full triple (query.node_of empty): {sum(not Q.node_of(c['fact_id']) for c in claims)}")
        finally:
            Q.TREES = trees
            Q._NODES.clear()
        self.note(f"j: comparisons from figures.json (1c): {sum(r['type'] == 'comparison' for r in rows)}")
        self.n_derived = len(out)
        return rows + out

    def statements(self, rows):
        """k: the record's own statement (P138) when it has one, else one line assembled from the fields. P138: nothing is left out
        and nothing is appended to pass a check (R3): a line that repeats eight words of its element, or the wording of another row,
        stays as it is and check.py reports it."""
        for f in rows:
            if "#" not in f["fact_id"]:
                continue
            name = f["label_as_printed"] if f["quantity"] == "other" else L.NAMES.get(f["quantity"], f["quantity"].replace("_", " "))
            var = lambda s: " and ".join(L.MECHANISMS[x]["name"] if x in L.MECHANISMS else L.NAMES.get(x, x.replace("_", " ")) for x in s.split(";") if x)
            v = f["censor"] + f["value"] if f["value"] else (f"{f['value_min']}–{f['value_max']}" if f["value_min"] and f["value_max"] else
                                                            (f["censor"] or ">") + f["value_min"] if f["value_min"] else ("<" + f["value_max"] if f["value_max"] else ""))
            v = " ".join(x for x in (v, f["unit"]) if x) or (f"'{f['value_text']}'" if f["value_text"] else "")
            q = f" ({f['qualifiers'].replace(';', ', ')})" if f["qualifiers"] else ""
            t = f["type"]
            if t == "claim":
                head = f"{f['stance'] or 'unstated'} claim: {var(f['cause'])} {f['relation'].replace('_', ' ')} {var(f['effect'])}" if f["cause"] else f"{f['stance'] or 'unstated'} claim without a cause and effect"
            elif t == "definition":
                head = f"definition of {name or 'an unnamed quantity'}" + (f" (symbol {f['term']})" if f["term"] else "")
            elif t == "caveat":
                head = f"caveat on {name}{q}" if f["quantity"] else "caveat"
            elif t == "cited":
                head = f"cited value of {name}{q}: {v}" if f["quantity"] else "cited statement"
            else:
                head = f"{t} {name or 'statement'}{q}" + (f": {v}" if v else "")
            optional = [x for x in (f" printed as '{f['label_as_printed']}'" if f["label_as_printed"] and f["quantity"] != "other" else "",
                                    f" for {f['mentions'].replace(';', ', ')}" if f["mentions"] else "") if x]
            kind = f", {V.PHRASES[f['data_kind']]}" if f["data_kind"] in V.PHRASES else ""
            s = (f.get("_statement") or "").strip() or head + "".join(optional) + kind
            self.count("k", "statement from the record" if (f.get("_statement") or "").strip() else "statement assembled")
            if copies(s, [self.text.get(e, "") for e in f["evidence"].split(";")]):
                self.count("k", "statement_copies_text (reported by check)")
            f["statement"] = " ".join(s.split())
        return rows

    def coverage(self, rows):
        by_el = collections.defaultdict(list)
        for f in rows:
            if "#" in f["fact_id"]:
                for e in f["evidence"].split(";"):
                    by_el[e].append(f)
        drops = collections.defaultdict(list)
        for d in self.dropped:
            drops[d["element"]].append(d["step"] + ":" + d["reason"])
        out = []
        for r in self.els:
            eid = r["element_id"]
            a = self.answers.get(eid)
            c = dict(element_id=eid, kind=r["kind"], status="", fact_ids="", reason="", n_numbers=r["n_numbers"], n_numbers_reached="")
            if by_el[eid]:
                c.update(status="covered", fact_ids=";".join(f["fact_id"] for f in by_el[eid]),
                         n_numbers_reached=str(len(F.nums_of(self.text.get(eid, "")) & {round(abs(F.num(f[x])), 9) for f in by_el[eid] for x in ("value", "value_min", "value_max") if F.num(f[x]) is not None})))
            elif isinstance(a, str):
                c.update(status="no knowledge", reason=a.removeprefix("NK:"))
            elif a is None:
                c.update(status="uncovered", reason="no answer in the pass-1 line of its group")
            elif drops[eid]:
                c.update(status="uncovered", reason="every record dropped: " + "; ".join(sorted(set(drops[eid]))))
            else:
                c.update(status="uncovered", reason="answered with no record")
            out.append(c)
        self.cov = out
        return out

    # ------------------------------------------------------------------------------------------------------------ write
    def write_facts(self, rows):
        OUT.mkdir(exist_ok=True)
        write_csv(OUT / f"{self.pid}.facts.csv", F.FIELDS, rows)

    def run(self):
        recs = self.read()
        recs = self.validate(recs)
        self.count("a", "kept", len(recs))
        recs = self.type_rules(recs)
        self.count("b", "kept", len(recs))
        recs = self.ground(recs)
        self.count("c", "kept", len(recs))
        recs = self.quotes(recs)
        self.count("d", "kept", len(recs))
        recs = self.units(recs)
        self.count("e", "kept", len(recs))
        recs = self.species(recs)
        self.count("f", "kept", len(recs))
        recs = self.mentions(recs)
        tree = self.tree()
        items = []
        for r in recs:
            p, why = self.parent(r)
            self.count("h", f"parent: {why}")
            items.append(self.fact_row(r, p))
        fig_tree, fig_facts = self.figures()
        self.rows_tree += fig_tree                                              # the series entities, before their measurement activities
        for f in fig_facts:
            if f["parent"].startswith("@meas:"):
                f["parent"] = self.measurement(f["parent"][6:], "")
        items = self.dedupe(items + fig_facts)
        self.count("i", "kept", len(items))
        items = self.ids(items)
        on = collections.defaultdict(list)
        for f in items:
            for e in f["evidence"].split(";"):
                on[e].append(f["fact_id"])
        for f in items:                                                         # P138: links (element ids) -> the fact ids on those elements
            if f.get("_links"):
                f["links"] = ";".join(dict.fromkeys(i for e in f["_links"] for i in on[e] if i != f["fact_id"]))
                self.count("m", "links resolved" if f["links"] else "links named elements without facts")
            if f.get("_kind_filled"):
                self.count("m", "kind_filled (stated)")
                self.note(f"m: {f['fact_id']}: kind_filled stated")
        for c in tree:                                                          # P138: a series: its purpose row, then its entities
            if c["type"] == "comparison":
                pr = self.purpose.get(c["fact_id"])
                c["links"] = ";".join(([pr["fact_id"]] if pr else []) + self.series_members.get(c["fact_id"], []))
        rows = tree + list(self.meas.values()) + items                         # tree holds the series entities (rows_tree)
        rows = self.derived(rows)
        rows = self.statements(rows)
        self.coverage(rows)
        self.write_facts(rows)
        self.rows = rows
        write_csv(OUT / f"{self.pid}.coverage.csv", F.COV_FIELDS, self.cov)
        write_csv(OUT / f"{self.pid}.dropped.csv", DROPPED_FIELDS, self.dropped)
        write_csv(OUT / f"{self.pid}.unmapped.csv", UNMAPPED_FIELDS, self.unmapped)
        import experiments as EX
        here, EX.HERE = EX.HERE, OUT
        try:
            EX.write(OUT / f"{self.pid}.experiments.csv", EX.table(self.pid, self.key))
        finally:
            EX.HERE = here
        return rows


def text_key(f):
    """P138: the dedupe key of a claim, caveat or definition (with the quote; a definition also by its normalized term), else None."""
    if f["type"] == "definition":
        t = normalize(f["term"] or f["label_as_printed"] or f["mentions"].split(";")[0]).lower()
        return ("definition", t, f.get("_quote", "")) if t else None
    if f["type"] in ("claim", "caveat"):
        return (f["type"], f["cause"], f["relation"], f["effect"], f.get("_quote", ""))
    return None


def quals_text(rec):
    q = rec.get("qualifiers") or {}
    return ";".join(f"{k}={num_text(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v}" for k, v in sorted(q.items()))


def words(t):
    return re.findall(r"[a-z0-9]+", re.sub(r"\$|\\text\{|\\mathrm\{|[{}^_]", " ", t.lower()))


def copies(s, texts):
    """check.py's own-words rule: eight words of an element in a row."""
    sw = words(s)
    grams = {tuple(sw[i:i + 8]) for i in range(len(sw) - 7)}
    return any(tuple(tw[i:i + 8]) in grams for t in texts for tw in [words(t)] for i in range(len(tw) - 7))


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------------------------------------------- diff against the gold
def canon(f):
    """P136 1d: a value for comparison: in the quantity's canonical unit (lists.UNITS, lists.convert), else in its dimension's base unit
    (vocab.UNIT_BASE; °C through K), else the raw (value, unit) strings."""
    v = F.num(f["value"]) if f["value"] else None
    if v is None:
        return None
    u = V.UNIT_ALIAS.get(f["unit"], f["unit"])
    for to in (L.UNITS.get(f["quantity"]), "K" if u == "°C" else None):
        if to is not None:
            try:
                v, u = L.convert(v, u, to), V.UNIT_ALIAS.get(to, to)
                break
            except (KeyError, ValueError):
                pass
    if u in V.UNIT_BASE:
        dim, fac = V.UNIT_BASE[u]
        dim = "dimensionless" if dim == "count" else dim                       # P139: a count compares as a number
        return dim, float(f"{v * fac:.6g}")
    return f["value"], f["unit"]


def match_key(f):
    """The P134 match on the value side, P136 1d: type, quantity, the value in canonical units, value_text."""
    return f["type"], f["quantity"], canon(f), f["value_text"].lower()


def matches(g, c):
    """A gold row g and a compiled row c match: a shared evidence element and equal match_key; D13: a gold model row without a value
    matches a model row on a shared element whatever its quantity."""
    if not set(g["evidence"].split(";")) & set(c["evidence"].split(";")):
        return False
    if g["type"] == "model" and not (g["value"] or g["value_min"] or g["value_max"] or g["value_text"]):
        return c["type"] == "model"
    return match_key(g) == match_key(c)


def diff(run):
    """Gold kb/pilot/<pid>.facts.csv against the compiled rows by matches() (P134 key, canonical units, D13); one gold row per compiled
    row, first come."""
    gold = list(csv.DictReader((C.V2 / "kb" / "pilot" / f"{run.pid}.facts.csv").open(encoding="utf-8")))
    comp = run.rows
    free = list(range(len(gold)))
    matched = collections.Counter()
    for c in comp:
        for j in free:
            g = gold[j]
            if matches(g, c):
                matched[c["type"]] += 1
                free.remove(j)
                break
    gn, cn = collections.Counter(f["type"] for f in gold), collections.Counter(f["type"] for f in comp)
    table = []
    for t in sorted(set(gn) | set(cn), key=lambda t: -gn[t]):
        m = matched[t]
        table.append(dict(type=t, gold=gn[t], compiled=cn[t], matched=m, precision=f"{m / cn[t]:.2f}" if cn[t] else "-", recall=f"{m / gn[t]:.2f}" if gn[t] else "-"))
    defs = [f for f in gold if f["type"] == "definition"]
    mwv = [f for f in gold if f["type"] == "model" and f["quantity"] and f["value"]]
    extra = [f"gold definitions with an eq* element in evidence: {sum(any(e.startswith('eq') for e in f['evidence'].split(';')) for f in defs)}/{len(defs)}",
             f"gold model rows with quantity and value: {len(mwv)}: {dict(collections.Counter(f['quantity'] for f in mwv))}",
             f"observations: gold {gn['observation']}, compiled {cn['observation']}, matched {matched['observation']}"]
    return table, extra


def main(arg):
    pid, key = C.resolve(arg)
    run = Run(pid)
    rows = run.run()
    table, extra = diff(run)
    log = run.log + [f"step {s}: {dict(c)}" for s, c in run.steps.items()]
    log.append("diff against the gold (type, gold, compiled, matched, precision, recall):")
    log += [f"  {d['type']:<12} {d['gold']:>4} {d['compiled']:>4} {d['matched']:>4} {d['precision']:>5} {d['recall']:>5}" for d in table]
    log += extra
    (OUT / f"{pid}.compile.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    summ = [("ontology_hash", C.X.ontology_hash()), ("lines_used", ";".join(map(str, run.lines_used))), ("lines_ignored", ";".join(map(str, run.lines_ignored))),
            ("facts", sum("#" in r["fact_id"] for r in rows)), ("tree_rows", sum("#" not in r["fact_id"] for r in rows)), ("derived_by_kb", run.n_derived),
            ("dropped", len(run.dropped)), ("unmapped", len(run.unmapped))]
    summ += [(f"step_{s}:{k}", v) for s, c in run.steps.items() for k, v in c.items()]
    summ += [(f"diff:{d['type']}", f"gold {d['gold']} compiled {d['compiled']} matched {d['matched']} P {d['precision']} R {d['recall']}") for d in table]
    with (OUT / f"{pid}.summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value"])
        w.writerows(summ)
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(C.main(main))
