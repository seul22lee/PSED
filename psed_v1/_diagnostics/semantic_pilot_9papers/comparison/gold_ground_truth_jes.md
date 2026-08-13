# Gold ground truth — `10.1149_2.067203jes`

*Plasma-assisted ALD of SiO2*, J. Electrochem. Soc. **159** (3) H277–H285 (2012), 10 pages.
Read from the original PDF **before** any semantic code was changed. Marker counts come
from the digitised source slices; every other fact is quoted from the PDF text.

**Process scope (Methods).** "Plasma-assisted atomic layer deposition (ALD) was used to
deposit SiO2 films in the temperature range of **Tdep = 50–400 °C** on Si(100)."
"The substrate temperature during deposition, Tdep, was varied between 50 and 400 °C."
Precursor SAM.24 = H2Si[N(C2H5)2]2, introduced by "ultrashort doses **(10–120 ms)**".

---

## Figure-by-figure

### Fig 1 — precursor vapour pressure
Vapour pressure of SAM.24 vs temperature, compared with TMA. A property of a **chemical**,
not of a film.
**Deposition cases: 0.** Preserve as Measurement + ResultSeries. No SiO2/Al2O3 deposited
material may be asserted here; the caption names both only to say what each precursor is
*used for*.

### Fig 2 — thickness vs ALD cycle number
Caption: "(a) Substrate temperatures of **50 °C, 200 °C and 250 °C**. The film thickness was
measured by **in situ** spectroscopic ellipsometry (SE). (b) SiO2 film thickness extracted
from the TEM image of Fig. 3, compared with values determined by in situ SE **on the same
sample**. The substrate temperature Tdep was 200 °C."
Body: "The ALD process was monitored by in situ SE **by taking data points after a certain
number of cycles**."

- **x axis = PROCESS_PROGRESSION.** Cycle number tracks the growth of one film, not
  independently prepared specimens. Each cycle-count point is **not** a case.
- **Case-defining variable = substrate temperature → 3 design branches** (50, 200, 250 °C).
- Fig 2b carries an **explicit same-sample link** to Fig 3 ("on the same sample").
- Note: "in situ" describes the *measurement mode*. It is **not** evidence that the four
  recipe parameters of Fig 4 were varied inside one physical deposition.

### Fig 3 — TEM of an Al2O3/SiO2 nanolaminate
"stack with alternating layers of ALD Al2O3 and ALD SiO2 deposited using **10–40 cycles
each**. The substrate temperature was 200 °C. The extracted layer thicknesses are shown in
Fig. 2b."
- `10–40 cycles` is an **interval**, not −40.
- Same specimen as Fig 2b → one SampleStack, two Measurements (SE and TEM).

### Fig 4 — saturation curves — **REQUIRED GOLD ANCHOR**
Caption: "(a)–(d) Saturation curves for the **growth-per-cycle, GPC, and refractive index,
n**, of the SiO2 films … as a function of the **4 process parameters** in the ALD recipe.
(e)–(h) Saturation curves for the GPC of **Al2O3** films. The substrate temperature was
**250 °C** for both."
Body: "In the corresponding experiments **one process parameter in the ALD recipe was varied
whereas the duration of the other steps was taken sufficiently long** to guarantee saturated
ALD conditions for the non-varied process parameters."

Axis labels read from the PDF: SiO2 — dose time (ms), purge time (s), plasma time (s),
plasma purge (s); Al2O3 — the same four.

**Source-explicit design branches, from the digitised markers:**

| panel | material | varied parameter | values | branches |
|---|---|---|---|---|
| 4a | SiO2 | dose time (ms) | 10, 20, 35, 50, 90, 120 | **6** |
| 4b | SiO2 | precursor purge (s) | 0.5, 1, 2, 3, 4, 5 | **6** |
| 4c | SiO2 | plasma time (s) | 0.2, 0.5, 1, 2, 3, 5 | **6** |
| 4d | SiO2 | plasma purge (s) | 0.5, 1, 2, 3 | **4** |
| 4e | Al2O3 | dose time (ms) | 10, 20, 30, 50 | **4** |
| 4f | Al2O3 | purge (s) | 1.5, 2.5, 3.5, 5 | **4** |
| 4g | Al2O3 | plasma time (s) | 0.5, 1, 2, 3, 4, 5 | **6** |
| 4h | Al2O3 | plasma purge (s) | 0.1, 0.5, 1, 2 | **4** |
| | | | **total** | **40** |

**This confirms the expected anchor of 40 exactly** (SiO2 6+6+6+4 = 22, Al2O3 4+4+6+4 = 18).

**GPC and refractive index are two OUTPUTS of the same branch**, not two cases:

```
DesignBranch: SiO2 dose = 50 ms, Tdep = 250 °C
    ├── Measurement: GPC
    └── Measurement: refractive index
```

A whole panel must not collapse to one case, and a branch must not split per output.

### Fig 5 — temperature series — **REQUIRED GOLD ANCHOR**
"Influence of the **substrate temperature** during deposition on (a) the **refractive index,
n**, and (b) the **growth-per-cycle, GPC**, of SiO2."

Digitised x values, both panels: **50, 100, 150, 200, 250, 300, 350, 400 °C → 8 branches**,
matching the Methods range exactly.

