# Docling → Canonical Information-Loss Audit

**Scope:** read-only. No production code, prompt, JSON, canonical output, or experiment
count was modified while producing this report. The only file written is this document.

**Question:** for experiment-relevant information that demonstrably exists in Docling
output, at what pipeline stage is it *first* lost, and what exact logic causes the loss?

**Answer (short):** the first loss point is **Scout input construction**, at
`pipeline/scout/scout.py:204`, where the expression `if f["caption"]` silently discards
every Docling `PictureItem` whose caption Docling failed to bind — including genuine,
digitizable data plots whose captions are present verbatim in `document.md`. Scout never
sees them, so it cannot select them, and every downstream stage is faithful to a
truncated input. **No stage after Scout's drill decision loses anything.**

---

## 1. Method

Six papers: the mandated primary failure case plus five drawn with seed `20260810`.

| Paper | Role |
|---|---|
| `10.1002/cnma.201700148` | primary failure case (mandated) |
| `10.1021/acs.chemmater.2c02292` | seed sample |
| `10.1016/j.tsf.2012.11.127` | seed sample |
| `10.3762/bjnano.5.25` | seed sample |
| `10.1002/celc.201600139` | seed sample |
| `10.1116/6.0002436` | seed sample |

For each paper the trace ran forward from the raw Docling artifacts
(`document.md`, `structure.json`, `figures/fig_N.png`) through
`scout.json` → `figure_data.json` → `records.json` → `resolved/*` →
`canonical/curves.json` → `review.json`, and every item present at stage *N* but absent
at stage *N+1* was attributed to the **earliest** transition at which it disappeared.
Every `PictureItem` that never reached Scout was opened and classified **visually**, not
by filename or heuristic — that is the only way to separate a lost data plot from a
publisher logo.

## 2. Failure taxonomy

| # | Category | Fires in this audit |
|---|---|---|
| 1 | Docling image-extraction failure (image never produced) | **no** |
| 2 | Docling provenance/caption-binding failure | **yes** — 319/561 corpus-wide |
| 3 | Scout **input** failure (existed, never shown to Scout) | **yes** — the first loss point |
| 4 | Scout **decision** failure (shown, wrongly declined) | **no** — 0/9 in sample |
| 5 | Figure-extraction (vision) failure | **yes** — 1 paper corpus-wide |
| 6 | Record-flattening loss (panels/series dropped) | **no** |
| 7 | Resolution/canonicalization loss | **no** |
| 8 | Axis/semantic misclassification (content kept, meaning corrupted) | **yes** — 1 instance |
| 9 | Stale artifact / run inconsistency | **yes** — 1 paper corpus-wide |
| 10 | Synthetic substitution (real data absent, placeholder minted) | **yes** — 4 papers |

Categories 1, 4, 6 and 7 are **clean**. That is a substantive finding in itself: the
digitization, flattening and resolution machinery is not where information is being lost.

---

## 3. Analysis by pipeline transition

### 3.1 PDF → Docling (`document.md`, `structure.json`, `figures/`) — category 1 CLEAN, category 2 FIRES

Docling extracts the images reliably. For `cnma.201700148` all 10 `PictureItem` images
were written to disk, including the two that matter. What Docling fails at is **binding
captions to images**.

Corpus-wide, across 32 papers:

| Metric | Value |
|---|---|
| Total `PictureItem`s | 561 |
| Empty-caption `PictureItem`s | **319 (56.9%)** |

The 6-paper sample reproduces this almost exactly: 79 `PictureItem`s, 44 empty-caption
(55.7%). This is not an outlier condition — **more than half of all extracted images
carry no caption**.

Critically, the caption is usually *not gone from the document*. For all three data
plots lost in this sample, the correct caption is present verbatim in `document.md`:

| Lost image | Caption in `document.md` | Offset |
|---|---|---|
| `cnma` `fig_3` | "Figure 2. a) Thicknesses of annealed BN films … as a function of the performed number of ALD cycles. The slop of th…" | 32038 |
| `cnma` `fig_4` | "Figure 3. a) FTIR spectrum of obtained BN nanotube array after thermal annealing. b) XPS survey spectrum…" | 32402 |
| `6.0002436` `fig_16` | "FIG. 1. Saturation curves for ozone (3 wt. %) and bis-isopropylcyclopentyldienyl molybdenum dihydride…" | 11349 |

**Caption recoverability: 3/3 (100%).** The information is not destroyed at this stage —
it is merely un-associated. The loss becomes irreversible only at the next transition.

### 3.2 Docling → Scout input — category 3, **THIS IS THE FIRST LOSS POINT**

`pipeline/scout/scout.py:204`:

```python
caps = [f"[F{f['index']}] {f['caption']}" for f in struct["figures"] if f["caption"]]
caps += [f"[T{t['index']}] {t['caption']}" for t in struct["tables"] if t["caption"]]
```

