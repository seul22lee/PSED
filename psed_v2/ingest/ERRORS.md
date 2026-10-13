# Ingest: errors and known limits

Scope: the first 44 papers. The 15 papers added on 2026-10-13 are parsed but not judged, so nothing below counts them; their flags are in `NUMBERS.md` (column "New 15").

What is wrong in the final output (`ingest/final/<paper_id>/`) of the 44 in-scope papers with a PDF, judged on the
PDF pages and crops by Claude Code (the verdicts are the answer set `ingest/answers/`), with the counts of
`ingest/NUMBERS.md`, and what the checks cannot see. Handling: **flag → review** = the item carries a flag for the
review at the start of the extraction stage; **repaired** = corrected by `body_repair.py`; **known limit** = nothing
flags it and the knowledge base must tolerate it.

## Body text (Marker): 44 distinct real errors in 23,779 checked lines (1.9 per 1,000)

| Error class | Count | Papers (page) | Handling |
|---|---|---|---|
| A sentence, paragraph or caption dropped (a line between display equations, a line after inline math, a paragraph beside a heading or figure, a table caption, a caption drawn inside the figure) | 10 | 10.1021_acs.chemmater.9b05116 p 22, p 33; 10.1002_adem.202201901 p 8; 10.1021_acs.chemmater.1c03164 p 10; 10.1021_acs.jpcc.5c06502 p 6; 10.1039_d0cp03358h p 8, p 9; 10.1039_d4cp00131a p 8; 10.1063_1.5028178 p 6; 10.1186_s11671-015-0872-9 p 3, p 4 | 4 repaired by R2 (9b05116 p 22 and p 33, 1c03164 p 10, d4cp00131a p 8), 1 partly (s11671 p 3: 2 of 3 lines restored, the middle line stays flagged); the others flag → review |
| Citation number changed, dropped or fused into an exponent | 8 | 10.1039_d0cp03358h p 1, p 11; 10.1116_6.0001094 p 13; 10.1116_6.0003182 p 4; 10.1038_s41467-022-35428-6 p 8; 10.1021_acs.chemmater.9b05116 p 29; 10.1039_d3cp05639b p 3; 10.1039_d1cp04758b p 2 | 1 repaired by R1 (s41467 ^43 → ^4); the others flag → review |
| A letter read as a digit or a digit as a letter (t→4, I→1, 1→I, 5→S, a→2) | 6 | 10.1021_acs.chemmater.2c01154 p 2 and 8; 10.1039_d0cp03358h p 11; 10.1038_s41467-022-35428-6 p 7; 10.1021_acs.jpcc.5c06502 p 6; 10.1039_d4cp00131a p 4, p 13 | flag → review (no rule: the pair differs in letters) |
| A lookalike letter: Latin v or p written Greek ν or ρ | 5 | 10.1002_adem.202201901 p 8; 10.1039_d0cp03358h p 9 (two tokens of one caption: p_A0 and p_B); 10.1039_d1cp04758b p 8, p 11; 10.1039_d4cp00131a p 6 | flag → review, with the text-layer letter as evidence |
| A digit changed | 4 | 10.1021_acs.chemmater.2c01154 p 4, p 10; 10.1116_6.0002993 p 4; 10.1039_d3cp05639b p 9 | 1 repaired by R1 (3d_3/2 → 3d_5/2); the others flag → review |
| A subscript digit dropped or fused | 3 | 10.1021_acs.chemmater.1c03164 p 1; 10.1021_acs.chemmater.2c01154 p 3; 10.1021_acs.chemmater.9b05116 p 15 | flag → review |
| Text added (a subscript invented, a label repeated) | 3 | 10.1021_acs.chemmater.2c01154 p 9; 10.1186_s11671-015-0872-9 p 4; 10.1039_d3cp05639b p 10 | flag → review |
| A decimal point inserted or replaced by a comma | 2 | 10.1002_adem.202201901 p 10; 10.1021_acs.chemmater.2c01154 p 4 | 1 repaired by R1 (<001>); the other flag → review |
| An exponent sign dropped | 1 (two occurrences) | 10.1021_acs.jpcc.5c06502 p 5 | repaired by R1 at both occurrences |
| A caption label merged into the preceding paragraph (text out of order) | 1 | 10.1021_acs.chemmater.2c01154 p 5 | flag → review |
| Margin line numbers of a line-numbered manuscript merged into the text | 1 paper | 10.1021_acs.chemmater.9b05116 | 1,044 removed by `line_numbers.py`; 5 leftovers flag → review |

