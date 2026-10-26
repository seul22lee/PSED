#!/usr/bin/env python3
"""The question-answering agent's tools: deterministic Python over the compiled knowledge base, no model call here.

Reads kb/compiled/<pid>.facts.csv and .binding.csv (the unit tree, values, claims, comparison sets, figure bindings),
kb/<pid>.figures.json (panels, curves, figure-derived values), kb/pilot/<pid>.elements.csv (crop paths), a run's recipe
fields (default kb/compiled/<pid>.recipe_fields.csv; RECIPE_SOURCE=records: kb/records/<pid>.jsonl pass '0rf' lines merged),
ontology/ontology.yaml and ontology/units.yaml. Crops are read from ingest/final of this checkout, else of the main checkout
(a linked worktree has none). Every tool returns a JSON-able dict: every value carries its fact_id, data_kind and unit,
every unit its paper and label as printed.

Rules the tools apply (general, keyed on no paper, element or value):
  - inheritance: a unit inherits its ancestors' conditions; per (quantity, qualifiers) the nearest level holding the key wins;
    a level holding several values of a key passes none down ('several values at <level>');
  - conflict: two conditions of one quantity at different levels whose qualifiers agree except a missing specifier
    (species, step, gas, element) and whose values differ: the nearer is preferred, both are reported;
  - a value whose unit's dimension differs from its quantity's dimension is rejected and listed;
  - a species of kind material on a value is no reactant: the value is excluded from a species query and listed;
  - an own value (measured, stated, read from a figure, computed by the authors or by the KB) without a species takes its
    run's reactant A from the recipe fill when a species is asked for, marked as filled; cited and model values are not filled;
  - a filter value against a recorded range is not a match ('recorded as a range').

    python3 -m psed_v2.agent.tools --check      # the three cases' expected tool paths and the five known KB issues
"""
import argparse, collections, csv, functools, inspect, json, math, os, re, subprocess, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
REPO = V2.parent
KBDIR = V2 / "kb"
COMPILED = KBDIR / "compiled"
ONTOLOGY = V2 / "ontology"


def main_checkout():
    """The repository's main checkout (the parent of git's common directory); differs from REPO in a linked worktree."""
    try:
        common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=HERE,
                                capture_output=True, text=True, check=True).stdout.strip()
        return Path(common).parent
    except (OSError, subprocess.CalledProcessError):
        return REPO


MAIN = main_checkout()
# the ingested papers (crops) are not in git: this checkout's psed_v2/ingest/final, else the main checkout's
FINAL = next((p for p in (V2 / "ingest/final", MAIN / "psed_v2/ingest/final") if p.is_dir()), V2 / "ingest/final")
CROP_ROOT = FINAL.parents[2]                                # crop paths are relative to this root ('psed_v2/ingest/final/...')

OWN = ("measured", "stated", "read_from_figure", "computed_by_authors", "computed_by_kb")
GROUPS = {"own": 0, "cited": 1, "model": 2}
RESULT_TYPES = ("observation", "derived", "model", "cited")
SPECIFIERS = {"species", "step", "gas", "element"}          # a qualifier naming what a value is about; absent = not stated
RECIPE_FIELDS = ("reactant_A", "reactant_B", "carrier_gas", "process_mode", "material")
KEY_CONDITIONS = ("deposition_temperature", "reactant_A", "reactant_B", "material", "process_mode", "structure", "feature_width")
LEVEL_NAMES = {"specimen": "this unit", "film": "this unit", "model_run": "this unit", "run": "run", "recipe": "recipe",
               "simulation": "simulation", "paper": "paper", "measurement": "measurement"}
STATEMENT_CHARS = 200                                       # statement length sent to the model (the log keeps the full text)
# where a run's reactants, carrier gas, process mode and material come from: 'compiled' (default, user: kb/compiled/<pid>.recipe_fields.csv,
# compile's importer with its quote check and the user's history.csv recipe decisions) or 'records' (every 0rf line merged in file order,
# the line compile.log names last); --check lists where the two differ
RECIPE_SOURCE = os.environ.get("PSED_AGENT_RECIPE_SOURCE", "compiled")


def group_of(data_kind):
    return "cited" if data_kind == "cited" else "model" if data_kind in ("model_input", "simulated") else "own"


def norm_term(s):
    """A term for lookup: lower case, '-', '_' and '/' as spaces, LaTeX braces and backslashes dropped, spaces collapsed."""
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", str(s))
    s = re.sub(r"[{}\\$]", "", s).replace("μ", "µ")
    return re.sub(r"\s+", " ", re.sub(r"[-_/]", " ", s.lower())).strip()


def num(s):
    try:
        return float(s) if s not in (None, "") else None
    except ValueError:
        return None


def sig(x, n=6):
    return None if x is None else float(f"{x:.{n}g}")


def parse_qual(s):
    return dict(p.split("=", 1) for p in (s or "").split(";") if "=" in p)


def qual_str(q):
    return ";".join(f"{k}={q[k]}" for k in sorted(q))


def cond_key(quantity, q):
    return f"{quantity}[{qual_str(q)}]" if q else quantity


# ------------------------------------------------------------------------------------------------------------ units
class Units:
    """ontology/units.yaml: printed unit -> dimension, SI factor and offset."""

    def __init__(self):
        d = yaml.safe_load((ONTOLOGY / "units.yaml").open(encoding="utf-8"))
        self.same = d.get("same_dimension", {})
        self.by = {}
        for u in d["units"]:
            u = dict(u, factor=float(u["factor"]), offset=float(u.get("offset", 0)))
            for v in [u["symbol"], *u["variants"]]:
                self.by.setdefault(self.norm(v), u)

    @staticmethod
    def norm(s):
        return re.sub(r"\s+", "", str(s or "").replace("μ", "µ").replace("⁻", "-").replace("−", "-"))

    def get(self, s):
        return self.by.get(self.norm(s))

    def dimension(self, s):
        u = self.get(s)
        return u and self.same.get(u["dimension"], u["dimension"])

    def convert(self, v, src, dst):
        if v is None:
            return None
        if self.norm(src) == self.norm(dst):
            return v
        a, b = self.get(src), self.get(dst)
        if not a or not b or self.dimension(src) != self.dimension(dst):
            return None
        return (v + a.get("offset", 0)) * a["factor"] / b["factor"] - b.get("offset", 0)

    def compatible(self, qdim, unit):
        """Is a printed unit of the quantity's dimension? Unknown units pass; dimensionless and count are one."""
        if qdim in (None, "categorical", "signal"):
            return True
        udim = self.dimension(unit)
        if udim is None:
            return True
        qdim = self.same.get(qdim, qdim)
        return udim == qdim or {udim, qdim} <= {"dimensionless", "count"}


# ------------------------------------------------------------------------------------------------------------ ontology
class Ontology:
    def __init__(self):
        d = yaml.safe_load((ONTOLOGY / "ontology.yaml").open(encoding="utf-8"))
        self.entries = {e["id"]: e for e in d["entries"]}
        self.classes = {c["id"]: c for c in d["structure_classes"]}
        self.children = collections.defaultdict(list)
        for c in d["structure_classes"]:
            if c["parent"]:
                self.children[c["parent"]].append(c["id"])
        self.qualifiers = d["qualifiers"]
        self.index = collections.defaultdict(set)            # normalized name -> {(id, how)}
        for e in d["entries"]:
            for how, names in (("id", [e["id"]]), ("name", [e.get("name")]), ("label", [e.get("label")]),
                               ("alias", e.get("aliases") or [])):
                for n in names:
                    if n:
                        self.index[norm_term(n)].add((e["id"], f"{how} '{n}'"))
        for c in d["structure_classes"]:
            self.index[norm_term(c["id"])].add((c["id"], f"structure class '{c['id']}'"))

    def kind(self, cid):
        if cid in self.classes:
            return "structure_class"
        e = self.entries.get(cid)
        return e["type"] if e else None

    def descendants(self, c):
        out, todo = [], [c]
        while todo:
            x = todo.pop(0)
            out.append(x)
            todo += self.children.get(x, [])
        return out

    def ancestors(self, c):
        out = []
        while c:
            out.append(c)
            c = self.classes.get(c, {}).get("parent")
        return out

    def structure_class(self, v):
        """A structure class id, or the class of a structure entry (pillarhall_3 -> lateral_channel)."""
        if v in self.classes:
            return v
        e = self.entries.get(v)
        return e.get("class") if e and e["type"] == "structure" else None

    def lookup(self, term):
        """Exact id / name / label / alias match of a term: [(id, how)]."""
        return sorted(self.index.get(norm_term(term), ()))

    def to_id(self, term, types=None):
        """One ontology id for a term (an id as is), else the term unchanged."""
        if term in self.entries or term in self.classes:
            return term
        hits = [i for i, _ in self.lookup(term) if types is None or self.kind(i) in types]
        return hits[0] if len(set(hits)) == 1 else term


