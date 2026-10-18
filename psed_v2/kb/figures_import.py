#!/usr/bin/env python3
"""P84-P87: the rule-based figure importer. Reads ingest/final/<id>/figures.json and ingest/answers/figures.json, writes
kb/<id>.figures.json (the records the knowledge base loads), kb/import_report.csv (one row per paper), kb/import_panels.csv (every data
panel with its outcome and reason), ontology/unmapped.csv (every unresolved field) and kb/problems.txt (the P86 cross-check).

    python3 psed_v2/kb/figures_import.py                 # every paper with a figures.json
    python3 psed_v2/kb/figures_import.py <paper_id> ...  # a subset (the report covers the papers run)

No model call, no PDF, no paper named in any rule. Every rule is general; a paper, figure or label is never special-cased.

Gate (P84): a plot, spectrum or map panel is imported when its verdict in answers/figures.json is ok and it carries no F5 or F6 flag;
F1-F4 are kept on the records as flags. Every other data panel is listed with its reason. Resolution, closed, in this order:
  a. axis label -> quantity id (resolve_label): LaTeX and braces stripped, the bracketed unit, trailing symbols, case and whitespace
     normalised, then matched to the ids, names, labels and aliases of the entries with role coordinate, condition, output or
     model_parameter; a transform prefix log(...)/log10(...)/ln(...) is recorded and resolution continues on the inner label; a symbol
     with a subscript word (T_deposition) resolves when the symbol is an entry's label and the word is in that entry's name.
  b. unit_raw -> canonical through ontology/units.yaml; points are converted to the entry's unit, a transformed axis back to linear
     values, raw label, unit and points kept; the unit's dimension must equal the entry's, else dimension_mismatch. A normalised axis
     whose denominator resolves to cycle_number reads a length unit as per cycle (the printed 'nm' of S/N).
  c. a normalised axis resolves to the normalised quantity by its label (normalized_thickness, surface_coverage, growth_per_cycle);
     its denominator symbol resolves to a quantity (N -> cycle_number) or a species and is recorded as a condition, else the reason
     is denominator.
  d. series_axis, series labels and condition keys -> conditions (resolve_label on the key; a label is numeric with unit -> the
     series_axis quantity's value, a species or element -> species, a model or measurement word -> kind simulated or measured, anything
     else -> a replicate label kept raw, series_structure replicate); a bare symbol that resolves only to a model_parameter entry is
     stored with role model_parameter. A series is simulated (P87) when its label is a model word or, failing a label word, when the
     panel's content line (else the caption's first sentence) holds a model word and no measurement word.
  e. every panel of every type is one inventory record (paper, figure, panel, panel_type, content, resolved quantities).
Records: curve (one per imported series), value (one per cell of a map with cells, one per peak), inventory, set (P85: a plot or
map panel with two or more series is a set of kind series over the resolved series_axis; a map with cells a grid over its axes), derived
(P86: plateau, half-value crossing -> penetration_depth, linear slope of thickness vs cycles -> growth_per_cycle, each with its method
and source curve). Kinds (P87): a measured series read_from_figure with the basis 'digitized', a simulated series simulated, cells and
peaks read_from_figure with the basis 'printed'.
"""
import collections, csv, datetime, json, math, re, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "pilot"))
import lists as L  # noqa: E402
import vocab as V  # noqa: E402
from elements import PAPERS  # noqa: E402

FINAL = V2 / "ingest" / "final"
ANSWERS = V2 / "ingest" / "answers" / "figures.json"
UNITS = yaml.safe_load((V2 / "ontology" / "units.yaml").read_text(encoding="utf-8"))["units"]
for _u in UNITS:                                                                 # YAML reads '1.0e5' as text: factors and offsets are numbers
    _u["factor"] = float(_u["factor"]); _u["offset"] = float(_u.get("offset", 0.0))
UNMAPPED = V2 / "ontology" / "unmapped.csv"
ROLES = ("coordinate", "condition", "output", "model_parameter")
PROFILE_Y = ("film_thickness", "normalized_thickness", "surface_coverage", "growth_per_cycle")
MODEL_WORDS = {"simulation": "simulated", "simulated": "simulated", "model": "simulated", "fit": "simulated", "fitting": "simulated", "numerical": "simulated",
               "approximation": "simulated", "appr": "simulated", "calculated": "simulated", "theory": "simulated", "measured": "measured", "experimental": "measured",
               "experiment": "measured", "data": "measured"}
ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe "
               "Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi".split())
SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "01234567890123456789-")
GREEK = {"delta": "δ", "Delta": "Δ", "theta": "θ", "mu": "µ", "tau": "τ", "epsilon": "ε", "sigma": "σ", "beta": "β", "rho": "ρ", "lambda": "λ", "alpha": "α", "xi": "ξ", "chi": "χ", "nu": "ν", "omega": "ω", "pi": "π", "phi": "φ"}
PLATEAU_TOL, PLATEAU_MIN, R2_MIN = 0.05, 4, 0.98


# ------------------------------------------------------------------------------------------------------------ text rules
def delatex(s):
    """LaTeX commands and braces removed, Greek letters as characters, subscripts and superscripts flattened."""
    s = str(s or "").replace("$", "")
    s = re.sub(r"\\(?:text|mathrm|mathit|mathbf|textit|mathsf)\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\tilde\{?([A-Za-z])\}?", r"\1̃", s)
    s = re.sub(r"\\bar\{?([A-Za-z])\}?", r"\1̄", s)
    for k, v in GREEK.items():
        s = re.sub(rf"\\{k}(?![A-Za-z])\s?", v, s)                            # '\delta t' is δt
    s = s.replace("\\circ", "°").replace("^\\circ", "°").replace("\\,", " ").replace("\\ ", " ").replace("\\%", "%")
    s = re.sub(r"\\([a-zA-Z]+)", r"\1", s)
    s = re.sub(r"[_^]\{([^}]*)\}", r"\1", s)
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    """The matching form of a label: delatex, subscript digits, lowercase, bracket groups holding a unit removed, punctuation and
    spaces dropped; µ and μ folded."""
    s = delatex(s).translate(SUB).replace("μ", "µ").lower()
    s = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]\s*$", "", s)                         # a trailing bracket group (the unit, or a note)
    s = re.sub(r"[\s\-_.,;:'\"]+", "", s)
    return s


def strip_unit_brackets(s):
    """The label without its trailing bracket group."""
    return re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]\s*$", "", delatex(s)).strip()


def _tokens(s):
    return [t for t in re.split(r"[\s,;:]+", strip_unit_brackets(s)) if t]


