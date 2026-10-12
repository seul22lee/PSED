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

## Status

fixed / limit / open; checked by auto script, Claude or user.

| ID | Item | Problem | Status | Checked by | Evidence (commit, papers) |
|---|---|---|---|---|---|
| F1 | Figures | Docling's own caption binding mostly wrong | fixed (own binding rules) | Claude (planning chat): 8 sampled papers (review_all.html), and 3 Dev papers, Ylilammi 10.1063_1.5028178, Yim 10.1039_d0cp03358h, pssa 10.1002_pssa.201532305, against review_dev.html and the PDFs: Ylilammi Fig. 1–7 and Yim Fig. 1–11 exact; pssa Fig. 8 went to Fig. 9, and logos attached to pssa Fig. 1 and 4. Done before later rule changes; pssa is now out of scope. | 647add1, 5918542, 70d98ab, bcf0d98; checked by hand on 8 sampled papers (74 of 75 exact, a120f36) and on Dev papers (count not recorded) |
| F2 | Figures | Docling merges side-by-side figures into one crop | limit | Claude | a120f36; 10.1116_6.0002804 Figures 6 and 8 have no crop of their own (merged into 5 and 7), also 10.1002_admi.202000318, 10.1039_d1dt03543f, 10.1186_s11671-015-0872-9 |
| F3 | Figures | Caption read before its picture; the picture goes to the next caption | limit | Claude | a120f36; 10.1002_pssa.201532305 Figure 8 went to Figure 9 |
| F4 | Figures | Nested caption without a label loses short pieces | limit | Claude | 1350a2c; 10.1186_s11671-015-0872-9 Figure 5 |
| F5 | Figures | Journal logos and banners attach to a figure | limit | Claude | a120f36; pssa Figures 1 and 4 |
| F6 | Figures | Figure-check count in INGEST.md (48 of 49) predates the current 44 papers | open | user | Figures section |
| T1 | Tables | Caption binding shifted by one; 11 of 63 tables right | fixed: 59 of 63 (the other 4 have no caption) | Claude (expected bindings) + auto score | 89f7357; 44 papers, 2026-10-12 |
| T2 | Tables | Multi-row headers flattened in the markdown | fixed (9 tables) | auto script (54 single-header tables byte-identical) + Claude | 7107b50 |
| T3 | Tables | Cell structure errors: merged or dropped rows, rotated table transposed | limit; a crop per table is saved for a vision model as last resort | Claude (8 picks against page renders) | 89f7357; Yim 10.1039_d0cp03358h Table 1, jpcc.9b08176, chemmater.1c03164, separations11010024, 2.067203jes |
| T4 | Tables | /C0, /C2 glyph names in cells | limit (no guessed substitution maps) | Claude | 89f7357 review; 22 tables, 17 of them RSC |
| T5 | Tables | Exponents and footnote letters split or glued in cells | limit | Claude | 89f7357 review; 21 tables with exponents, about 7 with footnote letters |
| T6 | Tables | Image-rendered table read by OCR | limit | auto script + Claude | c49f8c8; 10.1116_6.0003182 table 0 (page 4) |
| A1 | Abstract | Extraction for the 44 papers | fixed: 44 of 44 (24 heading, 19 openalex_match, 1 openalex) | Claude (planning chat), 2026-10-12: c7ta03257a and d4nr03749a against page renders; c5ta00205b, ijpharm.2017.04.031, mee.2018.01.027, mee.2018.01.033 by reading the extracted text only. Marks set on the user's instruction. The user did not check them. | 6c5cafa, 1ac60a6, b17bf29, 9e87def; marks in manifest abstract_review |
| A2 | Abstract | 10.1039_c4nr05049e drawn as image strips; OCR missed about 60 of 157 words | fixed (OpenAlex fallback, source openalex) | Claude (pdftotext, pdfplumber) + auto | 9e87def |
| A3 | Abstract | Fallback rules 3 (layout) and 4 (order) never used on the 44 papers | open (untested) | auto script (sources) | b17bf29; 0 of 44 |
| B1 | Body | Private-use ligature characters break words ("speci c", "a er") | open | auto script | 10 of 44 papers (2026-10-12), most in 10.1039_c5ta00205b, c7ta03257a, c3ra42928h |
| B2 | Body | Reading order puts title, authors and abstract inside the introduction; footnotes split sentences | open | Claude | seen in 10.1039_c7ta03257a page 2 (2026-10-12) |
| B3 | Body | Cover-page text at the top of document.md | open | Claude | AIP papers, e.g. 10.1063_5.0168768, 10.1063_1.5028178 |
| B4 | Body | Part of the text nested in figures (axis labels, legends, OCR'd labels) is written into document.md | open | auto script | 303 of 759 nested texts of 4+ words appear in document.md (44 papers, 2026-10-12); the OCR'd labels (43 papers, about 9,900 words) are only partly exported |
| B5 | Body | Running heads and footers | fixed (exact list verified) | auto script | b17bf29; 7 papers |
| B6 | Body | /C0, /C14, ¼ glyphs | limit (glyph names carry no meaning) | Claude | a120f36, ccce8fd |
| B7 | Body | Digit drawn for a degree sign ("300 1 C") | fixed as a "[?]" mark from PDF font evidence | auto script | ccce8fd; 170 digits in 4 papers |
| B8 | Body | Text-coverage check compares with pdftotext, which also breaks ligatures and cannot see OCR'd regions | open | Claude | 01f85c6 check, 2026-10-12 |
| B9 | Body | Headings drawn as outlines, read by OCR | limit | auto script + Claude | c49f8c8; 10.1021_acs.chemmater.1c03164, 17 headings |
| E1 | Equations | Not decoded | open (plan: Docling + Marker, a person decides disagreements) | user | Equations section; one-off test on Ylilammi 2018, 2026-10-12 |
| D1 | Docs | Numbers in INGEST.md lack date, commit, papers and method; some are stale | open | user | this file |
| D2 | Docs | Some "checked" marks were by Claude, not a person | open (to be labelled) | user | this file |

Rule: update the row in the same commit as any change that affects it.

## Environments

- `psed310`: Docling, pdfplumber. Runs `ingest/parse_docling.py`.
- `psed_marker`: Marker 2.0.0 only (llama.cpp backend, binary in `~/opt/llama.cpp/`).
  Kept separate: Docling pins transformers <5 and huggingface_hub <1, Marker needs newer; pillow pins conflict.
- Marker output is not fully deterministic across runs: run once per paper and keep the result.

## Marker

`ingest/parse_marker.py` (conda env `psed_marker`, llama.cpp settings from CLAUDE.md, set by the script when absent) runs Marker 2.0.0 once per paper and writes `ingest/marker/<paper_id>/` (gitignored): `document.md` with its figure crops (`_page_P_<Type>_K.jpeg`), `document_meta.json`, and `blocks.json`, the block tree rendered from the same conversion: block_type (Text, SectionHeader, Caption, Figure, Picture, Table, Equation, Footnote, PageHeader, PageFooter, …), page (1-based), bbox [l, t, r, b] in PDF points from the top-left, polygon, html, children. Same CLI shape as `parse_docling.py` (`<paper_id>…` | `--all`; in-scope rows with `pdf_status` ok; rows already ok are skipped and overwritten only with `--redo`). Manifest column `marker`: ok | failed | blank. Marker output is not deterministic across runs.

Settings: `force_ocr` (full-page OCR by the surya-ocr-2 VLM, layout from the OCR pass). Reason, checked on 10.1039_c7ta03257a on 2026-10-12: with the text layer Marker drops the letters of private-use ligatures ("specic", "aer", "soware") and the °, −, µ glyphs; with `force_ocr` the words and symbols come out right ("specific", "after", "°C", "min<sup>-1</sup>", "µg") and the reading order is the print order (title, authors, abstract, then the body). Runtime: 63–174 s per paper on one A6000 (13 papers, 2026-10-12; the llama.cpp server starts once per process).

Status, 13 papers (one per DOI prefix of the 44) compared with Docling against pdftotext body pages, 2026-10-12, by Claude: no body number changed by either tool; Docling splits decimals in one Elsevier paper ("0 . 178 eV", 10.1016_j.sse.2022.108584) and leaves /C glyphs and ligature characters, Marker renders them right; Marker turns the author line and the abstract block beside the TOC graphic into image placeholders in the ACS paper 10.1021_acs.jpcc.9b08176 (both lost) and splits the first Introduction paragraph by the affiliation block in 10.1002_adem.202201901; reading order title → authors → abstract → Introduction holds in Marker for all papers with such headings except the ACS one, in Docling it fails for RSC, Wiley and Beilstein layouts. Not used by the extraction yet; the plan is to use it for equations and to repair Docling's text where both differ (a decision for the user).

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
`structure.json` → `abstract`, `abstract_source`. Picked from Docling's text items, not reading order alone, so an abstract placed inside the introduction is still found. "Page 1" below is the first page with running text (publisher cover pages are skipped). In order:
1. the text under a heading "Abstract", or a paragraph starting with "Abstract:" (ACS), with its continuation items (past pictures and short widgets; the block ends where the overlap with the OpenAlex abstract drops, else where the column narrows, at a heading or keywords line, or at 400 words) → `heading`;
2. else, if OpenAlex has an abstract (`corpus/openalex_abstracts.json`, any length): the text item on pages 1–2 with the highest word overlap with it, joined with adjacent items that also overlap → `openalex_match`;
3. else the longest text item on page 1 wider than the body columns (1.4 × the median column width, i.e. full-width on a two-column page) → `layout`;
4. else the longest paragraph (40+ words) on page 1 after the author block and before the first body heading → `order`; if nothing, empty and `none`.
- Fallback: if the abstract's Docling items have no PDF text layer under them (OCR; pdfplumber finds no characters in their boxes) and recall against the OpenAlex abstract is below 80%, the OpenAlex abstract is used instead → `openalex` (one paper, 10.1039_c4nr05049e).
- Glyph repairs apply; `document.md` is unchanged. This is the extraction of commit 1ac60a6; the position, page-1 (2+ items) and abstract-side running-line variants tried on 2026-10-12 failed verification and were reverted (Change log).
- Check: `parse_docling.py --check-abstracts` prints, per paper, recall (OpenAlex words in ours), precision (our words in OpenAlex) and length ratio (our words / OpenAlex words); flags recall < 80%, precision < 80%, ratio > 1.5 or < 0.6. In the check only, an OpenAlex abstract under 50 words (a cover blurb) counts as missing; a paper without a usable OpenAlex abstract is flagged only if its abstract fails the form check: 80–400 words, ends with ".", and its first text item comes right after the title/author block (no body paragraph of 40+ words before it on that page; author and affiliation blocks excepted). An empty abstract is always flagged. Manifest column `abstract_review` records a review as `ok:<hash>` or `limit:<hash>` (first 8 hex of the sha1 of the reviewed abstract); a paper is skipped only while its abstract still has that hash, so a changed extraction is checked again; blank means not reviewed. Writes `ingest/review/abstract_check.html` (gitignored; ours next to OpenAlex's, pages 1–2 rendered) for the flagged papers.
- Result 2026-10-12 (44 parsed papers): 24 `heading`, 20 `openalex_match`, none from `layout`, `order` or `none`. Reviewed by eye, 7 marks: `limit` for c4nr05049e (Docling merged the abstract's two parts into one garbled item, recall 63%); `ok` for c7ta03257a, c5ta00205b, d4nr03749a (right, but their OpenAlex record is a short blurb) and for ijpharm.2017.04.031, mee.2018.01.027, mee.2018.01.033 (no OpenAlex abstract). Check after the revert: 0 flagged; the 37 unmarked papers have recall min 92%, precision min 83%, length ratio 0.92–1.42 against OpenAlex.

### Body text
- Running heads, footers and download stamps: a line of 10 words or fewer that appears identically (after the glyph repairs) on 3 or more pages and contains 4 or more letters (A–Z, a–z) is dropped from `document.md`; the abstract items, captions and tables are not touched. 2026-10-12, 44 papers: lines dropped in 7 papers only — "ARTICLE" (6.0001094 ×14, 6.0003182 ×7), "LETTER" (6.0002993 ×7), the two journal URLs (adem.202201901, ×9 and ×6), the DOI and journal-citation footers (jpcc.9b08176, ×3 each), "Separations" (separations11010024 ×4), and in 1.5116136 the manuscript title header (×9) and "Science Technology A Journal of Vacuum" (×4). The letter condition keeps the equation numbers, glyph names and single letters that also repeat across pages; a position rule (top or bottom 8% of the page) was tried the same day and caught only 1 of these lines, so it was not adopted.
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
- Abstract fallback: if the abstract's Docling items have no PDF text layer under them (OCR) and recall against the OpenAlex abstract is below 80%, the OpenAlex abstract is used, `abstract_source` = `openalex`. Reason: 10.1039_c4nr05049e draws its abstract as image strips and Docling's OCR missed about 60 of 157 words; the OpenAlex text is used and the source is marked (2026-10-12).
- OCR in general: our text checks compare against the PDF text layer, so they cannot see words missing from OCR'd regions. Census 2026-10-12 (pdfplumber characters under each Docling item, cross-checked with pdftotext; by Claude): Docling OCRs the labels inside figures in 43 of the 44 papers (about 7,000 items, 9,900 words; not body text). Outside figures, OCR-only text is substantive in 3 papers: the abstract and title of 10.1039_c4nr05049e, 17 section headings of 10.1021_acs.chemmater.1c03164 (46 words), and table 0 on page 4 of 10.1116_6.0003182; elsewhere it is page furniture only: manuscript stamps in 10.1116_1.5116136, cover-page adverts in 10.1116_6.0002993, 10.1116_6.0003182 and 10.1063_5.0168768, an "Export Citation" widget in 10.1116_6.0001094, one panel label in 10.1038_s41467-022-35428-6, one heading in 10.1039_c5ta00205b, one footer in 10.1039_d0cp03358h.

## Change log
Newest first. One line per change: date, what changed, effect, commit.

- 2026-10-12 — `structure_marker.py`: structure.json from Marker's blocks in Docling's schema (captions bound by Marker's groups, else parse_docling.py's position rules; tables as markdown; equations as LaTeX with page and bbox; abstract by the copied rules; document.md without running lines, Marker's own markdown kept as marker.md). Effect: 13 papers; compared with Docling item by item (review HTML in scratch, not committed). — this commit.
- 2026-10-12 — Marker stage added: `parse_marker.py` (Marker 2.0.0, force_ocr, llama.cpp backend) writes ingest/marker/<paper_id>/ with document.md, images and blocks.json; manifest column `marker`. Effect: 13 papers converted (one per DOI prefix), 63–174 s each; not used by the extraction yet. — this commit.
- 2026-10-12 — Abstract fallback to the OpenAlex text when the abstract is OCR-only and recall is below 80% (`openalex`). Effect: 10.1039_c4nr05049e gets its full 157-word abstract, mark ok:09ab0660; nothing else changed. — this commit.
- 2026-10-12 — Abstract extraction reverted to 1ac60a6 (heading, OpenAlex match, layout, order); kept check-side only: hash-bound `abstract_review` marks, empty abstract always flagged, form check without a usable OpenAlex abstract, 50-word rule in the check. Running lines (10 words or fewer, 3+ pages, 4+ letters) dropped from document.md only. Effect: all 7 marks verified (c7ta03257a = 4275c395), abstracts and captions unchanged, running heads/footers gone from 7 papers, 0 flagged. — this commit.
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