# ------------------------------------------------------------------------------------------------------------ the KB
class KB:
    def __init__(self):
        self.onto, self.units = Ontology(), Units()
        man = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus/manifest.csv").open(encoding="utf-8"))}
        self.papers, self.facts, self.kids = {}, {}, collections.defaultdict(list)
        self.items = collections.defaultdict(list)            # key -> binding rows
        self.curves, self.panels, self.derived, self.fsets = {}, {}, collections.defaultdict(list), []
        self.crops, self.fill_records, self.fill_compiled = {}, {}, {}
        for path in sorted(COMPILED.glob("*.facts.csv")):
            pid = path.name[: -len(".facts.csv")]
            rows = list(csv.DictReader(path.open(encoding="utf-8")))
            key = next(r["fact_id"] for r in rows if r["type"] == "paper")
            m = man.get(pid, {})
            first = (m.get("authors") or "?").split(";")[0].split()
            lower = [i for i, w in enumerate(first[:-1]) if w[:1].islower()]       # a particle starts the surname (van der Zouw)
            surname = " ".join(first[lower[0]:] if lower else first[-1:])
            self.papers[key] = {"key": key, "pid": pid, "label": f"{surname} {m.get('year', '')}".strip(),
                                "surname": surname, "year": m.get("year", ""), "title": m.get("title", ""),
                                "doi": m.get("doi", "")}
            for i, r in enumerate(rows):
                r["_paper"], r["_order"] = key, i
                self.facts[r["fact_id"]] = r
                self.kids[r["parent"]].append(r)
            bpath = COMPILED / f"{pid}.binding.csv"
            seen = set()
            for b in csv.DictReader(bpath.open(encoding="utf-8")) if bpath.exists() else []:
                k = (b["item"], b["unit_fact_id"], b["reason"])
                if k not in seen:
                    seen.add(k)
                    self.items[key].append(b)
            fpath = KBDIR / f"{pid}.figures.json"
            if fpath.exists():
                fj = json.loads(fpath.read_text(encoding="utf-8"))
                for c in fj.get("curves", []):
                    self.curves[c["id"]] = dict(c, _paper=key)
                for p in fj.get("inventory", []):
                    self.panels[p["id"]] = dict(p, _paper=key)
                for d in fj.get("derived", []):
                    self.derived[d["source"]].append(dict(d, _paper=key))
                self.fsets += [dict(s, _paper=key) for s in fj.get("sets", [])]
            epath = KBDIR / "pilot" / f"{pid}.elements.csv"
            for e in csv.DictReader(epath.open(encoding="utf-8")) if epath.exists() else []:
                if e.get("crop"):
                    self.crops[(key, e["element_id"])] = e["crop"]
            self.fill_records.update(self._load_fill(pid, key))
            self.fill_compiled.update(self._load_compiled_fill(pid, key))
        self.fill = self.fill_compiled if RECIPE_SOURCE == "compiled" else self.fill_records
        self.role, self._conds = {}, {}
        for fid, r in self.facts.items():
            if r["type"] in ("paper", "activity", "entity"):
                self.role[fid] = self._role(r)
        self.name_to_unit = collections.defaultdict(list)    # (key, pass-0 name) -> unit ids, for ambiguous bindings
        for fid in self.role:
            r = self.facts[fid]
            for n in {fid.split(":")[-1].lower(), r["label_as_printed"].lower()}:
                self.name_to_unit[(r["_paper"], n)].append(fid)

    # -------------------------------------------------------------------------------------------------------- loading
    def _load_fill(self, pid, key):
        """Merge every '0rf' line in file order, the line compile.log names ('recipe fill = line N') last; a field takes the
        latest line that holds it (a null holds nothing)."""
        rec = KBDIR / "records" / f"{pid}.jsonl"
        log = COMPILED / f"{pid}.compile.log"
        m = re.search(r"recipe fill = line (\d+)", log.read_text(encoding="utf-8")) if log.exists() else None
        last = int(m.group(1)) if m else None
        lines = []
        for i, line in enumerate(rec.open(encoding="utf-8") if rec.exists() else [], 1):
            d = json.loads(line)
            if d.get("pass") == "0rf":
                lines.append((i, d))
        lines.sort(key=lambda x: x[0] == last)
        merged = {}
        for i, d in lines:
            try:
                recipes = json.loads(d["response"]).get("recipes") or []
            except (ValueError, AttributeError):
                continue
            for r in recipes:
                for f in RECIPE_FIELDS:
                    if r.get(f) not in (None, ""):
                        merged.setdefault(r.get("id"), {})[f] = {"value": r[f], "quote": r.get(f + "_quote"),
                                                                 "element": r.get(f + "_element"), "line": i}
        return {(key, rid): fields for rid, fields in merged.items()}

    def _load_compiled_fill(self, pid, key):
        path = COMPILED / f"{pid}.recipe_fields.csv"
        out = {}
        for r in csv.DictReader(path.open(encoding="utf-8")) if path.exists() else []:
            if r["field"] in RECIPE_FIELDS and r["value"]:
                out.setdefault((key, r["run"]), {})[r["field"]] = {"value": r["value"], "quote": r["quote"],
                                                                   "element": r["element"], "line": None}
        return out

    def _role(self, r):
        t, k = r["type"], r["kind"]
        if t == "paper":
            return "paper"
        if t == "activity":
            if k == "measurement":
                return "method" if r["parent"] == r["_paper"] else "measurement"
            return {"recipe": "recipe", "deposition": "run", "simulation": "simulation"}.get(k, k or "activity")
        p = self.facts.get(r["parent"])
        while p is not None:
            if p["type"] == "activity" and p["kind"] == "simulation":
                return "model_run"
            p = self.facts.get(p["parent"])
        return "film" if r["fact_id"].endswith(":film") else "specimen"

    def fill_of(self, uid):
        """The recipe fill of a run or simulation (its id, or the last part of its id, is the fill's id)."""
        r = self.facts[uid]
        for rid in (uid, uid.split(":")[-1]):
            if (r["_paper"], rid) in self.fill:
                return rid, self.fill[(r["_paper"], rid)]
        return None, {}

    # -------------------------------------------------------------------------------------------------------- units of the tree
    def chain(self, uid):
        """The unit and its ancestors up to the paper, nearest first (a measurement's chain starts at the measurement)."""
        out = []
        while uid in self.facts:
            out.append(uid)
            uid = self.facts[uid]["parent"]
        return out

    def run_of(self, uid):
        return next((u for u in self.chain(uid) if self.role.get(u) in ("run", "simulation")), None)

    def is_sample(self, uid, models=False):
        return self.role.get(uid) in (("specimen", "film", "model_run") if models else ("specimen", "film"))

    def sample_of(self, uid):
        return next((u for u in self.chain(uid) if self.is_sample(u, models=True)), None)

    def measurements(self, uid):
        return [r["fact_id"] for r in self.kids[uid] if self.role.get(r["fact_id"]) == "measurement"]

    def method_of(self, mid):
        r = self.facts[mid]
        return r["method"] or (mid.split(":meas:")[-1] if ":meas:" in mid else "")

    def unit_label(self, uid):
        r = self.facts[uid]
        role = self.role.get(uid)
        if role == "film":
            return f"film of run '{self.facts[r['parent']]['label_as_printed']}'"
        return r["label_as_printed"] or uid.split(":")[-1]

    def unit_ref(self, uid):
        r = self.facts[uid]
        out = {"id": uid, "paper": self.papers[r["_paper"]]["label"], "label": self.unit_label(uid),
               "kind": {"film": "run film", "model_run": "model run"}.get(self.role.get(uid), self.role.get(uid))}
        sc = parse_qual(r["qualifiers"]).get("structure_class")
        if sc:
            out["structure_class"] = sc
        return out

    def scope(self, uid):
        """The units whose records belong to a unit: itself, its measurements, and, for the only sample of a run, the run's
        bound items (an item bound to a run belongs to its film)."""
        units = [uid] + self.measurements(uid)
        if self.is_sample(uid, models=True):
            parent = self.facts[uid]["parent"]
            sibs = [r["fact_id"] for r in self.kids[parent] if self.is_sample(r["fact_id"], models=True)]
            if self.role.get(parent) == "run" and sibs == [uid]:
                units.append(parent)
        return units

    # -------------------------------------------------------------------------------------------------------- values
    def has_value(self, f):
        return any(f[c] not in ("", None) for c in ("value", "value_min", "value_max", "value_text"))

    def entry(self, f, idx=0, level=""):
        return {"key": cond_key(f["quantity"], parse_qual(f["qualifiers"])), "quantity": f["quantity"],
                "qual": parse_qual(f["qualifiers"]), "value": num(f["value"]), "min": num(f["value_min"]),
                "max": num(f["value_max"]), "censor": f["censor"], "unit": f["unit"], "text": f["value_text"],
                "fact_id": f["fact_id"], "data_kind": f["data_kind"], "level": level, "idx": idx, "source": "fact",
                "printed": f["label_as_printed"]}

    def canon(self, e):
        """A comparable form: numbers in the quantity's unit (6 significant digits), text in lower case."""
        if e["value"] is None and e["min"] is None and e["max"] is None:
            return ("t", str(e["text"]).strip().lower())
        qe = self.onto.entries.get(e["quantity"], {})
        cu = qe.get("unit")
        conv = (lambda v: self.units.convert(v, e["unit"], cu)) if cu and self.units.convert(1.0, e["unit"], cu) is not None \
            else (lambda v: v)
        return ("n", sig(conv(e["value"])), sig(conv(e["min"])), sig(conv(e["max"])), e["censor"] or "")

    @staticmethod
    def show(e):
        unit = f" {e['unit']}" if e.get("unit") and e["unit"] != "1" else ""
        if e.get("value") is not None:
            return f"{e['censor'] or ''}{e['value']:g}{unit}"
        if e.get("min") is not None or e.get("max") is not None:
            lo = "" if e["min"] is None else f"{e['min']:g}"
            hi = "" if e["max"] is None else f"{e['max']:g}"
            return f"{lo}–{hi}{unit}"
        return str(e.get("text") or "")

    def level_entries(self, uid, idx):
        """The conditions a unit holds itself: its settings (and model inputs), and a run's recipe fill."""
        level = LEVEL_NAMES.get(self.role.get(uid), self.role.get(uid))
        out = [self.entry(f, idx, level) for f in self.kids[uid]
               if (f["type"] == "setting" or (f["type"] == "model" and f["data_kind"] == "model_input")) and self.has_value(f)]
        rid, fields = self.fill_of(uid) if self.role.get(uid) in ("run", "simulation") else (None, {})
        key = self.facts[uid]["_paper"]
        for field, x in fields.items():
            out.append({"key": field, "quantity": field, "qual": {}, "value": None, "min": None, "max": None, "censor": "",
                        "unit": "", "text": x["value"], "fact_id": f"{key}:recipe_fill:{rid}:{field}", "data_kind": "stated",
                        "level": level, "idx": idx,
                        "source": f"recipe fill (records line {x['line']})" if x["line"] else "recipe fill (recipe_fields.csv)",
                        "quote": x["quote"], "printed": x["quote"]})
        return out

    def conditions(self, uid):
        """Effective conditions of a unit: {key: condition}; each condition has the chosen entry, its level, the status
        (own, inherited, several values), the shadowed entries of farther levels and the cross-key conflicts."""
        if uid not in self._conds:
            self._conds[uid] = self._conditions(uid)
        return self._conds[uid]

    def _conditions(self, uid):
        chain = [u for u in self.chain(uid) if self.role.get(u) != "measurement"]
        by_key = collections.defaultdict(list)
        for i, u in enumerate(chain):
            for e in self.level_entries(u, i):
                by_key[e["key"]].append(e)
        out = {}
        for k, es in by_key.items():
            near = min(e["idx"] for e in es)
            at = [e for e in es if e["idx"] == near]
            distinct = list({self.canon(e): e for e in at}.values())
            c = {"key": k, "quantity": es[0]["quantity"], "qual": es[0]["qual"], "entry": at[0], "level": at[0]["level"],
                 "inherited": near > 0, "status": "ok", "entries": at, "shadowed": [e for e in es if e["idx"] > near],
                 "conflicts": []}
            if len(distinct) > 1:
                c["status"] = "several values" if near == 0 else f"several values at {at[0]['level']} (not inherited)"
                c["values"] = distinct
            out[k] = c
        byq = collections.defaultdict(list)
        for c in out.values():
            if c["status"] == "ok":
                byq[c["quantity"]].append(c)
        for cs in byq.values():
            for a in cs:
                for b in cs:
                    if a is b or a["entry"]["idx"] >= b["entry"]["idx"] or not self.qual_compatible(a["qual"], b["qual"]):
                        continue
                    if self.canon(a["entry"]) != self.canon(b["entry"]):
                        a["conflicts"].append({"role": "preferred", "other": b})
                        b["conflicts"].append({"role": "overridden", "other": a})
        return out

    @staticmethod
    def qual_compatible(qa, qb):
        for k in set(qa) | set(qb):
            if qa.get(k) == qb.get(k) or (k in SPECIFIERS and (k not in qa or k not in qb)):
                continue
            return False
        return True

    def cond_out(self, c, brief=False):
        e = c["entry"]
        out = {"value": self.show(e), "fact_id": e["fact_id"], "level": e["level"],
               "by": "inheritance" if c["inherited"] else "this unit"}
        if not brief:
            out["data_kind"] = e["data_kind"]
            if e["source"] != "fact":
                out["source"] = e["source"]
        if c["status"] != "ok":
            out["status"] = c["status"]
            out["values"] = [{"value": self.show(v), "fact_id": v["fact_id"]} for v in c["values"]]
        if c["conflicts"]:
            out["conflict"] = [self.conflict_text(c, x) for x in c["conflicts"]]
        return out

    def cite(self, c):
        """A condition in one string: value [fact_id] (level), with its status and a conflict mark."""
        if c["status"] != "ok":
            return f"{c['status']}: " + ", ".join(f"{self.show(v)} [{v['fact_id']}]" for v in c["values"])
        e = c["entry"]
        mark = "; conflict" if c["conflicts"] else ""
        return f"{self.show(e)} [{e['fact_id']}] ({c['level']}{mark})"

    def conflict_text(self, c, x):
        o = x["other"]
        mine = f"{c['key']} = {self.show(c['entry'])} ({c['level']}, {c['entry']['fact_id']})"
        theirs = f"{o['key']} = {self.show(o['entry'])} ({o['level']}, {o['entry']['fact_id']})"
        return f"preferred: {mine} over {theirs}" if x["role"] == "preferred" else f"overridden: {mine} by the nearer {theirs}"

    def conflicts_of(self, conds):
        return sorted({self.conflict_text(c, x) for c in conds.values() for x in c["conflicts"] if x["role"] == "preferred"})

    # -------------------------------------------------------------------------------------------------------- value rows
    def value_out(self, f, extra=None):
        uid = f["parent"]
        out = {"fact_id": f["fact_id"], "paper": self.papers[f["_paper"]]["label"], "type": f["type"],
               "quantity": f["quantity"], "qualifiers": f["qualifiers"], "label_as_printed": f["label_as_printed"]}
        for c in ("value", "value_min", "value_max", "censor", "unit", "value_text", "method", "points_ref"):
            if f.get(c):
                out[c] = num(f[c]) if c in ("value", "value_min", "value_max") else f[c]
        out["data_kind"] = f["data_kind"] or ""
        out["group"] = group_of(f["data_kind"])
        out["statement"] = f["statement"]
        if uid in self.facts:
            out["unit_id"] = uid
            out["unit_label"] = self.unit_label(uid)
            s = self.sample_of(uid)
            if s and s != uid:
                out["sample_id"], out["sample_label"] = s, self.unit_label(s)
            if self.role.get(uid) != "paper":
                conds = self.conditions(s or next((u for u in self.chain(uid) if self.role.get(u) != "measurement"), uid))
                kc = {k: self.cite(conds[k]) for k in KEY_CONDITIONS if k in conds}
                if kc:
                    out["key_conditions"] = kc
        if extra:
            out.update(extra)
        return out

    def derived_out(self, d, uid):
        """A figure-derived value (figures.json derived: a plateau or a half-value crossing read from a curve by rule)."""
        out = {"fact_id": d["id"], "paper": self.papers[d["_paper"]]["label"], "type": "derived", "quantity": d["quantity"],
               "qualifiers": d.get("qualifiers", ""), "label_as_printed": "", "value": sig(d["value"]), "unit": d["unit"],
               "method": d["method"], "data_kind": "computed_by_kb", "group": "own",
               "statement": f"read by rule from curve {d['source']}: {d['rule']}", "source_curve": d["source"]}
        if uid:
            out["unit_id"], out["unit_label"] = uid, self.unit_label(uid)
            s = self.sample_of(uid)
            if s and s != uid:
                out["sample_id"], out["sample_label"] = s, self.unit_label(s)
        return out


