# Extraction supplementation — nine papers

Policy: existing extraction first; local recovery only where scientific evidence exists in
the PDF but not in the extraction. **0 API calls** (`logs/api_calls.json` is `[]`).

| paper | supplementation | tool | why |
|---|---|---|---|
| `10.1038_am.2016.182` | printed Fig 4 recovered as 5 caption-only Measurements | pilot caption parser | production's `_PANEL_HEAD` rejects the spaced marker `( a )`, so the whole figure had no caption and never reached extraction |
| `10.1149_2.067203jes` | printed Fig 8 recovered as an image-supported ExperimentalCase (HAR trench, AR ~30, 830 cycles, 18.5 × 0.6 µm) | pilot caption parser + range parser | the figure is an SEM image, so no x-y data exists; the caption carries the full process and geometry |
| `10.1039_c7ta03257a` | printed Fig 8(b) recovered as a caption-only Measurement, PDF page rendered as visual evidence | PyMuPDF page render | Docling emitted no PictureItem for that panel |
| `10.1039_d0cp03358h` | Table 1 rebuilt from PDF reading order — 16 specimens with their series and conditions | PyMuPDF text extraction | Docling's export of the rotated table is transposed and column-merged |
| `cremers2019` | none | — | existing extraction sufficient; the semantic work was routing, not recovery |
| `10.1039_d0ra09876k` | none | — | existing extraction sufficient |
| `10.1039_c5ta00205b` | none | — | existing extraction sufficient |
| `10.1021_acs.langmuir.6b03119` | none | — | existing extraction sufficient |
| `10.1039_d0ra01602k` | 1 image-supported case detected from a figure caption reporting a deposition on a described structure | pilot caption parser | no x-y data for that figure |

**No points were invented anywhere.** Every recovered object carries
`data_recovered: false` and an empty `result_series_ids`. Source curve counts and
digitised point counts are identical to production on all nine papers.

**No extraction branch had to be stopped for want of an API.** The vision pipeline was not
needed: every recovery above is a caption, a table or a page render.
