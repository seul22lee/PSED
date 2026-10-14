#!/usr/bin/env python3
"""Stage 1: elements.csv per pilot paper (psed_v2/facts/<paper_id>/elements.csv).

    python3 psed_v2/facts/elements.py [--text DIR]

Starts from the v2 inventory (schema_pilot/v2/inventory.py, same ids) and adds what it lacked:
  - one panel element per lettered panel seen on the figure crop (PANELS below; the inventory took panels from
    cases/figures.csv, which merged some and left others out); the old inventory id is kept in inventory_id;
  - the unnumbered tables (a nomenclature list in yim20) as tabu<k>.r<i>c<j>.
Columns: element_id, kind, section, locator, n_numbers, n_chars, inventory_id, crop (figure image under ingest/final/<paper_id>/).
n_numbers of a panel is blank: numbers drawn on an image are not counted from text; they are listed as facts.
Not elements: journal logos and cover pictures on the first pages, and the reaction images of gre23 that repeat eq3-eq5.
With --text DIR, writes DIR/<paper_id>.jsonl with each element's text (for reading; kept out of git).
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "schema_pilot/v2"))
import inventory  # noqa: E402

PAPERS = inventory.PAPERS
# lettered panels per figure, read from the crops ("" = the figure is one panel)
PANELS = {
    "10.1039_d0cp03358h": {"1": "abc", "2": "abcd", "3": "ab", "4": "abc", "5": "ab", "6": "", "7": "", "8": "ab",
                           "9": "abcdef", "10": "abcdef", "11": "ab"},
    "10.1021_acs.chemmater.2c01154": {"1": "abcd", "2": "", "3": "ab", "4": "", "5": "ab", "6": "ab", "7": "ab", "8": "",
                                      "9": "ab"},
    "10.1116_6.0003182": {"1": "ab", "2": "abcd", "3": "abc", "4": "abcd", "5": "", "6": "abcdef"},
}
FIELDS = ["element_id", "kind", "section", "locator", "n_numbers", "n_chars", "inventory_id", "crop"]


def build(pid):
    rows, texts = inventory.build(pid)
    st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
    crops = {str(c["number"]): (c.get("images") or [""])[0] for c in st["captions"] if c["kind"] == "figure" and c.get("number")}
    out, otext, done = [], {}, set()
    for r in rows:
        eid = r["element_id"]
        if r["kind"] != "panel":
            r = dict(r, inventory_id=eid, crop=crops.get(eid[3:-4], "") if eid.endswith(".cap") and eid.startswith("fig") else "")
            out.append(r); otext[eid] = texts[eid]
            if eid.startswith("fig") and eid.endswith(".cap"):                 # panels follow their caption
                n = eid[3:-4]
                old = [x["element_id"] for x in rows if x["kind"] == "panel" and re.fullmatch(rf"fig{n}[a-z]*", x["element_id"])]
                for p in PANELS[pid][n] or [""]:
                    pe = f"fig{n}{p}"
                    suf = [o[len(f"fig{n}"):] for o in old]                 # "", "b", or "ac" (= panels a to c)
                    inv = ";".join(o for o, s in zip(old, suf) if s == p or s == "" or (len(s) == 2 and s[0] <= p <= s[1]))
                    out.append(dict(element_id=pe, kind="panel", section="figures", locator=f"Fig. {n}{p}", n_numbers="",
                                    n_chars="", inventory_id=inv, crop=crops.get(n, "")))
                    otext[pe] = f"[panel {p or '(whole)'} of Fig. {n}; see the crop] " + texts[eid]
                done.add(n)
    k = 0
    for c in st["captions"]:
        if c["kind"] == "table" and not c.get("number") and c.get("table"):
            k += 1
            lines = [l for l in c["table"].splitlines() if l.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|$", l.strip())]
            for i, l in enumerate(lines):
                for j, cell in enumerate([x.strip() for x in l.strip().strip("|").split("|")]):
                    if cell:
                        eid = f"tabu{k}.r{i}c{j}"
                        out.append(dict(element_id=eid, kind="table_cell", section=f"tabu{k}",
                                        locator=f"unnumbered table {k} (page {c.get('page')}), row {i}, column {j}",
                                        n_numbers=len(inventory.numbers(cell)), n_chars=len(cell), inventory_id="", crop=""))
                        otext[eid] = cell
    missing = set(PANELS[pid]) - done
    assert not missing, (pid, missing)
    return out, otext


def load(pid):
    return list(csv.DictReader((HERE / pid / "elements.csv").open(encoding="utf-8")))


if __name__ == "__main__":
    tdir = Path(sys.argv[sys.argv.index("--text") + 1]) if "--text" in sys.argv else None
    import collections
    for pid in PAPERS:
        rows, texts = build(pid)
        (HERE / pid).mkdir(exist_ok=True)
        with (HERE / pid / "elements.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
        if tdir:
            tdir.mkdir(parents=True, exist_ok=True)
            with (tdir / f"{pid}.jsonl").open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps({**r, "text": texts[r["element_id"]]}, ensure_ascii=False) + "\n")
        print(pid, len(rows), dict(collections.Counter(r["kind"] for r in rows)))