@functools.lru_cache(maxsize=1)
def kb():
    return KB()


def _err(msg, **kw):
    return {"error": msg, **kw}


def _ids(x):
    if x is None:
        return []
    return [x] if isinstance(x, str) else list(x)


# ============================================================================================================ tool 1: resolve
def resolve(term, kind=None):
    """Ontology concepts matching a term: exact (id, name, label, alias), partial (whole words of one in the other),
    in a definition, or printed so in the KB (label as printed)."""
    K, O = kb(), kb().onto
    t = norm_term(term)
    if not t:
        return _err("empty term")
    want = {"structure": ("structure", "structure_class")}.get(kind, (kind,)) if kind else None
    hits = collections.defaultdict(lambda: {"match": None, "matched": []})
    rank = {"exact": 0, "partial": 1, "printed_in_kb": 2, "definition": 3}

    def add(cid, match, how):
        h = hits[cid]
        h["matched"].append(how)
        if h["match"] is None or rank[match] < rank[h["match"]]:
            h["match"] = match

    for cid, how in O.lookup(t) + (O.lookup(t[:-1]) if t.endswith("s") else []):
        add(cid, "exact", how)
    tw = f" {t} "
    for name, ids in O.index.items():
        if name == t or len(name) < 3:
            continue
        if f" {name} " in tw or (len(t) >= 3 and f" {t} " in f" {name} "):
            for cid, how in ids:
                add(cid, "partial", how)
    defs = [(cid, norm_term(c.get("definition", "")), "structure class definition") for cid, c in O.classes.items()]
    defs += [(cid, norm_term(e.get("definition", "")), "definition") for cid, e in O.entries.items()
             if e["type"] in ("structure", "method", "species")]
    words = t.split()
    phrases = [" ".join(words[i:i + n]) for n in range(len(words), 1, -1) for i in range(len(words) - n + 1)] or [t]
    for ph in phrases:                                      # the longest part of the term (2+ words) that a definition holds
        found = [(cid, how) for cid, d, how in defs if len(ph) >= 5 and f" {ph} " in f" {d} "]
        for cid, how in found:
            add(cid, "definition", how if ph == t else f"{how} holds '{ph}'")
        if found:
            break
    printed = collections.Counter()
    for f in K.facts.values():
        if f["quantity"] and f["label_as_printed"] and norm_term(f["label_as_printed"]) == t:
            printed[f["quantity"]] += 1
    for q, n in printed.items():
        add(q, "printed_in_kb", f"printed as '{term}' on {n} records")
    out = []
    for cid, h in hits.items():
        typ = O.kind(cid)
        if typ is None or (want and typ not in want):
            continue
        r = {"id": cid, "type": typ, "match": h["match"], "matched": sorted(set(h["matched"]))[:4]}
        e = O.entries.get(cid, {})
        if e.get("name"):
            r["name"] = e["name"]
        if typ == "method":
            r["class"] = e.get("class")
            r["same_class"] = sorted(i for i, x in O.entries.items() if x["type"] == "method" and x.get("class") == e.get("class") and i != cid)
        elif typ == "structure_class":
            desc = O.descendants(cid)
            r["subclasses"] = desc[1:]
            r["structures"] = sorted(i for i, x in O.entries.items() if x["type"] == "structure" and x.get("class") in desc)
            r["parents"] = O.ancestors(cid)[1:]
        elif typ == "structure":
            r["class"] = e.get("class")
            r["class_parents"] = O.ancestors(e.get("class"))[1:]
        elif typ == "species":
            r["species_kind"] = e.get("kind")
        elif typ in ("quantity", "categorical"):
            r["dimension"], r["unit"] = e.get("dimension"), e.get("unit")
            labs = collections.defaultdict(set)
            quals = collections.Counter()
            for f in K.facts.values():
                if f["quantity"] == cid and f["type"] not in ("definition",):
                    if f["label_as_printed"]:
                        labs[f["label_as_printed"]].add(K.papers[f["_paper"]]["label"])
                    for kv in (f["qualifiers"] or "").split(";"):
                        if kv:
                            quals[kv] += 1
            r["printed_as"] = [{"label": k, "papers": sorted(v)} for k, v in sorted(labs.items(), key=lambda x: (-len(x[1]), x[0]))[:15]]
            r["qualifiers_in_kb"] = dict(quals.most_common(12))
            same = [i for i, x in O.entries.items() if x["type"] == "quantity" and x.get("category") == e.get("category") and i != cid]
            if same and e.get("category"):
                r["same_category_other_concepts"] = same
            carried = [c for c, x in O.classes.items() if cid in (x.get("slots") or [])]
            if carried:
                r["slot_of_structure_classes"] = carried
        out.append(r)
    out.sort(key=lambda r: (rank[r["match"]], r["type"], r["id"]))
    return {"term": term, "kind": kind, "matches": out[:25], "n_matches": len(out)}


