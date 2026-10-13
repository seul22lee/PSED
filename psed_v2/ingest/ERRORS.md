# Ingest: remaining errors after the rules

What is still wrong in the final output (`ingest/final/<paper_id>/`) after the rules of 2026-10-12/13, on
the 44 in-scope papers with a PDF (13 checked item by item on 2026-10-12, the other 31 on 2026-10-13), judged
on the PDF pages and crops by Claude Code (commits in the change log of `INGEST.md`); the body rows marked
"text layer" were found by `body_flags` on 2026-10-13 and judged on the decoded text layer against the output
text (script), not on the page, unless a crop is named. Per error type: an
example, the count, whether a rule check flags it, and how it is handled. Handling: **flag → review** = the
`check` field of the table entry is `flag`, or the body flag is in `body_flags`; **differ → review** = the
equation pair has `status: differ`. All three are resolved by an external vision-language model at the start
of the extraction stage (planned, not part of ingest), given the crop and, for a body flag, the output sentence
and the decoded text-layer line; ingest only writes the flags, the reasons, the tokens and the crops. Claude
Code's page judgements of these items are the answer set in `ingest/answers/` (tracked, ids and verdicts only);
the review step is scored against it before it is used. **known limit** = nothing flags it; the KB must tolerate it. Tables and equations of all 44 papers are
in `ingest/reports/review_44.html`, the body/abstract/figure/caption checks of the 31 papers in
`review_31.html` (both gitignored).

## Body text (Marker)

Every body flag of the 44 papers was judged by Claude Code on the line crop on 2026-10-13 (415 flag keys over the
passes of that day, 27 of them in pass 2 after the glyph table was extended; `ingest/reports/review_body.html` shows
each final flag with its crop and verdict). 44 distinct real errors of Marker's body text were found this way (11 in
the 13 papers checked on 2026-10-12, 33 in the 31): 1.9 per 1,000 checked body lines, a lower bound (only errors that
change a number or drop a line with a number are seen). Causes: c recognition 34, a layout 9, d our post-processing 1
(the margin line numbers, since removed). Three of the 44 came to light in pass 2, in paragraphs an undecoded glyph had
blocked before.

