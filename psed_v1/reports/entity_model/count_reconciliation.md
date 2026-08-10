# Entity-model rebuild — count reconciliation

> **Updated after the experiment-extraction repair.** The "after" column now
> reflects the repaired pipeline (series-level source identity, evidence-based
> sweep settings, scoped chemistry). See
> [experiment_extraction_regression/REPAIR_REPORT.md](../experiment_extraction_regression/REPAIR_REPORT.md)
> and, for the authoritative per-curve surface, `resolved/results.json`.

Every count below is reported separately. There is deliberately **no single
"experiment count"**, and no count is derived from digitised point density.

## Before → after

| | before | after |
|---|--:|--:|
| record nodes in `experiments.json` | **2457** | **636** |
| unique source entities (drawn curves) | not represented | **663** |
| **authoritative result records** (`results.json`) | not represented | **663** |
| digitised observations | 12085 | 12085 |
| raw figure series in `figure_data.json` | 659 | 659 |
| orphaned source series | — | **0** |

**No observation was lost**: all 12085 digitised points survive as
`Observation` records on their entity, and all 659 raw series have exactly one
result record. The drop from 2457 is the removal of nodes that were never
experiments; the subsequent rise from 204 to 636 is the restoration of genuine
per-setting cases for measured discrete sweeps, which the earlier
sample-list-only rule had suppressed.

## Where the 2253 removed nodes went

| reason | entities | former nodes |
|---|--:|--:|
| curves that are ONE run/specimen, previously expanded per point | 310 | 1 case each (35 traces, 70 profiles, 205 multi-output) |
| discrete sweeps with evidence-supported settings | 68 | **326 per-setting cases** |
| discrete sweeps whose settings remain unresolved | 83 | series + observations, 0 minted cases |
| simulations | 87 | no longer Experiments |
| model sweeps | 26 | no longer Experiments |
| re-plotted literature data | 10 | no longer this paper's Experiments |
| fits / calculated representations | 7 | linked to their measurement, no run minted |
| unresolved source entities | 72 | preserved, unsplit, unpromoted |

## Differentiated counts (31 papers)

| quantity | count |
|---|--:|
| plot series (drawn curves) | 663 |
| **physical experimental cases (supported)** | **204** |
| experimental cases, evidence-supported lower bound | 640 |
| deposition runs | 70 |
| unique samples | 204 |
| measurements | 422 |
| experimental profiles | 71 |
| continuous traces | 38 |
| multi-output measurements | 90 |
| experimental series | 218 |
| … of which case count unresolved | 218 |
| observations awaiting case resolution | 3123 |
| imported literature profiles | 10 |
| simulation runs | 88 |
| model sweeps | 26 |
| model prediction points | 1706 |
| fits | 5 |
| derived representations (scaled/normalized/inset) | 48 |
| **unresolved source entities** | **112** |
| total observations | 12085 |

## Why no exact experiment count is claimed

218 experimental series carry
3123 observations whose settings the papers do not
enumerate, and 112 source entities remain unresolved. The
supported figure is therefore a **lower bound of 204 confirmed cases**,
rising to **640** if every unresolved sweep is credited with the
minimum two settings a sweep must have. The true value lies between them and cannot
be fixed without per-setting evidence.

## Classification confidence

| | entities |
|---|--:|
| corroborated | 464 |
| unresolved | 112 |
| single_definitional_signal | 87 |

## Per paper

| paper | entities | cases | lower bound | series | sim | sweep | lit | unresolved | observations |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `10.1002_admi.202000318` | 17 | 0 | 28 | 14 | 1 | 2 | 0 | 0 | 269 |
| `10.1002_celc.201600139` | 17 | 15 | 19 | 2 | 0 | 0 | 0 | 0 | 330 |
| `10.1002_cnma.201700148` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `10.1002_pssa.201532305` | 28 | 23 | 31 | 4 | 0 | 0 | 0 | 1 | 708 |
| `10.1007_s11671-010-9676-0` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `10.1007_s12274-010-0066-9` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 36 |
| `10.1016_j.jcrysgro.2017.04.019` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 30 |
| `10.1016_j.matt.2019.12.026` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `10.1016_j.mee.2018.01.027` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 41 |
| `10.1016_j.mee.2018.01.033` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `10.1016_j.sse.2022.108584` | 26 | 0 | 0 | 0 | 5 | 11 | 10 | 0 | 555 |
| `10.1016_j.tsf.2012.11.127` | 32 | 10 | 54 | 22 | 0 | 0 | 0 | 0 | 873 |
| `10.1021_acs.chemmater.2c01154` | 56 | 3 | 109 | 53 | 0 | 0 | 0 | 0 | 632 |
| `10.1021_acs.chemmater.2c02292` | 44 | 15 | 45 | 15 | 0 | 0 | 0 | 12 | 696 |
| `10.1021_acs.jpcc.9b08176` | 15 | 0 | 0 | 0 | 0 | 9 | 0 | 6 | 136 |
| `10.1039_c5tc03561a` | 14 | 0 | 28 | 14 | 0 | 0 | 0 | 0 | 161 |
| `10.1039_c6dt03571j` | 26 | 6 | 14 | 4 | 0 | 0 | 0 | 16 | 515 |
| `10.1039_c7ra07722j` | 34 | 18 | 46 | 14 | 0 | 0 | 0 | 0 | 684 |
| `10.1039_d0cp03358h` | 74 | 42 | 42 | 0 | 32 | 0 | 0 | 0 | 1487 |
| `10.1039_d3dt01824e` | 30 | 9 | 21 | 6 | 0 | 0 | 0 | 15 | 638 |
| `10.1039_d3ra05217f` | 36 | 15 | 35 | 10 | 0 | 0 | 0 | 11 | 570 |
| `10.1063_1.4867469` | 6 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 212 |
| `10.1063_1.5028178` | 19 | 4 | 4 | 0 | 12 | 3 | 0 | 0 | 496 |
| `10.1116_1.4892385` | 6 | 1 | 1 | 0 | 5 | 0 | 0 | 0 | 176 |
| `10.1116_1.4938104` | 12 | 0 | 8 | 4 | 0 | 0 | 0 | 8 | 151 |
| `10.1116_6.0002154` | 26 | 2 | 46 | 22 | 0 | 0 | 0 | 1 | 670 |
| `10.1116_6.0002436` | 35 | 20 | 40 | 10 | 0 | 0 | 0 | 5 | 532 |
| `10.1116_6.0002804` | 34 | 9 | 55 | 23 | 0 | 0 | 0 | 2 | 412 |
| `10.1186_s11671-015-0872-9` | 1 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 51 |
| `10.3762_bjnano.14.89` | 26 | 6 | 6 | 0 | 0 | 0 | 0 | 20 | 613 |
| `10.3762_bjnano.5.25` | 39 | 5 | 5 | 0 | 33 | 1 | 0 | 0 | 411 |
