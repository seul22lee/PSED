# Gold ground truth — `10.1039_d0cp03358h` (Yim et al. 2020)

*Saturation profile catalog for ALD Al2O3 in lateral high-aspect-ratio structures*,
Phys. Chem. Chem. Phys. **22**, 23107–23120. Read from the original PDF before any semantic
code was changed. Table 1 is the design authority and was re-parsed from the PDF's own
reading order, independently of any earlier pilot output.

---

## Table 1 — verified, all 16 specimens

| sample | series | pulse–purge (s) | H (nm) | layout | cycles | magnification |
|---|---|---|---|---|---|---|
| 1 | A | 0.1-4.0-0.1-4.0 | 500 | **v1a** | 500 | 50× |
| 2 | A | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | 50× |
| 3 | A | 0.1-4.0-0.1-4.0 | 500 | **v2a** | 500 | 50× |
| 4 | B | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | **50×** |
| 5 | B | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | **10×** |
| 6 | B | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | **5×** |
| 7 | C | 0.1-4.0-0.1-4.0 | **100** | v1b | 500 | 50× |
| 8 | **C + D** | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | 50× |
| 9 | C | 0.1-4.0-0.1-4.0 | **2000** | v1b | 500 | 50× |
| 10 | D | 0.1-4.0-0.1-4.0 | 500 | v1b | **250** | 50× |
| 11 | D | 0.1-4.0-0.1-4.0 | 500 | v1b | **1000** | 50× |
| 12 | **E + F** | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | 50× |
| 13 | E | **0.2**-4.0-0.1-4.0 | 500 | v1b | 500 | 50× |
| 14 | E | **0.4**-4.0-0.1-4.0 | 500 | **v2a** | 500 | 50× |
| 15 | F | 0.1-**1.0**-0.1-**1.0** | 500 | v1b | 500 | 50× |
| 16 | F | 0.1-**10.0**-0.1-**10.0** | 500 | v1b | 500 | 50× |

Footnote a: "Different pillar layout design for **Series A**; reflectometer magnification for
**Series B**; design channel height for **Series C**; ALD cycles for **Series D**;
**TMA pulse time for Series E**; and **purge time for Series F**."

---

## The 11 unique nominal ExperimentalCases — verified

Normalising on the **deposition-defining** columns only — recipe, channel height, pillar
layout, cycle count — and excluding the reflectometer magnification, which is a measurement
setting:

| # | recipe | H | layout | cycles | realised by samples |
|---|---|---|---|---|---|
| 1 | 0.1-4.0-0.1-4.0 | 500 | v1a | 500 | 1 |
| **2 (BASE)** | 0.1-4.0-0.1-4.0 | 500 | v1b | 500 | **2, 4, 5, 6, 8, 12** |
| 3 | 0.1-4.0-0.1-4.0 | 500 | v2a | 500 | 3 |
| 4 | 0.1-4.0-0.1-4.0 | **100** | v1b | 500 | 7 |
| 5 | 0.1-4.0-0.1-4.0 | **2000** | v1b | 500 | 9 |
| 6 | 0.1-4.0-0.1-4.0 | 500 | v1b | **250** | 10 |
| 7 | 0.1-4.0-0.1-4.0 | 500 | v1b | **1000** | 11 |
| 8 | **0.2**-4.0-0.1-4.0 | 500 | v1b | 500 | 13 |
| 9 | **0.4**-4.0-0.1-4.0 | 500 | **v2a** | 500 | 14 |
| 10 | 0.1-**1.0**-0.1-**1.0** | 500 | v1b | 500 | 15 |
| 11 | 0.1-**10.0**-0.1-**10.0** | 500 | v1b | 500 | 16 |

**11 unique nominal cases from 16 specimens** — the expected anchor, confirmed
independently. The BASE case is realised by **six different specimens**: 2 (Series A), 4, 5,
6 (Series B), 8 (C and D) and 12 (E and F). Those six are **not** six cases.

Case 9 (sample 14) also carries `layout = v2a`, which differs from the rest of Series E.
Series E's author-declared variable is the **TMA pulse time**; the layout is **co-varying
context** and must be preserved as such, not promoted and not erased.

---

## Composite recipe decomposition

`0.1-4.0-0.1-4.0` must not stay an opaque string. It decomposes as

```
TMA_pulse = 0.1 s   TMA_purge = 4.0 s   H2O_pulse = 0.1 s   H2O_purge = 4.0 s
```

which is what makes the Series E and Series F value joins possible:
Series E varies field 1; Series F varies fields 2 and 4 together.

---

## Figure-by-figure

