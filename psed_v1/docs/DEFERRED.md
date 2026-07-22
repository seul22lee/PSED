# Deferred decisions & open questions

A running log of decisions we consciously postponed and things worth revisiting, so
they survive across sessions. **Newest entries at the top.** Remove an entry once it
is genuinely resolved (and say where the resolution lives).

Status values: `deferred` · `needs-decision` · `needs-verification`

---

## 2026-07-22 18:05 (local) — RESOLVED: `series_value` placeholder axis
**Context:** When vision returned no `series_axis`, `06` fell back to naming the
controlled quantity `"series_value"` — a meaningless, ungrounded placeholder. 30 rows in
`10.3762_bjnano.5.25`. The values were genuine; only the axis NAME was missing.
**Status:** resolved
**Detail:** Fixed where the information actually lives — the figure. `VISION_SCHEMA` now
makes `series_axis` **required** for any multi-curve panel and tells the model to derive
it from the label's unit when the caption/legend doesn't name it: labels `'10 cycles'` →
axis `'number of cycles'`, `'5ms'` → `'exposure time'`, `'150°C'` → `'temperature'`.
`06` never reconstructs the name; a blank axis now becomes the visible flag
`unnamed_series_axis` instead of hiding behind a plausible-looking `series_value`.

After re-extraction the axes are named and, better, **canonicalise into real ontology
quantities**:

    cycle_number                   24
    H2 flow ratio                  13
    pulse_time                      5
    reactive_sticking_coefficient   1

Corpus-wide check for `series_value` / `unnamed_series_axis`: **[]**. Only the axis name
changed — series values and points were already correct.

Two notes on the re-extraction. (1) The records-vs-KB rule below caught
`10.1039_d0cp03358h` (KB 44 > records 36), so it was **not** re-ingested; re-extracting it
also thinned its records 36→11 (332→151 points) for no benefit, so its `records.json` and
`figure_data.json` were restored from git. Lesson: only re-extract a paper if its KB will
actually be rebuilt from it. (2) `bjnano.5.25` lost points overall (379→308) but the loss
is entirely in the **simulation** figures — Fig 3 129→76, Fig 5 201→178 — while the
**measured** Fig 6 gained (49→54). Fig 5 is model output, not twin-used, so this trade is
acceptable; the twin-relevant data improved.

## 2026-07-22 17:15 (local) — ⚠️ NEVER re-ingest a paper whose KB is richer than its records.json
**Context:** Re-ingesting 16 papers to clear caption-path fabrications silently destroyed
**129 experiments**. Caught by the report totals dropping 354 → 225.
**Status:** resolved (restored); recorded as a standing hazard
**Detail:** Four papers' KB entries did not come from `03_corpus/extracted/*/records.json`
at all — they were carried over from the **older, richer** pipeline output:

    10.1063_1.5028178      116 -> 4    (-112)   <- the ylilammi dose profiles
    10.1039_d0cp03358h      44 -> 36   (-8)
    10.1016_j.sse.2022.108584 22 -> 10 (-12)

`06_to_kb.py --resolve-only` rebuilds `resolved/experiments.json` **from records.json**,
so for these papers it overwrites rich data with the thinner 0709 extraction. This is the
same hazard already noted for ylilammi (0709 decimated its dose profiles 98→4) — M1/M3
need the archived data, so this would have broken the twin.

Restored all three from git (`git checkout HEAD -- …/resolved/experiments.json`); total
is back to **357**. Verified first that none of the three contained any fabricated
condition — they never needed re-ingesting. Only **9** papers actually had fabrications;
re-ingesting all 16 that merely *contained categorical keys* was over-scoped.

**Rule going forward:** before `06_to_kb --resolve-only` on an existing paper, compare
`len(records.json)` against `len(resolved/experiments.json)`. If the KB has more, it is
not records-derived — re-ingesting will thin it. Scope re-ingests to papers that actually
need the fix, not to every paper that matches a broad grep.

## 2026-07-22 17:15 (local) — RESOLVED: caption-path parse vulnerability (the last one)
**Context:** `06`'s `panel_ctrl` applied `_ctrl(k, _num(v), _unit(v))` to every caption
condition, so `_num('Al2O3')` → **2.0** — the same fabrication shape as the series path,
via a different route. 67 rows across 9 papers.
**Status:** resolved
**Detail:** Fixed in code, not by re-flattening data. `_num_cond()` now requires the value
to match the same COMPLETE-number pattern (`_NUMU`) the series path uses — unit class
excludes `-`, so `Al2O3`, `TMA`, `2-propanol` are names, not numbers. Verified:

    substrate=Al2O3    -> rejected        temperature=150 °C   -> 150.0 '°C'
    precursor=TMA      -> rejected        pressure=0.8 mbar    -> 0.8 'mbar'
    coreactant=2-propanol -> rejected     dose=1.5e-3 Torr     -> 0.0015 'Torr'