# ============================================================================================================ tool 2: find_samples
def _filter_spec(f):
    """A filter in one form: concept id, its kind (structure, method, categorical, quantity), wanted values or range."""
    O = kb().onto
    c = O.to_id(f.get("concept", ""))
    vals = f.get("value", f.get("values"))
    vals = _ids(vals) if isinstance(vals, (str, list, tuple)) else ([] if vals is None else [vals])
    kind = O.kind(c)
    if c == "structure" or kind in ("structure", "structure_class"):
        if c != "structure":
            vals = [c] + vals
        return {"concept": "structure", "kind": "structure", "values": [O.to_id(v, ("structure", "structure_class")) for v in vals]}
    if c == "method" or kind == "method":
        if c != "method":
            vals = [c] + vals
        return {"concept": "method", "kind": "method", "values": [O.to_id(v, ("method",)) for v in vals]}
    if c in RECIPE_FIELDS or kind in ("categorical", "species"):
        return {"concept": c, "kind": "categorical", "values": [O.to_id(v) if isinstance(v, str) else v for v in vals],
                "qualifiers": f.get("qualifiers") or {}}
    if kind != "quantity":
        raise ValueError(f"unknown concept '{f.get('concept')}' (resolve it first)")
    return {"concept": c, "kind": "quantity", "values": [num(v) if isinstance(v, str) else v for v in vals],
            "min": f.get("min"), "max": f.get("max"), "unit": f.get("unit") or O.entries[c].get("unit") or "",
            "qualifiers": f.get("qualifiers") or {}}


def _label(spec):
    if spec["kind"] in ("structure", "method", "categorical"):
        return f"{spec['concept']} in {spec['values']}"
    q = f"[{qual_str(spec['qualifiers'])}]" if spec["qualifiers"] else ""
    if spec["values"]:
        return f"{spec['concept']}{q} = {', '.join(f'{v:g}' for v in spec['values'])} {spec['unit']}".strip()
    return f"{spec['concept']}{q} in [{spec.get('min')}, {spec.get('max')}] {spec['unit']}".strip()


def _ev(ev):
    """Filter evidence in one string (value [fact_id] (level)), or a list of them."""
    if ev is None:
        return None
    if "values" in ev and "value" not in ev:
        return [_ev(v) for v in ev["values"]] if isinstance(ev["values"][0], dict) else ev
    s = f"{ev.get('value', '')} [{ev.get('fact_id', '')}] ({ev.get('level', '')}"
    s += f"; {ev['source']}" if ev.get("source") else ""
    s += f"; qualifiers {ev['qualifiers']}" if ev.get("qualifiers") else ""
    s += f"; {ev['status']}" if ev.get("status") else ""
    s += "; conflict" if ev.get("conflict") else ""
    return s + ")" + (f" {ev['note']}" if ev.get("note") else "")


def _match(uid, conds, spec):
    """(status, evidence) of one filter on one sample. status: match, mismatch, not recorded, recorded as a range, several values."""
    K, O = kb(), kb().onto
    if spec["kind"] == "structure":
        accepted = set()
        for v in spec["values"]:
            accepted |= set(O.descendants(v)) if v in O.classes else {v}
        for u in K.chain(uid):
            sc = parse_qual(K.facts[u]["qualifiers"]).get("structure_class")
            if sc:
                ok = sc in accepted
                return ("match" if ok else "mismatch"), {"value": sc, "fact_id": u, "level": LEVEL_NAMES.get(K.role[u], K.role[u]),
                                                         "by": "this unit" if u == uid else "inheritance", "source": "structure_class of the unit"}
        c = conds.get("structure")
        if c:
            v = c["entry"]["text"]
            ok = v in accepted or O.structure_class(v) in accepted
            return ("match" if ok else "mismatch"), dict(K.cond_out(c, brief=True), structure_class=O.structure_class(v))
        return "not recorded", None
    if spec["kind"] == "method":
        hits = []
        for m in K.measurements(uid) + [x for x in K.scope(uid) if K.role.get(x) == "measurement"]:
            meth = K.method_of(m)
            if meth in spec["values"] and m not in [h["fact_id"] for h in hits]:
                hits.append({"value": meth, "fact_id": m, "level": "measurement", "by": "this unit"})
        if hits:
            return "match", hits[0] if len(hits) == 1 else {"values": hits}
        return ("not recorded" if not K.measurements(uid) else "mismatch"), \
            {"methods": sorted({K.method_of(m) for m in K.measurements(uid)})} if K.measurements(uid) else None
    cands = [c for c in conds.values() if c["quantity"] == spec["concept"] and all(c["qual"].get(k) == v for k, v in spec["qualifiers"].items())]
    if not cands:
        return "not recorded", None
    exact = [c for c in cands if c["qual"] == spec["qualifiers"]]
    pool = [c for c in (exact or cands) if not any(x["role"] == "overridden" for x in c["conflicts"])] or (exact or cands)
    results = []
    for c in pool:
        ev = K.cond_out(c, brief=True)
        if not exact:
            ev["qualifiers"] = qual_str(c["qual"])
        if c["status"] != "ok":
            results.append(("several values", ev))
            continue
        e = c["entry"]
        if spec["kind"] == "categorical":
            results.append((("match" if str(e["text"]).lower() in [str(v).lower() for v in spec["values"]] else "mismatch"), ev))
            continue
        conv = lambda v: K.units.convert(v, e["unit"] or spec["unit"], spec["unit"])
        v, lo, hi = conv(e["value"]), conv(e["min"]), conv(e["max"])
        if e["value"] is not None and v is None:
            results.append(("mismatch", dict(ev, note=f"unit '{e['unit']}' does not convert to '{spec['unit']}'")))
            continue
        close = lambda a, b: a is not None and b is not None and math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-12)
        if spec["values"]:
            if v is not None:
                results.append(("match" if any(close(v, w) for w in spec["values"]) else "mismatch", ev))
            elif lo is not None or hi is not None:
                inside = any((lo is None or w >= lo - 1e-12) and (hi is None or w <= hi + 1e-12) for w in spec["values"])
                results.append(("recorded as a range" if inside else "mismatch", ev))
            else:
                results.append(("not recorded", ev))
        else:
            fmin, fmax = num(spec.get("min")), num(spec.get("max"))
            inside = lambda a: a is not None and (fmin is None or a >= fmin) and (fmax is None or a <= fmax)
            if v is not None:
                results.append(("match" if inside(v) else "mismatch", ev))
            elif inside(lo) and inside(hi):
                results.append(("match", ev))
            elif (lo is None or fmax is None or lo <= fmax) and (hi is None or fmin is None or hi >= fmin):
                results.append(("recorded as a range", ev))
            else:
                results.append(("mismatch", ev))
    order = ["match", "recorded as a range", "several values", "not recorded", "mismatch"]
    best = min(results, key=lambda r: order.index(r[0]))
    if len(results) > 1:
        return best[0], {"values": [r[1] for r in results]} if best[0] != "match" else best[1]
    return best


