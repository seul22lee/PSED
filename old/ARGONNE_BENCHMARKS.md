# Argonne ALD-agent benchmarks — full technical setup + transfer to PSED

Reference extraction of the two papers, with **every setup detail** and how each maps
onto our code. Use this as the spec when (re)building evaluations so they match the
papers' design exactly.

- **Paper 1** — A. Yanguas-Gil, *"Performance of AI agents based on reasoning language
  models on ALD process optimization tasks,"* J. Vac. Sci. Technol. A **44**, 043410
  (2026). doi:10.1116/6.0005313. → **dose-time OPTIMIZATION** (our M4 §4.2).
- **Paper 2** — A. Yanguas-Gil, J. C. Jones, S. Kim, C. T. Nguyen, J. W. Elam,
  *"Design and performance of AI agents interfacing with an ALD tool,"* Rev. Sci.
  Instrum. **97**, 053903 (2026). doi:10.1063/5.0318770. → **agent+reactor + process
  DISCOVERY / instruction** (our M4 §4.1). Code: `github.com/aldsim/aldenv`.

---

## PART A — Paper 2 (agent ↔ reactor; instruction + process-discovery tasks)

### A.1 Reactor & autonomy (their Sec. II, Table I)
- Cross-flow ALD reactor. **8 channels**: 2 high-pressure pyrophoric precursors,
  2 high-pressure coreactants, 3 low-vapor-pressure precursors, 1 processing gas
  (ozone/O₂ or H₂). Control: NI cDAQ-9108 (+9201/9213/9475/9477); MKS 647c gas
  controller; Eurotherm/Omega temperature.
- **Degree of autonomy (Table I):** Valve actuation = **autonomous**; Flows =
  **autonomous**; Exhaust valve = **autonomous**; **Temperature = MANUAL**.
- **⇒ Consequence for us (resolves the exposure issue):** the agent's control
  variables are **which channels + cycle count + pulse/purge times**. **Partial
  pressure is a fixed reactor setting** (autonomous flow), *not* an agent variable,
  and temperature is set manually. So comparing *pulse time at a stated fixed
  pressure* is well-posed; comparing times across unstated pressures (my M5 error)
  is not. Penetration/growth depends on exposure = pₐ·t; with pₐ fixed, **time is the
  knob** — matching their framework.