**`_num()` is no longer applied to any non-numeric string anywhere in 06** — both the
caption and series paths now share one rule. The 9 affected papers were re-flattened from
cache (no vision) and re-ingested. Corpus-wide fabrication check: **[]**.

⚠️ Remaining cosmetic: 30 series conditions in `10.3762_bjnano.5.25` are named
`series_value` — the `series_axis or "series_value"` fallback firing when vision gave no
axis. The values are genuine numbers; only the quantity name is a placeholder, and it is
ungrounded in the ontology. Worth naming properly before batch-51.

## 2026-07-22 17:15 (local) — RESOLVED: 05 vision JSON parsing hardened
**Context:** `05` used bare `json.loads(r.text)` — no retry, no fence handling, error
truncated to 200 chars. `celc` hit this and produced **0 records**; only a manual retry
recovered it. At batch-51 scale a transient bad response silently zeros a paper.
**Status:** resolved
**Detail:** `05` now uses the same `_loads_json` as `04` (strips ```json fences, falls back
to the first balanced `{...}` block), **retries once** on parse failure, and keeps the
**full** raw text in `_parse_error` instead of 200 chars so failures stay diagnosable
without another API call. Verified against fenced, prose-wrapped, and plain JSON.

## 2026-07-22 17:15 (local) — RESOLVED: empty series label no longer renders "series: "
**Context:** `_classify_label` returns `"empty"` for a blank label, but the caller folded
it into the categorical branch.
**Status:** resolved
**Detail:** `05` handles `"empty"` explicitly (all series fields `None`, material falls
back to `mats[0]`), and `06` only builds `series_name` when there is a `series_kind` AND
a `series_value`. Corpus-wide check for `series_name == "series: "`: **[]**.

## 2026-07-22 16:30 (local) — RESOLVED BY REDESIGN: series identity is structured, not a string
**Context:** Two fabrications (`LTB:H2S` → LTB=2.0; `coreactant: 2-propanol` → coreactant=2.0)
both came from the same shape: 05 built a descriptive `"axis: value"` string and 06
split it back apart with `_num()`. Each guard fixed one route and the next input found
another.
**Status:** resolved — the failure mode is now structurally impossible
**Detail:** The string round-trip is deleted. 05 classifies **once** and emits structure:
`series_kind` (`numeric_sweep` | `categorical` | `material`), `series_axis`,
`series_value`, `series_value_num`, `series_unit`. 06 dispatches on `series_kind`:
only `numeric_sweep` yields a controlled condition, and it uses the float 05 already
parsed. **06 no longer calls `split()` or `_num()` on any label.** `series_name` is
rebuilt from structure for display and is never re-parsed. The `series_label` field is
gone.

Numeric-vs-categorical is decided by a COMPLETE-number match (`_NUMU`) whose unit class
excludes `-`, so `2-propanol` is a name, not a number. Validated across all four cases:

    class 1 sweep      '0.20'      -> numeric_sweep, num=0.20, material MoS2
    class 2 phase      'c-MoS2'    -> material,      num=None, material MoS2, phase c-MoS2
    class 3 substrate  'Al2O3'     -> categorical,   num=None, material Bi2Te3
    class 3 coreactant '2-propanol'-> categorical,   num=None, material RuO2

Re-extracted 6 papers: `series_kind` distribution — chemmater.2c01154 13 numeric_sweep,
2c02292 15 categorical, jcrysgro 3 categorical, celc 3 categorical, pssa 1 material +
3 categorical, tsf 1 categorical. **13 series conditions in the whole KB, all genuine H2
sweeps; zero series-source fabrications.**

⚠️ **Cosmetic:** an empty series label (single-curve panel) classifies as `categorical`
and renders `series_name: "series: "`. Harmless — it contributes no condition — but it
should be `None`. `_classify_label` returns `"empty"` and the caller folds that into the
categorical branch.

## 2026-07-22 16:30 (local) — 67 fabricated caption-source conditions in 9 STALE papers
**Context:** Found by the whole-KB fabrication sweep after the series redesign. These do
NOT come from the series path — they come from the **caption** path.
**Status:** needs-decision
**Detail:** Old records (extracted before the vision-prompt fix) still carry categorical
keys inside `conditions`, and `06`'s `panel_ctrl` line applies
`_ctrl(k, _num(v), _unit(v), source="caption")` to every one — so `_num('Al2O3')` yields
**2.0**:

    {'quantity': 'precursor',  'value': 2.0, 'source': 'caption'}
    {'quantity': 'material',   'value': 2.0, 'source': 'caption'}
    {'quantity': 'substrate',  'value': 2.0, 'unit': 'i', 'source': 'caption'}

**67 instances across 9 papers**; **0 in the 6 re-extracted papers**. Going forward this
cannot recur — the fixed prompt plus `_clean_conditions` (numeric-only) keeps categorical
keys out of `controlled`. But the existing KB rows are wrong today.

Cheapest remedy: **re-flatten the 9 stale papers from their cached `figure_data.json`**
(`scripts/reflatten_records.py`) — `_clean_conditions` strips the categorical keys, then
re-ingest. **No vision calls, no cost.** Not done here because those papers are outside
this task's DEEP6 scope. Worth clearing before batch-51 so the corpus has no fabricated
numbers at any scale.

## 2026-07-22 15:40 (local) — RESOLVED at root: categorical keys leaking into `controlled`
**Context:** `07` was proposing `material`/`precursor`/`substrate`/`process_type` as
ontology quantity_kinds. Root cause was upstream: the **vision prompt itself** listed
"precursor" as a conditions example — `conditions = things held fixed (e.g. temperature,
precursor, number of cycles)` — so the model dutifully put categorical fields there, and
`07` faithfully proposed them.
**Status:** resolved for re-extracted papers; see the stale-corpus note below
**Detail:** Fixed at the source. `VISION_SCHEMA` now asks for
`<numeric_value_with_unit_as_string>` and states: *"conditions = NUMERIC process
parameters held fixed in this panel … Do NOT put material, precursor, coreactant,
substrate, or process type in conditions — those are identified separately and are NOT
conditions."* A numeric-only backstop in `_clean_conditions` (value must start with a
digit) is retained as defense-in-depth — a prompt is not a guarantee.

The 6 deep papers were **re-extracted with fresh vision calls**, not cache-cleaned, so
they now go through the identical pipeline batch-51 will use and the prompt fix is
actually validated end-to-end. Result, measured on raw vision output before any filter:

    BEFORE (6 papers): precursor x4, coreactant x4
    AFTER  (6 papers): {}  — clean

Every condition key the model now emits is a genuine numeric process parameter:
`temperature`, `pressure`, `hot_wire_temperature`, `pulse_time`, `film_thickness`.
No structural data loss: panels/series counts identical across all 6; only `celc` point
count moved 33→35, fresh-vision sampling variance on a dense curve.
Vision cost: in=15,397 out=5,003 across 9 calls.

⚠️ **The stale corpus still pollutes proposals.** `gather_unmapped()` takes **no
arguments** — it iterates every directory under `extracted/`, so passing DOIs to
`07_propose_ontology.py` does not scope it. The 17 papers not yet re-extracted still
carry **300** categorical keys in their `records.json` `controlled` blocks, and those are
the entire source of the remaining junk candidates. The re-extracted 6 contribute zero.
This clears itself when the rest of the corpus runs through the fixed prompt.

## 2026-07-22 15:40 (local) — REGRESSION from re-extraction: series labels lost their semantic prefix
**Context:** Fresh vision on `10.1021_acs.chemmater.2c01154` returned Fig 16a's series
labels as bare values (`'0'`, `'0.20'`, `'0.50'`…) instead of the previous
`'H2 flow ratio: 0'`, `'H2 flow ratio: 0.20'`, …
**Status:** needs-decision
**Detail:** The `series_label → controlled` coercion in `06_to_kb` requires a
`"<name>: <value>"` shape. With bare numeric labels there is no name to parse, so the 6
H2-flow-ratio conditions added in `0b9ac9f` are **gone**: `H2 conditions: 0`,
`series-source conditions: 0`. `series_name` now holds `'0.20'` — a number with no
indication of what it measures.

Nothing is fabricated and nothing is corrupted, but the KB is **less informative** than
before the re-extraction. The quantity name does survive elsewhere: Fig 17's records
carry `coordinate: "H2 flow ratio"` (3 records), so the paper's sweep is still
represented — just not as a per-series condition on Fig 16a.

This is vision non-determinism between runs, not a consequence of the prompt edit (the
prompt does not mention series labels). It is the cost of re-extracting rather than
re-flattening. Options: (a) accept — the coordinate captures the sweep; (b) ask the
prompt to qualify series labels with the legend's quantity name; (c) fall back to the
panel's legend title when a series label is purely numeric. Worth settling before
batch-51, since parameter-sweep legends are common.

## 2026-07-22 14:55 (local) — Swept-condition quantities are ungrounded; 07 proposal needs curation
**Context:** Series conditions now reach `controlled`, but `canon_quantity('H2 flow
ratio')` returns `None`, so they enter the KB as free-text with `recipe_role: null` and
no family. Ran `07_propose_ontology.py` on the 6 deep papers to generate candidates.
**Status:** needs-decision — **do NOT run `08_merge_ontology` as-is**
**Detail:** 23 candidates written to `03_corpus/proposed/proposed_ontology.yaml`
(status: pending). Roughly a third are genuine; the rest are artifacts and must be
curated before any merge:

*Genuine and wanted:* `h2_flow_ratio` (the term that motivated the pass), `areal_mass`
(ng/cm²), `supercycle_ratio`, `log_conductivity`, `inverse_temperature` (1/K, from the
Arrhenius plot), `methanol_pulse_time` / `ruo4_pulse_time` — though the last two are
really `pulse_time` with `of_reactant` set, not new quantity kinds.

*Schema-key contamination (not quantities at all):* `materials`, `precursors`,
`coreactants`, `precursor`, `coreactant`, `material`, `process_type`, `substrate`,
`device_structure`. These are **record/scout dict field names** leaking into the
unmapped-term gatherer. That's a bug in the gather step, not a vocabulary gap.

*Normalisation artifacts:* `hot_wire_temperature`, `hot_wire_temperature_dash`,
`hot_wire_temperature_space` — three candidates for one quantity, because the gatherer
does not normalise `hot-wire temperature` / `hot wire temperature` / `hot_wire_temperature`
to a single surface form. Also `sup_percentage` (looks like a superscript parsing
artifact) and `pressure`, which duplicates the existing `total_pressure`.

*Wrong or already-decided individuals:* `LixAlyS` duplicates the `LiAlS_x` we already
added (different id, same substance) — and proposes `formula: Li x Al y S`, which would
break the molar-mass build. `[(Me3Si)2NBiμ-NSiMe3]2` is the **bismuth silylamide dimer
we deliberately held** pending the monomer/dimer policy, and its proposed
`deposits: [LixAlyS]` is simply wrong — in jcrysgro it deposits Bi2Te3.

**Before batch-51:** fix the gatherer (exclude schema keys, normalise separators)
before proposing at scale, or every sweep legend and every dict key will mint junk
candidates. The proposal file is committed for review but nothing is merged.

## 2026-07-22 14:25 (local) — RESOLVED: stoichiometry-strip bug in `_classify_label`
**Context:** The normalisation stripped trailing digits before comparing
(`re.sub(r"[+xy0-9\s]+$", ...)`), destroying stoichiometry — `c-WS2` → `WS` matched
nothing, so a real phase-tagged material was silently demoted to a condition and
rescued to `mats[0]` (wrong in a multi-material paper like `chemmater.2c01154`,
MoS2/WS2/TiS2).
**Status:** resolved
**Detail:** Two things were wrong and both are fixed:
1. *Stoichiometry.* `_strip_phase` now removes only the phase/stack prefix
   (`a-`, `c-`, `Mo/`) and a trailing non-stoichiometric `+x`/`+y`. Digits survive.
   The strip repeats (bounded to 4 passes) because prefixes stack in practice:
   `Mo/c-MoS2` → `c-MoS2` → `MoS2`. A single pass — the first attempt — left `c-MoS2`
   and still failed.
2. *Canonicalisation (Option A).* `_classify_label` now returns `(cls, matched)`, where
   `matched` is the **canonical scout material**. The record stores that, not the raw
   label. Storing the raw label (the intermediate attempt) fragmented the material axis:
   `canon_material('c-MoS2')` returns `None`, so `06_to_kb`'s `canon(raw) or raw`
   fallback would have created `MoS2`, `c-MoS2`, `a-MoS2+x`, `Mo/c-MoS2` as four
   separate KB materials and 3 spurious KG `Material` nodes. It also would not have met
   the original goal — `c-WS2` would have stored `c-WS2`, not `WS2`.

Phase is preserved rather than discarded: `material_raw` keeps the verbatim vision
label, and a new `phase` field holds the phase-tagged label **only when it differs from
the canonical material** (`c-MoS2` vs `MoS2`; `None` when they're equal).

Verified on `chemmater.2c01154`: `material` = MoS2 ×9, `phase` = {`a-MoS2+x`, `c-MoS2`,
`Mo/c-MoS2`, 6×None}, `series_label` = the 6 H2-flow-ratio labels. KB material Counter
is `{'MoS2': 9}` and KG `Material` node count stayed at **24** — no fragmentation. The
other 5 papers' records differ only by the additive `phase: null` key (verified: zero
non-`phase` diff lines).

## 2026-07-22 13:55 (local) — RESOLVED: figure numbering (docling index vs caption number)
**Context:** Records cited docling's image-extraction index as if it were the paper's
figure number. The offset is per-paper — it depends on how many caption-less images
(logos, journal marks) docling emits ahead of the first real figure.
**Status:** resolved
**Detail:** `_cap_fignum` already parsed the paper number from the caption, but an
earlier fix wired it only into the **display label** (`provenance.figure`), leaving the
primary numeric field as the docling index — which is why the bug looked unfixed. The
citable number is now an explicit field:
- `provenance.figure_number` — the paper's real number, parsed from the caption (or `None`)
- `provenance.fig_docling_index` — renamed from `fig_index`; the extraction index the
  scout drill tags (`F7`) refer to, kept for traceability
- `provenance.figure` — label; falls back to `"Fig <idx> (idx)"` when the caption has no
  parseable "Figure N", so an unresolved index is never displayed as a paper number

Measured offsets across the 6 deep papers, confirming this is per-paper and not a
constant that could be corrected globally:

    celc              idx 4  -> Fig 1      (-3)
    pssa              idx 13 -> Fig 10     (-3)
    jcrysgro          idx 7  -> Fig 6      (-1)
    tsf               idx 1  -> Fig 2      (+1)   <- index BELOW the paper number
    chemmater.2c01154 idx 16 -> Fig 7      (-9)   <- worst case
    chemmater.2c02292 idx 1  -> Fig 1      ( 0)

All drilled figures resolved; **no `figure_number: None`** in the current batch.
Only `relabel_figures.py` (a one-off retroactive script, already applied) referenced the
old `fig_index` name; the live pipeline does not. `06_to_kb.py` spreads provenance
wholesale, so both fields reach `resolved/experiments.json` with no change there.

## 2026-07-22 13:30 (local) — Series-label contamination of the material axis: rule settled
**Context:** Two variants of the same bug surfaced in the trial batch — condition
legends (`"H2 flow ratio: 0.20"`, `10.1021_acs.chemmater.2c01154`) and **substrate**
legends that are themselves valid formulas (`Al2O3`, `Si`, `SiO2` in `jcrysgro`, whose
deposited film is Bi2Te3). A naive "is this a formula?" test would keep the substrates
as material and get it wrong.
**Status:** resolved (classification rule); see the entry below for what is still open
**Detail:**

**The rule:** a series label counts as the material **only if it is in
`scout.materials`** (allowing a phase prefix). Every other label — including valid
formulas used as substrates, barriers, or co-reactants — becomes `series_label`, and
`material` falls back to `scout.materials[0]`. Implemented as `_classify_label` in
`05_figure_extract.py`, returning `material` / `condition` / `empty`.

Anchoring on `scout.materials` rather than on formula-shape is the guard that prevents
substrate and condition contamination of the material axis. **For the 51-paper batch
this matters most in multi-series figures**, which is where every instance so far came
from — substrate-comparison plots and parameter-sweep legends.

**Batch-51 watch list (both bug classes):**
1. *Unparseable captions.* Figures whose caption has no "Figure N" get
   `figure_number: None` and a `"Fig <idx> (idx)"` label. None occurred in the 6-paper
   batch, but they will at scale — grep for `(idx)` and eyeball those before citing.
2. *Over-routing by the material anchor.* If `scout.materials` misses a genuinely
   deposited second material, its series get re-routed to `series_label` and inherit
   `mats[0]` as material. `material_raw` retains the verbatim vision label, so any
   mis-route is **recoverable by re-flattening from cache — no vision re-call needed**.
   Cross-check `material_raw` against `material` after the batch to find these.

Re-flattened all 6 deep papers from cached `figure_data.json` (no vision re-call);
output was **byte-identical** to the previous scout-anchored helper, i.e. this revision
hardened the rule without changing current data. Record and point counts unchanged.

⚠️ **Known flaw, still present and now the main residual risk.** `_classify_label`
strips trailing digits (`base = re.sub(r"[+xy0-9\s]+$", "", base)`) *before* comparing,
which destroys stoichiometry — so the phase-prefix branch advertised in the docstring
never fires for any material whose formula ends in a digit (MoS2, WS2, TiS2, Al2O3,
TiO2, ZrO2, Fe2O3, Bi2Te3 — nearly all of them). Verified:

    mats = ['MoS2','WS2','TiS2']
    'MoS2'   -> material      'c-MoS2'  -> condition
    'WS2'    -> material      'c-WS2'   -> condition   <-- wrong
    'TiS2'   -> material      'a-MoS2+x'-> condition

Harmless across the current 6 papers because `mats[0]` is the right material every
time. **But in a multi-material paper, a phase-prefixed series such as `c-WS2` gets
`material = mats[0] = MoS2` — silently wrong**, and `chemmater.2c01154` is already such
a paper (MoS2/WS2/TiS2). Fix: strip the phase prefix without stripping trailing digits
(keep a narrow `+x`/`+y` suffix strip). Not applied — awaiting a decision.

## 2026-07-22 13:05 (local) — Series-label-in-material: fixed in records, NOT yet in the KB
**Context:** Multi-series figures were putting legend text into the `material` field
(e.g. `"H2 flow ratio: 0.20"` for `10.1021_acs.chemmater.2c01154`). Root cause was
post-processing in `flatten_records`, not the vision prompt.
**Status:** needs-decision (partially resolved)
**Detail:**

*Resolved:* `05_figure_extract.flatten_records` now classifies each series label as
material vs condition (`_label_is_material`), routing conditions to a new
`series_label` field and keeping the verbatim label in `material_raw`. All 6 deep-pass
papers were re-flattened from the cached `figure_data.json` via
`scripts/reflatten_records.py` — **no vision re-call**, record and point counts
unchanged. The bug was wider than first reported: substrates (`Si`, `SiO2`, `Al2O3`),
co-reactants (`Methanol`, `Ethanol`, `1/2-propanol`), precursor-pair labels
(`LTB:H2S`, `TDMAAl:H2S`) and thickness labels (`50nm LixAlyS`) were all sitting in
`material`. `jcrysgro` in particular went from `['Al2O3','Bi2Te3','SiO2']` to
`['Bi2Te3']` — the substrates had been masquerading as deposited films.

*RESOLVED 2026-07-22 14:55.* `06_to_kb.py` now sets `"series_name": r.get("series_label")`
and adds `"phase": r.get("phase")` (both record types, so the schema is uniform), and a
parseable `"<name>: <value>"` series label is additionally surfaced into `controlled`
with `source="series"` so tier/bridge logic can consume it rather than only display it.
Verified: `chemmater.2c01154` keeps `material {MoS2: 9}`, `series_name` = the 6
H2-flow-ratio labels, `phase` = {a-MoS2+x, c-MoS2, Mo/c-MoS2, 6×None}, and 6 H2
conditions in `controlled`.

⚠️ **The coercion needed a numeric guard.** The first attempt keyed only on `":" in
label`, which fired on precursor:co-reactant pair labels: `LTB:H2S` became
`{"quantity": "LTB", "value": 2.0}` — the 2.0 taken from the **H₂S subscript**, a number
that appears nowhere in the paper. `1-propanol` would have yielded `value=1.0,
unit="propanol"` by the same route. The rule is now **the value must start with a
digit** (`re.match(r"^[-+]?\.?\d", _val)`): `0.20` and `150 °C` are kept, `H2S` and `Si`
are rejected. Every label is still preserved verbatim in `series_name` regardless, so
rejecting a coercion loses nothing. Bare phase labels (no colon) live in `phase` only
and never become conditions. **Lesson for batch-51: any string→number coercion needs an
anchored numeric test, not a "contains a digit" test.**

*Previously open —*
`06_to_kb.py` hardcodes `"series_name": None` (lines 177 and 219) and sets
`"material_raw": r.get("material")` (line 163) from the **resolved** material rather
than the true raw label. As of the Option-A change it also drops the new `phase` field
— confirmed: `KB phase field: Counter({None: 9})` for `chemmater.2c01154`.

So `records.json` retains `series_label`, `material_raw` and `phase`, but
`resolved/experiments.json` carries none of them. Two things are therefore invisible to
any KB query: the H2-flow-ratio condition distinguishing the 9 MoS2 curves, and the
amorphous/crystalline/stack distinction that is the *point* of that paper.

**Decide before batch-51 whether phase and/or the condition series must be queryable in
`experiments.json`.** If yes, a single `06_to_kb` change carries both through — they are
already sitting in the records, so no re-extraction and no vision call is needed either
way. Deliberately not fixed in the Option-A commit to keep that change reviewable.

*Known flaw in the classifier regex.* `_label_is_material` strips trailing digits
(`base = re.sub(r"[+xy0-9\s]+$", "", base)`), which destroys stoichiometry, so the
phase/prefix branch never matches any material whose formula ends in a digit — i.e.
`MoS2`, `Al2O3`, `TiO2`, `ZrO2`, `WS2`, `TiS2`, `Fe2O3`, `Bi2Te3`, nearly all of them.
`c-MoS2`, `a-MoS2+x`, `a-Al2O3` are therefore misread as conditions. Only the exact
`lab == m` check saves unprefixed labels. Harmless across the current 6 papers because
the `mats[0]` fallback happens to be the right material every time — but in a
multi-material paper where a phase-prefixed series is *not* `mats[0]`, the record would
silently get the wrong material. Fix is to strip the prefix without touching trailing
digits before comparing.

*Rule for the 51-paper batch:* multi-series figures now route condition labels to
`series_label`, keeping `material` clean — but re-check the two items above before
scaling up, since both get worse with more multi-series papers.

## 2026-07-22 12:33 (local) — Bismuth silylamide dimer held out of the ontology
**Context:** Three jcrysgro precursors (`10.1016_j.jcrysgro.2017.04.019`) could not be
pinned down from secondary sources and were resolved from the docling'd paper text.
Two were confirmed and added; the silylamide is held.
**Status:** needs-decision
**Detail:**

*Resolved and added to `core_extensions.yaml`:*
- `(MeEtN)3Bi` (compound **4**) — monomer, `Bi(N(CH3)(C2H5))3` → 383.29
- `(Et3Si)2Te` — monomer, `(Si(C2H5)3)2Te` → 358.14, class `Chalcogenidant`

*Held — `[(Me3Si)2NBiμ-NSiMe3]2` (compound **6**):* deliberately NOT added, pending the
monomer/dimer policy decision below. Findings recorded here so they are not lost:
- The paper describes it as a **cyclo-dibismadiazane** — a 4-membered Bi₂N₂ ring where
  μ marks the two bridging NSiMe₃ groups and each Bi carries one terminal −N(SiMe₃)₂.
  It is a genuine discrete dimer, not an association equilibrium (unlike TDMAAl).
- Monomer unit `Bi(N(Si(CH3)3)2)(NSi(CH3)3)` → **456.56**
- Dimer as written `(Bi(N(Si(CH3)3)2)(NSi(CH3)3))2` → **913.12**
- Recommendation on record: use the **dimer**, since that is the molecule the authors
  synthesised, weighed, and loaded in the bubbler (heated to 100 °C).
- Source sentence: "the reaction of KN(SiMe₃)₂ with BiCl₃ yielded the cyclo-dibismadiazane
  [(Me₃Si)₂NBiμ-NSiMe₃]₂ **6**, which was obtained as a product mixture with roughly
  **5% (Me₃Si)₃Bi** as minor product".
- **Purity caveat:** that ~5% `(Me3Si)3Bi` is stated by the authors themselves, so any
  mass-based dose or molar-flux calculation inherits it. There is currently no field to
  record this — see the reagent-purity entry below.

## 2026-07-22 12:33 (local) — No field for reagent purity / stated impurities
**Context:** Surfaced while resolving the jcrysgro silylamide dimer, which the authors
explicitly report as a product mixture containing ~5% `(Me3Si)3Bi`.
**Status:** needs-decision
**Detail:** The precursor schema has no place to record a stated purity or a known
co-product. Anything that converts mass → moles (dose, molar flux, the twin's
exposure terms) silently assumes 100% purity. Options: add an optional
`purity_note` / `purity_fraction` field, or treat it as out of scope and rely on the
paper provenance. Not urgent, but it is a real source of systematic error that is
currently invisible.

## 2026-07-22 12:33 (local) — `Chalcogenide` is not a material class
**Context:** The trial-10 gap terms were specified with `class: Chalcogenide`, which
does not exist in the ontology's material class vocabulary.
**Status:** deferred (design note)
**Detail:** Actual vocabulary is `Metal, Nitride, Oxide, Phosphate, Sulfide, Telluride,
Ternary, TransitionMetalDichalcogenide`. Substituted the closest existing classes
rather than inventing one: `Bi2Te3 → Telluride` (joins GeTe, GST), `TiS2 →
TransitionMetalDichalcogenide` (joins MoS2, WS2 — same source paper), `LiAlS_x →
Sulfide` (joins ZnS; Li/Al are not transition metals). If a general `Chalcogenide`
superclass is wanted later, it belongs in `core.yaml`'s class hierarchy, not as an
individual's class string.

## 2026-07-22 12:33 (local) — Duplicate coreactant classes: `Reductant` vs `ReducingAgent`
**Context:** Noticed while classing the alcohol co-reactants from
`10.1021_acs.chemmater.2c02292`.
**Status:** needs-decision
**Detail:** Both classes exist and are semantically identical. `H2` and `B2H6` use
`ReducingAgent`; `atomic_hydrogen` and the four new alcohols use `Reductant`. This is
pre-existing, not introduced by the trial batch. Consolidating means editing
`core.yaml` (hand-curated), so it needs an explicit decision on which name wins.

## 2026-07-22 12:33 (local) — Monomer vs dimer policy for precursor molar_mass
**Context:** Extending the ontology with trial-10 gap precursors; several exist as
dimers or higher aggregates (TDMAAl `[Al(NMe2)3]2` 318.42 vs monomer 159.21; LTB
reported as hexamer/octamer).
**Status:** needs-decision
**Detail:** The build computes the **monomer** mass from `formula`. Decide whether the
twin needs the aggregated species mass; if so, decide how to store both — e.g.
`formula` = monomer plus `aggregation` plus a separate `reagent_mass` field. PubChem
lists monomer and dimer as separate CIDs, so it can ground both values but cannot
pick which one a given process actually uses. The `aggregation: dimer` field is
currently recorded on TDMAAl as passthrough metadata only; nothing consumes it.

## 2026-07-22 12:33 (local) — PubChem-grounded property fill
**Context:** Question of whether material/precursor info can be grounded in PubChem
rather than hand-entered.
**Status:** deferred (to the 51-paper batch)
**Detail:** PUG REST can auto-fetch formula / MW / CAS / SMILES / CID from a canonical
name. Blockers: (a) abbreviations don't match — a canonical name is needed first,
which is a human/paper step; (b) requires network, untested in this environment;
(c) monomer/dimer ambiguity (see above). Plan: run as a verification/enrichment pass
in the user's environment and **flag** mismatches between `molmass(formula)` and
PubChem MW rather than auto-overwriting. `pubchem_cid` is already being recorded on
new entries as provenance to make this pass cheap later.

## 2026-07-22 12:33 (local) — Non-stoichiometric materials carry no molar_mass
**Context:** `SiNx`, `MoOx`, and now `LiAlS_x` have a literal variable in their
composition.
**Status:** deferred (design note)
**Detail:** `molar_mass` stays `None` for these — correct, since the value is genuinely
undefined without a value for x. Any downstream consumer of `molar_mass` must tolerate
a missing value rather than assume every material has one. `MoOx` already lives in the
KB (`10.1116_6.0002436`), so this is not hypothetical.

## 2026-07-22 12:33 (local) — Silent-degradation risk in the build mass helper
**Context:** `molar_mass` auto-compute added to `build_ontology.py`.
**Status:** deferred (design note)
**Detail:** `_molar_mass()` swallows all exceptions and returns `None`, so if `molmass`
isn't importable the build drops every computed mass and still prints a normal-looking
summary. Cheap tell: the `computed:` count dropping to 0 in the coverage check — this
is exactly how the "precursors have no `formula` field" issue first surfaced. Not worth
a hard gate (this is enrichment, not correctness), but documented so a future silent
drop is diagnosable. Note the two interpreters in play carry different molmass
versions: system `python3` (3.8) has 2023.4.10, `psed310` has 2026.1.8 — they agree on
spot checks but are not pinned.