def find_samples(filters, vary=None, include_models=False, papers=None):
    """Coated samples (specimens and run films; model runs when include_models) whose conditions match every filter."""
    K = kb()
    try:
        specs = [_filter_spec(f) for f in (filters or [])]
    except ValueError as e:
        return _err(str(e))
    vary = [kb().onto.to_id(v) for v in _ids(vary)]
    keys = [kb().onto.to_id(p) if p in K.papers else p for p in _ids(papers)]
    keys = [k for k in K.papers if not keys or k in keys or K.papers[k]["label"] in keys]
    matched, undecided = [], []
    per_paper = {K.papers[k]["label"]: {"scanned": 0, "matched": 0} for k in keys}
    failed = collections.defaultdict(collections.Counter)
    scanned = 0
    for uid, role in K.role.items():
        if K.facts[uid]["_paper"] not in keys or not K.is_sample(uid, models=include_models):
            continue
        scanned += 1
        pl = K.papers[K.facts[uid]["_paper"]]["label"]
        per_paper[pl]["scanned"] += 1
        conds = K.conditions(uid)
        res = [(s, *_match(uid, conds, s)) for s in specs]
        for s, st, _ in res:
            if st != "match":
                failed[_label(s)][st] += 1
        if all(st == "match" for _, st, _ in res):
            per_paper[pl]["matched"] += 1
            out = dict(K.unit_ref(uid), matched={_label(s): _ev(ev) for s, st, ev in res})
            if vary:
                out["vary"] = {}
                for q in vary:
                    cs = {k: K.cite(c) for k, c in conds.items() if c["quantity"] == q}
                    out["vary"][q] = (cs.get(q) if list(cs) == [q] else cs) or "not recorded"
            fl = K.conflicts_of(conds)
            if fl:
                out["conflicts"] = fl
            matched.append(out)
        elif not any(st == "mismatch" for _, st, _ in res):
            undecided.append(dict(K.unit_ref(uid), open={_label(s): f"{st}" + (f": {_ev(ev)}" if ev else "")
                                                          for s, st, ev in res if st != "match"}))
    return {"filters": [_label(s) for s in specs], "vary": vary, "include_models": include_models,
            "counts": {"scanned": scanned, "matched": len(matched), "undecided": len(undecided),
                       "papers_matched": sum(1 for v in per_paper.values() if v["matched"]),
                       "per_paper": {k: v for k, v in per_paper.items() if v["scanned"]}},
            "not_matched_by_filter": {k: dict(v) for k, v in failed.items()},
            "samples": matched,
            "undecided": sorted(undecided, key=lambda u: len(u["open"]))[:15],
            "note_undecided": "samples with no recorded mismatch whose match the KB does not settle (a value not recorded, "
                              "recorded only as a range, or several values at a level); not matched"}


# ============================================================================================================ tool 3: get_records
def _images(K, uids, methods=None):
    """Image items bound to the units, and ambiguous image items naming one of them (methods: keep images of these methods)."""
    want = set(uids)
    out, seen = [], set()
    for key in {K.facts[u]["_paper"] for u in uids}:
        for b in K.items[key]:
            if b["kind"] != "image":
                continue
            cands = []
            if b["unit_fact_id"]:
                hit = b["unit_fact_id"] in want
            elif b["reason"].startswith("ambiguous:"):
                names = [n.strip().lower() for n in b["reason"].split(":", 1)[1].split(",")]
                cands = sorted({u for n in names for u in K.name_to_unit.get((key, n), [])})
                hit = any(c in want or K.sample_of(c) in want for c in cands)
            else:
                hit = False
            if not hit or b["item"] in seen:
                continue
            seen.add(b["item"])
            panel = K.panels.get(f"{key}:{b['panel']}", {})
            fids = [x for x in b["facts"].split(";") if x in K.facts]
            meth = sorted({K.facts[x]["method"] or K.method_of(K.facts[x]["parent"]) for x in fids
                           if K.facts[x]["method"] or K.role.get(K.facts[x]["parent"]) == "measurement"}
                          | ({K.method_of(b["unit_fact_id"])} if K.role.get(b["unit_fact_id"]) == "measurement" else set())
                          | {K.method_of(c) for c in cands if K.role.get(c) == "measurement"})
            crop = K.crops.get((key, b["panel"])) or K.crops.get((key, f"fig{panel.get('figure', '')}.cap"))
            path = f"psed_v2/ingest/final/{K.papers[key]['pid']}/{crop}" if crop else None
            img = {"image_id": b["item"], "paper": K.papers[key]["label"], "panel": f"{key}:{b['panel']}",
                   "figure": panel.get("figure", ""), "panel_letter": panel.get("panel", ""),
                   "panel_type": panel.get("panel_type", ""), "description": panel.get("content", ""),
                   "method": [m for m in meth if m], "crop_path": path,
                   "crop_present": bool(path and (CROP_ROOT / path).exists()),
                   "binding": "bound" if b["unit_fact_id"] else "ambiguous", "fact_ids": fids,
                   "statements": [K.facts[x]["statement"] for x in fids]}
            if b["unit_fact_id"]:
                img["unit_id"], img["unit_label"] = b["unit_fact_id"], K.unit_label(b["unit_fact_id"])
                s = K.sample_of(b["unit_fact_id"]) or (b["unit_fact_id"] if K.role.get(b["unit_fact_id"]) == "run" else None)
                if s:
                    img["sample_id"] = s
            else:
                img["candidates"] = [{"unit_id": c, "sample_id": K.sample_of(c), "label": K.unit_label(c)} for c in cands]
                img["note"] = f"binding {b['reason']}: the image shows one of these units, the KB does not say which"
                if not img["method"]:
                    img["candidate_methods"] = sorted({K.method_of(m) for c in cands for m in K.measurements(c)})
            if methods and not set(img["method"]) & set(methods):
                continue
            out.append(img)
    return out


def _curves(K, uids, quantity):
    out = []
    want = set(uids)
    for key in {K.facts[u]["_paper"] for u in uids}:
        for b in K.items[key]:
            if b["kind"] != "curve" or b["unit_fact_id"] not in want or b["item"] not in K.curves:
                continue
            c = K.curves[b["item"]]
            der = K.derived.get(c["id"], [])
            if quantity and quantity not in (c["x"]["quantity"], c["y"]["quantity"]) and quantity not in [d["quantity"] for d in der]:
                continue
            uid = b["unit_fact_id"]
            out.append({"curve_id": c["id"], "paper": K.papers[key]["label"], "unit_id": uid, "unit_label": K.unit_label(uid),
                        "sample_id": K.sample_of(uid) or uid, "figure": c["figure"], "panel": c["panel"],
                        "series": c["series"].get("label_raw", ""), "data_kind": c.get("kind", ""),
                        "x": {k: c["x"].get(k) for k in ("quantity", "unit", "label_raw")},
                        "y": {k: c["y"].get(k) for k in ("quantity", "unit", "label_raw")},
                        "conditions": c.get("conditions_raw", {}), "flags": sorted(set(c.get("flags", []))),
                        "points": [[sig(x, 5), sig(y, 5)] for x, y in c["points"]],
                        "derived": [{"fact_id": d["id"], "quantity": d["quantity"], "qualifiers": d.get("qualifiers", ""),
                                     "value": sig(d["value"]), "unit": d["unit"], "method": d["method"]} for d in der]})
    return out


