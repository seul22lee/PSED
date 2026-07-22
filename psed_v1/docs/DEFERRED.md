# Deferred decisions & open questions

A running log of decisions we consciously postponed and things worth revisiting, so
they survive across sessions. **Newest entries at the top.** Remove an entry once it
is genuinely resolved (and say where the resolution lives).

Status values: `deferred` · `needs-decision` · `needs-verification`

---

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

*Still open — the rescued condition does not reach the KB.* `06_to_kb.py` hardcodes
`"series_name": None` (lines 177 and 219) and sets `"material_raw": r.get("material")`
(line 163) from the **resolved** material rather than the true raw label. So in
`resolved/experiments.json` the material is now clean, but `series_name`,
`series_label` and a faithful `material_raw` are all absent — the H2-flow-ratio
condition that distinguishes the 9 MoS2 curves is still lost at the KB boundary.
Deciding how to carry it (populate `series_name` from `series_label`? promote a
parsed `name: value` label into `controlled`?) is the open question.

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
