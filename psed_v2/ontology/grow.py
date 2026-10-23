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
    """A paper's compiled unmapped rows as (label, kind, unit, element, quote): the label as printed, or for a unit row without one the unit
    itself (kind unit); the quote is the candidate's definition_quote, else the label."""
    out = []
    for r in rd(COMPILED / f"{pid}.unmapped.csv"):
        cand = json.loads(r["candidate"]) if r["candidate"].startswith("{") else {}
        label, kind = r["label_as_printed"], ""
        if not label and r["field"] == "unit":
            label, kind = r["unit"], "unit"
        if not norm(label):
            continue
        quote = " ".join((cand.get("definition_quote") or label).split())
        out.append(dict(label=label, kind=kind, field=r["field"], unit=r["unit"], element=r["element"], quote=quote, definition=" ".join((cand.get("definition_quote") or "").split())))
    return out


def printed_labels(row):
    """The printed labels behind a pending row: the compiled unmapped labels of its papers whose snake case is its id (a pilot row: its id)."""
    labs = [u["label"] for pid in filter(None, row["pids"].split(";")) for u in unmapped_rows(pid) if snake(u["label"]) == row["id"]]
    return list(dict.fromkeys(labs)) or [row["id"].replace("_", " ")]


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


def never_labels():
    return {norm(r["label"]) for r in X.never_rows()}


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
    r = current(("open",))
    if not r:
        raise Stop("no open round (grow.py add first)")
    n, pids = int(r["round"]), r["pids"].split(";")
    entries = [e for e in onto()["entries"] if not e.get("replaced_by")]
    rows = rd(PENDING)
    for x in rows:
        assert list(x) == X.PENDING_COLUMNS, "pending.csv columns differ from export.PENDING_COLUMNS"
    by_id = {x["id"]: x for x in rows}
    never, dois = never_labels(), doi_of()
    groups, dropped = defaultdict(list), []
    for pid in pids:
        for u in unmapped_rows(pid):
            if norm(u["label"]) in never:
                dropped.append((pid, u["label"]))
                continue
            groups[snake(u["label"])].append((pid, u))
    conds = {pid: run_conditions(pid) for pid in pids}
    new, touched = [], []
    for cid, members in sorted(groups.items()):
        old = by_id.get(cid)
        if old and old["decision"]:
            continue                                                            # a decided row stays as it is
        ev = {}
        for item in (old["evidence"].split(" || ") if old and old["evidence"] else []):
            ev.setdefault(item.split(":", 1)[0], item)
        for pid, u in members:
            ev.setdefault(pid, f"{pid}:{u['element']} — {u['quote']}")
        cpids = sorted(ev)
        labels = list(dict.fromkeys(u["label"] for _, u in members))
        units = Counter(u["unit"] for _, u in members if u["unit"])
        kinds = {u["kind"] for _, u in members}
        kind = "unit" if kinds == {"unit"} else "quantity" if units or any(re.search(r"\d", u["label"] + u["quote"]) for _, u in members) \
            else ("quantity" if any(u["field"] == "quantity" for _, u in members) else "unit")
        nid, ndef, score = nearest(labels[0], entries)
        hint = "a" if len(cpids) >= 2 else "c" if any(norm(labels[0]) in conds.get(p, set()) for p in cpids) else "none"
        row = dict(id=cid, kind=old["kind"] if old else kind, proposed_definition=(old or {}).get("proposed_definition") or next((u["definition"] for _, u in members if u["definition"]), ""),
                   unit=(old or {}).get("unit") or (units.most_common(1)[0][0] if units else ""), n_papers=str(len(cpids)), pids=";".join(cpids),
                   dois=";".join(dois.get(p, "") for p in cpids), evidence=" || ".join(ev[p] for p in cpids), nearest_id=nid, nearest_definition=shown(ndef),
                   rule_hint=hint, first_round=(old or {}).get("first_round") or str(n), decision="", alias_target="", never_category="", decision_note=(old or {}).get("decision_note", ""))
        if old:
            old.update(row)
            touched.append(cid)
        else:
            new.append(row)
    rows += new
    write(PENDING, X.PENDING_COLUMNS, rows)
    decide_page(rows, n)
    set_round(n, status="proposed", n_candidates=len(new) + len(touched))
    print(f"round {n}: {len(new) + len(touched)} candidates ({len(new)} new, {len(touched)} merged with earlier undecided rows; {len(dropped)} rows matched never.csv)")
    print(f"pending.csv: {len(rows)} rows; decide in {DECIDE}")