| Error (type) | Examples | Count | Set | Flagged | Handling |
|---|---|---|---|---|---|
| A sentence, paragraph or caption dropped (line-numbered manuscript page, a line between display equations, a line after inline math, a paragraph beside a heading or figure, a table caption, a caption drawn inside the figure) | 10.1021_acs.chemmater.9b05116 p 33 (sentence), p 22 (Table 2 caption); 10.1002_adem.202201901 p 8 ("which is the product of expressions (7) and (10)"); 10.1021_acs.chemmater.1c03164 p 10 ("High-magnification images …"); 10.1021_acs.jpcc.5c06502 p 6 ("… (101) and (211) facets of rutile IrO2"); 10.1039_d0cp03358h p 8 ("Fig. 11a shows …" paragraph), p 9 (caption sentence "Parameter values …"); 10.1039_d4cp00131a p 8 (two lines); 10.1063_1.5028178 p 6 ("… channel height values are shown in Fig. 4."); 10.1186_s11671-015-0872-9 p 3 (Figure 1 caption, 3 lines), p 4 (Figure 3 caption) | 10 | 13: 4, 31: 6 | yes: "line not found in the output" or the numbers missing | 7 restored by R2 (the Figure 1 caption's middle line and the paragraphs matched elsewhere stay missing); the rest flag → review |
| Citation number changed, dropped or fused into an exponent | 10.1039_d0cp03358h "^1,2" → "^12" (p 1), "(2017).^54" → "(2017)." (p 11); 10.1116_6.0001094 "0.0021,^53" → "^33" (p 13); 10.1116_6.0003182 "material^44" → "^14" (p 4); 10.1038_s41467-022-35428-6 "data^4,35,36" → "^43,35,36" (p 8); 10.1021_acs.chemmater.9b05116 "et al.^33" → "et al.^" (p 29); 10.1039_d3cp05639b "τ^-1.^35–37,45" → "τ^{-1.35-37,45}" (p 3); 10.1039_d1cp04758b "coefficient.^4,7,13,17,20,30" → "^4,7,8,11,12,30–34" (p 2, found in pass 2) | 8 | 13: 2, 31: 6 | yes | 1 repaired by R1 (^43 → ^4); the others flag → review |
| A digit changed | 10.1021_acs.chemmater.2c01154 "Mo 3d5/2" → "3d3/2" (p 4), "SP4-40045TRS" → "SP4-4004STRS" (p 10); 10.1116_6.0002993 "GaS_x" → "Ga_2x" (p 4); 10.1039_d3cp05639b "n_P0" → "n_Po" (p 9) | 4 | 13: 1, 31: 3 | yes | 1 repaired by R1 (3d_3/2 → 3d_5/2); the others flag → review |
| A letter read as a digit or a digit as a letter (t→4, I→1, 1→I, 5→S, a→2) | 10.1021_acs.chemmater.2c01154 "Mo(N^tBu)2" → "Mo(N^4Bu)2" (p 2, 8); 10.1039_d0cp03358h "GPC_I" → "GPC_1" (p 11); 10.1038_s41467-022-35428-6 "CN1 Co." → "CNI Co." (p 7); 10.1021_acs.jpcc.5c06502 "Figure 5f" → "Figure Sf" (p 6); 10.1039_d4cp00131a "Table 1 … simulations^a" → "simulations^2" (p 4), "p_I" → "p_1" (p 13, both found in pass 2) | 6 | 13: 1, 31: 5 | yes | flag → review (no rule: the pair differs in letters) |
| A lookalike letter: Latin v or p written Greek ν or ρ (the PDF text layer has the Latin letter in the italic text font) | 10.1002_adem.202201901 "P1, v1, h1" → "ν_1" (p 8); 10.1039_d0cp03358h, d1cp04758b, d4cp00131a "p_A0" (pressure) → "ρ_A0" (p 9; p 8, 11; p 6) | 5 | 13: 1, 31: 4 | yes (mixed token) | flag → review |
| A decimal point inserted or replaced | 10.1002_adem.202201901 "<001>" → "< 0.01 >" (p 10); 10.1021_acs.chemmater.2c01154 "a-MoS3.0" → "a-MoS3,0" (p 4) | 2 | 13: 1, 31: 1 | yes | 1 repaired by R1 (0.01 → 001); MoS3,0 flag → review |
| An exponent sign dropped | 10.1021_acs.jpcc.5c06502 "g/cm^-3" → "g/cm^3" twice (p 5) | 1 | 31 | yes | corrected by R1 at both occurrences (checked on the crop 2026-10-13; the first run had applied both records to one token, writing g/cm^--3 and leaving the other) |
| A subscript digit dropped or fused | 10.1021_acs.chemmater.1c03164 "n_0" → "n" (p 1); 10.1021_acs.chemmater.2c01154 "E₂¹g" → "E_1g" (p 3); 10.1021_acs.chemmater.9b05116 "Mg(MeCp)_2" → "Mg(MeCp)_" (p 15) | 3 | 31 | yes | flag → review |
| Text added | 10.1021_acs.chemmater.2c01154 "MoS2, TiS2, and WS2" → "MoS_2.2, TiS_2.2, WS_2.2" (p 9, crop viewed); 10.1186_s11671-015-0872-9 "Figure 4c-1,c-2,c-3" → "4c-1, 4c-2, 4c-3" (p 4); 10.1039_d3cp05639b "A_O" → "A_{O_0}" (p 10) | 3 | 13: 1, 31: 2 | yes | flag → review |
| Text out of order: a caption label merged into the preceding paragraph | 10.1021_acs.chemmater.2c01154 "… 5.06 g/cm^3.^66 Figure 6." (p 5) | 1 | 31 | yes (key `…|5|number|6`, judged real) | flag → review |
| Margin line numbers of a line-numbered manuscript merged into the text (every line) | 10.1021_acs.chemmater.9b05116 | 1 paper (761 numbers flagged before the rule) | 31 | yes before the rule | fixed: `line_numbers.py` removed 1,044; 5 leftovers at breaks where the same bare number stands in the adjacent line ("could 3 be achieved at 2 Å/cycle to 3 Å/cycle") |
| Angle brackets rendered as math ("<001>" written "< 0.01 >"), see the decimal-point row | 10.1002_adem.202201901 p 10 | — | 13 | yes | repaired |
| Two-column page read right column first for one block | 10.1186_s11671-015-0872-9 p 4 | 1 page | 13 | no | known limit |
| An abstract block rendered as an image whose band OCR returns no text | 10.1021_acs.langmuir.6b03119 p 1 | 1 | 31 | `bands.json` (applied: false) | the abstract field falls back to OpenAlex; the paragraph stays missing from the body |
| Author lines and "Check for updates" badges rendered as images, then OCR'd into the text | 25 band repairs in 20 papers: 2 captions, 4 abstracts, 1 table, 11 author lines, 7 badges | author lines and badges | both | recorded in `bands.json` | known limit (text added, nothing lost) |

`body_flags` in the final output (2026-10-13, 44 papers): 238 flags (12 "line not found", 120 text-layer numbers
missing from the output paragraph, 102 output numbers absent from the text layer, 4 "letters of the text layer differ from
the output"), 12 papers without a flag; 77 of the 234 judged flags are real (precision 33 %), 157 are not errors, the 4
letter flags are new after the lookup of garbled lines by similarity (not yet judged, listed with their crops in
review_body.html); a subscript attachment rule tried on 2026-10-13 was reverted (it moved superscript dashes and minus signs
to the wrong line, 7 false flags), so 15 flags of subscripts read as superscripts of the next line stay (all judged not
errors): lines of one paragraph or caption in other units or inside a
figure box (35), equations and formulas kept in the paragraph by Marker while their boxes are excluded (17 + 5 in pass 2),
undecoded or garbled glyphs (16), the MDPI duplicate layer (14), layer tokenisation of subscripts, stacked indices, gaps
and line breaks (15 + 5), furniture (7), table footnotes (4), count mismatches (2 + 2), other (12 + 2). Pass 2 (the glyph
table extended, 1,073 more lines checked) raised 28 new flags: 9 real, 19 not errors, 4 of which vanished after the
AdvPi1 "+" glyph was decoded as ± (on the crop). Besides these, 268 flags of kind "not checkable" name what the check
cannot compare, with the reason and a crop, so that the flag review sees them like a not-checkable table; together they
cover every unchecked layer line (156 of 23,935) and every output unit whose numbers are not compared (checked per paper).
Layer side: 67 lines of units under 4 words that the lookup near the previous match did not find in the output (headings
Marker dropped, labels, fragments: SectionHeader 24, Text 5, outside the blocks 38, Caption 0; 7 carry a digit; 380 before
the lookup, 303 found and checked), 83 garbled lines of the overlapping duplicate layer (82 in 10.3390_separations11010024
and 1 in 10.1063_5.0168768; 98 before the lookup, which recovered the 16 spaceless lines of 10.1016_j.mee.2018.01.027 and
5 others, 11 without spaces and 10 by similarity), 20 equation or weak lines holding undecoded delimiter pieces, 4 units too short to locate, 1 unit of 2 lines
with undecoded pieces. Output side: 55 sentences the layer lines of their paragraph do not cover (a paragraph spanning a
column or page break into another unit, text Marker added) and 38 paragraphs blocked by an undecoded glyph in an equation
or neighbour line; both carry the output text, the numbers left unchecked and a crop of the Marker block. Not flagged: 1,574
output paragraphs with numbers that no layer unit matches (1,049 at or after the References heading, the rest display
equations, author and furniture lines and paragraphs of excluded blocks), counted in `body_check.counts`. Countermeasures
(`body_repair.py`, 2026-10-13): 12 repair records in 8 papers, 0 undone by the recheck, each viewed on its crop: 8 distinct
errors corrected (<001>, 3d_5/2, g/cm^-3 at both occurrences, ^4,35,36, four dropped lines or captions), 1 partly (the
Figure 1 caption of 10.1186_s11671-015-0872-9: 2 of 3 lines restored, the middle line stays flagged); the other 35 errors
stay flagged only. Regression against every page verdict after pass 2: the 3 known errors of review_31
are flagged or repaired, 0 of the 41 known not-errors is flagged (the regression script's substring matcher reports "480"
of 10.1039_d1cp04758b against the output numbers of the judged p_A0 → ρ_A0 flags, not a flag of its own), 126 of 128
judged real flag keys are still detected (flagged, repaired or removed by the rule; the two token flags of the dropped
Fig. 11a paragraph were already absent before pass 2, its "11" flag remains), 151 not-error flag keys are gone, 136 remain
(listed in review_body.html).

Coverage of the body check per paper (lines read inside the text blocks after the exclusions; share checked; not
checkable by cause):

| paper | body lines read | checked | share | not checkable: undecoded glyph (lines; fonts) | rotated (characters) | other (lines/sentences) | flags | not-checkable flags | repairs |
|---|---|---|---|---|---|---|---|---|---|
| 10.1002_adem.202201901 | 749 | 749 | 100 % | 0 | 3759 | 2 | 5 | 15 | 1 |
| 10.1007_s12274-010-0066-9 | 352 | 351 | 100 % | 0 | 0 | 2 | 0 | 2 | 0 |
| 10.1016_j.ijpharm.2017.04.031 | 635 | 635 | 100 % | 0 | 0 | 1 | 4 | 1 | 0 |
| 10.1016_j.mee.2018.01.027 | 269 | 269 | 100 % | 0 | 0 | 4 | 2 | 4 | 0 |
| 10.1016_j.mee.2018.01.033 | 217 | 217 | 100 % | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1016_j.sse.2022.108584 | 363 | 363 | 100 % | 0 | 44 | 0 | 0 | 0 | 0 |
| 10.1021_acs.chemmater.1c03164 | 944 | 941 | 100 % | 0 | 0 | 3 | 1 | 3 | 1 |
| 10.1021_acs.chemmater.2c01154 | 926 | 925 | 100 % | 0 | 1625 | 5 | 15 | 5 | 1 |
| 10.1021_acs.chemmater.6c00816 | 1198 | 1197 | 100 % | 0 | 2520 | 2 | 5 | 2 | 0 |
| 10.1021_acs.chemmater.9b05116 | 754 | 751 | 100 % | 0 | 297 | 7 | 41 | 7 | 2 |
| 10.1021_acs.jpcc.5c06502 | 676 | 674 | 100 % | 0 | 1536 | 2 | 10 | 2 | 2 |
| 10.1021_acs.jpcc.9b08176 | 367 | 364 | 99 % | 0 | 822 | 4 | 9 | 4 | 0 |
| 10.1021_acs.jpclett.4c03545 | 269 | 269 | 100 % | 0 | 147 | 0 | 0 | 0 | 0 |
| 10.1021_acs.langmuir.6b03119 | 502 | 499 | 99 % | 0 | 1136 | 3 | 4 | 3 | 0 |
| 10.1021_acsami.0c06879 | 481 | 481 | 100 % | 0 | 201 | 0 | 0 | 0 | 0 |
| 10.1021_acsami.0c22121 | 301 | 301 | 100 % | 0 | 0 | 2 | 7 | 2 | 0 |
| 10.1021_acsnano.5b03429 | 473 | 473 | 100 % | 0 | 980 | 1 | 3 | 1 | 0 |
| 10.1038_s41467-022-35428-6 | 540 | 540 | 100 % | 0 | 30 | 1 | 5 | 5 | 1 |
| 10.1038_srep18401 | 226 | 226 | 100 % | 0 | 0 | 3 | 0 | 3 | 0 |
| 10.1039_c3ra42928h | 318 | 318 | 100 % | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1039_c4nr05049e | 374 | 373 | 100 % | 0 | 0 | 1 | 0 | 1 | 0 |
| 10.1039_c5ta00205b | 542 | 540 | 100 % | 0 | 0 | 2 | 2 | 2 | 0 |
| 10.1039_c7ta03257a | 602 | 602 | 100 % | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1039_d0cp03358h | 739 | 739 | 100 % | 0 | 2684 | 0 | 14 | 0 | 0 |
| 10.1039_d1cp04758b | 796 | 794 | 100 % | 0 | 0 | 7 | 23 | 7 | 0 |
| 10.1039_d3cp01829f | 690 | 690 | 100 % | 0 | 0 | 0 | 6 | 0 | 0 |
| 10.1039_d3cp05639b | 631 | 628 | 100 % | 0 | 0 | 3 | 12 | 3 | 0 |
| 10.1039_d4cp00131a | 997 | 996 | 100 % | 0 | 0 | 2 | 5 | 2 | 2 |
| 10.1039_d4nr03749a | 674 | 673 | 100 % | 0 | 0 | 1 | 2 | 1 | 0 |
| 10.1063_1.2338776 | 277 | 277 | 100 % | 0 | 92 | 0 | 3 | 0 | 0 |
| 10.1063_1.5028178 | 410 | 410 | 100 % | 0 | 171 | 1 | 1 | 1 | 0 |
| 10.1063_5.0168768 | 308 | 307 | 100 % | 0 | 126 | 5 | 2 | 13 | 0 |
| 10.1093_nsr_nwaf247 | 849 | 849 | 100 % | 0 | 1730 | 0 | 0 | 9 | 0 |
| 10.1116_1.4892385 | 493 | 493 | 100 % | 0 | 184 | 2 | 1 | 2 | 0 |
| 10.1116_1.5116136 | 202 | 202 | 100 % | 0 | 3213 | 1 | 5 | 1 | 0 |
| 10.1116_6.0001094 | 898 | 896 | 100 % | 2 (AdvP4C4E46 4) | 0 | 1 | 9 | 22 | 0 |
| 10.1116_6.0001679 | 236 | 235 | 100 % | 0 | 0 | 4 | 1 | 4 | 0 |
| 10.1116_6.0002804 | 423 | 416 | 98 % | 0 | 189 | 7 | 0 | 7 | 0 |
| 10.1116_6.0002993 | 382 | 382 | 100 % | 0 | 168 | 0 | 2 | 0 | 0 |
| 10.1116_6.0003182 | 719 | 719 | 100 % | 0 | 252 | 1 | 3 | 1 | 0 |
| 10.1149_2.067203jes | 721 | 720 | 100 % | 0 | 116 | 5 | 14 | 9 | 0 |
| 10.1186_s11671-015-0872-9 | 271 | 271 | 100 % | 0 | 0 | 0 | 6 | 0 | 2 |
| 10.3390_separations11010024 | 646 | 529 | 82 % | 0 | 0 | 123 | 16 | 123 | 0 |
| 10.3762_bjnano.5.25 | 495 | 495 | 100 % | 0 | 0 | 1 | 0 | 1 | 0 |

The text layer of 10.1116_1.5116136 (page box from −92) and the cover-page "Reference" heading of the same paper, and the
units of 10.1116_6.0002804 and 10.1039_d1cp04758b matching paragraphs after the References heading, had stopped the
check on page 1 before 2026-10-13; fixed (M19, M20). Rotated characters are table or figure text drawn sideways.

## Abstract (Marker, OpenAlex fallback)

44 of 44 abstracts right: 23 `heading`, 20 `openalex_match`, 1 `openalex` (10.1021_acs.langmuir.6b03119, see above);
recall against a usable OpenAlex abstract 90 % or more where one exists (the RSC and Elsevier records are short blurbs
or absent). No remaining error.

## Figures and captions (Marker)

| Error | Example | Count | Flagged | Handling |
|---|---|---|---|---|
| A figure split into several picture blocks, only one bound to the caption; the other panel stays an unnumbered entry | 10.1039_c3ra42928h p 4 (TEM panel a), 10.1039_c4nr05049e p 4 (plot panel a) | 2 | no | known limit |
| Journal logos, badges, covers and reaction equations drawn as pictures stay as unnumbered entries | 31 papers | — | no | known limit (no caption exists) |

Fixed on 2026-10-13 (no longer errors): captions joined with the body paragraph below (10.1021_acs.chemmater.1c03164
Figures 1 and 3); figures placed after all captions left without an image (10.1116_1.5116136 Figures 1–5); OCR'd
abstracts not written into document.md (4 ACS papers).

## Tables (Marker, 69 tables in 28 papers: 53 numbered tables, 16 unnumbered symbol lists)

Judged on the crop: 41 right, 28 wrong. The rule check (decoded text layer, `glyph_codes.json`) flags 27 of the 28,
misses 0, flags 7 right tables, and reports 1 as not checkable (the wrong one it cannot read).

| Error | Example | Count | Flagged | Handling |
|---|---|---|---|---|
| Structure: an extra empty column or trailing header cell, a header shifted by one column, a column lost in every row | 10.3390_separations11010024 A1, A2, A3, A4; 10.1021_acs.chemmater.9b05116 p 22; 10.1039_d4cp00131a Table 2 (a column lost); 10.1039_d0cp03358h Table 1 (header split, rotated) | 7 | 6 yes, 1 not checkable (rotated) | flag → review; the rotated table goes to review as "not checkable" |
| Rowspan misread: repetition counts or series labels shifted by one row | 10.1021_acs.chemmater.1c03164 Table 1; 10.1039_d1cp04758b Table 3 | 2 | yes | flag → review |
| The table block drawn as an image: no cells (the band OCR gives the cell texts without structure, put into document.md) | 10.1021_acsnano.5b03429 Table 1 | 1 | yes (no cells) | flag → review |
| A symbol misread: μ lost in "(μm)", letter O as digit 0 (Cu2O, A_O), Θ as θ, ξ as ζ, ȳ as ν̄, v as ν, l for I, a dash lost | acsami.0c06879 S1/S2; 1.5116136 Table I; 1.4892385 Table I; d3cp05639b Tables 1, 2, list; chemmater.1c03164 list; d3cp01829f Table 2, list; 6.0003182 Table I; d1cp04758b list; bjnano.5.25 Table 2 | 12 | yes | flag → review |
| Subscript case or letter wrong (p_I written p_i or p_t, P_d written p_d, σ_P written σ_p) | 10.1039_d1cp04758b Table 1 and list, d3cp01829f list, d4cp00131a Table 1, d3cp05639b Table 2 | 5 | yes | flag → review |
| Arrow counts wrong (↓↓↓↓ for ↓↓↓ or ↓) | 10.1039_d1cp04758b Table 2 | 1 | yes (symbol counts) | flag → review |

Right tables the check flags (7): table footnotes inside Marker's table box (10.1021_acs.jpcc.9b08176 Table 1),
numbers of a footnote line just below the box on the table's columns (10.1021_acs.chemmater.6c00816 Table 1),
the box covering body text beside a nomenclature list (10.1063_1.5028178 p 2), the MDPI hidden duplicate text
layer (10.3390_separations11010024 Table 1), a text font that encodes ν as "n" (10.1039_d4cp00131a p 17), one
unexplained P/p case difference in a symbol list (10.1039_d0cp03358h p 12), and footnote letters glued to
exponents (10.1039_d0cp03358h Table 2). Undetectable by the checks: a caption bound to the wrong table, and a
pure column shift with every token present and equal column counts (not seen on the 44 papers).

Fixed on 2026-10-12/13, no longer errors: trailing zeros dropped by tabulate (0.10 → 0.1); Greek letters in
headers (a comparison artefact); the text layer of RSC, AIP and Elsevier symbol fonts read as letters or (cid:N)
codes (now decoded per font, `glyph_codes.json`).

## Equations (Docling CodeFormula on R1/R2 crops + Marker; 321 entries in the 44 papers)

| Status | Count | Handling |
|---|---|---|
| agree | 197 | accepted |
| differ | 109 | differ → review (on the 13 checked papers: Marker right 14, Docling right 7, both wrong 3, equivalent forms 5 of 29) |
| docling only / marker only | 12 / 3 | review |

The R1 crop (tight formula box, 216 dpi) fixed 18 Docling equations and broke 1 (10.1063_1.5028178 eq 20) on the 13
checked papers; the R2 band box fixed 12 of the 19 Beilstein equations whose Docling box held only the number.
Marker's own equations were not re-recognised: on its own box at 216 dpi that fixed 2 and broke 13.

## Input limits seen

| Limit | Example | Effect | Handling |
|---|---|---|---|
| Duplicated text layer: caption regions and some paragraphs drawn twice, the hidden copy at the page's top edge or shifted over other lines | 10.3390_separations11010024 (12 % of the characters on p 7; no other paper of the 44) | Docling repeated those captions (not used); the table check sees stray letters (one false flag); the body check drops the off-page and shifted duplicate characters, reports 82 garbled lines as not checkable (each a flag with the reason: a copy elsewhere in the output or doubled characters) and raises 19 number flags, mostly false | known limit |
| Symbol-font glyphs and (cid:N) subset codes of body text without a decoding | before pass 2: RSC and AIP papers (10.1039_c7ta03257a 114 lines, 10.1063_1.5028178 91, 10.1063_1.2338776 90, 10.1039_d4cp00131a 177); after: 10.1116_6.0001094 only | 2 body lines not checkable (1,075 before pass 2, 2,726 before the first additions); on 2026-10-13 every undecoded glyph of the 44 papers was viewed on crops (150 font-subset/code keys, `reports/glyph_evidence/`): 110 decoded (operators, Greek letters, tall parentheses and brackets, s̄, v̄, Á, icons and brace pieces that carry no text) plus the AdvPi1 "+" that draws ±; 22 pieces of multi-part delimiters in 5 papers stay undecoded with the reason in `glyph_codes.json` ("undecoded"): they block 2 text lines and 20 equation lines (38 paragraphs lose the extra direction, 334 before) | known limit for the delimiter pieces; every blocked line is a "not checkable" flag |
| A page box that does not start at (0, 0) | 10.1116_1.5116136 (media box from −92) | Marker's boxes are 0-based, pdfplumber keeps the PDF origin: the body check shifts the boxes (M19) | — |
| A repository cover page with a "Reference" heading | 10.1116_1.5116136 p 1 | stopped the body check on page 1 until the stop was limited to the second half of a paper (M20) | — |
| Symbol fonts whose text layer gives letters (AdvPi2 "y" for θ) or subset glyph codes ((cid:3) is − in one paper and × in another) | RSC, AIP, Elsevier tables of 12 papers | decoded per font family / per embedded subset with evidence (`glyph_codes.json`); a code without a table makes the table "not checkable" | — |
| A rotated table | 10.1039_d0cp03358h Table 1 | not checkable (Marker read it; the header is shifted) | review |
| Figures placed after all captions (manuscript) | 10.1116_1.5116136 | bound by page order | — |
| Pages without a text layer (OCR-only regions) | 10.1039_c4nr05049e abstract, 10.1021_acs.chemmater.1c03164 headings, 10.1116_6.0003182 table (this one has a text layer in Marker's box) | Marker OCRs them itself; a table without a text layer is flagged | flag → review |
