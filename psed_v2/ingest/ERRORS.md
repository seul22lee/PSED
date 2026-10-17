# Ingest: errors and known limits

Scope: the 58 in-scope papers with a PDF (manifest `in_scope` = yes). Guyon 2004 (10.1016_j.cattod.2003.11.022) is ingested but excluded
from the scope and not judged; its numbers stand on their own line in `NUMBERS.md` and count nowhere below.

What is wrong in the final output (`ingest/final/<paper_id>/`) of the 58 papers, judged on the PDF pages and crops by Claude Code
(the verdicts are the answer set `ingest/answers/`), with the counts of `ingest/NUMBERS.md`, and what the checks cannot see.
Handling: **flag → review** = the item carries a flag for the review at the start of the extraction stage; **repaired** = corrected by
`body_repair.py`; **known limit** = nothing flags it and the knowledge base must tolerate it.

## Body text (Marker): 59 distinct real errors in 30,516 checked lines (1.9 per 1,000)

| Error class | Count | Papers (page) | Handling |
|---|---|---|---|
| A sentence, paragraph, caption or reference block dropped (a line or paragraph, a figure caption, the page-bottom references of an ACS page) | 12 | 10.1002_adem.202201901 p 8; 10.1002_cvde.200390005 p 4 (the sentence 'Writing this result in terms of the aspect ratio ...' between two equations); 10.1021_acs.chemmater.1c03164 p 10; 10.1021_acs.chemmater.9b05116 p 22, p 33; 10.1021_acs.jpcc.5c06502 p 6; 10.1021_cm0303080 p 2 (page-bottom footnote references (28)-(30), (35)-(37) of p2 dropped); 10.1039_d0cp03358h p 8; 10.1039_d4cp00131a p 8; 10.1063_1.5028178 p 6; 10.1186_s11671-015-0872-9 p 3 (the Figure 1 caption), p 4 | 8 lines restored by R2: 4 errors whole (acs.chemmater.1c03164 p 10; acs.chemmater.9b05116 p 33; acs.chemmater.9b05116 p 22; d4cp00131a p 8, 2 lines), 2 partly (cm0303080 p 2: 1 line(s), 6 key(s) still flagged; s11671-015-0872-9 p 3: 2 line(s), 1 key(s) still flagged); the others flag → review |
| Citation number changed, dropped or fused into an exponent | 8 | 10.1039_d0cp03358h p 1, p 11; 10.1116_6.0001094 p 13; 10.1116_6.0003182 p 4; 10.1038_s41467-022-35428-6 p 8; 10.1021_acs.chemmater.9b05116 p 29; 10.1039_d3cp05639b p 3; 10.1039_d1cp04758b p 2 | 1 repaired by R1 (s41467 ^43 → ^4); the others flag → review |
| A letter read as a digit or a digit as a letter (t→4, I→1, 1→I, 5→S, a→2, l→.1) | 7 | 10.1021_acs.chemmater.2c01154 p 2; 10.1038_s41467-022-35428-6 p 7; 10.1039_d0cp03358h p 11; 10.1039_d4cp00131a p 4, p 13; 10.1063_1.4972120 p 5; 10.1116_6.0002993 p 4 | flag → review (no rule: the pair differs in letters) |
| A lookalike letter: Latin v or p written Greek ν or ρ | 6 | 10.1002_adem.202201901 p 8; 10.1039_d0cp03358h p 9 (two tokens of one caption: p_A0 and p_B); 10.1039_d1cp04758b p 8, p 11; 10.1039_d4cp00131a p 6; 10.1021_acs.jpcc.1c01505 p 3 (n_0 v_th written ν_th) | flag → review, with the text-layer letter as evidence |
| A digit changed (in the exponent too: t^1 written t^4; 41 written 4) | 7 | 10.1021_acs.chemmater.2c01154 p 4, p 10; 10.1021_acs.jpcc.5c06502 p 6; 10.1021_cm0303080 p 10, p 11; 10.1039_d3cp05639b p 9; 10.1149_1.3491381 p 9 | 3 repaired by R1 (acs.chemmater.2c01154 p 4 3d3 → 3d5; cm0303080 p 11 4 → 1; 1.3491381 p 9 4 → 41); the others flag → review |
| Text added (a subscript invented, a label repeated, a list number written twice: "1. 1.", "2. 2.") | 5 | 10.1021_acs.chemmater.2c01154 p 9; 10.1186_s11671-015-0872-9 p 4; 10.1039_d3cp05639b p 10; 10.1002_cvde.200390005 p 1; 10.1063_1.4972120 p 4 | flag → review |
| A subscript digit dropped or fused | 3 | 10.1021_acs.chemmater.1c03164 p 1; 10.1021_acs.chemmater.2c01154 p 3; 10.1021_acs.chemmater.9b05116 p 15 | flag → review |
| A decimal point inserted or replaced by a comma | 2 | 10.1002_adem.202201901 p 10; 10.1021_acs.chemmater.2c01154 p 4 | 1 repaired by R1 (<001>); the other flag → review |
| A prescript of J dropped or misread in inline math (³J written J; ^{m−1}J written m^{-1} J) | 2 | 10.1063_1.2714685 p 4; 10.1149_1.2789802 p 3 | flag → review |
| Affiliation marks of the author line written as digits (^z → ^2, * → \8) | 2 | 10.1149_1.3072694 p 2; 10.1149_1.3301664 p 2 | flag → review (author line) |
| An exponent sign dropped | 1 (two occurrences) | 10.1021_acs.jpcc.5c06502 p 5 | repaired by R1 at both occurrences |
| A caption label merged into the preceding paragraph (text out of order) | 1 | 10.1021_acs.chemmater.2c01154 p 5 | flag → review |
| A caption label fused with the caption text (Table 5Simulated; the Table 1 and Table 4 captions of the same paper fused the same way, unflagged) | 1 | 10.1016_j.surfcoat.2012.02.038 p 7 | flag → review |
| Letter case changed (HfO2 written HFO2, a figure caption) | 1 | 10.1002_cvde.200390005 p 5 | flag → review |
| Margin line numbers of a line-numbered manuscript merged into the text | 1 paper | 10.1021_acs.chemmater.9b05116 | 1,044 removed by `line_numbers.py`; 5 leftovers flag → review |

