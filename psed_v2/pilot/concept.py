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
    if words.strip() in ix["items"] and q not in ix["exact"]:                   # an id as written whose name matches nothing else (family:conformality, phase=detected)
        out.append(words.strip())
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


def species_id(words):
    """P111: the species id the words name (an alias, formula, printed name or id of lists.SPECIES, normalised), else ''."""
    w = norm(words)
    for sid, sp in L.SPECIES.items():
        if w in {norm(x) for x in [sid, sp.get("formula", ""), sp.get("name", "")] + list(sp.get("aliases", [])) if x}:
            return sid
    return ""


def key_species(k):
    """The species-like qualifier values of a data key (species, gas, surface, phase, material)."""
    qs = k.split("{")[1].split("}")[0] if "{" in k else ""
    return {p.split("=", 1)[1] for p in qs.split(";") if "=" in p and p.split("=")[0] in ("species", "gas", "surface", "phase", "material")}


def resolve_phrase(words):
    """P105: concept() resolves like values(result=…). Returns dict(ids, keys, qualifier, note, nearest): ids = the concept ids the
    words name (resolve); else a result or setting name of the data (query.vocabulary: 'thickness in the channel', 'phase (metallic
    Mo)') gives its keys' quantities; else the longest window of the words that names quantities, the remaining words being the
    qualifier words ('initial porosity', 'MoS2 crystallinity', 'H2O exposure'), matched against the data keys of those quantities
    whose name contains every remaining word (keys). With no id at all, nearest = the three concept ids nearest by word overlap."""
    ids, note = resolve(words)
    out = dict(ids=ids, keys=[], qualifier="", note=note, nearest=[], species="")
    voc = Q.vocabulary()
    m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", words.strip())                 # P111: 'resistivity (MoS2)': the quantity with the species or material as a qualifier
    if m and species_id(m.group(2)) and not (norm(words) in {norm(n) for n in voc["keys"]}):
        q_ids = [i for i in resolve(m.group(1))[0] if i in L.ENTRIES and L.ENTRIES[i]["type"] in ("quantity", "categorical")]
        if q_ids:
            sid = species_id(m.group(2))
            keys = [k for q in q_ids for k in sorted({k for ks in voc["keys"].values() for k in ks if k.split("{")[0].split("[")[0] == q}) if sid in key_species(k)]
            out.update(ids=q_ids, keys=keys, qualifier=m.group(2).strip(), species=sid)
            return out
    nm = {norm(n): n for n in voc["keys"]}
    if norm(words) in nm and all("{" in k for k in voc["keys"][nm[norm(words)]]):   # a qualified data name ('penetration depth (50%)'): its keys and their quantities
        keys = voc["keys"][nm[norm(words)]]
        qids = sorted({k.split("{")[0].split("[")[0] for k in keys if k.split("{")[0].split("[")[0] in L.ENTRIES})
        if qids:
            out.update(keys=keys, ids=qids, qualifier=nm[norm(words)])
            return out
    if ids:
        return out
    w = [x for x in words_of(words) if x not in STOP]
    for n in range(len(w) - 1, 0, -1):                                          # the longest window that names quantities; the rest qualifies
        for a in range(len(w) - n + 1):
            win = w[a:a + n]
            cand = [i for i in resolve(" ".join(win))[0] if i in L.ENTRIES and L.ENTRIES[i]["type"] in ("quantity", "categorical")]
            if cand:
                rest = set(w[:a] + w[a + n:])
                sid = species_id(" ".join(w[:a] + w[a + n:]))                     # P111: the remaining words may name a species or material
                keys = [k for q in cand for k in sorted({k for ks in voc["keys"].values() for k in ks if k.split("{")[0].split("[")[0] == q})
                        if rest <= set(words_of(Q.name_of(k))) or (sid and sid in key_species(k))]
                out.update(ids=cand, keys=keys, qualifier=" ".join(sorted(rest)), species=sid)
                return out
    qw = set(w)
    ix = index()
    scored = []
    for i, sets in ix["wordsets"].items():
        ov = max((len(qw & s) for s in sets), default=0)
        if ov:
            scored.append((-ov, min(len(s) for s in sets), i))
    near = [i for _, _, i in sorted(scored)[:3]]
    if not near:
        import difflib
        names = {norm(n): i for i, it in ix["items"].items() for n in it["names"]}
        near = list(dict.fromkeys(names[x] for x in difflib.get_close_matches(norm(words), list(names), n=8, cutoff=0.0)))[:3]   # always three: the nearest spellings
    out["nearest"] = near
    return out


