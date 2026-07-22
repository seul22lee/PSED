# Deferred decisions & open questions

A running log of decisions we consciously postponed and things worth revisiting, so
they survive across sessions. **Newest entries at the top.** Remove an entry once it
is genuinely resolved (and say where the resolution lives).

Status values: `deferred` · `needs-decision` · `needs-verification`

---

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
