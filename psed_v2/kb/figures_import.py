#!/usr/bin/env python3
"""P84-P87: the rule-based figure importer. Reads ingest/final/<id>/figures.json and ingest/answers/figures.json, writes
kb/<id>.figures.json (the records the knowledge base loads), kb/import_report.csv (one row per paper), kb/import_panels.csv (every data
panel with its outcome and reason) and kb/problems.txt (the P86 cross-check).

    python3 psed_v2/kb/figures_import.py                 # every paper with a figures.json
    python3 psed_v2/kb/figures_import.py <paper_id> ...  # a subset (the report covers the papers run)

No model call, no PDF, no paper named in any rule. Every rule is general; a paper, figure or label is never special-cased.

P174 (user): no panel is dropped. A plot, spectrum or map panel is imported whatever its verdict and its labels. The verdict (P84: the
twelve pilot papers, judged by hand in answers/figures.json; P173: from paper 13 on, the figure stage's own flags: none -> pass, any ->
flagged) decides only whether the data are flagged: a rule verdict flagged, or for the twelve a verdict other than ok or an F5 / F6 flag,
puts the flag names on the panel, its curves and cells (verdict flagged, uncertainty note, basis digitized). F1-F4 are kept on the records
as flags. Resolution (P174, user: the one path):
  a. a label of the panel (the x and y axis titles, the series axis, a condition key) resolves as compile.py step a0 resolves a record
     key, compile.resolve_label: the generated vocab's ids, names and aliases and this paper's symbols, the text whole (never an entry's
     label). One id -> that quantity; two -> other, flagged ambiguous; none -> other with its never.csv category when a word (any paper)
     or a symbol of this paper matches. The key is the printed title inside a transform log(...)/log10(...)/ln(...) (recorded; the values
     are taken back to linear) without a trailing bracket group that is a unit units.yaml knows (the axis unit, P90b). compile.py writes
     every label left other as an unmapped row of field axis (kb/compiled/<pid>.unmapped.csv), so grow.py propose sees it.
  b. unit_raw -> canonical through ontology/units.yaml for a resolved axis; a unit units.yaml lacks, or of another dimension than the
     entry's, keeps the values as printed (unit_reason; compile.py writes a unit row); an other axis keeps its values as printed. A
     normalised axis whose denominator resolves to cycle_number reads a length unit as per cycle (the printed 'nm' of S/N).
  c. a normalised axis's denominator symbol resolves by the same path to a quantity, else a species, else stays as printed.
  d. P175 (user): a series axis naming a qualifier key (element, species, step) is no quantity (its legend names the qualifier's values); a
     series axis of two or more parts (' and ', ',') resolves part by part, its legend labels paired by compile.parse_legend.
     series labels: a number with a unit -> the series-axis quantity's value, a species or element -> species, a model or measurement
     word -> kind simulated or measured, anything else -> a replicate label kept raw, series_structure replicate. A series is simulated
     (P87) when its label is a model word or, failing a label word, when the panel's content line (else the caption's first sentence)
     holds a model word and no measurement word.
  e. every panel of every type is one inventory record (paper, figure, panel, panel_type, content, its labels and how each resolved).
Records: curve (one per series with points), value (one per cell of a map with cells, one per peak), inventory, set (P85: a plot or
map panel with two or more series is a set of kind series over the resolved series_axis; a map with cells over two resolved axes a
grid), derived (P86: plateau, half-value crossing -> penetration_depth, linear slope of thickness vs cycles -> growth_per_cycle, each
with its method and source curve). Kinds (P87): a measured series read_from_figure with the basis 'digitized', a simulated series
simulated, cells and peaks read_from_figure with the basis 'printed'.
"""
import collections, csv, datetime, json, math, re, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "kb" / "pilot"))
import lists as L  # noqa: E402
from elements import PAPERS  # noqa: E402
sys.path.insert(0, str(V2 / "kb" / "extract"))
import compile as K  # noqa: E402  P174: compile.resolve_label, the one resolution path

FINAL = V2 / "ingest" / "final"
ANSWERS = V2 / "ingest" / "answers" / "figures.json"
UNITS = yaml.safe_load((V2 / "ontology" / "units.yaml").read_text(encoding="utf-8"))["units"]
for _u in UNITS:                                                                 # YAML reads '1.0e5' as text: factors and offsets are numbers
    _u["factor"] = float(_u["factor"]); _u["offset"] = float(_u.get("offset", 0.0))
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


