#!/usr/bin/env python3
"""The map layer of the access tools (P63, P67, P70): concept resolution from words to ontology ids by the ontology's own matching
rules, per-paper counts of a concept from the data, the cross-paper footer, and the L0 map of the knowledge base. Nothing here is
hand-kept: every name, alias, family and count comes from vocab.py (the ontology) and the facts.

    python3 psed_v2/pilot/concept.py "penetration"      # the concept lines
    python3 psed_v2/pilot/concept.py --map              # the L0 map and the descend protocol, with the map's token count
"""
import collections, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import query as Q  # noqa: E402

SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def norm(s):
    """Sec. 6: lowercase, no spaces, hyphens, ® ™; subscript digits; aluminium -> aluminum."""
    return re.sub(r"[ \-®™_]", "", str(s).lower()).translate(SUB).replace("aluminium", "aluminum")


def words_of(s):
    return [w for w in re.findall(r"[a-z0-9]+", norm_words(s))]


def norm_words(s):
    return re.sub(r"[_\-/]", " ", str(s).lower()).translate(SUB)


# ---------------------------------------------------------------------------------------------------------------- the concept index
_INDEX = {}


def index():
    """Every concept the words may name: entries (quantities, categoricals, models, species, structures, mechanisms), families and
    categorical values; for each the normalized exact names (id, label, name, aliases) and the word sets of its names."""
    if _INDEX:
        return _INDEX
    items = {}
    for i, e in L.ENTRIES.items():
        if e.get("replaced_by"):
            continue
        names = [i, e.get("label", ""), e.get("name", "")] + list(e.get("aliases", []))
        items[i] = dict(kind=e["type"], names=[n for n in names if n])
    for fam, members in L.FAMILIES.items():
        items[f"family:{fam}"] = dict(kind="family", names=[fam, fam.replace("_", " ")])
    for key, vals in L.VALUE_ALIASES.items():
        for v, al in vals.items():
            items[f"{key}={v}"] = dict(kind="value", names=[v, v.replace("_", " ")] + list(al))
    amb = {norm(a): v for a, v in L.AMBIGUOUS_ALIASES.items()}
    exact, wordsets = {}, {}
    for i, it in items.items():
        for n in it["names"]:
            if norm(n) in amb:                                                  # an ambiguous word never names one concept (Sec. 4, 6)
                continue
            exact.setdefault(norm(n), set()).add(i)
            wordsets.setdefault(i, []).append(set(words_of(n)))
    _INDEX.update(items=items, exact=exact, wordsets=wordsets, ambiguous=amb)
    return _INDEX


def resolve(words):
    """The concept ids the words name, by the ontology's rules: an exact alias or name match (normalized) first; else the concepts
    whose name or alias contains every query word; an ambiguous word (ambiguous_aliases) lists its candidates. Returns
    (ids in order, ambiguous_note)."""
    ix = index()
    q = norm(words); qw = set(words_of(words))
    note = ""
    out = []
    if q in ix["ambiguous"]:
        cands = [c for c in ix["ambiguous"][q] if c in L.ENTRIES]
        note = f"'{words}' is ambiguous in the ontology: " + ", ".join(ix["ambiguous"][q]) + " (native = no entry)"
        out += cands
    out += sorted(ix["exact"].get(q, ()))
    if not out and qw:
        for i, sets in ix["wordsets"].items():
            if any(qw <= s for s in sets):
                out.append(i)
        out.sort(key=lambda i: (ix["items"][i]["kind"] != "quantity", min(len(s) for s in ix["wordsets"][i]), i))
    seen, uniq = set(), []
    for i in out:
        if i not in seen:
            seen.add(i); uniq.append(i)
    return uniq, note


# ---------------------------------------------------------------------------------------------------------------- counts from the data
_COUNTS = {}
HOMES = ("specimen", "input", "aggregate", "set-level", "paper", "cited")       # P81: where a value record lives (the P79 homes; cited works aside)


def home_of(T, f):
    """P81: the home of a value record: specimen (an experiment's rows, model runs included), input (an input entity), aggregate (a
    replicate set's own records), set-level (another set's own records), cited (a cited work's values), paper (no entity, no set)."""
    e = T.ent_of(f["fact_id"])
    if e:
        return "input" if Q.role(T, e) == "input" else "specimen"
    for x in T.chain(f["fact_id"]):
        n = T.byid[x]
        if n["type"] == "comparison":
            return "aggregate" if n["kind"] == "replicate" else "set-level"
        if n["type"] == "cited":
            return "cited"
    return "paper"


