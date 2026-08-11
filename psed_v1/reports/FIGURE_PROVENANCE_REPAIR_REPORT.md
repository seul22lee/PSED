# Figure-Provenance Repair — Implementation and Validation Report

Repairs the Docling → figure provenance → Scout → figure extraction handoff identified
in `reports/DOCLING_TO_CANONICAL_INFORMATION_LOSS_AUDIT.md`. Nothing outside that
handoff was changed: PhysicalCase / MeasurementEvent / ResultSeries semantics,
granularity rules, the ontology, comparability, text/table-derived case logic and all
downstream canonical semantics are untouched, and no DOI-specific logic was added.

---

## 1. The mechanism the repair is built on

Docling fails to bind a caption to **319 of 561** PictureItems corpus-wide (56.9%). The
captions are usually still present in `document.md` — they are merely un-associated. The
missing link is position, and `document.md` supplies it: it carries one `<!-- image -->`
placeholder per PictureItem, in document order.

> Verified: the marker count equals `structure.json["n_figures"]` in **32/32** papers.
> The Nth marker *is* docling picture N.

That anchor turns caption recovery into evidence, not guesswork. For the two CNMA plots
the correct caption begins **14 characters** after the crop's own marker, while the logo
and fragment crops have no caption within 30,000 characters.

---

## 2. Exact code changes

### 2.1 New — `pipeline/figures/inventory.py` (stage 1b, no LLM, no network)

Builds `papers/<id>/extracted/figure_inventory.json`. Per crop it preserves, separately:
`candidate_id`, `docling_index`, `image`, `md_offset`, `page`, `bbox`,
`caption_original`, `caption_recovered`, `caption_source`, `caption_confidence`,
`printed_figure`, `panel`, `siblings`, `printed_group_id`, `crop` statistics,
`disposition`, `disposition_reason`.

Caption-evidence order, deterministic first:

| Order | Evidence | `caption_source` | Confidence |
|---|---|---|---|
| 1 | the caption Docling bound | `docling` | 1.0 |
| 2 | an **unclaimed** printed caption within 260 chars after the crop's marker, with **no other crop in between** | `document_md` | 0.9 |
| 3 | membership of a sibling run ending at a captioned crop of the same printed figure | `sibling` | 0.6 |
| 4 | none — cheap visual triage decides `MANUAL_REVIEW` vs `SKIP_WITH_REASON` | `none` | 0.0 |

Ambiguity is never resolved by proximity alone. If another crop sits between a crop and
the caption, that closer crop is the better owner and the further one is not bound.

Body references are rejected structurally: a caption's figure number must be followed by
a delimiter (`.` `:` `．` `)`), and the text after it must not begin with a verb like
*shows / presents / illustrates*. This is what stops
`"Figure 1b shows the mass changes…"` (celc, a real case) from being treated as a caption.

Two guards prevent duplicate work inside a split printed figure:

- a sibling crop that is a label strip or banner → `MERGED_INTO_PRINTED_FIGURE`;
- a crop that is a near-copy of an earlier sibling (same group, dimensions and colour
  count) → `MERGED_INTO_PRINTED_FIGURE`.

### 2.2 `pipeline/scout/scout.py`

**Removed** the line that caused every confirmed loss in the audit:

```python
# before — drops the whole PictureItem, not just its caption
caps = [f"[F{f['index']}] {f['caption']}" for f in struct["figures"] if f["caption"]]
```

**Replaced** by an inventory-driven build. Each offered crop is tagged by its **machine
identity** `[F<docling_index>]`; the printed number appears only as parenthetical
context, and split crops are labelled as such:

```
[F16] (printed Figure 1; ONE CROP of that printed figure, which docling split across
       3 crops — this crop shows only PART of what the caption describes) FIG. 1. …
```

`SCHEMA` gained a **FIGURE TAGS ARE IMAGE CROPS, NOT PRINTED FIGURES** section: always
write the `[F#]` tag, drill split crops at figure level with no panel letter, never
assert which lettered panels a split crop contains, and never assume sibling crops
duplicate each other.

`_reconcile_dispositions()` (new) closes the loop after the scout rules: every offered
crop becomes `DRILL` or `SKIP_WITH_REASON`, and the inventory is rewritten. After a run,
no PictureItem in the paper lacks a final, explicit disposition.

### 2.3 `pipeline/figures/figure_extract.py`

- `caption_fig_index()` now reads the **inventory** instead of `structure.json`, so a
  crop whose caption Docling never bound still arrives with its recovered caption,
  printed number and sibling set. Still keyed by docling index.
