#!/usr/bin/env python3
"""P55: the sentence-only check. Knowledge that lives only in a fact's statement prose is invisible to every structured path and is
where a reader fills gaps from a prior (failure class 1). For every fact of the three papers this scanner pulls out of the statement
(a) species, by the aliases, formulas and names of the ontology's species entries (vocab.SPECIES, so every species added later is
covered), (b) numbers with a unit, (c) condition-like patterns without a unit (a ratio, a cycle count, a sample size), and checks
that each appears in the structured fields of the fact or of the settings it is linked to: its own value, range, uncertainty, unit,
qualifiers and value text; the condition vector of the node it sits under; for a claim the vectors of the nodes it links and the
values of the facts it links; for a derived or model fact its inputs; for a cited value the other facts of the same cited work;
and, for species, the paper's recipes (material, reactants, gases, growth surface). What is not covered is listed. A listed item
is allowed only by a row of sentence_only_allow.csv (fact id, item, reason); check.py fails on any other.

    python3 psed_v2/pilot/sentence_only.py            # the counts and the uncovered items
    python3 psed_v2/pilot/sentence_only.py --all      # also the allowed items with their reasons

Numbers that name another element (a figure, table, equation, section, reference, sample or series number, a year) are not data
and are skipped by rule, as are instrument model numbers (a letter-digit code).
"""
import collections, csv, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import query as Q  # noqa: E402

ALLOW_FILE = HERE / "sentence_only_allow.csv"

UNITS = sorted({u for u in list(L.UNIT_BASE) + list(L.UNIT_ALIAS) if u and u != "×"} | {"°C", "K", "nm", "µm", "μm", "mm", "cm", "m", "Å", "pm", "s", "min", "h", "ms", "%", "sccm", "SCCM", "Torr", "mTorr",
                                                                           "Pa", "hPa", "mbar", "eV", "keV", "kV", "MeV", "W", "mW", "V", "nA", "mA", "Ω cm", "Ω-cm", "Ωcm", "mΩ cm", "Ω/sq",
                                                                           "wt%", "at.%", "at. %", "g/cm3", "g/cm^3", "kg m-3", "nm-2", "µmol", "mmol", "mol", "cm-3", "cm^-3", "cm2/Vs",
                                                                           "Torr-s", "Torr s", "Pa s", "mTorr/min", "Å/cyc", "Å/cycle", "nm/cycle", "nm/h", "m2/g", "l",
                                                                           "kg mol-1", "g/mol", "amu", "MPa", "mol-1", "s-1", "keV", "cm-1"}, key=len, reverse=True)
UNIT_RE = "|".join(re.escape(u) for u in UNITS)
NUM = r"(?:\d{1,3}(?: \d{3})+|\d+(?:[.,]\d+)?(?:\s*[×x]\s*10\^?-?\d+)?|10\^-?\d+)"
SYM_UNITS = "|".join(re.escape(u) for u in UNITS if not u[0].isalpha())        # °C, %, Å, µm ...: no space needed
ALPHA_UNITS = "|".join(re.escape(u) for u in UNITS if u[0].isalpha())           # s, nm, eV ...: a space before, and not 'C 1s' or 'm-2 s-1'
NUM_UNIT = re.compile(rf"(?<![\w.\-])({NUM})(?:\s*(?:±|\+/-)\s*{NUM})?(?:\s*({SYM_UNITS})|\s+({ALPHA_UNITS}))(?![A-Za-z0-9\-^])")
RANGE_UNIT = re.compile(rf"(?<![\w.\-])({NUM})\s*(?:[–-]|to)\s*({NUM})(?:\s*({SYM_UNITS})|\s+({ALPHA_UNITS}))(?![A-Za-z0-9\-^])")
COND = [re.compile(r"\bratios?\s+(?:of\s+)?(\d+\.\d+|\d+)\b"), re.compile(r"\b(\d+)\s+(?:ALD\s+)?cycles?\b"), re.compile(r"\bn\s*=\s*(\d+)\b")]
SKIP = re.compile(r"(?:Fig(?:ure)?s?\.?|Table|Eq(?:n)?s?\.?|eq|Section|Sec\.|ref\.?|refs\.?|sample|samples|Series|run|runs|step|column|row|version|Region|Regions|ESI|S)\s*\(?\s*\d+[a-z]?", re.I)
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
MODEL = re.compile(r"\b[A-Z]{1,4}-?\d{2,5}[A-Z]*\b")                             # an instrument model (M-2000FI, R-150, E1200)