TRANSFORM = re.compile(r"^\s*\\?(log10|log|ln)\s*[\(\[](.+)[\)\]]\s*$", re.I)
UNIT_GROUP = re.compile(r"\s*[\(\[]([^()\[\]]*)[\)\]]\s*$")


def axis_title(label):
    """P174: a printed axis title as (transform, key, unit): a transform log(...)/log10(...)/ln(...) unwrapped; a trailing bracket group
    whose text is a unit units.yaml knows split off as the unit (P90b); the rest, as printed, is the key compile.resolve_label reads."""
    raw = str(label or "").strip()
    tr = ""
    m = TRANSFORM.match(raw)
    if m:
        tr, raw = m.group(1).lower(), m.group(2).strip()
    u = UNIT_GROUP.search(raw)
    if u and unit_of(u.group(1)) and raw[:u.start()].strip():
        return tr, raw[:u.start()].strip(), u.group(1).strip()
    return tr, raw, ""


K_B = 1.380649e-23                                                              # J/K (P109: p = n·k_B·T)
_FACT_ROWS = {}


def fact_rows(pid):
    """The paper's facts table (pilot/<pid>.facts.csv) as {fact id: row}, read once (P109: the context of a conversion)."""
    if pid not in _FACT_ROWS:
        p = V2 / "kb" / "pilot" / f"{pid}.facts.csv"
        _FACT_ROWS[pid] = {r["fact_id"]: r for r in csv.DictReader(p.open(encoding="utf-8"))} if p.exists() else {}
    return _FACT_ROWS[pid]


def context_fact(pid, fig, panel, quantity, conditions, cid=""):
    """P109: the record that gives a conversion's required quantity for a panel: the panel's own condition of it (its fact id or
    series label), else a setting or model fact of that quantity with a value on the entity whose facts cite the panel, or above it
    (parent chain); None when nothing states it. Returns (fact id, value in the record's unit, unit)."""
    c = (conditions or {}).get(quantity)
    if c and c.get("value") is not None:                                        # the curve's own condition record (its series label or panel): the curve is the context
        return (c.get("fact") or cid, float(c["value"]), c.get("unit", ""))
    rows = fact_rows(pid)
    cites = {r["parent"] for r in rows.values() if "#" in r["fact_id"] and any(ev in (f"fig{fig}{panel}", f"fig{fig}") for ev in r["evidence"].split(";"))}
    seen = set()
    for node in sorted(cites):
        while node in rows and node not in seen:
            seen.add(node)
            for r in rows.values():
                if r["parent"] == node and r["quantity"] == quantity and r["type"] in ("setting", "model") and r["value"] and "stat=" not in r["qualifiers"]:
                    try:
                        return (r["fact_id"], float(r["value"]), r["unit"])
                    except ValueError:
                        pass
            node = rows[node]["parent"]
    return None


def kelvin(v, unit):
    return v + 273.15 if unit.strip() in ("°C", "C", "degC") else v


def convert_curve(pid, c):
    """P109: for an axis whose quantity declares converts_to, the converted series stored beside the native one: quantity, unit, points
    (the other axis unchanged), the rule, the context record (kind computed_by_kb, citing it); nothing when the context is missing."""
    for ax in ("x", "y"):
        q = c[ax].get("quantity"); e = L.ENTRIES.get(q, {})
        ct = e.get("converts_to")
        if not ct or not c.get("points") or c[ax].get("unit_reason"):          # P174: values as printed are not converted
            continue
        ctx = context_fact(pid, c["figure"], c["panel"], ct["requires"], c.get("conditions"), c["id"])
        if not ctx:
            c["converted"] = dict(axis=ax, quantity=ct["target"], rule=ct["rule"], requires=ct["requires"], context=None, reason="no record of the required quantity on this panel's run")
            continue
        fid, v, u = ctx
        if ct["rule"].startswith("p = n") and ct["requires"] == "deposition_temperature":
            T = kelvin(v, u); src = UNIT_BY_SYMBOL.get(c[ax]["unit"]) or unit_of(c[ax]["unit"])
            n_fac = src["factor"] if src else 1.0                                 # to 1/m3
            pts = [[x, n * n_fac * K_B * T] if ax == "y" else [n * n_fac * K_B * T, y] for (x, y), n in zip(c["points"], [p[1] if ax == "y" else p[0] for p in c["points"]])]
            tgt = entry_unit_row(ct["target"]); unit = "Pa"
            if tgt and tgt["dimension"] == "pressure":
                pts = [[x, convert(y, UNIT_BY_SYMBOL["Pa"], tgt)] if ax == "y" else [convert(x, UNIT_BY_SYMBOL["Pa"], tgt), y] for x, y in pts]; unit = tgt["symbol"]
            c["converted"] = dict(axis=ax, quantity=ct["target"], unit=unit, points=[[g4(x), g4(y)] for x, y in pts], rule=ct["rule"], requires=ct["requires"],
                                  context=fid, context_value=v, context_unit=u, kind="computed_by_kb")


