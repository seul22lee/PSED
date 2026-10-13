# Ingest stage

PDF → text, figures, tables, equations for each in-scope paper, one folder per paper in
`ingest/final/<paper_id>/`. No external LLM API is called. Two local vision-language models run:
Docling's CodeFormula (CodeFormulaV2, equations) and Marker's surya-ocr-2 (page OCR and the band-crop
repairs, served by llama.cpp). This file holds what ingest extracts, with which tool, the numbers
behind each choice, the environments and a change log. The errors that remain after the rules are in
[ERRORS.md](ERRORS.md). `CLAUDE.md` points here; keep ingest details in these two files only.

All numbers below: 2026-10-12 for the 13 Marker papers (one per DOI prefix of the 44 in scope) and
2026-10-13 for the other 31 (the "44" numbers), checked by Claude Code on the PDF pages and crops
("page") or by script against the PDF text layer or pdftotext ("script"), at the commit named in the
change log line of the same date. The user has not re-checked them. Each cell of the pipeline table says
how its subset was checked. Marker's output is not deterministic (llama.cpp backend, no fixed seed or
temperature): each paper was converted once and its output kept; the 44 outputs, and the numbers below,
are not reproducible bit for bit by rerunning `parse_marker.py`.

## Pipeline

```
psed_marker env:  parse_marker.py --all                 Marker 2.0 (force_ocr) + band-crop OCR -> ingest/marker/<id>/
psed310 env:      structure_marker.py --all             structure.json (captions, tables + check, equations, abstract)
psed310 env, GPU: parse_docling.py --formulas <ids>     Docling layout + CodeFormula on R1/R2 crops -> docling/<id>/equations.json
psed310 env:      merge.py --all                        ingest/final/<id>/ (Marker items + paired equations + body_flags from body_check.py)
```