STOP = {"of", "in", "the", "a", "an", "at", "on", "for", "per", "with"}


def species_counts(qids, sid):
    """P111: per paper, the value records of the quantities on experiments whose material is the species: 'k 3 values; …'."""
    pc = collections.Counter()
    for k, T in Q.TREES.items():
        for e in Q.experiments(T):
            if T.material(e) == sid:
                pc[k] += sum(1 for kk, x in Q.result_records(T, e).items() if kk.split("{")[0].split("[")[0] in qids and (x["record"].get("text") or x["record"].get("curve")))
    return "; ".join(f"{k} {n} values" for k, n in pc.items() if n)


def key_counts(keys):
    """P105: per paper, the value and setting records under the given data keys: 'k 3 values / 1 settings; …'."""
    pc = collections.defaultdict(collections.Counter)
    ks = set(keys)
    for k, T in Q.TREES.items():
        for f in T.rows:
            if "#" in f["fact_id"] and Q.ckey(f) in ks and Q.text_of(f):
                pc[k]["settings" if f["type"] == "setting" else "values"] += 1
    return "; ".join(f"{k} " + " / ".join(f"{n} {x}" for x in ("values", "settings") if (n := d.get(x))) for k, d in pc.items() if d) or "no record under this key"


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
                    if f["data_kind"] == "computed_by_kb":                       # P86: a scalar this knowledge base derived from a curve is never the paper's value
                        c[q][k]["derived"] += 1
                    elif Q.text_of(f) or f["points_ref"]:
                        c[q][k][home_of(T, f)] += 1; c[q][k]["values"] += 1
                        if f["points_ref"]:
                            c[q][k]["curves"] += 1
                        elif f["fact_id"] in T.cells:
                            c[q][k]["cells"] += 1
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
    r = resolve_phrase(words)
    ids, note = r["ids"], r["note"]
    out = [("concept", note)] if note else []
    if not ids:                                                                 # P105: a miss suggests, never errors
        return out + [("concept", f"no concept named {words!r}" + ("; nearest: " + ", ".join(r["nearest"]) if r["nearest"] else "; nothing near it"))]
    if r["qualifier"]:                                                           # P105: the qualifier's counts first
        sp = f" (species {r['species']})" if r.get("species") else ""
        if r["keys"]:
            tail = f"keys {', '.join(Q.name_of(k) for k in r['keys'][:6])}" + (" …" if len(r["keys"]) > 6 else "") + " · " + key_counts(r["keys"])
        elif r.get("species"):                                                   # P111: no key carries the species: the records on experiments of that material
            tail = f"no data key carries it; records on experiments whose material is {L.species_text(r['species'])}: " + (species_counts(ids, r["species"]) or "none") + " · the full card follows"
        else:
            tail = "no data key of these quantities carries it; the full card follows"
        out.append(("concept", f"qualifier '{r['qualifier']}'{sp} of {', '.join(ids)}: {tail}"))
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
        if e.get("qualifiers"):
            bits.append("qualifiers " + ", ".join(e["qualifiers"]))
        if e["type"] == "species" and L.SPECIES.get(i, {}).get("formula"):
            bits.append(f"formula {L.SPECIES[i]['formula']}")
        bits.append(per_paper([i]))
        if e.get("attribute"):
            bits.append("attribute quantity (stored as data, not a concept)")
        out.append((i, " · ".join(bits)))
        out += [(i, "edge · " + t) for t in edges(i)]                            # P101: up to five edges, one line each
    return out


