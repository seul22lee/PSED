#!/usr/bin/env python3
"""P155: the ontology growth pipeline, one round at a time. No provider call, ever: a paper enters only when pass 0 and pass 1 ran.

    python3 psed_v2/ontology/grow.py init                  # round 0 (once): history rows reconstructed for every entry, rounds.csv row 0
    python3 psed_v2/ontology/grow.py add <pid> [<pid> ...] # open a round on extracted papers
    python3 psed_v2/ontology/grow.py propose               # their compiled unmapped lists -> candidates in pending.csv and decide.html
    python3 psed_v2/ontology/grow.py apply                 # the user's decisions -> ontology.yaml, never.csv, history.csv; export, check,
                                                           # recompile, score, ontology.html, one commit
    python3 psed_v2/ontology/grow.py status                # the open round, pending counts by decision, the last history rows
    python3 psed_v2/ontology/grow.py report                # ontology.html only

Files in ontology/: rounds.csv (one row per round), history.csv (append-only, one row per decision), pending.csv (export.PENDING_COLUMNS),
never.csv (the never-an-entry labels), decide.html (the decision form propose writes), ontology.html (the one report).

The user decides in decide.html, downloads pending.csv over ontology/pending.csv and runs apply. A candidate is a group of compiled
unmapped rows (kb/compiled/<pid>.unmapped.csv) with one normalized label (casefold, the trailing unit bracket stripped, whitespace
collapsed), across the round and the earlier undecided rows; its id is the label in snake case. The printed labels of a candidate are read
back from those rows (printed_labels); the paper text is never read. DOIs come from corpus/manifest.csv (ingest/final/<pid>/ holds no
metadata file). Held-out papers (kb/extract/common.py HELD_OUT) are refused and never shown. Imports nothing of the project but export.
P157b: never.csv is applied by kb/extract/compile.py (unmapped.csv column never, export.never_index); propose drops those rows and does no
never matching of its own; decide.html shows the candidates found in two or more papers first.
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
DECIDE, REPORT, UNMAPPED = HERE / "decide.html", HERE / "ontology.html", HERE / "unmapped.csv"
COMPILED, RECORDS, FINAL = V2 / "kb" / "compiled", V2 / "kb" / "records", V2 / "ingest" / "final"
ROUND_COLS = ["round", "opened", "applied", "pids", "dois", "status", "n_candidates", "n_accepted", "n_alias", "n_rejected", "n_never"]
HISTORY_COLS = ["date", "round", "action", "id", "kind", "target", "source_pids", "source_dois", "decided_by", "reason", "ontology_sha256_after"]
NEVER_COLS = ["label", "category", "paper", "source"]
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
HELD_RX = re.compile(r"\b(" + "|".join(re.escape(h) for h in sorted(HELD)) + r")\b")


def doi_of():
    return {r["paper_id"]: r["doi"] for r in rd(V2 / "corpus" / "manifest.csv")}


# ---------------------------------------------------------------- files
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
    candidate's definition_quote), quote (the definition, else the label, else the unit) and never (P157b: compile.py's never column,
    the never.csv category of the record's label)."""
    out = []
    for r in rd(COMPILED / f"{pid}.unmapped.csv"):
        cand = json.loads(r["candidate"]) if r["candidate"].startswith("{") else {}
        d = " ".join((cand.get("definition_quote") or "").split())
        out.append(dict(pid=pid, element=r["element"], field=r["field"], label=r["label_as_printed"].strip(), unit=r["unit"], symbol=(cand.get("symbol") or "").strip(),
                        definition=d, quote=d or r["label_as_printed"].strip() or r["unit"], never=r.get("never", "")))
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


SYMBOL_LAYOUT = next(k for k, d in X.P143_TABLE_LAYOUTS if "symbol table" in d)          # P143: not_units, 'a symbol table (symbol, meaning, value) or ...'
SYMBOL_ROLES = re.search(r"symbol table \(([^)]*)\)", dict(X.P143_TABLE_LAYOUTS)[SYMBOL_LAYOUT]).group(1).split(", ")   # ['symbol', 'meaning', 'value']: no unit column


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