| Item | Tool | How | Output in `final/<id>/structure.json` | Numbers (13 or 44 papers, as each cell says) |
| --- | --- | --- | --- | --- |
| DOI, title, authors, year, journal | `corpus/manifest.csv` (OpenAlex) | never extracted from the PDF | — | — |
| Body text | Marker | `document.md` without running lines (10 words or fewer, identical on 3+ pages, 4+ letters); band-OCR'd blocks (abstracts, author lines, an image-only table) written into it; body-number check by `body_check.py` (decoded text layer vs document.md per paragraph) | `document.md`; `body_flags` (one entry per mismatch: page, text-layer line, output sentence, numbers on each side, crop) and `body_check` (counts, not-checkable reasons) | 44 papers. 13 papers: numbers and 25-word blocks checked by script on 2026-10-12, flags viewed on the page; 31 papers: the same script check on 2026-10-13, flags viewed on the page (review_31). body_flags on 2026-10-13 (script): 1,154 flags in 34 papers (10 papers none), 761 of them in the line-numbered manuscript 10.1021_acs.chemmater.9b05116 whose margin numbers Marker merged into the text; of the known page verdicts it catches 3 of 3 real errors (a-MoS3,0; SP4-4004STRS; the dropped sentence p 33) and "<001>" written "< 0.01 >", and flags 0 of the 41 items judged not errors. Not checkable (reported, never skipped): 2,726 lines with an undecoded symbol-font glyph, 72 garbled lines of the MDPI duplicate layer, 192 output sentences the layer does not cover, 37 paragraphs shared with a not-checkable unit; 22,022 rotated characters. See ERRORS.md |
| Abstract | Marker | the rules copied from the Docling stage (heading / "Abstract:" paragraph, OpenAlex match on pages 1–2, layout, order) on Marker's blocks; the OpenAlex text when it has 50+ words and the extracted abstract is empty or has recall < 80 % against it | `abstract`, `abstract_source` | 44 of 44 right: 23 heading, 20 openalex_match, 1 openalex (10.1021_acs.langmuir.6b03119, whose abstract block is an image the band OCR could not read). How checked: the 13 papers on the page; of the 31, the 26 with a usable OpenAlex abstract (50+ words) by word recall against it (all 26 ≥ 90 %, script), the 5 without one (10.1016_j.ijpharm.2017.04.031, 10.1016_j.mee.2018.01.027, 10.1016_j.mee.2018.01.033, 10.1039_c5ta00205b, 10.1039_d4nr03749a) on the page on 2026-10-13 |
| Figures + captions | Marker | Marker's FigureGroup/PictureGroup binding, else the position rules; Text blocks that start with a caption label count; T1 band OCR for captions drawn inside the picture; captions do not continue into a body paragraph; figures placed after all captions bound by page order | `captions` with `images` | 44 papers: every numbered caption has its image and text. How checked: the 13 papers on the page; the 31 by script (caption numbers, images, text against the text layer), the flagged items viewed on the page; 2 figures split into panel blocks keep one panel unbound (ERRORS.md) |
| Tables + captions | Marker | Table html → github markdown (`<th>` rows merged with " / ", rowspans/colspans honoured, superscripts as `^`, trailing zeros kept); caption = nearest unused table caption on the page (position, not Marker's TableGroup); rule check against the decoded text layer (`glyph_codes.json`) + crop | `captions` with `table`, `bbox`, `check`, `check_reasons`, `check_detail`, `crop` | 69 tables in 28 papers (page): 41 right, 28 wrong; the check flags 27 of the 28, misses 0, flags 7 right tables, 1 wrong table not checkable (rotated) |
| Equations | Docling + Marker | Docling's layout gives the formula boxes, CodeFormula reads our crops (R1 tight box at 216 dpi; R2 band box when the box is ≤ 25 pt wide); Marker's `<math>` blocks; pairs by page and box, `agree` / `differ` | `equations[{page, bbox, number, docling, marker, status}]` | 44 papers: 321 entries, 197 agree, 109 differ, 15 one tool only (script counts). Judged on the crop only for the 13 papers' 29 differ pairs of their 103 pairs (74 agree): Marker right 14, Docling right 7, both wrong 3, equivalent forms 5; the 31 papers' equations were not judged on the page |

Paths: `ingest/marker/<id>/` (blocks.json, marker.md, document.md, images, structure.json, table crops,
bands.json), `ingest/docling/<id>/equations.json`, `ingest/final/<id>/` (all gitignored; the body-flag crops are
`final/<id>/figures/body_p<P>_<k>.png`). Progress:
manifest column `marker` (ok | failed | blank); `--formulas` and `merge.py` write no column.
`corpus/openalex_abstracts.json` (gitignored): OpenAlex abstracts, fetched once with
`parse_docling.py --fetch-abstracts` (the only network call in ingest), used by the abstract rule and
its fallback.

Review of what ingest flags is not part of ingest: a flagged table (`check: flag`) and an equation pair
with `status: differ` are resolved by an external vision-language model on the crop as a pre-processing
step of the extraction stage (planned). Ingest only writes the flags, the reasons and the crops.

## Why Marker for text, figures, tables and the abstract

Item-by-item comparison of the two tools on the 13 papers (every disagreement one row, crop viewed or
checked against pdftotext; the report is in `ingest/reports/disagreements.html`, gitignored):
114 rows before any rule, 26 of them not errors (citation numbers, running heads, counting
artefacts); of the 88 real ones Docling's side was wrong in 79 and Marker's in 19. Root causes
(Docling / Marker): layout 30 / 6, model input 30 / 0, recognition 15 / 11, our post-processing 4 / 2.
After the rules below, 68 rows remain, 29 of them equations. Decisive items: Docling reads the
MDPI paper's duplicated text layer twice (10 captions doubled), flattens exponents in tables
("10 - 5"), merges table rows (4 of 16 tables), and reads the introduction before the title on RSC,
Wiley and Beilstein pages; Marker's page OCR gets these right. Marker's failures are a caption bar
taken into the picture (2 cases) and an abstract beside a TOC graphic rendered as an image (1 case):
both repaired by OCR of the band (`parse_marker.py --bands`).

## Status

fixed / limit / open; checked by script, Claude Code or user.

| ID | Item | Problem | Status | Checked by | Evidence |
|---|---|---|---|---|---|
| M1 | Body | Marker drops the letters of private-use ligatures and the °, −, µ glyphs with the text layer | fixed: `force_ocr` | Claude Code, page | 10.1039_c7ta03257a, 2026-10-12 |
| M2 | Body | Reading order: Docling puts the introduction before the title/abstract on RSC, Wiley, Beilstein pages | fixed by using Marker's order | Claude Code, page | 10.1039_c7ta03257a p 2, 10.1002_adem.202201901 p 1, 10.3762_bjnano.5.25 p 1 |
| M3 | Body | "<001>" written "< 0.01 >" (Marker's math rendering of the angle brackets; the 2026-10-12 row said "001") | limit, flagged by body_flags (001 missing, 0.01 absent) | script (text layer vs output) | 10.1002_adem.202201901 p 10 |
| M4 | Figures | Caption bar inside the picture (BMC) | fixed: T1 band OCR | Claude Code, page | 10.1186_s11671-015-0872-9 Figures 1, 3 |
| M5 | Abstract | Abstract beside the TOC graphic rendered as an image (ACS) | fixed: T2 band OCR | Claude Code, page | 10.1021_acs.jpcc.9b08176 |
| M6 | Tables | Marker's TableGroup pairs a caption with the neighbouring table | fixed: position rule | Claude Code, page | 10.3390_separations11010024 Tables A1–A3 |
| M7 | Tables | Trailing zeros dropped by tabulate (0.10 → 0.1) in both tools | fixed: no number parsing | Claude Code on the crops (the 7 cells re-judged) | 7 cells in 5 tables, no other change |
| M8 | Tables | Structure (extra empty column, header shifted, column lost, rowspan misread), symbols misread (μ lost, O/0, Θ/θ, ξ/ζ, subscript case), arrow counts, one table drawn as an image | limit, flagged by the rule check: 27 of 28 wrong tables, 1 not checkable | Claude Code, page | 69 tables of 44 papers, 2026-10-13; ERRORS.md |
| M9 | Tables | Right tables flagged (footnotes in or just below the box, a box covering body text, the MDPI duplicate layer, a font encoding ν as "n") | limit: 7 false flags on 41 right tables | Claude Code, page | ERRORS.md |
| M10 | Tables | Text layer of symbol fonts read as letters or (cid:N) subset glyph codes | fixed: decoded per font family and per embedded subset, `glyph_codes.json` (13 families, 13 subsets, every code checked on a glyph crop); a code without a table makes the table "not checkable" | Claude Code, glyph crops | 12 papers, 2026-10-13 |
| M11 | Captions | A caption continued into the body paragraph below | fixed: no continuation past a sentence end into a block that starts a new sentence | Claude Code, page | 10.1021_acs.chemmater.1c03164 Figures 1, 3 |
| M12 | Figures | A manuscript with all figures after the captions: captions without an image | fixed: bound by page order when the counts match | Claude Code, page | 10.1116_1.5116136 Figures 1–5 |
| M13 | Abstract | OpenAlex fallback only for OCR-only blocks | fixed: fallback whenever a usable OpenAlex abstract exists and recall < 80 % or the abstract is empty | script | 10.1021_acs.langmuir.6b03119 |
| M14 | Body | OCR'd abstract text not written into document.md; table blocks drawn as an image not repaired | fixed: the band repair anchors the text in the markdown; T2 also for image-only Table blocks | script | 4 ACS papers, 10.1021_acsnano.5b03429 |
| M15 | Body | Numbers of the body changed, dropped or added by Marker (a decimal comma, a digit read as a letter, a dropped sentence, a hallucinated subscript, a lost minus sign, margin line numbers merged into the text) | limit, flagged: `body_flags` per paper by `body_check.py` (decoded text layer vs document.md, both directions; "not checkable" with a reason where it cannot read) | script; the known items judged by Claude Code on the page (2026-10-12/13), 1 new flag on the crop | 44 papers, 2026-10-13: 1,154 flags; 3 of 3 known errors caught, 0 of 41 known not-errors flagged; ERRORS.md |
| M16 | Body | Symbol-font glyphs of the text layer without a decoding (AdvOT private-use characters, AdvP4C4E74 cids, AdvPSMP10 letters) in body lines; rotated text; the MDPI duplicate layer | limit: those lines are "not checkable" with the reason and count in `body_check` | script | 2,726 undecoded lines, 72 garbled lines, 22,022 rotated characters in the 44 papers |
| E1 | Equations | Docling's enrichment crop (box + 18 %, 120 dpi) takes in neighbouring text; Beilstein boxes hold only the number | fixed: R1 tight crop at 216 dpi (18 fixed, 1 broken), R2 band box (12 of 19 fixed) | Claude Code, crops | 103 pairs, cf. ERRORS.md |
| E2 | Equations | Both tools misread some formulas | limit: `differ` pairs for review | Claude Code, crops (13 papers only) | 29 of 103 pairs differ on the 13 papers; the 31 papers' 80 differ pairs not judged |
| E3 | Equations | Marker re-recognition of its own equations on a 216-dpi crop | rejected: fixed 2, broke 13 | script + crops | not applied |
| I1 | Input | MDPI duplicated text layer (caption regions drawn twice in two fonts) | limit | Claude Code, text layer | 10.3390_separations11010024 only, of the 13 |
| D1 | Docling | Docling-stage rules (figure/table binding, abstract, running lines, glyph repairs) | removed on 2026-10-12: code, outputs and manifest columns deleted; `parse_docling.py` keeps `--formulas` and `--fetch-abstracts` | — | 25b9ea0 |

Rule: update the row in the same commit as any change that affects it.

## Environments

- `psed310`: Docling, pdfplumber, pypdfium2, tabulate. Runs `parse_docling.py` (`--formulas`, `--fetch-abstracts`), `structure_marker.py`, `merge.py`.
- `psed_marker`: Marker 2.0.0 only (llama.cpp backend, binary in `~/opt/llama.cpp/`). Runs `parse_marker.py`.
  Kept separate: Docling pins transformers <5 and huggingface_hub <1, Marker needs newer; pillow pins conflict.
- Marker output is not deterministic across runs (llama.cpp backend, no fixed seed or temperature): each paper is converted
  once and the result kept (`--redo` to overwrite); the 44 outputs are not reproducible bit for bit.
- `parse_docling.py --formulas` needs a GPU with about 6 GB free; set `CUDA_DEVICE_ORDER=PCI_BUS_ID` so that
  `CUDA_VISIBLE_DEVICES` matches nvidia-smi's numbering.

## Rules per item

### Marker conversion (`parse_marker.py`)
`force_ocr`: full-page OCR by surya-ocr-2, layout from the OCR pass; 63–174 s per paper on one A6000. Writes
`document.md` with its figure crops (`_page_P_<Type>_K.jpeg`) and `blocks.json` (block tree with page, bbox
from the top-left, html). Band-crop OCR after the conversion (or `--bands` on existing
output): T1, a Figure/Picture/Diagram block whose box holds a text-layer line starting with a caption
label while the page has no Caption block with that number → the band from that line to the block's bottom
is OCR'd and inserted as a Caption block; T2, a Text block that is only an image → OCR'd, its html and
markdown placeholder replaced, or the text placed after the preceding block when there is no placeholder; a Table
block that is only an image is OCR'd the same way (its cell texts go into the markdown as a paragraph). Records in
`bands.json`. 44 papers, 25 repairs in 20 papers: 2 captions and 4 abstracts recovered, 1 image table's texts, 11 author
lines and 7 "Check for updates" badges added as text, nothing lost; one abstract block returned no text
(10.1021_acs.langmuir.6b03119).

### Structure (`structure_marker.py`)
- Captions: a block whose text starts with Fig./Figure/Scheme/Table + number (letter prefix allowed) is a caption if
  Marker labels it Caption, the number is followed by ".", ":" or "|", or a Table caption's number is followed by a
  capitalised word (Text blocks count); it continues with the Text block directly below in the same column when the
  gap is at most 4 pt, unless the caption ends a sentence and the next block starts a new one (a body paragraph);
  a block that starts lowercase or with a panel letter continues the caption.
- Figures: bound by Marker's FigureGroup/PictureGroup, else the position rules (next caption on the page whose
  horizontal span overlaps the picture, else the previous one, else the next). A Figure/Picture/Diagram/ChemicalBlock
  without an image file is cropped from the page (`crop_page_<P-1>_<Type>_<K>.png`). A manuscript with its figures
  after all captions: the numbered captions without an image take the large loose pictures (80 pt or more on both
  sides) of the pages after the last caption, one page per caption, when the counts match.
- Tables: the nearest unused table caption on the same page (Marker's TableGroup ignored); html → markdown with the
  `<th>` rows merged into one header line (" / "), rowspans and colspans honoured, `<sup>` as `^`, tabulate without
  number parsing. Crop `table_<P-1>_<K>.png` (caption band above, 30 pt below). Rule check → `check`: ok | flag |
  not checkable, with `check_reasons` and `check_detail`. The text layer inside the box is decoded per font
  (`glyph_codes.json`): named characters of symbol-encoded fonts by a table per font family (AdvPi2 y → θ, AdvPSMP10
  g → η, AdvP80675 6 → ±, AdvP4C4E51 : → .), (cid:N) codes by a table per embedded subset (a cid is a glyph index of
  the subset: (cid:3) is − in the AIP subsets and × in an RSC one); every entry checked on a glyph crop. A glyph
  without a table, or a rotated table, makes the table not checkable (reason given). Flag reasons: (a) numeric
  tokens of the layer missing from or extra in the markdown (sign, decimals, exponents by font size; compared with
  and without thousands separators; a superscript number counts as present when it is anywhere in the markdown:
  a footnote marker) and the counts of ± ↑ ↓ ↗ ↘ ≤ ≥ ≈ ∼ ≪ ≫ ×; (b) letters of the layer the table lacks (LaTeX,
  Greek, operator names, sub/superscripts, math italics normalised); (c) header colspans vs body columns, empty
  trailing header, empty column, short last row, numbers just below the box on the table's columns; (d) fewer
  than 5 layer words; (e) no table cells. No exception: footnotes or a hidden duplicate layer inside the box also
  flag. 69 tables of 44 papers (2026-10-13): 27 of 28 wrong tables flagged, 0 missed, 7 right tables flagged,
  1 not checkable. A flagged table is read by a vision model at extract time; nothing here does.
- Equations: Equation blocks' `<math>` LaTeX with the number Marker kept, plus short standalone blocks (≤ 25 words)
  holding → or \rightarrow.
- Abstract: the Docling-stage rules on Marker's blocks (heading / "Abstract:" paragraph with its continuation,
  else the OpenAlex match on pages 1–2, else the widest page-1 item, else the longest early paragraph); the OpenAlex
  text replaces it when OpenAlex has 50 words or more and the extracted abstract is empty or has recall < 80 %.
- `document.md`: Marker's markdown without running lines; the original kept as `marker.md`.

### Body numbers (`body_check.py`, run by `merge.py`)
- Text layer: pdfplumber characters decoded per embedded font with `glyph_codes.json` (the table check's tables; the
  degree sign of AdvEls-ent5 and the prime of AdvP4C4E74 were added on 2026-10-13 from body crops). Characters outside
  the page area are dropped and a character drawn twice at a slightly different size on one baseline is read once
  (the MDPI hidden layer: 6,649 and 1,183 characters). Lines are read inside Marker's text blocks (Text, SectionHeader,
  Caption, ListItem, TextInlineMath, Footnote) by the baseline of the normal-size characters; citation and
  affiliation numbers, exponents and same-size LaTeX sub/superscripts join the nearest line, superscripts marked `^`;
  characters outside every block are read as segments split at 20-pt gaps.