MAX_EDGES = 5


def edges(i):
    """P101: up to MAX_EDGES edge lines of a concept card, from existing fields only: 'ratio of a / b' (ratio_of), 'derived from
    a, b (transform)' (the transforms with the entry as output), 'input of model m' (a model's parameters), 'same family f: members'
    (family) and 'defined by paper k (symbol)' (the papers' definition facts). Every target is an id that resolves (check_edges)."""
    e = L.ENTRIES.get(i, {})
    out = []
    if e.get("converts_to"):                                                   # P109: the store-level transformation, one line
        ct = e["converts_to"]
        out.append(f"converts to {ct['target']} given {ct['requires']} ({ct['rule']}; curve() shows the converted series)")
    if e.get("ratio_of"):
        out.append("ratio of " + " / ".join(e["ratio_of"]))
    for t in L.TRANSFORMS:
        if t["output"].split("{")[0] == i:
            out.append(f"derived from {', '.join(t['inputs'])} ({t['id']})")
    models = [m for m, me in L.ENTRIES.items() if me["type"] == "model" and i in me.get("parameters", [])]
    if models:
        out.append("input of model " + ", ".join(models))
    fam, members = family_of(i)
    if fam:
        out.append(f"same family {fam}: " + ", ".join(m for m in members if m != i) + " · the family across papers: " + per_paper(members))
    defs = {}
    for k, T in Q.TREES.items():
        for f in T.rows:
            if f["type"] == "definition" and f["quantity"] == i and "#" in f["fact_id"]:
                m = re.match(r"symbol (\S+):", f["statement"])
                defs.setdefault(k, m.group(1) if m else "")
    if defs:
        out.append("defined by paper " + ", ".join(f"{k} ({sym})" if sym else k for k, sym in defs.items()))
    return out[:MAX_EDGES]


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
                + ([f"{d['curves']} curves" + (f", {d['cells']} cells" if d.get("cells") else "") + " among them"] if d.get("curves") else ([f"{d['cells']} cells among them"] if d.get("cells") else [])) \
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
           "To see everything a set measured, values(set=<id>) is one call; detail also takes a location id (a paragraph, a table cell, a figure "
           "panel or a figure) and returns the records located there. papers lists the papers one line each, filtered by material, structure, process or "
           "quantity; search without a paper gives one line per paper (the best hit, the count of further hits, the sets holding the quantity), and "
           "search(words, paper=…) opens one paper.")


_SUMM = {}


def paper_summary(k, T=None):
    """One paper's map data (P97): materials, processes (reactant A / reactant B pairs), structure classes, experiment and claim counts,
    the outcome quantities with values (by count), panel and curve counts. Counts and names only."""
    T = T or Q.TREES[k]
    pc = counts()
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
    outs = sorted(((pc.get(q, {}).get(k, {}).get("values", 0), q) for q in L.OUTPUTS if pc.get(q, {}).get(k, {}).get("values")), reverse=True)
    inv = collections.Counter(i["panel_type"] for i in T.inventory)
    modes = set()                                                                # P112: thermal | plasma | ozone per experiment, from its settings (process_mode, a plasma step or power, an ozone or radical reactant)
    for e in Q.experiments(T):
        vt = Q.vtext(T, e)
        pm = next((v for kk, v in vt.items() if kk.split("{")[0] == "process_mode"), "")
        plasma = any("step=plasma" in kk or kk.split("{")[0] in ("plasma_power", "plasma_gas_ratio", "plasma_configuration") for kk in vt) or "plasma" in pm.lower() \
            or any(L.SPECIES.get(v, {}).get("kind") == "radical" or v in ("o_atom",) for kk, v in vt.items() if kk.split("{")[0] in ("reactant_A", "reactant_B"))
        ozone = "ozone" in pm.lower() or any(v == "o3" for kk, v in vt.items() if kk.split("{")[0] in ("reactant_A", "reactant_B"))
        modes.add("plasma" if plasma else "ozone" if ozone else "thermal")
    return dict(key=k, materials=sorted(mats), processes=procs, structures=sorted(structs), modes=sorted(modes), experiments=len(Q.experiments(T)),
                claims=sum(1 for f in T.rows if f["type"] == "claim"), outcomes=outs, panels=sum(inv.values()), curves=len(T.curves))