def _normalize(K, curve, how):
    """Apply ontology transforms to a curve's points: normalize_thickness (y over the curve's plateau, else the sample's
    recorded plateau thickness) and x_over_width (x over the sample's feature width). Says which reference it used."""
    pts, refs = [list(p) for p in curve["points"]], []
    if "normalize_thickness" in how:
        if curve["y"]["quantity"] == "film_thickness":
            ref = next((d for d in curve["derived"] if d["quantity"] == "film_thickness" and "position=plateau" in d["qualifiers"]), None)
            if ref:
                r = {"transform": "normalize_thickness", "reference": "plateau of this curve", "fact_id": ref["fact_id"],
                     "value": ref["value"], "unit": ref["unit"]}
            else:
                f = next((f for u in K.scope(curve["sample_id"]) for f in K.kids[u] if f["quantity"] == "film_thickness"
                          and parse_qual(f["qualifiers"]).get("position") == "plateau" and num(f["value"])), None)
                r = {"transform": "normalize_thickness", "reference": "the sample's plateau thickness", "fact_id": f["fact_id"],
                     "value": num(f["value"]), "unit": f["unit"]} if f else None
            if r:
                k = K.units.convert(1.0, r["unit"], curve["y"]["unit"]) or 1.0
                pts = [[x, sig(y / (r["value"] * k), 5)] for x, y in pts]
                refs.append(r)
            else:
                refs.append({"transform": "normalize_thickness", "reference": None, "note": "no plateau recorded; not normalized"})
        else:
            refs.append({"transform": "normalize_thickness", "note": f"y is {curve['y']['quantity']}, not film_thickness; not applied"})
    if "x_over_width" in how:
        if curve["x"]["quantity"] == "distance":
            conds = K.conditions(curve["sample_id"])
            c = conds.get("feature_width")
            if c and c["status"] == "ok" and c["entry"]["value"] is not None:
                w = K.units.convert(c["entry"]["value"], c["entry"]["unit"], curve["x"]["unit"])
                pts = [[sig(x / w, 5), y] for x, y in pts]
                refs.append({"transform": "x_over_width", "reference": "the sample's feature width", "fact_id": c["entry"]["fact_id"],
                             "value": c["entry"]["value"], "unit": c["entry"]["unit"], "level": c["level"]})
            else:
                refs.append({"transform": "x_over_width", "reference": None,
                             "note": "feature width not recorded as one value; not applied"})
        else:
            refs.append({"transform": "x_over_width", "note": f"x is {curve['x']['quantity']}, not distance; not applied"})
    return pts, refs


def get_records(sample_ids=None, quantity=None, qualifiers=None, include=("values", "curves", "images"), normalize=None,
                papers=None, methods=None):
    """Values, curves and images of samples (or any units; with no ids, every unit of the KB, quantity required)."""
    K, O = kb(), kb().onto
    ids = _ids(sample_ids)
    unknown = [i for i in ids if i not in K.role]
    if unknown:
        return _err(f"unknown unit ids: {unknown}")
    quantity = O.to_id(quantity) if quantity else None
    if quantity and O.kind(quantity) not in ("quantity", "categorical"):
        return _err(f"'{quantity}' is not a quantity (resolve it first)")
    if not ids and not quantity:
        return _err("give sample_ids, or a quantity to search the whole KB")
    include = set(_ids(include)) or {"values", "curves", "images"}
    quals = qualifiers if isinstance(qualifiers, dict) else parse_qual(qualifiers or "")
    keys = [p for p in _ids(papers)]
    if ids:
        scope = {u: s for s in ids for u in K.scope(s)}
    else:
        scope = {u: u for u in K.role if not keys or K.facts[u]["_paper"] in keys or K.papers[K.facts[u]["_paper"]]["label"] in keys}
    qdim = O.entries.get(quantity, {}).get("dimension") if quantity else None
    values, excluded, rejected = [], [], []
    if "values" in include:
        rows = [f for u in scope for f in K.kids[u]
                if (f["type"] in RESULT_TYPES or (quantity and f["type"] == "setting")) and K.has_value(f)
                and (not quantity or f["quantity"] == quantity)]
        for u in scope:
            for b in K.items[K.facts[u]["_paper"]]:
                if b["kind"] == "curve" and b["unit_fact_id"] == u:
                    for d in K.derived.get(b["item"], []):
                        if not quantity or d["quantity"] == quantity:
                            rows.append(("derived", d, u))
        for f in rows:
            if isinstance(f, tuple):
                row = K.derived_out(f[1], f[2])
                fq, fdk, funit, fdim = parse_qual(row["qualifiers"]), row["data_kind"], row["unit"], ""
            else:
                row = K.value_out(f)
                fq, fdk, funit, fdim = parse_qual(f["qualifiers"]), f["data_kind"], f["unit"], f["dimension_mismatch"]
            brief = {k: row[k] for k in ("fact_id", "paper", "value", "value_min", "value_max", "unit", "qualifiers", "data_kind") if k in row}
            if quantity and (fdim or (row.get("value") is not None or row.get("value_min") is not None) and not K.units.compatible(qdim, funit)):
                rejected.append(dict(brief, reason=f"unit '{funit}' ({K.units.dimension(funit) or 'unknown'}) does not match "
                                                    f"{quantity} ({qdim})" + (f"; compile: {fdim}" if fdim else "")))
                continue
            sp = fq.get("species")
            if sp and O.entries.get(sp, {}).get("kind") == "material" and (quantity or "species" in quals):
                excluded.append(dict(brief, reason=f"species {sp} is a material, not a molecule (no reactant)"))
                continue
            reason = None
            for k, v in quals.items():
                if fq.get(k) == v:
                    continue
                if k in fq:
                    reason = f"{k}={fq[k]}"
                    break
                if k == "species" and fdk in OWN and not isinstance(f, tuple):
                    run = K.run_of(f["parent"])
                    c = K.conditions(run).get("reactant_A") if run else None
                    if c and c["status"] == "ok" and str(c["entry"]["text"]).lower() == str(v).lower():
                        row["species_filled"] = f"{v}: the run's reactant A ({c['entry']['fact_id']}, {K.unit_label(run)})"
                        continue
                    reason = ("species not stated; the run's reactant A is " + str(c["entry"]["text"])) if c and c["status"] == "ok" \
                        else "species not stated and no single reactant A on its run"
                    break
                reason = f"{k} not stated" + (" (cited and model values are not filled)" if k == "species" else "")
                break
            if reason:
                excluded.append(dict(brief, reason=reason))
                continue
            values.append(row)
        values.sort(key=lambda r: (GROUPS[r["group"]], r["paper"], r["fact_id"]))
    out = {"quantity": quantity, "qualifiers": qual_str(quals), "units": [K.unit_ref(i) for i in ids] if ids else "every unit",
           "values": values, "counts": {"values": len(values), "by_data_kind": dict(collections.Counter(v["data_kind"] for v in values)),
                                        "papers": sorted({v["paper"] for v in values}), "excluded": len(excluded), "rejected": len(rejected)}}
    if excluded:
        out["excluded"] = excluded
    if rejected:
        out["rejected"] = rejected
    if "curves" in include and ids:
        curves = _curves(K, list(scope), quantity)
        how = set(_ids(normalize))
        for c in curves:
            if how:
                c["normalized_points"], c["normalized_by"] = _normalize(K, c, how)
        out["curves"] = curves
        out["counts"]["curves"] = len(curves)
    if "images" in include and ids:
        imgs = _images(K, list(scope), [kb().onto.to_id(m, ("method",)) for m in _ids(methods)])
        out["images"] = imgs
        out["counts"]["images"] = len(imgs)
    return out


# ============================================================================================================ tool 4: compare
def compare(sample_ids):
    """Every recorded condition of the samples: same, different (with values), or not recorded per sample; the conflicts;
    the KB comparison sets (type comparison facts; figure sets) that contain these samples."""
    K = kb()
    ids = _ids(sample_ids)
    unknown = [i for i in ids if i not in K.role]
    if unknown or not ids:
        return _err(f"unknown unit ids: {unknown}" if unknown else "no sample ids")
    conds = {s: K.conditions(s) for s in ids}
    keys = sorted({k for c in conds.values() for k in c})
    same, different, partly = [], [], []
    for k in keys:
        rec = {s: conds[s][k] for s in ids if k in conds[s]}
        vals = {s: K.cite(c) for s, c in rec.items()}
        canon = {K.canon(c["entry"]) if c["status"] == "ok" else ("several",) + tuple(sorted(map(K.canon, c["values"]), key=repr))
                 for c in rec.values()}
        if len(rec) < len(ids):
            missing = [s for s in ids if s not in rec]
            partly.append({"condition": k, "recorded": vals,
                           "not_recorded": missing if len(missing) <= len(rec) else f"the other {len(missing)} samples"})
        elif len(canon) == 1:
            any_c = next(iter(rec.values()))
            same.append({"condition": k, "value": K.show(any_c["entry"]),
                         "fact_ids": sorted({c["entry"]["fact_id"] for c in rec.values()}),
                         "levels": sorted({c["level"] for c in rec.values()})})
        else:
            different.append({"condition": k, "values": vals})
    sets = []
    for f in K.facts.values():
        if f["type"] == "comparison":
            members = [x for x in f["links"].split(";") if K.role.get(x) in ("specimen", "film", "model_run", "run")]
            hit = [s for s in ids if s in members]
            if hit:
                sets.append({"fact_id": f["fact_id"], "source": "kb comparison", "kind": f["kind"], "varied": f["quantity"],
                             "statement": f["statement"], "members": members, "contains": hit,
                             "members_not_in_query": {m: K.unit_label(m) for m in members if m not in ids}})
    for s in K.fsets:
        units = {}
        for m in s["members"]:
            b = next((b for b in K.items[s["_paper"]] if b["item"] == m and b["unit_fact_id"]), None)
            if b:
                units[m] = K.sample_of(b["unit_fact_id"]) or b["unit_fact_id"]
        hit = sorted({u for u in units.values() if u in ids})
        if hit:
            sets.append({"fact_id": s["id"], "source": "figure set", "kind": s["kind"], "varied": s.get("varied") or s.get("varied_raw"),
                         "statement": s.get("label", ""), "members": {m: units.get(m) for m in s["members"]},
                         "contains": hit})
    return {"samples": [K.unit_ref(s) for s in ids], "same": same, "different": different, "partly_recorded": partly,
            "conflicts": {s: K.conflicts_of(conds[s]) for s in ids if K.conflicts_of(conds[s])},
            "comparison_sets": sets,
            "counts": {"samples": len(ids), "papers": len({K.facts[s]["_paper"] for s in ids}), "same": len(same),
                       "different": len(different), "partly_recorded": len(partly), "comparison_sets": len(sets)}}