- Excluded, with counts in `body_check.counts`: PageHeader/PageFooter/Figure/Picture/Diagram/Table/Form/Handwriting/
  Reference/Code/Equation boxes; everything from a References, Acknowledgements, Funding, Author contributions,
  Conflicts, Associated content, Supporting information or Data availability heading on (layer side, or a unit that
  matches an output paragraph after the first such heading in the second half of document.md); author/affiliation
  blocks, author lines (names with affiliation markers on pages 1–2) and furniture ("Published by", "Cite as", doi,
  licence: the line is cut there); running lines; units of fewer than 4 words; segments that hold only a number (page
  and margin line numbers). A line without a word of 4+ letters (a formula) is kept for the extra direction only.
- Not checkable, with reason and count: rotated characters, undecoded glyphs (the font and code are listed in
  `not_checkable_reasons`), units of fewer than 3 words, garbled lines (two lines drawn over each other: fewer than
  30 % of their words occur in the output), output sentences the layer lines do not cover (70 % of their words of 4+
  letters) and output paragraphs that a not-checkable unit also matches.
- Numbers: both sides normalised as the table check does; a subscript joins its base (H2O), a superscript stands alone
  (10^12 → 10, 12), a number with a unit glued to it counts as the number (514nm). Pure numbers are compared as
  multisets, both ways; a run that mixes letters and digits (H2S, MoS3.0, 40045TRS) by occurrence in the other side's
  text with spaces and markers removed. A unit goes to the document.md paragraph sharing the most word 3-grams (2, or 1
  for a unit under 6 tokens) together with the contiguous run of candidate paragraphs around it; an unmatched unit with
  a number is "line not found in the output".