def counts():
    """P81: per concept id and paper, everything the knowledge base holds of it: the value records by home (HOMES: specimen, input,
    aggregate, set-level, paper, cited; 'values' their sum), settings (stated conditions), claims (cause or effect), derived (records
    computed by this knowledge base on the experiments and inputs) and, for a species, structure or mechanism, the facts that name it
    (mentions). The concept cards, the cross-paper footer and the L0 map read these counts."""
    if _COUNTS:
        return _COUNTS
    c = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for k, T in Q.TREES.items():
        for f in T.rows:
            if "#" not in f["fact_id"]:
                continue
            q = f["quantity"]
            if q and q != "other" and f["type"] != "caveat":
                if f["type"] == "setting":
                    if Q.text_of(f):
                        c[q][k]["settings"] += 1
                elif f["type"] in Q.RESULT_TYPES or f["type"] == "cited":
                    if Q.text_of(f) or f["points_ref"]:
                        c[q][k][home_of(T, f)] += 1; c[q][k]["values"] += 1
            if f["type"] == "claim":
                for t in (f["cause"] + ";" + f["effect"]).split(";"):
                    if t:
                        c[t][k]["claims"] += 1
            for p in f["qualifiers"].split(";"):
                kk, _, v = p.partition("=")
                if kk in ("species", "gas", "phase", "surface") and v in L.SPECIES:
                    c[v][k]["mentions"] += 1
            if f["value_text"] in L.SPECIES or f["value_text"] in L.STRUCTURES:
                c[f["value_text"]][k]["mentions"] += 1
        for e in Q.experiments(T) + Q.inputs(T):
            for kk, x in Q.result_records(T, e).items():
                if x["record"].get("kind") == "computed_by_kb":
                    c[kk.split("{")[0].split("[")[0]][k]["derived"] += 1
    _COUNTS.update({i: {k: dict(v) for k, v in d.items()} for i, d in c.items()})
    return _COUNTS


def derivable(q, k):
    """P81: whether a paper that holds nothing of a quantity holds every input of one of its transforms (lists.DERIVED): (transform id,
    [(input name, kind of the record found)]) for the first such transform, else None. An input given as other:<label> is a free label
    of the paper; @formula_metals is the film's formula."""
    T = Q.TREES[k]
    for did, D in L.DERIVED.items():
        if L.derived_key(did)[0] != q:
            continue
        found = []
        for spec in D["inputs"]:
            need = {a: b for a, b in (p.split("=", 1) for p in spec["quals"].split(";") if "=" in p) if not b.startswith("@")}   # the qualifiers the input must carry (a species of the material or reactant: any)
            carries = lambda f: all(Q.quals(f).get(a) == b for a, b in need.items())
            hit = None
            for alt in spec["q"].split("|"):
                if alt == "@formula_metals":
                    hit = ("the film's formula", "stated") if T.material(Q.experiments(T)[0]) in L.FORMULA_METALS else None
                elif alt.startswith("other:"):
                    f = next((f for f in T.rows if f["quantity"] == "other" and f["label_as_printed"] == alt[6:] and Q.text_of(f)), None)
                    hit = (alt[6:], Q.kind(f)) if f else None
                else:
                    f = next((f for f in T.rows if "#" in f["fact_id"] and f["quantity"] == alt and f["type"] in Q.RESULT_TYPES + ("setting", "cited") and Q.text_of(f) and carries(f)), None)
                    hit = (L.NAMES.get(alt, alt), Q.kind(f)) if f else None
                if hit:
                    break
            if not hit:
                break
            found.append(hit)
        else:
            return did, found
    return None


def family_of(i):
    """The family of a concept and its members (the entry's family; a category's members for an entry without one): (name, ids)."""
    e = L.ENTRIES.get(i, {})
    if e.get("family"):
        return e["family"], L.FAMILIES[e["family"]]
    if i.startswith("family:"):
        return i[7:], L.FAMILIES.get(i[7:], [])
    return "", []


def paper_counts(ids):
    """{paper: {values, claims, settings}} summed over the ids."""
    out = collections.defaultdict(collections.Counter)
    for i in ids:
        for k, d in counts().get(i, {}).items():
            out[k].update(d)
    return out


