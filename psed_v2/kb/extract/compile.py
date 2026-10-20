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
    \\circ / ^\\circ -> °; $ _ ^ { } and markdown * dropped; whitespace collapsed. Case is kept (step f lowers it)."""
    t = re.sub(r"\\(?:text|mathrm)\{([^{}]*)\}", r"\1", t or "")
    t = re.sub(r"\^?\{?\\circ\}?\s*", "°", t)                                       # P136 1b: ^\circ C -> °C
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\\mu\s*", "µ", t).replace("\u03bc", "µ")
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
        val = Draft202012Validator(C.schema("form.json"))
        out = []
        for r in recs:
            errs = list(val.iter_errors(r["rec"]))
            if not errs:
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
                self.drop("b", eid, rec, "statement_only"); continue
            out.append(r)
        return out

    def ground(self, recs):
        out = []
        for r in recs:
            rec, eid = r["rec"], r["eid"]
            q = rec.get("quantity", "")
            bad = []
            if q and q not in L.QUANTITIES:
                bad.append(("quantity", q))
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
            if normalize(r["rec"]["quote"]) in normalize(self.text.get(r["eid"], "")):
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
        k, rows = self.key, []
        ok_ev = lambda ids: ";".join(sorted({i for i in ids if i in self.order}, key=self.order.get))

        def row(**kw):
            r = {f: "" for f in F.FIELDS}
            r.update(kw)
            r["author"] = self.pid
            return r
        rows.append(row(fact_id=k, type="paper", evidence=self.els[0]["element_id"], statement=f"the paper {self.pid} ({k}) as compiled from its extraction records"))
        items = [it for it in self.pass0 if isinstance(it, dict)]
        runs = [it for it in items if it["role"] == "run"]
        specs = [it for it in items if it["role"] == "specimen"]
        sims = [it for it in items if it["role"] == "simulation"]
        self.node = {}                                                          # name as printed -> (node id, role)
        used = set()

        def uid(base):
            i, n = base, 2
            while i in used:
                i, n = f"{base}_{n}", n + 1
            used.add(i)
            return i
        if runs or specs:
            ev = ok_ev([e for it in runs + specs for e in it["introduced_in"]])
            rows.append(row(fact_id=f"{k}:recipe", type="activity", kind="recipe", how="inferred", evidence=ev, parent=k,
                            statement=f"the deposition recipe of {k}: the runs and specimens its first pass names", label_as_printed="recipe"))
        for it in runs:
            i = uid(f"{k}:run:{slug(it['name_as_printed'])}")
            self.node[it["name_as_printed"]] = (i, "run")
            rows.append(row(fact_id=i, type="activity", kind="deposition", how="stated", evidence=ok_ev(it["introduced_in"]), parent=f"{k}:recipe",
                            statement=f"deposition run named {it['name_as_printed']!r} in the first pass", label_as_printed=it["name_as_printed"]))
        for it in specs:
            share = [n for n in runs if set(n["introduced_in"]) & set(it["introduced_in"])]
            if len(share) == 1:
                dep = self.node[share[0]["name_as_printed"]][0]
                self.note(f"h: specimen {it['name_as_printed']!r} under run {dep} (one run shares an element of introduced_in)")
            else:
                dep = uid(f"{k}:dep:{slug(it['name_as_printed'])}")
                rows.append(row(fact_id=dep, type="activity", kind="deposition", how="inferred", evidence=ok_ev(it["introduced_in"]), parent=f"{k}:recipe",
                                statement=f"the deposition that made the specimen named {it['name_as_printed']!r}", label_as_printed=f"deposition of {it['name_as_printed']}"))
                self.note(f"h: specimen {it['name_as_printed']!r}: own deposition {dep} ({len(share)} runs share an element of introduced_in)")
            i = uid(f"{k}:ent:{slug(it['name_as_printed'])}")
            self.node[it["name_as_printed"]] = (i, "specimen")
            q = ";".join(f"{a}={it[a]}" for a in ("specimen_class", "structure_class") if it.get(a))
            rows.append(row(fact_id=i, type="entity", how="stated", evidence=ok_ev(it["introduced_in"]), parent=dep, qualifiers=q,
                            statement=f"specimen named {it['name_as_printed']!r} in the first pass", label_as_printed=it["name_as_printed"]))
        for it in sims:
            i = uid(f"{k}:sim:{slug(it['name_as_printed'])}")
            self.node[it["name_as_printed"]] = (i, "simulation")
            rows.append(row(fact_id=i, type="activity", kind="simulation", how="stated", evidence=ok_ev(it["introduced_in"]), parent=k,
                            statement=f"simulation named {it['name_as_printed']!r} in the first pass", label_as_printed=it["name_as_printed"]))
        self.note(f"h: tree from pass 0: {len(runs)} runs, {len(specs)} specimens, {len(sims)} simulations; "
                  f"{sum(it['role'] == 'cited_work' for it in items)} cited works (mention names only, no row); identity rows: none (pass 0 carries no identity; gold 1)")
        self.sole_run = self.node[runs[0]["name_as_printed"]][0] if len(runs) == 1 else ""
        self.sole_sim = self.node[sims[0]["name_as_printed"]][0] if len(sims) == 1 else ""
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

    def figures(self):
        """P136 1c: kb/<pid>.figures.json, its fields as they are. A simulated curve -> an entity (the run it shows) under the simulation
        whose pass-0 introduced_in shares an element with the figure (else the only simulation, else the paper, logged), its model row
        (quantity = the curve's y quantity, no value) and the conditions it does not share with its set as settings (model_input); a
        measured curve -> its observation row and its own conditions under the measurement activity of the specimen whose introduced_in
        shares an element with the figure (else the paper, logged); a set -> its conditions as settings under the set's activity and
        one comparison (kind, varied; links = the first curve row as purpose, then the curve entities). Returns (tree rows, fact rows)."""
        p = C.V2 / "kb" / f"{self.pid}.figures.json"
        if not p.exists():
            self.note("1c: no figures.json")
            return [], []
        Fj, k = json.loads(p.read_text(encoding="utf-8")), self.key
        tree, facts = [], []
        sims = [r for r in self.rows_tree if r["type"] == "activity" and r["kind"] == "simulation"]
        specs = [r for r in self.rows_tree if r["type"] == "entity"]

        def els(fig, panel=""):
            return [e for e in (f"fig{fig}{panel}", f"fig{fig}", f"fig{fig}.cap") if e in self.order]

        def owner(fig, rows, fallback=""):
            hit = [r["fact_id"] for r in rows if set(r["evidence"].split(";")) & set(els(fig))]
            return hit[0] if len(hit) == 1 else fallback

        def row(**kw):
            r = {x: "" for x in F.FIELDS}
            r.update(kw)
            r["author"] = self.pid
            return r

        def settings(conds, parent, ev, kind, mentions=""):
            for c in conds.values():
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
        members = collections.defaultdict(list)
        first = {}
        for cu in Fj.get("curves", []):
            ev = ";".join(els(cu["figure"], cu.get("panel", "")))
            st = sets.get(cu.get("set") or "")
            shared = st["conditions"] if st else {}
            own = {q: c for q, c in (cu.get("conditions") or {}).items() if shared.get(q, {}).get("value") != c.get("value")}
            y, lab = cu["y"], cu.get("series", {}).get("label_raw", "")
            if y.get("quantity") not in L.QUANTITIES:
                self.count("1c", "curve y quantity not an id"); continue
            if cu["kind"] == "simulated":
                sim = owner(cu["figure"], sims, self.sole_sim)
                if not sim:
                    self.count("1c", "curve parent: paper (no simulation found)")
                e = f"{k}:figrun:{cu['id'].split(':', 1)[1].replace('#', '.')}"
                tree.append(row(fact_id=e, type="entity", how="stated", evidence=ev, parent=sim or k, label_as_printed=lab or cu["id"],
                                statement=f"the simulation run of curve {cu['id']} ({lab or 'no series label'})"))
                members[cu.get("set") or ""].append(e)
                parent, kind = e, "model_input"
                facts.append(row(type="model", quantity=y["quantity"], label_as_printed=y.get("label_raw", "") or y["quantity"], data_kind="simulated",
                                 mentions=lab, evidence=ev, parent=e))
            else:
                spec = owner(cu["figure"], specs)
                parent, kind = (self.measurement(spec, ""), "stated") if spec else (k, "stated")
                if not spec:
                    self.count("1c", "curve parent: paper (no specimen found)")
                facts.append(row(type="observation", quantity=y["quantity"], label_as_printed=y.get("label_raw", "") or y["quantity"], data_kind="read_from_figure",
                                 mentions=lab, evidence=ev, parent=parent))
            first.setdefault(cu.get("set") or "", facts[-1])
            self.count("1c", f"curve {cu['kind']}")
            settings(own, parent, ev, kind, mentions=lab)
        for sid, st in sets.items():
            ev = ";".join(els(st["figure"], st.get("panel", "")))
            sim = owner(st["figure"], sims, self.sole_sim)
            spec = owner(st["figure"], specs)
            act = sim if members[sid] and sim else (self.measurement(spec, "") if spec else "")
            if act:
                settings(st.get("conditions") or {}, act, ev, "model_input" if act == sim else "stated")
            else:
                self.count("1c", "set conditions skipped (no activity found)")
            if len(members[sid]) >= 2 and sid in first and st.get("varied") in L.QUANTITIES:
                first[sid]["_purpose_of"] = sid
                tree.append(row(fact_id=f"{k}:figset:{sid.split(':')[-1]}", type="comparison", kind=st["kind"], how="stated", quantity=st["varied"],
                                label_as_printed=st.get("label", ""), evidence=ev, parent=k, links="", _members=members[sid], _sid=sid,
                                statement=f"the curves of figure set {sid} as a comparison, varying {L.NAMES.get(st['varied'], st['varied'])}"))
                self.count("1c", "comparison")
            else:
                self.count("1c", "set without a comparison (fewer than two curve entities or no varied id)")
        return tree, facts

    def parent(self, r):
        """h: claim, definition, caveat and cited under the paper (gold shape); a model input -> its simulation; a model -> its
        simulation; a setting -> its run or the recipe (D9); a value naming exactly one specimen -> that specimen's measurement activity."""
        rec, k = r["rec"], self.key
        t = rec["type"]
        if t in ("claim", "definition", "caveat", "cited"):
            return k, "paper"
        if r["unmatched"]:
            return "", "mention_unmatched"
        named = collections.defaultdict(list)
        for it in r["named"]:
            if it["name_as_printed"] in self.node:
                i, role = self.node[it["name_as_printed"]]
                named[role].append(i)
        if rec.get("kind") == "model_input" or t == "model":
            s = named["simulation"]
            if len(s) == 1:
                return s[0], "simulation (named)"
            if not s and self.sole_sim:
                return self.sole_sim, "simulation (the only one)"
        if t == "setting":                                                      # a setting belongs to a run: the one it names; naming none (D9),
            if len(named["run"]) == 1:                                          # the run of the one specimen it names, else the only run, else the
                return named["run"][0], "run (named)"                           # recipe (gold shape); naming several runs, the recipe they share
            if not named["run"] and len(named["specimen"]) == 1:
                e = named["specimen"][0]
                return next(x["parent"] for x in self.rows_tree if x["fact_id"] == e), "run of the named specimen"
            if not named["run"] and self.sole_run:
                return self.sole_run, "run (the only one)"
            return f"{self.key}:recipe", "parent_recipe"
        if any(rec.get(x) not in (None, "") for x in VALUE_KEYS) and t in ("observation", "derived", "model") and len(named["specimen"]) == 1:
            return self.measurement(named["specimen"][0], rec.get("method", "")), "measurement of the named specimen"
        return "", "parent_undecided"

    # ------------------------------------------------------------------------------------------------------------ rows
    def fact_row(self, r, parent):
        rec = r["rec"]
        f = {x: "" for x in F.FIELDS}
        for a in ("type", "quantity", "label_as_printed", "censor", "value_text", "method", "uncertainty_kind", "relation", "stance"):
            f[a] = str(rec.get(a, "") or "")
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
        return f

    def dedupe(self, items):
        """i (D3): equal DEDUPE_KEY from different elements -> one record, evidence = all element ids in element order. Value records
        only; P136 1a: a definition by its normalized term (term, else label_as_printed, else the first mention)."""
        seen, out = {}, []
        for f in items:
            if f["type"] == "definition":
                t = normalize(f["term"] or f["label_as_printed"] or f["mentions"].split(";")[0]).lower()
                if not t:
                    out.append(f); continue
                key = ("definition", t)
                if key in seen:
                    g = seen[key]
                    g["evidence"] = ";".join(sorted(set(g["evidence"].split(";")) | set(f["evidence"].split(";")), key=self.order.get))
                    self.count("i", "definition merged")
                    self.note(f"i: definition {t!r}: merged {f['evidence']} into {g['evidence']}")
                    continue
                seen[key] = f
                out.append(f); continue
            if not any(f[x] for x in VALUE_KEYS):
                out.append(f); continue
            key = tuple(f[x] for x in DEDUPE_KEY)
            if key in seen and f["evidence"] not in seen[key]["evidence"].split(";"):
                g = seen[key]
                g["evidence"] = ";".join(sorted(set(g["evidence"].split(";")) | {f["evidence"]}, key=self.order.get))
                self.count("i", "merged")
                self.note(f"i: merged {f['evidence']} into {g['evidence']} ({f['quantity']} {f['value'] or f['value_text']})")
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
                d = Q.derive(T, e, did)
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
        self.note("j: comparisons skipped (D8): gold has 3")
        self.n_derived = len(out)
        return rows + out

    def statements(self, rows):
        """k: one line from the fields; an optional part is left out when the line would repeat eight words of its element."""
        seen = collections.Counter()
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
            while True:
                s = head + "".join(optional) + kind
                if not copies(s, [self.text.get(e, "") for e in f["evidence"].split(";")]) or not optional:
                    break
                optional.pop()
                self.count("k", "statement_part_left_out")
            if copies(s, [self.text.get(e, "") for e in f["evidence"].split(";")]):
                self.count("k", "statement_copies_text")
            key = " ".join(words(s))
            seen[key] += 1
            if seen[key] > 1:
                s += f" (record {seen[key]} of this wording, from {f['evidence'].split(';')[0]})"
            f["statement"] = s
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
        items = self.dedupe(items + fig_facts)
        self.count("i", "kept", len(items))
        items = self.ids(items)
        for c in fig_tree:                                                      # 1c: a comparison's links once its purpose row has an id
            if c["type"] == "comparison":
                sid = c.pop("_sid")
                purpose = next(f["fact_id"] for f in items if f.get("_purpose_of") == sid)
                c["links"] = ";".join([purpose] + c.pop("_members"))
        rows = tree + fig_tree + list(self.meas.values()) + items
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
        return dim, float(f"{v * fac:.6g}")
    return f["value"], f["unit"]


def match_key(f):
    """The P134 match on the value side, P136 1d: type, quantity, the value in canonical units, value_text."""
    return f["type"], f["quantity"], canon(f), f["value_text"].lower()


def diff(run):
    """Gold pilot/<pid>.facts.csv against the compiled rows: a match shares an evidence element and has equal type, quantity, value,
    value in canonical units (canon) and value_text; one gold row per compiled row, first come."""
    gold = list(csv.DictReader((C.V2 / "kb" / "pilot" / f"{run.pid}.facts.csv").open(encoding="utf-8")))
    comp = run.rows
    key = match_key
    free = list(range(len(gold)))
    matched = collections.Counter()
    for c in comp:
        ce = set(c["evidence"].split(";")) - {""}
        for j in free:
            g = gold[j]
            if key(g) == key(c) and ce & set(g["evidence"].split(";")):
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