Totals: 10 errors corrected by the repairs, 2 partly, 47 flagged only. Causes, the answer set's labels per error:
c recognition 41, a layout 11, c Marker 6, d post-processing 1. Found through numbers
only: an error that changes no number and drops no numbered line is not seen (lower bound). The classes first seen in the 14 papers
added on 2026-10-13: page-bottom references dropped, list numbers duplicated, prescripts of J, affiliation marks written as digits,
a caption label fused with its caption, a letter case changed, an exponent digit changed (t^1 → t^4).

Body flags: 344 (171 layer numbers missing from the output, 147 output numbers absent from the layer, 18 lines not found, 8 letter
differences), all judged: 106 real, 238 not errors (precision 31 %): lines of one paragraph in other units or inside a figure box,
equations kept in the paragraph by Marker, undecoded or garbled glyphs, the MDPI duplicate layer, layer tokenisation of subscripts,
stacked indices, line breaks and displaced subscripts, furniture and the publishers' "You may also like" boxes, author lines, table
footnotes, count mismatches, stray letters of the text layer. Not-checkable flags: 396 (layer side 233, output side 163), see NUMBERS.md.

## Abstract: no remaining error found

44 of 44 earlier papers judged right on the page (one falls back to OpenAlex, 10.1021_acs.langmuir.6b03119, whose abstract block is an
image the band OCR could not read). Of the 14 papers added on 2026-10-13, 6 were checked on page 1 (right) and 8 come from the block
that matched the OpenAlex abstract (`abstract_source` openalex_match); 6 of those 8 (JES and AIP cover-page layouts) end with the
journal's copyright and DOI line, which Marker keeps inside the abstract block (known limit).

## Figures and captions

| Error | Count | Handling |
|---|---|---|
| A figure split into several picture blocks, only one bound to the caption; the other panel stays an unnumbered entry (10.1039_c3ra42928h p 4, 10.1039_c4nr05049e p 4; the figure binding of the 14 papers added on 2026-10-13 was not judged) | 2 | known limit |
| Journal logos, badges, covers and reaction equations drawn as pictures stay as unnumbered entries | 45 papers | known limit (no caption exists) |
| A "Table" that is a grid of plots (10.1116_1.4971196 Tables I and II) has no cells on the page; the output keeps the picture (Table I) or the caption alone (Table II), both flagged "no table cells" | 2 | flag → review (right on the page) |

## Tables: 33 of 90 wrong on the crop; the check flags 31, 1 not checkable, misses 1, flags 12 right ones