def is_symbol(t):
    """A token that is a symbol, not a word: short, or carrying a digit, a tilde, a bar, a Greek letter or a subscript."""
    return len(t) <= 3 or bool(re.search(r"[0-9̃̄δΔθτσρλαβεξχνωπφµ_^]", t))


def plural_forms(c):
    return [c] + ([c[:-1]] if c.endswith("s") else [c + "s"])


TRANSFORM = re.compile(r"^\s*(log10|log|ln)\s*[\(\[](.+)[\)\]]\s*$", re.I)


def paper_definitions(pid, with_quantity=True):
    """P89: the paper's definition facts that name a quantity (pilot/<pid>.facts.csv): {normalised term: (quantity, note, fact id)}.
    With with_quantity=False, the terms the paper defines WITHOUT an ontology quantity (D, η, P_d ...): {normalised term: fact id}; a
    label that is such a term is the paper's own symbol and resolves to nothing, never to an ontology guess (P89b)."""
    p = V2 / "pilot" / f"{pid}.facts.csv"
    out = {}
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r["type"] != "definition" or not r.get("term"):
                continue
            has_q = bool(r["quantity"]) and r["quantity"] in L.ENTRIES
            if has_q != with_quantity:
                continue
            for t in r["term"].split("|"):
                val = (r["quantity"], r.get("definition_note", ""), r["fact_id"]) if with_quantity else r["fact_id"]
                out.setdefault(norm(t), val)
                sym = delatex(t).translate(SUB).replace("μ", "µ").replace(" ", "")
                out.setdefault("sym:" + sym, val)
    return out