Totals: 8 errors corrected by the repairs, 1 partly, 35 flagged only. Causes: Marker's recognition 34, layout 9, our
own post-processing 1 (the margin numbers, removed). Found through numbers only: an error that changes no number and
drops no numbered line is not seen (lower bound).

Body flags: 238 (120 layer numbers missing from the output, 102 output numbers absent from the layer, 12 lines not
found, 4 letter differences), all judged: 78 real, 160 not errors (precision 33 %): lines of one
paragraph in other units or inside a figure box, equations kept in the paragraph by Marker, undecoded or garbled
glyphs, the MDPI duplicate layer, layer tokenisation of subscripts, stacked indices and line breaks, furniture, table
footnotes, count mismatches. Not-checkable flags: 268 (layer side 175, output side 93), see NUMBERS.md.

## Abstract: no remaining error (44 of 44 right; one falls back to OpenAlex, 10.1021_acs.langmuir.6b03119, whose abstract block is an image the band OCR could not read).

## Figures and captions

| Error | Count | Handling |
|---|---|---|
| A figure split into several picture blocks, only one bound to the caption; the other panel stays an unnumbered entry (10.1039_c3ra42928h p 4, 10.1039_c4nr05049e p 4) | 2 | known limit |
| Journal logos, badges, covers and reaction equations drawn as pictures stay as unnumbered entries | 31 papers | known limit (no caption exists) |

## Tables: 28 of 69 wrong on the crop; the check flags 27, misses 0, flags 7 right ones, 1 not checkable

| Error | Count | Handling |
|---|---|---|
| Structure: an extra empty column or trailing header cell, a header shifted by one column, a column lost in every row | 7 | 6 flag → review, 1 not checkable (rotated, 10.1039_d0cp03358h Table 1) → review |
| Rowspan misread: repetition counts or series labels shifted by one row | 2 | flag → review |
| The table block drawn as an image: no cells (the band OCR gives the cell texts without structure) | 1 | flag → review |
| A symbol misread: μ lost, O as 0, Θ as θ, ξ as ζ, ȳ as ν̄, v as ν, l for I, a dash lost | 12 | flag → review |
| Subscript case or letter wrong (p_I written p_i or p_t, P_d written p_d, σ_P written σ_p) | 5 | flag → review |
| Arrow counts wrong (↓↓↓↓ for ↓↓↓) | 1 | flag → review |

The 7 right tables the check flags: table footnotes inside the box, numbers of a footnote line just below it, body
text beside a nomenclature list, the MDPI duplicate layer, a text font that encodes ν as "n", one P/p case
difference, footnote letters glued to exponents. Undetectable: a caption bound to the wrong table, a pure column shift
with every token present (not seen on the 44 papers).

## Equations: 321 pairs, 197 agree (accepted), 109 differ (review), 15 single tool (review)

Every differ pair and single-tool item of the 44 papers is judged on the formula crop (`answers/equations.json`, 198
items with the 74 accepted agree pairs). The 109 differ pairs: Marker right 44, Docling right 33, both wrong 16,
equivalent forms 16 (the 13 papers of 2026-10-12: 14 / 7 / 3 / 5; the 31 others: 30 / 26 / 13 / 11). The 15 single-tool
items: the one tool right in 12 (Docling 9, Marker 3), Docling wrong in 3 (reaction equations of
10.1021_acs.chemmater.9b05116 p 16: a hat on O, C_2H_4 garbled). Recurring errors: Marker writes θ for Θ (10 pairs of
10.1021_acs.chemmater.1c03164), K_n for Kn (5), drops s̄ (4) and a second line of a two-line equation (2); Docling reads
O as 0 (7 pairs of 10.1116_1.4892385), drops the ∂t of a left side (4), garbles text labels in equations and appends
text, and writes bold or stray characters. A "both wrong" pair needs the formula written anew by the review.

