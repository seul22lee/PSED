#!/usr/bin/env python3
"""P134 compiler: records/<pid>.jsonl -> compiled/<pid>.facts.csv (facts.FIELDS), with .unmapped.csv, .dropped.csv, .coverage.csv,
.experiments.csv (pilot/experiments.py on the compiled tree, for check.py), .compile.log and .summary.csv. No provider call.

    python3 psed_v2/extract/compile.py yli18          # then: python3 psed_v2/pilot/check.py --dir psed_v2/compiled

Input: the groups of pass1_elements.groups(pid); per group the latest pass-1 line of that section name (lines of a name no group has
are ignored); the latest pass-0 line. Steps: a0 resolve_other (P157b: a value held as other or outside the vocabulary, matched to the
generated vocab by its record key, symbols only in their own paper (P157d); never.csv -> unmapped.csv column never; <pid>.promoted.csv), a1 symbol species (P178: a symbol's species from the paper's definition), a schema (form.json), b type rules, c grounding, d quote, e units, f species/structure
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
UNMAPPED_FIELDS = ["element", "field", "id", "label_as_printed", "unit", "candidate", "action", "never", "nearest"]   # P157b: never = the never.csv category; P158: nearest
PROMOTED_FIELDS = ["element", "field", "printed", "meaning", "lookup", "id", "outcome"]    # P157b: step a0; P157d: meaning (the record's definition)
DROPPED_FIELDS = ["element", "step", "field", "reason", "type", "quantity"]
BINDING_FIELDS = ["paper", "panel", "item", "kind", "unit", "unit_fact_id", "origin", "role", "how", "reason", "facts"]   # P184: the compiled unit id
SCOPE_FIELDS = ["paper", "element", "type", "quantity", "key", "value", "where", "recovered"]   # P182: kb/compiled/<pid>.qualifier_scope.csv
SPECIES_FIELDS = ["element", "label", "type", "quantity", "record_species", "definition", "own_element_names", "outcome", "species", "fact_id"]   # P179   # P177c: binding_rows and the item's facts
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


LATEX_SYMBOL = {"approx": "≈", "sim": "~", "gg": "≫", "ll": "≪", "pm": "±", "leq": "≤", "geq": "≥", "le": "≤", "ge": "≥", "cdot": "·"}   # P160


def normalize(t):
    """D10, the one normalization of steps d, e and f: P148 (C3): markup tags removed, their text kept; U+2212 -> -; thin and no-break
    spaces -> space; \\text{..} / \\mathrm{..} -> content; unicode NFKC; μ (U+03BC) and \\mu -> µ (U+00B5); \\circ / ^\\circ -> °;
    \\times -> ×; ◦C / ° C / deg C -> °C (P146); $ _ ^ { } and markdown * dropped; P160 (the ela03 pass-0 quotes): a LaTeX -- / --- and a
    unicode dash -> -, \\approx \\sim \\gg \\ll \\pm \\le(q) \\ge(q) \\cdot -> their symbol, no space around a math symbol, before , . ; : ) % or after
    (, none around °; whitespace collapsed; casefolded (P140 C1)."""
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
    t = re.sub(r"-{2,3}|[‐-―]", "-", t)                              # P160 (A, confirmed): a LaTeX -- / --- and a unicode dash -> -
    t = re.sub(r"\\(approx|sim|gg|ll|pm|leq|geq|le|ge|cdot)(?![a-z])", lambda m: LATEX_SYMBOL[m.group(1)], t)   # P160: a LaTeX relation as printed
    t = re.sub(r"\s*([≈~≫≪±×·≤≥])\s*", r"\1", t)                               # P160: no space around a math symbol (\sim 1 prints ∼1)
    t = re.sub(r"\s*°\s*", "°", re.sub(r"\s+(?=[,.;:)%])|(?<=\()\s+", "", t))   # P160: no space before , . ; : ) % or after (, none around °
    return norm_ws(t).casefold()                                                # P140 C1: casefolded (no unit spelling collides; checked)


_UNIT_KEYS = collections.defaultdict(set)
for _a in list(V.UNIT_BASE) + list(V.UNIT_ALIAS):
    if V.UNIT_ALIAS.get(_a, _a) in V.UNIT_BASE:
        _UNIT_KEYS[normalize(_a)].add(V.UNIT_ALIAS.get(_a, _a))
UNIT_SYMBOL = {k: next(iter(v)) for k, v in _UNIT_KEYS.items() if len(v) == 1}   # P160: a key that names two symbols (L Langmuir, l litre) resolves nothing
UNIT_AMBIGUOUS = {k: sorted(v) for k, v in _UNIT_KEYS.items() if len(v) > 1}


def unit_symbol(u):
    """The canonical spelling of a unit (vocab.UNIT_ALIAS): the spelling itself when units.yaml has it (P160: case kept, L is not l), else
    matched after normalize() unless that key names two symbols (UNIT_AMBIGUOUS); a 'u' prefix reads as µ (D4); None when units.yaml does
    not know it."""
    u_ = str(u).strip()
    if u_ in V.UNIT_BASE or u_ in V.UNIT_ALIAS:
        return V.UNIT_ALIAS.get(u_, u_)
    n = normalize(u)
    return UNIT_SYMBOL.get(n) or UNIT_SYMBOL.get(re.sub(r"^u(?=[A-Za-z])", "µ", n))


def dimless(u):
    """P151 C2: the dimensionless unit ("1", "-", "") is written as an empty unit."""
    return "" if u in ("1", "-", "") else u


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


# P157b: step a0, resolve_other(): a value the ontology did not give the record (quantity other, a species / structure / categorical
# value_text or a method not in the vocabulary) against the generated vocab, of its kind only. Not a unit: a unit spelling stays with
# unit_symbol() (normalize(), D10), which compares it with every units.yaml symbol and variant in step e. P157d: the lookup tables are
# export.resolve_index (ids, names, aliases; never an entry's label) and the symbols, which count only in their own paper.
LIVE = {i: e for i, e in V.ENTRIES.items() if not e["replaced_by"]}
SPECIES_KIND = {"material": "material", "substrate": "material", "reactant_A": "species", "reactant_B": "species", "structure": "structure"}
VALUES = {**V.CATEGORICAL_VALUES, **V.FORM_CATEGORICAL_VALUES}                 # the categoricals with a fixed value list
WORDS, SYMBOLS = C.X.resolve_index(V.ENTRIES, L.MATERIALS)
for _q, _vs in VALUES.items():                                                  # categorical values: the value ids and their value_aliases
    WORDS[f"value:{_q}"] = {}
    for _v, _t, _how in [(v, v, "value id") for v in _vs] + [(v, a, "value alias") for v, al in V.VALUE_ALIASES.get(_q, {}).items() for a in al]:
        WORDS[f"value:{_q}"].setdefault(C.X.norm_label(_t), {}).setdefault(_v, f"{_how} '{_t}'")
    SYMBOLS[f"value:{_q}"] = {}
NEVER, _, NEVER_SYMBOLS = C.X.never_index([dict(id=i, **e) for i, e in LIVE.items()])   # ontology/never.csv: words (any paper), symbols (their paper)
LEGEND_NUMBER = re.compile(r"[-+−]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+−]?\d+)?(?:\s*(?:×|x|\\times)\s*10\s*(?:\^\s*\{?\s*([-+−]?\d+)\s*\}?|([⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)))?")
SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


def vocab_hits(pid, kind, text):
    """The step-a0 lookup (P157b, P157d): {id: how} of a text against the generated vocab of one kind, whole (export.norm_label), and the
    symbols of this paper (export.symbol_key, case kept)."""
    hits = dict(WORDS[kind].get(C.X.norm_label(text), {}))
    for i, t in SYMBOLS[kind].get((pid, C.X.symbol_key(text)), {}).items():
        hits.setdefault(i, f"symbol '{t}' of this paper")
    return hits


def never_of(pid, text):
    """The never.csv row of a record key: a word (any paper, export.norm_label) or a symbol of this paper (export.symbol_key); else None."""
    return (NEVER.get(C.X.norm_label(text)) or NEVER_SYMBOLS.get((pid, C.X.symbol_key(text)))) if text.strip() else None


def resolve_label(pid, text, kind="quantity"):
    """P174 (user): the one resolution path for a label outside a record (a figure's x, y or series axis, a condition key), as step a0
    reads a record key: vocab_hits of one kind on the text whole. One id -> it; two -> other, ambiguous; none -> other, with the never.csv
    category of the text (never_of). Returns dict(id, how, ambiguous, never, never_label)."""
    hits = vocab_hits(pid, kind, text) if text.strip() else {}
    if len(hits) == 1:
        (i, how), = hits.items()
        return dict(id=i, how=how, ambiguous=[], never="", never_label="")
    nv = never_of(pid, text)
    return dict(id="other", how="", ambiguous=sorted(hits), never=nv["category"] if nv else "",
                never_label=(nv["label"] + (f" (symbol in {nv['paper']})" if nv.get("symbol") == "yes" else "")) if nv else "")


def series_axis(pid):
    """P163: {panel: the series_axis label as printed} of the figure stage's ingest/final/<pid>/figures.json (kb/<pid>.figures.json keeps
    it only as a set's varied_raw, and a map's set names its axes instead)."""
    p = C.V2 / "ingest" / "final" / pid / "figures.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {f"fig{f['number']}{x.get('panel', '')}": (x.get("series_axis") or "").strip() for f in d.get("figures", []) for x in f.get("panels") or []}


def legend_number(t):
    """P163: a text that is a number (n, n.n, n e m, n × 10^m, n × 10⁵) and then nothing or a unit units.yaml knows -> (value, unit as
    printed); else None."""
    t = t.strip()
    m = LEGEND_NUMBER.match(t)
    if not m:
        return None
    rest = t[m.end():].strip()
    if rest and unit_symbol(rest) is None:
        return None
    base = float(re.match(r"[-+−]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+−]?\d+)?", m.group(0)).group(0).replace("−", "-"))
    exp = (m.group(1) or (m.group(2) or "").translate(SUPERSCRIPT)).replace("−", "-")
    return (base * 10 ** int(exp) if exp else base), rest


def sep_rx(seps):
    """P177c: a separator list (ontology.yaml legend_separators / axis_separators) as one regex; a leading or trailing space means
    whitespace there (' and ' -> \\s+and\\s+, ',' -> \\s*,\\s*)."""
    return re.compile("|".join((r"\s+" if s[:1].isspace() else r"\s*") + re.escape(s.strip()) + (r"\s+" if s[-1:].isspace() else r"\s*") for s in seps if s.strip()))


SEPARATORS = C.X.separators()                                                   # P177c (user): the layouts' label separators
LEGEND_DASHES = [s for s in SEPARATORS["legend"] if len(s.strip()) == 1 and unicodedata.category(s.strip()) == "Pd"]
LEGEND_SPLIT = sep_rx([s for s in SEPARATORS["legend"] if s not in LEGEND_DASHES])   # P163 ',', P177c '@', ' at ': always
LEGEND_ALL = sep_rx(SEPARATORS["legend"])                                       # P175: with ' - ' / ' – ' when that gives the axis's count
AXIS_SPLIT = sep_rx(SEPARATORS["axis"])                                         # P175: the parts of a two-quantity axis label


def legend_parts(label, rx=LEGEND_SPLIT):
    """P163, P177c: a legend label split at its top-level separators (one inside brackets or braces stays)."""
    parts, last = [], 0
    for m in rx.finditer(label):
        pre = label[:m.start()]
        if sum(map(pre.count, "([{")) == sum(map(pre.count, ")]}")):
            parts.append(label[last:m.start()])
            last = m.end()
    return [p.strip() for p in parts + [label[last:]] if p.strip()]


RANGE = re.compile(r"(.+?)\s*=\s*([-+−]?(?:\d+\.?\d*|\.\d+))\s*to\s*([-+−]?(?:\d+\.?\d*|\.\d+))\s*(.*)")
QUALIFIER_AXES = ("element", "species", "step")                                 # P175 (user): an axis naming one of these qualifiers


def axis_parts(axis):
    """P175 (user): an axis label's quantity parts, split at ' and ' and at top-level commas ('power and pulse time' -> power, pulse time)."""
    return [x.strip() for x in AXIS_SPLIT.split(axis or "") if x.strip()]


def qualifier_key(axis):
    """P175 (user): the qualifier key an axis label names whole (element, species, step), else ''."""
    k = C.X.norm_label(axis or "")
    return k if k in QUALIFIER_AXES else ""


def qualifier_value(pid, key, part):
    """P175: a legend part as a value of the qualifier key: an element symbol (element), a species id of lists.QUALIFIERS (species, via the
    species vocab), a step of lists.QUALIFIERS (step); else ''."""
    name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", part).strip()
    if key == "element":
        return name if re.fullmatch(r"[A-Z][a-z]?", name) else ""
    if key == "species":
        hit = vocab_hits(pid, "species", name)
        return next(iter(hit)) if len(hit) == 1 and next(iter(hit)) in (L.QUALIFIERS.get("species") or set()) else ""
    return name if name in (L.QUALIFIERS.get(key) or set()) else ""


DATA_ROLE_WORDS = {"simulation": "simulated", "simulations": "simulated", "simulated": "simulated", "calculated": "simulated", "calculation": "simulated",
                   "theory": "simulated", "numerical": "simulated", "fit": "fitted", "fits": "fitted", "fitted": "fitted", "fitting": "fitted",
                   "measured": "measured", "measurement": "measured", "experimental": "measured", "experiment": "measured", "data": "measured"}
DATA_ROLE_FILLER = {"result", "results", "line", "lines", "linear", "curve", "curves", "values", "points", "of", "the"}
IMAGE_TYPES = ("micrograph", "photo", "table_image")
ITEM_ROLES = {"simulated": ("model_run",), "measured": ("run", "specimen")}       # P177b: the units an explicitly marked item may bind to


def data_role_word(part):
    """P177b: the data role a legend part names when its words are data-role words only ('Simulation', 'Fitting result', 'Linear Fits',
    'measured'): simulated | fitted | measured; else ''."""
    ws = re.findall(r"[A-Za-z]+", (part or "").lower())
    roles = [DATA_ROLE_WORDS[w] for w in ws if w in DATA_ROLE_WORDS]
    return roles[0] if roles and all(w in DATA_ROLE_WORDS or w in DATA_ROLE_FILLER for w in ws) else ""


def parse_legend(pid, label, axis):
    """P163 rule 1, P175, P177b, P177c (user): a legend label's parts (legend_parts at its top-level legend separators of ontology.yaml:
    ',', '@', ' at '; an axis of two or more parts (axis separators ' and ', ',') pairs with them by order, the legend split at the dash
    separators ' - ' / ' – ' too when the others do not give that count), each resolved on the one path and classed by the kind of what it
    resolved to:
      value     '<symbol> = <number> [unit]', '<name>: <number> [unit]', '<number> [unit]', '<symbol> = <a> to <b> [unit]' (value_min /
                value_max): the quantity of its own symbol or name, else of its axis part (vocab_hits, as step a0); unresolved: other;
      species   a species name on a material / reactant axis; name: a structure or categorical value;
      qualifier a value of the qualifier the axis names (element, species, step): no unit boundary, on the item's result;
      quantity  the part names a quantity entry, no number: the item's y quantity (no unit boundary);
      model     the part names a model entry (name, alias, a symbol of this paper): the item is a model run of that model;
      role      data-role words only (Simulation, Fit, Fitting result, measured): the item's data role (no unit boundary);
      method    measurement-method words (legend_methods: SE, XRR, EDS): the method of the item's result; the rest of the part is classed again;
      never     a never.csv word (or a symbol of this paper): a never condition (kept, no candidate);
      other     none of these: an other condition (a candidate).
    Returns [dict(kind, key, quantity, value, value_min, value_max, unit, value_text, qualifier, model, method, role, how, flag)]."""
    parts = legend_parts(label)
    aparts = axis_parts(axis)
    if len(aparts) >= 2 and len(parts) != len(aparts):
        dash = legend_parts(label, LEGEND_ALL)
        parts = dash if len(dash) == len(aparts) else parts
    paired = len(aparts) >= 2 and len(parts) == len(aparts)
    qk = qualifier_key(axis)
    out = []
    for n, part in enumerate(parts):
        out += classify_part(pid, part, aparts[n] if paired else axis, qk, len(parts) == 1 or paired, axis)
    return out


def classify_part(pid, part, ax_, qk, one, axis, methods=True):
    """P177b: one legend part classed (parse_legend)."""
    if qk:
        v = qualifier_value(pid, qk, part)
        return [dict(kind="qualifier", key=part, qualifier=qk, value_text=v, quantity="",
                     how=f"axis '{axis}' names the qualifier {qk}: {qk}={v}" if v else f"axis '{axis}' names the qualifier {qk}; '{part}' is none of its values",
                     **({} if v else dict(flag="legend part no value of the axis's qualifier")))]
    ax = vocab_hits(pid, "quantity", ax_) if ax_ else {}
    axis_q = next(iter(ax)) if len(ax) == 1 else ""
    rg = RANGE.fullmatch(part)
    if rg and (not rg.group(4).strip() or unit_symbol(rg.group(4).strip()) is not None):
        sym = rg.group(1).strip()
        hit = vocab_hits(pid, "quantity", sym)
        q, how = next(iter(hit.items())) if len(hit) == 1 else ("other", f"unresolved: other condition '{sym}'")
        lo, hi = (float(x.replace("−", "-")) for x in (rg.group(2), rg.group(3)))
        return [dict(kind="value", key=sym, value=None, value_min=lo, value_max=hi, unit=rg.group(4).strip(), quantity=q,
                     how=f"range of '{sym}' -> {q} ({how})" if len(hit) == 1 else how)]
    m = re.fullmatch(r"(.+?)\s*[=:]\s*(.+)", part)
    sym, num = (m.group(1).strip(), legend_number(m.group(2))) if m and legend_number(m.group(2)) else ("", legend_number(part))
    if num:
        keys = ([sym] if sym else []) + ([ax_] if ax_ and (one or not sym) else [])
        keys = keys[::-1] if one and not sym else keys
        found = [(k, h) for k in keys for h in [vocab_hits(pid, "quantity", k)] if len(h) == 1]
        hit = next(((k, h) for k, h in found if unit_fits(next(iter(h)), num[1])), None)   # P177c (user, chat): the dimension guard
        key = hit[0] if hit else sym or part if found else (ax_ if ax_ and (one or not sym) else sym or part)
        q, how = (next(iter(hit[1].items())) if hit else ("other", f"unresolved: other condition '{key}'" + (
            f" ('{found[0][0]}' names {next(iter(found[0][1]))}, whose dimension the unit '{num[1]}' does not have)" if found else "")))
        return [dict(kind="value", key=key, value=num[0], unit=num[1], quantity=q,
                     how=how if hit is None else f"{'series_axis' if key == ax_ else 'symbol / name'} '{key}' -> {q} ({how})")]
    name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", part).strip() or part
    mh = vocab_hits(pid, "model", name)
    if len(mh) == 1:
        (i, h), = mh.items()
        return [dict(kind="model", key=part, model=i, quantity="", how=f"names the model {i} ({h})")]
    dr = data_role_word(part)
    if dr:
        return [dict(kind="role", key=part, role=dr, quantity="", how=f"data-role words: {dr}")]
    ms = legend_methods(pid, part) if methods else {}
    if ms:
        rest = part
        for w in ms.values():
            rest = re.sub(rf"(?i)(?<!\w){re.escape(w)}(?!\w)", " ", rest)
        rest = " ".join(rest.split()).strip(" ,;-–")
        return [dict(kind="method", key=w, method=mi, quantity="", how=f"names the method {mi}") for mi, w in ms.items()] \
            + (classify_part(pid, rest, ax_, qk, one, axis, methods=False) if rest else [])
    sp = vocab_hits(pid, SPECIES_KIND[axis_q], name) if axis_q in SPECIES_KIND else {}
    if len(sp) == 1:
        (i, h), = sp.items()
        return [dict(kind="species", key=part, value_text=i, quantity=axis_q, how=f"name '{name}' on the {axis_q} axis -> {i} ({h})")]
    if not ax_:                                                                 # P177b: a species name with no axis: the species qualifier
        sq = vocab_hits(pid, "species", name)
        if len(sq) == 1 and next(iter(sq)) in (L.QUALIFIERS.get("species") or set()):
            (i, h), = sq.items()
            return [dict(kind="qualifier", key=part, qualifier="species", value_text=i, quantity="", how=f"a species name, no axis: species={i} ({h})")]
    hits = {(k_ if k_ == "structure" else k_[6:], i): h for k_ in ["structure"] + [f"value:{q}" for q in VALUES] for i, h in vocab_hits(pid, k_, name).items()}
    if len(hits) == 1:
        ((q, i), h), = hits.items()
        return [dict(kind="name", key=part, value_text=i, quantity=q, how=f"name '{name}' -> {q} = {i} ({h})")]
    qh = vocab_hits(pid, "quantity", name)
    if len(qh) == 1:
        (i, h), = qh.items()
        return [dict(kind="quantity", key=part, quantity=i, how=f"names the quantity {i} ({h})")]
    nv = never_of(pid, name) or never_of(pid, part)
    if nv:
        return [dict(kind="never", key=part, quantity="other", never=nv["category"], how=f"never.csv: {nv['label']} ({nv['category']})")]
    return [dict(kind="other", key=part, quantity="other", how="parsed to nothing" + (f" (names {sorted(hits)})" if hits else ""), flag="legend label parsed to nothing")]


def unit_fits(q, unit):
    """P177c (user, chat): a legend number may take quantity q when its unit is empty or unknown to units.yaml, or has q's dimension
    (vocab.UNIT_BASE against vocab.ENTRIES; a count reads as dimensionless; q with no dimension: no evidence, it fits). A number with a
    unit never takes a categorical quantity ('Thermal ALD@150°C' on the axis 'ALD process' = process_mode: 150 °C stays other)."""
    s = unit_symbol(unit) if unit else None
    qd = V.ENTRIES.get(q, {}).get("dimension")
    if s is None or s not in V.UNIT_BASE or not qd:
        return True
    d = lambda x: "dimensionless" if x == "count" else x                      # noqa: E731
    return d(V.UNIT_BASE[s][0]) == d(qd)


def legend_methods(pid, label):
    """P166: the measurement method entries (vocab.METHOD_MEASUREMENT: simulation, calculation, cited, schematic and tabulated are none) a
    legend label names: one, two or three consecutive words of it (split at spaces and punctuation), or the whole label, resolved by
    vocab_hits (kind method) -> {method id: the words}."""
    ws = [w for w in re.split(r"[\s,;/()\[\]]+", label or "") if w]
    found = {}
    for t in [label or ""] + [" ".join(ws[i:i + n]) for n in (3, 2, 1) for i in range(len(ws) - n + 1)]:
        for m in vocab_hits(pid, "method", t) if t.strip() else {}:
            if V.METHOD_MEASUREMENT.get(m, True):
                found.setdefault(m, t)
    return found


def species_named(pid, label):
    """P177c: the species entries a label names: the whole label, or one, two or three consecutive words of it (split as legend_methods
    splits), resolved by vocab_hits (kind species) -> {species id: the words}."""
    ws = [w for w in re.split(r"[\s,;/()\[\]]+", label or "") if w]
    found = {}
    for t in [label or ""] + [" ".join(ws[i:i + n]) for n in (3, 2, 1) for i in range(len(ws) - n + 1)]:
        for s in vocab_hits(pid, "species", t) if t.strip() else {}:
            found.setdefault(s, t)
    return found


SYMBOL_TYPES = ("model", "definition", "cited", "derived")                       # P182 (user): the record types the symbol-species step reads
SPECIES_EVIDENCED = ("kept: its own element names it", "backed by the definition", "from the definition", "corrected from the definition")   # P179c
UNNAMED_REACTANT = re.compile(r"\b(?i:reactants?|precursors?)\s+([A-Z])\b")    # P179 (user): a reactant presented unnamed ('reactant A')
SUBSCRIPT = re.compile(r"^[^_]+_\{?(.+?)\}?$")                                  # P178: a symbol's subscript (p_B -> B, c_{TMA} -> TMA)
CELL_ID = re.compile(r"^(tab\w*?)\.r(\d+)c(\d+)$")                              # a table cell id: table, row, column
PROCESS_MODE_PASS = "0pm"                                                        # P179: the records line of the process_mode fill (process_mode_fill.py)
RECIPE_FILL_PASS = "0rf"                                                         # P181: the records line of the recipe fill (the four recipe fields)
FILL_PASSES = (PROCESS_MODE_PASS, RECIPE_FILL_PASS)
EXTEND_PASS = "0x"                                                               # P184: the records line of the pass-0 extension (pass0_extend.py)


VALUE_ENTRIES = {i for i, e in V.ENTRIES.items() if e["type"] in ("quantity", "categorical")}


def out_of_scope(quantity, key):
    """P182 (user): whether a qualifier key may not sit on a fact of this quantity (vocab.QUALIFIER_SCOPE, from ontology.yaml applies_to):
    a fact without a quantity is no value fact (never); an any key or an unknown one (form.json judges it): never; a unit key: always; a
    key with entries: when the quantity is a value entry outside them (other, a list of quantities: no single entry, not checked)."""
    sc = V.QUALIFIER_SCOPE.get(key)
    if not quantity or not isinstance(quantity, str) or sc in ("any", None):
        return False
    return sc == "unit" or (quantity in VALUE_ENTRIES and quantity not in sc)


def recipe_fill(pid, lines=None):
    """P179, P181: the latest fill line of the pass-0 units (process_mode fill or recipe fill) as {unit id: {field, field_quote,
    field_element}} for export.RECIPE_FIELDS (a process_mode fill holds process_mode with quote and element). P182 (user): the importer's
    contract: a value whose quote is null or not found (quote_found, the record's element as its own text) is set to null and listed;
    a quote found across elements gets them all as its element (';'-separated). Then a user's recipe decision (history.csv kind
    recipe_field, the paper in source_pids: id = the field, target = the value or null, parameters = the run ids, empty = every run of
    the fill) sets the field, listed. -> (line number, fields, [listed: run, field, value, reason])."""
    lines = C.lines(pid) if lines is None else lines
    fl = [i for i, x in enumerate(lines, 1) if x["pass"] in FILL_PASSES]
    n = max(fl, default=None)
    if n is None:
        return None, {}, []
    out, listed, text = {}, [], C.E.texts(pid)
    for x in [y for i in fl for y in (C.loads_json(lines[i - 1]["response"]).get("recipes") or [])]:   # P185: every fill line in order; a later
        if isinstance(x, dict) and x.get("id"):                                    # line's field replaces an earlier one (a material-only refill)
            f_ = out.setdefault(x["id"], {})
            for f in C.X.RECIPE_FIELDS:
                if f in x:
                    legacy = f == "process_mode" and f + "_quote" not in x
                    v, q, e = x.get(f), x.get("quote") if legacy else x.get(f + "_quote"), x.get("element") if legacy else x.get(f + "_element")
                    if v:
                        how, els = quote_found(pid, q, normalize(text.get(e or "", "")), e)
                        if not how:
                            listed.append(dict(run=x["id"], field=f, value=v, reason="quote null" if not (q or "").strip() else f"quote not found ({e or 'no element'})"))
                            v = q = e = None
                        elif how == "span":
                            e = ";".join(els)
                    f_.update({f: v, f + "_quote": q, f + "_element": e})
    hist = C.V2 / "ontology" / "history.csv"
    for h in (csv.DictReader(hist.open(encoding="utf-8")) if hist.exists() else []):
        if h["kind"] != "recipe_field" or pid not in h["source_pids"].split(";") or h["id"] not in C.X.RECIPE_FIELDS:
            continue
        v = None if h["target"] in ("", "null") else h["target"]
        for run in [r for r in h["parameters"].split(";") if r] or list(out):
            if run in out:
                listed.append(dict(run=run, field=h["id"], value=out[run].get(h["id"]), reason=f"the user's recipe decision (history.csv, {h['date']}): {v or 'null'}"))
                out[run].update({h["id"]: v, h["id"] + "_quote": None, h["id"] + "_element": None})
    return n, out, listed


def pass0_object(pid, n0=None, lines=None):
    """P185: the pass-0 object (line n0, else the latest pass-0 line) with the latest pass-0 extension's new units added (P184, records
    pass EXTEND_PASS; a unit whose id the pass-0 line holds is left out) -> (line number, object, extension line number or None)."""
    lines = C.lines(pid) if lines is None else lines
    n0 = n0 or max(i for i, x in enumerate(lines, 1) if x["pass"] == 0)
    obj = C.loads_json(lines[n0 - 1]["response"])
    nx = max((i for i, x in enumerate(lines, 1) if x["pass"] == EXTEND_PASS), default=None)
    if nx and isinstance(obj, dict):
        have = {u.get("id") for u in obj.get("units") or [] if isinstance(u, dict)}
        new = [u for u in C.loads_json(lines[nx - 1]["response"]).get("units") or [] if isinstance(u, dict) and u.get("id") and u["id"] not in have]
        obj = {**obj, "units": list(obj.get("units") or []) + new}
    return n0, obj, nx


_PAPER_TEXT = {}


def paper_text(pid):
    """P182 (user, b): the paper's elements in element order (elements.load), each normalize()d, joined by one space -> (text,
    [(start, end, element id)])."""
    if pid not in _PAPER_TEXT:
        text, parts, spans, i = C.E.texts(pid), [], [], 0
        for r in C.E.load(pid):
            t = normalize(text.get(r["element_id"], ""))
            if t:
                spans.append((i, i + len(t), r["element_id"]))
                parts.append(t)
                i += len(t) + 1
        _PAPER_TEXT[pid] = (" ".join(parts), spans)
    return _PAPER_TEXT[pid]


def quote_found(pid, quote, own="", eid=None):
    """P182 (user, b): the one quote check of compile step d and of the recipe-fill importer. The quote normalize()d; own = the
    normalized texts it is checked against first (step d: scope(); the importer: the element it names). Found in own: 'own' (contiguous)
    or 'own_in_order' (P140 C1: every token in order, gaps allowed) -> [eid]; else a substring of the paper's elements concatenated in
    element order (paper_text): 'span' -> every element the occurrence spans (the first occurrence touching eid, else the first);
    else ('', [])."""
    q = normalize(quote or "")
    if not q:
        return "", []
    if q in own:
        return "own", [eid] if eid else []
    if in_order(q.split(), own):
        return "own_in_order", [eid] if eid else []
    t, spans = paper_text(pid)
    occ = [m.start() for m in re.finditer(re.escape(q), t)]
    if not occ:
        return "", []
    hit = [[e for a, b, e in spans if a < o + len(q) and b > o] for o in occ]
    return "span", next((h for h in hit if eid in h), hit[0])
FORM_VERSIONS = C.V2 / "ontology" / "form_versions.csv"                          # P179b (user): the form versions compile reads


def line_version(x):
    """P179b: a records line's form version; 'none' for a line written before the freeze (no form_version field)."""
    return x.get("form_version") or "none"


def accepted_versions(key):
    """P179b (user): the form versions whose pass-1 lines compile reads for a paper (key): status accepted in ontology/form_versions.csv
    for that paper (a row with its key), else for every paper (a row with no paper)."""
    rows = list(csv.DictReader(x for x in FORM_VERSIONS.open(encoding="utf-8") if not x.startswith("#"))) if FORM_VERSIONS.exists() else []   # P179c: # = the header
    st = {r["version"]: r["status"] for r in rows if not r["paper"]}
    st.update({r["version"]: r["status"] for r in rows if r["paper"] == key})
    return {v for v, x in st.items() if x == "accepted"}
PURGE_QUANTITIES = ("purge_time",)                                              # P177c: of form rule 1's step quantities (export.STEP_QUANTITIES)
#                                                                                 a purge time names its half-cycle's purge, a pulse time or an exposure its dose
CONDITION_KINDS = ("value", "name", "species", "other", "never")


def cond_key(c):
    """P177b: a condition as a comparable key: (quantity, canonical value or value range or text); an other or never condition by its
    label and printed value. None for a part that is no condition."""
    if c["kind"] not in CONDITION_KINDS:
        return None
    if c["kind"] in ("other", "never") or c.get("quantity") in ("", "other"):
        return ("other", C.X.norm_label(c["key"]), str(c.get("value", "")), str(c.get("value_min", "")), str(c.get("value_max", "")), c.get("unit") or "")
    if c["kind"] in ("name", "species"):
        return (c["quantity"], "text", str(c.get("value_text", "")).casefold())
    if c.get("value") is None:
        return (c["quantity"], "range", c.get("value_min"), c.get("value_max"), c.get("unit") or "")
    k = canon(dict(value=num_text(c["value"]), unit=dimless(unit_symbol(c.get("unit") or "") or (c.get("unit") or "")), quantity=c["quantity"]))
    return (c["quantity"], "value", k)


def same_value(a, b):
    """P177b: two condition keys equal: numbers within 0.1 % (canonical units), else equal."""
    if a[:2] != b[:2]:
        return False
    if a[1] == "value" and isinstance(a[2], tuple) and isinstance(b[2], tuple) and len(a[2]) == 2 and len(b[2]) == 2 and a[2][0] == b[2][0]:
        x, y = a[2][1], b[2][1]
        return isinstance(x, float) and isinstance(y, float) and abs(x - y) <= 1e-3 * max(abs(x), abs(y), 1e-300)
    return a == b


def unit_vectors(pid, units, recs):
    """P177b: {pass-0 unit id: [condition keys]}: the pass-1 settings (and valued model inputs) about it, the quantity its id or, for
    other, the record key resolved by vocab_hits; a specimen inherits its run's, a model run its simulation's."""
    own = collections.defaultdict(list)
    for r in recs or []:
        rec = r["rec"]
        if r.get("origin") or rec.get("type") not in ("setting", "model") or not isinstance(rec.get("about"), str):
            continue
        q = rec.get("quantity") if isinstance(rec.get("quantity"), str) else ""
        if q in ("", "other"):
            h = vocab_hits(pid, "quantity", C.X.record_text(rec)) if C.X.record_text(rec).strip() else {}
            q = next(iter(h)) if len(h) == 1 else ""
        if not q or q not in L.QUANTITIES:
            continue
        if rec.get("value") not in (None, ""):
            c = dict(kind="value", key="", quantity=q, value=rec["value"], unit=rec.get("unit") or "")
        elif isinstance(rec.get("value_text"), str) and rec["value_text"]:
            c = dict(kind="name", key="", quantity=q, value_text=categorical(q, rec["value_text"]) or rec["value_text"])
        else:
            continue
        try:
            own[rec["about"]].append(cond_key(c))
        except (TypeError, ValueError):
            continue
    by = {u["id"]: u for u in units}
    out = {}
    for u in units:
        ks = list(own.get(u["id"], []))
        if u.get("parent") in by:
            ks += own.get(u["parent"], [])
        out[u["id"]] = ks
    return out


def figure_caption_images(pid):
    """P177b: {figure number: the crop file(s) of the figure stage} (ingest/final/<pid>/structure.json captions)."""
    p = C.V2 / "ingest" / "final" / pid / "structure.json"
    st = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {str(c.get("number")): [str(x.get("file") if isinstance(x, dict) else x) for x in c.get("images") or []] for c in st.get("captions", []) if c.get("kind") == "figure"}


def bind(pid, obj, recs=None):
    """P177b (user): the one binding rule; it replaces curve_units, panel_items, legend_conditions, method_panels, the P161 / P162 / P176
    role rules and the unit merge. Per figure-stage panel (ingest/final/<pid>/figures.json) with its pass-0 layout (ontology.yaml layouts:):
    a. items: a schematic none, no flag; an image panel (micrograph, photo, table_image, a map with no items) one image item (the crop);
       a data panel with no curve, cell or peak one panel item; else per the layout: curve_per_unit its curves, point_per_unit its cells
       (a map with cells) else the points of its curves, panel_one_unit the panel (its curves, cells and peaks are its results); a peak
       outside a panel_one_unit panel an item of its own. No layout -> its items unbound 'no layout'; a layout other -> 'layout other'.
    b. each item's vector: its curve's legend parts (parse_legend); a point or cell adds its coordinates (the x / y axis quantities).
       Values, structure, species and categorical values and other parts are conditions; a qualifier, a quantity name, a method, a
       data-role word and a model name are no unit boundary; a never part is a never condition (kept, never matched on).
    c. the unit: a pass-0 unit whose data names the item (pass 0's own binding; a point is never named by its curve); a panel or image
       item: the layout's unit, else the one unit whose data names an item of the panel, else whose introduced_in names the panel, else
       the figure; a model-name item: a model run under the simulation linked to that model (created when the paper has none); else the
       one pass-0 run, specimen or model run (a simulated item: model runs; a measured one: runs and specimens) whose conditions (unit_
       vectors) contain every resolved condition of the vector (an item with an other condition matches none), among the units the figure
       names when it names any, an ancestor giving way to its descendant; several -> unbound 'ambiguous: ids'; none -> a point at x = 0
       unbound 'origin' (P177c, user), else a derived unit:
       role model_run for an explicit simulated or fit mark (or a model name), else run (runs only) / model_run (a simulation only), else
       null flagged 'role unresolved'; a panel item a specimen (measured) or a model run; parent the model's simulation, else the single
       simulation (a model run) or the single run (a specimen), else null flagged 'parent unresolved'; one unit per (role, model, vector)
       within a panel (across panels a legend repeats for runs that differ in what the caption states). An image item or an empty data panel gets no derived unit: unbound 'no unit named'.
    d. results: Run.figures (a curve its y quantity or the legend's quantity; a point or cell its value; an image a measurement).
    e. invariant: every item bound to exactly one unit or unbound with its reason (binding_check); the gate counts the unbound.
    recs: compile's records (the pass-1 settings give the pass-0 units' conditions); None before pass 1 (no vector match).
    Returns dict(items, units: the derived units, panels: {panel: dict(kind, layout, items, flags)}, refs_unknown)."""
    key = C.E.PAPERS.get(pid, pid)
    obj = obj if isinstance(obj, dict) else {}
    units = [u for u in obj.get("units") or [] if isinstance(u, dict) and u.get("id")]
    by = {u["id"]: u for u in units}
    p = C.V2 / "kb" / f"{pid}.figures.json"
    Fj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    q_ = C.V2 / "ingest" / "final" / pid / "figures.json"
    ing = json.loads(q_.read_text(encoding="utf-8")) if q_.exists() else {"figures": []}
    lays = {x["panel"]: x for x in obj.get("panel_layouts") or [] if isinstance(x, dict) and x.get("panel")}
    ids, axes, crops = set(C.E.texts(pid)), series_axis(pid), figure_caption_images(pid)
    holders = collections.defaultdict(list)
    for u in units:
        for d in u.get("data") or []:
            holders[d.get("id") if isinstance(d, dict) else d].append((u["id"], d.get("role") if isinstance(d, dict) else None))
    known = {x.get("id") for sec in ("curves", "values", "sets", "derived") for x in Fj.get(sec) or []}
    refs_unknown = [(u, i) for i, us in holders.items() if i not in known for u, _ in us]
    vecs = unit_vectors(pid, units, recs) if recs is not None else {}
    sims, runs = [u["id"] for u in units if u.get("role") == "simulation"], [u["id"] for u in units if u.get("role") == "run"]
    sim_model = {}
    for s in sims:
        mh = vocab_hits(pid, "model", (by[s].get("name_as_printed") or "").strip())
        if len(mh) == 1:
            sim_model.setdefault(next(iter(mh)), s)
    named = collections.defaultdict(set)
    for u in units:
        for e in u.get("introduced_in") or []:
            named[e].add(u["id"])
    items, derived, dkey, panels = [], [], {}, {}

    def leaves(cands):
        return {c for c in cands if not any(by.get(o, {}).get("parent") == c for o in cands)}

    def panel_unit(pel, fig, pitems):
        pel = pel.split("~")[0]                                                 # a repeated panel id: its own id for the lookups
        lay = lays.get(pel) or {}
        if lay.get("unit") in by:
            return lay["unit"], "the layout's unit", ""
        refs = {u for x in pitems for u, _ in holders.get(x, [])}
        if len(refs) == 1:
            return next(iter(refs)), "pass-0 data", ""
        for level in ([pel], [f"fig{fig}", f"fig{fig}.cap"]):
            c = leaves({u for e in level for u in named.get(e, set())})
            if len(c) == 1:
                return next(iter(c)), f"introduced_in names {'the panel' if level == [pel] else 'the figure'}", ""
            if c:
                return "", "", "ambiguous: " + ", ".join(sorted(c))
        return "", "", "no unit named"

    def derive(it, role, parent, flags, layout, label, fig, role_from):
        conds = [c for c in it["vector"] if c["kind"] in CONDITION_KINDS]
        ks = tuple(sorted(str(cond_key(c)) for c in conds))
        k = (role, it.get("model") or "", it["panel"], ks or "empty")          # one unit per role and vector within a panel (P177b: across
        #                                                                         panels a legend repeats for runs that differ in the caption)
        uid = f"{pid}:{it['panel']}:{it['ref'].split('#')[-1].replace(':', '_')}"
        if k in dkey:                                                           # one unit per vector: the item's own id is its alias (pass 1 may
            u = dkey[k]                                                         # name it; compile maps an alias to the unit's row)
            u["data"].append(dict(id=it["ref"], role=it["data_role"] or None))
            if uid != u["id"] and uid not in u["aliases"]:
                u["aliases"].append(uid)
            return u["id"]
        cap = f"fig{fig}.cap"
        u = dict(id=uid, parent=parent, name_as_printed=label or None, role=role,
                 structure_class=None, specimen_class=None, experiment_kind=None, introduced_in=[cap] if cap in ids else [],
                 data=[dict(id=it["ref"], role=it["data_role"] or None)], evidence_quote=label or None, origin=f"derived: {layout or 'none'}",
                 conditions=conds, series_axis=axes.get(it["panel"], ""), panel=it["panel"], curve=it["ref"], y=it.get("y") or "", role_from=role_from,
                 flag="; ".join(flags), aliases=[], model=it.get("model") or "")
        dkey[k] = u
        derived.append(u)
        return u["id"]

    def role_of(it):
        if it.get("model"):
            return "model_run", f"names the model {it['model']}"
        if it["data_role"] in ("simulated", "fitted"):
            return "model_run", f"figure stage or legend: {it['data_role']}"
        if runs and not sims:
            return "run", "unit list: runs, no simulation"
        if sims and not runs:
            return "model_run", "unit list: a simulation, no runs"
        return None, ""

    def parent_of(role, it):
        if role == "model_run":
            if it.get("model"):
                if it["model"] not in sim_model:                               # the paper has no simulation of this model: one derived
                    sid = f"{pid}:sim:{it['model']}"
                    derived.append(dict(id=sid, parent=None, name_as_printed=V.ENTRIES.get(it["model"], {}).get("name") or it["model"], role="simulation",
                                        structure_class=None, specimen_class=None, experiment_kind=None, introduced_in=[], data=[], evidence_quote=None,
                                        origin="derived: model name", conditions=[], series_axis="", panel=it["panel"], curve="", y="", role_from="names the model",
                                        flag="", aliases=[], model=it["model"]))
                    sim_model[it["model"]] = sid
                return sim_model[it["model"]], []
            return (sims[0], []) if len(sims) == 1 else (None, ["parent unresolved"])
        if role == "specimen":
            return (runs[0], []) if len(runs) == 1 else (None, ["parent unresolved"])
        return None, ([] if role else ["role unresolved"])

    def resolve(it, layout, fig, label, pel):
        refs = holders.get(it["ref"], []) if it["kind"] != "point" else []
        meas_ = {u for u, _ in refs if by.get(u, {}).get("role") == "measurement"}   # P185 (user): data belongs to the measurement that
        if meas_ and len({u for u, _ in refs}) > 1:                             # produced it: the parent of a measurement unit naming the
            refs = [x for x in refs if x[0] not in {by[m].get("parent") for m in meas_}]   # item gives way to it
            if len({u for u, _ in refs}) == 1:
                it.update(unit=refs[0][0], origin="pass-0", how="pass-0 data: the measurement that produced it (P185)", data_role=refs[0][1] or it["data_role"])
                return
        if len({u for u, _ in refs}) == 1:
            it.update(unit=refs[0][0], origin="pass-0", how="pass-0 data", data_role=refs[0][1] or it["data_role"])
            return
        if refs:
            it.update(reason="ambiguous: " + ", ".join(sorted({u for u, _ in refs})))
            return
        conds = [c for c in it["vector"] if c["kind"] in ("value", "name", "species", "other")]
        if conds and not it.get("model") and recs is not None and all(c.get("quantity") not in ("", "other") for c in conds):
            want = [cond_key(c) for c in conds]
            pool = [u for u in units if u.get("role") in ITEM_ROLES.get(it["data_role"], ("run", "specimen", "model_run"))]
            fig_named = {u for e in (pel.split("~")[0], f"fig{fig}", f"fig{fig}.cap") for u in named.get(e, set())}
            pool = [u for u in pool if u["id"] in fig_named] or pool if any(u["id"] in fig_named for u in pool) else pool
            hits = leaves({u["id"] for u in pool if all(any(same_value(w, h) for h in vecs.get(u["id"], [])) for w in want)})
            if len(hits) == 1:
                it.update(unit=next(iter(hits)), origin="pass-0", how="conditions match")
                return
            if hits:
                it.update(reason="ambiguous: " + ", ".join(sorted(hits)))
                return
        x = next((c for c in it["vector"] if c.get("coord") == "x"), None)
        if it["kind"] == "point" and x is not None and x.get("value") == 0:      # P177c (user, chat): an origin point no unit carries
            it.update(reason="origin")
            return
        role, why = role_of(it)
        parent, flags = parent_of(role, it)
        it.update(unit=derive(it, role, parent, flags, layout, label, fig, why), origin="derived", how="derived", role_flag="; ".join(flags))

    seen = collections.Counter()
    for f in ing.get("figures", []):
        fig = str(f["number"])
        for pn in f.get("panels") or []:
            pel0 = f"fig{fig}{pn.get('panel', '')}"
            seen[pel0] += 1
            pel = pel0 if seen[pel0] == 1 else f"{pel0}~{seen[pel0]}"          # a panel id the figure stage gives twice: its second panel pel~2
            ptype = pn.get("panel_type", "")
            layout = (lays.get(pel0) or {}).get("layout")
            first = seen[pel0] == 1                                            # figures.json keys data by figure and panel: the first panel takes it
            curves = [c for c in Fj.get("curves", []) if c["figure"] == fig and c.get("panel", "") == pn.get("panel", "")] if first else []
            vals = [v for v in Fj.get("values", []) if v["figure"] == fig and v.get("panel", "") == pn.get("panel", "")] if first else []
            cells, peaks = [v for v in vals if v["kind"] == "cell"], [v for v in vals if v["kind"] == "peak"]
            P = dict(kind="", layout=layout or "none", items=[], flags=[])
            panels[pel] = P
            if ptype == "schematic":
                P["kind"] = "schematic"
                continue
            sa = axes.get(pel0, "")
            if ptype in IMAGE_TYPES or (ptype == "map" and not curves and not cells):
                it = dict(kind="image", ref=f"{key}:{pel}#img", panel=pel, file=";".join(crops.get(fig, [])), vector=[], data_role="", unit="", reason="")
                u, how, why = panel_unit(pel, fig, [])
                it.update(unit=u, origin="pass-0" if u else "", how=how, reason=why)
                P.update(kind="image")
                items.append(it); P["items"].append(it)
                continue
            if not curves and not cells and not peaks:
                it = dict(kind="panel", ref=f"{key}:{pel}#panel", panel=pel, vector=[], data_role="", unit="", reason="", results=[])
                u, how, why = panel_unit(pel, fig, [])
                it.update(unit=u, origin="pass-0" if u else "", how=how, reason=why)
                P.update(kind="empty data panel")
                items.append(it); P["items"].append(it)
                continue
            P["kind"] = "data"
            if layout == "panel_one_unit":
                it = dict(kind="panel", ref=f"{key}:{pel}#panel", panel=pel, vector=[], data_role="simulated" if curves and all(c["kind"] == "simulated" for c in curves) else "",
                          unit="", reason="", results=[c["id"] for c in curves] + [v["id"] for v in vals])
                u, how, why = panel_unit(pel, fig, it["results"])
                if u:
                    it.update(unit=u, origin="pass-0", how=how)
                elif why.startswith("ambiguous"):
                    it.update(reason=why)
                else:
                    role = "model_run" if it["data_role"] == "simulated" else "specimen"
                    parent, flags = parent_of(role, it)
                    it.update(unit=derive(it, role, parent, flags, layout, pn.get("content", ""), fig, "a panel's one unit, not named"), origin="derived", how="derived",
                              role_flag="; ".join(flags))
                items.append(it); P["items"].append(it)
                continue
            its = []
            for c in (curves if not (layout == "point_per_unit" and cells) else []):   # point_per_unit with cells: the cells (the series repeat them)
                parts = parse_legend(pid, (c.get("series") or {}).get("label_raw", ""), sa)
                base = dict(vector=[x for x in parts if x["kind"] in CONDITION_KINDS], qualifiers=[f"{x['qualifier']}={x['value_text']}" for x in parts if x["kind"] == "qualifier" and x.get("value_text")],
                            y_quantity=next((x["quantity"] for x in parts if x["kind"] == "quantity"), ""), model=next((x["model"] for x in parts if x["kind"] == "model"), ""),
                            method=next((x["method"] for x in parts if x["kind"] == "method"), ""), parts=parts,
                            data_role=next((x["role"] for x in parts if x["kind"] == "role"), "") or ("simulated" if c.get("kind") == "simulated" else ""), label=(c.get("series") or {}).get("label_raw", ""))
                if layout == "point_per_unit" and not cells:
                    xq, xkey = c["x"]["quantity"], c["x"].get("key") or c["x"].get("label_raw") or ""
                    for n, (pt, raw) in enumerate(zip(c.get("points") or [], c.get("points_raw") or c.get("points") or []), 1):
                        coord = dict(kind="value" if xq != "other" else "other", key=xkey, quantity=xq, value=raw[0], unit=c["x"].get("unit_raw") or c["x"].get("unit") or "",
                                     how=f"x coordinate ({xq})", coord="x")
                        its.append(dict(base, kind="point", ref=f"{c['id']}:p{n}", curve=c["id"], n=n - 1, panel=pel, vector=base["vector"] + [coord], unit="", reason="",
                                        y=c["y"]["quantity"]))
                else:
                    its.append(dict(base, kind="curve", ref=c["id"], curve=c["id"], panel=pel, unit="", reason="", y=c["y"]["quantity"]))
            if layout == "point_per_unit":
                for v in cells:
                    at = [dict(kind="value" if not str(q).startswith("other:") else "other", key=str(q).removeprefix("other:"), quantity=q if not str(q).startswith("other:") else "other",
                               value=x, unit=next((c_[a]["unit"] for c_ in curves for a in ("x", "y") if c_[a]["quantity"] == q), "") if not str(q).startswith("other:") else "",
                               how="cell coordinate", coord="cell") for q, x in (v.get("at") or {}).items()]
                    its.append(dict(kind="cell", ref=v["id"], panel=pel, vector=at, qualifiers=[], y_quantity="", model="", method="", parts=[], data_role="", label=str(v.get("value_text") or v.get("value")),
                                    unit="", reason="", y=v.get("quantity") or ""))
            elif cells:
                its += [dict(kind="cell", ref=v["id"], panel=pel, vector=[], qualifiers=[], y_quantity="", model="", method="", parts=[], data_role="", label="", unit="", reason="",
                             y=v.get("quantity") or "") for v in cells]
            its += [dict(kind="peak", ref=v["id"], panel=pel, vector=[], qualifiers=[], y_quantity="", model="", method="", parts=[], data_role="", label=v.get("label") or "", unit="",
                         reason="", y=v.get("quantity") or "") for v in peaks]
            for it in its:
                if not layout:
                    it["reason"] = "no layout"
                elif layout == C.X.LAYOUT_OTHER:
                    it["reason"] = "layout other"
                elif it["kind"] in ("peak", "cell") and not it["vector"]:      # a peak (or a cell of a curve panel): pass 0's binding, else
                    refs = {u for u, _ in holders.get(it["ref"], [])}           # the one curve's unit, else the panel's named unit
                    if len(refs) == 1:
                        it.update(unit=next(iter(refs)), origin="pass-0", how="pass-0 data")
                    else:
                        u, how, why = panel_unit(pel, fig, [])
                        it.update(unit=u, origin="pass-0" if u else "", how=how, reason=why if not u else "")
                else:
                    resolve(it, layout, fig, it.get("label", ""), pel)
                items.append(it); P["items"].append(it)
            if not layout:
                P["flags"].append("no layout")
    origin = {u["id"]: ("derived", u) for u in derived}
    for it in items:
        if it["unit"]:
            o = origin.get(it["unit"])
            it.update(origin="derived" if o else it.get("origin") or "pass-0", role=(o[1] if o else by.get(it["unit"], {})).get("role"))
    return dict(items=items, units=derived, panels=panels, refs_unknown=refs_unknown)


def binding_check(B):
    """P177b (e): the invariant: every item bound to exactly one unit, or unbound with a reason. Returns the violations."""
    return [f"{it['ref']}: bound to no unit and no reason" for it in B["items"] if not it["unit"] and not it["reason"]] + \
           [f"{it['ref']}: bound and unbound" for it in B["items"] if it["unit"] and it["reason"]]


def binding_rows(pid, B, node=None):
    """P177b: one row per item (kb/reports/binding_regression.csv): paper, panel, item, kind, unit, origin, role, how, reason; P184: the
    compiled unit id (node: pass-0 id -> (row id, role))."""
    key = C.E.PAPERS.get(pid, pid)
    return [dict(paper=key, panel=it["panel"], item=it["ref"], kind=it["kind"], unit=it["unit"], unit_fact_id=(node or {}).get(it["unit"], ("",))[0] if it["unit"] else "",
                 origin=it.get("origin", "") if it["unit"] else "",
                 role=(it.get("role") or "null") if it["unit"] else "", how=it.get("how", ""), reason=it["reason"]) for it in B["items"]]


class Run:
    def __init__(self, pid):
        self.pid, self.key = pid, C.E.PAPERS[pid]
        self.log, self.dropped, self.unmapped, self.promoted = [], [], [], []
        self.scope_rows = []                                                    # P182: qualifier out of scope
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
        for p in self.promoted:                                                 # P157b: a promoted record's outcome
            if p["r"]["rec"] is rec and not p["outcome"]:
                p["outcome"] = f"dropped at {step}: {reason}" + (f" ({field})" if field else "")

    def count(self, step, what, n=1):
        self.steps.setdefault(step, collections.Counter())[what] += n

    # ------------------------------------------------------------------------------------------------------------ input
    def read(self):
        lines = [json.loads(x) for x in (C.RECORDS / f"{self.pid}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        self.groups = P1.groups(self.pid)[0]
        latest, p0, el_line, fill = {}, None, {}, None
        grp_of = {r["element_id"]: g for g, rs in self.groups.items() for r in rs}
        ok = accepted_versions(self.key)                                        # P179b (user): only lines of an accepted form version
        self.versions_skipped = collections.Counter(line_version(x) for x in lines if x["pass"] == 1 and line_version(x) not in ok)
        for n, x in enumerate(lines, 1):
            if x["pass"] == 0:
                p0 = n
            elif x["pass"] == 1 and line_version(x) in ok:
                latest[x["section"]] = n
                for e in x.get("element_ids") or []:                            # P179: per element, the latest line of its group that holds
                    if grp_of.get(e) == x["section"]:                           # it (a re-extraction line holds some of a group's elements)
                        el_line[e] = n
            elif x["pass"] in FILL_PASSES:                                      # P179, P181: the latest fill of the pass-0 units
                fill = n
        used = set(el_line.values())
        before = [n for n, x in enumerate(lines, 1) if x["pass"] == 0 and used and n < min(used)]
        p0 = before[-1] if before else p0                                       # P143b: the pass-0 line the pass-1 lines in use were written against
        ignored = [n for n, x in enumerate(lines, 1) if x["pass"] == 1 and n not in used]
        if self.versions_skipped:
            self.note("input: pass-1 lines of a form version not accepted (ontology/form_versions.csv), not read: "
                      + ", ".join(f"{v} {n}" for v, n in self.versions_skipped.items()))
        self.lines_used, self.lines_ignored = sorted(used | {p0}), ignored
        self.note(f"input: {len(lines)} lines; pass 0 = line {p0}; {len(used)} pass-1 lines for {len(self.groups)} groups; ignored lines "
                  + ", ".join(f"{n} ({lines[n - 1]['section']})" for n in ignored))
        for g in self.groups:
            if g not in latest:
                self.note(f"input: group {g} has no pass-1 line")
        p0obj = C.loads_json(lines[p0 - 1]["response"])
        self.panel_method = {}
        nx = max((i for i, x in enumerate(lines, 1) if x["pass"] == EXTEND_PASS), default=None)   # P184 (user): the pass-0 extension's units, added
        if nx and isinstance(p0obj, dict):
            ext = C.loads_json(lines[nx - 1]["response"])
            have = {u.get("id") for u in p0obj.get("units") or [] if isinstance(u, dict)}
            new = [u for u in ext.get("units") or [] if isinstance(u, dict) and u.get("id") and u["id"] not in have]
            self.count("input", "pass-0 extension units", len(new))
            if len(new) < len(ext.get("units") or []):
                self.count("input", "pass-0 extension units with a current id (left out)", len(ext.get("units") or []) - len(new))
            p0obj = {**p0obj, "units": list(p0obj.get("units") or []) + new}
            self.panel_method = {x["panel"]: x["method"] for x in ext.get("panel_methods") or [] if isinstance(x, dict) and x.get("panel") and x.get("method") in L.MEASUREMENT_METHODS}
            self.note(f"input: pass-0 extension = line {nx}: {len(new)} units (" + ", ".join(f"{r} {n}" for r, n in collections.Counter(u.get('role') for u in new).items())
                      + f"); {len(self.panel_method)} image panel methods")
        self.pass0 = (p0obj.get("units") or []) if isinstance(p0obj, dict) else p0obj    # P144: {units, table_layouts, panel_layouts}
        self.layouts = {k: (p0obj.get(k) or []) for k in ("table_layouts", "panel_layouts")} if isinstance(p0obj, dict) else {}
        self.answers, self.form_version = {}, {}                                # element id -> [record] | "NK:..."; P158: its line's form version
        parsed = {n: P1.answers(C.loads_json(lines[n - 1]["response"])) for n in used}
        for e, n in el_line.items():
            if e in parsed[n]:
                self.answers[e] = parsed[n][e]
                self.form_version[e] = lines[n - 1].get("form_version", "")     # P158: '' = written before the freeze
        fill, self.fill, self.fill_listed = recipe_fill(self.pid, lines)        # P179, P181: the recipe fields (+ quote, element) on the units; P182: contract
        for u in self.pass0:
            if isinstance(u, dict) and u.get("id") in self.fill:
                u.update(self.fill[u["id"]])
        for x in self.fill_listed:
            self.note(f"input: recipe field set to null: {x['run']} {x['field']} {x['value']} ({x['reason']})" if "decision" not in x["reason"]
                      else f"input: recipe field by the user's decision: {x['run']} {x['field']} {x['value']} -> ({x['reason']})")
        if fill:
            self.note(f"input: recipe fill = line {fill}: " + "; ".join(f"{i} " + ", ".join(f"{f} {x[f]}" for f in C.X.RECIPE_FIELDS if x.get(f)) for i, x in self.fill.items()))
        recs = []
        for eid, a in sorted(self.answers.items(), key=lambda x: self.order[x[0]]):
            if isinstance(a, list):
                for i, rec in enumerate(a):
                    if isinstance(rec.get("variables"), list):                  # rule 3: the provider's list back to {symbol: quantity}
                        rec["variables"] = {v.get("symbol"): v.get("quantity") for v in rec["variables"] if isinstance(v, dict)}
                    if "parent" in rec and "about" not in rec:                  # P148: a line written before the form's parent became about
                        rec["about"] = rec.pop("parent")
                        self.count("input", "parent read as about (older line)")
                    recs.append(dict(eid=eid, rec=rec, seq=i, form_version=self.form_version.get(eid, "")))
        self.count("input", "records", len(recs))
        self.binding = bind(self.pid, p0obj, recs)                              # P177b (user): the one binding rule
        self.layouts_other = {x.get("panel") or x.get("table"): x.get("description") or "(no description)"
                              for x in self.layouts.get("panel_layouts", []) + self.layouts.get("table_layouts", [])
                              if isinstance(x, dict) and x.get("layout") == C.X.LAYOUT_OTHER and (x.get("panel") or x.get("table"))}
        self.cap_methods = collections.defaultdict(collections.Counter)         # P177b: the method of a figure's caption records (an image)
        for r in recs:
            if r["eid"].endswith(".cap") and isinstance(r["rec"].get("method"), str):
                self.cap_methods[r["eid"]][r["rec"]["method"]] += 1
        for v in binding_check(self.binding):
            self.note(f"input: binding invariant: {v}")
        self.from_curves = self.binding["units"]
        self.pass0 = list(self.pass0) + self.from_curves
        recipe = self.recipe(recs)
        for u in self.from_curves:
            self.count("input", f"unit derived ({u['origin']}, {u['role']})")
            dkind = "model_input" if u["role"] == "model_run" else "stated"
            for c in u["conditions"] if u["introduced_in"] else []:              # P163: the legend label's values (and P177b a point's
                rec = dict(type="setting", quantity="other", label_as_printed=c["key"], quote=c["key"], about=u["id"])   # coordinates), resolved by step a0
                if c["kind"] == "value" and c.get("value_min") is not None:     # P175: '<symbol> = <a> to <b>'
                    rec.update(value_min=c["value_min"], value_max=c["value_max"], unit=c["unit"] or None, kind=dkind)
                elif c["kind"] == "value":
                    rec.update(value=c["value"], unit=c["unit"] or None, kind=dkind)
                sp = species_named(self.pid, c["key"]) if c.get("coord") else {}
                if len(sp) == 1:                                                # P178 (user): a coordinate axis that names one species: species=
                    rec["qualifiers"] = {"species": next(iter(sp))}
                    self.count("input", "coordinate setting species (the axis names it)")
                if c.get("coord") and c.get("quantity") in C.X.STEP_QUANTITIES:  # P177c (user): a coordinate axis that names a species
                    step = self.axis_step(c, recipe)
                    if step:
                        rec["qualifiers"] = {"step": step[0], **(rec.get("qualifiers") or {})}
                        if step[1]:
                            rec["note"] = step[1]
                        self.count("input", f"coordinate setting step {step[0]}" + (" (flagged)" if step[1] else ""))
                if c["kind"] == "species":                                      # P166: step a0 resolves the species name (value_text)
                    rec.update(quantity=c["quantity"], value_text=c["key"], kind=dkind, label_as_printed=u.get("series_axis") or c["quantity"])
                recs.append(dict(eid=u["introduced_in"][0], rec=rec, seq=-1, form_version=C.X.FORM_VERSION, origin=u["origin"],
                                 derived="name" if c["kind"] in ("name", "other", "never") else c["kind"],
                                 dkind=dkind, once=(u["panel"], c["key"]) if c["kind"] == "value" else None))
                self.count("input", f"condition of a derived unit ({c['kind']})")
        if self.from_curves:
            self.note(f"input: {len(self.from_curves)} units derived from curves (P161): " + ", ".join(u["id"] for u in self.from_curves))
        return recs

    def recipe(self, recs):
        """P177c (user): the paper's recipe as {species id: 'A' | 'B'}: the half-cycle whose reactant_A / reactant_B setting (pass 1) names
        the species (value_text resolved by vocab_hits); a species named in both halves is in neither."""
        half = collections.defaultdict(set)
        for r in recs:
            rec = r["rec"]
            if rec.get("type") == "setting" and rec.get("quantity") in ("reactant_A", "reactant_B") and isinstance(rec.get("value_text"), str):
                hit = vocab_hits(self.pid, "species", rec["value_text"])
                if len(hit) == 1:
                    half[next(iter(hit))].add(rec["quantity"][-1])
        return {s: next(iter(h)) for s, h in half.items() if len(h) == 1}

    def axis_step(self, c, recipe):
        """P177c (user): the step of a setting derived from a coordinate axis whose label names a species (species_named): the half-cycle
        in which the recipe lists it (reactant_A -> reactant_A / purge_A, reactant_B -> reactant_B / purge_B; a purge time its purge, a
        pulse time or an exposure its dose); a species not in the recipe -> none, flagged. Returns (step, flag); None when the label names
        no species."""
        sp = species_named(self.pid, c["key"])
        if not sp:
            return None
        halves = {recipe.get(s) for s in sp}
        if len(halves) != 1 or None in halves:
            return "none", f"step none: the axis '{c['key']}' names {', '.join(sorted(sp))}, no one species of the paper's recipe (reactant_A / reactant_B) (P177c)"
        h = halves.pop()
        return (f"purge_{h}" if c["quantity"] in PURGE_QUANTITIES else f"reactant_{h}"), ""

    # ------------------------------------------------------------------------------------------------------------ a1 (P178, P179)
    def symbol_species(self, recs):
        """a1, P178 / P179 (user): the species of a record labelled with a symbol (export.symbol_like, holding a letter) rests on evidence,
        every form version; P182 (user): the records are selected by type, model / definition / cited / derived (SYMBOL_TYPES), never
        by quantity; settings and observations keep their own species:
          1. this paper's definition record of the symbol, else of its subscript (p_B -> B), whose own text (its quote, the meaning it
             copies, its table row) names one substance: a species name; 'carrier gas' (the paper's one carrier_gas setting); an
             unnamed reactant ('reactant X', or 'molecule(s) X' for a letter X the paper calls a reactant) = model_reactant. A
             definition naming a specific substance decides the species (the note: 'species corrected from the symbol definition').
          2. a definition giving model_reactant backs model records only and gives way to a species the record's own element names.
          3. else the record's own element (its text; a table cell with its column and row header cells; the label's subscript when
             it is a species name) naming the record's species keeps it.
          4. else the species is cleared, listed 'species cleared (no evidence)' (P179; P178 listed it 'unverified (record only)').
        A definition record is held to 3 and 4 on its own text. Every such record is a log line 'a1: symbol species ...' and r['a1']."""
        text, self.a1_rows = self.text, []
        letters = {m.group(1) for t in text.values() for m in UNNAMED_REACTANT.finditer(t)}
        carrier = {next(iter(vocab_hits(self.pid, "species", r["rec"]["value_text"])), r["rec"]["value_text"]) for r in recs
                   if r["rec"].get("type") == "setting" and r["rec"].get("quantity") == "carrier_gas" and isinstance(r["rec"].get("value_text"), str) and r["rec"]["value_text"]}

        def subspecies(lab):
            m = SUBSCRIPT.match(lab or "")
            h = vocab_hits(self.pid, "species", m.group(1)) if m else {}
            return {next(iter(h))} if len(h) == 1 else set()

        def names(ts, lab):
            sp = {s_ for t in ts for s_ in species_named(self.pid, normalize(t))} | subspecies(lab)   # P182: the text normalize()d ($\\text{H}_2\\text{O}$ -> h2o)
            if any(UNNAMED_REACTANT.search(t) or any(re.search(rf"\b(?i:molecules?)\s+{x}\b", t) for x in letters) for t in ts):
                sp.add("model_reactant")
            if len(carrier) == 1 and any(re.search(r"(?i)\bcarrier gas\b", t) for t in ts):
                sp |= carrier
            return sp

        def element(eid):                                                       # a cell with its column and row header cells
            m = CELL_ID.match(eid)
            return [t for t in [text.get(eid, "")] + ([text.get(f"{m.group(1)}.r0c{m.group(3)}", ""), text.get(f"{m.group(1)}.r{m.group(2)}c0", "")] if m else []) if t]

        def row(eid):                                                           # a definition in a table: its row (the symbol and its meaning)
            m = CELL_ID.match(eid)
            return [t for x, t in text.items() if re.match(rf"^{re.escape(m.group(1))}\.r{m.group(2)}c\d+$", x)] if m else [text.get(eid, "")]
        defs = collections.defaultdict(list)
        for r in recs:
            rec = r["rec"]
            if rec.get("type") == "definition" and isinstance(rec.get("term"), str) and rec["term"].strip():
                defs[C.X.symbol_key(rec["term"])].append((r["eid"], names([rec.get("quote") or "", rec.get("label_as_printed") or ""] + row(r["eid"]), rec["term"])))
        for r in recs:
            rec = r["rec"]
            lab = rec.get("label_as_printed") if isinstance(rec.get("label_as_printed"), str) else ""
            if r.get("origin") or rec.get("type") not in SYMBOL_TYPES or not C.X.symbol_like(lab) or not re.search(r"[A-Za-z\\]", lab):
                continue
            q = rec.get("qualifiers") if isinstance(rec.get("qualifiers"), dict) else {}
            own = q.get("species") or ""
            if rec.get("type") == "definition":
                named, sp, found = names([rec.get("quote") or "", lab] + row(r["eid"]), rec.get("term") or lab), "", []
            else:
                sub = SUBSCRIPT.match(lab)
                found = next((ds for k in [C.X.symbol_key(lab)] + ([C.X.symbol_key(sub.group(1))] if sub else []) for ds in [[d for d in defs.get(k, []) if len(d[1]) == 1]] if ds), [])
                sp = {next(iter(x)) for _, x in found}
                sp = next(iter(sp)) if len(sp) == 1 else ""
                named = names(element(r["eid"]), lab) - ({"model_reactant"} if rec.get("type") != "model" else set())
            generic = sp == "model_reactant"
            if sp and (not generic or (rec.get("type") == "model" and not (own and own in named and own != "model_reactant"))):
                how = "backed by the definition" if own == sp else ("corrected from the definition" if own else "from the definition")
            elif own and own in named:
                how, sp = "kept: its own element names it", own
            elif own:
                how, sp = "species cleared (no evidence)", ""
            else:
                how, sp = "no species", ""
            ev = ", ".join(sorted({e for e, x in found if sp in x})) if how.endswith("definition") else ""
            if how.endswith("definition") and sp != own:
                rec["qualifiers"] = {**q, "species": sp}
                rec["note"] = "; ".join(x for x in (rec.get("note"), (f"species corrected from the symbol definition ({ev}): was {own}" if own
                                                                      else f"species from the symbol definition ({ev})")) if x)
            elif how.startswith("species cleared"):
                rec["qualifiers"] = {k: v for k, v in q.items() if k != "species"} or None
                rec["note"] = "; ".join(x for x in (rec.get("note"), f"species cleared (no evidence): was {own}") if x)
            r["a1"] = dict(element=r["eid"], label=lab, type=rec.get("type"), quantity=rec.get("quantity"), record_species=own, definition=ev,
                           own_element_names=",".join(sorted(named)), outcome=how, species=sp)
            self.a1_rows.append(r["a1"])
            self.count("a1", f"symbol species: {how}")
            self.note(f"a1: symbol species {r['eid']} {lab!r} {rec.get('type')} {rec.get('quantity')}: record {own or '-'}, definition "
                      f"{', '.join(f'{e}: {x}' for e, x in found) or '-'} -> {how}" + (f" ({sp})" if sp and sp != own else ""))
        self.symbol_species_paper(recs)
        return recs

    def symbol_species_paper(self, recs):
        """a1, P179c (user): a symbol is paper-local, its species too (P157d). Within the paper, a symbol (export.symbol_key of the label)
        whose species is evidenced in any record (kept, backed by, from or corrected from the definition) gives that species to every
        record of the symbol that has none; differing evidenced species clear every record of the symbol ('symbol species conflict').
        Then a user's symbol decision (history.csv kind symbol with a species, for this paper) gives its species to the paper's symbols
        whose subscript is the decided letter, where the species is still empty."""
        def put(r, sp, how, note):
            rec = r["rec"]
            q = rec.get("qualifiers") if isinstance(rec.get("qualifiers"), dict) else {}
            rec["qualifiers"] = ({**q, "species": sp} if sp else {k: v for k, v in q.items() if k != "species"}) or None
            rec["note"] = "; ".join(x for x in (rec.get("note"), note) if x)
            r["a1"].update(outcome=how, species=sp)
            self.count("a1", f"symbol species: {how}")
            self.note(f"a1: symbol species {r['eid']} {r['a1']['label']!r}: {note}")
        by = collections.defaultdict(list)
        for r in recs:
            if r.get("a1"):
                by[C.X.symbol_key(r["a1"]["label"])].append(r)
        for sym, rs in by.items():
            ev = collections.defaultdict(set)
            for r in rs:
                if r["a1"]["outcome"] in SPECIES_EVIDENCED and r["a1"]["species"]:
                    ev[r["a1"]["species"]].add(r["eid"])
            if len(ev) == 1:
                (sp, els), = ev.items()
                for r in rs:
                    if not r["a1"]["species"]:
                        put(r, sp, "from the symbol's evidence in this paper", f"species {sp} from the symbol's evidence in this paper ({', '.join(sorted(els))})")
            elif len(ev) > 1:
                for r in rs:
                    put(r, "", "symbol species conflict", "symbol species conflict: " + "; ".join(f"{sp} ({', '.join(sorted(e))})" for sp, e in sorted(ev.items())))
        hist = C.V2 / "ontology" / "history.csv"
        for h in csv.DictReader(hist.open(encoding="utf-8")) if hist.exists() else []:
            if h["kind"] != "symbol" or not h.get("species") or self.pid not in h["source_pids"].split(";"):
                continue
            for r in recs:
                m = SUBSCRIPT.match(r["a1"]["label"]) if r.get("a1") else None
                if m and C.X.symbol_key(m.group(1)) == C.X.symbol_key(h["id"]) and not r["a1"]["species"]:
                    put(r, h["species"], "from the user's symbol decision", f"species {h['species']}: the user's decision on subscript {h['id']} (history.csv, {h['date']})")


    def scope_row(self, eid, typ, quantity, key, v, where):
        self.scope_rows.append(dict(paper=self.key, element=eid, type=typ or "", quantity=quantity, key=key,
                                    value=num_text(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v, where=where, recovered=""))
        self.count("a1" if where == "record" else "n", f"qualifier out of scope: {key}")
        self.note(f"{'a1' if where == 'record' else 'n'}: qualifier out of scope: {eid} {typ} {quantity} {key}={v} ({where})")

    def qualifier_scope(self, recs):
        """P182 (user), every form version: a record's qualifier key outside its quantity's scope (out_of_scope) is removed and listed
        'qualifier out of scope' (kb/compiled/<pid>.qualifier_scope.csv); validate() checks whether the record was refused by form.json
        with them and is accepted without them (recovered, counted)."""
        for r in recs:
            rec = r["rec"]
            q = rec.get("qualifiers")
            out = [k for k in q if out_of_scope(rec.get("quantity"), k)] if isinstance(q, dict) else []
            if out:
                r["scope_removed"], r["scope_rows"] = {k: q[k] for k in out}, len(self.scope_rows)
                rec["qualifiers"] = {k: v for k, v in q.items() if k not in out}
                for k in out:
                    self.scope_row(r["eid"], rec.get("type"), rec["quantity"], k, q[k], "record")
        return recs

    def scope_facts(self, facts, where):
        """P182: the same scope on facts no record holds (figures.json curves and values, derived facts), before dedupe; listed."""
        for f in facts:
            if f.get("qualifiers"):
                kv = [x.split("=", 1) for x in f["qualifiers"].split(";") if "=" in x]
                out = [(k, v) for k, v in kv if out_of_scope(f.get("quantity"), k)]
                if out:
                    f["qualifiers"] = ";".join(f"{k}={v}" for k, v in kv if (k, v) not in out)
                    for k, v in out:
                        self.scope_row(f.get("evidence", "").split(";")[0], f.get("type"), f["quantity"], k, v, where)
        return facts

    def recipe_process_mode(self, recs):
        """P179 (user): process_mode on a run comes only from its recipe field (the pass-0 unit's process_mode with its quote, filled by
        kb/extract/process_mode_fill.py): one setting per run that has one, its evidence the quote's element; a pass-1 process_mode record
        about a pass-0 run is dropped (the recipe field holds it). A derived unit's legend condition stays (it has no recipe). No
        process_mode is derived."""
        runs = {u["id"]: u for u in self.pass0 if isinstance(u, dict) and u.get("role") == "run" and not u.get("origin")}
        out = []
        for r in recs:
            q, ab = r["rec"].get("quantity"), r["rec"].get("about")
            if ab in runs and not r.get("origin") and q == "process_mode":       # P185: a pass-1 material record stays (the recipe field adds its own)
                self.drop("a1", r["eid"], r["rec"], f"{q}_from_the_recipe_field")
                continue
            out.append(r)
        for u in runs.values():
            for f, lab in (("process_mode", "process mode"), ("material", "material")):   # P185 (user): material, like process_mode
                if u.get(f):
                    pe = (u.get(f + "_element") or "").split(";")[0]                # P182: a quote across elements names them all
                    eid = pe if pe in self.order else (u.get("introduced_in") or [self.els[0]["element_id"]])[0]
                    out.append(dict(eid=eid, rec=dict(type="setting", quantity=f, value_text=u[f], label_as_printed=lab,
                                                      quote=u.get(f + "_quote") or "", about=u["id"], kind="stated", statement=None),
                                    seq=-1, form_version=C.X.FORM_VERSION, recipe_field=True))
                    self.count("a1", f"{f} from the recipe field: {u[f]}")
        return out

    # ------------------------------------------------------------------------------------------------------------ a0 (P157b, P157d)
    def resolve_other(self, recs):
        """a0, before form.json: a value the record holds as other or outside the vocabulary, compared whole (never a substring) with
        the generated vocab of its kind only: quantity other by its record key (export.record_text: label_as_printed, else the meaning of
        its candidate definition) against the quantity and categorical ids, names and aliases (export.norm_label) and the symbols of this
        paper (export.symbol_key, case kept); a material / substrate / reactant / structure value_text not in form.json's enum (those
        entries); a categorical value_text not in its fixed list (the value ids and value_aliases); a method not in lists.METHODS (method
        entries). An entry's label is never read. A unit is left to step e. One id: the record takes it and goes on like any record
        (form.json, units, placement, fact); two ids: ambiguous, left as it is (unmapped.csv action 'kept (ambiguous: ids)'). A record still
        quantity other whose key is a never.csv word, or a never.csv symbol of this paper, carries the never category (unmapped.csv column
        never; export.never_index: a never label naming a live entry has no effect). Every promotion -> <pid>.promoted.csv. P162 rule 3, P163: a
        derived unit's legend name (parse_legend: a part that is no number) is read like a record value: one structure or categorical value
        (id or alias, the trailing bracket dropped) -> that quantity and value_text (Amorphous -> crystallinity = amorphous, Sphere (s = 2) ->
        structure = porous_sphere); else it goes on as other. A derived value (a number) holds the series_axis label or its symbol as its key
        and is resolved here like any quantity other."""
        enum = C.schema("form.json")["$defs"]
        for r in recs:
            rec = r["rec"]
            q = rec.get("quantity")
            q = q if isinstance(q, str) else ""
            if r.get("derived") == "name" and q == "other":                    # P162 rule 3, P163: a legend name is a structure or categorical value
                lab = C.X.record_text(rec)
                name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", lab).strip() or lab
                hits = {(k_ if k_ == "structure" else k_[6:], v): how for k_ in ["structure"] + [f"value:{cq}" for cq in VALUES]
                        for v, how in vocab_hits(self.pid, k_, name).items()}
                if len(hits) == 1:
                    ((cq, v), how), = hits.items()
                    rec.update(quantity=cq, value_text=v, kind=r["dkind"])
                    q = cq
                    self.promoted.append(dict(r=r, element=r["eid"], field="value_text", printed=lab, meaning=lab,
                                              lookup=f"{'structure' if cq == 'structure' else 'value:' + cq}: {how}", id=v, outcome=""))
                    self.count("a0", f"derived legend name -> {'structure' if cq == 'structure' else 'categorical'} value")
                    self.note(f"a0: {r['eid']}: legend name {lab!r} -> {cq} = {v} ({how})")
                else:
                    self.count("a0", "derived legend label parsed to nothing (other)" + (", two values" if hits else ""))
                    self.note(f"a0: {r['eid']}: legend label {lab!r} parsed to nothing" + (f": names {sorted(hits)}" if hits else ""))
            todo = [("quantity", C.X.record_text(rec), "quantity")] if q == "other" else []
            vt = rec.get("value_text")
            if q in SPECIES_KIND and isinstance(vt, str) and vt not in enum[SPECIES_KIND[q]]["enum"]:
                todo.append(("value_text", vt, SPECIES_KIND[q]))
            if q in VALUES and isinstance(vt, str) and vt not in VALUES[q]:
                todo.append(("value_text", vt, f"value:{q}"))
            if isinstance(rec.get("method"), str) and rec["method"] not in L.METHODS:
                todo.append(("method", rec["method"], "method"))
            for field, text, kind in todo:
                if not text.strip():
                    continue
                hits = vocab_hits(self.pid, kind, text)
                meaning = " ".join(((rec.get("candidate") or {}).get("definition_quote") or "").split()) if field == "quantity" else text
                if len(hits) == 1:
                    (i, how), = hits.items()
                    rec[field] = i
                    self.promoted.append(dict(r=r, element=r["eid"], field=field, printed=text, meaning=meaning, lookup=f"{kind}: {how}", id=i, outcome=""))
                    self.count("a0", f"{field} promoted ({kind}: {how.split(' ')[0]})")
                    self.note(f"a0: {r['eid']}: {field} {text!r} -> {i} ({kind}: {how})")
                elif hits:
                    r["ambiguous"] = sorted(hits)
                    self.promoted.append(dict(r=r, element=r["eid"], field=field, printed=text, meaning=meaning, lookup=f"{kind}: ambiguous ({'; '.join(f'{i}: {h}' for i, h in sorted(hits.items()))})",
                                              id=" | ".join(sorted(hits)), outcome="not promoted: the key names two ids"))
                    self.count("a0", f"{field} ambiguous (left as it is)")
                    self.note(f"a0: {r['eid']}: {field} {text!r} ambiguous: {sorted(hits)}")
            if rec.get("quantity") == "other":
                text = C.X.record_text(rec)
                mh = vocab_hits(self.pid, "model", text) if text.strip() else {}
                if len(mh) == 1:                                                # P172: a record of quantity other whose label names one model
                    r["names_model"] = next(iter(mh))                           # entry (its name, alias or a symbol of this paper): no quantity
                    self.count("a0", "quantity other naming a model entry (kept)")
                mt = vocab_hits(self.pid, "method", text) if text.strip() and not mh else {}
                if len(mt) == 1:                                                # P176 (user): one naming a method entry, as a model name
                    r["names_method"] = next(iter(mt))
                    self.count("a0", "quantity other naming a method entry (kept)")
                hit = never_of(self.pid, text)
                if hit:
                    r["never"], r["never_label"] = hit["category"], hit["label"] + (f" (symbol in {hit['paper']})" if hit.get("symbol") == "yes" else "")
                    self.count("a0", "quantity other: never.csv " + ("symbol" if hit.get("symbol") == "yes" else "word"))
        return recs

    # ------------------------------------------------------------------------------------------------------------ a-g
    def validate(self, recs):
        """a: D12 (a variable's quantity outside the enum -> null); C4 (P148): a numeric string in a number field (value, value_min,
        value_max, uncertainty, uncertainty_n, a numeric qualifier) -> the number, logged; C5 (P148): a variable whose quantity is null
        -> the quantity of the same paper's definition of that term (normalize()d; a term two definitions give different quantities is
        left null), logged; then form.json: C6 (P148, corrected in P148 D) every error drops the record, the reason
        schema:<validator> (inside a nullable anyOf, the validator of its non-null branch). P158: a record of a line written before the
        form freeze (no form_version) is validated without the allOf rules marked "P158 rule n", which it predates; every such record
        that one of them would reject is counted under a_p158 (rule and field), never dropped for it: extraction is once per paper."""
        from jsonschema import Draft202012Validator
        form = C.schema("form.json")
        val, qids = Draft202012Validator(form), set(form["$defs"]["quantity_id"]["enum"])
        pre = Draft202012Validator(before_freeze(form))
        noscope = lambda f: {**f, "allOf": [x for x in f.get("allOf", []) if not str(x.get("$comment", "")).startswith("P182 scope")]}   # noqa: E731
        val_ns, pre_ns = Draft202012Validator(noscope(form)), Draft202012Validator(noscope(before_freeze(form)))   # P182: refused for another rule
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
            if r.get("form_version"):
                errs = list(val.iter_errors(r["rec"]))
            else:                                                               # P158: a pre-freeze record, the rules of its own form
                errs = list(pre.iter_errors(r["rec"]))
                if not errs:
                    for e in val.iter_errors(r["rec"]):
                        rule = next((str(form["allOf"][p]["$comment"]).split(":")[0] for p_, p in zip(e.absolute_schema_path, list(e.absolute_schema_path)[1:])
                                     if p_ == "allOf" and isinstance(p, int) and "$comment" in form["allOf"][p]), "")
                        self.count("a_p158", f"{rule} (predates the freeze, kept)")
                        self.note(f"a: {r['eid']}: {rule} would reject it ({'.'.join(map(str, e.path)) or e.validator}); a pre-freeze record, kept")
            if r.get("scope_removed"):                                          # P182: refused (by a form rule other than the scopes) with the out-of-scope keys, accepted without
                rq = {k_: (float(v) if k_ in qnum and isinstance(v, str) and NUMBER.fullmatch(v.strip()) else v) for k_, v in r["scope_removed"].items()}
                un = {**r["rec"], "qualifiers": {**(r["rec"].get("qualifiers") or {}), **rq}}
                if not errs and list((val_ns if r.get("form_version") else pre_ns).iter_errors(un)):
                    self.count("a", "recovered: accepted once out-of-scope qualifiers removed (P182)")
                    self.note(f"a: {r['eid']}: recovered: form.json accepts it without {', '.join(r['scope_removed'])} (P182)")
                    for x in self.scope_rows[r["scope_rows"]:r["scope_rows"] + len(r["scope_removed"])]:
                        x["recovered"] = "yes"
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
        out, self.once = [], set()
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
            if q == "other" and r.get("once") and r["once"] in self.once:      # P163: a derived value's other condition, one row per panel
                self.count("c", "quantity_other of a derived value (the panel's row written once)")
            elif q == "other":
                if r.get("once"):
                    self.once.add(r["once"])
                self.unmapped.append(dict(element=eid, field="quantity", id="other", label_as_printed=rec.get("label_as_printed", ""), unit=rec.get("unit", ""),
                                          candidate=json.dumps(rec.get("candidate", {}), ensure_ascii=False),
                                          action=f"kept (never: {r['never_label']})" if r.get("never") else f"kept (ambiguous: {', '.join(r['ambiguous'])})" if r.get("ambiguous")
                                          else f"kept (names the model {r['names_model']})" if r.get("names_model")
                                          else f"kept (names the method {r['names_method']})" if r.get("names_method") else "kept",   # P172, P176
                                          never=r.get("never", ""), nearest=rec.get("nearest", "") or ""))
                self.count("c", "quantity_other never (kept)" if r.get("never") else "quantity_other (kept)")
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
        order (P140 C1); a null quote is not found. P162: a derived unit's condition (figures.json, no quote) is counted, not checked."""
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
            if r.get("origin"):                                                 # P162: a derived unit's condition comes from figures.json, not a quote
                self.count("d", "derived condition (figures.json, no quote check)")
                out.append(r)
                continue
            how, els = quote_found(self.pid, r["rec"].get("quote"), normalize(" ".join(self.scope(r["eid"]))), r["eid"])   # P182 (user, b)
            if not how:
                self.drop("d", r["eid"], r["rec"], "quote_not_found", "quote")
                continue
            if how == "own_in_order":                                           # P140 C1: every token in order, gaps allowed
                self.count("d", "quote_noncontiguous (kept)")
            elif how == "span":                                                 # P182: the quote spans elements or sits in another; evidence = those
                self.count("d", "quote found in the paper's elements concatenated (P182)")
                self.note(f"d: quote found across elements: {r['eid']} {r['rec'].get('type')} {r['rec'].get('quantity')} -> evidence {';'.join(els)}")
                r["quote_elements"] = els
            out.append(r)
        return out

    def units(self, recs):
        out = []
        for r in recs:
            rec = r["rec"]
            if rec.get("unit"):
                s = unit_symbol(rec["unit"])
                if s is None:                                                   # C6: kept with the unit as printed, logged
                    self.unmapped.append(dict(element=r["eid"], field="unit", id=normalize(rec["unit"]), label_as_printed=rec.get("label_as_printed", ""),
                                              unit=rec["unit"], candidate="", action="kept (unit as printed)", never=r.get("never", "")))
                    self.count("e", "unit_unresolved (kept as printed)")
                    s = rec["unit"]
                r["unit"] = dimless(s)                                          # P151 C2
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
        how = lambda it: "inferred" if it.get("origin") else "stated"                 # noqa: E731  P161: a unit derived from a curve
        origin = lambda it: f"; {it['origin']}" if it.get("origin") else ""          # noqa: E731
        rows.append(row(fact_id=f"{k}:recipe", type="activity", kind="recipe", how="inferred", parent=k, label_as_printed="recipe",   # P148: always (C1)
                        evidence=ok_ev([e for it in role("run") + role("specimen") for e in it.get("introduced_in") or []]) or self.els[0]["element_id"],
                        statement=f"the deposition recipe of {k}: the runs and specimens of its first pass"))
        for it in role("run"):
            self.node[it["id"]] = (f"{k}:run:{slug(it['id'])}", "run")
            rows.append(row(fact_id=self.node[it["id"]][0], type="activity", kind="deposition", how=how(it), evidence=ok_ev(it.get("introduced_in") or []),
                            parent=f"{k}:recipe", label_as_printed=it.get("name_as_printed") or it["id"], statement=f"deposition run {it['id']} ({it.get('name_as_printed')!r}{origin(it)})"))
        for it in role("simulation"):
            self.model_of(it)                                                   # P168: the model entry its printed name resolves to
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
            rows.append(row(fact_id=self.node[it["id"]][0], type="entity", how=how(it), evidence=ok_ev(it.get("introduced_in") or []),
                            parent=par[0] if par[1] == "simulation" else k, label_as_printed=it.get("name_as_printed") or it["id"],
                            statement=f"model run {it['id']} ({it.get('name_as_printed')!r}{origin(it)})"))
        for it in items:                                                        # P176 (user): a derived unit of role null: a row under the paper
            if it.get("origin") and not it.get("role"):                         # with its data and its legend's settings (nothing dropped)
                self.node[it["id"]] = (f"{k}:unit:{slug(it['id'])}", "unresolved")
                rows.append(row(fact_id=self.node[it["id"]][0], type="entity", how="inferred", evidence=ok_ev(it.get("introduced_in") or []), parent=k,
                                label_as_printed=it.get("name_as_printed") or it["id"], statement=f"derived unit {it['id']} ({it.get('name_as_printed')!r}{origin(it)}): role unresolved"))
                self.count("h", "derived unit of role null (role unresolved: a row under the paper)")
        for it in items:                                                        # P175: a deduplicated derived unit's other ids name its row
            for al in it.get("aliases") or [] if it["id"] in self.node else []:
                self.node.setdefault(al, self.node[it["id"]])
        self.note("h: tree from pass 0: " + ", ".join(f"{r} {len(role(r))}" for r in ("run", "simulation", "specimen", "model_run", "series", "cited_work"))
                  + "; identity rows: none (pass 0 carries no identity)")
        self.rows_tree = rows
        self.meas, self.films = {}, {}
        self.up = {r["fact_id"]: r["parent"] for r in rows}                     # P148: a unit row -> its parent row (place())
        self.under = collections.defaultdict(list)                             # a run / simulation row -> its specimen / model-run rows
        for nid, role_ in self.node.values():
            if role_ in ("specimen", "model_run"):
                self.under[self.up[nid]].append(nid)
        for it in role("measurement"):                                          # P184 (user): a measurement unit -> a measurement activity
            par = self.node.get(it.get("parent", ""), ("", ""))                 # under its specimen or model run (a run's: the run's entity)
            ent = par[0] if par[1] in ("specimen", "model_run", "unresolved") else self.run_entity(par[0])[0] if par[1] == "run" else ""
            if not ent:
                self.count("h", "measurement unit without a unit parent (left out)")
                continue
            m = it.get("method") if it.get("method") in L.MEASUREMENT_METHODS else ""
            i = f"{ent}:meas:{m or 'measurement'}"
            if i in self.meas:
                i = f"{ent}:meas:{slug(it['id'])}"
            lab = it.get("name_as_printed") or "; ".join(f"{d.get('quantity')} {d.get('value')} {d.get('unit') or ''}".strip() for d in it.get("distinguished_by") or []) or it["id"]
            r = {f: "" for f in F.FIELDS}
            r.update(fact_id=i, type="activity", kind="measurement", how="stated", parent=ent, author=self.pid, method=m, evidence=ok_ev(it.get("introduced_in") or []),
                     qualifiers=f"mode={L.METHOD_MODE.get(m, 'not_stated')}", label_as_printed=lab, statement=f"measurement {it['id']} ({m or 'no method'}) of {ent}")
            self.meas[i] = r
            self.node[it["id"]] = (i, "measurement")
            self.up[i] = ent
            self.count("h", "measurement unit" + ("" if m else " without a method"))
        return rows

    def meas_of_panel(self, ent, evidence):
        """P184: the pass-0 measurement unit of this entity whose introduced_in names one of the fact's elements (a panel), else ''."""
        ev = set(evidence.split(";"))
        for pid0, (nid, role) in self.node.items():
            if role == "measurement" and self.up.get(nid) == ent and ev & set(self.p0.get(pid0, {}).get("introduced_in") or []):
                return nid
        return ""

    def model_of(self, it):
        """P168 (user): a simulation unit's printed name through step a0's lookup against the model entries (vocab_hits kind model: the
        id, the name, the aliases, this paper's symbols), as a record value goes: one id -> unit.model = id and a promoted.csv row (field
        model); none (or two) -> an unmapped row of field model, so grow.py propose lists the name as a model candidate; a never.csv
        word (or a symbol of this paper) carries its category, as in step a0. Nothing else changes."""
        name = (it.get("name_as_printed") or "").strip()
        if not name:
            return
        eid = next((e for e in it.get("introduced_in") or [] if e in self.order), self.els[0]["element_id"])
        hits = vocab_hits(self.pid, "model", name)
        if len(hits) == 1:
            (i, how), = hits.items()
            it["model"] = i
            self.promoted.append(dict(r=dict(rec={}), element=eid, field="model", printed=name, meaning=name, lookup=f"model: {how}", id=i,
                                      outcome=f"simulation {it['id']} -> model {i}"))
            self.count("h", "simulation linked to a model entry")
            self.note(f"h: simulation {it['id']} ({name!r}) -> model {i} ({how})")
            return
        nv = never_of(self.pid, name)
        self.unmapped.append(dict(element=eid, field="model", id="other", label_as_printed=name, unit="", candidate="",
                                  action=f"kept (ambiguous: {', '.join(sorted(hits))})" if hits else "kept (a simulation name no model entry has)",
                                  never=nv["category"] if nv else "", nearest=""))
        self.count("h", "simulation name unresolved (unmapped, field model)" if not hits else "simulation name ambiguous (unmapped)")

    def measurement(self, ent, method):
        """<ent>:meas:<method>; P148 (C1): "measurement" when the method is not one of the ontology's measurement methods (P184: lists.MEASUREMENT_METHODS)."""
        method = method if method in L.MEASUREMENT_METHODS else ""
        i = f"{ent}:meas:{method or 'measurement'}"
        if i not in self.meas:
            ent_row = next(r for r in self.rows_tree if r["fact_id"] == ent)
            r = {f: "" for f in F.FIELDS}
            r.update(fact_id=i, type="activity", kind="measurement", how="inferred", parent=ent, author=self.pid, method=method,   # P185: the method column too
                     qualifiers=f"mode={L.METHOD_MODE.get(method, 'not_stated')}", label_as_printed=f"{method or 'measurement'} of {ent_row['label_as_printed']}",
                     statement=f"the {method.replace('_', ' ') if method else 'unstated'} measurement of the specimen named {ent_row['label_as_printed']!r}")
            self.meas[i] = r
        return i

    def method_activity(self, method):
        """P148 (C1, retree()): <paper>:method:<method>, a measurement activity under the paper for the paper-wide records of a method."""
        i = f"{self.key}:method:{method}"
        if i not in self.meas:
            r = {f: "" for f in F.FIELDS}
            r.update(fact_id=i, type="activity", kind="measurement", how="inferred", parent=self.key, author=self.pid, method=method,   # P185
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
        """P143b, P177b (user): kb/<pid>.figures.json data through bind()'s items (P151 C1: data rows only, never a setting). A bound item
        becomes the result rows of its unit by its data role (pass 0's data role, else the legend's data-role word, else the figure stage's
        simulated mark, else the unit's role): measured -> an observation under the unit's measurement, fitted -> a model row
        (computed_by_authors), simulated -> a model row under the model run. A curve: its y quantity (or the legend's quantity), its
        legend's qualifiers and method; a point: its y value; a cell or peak: its value; a panel item: its curves, cells and peaks; an image:
        a statement-only observation under the unit's measurement of the caption's method (its records' method, else none: a photograph),
        points_ref = the image item. points_ref = the figures.json id (a point: its curve). Unbound items -> logged by reason, left out."""
        p = C.V2 / "kb" / f"{self.pid}.figures.json"
        Fj = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        tree, facts = [], []
        curves = {c["id"]: c for c in Fj.get("curves", [])}
        values = {v["id"]: v for v in Fj.get("values", [])}
        for u, cid in self.binding["refs_unknown"]:                              # C6: the third drop reason
            self.drop("1c", u, {"type": "data", "quantity": ""}, "data_id_not_in_figures_json", str(cid))

        def els(fig, panel=""):
            return list(dict.fromkeys(e for e in (f"fig{fig}{panel}", f"fig{fig}", f"fig{fig}.cap") if e in self.order))

        cur = dict(item="")

        def row(**kw):
            r = {x: "" for x in F.FIELDS}
            r.update(kw)
            r["author"] = self.pid
            r["_item"] = cur["item"]                                            # P177c: the bound item (kb/compiled/<pid>.binding.csv)
            return r

        def flagged(f, item):                                                   # P173 (user): data of a panel the rule verdict flagged: the
            if item.get("verdict") == "flagged":                                 # flag names in the fact's note, basis digitized
                f["basis"] = "digitized"
                f["definition_note"] = (item.get("uncertainty") or {}).get("note", "") or "figure-stage flags"
                self.count("1c", "data of a flagged panel (rule verdict)")

        def place(nid, role, dr):
            if role == "measurement":                                           # P184: an item bound to a measurement unit goes under it
                return ("observation", nid) if dr == "measured" else ("model", self.up.get(nid, nid))
            return ("observation", "@meas:" + nid) if dr == "measured" else ("model", nid)

        def curve_row(cu, nid, role, it, parts=None):
            parts = parse_legend(self.pid, cu.get("series", {}).get("label_raw", ""), series_axis(self.pid).get(f"fig{cu['figure']}{cu.get('panel', '')}", "")) if parts is None else parts
            q = next((x["quantity"] for x in parts if x["kind"] == "quantity"), "") or cu["y"].get("quantity")
            if q not in L.QUANTITIES:
                self.count("1c", "curve y quantity not an id"); return
            dr = it.get("data_role") or next((x["role"] for x in parts if x["kind"] == "role"), "") or ("simulated" if cu.get("kind") == "simulated" else "") \
                or ("simulated" if role in ("model_run",) else "measured")
            qual = [f"{x['qualifier']}={x['value_text']}" for x in parts if x["kind"] == "qualifier" and x.get("value_text")]
            meth = next((x["method"] for x in parts if x["kind"] == "method"), "")
            typ, parent = place(nid, role, dr)
            facts.append(row(type=typ, quantity=q, label_as_printed=cu["y"].get("label_raw", "") or q, qualifiers=";".join(qual), method=meth if meth in L.METHODS else "",
                             data_kind={"measured": "read_from_figure", "fitted": "computed_by_authors"}.get(dr, "simulated"), mentions=cu.get("series", {}).get("label_raw", ""),
                             evidence=";".join(els(cu["figure"], cu.get("panel", ""))), parent=parent, points_ref=cu["id"]))
            flagged(facts[-1], cu)
            self.count("1c", f"curve -> {typ}" + (" (legend qualifier)" if qual else "") + (" (legend method)" if meth else "") + (" (legend quantity)" if q != cu["y"].get("quantity") else ""))

        def value_row(v, nid, role, dr):
            q = v.get("quantity") or ""
            if q not in L.QUANTITIES:
                self.count("1c", f"{v.get('kind', 'value')} without a quantity id (result left out)"); return
            u = dimless((unit_symbol(v["unit"]) or v["unit"]) if v.get("unit") else "")   # P174: a unit units.yaml lacks stays as printed
            vt = v.get("value_text") or ""
            if q in CATEGORICAL_ALIASES and vt:                                 # P149 F3: a cell's value_text resolved to the value id
                hit = categorical(q, vt)
                self.count("1c", f"{q} value_text resolved (F3)" if hit else f"{q} value_text not in its value set (kept as printed)")
                vt = hit or vt
            dr = dr or ("simulated" if role == "model_run" else "measured")
            typ, parent = place(nid, role, dr)
            facts.append(row(type=typ, quantity=q, label_as_printed=v.get("label") or q, value=f"{v['value']:.6g}" if v.get("value") is not None else "", value_text=vt,
                             unit=u or "", data_kind={"measured": "read_from_figure", "fitted": "computed_by_authors"}.get(dr, "simulated"),
                             evidence=";".join(els(v["figure"], v.get("panel", ""))), parent=parent, points_ref=v["id"]))
            flagged(facts[-1], v)
            self.count("1c", f"{v.get('kind', 'value')} -> {facts[-1]['type']}")

        for inv in Fj.get("inventory", []):                                     # P174 (user): a figure's label the one path left other is an
            ev = els(inv["figure"], inv.get("panel", ""))                       # unmapped row (field axis) like any other label; a resolved
            for a in inv.get("labels") or []:                                   # axis whose printed unit units.yaml lacks, a unit row
                cand = json.dumps(dict(axis=a["axis"], label_raw=a["label_raw"], panel=inv["id"]), ensure_ascii=False)
                if a["quantity"] == "other":
                    self.unmapped.append(dict(element=ev[0] if ev else self.els[0]["element_id"], field="axis", id="other", label_as_printed=a["key"], unit=a.get("unit", ""),
                                              candidate=cand, action=f"kept (never: {a['never_label']})" if a.get("never") else f"kept (ambiguous: {', '.join(a['ambiguous'])})"
                                              if a.get("ambiguous") else "kept", never=a.get("never", ""), nearest=""))
                    self.count("1c", f"figure label other ({a['axis']})" + (", never" if a.get("never") else ", ambiguous" if a.get("ambiguous") else ""))
                elif a.get("unit_reason") in ("unit_unknown", "dimension_mismatch"):
                    self.unmapped.append(dict(element=ev[0] if ev else self.els[0]["element_id"], field="unit", id=normalize(a.get("unit", "")), label_as_printed=a["key"],
                                              unit=a.get("unit", ""), candidate=cand, action=f"kept (axis {a['unit_reason'].replace('_', ' ')}: values as printed)", never=""))
                    self.count("1c", f"figure axis {a['unit_reason'].replace('_', ' ')} (values as printed)")
        for pel, x in (self.layouts_other or {}).items():                         # P177b: a pass-0 layout 'other' with its description
            ev = [e for e in (pel, re.sub(r"[a-z]+$", "", pel)) if e in self.order]
            self.unmapped.append(dict(element=ev[0] if ev else self.els[0]["element_id"], field="layout", id="other", label_as_printed=x, unit="", candidate="",
                                      action="kept (a layout candidate)", never="", nearest=""))
        for it in self.binding["items"]:
            if not it["unit"]:
                self.count("1c", f"unbound item ({it['kind']}): {it['reason'].split(':')[0]}")
                continue
            if it["unit"] not in self.node:
                self.count("1c", f"item bound to a unit with no row ({it['kind']})"); continue
            nid, role = self.node[it["unit"]]
            cur["item"] = it["ref"]                                             # P177c: row() marks each fact with its bound item
            if role not in ("model_run", "specimen", "run", "unresolved", "measurement"):
                self.count("1c", f"item bound to a {role} (left out)"); continue
            if it["kind"] == "curve":
                curve_row(curves[it["ref"]], nid, role, it, it.get("parts"))
            elif it["kind"] == "point":
                cu = curves[it["curve"]]
                q = it.get("y_quantity") or cu["y"].get("quantity")
                if q not in L.QUANTITIES:
                    self.count("1c", "point y quantity not an id"); continue
                dr = it.get("data_role") or ("simulated" if cu.get("kind") == "simulated" else "simulated" if role == "model_run" else "measured")
                typ, parent = place(nid, role, dr)
                y = cu["points"][it["n"]][1]
                facts.append(row(type=typ, quantity=q, label_as_printed=cu["y"].get("label_raw", "") or q, value=num_text(y) if isinstance(y, (int, float)) else "",
                                 unit=dimless(cu["y"].get("unit") or ""), qualifiers=";".join(it.get("qualifiers") or []),
                                 data_kind={"measured": "read_from_figure", "fitted": "computed_by_authors"}.get(dr, "simulated"),
                                 mentions=f"{cu.get('series', {}).get('label_raw', '')} point {it['n'] + 1}".strip(), evidence=";".join(els(cu["figure"], cu.get("panel", ""))),
                                 parent=parent, points_ref=cu["id"]))
                flagged(facts[-1], cu)
                self.count("1c", f"point -> {typ}")
            elif it["kind"] in ("cell", "peak"):
                value_row(values[it["ref"]], nid, role, it.get("data_role") or "")
            elif it["kind"] == "panel":
                for r_ in it.get("results") or []:
                    if r_ in curves:
                        curve_row(curves[r_], nid, role, dict(data_role=""))
                    elif r_ in values:
                        value_row(values[r_], nid, role, "")
            elif it["kind"] == "image":
                fig = re.sub(r"^fig(\d+).*", r"\1", it["panel"])
                ms = self.cap_methods.get(f"fig{fig}.cap", collections.Counter())
                mm = self.panel_method.get(it["panel"]) or next((m for m, _ in ms.most_common() if m in L.MEASUREMENT_METHODS), "")   # P184: the panel's method first
                ent = self.run_entity(nid)[0] if role == "run" else self.up.get(nid, nid) if role == "measurement" else nid
                ev_ = ";".join(els(fig, it["panel"][len(f'fig{fig}'):]))
                par_ = nid if role == "measurement" else self.meas_of_panel(ent, ev_) or self.measurement(ent, mm)   # P184: a pass-0 measurement of the panel
                facts.append(row(type="observation", label_as_printed=f"image {it['panel']}", how="stated", evidence=";".join(els(fig, it["panel"][len(f'fig{fig}'):])),
                                 statement=f"the image of Fig. {it['panel'][3:]} (" + (mm.replace("_", " ") if mm else "a photograph") + ")" + (f": {it['file']}" if it.get("file") else ""),
                                 parent=par_, points_ref=it["ref"], data_kind="read_from_figure"))
                self.count("1c", "image -> a measurement" + (f" ({mm})" if mm else " (a photograph)"))
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
            """P184 (user): the unit's own settings, then a parent's only where the parent holds one value of that setting (several:
            not inherited, nor anything above it for that setting)."""
            v, blocked = {}, set()
            for n, a in enumerate(chain(e)):
                if a["type"] == "paper" or (a["type"] == "activity" and a["kind"] == "measurement"):
                    continue
                level = collections.defaultdict(list)
                for f in kids[a["fact_id"]]:
                    if f["type"] == "setting" and f["quantity"] and f["quantity"] != "other" and "#" in f["fact_id"]:
                        level[(f["quantity"], f["qualifiers"])].append(canon(f) if f["value"] else f["value_text"].lower())
                for k_, vals in level.items():
                    if k_ in v or k_ in blocked:
                        continue
                    if n and len(set(vals)) > 1:
                        blocked.add(k_)
                        continue
                    v[k_] = vals[0]
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
        or model with a measurement method -> <paper>:method:<method>; the rest -> the recipe (never the paper row). about = a run or a
        specimen: a setting without a measurement method -> the run's deposition (the specimen itself when the record is about a
        specimen and several specimens share that deposition); a setting with one, an observation, a derived or a model ->
        <specimen>:meas:<method> ("measurement" when the method is not a measurement method): a run's to run_entity() (P148 D: no
        measurement node under a run). about = a simulation or a
        model run: a setting -> the simulation (the model run itself when the record is about a model run and several model runs share
        that simulation); a model without a value -> the simulation; an observation, a derived or a model with a value -> the model run
        (the simulation when about = the simulation). about null or not a unit id -> the recipe, flagged. A comparison is never a
        parent. Returns (row id, the rule that placed it)."""
        rec, k = r["rec"], self.key
        t, recipe = rec["type"], f"{k}:recipe"
        mm = rec.get("method") if rec.get("method") in L.MEASUREMENT_METHODS else ""
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
        if role == "measurement":                                               # P184: a record about a measurement unit sits under it
            return rid, f"{t} about a measurement -> the measurement"
        if role == "unresolved":                                                # P176: a derived unit of role null: its settings on its row,
            if t in ("observation", "derived") or (t == "setting" and mm):     # its results under its measurement
                return self.measurement(rid, mm), f"{t} about a unit of unresolved role -> its measurement"
            return rid, f"{t} about a unit of unresolved role -> the unit"
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
        f["evidence"], f["parent"], f["author"] = ";".join(r.get("quote_elements") or [r["eid"]]), parent, self.pid   # P182: the elements a quote spans
        f["_statement"] = rec.get("statement") or rec.get("quote", "")          # P138: the extractor's own words; P139: the quote when null
        if not rec.get("statement"):
            self.count("m", "statement filled from the quote")
        f["_parent_filled"] = bool(r.get("parent_filled"))                     # P148: about null or unknown
        f["_links"] = [e for e in rec.get("links") or [] if e in self.order]    # P138: resolved to fact ids after ids()
        f["_quote"] = normalize(rec.get("quote", "")).lower()
        f["_origin"] = r.get("origin", "")                                      # P161: the condition of a unit derived from a curve
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
        compiled fact (no assumed fact); caveats and claim nodes through query; comparisons not built (D8). P179 (user): no process_mode
        is derived (the recipe field, Run.recipe_process_mode)."""
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
        """P161: a derived unit's condition (made from its legend label, not extracted) covers no element."""
        by_el = collections.defaultdict(list)
        for f in rows:
            if "#" in f["fact_id"] and not f.get("_origin"):
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
        recs = self.resolve_other(recs)                                         # P157b
        recs = self.symbol_species(recs)                                        # P178, P179 (user)
        recs = self.recipe_process_mode(recs)                                   # P179 (user)
        recs = self.qualifier_scope(recs)                                       # P182 (user)
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
        mine = collections.defaultdict(list)
        for x in self.promoted:
            mine[id(x["r"])].append(x)
        for r in recs:
            p, why = self.place(r)
            self.count("h", f"place: {why}")
            items.append(self.fact_row(r, p))
            items[-1]["_source"] = why                                          # P140 C3: the parent path, for the audit
            items[-1]["_promoted"] = mine.get(id(r), [])                         # P157b
            items[-1]["_a1"] = r.get("a1")                                       # P179: the symbol species outcome
        fig_tree, fig_facts = self.figures()
        self.specimens_for_runs(items + fig_facts)                              # P146
        self.rows_tree += fig_tree                                              # the series entities, before their measurement activities
        for f in fig_facts:
            if f["parent"].startswith("@meas:"):
                f["parent"] = self.meas_of_panel(f["parent"][6:], f["evidence"]) or self.measurement(f["parent"][6:], "")   # P184: a pass-0 measurement of that panel
        items = self.dedupe(items + self.scope_facts(fig_facts, "figure"))      # P182: figures.json facts held to the scopes
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
        self.scope_facts([f for f in rows if f.get("type") == "derived"], "derived")   # P182
        rows = self.statements(rows)
        self.coverage(rows)
        self.write_facts(rows)
        self.rows = rows
        write_csv(OUT / f"{self.pid}.coverage.csv", F.COV_FIELDS, self.cov)
        write_csv(OUT / f"{self.pid}.dropped.csv", DROPPED_FIELDS, self.dropped)
        write_csv(OUT / f"{self.pid}.unmapped.csv", UNMAPPED_FIELDS, self.unmapped)
        facts_of = collections.defaultdict(list)                                # P179 (user): every symbol species outcome with its facts (none:
        for f in rows:                                                          # dropped later); check.py --dir: a cleared species is no problem
            if f.get("_a1"):
                facts_of[id(f["_a1"])].append(f["fact_id"])
        write_csv(OUT / f"{self.pid}.qualifier_scope.csv", SCOPE_FIELDS, self.scope_rows)   # P182 (user)
        write_csv(OUT / f"{self.pid}.species.csv", SPECIES_FIELDS, [dict(x, fact_id=";".join(facts_of.get(id(x), []))) for x in self.a1_rows])
        made = collections.defaultdict(list)                                    # P177c (user): bind()'s outcome per item with the facts it gave
        for f in rows:                                                          # (check.py --dir reads it: a fact of a bound item may carry points_ref)
            if f.get("_item"):
                made[f["_item"]].append(f["fact_id"])
        write_csv(OUT / f"{self.pid}.binding.csv", BINDING_FIELDS, [dict(b, facts=";".join(made.get(b["item"], []))) for b in binding_rows(self.pid, self.binding, self.node)])
        for x in self.promoted:                                                 # P157b: the fact a promoted record became
            if not x["outcome"]:
                f = next((f for f in rows if any(y is x for y in f.get("_promoted", []))), None)
                x["outcome"] = f"fact {f['fact_id']} (type {f['type']}, quantity {f['quantity']}, parent {f['parent']})" if f else "merged by dedupe into another fact"
        write_csv(OUT / f"{self.pid}.promoted.csv", PROMOTED_FIELDS, self.promoted)
        import experiments as EX
        here, EX.HERE = EX.HERE, OUT
        try:
            EX.write(OUT / f"{self.pid}.experiments.csv", EX.table(self.pid, self.key))
        finally:
            EX.HERE = here
        return rows


def before_freeze(form):
    """P158: form.json without its allOf rules marked "P158 rule n": the rules a record or a gold row written before the freeze was made
    under (compile.py step a for lines without form_version; audit.py for the gold rows, P159)."""
    return {**form, "allOf": [x for x in form.get("allOf", []) if not str(x.get("$comment", "")).startswith("P158")]}


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


GOLD_RESOLVED = {}


def gold_rows(pid):
    """P165 (user): the gold rows of kb/pilot/<pid>.facts.csv (the file is never written) as every matcher reads them: a row of quantity
    other is read through step a0's lookup (vocab_hits on its label_as_printed: the current ids, names, aliases and this paper's
    symbols); one id -> that quantity, as the compiler would give the record. GOLD_RESOLVED[pid] lists each resolution."""
    rows = list(csv.DictReader((C.V2 / "kb" / "pilot" / f"{pid}.facts.csv").open(encoding="utf-8")))
    log = GOLD_RESOLVED.setdefault(pid, [])
    log.clear()
    for g in rows:
        if g["quantity"] == "other" and g["label_as_printed"].strip():
            hits = vocab_hits(pid, "quantity", g["label_as_printed"])
            if len(hits) == 1:
                (i, how), = hits.items()
                log.append(dict(fact_id=g["fact_id"], type=g["type"], label=g["label_as_printed"], id=i, how=how))
                g["quantity"] = i
    return rows


def diff(run):
    """Gold kb/pilot/<pid>.facts.csv (gold_rows, P165) against the compiled rows by matches() (P134 key, canonical units, D13); one gold
    row per compiled row, first come. P172: a paper without a gold file (wer21, papers 14+) has an empty diff."""
    if not (C.V2 / "kb" / "pilot" / f"{run.pid}.facts.csv").exists():
        return [], [f"no gold: kb/pilot/{run.pid}.facts.csv absent (not scored)"]
    gold = gold_rows(run.pid)
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
            ("dropped", len(run.dropped)), ("unmapped", len(run.unmapped)), ("unmapped_never", sum(1 for u in run.unmapped if u.get("never"))),
            ("promoted", sum(1 for x in run.promoted if x["id"] and not x["outcome"].startswith("not promoted")))]
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