def candidates(pids):
    """P156: the candidates of a set of papers from their compiled unmapped rows, and the log of how they were made.

    1. A row of a symbol-table layout (pass 0: P143 not_units, whose definition names the roles symbol, meaning, value; the record carries a
       symbol) groups by table row and symbol: the cell whose text is the symbol is the symbol column, the other cell (or, when its text is
       empty, the record's definition) is the meaning column, which gives the label, the id and the definition; the symbol becomes an alias.
       The layout has no unit column: the unit is the records'. A symbol with no meaning cell in its row stays its own candidate, noted.
    2. A row elsewhere in the same paper whose label is its symbol joins the one symbol-table row with that symbol; else a row whose label (a
       symbol's: its definition) has the words of one symbol-table meaning (words(): articles and 'of' dropped, order ignored) joins it.
    3. P157b: a row compile.py marked never (its never column) is dropped; a symbol-table group with a never row is dropped with the rows
       that joined it. grow.py does no never matching of its own.
    4. A row with no label, or a label that is only a unit spelling of units.yaml, is a value without a quantity, not a candidate (FIX 3).
    5. The rest group across the papers by the normalized label (snake case of norm()).
    Returns ({id: group}, log)."""
    spell = unit_spellings()
    log = dict(table_groups=[], symbol_merges=[], label_merges=[], ambiguous=[], never=[], values=[])
    tables, rest = defaultdict(list), []
    for pid in pids:
        layouts = pass0_tables(pid)
        rows = unmapped_rows(pid)
        own = {(u["element"], u["label"]): u["symbol"] for u in rows if u["field"] == "quantity" and u["symbol"]}
        for u in rows:
            if u["field"] == "unit" and not u["symbol"]:                       # a unit row follows the quantity row of its cell and label
                u["symbol"] = own.get((u["element"], u["label"]), "")
            m = re.match(r"^(tab\w*)\.(r\d+)c\d+$", u["element"])
            if m and layouts.get(m.group(1)) == SYMBOL_LAYOUT and u["symbol"]:
                tables[(pid, f"{m.group(1)}.{m.group(2)}", norm_symbol(u["symbol"]))].append(u)
            elif not u["label"] or (u["label"] in spell and not (u["symbol"] and norm_symbol(u["label"]) == norm_symbol(u["symbol"]))):
                log["values"].append(u)                                         # FIX 3: no label, or a unit spelling that is not the record's own symbol
            else:
                rest.append(u)
    groups, by_sym, by_cell = [], defaultdict(list), {}
    for (pid, row, sym), us in tables.items():
        symcell = [u for u in us if u["label"] and norm_symbol(u["label"]) == sym]
        meaning = next((u["label"] for u in us if u["label"] and norm_symbol(u["label"]) != sym), "") \
            or next((X.strip_trailing_units(u["definition"]) for u in us if u["definition"]), "")
        symbol = symcell[0]["label"] if symcell else us[0]["symbol"]
        g = dict(label=meaning or symbol, aliases=[symbol] if meaning else [], definition=meaning, members=list(us), pid=pid, row=row,
                 note="" if meaning else f"symbol with no meaning cell in table row {row}")
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
            log["label_merges"].append((u, same[0], text))
            continue
        groups.append(dict(label=u["label"], aliases=[], definition=u["definition"], members=[u], pid=u["pid"], row="", note=""))
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
        c = out.setdefault(cid, dict(id=cid, label=g["label"], aliases=[], definition="", members=[], notes=[]))
        c["aliases"] += [a for a in g["aliases"] if a not in c["aliases"] and a != c["label"]]
        c["definition"] = c["definition"] or g["definition"]
        c["members"] += g["members"]
        c["notes"] += [g["note"]] if g["note"] else []
    for c in out.values():
        units = Counter(u["unit"] for u in c["members"] if u["unit"])
        c["unit"] = units.most_common(1)[0][0] if units else ""
        c["kind"] = "quantity" if units or any(re.search(r"\d", u["label"] + u["quote"]) for u in c["members"]) or any(u["field"] == "quantity" for u in c["members"]) else "unit"
        ev = {}
        for u in c["members"]:
            ev.setdefault(u["pid"], f"{u['pid']}:{u['element']} — {u['quote']}" + (f" ({'; '.join(c['notes'])})" if c["notes"] else ""))
        c["evidence"] = ev
    return out, log


_CAND = {}


def candidates_of(pids):
    key = tuple(sorted(p for p in pids if p))
    if key not in _CAND:
        _CAND[key] = candidates(key)
    return _CAND[key]