def g4(v):
    return float(f"{v:.4g}") if isinstance(v, (int, float)) else v


class Resolver:
    """Species names (series labels, a denominator): one index of every normalised species id, formula, name and alias (vocab.py). A
    quantity resolves by compile.resolve_label, the one path (P174)."""

    def __init__(self):
        self.species = collections.defaultdict(set)
        for i, s in L.SPECIES.items():
            for a in [i, s.get("formula") or "", s.get("name") or ""] + list(s.get("aliases") or []):
                if a:
                    self.species[norm(a)].add(i)

    def species_id(self, label):
        ws = str(label).split()
        if len(ws) <= 2 and (ew := L.element_word(ws[0], "", ws[1] if len(ws) == 2 else "")):   # P99: "oxygen" is an element, "oxygen gas" the molecule
            return ew[1] if ew[0] == "species" else ""
        if L.SUPPLIER_RX.fullmatch(str(label).strip()):
            return ""
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
    m = re.match(r"^\s*10\s*(?:\^\s*\{?([-+]?\d+)\}?|([-+]\d+))\s*(.*?)\s*$", t)       # '10^-3 Torr', '10-3 Torr' (flattened); P138: a caret or a sign, so '106 pm' and '1000' are numbers
    if m:
        return 10 ** int(m.group(1) or m.group(2)), None, m.group(3)
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
        self.panels = []                                                            # every data panel: outcome and reason
        self.problems = []
        ans = json.loads(ANSWERS.read_text(encoding="utf-8"))["items"] if ANSWERS.exists() else []
        self.verdict = {(v["paper_id"], str(v["figure"]), v["panel"]): v for v in ans}
        self.judged = {v["paper_id"] for v in ans}                               # P173: papers with human verdicts (the twelve)

    def label(self, axis, label_raw, key, unit, res, unit_reason=""):
        """P174: one label of the panel as the inventory keeps it (compile.py writes its unmapped row when it stays other)."""
        self.labels.append(dict(axis=axis, label_raw=label_raw, key=key, unit=unit, quantity=res["id"], how=res["how"], ambiguous=res["ambiguous"],
                                never=res["never"], never_label=res["never_label"], unit_reason=unit_reason))

    # ---- axes
    def axis(self, pid, fig, panel, ax, a):
        """One axis resolved (P174: the one path; never a reason to drop the panel): dict(quantity: an id or other, key, how, unit,
        unit_raw, label_raw, transform, dimension, unit_row, target_row, denominator, unit_reason)."""
        tr, key, ubr = axis_title(a.get("label_raw"))
        uraw = (a.get("unit_raw") or "").strip() or ubr                         # P90b: the unit inside the title's bracket
        res = K.resolve_label(pid, key)
        q = res["id"]
        out = dict(label_raw=a.get("label_raw"), unit_raw=a.get("unit_raw") or "", log=bool(a.get("log")), is_normalized=bool(a.get("is_normalized")),
                   quantity=q, key=key, how=res["how"], transform=tr, unit=uraw, unit_printed=uraw, dimension="", denominator=None, unit_row=None, target_row=None, unit_reason="")
        if q != "other":
            e = L.ENTRIES.get(q, {})
            out["dimension"] = e.get("dimension", "")
            if a.get("is_normalized") and a.get("normalization_denominator_symbol"):
                den = a["normalization_denominator_symbol"]
                dq = K.resolve_label(pid, den)["id"]
                sp = self.R.species_id(den) if dq == "other" else ""
                out["denominator"] = dict(symbol=den, quantity=dq) if dq != "other" else dict(symbol=den, species=sp) if sp else dict(symbol=den)
            row = fit_unit(uraw, q)
            if row is None:
                out["unit_reason"] = "unit_unknown" if uraw else "unit not printed"
            elif row["dimension"] != e.get("dimension") and not (row["dimension"] == "dimensionless" and e.get("dimension") == "signal"):
                out["unit_reason"] = "dimension_mismatch"
            else:
                target = entry_unit_row(q) or row
                out.update(unit=target["symbol"], unit_row=row, target_row=target)
        self.label(ax, a.get("label_raw") or "", key, uraw, res, out["unit_reason"])
        return out

    def to_canonical(self, v, ax):
        if ax["transform"]:
            v = 10 ** v if ax["transform"] in ("log", "log10") else math.exp(v)
        if not ax.get("unit_row") or ax["unit_row"]["dimension"] == "signal":   # P174: an other axis, or a unit units.yaml lacks: as printed
            return v
        return convert(v, ax["unit_row"], ax["target_row"])

    # ---- conditions and series labels
    def condition(self, pid, fig, panel, key, text):
        """A condition key and printed value resolved (the one path): dict(key_raw, raw, quantity, value, value_max, unit, role), or None
        when the key stays other (its label kept for compile.py's unmapped row)."""
        res = K.resolve_label(pid, key)
        pv = parse_value(text)
        q = res["id"]
        if q == "other":
            self.label("condition", key, key, (pv[2].strip() if pv else ""), res)
            return None
        rec = dict(key_raw=key, raw=text, quantity=q, role=L.ENTRIES.get(q, {}).get("role", ""), value=None, value_max=None, unit="")
        if pv is None:
            rec["text"] = str(text)
            self.label("condition", key, key, "", res)
            return rec
        v, vmax, u = pv
        row = fit_unit(u, q)
        target = entry_unit_row(q)
        if row and target and row["dimension"] == target["dimension"]:
            rec.update(value=convert(v, row, target), value_max=convert(vmax, row, target) if vmax is not None else None, unit=target["symbol"])
            self.label("condition", key, key, u.strip(), res)
        else:
            rec.update(value=v, value_max=vmax, unit=u.strip(), unit_unresolved=True)
            self.label("condition", key, key, u.strip(), res, "unit_unknown" if u.strip() else "unit not printed")
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
            return out
        head = re.sub(r"\s*[\(\[].*$", "", lab).strip()
        if head in ELEMENTS:
            return dict(label_raw=lab, cls="species", element=head)
        if (ew := L.element_word(head)) and ew[0] == "element":                    # P99: an element word alone is the element
            return dict(label_raw=lab, cls="species", element=ew[1])
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
                self.labels = []
                v = self.verdict.get((pid, fig, pan))
                rule = pid not in self.judged                                    # P173 (user): from paper 13 on the verdict is the rule's
                if rule:
                    v = dict(verdict="pass" if not flags else "flagged")         # no figure-stage flag -> pass; any flag -> flagged (imported)
                    why = flags
                else:                                                           # P174 (user): a verdict other than ok, or F5 / F6, flags the data
                    why = ([f"verdict {v['verdict']}"] if v and v["verdict"] != "ok" else [] if v else ["no verdict"]) + [x for x in flags if x in ("F5", "F6")]
                row = dict(paper=pid, figure=fig, panel=pan, panel_type=p["panel_type"], verdict=(("rule: " if rule else "") + v["verdict"]) if v else "",
                           flags=";".join(flags), outcome="", reason="")
                self.panels.append(row)
                inv["verdict"] = row["verdict"]
                inv["flagged"] = list(dict.fromkeys(why))
                ax = {a: self.axis(pid, fig, pan, a, p.get(a) or {}) for a in ("x", "y")}
                inv["quantities"] = [ax[a]["quantity"] for a in ("x", "y") if ax[a]["quantity"] != "other"]
                conds = {}
                for ck, cv in (p.get("conditions") or {}).items():
                    c = self.condition(pid, fig, pan, ck, cv)
                    if c:
                        conds[c["quantity"]] = c
                for a in ("x", "y"):
                    den = ax[a].get("denominator")
                    if den and den.get("quantity"):
                        conds.setdefault(den["quantity"], dict(key_raw=f"{a} denominator", raw=den["symbol"], quantity=den["quantity"], role=L.ENTRIES.get(den["quantity"], {}).get("role", ""), value=None, value_max=None, unit="", text=den["symbol"]))
                sa_raw = p.get("series_axis") or ""
                sa_q, sa_key, sa_parts = "", "", []
                if sa_raw and (len(p.get("series") or []) > 1 or p.get("cells")):
                    _, sa_key, sa_u = axis_title(sa_raw)
                    res = K.resolve_label(pid, sa_key)
                    kind_only = bool(p.get("series")) and all(len({MODEL_WORDS[w] for w in re.findall(r"[a-zA-Z]+", (s0.get("label") or "").lower()) if w in MODEL_WORDS}) == 1 for s0 in p.get("series") or []) \
                        or bool(re.search(r"\b(type|kind|model|dataset|method|geometry|shape)\s*$", sa_raw.strip().lower()))   # an axis that names a category ('sticking coefficient type', 'particle geometry'), not a quantity
                    qk, aparts = K.qualifier_key(sa_key), K.axis_parts(sa_key)
                    if qk:                                                      # P175 (user): an axis naming a qualifier key; its legend names the values
                        self.label("series", sa_raw, sa_key, "", dict(id=f"qualifier:{qk}", how=f"names the qualifier {qk}", ambiguous=[], never="", never_label=""))
                    elif len(aparts) >= 2:                                      # P175 (user): a two-quantity axis, each part on the one path
                        for part in aparts:
                            r_ = K.resolve_label(pid, part)
                            self.label("series", sa_raw, part, "", r_)
                            sa_parts.append(r_["id"])
                    elif res["id"] != "other":
                        sa_q = res["id"]
                        self.label("series", sa_raw, sa_key, sa_u, res)
                    elif not kind_only:                                         # a series axis over kinds ('model', 'type': fitted vs measured) names no quantity
                        self.label("series", sa_raw, sa_key, sa_u, res)
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
                    if lab.get("unit_unresolved"):
                        self.label("series", sa_raw, sa_key, lab["unit"], dict(id=sa_q, how="", ambiguous=[], never="", never_label=""), "unit_unknown")
                    pts = [[self.to_canonical(x, ax["x"]), self.to_canonical(y, ax["y"])] for x, y in s["points"]]
                    kind = "simulated" if (lab.get("kind") or panel_kind) == "simulated" else "read_from_figure"
                    cconds = dict(conds)
                    for c in K.parse_legend(pid, s["label"] or "", sa_raw) if sa_parts else []:   # P175: the legend's parts by order
                        q = c["quantity"]
                        if c["kind"] == "value" and q not in ("", "other") and c.get("value") is not None:
                            u_, t_ = fit_unit(c["unit"], q), entry_unit_row(q)
                            ok = u_ and t_ and u_["dimension"] == t_["dimension"]
                            cconds[q] = dict(key_raw=c["key"], raw=s["label"], quantity=q, role=L.ENTRIES.get(q, {}).get("role", ""), value=convert(c["value"], u_, t_) if ok else c["value"],
                                             value_max=None, unit=t_["symbol"] if ok else c["unit"], from_series_label=True)
                    if lab["cls"] == "numeric" and lab.get("quantity"):
                        cconds[lab["quantity"]] = dict(key_raw=sa_raw, raw=lab["label_raw"], quantity=lab["quantity"], role=L.ENTRIES[lab["quantity"]].get("role", ""),
                                                      value=lab["value"], value_max=lab.get("value_max"), unit=lab.get("unit", ""), from_series_label=True)
                    cid = f"{eid}#c{n}"
                    axd = lambda a: dict(quantity=ax[a]["quantity"], unit=ax[a]["unit"], transform=ax[a]["transform"], label_raw=ax[a]["label_raw"], unit_raw=ax[a]["unit_raw"],   # noqa: E731
                                         key=ax[a]["key"], how=ax[a]["how"], unit_reason=ax[a]["unit_reason"])
                    curves.append(dict(id=cid, figure=fig, panel=pan, series=lab, x=axd("x"), y=axd("y"),
                                       points=pts, points_raw=s["points"], conditions=cconds, conditions_raw=dict(p.get("conditions") or {}), flags=flags, kind=kind,
                                       uncertainty=dict(basis="digitized" if kind == "read_from_figure" else "", x=0.01 * (max(x for x, _ in pts) - min(x for x, _ in pts)) if ax["x"].get("unit_row") else None,
                                                        y=0.01 * (max(y for _, y in pts) - min(y for _, y in pts))),
                                       set="", provenance=dict(prov, figure=fig, panel=pan)))
                    n_imp += 1
                for c in curves:
                    out["derived"] += self.derive(c)
                sid = ""
                varied = sa_q or (";".join(sa_parts) if sa_parts and "other" not in sa_parts else "")   # P175: every part of a two-quantity axis resolved
                if len(curves) >= 2 and p["panel_type"] in ("plot", "map"):
                    if varied:
                        sid = f"{key}:cmp:{pel}"
                        out["sets"].append(dict(id=sid, figure=fig, panel=pan, kind="series", varied=varied, varied_raw=sa_raw, members=[c["id"] for c in curves],
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
                for c in curves:
                    convert_curve(pid, c)                                      # P109: a converts_to axis stores its converted series
                counts["converted"] += sum(1 for c in curves if (c.get("converted") or {}).get("context"))
                out["curves"] += curves; counts["curves"] += n_imp
                # cells (a map with printed values) and peaks (a spectrum)
                if p.get("cells"):
                    gid = f"{key}:cmp:{pel}:grid" if all(ax[a]["quantity"] != "other" for a in ("x", "y")) else ""   # P174: a grid over two resolved axes
                    at_key = lambda a: ax[a]["quantity"] if ax[a]["quantity"] != "other" else f"other:{ax[a]['key']}"   # noqa: E731
                    cq = sa_q or ("other" if sa_key else "")                    # P174: a cell quantity the one path leaves other keeps its label
                    members = []
                    for n, c in enumerate(p["cells"], 1):
                        vid = f"{eid}#v{n}"
                        val = c["value"]
                        num = parse_value(str(val)) if not isinstance(val, (int, float)) else (float(val), None, "")
                        members.append(vid)
                        out["values"].append(dict(id=vid, figure=fig, panel=pan, kind="cell", quantity=cq, value=(num[0] if num else None), value_text=(str(val) if not num else ""),
                                                  unit=(entry_unit_row(sa_q)["symbol"] if sa_q and entry_unit_row(sa_q) else ""), label=sa_key if cq == "other" else "",
                                                  at={at_key("x"): self.to_canonical(c["x"], ax["x"]), at_key("y"): self.to_canonical(c["y"], ax["y"])},
                                                  at_raw=dict(x=c["x"], y=c["y"]), conditions=conds, flags=flags, data_kind="read_from_figure", basis="printed", set=gid, provenance=dict(prov, figure=fig, panel=pan)))
                    if gid:
                        out["sets"].append(dict(id=gid, figure=fig, panel=pan, kind="grid", varied=f"{ax['x']['quantity']};{ax['y']['quantity']}", varied_raw=f"{ax['x']['label_raw']} × {ax['y']['label_raw']}",
                                                members=members, conditions=conds, label=f"Fig. {fig}{pan} grid", cell_quantity=sa_q, cell_quantity_raw=sa_raw))
                        counts["sets"] += 1
                    counts["cells"] += len(p["cells"])
                for n, pk in enumerate(p.get("peaks") or [], 1):
                    vid = f"{eid}#k{n}"
                    out["values"].append(dict(id=vid, figure=fig, panel=pan, kind="peak", quantity=ax["x"]["quantity"], value=self.to_canonical(pk["x"], ax["x"]), value_raw=pk["x"],
                                              unit=ax["x"]["unit"], label=pk.get("label", ""), conditions=conds, flags=flags, data_kind="read_from_figure", basis="printed", set="", provenance=dict(prov, figure=fig, panel=pan)))
                    counts["peaks"] += 1
                inv["labels"] = self.labels
                inv["status"] = "imported"
                other = [f"{x['axis']} '{x['key']}' other" + (" (never)" if x["never"] else " (ambiguous)" if x["ambiguous"] else "") for x in self.labels if x["quantity"] == "other"]
                row.update(outcome="imported", reason="; ".join(x for x in [row["reason"] or f"{n_imp} curves, {len(p.get('cells') or [])} cells, {len(p.get('peaks') or [])} peaks" + (f", set {sid}" if sid else ""),
                                                                       "flagged: " + ", ".join(inv["flagged"]) if inv["flagged"] else ""] + other if x))
        counts["derived"] = len(out["derived"])
        counts["labels_other"] = sum(1 for i in out["inventory"] for x in i.get("labels") or [] if x["quantity"] == "other")
        flagged = {(i["figure"], i["panel"]): i["flagged"] for i in out["inventory"] if i.get("flagged")}
        for c in out["curves"] + out["values"]:                                 # P173 / P174: a flagged panel's flag names on its curves and cells
            why = flagged.get((c["figure"], c.get("panel", "")))
            if why:
                c["verdict"] = "flagged"
                c.setdefault("uncertainty", {})
                if isinstance(c["uncertainty"], dict):
                    c["uncertainty"].setdefault("basis", "digitized")
                    c["uncertainty"]["note"] = ("figure-stage flags: " if pid not in self.judged else "flagged (P174, kept): ") + "; ".join(dict.fromkeys(why))
        out["report"] = dict(counts)
        fp = HERE / f"{pid}.figures.json"
        old = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
        if {k: v for k, v in old.items() if k != "imported_at"} != {k: v for k, v in json.loads(json.dumps(out)).items() if k != "imported_at"}:
            fp.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")   # P174: an import that changes nothing keeps the file (apply imports again)
        return out

    def derive(self, c):
        """P86: the three derived scalars of one curve, as records with method and source."""
        out = []
        xq, yq = c["x"]["quantity"], c["y"]["quantity"]
        if c["x"].get("unit_reason") or c["y"].get("unit_reason"):              # P174: an axis kept as printed derives nothing
            return []
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
    cols = ["paper_id", "key", "data_panels", "imported_panels", "curves", "cells", "peaks", "sets", "derived", "inventory_records", "labels_other"]
    rows = [dict(r, **{k: r.get(k, "") for k in cols}) for r in old]
    for r in results:
        c = r["report"]
        rows.append(dict(zip(cols, [r["paper_id"], r["key"], c.get("data_panels", 0), sum(1 for i in r["inventory"] if i["status"] == "imported"), c.get("curves", 0), c.get("cells", 0), c.get("peaks", 0), c.get("sets", 0), c.get("derived", 0), c.get("inventory", 0), c.get("labels_other", 0)])))
    rows.sort(key=lambda r: r["paper_id"])
    with rp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows({k: r.get(k, "") for k in cols} for r in rows)
    pp = HERE / "import_panels.csv"
    oldp = [r for r in csv.DictReader(pp.open(encoding="utf-8")) if r["paper"] not in done] if pp.exists() else []
    with pp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper", "figure", "panel", "panel_type", "verdict", "flags", "outcome", "reason"]); w.writeheader(); w.writerows(sorted(oldp + imp.panels, key=lambda r: (r["paper"], len(r["figure"]), r["figure"], r["panel"])))


def main(argv):
    pids = argv or sorted(p.name for p in FINAL.iterdir() if (p / "figures.json").exists())
    imp = Importer()
    results = [imp.paper(pid) for pid in pids]
    write_reports(imp, results)
    for r in results:
        c = r["report"]
        print(f"{r['paper_id']}: {c.get('data_panels', 0)} data panels, {sum(1 for i in r['inventory'] if i['status'] == 'imported')} imported; {c.get('curves', 0)} curves, {c.get('cells', 0)} cells, {c.get('peaks', 0)} peaks, "
              f"{c.get('sets', 0)} sets, {c.get('derived', 0)} derived, {c.get('converted', 0)} converted, {c.get('inventory', 0)} inventory; {c.get('labels_other', 0)} labels other "
              f"(compile.py's unmapped rows, field axis)")


if __name__ == "__main__":
    main(sys.argv[1:])
