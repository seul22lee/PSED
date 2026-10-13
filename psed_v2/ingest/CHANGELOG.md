# Ingest history (summary; the record is `git log -- psed_v2/ingest`, 40 commits, 2026-10-01 to 2026-10-13)

- 2026-10-01 to 03: corpus decisions (reviews and non-articles excluded) and a Docling-based parse, later replaced.
- 2026-10-12: Marker stage with band-crop OCR (dbc2c43, 2d53705); structure.json from Marker's blocks (31ca1cb, 0e2d59c); Docling kept for equations only, R1/R2 crops (1bb790d); abstract rules with the OpenAlex fallback (6c5cafa to 9e87def); the Docling stage removed (25b9ea0).
- 2026-10-13: table check on the decoded text layer, `glyph_codes.json` (cf783e0); body-number flags (e69310f); body verification, `line_numbers.py`, `body_repair.py` (fa7e735); the answer set `ingest/answers/` (f35fa71).
- 2026-10-13: glyph table pass 2, every undecoded body glyph viewed on crops (fdbd9f5); repairs with one distinct position each and a recheck (e5cb97c).
- 2026-10-13: short units and garbled lines looked up near the previous match, output-side not-checkable flags, paragraph crops (b4306e9); a subscript attachment rule tried in b4306e9 and reverted in f94e9f0 (it altered the reference text).
- Each change log line in the old INGEST.md names its commit; the measurement sequence of the body check (1,154 flags → 238) is in that log.
- 2026-10-13: ingest closed: stale outputs and reports deleted, the report and check scripts moved into the repo (report_papers.py, report_body.py, numbers_md.py, regression.py), the final INGEST.md, ERRORS.md and NUMBERS.md written, the plan's phase order set to ingest → ontology → schema.
- 2026-10-13: 15 papers added (PDFs obtained by hand through library access): Marker, bands, Docling formulas, structure, merge for these 15 only; the 44 earlier outputs unchanged (checksums) and regression.py passes; NUMBERS.md now has three columns (59, the first 44, the 15) and says that the answer set covers the 44 only; no new flag judged, glyph table not extended (58 % of the body lines of the 15 checked).
