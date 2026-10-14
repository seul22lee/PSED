#!/usr/bin/env python3
"""Element inventory of each pilot paper from ingest/final/<paper_id>/ (document.md, structure.json) and cases/figures.csv.

    python3 psed_v2/schema_pilot/v2/inventory.py [--text DIR]

Writes v2/<paper_id>/inventory.csv: element_id, kind (abstract | heading | paragraph | caption | panel | table_cell | equation),
section, locator, n_numbers, n_chars. No paper text goes into the tracked file. With --text DIR, also writes DIR/<paper_id>.jsonl
with the text of every element (for reading; kept out of git).
Ids: abs.g<n> (two abstract sentences per group), s<sec>.h (a heading), s<sec>.p<n> (paragraph n of section sec, in reading
order; s0 = front matter), fig<n>.cap and fig<n><panel> (panels from cases/figures.csv, or fig<n> when it has none),
tab<n>.cap and tab<n>.r<i>c<j> (row 0 = header), eq<n> (display equations in reading order); a paragraph that starts
with a figure reference but is not a caption is s<sec>.x<n> (added after the first extraction; existing ids are unchanged).
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent.parent
PAPERS = {"10.1039_d0cp03358h": "yim20", "10.1021_acs.chemmater.2c01154": "mat22", "10.1116_6.0003182": "gre23"}
NUM = re.compile(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?(?:\s*[×x]\s*10\^?\{?[-−]?\d+\}?)?(?:[eE][-−+]?\d+)?")


def numbers(t):
    t = re.sub(r"<sup>.*?</sup>|\[\d+(?:[,–-]\d+)*\]|\(\s*ref\.?.*?\)", " ", t)          # citation markers are not data
    t = re.sub(r"(Fig(ure)?s?\.?|Table|Eq(n)?s?\.?|eqn|Section|Sec\.)\s*\(?\d+[a-z]?", " ", t, flags=re.I)
    return NUM.findall(t)


def build(pid):
    st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
    doc = (V2 / f"ingest/final/{pid}/document.md").read_text(encoding="utf-8")
    m = re.search(r"\n\s*(?:#+\s*)?(?:■\s*)?\**\s*(Notes and references|References|REFERENCES)\b", doc)
    body = doc[:m.start()] if m else doc
    rows, texts = [], {}

    def add(eid, kind, sec, loc, text):
        rows.append(dict(element_id=eid, kind=kind, section=sec, locator=loc, n_numbers=len(numbers(text)) if kind not in ("heading", "caption") else len(numbers(text)), n_chars=len(text)))
        texts[eid] = text
    ab = re.split(r"(?<=[.!?])\s+(?=[A-Z])", st.get("abstract") or "")
    for i in range(0, len(ab), 2):
        add(f"abs.g{i // 2 + 1}", "abstract", "abstract", f"abstract, sentences {i + 1}-{min(i + 2, len(ab))}", " ".join(ab[i:i + 2]))
    sec, para, eq, extra = 0, 0, 0, {}
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if not b or b.startswith("![") or b.startswith("|"):
            continue
        if b.startswith("$$") or (b.startswith("$") and b.endswith("$") and "$$" in b):
            eq += 1
            num = re.search(r"\((\d+)\)\s*\$*\s*$", b) or re.search(r"\\tag\{(\d+)\}", b)
            add(f"eq{eq}", "equation", f"s{sec}", f"display equation {eq}" + (f", printed ({num.group(1)})" if num else ""), b)
            continue
        if re.match(r"^\**\s*(Fig\.?|Figure|Table)\s*[\dIVX]+", b):
            norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())[:60]
            if any(norm(b).startswith(norm(c["caption"])[:30]) or norm(c["caption"]).startswith(norm(b)[:30]) for c in st["captions"] if c.get("caption")):
                continue                                                   # a caption: it comes from structure.json
            extra[sec] = extra.get(sec, 0) + 1                             # a paragraph that starts with "Fig. n": own id, no renumbering
            add(f"s{sec}.x{extra[sec]}", "paragraph", f"s{sec}", f"section {sec}, paragraph starting with a figure reference", b)
            continue
        if b.startswith("#"):
            sec += 1; para = 0
            add(f"s{sec}.h", "heading", f"s{sec}", f"section {sec} heading", b.lstrip("# "))
            continue
        for part in re.split(r"\n(?=\$\$)", b):                            # an equation glued to its paragraph
            if part.strip().startswith("$$"):
                eq += 1
                num = re.search(r"\((\d+)\)\s*\$*\s*$", part)
                add(f"eq{eq}", "equation", f"s{sec}", f"display equation {eq}" + (f", printed ({num.group(1)})" if num else ""), part)
            else:
                para += 1
                add(f"s{sec}.p{para}", "paragraph", f"s{sec}", f"section {sec}, paragraph {para}", part)
    panels = {}
    for r in csv.DictReader((V2 / "cases/figures.csv").open(encoding="utf-8")):
        if r["paper_id"] == pid and not r["figure"].startswith("Table"):
            panels.setdefault(r["figure"], [])
            p = re.sub(r"\W", "", r["panel"])
            if p and p not in panels[r["figure"]]:
                panels[r["figure"]].append(p)
    for c in st["captions"]:
        n = str(c.get("number") or "")
        if not n:
            continue
        if c["kind"] == "figure":
            add(f"fig{n}.cap", "caption", "figures", f"Fig. {n} caption", c["caption"])
            for p in panels.get(n) or [""]:
                add(f"fig{n}{p}", "panel", "figures", f"Fig. {n}{p}", c["caption"])
        elif c["kind"] == "table":
            add(f"tab{n}.cap", "caption", "tables", f"Table {n} caption", c["caption"])
            lines = [l for l in (c.get("table") or "").splitlines() if l.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|$", l.strip())]
            for i, l in enumerate(lines):
                for j, cell in enumerate([x.strip() for x in l.strip().strip("|").split("|")]):
                    if cell:
                        add(f"tab{n}.r{i}c{j}", "table_cell", f"tab{n}", f"Table {n}, row {i}, column {j}", cell)
    return rows, texts


if __name__ == "__main__":
    tdir = Path(sys.argv[sys.argv.index("--text") + 1]) if "--text" in sys.argv else None
    for pid in PAPERS:
        rows, texts = build(pid)
        (HERE / pid).mkdir(exist_ok=True)
        with (HERE / pid / "inventory.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        if tdir:
            tdir.mkdir(parents=True, exist_ok=True)
            with (tdir / f"{pid}.jsonl").open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps({**r, "text": texts[r["element_id"]]}, ensure_ascii=False) + "\n")
        import collections
        print(pid, len(rows), dict(collections.Counter(r["kind"] for r in rows)), "numbers in paragraphs:", sum(r["n_numbers"] for r in rows if r["kind"] == "paragraph"))