- Flags: `body_flags[{page, kind, number, layer_line, output_sentence, layer_numbers, output_numbers, crop}]`, kinds
  "line not found in the output" / "number of the text layer missing from the output paragraph" / "number of the output
  paragraph absent from the text layer". 44 papers on 2026-10-13: 22,037 lines read, 18,891 checked, 1,154 flags (13 /
  163 / 978 by kind; 761 in 10.1021_acs.chemmater.9b05116, 393 in the other 43 papers, 10 papers without a flag).
  Against the page verdicts of 2026-10-12/13: 3 of 3 real body-number errors caught, "<001>" (written "< 0.01 >")
  flagged too, 0 of the 41 items judged not errors flagged. False flags fixed on the way were decoding or normalisation
  gaps only (the ° and ′ glyphs, `< 10^11` eaten as an html tag, "H_2 S" spacing, a space after a sign, a unit glued to
  a number, Greek letters in runs, the hidden MDPI layer). False flags that remain, seen in samples and left as they
  are: stacked sub- and superscripts written in another order (O₂⁺, E₂¹g), inline equations that Marker keeps in the
  paragraph while their Equation box is excluded on the layer side, a paragraph straddling a column break, enumeration
  numbers "(1)" of a split paragraph, and the residue of the MDPI duplicate layer (74 flags in that paper). Flags are
  not reviewed here; the extraction stage reads the crop.