| Error | Count | Handling |
|---|---|---|
| Structure: an extra empty column or trailing header cell, a header shifted by one column, a column lost in every row, rows split in two by header colspans, two rows shifted a column, a data row taken into the header | 11 | 9 flag → review, 1 not checkable (rotated, 10.1039_d0cp03358h Table 1) → review, 1 missed (10.1016_j.surfcoat.2012.02.038 Table 1: the first data row became part of the header, every token present, check ok) |
| Rowspan misread: repetition counts, series labels or row-group labels shifted by one row, a row duplicated | 3 | flag → review |
| The table block drawn as an image: no cells (the band OCR gives the cell texts without structure) | 1 | flag → review |
| A symbol misread: μ lost, O as 0, Θ as θ, ξ as ζ, ȳ as ν̄, v as ν, l for I, a dash lost | 12 | flag → review |
| Subscript case or letter wrong (p_I written p_i or p_t, P_d written p_d, σ_P written σ_p) | 5 | flag → review |
| Arrow counts wrong (↓↓↓↓ for ↓↓↓) | 1 | flag → review |

The 12 right tables the check flags: table footnotes inside the box, numbers of a footnote line just below it, body text beside a
nomenclature list, the MDPI duplicate layer, a text font that encodes ν as "n", one P/p case difference, footnote letters glued to
exponents, the μm of a header read as "m" missing (10.1016_j.apsusc.2010.01.025 Tables 1–3), the two grids of plots of
10.1116_1.4971196 (no cells on the page). Undetectable: a caption bound to the wrong table, a pure column shift with every token
present, a data row taken into the header with every token present (the one wrong table the check misses).

## Equations: 434 pairs, 254 agree (accepted), 158 differ (review), 22 single tool (review)

Every differ pair and single-tool item of the 58 papers is judged on the formula crop (`answers/equations.json`, 254 items with the
74 accepted agree pairs of the first 13 papers). The 158 differ pairs: Marker right 74, Docling right 39, both wrong 18, equivalent
forms 27. The 22 single-tool items: the one tool right in 15 (Docling 10, Marker 5), Docling wrong in 7 (reaction equations with l read
as I or O as 0, a sliver of two equations, arrow labels written as fractions). Recurring errors: Marker writes θ for Θ (10 pairs of
10.1021_acs.chemmater.1c03164), K_n for Kn (5), λ as l, drops s̄ (4), a second line of a two-line equation (2) and the prescript of a
symbol in inline text, folds a trailing factor into a denominator and misplaces the scope of a root (10.1021_acs.jpcc.1c01505 eqs 5
and 9); Docling reads O as 0 (7 pairs of 10.1116_1.4892385), l as I, T as Γ (3 pairs of 10.1016_j.surfcoat.2012.02.038), drops the ∂t
of a left side (4) and prescripts, garbles text labels in equations and appends text (`\intertext` garbage in the ACS layout), and
writes bold or stray characters. A "both wrong" pair needs the formula written anew by the review.

## Figure stage (VLM): 147 data panels of 88 captioned figures judged, 142 right, 2 wrong points, 9 series missed

The 12 papers of the pilot and its expansion (`ingest/figures.py`, gemini-3.8-flash, prompt 1cb472bef385, 2026-10-17; the
counts are the Figure stage table of `NUMBERS.md`): 88 captioned figures, 236 panels (130 plot, 15 spectrum, 17 map, 40 micrograph,
28 schematic, 5 photo, 1 table image), 5,716 points, 33 peaks, 64 cells, 525,054 tokens. The 147 plot, spectrum and map-with-data
panels were judged on `reports/figures.html` (`answers/figures.json`, 153 verdicts: 146 data-panel keys, the two unlettered panels of
10.1116_6.0002804 Fig. 4 share one, plus the 7 colour-scale map panels of figures that also carry data).
- **Wrong points (2, flag → review).** 10.1039_d0cp03358h Fig. 9b and 9c: the 2000 nm series stops at its drop, the tail to zero is
  missing (F2 flags both panels). Elsewhere a sampled line is coarse (8 to 15 points per curve on the 12-curve panels of
  10.1039_d1cp04758b Fig. 4 and 10.1039_d3cp05639b Fig. 5) but on the printed shape.
- **Series missed (9, judged).** The six XPS panels of 10.1116_6.0002993 Fig. 3: the peaks are marked by a fitted baseline, not by a
  printed position, and the model returned no peak. 10.1039_d1cp04758b Fig. 7a and 7b: the pressure series on the right-hand axis
  are not read (two y axes; only the left-axis series come back). 10.1039_d0cp03358h Fig. 8a: nine repeat profiles with three legend
  labels were merged into four series. Fit lines drawn through data points are read as a second series in some figures
  (10.1021_cm0303080 Figs. 10b and 12, 10.1063_1.5028178 Figs. 5-7) and not in others (Figs. 8, 11b; 10.1021_acs.jpcc.9b08176 Fig. 3).