### Fig 5 — sample 11, several techniques
"SEM image of **sample 11** surface (top view) with an overlayer of corresponding Al-Kα
X-ray count map in red. **1000 growth cycles**…"
→ **one Sample, one ExperimentalCase (case 7), several Measurements** (SEM, Al-Kα map,
EDS line scan). Not one case per technique.

### Fig 6
The main text does not bind every profile to a unique specimen without the stated ESI.
→ preserve result and Measurement; **case link may remain UNRESOLVED**. Do not guess.

### Fig 7 — Series B, measurement setting only
"As-measured saturation profiles for ALD Al2O3 as a function of reflectometer spot sizes.
**Samples 4, 5 and 6** (Table 1 Series B)."
Methods: "a **50×** objective lens with an estimated spot size of **5–6 µm**"; "**10×** and
**5×** objective lenses with an estimated spot size of **25** and **50 µm**, respectively".

Value join, from the magnification column:
```
X50 → sample 4      X10 → sample 5      X5 → sample 6
```
→ **1 nominal ExperimentalCase** (the BASE case), 3 Samples, 3 measurement settings.
Magnification and spot size are MEASUREMENT_SETTINGs.

### Fig 8a — repeatability
"Repeatability of saturation profile measurement (a) for ALD Al2O3 film grown on a LHAR
channel (**sample 8** in Table 1)". Repeated measurements of one specimen →
**no new cases**.

### Fig 8b — reproducibility across runs
"…reproducibility of **ALD runs** (b) for Al2O3 films made in 500 cycles on **various LHAR
channels**, having the same design channel height of 500 nm and pillar design of **v1b**."
Legends name samples **2, 4, 8, 12** — all four are BASE-case specimens.
→ **ONE nominal ExperimentalCase**, four physical realisations, explicit **run-distinctness
evidence**. The paper names no individual runs, so **no run IDs may be invented**.

### Fig 9 — Series C and D
Top row (a–c): "**Sample 7, 8, and 9** (Table 1 Series C)" — H = 100 / 500 / 2000 nm.
Bottom row (d–f): "**Sample 8, 10 and 11** (Table 1 Series D)" — N = 500 / 250 / 1000.
Each row is shown as-measured, scaled and Type-1 normalized.

**Sample 8 is shared.** Therefore:
```
Series C cases: 4 (H=100), 2 (BASE, H=500), 5 (H=2000)
Series D cases: 6 (N=250), 2 (BASE, N=500), 7 (N=1000)
union = {2, 4, 5, 6, 7}  ->  5 unique nominal cases
```
→ **18 displayed representations → 6 underlying profile appearances → 5 unique
ExperimentalCases.** The current pilot's "6 cases" is wrong by exactly the shared BASE case.

### Fig 10 — simulation
MATLAB re-implementation of the Ylilammi model. `SimulationRun`, never an ExperimentalCase.

### Fig 11a — Series E
"different TMA pulse times (**sample 12, 13, and 14** in Table 1 Series E)"
```
TMA 0.1 s → sample 12 → BASE case (2)
TMA 0.2 s → sample 13 → case 8
TMA 0.4 s → sample 14 → case 9
```
Each curve binds to **its own** branch and specimen — not all three to all three.

### Fig 11b — Series F
"purge times … (**sample 12, 15, and 16** in Table 1 Series F)"
```
purge 1 s  → sample 15 → case 10
purge 4 s  → sample 12 → BASE case (2)
purge 10 s → sample 16 → case 11
```

**Series E and F share the base case through sample 12.** Six displayed branches across
Fig 11a and 11b, but the union is `{2, 8, 9, 10, 11}` →
**5 unique ExperimentalCases, not 6.**

---

## Required structural facts

```
DepositionRun (Series A, explicit) ──produces──> Samples 1, 2, 3
                                                   │  realise
                                                   ▼
                                    3 DIFFERENT ExperimentalCases (v1a / v1b / v2a)
```
One run producing three cases — the run does **not** collapse them.

```
ExperimentalCase 2 (BASE) <──realised by── Samples 2, 4, 5, 6, 8, 12
```
Six specimens realising one case — the specimens do **not** split it.

StudySeries membership is **many-to-many**: sample 8 ∈ {C, D}, sample 12 ∈ {E, F}.

## Where the current pilot is wrong (before repair)

1. **18 cases instead of 11** — Samples and Series branches are treated too much like case
   identity.
2. Fig 9 gives 6 cases where the shared BASE specimen makes it **5**.
3. Fig 11 gives 6 cases where the shared BASE specimen makes it **5**.
4. Fig 11a/11b curves bind to *all* of their series' specimens rather than to the one whose
   value they carry.
5. The composite recipe string is never decomposed, so Series E/F cannot value-join.
6. Series A's single run and its three distinct layouts are not represented as one run
   producing three cases.
