"""
slice_scopes.py
---------------
Produce the three INPUT-SCOPE text slices per paper from the existing docling
output, so the only variable in the benchmark is how much of the paper the
extractor sees:

  abstract              - sections.json['abstract']
  abstract+conclusion   - abstract + sections.json['conclusion']
  full                  - 01_docling/document.md  (whole manuscript)

Pure file ops (no LLM). Writes slices/<paper_id>/{abstract,abstract_conclusion,full}.txt
plus slices/index.json describing what was available (e.g. missing abstracts).
"""
import json
import re
from pathlib import Path

SRC = Path(__file__).parent.parent.parent / "0604_kg" / "output"
OUT = Path(__file__).parent / "slices"


def paper_id(name: str) -> str:
    m = re.match(r"([A-Za-z]+) et al\. - (\d{4})", name)
    return f"{m.group(1)}{m.group(2)}".lower() if m else re.sub(r"\W+", "_", name)[:20]


def read_evidence(pdir) -> str:
    """Assemble the experiment-relevant text: figure captions + the paragraphs
    that discuss them + table captions/content. This is the 'evidence region'
    (excludes intro/background), built from the 05_enrich_figures + tables output."""
    parts, seen = [], set()

    def add(tag, txt):
        txt = str(txt).strip()
        if txt and txt not in seen:
            seen.add(txt)
            parts.append(f"{tag}{txt}" if tag else txt)

    enrich = pdir / "05_enrich_figures"
    if enrich.exists():
        for jf in sorted(enrich.glob("figure-*.json")):
            d = json.loads(jf.read_text())
            add("[FIGURE CAPTION] ", d.get("caption") or "")
            for lbl in (d.get("x_label"), d.get("y_label")):
                add("[AXIS] ", lbl or "")
            for c in (d.get("figure_contexts") or []):
                add("", c)
            sub = d.get("subfigure_contexts") or {}
            if isinstance(sub, dict):
                for v in sub.values():
                    add("", v if isinstance(v, str) else " ".join(map(str, v)) if isinstance(v, list) else "")
    tdir = pdir / "01_docling" / "tables"
    if tdir.exists():
        tj = tdir / "tables.json"
        if tj.exists():
            try:
                td = json.loads(tj.read_text())
                items = td if isinstance(td, list) else td.get("tables", [])
                for t in items:
                    if isinstance(t, dict):
                        add("[TABLE CAPTION] ", t.get("caption") or t.get("title") or "")
            except Exception:
                pass
        for csv in sorted(tdir.glob("*.csv")):
            add("[TABLE]\n", csv.read_text()[:2000])
    return "\n\n".join(parts)


def main():
    index = []
    for pdir in sorted(SRC.iterdir()):
        if not pdir.is_dir():
            continue
        doc = pdir / "01_docling" / "document.md"
        sec = pdir / "01_docling" / "sections.json"
        if not doc.exists() or not sec.exists():
            continue
        s = json.loads(sec.read_text())
        abstract = (s.get("abstract") or "").strip()
        conclusion = (s.get("conclusion") or "").strip()
        full = doc.read_text()

        evidence_region = read_evidence(pdir)
        evidence = (abstract + "\n\n" + conclusion + "\n\n" + evidence_region).strip()

        pid = paper_id(pdir.name)
        d = OUT / pid
        d.mkdir(parents=True, exist_ok=True)
        (d / "abstract.txt").write_text(abstract)
        (d / "abstract_conclusion.txt").write_text(
            (abstract + "\n\n" + conclusion).strip())
        (d / "evidence.txt").write_text(evidence)
        (d / "full.txt").write_text(full)

        rec = {
            "paper_id": pid,
            "paper": pdir.name,
            "abstract_chars": len(abstract),
            "abstract_conclusion_chars": len((abstract + conclusion)),
            "evidence_chars": len(evidence),
            "full_chars": len(full),
            "abstract_available": bool(abstract),
        }
        index.append(rec)
        flag = "" if abstract else "   [!] no parsed abstract"
        print(f"  {pid:12} abstract={len(abstract):>5}  abs+concl={len(abstract)+len(conclusion):>6}  "
              f"evidence={len(evidence):>6}  full={len(full):>6}{flag}")

    (OUT / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"\nwrote {len(index)} papers x 3 scopes -> {OUT}")
    n_abs = sum(1 for r in index if r["abstract_available"])
    print(f"abstract-scope covers {n_abs}/{len(index)} papers "
          f"(papers without a parsed abstract are excluded from abstract-scope scoring)")


if __name__ == "__main__":
    main()
