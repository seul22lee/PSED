# dt — knowledge base + digital twin for ALD in a lateral channel

Downstream use of the PSED knowledge base (`psed_v2/kb`): the KB is linked to an analytical/physics model of ALD so that an agent can
answer requests such as "coat a 500 nm lateral gap with Al2O3 so that the film reaches 100 µm in our reactor" and return a recipe.
This folder holds the model code, every change made to it, the fits to KB data, the digital-twin demonstrations and the paper figure.

## Ground rules

- The base is Larry's model (`original/ReactionModel.ipynb`, section "Coupled", cells 71–86), extracted verbatim into
  `reaction_model.py` (commit B0 in `CHANGELOG.md`). All later changes are made on top of it.
- Every change is one row in `CHANGELOG.md` (id, where, type, what, why / evidence). Known issues that were not changed are listed
  separately (K rows). User decisions are D rows.
- Scope of the model (model card): structure class `lateral_channel`, process mode `thermal`, model `ylilammi_diffusion_reaction`.
  TMA is treated as irreversible (Larry's model, decision A7).

## Layout

```
reaction_model.py     Larry's reactor model, FlatModel, ChannelModel, ModelCoupling (+ logged changes)
yli18_approx.py       analytic approximation of Ylilammi et al. 2018 (Eqs. 17-37), used for multi-cycle profile fits (A1)
fitting/              fits of KB profiles: slope method (A3), literature campaign (A4), yim20/gao15 fits (A2), WALDO pressure fit (A10),
                      WALDO per-cycle and purge-decay analysis (A12, A13), QCM identifiability with desorption (A14)
demo/                 digital-twin demonstrations on a synthetic reactor B (A5, A6, A8, A9, A11)
figures/              paper figure fig_dt_kb_control (concept + results, F2)
tests/                12 tests + 1 strict xfail
original/             Larry's notebook, untouched
CHANGELOG.md          every change and known issue
DESORPTION.md         WALDO desorption evidence, proposed sticky-precursor terms (not implemented), identifiability
REPRODUCE.md          how to rerun everything, expected numbers
run_all.sh            runs all steps (~15 min on 2 cores)
```

## Models

| model | what it computes | used for |
|---|---|---|
| reactor transport (`ALD_Reactor_Model`) | 1D advection–diffusion of TMA/H2O along a tube reactor, irreversible wall uptake (β_wall per reactant), inlet partial-pressure pulses | recipe → partial pressure p(t) at the sample |
| flat sample (`FlatModel`) | coverage θ of a flat sample (QCM), irreversible Langmuir, H2O resets θ | in-situ QCM signal |
| HAR channel (`ChannelModel`) | gas and coverage along a lateral channel (Knudsen + molecular diffusion, implicit solver) | penetration depth (front at θ = 0.5) |
| yli18 analytic (`yli18_approx.py`) | Ylilammi 2018 approximation with narrowing over many cycles | fits of literature thickness profiles |

Coupling is one-way: the reactor model gives the sample-region average pressure, which drives the flat or channel model
(Larry's `ModelCoupling` scheme).

## Main code changes (full list in CHANGELOG.md)

- Units: axial velocity (Pa passed as Torr, 133× slow), molar masses g→kg (thermal velocity 31.6× slow), coverage rates missing
  1/(RT) (~3100× fast) — R1–R3, F1, C2–C4.
- ChannelModel: decoupled pressure/coverage with an implicit diffusion step (Larry's idea, C5/C5b), optional reversible adsorption K
  (C6, default off), narrowing on both walls (C7), banded solver when no gradient is needed (C10, 20× faster).
- Growth counted from the θ increase only (G1); reactor walls inert by default (D1); per-reactant sample sticking (P1).
- Reactor model: `return_profile` (C9) so a pulse window is integrated in one BDF call (0.4 s instead of 18 s for 1 s of
  process time); optional reversible wall reservoir (C11, default off).
- Known issue K9: Larry's run_model resets small gas and wall-coverage values at the end of every call; with 5 ms calls this
  distorts low-dose runs with reactive walls. Avoided by one call per pulse window (A8).

## Results

### Reproduction of the source paper (yli18)
- ChannelModel, yli18 Fig. 3 inputs: front 56.6 µm (paper 55.9) at 0.02 s, 129.3 µm (paper 137.6) at 0.1 s.
- yli18_approx with Table I: RMSE 2.5 nm (Al2O3), 0.9 nm (TiO2).

### Literature fits (A4; KB papers yli18, yim20, gao15; 17 curves)
| data | species | slope c | profile-fit c | p_A0 (Pa) | reported |
|---|---|---|---|---|---|
| yli18 Fig. 6 | TMA | 4.1e-3 | 7.5e-3 | 111 | c 5.72e-3 |
| yim20 (10 curves) | TMA | 1.5–12e-3 | 1e-3–1.6e-2 | 54–151 | c 4e-3 |
| yim20 0.4 s pulse | H2O | 2.6e-4 | 9e-5 | 212 | c 3e-4 |
| gao15 Fig. 5a | TMA | 2.2e-3 | 1.6e-3 | 44 | none |
| yli18 Fig. 7 | TiCl4 | — | not identifiable | K 0.26 1/Pa | K 0.252 |

- p_A0 (entrance pressure) is identifiable from a profile; c is only bounded (3–5× per curve). p_A0 does not transfer between tools.
- TiCl4 (reversible, K·p ≈ 7–20): K is identifiable, c is not — outside the irreversible model (extension point).

### Digital twin on a synthetic reactor B (A5, A11, A9)
Reactor A = Larry's default geometry (L 64 cm, ID 3.5 cm, 1 Torr, 120 sccm), ideal delivery, inert walls.
Reactor B = L 30 cm, ID 8 cm, 2 Torr, 300 sccm, true delivery η = 0.6 and wall sticking β_wall = 2e-3 (set by hand, hidden from the twin).
Channel: 500 nm gap; target front 100 µm after one TMA pulse; 300 °C; c_TMA = 4e-3 from the KB.

- Same recipe in both reactors: 0.31 s TMA → 99 µm in A, 63 µm in B.
- Calibration on a QCM dose series (Δm_TMA after pulses of 0.1–3.2 s at a reduced source flow; mass scale = saturated TMA step on the
  WALDO reactor, 71 ng/cm²; synthetic noise 2 ng/cm²): η = 0.58, β_wall = 2.1e-3. Corrected pulse 0.66 s → 100.0 µm in B.
- If the twin is given c at half / twice the true value: 83 / 116 µm.
- Full recipe for B (A9): TMA 0.66 s / purge 1.2 s / H2O 0.72 s / purge 1.3 s. Purges are gas-transport lower bounds (no wall
  desorption or dead volumes in the model). H2O delivery and H2O wall reactivity are assumptions.

### Identifiability (why the KB is needed)
- A flat in-situ signal (QCM) sees only the product c·η: sticking and precursor delivery cannot be separated by it.
  With c from the KB, the twin calibrates the reactor terms (η, β_wall). A dose series separates η and β_wall (correlation 0.9);
  a single low-dose trace does not (1.0).
- A test-chip profile (ex situ, roof removed) responds to the delivered exposure and only weakly to c; with QCM it gives c,
  which can be written back to the KB.
- The KB prior sets the recipe accuracy (±16 % in front depth for a 2× error in c); one test chip removes most of it.

### Real reactor data (WALDO, NCSU) — not included here
Collaborator data (QCM, pressure, temperature of two runs) were examined but are not part of this public folder:
- Standard runs saturate every half-cycle, so c and η cannot be fitted from them; they give the coverage-to-mass scale.
- The reactor model reproduces the measured H2O pressure spike at the exhaust gauge (gas transport + 0.33 s gauge lag).
  The TMA spike has a long tail that gas transport alone does not explain (wall desorption or delivery-line bleed).
- `fitting/waldo_pressure_fit.py` needs `WALDO_PRESSURE` pointing to the data file.
- Desorption (DESORPTION.md, A12-A14): the per-cycle QCM mass gains of the verification summary are reproduced from the raw logs
  (mean abs difference 1.6 ng/cm2, QCM step 2.1). The QCM loses mass during every purge (TMA: fast 3 ng/cm2 in ~1 s + slow 14 ng/cm2,
  tau ~58 s; H2O: 7 + 8 ng/cm2, tau ~24 s); the QCM does not read pressure and the TMA exhaust tail decays on a similar time scale
  (31-42 s). Proposed model terms (sticky precursor, Yanguas-Gil 2021 Eqs. 21-22) are written out there but not implemented;
  identifiability: the 7/02 run fixes only the reacted mass, kd (roughly) and the desorbing amount; a dose series with long purges
  fixes all of them given c from the KB. Scripts need `WALDO_PRESSURE`, `WALDO_QCM`, `WALDO_TEMP`.

## Paper figure

`figures/fig_dt_kb_control.pdf` (from `fig_dt_kb_control.py`): illustrative example of the proposed agentic workflow.
(a) user input → agent → tool calls linking KB, twin and reactor (steps 1–5); (b) model selection (illustration);
(c) c reported in the KB and fitted in this work; (d) fits to profiles of three papers; (e–g) synthetic reactor B:
calibration on a QCM dose series, recipe correction, effect of the prior. The agent is envisioned, not implemented: each step
was executed as a scripted call.

## Limitations

- Reactor B and all twin "measurements" are synthetic; only panels c, d of the figure use real (KB) data.
- Purge times are lower bounds; real purges are set by wall/line residue.
- H2O delivery and H2O wall reactivity in the full recipe are assumed, not calibrated.
- Fitted parameters are model/solver specific (yli18 approximation vs ChannelModel).
- Results were produced against the KB at commit ba77854; later KB updates changed some digitized curves slightly, so a rerun
  may shift fitted numbers in the last digit(s). Tests pass on the current KB.
- Not implemented: the agent, model-card selection code, reversible (TiCl4), plasma (radical recombination, art19) and pore (ela03)
  models — extension points.

See `REPRODUCE.md` to rerun everything and `CHANGELOG.md` for every change.