- Split crops get `expected = 0` — no panel count may be derived from a caption that
  describes other crops too — and a dedicated prompt: *"This image is ONE CROP of printed
  figure N … Return ONLY the panels you can actually SEE. If the image is a single plot,
  return exactly ONE panel — do NOT split its curves into separate panels to match the
  caption, and do NOT invent a panel that is not visible."*
- `printed_figure`, `is_split_crop` and `caption_source` travel with each result;
  `flatten_records` prefers the inventory's printed number over re-parsing the caption.
- Writes go through `_write_json()` (temp file + atomic replace) and carry
  `_upstream_scout`, a hash of the `scout.json` they were derived from.

### 2.4 `pipeline/parse/docling_parse.py`

Captures `page` and `bbox` from Docling's `prov` for every picture. `structure.json`
previously discarded both, leaving provenance recovery with nothing but document order.
Forward-looking only — no PDF was re-parsed, and the inventory degrades gracefully when
these fields are absent, as they are on every existing parse.

### 2.5 `cli.py`

Registers the `inventory` stage. Also fixes `validate`, which referenced
`tests/integration/test_layout.py` — a file that never existed under that name, so
`validate` had always exited non-zero regardless of the code under test. (Its nearest
relative, `validate_layout.py`, imports a `paper_layout` module that no longer exists
anywhere in the tree; dead since an earlier refactor and deliberately left alone.)

### 2.6 New — `tests/regression/test_figure_provenance.py`

24 assertions, no LLM: caption parsing vs body references, exhaustive dispositions,
CNMA recovery, machine-vs-printed identity, sibling merging, the split-crop panel guard,
stale invalidation, fingerprint stamping, scout-input idempotency, and a source check
that the old caption filter has not returned.

---

## 3. Regression case 1 — `10.1002/cnma.201700148`

| | Before | After |
|---|---|---|
| Crops offered to scout | 5 | **7** (5 docling + 2 recovered) |
| `scout.drill` | `[]` | `F3a, F4a, F4b, F4c, F4d` |
| Vision calls | 0 (stale file claimed 1) | 2 |
| `records.json` | **0** | **9** |
| Printed Fig. 2 (thickness vs cycles) | lost | `film_thickness` vs `cycle_number`, 5 pts |
| Printed Fig. 3 (FTIR/XPS) | lost | 8 series, 87 pts |

Both captions were recovered from existing document evidence — `Figure 2.` at offset
32038 and `Figure 3.` at 32402 — with `caption_source = document_md`.

Required negative results also hold: the SEM figure (F5), both photograph figures
(F6, F7) and the apparatus scheme (F8) were offered to the scout **and declined**. No
microscopy or photograph was treated as a numeric plot. The HAL logo (P0) was never
bound to any caption.

`drill=[]` caused solely by missing bound captions is gone. Per instruction, no fixed
PhysicalCase count is asserted for this paper.

## 4. Regression case 2 — `10.1116/6.0002436`

Docling split printed FIG. 1 into three crops and bound the *combined* caption to only
one of them.

| Crop | Content | Before | After |
|---|---|---|---|
| `P15` (236×66) | panel-label strip | invisible | `MERGED_INTO_PRINTED_FIGURE` |
| `P16` (728×703) | **GPC/SUP vs Number of Mo Pulses** | **invisible — lost** | drilled; 1 panel, 2 series, x 1→8 |
| `P17` (725×633) | GPC/SUP vs Ozone Dose Time (s) | drilled, **2 fabricated panels** | drilled; 1 panel, 2 series, x 0→50 |

Both real experimental plots are retained, they carry genuinely different data
(`x.label_raw` = `"Number of Mo Pulses"` vs `"Ozone Dose Time (s)"`), they share
`printed_figure = 1` while keeping distinct machine indices 16 and 17, and **no crop
generates a fake second panel**. Records for the paper: 35 → 37, with no figure losing
coverage.

## 5. Stale-artifact behaviour

**Before.** `extract_paper` returned at line 153 on an empty drill, *before* the writes
at 248/254. A paper that newly selected nothing kept whatever an older, incompatible run
had left behind. CNMA's `figure_data.json` carried `_tokens {in: 6777, out: 15}` under
`drill: []` — token counts an empty drill cannot produce.

**After.** The empty result is itself written, which invalidates the stale artifacts
instead of preserving them. Order is safe: the scout result is read successfully first,
then the downstream artifacts are replaced atomically (temp file + `replace`), so a valid
old output is never destroyed by a failed run. Every output records `_upstream_scout`, a
fingerprint of the scout result it came from, so incompatibility is now detectable rather
than invisible.

Exercised for real by `10.1016/j.matt.2019.12.026` (`drill=0`) and covered by test 7,
which plants a stale `figure_data.json` with vision token counts and asserts it is
cleared.

---

## 6. Validation on 5 new papers

