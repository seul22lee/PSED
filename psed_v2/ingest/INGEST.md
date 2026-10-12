# Ingest stage

PDF → text, figures, tables, equations for each in-scope paper. No LLM in this stage.
This file holds what ingest extracts, how, the decisions behind it, the known limits, and a change log.
`CLAUDE.md` points here; keep ingest details in this file only.

## What comes from where

| Item | Source | Tool | Output |
| --- | --- | --- | --- |
| DOI, title, authors, year, journal | `corpus/manifest.csv` (OpenAlex) | none: never extracted from the PDF | manifest columns |
| Abstract | PDF (+ OpenAlex abstract as a locator) | Docling text items + four rules in order (heading, OpenAlex match, layout, order) | `structure.json` → `abstract`, `abstract_source` |
| Body text | PDF | Docling | `document.md` |
| Figures + captions | PDF | Docling for crops; caption binding by our rules (Docling's own binding is not used) | `structure.json` → captions with `images`; crops in `figures/pic_K.png` |
| Tables + captions | PDF | Docling for cells and position; caption: Docling's table–caption link first, else our same-page rule | `structure.json` → captions with `table` (markdown) and `image` (crop) |
| Equations | PDF | Docling and Marker, compared | planned: per-equation LaTeX from both, agreement flag |

Paths: `ingest/docling/<paper_id>/` (gitignored). Progress: manifest column `docling`.
`corpus/openalex_abstracts.json` (gitignored): OpenAlex abstracts of the in-scope papers, fetched once with `parse_docling.py --fetch-abstracts` (the only network call in ingest; `--rebind` never calls the network). Fetched 2026-10-12: 273 of 327 in-scope papers have one.

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
- Markdown is built from Docling's cell grid: the column-header rows at the top (Docling's `column_header` flag) become one header line, the texts per column joined with " / " (a cell spanning several columns applies to each; repeated identical parts skipped). Tables with one header row are Docling's own export, byte for byte. 2026-10-12: 9 tables changed, 54 unchanged.
- Not done: substitution maps for `/Cn` glyphs, rewriting exponents, symbol lists read as tables (left unnumbered).

### Equations
- Both Docling (`do_formula_enrichment`) and Marker extract LaTeX. Tested on Ylilammi 2018: each got about 37 of 46 right, wrong on different equations.
- Decision: keep both. Equations where they agree (after notation normalisation) are accepted; where they disagree, a person decides. Not yet built.