def species_dict():
    """normalized alias -> species id, from the ontology's species (aliases, formula, name, id). A bare element symbol (Si, Mo,
    Zn, C) is the element qualifier's business, not a species mention, and a word in the ontology's ambiguous_aliases (AR, Mo,
    Zn) never counts."""
    out = {}
    amb = {norm(a) for a in L.AMBIGUOUS}
    for sid, s in L.SPECIES.items():
        element = bool(re.fullmatch(r"[A-Z][a-z]?", s["formula"] or ""))
        for a in list(s["aliases"]) + ([] if element else [s["formula"], s["name"], sid]):
            if a and len(a) > 1 and norm(a) not in amb and not re.fullmatch(r"[A-Z][a-z]?", a):
                out[norm(a)] = sid
    return out


def norm(s):
    return re.sub(r"[ \-®™_]", "", str(s).lower()).translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")).replace("aluminium", "aluminum")


SPECIES = species_dict()
WORD = re.compile(r"[A-Za-z][A-Za-z0-9()\.,'/+\-]*[A-Za-z0-9)]|[A-Za-z]")


def species_in(text):
    """The species ids whose alias appears in the text (one to three words, normalized as Sec. 6 says)."""
    words = WORD.findall(text)
    hits = set()
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            w = norm(" ".join(words[i:i + n]).strip(".,;:()"))
            if w in SPECIES:
                hits.add(SPECIES[w])
    return hits


def numbers_in(text):
    """(number text, unit) pairs the prose prints, element numbers and years skipped."""
    t = SKIP.sub(" ", text)
    t = YEAR.sub(" ", t)
    t = MODEL.sub(" ", t)
    out = []
    for m in RANGE_UNIT.finditer(t):
        u = m.group(3) or m.group(4)
        out += [(m.group(1), u), (m.group(2), u)]
    for m in NUM_UNIT.finditer(t):
        out.append((m.group(1), m.group(2) or m.group(3)))
    for c in COND:
        for m in c.finditer(t):
            out.append((m.group(1), ""))
    return list(dict.fromkeys(out))


def tonum(s):
    s = s.replace(",", ".").replace(" ", "").replace("−", "-")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s) and "." in s and len(s.split(".")[-1]) == 3 and s.count(".") >= 1 and " " in s:
        s = s.replace(".", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)[×x]10\^?(-?\d+)", s)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    m = re.fullmatch(r"10\^(-?\d+)", s)
    if m:
        return 10.0 ** int(m.group(1))
    try:
        return float(s)
    except ValueError:
        return None


def base(v, unit):
    """A number in the base unit of its dimension (lists.UNIT_BASE), so that 48 min and 2880 s are one number; (dimension, value)."""
    u = L.UNIT_ALIAS.get(unit, unit)
    if u in L.UNIT_BASE and u not in ("°C", "K"):
        d, fac = L.UNIT_BASE[u]
        return (d, round(abs(v) * fac, 9))
    return ("", round(abs(v), 9))


def fact_numbers(f):
    out = set()
    for k in ("value", "value_min", "value_max", "uncertainty"):
        v = tonum(f.get(k, "") or "") if f.get(k) else None
        if v is not None:
            out.add(round(abs(v), 9))
            out.add(base(v, f["unit"]))
    if f.get("uncertainty_n") and tonum(f["uncertainty_n"]) is not None:
        out.add(round(abs(tonum(f["uncertainty_n"])), 9))
    for p in f["qualifiers"].split(";"):
        if "=" in p:
            v = tonum(p.split("=", 1)[1].replace("%", ""))
            if v is not None:
                out.add(round(v, 9))
    if f["value_text"]:
        for n in re.findall(r"\d+(?:\.\d+)?", f["value_text"]):
            out.add(round(float(n), 9))
    return out


