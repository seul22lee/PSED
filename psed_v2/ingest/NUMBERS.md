# Ingest numbers (58 in-scope papers with a PDF; written by ingest/numbers_md.py from the final output)

One table; every number in INGEST, ERRORS and the plan must match it. "structure.json" means the sum over
`ingest/final/<paper_id>/structure.json`. The first number column is the 58 in-scope papers (manifest `in_scope` = yes),
which the answer set `ingest/answers/` (Claude Code's page judgements) covers in full: every judged number (tables wrong
on the page, equation verdicts, body flags real or not, distinct real errors) holds for them. The second column is
10.1016_j.cattod.2003.11.022 (Guyon 2004: ingested, excluded from the scope as not an ALD paper, not judged); it stands on its own and is
in no total. One recorded number names its origin (the kinds of the unmatched paragraphs, recounted for the first 44 papers).

| Item | 58 in scope | Guyon 2004 (out of scope) | Source |
|---|---|---|---|
| Papers ingested | 58 | 1 | `ingest/final/` (manifest `marker` = ok) |
| **Tables** total | 90 | 2 | structure.json `captions[kind=table]` |
| Tables `check` = flag | 43 | 2 | structure.json `captions[].check` |
| Tables `check` = ok | 46 | 0 | structure.json `captions[].check` |
| Tables `check` = not checkable | 1 | 0 | structure.json `captions[].check` |
| Tables wrong on the page (judged) | 33 of 90 judged; reaching the review 32 (31 flagged, 1 not checkable), missed with `check` = ok 1; 12 right tables flagged | not judged (out of scope) | `answers/tables.json` against `check` |
| **Equations** pairs | 434 | 24 | structure.json `equations` |
| Equations `agree` | 254 | 11 | structure.json `equations[].status` |
| Equations `differ` | 158 | 11 | structure.json `equations[].status` |
| Equations single tool | 22 (17 docling only, 5 marker only) | 2 (2 docling only, 0 marker only) | structure.json `equations[].status` |
| Equation pairs judged (answer set) | 254 items: 74 agree accepted (not judged); 158 differ pairs judged on the crop: Marker right 74, Docling right 39, both wrong 18, equivalent 27; 22 single-tool items judged: Docling right 10, Docling wrong 7, Marker right 5, Marker wrong 0 | not judged (out of scope) | `answers/equations.json` |
| **Body** lines read | 30,683 | 364 | structure.json `body_check.counts.lines` |
| Body lines checked | 30,516 (99.5 %; median 100 % per paper, min 82 %) | 308 (84.6 %; median 85 % per paper, min 85 %) | structure.json `body_check.counts.checked` |
| Body lines not checkable, total | 167 (every one covered by a layer-side "not checkable" flag) | 56 (every one covered by a layer-side "not checkable" flag) | structure.json `body_check.counts`, `body_flags` |
| not checkable: unit under 4 words | 73 | 50 | structure.json `body_check.counts` |
| not checkable: garbled text-layer line (overlapping duplicate layer) | 85 | 0 | structure.json `body_check.counts` |
| not checkable: unit too short to locate in the output (fewer than 3 words) | 4 | 1 | structure.json `body_check.counts` |
| not checkable: undecoded glyph | 5 | 5 | structure.json `body_check.counts` |
| Equation lines with an undecoded glyph (the extra direction of their paragraph blocked) | 67, each a layer-side flag | 6, each a layer-side flag | structure.json `body_flags[kind=not checkable]` |
| Output sentences not covered by the text layer (numbers not compared) | 59, each an output-side flag | 9, each an output-side flag | structure.json `body_check.counts` |
| Output paragraphs blocked by an undecoded glyph in an equation or neighbour line | 103, each an output-side flag | 11, each an output-side flag | structure.json `body_check.counts` |
| Output paragraphs with numbers matched by no unit (counted, not flagged) | 1,867 (kinds from a read-only recount of the first 44 papers on 2026-10-13: 1,046 at or after the References heading; before it 527: 294 equations, 127 author/affiliation/licence/furniture lines, 91 headings/labels/fragments, 9 captions, 4 author lists read as text, 2 reaction table rows) | 29 | structure.json `body_check.counts`; kinds recorded |
| Units recovered by the lookup near the previous match | 430 (short units 402: 389 exact, 13 without spaces; garbled lines 28: 12 without spaces, 16 by similarity) | 34 (short units 34: 32 exact, 2 without spaces; garbled lines 0: 0 without spaces, 0 by similarity) | structure.json `body_check.recovered` |
| Rotated characters (not read) | 25,823 | 0 | structure.json `body_check.counts` |
| **Body flags** (number or letter kinds) | 344 | 30 | structure.json `body_flags` |
| flags: number of the text layer missing from the output paragraph | 171 | 6 | structure.json `body_flags[].kind` |
| flags: number of the output paragraph absent from the text layer | 147 | 18 | structure.json `body_flags[].kind` |
| flags: line not found in the output | 18 | 6 | structure.json `body_flags[].kind` |
| flags: letters of the text layer differ from the output | 8 | 0 | structure.json `body_flags[].kind` |
| flags cropping the paragraph block / the line | 171 / 173 | 17 / 13 | structure.json `body_flags[].crop_scope` |
| Body flags judged (answer set) | 344 of 344: 106 real, 238 not errors (precision 31 %) | not judged (out of scope) | `answers/body_flags.json` against `body_flags` |
| Answer-set body flag keys (all passes) | 512: 152 real, 360 not errors | not judged (out of scope) | `answers/body_flags.json` |
| Papers without a number flag | 17 | 0 | structure.json `body_flags` |
| **Not-checkable flags** | 396: layer side 233, output side 163 | 82: layer side 62, output side 20 | structure.json `body_flags[kind=not checkable]` |
| **Repairs** applied | 15 records (7 R1 numbers replaced, 8 R2 lines restored), 0 undone | 0 records (0 R1 numbers replaced, 0 R2 lines restored), 0 undone | structure.json `body_repairs`, `body_repairs_undone` |
| Distinct real body errors (judged, a lower bound) | 58: 12 dropped text, 8 citations, 7 letter/digit, 6 lookalike letters, 6 digits, 5 text added, 3 subscripts, 2 decimal points, 2 prescripts of J, 2 affiliation marks, 1 exponent sign, 1 caption label out of order, 1 caption label fused, 1 letter case, 1 margin numbers (ingest/ERRORS.md, judged on crops; the 14 of the papers added on 2026-10-13 carry distinct_error in answers/body_flags.json) | not judged (out of scope) | `answers/body_flags.json` verdicts grouped by error, classes recorded from ERRORS.md |
| Distinct real errors corrected / partly / flagged only | 9 corrected (each viewed on its crop; 10.1021_cm0303080 p11 t^4 → t^1 by R1), 2 partly (10.1186_s11671-015-0872-9 Figure 1 caption: 2 of 3 lines restored; 10.1021_cm0303080 p2: 1 line of the dropped references restored by R2), 47 flagged only (one of them, the margin numbers, removed by line_numbers.py with 5 leftovers flagged) | not judged (out of scope) | `body_repairs`, `body_flags`, recorded |
| Margin line numbers removed | 1,044 in 1 paper, 5 real numbers kept | 0 in 0 paper, 0 real numbers kept | structure.json `body_check.line_numbers` |
| Band repairs (parse_marker.py --bands) | 29 applied of 37 records | 0 applied of 0 records | `marker/<id>/bands.json` |
| Abstracts | 58: 30 openalex_match, 27 heading, 1 openalex | 1: 1 heading | structure.json `abstract_source` |
| Figure captions | 630 (451 numbered, 179 unnumbered pictures); other kinds: 2 scheme | 8 (6 numbered, 2 unnumbered pictures) | structure.json `captions[kind=figure]` and the other non-table kinds |
| Glyph table | 521 entries (25 families, 78 subsets), 7 groups left undecoded with the reason | one table for all papers | `glyph_codes.json` |