### Abstract
`structure.json` → `abstract`, `abstract_source`. Picked from Docling's text items, not reading order alone, so an abstract placed inside the introduction is still found. "Page 1" is the first page with 2 or more text items of 25+ words (publisher cover pages are skipped; an inside-cover blurb page qualifies only if its blurb is split into two such items, as in c7ta03257a). Items that are running lines (see Body text) are not used. In order:
1. the text under a heading "Abstract", or a paragraph starting with "Abstract:" (ACS), with its continuation items (past pictures and short widgets; the body starts where the OpenAlex overlap drops, else where the column narrows; 400 words at most) → `heading`;
2. else, if OpenAlex has an abstract of 50 words or more (shorter ones are cover blurbs and count as missing, here and in the check): the text item on pages 1–2 with the highest word overlap with it, joined with adjacent items that also overlap → `openalex_match`;
3. else the longest text item on page 1 wider than the body columns (1.4 × the median column width, i.e. full-width on a two-column page) → `layout`;
4. else the longest paragraph (40+ words) on page 1 after the author block and before the first body heading → `order`; if nothing, empty and `none`.
- Glyph repairs apply; `document.md` is unchanged.
- Check: `parse_docling.py --check-abstracts` prints, per paper, recall (OpenAlex words in ours), precision (our words in OpenAlex) and length ratio (our words / OpenAlex words); flags recall < 80%, precision < 80%, ratio > 1.5 or < 0.6. A paper without a usable OpenAlex abstract (none, or under 50 words) is flagged only if its abstract fails the form check: 80–400 words, ends with ".", and its first text item comes right after the title/author block (no body paragraph of 40+ words before it on that page; author and affiliation blocks excepted). An empty abstract is always flagged. Manifest column `abstract_review` records a review as `ok:<hash>` or `limit:<hash>` (first 8 hex of the sha1 of the reviewed abstract); a paper is skipped only while its abstract still has that hash, so a changed extraction is checked again; blank means not reviewed. Writes `ingest/review/abstract_check.html` (gitignored; ours next to OpenAlex's, pages 1–2 rendered) for the flagged papers.
- Result 2026-10-12 (44 parsed papers): 24 `heading`, 20 `openalex_match`, none from `layout`, `order` or `none`; overlap with OpenAlex (41 papers have one) min 63%, median 98%; 1 flagged: 10.1039_c4nr05049e (63%, Docling merged the abstract's two parts into one garbled item; the rest is not in any text item).
- Checked 2026-10-12 on 44 papers: 43 correct, 1 known limit. Some RSC papers have only a short blurb as their OpenAlex abstract, so they are flagged by precision and length ratio although the extraction is right (c7ta03257a, c5ta00205b, d4nr03749a); papers without an OpenAlex abstract are checked by eye (3, all correct).
- Follow-up 2026-10-12 (50-word rule, form check, `abstract_review` column: limit for c4nr05049e, ok for the 3 RSC blurb papers and the 3 without an OpenAlex abstract): rebound all 44; c5ta00205b and d4nr03749a now come from the `layout` rule with the same text; c7ta03257a is now empty (`none`): its inside-cover page has a 33-word blurb, so it counts as the first page with running text and rules 3–4 look there, while the abstract is on page 2. Open, no rule change made. Check: 0 flagged of the 37 not marked.
- 2026-10-12, page-1 rule (2+ items of 25+ words) and hash-bound marks: no abstract changed; c7ta03257a stays empty because its cover blurb is two items of 38 and 33 words, so the cover page still counts as page 1 (the abstract, 207 words, is on page 2). Check: 1 flagged (c7ta03257a, empty) of 44. Open: raise the page-1 rule to 3 items, or 2 items of 40+ words.

### Body text
- Running heads, footers and download stamps: a text of 10 words or fewer that appears identically on 3 or more pages is dropped from `document.md` and from the items the abstract is picked from (captions and tables are not touched). 2026-10-12: 262 lines in 13 of 44 papers, e.g. "ARTICLE" ×14 (AVS), "www.aem-journal.com" ×9 (Wiley), "DOI: 10.1021/acs.jpcc.9b08176" ×3 (ACS), a manuscript's title header ×5; the rule also catches repeated fragments ("|", "2", "/C18", "s") in RSC and AIP papers.
- Coverage check (2026-10-12, commit 01f85c6, 44 papers, method auto, read-only): share of pdftotext words (lowercased, 4+ letters, reference list excluded) found in `document.md`: min 94.3%, median 98.7%. Only 10.3390_separations11010024 is below 95%, and its missing words are pdftotext artefacts (dropped spaces: "theflow"); the other low ones are ligature fragments ("usion", "cient") and the RSC footer. No real body text found missing. Below 95% is the flag for the next run.

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
- Abstract: when Docling garbles or drops part of the abstract, the extracted abstract stays incomplete; it is not replaced by the OpenAlex abstract (seen: 10.1039_c4nr05049e, recall 63%).

## Change log
Newest first. One line per change: date, what changed, effect, commit.

- 2026-10-12 — Page-1 rule for the abstract (2+ items of 25+ words), `abstract_review` marks bound to the abstract's hash (empty abstract always flagged), running heads/footers/stamps (10 words or fewer, identical on 3+ pages) dropped from document.md and from the abstract's items. Effect: 262 lines dropped in 13 papers, no abstract changed, c7ta03257a still empty (open), 1 flagged. — this commit.
- 2026-10-12 — Abstract follow-up: OpenAlex abstracts under 50 words count as missing; --check-abstracts form check (80–400 words, final period, after the title/author block) for papers without a usable OpenAlex abstract; manifest column `abstract_review` (ok/limit skipped). Effect: 3 abstracts changed source, one of them (c7ta03257a) now empty; 0 flagged. — this commit.
- 2026-10-12 — Abstract check closed: 43 of 44 correct, 1 known limit (c4nr05049e); RSC blurb abstracts and the 3 papers without an OpenAlex abstract checked by eye. Effect: documented only. — this commit.
- 2026-10-12 — Abstract: `abstract` and `abstract_source` in structure.json (heading, OpenAlex match, layout, order rules); `--fetch-abstracts` writes corpus/openalex_abstracts.json once; `--check-abstracts` scores against OpenAlex and writes review/abstract_check.html. Effect: 44 of 44 abstracts found (24 heading, 20 OpenAlex match), overlap median 98%, 1 flagged. — this commit.
- 2026-10-12 — Tables: markdown built from Docling's cell grid; column-header rows merged into one header line joined with " / ". Effect: 9 tables with 2–3 header rows changed, the 54 single-header tables byte-identical. — this commit.
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