Two properties make this the decisive line:

1. **It reads captions only from `structure.json`.** The recovered captions sitting in
   `document.md` at the offsets above are never consulted, even though `document.md` is
   already loaded three lines earlier.
2. **`if f["caption"]` drops the image entirely, not just its caption.** An uncaptioned
   `PictureItem` is not passed to Scout as "figure N, caption unknown" — it ceases to
   exist from Scout's perspective. There is no log line, no counter, and no
   `unresolved`/`needs-review` record. The discard is **silent and unrecoverable**.

Classification of all 44 invisible `PictureItem`s in the sample, every one opened and
viewed:

| Class | Count | Correctly discarded? |
|---|---|---|
| Layout fragments (sub-glyph crops, rules, < 40 kpx) | 28 | yes |
| Publisher logos / journal banners | 8 | yes |
| TOC / graphical abstracts | 2 | yes |
| Micrographs (non-digitizable) | 2 | yes |
| Advertisement | 1 | yes |
| **Genuine digitizable data plots** | **3** | **NO — real loss** |

The filter is 41/44 (93%) correct. Its precision is not the problem; its **silence** is.
The 3 misses are exactly the items that carry quantitative experimental content.

Confirmed losses:

| Paper | Image | Printed identity | Content lost |
|---|---|---|---|
| `cnma.201700148` | `fig_3` (1333×518) | Figure 2 | Thickness vs. ALD cycles — 5 digitizable points, GPC = 0.185 nm/cycle |
| `cnma.201700148` | `fig_4` (1320×939) | Figure 3 | FTIR spectrum, XPS survey, B 1s, N 1s |
| `6.0002436` | `fig_16` (728×703) | FIG. 1(a) | GPC and SUP vs. **Number of Mo Pulses** — precursor saturation curve |

### 3.3 Scout input → Scout decision — category 4 CLEAN

Scout's judgment is sound. Nine figures in the sample were shown to Scout and declined:

```
cnma      F2  Figure 1. General reaction mechanism …          (schematic)
cnma      F5  Figure 4. SEM images … cross section views      (micrograph)
cnma      F6  Figure 5. Images capture of a water droplet …   (photograph)
cnma      F7  Figure 6. Photograph of droplets …              (photograph)
cnma      F8  Figure 7. Scheme of the ALD set-up …            (schematic)
tsf       F0  Figure 1 Schematic of the ALD process …         (schematic)
bjnano    F1  Figure 1: Illustration of one ALD cycle …       (schematic)
bjnano    F2  Figure 2: Flow chart of the … simulation        (flow chart)
celc      F12 Figure 5. Top-view and cross-sectional SEM …    (micrograph)
```

All nine are correctly non-digitizable. **Scout false-negative rate: 0/9.**

This reframes the primary failure case entirely. `cnma`'s `drill: []` is **not** a Scout
error. Scout received exactly five captions — a reaction mechanism, SEM images, two
photographs and an apparatus scheme — and zero tables. Given that input, `drill: []` was
the *correct* decision. **100% of `cnma`'s digitizable content (2 of 2 figures) was
invisible before Scout ran.** The stage that failed is the one that built the input.

### 3.4 Scout drill → figure extraction — category 5 CLEAN in sample, 1 corpus-wide failure

Every drill target in the sample was fulfilled:

| Paper | Drill targets | Figures returned | Panels returned | Points | Unfulfilled |
|---|---|---|---|---|---|
| `cnma` | 0 | 1 (stale, see §4) | 0 | 0 | — |
| `chemmater.2c02292` | 20 | 6 | 19 | 696 | none |
| `tsf.2012.11.127` | 8 | 6 | 10 | 873 | none |
| `bjnano.5.25` | 9 | 4 | 9 | 411 | none |
| `celc.201600139` | 8 | 4 | 8 | 330 | none |
| `6.0002436` | 8 | 6 | 9 | 532 | none |
| **Total** | **53** | | **55** | **2842** | **0** |

Corpus-wide there is exactly one genuine category-5 failure:
`10.1007/s11671-010-9676-0` has `drill = 1`, a `figure_data.json` carrying real token
usage (`in: 6657, out: 19`) and one figure entry — but `records.json == []`. The vision
call ran and returned nothing digitizable. This is the only paper in the corpus where
information is lost *at* the extraction stage rather than before it.

### 3.5 A caption-binding side effect that corrupts meaning — category 8

`6.0002436` shows that a mis-bound caption does more than hide an image; it can falsify
the image that *is* kept.

Docling split printed FIG. 1 into two sibling `PictureItem`s and bound the **combined**
caption — which describes both panel (a) and panel (b) — to only one of them:

- `fig_16` — panel **(a)**, x-axis "Number of Mo Pulses" → **empty caption, dropped at §3.2**
- `fig_17` — panel **(b)**, x-axis "Ozone Dose Time (s)" → captioned, drilled

Direct inspection of `fig_17.png` confirms it is a *single* plot: x = Ozone Dose Time (s),
with two y-series (Average GPC on the left axis, SUP on the right). But because its
caption promised two panels, the vision stage emitted a two-panel decomposition:

```
panel a  x={'quantity':'pulse_time','unit':'s'}  y={'quantity':'growth_per_cycle','unit':'Å/cycle'}
           Average GPC  n=7  [[0,0.07],[5,1.04],[10,1.15],[20,1.35], …]
panel b  x={'quantity':'pulse_time','unit':'s'}  y={'quantity':'SUP','unit':'%'}
           SUP          n=7  [[0,14.0],[5,4.0],[10,1.0],[20,6.5], …]
```

Both "panels" share identical x-values because they are the two y-series of one panel.
The consequences:

- The **Mo-pulse saturation experiment (printed panel a) is absent from the KB entirely.**
- The surviving ozone-dose data is labelled `pulse_time`, which reads as a generic
  precursor pulse rather than specifically the **ozone dose**.
- Scout's two distinct drill targets `F17a` ("Mo precursor dose") and `F17b` ("ozone
  precursor dose") were both counted as fulfilled by a figure containing only the ozone
  panel — so the unfulfilled-target check in §3.4 cannot detect this.

This is content preserved with corrupted meaning, and it is caused by the *same*
caption-binding defect as §3.2, not by a defect in the vision stage.

### 3.6 records → resolved → canonical → review — categories 6 and 7 CLEAN

Strict 1:1 preservation, verified per paper:

| Paper | records | entities | results | curves | review series |
|---|---|---|---|---|---|
| `cnma.201700148` | 0 | 1 | 1 | 0 | 1 |
| `chemmater.2c02292` | 44 | 44 | 44 | 44 | 44 |
| `tsf.2012.11.127` | 32 | 32 | 32 | 32 | 32 |
| `bjnano.5.25` | 39 | 39 | 39 | 39 | 39 |
| `celc.201600139` | 17 | 17 | 17 | 17 | 17 |
| `6.0002436` | 35 | 35 | 35 | 35 | 35 |

**Nothing is dropped downstream of `records.json`.** `cnma` is the sole exception and it
moves in the opposite direction — 0 records become 1 entity. That is an *addition*, not a
loss, and it is analysed in §5.

---

## 4. Mandatory stale-artifact check

**`cnma.201700148` carries a stale `figure_data.json` that cannot have been produced by
the current `scout.json`.** Proof by contradiction:

`pipeline/figures/figure_extract.py:153` returns before any write:

```python
if not scout.get("drill"):
    print(f"[05 skip] {sd}: drill=0 — nothing to read (go_deeper={scout.get('go_deeper')})")
    return [], [], 0, 0
```

The writes are at lines 248 and 254, *after* that return:

```python
(d / "figure_data.json").write_text(json.dumps(
    {"doi": sd, "process_card": card, "figures": results,
     "_tokens": {"in": tok_in, "out": tok_out}}, indent=1))
records = flatten_records(sd, scout, results)
(d / "records.json").write_text(json.dumps(records, indent=1))
```

Current `cnma` state: `drill = []`, yet `figure_data.json` exists with
`_tokens = {'in': 6777, 'out': 15}` and one figure entry. Non-zero token usage proves a
vision API call occurred; an empty drill makes that call unreachable. Therefore the file
predates the current `scout.json`.

The underlying defect is structural: **an empty drill writes nothing and deletes
nothing.** There is no generation hash, no input-timestamp comparison, and no downstream
invalidation, so a stage that produces no output leaves the previous run's output in
place, indistinguishable from a fresh result.

Corpus-wide, three papers have `drill == []`. Only `cnma` is stale —
`10.1016/j.matt.2019.12.026` and `10.1016/j.mee.2018.01.033` have no `figure_data.json`
at all and are internally consistent. The risk is real but currently affects one paper.

---

## 5. The `NoFig` lineage — category 10

`cnma`'s canonical entity `10.1002_cnma.201700148__NoFig` is **synthesized, not
extracted**. Full chain:

1. `records.json == []` (nothing was ever drilled).
2. `to_experiments` returns `exps == []`.
3. `pipeline/resolve/to_kb.py:1829`:

```python
if not exps:
    # No figure data digitized — still admit the paper as ONE paper-level experiment
    _pm = lib.canon_material((scout.get("materials") or [None])[0]) \
        or (scout.get("materials") or [None])[0]
    _pch = _chem_for(_pm)
    exps.append(paper_level_experiment(sd, scout, card, pid, ...))
```

