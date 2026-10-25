#!/usr/bin/env python3
"""P155: the ontology growth pipeline, one round at a time. No provider call, ever: a paper enters only when pass 0 and pass 1 ran.

    python3 psed_v2/ontology/grow.py init                  # round 0 (once): history rows reconstructed for every entry, rounds.csv row 0
    python3 psed_v2/ontology/grow.py add <pid> [<pid> ...] # open a round on extracted papers
    python3 psed_v2/ontology/grow.py propose               # their compiled unmapped lists -> candidates in pending.csv and decide.html
    python3 psed_v2/ontology/grow.py apply                 # the user's decisions -> ontology.yaml, never.csv, history.csv; export, check,
                                                           # recompile, score, ontology.html, one commit
    python3 psed_v2/ontology/grow.py status                # the open round, pending counts by decision, the last history rows
    python3 psed_v2/ontology/grow.py report                # ontology.html only
    python3 psed_v2/ontology/grow.py audit <round>         # P157d: A1-A3 of a round and its acceptance (apply runs it after every round)
    python3 psed_v2/ontology/grow.py run <paper> [<paper> <paper>] [--plan] [--yes]   # P172: papers 14+ end to end with gates, to decide.html

Files in ontology/: rounds.csv (one row per round), history.csv (append-only, one row per decision), pending.csv (export.PENDING_COLUMNS),
never.csv (the never-an-entry labels), decide.html (the decision form propose writes), ontology.html (the one report).

The user decides in decide.html, downloads pending.csv over ontology/pending.csv and runs apply. A candidate is a group of compiled
unmapped rows (kb/compiled/<pid>.unmapped.csv) with one normalized label (casefold, the trailing unit bracket stripped, whitespace
collapsed), across the round and the earlier undecided rows; its id is the label in snake case. The printed labels of a candidate are read
back from those rows (printed_labels); the paper text is never read. DOIs come from corpus/manifest.csv (ingest/final/<pid>/ holds no
metadata file). Held-out papers (kb/extract/common.py HELD_OUT) are refused and never shown. Imports nothing of the project but export.
P157b: never.csv is applied by kb/extract/compile.py (unmapped.csv column never, export.never_index); propose drops those rows and does no
never matching of its own; decide.html shows the candidates found in two or more papers first. P162: an unmapped row of a paper of an
applied round that its apply snapshot does not hold (born after apply) is carried into the next propose (carried_rows), not an A3 failure.
"""
import argparse
import ast
import csv
import datetime
import hashlib
import html
import io
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
ROOT = V2.parent
sys.path.insert(0, str(HERE))
import export as X  # noqa: E402

ONTO = HERE / "ontology.yaml"
ROUNDS, HISTORY, PENDING, NEVER = HERE / "rounds.csv", HERE / "history.csv", HERE / "pending.csv", HERE / "never.csv"
DECIDE, REPORT = HERE / "decide.html", HERE / "ontology.html"                # P174: ontology/unmapped.csv deleted (a figure label is a compiled unmapped row)
GATES_CSV = HERE / "gates.csv"                                                  # P172: written by kb/extract/gates.py reference
COMPILED, RECORDS, FINAL = V2 / "kb" / "compiled", V2 / "kb" / "records", V2 / "ingest" / "final"
ROUND_COLS = ["round", "opened", "applied", "pids", "dois", "status", "n_candidates", "n_accepted", "n_alias", "n_rejected", "n_never"]
DECISION_COLS = ["class", "category", "slot", "parameters", "symbol_paper"]   # P175 (user): what apply reads besides the decision (pending.csv)
HISTORY_COLS = ["date", "round", "action", "id", "kind", "target", "source_pids", "source_dois", "decided_by", "reason", "ontology_sha256_after"] + DECISION_COLS + ["species"]   # P179c (user): a symbol decision may carry the species its subscript denotes
NEVER_COLS = ["label", "category", "paper", "source", "symbol"]                 # P157d: symbol yes = matched only in its paper
STOP_WORDS = {"of", "the", "an", "and", "or", "in", "on", "at", "to", "for", "by", "with", "is", "as", "from", "per", "its", "a"}


class Stop(Exception):
    pass


def literal(path, name):
    """The first module-level assignment `name = <literal>` of a file, read with ast (the module is not imported)."""
    for n in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise KeyError(f"{name} in {path}")


PAPERS = literal(V2 / "kb" / "pilot" / "elements.py", "PAPERS")              # pid -> paper key
HELD_KEYS = set(literal(V2 / "kb" / "extract" / "common.py", "HELD_OUT"))
HELD = HELD_KEYS | {p for p, k in PAPERS.items() if k in HELD_KEYS}
KEY2PID = {k: p for p, k in PAPERS.items()}
KEY2PID.update({k: v.rstrip(".") for k, v in re.findall(r"(\w+) = (10\.[\w.\-]+)", "\n".join(l for l in ONTO.read_text(encoding="utf-8").splitlines()[:4] if l.startswith("#")))})   # the header's evidence keys
HELD_RX = re.compile(r"\b(" + "|".join(re.escape(h) for h in sorted(HELD)) + r")\b") if HELD else None   # P157f: none while papers 13+ do not exist


def doi_of():
    return {r["paper_id"]: r["doi"] for r in rd(V2 / "corpus" / "manifest.csv")}


# ---------------------------------------------------------------- files
_PAPER_VERSION = {}


def paper_version(key):
    """P200 (user): compile.paper_version (the paper's latest accepted version, whose pass-1 lines compile reads), read in a subprocess
    (as paper_index), once per paper."""
    if key not in _PAPER_VERSION:
        code = f"import sys, json; sys.path.insert(0, {str(V2 / 'kb' / 'extract')!r}); import compile; print(json.dumps(compile.paper_version({key!r})))"
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
        _PAPER_VERSION[key] = json.loads(out.strip().splitlines()[-1])
    return _PAPER_VERSION[key]


def retired_by(pid, element, label, unit=False):
    """P187 (user): the form version that retired a decision's row: a version accepted for this paper alone (ontology/form_versions.csv,
    a row with the paper) whose pass-1 lines answer the element, none of its records there carrying the label as quantity other (the
    adopted re-extraction no longer prints it). '' when no such version, or when the adopted lines still give the label as other.
    P191 (user): unit=True, a unit row: retired when none of those records carries the label as other with a unit (no unit row printed).
    P200 (user): the version is the one whose lines compile reads (paper_version: the paper's latest accepted version), no own list."""
    key = PAPERS.get(pid, pid)
    acc = [paper_version(key)] if paper_version(key) else []
    path = RECORDS / f"{pid}.jsonl"
    if not acc or not path.exists():
        return ""
    lab, seen = X.norm_label(label), ""
    for ln in path.read_text(encoding="utf-8").splitlines():
        x = json.loads(ln) if ln.strip() else {}
        if x.get("pass") != 1 or x.get("form_version") not in acc:
            continue
        txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", (x.get("response") or "").strip())
        try:
            resp = json.loads(txt)
        except ValueError:
            continue
        for a in resp.get("answers") or [] if isinstance(resp, dict) else []:
            if isinstance(a, dict) and a.get("id") == element:
                seen = x["form_version"]
                if any(isinstance(r, dict) and r.get("quantity") == "other" and X.norm_label(str(r.get("label_as_printed") or "")) == lab and (r.get("unit") or not unit)
                       for r in a.get("records") or []):
                    return ""
    return seen


def rd(p):
    return list(csv.DictReader(p.open(newline="", encoding="utf-8"))) if p.exists() else []


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore", restval="")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write(p, cols, rows):
    p.write_text(csv_text(cols, rows), encoding="utf-8")


def append(p, cols, rows):
    """history.csv is append-only: rows go after the last line, the header is written once."""
    if not p.exists():
        write(p, cols, [])
    with p.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=cols, lineterminator="\n", restval="").writerows(rows)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def today():
    return datetime.date.today().isoformat()


