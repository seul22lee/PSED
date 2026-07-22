# Extraction quality audit — 3 papers, end-to-end to M5

**Setup.** The LLM extraction stages (docling 01, enrich 05, experiment_schema 06 =
gemini-2.5-flash + GOOGLE_API_KEY) **cannot run in this sandbox** (docling + gemini SDK
not installed, no API key). So new papers can't be extracted here. Instead we ran the
full **deterministic downstream** (resolve → recipes → KB → M0–M5) on 3 already-extracted
papers and audited whether the stored knowledge faithfully matches the source.

Downstream ran clean end-to-end (s08_resolve, build_recipes, kb_service, M-modules all OK).
The problems are in **extraction quality**, and they will scale badly to ~967 papers.

## What is done well
- **recipe_role tagging is correct** on every field (control_setting / structure /
  model_parameter / species_property / observable / derived). This is *why* the downstream
  works despite messy raw records — the ontology layer separates signal from noise.
- **Some conditions extracted correctly**: Aguinsky temperatures 150/220/310 °C match its
  Table 1; Yim 300 °C; per-reactant pulse/purge from methods (via methods_recipe.py).

## Errors & weaknesses found (root-caused)

**E1 — Global/figure conditions bleed onto records that shouldn't have them.**
All 116 Ylilammi records — *experimental (10) and model (106) alike* — carry **T = 227 °C
(500 K)**, which is the value in the **model figure captions** (Figs 2–5), not the
experimental growth temperature (~300 °C). The temperature was assigned globally from a
model figure, not extracted per experiment. → wrong conditions on experimental data.

**E2 — Model parameters & species properties pooled into `controlled[]` as if they were
process conditions.** Per Ylilammi record: `molecular_mass` (×232), `precursor_molecular_
diameter` (×230), `adsorption_rate_constant`/`reaction_probability`/`site_density` (×112).
These are *fitted model params* and *intrinsic species properties*, not knobs the
experimenter set. They inflate every record (~19 "conditions", only ~6 real settings) and
duplicate the same species constant hundreds of times.

**E3 — Model curves and experimental data are both stored as "experiments."** Ylilammi:
**106/116 records are `relevance=model`** (parametric model sweeps), 90% of the "corpus"
for that paper. 92 are `sweep_point` — individual points of a model curve fragmented into
separate "experiments."

**E4 — Under-extraction of the real experimental content (lacks).** The actual experimental
process window (true growth T, the doses used in the measured runs) is thin or wrong;
Ylilammi **TiO₂ = 2 records** though the paper has TiO₂ conformality data; experimental
thickness profiles are a minority drowned by model curves.

**Containment:** E1–E3 are *mitigated downstream* by recipe_role + relevance tags + fix #1
(species props → ontology), which is why M0–M5 still function. But the raw extraction is
low-fidelity, and at 967 papers the noise, bloat, and misattribution compound.

## Root cause (single)
The extraction is **figure-centric and role-blind**: stage 06 reads a figure + the paper's
parameter table and dumps *everything it sees* into one flat `controlled[]` per figure,
without distinguishing **(a) process conditions the experimenter set**, **(b) fitted model
parameters**, **(c) intrinsic species properties**, or **(d) experimental vs model curves**.

## Fix strategy (folds into EXTRACTION_FRAMEWORK.md)

**S1 — Role-separated extraction schema (biggest fix).** Emit into typed buckets, not one
flat list:
  - `process` (conditions the experimenter set: T, P, dose, purge, cycles, chemistry),
  - `model_fit` (a *separate object per material/process*: K, c, β0, Γev, site_density …),
  - species properties → **never per-experiment** (ontology individual only),
  - so `controlled[]` holds only real control_settings. The ontology recipe_role map
    already defines these classes — enforce them **at extraction**, not just downstream.

**S2 — Experimental-vs-model classifier (relevance-first).** Classify each figure/curve
from its caption ("measured/experimental" vs "simulated/model/calculated/fitted"); store
model curves as `model_output`, never as experiments; **do not fragment a model sweep into
per-point experiments**. Kills E3 and the 90%-model inflation.

**S3 — Conditions from METHODS, per experiment — not from figure captions.** Extract the
true growth T / doses from the experimental section and bind them to the experimental
records; never propagate a model-figure caption value onto experimental data. Kills E1.
(Generalize methods_recipe.py into the Stage-2 rules library.)

**S4 — Deduplicate paper-level facts.** One `model_fit` and one species-property lookup per
(paper, material, process) — referenced, not copied into every figure. Kills E2 bloat.

**S5 — Caption-gating (already in framework).** Only digitize/extract figures whose captions
show experimental data of interest → far fewer model curves ingested in the first place.

**S6 — Validation gate.** Sanity bounds (T∈[50,500]°C, plausible P/dose/GPC) + a
"globally-constant field" flag (a single value across all records ⇒ likely a figure-caption
leak, not a real per-experiment condition) → review queue.

**Net:** these turn the extraction from "dump-then-tag-downstream" into "separate-at-source,"
which removes E1–E4 at the root, shrinks records ~3×, and (with caption-gating + triage)
cuts tokens — the same changes that make the 967-paper run affordable also make it correct.