def footer(ids, paper=None):
    """P67: one line derived from the concepts and their families: 'also in <paper>: N values · M claims' per other paper (and
    '· K settings' where the concept is a setting there, P76), or 'not studied in: <papers>'."""
    fam_ids = set()
    for i in ids:
        fam_ids.add(i); fam_ids |= set(family_of(i)[1])
    pc = paper_counts(fam_ids)
    fams = sorted({family_of(i)[0] for i in ids if family_of(i)[0]})
    parts, absent = [], []
    for k in Q.TREES:
        if k == paper:
            continue
        d = pc.get(k, {})
        n, ns = d.get("values", 0) + d.get("mentions", 0), d.get("settings", 0)
        if n or ns or d.get("claims"):
            parts.append(f"{'also in' if paper else 'in'} {k}: {n} values · {d.get('claims', 0)} claims" + (f" · {ns} settings" if ns else "")
                         + (f" (with the famil{'ies' if len(fams) > 1 else 'y'} {', '.join(fams)})" if fams and len(fam_ids) > len(ids) else ""))
        else:
            absent.append(k)
    if not parts and not absent:
        return ""
    return " · ".join(parts) + (f" · not studied in: {', '.join(absent)}" if absent else "")


# ---------------------------------------------------------------------------------------------------------------- the concept lines (P63)
def concept_lines(words):
    """[(id, line)] for every concept the words name: id · definition · unit · family and siblings · qualifier keys · per-paper
    counts · not studied in · attribute flag; plus the ambiguity note when the word has several definitions."""
    ids, note = resolve(words)
    out = [("concept", note)] if note else []
    if not ids:
        return out
    for i in ids:
        it = index()["items"][i]
        if i.startswith("family:"):
            fam = i[7:]; members = L.FAMILIES[fam]
            out.append((i, f"family {fam}: members " + ", ".join(members) + " · " + per_paper(members)))
            continue
        if "=" in i and i not in L.ENTRIES:
            key, v = i.split("=", 1)
            out.append((i, f"value {v} of the categorical {key}"))
            continue
        e = L.ENTRIES[i]
        d = short_definition(e["definition"])
        bits = [f"{e['type']} {i}: {d}"]
        if e.get("unit"):
            bits.append(f"unit {e['unit']}")
        fam, members = family_of(i)
        if fam:
            bits.append(f"family {fam}: " + ", ".join(m for m in members if m != i) + " · the family across papers: " + per_paper(members))
        if e.get("qualifiers"):
            bits.append("qualifiers " + ", ".join(e["qualifiers"]))
        if e["type"] == "species" and L.SPECIES.get(i, {}).get("formula"):
            bits.append(f"formula {L.SPECIES[i]['formula']}")
        bits.append(per_paper([i]))
        if e.get("attribute"):
            bits.append("attribute quantity (stored as data, not a concept)")
        out.append((i, " · ".join(bits)))
    return out


def short_definition(d, n=160):
    """The first sentence of a definition, abbreviations kept (Sec., Fig., Eq.), at most n characters."""
    m = re.search(r"(?<!Sec)(?<!Fig)(?<!Eq)(?<!Figs)(?<!Eqs)(?<!al)\. (?=[A-Z])", d)
    s = d[:m.start() + 1] if m else d
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"


def per_paper(ids):
    """P81: per paper, in this order: values N (by home: specimen, input, aggregate, set-level, paper, cited), settings, claims,
    derived M (computed by this knowledge base), mentions; 'not studied in: p' only when every count is zero for p, and when a
    transform of the entry has every input in p, 'derivable in p from <inputs> (<kinds>)' instead."""
    pc = paper_counts(ids)
    have, absent, deriv = [], [], []
    for k in Q.TREES:
        d = pc.get(k, {})
        if any(d.get(x) for x in ("values", "settings", "claims", "derived", "mentions")):
            homes = ", ".join(f"{h} {d[h]}" for h in HOMES if d.get(h))
            bits = ([f"{d['values']} values" + (f" ({homes})" if homes else "")] if d.get("values") else []) \
                + [f"{d[x]} {x}" for x in ("settings", "claims") if d.get(x)] + ([f"derived {d['derived']}"] if d.get("derived") else []) \
                + ([f"{d['mentions']} mentions"] if d.get("mentions") else [])
            have.append(f"{k} " + " / ".join(bits))
        else:
            dv = derivable(ids[0], k) if len(ids) == 1 and ids[0] in L.ENTRIES else None
            if dv:
                deriv.append(f"derivable in {k} from " + ", ".join(n for n, _ in dv[1]) + " (" + ", ".join(L.PHRASES.get(kd, kd) for _, kd in dv[1]) + ")")
            else:
                absent.append(k)
    return "; ".join(have) + ("".join(f" · {x}" for x in deriv)) + (f" · not studied in: {', '.join(absent)}" if absent else "")