def summaries():
    if not _SUMM:
        _SUMM.update({k: paper_summary(k, T) for k, T in Q.TREES.items()})
    return _SUMM


def paper_line(s):
    """The one line of a paper (P97): key · material · process · structure class · experiment and claim counts · main outcomes · panels, curves."""
    figs = f" · panels {s['panels']}, curves {s['curves']}" if s["panels"] else ""
    return (f"{s['key']}: material {', '.join(s['materials']) or '—'} · process {', '.join(s['processes']) or '—'}" + (f" ({', '.join(s['modes'])})" if s.get("modes") else "") + f" · structure {', '.join(s['structures']) or '—'} · "
            f"{s['experiments']} experiments, {s['claims']} claims · main outcomes: " + ", ".join(f"{q} {n}" for n, q in s["outcomes"][:4]) + figs)


def papers_lines(material=None, structure=None, process=None, quantity=None):
    """[(key, line)] of the papers that pass the filters (P97): material (a species id or its printed name), structure (a class or a
    structure id), process (words of a reactant), quantity (an id or name: papers holding values, claims or settings of it)."""
    summ = summaries()
    qids = set()
    if quantity:
        qids = {quantity} if quantity in L.ENTRIES else set(Q.concept_ids(quantity))
        qids |= {q for q, n in L.NAMES.items() if n.lower() == str(quantity).lower()}
    pc = counts()
    out = []
    msid = species_id(material) if material else ""                             # P112: a species id, formula or printed name
    for k, s in summ.items():
        if material and not any(norm(material) == norm(m) or (msid and norm(L.species_text(msid)) == norm(m)) for m in s["materials"]):
            continue
        if structure and not any(norm(structure) in (norm(x), norm(L.STRUCTURE_CLASS.get(structure, ""))) for x in s["structures"]):
            continue
        if process and not (any(norm(process) in norm(x) for x in s["processes"]) or norm(process) in {norm(x) for x in s.get("modes", [])}):   # P112: a reactant's words or a mode (thermal, plasma, ozone)
            continue
        if quantity and not any(pc.get(q, {}).get(k, {}).get(x) for q in qids for x in ("values", "claims", "settings")):
            continue
        out.append((k, paper_line(s)))
    return out


INDEX_LINES = 40