class Resolver:
    """Labels, series labels and condition keys against the ontology (vocab.py): one index of every normalised id, name, label and
    alias of the quantity entries with a role in ROLES, and of every species id, formula and alias."""

    def __init__(self):
        self.idx = collections.defaultdict(set)
        self.label_of = {}
        self.alias_sym = {}
        for i, e in L.ENTRIES.items():
            if e["type"] not in ("quantity", "categorical") or e.get("replaced_by") or e.get("role") not in ROLES:
                continue
            for s in [i.replace("_", " "), e.get("name") or "", e.get("label") or ""] + list(e.get("aliases") or []):
                if s:
                    self.idx[norm(s)].add(i)
            for a in e.get("aliases") or []:                                     # the symbol part of an alias ('Pressure pA (Pa)' -> pA): matched as a symbol only
                ts = _tokens(a)
                if len(ts) > 1 and is_symbol(ts[-1]) and not re.fullmatch(r"\d+", ts[-1]):
                    self.alias_sym.setdefault(norm(ts[-1]), set()).add(i)
            if e.get("label"):
                self.label_of.setdefault(delatex(e["label"]).translate(SUB).replace("μ", "µ").replace(" ", ""), set()).add(i)   # case-sensitive: T and t differ
        self.species = collections.defaultdict(set)
        for i, s in L.SPECIES.items():
            for a in [i, s.get("formula") or "", s.get("name") or ""] + list(s.get("aliases") or []):
                if a:
                    self.species[norm(a)].add(i)
        self.ambiguous = {norm(a) for a in L.AMBIGUOUS_ALIASES}
        self.p89_hits = []

    def _pick(self, hit, dimension, axis=""):
        """The ids whose dimension is the printed unit's, when a unit is known (a lone symbol of another dimension is not a match); still
        several and an axis given: P90c, an x axis takes a coordinate over a condition, a y axis an output."""
        if dimension:
            hit = {i for i in hit if L.ENTRIES[i].get("dimension") == dimension or (dimension == "dimensionless" and L.ENTRIES[i].get("dimension") in ("signal", "count"))}
        hit = set(hit)
        if len(hit) > 1 and axis:
            want = {"x": ("coordinate",), "y": ("output",)}[axis]
            pref = {i for i in hit if L.ENTRIES[i].get("role") in want}
            if len(pref) == 1 and all(L.ENTRIES[i].get("role") in ("coordinate", "condition", "output") for i in hit):
                hit = pref
        return hit

    def symbol(self, t, dimension="", axis=""):
        """A symbol token against the entries' labels, case-sensitive, then the index (case-folded)."""
        key = delatex(t).translate(SUB).replace("μ", "µ").replace(" ", "")
        hit = self._pick(self.label_of.get(key, set()), dimension, axis)
        if len(hit) == 1:
            return hit
        hit = self._pick(self.idx.get(norm(t), set()), dimension, axis)
        if hit:
            return hit
        return self._pick(self.alias_sym.get(norm(t), set()), dimension, axis)

    def quantity(self, label, unit_dimension="", defs=None, axis=""):
        """(id, transform, reason) for an axis label or a condition key: the whole label (plural folded), the label without its
        trailing symbol, the symbol alone (case-sensitive against the entries' labels), a symbol with a subscript word, A/B where a
        transform of the ontology divides A by B; several matches are narrowed to the printed unit's dimension; '' with a reason
        when nothing or several match."""
        raw = str(label or "")
        transform = ""
        m = TRANSFORM.match(delatex(raw))
        if m:
            transform, raw = m.group(1).lower(), m.group(2)
        raw = re.sub(r"^\s*#\s*", "number of ", raw)                            # '#ALD cycle' = number of ALD cycles
        if not raw.strip():
            return "", transform, "empty"
        noq = getattr(self, "noq", {})
        if noq:                                                                 # P89b: a symbol the paper defines without an ontology quantity is its own, not an ontology guess
            core = strip_unit_brackets(raw).strip()
            sym = "sym:" + delatex(core).translate(SUB).replace("μ", "µ").replace(" ", "")
            keys = [sym] if " " not in core else [sym, norm(core), norm(core.replace("|", ""))]   # a lone symbol matches case-sensitively (h is not H, S is not s); a worded label by its words, absolute-value bars aside
            hit = next((noq[c] for c in keys if c in noq), "")                  # the whole label defined: beats any token-level match
            if hit:
                return "", transform, f"defined by the paper without an ontology quantity ({hit}; P89b)"
        q, why = self._quantity(raw, unit_dimension, axis)
        if not q and strip_unit_brackets(raw).count("/") == 1 and all(x.strip() for x in strip_unit_brackets(raw).split("/")):      # P90a on a worded ratio: 'Distance / cavity height'
            a, b = (x.strip() for x in strip_unit_brackets(raw).split("/"))
            qa, _ = self._quantity(a, "", ""); qb, _ = self._quantity(b, "", "")
            qa = qa or self._defined(a, defs); qb = qb or self._defined(b, defs)   # P89 on the parts: 'Distance / cavity height' with h defined by the paper
            r = self.ratio(a, b) or (next(iter({i for i, e in L.ENTRIES.items() if len(e.get("ratio_of") or []) == 2 and e["ratio_of"][0].split("{")[0] == qa and e["ratio_of"][1].split("{")[0] == qb}), "") if qa and qb else "")
            if r:
                return r, transform, ""
            why = f"{why}; P90a ratio: parts {a!r} -> {qa or 'unresolved'}, {b!r} -> {qb or 'unresolved'}, no entry declares that ratio"
        if q:
            return q, transform, ""
        if defs:                                                                # P89: the paper's own definitions, after the ontology and before giving up
            toks = _tokens(raw)
            cands = [norm(raw)] + ([norm(" ".join(toks[:-1])), "sym:" + delatex(toks[-1]).translate(SUB).replace("μ", "µ").replace(" ", ""), norm(toks[-1])] if len(toks) > 1 else ["sym:" + delatex(raw.strip()).translate(SUB).replace("μ", "µ").replace(" ", "")])
            for c in [x for c0 in cands for x in (plural_forms(c0) if not c0.startswith("sym:") else [c0])]:
                if c in defs:
                    self.p89_hits.append((raw, defs[c]))
                    return defs[c][0], transform, "definition:" + defs[c][2]
        return "", transform, why

    def _defined(self, raw, defs):
        """The paper's definition (P89) that names `raw`, as the quantity id, or ''."""
        if not defs or not str(raw).strip():
            return ""
        toks = _tokens(raw)
        cands = [norm(raw), "sym:" + delatex(str(raw).strip()).translate(SUB).replace("μ", "µ").replace(" ", "")] + ([norm(toks[-1])] if len(toks) > 1 else [])
        for c in [x for c0 in cands for x in (plural_forms(c0) if not c0.startswith("sym:") else [c0])]:
            if c in defs:
                self.p89_hits.append((raw, defs[c]))
                return defs[c][0]
        return ""

    def _quantity(self, raw, unit_dimension="", axis=""):
        """The ontology part of the resolution: (id, reason)."""
        toks = _tokens(raw)
        if len(toks) >= 2 and self.species_id(toks[0]):                            # '<species> pressure': the species-scoped entry of what the rest names
            q0, why0 = self._quantity(" ".join(toks[1:]), unit_dimension, axis)
            dim = L.ENTRIES[q0].get("dimension") if q0 else unit_dimension
            scoped = {i for i, e in L.ENTRIES.items() if e.get("role") in ROLES and "species" in (e.get("qualifiers") or []) and e.get("dimension") == dim and dim}
            if len(scoped) == 1:
                return next(iter(scoped)), ""
        if len(toks) == 1 and is_symbol(toks[0]):                                  # a lone symbol: case-sensitive against the entries' labels first (N is not n, T is not t)
            hit = self.symbol(toks[0], unit_dimension, axis)
            if len(hit) == 1:
                return next(iter(hit)), ""
        steps = [norm(raw)]
        words = toks[:-1] if len(toks) > 1 and is_symbol(toks[-1]) else toks
        if len(toks) > 1 and is_symbol(toks[-1]):
            steps.append(norm(" ".join(toks[:-1])))                                # 'film thickness S' -> 'film thickness'
        prefixed = bool(words) and words[0].lower() in ("normalized", "normalised", "relative", "elapsed")
        if prefixed:
            steps.append(norm(" ".join(words[1:])))                                # a normalised or relative axis: the quantity it normalises
        for c in steps:
            for cc in plural_forms(c):
                if not cc:
                    continue
                hit = self._pick(self.idx.get(cc, set()), unit_dimension, axis)
                if len(hit) == 1:
                    return next(iter(hit)), ""
                if len(hit) > 1:
                    return "", f"ambiguous: {', '.join(sorted(hit))}"
                if cc in self.ambiguous:
                    return "", f"ambiguous alias: {', '.join(L.AMBIGUOUS_ALIASES.get(cc, []))}"
        sym = toks[-1] if len(toks) > 1 and is_symbol(toks[-1]) else (toks[0] if len(toks) == 1 else "")
        if sym:
            if "/" in sym and sym.count("/") == 1 and all(sym.split("/")):            # A/B: a transform of the ontology that divides A by B
                a, b = sym.split("/")
                r = self.ratio(a, b)                                            # P90a: an entry that declares this ratio
                if r:
                    return r, ""
                ha, hb = self.symbol(a) | self.idx.get(norm(a), set()), self.symbol(b) | self.idx.get(norm(b), set())
                outs = {t["output"].split("{")[0] for t in V.TRANSFORMS if [x.split("{")[0] for x in t["inputs"]] in [[ia, ib] for ia in ha for ib in hb] and "/" in t["formula"].split("(")[0]}
                if len(outs) == 1:
                    return next(iter(outs)), ""
            hit = self.symbol(sym, unit_dimension, axis)
            if len(hit) == 1:
                return next(iter(hit)), ""
            if len(hit) > 1:
                return "", f"ambiguous: {', '.join(sorted(hit))}"
            if norm(sym) in self.ambiguous:
                return "", f"ambiguous alias: {', '.join(L.AMBIGUOUS_ALIASES.get(norm(sym), []))}"
        m = re.match(r"^\s*([A-Za-z]̃?|[δΔθτσρλαβ])\s*[_]?\s*\{?([A-Za-z]+)\}?\s*$", delatex(strip_unit_brackets(raw)))
        if m:                                                                       # a symbol with a subscript word: T_deposition
            ids = self.label_of.get(m.group(1), set())
            word = m.group(2).lower()
            ids = {i for i in ids if len(word) >= 3 and (word in (L.ENTRIES[i].get("name") or i).lower().replace("_", " ").split() or any(word in re.findall(r"[a-z]+", a.lower()) for a in L.ENTRIES[i].get("aliases") or []))}
            if len(ids) == 1:
                return next(iter(ids)), ""
        if len(words) >= 2 and (unit_dimension or prefixed):                       # 'Elapsed time', 'MoCl2O2 pulse', 'Normalized X-ray counts': the head word alone, confirmed by the unit's dimension or the prefix
            hit = self._pick(self.idx.get(norm(words[-1]), set()) | self.symbol(words[-1]), unit_dimension)
            if len(hit) == 1:
                return next(iter(hit)), ""
        m = re.match(r"^(?:number of|no\. of)\s+(.+)$|^(.+?)\s+(?:count|number)$", str(raw).strip(), flags=re.I)
        if m:                                                                       # 'cycle count', 'number of cycles': the counted noun, as its plural, is the label (P90d)
            noun = (m.group(1) or m.group(2)).strip().lower()
            hit = set()
            for cand in (noun, noun + "s", noun.rstrip("s")):
                hit |= self.idx.get(norm(cand), set())
            hit = self._pick(hit, unit_dimension or "count")
            if len(hit) == 1:
                return next(iter(hit)), ""
        return "", "no entry, alias or label matches"

    def ratio(self, a, b):
        """P90a: 'X / Y' whose parts resolve to the ratio_of of an entry resolves to that entry ('' otherwise)."""
        ha = self.symbol(a) | self.idx.get(norm(a), set()); hb = self.symbol(b) | self.idx.get(norm(b), set())
        if not ha or not hb:
            return ""
        outs = {i for i, e in L.ENTRIES.items() if len(e.get("ratio_of") or []) == 2 and e["ratio_of"][0].split("{")[0] in ha and e["ratio_of"][1].split("{")[0] in hb}
        return next(iter(outs)) if len(outs) == 1 else ""

    def species_id(self, label):
        hit = self.species.get(norm(label), set())
        return next(iter(hit)) if len(hit) == 1 else ""


