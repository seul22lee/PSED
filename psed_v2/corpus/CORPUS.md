# Corpus

How the PSED v2 corpus was built: where the papers come from, what was added and removed, and why.
Numbers are from `corpus/manifest.csv` as of 2026-10-13, after 15 PDFs were obtained by hand on that day. `manifest.csv` is the record; this file explains it.

## Summary

The corpus is built in three stages, and the count goes down at each step.

**1. Collect candidates: 436**

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
```

**2. Exclude: 327**

```
Candidates                         436
  − Step 1, rules (auto)           −73   not ALD 19, not a publication 28,
                                         not a research article 11, review by title/journal 15
                                   363
  − Step 2, rules could not decide −24   no DOI 22, no ALD term and no abstract 2 (1 more kept)
                                   339
  − Step 3, rules missed           −12   review in full text 9, not ALD in full text 3
In scope                           327
```

**3. Collect PDFs: 59**

```
In scope                           327
  − no PDF yet                    −268   (pending library access)
With a PDF, parsed                  59   (44 by script or copied, 15 obtained by hand)
```

In short: 299 + 505 → 436 → 363 → 339 → 327 → 59. The 15 PDFs obtained by hand change only this last step; the candidates (436) and the in-scope papers (327) are as before.

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
3. `cremers_context` records where the review cites each entry: Table II (thermal ALD conformality), III (ozone), IV (plasma), V (sticking probabilities), VIII and IX (models), or `text` (body only). Table rows were matched by the reference number at the end of each row; model tables by the superscript after the author name, so their tags may miss a few.

### 2. Works citing Cremers 2019 (after 2019)

Cremers 2019 covers work up to early 2019. Later work enters through its citations. The rule below is fixed in `citing_filter.py`, and its output, one row per citing work with the outcome, is `cremers_citing_all.csv`.

1. **Search.** OpenAlex API, `/works?filter=cites:W2931684697` (the OpenAlex id of Cremers 2019), cursor paging to the end, run on 2026-10-13. **505 works.**
2. **Conformality keyword filter.** Kept if the title or the OpenAlex abstract (rebuilt from `abstract_inverted_index`) contains at least one of: conformal, conformality, aspect ratio, high-aspect-ratio, step coverage, trench, LHAR, PillarHall, penetration depth, saturation profile. Matching: case-insensitive; every hyphen character (ASCII or Unicode) and whitespace treated as one space; any prefix allowed (superconformal, ultrahigh-aspect-ratio); the keyword may end in s, es or ly and must then end the word, so conformality does not count as conformal. Works without an abstract are matched on the title alone. **144 works.** The matched words are in `cites_cremers_keywords`.
3. **Duplicates.** Preprints whose title matches a published article in the list were dropped (2). **142 works.**
4. **Index lag.** One manifest paper (10.3390/met13030528) is missing from the `cites:` index on 2026-10-13, although its own OpenAlex record still lists Cremers 2019 among its references. It is kept. **143 rows**, of which 3 are also in Popov.
5. **ALD filter** (recorded as exclusions, see below). Rows whose only source is this list are excluded when neither the title nor the abstract matches `atomic[\s-]layer` (case-insensitive) or `\bALD\b` (case-sensitive, whole word).

**First pull and re-run.** The list was first pulled on 2026-10-01 (522 works, 152 passed, 9 duplicate preprints dropped, 143 rows); that script was not kept. On 2026-10-13 the filter was written down as `citing_filter.py` and re-run: all 143 manifest rows pass, and every passing work is either in the manifest or a duplicate preprint, so no paper was missed. The difference between 522 and 505 is a change in the OpenAlex index. The re-run also normalizes Unicode hyphens, which the first pull did not: this added keywords to 4 rows without changing any outcome, and moved one paper past the ALD term rule (see step 3 of the exclusions).

### 3. Extra

Added by hand, with the reason in `extra_reason`. One paper: 10.1021/acs.chemmater.2c01154, a core paper of the earlier pipeline that does not cite Cremers 2019. (Yim 2020, first added by hand, was later found among the citing works and is marked as Cremers-citing only.)

### 4. Popov 2025 Table I (out of the current scope)

Review: Popov et al., "Recent trends in thermal atomic layer deposition chemistry", *J. Vac. Sci. Technol. A* 43, 030801 (2025). Every first reference in Table I (new thermal ALD processes 2010–2023, from the AtomicLimits database): refs 14–712, 942 processes, 699 papers. DOIs from the links embedded in the reference list; 4 had none. Kept in the manifest for a possible later scope.

**Why two axes.** Popov 2025 covers process chemistry (which precursors and co-reactants deposit which material) for thermal ALD. Cremers 2019 and its citing works cover geometry: conformality in high-aspect-ratio structures. Plasma and ozone ALD papers entered through the geometry axis and were kept; their coverage is therefore limited to conformality.

## Scope

Current scope: **conformality only**. A paper is in scope if it comes from Cremers 2019, Cremers-citing or Extra and is not excluded. Popov-only papers stay in the manifest but are out of scope.

The rule is one line in `make_report.py` (`SCOPE_ORIGINS`), so the scope can change without editing rows.

## Exclusions

A paper is excluded for something about the paper itself, independent of scope. Excluded rows are kept, with `reason`, `decision` (auto = by rule, manual = by a person) and `decided_on`.

Within the 436 conformality candidates, exclusions were made in three steps. Rule-based exclusions came first; a person then decided the cases the rules could not decide, and finally the cases the rules missed.

**Step 1. Rules (auto, 2026-10-01): 73**

| Rule | How it was applied | Papers |
| --- | --- | --- |
| Not ALD (Cremers-citing only) | Neither title nor OpenAlex abstract matches `atomic[\s-]layer` or `\bALD\b` | 19 |
| Not a publication | Cremers references that are footnotes, table notes or a private communication (refs 68, 71, 72, 74, 152, 155, 165, 167, 170, 175, 183, 188, 190, 193, 199, 207, 209, 214, 219, 223, 224, 227, 240, 289, 291, 292, 293, 296) | 28 |
| Not a research article | OpenAlex `type` other than `article` or `letter`: conference paper 5, review 3, book chapter 1, reference entry 1, dissertation 1 | 11 |
| Review by title or journal | Title contains the whole word review, perspective, survey, overview or tutorial (case-insensitive), or the journal is a review journal: Chemical Reviews, Chemical Society Reviews, Coordination Chemistry Reviews, Applied Physics Reviews, Annual Review of *, Progress in Materials Science, Materials Science and Engineering R, Nature Reviews * | 15 |

A paper caught by more than one rule is counted once.

**Step 2. Cases the rules could not decide (manual, 2026-10-01): 24 excluded, 1 kept**

| Case | Why no rule applied | Decision | Papers |
| --- | --- | --- | --- |
| Cremers references without a DOI | No OpenAlex record, so no document type | Judged from the citation text: 12 books and patents, 10 theses, proceedings and book chapters | 22 excluded |
| Cremers-citing works with no ALD term in the title and no abstract | The ALD rule had nothing to read | Judged from the title: Cu deposition on Ni trenches and ion-assisted trench filling excluded; ultrathin ZnO conformal coating (10.1016/j.solmat.2025.114105) kept | 2 excluded, 1 kept |

**Step 3. Cases the rules missed (manual): 12**

| Case | How it was found | Papers |
| --- | --- | --- |
| Reviews without a review word in the title | After parsing (2026-10-03): the first pages carry the journal's review label (REVIEW ARTICLE, MINIREVIEW, PERSPECTIVE) or the paper calls itself a review | 9 |
| Not ALD | After parsing (2026-10-03): W-CVD/SACVD through-silicon vias; SBA-15 silica synthesis | 2 |
| Not ALD | On the 2026-10-13 re-run (2026-10-13): 10.1002/adem.202302257 passes the ALD term rule once Unicode hyphens are normalized ("atomic‐layer deposited protective film"), but the paper studies MLD films; conformality is measured on the MLD film and ALD is only a protective layer | 1 |

**Total excluded: 109** (73 + 24 + 12). In steps 2 and 3, candidates and evidence were prepared by script and each decision was approved by the authors; the reason is in `reason`.

The kept paper has `status = included`.

Outside the scope, 10 Popov-only conference papers are also marked excluded by the type rule.

**Why reviews are excluded:** they report data from other papers, so keeping them would count the same experiment twice. **Why three review checks:** OpenAlex types most reviews as "article" (the type rule caught 3), the title and journal rule caught most (15), and the full-text check caught the rest (9). The full-text check runs again after each parsing run on newly collected PDFs.

## In scope: 327 papers

- By source: Cremers 2019 only 212, Cremers-citing only 103, Popov and Cremers 8, Popov and Cremers-citing 3, Extra 1.
- All are OpenAlex type "article". Published up to 2019: 227; after 2019: 100.
- Where Cremers 2019 cites them (220 papers): experimental conformality tables (thermal, ozone, plasma) 91, sticking-probability and model tables 33 (a paper can be in both), body text only 111.

## PDFs

1. OpenAlex gives each DOI its open-access status, license and PDF link.
2. Open PDFs are downloaded by script (`fetch_pdfs.py`, identified user agent, about one request per second). Many publisher sites refuse scripted downloads; no attempt is made to get around this.
3. The rest come through Northwestern University Libraries access. A request for text-and-data-mining access and LLM use is pending with the library.

In scope: 59 PDFs, 268 still to collect. By how the file was obtained (`pdf_source`):

| How obtained | `pdf_source` | PDFs |
| --- | --- | --- |
| OpenAlex best location, by script | `openalex` | 34 |
| Alternate OpenAlex location, by script | `openalex_alt` | 8 |
| Copied from the earlier pipeline | `v1_copy` | 2 |
| Obtained by hand from the publisher through library access (2026-10-13) | `library_manual` | 15 |

"Obtained by hand" is about the PDF of a paper that was already a candidate. It is separate from the "Extra (added by hand)" source, which is about how a paper became a candidate and still counts 1.

The 15: Cremers references 62, 65, 66, 67, 69, 70, 86, 128, 178, 180, 200, 204, 228 and 251, and one Cremers-citing paper (10.1021/acs.jpcc.1c01505). All 15 are the published version.

Of the first 44, OpenAlex marks all as open access (hybrid 22, green 10, bronze 6, gold 5, diamond 1); version: published 28, submitted (author manuscript) 16. Of the 15 obtained by hand, OpenAlex marks 8 as closed, 5 bronze, 1 green and 1 hybrid.

Licenses of the 59: CC BY 18, CC BY-NC 2, CC BY-NC-ND 3, public domain 1, other open access 10, none 25 (12 of the first 44 and 13 of the 15).

Open-access status is recorded, not used as a filter. Only extracted data (conditions, digitized values, provenance) is shared. PDFs, parsed text and figure crops are never committed to git and are redistributed only where the license allows.

## Open questions

- **Cremers references that are not ALD papers are in scope.** The not-ALD rule is applied to Cremers-citing works only, so a Cremers reference stays in scope whatever it is about. Certain cases: 16 references behind the recombination values (242 and 243 on ozone decomposition; 250 to 263 on O, N and H atom recombination, the Table VII sources). One of them, ref. 251 (10.1016/j.cattod.2003.11.022), now has a PDF and was parsed: a plasma study of oxygen recombination on oxide surfaces, with no deposition. A further 43 in-scope Cremers references have no ALD term in the title and were not judged (refs 10, 17, 19, 20, 21, 27, 35, 52, 54, 63, 73, 75, 76, 82, 84, 86, 90, 95, 112, 117, 118, 119, 120, 121, 125, 127, 130, 132, 146, 159, 173, 210, 212, 235, 265, 267, 268, 269, 284, 285, 286, 287, 297); some of them are ALD papers by content (for example 86 and 173). To decide: keep such papers as sources of cited values, or extend the rule to Cremers references.

## Files

| File | Content |
| --- | --- |
| `manifest.csv` | One row per candidate: metadata, source marks and evidence, scope, decision, PDF status. The record. |
| `report.csv` | Reader-facing view of the manifest, generated by `make_report.py`. |
| `manual_list.csv` | In-scope papers without a PDF, generated by `fetch_pdfs.py`. |
| `cremers_citing_all.csv` | Every work citing Cremers 2019 (2026-10-13), with matched keywords and whether it passed; the works filtered out are here. |
| `fetch_pdfs.py` | OpenAlex lookup and open-access download. |
| `citing_filter.py` | Fetches the works citing Cremers 2019 and applies the keyword rule; writes `cremers_citing_all.csv`. |
| `make_report.py` | Holds the scope rule; writes `in_scope` and `report.csv`. |
| `raw/` | PDFs, one per paper (`<doi with / as _>.pdf`). Not in git. |

## History

| Date | Change |
| --- | --- |
| 2026-09-30 | Popov 2025 Table I parsed: 699 papers. First OpenAlex lookup and downloads. |
| 2026-09-30 | Cremers 2019 references added (292); geometry axis. |
| 2026-10-01 | Cremers-citing works added (143, first pull of 522). Exclusions: not ALD, not a publication, no DOI, document type, review by title or journal. |
| 2026-10-01 | Scope set to conformality only; Popov-only papers out of scope. |
| 2026-10-03 | Reviews found in full text (9) and non-ALD papers (2) excluded after parsing. |
| 2026-10-13 | Keyword filter written down as `citing_filter.py` and re-run (505 citing works, 144 pass; no paper missed). Unicode hyphens now normalized; 10.1002/adem.202302257 re-judged by hand (MLD study), still excluded. |
| 2026-10-13 | 15 PDFs obtained by hand through library access and parsed: 44 → 59 PDFs. Candidates and scope unchanged. |