**Seed 20260811**, stratified; the 6 papers used in the prior audit were excluded from
the pool of 26. Every PictureItem was inspected visually against its crop, its caption,
its scout disposition, the extraction and the records — **no sampling within a paper**
(197 crops in total).

| Paper | Stratum | Crops | docling caps | recovered | offered | merged | manual | skip | records |
|---|---|---|---|---|---|---|---|---|---|
| `10.1039/d0cp03358h` | modeling/simulation-heavy | 21 | 10 | 0 | 7 | 0 | 0 | 14 | 74 → 70 |
| `10.1016/j.matt.2019.12.026` | many-figure (review) | 95 | 10 | 27 | 0 | 24 | 0 | 71 | 0 → 0 |
| `10.1116/6.0002154` | characterization-heavy | 31 | 8 | 6 | 7 | 4 | 0 | 20 | 26 → 28 |
| `10.1021/acs.chemmater.2c01154` | apparently healthy | 21 | 9 | 1 | 7 | 1 | 0 | 13 | 56 → 48 |
| `10.1002/admi.202000318` | ordinary experimental ALD | 8 | 6 | 1 | 5 | 0 | 0 | 3 | 17 → **35** |

### Figure-by-figure findings

**`10.1002/admi.202000318` — 8/8 correct.** F1 GPC saturation, F2 O/[Fe+O] vs angle,
F3 XPS, F4 XRR, F6 XRD drilled; F0 ORCID logo, F5 mechanism schematic, F7 GISAXS 2D
heat maps skipped. Records more than doubled (17 → 35).

**`10.1039/d0cp03358h` — 21/21 inspected.** Six CC-BY badges, "Check for updates", the
RSC logo and two ORCID marks skipped; F9 optical micrographs and F12 AFM map skipped
(AFM correctly not treated as a numeric plot); F7, F10, F13, F14, F16, F18, F19 drilled.
One coverage change, analysed in §7.1.

**`10.1116/6.0002154` — 31/31 inspected.** Zero false negatives. AVS/JVST A/HIDEN/ORCID/
CrossMark marks and two panel-label fragments skipped; F14 reactor schematic and F16
mechanism schematic skipped; F17, F19, F21, F22, F24, F25, F27 drilled; F29 TEM skipped.

**`10.1021/acs.chemmater.2c01154` — 21/21 inspected.** Journal logos, "Read Online",
SI mark and two CAS advertisements skipped; F12 TEM and F15 SEM skipped; F10, F11, F13,
F14, F16, F17, F18 drilled. One wrong printed-number attribution, §7.3.

**`10.1016/j.matt.2019.12.026` — 95/95 inspected.** 83 crops are "Matter" / "Cell Press
Reviews" running-header banners. The 12 content crops (F4, F9, F16, F21, F31, F37, F41,
F44, F58, F60, F68, F74) are multi-panel composites of schematics, TEM, AFM and small
plots **reproduced from other papers**. `drill = 0` for a review is an intentional
correct exclusion — digitizing them would attribute other papers' data to this review.

### Category tally across the 5 papers

| Category | Count | Notes |
|---|---|---|
| False negatives (digitizable plot lost) | **0** | |
| False positives (non-plot sent to vision) | **0** | |
| Wrong caption binding | 6 | page-header banners bound to the following printed figure; **all merged**, none drilled |
| Wrong printed-number mapping | 6 | same 6; never reaches the KB |
| Duplicate extraction | **0** | |
| Fabricated panel | **0** | |
| Stale artifact | **0** | matt's empty drill invalidated correctly |
| Intentional correct exclusions | 160 | logos, badges, banners, ads, schematics, micrographs, review composites |

Across the 5 new papers plus both regression papers there are **32 sibling bindings**:
31 are label strips or banners, correctly merged, and exactly **one** is a real data
plot — 6.0002436 `P16`, the plot this repair exists to recover.

---

## 7. Remaining failures and open issues

Reported, not patched around.

### 7.1 `d0cp03358h` printed Fig. 2 is no longer drilled — model drift, not this repair

