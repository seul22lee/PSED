# ALD Autonomous-Design Stack — Integration Strategy
### KB (knowledge) × LLM agent (planning) × MPC twin (control)

This is the plan to connect four things that currently live apart: the
ontology-grounded **KB** (`0706_ontology/`, `0706_pipeline/`), the **LLM agent**
(`aldmodeling_agent/`), the physics **MPC/PID digital twin** (`PSED_MPC/`), and
the lessons from the two Argonne agent papers. It covers the five integration
approaches, how we can do the Argonne tasks *better*, and what new capabilities
this unlocks — broken into concrete coding pieces with file locations.

---

## 1. Why three components — the role of each

The core claim: **three components are needed because each fails at what the
others do.** The Argonne papers and PSED_MPC each hardcode or hallucinate the
piece another component owns.

| Component | Role | Answers | Why it's needed | Failure if removed |
|-----------|------|---------|-----------------|--------------------|
| **KB** (substrate / memory) | stores *what is known* — parameters, curves, processes — with **provenance + uncertainty** | "what do we know about this process?" | only component grounded in literature; the shared memory both others read | agent hallucinates (Argonne P1), MPC hardcodes one process (PSED_MPC) |
| **LLM agent** (interpreter / planner) | NL/high-level goal → structured **Recipe**; open-ended process discovery over combinatorial recipe space | "what should we grow, and roughly how?" | recipe/chemistry space can't be rule-enumerated; human intent is fuzzy | can't turn "grow doped ZnO" into a recipe; no discovery |
| **MPC twin** (executor / controller) | deterministic physics control of dose to hit a spatial/temporal target; **the model fills missing KB data** | "what exact pA, t_p hits the target?" | LLMs have run-to-run variability (Argonne P2) — unusable for quantitative control; physics model is exact + reproducible | dose optimization becomes noisy & unreliable |

**Data contracts (the arrows):**
```
        NL query / goal
             │
             ▼
   ┌──────────────────┐   retrieve (RAG)      ┌──────────────────┐
   │    LLM AGENT      │◀─────────────────────▶│       KB         │
   │  goal → Recipe    │   grounded facts,     │  ontology +      │
   └────────┬─────────┘   priors, candidates   │  experiments +   │
            │ Recipe (validated vs ontology)   │  Recipe/Model +  │
            ▼                                   │  kb_params()     │
   ┌──────────────────┐   params±σ, targets,   └────────┬─────────┘
   │   MPC / TWIN      │◀── warm-start ─────────────────┘
   │ optimal (pA,t_p)  │                                 ▲
   └────────┬─────────┘   optimized recipe / fitted params (write-back)
            └─────────────────────────────────────────────┘
                         autonomous-discovery loop
```

The **write-back arrow** is what the Argonne agents lack: they are stateless per
query. Here, every optimized recipe / fitted parameter flows back into the KB, so
the system's memory *grows* — the substrate for a self-driving lab.

---

## 2. Shared contracts (the glue — build these first)

Three contracts let the components interoperate without knowing each other's
internals.

### 2.1 The `Recipe` object — the bridge between all three
A Recipe is the actionable process spec. It unifies Argonne's JSON schema, our
reactant model, and the MPC's control inputs. Every KB experiment lifts to a
(partial) Recipe; the agent emits a Recipe; the MPC consumes one.