### Equations (`parse_docling.py --formulas`, `merge.py`)
- Docling's layout gives the formula items; CodeFormula reads our crops: R1, the formula box without expansion at
  216 dpi; R2, a box of at most 25 pt width (only the printed number) → the band of its text column between the
  text items above and below. `equations.json`: page, bbox (bottom-left), LaTeX, printed number (from the LaTeX or
  the "(N)" word right of the formula), rule, crop box. 103 paired equations: R1 fixed 18 and broke 1 (10.1063_1.5028178
  eq 20); R2 fixed 12 of 19 Beilstein equations.
- `merge.py` pairs Docling's and Marker's equations on a page by box (IoU + vertical overlap ≥ 0.6), the rest by
  printed number, and marks each pair `agree` (equal after notation normalisation: \text{}, \left/\right,
  spacing, aligned environments, trailing number, \cdot/\times, braces) or `differ`; unpaired ones `docling only` /
  `marker only`. 74 of 103 agree. A `differ` pair is decided at extract time (a person or a vision model on the crop).

### Review of flags (not part of ingest)
A flagged table and a `differ` equation pair are resolved by an external vision-language model reading the crop,
as a pre-processing step of the extraction stage (planned). Ingest writes the flag, the reasons and the crop path.

### Docling stage (removed)
The earlier Docling rules of this stage (figure/table binding, abstract, running lines, glyph repairs; change log
2026-09-30 to 2026-10-12) were removed on 2026-10-12 with their outputs (`ingest/docling/<id>/` except
equations.json, `ingest/review/`) and the manifest columns `docling` and `abstract_review`. Their numbers in the
change log are historical.

