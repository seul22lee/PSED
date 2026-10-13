# Ingest numbers (44 in-scope papers with a PDF; written by ingest/numbers_md.py from the final output)

One table; every number in INGEST, ERRORS and the plan must match it. "structure.json" means the sum over
`ingest/final/<paper_id>/structure.json`. Judged numbers come from the answer set `ingest/answers/` (Claude Code's
page judgements) and are marked as such; two recorded numbers name their origin.

| Item | Number | Source |
|---|---|---|
| Papers ingested | 44 | `ingest/final/` (manifest `marker` = ok) |
| **Tables** total | 69 | structure.json `captions[kind=table]` |
| Tables `check` = flag | 34 | structure.json `captions[].check` |
| Tables `check` = ok | 34 | structure.json `captions[].check` |
| Tables `check` = not checkable | 1 | structure.json `captions[].check` |
| Tables wrong on the page (judged) | 28 of 69; 27 of them flagged, 1 not checkable; 7 right tables flagged | `answers/tables.json` against `check` |
| **Equations** pairs | 321 | structure.json `equations` |
| Equations `agree` | 197 | structure.json `equations[].status` |
| Equations `differ` | 109 | structure.json `equations[].status` |
| Equations single tool | 15 (12 docling only, 3 marker only) | structure.json `equations[].status` |
| Equation pairs judged (answer set, 44 papers) | 198 items: 74 agree accepted (not judged); 109 differ pairs judged on the crop: Marker right 44, Docling right 33, both wrong 16, equivalent 16; 15 single-tool items judged: Docling right 9, Docling wrong 3, Marker right 3, Marker wrong 0 | `answers/equations.json` |
| **Body** lines read | 23,935 | structure.json `body_check.counts.lines` |
| Body lines checked | 23,779 (99.3 %; median 100 % per paper, min 82 %) | structure.json `body_check.counts.checked` |
| Body lines not checkable, total | 156 (every one covered by a layer-side "not checkable" flag) | structure.json `body_check.counts`, `body_flags` |
| not checkable: unit under 4 words | 67 | structure.json `body_check.counts` |
| not checkable: garbled text-layer line (overlapping duplicate layer) | 83 | structure.json `body_check.counts` |
| not checkable: unit too short to locate in the output (fewer than 3 words) | 4 | structure.json `body_check.counts` |
| not checkable: undecoded glyph | 2 | structure.json `body_check.counts` |
| Output sentences not covered by the text layer (numbers not compared) | 55, each an output-side flag | structure.json `body_check.counts` |
| Output paragraphs blocked by an undecoded glyph in an equation or neighbour line | 38, each an output-side flag | structure.json `body_check.counts` |
| Output paragraphs with numbers matched by no unit (counted, not flagged) | 1,573 (read-only recount 2026-10-13: 1,046 at or after the References heading; before it 527: 294 equations, 127 author/affiliation/licence/furniture lines, 91 headings/labels/fragments, 9 captions, 4 author lists read as text, 2 reaction table rows) | structure.json `body_check.counts`; kinds recorded |
| Units recovered by the lookup near the previous match | 325 (short units 303: 292 exact, 11 without spaces; garbled lines 22: 11 without spaces, 11 by similarity) | structure.json `body_check.recovered` |
| Rotated characters (not read) | 22,022 | structure.json `body_check.counts` |
| **Body flags** (number or letter kinds) | 238 | structure.json `body_flags` |
| flags: number of the text layer missing from the output paragraph | 120 | structure.json `body_flags[].kind` |
| flags: number of the output paragraph absent from the text layer | 102 | structure.json `body_flags[].kind` |
| flags: line not found in the output | 12 | structure.json `body_flags[].kind` |
| flags: letters of the text layer differ from the output | 4 | structure.json `body_flags[].kind` |
| flags cropping the paragraph block / the line | 132 / 106 | structure.json `body_flags[].crop_scope` |
| Body flags judged (answer set) | 238 of 238: 78 real, 160 not errors (precision 33 %) | `answers/body_flags.json` against `body_flags` |
| Answer-set body flag keys (all passes) | 419: 129 real, 290 not errors | `answers/body_flags.json` |
| Papers without a number flag | 12 | structure.json `body_flags` |
| **Not-checkable flags** | 268: layer side 175, output side 93 | structure.json `body_flags[kind=not checkable]` |
| **Repairs** applied | 12 records (5 R1 numbers replaced, 7 R2 lines restored), 0 undone | structure.json `body_repairs`, `body_repairs_undone` |
| Distinct real body errors (judged) | 44: 10 dropped text, 8 citations, 6 letter/digit, 5 lookalike letters, 4 digits, 3 subscripts, 3 text added, 2 decimal points, 1 exponent sign, 1 caption label out of order, 1 margin numbers (ingest/ERRORS.md, judged on crops) | `answers/body_flags.json` verdicts grouped by error, classes recorded from ERRORS.md |
| Distinct real errors corrected / partly / flagged only | 8 corrected (each viewed on its crop), 1 partly (10.1186_s11671-015-0872-9 Figure 1 caption: 2 of 3 lines restored), 35 flagged only (one of them, the margin numbers, removed by line_numbers.py with 5 leftovers flagged) | `body_repairs`, `body_flags`, recorded |
| Margin line numbers removed | 1,044 in 1 paper, 5 real numbers kept | structure.json `body_check.line_numbers` |
| Band repairs (parse_marker.py --bands) | 25 applied of 32 records | `marker/<id>/bands.json` |
| Abstracts | 44: 23 heading, 20 openalex_match, 1 openalex | structure.json `abstract_source` |
| Figure captions | 445 (342 numbered, 103 unnumbered pictures); other kinds: 2 scheme | structure.json `captions[kind=figure]` and the other non-table kinds |
| Glyph table | 198 entries (19 families, 43 subsets), 6 groups left undecoded with the reason | `glyph_codes.json` |

## Per paper (body check)

| paper | body lines read | checked | share | not checkable: undecoded glyph (lines) | rotated (characters) | other not checkable (lines/sentences) | number or letter flags | not-checkable flags | repairs |
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
| 10.1116_6.0001094 | 898 | 896 | 100 % | 2 | 0 | 1 | 9 | 22 | 0 |
| 10.1116_6.0001679 | 236 | 235 | 100 % | 0 | 0 | 4 | 1 | 4 | 0 |
| 10.1116_6.0002804 | 423 | 416 | 98 % | 0 | 189 | 7 | 0 | 7 | 0 |
| 10.1116_6.0002993 | 382 | 382 | 100 % | 0 | 168 | 0 | 2 | 0 | 0 |
| 10.1116_6.0003182 | 719 | 719 | 100 % | 0 | 252 | 1 | 3 | 1 | 0 |
| 10.1149_2.067203jes | 721 | 720 | 100 % | 0 | 116 | 5 | 14 | 9 | 0 |
| 10.1186_s11671-015-0872-9 | 271 | 271 | 100 % | 0 | 0 | 0 | 6 | 0 | 2 |
| 10.3390_separations11010024 | 646 | 529 | 82 % | 0 | 0 | 123 | 16 | 123 | 0 |
| 10.3762_bjnano.5.25 | 495 | 495 | 100 % | 0 | 0 | 1 | 0 | 1 | 0 |
