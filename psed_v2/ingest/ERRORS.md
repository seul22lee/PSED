# Ingest: remaining errors after the rules

What is still wrong in the final output (`ingest/final/<paper_id>/`) after the rules of 2026-10-12/13, on
the 44 in-scope papers with a PDF (13 checked item by item on 2026-10-12, the other 31 on 2026-10-13), judged
on the PDF pages and crops by Claude Code (commits in the change log of `INGEST.md`); the body rows marked
"text layer" were found by `body_flags` on 2026-10-13 and judged on the decoded text layer against the output
text (script), not on the page, unless a crop is named. Per error type: an
example, the count, whether a rule check flags it, and how it is handled. Handling: **flag → review** = the
`check` field of the table entry is `flag`; **differ → review** = the equation pair has `status: differ`.
Both are resolved by an external vision-language model reading the crop, as a pre-processing step of the
extraction stage (planned, not part of ingest); ingest only writes the flags, the reasons, the tokens and the
crops. **known limit** = nothing flags it; the KB must tolerate it. Tables and equations of all 44 papers are
in `ingest/reports/review_44.html`, the body/abstract/figure/caption checks of the 31 papers in
`review_31.html` (both gitignored).

## Body text (Marker)

| Error | Example | Count (44 papers) | Flagged | Handling |
|---|---|---|---|---|
| A sentence of a line-numbered manuscript page dropped | 10.1021_acs.chemmater.9b05116 p 33: "The mean pore radii of the porous films all lie between approximately 0.9 nm and 1.6 nm." | 1 | yes: `body_flags` "line not found in the output" | flag → review |
| A decimal point read as a comma, a digit read as a letter | 10.1021_acs.chemmater.2c01154: "a-MoS3,0" for a-MoS3.0, "SP4-4004STRS" for SP4-40045TRS | 3 numbers | yes: `body_flags` (MoS3.0 missing / MoS3,0 absent; 40045 missing / 4004STRS absent) | flag → review |
| Angle brackets rendered as math: "<001>" written "< 0.01 >" (the 2026-10-12 row said "001") | 10.1002_adem.202201901 p 10 | 1 | yes: `body_flags` (001 missing, 0.01 absent) | flag → review |
| Two-column page read right column first for one block | 10.1186_s11671-015-0872-9 p 4 | 1 page | no | known limit |
| Margin line numbers of a line-numbered manuscript merged into the text (text layer) | 10.1021_acs.chemmater.9b05116, every page | 761 numbers | yes: `body_flags` "number of the output paragraph absent from the text layer" | flag → review; the KB must drop them |
| A digit or letter changed inside a formula, a label or a unit (text layer; the MoS2 case also on the crop) | 10.1021_acs.chemmater.2c01154: Mo(N^tBu)2 → Mo(N^4Bu)2 (p 2, 8), E₂¹g → E_1g (p 3), Mo 3d5/2 → 3d3/2 (p 4), "MoS2, TiS2, and WS2" → MoS_2.2, TiS_2.2, WS_2.2 (p 9); 10.1039_d0cp03358h GPC_I → GPC_1 (p 11); 10.1039_d4cp00131a "c (-)" → "c (s^-1)" (p 2), footnote mark ^a → ^2 (p 4); 10.1021_acs.jpcc.5c06502 "Figure 5f" → "Figure Sf" (p 6), g/cm^-3 → g/cm^3 twice (p 5); 10.1116_6.0003182 "material^44" → "^14" (p 4); 10.1021_acs.chemmater.1c03164 n_0 → n (p 1) | 13 | yes: `body_flags` | flag → review |
| A citation number rewritten or dropped (text layer) | 10.1039_d0cp03358h: "^1,2" → "^12" (p 1), "(2017).^54" → "(2017)." (p 11) | 2 | yes: `body_flags` | flag → review |
| A sentence, paragraph or caption sentence dropped (text layer, absence confirmed in document.md) | 10.1039_d0cp03358h p 8 ("Fig. 11a shows the effect of TMA pulse time … Series E in Table 1 …"), p 9 (caption sentence "Parameter values: T = 300 °C, t_P = 0.10 s, p_A0 = 65 Pa …"); 10.1063_1.5028178 p 6 ("… channel height values are shown in Fig. 4."); 10.1021_acs.chemmater.9b05116 p 22 (Table 2 caption) | 4 | yes: `body_flags` ("line not found" or the numbers missing) | flag → review |
| An abstract block rendered as an image whose band OCR returns no text | 10.1021_acs.langmuir.6b03119 p 1 | 1 | `bands.json` (applied: false) | the abstract field falls back to OpenAlex; the paragraph stays missing from the body |
| Author lines and "Check for updates" badges rendered as images, then OCR'd into the text | 25 band repairs in 20 papers: 2 captions, 4 abstracts, 1 table, 11 author lines, 7 badges | author lines and badges | recorded in `bands.json` | known limit (text added, nothing lost) |