# ============================================================================================================ tool 5: claims
def claims(cause=None, effect=None, papers=None, relation=None):
    """Claim facts (cause, relation, effect, stance) and the records they link to, resolved to units and their conditions."""
    K, O = kb(), kb().onto
    cs = [O.to_id(c) for c in _ids(cause)]
    es = [O.to_id(e) for e in _ids(effect)]
    rels = _ids(relation)
    keys = [k for k in K.papers if not _ids(papers) or k in _ids(papers) or K.papers[k]["label"] in _ids(papers)]
    out = []
    for f in K.facts.values():
        if f["type"] != "claim" or f["_paper"] not in keys:
            continue
        fc, fe = f["cause"].split(";") if f["cause"] else [], f["effect"].split(";") if f["effect"] else []
        if (cs and not set(cs) & set(fc)) or (es and not set(es) & set(fe)) or (rels and f["relation"] not in rels):
            continue
        links, units = [], {}
        for lid in [x for x in f["links"].split(";") if x]:
            lf = K.facts.get(lid)
            if not lf:
                links.append({"fact_id": lid, "note": "not in the KB"})
                continue
            uid = lid if lid in K.role else lf["parent"]
            sample = K.sample_of(uid) if uid in K.facts else None
            row = {"fact_id": lid, "type": lf["type"], "quantity": lf["quantity"]}
            for c in ("value", "value_min", "value_max", "unit", "points_ref", "data_kind"):
                if lf.get(c):
                    row[c] = num(lf[c]) if c.startswith("value") else lf[c]
            if sample:
                row["sample_id"] = sample
                units.setdefault(sample, None)
            links.append(row)
        resolved = {}
        if units:
            conds = {u: K.conditions(u) for u in units}
            allk = sorted({k for c in conds.values() for k in c})
            for u in units:
                differ = {}
                for k in allk:
                    vals = {K.canon(conds[x][k]["entry"]) if k in conds[x] else None for x in units}
                    if len(vals) > 1 and k in conds[u]:
                        differ[k] = K.cond_out(conds[u][k], brief=True)["value"]
                resolved[u] = dict(K.unit_ref(u), differing_conditions=differ)
        out.append({"fact_id": f["fact_id"], "paper": K.papers[f["_paper"]]["label"], "cause": f["cause"], "relation": f["relation"],
                    "effect": f["effect"], "stance": f["stance"], "statement": f["statement"], "links": links,
                    "linked_samples": resolved})
    return {"cause": cs, "effect": es, "relation": rels, "claims": out[:40], "n_claims": len(out),
            "papers": sorted({c["paper"] for c in out})}


# ============================================================================================================ tool 6: trace_citation
def trace_citation(fact_id):
    """For a cited value: the cited paper when it is one of the KB's papers (first author's surname, and the year when the
    text gives one), its own values of the quantity, and value and condition agreement."""
    K = kb()
    f = K.facts.get(fact_id)
    if not f:
        return _err(f"unknown fact_id '{fact_id}'")
    if f["data_kind"] != "cited":
        return _err(f"{fact_id} is not a cited value (data_kind {f['data_kind'] or 'empty'})")
    text = " ".join([f["statement"], f["label_as_printed"], f["definition_note"]])
    years = set(re.findall(r"\b(19\d\d|20\d\d)\b", text))
    found = []
    for k, p in K.papers.items():
        if k == f["_paper"] or not re.search(rf"\b{re.escape(p['surname'])}\b", text, re.I):
            continue
        if years and p["year"] not in years:
            continue
        found.append(k)
    cited = K.value_out(f)
    out = {"cited": cited, "searched_text": text.strip(), "cited_paper": None, "own_values": []}
    if not found:
        out["outcome"] = "not found: the text names no first author (with year) of the KB's papers"
        return out
    cq = parse_qual(f["qualifiers"])
    out["cited_paper"] = [{"key": k, "paper": K.papers[k]["label"], "title": K.papers[k]["title"]} for k in found]
    for k in found:
        res = get_records(None, f["quantity"], {"species": cq["species"]} if cq.get("species") else None, papers=[k])
        for v in res.get("values", []):
            if v["group"] != "own":
                continue
            cv, ov = num(f["value"]), v.get("value")
            if cv is not None and ov is not None:
                vm = "match" if math.isclose(cv, ov, rel_tol=5e-3) else f"mismatch (own {ov:g} vs cited {cv:g})"
            elif f["value_min"] or f["value_max"]:
                lo, hi = num(f["value_min"]), num(f["value_max"])
                vm = "own value inside the cited range" if ov is not None and (lo is None or ov >= lo) and (hi is None or ov <= hi) \
                    else "own value outside the cited range"
            else:
                vm = "not comparable"
            uid = v.get("unit_id")
            conds = K.conditions(K.sample_of(uid) or uid) if uid else {}
            cmp_ = []
            for qk, qv in cq.items():
                own = parse_qual(v["qualifiers"]).get(qk) or (v.get("species_filled", "").split(":")[0] if qk == "species" else None)
                cmp_.append({"condition": qk, "cited": qv, "own": own or "not recorded",
                             "status": "match" if own == qv else "mismatch" if own else "not recorded on the own value"})
            for ck in ("deposition_temperature", "reactant_A", "reactant_B", "material", "structure", "feature_width"):
                if ck in conds:
                    cmp_.append({"condition": ck, "cited": "not recorded on the cited value",
                                 "own": K.cond_out(conds[ck], brief=True)["value"], "own_fact_id": conds[ck]["entry"]["fact_id"]})
            out["own_values"].append(dict(v, value_comparison=vm, conditions=cmp_))
    out["outcome"] = "found" if out["own_values"] else "cited paper found; no own value of the quantity there"
    out["excluded_in_cited_paper"] = [x for k in found for x in get_records(None, f["quantity"],
                                      {"species": cq["species"]} if cq.get("species") else None, papers=[k]).get("excluded", [])
                                      if group_of(x.get("data_kind", "")) == "own"]
    return out


# ============================================================================================================ UI helper: unit_tree
def unit_tree(unit_id):
    """The unit tree of a sample for the evidence panel: its measurements, then each level up to the paper, every condition
    at its level marked chosen / shadowed / conflict / several values. Not offered to the model."""
    K = kb()
    if unit_id not in K.role:
        return _err(f"unknown unit id '{unit_id}'")
    conds = K.conditions(unit_id)
    chosen = {c["entry"]["fact_id"]: c for c in conds.values()}
    levels = []
    for i, u in enumerate([u for u in K.chain(unit_id) if K.role.get(u) != "measurement"]):
        rows = []
        for e in K.level_entries(u, i):
            c = conds.get(e["key"])
            mark = "chosen" if e["fact_id"] in chosen else "shadowed by a nearer level" if c and e in c["shadowed"] else \
                "several values" if c and c["status"] != "ok" else ""
            if c and e["fact_id"] in chosen and c["conflicts"]:
                mark = "; ".join(K.conflict_text(c, x) for x in c["conflicts"])
            rows.append({"condition": e["key"], "value": K.show(e), "fact_id": e["fact_id"], "data_kind": e["data_kind"],
                         "printed": e.get("printed", ""), "source": e["source"], "mark": mark})
        levels.append(dict(K.unit_ref(u), level=LEVEL_NAMES.get(K.role[u], K.role[u]), conditions=rows))
    meas = [{"id": m, "method": K.method_of(m), "label": K.unit_label(m),
             "settings": [{"condition": cond_key(f["quantity"], parse_qual(f["qualifiers"])), "value": K.show(K.entry(f)),
                           "fact_id": f["fact_id"]} for f in K.kids[m] if f["type"] == "setting" and K.has_value(f)],
             "n_results": sum(1 for f in K.kids[m] if f["type"] in RESULT_TYPES and K.has_value(f))} for m in K.measurements(unit_id)]
    return {"unit": K.unit_ref(unit_id), "measurements": meas, "levels": levels, "conflicts": K.conflicts_of(conds)}