def paper_index(k, short=""):
    """P117: the paper's quantity index: one line per quantity the paper holds values for — label (id) · n values (by home, derived) ·
    range with unit · the set ids that hold it · claims n — ordered by count, at most INDEX_LINES lines (the tail collapsed into one
    '+n quantities: ids' line), then two closing lines with counts only: the figure panels by type and the model inputs. Never a value
    with its id. [(line id, text)]."""
    T = Q.TREES[k]
    pc = counts()
    qs = [(d[k]["values"], q) for q, d in pc.items() if q in L.ENTRIES and L.ENTRIES[q]["type"] in ("quantity", "categorical") and d.get(k, {}).get("values")]
    qs.sort(key=lambda x: (-x[0], x[1]))
    out = [(f"{k}:index", f"{short or k} ({k}) · quantity index: {len(qs)} quantities with values · label (id) · n values (by home) · range · sets · claims; open one with values(result=<id>, paper=\"{k}\")")]
    for n, q in qs[:INDEX_LINES]:
        d = pc[q][k]; e = L.ENTRIES[q]
        homes = ", ".join(f"{h} {d[h]}" for h in HOMES if d.get(h))
        unit = e.get("unit", "")
        vals = []
        base = lambda x: "" if x == "1" else L.UNIT_ALIAS.get(x, L.UNIT_ALIAS.get(x.replace("·", " "), x.replace("·", " ")))   # '1' is the dimensionless unit, stored as ''

        tgt = base(unit)
        for f in T.rows:                                                        # the counted value records: results and cited values, not settings, not KB-computed
            if "#" in f["fact_id"] and f["quantity"] == q and f["type"] in Q.RESULT_TYPES + ("cited",) and "stat=" not in f["qualifiers"] and f.get("data_kind") != "computed_by_kb":
                v = Q.val(f)
                if v is None:
                    continue
                u = base(f["unit"])
                if unit and u != tgt:
                    if u in L.UNIT_BASE and tgt in L.UNIT_BASE and L.UNIT_BASE[u][0] == L.UNIT_BASE[tgt][0]:
                        v = v * L.UNIT_BASE[u][1] / L.UNIT_BASE[tgt][1]
                    else:
                        continue
                vals.append(v)
        rng = (f"{Q.g(min(vals), 3)}–{Q.g(max(vals), 3)} {unit}".strip() if len(vals) > 1 and min(vals) != max(vals) else f"{Q.g(vals[0], 3)} {unit}".strip()) if vals else ("categorical" if e["type"] == "categorical" else "no numeric value")
        sets = Q.sets_with_quantity(T, {q})
        bits = [f"{L.LABELS.get(q, q)} ({q})", f"{n} values ({homes})" + (f", derived {d['derived']}" if d.get("derived") else ""), rng,
                ("sets " + ", ".join(f"[{c}]" for c in sets[:4]) + (f" +{len(sets) - 4}" if len(sets) > 4 else "")) if sets else "no set",
                f"claims {d.get('claims', 0)}"]
        out.append((f"{k}:index", " · ".join(bits)))
    if len(qs) > INDEX_LINES:
        out.append((f"{k}:index", f"+{len(qs) - INDEX_LINES} quantities: " + ", ".join(q for _, q in qs[INDEX_LINES:])))
    inv = collections.Counter(i["panel_type"] for i in T.inventory)
    out.append((f"{k}:index", f"figure panels {sum(inv.values())}" + (" (" + ", ".join(f"{t} {n}" for t, n in inv.most_common()) + ")" if inv else "") + f" · curves {len(T.curves)}"))
    inputs_n = sum(1 for f in T.rows if "#" in f["fact_id"] and f.get("data_kind") == "model_input" and Q.text_of(f))
    out.append((f"{k}:index", f"model inputs {inputs_n} · input entities {len(Q.inputs(T))} · experiments {len(Q.experiments(T))} · claims {sum(1 for f in T.rows if f['type'] == 'claim')}"))
    return out


PROMPT_INDEX_BUDGET = 300                                                       # P120: tokens per paper line in the kb prompt


def prompt_index(names=None, pc=None, keys=None):
    """P120: the compact paper index of the kb prompt, from concept.counts (the P117 source): one line per paper — key (short name) ·
    <quantity id> n, … (every quantity with values, by count) · claims n · panels n · curves n. No labels, ranges, set ids or values;
    at most PROMPT_INDEX_BUDGET tokens per paper. names = {key: short name}; pc, keys override the counts and papers (the 58-paper
    simulation of check_map)."""
    pc = pc if pc is not None else counts()
    keys = keys if keys is not None else list(Q.TREES)
    out = ["Paper index (every quantity each paper holds values for, by count; open a paper with values(paper=<key>)):"]
    for k in keys:
        qs = sorted(((d[k]["values"], q) for q, d in pc.items() if q in L.ENTRIES and L.ENTRIES[q]["type"] in ("quantity", "categorical") and d.get(k, {}).get("values")), key=lambda x: (-x[0], x[1]))
        T = Q.TREES.get(k)
        claims = sum(1 for f in T.rows if f["type"] == "claim") if T else 0
        line = f"{k}" + (f" ({names[k]})" if names and k in names else "") + " · " + ", ".join(f"{q} {n}" for n, q in qs) + f" · claims {claims} · panels {len(T.inventory) if T else 0} · curves {len(T.curves) if T else 0}"
        while len(line) // 4 > PROMPT_INDEX_BUDGET and qs:                       # over the budget: the smallest counts fold into '+n more'
            qs = qs[:-1]
            line = f"{k}" + (f" ({names[k]})" if names and k in names else "") + " · " + ", ".join(f"{q} {n}" for n, q in qs) + f" +{len(qs)} more · claims {claims} · panels {len(T.inventory) if T else 0} · curves {len(T.curves) if T else 0}"
        out.append(line)
    return "\n".join(out)