`body_flags` (2026-10-13, 44 papers, script): 1,154 flags, 13 "line not found", 163 text-layer numbers missing from the
output paragraph, 978 output numbers absent from the text layer (761 of them the margin line numbers of 9b05116); 10 papers
without a flag. Against the page verdicts: 3 of 3 known real errors caught, 0 of the 41 known not-errors flagged. Not
checkable, reported per paper with the reason: 2,726 lines with an undecoded symbol-font glyph (AdvOT private-use
characters, AdvP4C4E74 cids, AdvPSMP10 letters: RSC, AIP and Wiley body text), 72 garbled lines of the MDPI duplicate
layer, 192 output sentences the layer does not cover, 37 paragraphs shared with a not-checkable unit, 22,022 rotated
characters. False flags remain (samples, not counted over the 44): stacked sub/superscripts written in another order
(O₂⁺, E₂¹g, n_0^t), inline equations kept in the output paragraph while their Equation box is excluded on the layer
side (10.3762_bjnano.5.25), a paragraph straddling a column break, enumeration numbers of a split paragraph
(10.1016_j.mee.2018.01.027), the MDPI duplicate-layer residue (74 flags). The rows above list the flags that were judged;
the other flags were not reviewed.

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
| Duplicated text layer: caption regions and some paragraphs drawn twice, the hidden copy at the page's top edge or shifted over other lines | 10.3390_separations11010024 (12 % of the characters on p 7; no other paper of the 44) | Docling repeated those captions (not used); the table check sees stray letters (one false flag); the body check drops 6,649 off-page and 1,183 shifted duplicate characters, reports 72 garbled lines as not checkable and still raises 74 flags, mostly false | known limit |
| Symbol-font glyphs of body text without a decoding (AdvOT private-use characters, AdvP4C4E74 cids, AdvPSMP10 letters) | RSC, AIP, Wiley papers (most: 10.1039_c7ta03257a, c5ta00205b, 10.1021_acsnano.5b03429, 10.1039_c3ra42928h) | 2,726 body lines not checkable by the body check (reason and count per paper in `body_check`) | known limit; decode on evidence when needed |
| Symbol fonts whose text layer gives letters (AdvPi2 "y" for θ) or subset glyph codes ((cid:3) is − in one paper and × in another) | RSC, AIP, Elsevier tables of 12 papers | decoded per font family / per embedded subset with evidence (`glyph_codes.json`); a code without a table makes the table "not checkable" | — |
| A rotated table | 10.1039_d0cp03358h Table 1 | not checkable (Marker read it; the header is shifted) | review |
| Figures placed after all captions (manuscript) | 10.1116_1.5116136 | bound by page order | — |
| Pages without a text layer (OCR-only regions) | 10.1039_c4nr05049e abstract, 10.1021_acs.chemmater.1c03164 headings, 10.1116_6.0003182 table (this one has a text layer in Marker's box) | Marker OCRs them itself; a table without a text layer is flagged | flag → review |