4. `paper_level_experiment` (line 1876) mints a record with `points: []`,
   `coordinate: None`, `granularity: "single"`, and `measurand = growth_per_cycle`
   taken from `scout.gpc_nm = 0.18` — a value Scout read from prose, never from a figure.
5. `figure_slug()` finds neither a printed figure number nor a Docling index, and returns
   the literal `"NoFig"`, producing the entity id.

The result is an `UnresolvedSourceEntity` with `experimental_case_count = 0` and
`physical_case_id = None`, which nonetheless receives a `measurement_event_id` and a
`result_series_id`. It bypasses figure extraction completely.

Two observations worth separating:

- The **fallback itself is defensible** — the paper genuinely reports GPC ≈ 0.18 nm in
  prose, and admitting it preserves recall.
- The **failure is that it fires at all here.** `cnma` has a real thickness-vs-cycles plot
  (`fig_3`) yielding GPC = 0.185 nm/cycle from 5 digitized points. The synthetic
  paper-level record is standing in for data the pipeline already had on disk and threw
  away at §3.2. `NoFig` is therefore a *symptom marker* for §3.2, not an independent
  defect.

Corpus-wide, 4 of 32 papers carry a `NoFig` entity: `cnma.201700148`,
`s11671-010-9676-0`, `matt.2019.12.026`, `mee.2018.01.033`.

---

## 6. Systemic metrics

| Metric | Sample (6 papers) | Corpus (32 papers) |
|---|---|---|
| `PictureItem`s | 79 | 561 |
| Empty-caption `PictureItem`s | 44 (55.7%) | **319 (56.9%)** |
| Visible to Scout | 35 (44.3%) | — |
| Invisible that were genuine data plots | **3** | — |
| Captions recoverable from `document.md` | **3/3 (100%)** | — |
| Scout drill targets | 53 | — |
| Panels returned | 55 (0 unfulfilled) | — |
| Scout decision false negatives | 0/9 | — |
| Records → review preservation | 1:1 | — |
| Papers with `drill == []` | 1 | 3 |
| Papers with `records == []` | 1 | 2 |
| Papers with a `NoFig` entity | 1 | **4** |
| Stale artifacts | 1 | **1** |

**Loss rate.** Of 29 digitizable figure-level items in the sample (26 drilled + 3 lost),
**3 were lost — 10.3%.** Two of six papers (33%) are affected. For `cnma` specifically the
loss rate is **100%** — both digitizable figures were invisible, which is precisely why
this paper produces no experiments at all.

**Where losses occur.** All information loss in this audit occurs in the
**Docling → Scout-input** window. Zero occurs after Scout's drill decision, with the
single corpus-wide exception of `s11671-010-9676-0` (§3.4).

---

## 7. Prioritized findings

Listed by causal weight. No code was changed; these are diagnoses, not patches.

1. **`scout.py:204` discards uncaptioned `PictureItem`s silently.** Single root cause of
   every confirmed loss in this audit (3/3), and the reason `cnma` yields zero
   experiments. Captions are recoverable from `document.md` in 100% of observed cases —
   the information needed to fix this is already in memory when the loss occurs.
2. **Docling caption binding fails on 56.9% of images corpus-wide.** Not itself a loss
   (the text survives in `document.md`), but it is the upstream condition that makes
   finding 1 destructive, and via §3.5 it can also corrupt the meaning of images that
   *are* kept.
3. **No run-consistency mechanism.** A stage that produces no output leaves stale output
   in place (`cnma` `figure_data.json`). One paper affected today; the mechanism is
   general.
4. **`NoFig` masks upstream loss.** The paper-level fallback produces a plausible-looking
   entity that hides a total figure-extraction failure behind a prose-derived GPC value.
   4 papers corpus-wide.
5. **Multi-panel captions can induce fabricated panel decompositions** (§3.5), and
   unfulfilled-target checks cannot detect it because the fabricated panels satisfy the
   drill targets by label.
6. **`s11671-010-9676-0`** is the corpus's only true vision-stage failure and is
   unrelated to the above.

---

## 8. Conclusion

> **For experiment-relevant information that exists in Docling output, the first loss
> occurs at Scout input construction — `pipeline/scout/scout.py:204` — where the
> comprehension filter `if f["caption"]` removes every `PictureItem` Docling failed to
> caption, including genuine digitizable data plots whose captions are present verbatim
> in `document.md` and are never consulted.**

The pipeline downstream of that line is faithful. Scout's selection judgment is sound
(0/9 false negatives), the vision stage fulfils 53/53 drill targets, and records are
preserved 1:1 through resolution, canonicalization and review. `10.1002/cnma.201700148`
produces no experiments not because any stage mishandled its data, but because both of
its digitizable figures were deleted from the input before the first decision was made —
and the `NoFig` paper-level record that replaced them is a synthetic stand-in for data
that was sitting on disk the entire time.
