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
psed310 env:      merge.py --all                        ingest/final/<id>/ (Marker items + paired equations; line_numbers.py removes
                                                        margin line numbers, body_check.py writes body_flags, body_repair.py repairs
                                                        document.md and the check runs again)
```

| Item | Tool | How | Output in `final/<id>/structure.json` | Numbers (13 or 44 papers, as each cell says) |
| --- | --- | --- | --- | --- |
| DOI, title, authors, year, journal | `corpus/manifest.csv` (OpenAlex) | never extracted from the PDF | — | — |
| Body text | Marker | `document.md` without running lines (10 words or fewer, identical on 3+ pages, 4+ letters); band-OCR'd blocks written into it; margin line numbers of a line-numbered manuscript removed (`line_numbers.py`); body-number check (`body_check.py`: decoded text layer vs document.md per paragraph, both directions); two countermeasures on born-digital pages (`body_repair.py`: a number replaced from the text layer, a dropped line restored) | `document.md`; `body_flags` (one entry per mismatch: page, kind, number, text-layer line, output sentence, numbers on each side, line box and crop; entries of kind "not checkable" with the reason, line count, box and crop), `body_check` (counts, not-checkable reasons, line-number counts), `body_repairs` | 44 papers, 2026-10-13. 23,935 body lines read, 23,779 checked (99 %; median 100 % per paper, min 82 %); 156 lines not checkable (67 in units under 4 words, 83 garbled, 4 in units too short to locate, 2 with an undecoded glyph; 484 before the lookup of short units and garbled lines near the previous match recovered 325 units), 22,022 rotated characters; on the output side 55 sentences the layer does not cover and 38 paragraphs blocked by an undecoded glyph in an equation line. Every body flag of the 44 papers judged by Claude Code on the line crop (415 flag keys over the passes: 128 real, 287 not errors), see ERRORS.md: 44 distinct real errors of Marker's body text in the 44 papers (11 in the 13 papers, 33 in the 31), 1.9 per 1,000 checked lines, found through numbers only. Final output: 238 flags (12 lines not found, 120 text-layer numbers missing, 102 output numbers absent, 4 letter differences), 12 papers without a flag; 77 of the 234 judged flags are real, 157 not (precision 33 %), the 4 letter flags not yet judged; 268 flags of kind "not checkable" cover every unchecked line and every output unit whose numbers are not compared: layer side 67 lines of units under 4 words, 83 garbled lines, 20 equation lines with undecoded delimiter pieces, 4 units too short, 1 unit with undecoded pieces; output side 55 sentences not covered by the layer, 38 paragraphs blocked by an undecoded glyph. Countermeasures: 1,044 margin numbers removed from 10.1021_acs.chemmater.9b05116 (no other paper changes); 12 repair records (5 numbers replaced, 7 dropped lines restored; each repair takes a distinct position, and a repair whose sentence stays flagged after the recheck is undone: 0 undone): 8 distinct errors corrected, 1 partly (the Figure 1 caption of 10.1186_s11671-015-0872-9: 2 of 3 lines restored, the middle line stays flagged), each viewed on its crop against the page. All 44 real errors stay detected: 8 corrected, 1 partly, 35 flagged. A number flag crops the line when it can be pinned down, else the whole paragraph block (132 of 238). Handling: flag → review by the external vision model at the extraction stage (crop, output sentence, text-layer line), like flagged tables and differ equations; the judgements are the answer set `ingest/answers/body_flags.json` |
| Abstract | Marker | the rules copied from the Docling stage (heading / "Abstract:" paragraph, OpenAlex match on pages 1–2, layout, order) on Marker's blocks; the OpenAlex text when it has 50+ words and the extracted abstract is empty or has recall < 80 % against it | `abstract`, `abstract_source` | 44 of 44 right: 23 heading, 20 openalex_match, 1 openalex (10.1021_acs.langmuir.6b03119, whose abstract block is an image the band OCR could not read). How checked: the 13 papers on the page; of the 31, the 26 with a usable OpenAlex abstract (50+ words) by word recall against it (all 26 ≥ 90 %, script), the 5 without one (10.1016_j.ijpharm.2017.04.031, 10.1016_j.mee.2018.01.027, 10.1016_j.mee.2018.01.033, 10.1039_c5ta00205b, 10.1039_d4nr03749a) on the page on 2026-10-13 |
| Figures + captions | Marker | Marker's FigureGroup/PictureGroup binding, else the position rules; Text blocks that start with a caption label count; T1 band OCR for captions drawn inside the picture; captions do not continue into a body paragraph; figures placed after all captions bound by page order | `captions` with `images` | 44 papers: every numbered caption has its image and text. How checked: the 13 papers on the page; the 31 by script (caption numbers, images, text against the text layer), the flagged items viewed on the page; 2 figures split into panel blocks keep one panel unbound (ERRORS.md) |
| Tables + captions | Marker | Table html → github markdown (`<th>` rows merged with " / ", rowspans/colspans honoured, superscripts as `^`, trailing zeros kept); caption = nearest unused table caption on the page (position, not Marker's TableGroup); rule check against the decoded text layer (`glyph_codes.json`) + crop | `captions` with `table`, `bbox`, `check`, `check_reasons`, `check_detail`, `crop` | 69 tables in 28 papers (page): 41 right, 28 wrong; the check flags 27 of the 28, misses 0, flags 7 right tables, 1 wrong table not checkable (rotated) |
| Equations | Docling + Marker | Docling's layout gives the formula boxes, CodeFormula reads our crops (R1 tight box at 216 dpi; R2 band box when the box is ≤ 25 pt wide); Marker's `<math>` blocks; pairs by page and box, `agree` / `differ` | `equations[{page, bbox, number, docling, marker, status}]` | 44 papers: 321 entries, 197 agree, 109 differ, 15 one tool only (script counts). Judged on the crop only for the 13 papers' 29 differ pairs of their 103 pairs (74 agree): Marker right 14, Docling right 7, both wrong 3, equivalent forms 5; the 31 papers' equations were not judged on the page |

Paths: `ingest/marker/<id>/` (blocks.json, marker.md, document.md, images, structure.json, table crops,
bands.json), `ingest/docling/<id>/equations.json`, `ingest/final/<id>/` (all gitignored; the body-flag crops are
`final/<id>/figures/body_p<P>_<k>.png`). `ingest/answers/` (tracked): the answer set, Claude Code's page judgements
with ids and verdicts only (tables.json, equations.json, body_flags.json). `ingest/reports/glyph_evidence/` (gitignored):
the crop sheets and the census behind the glyph entries of 2026-10-13. Progress:
manifest column `marker` (ok | failed | blank); `--formulas` and `merge.py` write no column.
`corpus/openalex_abstracts.json` (gitignored): OpenAlex abstracts, fetched once with
`parse_docling.py --fetch-abstracts` (the only network call in ingest), used by the abstract rule and
its fallback.

Review of what ingest flags is not part of ingest: a flagged table (`check: flag`), an equation pair with
`status: differ` and a body flag (`body_flags`) are resolved by an external vision-language model at the
start of the extraction stage (planned), given the crop; for a body flag also the output sentence and the
decoded text-layer line. Ingest only writes the flags, the reasons and the crops. Claude Code's page
judgements are kept apart as the reference for that step, in `ingest/answers/` (tracked: ids and verdicts
only, no paper text): `tables.json` (69 tables), `equations.json` (103 pairs of the 13 papers),
`body_flags.json` (415 judged body flags); the review step is scored against them before it is used.

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
| M15 | Body | Numbers of the body changed, dropped or added by Marker: sentences, paragraphs and captions dropped (10 of 41 errors), citation numbers changed, dropped or fused (7), digits changed (4), letter/digit confusions t→4, I→1, 1→I, S→2, 5→S, 0→o (4), lookalike letters v→ν, p→ρ (5), subscript digits dropped (3), text added (3), a decimal point inserted or replaced by a comma (2), an exponent sign dropped (1), a caption label merged into a paragraph (1), margin line numbers merged (1 paper) | limit, flagged: `body_flags` by `body_check.py`; 12 repaired by `body_repair.py` (ERRORS.md lists each error, its cause and whether a countermeasure fixes it) | Claude Code on the line crops: every flag of the 44 papers (388 flag keys over the passes) | 41 distinct real errors, 2026-10-13; the 3 known errors of 2026-10-12/13 among them |
| M16 | Body | Symbol-font glyphs and (cid:N) subset codes of the text layer without a decoding in body lines; rotated text; the MDPI duplicate layer | limit: those lines are "not checkable" with the reason and count in `body_check` and a flag each; 27 glyph entries added on 2026-10-13 from body crops, then in pass 2 every remaining undecoded body glyph (150 font-subset/code keys) viewed on crops (`reports/glyph_evidence/`): 111 entries added, 22 pieces of multi-part delimiters in 5 papers left undecoded with the reason | Claude Code, glyph crops | 2 undecoded lines (1,075 before pass 2, 2,726 before the first additions), 83 garbled lines (98 before the lookup near the previous match), 22,022 rotated characters in the 44 papers; coverage per paper in ERRORS.md |
| M17 | Body | Margin line numbers of a line-numbered manuscript merged into the text by Marker (every line; 761 numbers flagged on 2026-10-13) | fixed: `line_numbers.py` finds the margin column in the text layer and removes the numbers at line breaks, alone on a line, or in runs; fires on 10.1021_acs.chemmater.9b05116 only (48 pages, 1,044 removed, 5 real numbers kept), no other document.md changes | script + Claude Code on crops (leftovers judged) | 10.1021_acs.chemmater.9b05116; 5 leftovers at breaks where the same bare number stands in the adjacent line |
| M18 | Body | Countermeasures for Marker's body errors | fixed where a rule applies: `body_repair.py` replaces a number from the text layer when one missing and one absent number pair up in a paragraph (same letters, at most two characters apart) and restores a dropped line of a Text/Caption block (8+ words, vocabulary 70 %, no undecoded glyph); born-digital pages only; each repair takes a distinct position in the output (the first run wrote g/cm^--3 by applying two records to one token, found on 2026-10-13); after the repairs the check runs again and a repair whose sentence still carries a flag is undone (`body_repairs_undone`); recorded in `body_repairs` | Claude Code on the crops: every repair viewed against the page; three stricter variants rejected on the way (sentence-level pairing broke 1, letter differences broke 1, ambiguous pairs broke 1) | 12 repair records in 8 papers: 8 distinct errors corrected, 1 partly (2 of 3 caption lines), 0 undone; errors without a rule (letters, lookalikes, hallucinated subscripts, dropped paragraphs matched elsewhere) stay flagged |
| M19 | Body | A page box that does not start at (0, 0) (10.1116_1.5116136, media box from −92): Marker's boxes are 0-based, pdfplumber keeps the PDF origin | fixed: boxes shifted by the page box origin | script | 10.1116_1.5116136 (196 lines checked instead of 2) |
| M20 | Body | A cover page whose "Reference" heading, or a unit matching a paragraph after the References heading, stopped the check on page 1 | fixed: both stops apply in the second half of a paper only | script | 10.1116_1.5116136, 10.1116_6.0002804, 10.1039_d1cp04758b (866 lines regained) |
| M21 | Body | Lines the check cannot compare were only counted; units under 4 words were "excluded" without a flag; output units whose numbers are not compared were only counted | fixed: a flag of kind "not checkable" (reason, crop) per unit with an undecoded glyph, per line of a unit under 4 words, per garbled line, per unit too short to locate, per equation or weak line with an undecoded glyph, and on the output side per sentence the layer does not cover, per paragraph blocked by an undecoded glyph in an equation or neighbour line and per paragraph a not-checkable unit also matches (output text, the numbers left unchecked, a crop of the Marker block); every unchecked layer line and every such output unit carries one (checked per paper) | script; the flags listed in review_body.html (the under-4-word lines in their own section by block type) | 268 flags: layer side 175 (67 lines of units under 4 words: SectionHeader 24, Text 5, outside the blocks 38, Caption 0; 7 with a digit; 83 garbled, 20 equation lines, 4 too short, 1 unit), output side 93 (55 sentences, 38 paragraphs), 2026-10-13 |
| M22 | Body | The "+" of the AdvPi1 symbol font draws ±; read as + and joined to the number it gave four false flags | fixed: family entry with crops as evidence | Claude Code, glyph crops | 10.1116_6.0001094 p14 |
| M23 | Bands | A later `--bands` run overwrote bands.json; 9 records rebuilt from the `band_ocr` mark had no crop | fixed: records merged per (trigger, block) (`parse_marker.py`, tested with a stub converter on a scratch copy); the 9 crops rendered again from the PDF and the band box, each record's text confirmed in document.md or the captions of structure.json | script | 6 papers, 2026-10-13 |
| M24 | Body | Short units (under 4 words, or fewer than 3 tokens: headings, labels, fragments) and lines the vocabulary test calls garbled (a spaceless or doubled layer, a typo) were not checkable | fixed: looked up in the output near the previous match (3 paragraphs before to 10 after) after normalisation (case, whitespace, markup, LaTeX commands, hyphenation), with and without spaces, garbled lines also by similarity (85 % of the characters in matching runs; letters compared, flag "letters of the text layer differ from the output"); found, the unit is checked as a normal unit; else not checkable with the reason (copy elsewhere in the output, doubled characters, nearest similarity) | script; every recovered unit listed with its matched output text in review_body.html | 324 units checked this way (303 short units: 292 exact, 11 without spaces; 21 garbled lines: 11 without spaces, 10 by similarity); units under 4 words 380 → 67, garbled lines 98 → 83; 4 letter flags (one the ρ_B caption of 10.1039_d0cp03358h p9) |
| M25 | Body | A number flag cropped the first line holding the number, the wrong line when the number occurs several times in the paragraph or the differing line cannot be pinned down (10.1021_acs.chemmater.2c01154 p3, the "1" of E_2^1g → E_1g) | fixed: the whole paragraph block is cropped unless exactly one layer line holds a missing number or the output sentence of an absent number lies in one line (`crop_scope`) | script | 132 of 238 flags crop the paragraph, 106 the line; no flag removed |
| M26 | Body | A subscript glyph just below a line's baseline joined the next line as a superscript (10.1021_acs.langmuir.6b03119 p2, "diameter^2 of ∼110 nm" for TiO_2) | tried and reverted on 2026-10-13: a rule attaching such a glyph to the line above (bottom within half the font size below its baseline, top above it, in a gap of its text) moved superscript dashes, minus signs and the subscript of TiCl_4 to the wrong line and gave 7 false flags (10.1116_6.0002804 p2 "5660"/56/60, 10.1021_acs.jpcc.9b08176 p2 "4", 10.3390_separations11010024 p7 "−4"/4/TiCl4); a check must not alter its own reference, so the line assembly of e5cb97c stands and the 15 flags the rule had removed (subscripts read as superscripts of the next line, all judged not errors) go to the VLM review | script, ablation | 15 flags, 6 papers |
| M27 | Body | The superscript citation of 10.1116_6.0001679 p2 reads "films.^1.2" in the layer where Marker wrote "1,2" | not a glyph: the page prints a period there (crop at 900 dpi, `reports/glyph_evidence/citation_period_6.0001679.png`; the true commas of the same font, "3,4" and "13,14", show their tails), the layer is right; no table entry | Claude Code, glyph crops | 1 line |
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
`bands.json`, one per (trigger, block) with the band crop `band_<trigger>_<block>.png` beside it: a later `--bands` run
adds records for new triggers and replaces the record of a block it OCRs again; earlier records are kept (tested on a
scratch copy of 10.1038_s41467-022-35428-6 with a stub converter on 2026-10-13: the duplicate pair of one block
collapsed to one record, the re-OCR'd block updated in place, the other records kept). 44 papers, 25 repairs in 20
papers: 2 captions and 4 abstracts recovered, 1 image table's texts, 11 author lines and 7 "Check for updates" badges
added as text, nothing lost; one abstract block returned no text (10.1021_acs.langmuir.6b03119). The 9 records rebuilt
from the `band_ocr` mark after the first run (which overwrote bands.json) had no crop; on 2026-10-13 each record's text
was confirmed in document.md (the two T1 captions in `captions` of structure.json; one of them also restored into
document.md by `body_repair.py`) and the crop rendered again from the PDF page and the record's band (no OCR rerun).

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

### Line numbers (`line_numbers.py`, run by `merge.py`)
A page carries margin line numbers when at least 8 bare integers stand at one x outside the text column (the 10th–90th
percentile x-span of the first and last letters of the text lines, by 3 pt or more), increase down the page (70 % of
the steps +1) and are at least as many as 70 % of the page's text lines; a paper is line-numbered when 3+ pages are.
Then a bare integer of the sequence is removed from document.md where the two words before it end a text line and the
two words after it start the next one (a line break; a word hyphenated across it is joined), unless the same bare
number occurs in those lines; numbers alone on a markdown line and runs of 3+ consecutive integers are removed too.
44 papers: fires on 10.1021_acs.chemmater.9b05116 only (48 pages, 1,044 removed, 5 kept); the 43 other document.md
files are byte-identical with and without the rule (checked 2026-10-13).

### Body numbers (`body_check.py`, run by `merge.py`)
- Text layer: pdfplumber characters decoded per embedded font with `glyph_codes.json` (198 entries: 19 families, 43
  subsets; 27 added from body crops on 2026-10-13, 111 more in pass 2 after every remaining undecoded body glyph was
  viewed on crops, `reports/glyph_evidence/`; 22 delimiter pieces listed under "undecoded" with the reason). Dropped or read once: characters outside the page box, a
  character drawn twice at a slightly different size on one baseline, a line printed twice on a page (the MDPI hidden
  layer). Lines are read inside Marker's text blocks (Text, SectionHeader, Caption, ListItem, TextInlineMath,
  Footnote; boxes shifted by the page box origin) by the baseline of the normal-size characters; small characters join
  the line whose baseline and size span they overlap (superscripts marked `^`), same-size LaTeX sub/superscripts join
  the nearest line, stacked indices are read subscript first (O_2^+), a word space is a gap above 13 % of the line's
  font size; an Equation box's lines join the text unit before it for the extra direction; characters outside every
  block are segments split at 20-pt gaps.
- Excluded, with counts in `body_check.counts`: PageHeader/PageFooter/Figure/Picture/Diagram/Table/Form/Handwriting/
  Reference/Code boxes; everything from a References, Acknowledgements, Funding, Author contributions, Conflicts,
  Associated content, Supporting information or Data availability heading on (layer side, or a unit matching an output
  paragraph after the first such heading in the second half of document.md; both in the second half of the paper
  only); author/affiliation blocks (keywords, addresses, dates), author lines (names with affiliation markers, pages
  1–2), furniture ("Published by", "Cite as", doi, URL, ORCID, licence, article id); running lines (page headers
  counted); segments holding only a number; the page abstract when the abstract comes from
  OpenAlex. On the output side URLs, DOIs, received/accepted/published dates, ORCID ids, "Citation:" lines and
  markdown table rows are removed first. A line without a word of 4+ letters (a formula) counts for the extra
  direction only.
- Not checkable, with reason and count: rotated characters, undecoded glyphs (font and code in
  `not_checkable_reasons`), units under 4 words (headings, labels, fragments: nothing to locate in the output), units
  under 3 words, garbled lines (two lines drawn over each other), output sentences the
  layer lines do not cover (70 % of their words of 4+ letters), paragraphs a not-checkable unit also matches or whose
  equation lines hold an undecoded glyph. Each line-level case is also a flag of kind "not checkable" (reason, line
  count, crop): one per unit with an undecoded glyph, per line of a unit under 4 words, per garbled line, per unit too
  short, per equation or weak line with an undecoded glyph; counted apart from the number flags ("not-checkable
  flags"). Every line counted in `lines` is either checked or covered by such a flag (44 of 44 papers, 2026-10-13).
- Numbers: both sides normalised as the table check does; a subscript joins its base (H2O), a superscript stands alone
  (10^12 → 10, 12), a number with a unit or a lowercase word glued to it counts as the number (514nm, 30μm, 4seconds),
  a comma run is a list in the plain variant and a thousands number in the other, the letter x between digits and 10
  is ×, Greek letters are letters of a run. Pure numbers (signed after a space or bracket, not after ° or %) are
  compared as multisets in both variants; mixed runs (H2S, MoS3.0, 40045TRS) by occurrence in the other side's text
  with spaces and markers removed. Display math and equation-like inline math are the equation check's domain (not
  required in the layer).
- Matching: a unit goes to the paragraph sharing the most word 3-grams (markers removed; at least a fifth of the
  unit's 3-grams, 2 at least; ties to the first paragraph after the last match), with the contiguous run of candidate
  paragraphs around it; overlapping runs form one group. Missing numbers: one flag each, unless the group gathers
  several units or repeated text and the number occurs in the paragraphs and within 3 paragraphs (a count mismatch),
  or the group's layer text is repeated (presence only). Absent numbers: one flag each, for covered output sentences
  only, with the neighbouring units' lines counting for the layer. An unmatched unit with a number is "line not found
  in the output".
- Measurement fixes of 2026-10-13, measured on the 44 papers with `BODY_CHECK_DISABLE` (ablation switch): 1,154 flags
  → 458 after the line-number rule → 431 with the stacked sub/superscript order → 430 with the Equation boxes joined →
  415 with the neighbouring units → 415 with duplicate lines read once → 423 with the 27 glyphs (more lines checked) →
  306 with markdown table rows, near-duplicate lines, running heads, address lines and equation glyphs handled → 268
  with the comma-list, author-line, date and DOI rules → 216 with the stricter matching, repeated-text presence rule
  and tokeniser fixes → 246 after the two stops were limited to the second half (three papers regained) → 224 final,
  after the page-box shift, × typed as x, and the 12 repairs.
- Judgement (Claude Code, every flag on its line crop, 2026-10-13): 415 flag keys over the passes, 128 real (44
  distinct errors), 287 not errors; of the 238 final flags 77 are real, 157 not (precision 33 % of the 234 judged), the 4 letter flags are new (not yet judged; listed with crops in review_body.html). Pass 2 (glyph table
  extended: 2 lines not checkable instead of 1,075; 23,456 of 23,936 lines checked instead of 22,386) raised 28 new
  flags, 9 real (3 distinct errors not seen before: a citation list changed, a footnote mark a → 2, p_I → p_1) and 19
  not; 4 of the not-errors vanished with the AdvPi1 ± entry, no other flag vanished. Remaining not-error causes: lines
  of one paragraph or caption in other units or in a figure box (35), equations and formulas kept in the paragraph
  by Marker (17 + 5), undecoded or garbled glyphs (16), the MDPI duplicate layer (14), layer tokenisation of
  subscripts, stacked indices, gaps and line breaks (15 + 5), furniture (7), table footnotes (4), count mismatches
  (2 + 2), other (12 + 2). Real errors by cause: c recognition 34, a layout 9, d our post-processing 1 (the margin
  numbers, now removed).

### Countermeasures (`body_repair.py`, run by `merge.py`)
On born-digital pages (embedded fonts, no OCR font, no full-page image): R1 a number of the output is replaced by the
text layer's when, in one paragraph, a missing layer number and an absent output number pair up unambiguously (same
letters, at most two characters and one in length apart, the layer token not glued to a minus sign); R2 a text-layer
line of a Text, Caption or TextInlineMath block that no output paragraph contains is inserted after the paragraph the
previous unit matched, marked "[restored from the text layer]" (8+ words, 70 % of its words in the document's
vocabulary, no undecoded glyph, no reaction arrow). Each repair takes one distinct position in the output: a pair that
occurs n times goes to the first n occurrences of the token, and a span already repaired is never matched again (the
first run had applied two records to one token and written g/cm^--3). After the repairs the check runs again on the
repaired text; a repair whose sentence still carries a number flag (R1), or whose restored line is flagged again (R2),
is undone and recorded under `body_repairs_undone` with the remaining flag. 44 papers, 2026-10-13: 12 repair records
(5 R1: 0.01 → 001, 3d_3/2 → 3d_5/2, g/cm^3 → g/cm^-3 at both occurrences, ^43 → ^4; 7 R2: 5 dropped sentences, a
Table 2 caption, 2 of the 3 lines of a Figure 1 caption), 0 undone, each viewed on its crop against the page: 8 distinct
errors corrected, 1 partly (the Figure 1 caption's middle line stays missing and flagged). Variants rejected during the test: pairing per
sentence (replaced a correct 55 by 155), pairs that differ in letters (turned E_1g into E2), ambiguous pairs (turned
^12 into ^1 where ^1,2 was right). Errors without a rule stay flagged (ERRORS.md).

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
A flagged table, a `differ` equation pair and a body flag are resolved by an external vision-language model at the
start of the extraction stage (planned): it reads the crop, and for a body flag the output sentence and the decoded
text-layer line, and decides whether the output is right, what the right value is, or that the item is a measurement
artefact. Ingest writes the flag, the reasons, the tokens and the crop path; `body_repair.py` fixes only what a rule
can fix without that review. The answer set in `ingest/answers/` (Claude Code's judgements of 2026-10-12/13: 69
tables, 103 equation pairs, 415 body flags; ids and verdicts only) scores the review step before it is used: a review
that disagrees with the answer set on more than a few items is not switched on.

### Docling stage (removed)
The earlier Docling rules of this stage (figure/table binding, abstract, running lines, glyph repairs; change log
2026-09-30 to 2026-10-12) were removed on 2026-10-12 with their outputs (`ingest/docling/<id>/` except
equations.json, `ingest/review/`) and the manifest columns `docling` and `abstract_review`. Their numbers in the
change log are historical.

## Change log
Newest first. One line per change: date, what changed, effect, commit.

- 2026-10-13 — The subscript attachment rule of b4306e9 reverted (`body_check.py` `_lines_of` as in e5cb97c): it moved
  superscript dashes and minus signs and the subscript of TiCl_4 to the wrong line and gave 7 false flags; a check must
  not alter its own reference (M26). Effect: the 7 flags gone, the 15 flags the rule had removed back (all judged not
  errors, for the VLM review); 238 flags (77 real, 157 not, 4 unjudged letter flags), lines checked 23,779 of 23,935,
  not checkable 156 with a flag each, identities hold; reports rebuilt. — f94e9f0 (this line's hash: the next commit)

- 2026-10-13 — `body_check.py`: short units and garbled lines looked up near the previous match (normalised, with and
  without spaces, by similarity with a letter comparison) and checked when found (324 units); output-side "not checkable"
  flags for sentences the layer does not cover and paragraphs blocked by an equation glyph (93, with block crops);
  paragraph crops when the differing line cannot be pinned down (129 flags); subscripts just below a baseline join their
  line (15 flag keys removed, 7 added); the "1.2" citation of 10.1116_6.0001679 is a printed period, no glyph entry.
  Effect: lines checked 23,452 → 23,775 of 23,931, not checkable 484 → 156 (every one flagged), flags 244 → 230 (11 new,
  unjudged); regression clean; reports rebuilt (papers.html 64 MB, review_body.html 38 MB). — b4306e9 (this line's hash: the next commit)

- 2026-10-13 — `body_repair.py`: one distinct position per repair and a recheck that undoes a repair whose sentence stays
  flagged (the first run had written g/cm^--3 in 10.1021_acs.jpcc.5c06502 and left the second g/cm^3); `body_check.py`:
  lines of units under 4 words are not checkable with a flag each (380), so every unchecked line carries a flag; docs
  corrected (distinct errors corrected: 8, partly 1; the "Text out of order" row is flagged). Effect: both g/cm^-3 right,
  4 flags gone (244 number flags, 77 real), 503 not-checkable flags, lines checked 23,452 of 23,936; 0 repairs undone;
  reports rebuilt (papers.html 51 MB, review_body.html with the under-4-word section). — e5cb97c (this line's hash: the next commit)

- 2026-10-13 — Glyph table pass 2: every undecoded body glyph of the 44 papers viewed on crops (150 keys; 111 entries
  added, 22 delimiter pieces listed undecoded with the reason, AdvPi1 + = ±); `body_check.py` writes flags of kind
  "not checkable" (reason, line crop) for the lines it cannot compare; 28 new flags judged (9 real, 3 new distinct
  errors; answer set 415 keys); `parse_marker.py` merges bands.json records per block (tested), the 9 band crops
  regenerated. Effect: body lines not checkable for undecoded glyphs 1,075 → 2, lines checked 22,386 → 23,456 of
  23,936, flags 224 → 248 (none vanished), 123 not-checkable flags; tables unchanged (34 ok, 34 flag, 1 not
  checkable); reports papers.html 49 MB and review_body.html 11 MB rebuilt. — fdbd9f5 (this line's hash: the next commit)

- 2026-10-13 — Answer set `ingest/answers/` (tables 69, equation pairs 103, body flags 388: ids and verdicts of Claude Code's
  page judgements, no paper text); body flags go to the same review step as flagged tables and differ equations (external
  vision model at the extraction stage), scored against the answer set first; docs and CLAUDE.md updated; the user's plan
  committed. Effect: documentation and data only, no pipeline output changed. — f35fa71 (this line's hash: the next commit)

- 2026-10-13 — Body text verification: `line_numbers.py` (margin line numbers removed, 1 paper), `body_check.py` measurement
  fixes (stacked indices, equation boxes, neighbouring units, duplicate lines, table rows, furniture both sides, author lines,
  comma lists, stricter matching with a reading-order tie-break, repeated-text presence, page-box origin, stops in the second
  half only), 27 glyphs added, `body_repair.py` (a number replaced from the text layer, a dropped line restored; 12 repairs,
  0 broken); every body flag of the 44 papers judged on its crop (41 distinct real errors), `reports/review_body.html`.
  Effect: body flags 1,154 → 224, precision 32 %, coverage median 97 % of body lines; tables unchanged (27 of 28 wrong
  flagged, 7 false, 1 not checkable); all page verdicts hold (the 3 known errors flagged or repaired, 0 of 41 known
  not-errors flagged, 41 of 41 judged errors still detected). — fa7e735 (this line's hash: the next commit)

- 2026-10-13 — Body-number flags: `body_check.py` (decoded text layer vs document.md per paragraph, both directions,
  "not checkable" with reasons) run by `merge.py` into `body_flags` / `body_check` of final structure.json; glyph table:
  AdvEls-ent5 "1" is the degree sign (the earlier entry said digit one), AdvP4C4E74 "0" the prime; docs state how each
  subset was checked, M7 re-judged on the crops, M3 corrected ("< 0.01 >"), Marker non-determinism stated. Effect:
  1,154 flags in the 44 papers, 3 of 3 known errors caught, 0 of 41 known not-errors flagged; tables unchanged (27 of
  28 wrong flagged, 7 false, 1 not checkable; the 3 RSC tables with the ent5 glyph unchanged, ok). — e69310f (this line's hash: the next commit)

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
