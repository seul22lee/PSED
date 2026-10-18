#!/usr/bin/env python3
"""Stage 1: <paper_id>.elements.csv for each pilot paper, from ingest/final/<paper_id>/ (document.md, structure.json).

    python3 psed_v2/pilot/elements.py [--text DIR]

Columns: element_id, kind (abstract | heading | paragraph | caption | panel | table_cell | equation), section, locator,
n_numbers, n_chars, crop (figure image under ingest/final/<paper_id>/). No paper text goes into the tracked file; with
--text DIR, DIR/<paper_id>.jsonl gets the text of every element (for reading; kept out of git).
Ids: abs.g<n> (two abstract sentences per group), s<sec>.h (a heading), s<sec>.p<n> (paragraph n of section sec, in reading
order; s0 = front matter), s<sec>.x<n> (a paragraph that starts with a figure reference but is not a caption), eq<n>
(display equations in reading order), fig<n>.cap and fig<n><panel> (one element per lettered panel seen on the crop,
PANELS below; fig<n> when the figure is one panel), tab<n>.cap and tab<n>.r<i>c<j> (row 0 = header), tabu<k>.r<i>c<j>
(unnumbered tables, e.g. a nomenclature list). n_numbers of a panel is blank: numbers drawn on an image are not counted
from text; they are listed as facts.
Not elements: journal logos and cover pictures on the first pages, and the reaction images of gre23 that repeat eq3-eq5.
"""
import collections, csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PAPERS = {"10.1039_d0cp03358h": "yim20", "10.1021_acs.chemmater.2c01154": "mat22", "10.1116_6.0003182": "gre23"}
# 10.1021_cm0303080 (ela03): a draft facts file stopped on 2026-10-17 (Directive 5), not built; the nine papers join in a later directive
# lettered panels per figure, read from the crops ("" = the figure is one panel)
PANELS = {
    "10.1039_d0cp03358h": {"1": "abc", "2": "abcd", "3": "ab", "4": "abc", "5": "ab", "6": "", "7": "", "8": "ab",
                           "9": "abcdef", "10": "abcdef", "11": "ab"},
    "10.1021_acs.chemmater.2c01154": {"1": "abcd", "2": "", "3": "ab", "4": "", "5": "ab", "6": "ab", "7": "ab", "8": "",
                                      "9": "ab"},
    "10.1116_6.0003182": {"1": "ab", "2": "abcd", "3": "abc", "4": "abcd", "5": "", "6": "abcdef"},
    "10.1021_cm0303080": {"1": "ab", "2": "ab", "3": "", "4": "", "5": "ab", "6": "ab", "7": "ab", "8": "ab", "9": "ab", "10": "ab", "11": "ab", "12": "ab", "13": ""},
}
FIELDS = ["element_id", "kind", "section", "locator", "n_numbers", "n_chars", "crop"]
NUM = re.compile(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?(?:\s*[×x]\s*10\^?\{?[-−]?\d+\}?)?(?:[eE][-−+]?\d+)?")


def numbers(t):
    t = re.sub(r"<sup>.*?</sup>|\[\d+(?:[,–-]\d+)*\]|\(\s*ref\.?.*?\)", " ", t)          # citation markers are not data
    t = re.sub(r"(Fig(ure)?s?\.?|Table|Eq(n)?s?\.?|eqn|Section|Sec\.)\s*\(?\d+[a-z]?", " ", t, flags=re.I)
    return NUM.findall(t)


def table_lines(md):
    return [l for l in (md or "").splitlines() if l.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|$", l.strip())]


def build(pid):
    """(rows, texts) of one paper."""
    st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
    doc = (V2 / f"ingest/final/{pid}/document.md").read_text(encoding="utf-8")
    m = re.search(r"\n\s*(?:#+\s*)?(?:■\s*)?\**\s*(Notes and references|References|REFERENCES)\b", doc)
    body = doc[:m.start()] if m else doc
    rows, texts = [], {}

    def add(eid, kind, sec, loc, text, crop="", count=True):
        rows.append(dict(element_id=eid, kind=kind, section=sec, locator=loc, n_numbers=len(numbers(text)) if count else "",
                         n_chars=len(text) if count else "", crop=crop))
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
    done, k = set(), 0
    for c in st["captions"]:
        n = str(c.get("number") or "")
        if c["kind"] == "figure" and n:
            crop = (c.get("images") or [""])[0]
            add(f"fig{n}.cap", "caption", "figures", f"Fig. {n} caption", c["caption"], crop)
            for p in PANELS[pid][n] or [""]:                                # panels follow their caption
                add(f"fig{n}{p}", "panel", "figures", f"Fig. {n}{p}", f"[panel {p or '(whole)'} of Fig. {n}; see the crop] " + c["caption"],
                    crop, count=False)
            done.add(n)
        elif c["kind"] == "table" and n:
            add(f"tab{n}.cap", "caption", "tables", f"Table {n} caption", c["caption"])
            for i, l in enumerate(table_lines(c.get("table"))):
                for j, cell in enumerate([x.strip() for x in l.strip().strip("|").split("|")]):
                    if cell:
                        add(f"tab{n}.r{i}c{j}", "table_cell", f"tab{n}", f"Table {n}, row {i}, column {j}", cell)
    for c in st["captions"]:
        if c["kind"] == "table" and not c.get("number") and c.get("table"):
            k += 1
            for i, l in enumerate(table_lines(c["table"])):
                for j, cell in enumerate([x.strip() for x in l.strip().strip("|").split("|")]):
                    if cell:
                        add(f"tabu{k}.r{i}c{j}", "table_cell", f"tabu{k}",
                            f"unnumbered table {k} (page {c.get('page')}), row {i}, column {j}", cell)
    missing = set(PANELS[pid]) - done
    assert not missing, (pid, missing)
    return rows, texts


def texts(pid):
    """Element texts from the ingest output (read at run time; never written to a tracked file)."""
    return build(pid)[1]


def load(pid):
    return list(csv.DictReader((HERE / f"{pid}.elements.csv").open(encoding="utf-8")))


if __name__ == "__main__":
    tdir = Path(sys.argv[sys.argv.index("--text") + 1]) if "--text" in sys.argv else None
    for pid in PAPERS:
        rows, tx = build(pid)
        with (HERE / f"{pid}.elements.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
        if tdir:
            tdir.mkdir(parents=True, exist_ok=True)
            with (tdir / f"{pid}.jsonl").open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps({**r, "text": tx[r["element_id"]]}, ensure_ascii=False) + "\n")
        print(pid, len(rows), dict(collections.Counter(r["kind"] for r in rows)))
