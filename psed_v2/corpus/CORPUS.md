# Corpus

How the PSED v2 corpus was built: where the papers come from, what was added and removed, and why.
Numbers are from `corpus/manifest.csv` as of 2026-10-13. `manifest.csv` is the record; this file explains it.

## Summary

The corpus is built in three stages: collect candidates, exclude by criteria, collect PDFs.

```
Cremers 2019 references            299
  − table footnotes                 −7
                                   292

Works citing Cremers 2019          505   (OpenAlex, 2026-10-13, citing_filter.py)
  − no conformality keyword       −361
                                   144
  − preprints duplicating articles  −2
                                   142
  + missing from today's index      +1   (cites Cremers 2019; OpenAlex index lag)
                                   143

Added by hand                        1

Candidates                         436   (292 + 143 + 1; no paper is in more than one source)
  − excluded                      −175   (see Exclusions)
In scope                           261
  − no PDF yet                    −203   (pending library access)
With a PDF, parsed                  58
```

In short: 299 + 505 → 436 → 261 → 58.

## Sources

Candidates come from two published reviews and from the papers that cite one of them. Each paper keeps a mark (`O`) for every source it appears in, with the evidence (`popov_ref`, `cremers_ref`, `cremers_context`, `cites_cremers_keywords`, `extra_reason`). Rows are merged by DOI.

| Source | Rows | In current scope |
| --- | --- | --- |
| Cremers 2019 references | 292 | yes |
| Works citing Cremers 2019 | 143 | yes |
| Extra (added by hand) | 1 | yes |
| Popov 2025 Table I | 699 | no |

Overlaps: 8 papers are in both Popov and Cremers, 3 in both Popov and Cremers-citing.

### 1. Cremers 2019 references (seed)

Review: Cremers, Puurunen and Dendooven, "Conformality in atomic layer deposition: Current status overview of analysis and modelling", *Appl. Phys. Rev.* 6, 021302 (2019), doi:10.1063/1.5060967.

1. The reference list of the PDF (299 numbered entries) was parsed. Each DOI was taken from the link embedded in the PDF under that reference number (242 of 299 have one).
2. Seven entries that are table footnotes (structure dimensions, refs 136, 137, 142, 145, 147, 163, 179) were dropped. **292 rows.**
3. `cremers_context` records where the review cites each entry: Table II (thermal ALD conformality), III (ozone), IV (plasma), V (sticking probabilities), VIII and IX (models), or `text` (body only). Table rows were matched by the reference number at the end of each row; model tables by the superscript after the author name, so their tags may miss a few. Tables VI and VII (ozone and atom recombination) are not tagged.

The references enter without a topic filter, because the review's authors chose them for a conformality review. The exclusion criteria below apply to them as to the other sources.

### 2. Works citing Cremers 2019 (after 2019)

Cremers 2019 covers work up to early 2019. Later work enters through its citations. The rule below is fixed in `citing_filter.py`, and its output, one row per citing work with the outcome, is `cremers_citing_all.csv`.

1. **Search.** OpenAlex API, `/works?filter=cites:W2931684697` (the OpenAlex id of Cremers 2019), cursor paging to the end, run on 2026-10-13. **505 works.**
2. **Conformality keyword filter.** Kept if the title or the OpenAlex abstract (rebuilt from `abstract_inverted_index`) contains at least one of: conformal, conformality, aspect ratio, high-aspect-ratio, step coverage, trench, LHAR, PillarHall, penetration depth, saturation profile. Matching: case-insensitive; every hyphen character (ASCII or Unicode) and whitespace treated as one space; any prefix allowed (superconformal, ultrahigh-aspect-ratio); the keyword may end in s, es or ly and must then end the word, so conformality does not count as conformal. Works without an abstract are matched on the title alone. **144 works.** The matched words are in `cites_cremers_keywords`.
3. **Duplicates.** Preprints whose title matches a published article in the list were dropped (2). **142 works.**
4. **Index lag.** One manifest paper (10.3390/met13030528) is missing from the `cites:` index on 2026-10-13, although its own OpenAlex record still lists Cremers 2019 among its references. It is kept. **143 rows**, of which 3 are also in Popov.