def l0_map(summ=None):
    """The map of the knowledge base, generated from the data (P70, P97): corpus-level counts only: papers, the hierarchy's top nodes and
    families with concept counts, species, structures, mechanisms and methods, the materials and structure classes with their paper counts,
    and the ten most populated quantities with their paper counts; the per-paper lines live in papers(). Counts and names only, never a
    conclusion or a value; the generator keeps every number a count (checked by map_numbers_are_counts)."""
    summ = summ if summ is not None else summaries()
    kids = collections.defaultdict(list)
    for n in L.HIERARCHY:
        kids[n["parent"]].append(n["id"])
    cat = collections.Counter(L.ENTRIES[i]["category"] for i in L.CONCEPTS if L.ENTRIES[i].get("category"))

    def under(n):
        return cat[n] + sum(under(c) for c in kids.get(n, []))
    mats = collections.Counter(m for s in summ.values() for m in s["materials"])
    structs = collections.Counter(x for s in summ.values() for x in s["structures"])
    qpap = collections.Counter(q for s in summ.values() for _, q in s["outcomes"])
    lines = ["Knowledge base map (generated from the data):", f"Papers {len(summ)} (one line each: papers(material=…, structure=…, process=…, quantity=…)).",
             "Concept groups (concepts): " + "; ".join(f"{n} {under(n)}" for n in kids[""]),
             "Families (members): " + "; ".join(f"{f} {len(m)}" for f, m in sorted(L.FAMILIES.items())),
             f"Species {len(L.SPECIES)}, structures {len(L.STRUCTURES)}, mechanisms {len(L.MECHANISMS)}, methods {len(L.METHODS)}.",
             "Materials (papers): " + "; ".join(f"{m} {n}" for m, n in mats.most_common()),
             "Structure classes (papers): " + "; ".join(f"{x} {n}" for x, n in structs.most_common()),
             "Most populated quantities (papers with values): " + "; ".join(f"{q} {n}" for q, n in qpap.most_common(10))]
    return "\n".join(lines)


def map_numbers_are_counts(text=None):
    """P70 check: every number in the map is a count the generator produced (an integer in a 'N <noun>' or '<node> N' position);
    a digit inside a species formula (H2O, Mo(NtBu)2(NMe2)2) is not a number. Returns the numbers that are not counts."""
    text = text or l0_map()
    bad = []
    for m in re.finditer(r"(?<![\w.)])\d+(?:\.\d+)?(?![\w.(])", text):
        n = m.group(0)
        after = text[m.end():m.end() + 14]; before = text[max(0, m.start() - 12):m.start()]
        ok = "." not in n and (re.match(r"\s*(values|experiments|claims|members|concepts|mechanisms|methods|species|structures|curves|\)|;|,|\.)", after) or re.search(r"[A-Za-z_]+ $", before))
        if not ok:
            bad.append(n)
    return bad


if __name__ == "__main__":
    if "--map" in sys.argv:
        m = l0_map(); print(m); print(DESCEND); print(f"\n[map {round(len(m) / 4)} tokens of at most {MAP_BUDGET}; numbers that are not counts: {map_numbers_are_counts(m) or 'none'}; protocol {round(len(DESCEND) / 4)} tokens]")
    else:
        for i, line in concept_lines(" ".join(a for a in sys.argv[1:])):
            print(f"[{i}] {line}")
