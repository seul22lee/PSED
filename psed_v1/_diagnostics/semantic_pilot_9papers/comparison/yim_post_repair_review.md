# Yim 2020 — post-repair review

`10.1039_d0cp03358h` · *Phys. Chem. Chem. Phys.* **22**, 23107–23120

Reconciled against `comparison/gold_ground_truth_yim.md`, which was written from the
PDF before any of this code existed.

## Verdict

| gold anchor | expected | produced | |
|---|---|---|---|
| Samples from Table 1 | 16 | 16 | ✅ |
| Unique nominal ExperimentalCases | 11 | 11 | ✅ |
| BASE realised by | 2,4,5,6,8,12 | 2,4,5,6,8,12 | ✅ |
| Fig 9 unique cases (sample 8 shared) | 5 | 5 | ✅ |
| Fig 11 unique cases (sample 12 shared) | 5 | 5 | ✅ |
| Table-defined cases with no plotted curve | 2 | 2 | ✅ |
| Fig 6 unsupported deposition cases | 0 | 0 | ✅ |
| sample 8 in Series C and D | C,D | C,D | ✅ |
| sample 12 in Series E and F | E,F | E,F | ✅ |

**11 of 11 gold anchors reproduced.**

## The 11 nominal cases

| case | samples | series | figures | fingerprint (case-defining only) |
|---|---|---|---|---|
| `CASE-10.103-001` | 11 | D | 5, 9 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=1000; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-002` | 2, 4, 5, 6, 8, 12 | A, B, C, D, E, F | 7, 8, 9, 11 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-003` | 7 | C | 9 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; deposition_temperature=300; feature_height=100 |
| `CASE-10.103-004` | 9 | C | 9 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; deposition_temperature=300; feature_height=2000 |
| `CASE-10.103-005` | 10 | D | 9 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=250; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-006` | 13 | E | 11 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-007` | 14 | E | 11 | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-008` | 15 | F | 11 | coreactant_pulse_time=0.1; coreactant_purge_time=1.0; cycle_number=500; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-009` | 16 | F | 11 | coreactant_pulse_time=0.1; coreactant_purge_time=10.0; cycle_number=500; deposition_temperature=300; feature_height=500 |
| `CASE-10.103-010` | *table-only* | – | – | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; feature_height=500; pillar_layout=v1a |
| `CASE-10.103-011` | *table-only* | – | – | coreactant_pulse_time=0.1; coreactant_purge_time=4.0; cycle_number=500; feature_height=500; pillar_layout=v2a |

## Fig 9 and Fig 11 — one curve, one specimen

**Fig 9**

| curve | sample | case |
|---|---|---|
| `Fig9a/exp01` | 7 | `CASE-10.103-003` |
| `Fig9b/exp01` | 7 | `` |
| `Fig9c/exp01` | 7 | `` |
| `Fig9a/exp02` | 8 | `CASE-10.103-002` |
| `Fig9b/exp02` | 8 | `` |
| `Fig9c/exp02` | 8 | `` |
| `Fig9d/exp02` | 8 | `CASE-10.103-002` |
| `Fig9e/exp02` | 8 | `` |
| `Fig9f/exp02` | 8 | `` |
| `Fig9a/exp03` | 9 | `CASE-10.103-004` |
| `Fig9b/exp03` | 9 | `` |
| `Fig9c/exp03` | 9 | `` |
| `Fig9d/exp01` | 10 | `CASE-10.103-005` |
| `Fig9e/exp01` | 10 | `` |
| `Fig9f/exp01` | 10 | `` |
| `Fig9d/exp03` | 11 | `CASE-10.103-001` |
| `Fig9e/exp03` | 11 | `` |
| `Fig9f/exp03` | 11 | `` |

**Fig 11**

| curve | sample | case |
|---|---|---|
| `Fig11a/exp01` | 12 | `CASE-10.103-002` |
| `Fig11b/exp02` | 12 | `CASE-10.103-002` |
| `Fig11a/exp02` | 13 | `CASE-10.103-006` |
| `Fig11a/exp03` | 14 | `CASE-10.103-007` |
| `Fig11b/exp01` | 15 | `CASE-10.103-008` |
| `Fig11b/exp03` | 16 | `CASE-10.103-009` |

## Sample 11 — condition-specificity precedence

Table 1 row 11 states **1000 cycles**. A methods default of 500 cycles was inherited
first and was previously compared as an equal, which read as a contradiction and blocked
the merge, leaving the Fig 5 result stranded in a case of its own.

Resolved value: `cycle_number = 1000 cycle` (sample_table_direct)

The superseded default is retained on the record rather than discarded.

## Fig 6 — characterisation without deposition identity

Its caption states only the paper's default process (500 cycles, 500 nm channel,
300 °C) and refers to ESI that is not present. It now mints no case: the AFM
measurement is preserved with its caption evidence and its case link is UNRESOLVED.

## DesignFactor mapping (unchanged by this repair)

| series | author's words | components | role | members |
|---|---|---|---|---|
| Series A | | 12 13 14 | 15 12 16 | | Series a A | B | C D | E | | F | a Different pillar layout design for Series A; reflectometer magnification | `pillar_layout` | CASE_DEFINING | 1, 2, 3 |
| Series B | | E | | F | a Different pillar layout design for Series A; reflectometer magnification for Series B; design channel height for Se | `reflectometer_magnification` | MEASUREMENT_SETTING | 4, 5, 6 |
| Series C | ign for Series A; reflectometer magnification for Series B; design channel height for Series C; ALD cycles for Series D; TMA | `feature_height` | CASE_DEFINING | 7, 8, 9 |
| Series D | ification for Series B; design channel height for Series C; ALD cycles for Series D; TMA pulse time for Series E; | `cycle_number` | CASE_DEFINING | 10, 11, 8 |
| Series E | esign channel height for Series C; ALD cycles for Series D; TMA pulse time for Series E; and purge time for Series F. | `pulse_time` | CASE_DEFINING | 12, 13, 14 |
| Series F | es C; ALD cycles for Series D; TMA pulse time for Series E; and purge time for Series F. b Original traceable sample | `purge_time` | CASE_DEFINING | 12, 15, 16 |