# ----------------------------------------------------------------------------------------------------------- unit rules
def norm_unit(u):
    u = delatex(u).replace("μ", "µ").translate(SUB)
    u = re.sub(r"\s*\^\s*", "^", u)
    u = u.replace("^-1", "-1").replace("^-2", "-2").replace("^-3", "-3").replace("^{-1}", "-1").replace("^{-2}", "-2").replace("^{-3}", "-3")
    u = re.sub(r"[\s.]", "", u).replace("·", "")
    return u


UNIT_INDEX = {}
for _u in UNITS:
    for _v in _u["variants"]:
        UNIT_INDEX.setdefault(norm_unit(_v), _u)
UNIT_BY_SYMBOL = {u["symbol"]: u for u in UNITS}


UNIT_INDEX_CI = {}
for _k, _u in list(UNIT_INDEX.items()):
    UNIT_INDEX_CI.setdefault(_k.lower(), _u)


def unit_of(raw):
    """The table row of a printed unit (exact, then case-folded), or None; an empty unit is no unit."""
    if not (raw or "").strip():
        return None
    n = norm_unit(raw)
    return UNIT_INDEX.get(n) or UNIT_INDEX_CI.get(n.lower())


def convert(v, frm, to):
    """A value from one table row to another (same dimension): printed -> SI -> target."""
    si = (v + frm.get("offset", 0.0)) * frm["factor"]
    return si / to["factor"] - to.get("offset", 0.0)


def fit_unit(uraw, q):
    """The table row of a printed unit for an entry: a per-cycle entry printed in a length unit reads it as that length per cycle
    (rule c); an empty unit of a dimensionless, signal or count entry is the entry's own unit."""
    e = L.ENTRIES.get(q, {})
    if not (uraw or "").strip() and e.get("dimension") in ("dimensionless", "signal", "count"):
        return {"dimensionless": UNIT_BY_SYMBOL["1"], "signal": UNIT_BY_SYMBOL[""], "count": UNIT_BY_SYMBOL["cycle"]}[e["dimension"]]
    row = unit_of(uraw)
    if row and e.get("dimension") == "length_per_cycle" and row["dimension"] == "length":
        row = unit_of(uraw.strip() + "/cycle") or row
    if row is None and not (uraw or "").strip() and e.get("dimension") in ("dimensionless", "signal", "count"):
        row = {"dimensionless": UNIT_BY_SYMBOL["1"], "signal": UNIT_BY_SYMBOL[""], "count": UNIT_BY_SYMBOL["cycle"]}[e["dimension"]]
    return row


def entry_unit_row(q):
    """The table row of an entry's canonical unit ('' for a signal, '1' for a dimensionless quantity)."""
    u = L.ENTRIES[q].get("unit", "")
    return UNIT_BY_SYMBOL.get(u) or unit_of(u)


# ------------------------------------------------------------------------------------------------------ number parsing
NUM = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(?:[–-]\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?))?\s*(.*?)\s*$")
SCI = re.compile(r"^\s*([-+]?\d+\.?\d*)\s*[×x]\s*10\s*\^?\s*\{?([-+]?\d+)\}?\s*(.*?)\s*$")


def parse_value(text):
    """(value, value_max or None, unit text) of a printed value: '150 °C', '100–140', '1 × 10^5 Pa·s', '0.80'; None when no number leads."""
    t = delatex(text).translate(SUB)
    m = SCI.match(t)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2)), None, m.group(3)
    m = re.match(r"^\s*10\s*\^?\s*\{?([-+]?\d+)\}?\s*(.*?)\s*$", t)                     # '10^-3 Torr'
    if m:
        return 10 ** int(m.group(1)), None, m.group(2)
    m = NUM.match(t)
    if not m or m.group(1) is None:
        return None
    unit = m.group(3)
    if unit and re.match(r"^[A-Za-z]", unit) and len(unit.split()) > 2:        # 'Sample 2' is not a value; a long tail is a name
        return None
    return float(m.group(1)), (float(m.group(2)) if m.group(2) else None), unit


# ------------------------------------------------------------------------------------------------------------- derived
def plateau_of(pts):
    """P86: the mean of the longest run of consecutive points within PLATEAU_TOL of the running maximum, at least PLATEAU_MIN points:
    (value, first index, last index) or None."""
    best, run, rm = None, [], -math.inf
    for n, (x, y) in enumerate(pts):
        rm = max(rm, y)
        if rm > 0 and y >= (1 - PLATEAU_TOL) * rm:
            run.append(n)
        else:
            run = []
        if len(run) >= PLATEAU_MIN and (best is None or len(run) > len(best)):
            best = list(run)
    if not best:
        return None
    return sum(pts[n][1] for n in best) / len(best), best[0], best[-1]


def half_crossing(pts, plateau, after):
    """P86: the x where y first falls below half the plateau after the plateau run, by linear interpolation; None without a crossing."""
    half = 0.5 * plateau
    for n in range(after, len(pts) - 1):
        (x0, y0), (x1, y1) = pts[n], pts[n + 1]
        if y0 >= half > y1:
            return x0 + (half - y0) * (x1 - x0) / (y1 - y0) if y1 != y0 else x1
    return None


def linear_fit(pts):
    """(slope, intercept, r2) of y against x."""
    n = len(pts)
    sx = sum(x for x, _ in pts); sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts); sxy = sum(x * y for x, y in pts); syy = sum(y * y for _, y in pts)
    d = n * sxx - sx * sx
    if d == 0:
        return None
    b = (n * sxy - sx * sy) / d; a = (sy - b * sx) / n
    ss_res = sum((y - a - b * x) ** 2 for x, y in pts); ss_tot = syy - sy * sy / n
    return b, a, (1 - ss_res / ss_tot if ss_tot else 1.0)