## Change log
Newest first. One line per change: date, what changed, effect, commit.

- 2026-10-13 — Body-number flags: `body_check.py` (decoded text layer vs document.md per paragraph, both directions,
  "not checkable" with reasons) run by `merge.py` into `body_flags` / `body_check` of final structure.json; glyph table:
  AdvEls-ent5 "1" is the degree sign (the earlier entry said digit one), AdvP4C4E74 "0" the prime; docs state how each
  subset was checked, M7 re-judged on the crops, M3 corrected ("< 0.01 >"), Marker non-determinism stated. Effect:
  1,154 flags in the 44 papers, 3 of 3 known errors caught, 0 of 41 known not-errors flagged; tables unchanged (27 of
  28 wrong flagged, 7 false, 1 not checkable; the 3 RSC tables with the ent5 glyph unchanged, ok). — hash: see the follow-up line below

- 2026-10-13 — Table check rebuilt on a decoded text layer (`glyph_codes.json`: 13 symbol-font families, 13 embedded subsets, every
  code checked on a glyph crop; thousands separators; footnote numbers; symbol counts; "not checkable" for undecoded glyphs and
  rotated tables); band repair writes the OCR text into the markdown and covers image-only Table blocks; caption continuation stops
  at a body paragraph; figures-after-captions manuscripts bound by page order; OpenAlex abstract fallback on low recall; all 69
  tables of the 44 papers judged on the crop. Effect: 27 of 28 wrong tables flagged, 0 missed, 7 right tables flagged, 1 not
  checkable; 11 review_31 real errors fixed (4 abstracts into document.md, 2 captions, 5 figure images, 1 abstract), 0 broken;
  ERRORS.md and review_44.html rebuilt. — cf783e0, c2a45b2