- **Flags (review; the judged outcome).** F1 panel-count 6: four are true differences (a sub-panel of a micrograph figure counted or
  not, 10.1116_1.4903941 Fig. 3, 10.1116_6.0002804 Fig. 10, 10.1039_d0cp03358h Figs. 7 and 11, where panels e and f of Fig. 11 are
  not in the crop), two are bracketed symbols in the caption text read as panel letters (10.1002_cvde.200390005 Fig. 4 "(p)",
  10.1039_d3cp05639b Fig. 5 "(m)"). F2 out-of-range 12: tick-range rows of a phase map (10.1021_acs.chemmater.2c01154 Figs. 2 and 4,
  the 50 and 450 °C rows lie beyond the first and last tick), points just past an axis end (within 5 % but over the 2 % tolerance)
  and the two wrong tails above. F3 duplicate-x 68: step functions and vertical line scans read as their edge points (10.1039_d3cp05639b
  Figs. 2b and 6, 10.1116_6.0003182 Fig. 6 where position is the y axis): right readings, the flag marks the shape. F4 unit-missing 16:
  dimensionless axes printed "(-)" or "(θ)" and log-axis labels, all right readings. F6 1: the single Cl point of 10.1116_6.0002804
  Fig. 5b, as printed. F5 unreadable 0: every response parsed.
- **Repeat agreement (`--repeat`, 13 figures, 75 series).** 23 series agree (31 %) by the rule (80 % of the first-run points within
  2 % of both ranges); the median point deviation is 0.011 of the axis range. Discrete series agree in full (the 64 cells and the two
  phase-map series, the marker series of 10.1116_6.0002804 Fig. 1, the four peaks of 10.1116_6.0002993 Fig. 2d); the disagreeing
  series are sampled continuous lines whose sample positions differ between runs (3 to 5 of 8 points within tolerance on
  10.1039_d0cp03358h Fig. 10 and 10.1039_d3cp05639b Fig. 8, 2 of 30 and 0 of 10 series), and four series whose label differed between
  runs (10.1063_1.5028178 Fig. 2). The number measures the sampling, not the shape; two runs on the same crops are not identical.

## Known limits (nothing flags them unless stated)
- **Figure stage: what the VLM reading cannot see.** A plot or spectrum drawn inside a schematic panel is part of the schematic and is
  not read (10.1021_acs.chemmater.2c01154 Fig. 1a, Raman spectra inside the process illustration). Insets are not read
  (10.1116_6.0002993 Fig. 1b, 10.1116_6.0002804 Fig. 3, 10.1039_d3cp05639b Figs. 4, 5i, 5j). A second ordinate is not read
  (10.1039_d1cp04758b Fig. 7). A top axis is not recorded (10.1116_1.4903941 Fig. 5a, 10.1021_acs.jpcc.9b08176 Fig. 2B). Reference
  stick patterns under a diffractogram and unlabelled peaks are not returned (10.1116_6.0003182 Fig. 5, 10.1116_6.0002993 Fig. 3).
  A continuous line is a sample of at most 40 points, so a sharp spike or a short step may be missed (10.1116_6.0003182 Fig. 2).
  The crops are Marker's figure images (450 to 800 px wide), below the 1100 px downscale: small tick labels are read from a low-resolution
  image. The caption's panel letters are a text rule: a bracketed symbol in the caption text can look like a panel letter (F1).


- **Lookalike letters.** Latin v and p of the italic text font written Greek ν and ρ (6 body errors, 2 table symbol
  errors); a flag only when the token holds a digit (v1, p_A0, v_th). The text layer carries the Latin letter: the review
  gets it as evidence.
- **The table check compares tokens, not their position.** It compares numbers, letters and symbols and the outer
  structure (column counts, empty cells, short rows), not where a token sits. A table with every token present but
  placed wrongly passes as ok and never reaches the review: a body row put into the header, or a row label put on
  the wrong row. In the 58 papers: 10.1016_j.surfcoat.2012.02.038 Table 1 (both errors). Table recall on the page:
  32 of 33.
- **Symbols not compared in the body.** The body check compares numbers and letters, not the operator symbols: ≈
  written ~, × written x, a lost dash in "7–9" are not flagged (the table check counts ± ↑ ↓ ≤ ≥ ≈ ∼ ≪ ≫ ×).
- **Escaped underscores in inline LaTeX break the subscript join.** Marker writes `\text{Al}\_2\text{O}\_3` in some
  paragraphs (the abstract of 10.1116_1.4903941, the publishers' "You may also like" boxes of 10.1149_1.3301664 and
  10.1149_1.2789802); the comparison does not join `\_2` to its base, so Al2O3, H2O, Me3Al, TiCl4 and TiO2 raise 5 false
  flags in the 4903941 abstract (judged not errors). Not fixed: the normalisation would have to read `\_` as `_`.