```
T = 50 °C branch  ├── refractive index (5a)   └── GPC (5b)
…  (8 branches, each with two outputs)
```

**Known ontology defect confirmed in the extraction:** Fig 5a's measurand is resolved as
`cycle_number`. It is the **refractive index**. A generic regression test is required.

Table I adds RBS/ERD data at 100 / 200 / … °C — outputs of the same temperature branches.

### Fig 6 — FTIR
"FTIR spectra of ALD SiO2 prepared at 200 °C (48 nm film thickness) **and thermal SiO2 grown
by wet oxidation at ~900 °C** (295 nm)."
The thermal oxide is a **reference**, not a current-paper ALD deposition. Wavenumber is a
MEASUREMENT_COORDINATE. Deposition cases from this figure: the ALD SiO2 spectrum belongs to
the 200 °C branch; the thermal oxide mints none.

### Fig 7 — TEM of a real deposited stack
"High-resolution TEM image of an **ALD SiO2 film of 7.0 ± 0.3 nm thickness deposited on a
H-terminated Si(100) wafer. The SiO2 was covered by an Al2O3 film deposited by
plasma-assisted ALD.**"
```
ExperimentalCase → SampleStack (SiO2 DEPOSITED, Al2O3 CAP, Si SUBSTRATE) → TEM Measurement
```
The PDF gives **no deposition temperature and no cycle count** for this specimen. Those stay
**unknown** — they must not be inherited from another figure.

### Fig 8 — HAR trench — **distinct deposition case**
"High-resolution SEM images of a **high-aspect ratio trench** in Si coated by **830 cycles**
of ALD SiO2. The SiO2 was deposited **on top of thermal SiO2/ALD Al2O3 layers** for optical
contrast. The depth and average width of the trench were **18.5** and **0.6 µm**, resulting
in an **aspect ratio of ~30**."
Body: bottom thickness ~50 nm vs ~100 nm on the surface (that figure refers to the prior
Al2O3 deposition, which "exhibited a lower conformality").

A genuine HAR deposition case with no digitised x-y data. It is **informed by** the Fig 4
saturation design but is **not the same case** — the relation is recipe selection, not
identity.

### Figs 9–10 — process diagnostics
QMS m/z traces and OES wavelength spectra of the plasma step. Both axes are
MEASUREMENT_COORDINATEs. Individual traces and peaks mint **no deposition cases**; the OES
reference plasma is a reference observation.

### Fig 11 — surface passivation
"…for a **single layer ~45 nm SiO2** film (annealed 400 °C, N2/H2, 20 min) and for a
**~12 nm SiO2 / ~30 nm Al2O3 stack** (annealed 400 °C, N2, 10 min). The **inset** shows the
long-term stability corresponding to the single layer SiO2 film after annealing."
- **2 deposited-structure branches.**
- The inset is a **SampleState / post-treatment** observation of an existing sample — it
  mints no new deposition case.
- Injection level is a MEASUREMENT_COORDINATE.

### Fig 12 — C–V
"(a) single layer ALD SiO2 films after annealing in forming gas … and (b) SiO2/Al2O3 stacks
… **The SiO2 thickness was varied and the Al2O3 film thickness was 30 nm.** The transients
were measured using **frequencies of 1, 10 and 100 kHz**."
Body names stack interlayers of **1 and 2.5 nm** and **12.5 nm**, plus "a single layer ALD
Al2O3 reference sample deposited directly on H-terminated Si".
- **Deposited-structure branches: 7** (single-layer SiO2 at 5 / 12.5 / 30 nm; stacks with
  SiO2 = 1 / 2.5 / 12.5 / 30 nm over 30 nm Al2O3) — the expected anchor. The PDF names 1,
  2.5 and 12.5 nm explicitly in the interlayer discussion; the remaining values are read
  from the figure legends and are marked as such in the fixture.
- Voltage and frequency are MEASUREMENT_COORDINATE / MEASUREMENT_SETTING.
- The **single-layer Al2O3 reference sample** is a reference observation.

---

## Summary of the required counts

| | |
|---|---|
| **Source-explicit design branches** | Fig 4 = **40**, Fig 5 = **8**, Fig 2a = **3**, Fig 11 = **2**, Fig 12 = **7** |
| **Unique nominal ExperimentalCases** | not asserted as a single whole-paper number — the Fig 4 and Fig 5 designs overlap only at Tdep = 250 °C for Fig 4 vs the 250 °C Fig 5 branch, and the source never states that the Fig 4 saturation specimens and the Fig 5 temperature specimens are the same films |
| **Reference / non-current-paper** | Fig 6 thermal oxide, Fig 10 reference plasma, Fig 12 Al2O3 reference sample |
| **Zero-case figures** | Fig 1, Fig 9, Fig 10 |

## Where the current pilot is wrong (before repair)

1. **Fig 4 collapses 40 branches into 8 panel-level cases** — the dominant under-split.
2. **Fig 5 collapses 8 temperature branches into 2 panel-level cases.**
3. Fig 5a's refractive index is typed `cycle_number`.
4. Fig 2a's cycle-number progression risks being read as a case-defining sweep.
5. GPC and refractive index at the same branch are two cases rather than two outputs.
6. Fig 11's aging inset and Fig 12's reference sample are not distinguished.