# --------------------------------------------------------------------------------------------------------- the import
class Importer:
    def __init__(self):
        self.R = Resolver()
        self.unmapped = []
        self.panels = []                                                            # every data panel: outcome and reason
        self.problems = []
        ans = json.loads(ANSWERS.read_text(encoding="utf-8"))["items"] if ANSWERS.exists() else []
        self.verdict = {(v["paper_id"], str(v["figure"]), v["panel"]): v for v in ans}

    def unm(self, pid, fig, panel, field, raw, reason):
        self.unmapped.append(dict(paper=pid, figure=fig, panel=panel, field=field, raw=raw, reason=reason))

    # ---- axes
    def axis(self, pid, fig, panel, ax, a):
        """One axis resolved: dict(quantity, unit, unit_raw, label_raw, transform, dimension, unit_row, denominator, reason)."""
        out = dict(label_raw=a.get("label_raw"), unit_raw=a.get("unit_raw") or "", log=bool(a.get("log")), is_normalized=bool(a.get("is_normalized")),
                   quantity="", unit="", transform="", dimension="", denominator=None, reason="")
        uraw0 = a.get("unit_raw") or ""
        if not uraw0.strip():                                                   # P90b: the unit inside the label's bracket feeds unit resolution
            lab0 = delatex(a.get("label_raw") or "")
            mt = TRANSFORM.match(lab0)
            if mt:                                                              # 'ln(Plasma time (s))': the bracket inside the transform
                lab0 = mt.group(2)
            m = re.search(r"[\(\[]([^()\[\]]*)[\)\]]\s*$", lab0)
            if m and unit_of(m.group(1)):
                uraw0 = m.group(1)
        urow0 = unit_of(uraw0)
        q, tr, why = self.R.quantity(a.get("label_raw") or "", urow0["dimension"] if urow0 else "", self.defs, ax)
        out["transform"] = tr
        if why.startswith("definition:"):
            out["definition"] = why.split(":", 1)[1]; out["definition_note"] = self.defs_note.get(q, "")
            why = ""
        if not q:
            out["reason"] = f"label_unresolved: {why}"
            self.unm(pid, fig, panel, f"{ax}.label_raw", a.get("label_raw") or "", out["reason"])
            return out
        e = L.ENTRIES[q]
        out["quantity"], out["dimension"] = q, e.get("dimension", "")
        if a.get("is_normalized") and a.get("normalization_denominator_symbol"):
            den = a["normalization_denominator_symbol"]
            dq, _, _ = self.R.quantity(den, "", self.defs)                       # P89: a denominator the paper defines ('cavity height' = h)
            sp = self.R.species_id(den) if not dq else ""
            if dq:
                out["denominator"] = dict(symbol=den, quantity=dq)
            elif sp:
                out["denominator"] = dict(symbol=den, species=sp)
            else:
                out["reason"] = "denominator"
                self.unm(pid, fig, panel, f"{ax}.normalization_denominator_symbol", den, "denominator: no quantity or species matches")
                return out
        uraw = uraw0
        row = fit_unit(uraw, q)
        if row is None:
            if True:
                out["reason"] = "unit_unknown"
                self.unm(pid, fig, panel, f"{ax}.unit_raw", uraw, f"unit_unknown: not in units.yaml (quantity {q})")
                return out
        if row["dimension"] != e.get("dimension") and not (row["dimension"] == "dimensionless" and e.get("dimension") == "signal"):
            out["reason"] = "dimension_mismatch"
            self.unm(pid, fig, panel, f"{ax}.unit_raw", uraw, f"dimension_mismatch: unit {row['symbol']} is {row['dimension']}, {q} is {e.get('dimension')}")
            return out
        target = entry_unit_row(q) or row
        out["unit"], out["unit_row"], out["target_row"] = target["symbol"], row, target
        return out

    def to_canonical(self, v, ax):
        if ax["transform"]:
            v = 10 ** v if ax["transform"] in ("log", "log10") else math.exp(v)
        if ax["unit_row"]["dimension"] == "signal":
            return v
        return convert(v, ax["unit_row"], ax["target_row"])

    # ---- conditions and series labels
    def condition(self, pid, fig, panel, key, text):
        """A condition key and printed value resolved: dict(key_raw, raw, quantity, value, value_max, unit, role) or None."""
        pv0 = parse_value(text)
        urow0 = unit_of(pv0[2]) if pv0 and pv0[2].strip() else None
        q, _, why = self.R.quantity(key, urow0["dimension"] if urow0 else "", self.defs)
        if not q:
            self.unm(pid, fig, panel, "conditions.key", key, f"label_unresolved: {why}")
            return None
        rec = dict(key_raw=key, raw=text, quantity=q, role=L.ENTRIES[q].get("role", ""), value=None, value_max=None, unit="")
        if why.startswith("definition:"):
            rec["definition"] = why.split(":", 1)[1]
        pv = parse_value(text)
        if pv is None:
            rec["text"] = str(text)
            return rec
        v, vmax, u = pv
        row = fit_unit(u, q)
        target = entry_unit_row(q)
        if self.defs and not (row and target and row["dimension"] == target["dimension"]) and not why.startswith("definition:"):   # P89: the paper's definition of the symbol, when the ontology's match fails the unit check
            q2, _, why2 = self.R.quantity(key, "", self.defs) if False else ("", "", "")
            dq = self.defs.get(norm(key)) or self.defs.get("sym:" + delatex(key).translate(SUB).replace("μ", "µ").replace(" ", ""))
            if dq and dq[0] != q:
                q = dq[0]; rec.update(quantity=q, role=L.ENTRIES[q].get("role", ""), definition=dq[2]); self.R.p89_hits.append((key, dq))
                row = fit_unit(u, q); target = entry_unit_row(q)
        if row and target and row["dimension"] == target["dimension"]:
            rec.update(value=convert(v, row, target), value_max=convert(vmax, row, target) if vmax is not None else None, unit=target["symbol"])
        else:
            rec.update(value=v, value_max=vmax, unit=u.strip(), unit_unresolved=True)
            self.unm(pid, fig, panel, "conditions.value", f"{key}: {text}", f"unit_unknown: {u!r} for {q}")
        return rec

    def series_label(self, pid, fig, panel, label, axis_q):
        """One of four classes (P84d): numeric (with the series-axis quantity), species, kind, replicate."""
        lab = str(label or "").strip()
        if not lab:
            return dict(label_raw="", cls="empty")
        pv = parse_value(lab)
        if pv is not None and pv[2] and not re.match(r"^[A-Za-z°µμ%Å]", pv[2]):   # '120/160 °C': a number followed by a separator is a name, not a value with a unit
            pv = None
        if pv is not None and axis_q:
            v, vmax, u = pv
            target = entry_unit_row(axis_q); row = fit_unit(u, axis_q) if (u.strip() or target and target["dimension"] in ("dimensionless", "count")) else None
            out = dict(label_raw=lab, cls="numeric", quantity=axis_q, value=v, value_max=vmax, unit=u.strip())
            if row and target and row["dimension"] == target["dimension"]:
                out.update(value=convert(v, row, target), value_max=convert(vmax, row, target) if vmax is not None else None, unit=target["symbol"])
            elif not u.strip() and target:
                out.update(unit="", unit_missing=True)
            else:
                out["unit_unresolved"] = True
                self.unm(pid, fig, panel, "series.label", lab, f"unit_unknown: {u!r} for {axis_q}")
            return out
        head = re.sub(r"\s*[\(\[].*$", "", lab).strip()
        if head in ELEMENTS:
            return dict(label_raw=lab, cls="species", element=head)
        sp = self.R.species_id(head)
        if sp:
            return dict(label_raw=lab, cls="species", species=sp)
        words = re.findall(r"[a-zA-Z]+", lab.lower())
        kinds = {MODEL_WORDS[w] for w in words if w in MODEL_WORDS}
        if len(kinds) == 1:
            return dict(label_raw=lab, cls="kind", kind=next(iter(kinds)))
        return dict(label_raw=lab, cls="replicate", series_structure="replicate")

    # ---- one paper
    def paper(self, pid):
        d = json.loads((FINAL / pid / "figures.json").read_text(encoding="utf-8"))
        key = PAPERS.get(pid, pid)
        self.defs = paper_definitions(pid)                                      # P89
        self.R.noq = paper_definitions(pid, with_quantity=False)                # P89b
        self.defs_note = {q: note for _, (q, note, _) in self.defs.items()}
        self.R.p89_hits = []
        prov = dict(extractor="vlm", model=d["model"], prompt_sha256=d["prompt_sha256"])
        out = dict(paper_id=pid, key=key, model=d["model"], prompt_sha256=d["prompt_sha256"], imported_at=datetime.datetime.now().isoformat(timespec="seconds"),
                   inventory=[], curves=[], values=[], sets=[], derived=[])
        counts = collections.Counter()
        for f in d["figures"]:
            fig = str(f["number"]); flags = [x["flag"] for x in f["flags"]]
            for p in f["panels"]:
                pan = p["panel"]; pel = f"fig{fig}{pan}"; eid = f"{key}:{pel}"
                inv = dict(id=eid, figure=fig, panel=pan, panel_type=p["panel_type"], content=p.get("content", ""), quantities=[], flags=flags, status="inventory")
                out["inventory"].append(inv); counts["inventory"] += 1
                data = p["panel_type"] in ("plot", "spectrum") or (p["panel_type"] == "map" and (p.get("series") or p.get("cells")))
                if not data:
                    continue
                counts["data_panels"] += 1
                v = self.verdict.get((pid, fig, pan))
                row = dict(paper=pid, figure=fig, panel=pan, panel_type=p["panel_type"], verdict=v["verdict"] if v else "", flags=";".join(flags), outcome="", reason="")
                self.panels.append(row)
                if not v:
                    row.update(outcome="not imported", reason="no verdict"); inv["status"] = "not judged"; continue
                if v["verdict"] != "ok":
                    row.update(outcome="not imported", reason=f"verdict {v['verdict']}"); inv["status"] = f"verdict {v['verdict']}"; continue
                if "F5" in flags or "F6" in flags:
                    row.update(outcome="not imported", reason="flag " + ", ".join(x for x in flags if x in ("F5", "F6"))); inv["status"] = "flagged F5/F6"; continue
                ax = {a: self.axis(pid, fig, pan, a, p.get(a) or {}) for a in ("x", "y")}
                inv["quantities"] = [ax[a]["quantity"] for a in ("x", "y") if ax[a]["quantity"]]
                need = ("x",) if p["panel_type"] == "spectrum" else ("x", "y")
                bad = [a for a in need if not ax[a]["quantity"] or ax[a]["reason"]]
                if bad:
                    row.update(outcome="inventory only", reason="; ".join(f"{a} {ax[a]['reason']}" for a in bad)); inv["status"] = "unresolved axis"; continue
                conds = {}
                for ck, cv in (p.get("conditions") or {}).items():
                    c = self.condition(pid, fig, pan, ck, cv)
                    if c:
                        conds[c["quantity"]] = c
                for a in ("x", "y"):
                    den = ax[a].get("denominator")
                    if den and den.get("quantity"):
                        conds.setdefault(den["quantity"], dict(key_raw=f"{a} denominator", raw=den["symbol"], quantity=den["quantity"], role=L.ENTRIES[den["quantity"]].get("role", ""), value=None, value_max=None, unit="", text=den["symbol"]))
                sa_raw = p.get("series_axis") or ""
                sa_q = ""
                if sa_raw and len(p.get("series") or []) > 1:
                    dim0 = ""
                    for s0 in p.get("series") or []:
                        pv0 = parse_value(s0.get("label") or "")
                        if pv0 and pv0[2].strip() and unit_of(pv0[2]):
                            dim0 = unit_of(pv0[2])["dimension"]; break
                    sa_q, _, why = self.R.quantity(sa_raw, dim0, self.defs)
                    if why.startswith("definition:"):
                        why = ""
                    kind_only = all(len({MODEL_WORDS[w] for w in re.findall(r"[a-zA-Z]+", (s0.get("label") or "").lower()) if w in MODEL_WORDS}) == 1 for s0 in p.get("series") or []) \
                        or bool(re.search(r"\b(type|kind|model|dataset|method)\s*$", sa_raw.strip().lower()))   # an axis that names a category ('sticking coefficient type'), not a quantity
                    if not sa_q and not kind_only:                                  # a series axis over kinds ('model', 'type': fitted vs measured) names no quantity
                        self.unm(pid, fig, pan, "series_axis", sa_raw, f"label_unresolved: {why}")
                curves = []
                n_imp = 0
                cwords = {MODEL_WORDS[w] for w in re.findall(r"[a-zA-Z]+", (p.get("content") or "").lower()) if w in MODEL_WORDS}
                if not cwords:                                                  # else the caption's first sentence ('Simulated saturation profiles ...')
                    head = re.sub(r"^\s*(fig(?:ure)?\.?|scheme)\s*\d+[.:]?\s*", "", f.get("caption") or "", flags=re.I).split(". ")[0]   # the caption's first sentence, its figure label stripped
                    cwords = {MODEL_WORDS[w] for w in re.findall(r"[a-zA-Z]+", head.lower()) if w in MODEL_WORDS}
                panel_kind = next(iter(cwords)) if len(cwords) == 1 else ""      # P87: a panel whose content line (else its caption) says simulated, not measured, holds simulated series
                for n, s in enumerate(p.get("series") or [], 1):
                    if not s["points"]:
                        continue
                    lab = self.series_label(pid, fig, pan, s["label"], sa_q)
                    pts = [[self.to_canonical(x, ax["x"]), self.to_canonical(y, ax["y"])] for x, y in s["points"]]
                    kind = "simulated" if (lab.get("kind") or panel_kind) == "simulated" else "read_from_figure"
                    cconds = dict(conds)
                    if lab["cls"] == "numeric" and lab.get("quantity"):
                        cconds[lab["quantity"]] = dict(key_raw=sa_raw, raw=lab["label_raw"], quantity=lab["quantity"], role=L.ENTRIES[lab["quantity"]].get("role", ""),
                                                      value=lab["value"], value_max=lab.get("value_max"), unit=lab.get("unit", ""), from_series_label=True)
                    xr = (max(x for x, _ in pts) - min(x for x, _ in pts)) or 1.0
                    yr = (max(y for _, y in pts) - min(y for _, y in pts)) or 1.0
                    cid = f"{eid}#c{n}"
                    curves.append(dict(id=cid, figure=fig, panel=pan, series=lab, x=dict(quantity=ax["x"]["quantity"], unit=ax["x"]["unit"], transform=ax["x"]["transform"], label_raw=ax["x"]["label_raw"], unit_raw=ax["x"]["unit_raw"], definition=ax["x"].get("definition", ""), definition_note=ax["x"].get("definition_note", "")),
                                       y=dict(quantity=ax["y"]["quantity"], unit=ax["y"]["unit"], transform=ax["y"]["transform"], label_raw=ax["y"]["label_raw"], unit_raw=ax["y"]["unit_raw"], definition=ax["y"].get("definition", ""), definition_note=ax["y"].get("definition_note", "")),
                                       points=pts, points_raw=s["points"], conditions=cconds, conditions_raw=dict(p.get("conditions") or {}), flags=flags, kind=kind,
                                       uncertainty=dict(basis="digitized" if kind == "read_from_figure" else "", x=0.01 * (max(x for x, _ in pts) - min(x for x, _ in pts)) if ax["x"].get("unit_row") else None,
                                                        y=0.01 * (max(y for _, y in pts) - min(y for _, y in pts))),
                                       set="", provenance=dict(prov, figure=fig, panel=pan)))
                    n_imp += 1
                for c in curves:
                    out["derived"] += self.derive(c)
                sid = ""
                if len(curves) >= 2 and p["panel_type"] in ("plot", "map"):
                    if sa_q:
                        sid = f"{key}:cmp:{pel}"
                        out["sets"].append(dict(id=sid, figure=fig, panel=pan, kind="series", varied=sa_q, varied_raw=sa_raw, members=[c["id"] for c in curves],
                                                conditions={q: c for q, c in conds.items()}, label=f"Fig. {fig}{pan} series" + (f" ({sa_raw})" if sa_raw else "")))
                        for c in curves:
                            c["set"] = sid
                        counts["sets"] += 1
                    elif all(c["series"]["cls"] == "replicate" for c in curves):
                        sid = f"{key}:cmp:{pel}"                                    # P85: replicate labels (samples, runs) form a replicate set, no varied quantity
                        out["sets"].append(dict(id=sid, figure=fig, panel=pan, kind="replicate", varied="", varied_raw=sa_raw, members=[c["id"] for c in curves],
                                                conditions={q: c for q, c in conds.items()}, label=f"Fig. {fig}{pan} replicates" + (f" ({sa_raw})" if sa_raw else "")))
                        for c in curves:
                            c["set"] = sid
                        counts["sets"] += 1
                    else:
                        row["reason"] = "set not formed: series are kinds (model vs measured), no varied quantity" if all(c["series"]["cls"] == "kind" for c in curves) else "set not formed: series_axis unresolved"
                out["curves"] += curves; counts["curves"] += n_imp
                # cells (a map with printed values) and peaks (a spectrum)
                if p.get("cells"):
                    gid = f"{key}:cmp:{pel}:grid"
                    members = []
                    for n, c in enumerate(p["cells"], 1):
                        vid = f"{eid}#v{n}"
                        val = c["value"]
                        num = parse_value(str(val)) if not isinstance(val, (int, float)) else (float(val), None, "")
                        members.append(vid)
                        out["values"].append(dict(id=vid, figure=fig, panel=pan, kind="cell", quantity=sa_q or "", value=(num[0] if num else None), value_text=(str(val) if not num else ""),
                                                  unit=(entry_unit_row(sa_q)["symbol"] if sa_q and entry_unit_row(sa_q) else ""),
                                                  at={ax["x"]["quantity"]: self.to_canonical(c["x"], ax["x"]), ax["y"]["quantity"]: self.to_canonical(c["y"], ax["y"])},
                                                  at_raw=dict(x=c["x"], y=c["y"]), conditions=conds, flags=flags, data_kind="read_from_figure", basis="printed", set=gid, provenance=dict(prov, figure=fig, panel=pan)))
                    out["sets"].append(dict(id=gid, figure=fig, panel=pan, kind="grid", varied=f"{ax['x']['quantity']};{ax['y']['quantity']}", varied_raw=f"{ax['x']['label_raw']} × {ax['y']['label_raw']}",
                                            members=members, conditions=conds, label=f"Fig. {fig}{pan} grid", cell_quantity=sa_q, cell_quantity_raw=sa_raw))
                    counts["cells"] += len(p["cells"]); counts["sets"] += 1
                    if not sa_q and p["cells"] and all(isinstance(c["value"], (int, float)) for c in p["cells"]):
                        self.unm(pid, fig, pan, "cells.quantity", sa_raw or "(no series_axis)", "the printed cell values have no resolved quantity (series_axis)")
                for n, pk in enumerate(p.get("peaks") or [], 1):
                    vid = f"{eid}#k{n}"
                    out["values"].append(dict(id=vid, figure=fig, panel=pan, kind="peak", quantity=ax["x"]["quantity"], value=self.to_canonical(pk["x"], ax["x"]), value_raw=pk["x"],
                                              unit=ax["x"]["unit"], label=pk.get("label", ""), conditions=conds, flags=flags, data_kind="read_from_figure", basis="printed", set="", provenance=dict(prov, figure=fig, panel=pan)))
                    counts["peaks"] += 1
                inv["status"] = "imported"
                row.update(outcome="imported", reason=row["reason"] or f"{n_imp} curves, {len(p.get('cells') or [])} cells, {len(p.get('peaks') or [])} peaks" + (f", set {sid}" if sid else ""))
        counts["derived"] = len(out["derived"]); counts["unmapped"] = sum(1 for u in self.unmapped if u["paper"] == pid)
        counts["resolved_p89"] = len(self.R.p89_hits); out["p89"] = [dict(label=l, quantity=q, note=n, definition=f) for l, (q, n, f) in self.R.p89_hits]
        out["report"] = dict(counts)
        (HERE / f"{pid}.figures.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return out

    def derive(self, c):
        """P86: the three derived scalars of one curve, as records with method and source."""
        out = []
        xq, yq = c["x"]["quantity"], c["y"]["quantity"]
        pts = sorted(c["points"])
        def canon(v, q, from_unit):                                             # P91b: a derived value in its quantity's canonical unit, never a source axis's
            tgt = entry_unit_row(q); src = UNIT_BY_SYMBOL.get(from_unit) or unit_of(from_unit)
            return (convert(v, src, tgt), tgt["symbol"]) if tgt and src and src["dimension"] == tgt["dimension"] else (v, L.ENTRIES[q].get("unit", from_unit))
        xe, ye = L.ENTRIES.get(xq, {}), L.ENTRIES.get(yq, {})
        n = 0
        if xe.get("role") == "coordinate" and yq in PROFILE_Y and len(pts) >= PLATEAU_MIN:
            pl = plateau_of(pts)
            if pl:
                n += 1
                pv, pu = canon(pl[0], yq, c["y"]["unit"])
                out.append(dict(id=f"{c['id'].split('#')[0]}#d{c['id'].split('#c')[1]}_{n}", source=c["id"], quantity=yq, qualifiers="position=plateau", value=pv, unit=pu,
                                method="plateau", rule="P86: mean of the longest run of points within 5 % of the running maximum (at least 4 points)", conditions=c["conditions"], figure=c["figure"], panel=c["panel"]))
                if xe.get("dimension") == "length":
                    hx = half_crossing(pts, pl[0], pl[2])
                    if hx is not None:
                        n += 1
                        hv, hu = canon(hx, "penetration_depth", c["x"]["unit"])
                        out.append(dict(id=f"{c['id'].split('#')[0]}#d{c['id'].split('#c')[1]}_{n}", source=c["id"], quantity="penetration_depth", qualifiers="level=50%", value=hv, unit=hu,
                                        method="half_value_crossing", rule="P86: the x where y first falls below 50 % of the plateau, linear interpolation", conditions=c["conditions"], figure=c["figure"], panel=c["panel"]))
        if yq == "film_thickness" and xq == "cycle_number" and len(pts) >= 4:
            fit = linear_fit(pts)
            if fit and fit[2] >= R2_MIN:
                n += 1
                tgt = entry_unit_row("growth_per_cycle"); yrow = UNIT_BY_SYMBOL.get(c["y"]["unit"])
                slope = fit[0] * (yrow["factor"] / tgt["factor"]) if yrow and tgt else fit[0]
                out.append(dict(id=f"{c['id'].split('#')[0]}#d{c['id'].split('#c')[1]}_{n}", source=c["id"], quantity="growth_per_cycle", qualifiers="", value=slope, unit=tgt["symbol"] if tgt else "",
                                method="linear_slope", rule=f"P86: linear slope of film thickness against cycle number (R² {fit[2]:.3f} ≥ 0.98, {len(pts)} points)", r2=fit[2], conditions=c["conditions"], figure=c["figure"], panel=c["panel"]))
        return out


def write_reports(imp, results):
    """The reports: a subset run replaces its papers' rows and keeps the others'."""
    done = {r["paper_id"] for r in results}
    rp = HERE / "import_report.csv"
    old = [r for r in csv.DictReader(rp.open(encoding="utf-8")) if r["paper_id"] not in done] if rp.exists() else []
    cols = ["paper_id", "key", "data_panels", "imported_panels", "curves", "cells", "peaks", "sets", "derived", "inventory_records", "unmapped", "resolved_p89"]
    rows = [dict(r, **{k: r.get(k, "") for k in cols}) for r in old]
    for r in results:
        c = r["report"]
        rows.append(dict(zip(cols, [r["paper_id"], r["key"], c.get("data_panels", 0), sum(1 for i in r["inventory"] if i["status"] == "imported"), c.get("curves", 0), c.get("cells", 0), c.get("peaks", 0), c.get("sets", 0), c.get("derived", 0), c.get("inventory", 0), c.get("unmapped", 0), c.get("resolved_p89", 0)])))
    rows.sort(key=lambda r: r["paper_id"])
    with rp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows({k: r.get(k, "") for k in cols} for r in rows)
    pp = HERE / "import_panels.csv"
    oldp = [r for r in csv.DictReader(pp.open(encoding="utf-8")) if r["paper"] not in done] if pp.exists() else []
    with pp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "figure", "panel", "panel_type", "verdict", "flags", "outcome", "reason"]); w.writeheader(); w.writerows(sorted(oldp + imp.panels, key=lambda r: (r["paper"], len(r["figure"]), r["figure"], r["panel"])))
    keep = [r for r in csv.DictReader(UNMAPPED.open(newline="", encoding="utf-8")) if r.get("field") == "pilot"] if UNMAPPED.exists() else []   # the pilot's hand rows stay
    done = {r["paper_id"] for r in results}
    old = [r for r in csv.DictReader(UNMAPPED.open(newline="", encoding="utf-8")) if r.get("field") != "pilot" and r["paper"] not in done] if UNMAPPED.exists() else []
    with UNMAPPED.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "figure", "panel", "field", "raw", "reason"]); w.writeheader(); w.writerows(keep + old + imp.unmapped)


def main(argv):
    pids = argv or sorted(p.name for p in FINAL.iterdir() if (p / "figures.json").exists())
    imp = Importer()
    results = [imp.paper(pid) for pid in pids]
    write_reports(imp, results)
    for r in results:
        c = r["report"]
        print(f"{r['paper_id']}: {c.get('data_panels', 0)} data panels, {sum(1 for i in r['inventory'] if i['status'] == 'imported')} imported; {c.get('curves', 0)} curves, {c.get('cells', 0)} cells, {c.get('peaks', 0)} peaks, "
              f"{c.get('sets', 0)} sets, {c.get('derived', 0)} derived, {c.get('inventory', 0)} inventory; {c.get('unmapped', 0)} unmapped; {c.get('resolved_p89', 0)} fields through the paper's definitions (P89)")
    reasons = collections.Counter(u["reason"].split(":")[0] for u in imp.unmapped)
    print(f"unmapped rows {len(imp.unmapped)}: {dict(reasons)}")


if __name__ == "__main__":
    main(sys.argv[1:])