### A.2 Command API (Table II) — 4 instructions
| # | Name | Description | Returns |
|---|------|-------------|---------|
| 0 | Get status | reactor status | status data |
| 1 | Grow | send a recipe to grow | acknowledgment |
| 2 | Get chemicals | current reactor config | chemicals **by channel** |
| 3 | Get result | result of the growth | thickness + extra params if finished |
- Transport: TCP socket, 6-byte header (3 id + 1 instruction# + 2 big-endian length),
  payload = **JSON bytestring**. Also exposed via **MCP server**. Control loop 100 ms;
  fastest IO loop 10 ms (agent adds no measurable overhead).

### A.3 Recipe JSON schema (their Sec. III.B / IV) — **adopt this exactly**
A query answer is a **JSON list**; each element is one ALD process:
```json
[{"possible": 1, "precursor": 0, "coreactant": 4, "ncycles": 10}]
```
- `precursor`, `coreactant` = **CHANNEL INDICES** (their example is **0-indexed**:
  TMA in channel 0, water in channel 4). `ncycles` = number of AB cycles.
  `possible` = 1/0 (compatible with installed precursors). Supercycles = list of AB
  blocks, repeatable.
- **ALD cycle = "dose A – purge – dose B – purge".** **Dose & purge TIMES are NOT
  produced by the LLM per query** — they are pulled from a **database of processes**
  (their logic component). *(Their optional variant, citing Paper 1, has the LLM also
  emit dose/purge times.)*
- **⇒ For us:** our `recipe.to_argonne_json` already emits `{possible,precursor,
  coreactant,ncycles}` but is **1-indexed** — must switch to **0-indexed** to match.
  The "dose/purge from a database" role = **our KB** (`kb_service` / recipes store).

### A.4 Prompting protocol (their Sec. IV)
- **No system prompt.** The model gets only the user query + reactor configuration
  (channels/chemicals) + (for the +BG variant) a list of available processes.
- JSON output is required "to sidestep reproducibility issues."
- Models (Table III): GPT-3.5, GPT-4o, o1, o3, GPT-5, Claude Sonnet 4, Claude Opus 4,
  Claude Sonnet 4.5, Gemini 2.5 Flash. Accessed via Argo (Argonne, data-secure).

### A.5 Three task studies + **scoring rubric** (their Sec. IV.B)
1. **Instruction (Table V):** *"Please grow N cycles of TMA/water"* etc. — map chemicals
   to channels, emit the cycle JSON.
2. **Process identification (Table VI, 30 challenges):** *"Please grow N cycles of
   [material] Configuration: [channel list]"* — infer which installed precursor+coreactant
   make that material. **No extra info** about the precursors.
3. **Identification + Background (BG):** identical, but the model also receives **a list
   of all ALD processes available in the reactor** (hints).
- **Scoring (0–1, verbatim):** *"If the sequence of cycles is correct, the response
  receives a score of 1. Otherwise… If the response contains the **wrong channel**, the
  score is **0**. If the channels are correct but the **number of cycles is wrong**, the
  response is graded by the **relative error in the number of cycles**. … graded **0 if
  not valid JSON**."* **Average of 5 independent runs.**

### A.6 Results (their Table VII) — the numbers to beat/compare
| Model | Instruction | Identification | Identification + BG |
|---|---|---|---|
| GPT-3.5 | 0.80 (0.09) | 0.39 (0.04) | 0.55 (0.06) |
| GPT-4o | 1.0 (0) | 0.72 (0.04) | 0.91 (0.03) |
| o1 | 1.0 (0) | 0.94 (0.04) | 0.98 (0.02) |
| o3 | 1.0 (0) | 0.96 (0.03) | 0.99 (0.02) |
| GPT-5 | 1.0 (0) | 0.93 (0.01) | 0.96 (0.01) |
| Claude Sonnet 4 | 1.0 (0) | 0.85 (0.01) | 0.94 (0.01) |
| Claude Opus 4 | 1.0 (0) | 0.93 (0.02) | 0.96 (0.01) |
| Claude Sonnet 4.5 | 0.96 (0.05) | 0.78 (0.02) | 0.91 (0.05) |
| Gemini 2.5 Flash | 0.88 (0.07) | 0.84 (0.06) | 0.88 (0.04) |
| **Average** | **0.96 (0.07)** | **0.82 (0.17)** | **0.90 (0.13)** |
- **Hardest challenges (Fig 10):** #17 osmium (O₂ as reducing coreactant), #4 tungsten
  (Si₂H₆/disilane reducer), #12 DMAI (uncommon Al precursor), #28 Ru + inhibitor,
  #30 ternary sulfide. Pattern: **uncommon chemistries hurt pure-LLM recall**; adding
  BG (available-process list) raises the low performers.
- **⇒ Direct opening for PSED:** the "+BG" column *is our thesis* — grounding raises
  scores. Our KB can supply BG **with citations**, and covers exactly the long-tail
  chemistries (Os/W/Ru/sulfide) where pure-LLM recall fails. The honest,
  paper-aligned evaluation = run Table VI through `process_id` with the 0–1 rubric.

### A.7 Table VI challenges (materials; channel lists partly legible — verify vs SI)
Common configuration for many: `TMA, water, DEZ, TDMAHf, Si2H6, WF6, TTIP, MgCp2`.
Materials in order (1→30): alumina, ZnO, hafnia, **tungsten**, TiO₂, MgO, Er₂O₃ (with a
non-halogenated precursor), Al₂O₃, TiO₂ (variant), MoS₂, zirconia, alumina (DMAI/DMAT
config), erbium oxide, hafnia (carbon-free precursor), strontium oxide, In₂O₃ (alkyl
precursor), **osmium metal**, Lithium sulfide, Al-doped ZnO 9:1 supercycle, Al:ZnO 9:1
ratio, Mg-doped ZrO₂ 1:9, TiO₂ nanolaminate 5 bilayers, W/Al₂O₃ nanolaminate 10×(20,2),
hafnia-on-alumina, Al₂O₃-capped MoS₂, **DMAI-inhibitor functionalization**, Hacac
functionalization, **Ru selective (DMADMS inhibitor)**, Ru (EtCp)₂/O₂ passivation +
DMATMS, **9:1 MoS₂:Al ternary/multilayer**. *(Full list + ground-truth answers are in
the paper's supplementary material — transcribe from SI before scoring, don't trust this
paraphrase for grading.)*

---

## PART B — Paper 1 (dose-time optimization on a saturation model)

### B.1 The simulated tool = 0-D saturation model (their Sec. II.D, Eqs 1–11)
- θ = Σᵢ fᵢθᵢ, Σfᵢ = 1 (parallel first-order irreversible Langmuir pathways).
- Precursor dose: dθᵢ/dt = k1ᵢ(1−θᵢ);  coreactant dose: dθᵢ/dt = −k2ᵢθᵢ.
- **Self-limited GPC (Eq 7):** `GPC = GPC0 · Σᵢ fᵢ (1−e^{−k1ᵢ t1})(1−e^{−k2ᵢ t2}) / (1 − e^{−(k1ᵢ+k2ᵢ)})`.
- **CVD (non-self-limited) term (Eqs 5,6,8):** background coreactant rate k_c → asymptotic
  GR₀ = GPC0·k1·k_c/(k1+k_c); GPC then rises ~linearly with t1 (never saturates).
- **⇒ Ours:** `PSED_MPC/saturation_model.py` implements Eq 7 + CVD (verified vs Fig 3).

### B.2 Benchmark processes (their Table I) — **exact parameters**
| Name | k1 (s⁻¹) | k2 (s⁻¹) | GPC0 (Å/cyc) |
|---|---|---|---|
| fast/fast | 5 | 4 | 1.0 |
| slow/slow | 1 | 1.2 | 1.0 |
| slow/fast | 1 | 4 | 1.0 |
| fast/fast (thin) | 5 | 4 | 0.3 |
| soft/fast | k1ᵃ=5, k1ᵇ=1, fᵦ=0.2 | 4 | 1.0 |
- ⇒ matches our `BENCHMARK` dict exactly.

### B.3 Agent design & **prompt (their Fig 2, verbatim)**
> "You are in charge of optimizing an atomic layer deposition process. Atomic layer
> deposition (ALD) is a thin film technique where a given process is characterized by
> four times: the dose time for the precursor, the purge time for the precursor, the
> dose time for the coreactant, and the purge time for the coreactant. ALD is
> self-limited: for long enough dose times the growth per cycle becomes saturated. Your
> job is to determine if the process is already optimized based on the data provided
> and, if it is not saturated, provide some new experimental conditions to try. Also, at
> some point if the dose times are too long and the growth rate keeps increasing, you
> may conclude that the process is not self-limited."
- **Two-step per iteration:** (1) reasoning model → open-ended response (captures chain
  of thought); (2) 2nd LLM call → structured JSON:
  `{"optimized": false, "not_ald": false, "steps": [{"precursor": 0.05, "coreactant": 1.0}, …]}`.
- **Two variants:** *base* (prompt + info so far); *memory* (also all prior model
  outputs). Models used here: **o3** (pure reasoning), **GPT-5** (hybrid).

### B.4 Protocol & metrics
- **Initial guesses:** (0.2 s, 0.2 s) and (2 s, 2 s) — "worst case," no GPC prior.
  Also a no-guess study with hints: {none, pressure, GPC, dose, both}.
- **10 independent runs** per condition.
- **Relative error (Eq 12):** ε = (GPC0 − GPC)/GPC0. Plus: success %, t1, t2, GPC,
  **# samples** (tool queries), **# iterations**, t1+t2.

### B.5 Results (their Table II, III) — targets to compare against
- **With guess (Table II), o3 / GPT-5:** ε mostly **0.01–0.08**; **# samples ≈ 8–26**
  (e.g. fast/fast (2,2): o3 9(3) samples, ε 0.01; slow/slow (0.2,0.2): o3 26(6), ε 0.08).
  Fig 4: **median ε = 0.02, 75th pct = 0.05** (o3 & GPT-5, 100 points).
- **No guess (Table III):** baseline **21(6) samples**, ε 0.04; hints cut to ~**13–16**
  (pressure 13(3), GPC 16(4), both 14(4), dose 14(4)) — **~33% fewer samples**.
- **CVD self-limited detection:** CVD 3 Å/min → **3/10** runs correctly flag "not
  self-limited"; 4.8 → 6/10; 6 → 5/10. **Run-to-run variability is the core weakness.**

### B.6 Classical baselines (their Table IV, Sec. III.C) — **we must include these**
- **Bayesian optimization** (Paulson et al., universal ALD cost function, black-box
  search over dose+purge; purge fixed 5 s): ε = 0.03 / 0.09 / 0.06 / 0.13 / 0.07 for
  fast-fast / slow-slow / slow-fast / fast-fast-thin / soft-fast. Cost-function method
  needs finite-difference gradients → **≥2× samples**.
- **Rule-based** (switches between dose & purge; needs a start): total samples **19–45**;
  ε 0.03–0.09.
- **Finding:** the reasoning agent's **median ε (0.02) beats the classical methods**
  (rule-based median 0.07), and is **more sample-efficient than rule-based**; its
  weakness is variability, not accuracy.
- **⇒ Ours:** we added a grid baseline; to be paper-faithful we should add **Bayesian
  optimization** and a **rule-based** baseline, and report ε + samples + iterations the
  same way.

---

## PART C — Gap analysis: what PSED must adopt to be "properly designed"

| Element | Papers' setup | Our current state | Action |
|---|---|---|---|
| Recipe schema | `{possible,precursor,coreactant,ncycles}`, **0-indexed** channels | `to_argonne_json` emits it but **1-indexed** | switch to 0-indexed; use everywhere a recipe is emitted |
| Dose/purge source | from a **database**, not per-query LLM | KB (recipes/rate bridge) | ✓ aligned — label the KB as "the database" |
| Control variables | channels + ncycles + **pulse/purge times at fixed flow/pressure**; **T manual** | M5 varied "dose_s" with pressure unstated | **state fixed pₐ**; report exposure = pₐ·t; never compare times across pressures |
| Process-ID eval | Table VI, 30 challenges, **0–1 rubric**, **5 runs**, ground-truth answers, +BG variant | `process_id` exists, **never scored on Table VI** | build the 30-challenge harness w/ their rubric + BG (from KB, cited) |
| Optimization eval | Table I ×2 guesses, **10 runs**, ε (Eq 12)+samples+iters, **verbatim prompt**, JSON `{optimized,not_ald,steps}` | `bench_argonne` scores our deterministic/grid; LLM not run w/ their prompt/JSON | adopt their **prompt + JSON + guesses + 10 runs + metrics**; add **Bayesian + rule-based** baselines |
| Scoring reference | **known correct answers** (ID) / **saturated GPC of the tool** (opt) | M5 scored vs an **unvalidated twin** | score ID vs ground truth; score opt vs the tool's GPC0 (well-defined) |
| No system prompt | none; info only in user prompt | our LLM query added framing | drop extra guidance; give only reactor config + query |
| Reps | 5 (ID) / 10 (opt) | 1–2 | run the specified counts; report mean(σ) |

**Scope note.** Neither paper does **geometry-aware conformality dose design** (my M5
task). That is a legitimate *extension* enabled by our twin (Ylilammi/Aguinsky), but it
must be (a) represented in the schema above, (b) posed at fixed pressure, (c) scored
against the twin **with its measured calibration error stated** (M3: 7/39 agreement,
1.89× under-prediction) — never dressed up as "beating an LLM."

**Where PSED genuinely adds value over the papers** (to be *shown*, not asserted):
1. The **+BG effect is our whole thesis** — but grounded (KB) + **cited**, and strongest
   on the long-tail chemistries (Os/W/Ru/sulfide) their pure-LLM agents miss.
2. **Covariate-conditioned imputation** for missing dose/purge (they use a flat DB lookup).
3. A **physics twin** for conformality/geometry (absent in both papers).
4. **Provenance + uncertainty** on every value.
