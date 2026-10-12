# Ingest stage

PDF → text, figures, tables, equations for each in-scope paper. No LLM in this stage.
This file holds what ingest extracts, how, the decisions behind it, the known limits, and a change log.
`CLAUDE.md` points here; keep ingest details in this file only.

## What comes from where

| Item | Source | Tool | Output |
| --- | --- | --- | --- |
| DOI, title, authors, year, journal | `corpus/manifest.csv` (OpenAlex) | none: never extracted from the PDF | manifest columns |
| Abstract | PDF | Docling + rule | `structure.json` → `abstract` (planned) |
| Body text | PDF | Docling | `document.md` |
| Figures + captions | PDF | Docling for crops; caption binding by our rules (Docling's own binding is not used) | `structure.json` → captions with `images`; crops in `figures/pic_K.png` |
| Tables + captions | PDF | Docling for cells and position; caption: Docling's table–caption link first, else our same-page rule | `structure.json` → captions with `table` (markdown) and `image` (crop) |
| Equations | PDF | Docling and Marker, compared | planned: per-equation LaTeX from both, agreement flag |

Paths: `ingest/docling/<paper_id>/` (gitignored). Progress: manifest column `docling`.

## Environments

- `psed310`: Docling, pdfplumber. Runs `ingest/parse_docling.py`.
- `psed_marker`: Marker 2.0.0 only (llama.cpp backend, binary in `~/opt/llama.cpp/`).
  Kept separate: Docling pins transformers <5 and huggingface_hub <1, Marker needs newer; pillow pins conflict.
- Marker output is not fully deterministic across runs: run once per paper and keep the result.

## Rules per item

### Figures
Caption binding replaces Docling's; rules are in the `parse_docling.py` docstring.
Checked by hand on 8 sampled papers (74 of 75 exact) and on Dev papers. Figure check: 48 of 49 papers pass at the last full count.

### Tables
- Caption binding: Docling's own table–caption link first (if its text starts with "Table N"); else the nearest unused Table caption on the same page, before or after. Never across pages.
- Caption numbers: letter prefixes allowed (A1, S1); "Table N" followed by a capitalised word counts even without punctuation.
- Glyph repairs apply to table markdown as to text.
- Each table also has a crop image (`figures/tab_K.png`, K = index in Docling's tables, cut from the PDF page with pypdfium2 at the picture scale; `image` in the structure.json entry), for checking and, as a last resort, reading by a vision model at extract time.
- Result of the 2026-10-12 change (63 tables in 28 of the 44 parsed papers, scored against Docling's own caption links and a hand check of the rest): 11 → 59 tables numbered as expected, none worse; the 4 others have no caption anywhere (bjnano.5.25 t0/t1, acsami.0c06879 t0, 6.0003182 t0). Before, 15 tables were shifted by one because Docling places the linked caption after the table in reading order although 43 of the 45 are printed above it, 24 were unnumbered, and 4 symbol lists had taken leftover captions. Figure entries unchanged, except Figure A1 of 10.3390_separations11010024, now bound thanks to the letter prefix.
- Known, not fixed: TableFormer structure errors in 7 of 9 inspected tables (merged or dropped rows, a spurious empty column, table footnotes absorbed as rows, ± dropped in one row, a rotated page read transposed: Yim Table 1); `/Cn` glyphs in 22 tables (mostly RSC); exponents and footnote letters flattened ("1 × 10 - 4", "Kn c 1 c"); multi-row headers appear only as row 0 in the markdown.
- Not done: substitution maps for `/Cn` glyphs, rewriting exponents, multi-row header merge (next), symbol lists read as tables (left unnumbered).

### Equations
- Both Docling (`do_formula_enrichment`) and Marker extract LaTeX. Tested on Ylilammi 2018: each got about 37 of 46 right, wrong on different equations.
- Decision: keep both. Equations where they agree (after notation normalisation) are accepted; where they disagree, a person decides. Not yet built.

### Abstract (planned)
- Text under an "Abstract" heading; otherwise the longest paragraph between the author block and the first body section.
- Checked against the OpenAlex abstract (word overlap); papers below 80% are flagged for a person.

### Body text (planned check)
- Share of pdftotext words found in `document.md` per paper; below 95% is flagged. Repeated running headers/footers are flagged.

### Glyph repairs (text, captions, tables)
- `/uniXXXX`, `/uXXXXX` → the character; ligatures → plain letters.
- A digit drawn in a symbol font between a number and C/K ("300 1 C") → "300 [?] C", using PDF font evidence. The symbol is not guessed.
- Other broken glyphs (`/C0`, `/C14`, `¼`, private-use) are left as they are.

### Last resort
A vision model reading the crop (figure, table, equation) is allowed only where rules and the two tools fail, and only at extract time.

## Known limits
Accepted limits of the Docling stage; do not fix without a new decision. Moved from `CLAUDE.md` on 2026-10-12.

- Figure binding was checked by hand on 8 sampled papers: 74 of 75 figures exact.
- Docling-side misses: a few captions are absent from Docling output (image-only PDF, caption drawn as image) or two side-by-side figures are merged into one crop. Seen in 10.1002_admi.202000318, 10.1039_d1dt03543f, 10.1186_s11671-015-0872-9, 10.1116_6.0002804.
- Captions split across two columns keep only the first part. Captions split across pages are joined.
- A non-figure image (equation, banner whose copy differs slightly) on a figure's page can attach to that figure as an extra image.
- Tables: caption binding is not validated. Known issues: shift by one when Docling reads a table before its caption, tables Docling does not detect, captions placed inside the table's first row. [The shift by one was fixed on 2026-10-12, see Tables and the change log; the other two remain.]
- Broken glyphs from PDF fonts (e.g. "/C14" for °, "/C0" for −, "¼" for =, private-use characters) are not fixed yet. Fixed: "/uniXXXX" and "/uXXXXX" glyph names; a digit standing for a degree sign ("300 1 C") is marked "[?]" where the PDF font shows it.
- Equations are not decoded.
- 10.1146_annurev-chembioeng-060816-101547 is a review paper; whether it belongs in the corpus is a corpus question.
- Docling occasionally reads a caption before its picture although the caption is below it; the picture then goes to the next caption (seen: 10.1002_pssa.201532305 Figure 8 went to Figure 9).
- Repeated journal logos whose copies differ slightly are not caught as decoration and can attach to a figure (seen: pssa Figures 1 and 4).
- A paper that prints the same figure number twice keeps one caption; the other figure can lose its image (seen: 10.1021_acsaelm.3c00245 Figure 10).
- Manuscripts that list all captions together and put the figures at the end cannot be bound by position (seen: 10.1116_1.5116136).
- Docling sometimes labels a body sentence as a caption, which then replaces the real one (seen: 10.1021_acs.chemmater.9b05116 Figure 10).
- A caption nested inside its picture without a caption label keeps only text items of 4 or more words, so short pieces (panel markers like (a), short phrases) can drop out (seen: 10.1186_s11671-015-0872-9 Figure 5).

## Change log
Newest first. One line per change: date, what changed, effect, commit.

- 2026-10-12 — Tables: caption binding uses Docling's table–caption link first, then the nearest unused same-page caption; letter-prefixed numbers (A1, S1) and "Table N Capitalised" items of any label accepted; glyph repairs on table markdown; crop per table (`figures/tab_K.png`, `image` in structure.json). Effect: 11 → 59 of 63 tables numbered as expected, none worse; Figure A1 of separations11010024 gained. Known limits moved here from CLAUDE.md. — this commit.
- 2026-10-12 — CLAUDE.md records the Marker environment (psed_marker env, llama.cpp backend, `~/opt/llama.cpp/`). Effect: Marker 2.0.0 runs without touching psed310. — 2118b2a
- 2026-10-03 — Known limit added: a caption nested in its picture without a label keeps only text items of 4+ words. Effect: documented only. — 1350a2c
- 2026-10-03 — parse_docling.py split into a Docling step (docling.json, figures/pic_K.png) and a binding step; `--rebind` reruns binding and text repairs without Docling; binding fixes for the last figure failures. Effect: rebinding takes seconds per paper. — bcf0d98
- 2026-10-01 — Broken-glyph known limit extended with private-use characters. Effect: documented only. — f977f3d
- 2026-10-01 — Glyph names `/uniXXXX` and `/uXXXXX` replaced (ligatures as plain letters); digit-like degree signs marked "[?]" from PDF font evidence. Effect: 2,400 glyph names in 14 papers, 170 digits in 4 papers; figure check unchanged at 52/59. — ccce8fd
- 2026-10-01 — Chinese caption words (图, 表) accepted; two known limits added (captions listed together with the figures at the end; body sentences Docling labels caption). Effect: bilingual captions bound. — d86775f
- 2026-10-01 — Scope column in the manifest; parse_docling.py parses in-scope papers only. Effect: out-of-scope papers are skipped. — 101ade3
- 2026-10-01 — Paths fixed after the move to ingest/. Effect: none on output. — 0caa45b
- 2026-10-01 — Docling stage moved from corpus/ to psed_v2/ingest/. Effect: none on output. — 82896bd
- 2026-10-01 — parse_docling.py empties a paper's figures/ before parsing it. Effect: no stale crops from earlier parses. — ec3983f
- 2026-10-01 — CLAUDE.md records the Docling stage's known limits (11 bullets, with the papers where each was seen). Effect: documented only. — a120f36
- 2026-10-01 — Picture binding refinements: pictures outside the page area and repeated decoration images ignored; the next-page rule only for a picture after the last text item; previous-else-next caption fallback. Effect: margin stamps and logos no longer bound. — 70d98ab
- 2026-10-01 — Pictures bound by caption position (next overlapping caption on the page, else the next page's first caption, else the previous one); captions nested in pictures seen; heading rule dropped. Effect: 5 of the 10 failing papers pass. — 5918542
- 2026-09-30 — Own caption binding replaces Docling's for pictures and tables, in reading order; structure.json lists one entry per caption. Effect: first bound structure.json. — 647add1
- 2026-09-30 — docling_parse.py renamed parse_docling.py. Effect: none on output. — ee51eca
- 2026-09-30 — v1's Docling parse stage ported (corpus/docling_parse.py), manifest column `docling`; run on one paper (Ylilammi 2018). Effect: first ingest output. — cc5e59d
