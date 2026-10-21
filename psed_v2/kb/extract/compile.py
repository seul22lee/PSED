#!/usr/bin/env python3
"""P134 compiler: records/<pid>.jsonl -> compiled/<pid>.facts.csv (facts.FIELDS), with .unmapped.csv, .dropped.csv, .coverage.csv,
.experiments.csv (pilot/experiments.py on the compiled tree, for check.py), .compile.log and .summary.csv. No provider call.

    python3 psed_v2/extract/compile.py yli18          # then: python3 psed_v2/pilot/check.py --dir psed_v2/compiled

Input: the groups of pass1_elements.groups(pid); per group the latest pass-1 line of that section name (lines of a name no group has
are ignored); the latest pass-0 line. Steps: a schema (form.json), b type rules, c grounding, d quote, e units, f species/structure
ids, g mentions, h tree and placement (place(), the pilot rule), i dedupe, j derived (query layer), k statements, l coverage,
m facts.csv. Then the diff against the gold pilot/<pid>.facts.csv (read only). P148 (C6, user correction in P148 D): a record is
dropped for a form.json error (any validator, after the numeric strings are coerced, C4; the reason names the validator), a quote not
found (after C3), or a pass-0 data id not in figures.json; every other finding is logged and the record kept.
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
NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
MARKUP = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>")                      # P148 C3: a markup tag (an autolink <https://...> is not one)


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
    """D10, the one normalization of steps d, e and f: P148 (C3): markup tags removed, their text kept; U+2212 -> -; thin and no-break
    spaces -> space; \\text{..} / \\mathrm{..} -> content; unicode NFKC; μ (U+03BC) and \\mu -> µ (U+00B5); \\circ / ^\\circ -> °;
    \\times -> ×; ◦C / ° C / deg C -> °C (P146); $ _ ^ { } and markdown * dropped; whitespace collapsed; casefolded (P140 C1)."""
    t = MARKUP.sub("", t or "").replace("\u2212", "-")
    t = re.sub(r"[\u00a0\u2007\u2009\u200a\u202f]", " ", t)
    t = re.sub(r"\\(?:text|mathrm)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\^?\{?\\circ\}?\s*", "°", t)                                       # P136 1b: ^\circ C -> °C
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\\mu\s*", "µ", t).replace("\u03bc", "µ")
    t = re.sub(r"\\times\s*", "×", t)                                                  # P136b: 50\times -> 50×
    t = t.replace("\u25e6", "°")                                                     # P146: ◦C, ° C, deg C -> °C
    t = re.sub(r"°\s+([CFK])\b", r"°\1", t)
    t = re.sub(r"\bdeg\.?\s*C\b", "°C", t)
    t = re.sub(r"[$_^{}*]", "", t)
    return norm_ws(t).casefold()                                                # P140 C1: casefolded (no unit spelling collides; checked)


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
CATEGORICAL_ALIASES = {q: {normalize(a).lower(): v for v in vs for a in [v] + V.VALUE_ALIASES.get(q, {}).get(v, [])}
                       for q, vs in V.FORM_CATEGORICAL_VALUES.items()}           # P149 F3: crystallinity's value ids and their value_aliases


def categorical(q, text):
    """P149 F3: the value id of a FORM_CATEGORICALS quantity a value_text stands for (normalize()d, any case), else None."""
    return CATEGORICAL_ALIASES.get(q, {}).get(normalize(text or "").lower())


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
        before = [n for n, x in enumerate(lines, 1) if x["pass"] == 0 and used and n < min(used)]
        p0 = before[-1] if before else p0                                       # P143b: the pass-0 line the pass-1 lines in use were written against
        ignored = [n for n, x in enumerate(lines, 1) if x["pass"] == 1 and n not in used]
        self.lines_used, self.lines_ignored = sorted(used | {p0}), ignored
        self.note(f"input: {len(lines)} lines; pass 0 = line {p0}; {len(used)} pass-1 lines for {len(self.groups)} groups; ignored lines "
                  + ", ".join(f"{n} ({lines[n - 1]['section']})" for n in ignored))
        for g in self.groups:
            if g not in latest:
                self.note(f"input: group {g} has no pass-1 line")
        p0obj = C.loads_json(lines[p0 - 1]["response"])
        self.pass0 = (p0obj.get("units") or []) if isinstance(p0obj, dict) else p0obj    # P144: {units, table_layouts, panel_layouts}
        self.layouts = {k: (p0obj.get(k) or []) for k in ("table_layouts", "panel_layouts")} if isinstance(p0obj, dict) else {}
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
                    if "parent" in rec and "about" not in rec:                  # P148: a line written before the form's parent became about
                        rec["about"] = rec.pop("parent")
                        self.count("input", "parent read as about (older line)")
                    recs.append(dict(eid=eid, rec=rec, seq=i))
        self.count("input", "records", len(recs))
        return recs

    # ------------------------------------------------------------------------------------------------------------ a-g
    def validate(self, recs):
        """a: D12 (a variable's quantity outside the enum -> null); C4 (P148): a numeric string in a number field (value, value_min,
        value_max, uncertainty, uncertainty_n, a numeric qualifier) -> the number, logged; C5 (P148): a variable whose quantity is null
        -> the quantity of the same paper's definition of that term (normalize()d; a term two definitions give different quantities is
        left null), logged; then form.json: C6 (P148, corrected in P148 D) every error drops the record, the reason
        schema:<validator> (inside a nullable anyOf, the validator of its non-null branch)."""
        from jsonschema import Draft202012Validator
        form = C.schema("form.json")
        val, qids = Draft202012Validator(form), set(form["$defs"]["quantity_id"]["enum"])
        branch = lambda p: next((x for x in p.get("anyOf", []) if x.get("type") != "null"), p)                     # noqa: E731
        nums = {k_: branch(p).get("type") for k_, p in form["properties"].items() if branch(p).get("type") in ("number", "integer")}
        qnum = {k_ for k_, p in form["properties"]["qualifiers"]["anyOf"][0]["properties"].items()
                if p.get("type") == "number" or any(x.get("type") == "number" for x in p.get("anyOf", []))}
        for r in recs:
            rec = r["rec"]
            vs = rec.get("variables")
            for sym, q in (vs.items() if isinstance(vs, dict) else []):          # D12: a symbol's quantity outside the enum -> null, logged
                if q is not None and q not in qids:
                    vs[sym] = None
                    self.count("a", "variables_unmapped (set to null)")
                    self.note(f"a: {r['eid']}: variables_unmapped {sym!r} -> {q!r}")
            for k_, t in nums.items():                                          # C4
                rec[k_] = self.coerce(r["eid"], k_, rec.get(k_), t)
            if isinstance(rec.get("qualifiers"), dict):
                for k_ in qnum & set(rec["qualifiers"]):
                    rec["qualifiers"][k_] = self.coerce(r["eid"], f"qualifiers.{k_}", rec["qualifiers"][k_], "number")
            hit = categorical(rec.get("quantity"), rec.get("value_text")) if isinstance(rec.get("quantity"), str) and rec.get("value_text") else None
            if hit and hit != rec["value_text"]:                                # P149 F3: the value id, before form.json's enum
                self.count("a", f"{rec['quantity']} value_text resolved (F3)")
                self.note(f"a: {r['eid']}: {rec['quantity']} value_text {rec['value_text']!r} -> {hit!r} (F3)")
                rec["value_text"] = hit
        terms = collections.defaultdict(set)                                    # C5: term -> quantity, from the paper's definition records
        for r in recs:
            rec = r["rec"]
            if rec.get("type") == "definition" and isinstance(rec.get("quantity"), str) and rec["quantity"] in qids:
                for t in {rec.get("term"), rec.get("label_as_printed")} - {None, ""}:
                    terms[normalize(t)].add(rec["quantity"])
        for r in recs:
            vs = r["rec"].get("variables")
            for sym in [x for x, q in (vs.items() if isinstance(vs, dict) else []) if q is None]:
                got = terms.get(normalize(sym), set())
                if len(got) == 1:
                    vs[sym] = next(iter(got))
                    self.count("a", "variable filled from a definition (C5)")
                    self.note(f"a: {r['eid']}: variable {sym!r} -> {vs[sym]} (C5, from the paper's definition)")
                elif got:
                    self.count("a", "variable left null: definitions disagree (C5)")
        out = []
        for r in recs:
            for k_ in form["required"]:                                         # P139: a missing field is a null
                r["rec"].setdefault(k_, None)
            if r["rec"].get("type") is None:
                self.drop("a", r["eid"], r["rec"], "schema:type null", "type"); continue
            errs = list(val.iter_errors(r["rec"]))
            if errs:                                                            # P148 D: every form.json error drops
                e = errs[0]
                field = ".".join(str(p) for p in e.path) or e.validator
                self.drop("a", r["eid"], r["rec"], f"schema:{leaf(e)}", field)
                self.count("a_fields", field)
                continue
            r["rec"] = {k_: (({q: v for q, v in x.items() if v is not None} if k_ == "qualifiers" else x) if isinstance(x, dict) else x)
                        for k_, x in r["rec"].items() if x is not None}         # P139: null = absent
            out.append(r)
        return out

    def coerce(self, eid, field, v, t):
        """C4: a numeric string (U+2212 read as -) -> its number (an integer field: an integer), logged; anything else as it is."""
        if not isinstance(v, str) or not NUMBER.fullmatch(v.strip().replace("\u2212", "-")):
            return v
        x = float(v.strip().replace("\u2212", "-"))
        x = int(x) if t == "integer" and x.is_integer() else x
        self.count("a", "numeric string coerced (C4)")
        self.note(f"a: {eid}: {field} {v!r} -> {x!r} (C4)")
        return x

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
            if bad:                                                             # C6: form.json validated these ids; a miss here is a bug, kept and logged
                for field, x in bad:
                    self.unmapped.append(dict(element=eid, field=field, id=x, label_as_printed=rec.get("label_as_printed", ""), unit=rec.get("unit", ""),
                                              candidate="", action="kept (bug: passed form.json)"))
                self.count("c", "BUG: id not in the vocabulary after form.json (kept)")
                self.note(f"c: BUG {eid}: {bad} not in the vocabulary after form.json (kept)")
            if q == "other":
                self.unmapped.append(dict(element=eid, field="quantity", id="other", label_as_printed=rec.get("label_as_printed", ""), unit=rec.get("unit", ""),
                                          candidate=json.dumps(rec.get("candidate", {}), ensure_ascii=False), action="kept"))
                self.count("c", "quantity_other (kept)")
            out.append(r)
        return out

    def scope(self, eid):
        """C3 (P148): the texts a quote is checked against: the element; a table cell: + the cells of its row and the table's caption;
        a figure element (caption or panel): + the figures.json series labels of that figure; P150 X2: + the texts and labels of the
        figures.json cells and peaks of the panel (of the whole figure for a caption or a one-panel figure): value_text, label, the
        value and the at coordinates as printed."""
        out = [self.text.get(eid, "")]
        m = re.fullmatch(r"(tab\w*?)\.r(\d+)c\d+", eid)
        if m:
            out += [self.text[e] for e in self.order if e != eid and re.fullmatch(rf"{re.escape(m.group(1))}\.r{m.group(2)}c\d+", e)]
            out.append(self.text.get(f"{m.group(1)}.cap", ""))
        f = re.fullmatch(r"fig(\d+)([a-zA-Z]*|\.cap)", eid)
        if f:
            out += self.labels.get(f.group(1), [])
            panel = f.group(2) if f.group(2) != ".cap" else ""
            out += [t for (n, pn), ts in self.cells.items() if n == f.group(1) and (not panel or pn == panel) for t in ts]   # P150 X2
        return out

    def quotes(self, recs):
        """d (D11): the quote, normalize()d, in the normalized texts of the record's scope (scope()), contiguous or every token in
        order (P140 C1); a null quote is not found."""
        self.labels = collections.defaultdict(list)
        p = C.V2 / "kb" / f"{self.pid}.figures.json"
        Fj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        for c in Fj.get("curves", []):
            if c.get("series", {}).get("label_raw"):
                self.labels[str(c["figure"])].append(c["series"]["label_raw"])
        self.cells = collections.defaultdict(list)                              # P150 X2: (figure, panel) -> cell and peak texts
        for v in Fj.get("values", []):
            self.cells[(str(v["figure"]), v.get("panel", ""))] += [str(x) for x in (v.get("value_text"), v.get("label"), v.get("value_raw", v.get("value")),
                                                                                    *(v.get("at_raw") or {}).values()) if x not in (None, "")]
        out = []
        for r in recs:
            q, txt = normalize(r["rec"].get("quote") or ""), normalize(" ".join(self.scope(r["eid"])))
            if not q:
                self.drop("d", r["eid"], r["rec"], "quote_not_found", "quote")
            elif q in txt:
                out.append(r)
            elif in_order(q.split(), txt):                                      # P140 C1: every token in order, gaps allowed
                self.count("d", "quote_noncontiguous (kept)")
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
                if s is None:                                                   # C6: kept with the unit as printed, logged
                    self.unmapped.append(dict(element=r["eid"], field="unit", id=normalize(rec["unit"]), label_as_printed=rec.get("label_as_printed", ""),
                                              unit=rec["unit"], candidate="", action="kept (unit as printed)"))
                    self.count("e", "unit_unresolved (kept as printed)")
                    s = rec["unit"]
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
                if hit is None:                                                 # C6: kept with its value_text, logged
                    self.count("f", "species_unresolved (kept)")
                    self.unmapped.append(dict(element=r["eid"], field=q, id=rec.get("value_text", ""), label_as_printed=rec.get("label_as_printed", ""),
                                              unit="", candidate="", action="kept (value_text as given)"))
                    out.append(r)
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
        parent names (else under the recipe, logged); P143b: a model run -> an entity under the simulation its parent names (else
        under the paper, logged); series and cited works are no units (no row). self.node: pass-0 id -> (row id, role)."""
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
        rows.append(row(fact_id=f"{k}:recipe", type="activity", kind="recipe", how="inferred", parent=k, label_as_printed="recipe",   # P148: always (C1)
                        evidence=ok_ev([e for it in role("run") + role("specimen") for e in it.get("introduced_in") or []]) or self.els[0]["element_id"],
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
        for it in role("model_run"):                                           # P143b
            par = self.node.get(it.get("parent", ""), ("", ""))
            if par[1] != "simulation":
                self.count("h", "model run without a simulation parent (under the paper)")
            self.node[it["id"]] = (f"{k}:mrun:{slug(it['id'])}", "model_run")
            rows.append(row(fact_id=self.node[it["id"]][0], type="entity", how="stated", evidence=ok_ev(it.get("introduced_in") or []),
                            parent=par[0] if par[1] == "simulation" else k, label_as_printed=it.get("name_as_printed") or it["id"],
                            statement=f"model run {it['id']} ({it.get('name_as_printed')!r})"))
        self.note("h: tree from pass 0: " + ", ".join(f"{r} {len(role(r))}" for r in ("run", "simulation", "specimen", "model_run", "series", "cited_work"))
                  + "; identity rows: none (pass 0 carries no identity)")
        self.rows_tree = rows
        self.meas, self.films = {}, {}
        self.up = {r["fact_id"]: r["parent"] for r in rows}                     # P148: a unit row -> its parent row (place())
        self.under = collections.defaultdict(list)                             # a run / simulation row -> its specimen / model-run rows
        for nid, role_ in self.node.values():
            if role_ in ("specimen", "model_run"):
                self.under[self.up[nid]].append(nid)
        return rows

    def measurement(self, ent, method):
        """<ent>:meas:<method>; P148 (C1): "measurement" when the method is not in facts.MEAS_METHODS."""
        method = method if method in F.MEAS_METHODS else ""
        i = f"{ent}:meas:{method or 'measurement'}"
        if i not in self.meas:
            ent_row = next(r for r in self.rows_tree if r["fact_id"] == ent)
            r = {f: "" for f in F.FIELDS}
            r.update(fact_id=i, type="activity", kind="measurement", how="inferred", parent=ent, author=self.pid,
                     qualifiers=f"mode={L.METHOD_MODE.get(method, 'not_stated')}", label_as_printed=f"{method or 'measurement'} of {ent_row['label_as_printed']}",
                     statement=f"the {method.replace('_', ' ') if method else 'unstated'} measurement of the specimen named {ent_row['label_as_printed']!r}")
            self.meas[i] = r
        return i

    def method_activity(self, method):
        """P148 (C1, retree()): <paper>:method:<method>, a measurement activity under the paper for the paper-wide records of a method."""
        i = f"{self.key}:method:{method}"
        if i not in self.meas:
            r = {f: "" for f in F.FIELDS}
            r.update(fact_id=i, type="activity", kind="measurement", how="inferred", parent=self.key, author=self.pid,
                     qualifiers=f"mode={L.METHOD_MODE.get(method, 'not_stated')}", label_as_printed=f"{method.replace('_', ' ')} (method)",
                     statement=f"the {method.replace('_', ' ')} measurement settings the paper shares")
            self.meas[i] = r
        return i

    def run_entity(self, run):
        """P148 D (user: no run-level measurement node; P146: the run-level specimen is the compiler's): the specimen a result about a
        run goes to: the run's one pass-0 specimen, else (none or several) its "film of <run>". Returns (entity, which)."""
        sp = self.under.get(run, [])
        if len(sp) == 1:
            return sp[0], "its specimen"
        if sp:
            self.count("h", "film of a run with several specimens")
        return self.film(run), "film" if not sp else "film (several specimens)"

    def film(self, run):
        """P146: the specimen "film of <run>" of a run the pass-0 units give no specimen (how inferred, logged specimen_created); the
        one unit the compiler makes (C2)."""
        if run not in self.films:
            lab = next((r["label_as_printed"] for r in self.rows_tree if r["fact_id"] == run), run)
            e = f"{run}:film"
            self.rows_tree.append({**{x: "" for x in F.FIELDS}, "fact_id": e, "type": "entity", "how": "inferred", "parent": run, "author": self.pid,
                                   "evidence": next((r["evidence"] for r in self.rows_tree if r["fact_id"] == run), ""),
                                   "label_as_printed": f"film of {lab}", "statement": f"the film of run {lab} (the run states no specimen)"})
            self.films[run] = e
            self.count("h", "specimen_created")
            self.note(f"h: specimen_created {e}")
        return self.films[run]

    def figures(self):
        """P143b: kb/<pid>.figures.json curves through the pass-0 units' curves field, the curve fields as they are. A curve a model run
        names -> a model row (y quantity, no value) under that model run's entity, its conditions as model_input settings there; a curve
        a specimen names -> an observation row under the specimen's measurement activity, its conditions as settings of the specimen;
        P144: a curve a run names -> an observation row under the run's measurement activity, its conditions as settings of the run (no
        entity is made); a curve no unit names -> logged and left out (no fallback). Returns (tree rows, fact rows)."""
        p = C.V2 / "kb" / f"{self.pid}.figures.json"
        Fj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        k, tree, facts = self.key, [], []
        owner, drole = {}, {}
        known = {x.get("id") for sec in ("curves", "values", "sets", "derived") for x in Fj.get(sec) or []}
        for i, it in self.p0.items():
            for d in (it.get("data") or it.get("curves") or []):               # P146: data = [{id, role}]; P145 ids, curves on older lines
                cid = d.get("id") if isinstance(d, dict) else d
                if cid not in known:                                            # C6: the third drop reason
                    self.drop("1c", i, {"type": "data", "quantity": ""}, "data_id_not_in_figures_json", str(cid)); continue
                owner.setdefault(cid, []).append(i)
                drole[(i, cid)] = (d.get("role") if isinstance(d, dict) else None) or ("simulated" if it.get("role") == "model_run" else "measured")

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
                                 value_min=lo, value_max=hi, unit=u, data_kind=kind, mentions=mentions, evidence=ev, parent=parent, _unit=parent))
                self.count("1c", "setting")

        def result(cu, parent, typ):
            y = cu["y"]
            if y.get("quantity") not in L.QUANTITIES:
                self.count("1c", "curve y quantity not an id"); return
            facts.append(row(type=typ, quantity=y["quantity"], label_as_printed=y.get("label_raw", "") or y["quantity"],
                             data_kind="simulated" if typ == "model" else "read_from_figure", mentions=cu.get("series", {}).get("label_raw", ""),
                             evidence=";".join(els(cu["figure"], cu.get("panel", ""))), parent=parent))
            self.count("1c", f"curve -> {typ}")
        unowned = []
        for cu in Fj.get("curves", []):
            own = [i for i in owner.get(cu["id"], []) if i in self.node]
            if len(own) != 1:
                if own:
                    self.count("1c", "curve named by several units (left out)")
                    continue
                unowned.append(cu); continue
            nid, role = self.node[own[0]]
            conds = list((cu.get("conditions") or {}).values())
            ev = ";".join(els(cu["figure"], cu.get("panel", "")))
            lab = cu.get("series", {}).get("label_raw", "")
            dr = drole[(own[0], cu["id"])]                                      # P146: the row type from the data role (figures.json kind not read)
            if role not in ("model_run", "specimen", "run"):
                self.count("1c", f"curve named by a {role} (left out)"); continue
            settings(conds, nid, ev, "model_input" if role == "model_run" else "stated", lab)
            if dr == "measured":
                result(cu, "@meas:" + nid, "observation")
            else:
                result(cu, nid, "model")
                if dr == "fitted":
                    facts[-1]["data_kind"] = "computed_by_authors"
            self.count("1c", f"data role {dr}")

        for v in Fj.get("values", []):                                          # P145: a cell or a peak a unit names
            own = [i for i in owner.get(v["id"], []) if i in self.node]
            if len(own) != 1:
                self.count("1c", f"{v.get('kind', 'value')} not named by exactly one unit (left out)"); continue
            nid, role = self.node[own[0]]
            dr = drole[(own[0], v["id"])]
            ev = ";".join(els(v["figure"], v.get("panel", "")))
            at = [dict(quantity=q, value=x, value_max=None, key_raw=q, unit=L.ENTRIES.get(q, {}).get("unit", "")) for q, x in (v.get("at") or {}).items()]
            settings(at + list((v.get("conditions") or {}).values()), nid, ev, "model_input" if role == "model_run" else "stated", v.get("label", ""))
            q = v.get("quantity") or ""
            if q not in L.QUANTITIES:
                self.count("1c", f"{v.get('kind', 'value')} without a quantity id (result left out)"); continue
            u = unit_symbol(v.get("unit") or "") if v.get("unit") else ""
            vt = v.get("value_text") or ""
            if q in CATEGORICAL_ALIASES and vt:                                 # P149 F3: a cell's value_text resolved to the value id
                hit = categorical(q, vt)
                self.count("1c", f"{q} value_text resolved (F3)" if hit else f"{q} value_text not in its value set (kept as printed)")
                vt = hit or vt
            facts.append(row(type="observation" if dr == "measured" else "model", quantity=q, label_as_printed=v.get("label") or q,
                             value=f"{v['value']:.6g}" if v.get("value") is not None else "", value_text=vt, unit=u or "",
                             data_kind={"measured": "read_from_figure", "fitted": "computed_by_authors"}.get(dr, "simulated"), evidence=ev,
                             parent="@meas:" + nid if dr == "measured" else nid))
            self.count("1c", f"{v.get('kind', 'value')} -> {facts[-1]['type']}")
        if unowned:                                                             # P144: no fallback
            self.count("1c", "curves no unit names (left out)", len(unowned))
            self.note(f"1c: {len(unowned)} curves no pass-0 unit names, left out: " + ", ".join(c["id"] for c in unowned))
        return tree, facts

    def specimens_for_runs(self, facts):
        """P146: the result rows a run carries directly (an observation, a derived or a model row whose parent is the run or the run's
        measurement) move to a specimen: P148 D run_entity() (the run's one specimen, else "film of <run>", how inferred, logged
        specimen_created); an observation to that specimen's measurement activity of the row's method. No measurement node under a
        run. Structure the pilot tree needs, not a count judgement."""
        runs = {nid for nid, role in self.node.values() if role == "run"}
        for run in sorted(runs):
            res = [f for f in facts if f["type"] in ("observation", "derived", "model") and f["parent"] in (run, "@meas:" + run)]
            if not res:
                continue
            e = self.run_entity(run)[0]
            for f in res:
                f["parent"] = self.measurement(e, f["method"]) if f["type"] == "observation" else e
            self.note(f"h: {len(res)} result rows moved to {e}")

    def comparisons(self, rows):
        """P143b: comparisons derived from the condition vectors of the experiment units (entities), never asked of the extractor and
        never a parent. A unit's vector: the settings (quantity, qualifiers -> value in canonical units, else value_text) on the unit and
        on the activities and entities above it, measurement activities excepted. Units are compared within one top activity under the
        paper (a recipe or a simulation) and only with units of the same vector keys. replicate: two or more units with equal vectors;
        series: two or more units equal except in one quantity, which takes two or more values; grid: three or more units equal except
        in two quantities, each taking two or more values. A comparison: kind, quantity (the varied ids), links = a result row of its
        first member as purpose, then the members; label = the label_as_printed of a series-name setting (quantity other, no value,
        mentions naming two or more of the members), when one names exactly these members or a subset of them."""
        R_ = {r["fact_id"]: r for r in rows}
        kids = collections.defaultdict(list)
        for r in rows:
            kids[r["parent"]].append(r)

        def chain(i):
            out = []
            while i in R_:
                out.append(R_[i]); i = R_[i]["parent"]
            return out

        def top(i):
            c = chain(i)                                                        # the unit, ..., the paper: the row under the paper, unless that is the unit
            return c[-2]["fact_id"] if len(c) >= 3 else self.key

        def vector(e):
            v = {}
            for a in chain(e):
                if a["type"] == "paper" or (a["type"] == "activity" and a["kind"] == "measurement"):
                    continue
                for f in kids[a["fact_id"]]:
                    if f["type"] == "setting" and f["quantity"] and f["quantity"] != "other" and "#" in f["fact_id"]:
                        v.setdefault((f["quantity"], f["qualifiers"]), canon(f) if f["value"] else f["value_text"].lower())
            return v

        def purpose(e):
            for a in [e] + [x["fact_id"] for x in kids[e] if x["type"] == "activity"]:
                for f in kids[a]:
                    if "#" in f["fact_id"] and f["type"] in ("observation", "model"):
                        return f["fact_id"]
            return next((f["fact_id"] for f in kids[e] if "#" in f["fact_id"] and f["type"] == "setting"), "")
        units = [r["fact_id"] for r in rows if r["type"] == "entity"]
        fam = collections.defaultdict(list)
        for u in units:
            fam[top(u)].append(u)
        out, seen = [], set()
        labels = [f for f in rows if f["type"] == "setting" and f["quantity"] == "other" and not (f["value"] or f["value_text"]) and ";" in f["mentions"]]
        name2node = {it.get("name_as_printed"): self.node[i][0] for i, it in self.p0.items() if i in self.node}

        def emit(kind, varied, members):
            key = (kind, tuple(sorted(members)))
            if key in seen or len(members) < 2:
                return
            seen.add(key)
            ev = sorted({e for m in members for e in R_[m]["evidence"].split(";") if e}, key=lambda e: self.order.get(e, 0))
            lab = ""
            for f in labels:
                named = {name2node.get(x) for x in f["mentions"].split(";")} - {None}
                if len(named) >= 2 and named <= set(members):
                    lab = f["label_as_printed"]; self.count("n", "comparison labelled from a series-name setting"); break
            pr = purpose(members[0])
            out.append({**{x: "" for x in F.FIELDS}, "fact_id": f"{self.key}:cmp:{len(out) + 1}", "type": "comparison", "kind": kind, "how": "inferred",
                        "quantity": ";".join(q for q, _ in varied), "qualifiers": "", "evidence": ";".join(ev), "parent": self.key, "author": self.pid,
                        "links": ";".join(([pr] if pr else []) + members), "label_as_printed": lab,
                        "statement": f"{kind} of {len(members)} units" + (f" varying {', '.join(q for q, _ in varied)}" if varied else " with equal conditions")})
            self.count("n", f"comparison {kind}")
        for t, us in fam.items():
            V_ = {u: vector(u) for u in us}
            groups = collections.defaultdict(list)
            for u in us:
                if V_[u]:
                    groups[tuple(sorted(V_[u].items(), key=str))].append(u)
            for g in groups.values():
                emit("replicate", [], sorted(g))
            keysets = collections.defaultdict(list)
            for u in us:
                if V_[u]:
                    keysets[tuple(sorted(V_[u], key=str))].append(u)
            for ks, members in keysets.items():
                for q in ks:
                    part = collections.defaultdict(list)
                    for u in members:
                        part[tuple((x, V_[u][x]) for x in ks if x != q)].append(u)
                    for g in part.values():
                        if len({str(V_[u][q]) for u in g}) >= 2:
                            emit("series", [q], sorted(g))
                for a in range(len(ks)):
                    for b in range(a + 1, len(ks)):
                        part = collections.defaultdict(list)
                        for u in members:
                            part[tuple((x, V_[u][x]) for x in ks if x not in (ks[a], ks[b]))].append(u)
                        for g in part.values():
                            if len(g) >= 3 and len({str(V_[u][ks[a]]) for u in g}) >= 2 and len({str(V_[u][ks[b]]) for u in g}) >= 2:
                                emit("grid", [ks[a], ks[b]], sorted(g))
        return out

    def place(self, r):
        """P148 (C1): the row's parent by the pilot rule (kb/pilot/facts.py retree()), from the record's type and method and the unit
        its about names. A claim, definition, caveat or cited record -> the paper row. about = "paper": a setting, observation, derived
        or model with a MEAS_METHODS method -> <paper>:method:<method>; the rest -> the recipe (never the paper row). about = a run or a
        specimen: a setting without a MEAS_METHODS method -> the run's deposition (the specimen itself when the record is about a
        specimen and several specimens share that deposition); a setting with one, an observation, a derived or a model ->
        <specimen>:meas:<method> ("measurement" when the method is not in MEAS_METHODS): a run's to run_entity() (P148 D: no
        measurement node under a run). about = a simulation or a
        model run: a setting -> the simulation (the model run itself when the record is about a model run and several model runs share
        that simulation); a model without a value -> the simulation; an observation, a derived or a model with a value -> the model run
        (the simulation when about = the simulation). about null or not a unit id -> the recipe, flagged. A comparison is never a
        parent. Returns (row id, the rule that placed it)."""
        rec, k = r["rec"], self.key
        t, recipe = rec["type"], f"{k}:recipe"
        mm = rec.get("method") if rec.get("method") in F.MEAS_METHODS else ""
        valued = any(rec.get(x) not in (None, "") for x in VALUE_KEYS)
        if t in ("claim", "definition", "caveat", "cited"):
            return k, f"{t} -> paper"
        a = rec.get("about")
        if a == "paper":
            if mm and t in ("setting", "observation", "derived", "model"):
                return self.method_activity(mm), "about paper, method -> paper method activity"
            return recipe, "about paper -> recipe"
        if a not in self.node:
            r["parent_filled"] = True
            return recipe, f"about {'null' if not a else 'unknown'} -> recipe (flagged)"
        rid, role = self.node[a]
        setting_here = t == "setting" and not mm
        if role in ("run", "specimen"):
            run = rid if role == "run" else (self.up[rid] if self.node_role(self.up[rid]) == "run" else "")
            if setting_here:
                if role == "specimen" and (len(self.under.get(run, [])) > 1 or not run):
                    return rid, "setting about a specimen sharing its deposition -> specimen"
                return run, f"setting about a {role} -> deposition"
            if role == "specimen":
                return self.measurement(rid, mm), "result about a specimen -> its measurement"
            ent, why = self.run_entity(rid)
            return self.measurement(ent, mm), f"result about a run -> {why} measurement"
        sim = rid if role == "simulation" else (self.up[rid] if self.node_role(self.up[rid]) == "simulation" else "")
        if role == "simulation":
            return rid, f"{t} about a simulation -> simulation"
        if t == "setting" or (t == "model" and not valued):
            if sim and not (t == "setting" and len(self.under.get(sim, [])) > 1):
                return sim, f"{t} about a model run -> simulation"
            return rid, f"{t} about a model run sharing its simulation -> model run"
        return rid, f"{t} about a model run -> model run"

    def node_role(self, row_id):
        return next((role for nid, role in self.node.values() if nid == row_id), "")

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
        f["_parent_filled"] = bool(r.get("parent_filled"))                     # P148: about null or unknown
        f["_links"] = [e for e in rec.get("links") or [] if e in self.order]    # P138: resolved to fact ids after ids()
        f["_quote"] = normalize(rec.get("quote", "")).lower()
        if any(f[x] for x in ("value", "value_min", "value_max")) and not f["data_kind"]:
            f["data_kind"] = "stated"                                           # P138: filled, flagged
            f["_kind_filled"] = True
        return f

    def merge_figure_settings(self, items, figs):
        """P149 F2: a setting from a caption or paragraph record and a setting from figures.json (1c) with the same quantity, the same
        value in canonical units (canon()) and the same unit (the record's about unit; the unit that owns the figures.json entry)
        are one row: the record's, its evidence joined with the figures.json row's, its parent the placement rule's (place()).
        Returns the figures.json rows left; each merge is logged (self.merges)."""
        self.merges, by = [], {}
        for f in items:
            if f["type"] == "setting" and f["value"] and f.get("_unit") and self.kind_of.get(f["evidence"].split(";")[0]) in ("caption", "paragraph"):
                by.setdefault((f["quantity"], canon(f), f["_unit"]), f)
        out = []
        for g in figs:
            f = by.get((g["quantity"], canon(g), g.get("_unit"))) if g["type"] == "setting" and g["value"] and g.get("_unit") else None
            if f is None:
                out.append(g); continue
            before = f["evidence"]
            f["evidence"] = ";".join(sorted(set(f["evidence"].split(";")) | set(g["evidence"].split(";")), key=lambda e: self.order.get(e, 10 ** 9)))
            self.merges.append(dict(paper=self.key, quantity=f["quantity"], value=f["value"], unit=f["unit"], unit_row=g["_unit"], record_evidence=before,
                                    figure_evidence=g["evidence"], figure_parent=g["parent"], kept_parent=f["parent"], evidence=f["evidence"]))
            self.count("i", "figures.json setting merged into a record (F2)")
            self.note(f"i: F2 merged figures.json setting {g['quantity']}={g['value']} {g['unit']} ({g['evidence']}, under {g['parent']}) into the record on {before} (under {f['parent']})")
        return out

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
            p, why = self.place(r)
            self.count("h", f"place: {why}")
            items.append(self.fact_row(r, p))
            items[-1]["_source"] = why                                          # P140 C3: the parent path, for the audit
            items[-1]["_unit"] = self.node.get(r["rec"].get("about"), ("",))[0]   # P149 F2: the row of the unit the record is about
        fig_tree, fig_facts = self.figures()
        self.specimens_for_runs(items + fig_facts)                              # P146
        self.rows_tree += fig_tree                                              # the series entities, before their measurement activities
        for f in fig_facts:
            if f["parent"].startswith("@meas:"):
                f["parent"] = self.measurement(f["parent"][6:], "")
        fig_facts = self.merge_figure_settings(items, fig_facts)               # P149 F2
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
        rows = tree + list(self.meas.values()) + items                         # tree holds the figure entities (rows_tree)
        rows = rows + self.comparisons(rows)                                    # P143b: from the condition vectors
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


def leaf(e):
    """P148 D: the validator that names a form.json error; inside an anyOf (a nullable field) the one of its non-null branch."""
    if e.validator == "anyOf":
        subs = [c for c in e.context if e.validator_value[c.relative_schema_path[0]] != {"type": "null"}]
        if subs:
            return leaf(subs[0])
    return e.validator


def in_order(tokens, text):
    """P140 C1: every token occurs in text, each after the previous one."""
    i = 0
    for t in tokens:
        j = text.find(t, i)
        if j < 0:
            return False
        i = j + len(t)
    return bool(tokens)


def text_key(f):
    """P138: the dedupe key of a claim, caveat or definition (with the quote; a definition also by its normalized term), else None."""
    if f["type"] == "definition":
        t = normalize(f["term"] or f["label_as_printed"] or f["mentions"].split(";")[0]).lower()
        return ("definition", f["parent"], t, f.get("_quote", "")) if t else None      # P140 C2: the parent too
    if f["type"] in ("claim", "caveat"):
        return (f["type"], f["parent"], f["cause"], f["relation"], f["effect"], f.get("_quote", ""))
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