# ---------------------------------------------------------------- decide.html
DECIDE_SCRIPT = r"""
const D=JSON.parse(document.getElementById('data').textContent);
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
    return [f"<b>{esc(row['id'])}</b><br><span class='lab'>printed: {esc('; '.join(labels))}</span>", esc(row["kind"]),
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
    for i, r in enumerate(rows):
        if r["decision"]:
            continue
        cells = candidate_cells(r, by_id)
        ctl = (f"<div class='ctl'>" + "".join(f"<label><input type='radio' name='d{i}' value='{v}'> {v}</label>" for v in ("accept", "alias", "reject", "never"))
               + f"<div>alias to: <input class='filter' placeholder='type to filter'><select class='alias'>{opt_ids}</select></div>"
               + f"<div>never category: <select class='never'>{opt_cats}</select></div><textarea placeholder='note'>{html.escape(r['decision_note'])}</textarea></div>")
        body.append(f"<tr id='r{i}'>" + "".join(f"<td>{c}</td>" for c in cells) + f"<td>{ctl}</td></tr>")
    done = [r for r in rows if r["decision"]]
    done_html = "".join("<tr>" + "".join(f"<td>{html.escape(r[k])}</td>" for k in ("id", "kind", "decision", "alias_target", "never_category", "decision_note", "first_round")) + "</tr>" for r in done)
    data = json.dumps(dict(cols=X.PENDING_COLUMNS, rows=rows, lines=lines, header=header), ensure_ascii=False).replace("</", "<\\/")
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>decide round {n}</title><style>{STYLE}"
            ".ctl label{display:block}.ctl select,.ctl input.filter{max-width:16em}.ctl textarea{width:16em;height:3em}.lab{color:#555;font-size:12px}</style></head><body>"
            f"<h1>Round {n}: decide the candidates</h1><p>{len(body)} candidates without a decision. Choose accept / alias / reject / never per row, then "
            "<button id='dl'>download pending.csv</button> and save it over psed_v2/ontology/pending.csv; then run <code>python3 psed_v2/ontology/grow.py apply</code>. "
            "Rows left without a choice stay pending.</p>"
            f"<table><tr>{''.join(f'<th>{h}</th>' for h in CAND_HEAD)}<th>decision</th></tr>{''.join(body)}</table>"
            f"<h2>Decided earlier (read-only)</h2><table><tr><th>id</th><th>kind</th><th>decision</th><th>alias target</th><th>never category</th><th>note</th><th>first round</th></tr>{done_html}</table>"
            f"<script type='application/json' id='data'>{data}</script><script>{DECIDE_SCRIPT}</script></body></html>\n")
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
        elif x["decision"] == "alias":
            text = add_alias(text, x["alias_target"], labels)
        elif x["decision"] == "never":
            nev += [dict(label=lab, category=x["never_category"], paper=x["pids"], source=f"round {n}") for lab in labels]
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
    nodes, children, _ = X.hierarchy_tree(o)
    members = defaultdict(list)
    for e in o["entries"]:
        if e.get("category"):
            members[e["category"]].append(e["id"])

    def render(pid):
        items = ""
        for c in children.get(pid, []):
            n = nodes[c]
            items += (f"<li><b>{esc(c)}</b>: {esc(n['definition'])} <i>[{esc(n.get('citation', ''))}]</i>"
                      + (f"<br>entries: {esc(', '.join(members[c]))}" if members[c] else "") + render(c) + "</li>")
        return f"<ul>{items}</ul>" if items else ""
    return render(None)


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
    kinds = Counter(e["type"] for e in entries)
    summary = [["ontology.yaml sha256", sha(ONTO)], ["ontology hash (export.ontology_hash: this file without its header line, then units.yaml)", X.ontology_hash()],
               ["entries", len(entries)]] + [[f"entries of kind {k}", kinds[k]] for k in ("quantity", "categorical", "species", "structure", "mechanism", "method", "model")] \
        + [["units (units.yaml spellings)", sum(1 + len(u["variants"]) for u in yaml.safe_load((HERE / "units.yaml").read_text(encoding="utf-8"))["units"])],
           ["qualifier keys", len(o["qualifiers"])], ["rounds", len(rs)], ["history rows", len(hist)], ["pending rows", len(pend)],
           ["pending undecided", sum(1 for x in pend if not x["decision"])], ["never labels", len(nev)], ["unmapped (figure import)", len(unm)],
           ["checks passed", f"{sum(1 for c in checks if c[1])} of {len(checks)}"], ["text fields withheld on this page (they name a held-out paper)", "{withheld}"]]
    check_html = "".join(f"<tr class='{'pass' if c[1] else 'fail'}'><td>{esc(c[0])}</td><td>{'pass' if c[1] else 'FAIL'}</td><td>{esc(c[2])}</td>"
                         f"<td>{'<ul>' + ''.join(f'<li>{esc(b)}</li>' for b in c[3]) + '</ul>' if c[3] else '—'}</td></tr>" for c in checks)
    ent_html = ""
    for k in ("quantity", "categorical", "species", "structure", "mechanism", "method", "model"):
        rows = [[e["id"], e.get("name", ""), e.get("definition", ""), e.get("unit", ""), e.get("origin", ""), ", ".join(src[e["id"]]["rounds"]),
                 "; ".join(src[e["id"]]["pids"]), "; ".join(src[e["id"]]["dois"]), "; ".join(x for x in map(str, e.get("evidence") or []) if not HELD_RX.search(x)),
                 ("replaced by " + (", ".join(e["replaced_by"]) if isinstance(e["replaced_by"], list) else e["replaced_by"])) if e.get("replaced_by") else ""] for e in entries if e["type"] == k]
        ent_html += f"<h3>{esc(k)} ({len(rows)})</h3>" + table(["id", "name", "definition", "unit", "origin", "source round", "source pids", "DOIs", "evidence (held-out removed)", "replaced"], rows)
    cand = [candidate_cells(x, by_id) + [esc(x["decision"]), esc(x["alias_target"]), esc(x["never_category"]), esc(x["decision_note"]), esc(x["first_round"])] for x in pend]
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>ontology</title><style>{STYLE}</style></head><body><h1>PSED v2 ontology</h1>"
            f"<p>Written by psed_v2/ontology/grow.py (report / apply) from ontology.yaml, units.yaml, history.csv, rounds.csv, pending.csv, never.csv and "
            f"unmapped.csv. Held-out papers are never shown.</p>"
            f"<h2>1. Kinds</h2><pre>{esc(chr(10).join(X.kinds_lines(o)))}</pre>"
            f"<h2>2. Summary</h2>{table(['item', 'value'], summary)}"
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
            + f"<h2>13. Never ({len(nev)})</h2>{table(NEVER_COLS, [[x[c] for c in NEVER_COLS] for x in nev])}"
            f"<h2>14. Unmapped (figure import, {len(unm)})</h2>{table(['paper', 'figure', 'panel', 'field', 'raw', 'reason'], [[x[c] for c in ('paper', 'figure', 'panel', 'field', 'raw', 'reason')] for x in unm if not HELD_RX.search(x['paper'])])}"
            "</body></html>\n")
    page = page.replace(esc("{withheld}"), str(page.count(WITHHELD)), 1)
    assert not HELD_RX.search(page), "a held-out paper in ontology.html"
    REPORT.write_text(page, encoding="utf-8")
    print(f"{REPORT}: {len(entries)} entries, {len(hist)} history rows, {len(pend)} pending, checks {sum(1 for c in checks if c[1])}/{len(checks)}")


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