def onto():
    return yaml.safe_load(ONTO.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- labels, candidates (pending_decide.py's grouping and rule hints, P98/P131b)
def norm(label):
    """The normalized label: casefold, the trailing unit bracket stripped, whitespace collapsed."""
    return " ".join(X.strip_unit(label or "").casefold().split())


def snake(label):
    return re.sub(r"[^a-z0-9]+", "_", norm(label)).strip("_")


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", str(text).casefold()) if len(t) > 1 and t not in STOP_WORDS}


def nearest(label, entries):
    """(id, definition, score): the entry whose id, aliases or definition share the most tokens with the label (ties: the most shared with id
    and aliases, then the id); ('', '', 0) when none shares one."""
    want = tokens(label)
    best = ("", "", 0, 0)
    for e in entries:
        head = tokens(e["id"].replace("_", " ")) | {t for a in e.get("aliases") or [] for t in tokens(a)}
        s, h = len(want & (head | tokens(e.get("definition", "")))), len(want & head)
        if s and ((s, h) > best[2:] or ((s, h) == best[2:] and e["id"] < best[0])):
            best = (e["id"], e.get("definition", ""), s, h)
    return best[:3]


def unmapped_rows(pid):
    """A paper's compiled unmapped rows, every one: element, field, the label as printed, unit, the record's symbol, definition (the
    candidate's definition_quote), quote (the definition, else the label, else the unit), never (P157b: compile.py's never column,
    the never.csv category of the record's label) and text (P157d: export.record_text, the one record key: the label, else the meaning)."""
    out = []
    for r in rd(COMPILED / f"{pid}.unmapped.csv"):
        cand = json.loads(r["candidate"]) if r["candidate"].startswith("{") else {}
        d = " ".join((cand.get("definition_quote") or "").split())
        out.append(dict(pid=pid, element=r["element"], field=r["field"], label=r["label_as_printed"].strip(), unit=r["unit"], symbol=(cand.get("symbol") or "").strip(),
                        definition=d, quote=d or r["label_as_printed"].strip() or r["unit"], never=r.get("never", ""), text=X.record_text(r), action=r.get("action", "")))
    return out


# P157b: the label normalization (norm_label, P156 FIX 2b) and the never index moved to export.py; compile.py applies never.csv, propose
# reads its never column. Here only the symbol-table grouping (P156 FIX 1).
def norm_symbol(s):
    """A symbol for equality within one paper: LaTeX unwrapped, braces, backslashes, ^, _ and spaces removed; case kept (R is not r)."""
    return re.sub(r"[\s{}\\^_]", "", X.LATEX_TEXT.sub(r"\1", str(s)))


ARTICLES = {"a", "an", "the", "of"}


def words(s):
    """FIX 1: a label as words for the equation / symbol-table merge: trailing units and LaTeX stripped, casefold, articles and 'of' dropped,
    sorted (word order ignored: eq11 'rate of adsorption' = tabu1 'Adsorption rate')."""
    return sorted(w for w in re.findall(r"[a-z0-9]+", X.strip_latex(X.strip_trailing_units(s)).casefold()) if w not in ARTICLES)


SYMBOL_LAYOUT = next(k for k, d, _ in X.layouts("table") if "symbol table" in d)          # P143, P177b (ontology.yaml layouts): not_units, 'a symbol table ...'
SYMBOL_ROLES = re.search(r"symbol table \(([^)]*)\)", {k: d for k, d, _ in X.layouts("table")}[SYMBOL_LAYOUT]).group(1).split(", ")   # ['symbol', 'meaning', 'value']: no unit column


def pass0_tables(pid):
    """{table id: layout} of the pass-0 line compile.py read for the paper (its compile.log names the line)."""
    log = COMPILED / f"{pid}.compile.log"
    m = re.search(r"pass 0 = line (\d+)", log.read_text(encoding="utf-8")) if log.exists() else None
    if not m:
        return {}
    lines = [x for x in (RECORDS / f"{pid}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    obj = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", json.loads(lines[int(m.group(1)) - 1])["response"].strip()))
    return {t["table"]: t["layout"] for t in (obj.get("table_layouts") or []) if isinstance(t, dict)} if isinstance(obj, dict) else {}


def unit_spellings():
    return {str(v) for u in yaml.safe_load((HERE / "units.yaml").read_text(encoding="utf-8"))["units"] for v in [u["symbol"]] + list(u["variants"])}


def candidates(pids, extra=()):
    """P156: the candidates of a set of papers from their compiled unmapped rows, and the log of how they were made. P162: extra = rows
    carried from papers of applied rounds (carried_rows), taken in beside the papers' own rows, by the same steps.

    1. A row of a symbol-table layout (pass 0: P143 not_units, whose definition names the roles symbol, meaning, value; the record carries a
       symbol) groups by table row and symbol: the cell whose text is the symbol is the symbol column, the other cell (or, when its text is
       empty, the record's definition) is the meaning column, which gives the label, the id and the definition; the symbol becomes an alias.
       The layout has no unit column: the unit is the records'. A symbol with no meaning cell in its row stays its own candidate, noted.
    2. A row elsewhere in the same paper whose label is its symbol joins the one symbol-table row with that symbol; else a row whose label (a
       symbol's: its definition) has the words of one symbol-table meaning (words(): articles and 'of' dropped, order ignored) joins it.
    3. P157b: a row compile.py marked never (its never column) is dropped; a symbol-table group with a never row is dropped with the rows
       that joined it. grow.py does no never matching of its own.
    4. A row with no record key (P157d: export.record_text, the label else the meaning of its definition), or a label that is only a unit
       spelling of units.yaml, is a value without a quantity, not a candidate (FIX 3).
    5. The rest group across the papers by their record key, the id built with the unit group stripped (snake case of norm()).
    P157d: a candidate's symbols ([(text, pid)]: the symbol of its table row, the rows joined by their symbol) go into ontology.yaml symbols
    on accept and into never.csv as paper-local rows on never.
    6. P175 (user): candidates merge only when their record keys are identical (the P163 label-prefix merge and its P170 patch removed).
    7. P177b: a row of field layout (a pass-0 layout 'other' and its description) makes a candidate of kind layout.
       P168: a row of field model (a simulation unit's printed name no model entry has) makes a candidate of kind model (P170: any member
       of that field; a pass-1 record of the same printed name joins it); a row whose
       field is a categorical (an unresolved material, structure, ... value) makes none (log categorical).
    Returns ({id: group}, log)."""
    spell = unit_spellings()
    log = dict(table_groups=[], symbol_merges=[], label_merges=[], ambiguous=[], never=[], values=[], categorical=[], model_names=[])
    categ = {e["id"] for e in onto()["entries"] if e.get("type") == "categorical"}   # P168: a categorical's value row is no candidate
    tables, rest = defaultdict(list), []
    carried = defaultdict(list)
    for u in extra:
        carried[u["pid"]].append(u)
    for pid, rows in [(p, unmapped_rows(p)) for p in pids] + [(p, us) for p, us in carried.items() if p not in pids]:
        layouts = pass0_tables(pid)
        own = {(u["element"], u["label"]): u["symbol"] for u in rows if u["field"] == "quantity" and u["symbol"]}
        for u in rows:
            if u["field"] in categ:                                             # P168 (user): its unit is nothing; no "unit" candidate
                log["categorical"].append(u)
                continue
            if u.get("action", "").startswith(("kept (names the model ", "kept (names the method ")):   # P172, P176: a record naming a model or a method entry is no quantity candidate
                log["model_names"].append(u)
                continue
            if u["field"] == "unit" and not u["symbol"]:                       # a unit row follows the quantity row of its cell and label
                u["symbol"] = own.get((u["element"], u["label"]), "")
            m = re.match(r"^(tab\w*)\.(r\d+)c\d+$", u["element"])
            if m and layouts.get(m.group(1)) == SYMBOL_LAYOUT and u["symbol"]:
                tables[(pid, f"{m.group(1)}.{m.group(2)}", norm_symbol(u["symbol"]))].append(u)
            elif not u["text"] or (u["label"] in spell and not (u["symbol"] and norm_symbol(u["label"]) == norm_symbol(u["symbol"]))):
                log["values"].append(u)                                         # FIX 3: no label, or a unit spelling that is not the record's own symbol
            else:
                rest.append(u)
    groups, by_sym, by_cell = [], defaultdict(list), {}
    for (pid, row, sym), us in tables.items():
        symcell = [u for u in us if u["label"] and norm_symbol(u["label"]) == sym]
        meaning = next((u["label"] for u in us if u["label"] and norm_symbol(u["label"]) != sym), "") \
            or next((X.strip_trailing_units(u["definition"]) for u in us if u["definition"]), "")
        symbol = symcell[0]["label"] if symcell else us[0]["symbol"]
        g = dict(label=meaning or symbol, aliases=[symbol] if meaning else [], symbols=[(symbol, pid)] if meaning else [], definition=meaning,
                 members=list(us), pid=pid, row=row, note="" if meaning else f"symbol with no meaning cell in table row {row}")
        groups.append(g)
        by_sym[(pid, sym)].append(g)
        by_cell.update({(pid, u["element"]): g for u in us})
        log["table_groups"].append(g)
    log["same_cell"] = []
    for u in rest:
        if (u["pid"], u["element"]) in by_cell:                                 # a unit row of a symbol-table cell joins its cell's row
            by_cell[(u["pid"], u["element"])]["members"].append(u)
            log["same_cell"].append(u)
            continue
        sym = norm_symbol(u["symbol"]) if u["symbol"] else ""
        is_symbol = bool(sym) and norm_symbol(u["label"]) == sym
        hits = by_sym.get((u["pid"], sym), []) if is_symbol else []
        if len(hits) == 1:
            hits[0]["members"].append(u)
            hits[0]["aliases"] += [u["label"]] if u["label"] not in hits[0]["aliases"] else []
            hits[0]["symbols"].append((u["label"], u["pid"]))
            log["symbol_merges"].append((u, hits[0]))
            continue
        if len(hits) > 1:
            log["ambiguous"].append((u, [h["row"] for h in hits]))
        if u["never"]:
            log["never"].append((u, u["never"]))
            continue
        text = X.strip_trailing_units(u["definition"]) if is_symbol and u["definition"] else u["label"]
        lw = words(text)
        same = [g for g in groups if g.get("row") and g["pid"] == u["pid"] and g["definition"] and words(g["definition"]) == lw] if lw else []
        if len(same) == 1:
            same[0]["members"].append(u)
            if is_symbol and u["label"] not in same[0]["aliases"]:
                same[0]["aliases"].append(u["label"])
            if is_symbol:
                same[0]["symbols"].append((u["label"], u["pid"]))
            log["label_merges"].append((u, same[0], text))
            continue
        groups.append(dict(label=u["text"], aliases=[], symbols=[], definition=u["definition"], members=[u], pid=u["pid"], row="", note=""))
    out = {}
    for g in groups:
        nv = next((u["never"] for u in g["members"] if u["never"]), "")
        if nv:
            log["never"] += [(u, u["never"] or f"{nv} (in a never group)") for u in g["members"]]
            continue
        cid = snake(g["label"])
        if not cid:
            log["values"] += g["members"]
            continue
        c = out.setdefault(cid, dict(id=cid, label=g["label"], aliases=[], symbols=[], definition="", members=[], notes=[]))
        c["aliases"] += [a for a in g["aliases"] if a not in c["aliases"] and a != c["label"]]
        c["symbols"] += [x for x in g["symbols"] if x not in c["symbols"] and x[0] != c["label"]]
        c["definition"] = c["definition"] or g["definition"]
        c["members"] += g["members"]
        c["notes"] += [g["note"]] if g["note"] else []
    for c in out.values():
        units = Counter(u["unit"] for u in c["members"] if u["unit"])
        c["unit"] = units.most_common(1)[0][0] if units else ""
        c["kind"] = "layout" if any(u["field"] == "layout" for u in c["members"]) else "model" if any(u["field"] == "model" for u in c["members"]) else \
            "quantity" if units or any(re.search(r"\d", u["label"] + u["quote"]) for u in c["members"]) or any(u["field"] in ("quantity", "axis") for u in c["members"]) else "unit"   # P168: a simulation name; P174: a figure label
        ev = {}
        for u in c["members"]:
            ev.setdefault(u["pid"], f"{u['pid']}:{u['element']} — {u['quote']}" + (f" ({'; '.join(c['notes'])})" if c["notes"] else ""))
        c["evidence"] = ev
    return out, log


_CAND = {}


def round_candidates(pids):
    """P162: a round's candidates: its papers' rows and the rows carried from the papers of applied rounds (carried_rows). propose and the
    apply snapshot read the same set."""
    key = tuple(sorted(p for p in pids if p)) + ("+carried",)
    if key not in _CAND:
        _CAND[key] = candidates(key[:-1], extra=carried_rows(key[:-1]))
    return _CAND[key]


def candidates_of(pids):
    key = tuple(sorted(p for p in pids if p))
    if key not in _CAND:
        _CAND[key] = candidates(key)
    return _CAND[key]


def candidate_of(row):
    """P164: a pending row's candidate: by its id, else (an id the user edited in pending.csv) the one candidate of its papers with the
    same evidence items; a pilot row: none."""
    if row["first_round"] in ("", "0"):
        return None
    cands = candidates_of(row["pids"].split(";"))[0]
    if row["id"] in cands:
        return cands[row["id"]]
    ev = sorted(evidence_items(row))
    hits = [c for c in cands.values() if sorted(c["evidence"].values()) == ev]
    return hits[0] if len(hits) == 1 else None                                 # P175: the note names nothing (a memo)


def printed_labels(row):
    """The printed labels behind a pending row: its candidate's label, then its aliases (the symbols); a pilot row: its id. P172: a row of a
    round whose candidate is gone (its rows closed meanwhile) and whose evidence is one 'pid:element — <printed>' item: that printed label."""
    c = candidate_of(row)
    if c:                                                                       # P176: and every member's printed label (one record key,
        return list(dict.fromkeys([c["label"]] + c["aliases"] + [u["label"] for u in c["members"] if u["label"]]))   # printed 'Power' and 'power')
    ev = evidence_items(row)
    m = re.match(r"^[^:]+:\S+ — (.+)$", ev[0]) if row["first_round"] not in ("", "0") and len(ev) == 1 else None
    return [m.group(1).strip()] if m else [row["id"].replace("_", " ")]


def candidate_symbols(row):
    """P157d: the symbols of a pending row's candidate, each with the paper it came from: [(text, pid)]; a pilot row: none."""
    c = candidate_of(row)
    return list(dict.fromkeys(c["symbols"])) if c else []


def label_papers(row, label):
    """P164: the papers whose rows of a pending row's candidate print this label (the row's papers when none does)."""
    c = candidate_of(row)
    ps = list(dict.fromkeys(u["pid"] for u in (c["members"] if c else []) if u["label"] == label))
    return ps or [p for p in row["pids"].split(";") if p]


symbol_like = X.symbol_like                                                      # P178: moved to export.py (compile.py reads it too)


def run_conditions(pid):
    """The normalized other[...] condition labels of the experimental runs of a compiled tree (experiments.csv, not model runs): pass 0
    carries no conditions since P151, so rule hint c reads the pass-1 conditions on the pass-0 runs."""
    out = set()
    for r in rd(COMPILED / f"{pid}.experiments.csv"):
        if ":mrun:" in r["run"] or r.get("kind") == "cited":
            continue
        for k, v in r.items():
            if v and k.startswith("setting:other:"):
                out.add(norm(re.sub(r"\[[^\]]*\]$", "", k[len("setting:other:"):])))
    return out


# ---------------------------------------------------------------- rounds
def rounds():
    return rd(ROUNDS)


def current(statuses=("open", "proposed")):
    return next((r for r in rounds() if r["status"] in statuses), None)


def set_round(n, **kw):
    rs = rounds()
    for r in rs:
        if r["round"] == str(n):
            r.update({k: str(v) for k, v in kw.items()})
    write(ROUNDS, ROUND_COLS, rs)


def cmd_add(pids):
    for p in pids:
        if p in HELD or PAPERS.get(p) in HELD:
            raise Stop(f"{p}: a held-out paper (CLAUDE.md: yim22, gre23, mat23 are never extracted, never read, never shown); refused")
    missing_final = [p for p in pids if not (FINAL / p).is_dir()]
    if missing_final:
        raise Stop("not in ingest/final: " + ", ".join(missing_final))
    r = current()
    if r:
        raise Stop(f"round {r['round']} is {r['status']}; apply it first")
    missing = [str(path.relative_to(V2)) for p in pids for path in (RECORDS / f"{p}.jsonl", COMPILED / f"{p}.unmapped.csv") if not path.exists()]
    if missing:
        raise Stop("missing: " + ", ".join(missing) + "\nnot extracted; run pass 0 / pass 1 first (grow.py never calls a provider)")
    rs = rounds()
    n = max([int(r["round"]) for r in rs] + [0]) + 1
    dois = doi_of()
    rs.append(dict(round=n, opened=today(), applied="", pids=";".join(pids), dois=";".join(dois.get(p, "") for p in pids), status="open",
                   n_candidates="", n_accepted="", n_alias="", n_rejected="", n_never=""))
    write(ROUNDS, ROUND_COLS, rs)
    print(f"round {n} open: {len(pids)} papers ({', '.join(pids)}); DOIs from corpus/manifest.csv")


def cmd_propose():
    r = current(("open", "proposed"))                                           # P156: a proposed round can be proposed again (not yet applied)
    if not r:
        raise Stop("no open or proposed round (grow.py add first)")
    n, pids = int(r["round"]), r["pids"].split(";")
    entries = [e for e in onto()["entries"] if not e.get("replaced_by")]
    rows = rd(PENDING)
    for x in rows:
        assert list(x) == X.PENDING_COLUMNS, "pending.csv columns differ from export.PENDING_COLUMNS"
    redo = [x for x in rows if x["first_round"] == str(n) and not x["decision"]]
    rows = [x for x in rows if not (x["first_round"] == str(n) and not x["decision"])]   # the round's undecided rows are rebuilt
    for x in rows:                                                              # an earlier undecided row gives back this round's papers
        if not x["decision"] and set(x["pids"].split(";")) & set(pids):
            items = [i for i in x["evidence"].split(" || ") if i and i.split(":", 1)[0] not in pids]
            keep = [p for p in x["pids"].split(";") if p and p not in pids]
            x.update(evidence=" || ".join(items), pids=";".join(keep), n_papers=str(len(keep)), dois=";".join(doi_of().get(p, "") for p in keep))
    by_id = {x["id"]: x for x in rows}
    dois = doi_of()
    _CAND.clear()
    cands, log = round_candidates(pids)                                          # P162: with the rows carried from applied rounds
    conds = {pid: run_conditions(pid) for pid in pids}
    new, touched = [], []
    for cid, c in sorted(cands.items()):
        old = by_id.get(cid)
        if old and old["decision"]:
            continue                                                            # a decided row stays as it is
        ev = {}
        for item in (old["evidence"].split(" || ") if old and old["evidence"] else []):
            ev.setdefault(item.split(":", 1)[0], item)
        for pid, item in c["evidence"].items():
            ev.setdefault(pid, item)
        cpids = sorted(ev)
        nid, ndef, score = nearest(c["label"], entries)
        hint = "a" if len(cpids) >= 2 else "c" if any(norm(c["label"]) in conds.get(p, set()) for p in cpids) else "none"   # whole normalized label
        row = dict(id=cid, kind=old["kind"] if old else c["kind"], proposed_definition=(old or {}).get("proposed_definition") or c["definition"],
                   unit=(old or {}).get("unit") or c["unit"], n_papers=str(len(cpids)), pids=";".join(cpids), dois=";".join(dois.get(p, "") for p in cpids),
                   evidence=" || ".join(ev[p] for p in cpids), nearest_id=nid, nearest_definition=shown(ndef), rule_hint=hint,
                   first_round=(old or {}).get("first_round") or str(n), decision="", alias_target="", never_category="", decision_note=(old or {}).get("decision_note", ""),
                   **{k: (old or {}).get(k, "") for k in DECISION_COLS})
        if old:
            old.update(row)
            touched.append(cid)
        else:
            new.append(row)
    rows += new
    write(PENDING, X.PENDING_COLUMNS, rows)
    decide_page(rows, n)
    set_round(n, status="proposed", n_candidates=len(new) + len(touched))
    print(f"round {n}: {len(new) + len(touched)} candidates ({len(new)} new, {len(touched)} merged with earlier undecided rows; {len(redo)} undecided rows of "
          f"round {n} rebuilt); {len(log['never'])} rows never (compile.py's never column), "
          f"{len(log['values'])} values without a quantity, {len(log['symbol_merges'])} symbol and {len(log['label_merges'])} label merges into "
          f"{len(log['table_groups'])} symbol-table rows")
    print(f"pending.csv: {len(rows)} rows; decide in {DECIDE}")


# ---------------------------------------------------------------- decide.html
DECIDE_SCRIPT = r"""
const COLS=D.cols, ROWS=D.rows, LINES=D.lines, F=['decision','alias_target','never_category','class','category','slot','parameters','symbol_paper','decision_note'];
function q(v){return /[",\n\r]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function state(i){const r=document.getElementById('r'+i);if(!r)return ROWS[i];
  const o=Object.assign({},ROWS[i]);const c=r.querySelector('input[type=radio]:checked');o.decision=c?c.value:'';
  o.alias_target=o.decision==='alias'?r.querySelector('select.alias').value:'';o.never_category=o.decision==='never'?r.querySelector('select.never').value:'';
  o['class']=r.querySelector('select.cls').value;o.category=r.querySelector('select.cat').value;o.slot=r.querySelector('select.slot').value;
  o.parameters=r.querySelector('input.params').value.trim();o.symbol_paper=r.querySelector('input.sympap').value.trim();
  o.decision_note=r.querySelector('textarea').value;return o;}
function csvText(){let out=D.header;ROWS.forEach((row,i)=>{const s=state(i);
  out+=F.every(k=>s[k]===row[k])?LINES[i]:COLS.map(c=>q(s[c]??'')).join(',')+'\n';});return out;}
document.getElementById('dl').addEventListener('click',()=>{const b=new Blob([csvText()],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='pending.csv';document.body.appendChild(a);a.click();a.remove();});
document.querySelectorAll('input.filter').forEach(f=>f.addEventListener('input',()=>{const s=f.value.toLowerCase(),sel=f.nextElementSibling;
  let first=null;[...sel.options].forEach(o=>{const hit=!s||o.value.toLowerCase().includes(s);o.hidden=!hit;if(hit&&first===null)first=o;});if(first&&sel.selectedOptions[0]&&sel.selectedOptions[0].hidden)sel.value=first.value;}));
"""


def evidence_items(row):
    return [x for x in (row["evidence"] or "").split(" || ") if x]           # P157f: papers 1-12 are development papers, nothing withheld


def doi_links(row):
    return " ".join(f"<a href='https://doi.org/{html.escape(d)}'>{html.escape(d)}</a>" for d in filter(None, row["dois"].split(";")))


def candidate_cells(row, entries_by_id):
    """The cells decide.html and ontology.html show for a candidate: id, kind, proposed definition, unit, papers with DOI links, the evidence
    quotes with their element ids, the nearest entry with its definition and score, the rule hint."""
    labels = printed_labels(row)
    score = len(tokens(labels[0]) & (tokens(row["nearest_id"].replace("_", " ")) | {t for a in entries_by_id.get(row["nearest_id"], {}).get("aliases") or [] for t in tokens(a)}
                                     | tokens(row["nearest_definition"]))) if row["nearest_id"] else 0
    ev = "".join(f"<li>{esc(x)}</li>" for x in evidence_items(row))
    return [f"<b>{esc(row['id'])}</b><br><span class='lab'>printed: {esc(labels[0])}" + (f"<br>aliases (symbols): {esc('; '.join(labels[1:]))}" if labels[1:] else "") + "</span>", esc(row["kind"]),
            esc(row["proposed_definition"]), esc(row["unit"]), f"{esc(row['n_papers'])}<br>{doi_links(row)}", f"<ul>{ev}</ul>",
            (f"<b>{esc(row['nearest_id'])}</b> (score {score})<br>{esc(row['nearest_definition'])}" if row["nearest_id"] else "none (score 0)"),
            esc(row["rule_hint"])]


CAND_HEAD = ["id", "kind", "proposed definition", "unit", "papers (DOI)", "evidence (pid:element — quote)", "nearest entry (score)", "rule hint"]


def decide_page(rows, n):
    o = onto()
    entries = [e for e in o["entries"] if not e.get("replaced_by")]
    by_id = {e["id"]: e for e in entries}
    ids = sorted(by_id)
    cats = sorted({r["category"] for r in X.never_rows() if r["category"]})
    text = csv_text(X.PENDING_COLUMNS, rows)
    header = csv_text(X.PENDING_COLUMNS, [])
    lines = [csv_text(X.PENDING_COLUMNS, [r])[len(header):] for r in rows]
    assert header + "".join(lines) == text == PENDING.read_text(encoding="utf-8"), "pending.csv does not reserialize byte for byte"
    opt_ids = "".join(f"<option value='{html.escape(i)}'>{html.escape(i)}</option>" for i in ids)
    opt_cats = "".join(f"<option value='{html.escape(c)}'>{html.escape(c)}</option>" for c in cats)
    opt = lambda vs, cur: "".join(f"<option value='{html.escape(v)}'{' selected' if v == cur else ''}>{html.escape(v) or '—'}</option>" for v in vs)   # noqa: E731
    leaves = sorted({e.get("category") for e in entries if e["type"] in ("quantity", "categorical") and e.get("category")})
    scls = sorted(c["id"] for c in o.get("structure_classes", []))
    body = []
    multi = lambda r: int(r["n_papers"] or 0) >= 2                                # noqa: E731  P157b: rows in two or more papers first, marked
    for i, r in sorted(((i, r) for i, r in enumerate(rows) if not r["decision"]), key=lambda x: (not multi(x[1]), x[0])):
        cells = candidate_cells(r, by_id)
        if multi(r):
            cells[0] = f"<span class='multi'>▲ in {esc(r['n_papers'])} papers</span><br>" + cells[0]
        ctl = (f"<div class='ctl'>" + "".join(f"<label><input type='radio' name='d{i}' value='{v}'> {v}</label>" for v in ("accept", "alias", "reject", "never"))
               + f"<div>alias to: <input class='filter' placeholder='type to filter'><select class='alias'>{opt_ids}</select></div>"
               + f"<div>never category: <select class='never'>{opt_cats}</select></div>"
               + f"<div>class (model): <select class='cls'>{opt(('',) + X.MODEL_CLASSES, r['class'])}</select></div>"   # P175: the columns apply reads
               + f"<div>category (leaf): <select class='cat'>{opt([''] + leaves, r['category'])}</select></div>"
               + f"<div>slot (structure class): <select class='slot'>{opt([''] + scls, r['slot'])}</select></div>"
               + f"<div>parameters: <input class='params' placeholder='entry ids; ;-separated' value='{html.escape(r['parameters'])}'></div>"
               + f"<div>symbol of papers: <input class='sympap' placeholder='paper keys; ;-separated' value='{html.escape(r['symbol_paper'])}'></div>"
               + f"<textarea placeholder='note (a memo; apply reads none)'>{html.escape(r['decision_note'])}</textarea></div>")
        body.append(f"<tr id='r{i}'{' class=multi' if multi(r) else ''}>" + "".join(f"<td>{c}</td>" for c in cells) + f"<td>{ctl}</td></tr>")
    done = [r for r in rows if r["decision"]]
    done_html = "".join("<tr>" + "".join(f"<td>{html.escape(r[k])}</td>" for k in ("id", "kind", "decision", "alias_target", "never_category", *DECISION_COLS, "decision_note", "first_round")) + "</tr>" for r in done)
    data = json.dumps(dict(cols=X.PENDING_COLUMNS, rows=rows, lines=lines, header=header), ensure_ascii=False).replace("</", "<\\/")
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>decide round {n}</title><style>{STYLE}"
            ".ctl label{display:block}.ctl select,.ctl input.filter{max-width:16em}.ctl textarea{width:16em;height:3em}.lab{color:#555;font-size:12px}"
            "tr.multi td:first-child{border-left:4px solid #b35900}.multi{color:#b35900;font-weight:bold}</style></head><body>"
            f"<h1>Round {n}: decide the candidates</h1><p>{len(body)} candidates without a decision ({sum(1 for r in rows if not r['decision'] and multi(r))} found in two "
            "or more papers come first, marked ▲). Choose accept / alias / reject / never per row, then "
            "<button id='dl'>download pending.csv</button> and save it over psed_v2/ontology/pending.csv; then run <code>python3 psed_v2/ontology/grow.py apply</code>. "
            "Rows left without a choice stay pending.</p>"
            f"<table><tr>{''.join(f'<th>{h}</th>' for h in CAND_HEAD)}<th>decision</th></tr>{''.join(body)}</table>"
            f"<h2>Decided earlier (read-only)</h2><table><tr><th>id</th><th>kind</th><th>decision</th><th>alias target</th><th>never category</th>{''.join(f'<th>{c}</th>' for c in DECISION_COLS)}<th>note</th><th>first round</th></tr>{done_html}</table>"
            f"<script>const D={data};{DECIDE_SCRIPT}</script></body></html>\n")                       # the one script: the rows, then the form logic
    DECIDE.write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- apply (merge_pending.py's writing of entries)
ORDER = ["id", "type", "label", "name", "origin", "role", "category", "definition", "dimension", "unit", "kind", "formula", "class", "model_type",
         "parameters", "aliases", "symbols", "source_pids", "evidence"]


def block(e):
    text = yaml.safe_dump([e], sort_keys=False, allow_unicode=True, width=100000, default_flow_style=None)
    return "".join("  " + ln + "\n" for ln in text.splitlines()) + "\n"


def entry_span(text, eid):
    """(start, end) of an entry's block in ontology.yaml text."""
    m = re.search(rf"(?m)^  - id: {re.escape(eid)}\n", text)
    if not m:
        raise Stop(f"{eid}: no entry block in ontology.yaml")
    nxt = re.search(r"(?m)^  - id: |^\S", text[m.end():])
    return m.start(), m.end() + (nxt.start() if nxt else len(text) - m.end())


def add_alias(text, eid, labels):
    """Append labels to an entry's aliases (a flow list on one line; a new line after the id when it has none)."""
    s, e = entry_span(text, eid)
    blk = text[s:e]
    m = re.search(r"(?m)^    aliases: (\[.*\])$", blk)
    have = yaml.safe_load(m.group(1)) if m else []
    seen = {X.norm_label(h) for h in have}                                  # P176: one alias per word key (export --check 4), the first printed,
    add = [" ".join(a.split()) for a in labels if X.norm_label(a) not in seen and not seen.add(X.norm_label(a))]   # on one line
    if not add:
        return text
    line = "    aliases: " + yaml.safe_dump(have + add, default_flow_style=True, allow_unicode=True, width=100000).strip()
    blk = blk[:m.start()] + line + blk[m.end():] if m else blk.replace("\n", "\n" + line + "\n", 1)
    return text[:s] + blk + text[e:]


def add_symbols(text, eid, pairs):
    """P164: append {text, paper} symbols to an entry's symbols (a flow list on one line; a new line after its aliases, else after its id);
    a symbol the entry already has for that paper (equal export.symbol_key) is left out. Returns (text, the symbols added)."""
    s, e = entry_span(text, eid)
    blk = text[s:e]
    m = re.search(r"(?m)^    symbols: (\[.*\])$", blk)
    have = yaml.safe_load(m.group(1)) if m else []
    keys, add = {(X.symbol_key(h["text"]), h.get("paper", "")) for h in have}, []
    for t, p in [(" ".join(str(t).split()), p) for t, p in pairs]:            # P176: on one line
        if (X.symbol_key(t), p) not in keys:
            keys.add((X.symbol_key(t), p))
            add.append(dict(text=t, paper=p))
    if not add:
        return text, []
    line = "    symbols: " + yaml.safe_dump(have + add, default_flow_style=True, allow_unicode=True, width=100000, sort_keys=False).strip()
    if m:
        blk = blk[:m.start()] + line + blk[m.end():]
    else:
        a = re.search(r"(?m)^    aliases: .*$", blk)
        blk = blk[:a.end()] + "\n" + line + blk[a.end():] if a else blk.replace("\n", "\n" + line + "\n", 1)
    return text[:s] + blk + text[e:], add


def model_fields(row):
    """P168 (user), P175 (user: the columns, never the note): an accepted model's class (column class: analytical / computational) and its
    parameters (column parameters: entry ids, ';'-separated). Returns (model_type, parameters)."""
    return row.get("class", ""), [q for q in re.split(r"[;,\s]+", row.get("parameters") or "") if q]


def entry_fields(row, categories, classes):
    """P171 (user), P175 (user: the columns, never the note): an accepted entry's category (column category: a hierarchy leaf the quantity
    entries use) and structure-class slot (column slot: a structure class). Returns (category or '', class or '')."""
    return (row.get("category", "") if row.get("category", "") in categories else ""), (row.get("slot", "") if row.get("slot", "") in classes else "")


def symbol_papers(row):
    """P175 (user): the papers of column symbol_paper (paper keys, ';'-separated) as paper ids: the decision's printed labels become symbols
    of these papers, never aliases. Unknown keys -> Stop."""
    keys = [k for k in re.split(r"[;,\s]+", row.get("symbol_paper") or "") if k]
    bad = [k for k in keys if k not in KEY2PID and k not in PAPERS]
    if bad:
        raise Stop(f"{row['id']}: symbol_paper names no paper: {bad}")
    return [KEY2PID.get(k, k) for k in keys]


def add_slot(text, cls, eid):
    """P171: append an entry id to a structure class's slots (its one-line flow mapping under structure_classes)."""
    m = re.search(rf"(?m)^  - \{{id: {re.escape(cls)}, .*slots: \[([^\]]*)\]\}}$", text)
    if not m:
        raise Stop(f"structure class {cls}: no one-line entry with slots")
    have = [x.strip() for x in m.group(1).split(",") if x.strip()]
    if eid in have:
        return text
    return text[:m.start(1)] + ", ".join(have + [eid]) + text[m.end(1):]


def split_labels(row, labels):
    """P164 (user): a decision's printed labels as (word labels, symbols [(text, pid)]): a symbol-like label is a symbol of each paper
    that prints it, never a word."""
    one = lambda t: " ".join(str(t).split())                                   # noqa: E731  P176: a printed line break is layout (one-line YAML)
    words = list({X.norm_label(t): one(t) for t in reversed([t for t in labels if not symbol_like(t)])}.values())[::-1]   # P176: one per word key (the first)
    syms = [(one(t), p) for t in labels if symbol_like(t) for p in label_papers(row, t)]
    return words, syms


def cmd_apply():
    """P173 (user): apply is atomic. Every write happens in a sandbox (a temporary copy of ontology/ and kb/: kb/reports holds only the
    R<n>_apply files; kb/cache, kb/records, kb/verify, ingest and corpus are read-only links; P174: the sandbox lives in psed_v2/kb/tmp/,
    git-ignored, never the system temp); apply_here() runs there, imports the figures again and ends with
    export --check and the audits of every applied round. Only when all pass are the files it changed moved into the real tree and
    committed; a failure leaves ontology/, kb/compiled and pending.csv untouched and prints what would have been written."""
    import os
    import shutil
    import tempfile
    if os.environ.get("GROW_SANDBOX"):
        return apply_here()
    (V2 / "kb" / "tmp").mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="grow_apply_", dir=V2 / "kb" / "tmp"))
    T = tmp / V2.name
    skip = shutil.ignore_patterns("__pycache__")
    try:
        (T / "kb" / "reports").mkdir(parents=True)
        shutil.copytree(HERE, T / "ontology", ignore=skip)
        for x in (V2 / "kb").iterdir():
            if x.name in ("reports", "cache", "records", "verify", "tmp", "__pycache__"):
                continue
            if x.is_dir():
                shutil.copytree(x, T / "kb" / x.name, ignore=skip)
            else:
                shutil.copy2(x, T / "kb" / x.name)
        for name in ("cache", "records", "verify"):
            (T / "kb" / name).symlink_to(V2 / "kb" / name)
        for f in (V2 / "kb" / "reports").glob("R*_apply.*"):
            shutil.copy2(f, T / "kb" / "reports" / f.name)
        for name in ("ingest", "corpus", ".env"):
            if (V2 / name).exists():
                (T / name).symlink_to(V2 / name)
        p = subprocess.run([sys.executable, str(T / "ontology" / "grow.py"), "apply"], cwd=tmp, env={**os.environ, "GROW_SANDBOX": "1"}, capture_output=True, text=True)
        print(p.stdout[-8000:] + p.stderr[-3000:])
        changed = []
        for top in ("ontology", "kb"):
            for f in sorted((T / top).rglob("*")):
                if f.is_symlink() or any(q.is_symlink() for q in f.parents if T in q.parents) or not f.is_file() or "__pycache__" in f.parts or f.name == ".apply_message":
                    continue
                rel = f.relative_to(T)
                real = V2 / rel
                if not real.exists() or real.read_bytes() != f.read_bytes():
                    changed.append((rel, "new" if not real.exists() else "changed"))
        if p.returncode:
            print("APPLY FAILED in the sandbox: nothing was written. It would have written:")
            for rel, st in changed:
                print(f"  {st}: {rel}")
            raise Stop("apply failed (see above); ontology/, kb/compiled and pending.csv untouched")
        for rel, _ in changed:
            (V2 / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(T / rel, V2 / rel)
        msg = (T / "ontology" / ".apply_message").read_text(encoding="utf-8")
        paths = [str(V2 / rel) for rel, _ in changed]                         # P174: exactly the files moved into place, the git-ignored ones
        ign = set(subprocess.run(["git", "check-ignore", "--", *paths], cwd=ROOT, capture_output=True, text=True).stdout.splitlines())   # (paper text) left out
        subprocess.run(["git", "add", "--", *[x for x in paths if x not in ign]], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=ROOT, check=True)
        print(f"moved {len(changed)} files into place and committed: {msg.splitlines()[0]}")
        return []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def apply_here():
    r, late = current(("proposed",)), False
    if not r:                                                                   # P169: late decisions of an applied round (no new snapshot)
        dec = [x for x in rd(PENDING) if x["decision"]]
        rnd = {x["first_round"] for x in dec}
        r = next((y for y in rounds() if len(rnd) == 1 and y["round"] in rnd and y["status"] == "applied"), None)
        if not dec or r is None:
            raise Stop("no proposed round (and no decided pending rows of one applied round)")
        late = True
    n = int(r["round"])
    o = onto()
    have = {e["id"]: e for e in o["entries"]}
    rows = rd(PENDING)
    decided = [x for x in rows if x["decision"]]
    stops = []
    cats = {e.get("category") for e in o["entries"] if e["type"] in ("quantity", "categorical") and e.get("category")}   # P171
    classes = {c["id"] for c in o.get("structure_classes", [])}
    for x in decided:
        if x["decision"] not in X.DECISIONS:
            stops.append(f"{x['id']}: decision {x['decision']!r}")
        if x["decision"] == "accept" and x["id"] in have and have[x["id"]].get("definition") != x["proposed_definition"]:
            stops.append(f"{x['id']}: accept, but ontology.yaml has it with another definition: {have[x['id']].get('definition')!r}")
        if x["decision"] == "accept" and x["kind"] == "unit":
            stops.append(f"{x['id']}: accept of a unit; units go into units.yaml by hand, not into ontology.yaml")
        if x["decision"] == "accept" and x["kind"] == "layout":                # P177b: a layout kind goes into ontology.yaml layouts: by hand
            stops.append(f"{x['id']}: accept of a layout; a layout kind (item, conditions_from, results_from) goes into ontology.yaml layouts: by hand")
        if x["decision"] == "alias" and x["alias_target"] not in have and x["alias_target"] not in {y["id"] for y in decided if y["decision"] == "accept"}:
            stops.append(f"{x['id']}: alias target {x['alias_target']!r} is not an entry, nor accepted in this round")
        if x["decision"] == "never" and not x["never_category"].strip():
            stops.append(f"{x['id']}: never without a never_category")
        if x.get("slot") and x["slot"] not in classes:                          # P175: the columns, never the note
            stops.append(f"{x['id']}: slot {x['slot']!r} is no structure class")
        if x.get("category") and x["category"] not in cats:
            stops.append(f"{x['id']}: category {x['category']!r} is no category of the quantity entries")
        if x.get("symbol_paper"):
            try:
                symbol_papers(x)
            except Stop as e:
                stops.append(str(e))
        if x["decision"] == "accept" and x["kind"] == "model":                 # P168: a model's class and parameters (model_fields)
            mt, params = model_fields(x)
            if mt not in X.MODEL_CLASSES:
                stops.append(f"{x['id']}: accept of a model without its class (column class: analytical or computational)")
            bad = [q for q in params if q not in have and q not in {y["id"] for y in decided if y["decision"] == "accept"}]
            if bad:
                stops.append(f"{x['id']}: model parameters that are no entry: {bad}")
    if stops:
        raise Stop("nothing written:\n  " + "\n  ".join(stops))
    backup = {p: p.read_bytes() for p in (ONTO, PENDING, NEVER, HISTORY, ROUNDS) if p.exists()}
    if not late:                                                                # a late decision's rows are in the round's snapshot already
        snapshot(n, r["pids"].split(";"), rows)                                 # P157d: the rows each candidate covers, before anything changes
    text = ONTO.read_text(encoding="utf-8")
    new, hist, nev, applied, slots = [], [], X.never_rows(), [], []
    order = {"accept": 0, "alias": 1}                                          # P164: accepts first (an alias may target an entry of this round)
    for x in sorted(decided, key=lambda x: order.get(x["decision"], 2)):
        labels, syms = printed_labels(x), candidate_symbols(x)
        words, lsyms = split_labels(x, labels)                                 # P164: a symbol-like label is a symbol of its paper, never a word;
                                                                                # P171 fix: every printed label (a prefix-merged label too)
        sp = symbol_papers(x)                                                   # P175 (user): column symbol_paper: the printed labels are
        if sp:                                                                  # symbols of those papers, never aliases
            lsyms, words = [(t, p) for t in labels for p in sp], []
        if x["decision"] == "accept" and x["id"] not in have:                  # P157d: the printed label -> aliases, the table symbols -> symbols
            mt, params = model_fields(x) if x["kind"] == "model" else ("", [])
            e = X.pending_entry(x, words, list(dict.fromkeys(syms + lsyms)))
            if x["kind"] == "model":
                e.update(model_type=mt, parameters=params)
            cat, slot = entry_fields(x, cats, classes)                          # P171, P175: category and structure-class slot (the columns)
            if cat:
                e["category"] = cat
            if slot:
                slots.append((slot, x["id"]))
            e.update(origin=f"round {n}", source_pids=[p for p in x["pids"].split(";") if p], evidence=evidence_items(x))
            new.append({k: e[k] for k in ORDER if k in e and e[k] not in ("", [], None)})
            applied.append(dict(id=x["id"], decision="accept", candidate=(candidate_of(x) or {}).get("id", ""), aliases="; ".join(e.get("aliases") or []),
                                symbols="; ".join(f"{s_['text']} ({s_['paper']})" for s_ in e.get("symbols") or []), note=""))
        elif x["decision"] == "alias":                                         # P156: the label only (a candidate's table symbols stay out)
            t_new = next((e for e in new if e["id"] == x["alias_target"]), None)   # P164: a symbol-like label goes to the target's symbols
            if t_new is not None:
                al = [w for w in words if X.norm_label(w) not in {X.norm_label(a) for a in t_new.get("aliases", [])}]
                t_new["aliases"] = t_new.get("aliases", []) + al
                keys = {(X.symbol_key(s_["text"]), s_["paper"]) for s_ in t_new.get("symbols", [])}
                sy = [dict(text=t, paper=p) for t, p in dict.fromkeys(lsyms) if (X.symbol_key(t), p) not in keys]
                t_new["symbols"] = t_new.get("symbols", []) + sy
            else:
                text = add_alias(text, x["alias_target"], words) if words else text
                al = words
                text, sy = add_symbols(text, x["alias_target"], lsyms)
            applied.append(dict(id=x["id"], decision=f"alias -> {x['alias_target']}", candidate=(candidate_of(x) or {}).get("id", ""), aliases="; ".join(al),
                                symbols="; ".join(f"{s_['text']} ({s_['paper']})" for s_ in sy),
                                note="" if al or sy else "nothing new: the target already has this label or symbol"))
        elif x["decision"] == "never":                                         # P157d: the label (any paper) and each symbol (its paper only);
            nev += [dict(label=w, category=x["never_category"], paper=x["pids"], source=f"round {n}: {x['id']}", symbol="") for w in words]
            nev += [dict(label=t, category=x["never_category"], paper=p, source=f"round {n}: " + ("symbol of " if t not in labels[:1] else "") + x["id"],
                         symbol="yes") for t, p in dict.fromkeys(lsyms + syms)    # P164: a symbol-like label is a symbol row of its paper
                    if not any(r["label"] == t and r["paper"] == p and r.get("symbol") == "yes" for r in nev)]   # P172: not twice
            applied.append(dict(id=x["id"], decision=f"never ({x['never_category']})", candidate=(candidate_of(x) or {}).get("id", ""), aliases="; ".join(words),
                                symbols="; ".join(f"{t} ({p})" for t, p in dict.fromkeys(lsyms + syms)), note=""))
    old_w = rd(REPORTS / f"R{n}_apply.written.csv") if late else []             # P169: late decisions add to the round's rows
    write(REPORTS / f"R{n}_apply.written.csv", ["id", "decision", "candidate", "aliases", "symbols", "note"], old_w + applied)   # P164: what apply wrote
    if new:
        mark = "\nfamilies:"
        assert text.count(mark) == 1
        head, tail = text.split(mark)
        text = head.rstrip("\n") + f"\n\n  # ---------------------------------------------------------------- grow.py round {n}: accepted\n" \
            + "".join(block(e) for e in new).rstrip("\n") + "\n" + mark + tail
    for cls, eid in slots:                                                      # P171
        text = add_slot(text, cls, eid)
    ONTO.write_text(text, encoding="utf-8")
    yaml.safe_load(ONTO.read_text(encoding="utf-8"))                            # still parses
    X.stamp_header()
    write(NEVER, NEVER_COLS, nev)
    write(PENDING, X.PENDING_COLUMNS, [x for x in rows if not x["decision"]])
    py = sys.executable
    steps = [[py, str(HERE / "export.py")], [py, str(HERE / "export.py"), "--check"]]
    for cmd in steps:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if p.returncode:
            for path, b in backup.items():
                path.write_bytes(b)
            subprocess.run([py, str(HERE / "export.py")], capture_output=True, text=True, cwd=ROOT)
            raise Stop(f"{' '.join(cmd[1:])} failed; every file restored, nothing applied:\n{p.stdout}{p.stderr}")
    extracted = sorted(p.stem for p in RECORDS.glob("*.jsonl") if (COMPILED / f"{p.stem}.facts.csv").exists() and p.stem not in HELD)
    figs = [pid for pid in extracted if (V2 / "ingest" / "final" / pid / "figures.json").exists()]
    if figs:                                                                    # P174: a figure label resolves at import (the one path): import again
        subprocess.run([py, str(V2 / "kb" / "figures_import.py"), *figs], cwd=ROOT, check=True, capture_output=True)
    for pid in extracted:                                                       # 0 calls: compile reads the stored records
        subprocess.run([py, str(V2 / "kb" / "extract" / "compile.py"), pid], cwd=ROOT, check=True)
    gold = [pid for pid in extracted if (V2 / "kb" / "pilot" / f"{pid}.facts.csv").exists()]
    if gold:
        subprocess.run([py, str(V2 / "kb" / "extract" / "score.py"), f"R{n}", *gold], cwd=ROOT, check=True)
    reg = subprocess.run([py, str(V2 / "kb" / "extract" / "binding.py"), "--check"], cwd=ROOT, capture_output=True, text=True)   # P177b (user): the
    binding_fails = [f"binding regression: {x}" for x in reg.stdout.splitlines() if x and not x.startswith("binding regression:")]   # binding re-checked
    after = sha(ONTO)
    dois = doi_of()
    for x in decided:
        pids = [p for p in x["pids"].split(";") if p]
        hist.append(dict(date=today(), round=n, action={"accept": "add"}.get(x["decision"], x["decision"]), id=x["id"], kind=x["kind"],
                         target=x["alias_target"] if x["decision"] == "alias" else x["never_category"] if x["decision"] == "never" else "",
                         source_pids=";".join(pids), source_dois=";".join(dois.get(p, "") for p in pids), decided_by="user", reason=x["decision_note"],
                         ontology_sha256_after=after, **{k: x.get(k, "") for k in DECISION_COLS}))
    append(HISTORY, HISTORY_COLS, hist)
    c = Counter(x["decision"] for x in decided)
    plus = lambda k, v: int(r.get(k) or 0) + v if late else v                 # noqa: E731  P169: late decisions add to the round's counts
    set_round(n, status="applied", applied=today(), n_accepted=plus("n_accepted", c["accept"]), n_alias=plus("n_alias", c["alias"]),
              n_rejected=plus("n_rejected", c["reject"]), n_never=plus("n_never", c["never"]))
    fails = audit_round(n) + binding_fails                                      # P157d: A1-A3 and their acceptance, every round; P177b: binding
    for r2 in rounds():                                                         # P173: and every other applied round's audit
        if r2["status"] == "applied" and r2["round"] != str(n) and (REPORTS / f"R{r2['round']}_apply.decision_rows.csv").exists():
            fails += [f"round {r2['round']}: {x}" for x in audit_round(int(r2["round"]))]
    report_page()
    (HERE / ".apply_message").write_text(f"grow round {n} {'late decisions ' if late else ''}applied: {c['accept']} accepted, {c['alias']} aliases, "
                                         f"{c['reject']} rejected, {c['never']} never; recompiled {len(extracted)} papers, scored {len(gold)} (0 calls)", encoding="utf-8")
    print(f"round {n} applied in the sandbox: {dict(c)}; {len(rows) - len(decided)} rows stay pending; ontology.yaml sha256 {after[:12]}")
    for f in fails:
        print(f"ACCEPTANCE FAIL round {n}: {f}")
    if fails:
        raise Stop(f"{len(fails)} audit failures: nothing moved into place")
    subprocess.run([py, str(V2 / "kb" / "extract" / "binding.py"), "--write"], cwd=ROOT, check=True, capture_output=True)   # P177b: the outcomes anew
    return fails


# ---------------------------------------------------------------- P157d: the decision audit of a round (A1-A3, P157c), every round
REPORTS = V2 / "kb" / "reports"
SNAP_COLS = ["pid", "element", "field", "label", "unit", "candidate", "decision"]
A1_COLS = ["id", "decision", "covers", "pid", "element", "field", "row_label", "now", "effect", "reason"]
A2_COLS = ["pid", "element", "field", "printed", "record_meaning", "lookup", "entry", "entry_name", "entry_definition", "head_record", "head_entry_name",
           "head_entry_definition", "verdict", "symbol", "history", "outcome"]
A3_COLS = ["pid", "element", "field", "label", "unit", "record_key", "class", "candidate_at_snapshot", "why"]
A3P_COLS = ["candidate", "first_round", "pids", "rows_at_snapshot", "open_rows_now", "accounted", "detail"]
HEAD_STOPS = r"\b(of|at|in|for|with|between|without|per|from|on|to|by|where|that|which|during|when|as|under|over)\b|[,;:(\[$]| - | – "


def snapshot(n, pids, pend):
    """The rows of a round before apply changes anything: every compiled unmapped row of its papers with the candidate propose made of
    it and that candidate's decision in pending.csv ('' when undecided; candidate '' for a never row or a value without a quantity).
    P164: a candidate whose pending row the user gave another id is written under that id (candidate_of: the same evidence)."""
    _CAND.clear()
    cands, _ = round_candidates(pids)                                            # P162: the carried rows too, as propose made them
    dec = {x["id"]: x["decision"] for x in pend}
    rid = {c["id"]: x["id"] for x in pend for c in [candidate_of(x)] if c and c["id"] != x["id"]}   # P164: an id the user edited
    out = []
    for cid, c in cands.items():
        for u in c["members"]:
            out.append(dict(pid=u["pid"], element=u["element"], field=u["field"], label=u["label"], unit=u["unit"], candidate=rid.get(cid, cid),
                            decision=dec.get(rid.get(cid, cid), "")))
    write(REPORTS / f"R{n}_apply.decision_rows.csv", SNAP_COLS, out)
    return out


def head_noun(text):
    """The head noun of a noun phrase (P157c): LaTeX unwrapped, casefold, the text before the first preposition / relative word / comma
    / bracket / '$', its last alphabetic word of two or more letters, a plural s dropped (not ss, us, is). P165: a hyphen is a word
    boundary ('flow-type' -> type)."""
    t = re.split(HEAD_STOPS, X.LATEX_TEXT.sub(r"\1", str(text or "")).casefold(), maxsplit=1)[0]
    ws = [x for x in t.replace("-", " ").split() if re.fullmatch(r"[a-zà-ÿ]{2,}", x)]
    h = ws[-1] if ws else ""
    return h[:-1] if h.endswith("s") and not h.endswith(("ss", "us", "is")) and len(h) > 3 else h


NEW_SINCE_APPLY = "new since apply → next round"


def open_rows(n, compiled, unm, snap):
    """P157d A3, out of audit_round since P162: every open (not never) unmapped row of round n's compiled papers (unm: their unmapped.csv
    rows), classified. P162: a row that would be unclassified and is absent from the round's apply snapshot (born after apply, e.g. a
    derived unit's condition) is NEW_SINCE_APPLY: counted, listed and carried into the next propose (carried_rows), not a failure.
    P165: the unit row of a promoted record whose unit units.yaml lacks is "unit unresolved" (listed), not open.
    Returns (A3 rows, failures, the unmapped_rows() row of each A3 row)."""
    fails = []
    pro = {p: rd(COMPILED / f"{p}.promoted.csv") for p in compiled}
    pend = {x["id"]: x for x in rd(PENDING)}
    decided_ids = {h["id"]: h for h in rd(HISTORY) if h["action"] in ("add", "alias", "never", "reject")}
    _CAND.clear()
    _SCOPE.clear()                                                              # P175: the ontology as it is now (apply writes it before the audits)
    cands, log = candidates_of(sorted(compiled)) if compiled else ({}, dict(never=[], values=[]))
    member, ngrp, vals = {}, {}, set()
    ck = lambda u: (u["pid"], u["element"], u["field"], u["label"], u["unit"])  # noqa: E731
    for cid, c in cands.items():
        for u in c["members"]:
            member.setdefault(ck(u), []).append(cid)
    for u, nv in log["never"]:
        if not u["never"]:
            ngrp[ck(u)] = nv
    for u in log["values"]:
        vals.add(ck(u))
    cats = {ck(u) for u in log.get("categorical", [])}                         # P168
    snap_of = {}
    for r in snap:
        snap_of.setdefault((r["pid"], r["element"], r["field"], r["label"], r["unit"]), []).append(r["candidate"])
    a3, seen, src = [], Counter(), []
    for p in sorted(compiled):
        for u in unmapped_rows(p):
            if u["never"]:
                continue
            k = ck(u)
            cids = member.get(k, [])
            cid = cids[min(seen[k], len(cids) - 1)] if cids else ""
            seen[k] += 1
            raw = next(x for x in unm[p] if x["element"] == u["element"] and x["field"] == u["field"] and x["label_as_printed"].strip() == u["label"])
            prom = next((x for x in pro.get(p, []) if x["element"] == u["element"] and x["printed"] == u["label"] and not x["outcome"].startswith("not promoted")), None)
            if cid in pend:
                cls, why = f"pending candidate {cid}", ("cell without printed label, keyed by its meaning" if not u["label"] else "")
            elif u["field"] == "unit" and prom:                                 # P165 (user): its record is promoted; the unit is a units.yaml matter
                cls, why = "unit unresolved", f"the record is promoted to {prom['id']}; its unit {u['unit']!r} is not in units.yaml"
            elif raw["action"].startswith("kept (ambiguous"):
                cls, why = "other", f"compile: {raw['action'][6:-1]}; propose groups it as {cid or 'nothing'}"
            elif k in ngrp:
                cls, why = "other", f"joined the symbol-table row of a never candidate through its symbol ({ngrp[k]}); propose drops the group"
            elif k in vals:
                cls, why = "other", "a value without a quantity: no record key, or the label is only a units.yaml spelling"
            elif k in cats:
                cls, why = "other", f"the value row of the categorical {u['field']}: propose makes no candidate of it (P168)"
            elif u.get("action", "").startswith(("kept (names the model ", "kept (names the method ")):
                cls, why = "other", f"a record of no quantity that names a {'model' if 'the model' in u['action'] else 'method'} entry: {u['action'][6:-1]} (P172, P176)"
            elif cid in decided_ids and k not in snap_of:                      # P176 (user, the P162 rule): born after apply, its id decided
                h = decided_ids[cid]                                            # before the row existed; carried
                cls, why = NEW_SINCE_APPLY, (f"candidate {cid} decided in round {h['round']} ({h['action']}" + (f" -> {h['target']}" if h["target"] else "")
                                             + "): the row was born after apply; carried into the next propose")
            elif cid in decided_ids and decided_ids[cid]["action"] != "reject" and scoped_elsewhere(p, u["label"]):   # P175 (user)
                h = decided_ids[cid]
                cls, why = NEW_SINCE_APPLY, (f"candidate {cid} decided in round {h['round']} ({h['action']}" + (f" -> {h['target']}" if h["target"] else "")
                                             + f"): {scoped_elsewhere(p, u['label'])}; carried into the next propose")
            elif cid in decided_ids:
                h = decided_ids[cid]
                cls, why = "other", f"candidate {cid} decided in round {h['round']} ({h['action']}" + (f" -> {h['target']}" if h["target"] else "") + "): " + (
                    "a rejected label is written nowhere (by design)" if h["action"] == "reject" else "decided, but the row is still open")
            elif not u["label"]:
                cls, why = "cell without printed label", f"candidate {cid or 'none'}"
            elif k in snap_of and cid not in snap_of[k]:                        # P176 (user, the P162 rule): regrouped since apply
                cls, why = NEW_SINCE_APPLY, f"regrouped since apply: candidate {';'.join(sorted(set(snap_of[k])))} at the snapshot, {cid or 'none'} now; carried into the next propose"
            elif k not in snap_of:                                              # P162: born after apply (absent from the snapshot)
                cls, why = NEW_SINCE_APPLY, f"candidate {cid or 'none'}: not in R{n}_apply.decision_rows.csv; carried into the next propose"
            else:
                cls, why = "unclassified", f"candidate {cid or 'none'}: not pending, not decided"
            if cls == "unclassified" or why.endswith("still open"):
                fails.append(f"A3 {p}:{u['element']} {u['field']} '{u['label']}': {why}")
            a3.append(dict(pid=p, element=u["element"], field=u["field"], label=u["label"], unit=u["unit"], record_key=X.norm_label(u["text"]), **{"class": cls},
                           candidate_at_snapshot=";".join(snap_of.get(k, [])), why=why))
            src.append(u)
    return a3, fails, src


def figure_label(pid, element, key):
    """P176: a figure label of kb/<pid>.figures.json (the inventory's labels, P174) at an element and with a key, as the import resolved it:
    dict(quantity, how), or None."""
    p = V2 / "kb" / f"{pid}.figures.json"
    F = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    for inv in F.get("inventory", []):
        els = [f"fig{inv['figure']}{inv.get('panel', '')}", f"fig{inv['figure']}", f"fig{inv['figure']}.cap"]
        if element in els:
            hit = next((x for x in inv.get("labels") or [] if x["key"].strip() == key), None)
            if hit:
                return dict(quantity=hit["quantity"], how=hit.get("how", ""))
    return None


_SCOPE = {}


def scoped_elsewhere(pid, label):
    """P175 (user), A3: why a row's label is not covered by a decision of its candidate: the label is a paper-local symbol of other papers
    only (a never.csv symbol row, or an entry's symbol; export.symbol_key), or it is an entry's id, name or label that is no alias of it
    (export.norm_label; the one path reads ids, names and aliases of quantities only). '' when neither."""
    if not _SCOPE:
        live = [e for e in onto()["entries"] if not e.get("replaced_by")]
        sym = defaultdict(set)
        for r in X.never_rows():
            if r.get("symbol") == "yes":
                for q in str(r["paper"]).split(";"):
                    sym[X.symbol_key(r["label"])].add(q)
        for e in live:
            for x in e.get("symbols") or []:
                sym[X.symbol_key(x["text"])].add(x.get("paper", ""))
        names = defaultdict(set)
        for e in onto()["entries"]:                                             # an entry replaced by another is an entry too
            al = {X.norm_label(str(a)) for a in e.get("aliases") or []}
            for t in (e["id"], e["id"].replace("_", " "), e.get("name", ""), e.get("label", "")):
                if str(t).strip() and X.norm_label(str(t)) not in al:
                    names[X.norm_label(str(t))].add(e["id"])
        _SCOPE.update(sym=sym, names=names)
    ps = _SCOPE["sym"].get(X.symbol_key(label), set())
    if ps and pid not in ps and "" not in ps:
        return "the label is a paper-local symbol of " + ", ".join(sorted(PAPERS.get(q, q) for q in ps)) + " only"
    ids = _SCOPE["names"].get(X.norm_label(label), set())
    return f"the label is the id, name or label of {', '.join(sorted(ids))}, no alias" if ids else ""


def carried_rows(exclude=()):
    """P162: the rows open_rows() classes NEW_SINCE_APPLY, of the papers of every applied round with an apply snapshot (a paper in two
    such rounds: the later one), the papers in exclude (the open round's own, read whole) left out. P168 fix: also the rows already
    pending under a candidate first proposed in the open round (a carried row stays carried once propose made it pending, so the
    apply snapshot holds it)."""
    cur = current(("open", "proposed"))
    first = {x["id"] for x in rd(PENDING) if cur and x["first_round"] == cur["round"]}
    out, done = [], set(exclude)
    for r in sorted(rounds(), key=lambda r: -int(r["round"])):
        snap = rd(REPORTS / f"R{r['round']}_apply.decision_rows.csv") if r["status"] == "applied" else []
        pids = [p for p in r["pids"].split(";") if p and p not in done and (COMPILED / f"{p}.facts.csv").exists()]
        if not snap or not pids:
            continue
        done |= set(pids)
        rows, _, us = open_rows(int(r["round"]), set(pids), {p: rd(COMPILED / f"{p}.unmapped.csv") for p in pids}, snap)
        out += [u for x, u in zip(rows, us) if x["class"] == NEW_SINCE_APPLY or (x["class"].startswith("pending candidate ") and x["class"][18:] in first)]
    return out


def user_labels(entries):
    """P169 (user): {(entry id, 'alias' | 'symbol', key): the history row} of every alias and symbol a user decision wrote: an entry a user
    accepted (history add, decided_by user): its aliases and symbols; a user's alias decision: what R<n>_apply.written.csv says it wrote
    (P164 on), else the target's aliases whose snake form is the decision's id. Keys: export.norm_label / export.symbol_key."""
    out = {}
    for row_no, h in enumerate(rd(HISTORY), 2):
        if h["decided_by"] != "user" or h["action"] not in ("add", "alias"):
            continue
        ref = f"history.csv row {row_no} (round {h['round']}, {h['action']} {h['id']})"
        eid = h["id"] if h["action"] == "add" else h["target"]
        e = entries.get(eid, {})
        if h["action"] == "add":
            als, sys_ = list(e.get("aliases") or []), [x["text"] for x in e.get("symbols") or []]
        else:
            ws = [x for x in rd(REPORTS / f"R{h['round']}_apply.written.csv") if x["id"] == h["id"]]
            als = [a for w in ws for a in w["aliases"].split("; ") if a] if ws else [a for a in e.get("aliases") or [] if snake(a) == h["id"]]
            sys_ = [re.sub(r" \([^()]*\)$", "", t) for w in ws for t in w["symbols"].split("; ") if t]
        for a in als:
            out.setdefault((eid, "alias", X.norm_label(a)), ref)
        for t in sys_:
            out.setdefault((eid, "symbol", X.symbol_key(t)), ref)
    return out


def audit_round(n):
    """P157d: A1-A3 of round n (the P157c audit), written to kb/reports/R<n>_apply.{A1,A2,A3,A3_pending}.csv, .acceptance.txt and .html.
    A1: every decision of the round (history.csv; back-fill rows extend its never labels) and every row it covered (the snapshot), with
    where the row is now: a fact (promoted.csv), never (unmapped.csv column never) or open. A2: every promotion in the round's papers,
    agree when the record's meaning and the entry share the head noun (P165: a promotion through a paper-local symbol of the record's
    paper is "symbol (paper-local)", no head-noun test). A3: every open row, classified; every pending candidate of the
    round's papers accounted for. Acceptance: A1 every covered row has its effect, except a reject (by design), a paper with no compiled
    output and the unit row of a promoted record (a units.yaml matter); A2 no disagree; A3 no unclassified row, no pending candidate
    lost a row (P189, user: a row an adopted re-extraction retired, retired_by, is dormant, listed with the version, not lost). P162: A3 is open_rows() (a row born after apply: NEW_SINCE_APPLY, carried, not a failure); A1 also reads the papers of rows
    a propose carried into the round (carried_rows). Returns the failures (printed by the caller, never silenced)."""
    rnd = next((r for r in rounds() if r["round"] == str(n)), None)
    if rnd is None:
        raise Stop(f"no round {n}")
    pids = [p for p in rnd["pids"].split(";") if p]
    snap = rd(REPORTS / f"R{n}_apply.decision_rows.csv")
    if not snap:
        raise Stop(f"kb/reports/R{n}_apply.decision_rows.csv missing (written by apply before it changes anything)")
    compiled = {p for p in pids if (COMPILED / f"{p}.facts.csv").exists()}
    a1p = compiled | {r["pid"] for r in snap if (COMPILED / f"{r['pid']}.facts.csv").exists()}   # P162: + the papers of rows carried in (A1 only)
    unm = {p: rd(COMPILED / f"{p}.unmapped.csv") for p in a1p}
    pro = {p: rd(COMPILED / f"{p}.promoted.csv") for p in a1p}
    hist = [h for h in rd(HISTORY) if h["round"] == str(n)]
    nev = [r for r in X.never_rows() if r["source"].startswith(f"round {n}")]
    never_of = defaultdict(list)                                               # decision id -> its never.csv rows
    for r in nev:
        m = re.match(rf"round {n}: (?:symbol of )?(\S+)$", r["source"])
        never_of[m.group(1) if m else snake(r["label"])].append(r)
    entries = {e["id"]: e for e in onto()["entries"]}
    fails, a1 = [], []
    pool, used = defaultdict(list), Counter()
    for p in a1p:
        for u in unm[p]:
            pool[(p, u["element"], u["field"], X.norm_label(u["label_as_printed"]))].append(u)   # P191 (user): the label normalized, the unit not in the key
    taken_pro = set()
    resolving = defaultdict(list)                                               # P169: entry id -> every promoted row of a compiled paper
    for f in sorted(COMPILED.glob("*.promoted.csv")):
        for x in rd(f):
            if not x["outcome"].startswith("not promoted"):
                resolving[x["id"]].append(dict(x, pid=f.name[:-len(".promoted.csv")]))
    decisions = {}
    for h in hist:
        if h["action"] in ("add", "alias", "never", "reject") and "back-fill" not in h["decided_by"]:
            decisions.setdefault(h["id"], h)
    for cid, h in decisions.items():
        act = h["action"]
        if act == "never":
            covers = "; ".join(f"{r['label']}" + (f" (symbol, {PAPERS.get(r['paper'], r['paper'])} only)" if r.get("symbol") == "yes" else " (any paper)") for r in never_of[cid])
        elif act == "alias":
            covers = f"alias of {h['target']}: " + "; ".join(a for a in (entries.get(h["target"], {}).get("aliases") or []) if snake(a) == cid)
        else:
            covers = cid.replace("_", " ")
        rows = [r for r in snap if r["candidate"] == cid]
        src = [p for p in h["source_pids"].split(";") if p]
        base = dict(id=cid, decision=act + (f" -> {h['target']}" if h["target"] else ""), covers=covers)
        if act == "add":                                                        # P169 (user): an accept's effect is every compiled row that
            for x in resolving.get(cid, []):                                    # resolves to the new entry, by any path (label, alias, symbol)
                if not any(r["pid"] == x["pid"] and r["element"] == x["element"] and r["label"] == x["printed"] for r in rows):
                    a1.append(dict(base, pid=x["pid"], element=x["element"], field=x["field"], row_label=x["printed"],
                                   now=f"fact: {cid} ({x['lookup']}); {x['outcome']}", effect="yes", reason="resolves to the entry (not the candidate's own row)"))
            if not rows and resolving.get(cid):
                continue
        if not rows:
            labs = {X.norm_label(t) for t in [cid.replace("_", " ")] + [a for a in (entries.get(h["target"], {}).get("aliases") or []) if snake(a) == cid]}
            carried = [p for p in src if (COMPILED / f"{p}.facts.csv").exists() and any(X.norm_label(x.get("label_as_printed", x.get("printed", ""))) in labs
                       for x in rd(COMPILED / f"{p}.unmapped.csv") + rd(COMPILED / f"{p}.promoted.csv"))]
            why = (f"no compiled output for {', '.join(src)}" if src and not any((COMPILED / f"{p}.facts.csv").exists() for p in src)   # P168 fix: the papers
                   else "no row of this decision in the snapshot" if carried or not src                                              # themselves; P169:
                   else f"no compiled row of {', '.join(PAPERS.get(p, p) for p in src)} carries its label (no compiled output)")    # nothing to trace
            a1.append(dict(base, now="none", effect="n/a" if "no compiled output" in why else "no effect", reason=why))
            if "no compiled output" not in why and act != "reject":
                fails.append(f"A1 {cid}: {why}")
            continue
        for r in rows:
            k = (r["pid"], r["element"], r["field"], X.norm_label(r["label"]))
            hits = pool.get(k, [])
            u = hits[used[k]] if used[k] < len(hits) else None
            used[k] += 1 if u else 0
            row = dict(base, pid=r["pid"], element=r["element"], field=r["field"], row_label=r["label"])
            if r["pid"] not in a1p:
                a1.append(dict(row, now="none", effect="n/a", reason=f"no compiled output for {r['pid']}"))
                continue
            if u is None and r["field"] == "axis":                              # P176: a figure label closes at import (kb/<pid>.figures.json)
                fl = figure_label(r["pid"], r["element"], r["label"])
                ok = bool(fl) and ((act == "alias" and fl["quantity"] == h["target"]) or (act == "add" and fl["quantity"] == cid))
                a1.append(dict(row, now=f"figure label: {fl['quantity']} ({fl['how']})" if fl else "not in unmapped.csv, no figure label",
                               effect="yes" if ok else "no effect", reason="" if ok else (f"resolves to {fl['quantity']}" if fl else "row not found")))
                if not ok and act != "reject":
                    fails.append(f"A1 {cid}: {r['pid']}:{r['element']} {r['field']} '{r['label']}': " + (f"resolves to {fl['quantity']}" if fl else "row not found"))
                continue
            if u is None:
                p = next((x for i, x in enumerate(pro[r["pid"]]) if (r["pid"], i) not in taken_pro and x["element"] == r["element"] and x["field"] == r["field"]
                          and (X.norm_label(x["printed"]) == X.norm_label(r["label"]) or not r["label"]) and not x["outcome"].startswith("not promoted")), None)
                if p:
                    taken_pro.add((r["pid"], pro[r["pid"]].index(p)))
                ok = bool(p) and ((act == "alias" and p["id"] == h["target"]) or (act == "add" and p["id"] == cid))
                ret = retired_by(r["pid"], r["element"], r["label"], unit=r["field"] == "unit") if not p else ""   # P187 (user): dormant, not a failure
                if ret:
                    a1.append(dict(row, now="not in unmapped.csv, not promoted", effect="dormant",
                                   reason=f"dormant: the records were replaced by the adopted {ret} lines, which no longer give the label as other"
                                          f"{' with a unit' if r['field'] == 'unit' else ''} (retired by {ret})"))
                    continue
                a1.append(dict(row, now=f"fact: {p['id']} ({p['lookup']}); {p['outcome']}" if p else "not in unmapped.csv, not promoted",
                               effect="yes" if ok else "no effect", reason="" if ok else (f"promoted to {p['id']}" if p else "row not found")))
                if not ok and act != "reject":
                    fails.append(f"A1 {cid}: {r['pid']}:{r['element']} {r['field']} '{r['label']}': " + (f"promoted to {p['id']}" if p else "row not found"))
                continue
            if u["never"]:
                ok = act == "never"
                a1.append(dict(row, now=f"never: {u['never']} ({u['action']})" if u["field"] == "quantity" else f"never: {u['never']} (unit row of a never record)",
                               effect="yes" if ok else "no effect", reason="" if ok else "marked never, but the decision is not never"))
                if not ok and act != "reject":
                    fails.append(f"A1 {cid}: {r['pid']}:{r['element']} never, decision {act}")
                continue
            if act == "reject":
                a1.append(dict(row, now="unmapped (open)", effect="n/a", reason="reject writes nothing to ontology.yaml or never.csv (by design)"))
                continue
            if u["field"] == "unit" and act in ("alias", "add"):
                a1.append(dict(row, now="unmapped (open): unit row", effect="n/a", reason="the record is promoted; its unit is not in units.yaml"))
                continue
            mm = re.match(r"kept \(names the (model|method) (\S+)\)", u["action"])
            if mm and mm.group(2) == (h["target"] if act == "alias" else cid):      # P172, P176: the record names the decision's model or method
                a1.append(dict(row, now=f"unmapped: {u['action']}", effect="yes", reason=f"a record of no quantity naming the decided {mm.group(1)} entry"))
                continue
            key = X.record_key(u)
            a1.append(dict(row, now="unmapped (open)" + (f": {u['action']}" if u["action"] != "kept" else ""), effect="no effect",
                           reason=f"record key '{key}' (symbol key '{X.symbol_key(X.record_text(u))}') matches none of: {covers}"))
            fails.append(f"A1 {cid}: {r['pid']}:{r['element']} {r['field']} '{r['label']}' open")
    write(REPORTS / f"R{n}_apply.A1.csv", A1_COLS, a1)
    # A2
    a2 = []
    user = user_labels(entries)                                                 # P169
    for p in sorted(compiled):
        for x in pro[p]:
            if x["field"] in ("quantity", "model"):                             # P168: a model promotion against the entry's name
                es = [entries.get(i, {}) for i in x["id"].split(" | ")]
                name, defi = " | ".join(e.get("name", "") for e in es), " | ".join(e.get("definition", "") for e in es)
                hd = head_noun(defi)
            else:
                q = x["lookup"].split(":")[1].strip()
                name, defi = x["id"], f"a value of {q}"
                hd = head_noun(entries.get(q, {}).get("definition", ""))
            hr, hn = head_noun(x.get("meaning") or x["printed"]), head_noun(name.replace("_", " "))
            sym = re.search(r"symbol '(.*)' of this paper", x["lookup"])           # P165 (user): a paper-local symbol of the record's own paper
            al = re.search(r"\balias '(.*)'$", x["lookup"])
            ref = (user.get((x["id"], "symbol", X.symbol_key(sym.group(1)))) if sym else user.get((x["id"], "alias", X.norm_label(al.group(1)))) if al else None)
            verdict = "not promoted (ambiguous)" if x["outcome"].startswith("not promoted") else \
                (f"{'symbol' if sym else 'alias'} (user decision)" if ref else "symbol (paper-local)" if sym else    # P169: a user's alias / symbol
                 "alias (curated)" if al else "id (curated)" if re.search(r"\bid '(.*)'$", x["lookup"]) else   # P176 (user): an alias of the entry, or its id,
                 #                                                                  is a curated equality
                 "agree" if hr and hr in (hn, hd) else "disagree" if hr else "no meaning text")
            a2.append(dict(pid=p, element=x["element"], field=x["field"], printed=x["printed"], record_meaning=x.get("meaning", ""), lookup=x["lookup"], entry=x["id"],
                           entry_name=name, entry_definition=defi, head_record=hr, head_entry_name=hn, head_entry_definition=hd, verdict=verdict,
                           symbol=sym.group(1) if sym else "", history=ref or "", outcome=x["outcome"]))
            if verdict in ("disagree", "no meaning text"):
                fails.append(f"A2 {p}:{x['element']} '{x['printed']}' -> {x['id']}: {verdict} (head nouns {hr} / {hn} / {hd})")
    write(REPORTS / f"R{n}_apply.A2.csv", A2_COLS, a2)
    a3, fails3, _ = open_rows(n, compiled, unm, snap)
    fails += fails3
    write(REPORTS / f"R{n}_apply.A3.csv", A3_COLS, a3)
    a3p = []
    open_now = {(u["pid"], u["element"], u["field"]) for p in a1p for u in unmapped_rows(p) if not u["never"]}   # P176: the snapshot's papers, as A1
    #                                                                             reads them (a carried row's paper is not the round's)
    for x in rd(PENDING):                                                       # P176: every pending row, by (id, first round)
        cid = x["id"]
        xp = [p for p in x["pids"].split(";") if p]
        fr = int(x["first_round"] or 0)
        at = [r for r in snap if r["candidate"] == cid] if fr <= n else []    # P176: keyed by (id, first round): a later
        now = [r for r in a3 if r["class"] == f"pending candidate {cid}"]                             # round's row of the same id is another candidate
        if not set(xp) & set(pids) and not at:
            if not set(xp) & {p.stem for p in COMPILED.glob("*.facts.csv")}:
                a3p.append(dict(candidate=cid, first_round=x["first_round"], pids=x["pids"], rows_at_snapshot=0, open_rows_now=0, accounted="yes",
                                detail=f"no compiled output for {x['pids']} (its paper is not compiled)"))
            continue
        if fr > n and not at:                                                   # P195 (user): whatever round first held it: the rows of the
            at = [r for r in rd(REPORTS / f"R{fr}_apply.decision_rows.csv") if r["candidate"] == cid and r["pid"] in pids]   # candidate's first round, this round's papers
        dorm = [(r, ret) for r in at for ret in [retired_by(r["pid"], r["element"], r["label"])] if ret]   # P189, P195 (user): dormant when an adopted
        lost = [r for r in at if (r["pid"], r["element"], r["field"]) not in open_now   # re-extraction no longer prints the label at the element
                and not any(r is d for d, _ in dorm)]                           # P176: closed; a row regrouped since apply is still open
        ok = not lost and bool(now or at)
        a3p.append(dict(candidate=cid, first_round=x["first_round"], pids=x["pids"], rows_at_snapshot=len(at), open_rows_now=len(now),
                        accounted=("dormant" if dorm else "yes") if ok else "NO",
                        detail="; ".join([f"{r['pid']}:{r['element']} {r['field']} '{r['label']}' is no longer open" for r in lost]
                                         + [f"{r['pid']}:{r['element']} {r['field']} '{r['label']}' dormant: the records were replaced by the adopted {ret} lines, "
                                            f"which no longer give the label as other (retired by {ret})" for r, ret in dorm]) or ("" if now else "no open row")))
        if not ok:
            fails.append(f"A3 pending {cid}: " + (a3p[-1]["detail"] or "no open row"))
    write(REPORTS / f"R{n}_apply.A3_pending.csv", A3P_COLS, a3p)
    eff = Counter(r["effect"] for r in a1)
    acc = [f"round {n} acceptance (grow.py audit_round)", f"A1: {len(decisions)} decisions, {len(a1)} rows: effect {dict(eff)}",
           f"A2: {len(a2)} promotions: {dict(Counter(r['verdict'] for r in a2))}", f"A3: {len(a3)} open rows: {dict(Counter(r['class'].split(' ')[0] for r in a3))}; "
           f"pending candidates accounted {sum(1 for r in a3p if r['accounted'] == 'yes')}/{len(a3p)}",
           f"A3 {NEW_SINCE_APPLY} (P162, carried, not a failure): {sum(1 for r in a3 if r['class'] == NEW_SINCE_APPLY)} rows"
           + "".join(f"\n  {r['pid']}:{r['element']} {r['field']} '{r['label']}'" for r in a3 if r["class"] == NEW_SINCE_APPLY),
           "result: " + ("PASS" if not fails else f"FAIL ({len(fails)})")] + [f"FAIL {f}" for f in fails]
    (REPORTS / f"R{n}_apply.acceptance.txt").write_text("\n".join(acc) + "\n", encoding="utf-8")
    R_ = f"psed_v2/kb/reports/R{n}_apply"
    subprocess.run([sys.executable, str(V2 / "kb" / "report.py"), f"{R_}.html", f"Acceptance={R_}.acceptance.txt",
                    f"A1 decision trace: every decision, every row it covered, where it is now={R_}.A1.csv",
                    f"A2 promotions in the round's papers, head-noun check={R_}.A2.csv", f"A3 open rows, classified={R_}.A3.csv",
                    f"A3 pending candidates of the round's papers={R_}.A3_pending.csv", f"Snapshot: every row of the round before apply={R_}.decision_rows.csv"],
                   cwd=ROOT, check=True, capture_output=True)
    print("\n".join(acc))
    return fails


def cmd_audit(n):
    fails = audit_round(int(n))
    report_page()
    return fails


# ---------------------------------------------------------------- P172: grow.py run, papers 14+ end to end with gates
EXTRACT, PILOT = V2 / "kb" / "extract", V2 / "kb" / "pilot"


def paper_index():
    """The paper index (kb/pilot/elements.py PAPERS with kb/pilot/paper_keys.csv), read in a subprocess (grow.py imports nothing of the
    project but export)."""
    code = f"import sys, json; sys.path.insert(0, {str(PILOT)!r}); import elements; print(json.dumps(elements.PAPERS))"
    return json.loads(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout)


def new_key(pid, index):
    """A paper key from corpus/manifest.csv: the first author's surname, its first three letters (ASCII, lower case), and the year's last two
    digits (Werbrouck 2021 -> wer21); a key already taken gets b, c, ..."""
    import unicodedata
    row = next((r for r in rd(V2 / "corpus" / "manifest.csv") if r["paper_id"] == pid), None)
    if not row or not row["authors"] or not row["year"]:
        raise Stop(f"{pid}: no authors or year in corpus/manifest.csv; give it a key by hand (kb/pilot/paper_keys.csv)")
    sur = re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", row["authors"].split(";")[0].strip().split()[-1]).encode("ascii", "ignore").decode().lower())
    key, taken = f"{sur[:3]}{row['year'][-2:]}", set(index.values())
    for suf in [""] + list("bcdefgh"):
        if key + suf not in taken:
            return key + suf
    raise Stop(f"{pid}: no free key for {key}")


def table_shapes(pid):
    """P195 (user) A5: {table id: (header cells, body columns)} as the ingest built the elements (kb/pilot/<pid>.elements.csv: row 0 the
    header; a body column counts when a body row holds an element in it)."""
    rows = defaultdict(lambda: defaultdict(set))
    for r in rd(PILOT / f"{pid}.elements.csv"):
        m = re.fullmatch(r"(tab\w*?)\.r(\d+)c(\d+)", r["element_id"])
        if m:
            rows[m.group(1)][int(m.group(2))].add(int(m.group(3)))
    return {t_: (len(rs.get(0, ())), len(set().union(*[c for i, c in rs.items() if i > 0]))) for t_, rs in rows.items()}


def table_header_decided(pid):
    """P195 (user) A5: the tables of a paper with a user's table_header decision (history.csv kind table_header). P200 (user): the latest
    row per (paper, table) decides; target {} = no decision (as elements.header_decisions, which text_gate reads)."""
    last = {h["id"]: h["target"] for h in rd(HISTORY) if h["kind"] == "table_header" and h["decided_by"] == "user" and pid in h["source_pids"].split(";")}
    return {t_ for t_, tg in last.items() if json.loads(tg or "{}")}


def text_gate(pids):
    """P199 (user): the elements whose text (kb/pilot/elements.py texts, as sent) holds NUL or U+FFFD and that no table_header decision
    covers (a decided header cell tab<n>.r0c<j>): [{pid, element, nul, fffd}], read in a subprocess (as paper_index)."""
    code = (f"import sys, json; sys.path.insert(0, {str(PILOT)!r}); import elements as E; d = E.header_decisions(); out = []\n"
            f"for p in {list(pids)!r}:\n"
            "    cov = {f'{t}.r0c{j}' for (q, t), cols in d.items() if q == p for j in cols}\n"
            "    out += [dict(pid=p, element=e, nul=x.count(chr(0)), fffd=x.count(chr(0xfffd))) for e, x in E.texts(p).items()\n"
            "            if (chr(0) in x or chr(0xfffd) in x) and e not in cov]\n"
            "print(json.dumps(out))")
    return json.loads(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout)


def cmd_run(args, yes=False, plan_only=False):
    """P172 (user): papers 14+ end to end, 3 per round: resolve the papers (paper key: kb/pilot/paper_keys.csv; elements.csv; the figure
    stage and its import when figures.json is missing) -> pass 0 -> units from curves + the consistency, model-named and measurement-named
    checks (printed by pass 0) -> GATE -> pass 1 -> compile -> check.py -> inspection (P174: kb/extract/inspection.py, sections 5a-5h) -> gates
    after pass 1 -> the audits of the applied rounds and export
    --check -> grow.py add + propose -> decide.html -> stop. The planned provider calls and dollars are printed before the first call; a y/n is
    asked unless --yes; --plan stops after the plan. GATE (gates.py, ontology/gates.csv: the worst of the twelve development papers):
    a. pass 0 lists no run and no simulation, or fewer than 3 units; b. a pass-0 value worse than the worst development value; c. a provider
    error or a cached-prefix failure (any non-zero exit of a provider step). P173: the figures import gives a paper 14+ its verdicts by rule
    (kb/figures_import.py: the figure stage's flags), so gate d (no verdicts, P172) is gone. After pass 1 (before propose): form failures or quotes not found
    worse than the worst development value; an earlier round's audit FAIL; export --check FAIL. Every run writes kb/reports/RUN_<keys>.html
    with its plan, its gate tables, its steps and (P174) the no-gold inspection of each compiled paper. P201 (user): after the figures import,
    the figure-label job (kb/extract/figure_axes.py, records pass 0ax, one call per paper) and the import again, then pass 0 and pass 1."""
    if not 1 <= len(args) <= 3:
        raise Stop("grow.py run takes 1 to 3 papers (one round)")
    py, steps, stopped = sys.executable, [], ""
    manifest = {r["paper_id"] for r in rd(V2 / "corpus" / "manifest.csv")}
    index = paper_index()
    by_key = {k: p for p, k in index.items()}
    pids, added = [], []
    for a in args:
        pid = by_key.get(a, a)
        if pid not in manifest:
            raise Stop(f"{a}: not a paper_id of corpus/manifest.csv nor a paper key")
        if not (FINAL / pid / "document.md").exists():
            raise Stop(f"{pid}: no ingest/final/{pid}/document.md (ingest first)")
        if pid not in index:
            key = new_key(pid, index)
            index[pid] = key
            added.append(dict(paper_id=pid, key=key))
        pids.append(pid)
    if added:
        kf = PILOT / "paper_keys.csv"
        write(kf, ["paper_id", "key"], rd(kf) + added)
    keys = [index[p] for p in pids]
    tag = "_".join(keys)

    inspected = []

    def step(name, cmd):
        p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        steps.append(dict(step=name, command=" ".join(str(c).replace(str(ROOT) + "/", "") for c in cmd), exit=p.returncode, output=out[-3000:]))
        print(f"== {name}: exit {p.returncode}\n{out[-1500:]}")
        return p.returncode, out

    def finish(msg=""):
        R_ = REPORTS / f"RUN_{tag}"
        write(Path(f"{R_}.steps.csv"), ["step", "command", "exit", "output"], steps)
        Path(f"{R_}.summary.txt").write_text((f"STOPPED: {msg}\n" if msg else "") + "\n".join(f"{s['step']}: exit {s['exit']}" for s in steps) + "\n", encoding="utf-8")
        parts = [f"Summary={R_}.summary.txt", f"Plan (calls and dollars per step)={R_}.plan.csv", f"Gates (ontology/gates.csv: the worst development values)={GATES_CSV}"]
        parts += [f"Gate {g} ({k})={REPORTS / f'RUN_{k}.gate_{g}.csv'}" for k in keys for g in ("pass0", "pass1") if (REPORTS / f"RUN_{k}.gate_{g}.csv").exists()]
        if (REPORTS / f"RUN_{tag}.gate_tables.csv").exists():                 # P195 (user) A5: the tables the header gate stopped on
            parts += [f"Table header gate (header cells vs body columns, no table_header decision)={REPORTS / f'RUN_{tag}.gate_tables.csv'}"]
        if (REPORTS / f"RUN_{tag}.gate_text.csv").exists():                   # P199 (user): the elements the text gate stopped on
            parts += [f"Text gate (NUL or U+FFFD in an element text, no table_header decision)={REPORTS / f'RUN_{tag}.gate_text.csv'}"]
        parts += [f"Steps={R_}.steps.csv"]
        if inspected:                                                           # P174 (user): the no-gold inspection, sections 5a-5h, of every paper
            sys.path.insert(0, str(EXTRACT))
            import inspection
            parts += [f"{k} {t}={p}" for k in inspected for t, p in inspection.parts(f"RUN_{k}")]
        subprocess.run([sys.executable, str(V2 / "kb" / "report.py"), f"{R_}.html", *parts], cwd=ROOT, check=True, capture_output=True)
        print(f"run report: {R_}.html" + (f"; STOPPED: {msg}" if msg else ""))
        if msg:
            raise Stop(msg)

    need = [p for p in pids if not (PILOT / f"{p}.elements.csv").exists()]
    if need:
        step("elements (0 calls)", [py, PILOT / "elements.py", "--ids", *need])
    bad = [dict(paper=index[p], pid=p, table=t_, header_cells=h, body_columns=b) for p in pids for t_, (h, b) in sorted(table_shapes(p).items())
           if h != b and t_ not in table_header_decided(p)]                    # P195 (user) A5: the table-header gate
    if bad:
        write(REPORTS / f"RUN_{tag}.gate_tables.csv", ["paper", "pid", "table", "header_cells", "body_columns"], bad)
        finish("table header gate: header cells differ from body columns with no table_header decision: "
               + "; ".join(f"{x['paper']} {x['table']} ({x['header_cells']} header cells, {x['body_columns']} body columns)" for x in bad))
    bad = [dict(paper=index[x["pid"]], **x) for x in text_gate(pids)]          # P199 (user): the text gate
    if bad:
        write(REPORTS / f"RUN_{tag}.gate_text.csv", ["paper", "pid", "element", "nul", "fffd"], bad)
        finish("text gate: an element text holds NUL or U+FFFD with no table_header decision: "
               + "; ".join(f"{x['paper']} {x['element']} (NUL {x['nul']}, U+FFFD {x['fffd']})" for x in bad))
    rc, out = step("plan (0 calls)", [py, EXTRACT / "gates.py", "plan", *keys])
    plan = json.loads(out.strip().splitlines()[-1]) if rc == 0 else []
    write(Path(f"{REPORTS / f'RUN_{tag}'}.plan.csv"), ["paper", "pid", "figure_calls", "figure_usd", "axes_calls", "axes_usd", "pass0_calls", "pass0_usd", "pass1_calls",
                                                      "pass1_usd", "note"], plan)
    calls = sum(x["figure_calls"] + x["axes_calls"] + x["pass0_calls"] + x["pass1_calls"] for x in plan)
    usd = sum(x["figure_usd"] + x["axes_usd"] + x["pass0_usd"] + x["pass1_usd"] for x in plan)
    for x in plan:
        print(f"{x['paper']}: figure stage {x['figure_calls']} calls (${x['figure_usd']}), figure axes {x['axes_calls']} (${x['axes_usd']}), "
              f"pass 0 {x['pass0_calls']} (${x['pass0_usd']}), pass 1 {x['pass1_calls']} (${x['pass1_usd']})")
    print(f"planned: {calls} provider calls, about ${usd:.2f}")
    if plan_only:
        return finish()
    if calls and not yes:
        try:
            ok = input(f"make these {calls} provider calls (about ${usd:.2f})? [y/N] ").strip().lower() == "y"
        except EOFError:
            ok = False
        if not ok:
            return finish("no y given: no call made")
    for x in plan:
        if x["figure_calls"]:
            if step(f"figure stage {x['paper']} ({x['figure_calls']} vision calls)", [py, V2 / "ingest" / "figures.py", "--ids", x["pid"]])[0]:
                return finish(f"gate c: the figure stage of {x['paper']} failed")
            step(f"elements {x['paper']} again, with the figure stage's panels (0 calls)", [py, PILOT / "elements.py", "--ids", x["pid"]])
        step(f"figures import {x['paper']} (0 calls; P173 rule verdicts)", [py, V2 / "kb" / "figures_import.py", x["pid"]])
        if x.get("axes_calls"):                                                 # P201 (user): the figure-label job, then the import again with its answers
            if step(f"figure axes {x['paper']} ({x['axes_calls']} call)", [py, EXTRACT / "figure_axes.py", x["pid"]])[0]:
                return finish(f"gate c: the figure-label job of {x['paper']} failed")
            step(f"figures import {x['paper']} again, with the 0ax answers (0 calls)", [py, V2 / "kb" / "figures_import.py", x["pid"]])
    for k in keys:
        if step(f"pass 0 {k}", [py, EXTRACT / "pass0_paper.py", k])[0]:
            return finish(f"gate c: pass 0 of {k} failed (provider error)")
    bad = [k for k in keys if step(f"gate pass 0 {k}", [py, EXTRACT / "gates.py", "pass0", k])[0]]
    if bad:
        return finish(f"pass-0 gate: {', '.join(bad)} (see the gate table)")
    for k in keys:
        if step(f"pass 1 {k}", [py, EXTRACT / "pass1_elements.py", k])[0]:
            return finish(f"gate c: pass 1 of {k} failed (provider error or cached-prefix failure)")
    for k, pid in zip(keys, pids):
        if step(f"compile {k} (0 calls)", [py, EXTRACT / "compile.py", k])[0]:
            return finish(f"compile of {k} failed")
        step(f"check.py {k} (0 calls)", [py, "-c", f"import sys; sys.path.insert(0, {str(EXTRACT)!r}); import score; e, _ = score.check_dir({pid!r}); print(len(e), 'check.py problems')"])
        if not step(f"inspection {k} (0 calls; sections 5a-5h)", [py, EXTRACT / "inspection.py", k, "--prefix", f"RUN_{k}"])[0]:   # P174 (user): every run
            inspected.append(k)
    bad = [k for k in keys if step(f"gate pass 1 {k}", [py, EXTRACT / "gates.py", "pass1", k])[0]]
    if bad:
        return finish(f"pass-1 gate: {', '.join(bad)} (see the gate table); stopped before propose")
    for r in rounds():
        if r["status"] == "applied" and (REPORTS / f"R{r['round']}_apply.decision_rows.csv").exists():
            fails = audit_round(int(r["round"]))
            steps.append(dict(step=f"audit round {r['round']}", command="grow.py audit", exit=len(fails), output="; ".join(fails)[:3000]))
            if fails:
                return finish(f"round {r['round']} audit FAIL ({len(fails)}); stopped before propose")
    if step("export --check (0 calls)", [py, HERE / "export.py", "--check"])[0]:
        return finish("export --check failed; stopped before propose")
    cmd_add(pids)
    steps.append(dict(step="grow.py add", command="cmd_add", exit=0, output=", ".join(keys)))
    cmd_propose()
    steps.append(dict(step="grow.py propose", command="cmd_propose", exit=0, output=str(DECIDE.relative_to(ROOT))))
    return finish()


def cmd_status():
    r = current()
    print(f"open round: {r['round']} ({r['status']}; {r['pids']})" if r else "no open round")
    rows = rd(PENDING)
    print("pending.csv:", dict(Counter(x["decision"] or "undecided" for x in rows)), f"({len(rows)} rows)")
    for h in rd(HISTORY)[-10:]:
        print(f"  {h['date']} round {h['round']} {h['action']} {h['id']} ({h['kind']}) {h['decided_by']}: {h['reason'][:80]}")


# ---------------------------------------------------------------- round 0 (once)
def cmd_init():
    if any(r["round"] == "0" for r in rounds()):
        raise Stop("round 0 is in rounds.csv already")
    rel = "psed_v2/ontology/ontology.yaml"
    log = subprocess.run(["git", "log", "--reverse", "--format=%h|%ad|%s", "--date=short", "--", rel], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    first = {}
    for line in log:
        h, d, s = line.split("|", 2)
        blob = subprocess.run(["git", "show", f"{h}:{rel}"], cwd=ROOT, capture_output=True, check=True).stdout
        for eid in re.findall(r"(?m)^  - id: (\S+)$", blob.decode("utf-8")):
            first.setdefault(eid, (h, d, s, hashlib.sha256(blob).hexdigest()))
    c_methods = {r["id"] for r in rd(V2 / "kb" / "reports" / "P142b_ontology.c_methods.csv") if r.get("ontology_entry") == "yes"}
    o, dois, out, missing = onto(), doi_of(), [], []
    for e in o["entries"]:
        if e["id"] not in first:
            missing.append(e["id"])
            continue
        h, d, s, blob_sha = first[e["id"]]
        keys = [(x.split()[1] if x.startswith("quote ") else x.split()[0]) for x in (e.get("evidence") or []) if str(x).split()]
        pids = list(dict.fromkeys(KEY2PID[k] for k in keys if k in KEY2PID and k not in HELD and KEY2PID[k] not in HELD))
        dev = e.get("deviation") or {}
        reason = f"origin {e.get('origin', '')}; first in {h} {d} ({s[:70]})" + (f"; deviation {dev.get('type')}: {str(dev.get('reason', ''))[:100]}" if dev else "") \
            + ("; P142b: a method made an entry (kb/reports/P142b_ontology.c_methods.csv)" if e["id"] in c_methods else "")
        out.append(dict(date=d, round=0, action="add", id=e["id"], kind=e["type"], target="", source_pids=";".join(pids),
                        source_dois=";".join(dois.get(p, "") for p in pids), decided_by="pilot", reason=HELD_RX.sub("held-out", reason) if HELD_RX else reason, ontology_sha256_after=blob_sha))
    never = [x for x in X.never_rows() if x["source"].startswith("pilot")]
    nev_pids = lambda k: KEY2PID.get(k, k if k.startswith("10.") else "")   # noqa: E731
    out += [dict(date=today(), round=0, action="never", id=snake(x["label"]), kind="", target=x["category"], source_pids=nev_pids(x["paper"]),
                 source_dois=dois.get(nev_pids(x["paper"]), ""), decided_by="pilot", reason=f"pilot hand row (unmapped.csv, field pilot): {x['label']}; moved to never.csv in P155",
                 ontology_sha256_after=sha(ONTO)) for x in never]
    append(HISTORY, HISTORY_COLS, out)
    pids = sorted({p for r in out for p in r["source_pids"].split(";") if p})
    rs = rounds()
    rs.insert(0, dict(round=0, opened=min(r["date"] for r in out), applied=today(), pids=";".join(pids), dois=";".join(dois.get(p, "") for p in pids),
                      status="applied", n_candidates="", n_accepted=len(o["entries"]), n_alias=0, n_rejected=0, n_never=len(never)))
    write(ROUNDS, ROUND_COLS, rs)
    print(f"round 0: {len(out)} history rows ({len(out) - len(never)} entries, {len(never)} never); entries with no history row: {missing or 'none'}")
    return missing


# ---------------------------------------------------------------- ontology.html (make_report.py's sections, P155 order)
STYLE = ("body{font-family:sans-serif;font-size:13px;margin:16px;color:#222;background:#fff}table{border-collapse:collapse;margin:8px 0 16px}"
         "th,td{border:1px solid #bbb;padding:3px 6px;text-align:left;vertical-align:top}th{background:#eee}td ul{margin:0;padding-left:16px}"
         "pre{white-space:pre-wrap;border:1px solid #bbb;padding:8px}.fail{background:#f6c0c0}.pass{background:#d8f0d8}")


def shown(x):
    """A text as the pages show it, never cut (P157f: nothing is withheld; papers 1-12 are development papers)."""
    return "" if x is None else str(x)


def esc(x):
    return html.escape(shown(x))


def table(head, rows, raw=False):
    cell = (lambda c: str(c)) if raw else esc
    return "<table><tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr>" + "".join("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>"


def hierarchy_html(o):
    """Section 8: every node with its definition, the number of entries it holds (its own and its children's) by kind, and the ids of
    its own members (P157: so the summary tree can be checked against it by eye)."""
    nodes, children, _ = X.hierarchy_tree(o)
    members = defaultdict(list)
    for e in o["entries"]:
        if e.get("category"):
            members[e["category"]].append(e)

    def held(c):
        return members[c] + [e for k in children.get(c, []) for e in held(k)]

    def render(pid):
        items = ""
        for c in children.get(pid, []):
            n, h = nodes[c], held(c)
            kinds = ", ".join(f"{k} {v}" for k, v in Counter(e["type"] for e in h).items())
            items += (f"<li><b>{esc(c)}</b> holds {len(h)}{f' ({esc(kinds)})' if h else ''}: {esc(n['definition'])} <i>[{esc(n.get('citation', ''))}]</i>"
                      + (f"<br>ids: {esc(', '.join(e['id'] for e in members[c]))}" if members[c] else "") + render(c) + "</li>")
        return f"<ul>{items}</ul>" if items else ""
    return render(None)


# ---------------------------------------------------------------- the summary tree (P157)
TREE_KINDS = ("quantity", "categorical", "model", "species", "structure", "mechanism", "method")


def node(label, n, children=(), ids=(), text=""):
    """A summary-tree node: its count n is computed from the data on its own, never as the sum of its children (check_tree compares
    them); ids on an 'unplaced' node and on a kind with no grouping field (a flat list); text replaces 'label n' in the drawing."""
    return dict(label=label, n=n, children=[c for c in children if c], ids=list(ids), text=text)


def unplaced(es):
    return node("unplaced", len(es), ids=[e["id"] for e in es]) if es else None


def by_hierarchy(o, es):
    """Entries split by their category: the hierarchy node it names, nested under its parents (only nodes that hold one of es). An entry
    whose category is no hierarchy node goes under 'unplaced'. A non-leaf node holding entries itself (check 8 forbids it) shows them
    as '<node> itself'."""
    nodes, children, _ = X.hierarchy_tree(o)

    def sub(n):
        return {n} | {d for c in children.get(n, []) for d in sub(c)}

    def walk(n):
        held = [e for e in es if e.get("category") in sub(n)]
        if not held:
            return None
        own = [e for e in held if e.get("category") == n]
        kids = [walk(c) for c in children.get(n, [])]
        if any(kids) and own:
            kids.append(node(f"{n} itself", len(own)))
        return node(n, len(held), kids)
    return [walk(t) for t in children.get(None, [])] + [unplaced([e for e in es if e.get("category") not in nodes])]


def by_class(o, es):
    """Structure entries split by their structure class, nested along the class tree (section 7) below its root; an instance counts
    under its class; a class with instances and subclasses shows its own as '<class> itself'; a class not in the tree: 'unplaced'."""
    kids = defaultdict(list)
    for c in o.get("structure_classes", []):
        kids[c.get("parent") or ""].append(c["id"])

    def sub(c):
        return {c} | {d for k in kids.get(c, []) for d in sub(k)}

    def walk(c):
        held = [e for e in es if e.get("class") in sub(c)]
        if not held:
            return None
        own = [e for e in held if e.get("class") == c]
        ch = [walk(k) for k in kids.get(c, [])]
        if any(ch) and own:
            ch.append(node(f"{c} itself", len(own)))
        return node(c, len(held), ch)
    roots = kids.get("", [])
    out = [walk(k) for r in roots for k in kids.get(r, [])] + [node(f"{r} itself", n) for r in roots for n in [sum(1 for e in es if e.get("class") == r)] if n]
    return out + [unplaced([e for e in es if not any(e.get("class") in sub(r) for r in roots)])]


def by_field(es, key, order=()):
    """Entries split by the value key(e) gives, in the given order and then sorted; '' or None: 'unplaced'."""
    vals = Counter(key(e) for e in es if key(e))
    return [node(v, vals[v]) for v in list(dict.fromkeys([v for v in order if v in vals] + sorted(vals)))] + [unplaced([e for e in es if not key(e)])]


def summary_trees(o, hist, pend, nev):
    """The summary as trees: the entries by kind and within a kind by a field it has (quantity, categorical, model: hierarchy leaf;
    species: kind; structure: structure class; method: measurement yes / no); mechanism has no grouping field: a flat list, no unplaced
    check (P157b). Then units (both tables, with their source), qualifier keys, never, pending (by n_papers) and history."""
    entries = o["entries"]
    of = lambda t: [e for e in entries if e["type"] == t]                       # noqa: E731
    split = {"quantity": ("hierarchy leaf", by_hierarchy(o, of("quantity"))),
             "categorical": ("hierarchy leaf", by_hierarchy(o, of("categorical"))),
             "model": ("hierarchy leaf", by_hierarchy(o, of("model"))),
             "species": ("species kind", by_field(of("species"), lambda e: e.get("kind"), X.SPECIES_KINDS)),
             "structure": ("structure class", by_class(o, of("structure"))),
             "method": ("the measurement field", by_field(of("method"), lambda e: {True: "measurement yes", False: "measurement no"}.get(e.get("measurement")), ("measurement yes", "measurement no")))}
    kinds = [node(k, len(of(k)), split[k][1], text=f"{k} {len(of(k))}   [split by {split[k][0]}]") if k in split else
             node(k, len(of(k)), ids=[e["id"] for e in of(k)], text=f"{k} {len(of(k))}   [no grouping field: a flat list]") for k in TREE_KINDS]
    ent = node("entries", len(entries), kinds + [unplaced([e for e in entries if e["type"] not in TREE_KINDS])])
    units = yaml.safe_load((HERE / "units.yaml").read_text(encoding="utf-8"))["units"]
    dims = Counter(u["dimension"] for u in units)
    spell = sum(1 + len(u["variants"]) for u in units)
    species = [e["id"] for e in entries if e["type"] == "species" and not e.get("replaced_by")]
    mats = [e["id"] for e in entries if e["type"] == "species" and e.get("kind") == "material" and not e.get("replaced_by")]
    defs = {d["id"] for e in entries if not e.get("replaced_by") for d in (e.get("definitions") or [])}
    quals = []
    for k, q in o["qualifiers"].items():
        v = X.qualifier_values(q, species, mats, defs)
        quals.append(node(k, 1, text=f"{k}: {len(v)} values" + (f" ({q['values']})" if isinstance(q.get("values"), str) else "") if v is not None else f"{k}: open ({q.get('values')})"))
    src = Counter("pilot" if r["source"].startswith("pilot") else r["source"] for r in nev)
    hist_rounds = defaultdict(Counter)
    for h in hist:
        hist_rounds[h["round"]][h["action"]] += 1
    block = o.get("units") or {}
    n_pap = Counter(min(int(x["n_papers"] or 0), 3) for x in pend)
    rest = [node("units", len(units), [node(d, n) for d, n in dims.most_common()], text=f"units {len(units)} (ontology/units.yaml: symbols, {len(dims)} dimensions)"),
            node("units block", sum(len(u.get("accepted") or []) for u in block.values()),
                 text=f"units {sum(len(u.get('accepted') or []) for u in block.values())} (ontology/ontology.yaml units: block: accepted, {len(block)} dimensions)"),
            node("unit spellings", spell, text=f"unit spellings {spell} (ontology/units.yaml: symbol and variants of each row)"),
            node("qualifier keys", len(o["qualifiers"]), quals),
            node("never", len(nev), [node(c, n) for c, n in Counter(r["category"] for r in nev).most_common()],
                 text=f"never {len(nev)} (" + " + ".join(f"{n} {s}" for s, n in src.items()) + ")"),
            node("pending", len(pend), text=f"pending {len(pend)} (" + (f"no paper {n_pap[0]}, " if n_pap[0] else "") + f"1 paper {n_pap[1]}, 2 papers {n_pap[2]}, 3+ papers {n_pap[3]})"),
            node("history rows", len(hist), [node(f"round {r}", sum(c.values()), [node(a, n) for a, n in c.most_common()]) for r, c in hist_rounds.items()])]
    return [ent] + rest


def draw(n, lead="", last=True, top=True):
    """The tree as text lines: '├─ ' / '└─ ' before a child, '│  ' below an open branch."""
    line = (n["text"] or f"{n['label']} {n['n']}") + (f": {', '.join(n['ids'])}" if n["ids"] else "")
    out = [line if top else lead + ("└─ " if last else "├─ ") + line]
    pad = "" if top else lead + ("   " if last else "│  ")
    for i, c in enumerate(n["children"]):
        out += draw(c, pad, i == len(n["children"]) - 1, False)
    return out


def check_tree(trees):
    """(sum problems, unplaced problems): every parent's n against the sum of its children's n, with the path and the difference; every
    'unplaced' node with its ids (a check failure, reported)."""
    sums, lost = [], []

    def walk(n, path):
        here = f"{path} / {n['label']}" if path else n["label"]
        if n["children"] and sum(c["n"] for c in n["children"]) != n["n"]:
            s = sum(c["n"] for c in n["children"])
            sums.append(f"{here}: {n['n']} but its children sum to {s} (off by {s - n['n']:+d})")
        if n["label"] == "unplaced":
            lost.append(f"{path}: {n['n']} unplaced: {', '.join(n['ids'])}")
        for c in n["children"]:
            walk(c, here)
    for t in trees:
        walk(t, "")
    return sums, lost


def tree_result(trees):
    sums, lost = check_tree(trees)
    return ["sum check: " + ("pass (every parent equals the sum of its children, at every level)" if not sums else "FAIL at " + "; ".join(sums)),
            "unplaced: " + ("none" if not lost else "FAIL: " + "; ".join(lost))]


def structure_classes_html(o):
    kids, inst = defaultdict(list), defaultdict(list)
    for c in o.get("structure_classes", []):
        kids[c.get("parent") or ""].append(c)
    for e in o["entries"]:
        if e["type"] == "structure":
            inst[e.get("class")].append(e["id"])

    def render(pid):
        items = ""
        for c in kids.get(pid, []):
            items += (f"<li><b>{esc(c['id'])}</b>: {esc(c['definition'])} <i>[{esc(c.get('citation', ''))}]</i>"
                      + (f"<br>slots: {esc(', '.join(c.get('slots', [])))}" if c.get("slots") else "<br>slots: none")
                      + (f"<br>instances: {esc(', '.join(inst[c['id']]))}" if inst.get(c["id"]) else "") + render(c["id"]) + "</li>")
        return f"<ul>{items}</ul>" if items else ""
    return render("")


def values_rows(o):
    entries, voc = o["entries"], o["vocabularies"]
    by_id = {e["id"]: e for e in entries}
    rows = []
    for e in entries:
        if e["type"] != "categorical":
            continue
        vf, targets = e["values_from"], X.values_from_targets(e, entries)
        if targets:
            rows.append([e["id"], vf, ", ".join(targets), "; ".join(f"{i}: {', '.join(by_id[i].get('aliases', []))}" for i in targets)])
        elif vf.startswith("fixed list"):
            rows.append([e["id"], vf, ", ".join(map(str, voc.get(e["id"], []))), "; ".join(f"{v}: {', '.join(a)}" for v, a in voc["value_aliases"].get(e["id"], {}).items())])
        else:
            rows.append([e["id"], vf, "—", "—"])
    joint = voc["value_aliases"].get("joint", {})
    rows.append(["(joint)", "value_aliases.joint: one printed value sets two fields", ", ".join(joint), "; ".join(f"{k}: {v}" for k, v in joint.items())])
    return rows


def family_rows(o):
    fam = defaultdict(list)
    for e in o["entries"]:
        if e.get("family") and not e.get("replaced_by"):
            fam[e["family"]].append(e)
    eq = X.entry_qualifiers(o)                                                  # P182: the entry's keys, from the qualifier scopes
    return [[f, "; ".join(f"{e['id']} ({e.get('unit', '')}; {', '.join(eq.get(e['id'], []))})" for e in ms),
             " | ".join(f"{e['id']}: {e['definition'].split('.')[0]}" for e in ms)] for f, ms in sorted(fam.items())]


def ambiguous_keys(o):
    """P157d: every key of compile.py's lookup (export.resolve_index over ontology.yaml) that names two or more entries: [lookup, key, entries]."""
    ents = {e["id"]: e for e in o["entries"]}
    words, syms = X.resolve_index(ents, [i for i, e in ents.items() if e["type"] == "species" and e.get("kind") == "material"])
    out = [[kind, k, "; ".join(f"{i} ({h})" for i, h in sorted(v.items()))] for kind, idx in words.items() for k, v in sorted(idx.items()) if len(v) > 1]
    out += [[f"{kind} symbols", f"{k[1]} in {PAPERS.get(k[0], k[0]) or 'no paper'}", "; ".join(sorted(v))] for kind, idx in syms.items() for k, v in sorted(idx.items()) if len(v) > 1]
    return out


def rounds_audit_html(rs):
    """P157d: per applied round, its acceptance and the A1-A3 tables (kb/reports/R<n>_apply.*, written by audit_round)."""
    out = ""
    for r in rs:
        acc = REPORTS / f"R{r['round']}_apply.acceptance.txt"
        if not acc.exists():
            continue
        text = acc.read_text(encoding="utf-8")
        out += (f"<h3>Round {esc(r['round'])}: decision audit (kb/reports/R{esc(r['round'])}_apply.html)</h3>"
                f"<pre class='{'pass' if 'result: PASS' in text else 'fail'}'>{esc(text)}</pre>")
        for part, cols in (("A1", A1_COLS), ("A2", A2_COLS), ("A3", A3_COLS), ("A3_pending", A3P_COLS)):
            rows = rd(REPORTS / f"R{r['round']}_apply.{part}.csv")
            out += f"<h4>{part} ({len(rows)})</h4>" + table(cols, [[x.get(c, "") for c in cols] for x in rows])
    return out


def report_page():
    o = onto()
    entries = o["entries"]
    by_id = {e["id"]: e for e in entries}
    hist, rs, pend, nev = rd(HISTORY), rounds(), rd(PENDING), X.never_rows()
    axis = [u for r in rs if r["round"] != "0" for p in r["pids"].split(";") if p and (COMPILED / f"{p}.unmapped.csv").exists() for u in unmapped_rows(p) if u["field"] == "axis"]
    checks = X.run_checks(o)
    src = defaultdict(lambda: dict(rounds=[], pids=[], dois=[]))
    for h in hist:
        if h["action"] in ("add", "alias", "edit") and h["id"] in by_id:
            s = src[h["id"]]
            s["rounds"].append(h["round"])
            s["pids"] += [p for p in h["source_pids"].split(";") if p and p not in s["pids"]]
            s["dois"] += [d for d in h["source_dois"].split(";") if d and d not in s["dois"]]
    trees = summary_trees(o, hist, pend, nev)                                   # P157: the entries, units, qualifiers, never, pending, history
    tree_check = tree_result(trees)
    summary = [["ontology.yaml sha256", sha(ONTO)], ["ontology hash (export.ontology_hash: this file without its header line, then units.yaml)", X.ontology_hash()],
               ["rounds", len(rs)], ["figure labels other (compiled unmapped rows, field axis)", len(axis)],
               ["checks passed", f"{sum(1 for c in checks if c[1])} of {len(checks)}"]]
    check_html = "".join(f"<tr class='{'pass' if c[1] else 'fail'}'><td>{esc(c[0])}</td><td>{'pass' if c[1] else 'FAIL'}</td><td>{esc(c[2])}</td>"
                         f"<td>{'<ul>' + ''.join(f'<li>{esc(b)}</li>' for b in c[3]) + '</ul>' if c[3] else '—'}</td></tr>" for c in checks)
    ent_html = ""
    for k in ("quantity", "categorical", "species", "structure", "mechanism", "method", "model"):
        rows = [[e["id"], e.get("name", ""), e.get("definition", ""), e.get("unit", ""), e.get("origin", ""), ", ".join(src[e["id"]]["rounds"]),
                 "; ".join(src[e["id"]]["pids"]), "; ".join(src[e["id"]]["dois"]), "; ".join(map(str, e.get("evidence") or [])),
                 ("replaced by " + (", ".join(e["replaced_by"]) if isinstance(e["replaced_by"], list) else e["replaced_by"])) if e.get("replaced_by") else "",
                 "; ".join(e.get("aliases") or []), "; ".join(f"{x['text']} ({PAPERS.get(x.get('paper', ''), x.get('paper', '')) or 'no paper'})" for x in e.get("symbols") or [])]
                for e in entries if e["type"] == k]
        ent_html += f"<h3>{esc(k)} ({len(rows)})</h3>" + table(["id", "name", "definition", "unit", "origin", "source round", "source pids", "DOIs", "evidence",
                                                                  "replaced", "aliases", "symbols (paper; P157d)"], rows)
    sup = X.never_index([e for e in entries if not e.get("replaced_by")])[1]
    round_pids = [p for r in rs if r["round"] != "0" for p in r["pids"].split(";") if p]
    values = candidates_of(round_pids)[1]["values"] if round_pids else []
    cand = [candidate_cells(x, by_id) + [esc(x["decision"]), esc(x["alias_target"]), esc(x["never_category"]), esc(x["decision_note"]), esc(x["first_round"])] for x in pend]
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>ontology</title><style>{STYLE}</style></head><body><h1>PSED v2 ontology</h1>"
            f"<p>Written by psed_v2/ontology/grow.py (report / apply) from ontology.yaml, units.yaml, history.csv, rounds.csv, pending.csv, never.csv and "
            f"the compiled unmapped rows. Papers 1-12 (the pilot golds) are development papers (P157f); held-out papers (13+) are refused by grow.py add.</p>"
            f"<h2>1. Kinds</h2><pre>{esc(chr(10).join(X.kinds_lines(o)))}</pre>"
            f"<h2>2. Summary</h2><pre>{esc(chr(10).join(draw(trees[0])))}</pre>"
            f"<pre class='{'pass' if tree_check[0].startswith('sum check: pass') and tree_check[1] == 'unplaced: none' else 'fail'}'>{esc(chr(10).join(tree_check))}</pre>"
            f"<pre>{esc(chr(10).join(ln for t in trees[1:] for ln in draw(t)))}</pre>{table(['item', 'value'], summary)}"
            f"<h2>3. Checks (export.py --check)</h2><table><tr><th>check</th><th>result</th><th>detail</th><th>rows</th></tr>{check_html}</table>"
            f"<h3>Ambiguous keys (P157d: a key under two entries promotes nothing in compile.py; listed every round)</h3>"
            f"{table(['lookup', 'key', 'entries'], ambiguous_keys(o))}"
            f"<h2>4. Entries by kind</h2>{ent_html}"
            f"<h2>5. Values</h2>{table(['categorical', 'values_from', 'current values', 'value aliases'], values_rows(o))}"
            f"<h2>6. Families</h2>{table(['family', 'members', 'what they answer'], family_rows(o))}"
            f"<h2>7. Structure classes</h2>{structure_classes_html(o)}"
            f"<h2>8. Hierarchy</h2>{hierarchy_html(o)}"
            f"<h2>9. Units</h2>{table(['dimension', 'canonical', 'accepted'], [[d, u['canonical'], ', '.join(u['accepted'])] for d, u in o['units'].items()])}"
            f"<h2>10. History ({len(hist)} rows)</h2>{table(HISTORY_COLS, [[h[c] for c in HISTORY_COLS] for h in hist])}"
            f"<h2>11. Rounds</h2>{table(ROUND_COLS, [[r[c] for c in ROUND_COLS] for r in rs])}{rounds_audit_html(rs)}"
            f"<h2>12. Pending ({len(pend)} rows; read-only, as decide.html shows them)</h2>"
            + table(CAND_HEAD + ["decision", "alias target", "never category", "note", "first round"], cand, raw=True)
            + f"<h2>13. Never ({len(nev)}; a part that names a live entry is superseded and suppresses nothing)</h2>"
            + table(NEVER_COLS + ["superseded by"], [[x[c] for c in NEVER_COLS] + ["; ".join(f"{p} → superseded by {e}" for lab, p, e in sup if lab == x["label"])] for x in nev])
            + f"<h2>14. Unmapped</h2><h3>Values without a quantity (compiled unmapped rows of the rounds' papers with no label or only a unit; not candidates)</h3>"
            + table(["pid", "element", "raw text", "unit"], [[u["pid"], u["element"], u["quote"], u["unit"]] for u in values])
            + f"<h3>Figure labels left other ({len(axis)}; compiled unmapped rows of field axis, P174)</h3>"
            + table(["pid", "element", "label", "unit", "action"], [[u["pid"], u["element"], u["label"], u["unit"], u["action"]] for u in axis])
            + "</body></html>\n")
    if HELD_RX:
        assert not HELD_RX.search(page), "a held-out paper in ontology.html"
    REPORT.write_text(page, encoding="utf-8")
    print(f"{REPORT}: {len(entries)} entries, {len(hist)} history rows, {len(pend)} pending, checks {sum(1 for c in checks if c[1])}/{len(checks)}")
    print("\n".join(draw(trees[0]) + tree_check))                              # P157: the tree and its check, printed next to each other


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    a = sub.add_parser("add")
    a.add_argument("pids", nargs="+")
    au = sub.add_parser("audit")                                                # P157d: A1-A3 of a round
    au.add_argument("round")
    for c in ("propose", "apply", "status", "report"):
        sub.add_parser(c)
    rn = sub.add_parser("run")                                                  # P172: papers 14+ end to end with gates
    rn.add_argument("papers", nargs="+")
    rn.add_argument("--yes", action="store_true")
    rn.add_argument("--plan", action="store_true")
    args = ap.parse_args(argv)
    try:
        out = {"init": cmd_init, "add": lambda: cmd_add(args.pids), "propose": cmd_propose, "apply": cmd_apply, "status": cmd_status, "report": report_page,
               "audit": lambda: cmd_audit(args.round), "run": lambda: cmd_run(args.papers, yes=args.yes, plan_only=args.plan)}[args.cmd]()
    except Stop as e:
        print(f"STOPPED: {e}")
        return 1
    return 1 if args.cmd in ("apply", "audit") and out else 0                  # P157d: a failed acceptance is an exit code too


if __name__ == "__main__":
    sys.exit(main())