```jsonc
Recipe = {
  "recipe_id": "...",
  "material": "Al2O3",
  "reactants": [                        // our A/B/C/D reactant model
    {"label":"A","role":"precursor","species":"TMA",
     "dose_time":0.1,"purge_time":5,"partial_pressure":100},
    {"label":"B","role":"coreactant","species":"H2O",
     "dose_time":0.1,"purge_time":5,"partial_pressure":300}
  ],
  "cycle_sequence": "AB",               // generalizes to ABC / ABAC
  "supercycle": [ {"seq":"AB","n":10}, {"seq":"CD","n":1} ] | null,  // doping / nanolaminate
  "ncycles": 1000,
  "temperature": 500,
  "structure": {"H":0.2e-6,"W":0.1e-3} | null,   // geometry if HAR
  "targets": {"penetration_depth": 5e-4, "gpc_sat": 1.06e-10} | null,
  "provenance": "extracted | agent | user",
  "completeness": 0.0-1.0,              // fraction of fields populated
  "param_sources": {"gpc":"kb","K":"kb","q":"model-default"}  // per-field source tag
}
```
**Key point (user's ask):** missing fields are allowed. Completeness is tracked,
and the MPC **model fills the gaps** (§2.3). A KB experiment with no dose/purge
times still lifts to a valid Recipe with `completeness < 1`.

### 2.2 The KB service API — one interface both agent and MPC call
`0706_pipeline/kb_service.py` (NEW). Pure functions over the resolved corpus +
ontology. This is the *only* thing the agent and MPC import from the KB.

```python
kb_params(material, process=None, reactant=None) -> {quantity: {value, unit, source, sigma, n, refs}}
get_priors(material, process=None)               -> {gpc_expected, dose_typical, self_limited?, ...}
get_targets(material, structure=None)            -> {penetration_depth, pd50, ...}   # control targets
find_similar(recipe_or_conditions, k=5)          -> [ (recipe, similarity) ]          # warm-start / RAG
get_recipe(exp_id) / list_recipes(filter)        -> [Recipe]
retrieve(query)                                  -> [grounded facts + citations]      # RAG for the agent
```
Every returned value carries **source, uncertainty (σ, n), and citations** — this
is what makes the agent grounded and the MPC honest.

### 2.3 Parameter-resolution cascade — "the model complements missing pieces"
The heart of the KB↔MPC bridge. For each parameter the twin needs, resolve in
order, tagging the source:

```
1. KB literature value   (kb_params → extracted, with σ across papers)      source=kb
2. Ontology equation     (defined_by: derive from other known quantities)   source=derived
3. Model default / fit   (PSED_MPC model's own default, or fit to a curve)  source=model
```
So the MPC always gets a complete parameter set, but each value knows *where it
came from* and *how confident* it is → enables uncertainty-aware control (§5) and
flags which parameters are literature-grounded vs assumed.

---

## 3. Coding breakdown — the five approaches as phases

Ordered by dependency. Each piece lists **file · function · why**.

### Phase 0 — Foundations (prerequisite for everything)
- **`PSED_MPC/channel_model.py`** (NEW) — extract `channelModel` + `evaluate_step`
  + `mpc_step` + cost from the notebooks into an importable module. *Why: it's
  trapped in `.ipynb`; nothing can parameterize it until it's a module.*
- **`0706_pipeline/kb_service.py`** (NEW) — skeleton of §2.2 over
  `output/*/resolved/experiments.json` + `ald_ontology.json`. *Why: the single
  KB interface.*
- **`0706_pipeline/recipe.py`** (NEW) — the `Recipe` dataclass/schema (§2.1) +
  `validate(recipe)` against the ontology. *Why: the shared bridge type.*

### Phase 1 — MPC ← KB parameters  *(Approach 1: the headline)*
The channelModel ↔ ontology mapping is nearly 1:1 (we extracted many verbatim):

| channelModel attr | ontology quantity | status |
|---|---|---|
| `gpc` (106 pm) | growth_per_cycle | **extracted ✓** |
| `K` (100) | adsorption_rate_constant | **extracted ✓** |
| `c` (0.01) | reaction_probability | **extracted ✓** |
| `da` (591 pm) | precursor_molecular_diameter (A) | **extracted ✓** |
| `db` (418 pm) | precursor_molecular_diameter (B) | extractable |
| `MA`,`MB` | molecular_mass (A/B) | **extracted ✓** |
| `H`,`W` | feature_height, feature_width | **extracted ✓** |
| `T`,`t_p`,`pA`,`pB` | temperature, pulse_time, partial_pressure (A/B) | **extracted ✓** |
| `M`,`rho`,`b_film`,`b_a` | molar_mass, film_density, stoichiometry | add to ontology individuals |

- **`PSED_MPC/kb_bridge.py`** (NEW) — `params_for(material, process) -> dict` that
  calls `kb_service.kb_params`, applies the §2.3 cascade, and maps quantity ids →
  channelModel attribute names via a `PARAM_MAP`. *Why: turns the twin from one
  hardcoded process into any KB process.*
- **`PSED_MPC/channel_model.py`** — `channelModel.from_kb(material, process,
  kb=...)` classmethod that sets attrs from `kb_bridge`. Keep the hardcoded
  `__init__` as the fallback/default. *Why: non-breaking; defaults survive.*
- **`0706_ontology/core.yaml`** — add `film_density`, stoichiometry
  (`metal_atoms_per_formula`) as quantities/material attributes for M, rho,
  b_film. *Why: the last 3 params the KB doesn't yet carry.*
- **Deliverable:** `channelModel.from_kb("Al2O3","ThermalALD")` reproduces the
  current hardcoded run (regression check), then works for TiO2/HfO2/SiO2.

### Phase 2 — Recipe objects in the KB  *(Approach 4 groundwork + Recipe emphasis)*
- **`0706_pipeline/stages/s08_resolve.py`** — after `finalize`, emit a `recipe`
  block per experiment via `recipe.from_experiment(exp)` (material, reactants,
  cycle_sequence, ncycles=cycle_number, temperature, structure H/W, targets =
  extracted penetration_depth/pd50, completeness + param_sources). *Why: lifts our
  measurement records into actionable recipes; this is the object the agent and
  MPC both speak.*
- **`0706_pipeline/recipe.py`** — `from_experiment(exp)` + `completeness(recipe)` +
  `fill_gaps(recipe, kb, model=None)` (uses §2.3 cascade; the twin model supplies
  dose/purge/params the KB lacks). *Why: "some info may be missing but the model
  complements it."*
- **`0706_pipeline/build_analysis.py`** — add a Recipe view/column (dose/purge,
  cycle_sequence, completeness) so recipes are inspectable. *Why: visibility.*

### Phase 3 — Kinetic model as an ontology object  *(Approach 2)*
- **`0706_ontology/core.yaml`** — new `models:` section: each model = {id, equations
  (reuse `defined_by`), inputs (quantity ids), assumptions, refs}. Encode the
  Ylilammi/PSED_MPC Langmuir model (θ evolution, GPC, x_half) here. *Why: the twin's
  physics becomes traceable, swappable, and linked to the quantities it consumes —
  not magic numbers in a notebook.*
- **`0706_ontology/build_ontology.py`** — compile `models`, validate input quantity
  ids exist. *Why: integrity.*
- **`PSED_MPC/channel_model.py`** — tag which ontology model it implements
  (`MODEL_ID = "ylilammi_langmuir_channel"`). *Why: KB and twin agree on which model.*

### Phase 4 — Twin validation against KB curves  *(Approach 3)*
- **`PSED_MPC/twin_validation.py`** (NEW) — for each KB experiment with a measured
  conformality curve, run `channelModel.from_kb(...)`, compare predicted vs measured
  profile using the **existing similarity engine** (`similarity.curve_similarity`:
  nRMSE, R², overlap) + Δ(PD50). *Why: reuses our model-vs-experiment 2×2 as the
  twin's validation harness; tells us where the model (or the literature params)
  is wrong.*
- **`0706_pipeline/similarity.py`** — expose `curve_similarity(a_points, b_points)`
  as a plain function (currently experiment-keyed). *Why: reuse for twin vs data.*
- **Deliverable:** a validation report: per process, twin-vs-measured R²; flags the
  discrepancies (→ active-learning targets, §5).

### Phase 5 — Warm-start / priors for the controller  *(Approach 5)*
- **`PSED_MPC/kb_bridge.py`** — `warm_start(material, target) -> (pA0, tp0)` via
  `kb_service.find_similar` (nearest known process' dose conditions). *Why: Argonne
  P2 got −33% samples from one prior; a literature warm-start cuts MPC/PID
  iterations and the run-to-run spread.*
- **`PSED_MPC/*mpc*.py`** — accept optional `(pA0, tp0)` and `priors` (expected GPC,
  self-limited?) from the bridge. *Why: seed the optimizer with grounded values.*

### Phase 6 — Orchestration: KB ↔ LLM ↔ MPC  *(Approach 4)*
- **`aldmodeling_agent/`** (extend `ald_modeling_co_pilot_*.py` + `llm_client.py`)
  — the agent: (1) NL query → intent; (2) `kb_service.retrieve` for grounding
  (RAG); (3) emit a `Recipe`; (4) `recipe.validate`; (5) hand to MPC. *Why: the
  planner; grounded by KB so it doesn't hallucinate.*
- **`orchestrator.py`** (NEW, repo root or `0706_pipeline/`) — the loop:
  `agent(query) -> Recipe -> kb.fill_gaps -> mpc.optimize(recipe, warm_start) ->
  result -> kb.write_back`. *Why: makes the three roles a pipeline; the single
  entry point for "grow X with target Y".*
- **`0706_pipeline/kb_service.py`** — `write_back(recipe, result)` appends
  optimized recipes / fitted params to a `kb/derived/` store. *Why: closes the
  autonomous-discovery loop; memory grows.*

---

## 4. Doing the Argonne tasks *better*

### 4.1 Process identification (Paper 1, Table VI) — grounded + cited
Their agents fail on rare chemistries (Os/O₂ #17, W/Si₂H₆ #4, ternary sulfides
#30) because they rely on LLM memory. **We ground it in extracted literature.**
- **`0706_pipeline/process_id.py`** (NEW) — `identify(material, reactor_config) ->
  Recipe + citations`: query KB for precursor→material→coreactant paths compatible
  with the installed channels, rank, return with provenance. Falls back to the LLM
  only when the KB is silent. *Why: beats pure-LLM on the long tail and adds
  citations (trust).*
- **`0706_pipeline/bench_argonne.py`** (NEW) — run their Table VI (30 challenges) +
  Table V through our KB-grounded identifier and score with their 0–1 rubric.
  *Why: a direct, publishable comparison vs their Fig. 9/11 numbers.*

### 4.2 Process optimization (Paper 2) — deterministic + primed
Their weakness: run-to-run variability + can't spot non-self-limited (CVD).
- **Determinism:** route dose optimization to **PSED_MPC (physics MPC)** instead of
  an LLM — no run-to-run variability by construction.
- **Priors:** `kb_service.get_priors` supplies expected GPC + "is this process known
  self-limited?" *from the literature*, which is exactly the CVD/self-limited
  determination their agent fails at. *Why: the KB already knows what their agent
  must rediscover noisily.*
- **Hybrid:** LLM proposes strategy → physics-MPC executes/validates → best of both.
  Add to `orchestrator.py` as an "optimize" intent.

---

## 5. What else becomes possible (new capabilities, beyond both papers)

1. **Conformality-aware recipe optimization** — neither Argonne paper handles HAR
   penetration; PSED_MPC + KB does. Optimize a recipe for a *target penetration in a
   real structure*. **Our unique niche.** (Phases 1+5.)
2. **Inverse design / what-if** — target (thickness / PD50 / conformality) → invert
   twin+KB to a recipe. `PSED_MPC/inverse.py`. Neither paper does literature-grounded
   inverse design.
3. **Uncertainty-aware / robust control** — KB gives parameter spread (σ across
   papers) → robust MPC that hits the target across the uncertainty band, not a point
   estimate. Enabled directly by §2.3's per-param σ.
4. **Model–data discrepancy → active learning** — Phase 4 flags where the twin
   disagrees with measured curves; those are the highest-value next experiments.
   `twin_validation.py` → ranked experiment suggestions.
5. **Autonomous loop with persistent memory** — the write-back arrow (§1) makes the
   KB grow with every run; the Argonne agents are stateless. This is the self-driving
   substrate.
6. **Provenance & explainability** — every recommendation cites papers and shows each
   parameter's source (kb/derived/model) + σ. Neither paper provides provenance —
   essential for trust in autonomous labs.
7. **Supercycle / nanolaminate / doping design** — `cycle_sequence` + `supercycle` in
   the Recipe make these structured, validatable objects (Argonne represents them as
   ad-hoc text).
8. **Multi-objective Pareto recipes** — PSED_MPC already trades pressure/time/
   conformality; add KB-derived constraints (precursor cost, thermal budget). Neither
   Argonne paper is multi-objective.

---

## 6. Suggested order (milestones)

1. **M0 – Foundations:** Phase 0 (channel_model.py module, kb_service skeleton,
   Recipe schema). *Nothing works until the twin is importable and the KB has an API.*
2. **M1 – The headline:** Phase 1 (`channelModel.from_kb`). Regression-check it
   reproduces the hardcoded Al₂O₃ run, then generalize to TiO₂/HfO₂. **Biggest single
   win; proves the KB↔twin bridge.**
3. **M2 – Recipes:** Phase 2 (recipes in the KB) + Phase 5 (warm-start). Now the twin
   is KB-driven end-to-end.
4. **M3 – Rigor:** Phase 3 (model in ontology) + Phase 4 (twin validation).
5. **M4 – Beat Argonne:** §4.1 process-id + §4.2 optimization, with `bench_argonne.py`.
6. **M5 – Orchestrate:** Phase 6 (agent↔KB↔MPC loop) + §5 new capabilities.

**Start at M1's bridge** — it's concrete (params already extracted), non-breaking
(defaults survive), and immediately turns PSED_MPC from a one-process demo into a
literature-parameterized, uncertainty-aware conformality twin.

---

## Future directions — expanding model coverage (noted during M3)

The twin currently implements **one branch** of the `ald_surface_kinetics` family
(Ylilammi, thermal precursor-diffusion-limited). The ontology now records three
sibling models it does **not** yet execute — that is the roadmap:

- **Plasma / recombination-limited (Arts 2019, `arts_recombination`).** PEALD
  conformality is set by radical *surface recombination*, not precursor diffusion.
  Adapting the twin is a small, additive change: add the loss term `−η·r·ñ` to the
  radical transport equation (Yanguas-Gil & Elam continuum model) and fit the
  recombination probability `r` from the penetration-vs-ln(dose) slope (Arts Eq. 5–6).
  We do not extract these equations/`r` from the paper yet — that extraction + a
  `plasma` twin variant is the next model-coverage step. (8 Arts profiles are marked
  *out of scope* in the validation report today.)
- **Reversible + evolving geometry (Aguinsky 2023, `aguinsky_reversible_levelset`).**
  Adds an evaporation flux `Γ_ev` (reversibility) and level-set topography for the
  narrowing channel — captures the high-Γ_ev transition region Ylilammi's frozen-height
  assumption misses.
- **0-D saturation for dose optimization (Yanguas-Gil 2026, `yanguas_gil_saturation`).**
  The agent-benchmark GPC-vs-dose model with a CVD (non-self-limited) component — the
  target for M4's process-ID benchmark.

**Other configurations / geometries.** The Recipe + `structure` individuals already
generalize beyond LHAR channels (trench, via, AAO, cylindrical pore…); the twin's
hydraulic-diameter mapping is the single hook to swap geometry. Broadening beyond
Al₂O₃/TMA (more precursors, coreactants, materials) is bounded only by the KB's
species/parameter coverage, which the covariate-conditioned imputation already fills
probabilistically.