# ---------------------------------------------------------------------------------------------------------------- the L0 map (P70)
MAP_BUDGET = 800                    # tokens (chars/4) the map may take in the prompt
DESCEND = ("How to use the knowledge base: resolve the question's words with concept (what exists, where, under which id, how many); read "
           "grouped evidence with values (one row per specimen, comparison sets separated); open chosen ids with detail (up to 8 at once); "
           "source gives the paper's own words behind an id. Prefer one concept call over repeated searches; a call identical to an earlier "
           "one is not answered twice; the last line of values and search says where else the concept lives or that a paper does not study it. "
           "To see everything a set measured, values(set=<id>) is one call.")


def l0_map():
    """The map of the knowledge base, generated from the data: the hierarchy's top nodes and families with concept counts, and one
    line per paper (id · material · process · structure class · experiment and claim counts · headline outcome concepts). Counts and
    names only, never a conclusion or a value; the generator keeps every number a count (checked by map_numbers_are_counts)."""
    kids = collections.defaultdict(list)
    for n in L.HIERARCHY:
        kids[n["parent"]].append(n["id"])
    cat = collections.Counter(L.ENTRIES[i]["category"] for i in L.CONCEPTS if L.ENTRIES[i].get("category"))

    def under(n):
        return cat[n] + sum(under(c) for c in kids.get(n, []))
    lines = ["Knowledge base map (generated from the data):", "Concept groups (concepts): " + "; ".join(f"{n} {under(n)}" for n in kids[""]),
             "Families (members): " + "; ".join(f"{f} {len(m)}" for f, m in sorted(L.FAMILIES.items())),
             f"Species {len(L.SPECIES)}, mechanisms {len(L.MECHANISMS)}, methods {len(L.METHODS)}."]
    pc = counts()
    for k, T in Q.TREES.items():
        mats, procs, structs = set(), [], set()
        for f in T.rows:
            if f["type"] == "setting" and f["quantity"] == "material" and f["value_text"]:
                mats.add(L.species_text(f["value_text"]))
            if f["type"] == "setting" and f["quantity"] == "structure" and f["value_text"]:
                structs.add(L.STRUCTURE_CLASS.get(f["value_text"], f["value_text"]))
            if f["type"] == "setting" and f["quantity"] in ("reactant_A", "reactant_B") and f["value_text"]:
                procs.append((f["parent"], f["quantity"], L.species_text(f["value_text"])))
        pairs = collections.defaultdict(dict)
        for par, qn, sp in procs:
            pairs[par][qn] = sp
        procs = sorted({f"{d.get('reactant_A', '?')} / {d.get('reactant_B', '?')}" for d in pairs.values()})
        outs = sorted(((pc.get(q, {}).get(k, {}).get("values", 0), q) for q in L.OUTPUTS if pc.get(q, {}).get(k, {}).get("values")), reverse=True)[:6]
        n_exp = len(Q.experiments(T)); n_claims = sum(1 for f in T.rows if f["type"] == "claim")
        lines.append(f"{k}: material {', '.join(sorted(mats))} · process {', '.join(sorted(procs))} · structure {', '.join(sorted(structs))} · "
                     f"{n_exp} experiments, {n_claims} claims · main outcomes: " + ", ".join(f"{q} ({n} values)" for n, q in outs))
    return "\n".join(lines)


def map_numbers_are_counts(text=None):
    """P70 check: every number in the map is a count the generator produced (an integer in a 'N <noun>' or '<node> N' position);
    a digit inside a species formula (H2O, Mo(NtBu)2(NMe2)2) is not a number. Returns the numbers that are not counts."""
    text = text or l0_map()
    bad = []
    for m in re.finditer(r"(?<![\w.)])\d+(?:\.\d+)?(?![\w.(])", text):
        n = m.group(0)
        after = text[m.end():m.end() + 14]; before = text[max(0, m.start() - 12):m.start()]
        ok = "." not in n and (re.match(r"\s*(values|experiments|claims|members|concepts|mechanisms|methods|species|\)|;|,|\.)", after) or re.search(r"[a-z_]+ $", before))
        if not ok:
            bad.append(n)
    return bad


if __name__ == "__main__":
    if "--map" in sys.argv:
        m = l0_map(); print(m); print(DESCEND); print(f"\n[map {round(len(m) / 4)} tokens of at most {MAP_BUDGET}; numbers that are not counts: {map_numbers_are_counts(m) or 'none'}; protocol {round(len(DESCEND) / 4)} tokens]")
    else:
        for i, line in concept_lines(" ".join(a for a in sys.argv[1:])):
            print(f"[{i}] {line}")