def printed_labels(row):
    """The printed labels behind a pending row: its candidate's label, then its aliases (the symbols); a pilot row: its id."""
    c = candidates_of(row["pids"].split(";"))[0].get(row["id"]) if row["first_round"] not in ("", "0") else None
    return [c["label"]] + c["aliases"] if c else [row["id"].replace("_", " ")]


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
    cands, log = candidates_of(pids)
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
                   first_round=(old or {}).get("first_round") or str(n), decision="", alias_target="", never_category="", decision_note=(old or {}).get("decision_note", ""))
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
const COLS=D.cols, ROWS=D.rows, LINES=D.lines, F=['decision','alias_target','never_category','decision_note'];
function q(v){return /[",\n\r]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function state(i){const r=document.getElementById('r'+i);if(!r)return ROWS[i];
  const o=Object.assign({},ROWS[i]);const c=r.querySelector('input[type=radio]:checked');o.decision=c?c.value:'';
  o.alias_target=o.decision==='alias'?r.querySelector('select.alias').value:'';o.never_category=o.decision==='never'?r.querySelector('select.never').value:'';
  o.decision_note=r.querySelector('textarea').value;return o;}
function csvText(){let out=D.header;ROWS.forEach((row,i)=>{const s=state(i);
  out+=F.every(k=>s[k]===row[k])?LINES[i]:COLS.map(c=>q(s[c]??'')).join(',')+'\n';});return out;}
document.getElementById('dl').addEventListener('click',()=>{const b=new Blob([csvText()],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='pending.csv';document.body.appendChild(a);a.click();a.remove();});
document.querySelectorAll('input.filter').forEach(f=>f.addEventListener('input',()=>{const s=f.value.toLowerCase(),sel=f.nextElementSibling;
  let first=null;[...sel.options].forEach(o=>{const hit=!s||o.value.toLowerCase().includes(s);o.hidden=!hit;if(hit&&first===null)first=o;});if(first&&sel.selectedOptions[0]&&sel.selectedOptions[0].hidden)sel.value=first.value;}));
"""


def evidence_items(row):
    return [x for x in (row["evidence"] or "").split(" || ") if x and not HELD_RX.search(x)]


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
    body = []
    multi = lambda r: int(r["n_papers"] or 0) >= 2                                # noqa: E731  P157b: rows in two or more papers first, marked
    for i, r in sorted(((i, r) for i, r in enumerate(rows) if not r["decision"]), key=lambda x: (not multi(x[1]), x[0])):
        cells = candidate_cells(r, by_id)
        if multi(r):
            cells[0] = f"<span class='multi'>▲ in {esc(r['n_papers'])} papers</span><br>" + cells[0]
        ctl = (f"<div class='ctl'>" + "".join(f"<label><input type='radio' name='d{i}' value='{v}'> {v}</label>" for v in ("accept", "alias", "reject", "never"))
               + f"<div>alias to: <input class='filter' placeholder='type to filter'><select class='alias'>{opt_ids}</select></div>"
               + f"<div>never category: <select class='never'>{opt_cats}</select></div><textarea placeholder='note'>{html.escape(r['decision_note'])}</textarea></div>")
        body.append(f"<tr id='r{i}'{' class=multi' if multi(r) else ''}>" + "".join(f"<td>{c}</td>" for c in cells) + f"<td>{ctl}</td></tr>")
    done = [r for r in rows if r["decision"]]
    done_html = "".join("<tr>" + "".join(f"<td>{html.escape(r[k])}</td>" for k in ("id", "kind", "decision", "alias_target", "never_category", "decision_note", "first_round")) + "</tr>" for r in done)
    data = json.dumps(dict(cols=X.PENDING_COLUMNS, rows=rows, lines=lines, header=header), ensure_ascii=False).replace("</", "<\\/")
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>decide round {n}</title><style>{STYLE}"
            ".ctl label{display:block}.ctl select,.ctl input.filter{max-width:16em}.ctl textarea{width:16em;height:3em}.lab{color:#555;font-size:12px}"
            "tr.multi td:first-child{border-left:4px solid #b35900}.multi{color:#b35900;font-weight:bold}</style></head><body>"
            f"<h1>Round {n}: decide the candidates</h1><p>{len(body)} candidates without a decision ({sum(1 for r in rows if not r['decision'] and multi(r))} found in two "
            "or more papers come first, marked ▲). Choose accept / alias / reject / never per row, then "
            "<button id='dl'>download pending.csv</button> and save it over psed_v2/ontology/pending.csv; then run <code>python3 psed_v2/ontology/grow.py apply</code>. "
            "Rows left without a choice stay pending.</p>"
            f"<table><tr>{''.join(f'<th>{h}</th>' for h in CAND_HEAD)}<th>decision</th></tr>{''.join(body)}</table>"
            f"<h2>Decided earlier (read-only)</h2><table><tr><th>id</th><th>kind</th><th>decision</th><th>alias target</th><th>never category</th><th>note</th><th>first round</th></tr>{done_html}</table>"
            f"<script>const D={data};{DECIDE_SCRIPT}</script></body></html>\n")                       # the one script: the rows, then the form logic
    DECIDE.write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- apply (merge_pending.py's writing of entries)
ORDER = ["id", "type", "label", "name", "origin", "role", "category", "definition", "dimension", "unit", "kind", "formula", "class", "model_type",
         "parameters", "aliases", "source_pids", "evidence"]


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
    add = [a for a in labels if a.casefold() not in {h.casefold() for h in have}]
    if not add:
        return text
    line = "    aliases: " + yaml.safe_dump(have + add, default_flow_style=True, allow_unicode=True, width=100000).strip()
    blk = blk[:m.start()] + line + blk[m.end():] if m else blk.replace("\n", "\n" + line + "\n", 1)
    return text[:s] + blk + text[e:]


def cmd_apply():
    r = current(("proposed",))
    if not r:
        raise Stop("no proposed round")
    n = int(r["round"])
    o = onto()
    have = {e["id"]: e for e in o["entries"]}
    rows = rd(PENDING)
    decided = [x for x in rows if x["decision"]]
    stops = []
    for x in decided:
        if x["decision"] not in X.DECISIONS:
            stops.append(f"{x['id']}: decision {x['decision']!r}")
        if x["decision"] == "accept" and x["id"] in have and have[x["id"]].get("definition") != x["proposed_definition"]:
            stops.append(f"{x['id']}: accept, but ontology.yaml has it with another definition: {have[x['id']].get('definition')!r}")
        if x["decision"] == "accept" and x["kind"] == "unit":
            stops.append(f"{x['id']}: accept of a unit; units go into units.yaml by hand, not into ontology.yaml")
        if x["decision"] == "alias" and x["alias_target"] not in have:
            stops.append(f"{x['id']}: alias target {x['alias_target']!r} is not an entry")
        if x["decision"] == "never" and not x["never_category"].strip():
            stops.append(f"{x['id']}: never without a never_category")
    if stops:
        raise Stop("nothing written:\n  " + "\n  ".join(stops))
    backup = {p: p.read_bytes() for p in (ONTO, PENDING, NEVER, HISTORY, ROUNDS) if p.exists()}
    text = ONTO.read_text(encoding="utf-8")
    new, hist, nev = [], [], X.never_rows()
    for x in decided:
        labels = printed_labels(x)
        if x["decision"] == "accept" and x["id"] not in have:
            e = X.pending_entry(x, labels)
            e.update(origin=f"round {n}", source_pids=[p for p in x["pids"].split(";") if p], evidence=evidence_items(x))
            new.append({k: e[k] for k in ORDER if k in e and e[k] not in ("", [], None)})
        elif x["decision"] == "alias":                                         # P156: the label only; a symbol (an alias of the candidate) is
            text = add_alias(text, x["alias_target"], labels[:1])              # local to its paper and goes into an entry only on accept
        elif x["decision"] == "never":
            nev.append(dict(label=labels[0], category=x["never_category"], paper=x["pids"], source=f"round {n}"))
    if new:
        mark = "\nfamilies:"
        assert text.count(mark) == 1
        head, tail = text.split(mark)
        text = head.rstrip("\n") + f"\n\n  # ---------------------------------------------------------------- grow.py round {n}: accepted\n" \
            + "".join(block(e) for e in new).rstrip("\n") + "\n" + mark + tail
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
    for pid in extracted:                                                       # 0 calls: compile reads the stored records
        subprocess.run([py, str(V2 / "kb" / "extract" / "compile.py"), pid], cwd=ROOT, check=True)
    gold = [pid for pid in extracted if (V2 / "kb" / "pilot" / f"{pid}.facts.csv").exists()]
    if gold:
        subprocess.run([py, str(V2 / "kb" / "extract" / "score.py"), f"R{n}", *gold], cwd=ROOT, check=True)
    after = sha(ONTO)
    dois = doi_of()
    for x in decided:
        pids = [p for p in x["pids"].split(";") if p]
        hist.append(dict(date=today(), round=n, action={"accept": "add"}.get(x["decision"], x["decision"]), id=x["id"], kind=x["kind"],
                         target=x["alias_target"] if x["decision"] == "alias" else x["never_category"] if x["decision"] == "never" else "",
                         source_pids=";".join(pids), source_dois=";".join(dois.get(p, "") for p in pids), decided_by="user", reason=x["decision_note"],
                         ontology_sha256_after=after))
    append(HISTORY, HISTORY_COLS, hist)
    c = Counter(x["decision"] for x in decided)
    set_round(n, status="applied", applied=today(), n_accepted=c["accept"], n_alias=c["alias"], n_rejected=c["reject"], n_never=c["never"])
    report_page()
    files = [ONTO, PENDING, NEVER, HISTORY, ROUNDS, REPORT, V2 / "kb" / "pilot" / "vocab.py", V2 / "kb" / "schema", COMPILED, V2 / "kb" / "reports"]
    subprocess.run(["git", "add", "--", *map(str, files)], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"grow round {n} applied: {c['accept']} accepted, {c['alias']} aliases, {c['reject']} rejected, "
                    f"{c['never']} never; recompiled {len(extracted)} papers, scored {len(gold)} (0 calls)"], cwd=ROOT, check=True)
    print(f"round {n} applied: {dict(c)}; {len(rows) - len(decided)} rows stay pending; ontology.yaml sha256 {after[:12]}; committed")


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
                        source_dois=";".join(dois.get(p, "") for p in pids), decided_by="pilot", reason=HELD_RX.sub("held-out", reason), ontology_sha256_after=blob_sha))
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


WITHHELD = "[withheld: names a held-out paper]"


def shown(x):
    """A text as the pages show it: withheld whole when it names a held-out paper (CLAUDE.md: never shown), never cut."""
    s = "" if x is None else str(x)
    return WITHHELD if HELD_RX.search(s) else s


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
    return [[f, "; ".join(f"{e['id']} ({e.get('unit', '')}; {', '.join(e.get('qualifiers', []))})" for e in ms),
             " | ".join(f"{e['id']}: {e['definition'].split('.')[0]}" for e in ms)] for f, ms in sorted(fam.items())]


def report_page():
    o = onto()
    entries = o["entries"]
    by_id = {e["id"]: e for e in entries}
    hist, rs, pend, nev, unm = rd(HISTORY), rounds(), rd(PENDING), X.never_rows(), rd(UNMAPPED)
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
               ["rounds", len(rs)], ["unmapped (figure import)", len(unm)],
               ["checks passed", f"{sum(1 for c in checks if c[1])} of {len(checks)}"], ["text fields withheld on this page (they name a held-out paper)", "{withheld}"]]
    check_html = "".join(f"<tr class='{'pass' if c[1] else 'fail'}'><td>{esc(c[0])}</td><td>{'pass' if c[1] else 'FAIL'}</td><td>{esc(c[2])}</td>"
                         f"<td>{'<ul>' + ''.join(f'<li>{esc(b)}</li>' for b in c[3]) + '</ul>' if c[3] else '—'}</td></tr>" for c in checks)
    ent_html = ""
    for k in ("quantity", "categorical", "species", "structure", "mechanism", "method", "model"):
        rows = [[e["id"], e.get("name", ""), e.get("definition", ""), e.get("unit", ""), e.get("origin", ""), ", ".join(src[e["id"]]["rounds"]),
                 "; ".join(src[e["id"]]["pids"]), "; ".join(src[e["id"]]["dois"]), "; ".join(x for x in map(str, e.get("evidence") or []) if not HELD_RX.search(x)),
                 ("replaced by " + (", ".join(e["replaced_by"]) if isinstance(e["replaced_by"], list) else e["replaced_by"])) if e.get("replaced_by") else ""] for e in entries if e["type"] == k]
        ent_html += f"<h3>{esc(k)} ({len(rows)})</h3>" + table(["id", "name", "definition", "unit", "origin", "source round", "source pids", "DOIs", "evidence (held-out removed)", "replaced"], rows)
    sup = X.never_index([e for e in entries if not e.get("replaced_by")])[1]
    round_pids = [p for r in rs if r["round"] != "0" for p in r["pids"].split(";") if p]
    values = candidates_of(round_pids)[1]["values"] if round_pids else []
    cand = [candidate_cells(x, by_id) + [esc(x["decision"]), esc(x["alias_target"]), esc(x["never_category"]), esc(x["decision_note"]), esc(x["first_round"])] for x in pend]
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>ontology</title><style>{STYLE}</style></head><body><h1>PSED v2 ontology</h1>"
            f"<p>Written by psed_v2/ontology/grow.py (report / apply) from ontology.yaml, units.yaml, history.csv, rounds.csv, pending.csv, never.csv and "
            f"unmapped.csv. Held-out papers are never shown.</p>"
            f"<h2>1. Kinds</h2><pre>{esc(chr(10).join(X.kinds_lines(o)))}</pre>"
            f"<h2>2. Summary</h2><pre>{esc(chr(10).join(draw(trees[0])))}</pre>"
            f"<pre class='{'pass' if tree_check[0].startswith('sum check: pass') and tree_check[1] == 'unplaced: none' else 'fail'}'>{esc(chr(10).join(tree_check))}</pre>"
            f"<pre>{esc(chr(10).join(ln for t in trees[1:] for ln in draw(t)))}</pre>{table(['item', 'value'], summary)}"
            f"<h2>3. Checks (export.py --check)</h2><table><tr><th>check</th><th>result</th><th>detail</th><th>rows</th></tr>{check_html}</table>"
            f"<h2>4. Entries by kind</h2>{ent_html}"
            f"<h2>5. Values</h2>{table(['categorical', 'values_from', 'current values', 'value aliases'], values_rows(o))}"
            f"<h2>6. Families</h2>{table(['family', 'members', 'what they answer'], family_rows(o))}"
            f"<h2>7. Structure classes</h2>{structure_classes_html(o)}"
            f"<h2>8. Hierarchy</h2>{hierarchy_html(o)}"
            f"<h2>9. Units</h2>{table(['dimension', 'canonical', 'accepted'], [[d, u['canonical'], ', '.join(u['accepted'])] for d, u in o['units'].items()])}"
            f"<h2>10. History ({len(hist)} rows)</h2>{table(HISTORY_COLS, [[h[c] for c in HISTORY_COLS] for h in hist])}"
            f"<h2>11. Rounds</h2>{table(ROUND_COLS, [[r[c] for c in ROUND_COLS] for r in rs])}"
            f"<h2>12. Pending ({len(pend)} rows; read-only, as decide.html shows them)</h2>"
            + table(CAND_HEAD + ["decision", "alias target", "never category", "note", "first round"], cand, raw=True)
            + f"<h2>13. Never ({len(nev)}; a part that names a live entry is superseded and suppresses nothing)</h2>"
            + table(NEVER_COLS + ["superseded by"], [[x[c] for c in NEVER_COLS] + ["; ".join(f"{p} → superseded by {e}" for lab, p, e in sup if lab == x["label"])] for x in nev])
            + f"<h2>14. Unmapped</h2><h3>Values without a quantity (compiled unmapped rows of the rounds' papers with no label or only a unit; not candidates)</h3>"
            + table(["pid", "element", "raw text", "unit"], [[u["pid"], u["element"], u["quote"], u["unit"]] for u in values])
            + f"<h3>Figure import ({len(unm)})</h3>{table(['paper', 'figure', 'panel', 'field', 'raw', 'reason'], [[x[c] for c in ('paper', 'figure', 'panel', 'field', 'raw', 'reason')] for x in unm if not HELD_RX.search(x['paper'])])}"
            "</body></html>\n")
    page = page.replace(esc("{withheld}"), str(page.count(WITHHELD)), 1)
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
    for c in ("propose", "apply", "status", "report"):
        sub.add_parser(c)
    args = ap.parse_args(argv)
    try:
        {"init": cmd_init, "add": lambda: cmd_add(args.pids), "propose": cmd_propose, "apply": cmd_apply, "status": cmd_status, "report": report_page}[args.cmd]()
    except Stop as e:
        print(f"STOPPED: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
