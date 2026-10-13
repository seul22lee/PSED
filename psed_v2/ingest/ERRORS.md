# Ingest: remaining errors after the rules

What is still wrong in the final output (`ingest/final/<paper_id>/`) after the rules of 2026-10-12, from
the 13 Marker papers (one per DOI prefix of the 44 in scope), judged on the PDF pages and crops by
Claude Code (commit in the change log of `INGEST.md`). Per error type: an example, the count on the
13 papers, whether a rule check flags it, and how it is handled. Handling: **flag → review** = the
`check` field of the table entry is `flag`, a vision model reads the crop at extract time;
**differ → review** = the equation pair has `status: differ`, a person or a vision model decides at
extract time; **known limit** = nothing flags it; the KB must tolerate it.

## Body text (Marker)

| Error | Example | Count | Flagged | Handling |
|---|---|---|---|---|
| Angle brackets dropped by Marker's renderer: "<001>" written "001" | 10.1002_adem.202201901, p 10 | 1 number in 13 papers | no | known limit |
| Two-column page read right column first for one block | 10.1186_s11671-015-0872-9, p 4 | 1 page in 13 papers | no | known limit |
| Author line or "Check for updates" badge rendered as an image, then OCR'd by the band repair as text | 10.1021_acs.jpcc.9b08176 p 1, 10.1116_6.0002993 p 2, 10.3390_separations11010024 p 1 | 3 author lines, 3 badges | recorded in `bands.json` | known limit (text added, nothing lost) |

Figures, captions and the abstract have no remaining error on the 13 papers after the band-crop OCR
(captions drawn inside the picture: 10.1186_s11671-015-0872-9 Figures 1 and 3; abstract beside the
TOC graphic: 10.1021_acs.jpcc.9b08176).

## Tables (Marker, 16 numbered tables in the 13 papers)

| Error | Example | Count | Flagged | Handling |
|---|---|---|---|---|
| An extra empty column: Marker's header colspans sum to one more than the body has | 10.3390_separations11010024 Tables A1, A2 (p 14), A4 (p 15) | 3 | yes (header colspans vs body columns) | flag → review |
| Header shifted by one column: a sub-header cell lost ("[K]") | 10.3390_separations11010024 Table A3, p 14 | 1 | yes (letters, empty trailing header, colspans) | flag → review |
| A symbol misread ("l" for "I") and a wrong exponent sign in a unit (cm^-2 for cm^2) | 10.3762_bjnano.5.25 Table 2, p 10 | 1 | yes (numbers, letters) | flag → review |
| Right table flagged: footnotes inside Marker's table box | 10.1021_acs.jpcc.9b08176 Table 1, p 4 | 1 | — | review finds nothing wrong |
| Right table flagged: a minus drawn from an unmapped glyph in the PDF text layer | 10.1063_1.5028178 Table I, p 8 | 1 | — | review finds nothing wrong |
| Right table flagged: the MDPI hidden duplicate text layer puts stray letters in the box | 10.3390_separations11010024 Table 1, p 11 | 1 | — | review finds nothing wrong |

Check result on the 16 tables: 5 wrong tables flagged, 0 missed, 3 right tables flagged (11 of 16
are fully right). Undetectable by the checks, not seen on the 13 papers but possible: a caption bound
to the wrong table (the caption is outside the box the check reads), a pure column shift with every
token present and the header and body column counts equal, and tables on pages without a usable text
layer (scanned PDFs), which the check flags wholesale (`no text layer in the table box`).

Fixed on 2026-10-12, no longer errors: trailing zeros dropped by tabulate's number parsing (0.10 →
0.1, 8.0 → 8; 7 cells in 5 tables), Greek letters in headers (they were always in Marker's output as
LaTeX, `\beta_0`; the comparison stripped them).

## Equations (Docling CodeFormula on R1/R2 crops + Marker, 103 pairs in the 13 papers)

| Error | Example | Count | Flagged | Handling |
|---|---|---|---|---|
| Marker's LaTeX wrong where Docling's is right (symbol, missing term, scope of a root) | 10.1002_adem.202201901 eq (9), p 8: ν for v | 14 pairs | yes (`differ`) | differ → review |
| Docling's LaTeX wrong where Marker's is right (symbol, junk text, a term missing) | 10.3390_separations11010024 eq (3), p 6: "lare" for "layer" | 7 pairs | yes (`differ`) | differ → review |
| Both wrong | 10.1063_1.5028178 eq (32), p 6 | 3 pairs | yes (`differ`) | differ → review |
| Equivalent forms or alignment markup only | 10.1063_1.5028178 eq (10), p 4: 4/h·RT/N_0 vs 4RT/(hN_0) | 5 pairs | yes (`differ`) | differ → review (nothing wrong) |
| Equation present in one tool only | — | 0 on the 13 papers | yes (`docling only` / `marker only`) | review |

74 of the 103 pairs agree. The R1 crop (tight formula box, 216 dpi) fixed 18 Docling equations and
broke 1 (10.1063_1.5028178 eq (20)); the R2 band box fixed 12 of the 19 Beilstein equations whose
Docling box held only the number; the remaining Docling errors are CodeFormula's reading of the crop.
Marker's own equations were not re-recognised: on its own box at 216 dpi that fixed 2 and broke 13.

## Input limits seen on the 13 papers

| Limit | Example | Effect | Handling |
|---|---|---|---|
| Duplicated text layer: caption regions and some paragraphs drawn twice in two fonts, 9 pt apart | 10.3390_separations11010024 (12 % of the characters on p 7; none of the other 12 papers) | Docling repeats those captions 2–3× (not used by final); the table check sees stray letters (one false flag) | known limit |
| Layout reading order with a left sidebar | 10.3762_bjnano.5.25 p 1, 10.1093_nsr_nwaf247 p 1 | Docling reads the sidebar before the title (not used by final); Marker reads the print order | — |
| Pages without a text layer (OCR-only regions) | none among the 13; in the 44: 10.1039_c4nr05049e abstract, 10.1021_acs.chemmater.1c03164 headings, 10.1116_6.0003182 table | Marker OCRs them itself; the table check cannot compare and flags such tables | flag → review |