- 2026-10-12 — Docling stage removed: `parse_docling.py` keeps `--formulas` and `--fetch-abstracts` only; `ingest/review/`, the
  Docling full-parse outputs (docling.json, document.md, structure.json, figures/, 132 MB over 44 papers) and the manifest
  columns `docling` and `abstract_review` deleted; Marker's `document_meta.json` and band crops deleted. Flag review assigned
  to the extraction stage (external VLM, planned). Effect: equations.json of 10.1063_1.5028178 unchanged on rerun. — 25b9ea0
- 2026-10-12 — Final ingest rules: Marker supplies body, abstract, figures, captions and tables; `parse_marker.py --bands`
  (T1/T2 band-crop OCR); `structure_marker.py` with tabulate number parsing off, a rule check and a crop per table;
  `parse_docling.py --formulas` with the R1/R2 crops and CodeFormula on them; new `merge.py` → `ingest/final/<id>/` with
  paired equations; `ERRORS.md`. Effect on the 13 papers: 2 captions and 1 abstract recovered; 16 tables with 11 fully
  right, 5 wrong all flagged, 3 right flagged; 103 equation pairs, 74 agree; disagreement rows with Docling 114 → 68. — 2d53705
- 2026-10-12 — `structure_marker.py` rules from parse_docling.py (Text-block captions, 4-pt caption continuation, table position rule instead of TableGroup, multi-row header merge with rowspans, PDF crops for image blocks without a file, arrow blocks as equations). Effect: disagreement rows 142 → 57, no row that was right turned wrong, 0 unchecked; Docling right 28, Marker right 28. — 0e2d59c
- 2026-10-12 — `parse_docling.py --formulas`: Docling with formula enrichment (CodeFormula) writes docling/<paper_id>/equations.json only (page, bbox, LaTeX, printed number from the LaTeX or from the PDF text right of the formula); no other Docling file touched. Effect on the 13 Marker papers: 103 formula items with LaTeX (Ylilammi 46 of 46 numbered right); 6 to 221 s per paper. — 1bb790d
- 2026-10-12 — `structure_marker.py`: structure.json from Marker's blocks in Docling's schema (captions bound by Marker's groups, else parse_docling.py's position rules; tables as markdown; equations as LaTeX with page and bbox; abstract by the copied rules; document.md without running lines, Marker's own markdown kept as marker.md). Effect: 13 papers; compared with Docling item by item. — 31ca1cb
- 2026-10-12 — Marker stage added: `parse_marker.py` (Marker 2.0.0, force_ocr, llama.cpp backend) writes ingest/marker/<paper_id>/ with document.md, images and blocks.json; manifest column `marker`. Effect: 13 papers converted (one per DOI prefix), 63–174 s each. — dbc2c43
- 2026-10-12 — Abstract fallback to the OpenAlex text when the abstract is OCR-only and recall is below 80% (`openalex`). Effect: 10.1039_c4nr05049e gets its full 157-word abstract, mark ok:09ab0660; nothing else changed — 9e87def
- 2026-10-12 — Abstract extraction reverted to 1ac60a6 (heading, OpenAlex match, layout, order); kept check-side only: hash-bound `abstract_review` marks, empty abstract always flagged, form check without a usable OpenAlex abstract, 50-word rule in the check. Running lines (10 words or fewer, 3+ pages, 4+ letters) dropped from document.md only. Effect: all 7 marks verified, abstracts and captions unchanged, running heads/footers gone from 7 papers, 0 flagged — b17bf29
- 2026-10-12 — Page-1 rule for the abstract, `abstract_review` marks bound to the abstract's hash, running heads/footers/stamps dropped from document.md and from the abstract's items. Effect: 262 lines dropped in 13 papers, no abstract changed, 1 flagged — 8970bb2
- 2026-10-12 — Abstract follow-up: OpenAlex abstracts under 50 words count as missing; --check-abstracts form check; manifest column `abstract_review`. Effect: 3 abstracts changed source; 0 flagged — b2b9fcb
- 2026-10-12 — Abstract check closed: 43 of 44 correct, 1 known limit (c4nr05049e). Effect: documented only — 01f85c6
- 2026-10-12 — Abstract: `abstract` and `abstract_source` in structure.json (heading, OpenAlex match, layout, order rules); `--fetch-abstracts` writes corpus/openalex_abstracts.json once; `--check-abstracts` scores against OpenAlex. Effect: 44 of 44 abstracts found, overlap median 98%, 1 flagged — 6c5cafa, 1ac60a6
- 2026-10-12 — Tables: markdown built from Docling's cell grid; column-header rows merged into one header line joined with " / ". Effect: 9 tables with 2–3 header rows changed, the 54 single-header tables byte-identical — 7107b50
- 2026-10-12 — Tables: caption binding uses Docling's table–caption link first, then the nearest unused same-page caption; letter-prefixed numbers and "Table N Capitalised" items accepted; glyph repairs on table markdown; crop per table. Effect: 11 → 59 of 63 tables numbered as expected. Known limits moved here from CLAUDE.md — 89f7357
- 2026-10-12 — CLAUDE.md records the Marker environment (psed_marker env, llama.cpp backend, `~/opt/llama.cpp/`). Effect: Marker 2.0.0 runs without touching psed310. — 2118b2a
- 2026-10-03 — Known limit added: a caption nested in its picture without a label keeps only text items of 4+ words. — 1350a2c
- 2026-10-03 — parse_docling.py split into a Docling step (docling.json, figures/pic_K.png) and a binding step; `--rebind` reruns binding and text repairs without Docling. Effect: rebinding takes seconds per paper. — bcf0d98
- 2026-10-01 — Broken-glyph known limit extended with private-use characters. — f977f3d
- 2026-10-01 — Glyph names `/uniXXXX` and `/uXXXXX` replaced (ligatures as plain letters); digit-like degree signs marked "[?]" from PDF font evidence. Effect: 2,400 glyph names in 14 papers, 170 digits in 4 papers. — ccce8fd
- 2026-10-01 — Chinese caption words (图, 表) accepted; two known limits added. — d86775f
- 2026-10-01 — Scope column in the manifest; parse_docling.py parses in-scope papers only. — 101ade3
- 2026-10-01 — Paths fixed after the move to ingest/. — 0caa45b
- 2026-10-01 — Docling stage moved from corpus/ to psed_v2/ingest/. — 82896bd
- 2026-10-01 — parse_docling.py empties a paper's figures/ before parsing it. — ec3983f
- 2026-10-01 — CLAUDE.md records the Docling stage's known limits (11 bullets). — a120f36
- 2026-10-01 — Picture binding refinements: pictures outside the page area and repeated decoration images ignored; the next-page rule only for a picture after the last text item; previous-else-next caption fallback. — 70d98ab
- 2026-10-01 — Pictures bound by caption position; captions nested in pictures seen; heading rule dropped. Effect: 5 of the 10 failing papers pass. — 5918542
- 2026-09-30 — Own caption binding replaces Docling's for pictures and tables, in reading order. Effect: first bound structure.json. — 647add1
- 2026-09-30 — docling_parse.py renamed parse_docling.py. — ee51eca
- 2026-09-30 — v1's Docling parse stage ported (corpus/docling_parse.py), manifest column `docling`; run on one paper. Effect: first ingest output. — cc5e59d