## Per paper (body check)

| paper | body lines read | checked | share | not checkable: undecoded glyph (lines) | rotated (characters) | other not checkable (lines/sentences) | number or letter flags | not-checkable flags | repairs |
|---|---|---|---|---|---|---|---|---|---|
| 10.1002_adem.202201901 | 749 | 749 | 100 % | 0 | 3759 | 2 | 5 | 15 | 1 |
| 10.1002_cvde.200390005 | 472 | 471 | 100 % | 1 | 25 | 1 | 8 | 20 | 0 |
| 10.1007_s12274-010-0066-9 | 352 | 351 | 100 % | 0 | 0 | 2 | 0 | 2 | 0 |
| 10.1016_j.apsusc.2009.02.055 | 210 | 210 | 100 % | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1016_j.apsusc.2010.01.025 | 304 | 304 | 100 % | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1016_j.ijpharm.2017.04.031 | 635 | 635 | 100 % | 0 | 0 | 1 | 4 | 1 | 0 |
| 10.1016_j.mee.2018.01.027 | 269 | 269 | 100 % | 0 | 0 | 4 | 2 | 4 | 0 |
| 10.1016_j.mee.2018.01.033 | 217 | 217 | 100 % | 0 | 0 | 0 | 0 | 0 | 0 |
| 10.1016_j.sse.2022.108584 | 363 | 363 | 100 % | 0 | 44 | 0 | 0 | 0 | 0 |
| 10.1016_j.surfcoat.2012.02.038 | 401 | 399 | 100 % | 2 | 248 | 1 | 10 | 21 | 0 |
| 10.1021_acs.chemmater.1c03164 | 944 | 941 | 100 % | 0 | 0 | 3 | 1 | 3 | 1 |
| 10.1021_acs.chemmater.2c01154 | 926 | 925 | 100 % | 0 | 1625 | 5 | 15 | 5 | 1 |
| 10.1021_acs.chemmater.6c00816 | 1198 | 1197 | 100 % | 0 | 2520 | 2 | 5 | 2 | 0 |
| 10.1021_acs.chemmater.9b05116 | 754 | 751 | 100 % | 0 | 297 | 7 | 41 | 7 | 2 |
| 10.1021_acs.jpcc.1c01505 | 605 | 600 | 99 % | 0 | 1134 | 6 | 14 | 6 | 0 |
| 10.1021_acs.jpcc.5c06502 | 676 | 674 | 100 % | 0 | 1536 | 2 | 10 | 2 | 2 |
| 10.1021_acs.jpcc.9b08176 | 367 | 364 | 99 % | 0 | 822 | 4 | 9 | 4 | 0 |
| 10.1021_acs.jpclett.4c03545 | 269 | 269 | 100 % | 0 | 147 | 0 | 0 | 0 | 0 |
| 10.1021_acs.langmuir.6b03119 | 502 | 499 | 99 % | 0 | 1136 | 3 | 4 | 3 | 0 |
| 10.1021_acsami.0c06879 | 481 | 481 | 100 % | 0 | 201 | 0 | 0 | 0 | 0 |
| 10.1021_acsami.0c22121 | 301 | 301 | 100 % | 0 | 0 | 2 | 7 | 2 | 0 |
| 10.1021_acsnano.5b03429 | 473 | 473 | 100 % | 0 | 980 | 1 | 0 | 1 | 0 |
| 10.1021_cm0303080 | 906 | 903 | 100 % | 0 | 1386 | 4 | 13 | 4 | 2 |
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
| 10.1063_1.2714685 | 421 | 421 | 100 % | 0 | 168 | 0 | 1 | 21 | 0 |
| 10.1063_1.4972120 | 636 | 636 | 100 % | 0 | 189 | 0 | 10 | 5 | 0 |
| 10.1063_1.5028178 | 410 | 410 | 100 % | 0 | 171 | 1 | 1 | 1 | 0 |
| 10.1063_5.0168768 | 308 | 307 | 100 % | 0 | 126 | 5 | 2 | 13 | 0 |
| 10.1093_nsr_nwaf247 | 849 | 849 | 100 % | 0 | 1730 | 0 | 0 | 9 | 0 |
| 10.1116_1.4892385 | 493 | 493 | 100 % | 0 | 184 | 2 | 0 | 2 | 0 |
| 10.1116_1.4903941 | 285 | 285 | 100 % | 0 | 126 | 0 | 5 | 0 | 0 |
| 10.1116_1.4971196 | 522 | 522 | 100 % | 0 | 231 | 1 | 0 | 13 | 0 |
| 10.1116_1.5116136 | 202 | 202 | 100 % | 0 | 3213 | 1 | 5 | 1 | 0 |
| 10.1116_6.0001094 | 898 | 896 | 100 % | 2 | 0 | 1 | 9 | 22 | 0 |
| 10.1116_6.0001679 | 236 | 235 | 100 % | 0 | 0 | 4 | 1 | 4 | 0 |
| 10.1116_6.0002804 | 423 | 416 | 98 % | 0 | 189 | 7 | 0 | 7 | 0 |
| 10.1116_6.0002993 | 382 | 382 | 100 % | 0 | 168 | 0 | 2 | 0 | 0 |
| 10.1116_6.0003182 | 719 | 719 | 100 % | 0 | 252 | 1 | 3 | 1 | 0 |
| 10.1149_1.2789802 | 365 | 365 | 100 % | 0 | 0 | 0 | 13 | 16 | 0 |
| 10.1149_1.3072694 | 341 | 341 | 100 % | 0 | 103 | 0 | 10 | 9 | 0 |
| 10.1149_1.3301664 | 487 | 487 | 100 % | 0 | 182 | 0 | 22 | 8 | 0 |
| 10.1149_1.3491381 | 793 | 793 | 100 % | 0 | 9 | 0 | 4 | 5 | 1 |
| 10.1149_2.067203jes | 721 | 720 | 100 % | 0 | 116 | 5 | 14 | 9 | 0 |
| 10.1186_s11671-015-0872-9 | 271 | 271 | 100 % | 0 | 0 | 0 | 6 | 0 | 2 |
| 10.3390_separations11010024 | 646 | 529 | 82 % | 0 | 0 | 123 | 16 | 123 | 0 |
| 10.3762_bjnano.5.25 | 495 | 495 | 100 % | 0 | 0 | 1 | 0 | 1 | 0 |
| **total, 58 in scope** | 30,683 | 30,516 | 99 % | 5 | 25,823 | 222 | 344 | 396 | 15 |
| 10.1016_j.cattod.2003.11.022 (out of scope, in no total) | 364 | 308 | 85 % | 5 | 0 | 60 | 30 | 82 | 0 |