# ============================================================================================================ dispatch
TOOLS = {"resolve": resolve, "find_samples": find_samples, "get_records": get_records, "compare": compare, "claims": claims,
         "trace_citation": trace_citation}


def run_tool(name, args):
    """Run a tool by name; an exception is returned as {'error': ...} (the model reads it as a tool error)."""
    if name not in TOOLS:
        return _err(f"unknown tool '{name}'; tools: {sorted(TOOLS)}")
    try:
        inspect.signature(TOOLS[name]).bind(**(args or {}))
    except TypeError as e:
        return _err(f"bad arguments for {name}: {e}")
    try:
        return TOOLS[name](**(args or {}))
    except Exception as e:  # noqa: BLE001 - a tool failure is the model's to read, not a crash of the conversation
        return _err(f"{type(e).__name__}: {e}")


def model_view(result):
    """What the model receives: the result with curve points summarized (count and ranges) and statements cut to
    STATEMENT_CHARS; the log keeps the full result. Compact JSON."""
    def walk(x, key=None):
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                if k in ("points", "normalized_points") and isinstance(v, list):
                    xs, ys = [p[0] for p in v if p[0] is not None], [p[1] for p in v if p[1] is not None]
                    out[k] = {"n": len(v), "x_range": [min(xs), max(xs)] if xs else None, "y_range": [min(ys), max(ys)] if ys else None}
                else:
                    out[k] = walk(v, k)
            return out
        if isinstance(x, list):
            return [walk(v, key) for v in x]
        if isinstance(x, str) and key in ("statement", "statements", "searched_text") and len(x) > STATEMENT_CHARS:
            return x[:STATEMENT_CHARS] + "…"
        return x
    return json.dumps(walk(result), ensure_ascii=False, separators=(",", ":"))


# ============================================================================================================ check
def check():
    """The three cases' expected tool paths and the five known KB issues, as invariants (no counts pinned)."""
    ok = True

    def expect(cond, text):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + text)

    K = kb()
    sizes = {}

    def size(name, r):
        sizes[name] = len(model_view(r))
        return r

    # recipe fill: compile's recipe_fields.csv against the 0rf merge (listed, not a pass / fail item)
    print(f"INFO recipe source in use: {RECIPE_SOURCE}")
    for k in sorted(set(K.fill_records) | set(K.fill_compiled)):
        a, b = K.fill_records.get(k, {}), K.fill_compiled.get(k, {})
        for f in RECIPE_FIELDS:
            va, vb = a.get(f, {}).get("value"), b.get(f, {}).get("value")
            if va != vb:
                print(f"INFO recipe fill differs  {k[0]} {k[1]} {f}: recipe_fields.csv {vb}  |  0rf merge {va}")

    # case 1
    r = size("resolve SEM", resolve("SEM", "method"))
    ids = [m["id"] for m in r["matches"]]
    sem = next((m for m in r["matches"] if m["id"] == "sem"), {})
    expect({"sem", "sem_eds"} <= set(ids) and "tem" in sem.get("same_class", []), f"resolve SEM -> {ids}, sem same class {sem.get('same_class')}")
    r = size("resolve high aspect ratio", resolve("high-aspect-ratio", "structure"))
    ids = [m["id"] for m in r["matches"]]
    expect("har_feature" in ids, f"resolve high-aspect-ratio (structure) -> {ids}")
    r = size("resolve high aspect ratio (any)", resolve("high-aspect-ratio"))
    ar = next((m for m in r["matches"] if m["id"] == "aspect_ratio"), {})
    expect("porous_body" in ar.get("slot_of_structure_classes", []), f"aspect_ratio is a slot of {ar.get('slot_of_structure_classes')}")
    methods = ["sem", "sem_eds", "tem", "tem_eds", "epma"]
    r = size("find_samples case 1", find_samples([{"concept": "method", "value": methods}, {"concept": "structure", "value": ["har_feature", "porous_body"]}]))
    s1 = [s["id"] for s in r["samples"]]
    expect(r["counts"]["matched"] > 0, f"case 1 find_samples: {r['counts']['matched']} samples in {r['counts']['papers_matched']} papers")
    g = size("get_records case 1 images", get_records(s1, include=["images"]))
    expect(any(i["method"] and set(i["method"]) & set(methods) for i in g["images"]), f"case 1 images: {len(g['images'])} "
           f"({sorted({i['paper'] for i in g['images']})}); ambiguous {sum(i['binding'] == 'ambiguous' for i in g['images'])}")

    # case 2
    f2 = [{"concept": "reactant_A", "value": "tma"}, {"concept": "reactant_B", "value": "h2o"},
          {"concept": "deposition_temperature", "value": 300, "unit": "°C"}, {"concept": "structure", "value": "lateral_channel"},
          {"concept": "feature_width", "value": 500, "unit": "nm"}]
    r = size("find_samples case 2", find_samples(f2, vary=["cycle_number"]))
    s2 = [s["id"] for s in r["samples"]]
    expect(len(s2) > 0 and len({K.facts[s]["_paper"] for s in s2}) > 1, f"case 2 find_samples: {len(s2)} samples, papers {r['counts']['papers_matched']}")
    s15 = next((s for s in r["samples"] if s["id"].endswith("sample_15")), None)
    expect(s15 and any("purge_time" in c for c in s15.get("conflicts", [])), "known issue 1: own N2 purge vs inherited 4 s purge flagged, own preferred: "
           + str((s15 or {}).get("conflicts", [])[:2]))
    und = [u for u in r["undecided"] if "fig3" in u["id"]]
    expect(any("recorded as a range" in json.dumps(u) for u in und), "known issue 5: a specimen with only the recipe's temperature "
           "range is not matched to 300 °C, listed as undecided " + str([u["id"] for u in und][:4]))
    g = size("get_records case 2 PD50", get_records(s2, "penetration_depth", {"level": "50%"}, normalize=["normalize_thickness", "x_over_width"]))
    expect(all("level=50%" in v["qualifiers"] for v in g["values"]) and g["values"], f"case 2 PD50 values {len(g['values'])}, "
           f"excluded (no level) {sum('level not stated' in x['reason'] for x in g.get('excluded', []))}")
    g4 = get_records(None, "penetration_depth", {"level": "50%"})
    expect(any(x["fact_id"] == "gao15:s6.p22#2" for x in g4.get("rejected", [])), "known issue 4: a level=50% value with no unit "
           "(an aspect ratio) rejected for its dimension")
    c = size("compare case 2", compare(s2))
    expect(any(x["varied"] == "cycle_number" for x in c["comparison_sets"]), "case 2 compare: a cycle-number comparison set holds these samples")
    cl = size("claims case 2", claims(cause="cycle_number", effect="penetration_depth"))
    expect(cl["n_claims"] > 0, f"case 2 claims cycle_number -> penetration_depth: {cl['n_claims']}")

    # case 3
    r = size("resolve sticking coefficient", resolve("sticking coefficient"))
    ids = [m["id"] for m in r["matches"]]
    expect(ids and ids[0] == "initial_sticking_coefficient" and "recombination_probability" not in ids[:1], f"resolve sticking coefficient -> {ids[:4]}")
    g = size("get_records case 3", get_records(None, "initial_sticking_coefficient", {"species": "tma"}))
    own = {v["fact_id"]: v for v in g["values"] if v["group"] == "own"}
    expect("yli18:tabI.r1c4#1" in own and own["yli18:tabI.r1c4#1"].get("species_filled"), "known issue 3: yli18 Table I c filled "
           "from its run's reactant A: " + str(own.get("yli18:tabI.r1c4#1", {}).get("species_filled")))
    expect("yim20:s19.p4#1" in own, f"case 3 own TMA values {sorted(own)}")
    expect(any("material" in x["reason"] and x["fact_id"].startswith("ela03") for x in g.get("excluded", [])), "known issue 2: "
           "film species (al2o3, sio2) excluded and reported")
    cited = [v for v in g["values"] if v["group"] == "cited"]
    tr = None
    for v in cited:
        t = trace_citation(v["fact_id"])
        if t.get("outcome") == "found":
            tr = size("trace_citation case 3", t)
            break
    expect(tr and any(o["value_comparison"] == "match" for o in tr["own_values"]), "case 3 trace_citation: a cited TMA value traced "
           "to its paper with a matching own value " + (f"({tr['cited']['fact_id']} -> {tr['cited_paper'][0]['paper']})" if tr else ""))
    print("model-view sizes (chars):", json.dumps(sizes))
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--call", nargs=2, metavar=("TOOL", "JSON_ARGS"), help="run one tool and print its full result")
    a = ap.parse_args()
    if a.call:
        print(json.dumps(run_tool(a.call[0], json.loads(a.call[1])), ensure_ascii=False, indent=1))
    else:
        sys.exit(0 if check() else 1)