def fact_species(f):
    out = set()
    for p in f["qualifiers"].split(";"):
        k, _, v = p.partition("=")
        if k in ("species", "gas", "phase", "surface") and v in L.SPECIES:
            out.add(v)
        if k == "element":                                                      # 'nitrogen' in a fact about the element N is the element, not N2
            out |= {sid for sid, s in L.SPECIES.items() if s["formula"] in (v, v + "2")}
    if f["value_text"] in L.SPECIES:
        out.add(f["value_text"])
    return out


def context(T, f):
    """The structured context of a fact: the facts whose fields may hold its prose numbers and species."""
    fs = [f]
    nid = Q.tree_of(f["fact_id"]) and f["parent"]
    node = T.byid.get(nid)
    while node is not None and "#" in node["fact_id"]:                          # up to the nearest tree row
        node = T.byid.get(node["parent"])
    nodes = [node["fact_id"]] if node else []
    for l in filter(None, f["links"].split(";") + f["inputs"].split(";")):
        if l in T.byid:
            fs.append(T.byid[l])
            nodes.append(l if "#" not in l else T.byid[l]["parent"])
    if f["type"] == "cited" and node and node["type"] == "cited":
        fs += [x for x in T.kids.get(node["fact_id"], [])]
    if f["type"] == "comparison":
        fs += [x for x in T.own(f["fact_id"])]
    for n in nodes:
        if n in T.byid and n != T.key:
            x = n
            while x in T.byid and "#" in x:
                x = T.byid[x]["parent"]
            if x in T.byid and T.byid[x]["type"] in ("activity", "entity", "comparison"):
                fs += [g for gs in T.vector(x).values() for g in gs] if T.byid[x]["type"] != "comparison" else [g for m in T.member_entities(T.byid[x]) for gs in T.vector(m).values() for g in gs]
                fs += T.own(x)
            if T.byid[x]["type"] == "comparison":
                fs += [g for m in T.member_entities(T.byid[x]) for gs in T.results(m).values() for g in gs]
    return fs


def paper_species(T):
    """The species the paper's own process settings name anywhere: its materials, reactants, gases and growth surfaces."""
    return {s for r in T.rows if "#" in r["fact_id"] and r["type"] == "setting" and r["quantity"] in ("material", "reactant_A", "reactant_B", "substrate", "carrier_gas", "gas_flow_rate", "plasma_gas_ratio", "precursor_purity")
            for s in fact_species(r)}


def scan():
    """[(fact id, kind, item)] of the items of every fact's statement that no structured field covers."""
    out = []
    for k, T in Q.TREES.items():
        ps = paper_species(T)
        for f in T.rows:
            if "#" not in f["fact_id"] or f["type"] == "caveat":
                continue
            ctx = context(T, f)
            nums = set().union(*(fact_numbers(g) for g in ctx))
            sp = set().union(*(fact_species(g) for g in ctx)) | ps
            for n, u in numbers_in(f["statement"]):
                v = tonum(n)
                if v is None:
                    continue
                v = abs(v)
                if round(v, 9) not in nums and round(v / 100, 9) not in nums and round(v * 100, 9) not in nums and base(v, u) not in nums:
                    out.append((f["fact_id"], "number", f"{n} {u}".strip()))
            for s in species_in(f["statement"]) - sp:
                out.append((f["fact_id"], "species", s))
    return out


def allowed():
    if not ALLOW_FILE.exists():
        return {}
    return {(r["fact_id"], r["item"]): r["reason"] for r in csv.DictReader(ALLOW_FILE.open(encoding="utf-8"))}


def report(show_all=False):
    items = scan()
    allow = allowed()
    left = [(i, k, x) for i, k, x in items if (i, x) not in allow and (i, "*") not in allow]
    kinds = collections.Counter(k for _, k, _ in items)
    print(f"== sentence-only (P55): {len(items)} items found in statements ({dict(kinds)}); {len(items) - len(left)} allowed with a reason; {len(left)} uncovered")
    for i, k, x in left:
        print(f"   {i}: {k} {x!r} only in prose")
    if show_all:
        for (i, x), why in allow.items():
            print(f"   allowed {i} {x!r}: {why}")
    return left


if __name__ == "__main__":
    sys.exit(1 if report("--all" in sys.argv) else 0)