**First pull and re-run.** The list was first pulled on 2026-10-01 (522 works, 152 passed, 9 duplicate preprints dropped, 143 rows); that script was not kept. On 2026-10-13 the filter was written down as `citing_filter.py` and re-run: all 143 manifest rows pass, and every passing work is either in the manifest or a duplicate preprint, so no paper was missed. The difference between 522 and 505 is a change in the OpenAlex index. The re-run also normalizes Unicode hyphens, which the first pull did not: this added keywords to 4 rows without changing any outcome, and moved one paper past the ALD term rule (10.1002/adem.202302257, see Exclusions).

`cremers_citing_all.csv` gives each of the 505 works an `outcome`: `no_keyword` 361, `in_manifest` 142, `duplicate_preprint` 2; `outcome_detail` holds the manifest status and reason, or the DOI of the article a preprint duplicates.

### 3. Extra

Added by hand, with the reason in `extra_reason`. One paper: 10.1021/acs.chemmater.2c01154, a core paper of the earlier pipeline that does not cite Cremers 2019. (Yim 2020, first added by hand, was later found among the citing works and is marked as Cremers-citing only.)

### 4. Popov 2025 Table I (out of the current scope)

Review: Popov et al., "Recent trends in thermal atomic layer deposition chemistry", *J. Vac. Sci. Technol. A* 43, 030801 (2025). Every first reference in Table I (new thermal ALD processes 2010–2023, from the AtomicLimits database): refs 14–712, 942 processes, 699 papers. DOIs from the links embedded in the reference list; 4 had none. Kept in the manifest for a possible later scope.

**Why two axes.** Popov 2025 covers process chemistry (which precursors and co-reactants deposit which material) for thermal ALD. Cremers 2019 and its citing works cover geometry: conformality in high-aspect-ratio structures. Plasma and ozone ALD papers entered through the geometry axis and were kept; their coverage is therefore limited to conformality.

## Scope

Current scope: **conformality only**. A paper is in scope if it comes from Cremers 2019, Cremers-citing or Extra and is not excluded. Popov-only papers stay in the manifest but are out of scope.

The rule is one line in `make_report.py` (`SCOPE_ORIGINS`), so the scope can change without editing rows.

## Exclusions

A paper is excluded for something about the paper itself, independent of scope. The same criteria apply to every source. Excluded rows stay in the manifest, with `reason`, `decision` (auto = by rule, manual = by a person) and `decided_on`. Rules run by script; for manual decisions, candidates and evidence were prepared by script and each decision was approved by the authors.

| Criterion | How it is decided | Decision | Cremers refs | Cremers-citing | Total |
| --- | --- | --- | --- | --- | --- |
| Not a publication | Cremers references that are footnotes, table notes or a private communication | auto | 28 | – | 28 |
| No DOI | Books, patents, theses, proceedings, judged from the citation text | manual | 22 | – | 22 |
| Not a research article | OpenAlex `type` other than `article` or `letter` (conference paper 5, book chapter 1, reference entry 1, dissertation 1) | auto | 4 | 4 | 8 |
| Not ALD | Neither title nor OpenAlex abstract matches `atomic[\s-]layer` or `\bALD\b` | auto | 33 | 19 | 52 |
| | Same rule, no OpenAlex abstract: judged from the title | manual | 12 | 2 | 14 |
| | Kept by the rule: Cremers references cited in Tables II–V, VIII or IX | – | (2 kept) | – | |
| | Shown by the parsed full text | manual | 2 | 1 | 3 |
| Review | (1) OpenAlex `type` is `review` | auto | 3 | 0 | 3 |
| | (2) Title has review, perspective, survey, overview or tutorial, or the journal is a review journal | auto | 7 | 8 | 15 |
| | (3) The OpenAlex abstract calls the paper a review, Account or essay | manual | 14 | 7 | 21 |
| | (4) The first pages of the parsed full text carry a review label or self-description | manual | 6 | 3 | 9 |
| **Total** | | | **131** | **44** | **175** |

A paper caught by more than one criterion is counted once, under the criterion that excluded it first.

**Details**