- **Undecoded glyphs left in equation lines.** 67 equation lines of the 58 papers hold a glyph without a decoding
  (MathematicalPi, Symbol private-use, MTEX and AdvP4C4E46/AdvP4C4E74 cids; the 7 groups viewed and left undecoded are listed
  in `glyph_codes.json`, the rest were not viewed because they block no body line). Each is a layer-side flag; they block
  only the extra direction of their paragraph (103 output paragraphs, each an output-side flag), never a body line. 5 body
  lines in all are not checkable for an undecoded glyph.
- **Citation marks printed wrongly in the source.** 10.1116_6.0001679 p 2 prints "films.^1.2" with a period (crop
  at 900 dpi, `reports/glyph_evidence/citation_period_6.0001679.png`); Marker wrote "1,2". The flag names the layer
  as reference; the page is the wrong one here. A reviewer must read the source, not the flag.
- **Typos of the source silently corrected by OCR.** The page prints "postitions" and "pyridinedicar-boxylicacid"
  (10.1021_acs.chemmater.9b05116 p 8 and p 6); Marker wrote the correct words, so the output differs from the source
  on purpose (letter flags, judged not errors). A related case: 10.1116_6.0001094 p 8 prints "electron densities"
  while its text layer reads "electrohn denisities" (a text-layer defect); Marker is right (judged not an error). The
  text layer of 10.1021_acs.jpcc.1c01505 carries stray letters (obtainedjjjj, recozzzzmbination): 4 letter flags, Marker right.
- **A flag names one representative line.** `layer_line` and `output_sentence` name the line and sentence the check
  used; when a number occurs several times or the differing line cannot be pinned down the crop shows the whole
  paragraph block (`crop_scope`), and the review should read the paragraph, not the one line.
- **The MDPI duplicate layer.** 10.3390_separations11010024 draws caption regions and some paragraphs twice (a
  hidden copy at the page's top edge or shifted over other lines). The check drops the off-page and shifted
  copies, reports 82 garbled lines as not checkable (each a flag with the reason) and still raises 16 number flags,
  mostly false; the table check sees stray letters in Table 1.
- **The subscript attachment rule, tried and reverted** (b4306e9 → f94e9f0). A small glyph just below a line's
  baseline was attached to that line (TiO_2 read as "TiO" + "^2" of the next line). It also moved superscript
  dashes, minus signs and the subscript of TiCl_4 to the wrong line and gave 7 false flags
  (10.1116_6.0002804 p 2, 10.1021_acs.jpcc.9b08176 p 2, 10.3390_separations11010024 p 7). A check must not alter
  its own reference, so the line assembly of e5cb97c stands; the subscript flags it had removed (all judged not
  errors) go to the review, as do the displaced-subscript flags of the JES layouts added on 2026-10-13.
- **A header-rule position test, tried and not applied** (2026-10-13, read only). Header cells of Marker's html
  would have to be printed above the rule that ends the header on the page (variants A, B, C of the rule's
  definition, tested on the 90 tables against `answers/tables.json`; variant C flagged the surfcoat table and no
  right table). It was tuned on the same tables it was tested on, so it was not adopted. A general fix needs
  independent evidence of the table structure, for example a second table extractor, and stays an open question.
- **Output paragraphs with numbers that no layer unit matches.** 1,867 in the 58 papers; the kinds were recounted for
  the first 44 on 2026-10-13 (1,573: 1,046 at or after the References heading, 527 before it: 294 display equations
  written as LaTeX paragraphs, 127 author, affiliation, licence and furniture lines, 91 headings, labels and fragments,
  9 captions, 4 author lists, 2 reaction table rows). Their numbers are not compared; they are counted, not flagged (their
  layer side is excluded by rule: equation boxes, author blocks, references).
- **Text not in the output at all.** The page abstract of 10.1021_acs.langmuir.6b03119 (an image block the band OCR
  could not read; the abstract field comes from OpenAlex); one two-column page read right column first
  (10.1186_s11671-015-0872-9 p 4); author lines and "Check for updates" badges OCR'd into the text (text added,
  nothing lost); the publishers' "You may also like" boxes of the JES cover pages kept as text with markdown links.
- **Input oddities handled by rule.** A page box not starting at (0, 0) (10.1116_1.5116136); a cover page with a
  "Reference" heading; figures placed after all captions; OCR-only regions without a text layer (Marker reads them,
  a table without a layer is flagged); a rotated table (not checkable, review); ACS page-bottom references and Wiley
  fonts with wrong Unicode values (decoded by a family table, 10.1002_cvde.200390005).