## Known limits (nothing flags them unless stated)

- **Lookalike letters.** Latin v and p of the italic text font written Greek ν and ρ (5 body errors, 2 table symbol
  errors); a flag only when the token holds a digit (v1, p_A0). The text layer carries the Latin letter: the review
  gets it as evidence.
- **Symbols not compared in the body.** The body check compares numbers and letters, not the operator symbols: ≈
  written ~, × written x, a lost dash in "7–9" are not flagged (the table check counts ± ↑ ↓ ≤ ≥ ≈ ∼ ≪ ≫ ×).
- **Citation marks printed wrongly in the source.** 10.1116_6.0001679 p 2 prints "films.^1.2" with a period (crop
  at 900 dpi, `reports/glyph_evidence/citation_period_6.0001679.png`); Marker wrote "1,2". The flag names the layer
  as reference; the page is the wrong one here. A reviewer must read the source, not the flag.
- **Typos of the source silently corrected by OCR.** The page prints "postitions" and "pyridinedicar-boxylicacid"
  (10.1021_acs.chemmater.9b05116 p 8 and p 6); Marker wrote the correct words, so the output differs from the source
  on purpose (letter flags, judged not errors). A related case: 10.1116_6.0001094 p 8 prints "electron densities"
  while its text layer reads "electrohn denisities" (a text-layer defect); Marker is right (judged not an error).
- **A flag names one representative line.** `layer_line` and `output_sentence` name the line and sentence the check
  used; when a number occurs several times or the differing line cannot be pinned down the crop shows the whole
  paragraph block (`crop_scope`), and the review should read the paragraph, not the one line.
- **The MDPI duplicate layer.** 10.3390_separations11010024 draws caption regions and some paragraphs twice (a
  hidden copy at the page's top edge or shifted over other lines). The check drops the off-page and shifted
  copies, reports 82 garbled lines as not checkable (each a flag with the reason) and still raises 19 number flags,
  mostly false; the table check sees stray letters in Table 1.
- **The subscript attachment rule, tried and reverted** (b4306e9 → f94e9f0). A small glyph just below a line's
  baseline was attached to that line (TiO_2 read as "TiO" + "^2" of the next line). It also moved superscript
  dashes, minus signs and the subscript of TiCl_4 to the wrong line and gave 7 false flags
  (10.1116_6.0002804 p 2, 10.1021_acs.jpcc.9b08176 p 2, 10.3390_separations11010024 p 7). A check must not alter
  its own reference, so the line assembly of e5cb97c stands; the 15 subscript flags it had removed (all judged not
  errors) go to the review.
- **Output paragraphs with numbers that no layer unit matches.** 1,573: 1,046 at or after the
  References heading (reference entries) and 527 before it: 294 display equations written as LaTeX paragraphs,
  127 author, affiliation, licence and furniture lines, 91 headings, labels and fragments, 9 captions, 4 author
  lists, 2 reaction table rows. Their numbers are not compared; they are counted, not flagged (their layer side is
  excluded by rule: equation boxes, author blocks, references).
- **Undecoded glyphs.** 22 pieces of multi-part tall delimiters in 5 papers stay undecoded (`glyph_codes.json`
  "undecoded"): 2 body lines and 20 equation lines are not checkable, and 38 paragraphs lose the extra direction.
- **Text not in the output at all.** The page abstract of 10.1021_acs.langmuir.6b03119 (an image block the band OCR
  could not read; the abstract field comes from OpenAlex); one two-column page read right column first
  (10.1186_s11671-015-0872-9 p 4); author lines and "Check for updates" badges OCR'd into the text (text added,
  nothing lost).
- **Input oddities handled by rule.** A page box not starting at (0, 0) (10.1116_1.5116136); a cover page with a
  "Reference" heading; figures placed after all captions; OCR-only regions without a text layer (Marker reads them,
  a table without a layer is flagged); a rotated table (not checkable, review).