- **Not a publication**: refs 68, 71, 72, 74, 152, 155, 165, 167, 170, 175, 183, 188, 190, 193, 199, 207, 209, 214, 219, 223, 224, 227, 240, 289, 291, 292, 293, 296 (2026-10-01).
- **No DOI**: 12 books and patents, 10 theses, proceedings and book chapters (2026-10-01).
- **Not ALD, rule**: `ald_filter.py` lists the rows the rule excludes. Matching: `atomic[\s-]layer` case-insensitive, `\bALD\b` case-sensitive and whole word, Unicode hyphens normalized, OpenAlex abstracts only. Applied to Cremers-citing works on 2026-10-01 and to Cremers references on 2026-10-13; before that date the Cremers references had no ALD check. The Cremers references excluded are on O, N and H atom recombination (refs 250–263, the Table VII sources) and ozone decomposition (242, 243), CVD (17, 19, 20, 21, 84, 127, 269, 297), PVD and initiated CVD (10, 75, 76), deposition and flux models for CVD and PVD (267, 268, 284), gas transport theory (52, 54, 265, 285, 286, 287), etching and structure fabrication (117–121, 125), and others (73, 82, 130). Rows with a Cremers table tag are kept, because the review lists them as ALD data (refs 159 and 235 have no ALD term).
- **Not ALD, no abstract**: Cremers refs 52, 54, 82, 120, 125, 130, 251, 256, 263, 265, 268, 286 (gas transport theory, etching, structure fabrication, IUPAC porous-solids report, TDMAT crystal structure, atom recombination; ref 82's OpenAlex abstract is only the word "Abstract", so `ald_filter.py` lists it with the abstract rows, but it was judged from the title). Cremers-citing: Cu deposition on Ni trenches and ion-assisted trench filling.
- **Not ALD, full text**: W-CVD/SACVD through-silicon vias and SBA-15 silica synthesis (2026-10-03); 10.1002/adem.202302257 (2026-10-13), which passes the ALD term rule once Unicode hyphens are normalized ("atomic‐layer deposited protective film") but studies MLD films, with ALD only as a protective layer.
- **Review journals**: Chemical Reviews, Chemical Society Reviews, Coordination Chemistry Reviews, Applied Physics Reviews, Annual Review of *, Progress in Materials Science, Materials Science and Engineering R, Nature Reviews *.
- **Review by abstract** (2026-10-13): the abstract describes the paper itself as a review ("in this review", "this paper reviews", "is reviewed", "in this Account"); the matched phrase is in `reason`. Cremers refs 2, 3, 5, 8, 12, 28, 32, 33, 36, 38, 39, 43, 63, 231; Cremers-citing 10.1063/1.5113656, 10.1116/1.5142859, 10.1116/6.0000068, 10.1088/1361-6595/ac95bc, 10.1002/admi.202400262, 10.1002/sstr.70546, 10.3390/ma19132918.
- **Review by full text** (2026-10-03): journal labels such as REVIEW ARTICLE, MINIREVIEW or PERSPECTIVE, or a self-description. It runs again after each parsing run on newly collected PDFs.

**Kept by hand** (`status = included`, manual): Cremers ref 112, whose abstract describes separate saturated TMA and ammonia reactions, i.e. ALD under another name; and 10.1016/j.solmat.2025.114105 (ultrathin ZnO conformal coating), which has no abstract.

**Why reviews are excluded:** they report data from other papers, so keeping them would count the same experiment twice. **Why four review checks:** OpenAlex types most reviews as "article", so each check catches what the earlier ones miss.

Outside the scope, 10 Popov-only conference papers are also marked excluded by the type rule.

## Undecided

Seven in-scope papers have no decision yet (`status` blank). Each is judged from its first pages when its PDF comes.

| Ref | Question |
| --- | --- |
| Cremers 132 | Pt@MIL-101 catalyst: the title does not say how the Pt was deposited; no abstract. |
| Cremers 11, 15, 22, 31, 40, 64 | Possibly reviews by title or content, but the abstract does not call the paper a review. |

## In scope: 261 papers

- By source: Cremers 2019 only 153, Cremers-citing only 96, Popov and Cremers 8, Popov and Cremers-citing 3, Extra 1.
- All are OpenAlex type "article". Published up to 2019: 167; after 2019: 94.
- Where Cremers 2019 cites them (161 papers): experimental conformality tables (thermal, ozone, plasma) 91, sticking-probability and model tables 33 (a paper can be in both), body text only 52.

## PDFs

1. OpenAlex gives each DOI its open-access status, license and PDF link.
2. Open PDFs are downloaded by script (`fetch_pdfs.py`, identified user agent, about one request per second). Many publisher sites refuse scripted downloads; no attempt is made to get around this.
3. The rest come through Northwestern University Libraries access. A request for text-and-data-mining access and LLM use is pending with the library.

59 PDFs have been collected; 58 are in scope and 203 in-scope papers are still to collect. By how the file was obtained (`pdf_source`):

| How obtained | `pdf_source` | Collected | In scope |
| --- | --- | --- | --- |
| OpenAlex best location, by script | `openalex` | 34 | 34 |
| Alternate OpenAlex location, by script | `openalex_alt` | 8 | 8 |
| Copied from the earlier pipeline | `v1_copy` | 2 | 2 |
| Obtained by hand from the publisher through library access (2026-10-13) | `library_manual` | 15 | 14 |

The one collected PDF out of scope is Cremers ref 251 (10.1016/j.cattod.2003.11.022, oxygen recombination, excluded as not ALD). Its file stays in `raw/`, as for every excluded row, because the cases cite its Table VII value.

"Obtained by hand" is about the PDF of a paper that was already a candidate. It is separate from the "Extra (added by hand)" source, which is about how a paper became a candidate.

Of the 44 obtained by script or copied, OpenAlex marks all as open access (hybrid 22, green 10, bronze 6, gold 5, diamond 1); version: published 28, submitted (author manuscript) 16. The 15 obtained by hand are the published version; OpenAlex marks 8 of them as closed, 5 bronze, 1 green and 1 hybrid. Licenses of the 59: CC BY 18, CC BY-NC 2, CC BY-NC-ND 3, public domain 1, other open access 10, none 25.

Open-access status is recorded, not used as a filter. Only extracted data (conditions, digitized values, provenance) is shared. PDFs, parsed text and figure crops are never committed to git and are redistributed only where the license allows.

## Files

| File | Content |
| --- | --- |
| `manifest.csv` | One row per candidate: metadata, source marks and evidence, scope, decision, PDF status. The record. |
| `report.csv` | Reader-facing view of the manifest, generated by `make_report.py`. |
| `manual_list.csv` | In-scope papers without a PDF, generated by `fetch_pdfs.py`. |
| `cremers_citing_all.csv` | Every work citing Cremers 2019 (2026-10-13), with matched keywords, whether it passed, `outcome` and `outcome_detail`; the works filtered out are here. |
| `fetch_pdfs.py` | OpenAlex lookup and open-access download. |
| `citing_filter.py` | Fetches the works citing Cremers 2019 and applies the keyword rule; writes `cremers_citing_all.csv`. |
| `ald_filter.py` | The not-ALD rule: lists the rows of both sources with no ALD term in title or OpenAlex abstract. |
| `make_report.py` | Holds the scope rule; writes `in_scope` and `report.csv`. |
| `raw/` | PDFs, one per paper (`<doi with / as _>.pdf`). Not in git. |

## History

| Date | Change |
| --- | --- |
| 2026-09-30 | Popov 2025 Table I parsed: 699 papers. First OpenAlex lookup and downloads. |
| 2026-09-30 | Cremers 2019 references added (292); geometry axis. |
| 2026-10-01 | Cremers-citing works added (143, first pull of 522). Exclusions: not ALD (Cremers-citing), not a publication, no DOI, document type, review by title or journal. |
| 2026-10-01 | Scope set to conformality only; Popov-only papers out of scope. |
| 2026-10-03 | Reviews found in full text (9) and non-ALD papers (2) excluded after parsing. |
| 2026-10-13 | Keyword filter written down as `citing_filter.py` and re-run (505 citing works, 144 pass; no paper missed). Unicode hyphens now normalized; 10.1002/adem.202302257 re-judged by hand (MLD study), still excluded. |
| 2026-10-13 | 15 PDFs obtained by hand through library access and parsed: 44 → 59 PDFs. |
| 2026-10-13 | The not-ALD rule extended to Cremers references (45 excluded, ref 112 kept by hand), written down as `ald_filter.py`; reviews found from the abstract (21) excluded. In scope 327 → 261, with a PDF 58. |