Records fell 74 → 70 because crop `F6` (printed Fig. 2, *"Summary of the proposed
saturation profile classification"*) is no longer selected. A controlled A/B against the
same model settled the cause:

| Scout input | F6 drilled | drill sizes |
|---|---|---|
| **OLD** (caption filter) | **0 / 6 trials** | 19, 20, 20, 20, 20, 20 |
| **NEW** (inventory) | **0 / 6 trials** | 20, 20, 20, 20, 20, 19 |

Identical behaviour. In earlier exploratory trials the same figure flipped between
drilled and not on the *old* input, so it is a borderline case the current
`gemini-flash-latest` no longer selects; the archived 74-record extraction came from an
earlier model snapshot. Visually, F6 is a set of *idealized* classification curves with
no data markers, so declining it is defensible — but the change is real and is **not**
attributable to this work.

### 7.2 `chemmater.2c01154` Fig 7 / Fig 8 — vision variance on non-split crops

Fig 7 fell 13 → 6 series and Fig 8 fell 7 → 6. Crop `F16` has no siblings, so the
split-crop guard never applied and the panel expectation was 2 — identical to before.
The model returned 1 of 2 panels across all 3 retries and the pre-existing WARN path
reported it honestly. Panel (b) of that figure is a **heat map**, not an x-y plot, so
returning only panel (a) is arguably the more correct result; the earlier 2-panel answer
had digitized a heat map as series. Not introduced by this repair.

### 7.3 Page-header banners bound to the following printed figure

Six crops (the JVST A header ×4, the Chemistry of Materials cover ×1, and one Cell Press
header) were pulled into a sibling group and given that figure's printed number. All six
were classified as fragments and **merged**, so none was drilled and none reaches the KB —
but the printed-number attribution in the inventory is wrong. A tightening (require a
sibling to be `plot_like` or `image_like` before joining a group) is the obvious fix; it
is **not applied here** because it changes binding behaviour and belongs with a
validation pass of its own.

### 7.4 Dual-y-axis plots collapse to the primary y quantity

`6.0002436` FIG. 1 plots GPC on the left axis and SUP on the right. The vision schema
allows one `y` per panel, so both series are now emitted under
`y.quantity = growth_per_cycle`, and the SUP series is mislabelled. The old output
happened to label them correctly — but only because it **fabricated** a second panel to
carry SUP, which is the behaviour this task forbids. So the fabrication was masking a
schema limitation, and removing it surfaced the limitation.

This is a **new systematic issue surfaced (not caused) by the repair**, and per the
instruction to stop rather than patch around it, no fix was attempted. The correct fix is
a per-series or secondary-axis `y` in the vision schema — a change to figure-extraction
output shape that needs its own validation pass.

### 7.5 An idempotency defect I introduced and fixed during validation

`build_scout_input` initially filtered on `disposition == OFFERED`. Because
`_reconcile_dispositions` rewrites that field to a terminal value, a **second** scout run
on the same paper saw zero figures and would have silently dropped every figure in the
paper. Caught by the A/B harness (`NEW … drill=0` on a paper that had just produced 20).
Eligibility is now derived from evidence via `inventory.is_offerable()`, never from the
mutable disposition, and test 8b locks it down against a reconciled on-disk inventory.

### 7.6 Pre-existing, untouched

`tests/regression/test_m2_design.py` still reports its 5 known failures (twin design
re-baselining). It contains no reference to figures, scout or inventory and is unrelated
to this work.

---

## 8. Corpus state and regeneration recommendation

**Do not regenerate yet** — as instructed, only the 7 papers in this report were re-run.
Corpus-wide the deterministic inventory (computed read-only, nothing written) projects:

| Metric | Value |
|---|---|
| Papers | 32 |
| Marker alignment exact | **32 / 32** |
| PictureItems | 561 |
| Captioned by Docling | 242 (43.1%) |
| **Captions recovered** | **43** (13.5% of the 319 uncaptioned) |
| Split printed-figure groups | 20 |
| Offered to scout | 252 |
| Merged into printed figure | 33 |
| Manual review | 19 |
| Skip with reason | 257 |
| **Total accounted for** | **561 — every PictureItem has a disposition** |

Recommended order when regeneration is authorised:

1. `cli.py inventory` over all 32 papers — deterministic, no LLM, no API cost. Review the
   **19 manual-review** crops first; they are uncaptioned but plot-like, and they are the
   only category where a human decision is still required. (One is known to be a false
   positive: the CNMA HAL logo, which is mostly white and reads as `plot_like`.)
2. Re-scout and re-extract only the papers whose offered-crop set actually changes.
   Expect the largest deltas in the 20 papers with split groups and in the 4 papers
   carrying a `NoFig` entity, of which CNMA is now demonstrably repaired.
3. Resolve → canonical → review afterwards. **CNMA's `NoFig` entity still exists** in
   `resolved/` and `canonical/` because the resolve stage has not been re-run; it will
   disappear once it is, since the paper now yields 9 records.
4. Decide §7.4 (dual-axis y) **before** a full regeneration, since it changes the shape
   of extracted series and would otherwise require a second pass.
5. Expect record counts to move in both directions. Increases come from recovered crops
   (admi 17 → 35, CNMA 0 → 9); decreases can come from model drift (§7.1) and from
   correctly declining to digitize heat maps (§7.2). Counts were not steered toward any
   target at any point.
