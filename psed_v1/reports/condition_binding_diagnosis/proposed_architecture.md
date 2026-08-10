# Proposed architecture

Preserve extraction. Add a deterministic recovery + binding layer between the
immutable evidence and the resolved records.

```
IMMUTABLE EVIDENCE                    (never rewritten)
  figure_data.json · records.json · document.md · structure.json
  captions · series labels · tables · figure images
        │
        │  (1) ConditionMentionRecovery        deterministic, no LLM
        │      caption parser · legend parser · figure-linked-text parser · table joiner
        ▼
  ConditionAssertion[]                 NEW, versioned, additive
  extracted/{doi}/assertions/condition_assertions_v1.json
        │
        │  (2) ScopedConditionBinder           deterministic
        │      narrowest applicable scope wins; conflicts stay ambiguous
        ▼
  resolved cases:  ExperimentalCase | ModelRun | Observation | ImportedLiteratureProfile
        │
        ▼
  recipes · KB · KG · canonical layer
```

## ConditionAssertion (evaluated and extended)

The schema proposed in the brief is close; three additions are needed, all forced by
verified cases:

```json
{
  "assertion_id": "sse2022::fig6::ylilammi::pA",
  "quantity": "precursor_partial_pressure",
  "value": 325, "unit": "mTorr",
  "raw_text": "we estimate 𝑝 𝐴 = 325 mTorr", "symbol": "p_A",

  "value_status": "estimated",              // reported | estimated | assumed | fitted | derived
  "evidence_kind": "model_input",           // experimental_condition | model_input |
                                            // fitted_parameter | literature_condition
  "source_kind": "in_text",                 // caption | legend | in_text | table | methods
  "attribution": "current_paper_model",     // + current_paper_experiment | cited_work
  "reference_work": "Ylilammi 2018",

  "paper_id": "10.1016_j.sse.2022.108584",
  "figure_number": "6", "fig_docling_index": "8", "panel": "a",
  "series_selector": "Ylilammi 2018*",
  "of_reactant": "A", "species": "TMA",

  "scope": "reference_series",
  "evidence_locator": {"file": "document.md", "char_span": [12043, 12089]},
  "confidence": 0.9,
  "supersedes_scope": ["paper"]             // NEW: this narrower value beats a broadcast
}
```

Additions beyond the brief's draft, each justified:

1. **`attribution`** — separate from `evidence_kind`. `Arts 2019, 310 °C` in SSE
   Fig. 4 is a *literature experimental condition* re-plotted inside a modelling
   paper; `evidence_kind` alone cannot say whose experiment it was. Without this,
   category **R** cannot be fixed.
2. **`supersedes_scope`** — makes the fix for **I**/**J** declarative instead of a
   dedup heuristic: a caption-scope pressure explicitly outranks a paper-scope one.
3. **`series_selector` as a glob over the verbatim label**, not an index. Labels are
   stable across re-extraction; series indices are not.

## Per-series measurand (fixes N)

`figure_data.panels[].series[]` needs an optional per-series
`{quantity, unit}` override. This is additive: absent ⇒ inherit the panel value, so
every existing file stays valid. `10.1016_j.sse.2022.108584` Fig. 5a/5b are the
proof cases.

## Record kinds (fixes P and S)

`resolved/experiments.json` currently holds one class. The audit shows at least four:

| kind | test | example |
|---|---|---|
| `ExperimentalCase` | separately prepared sample | `10.1116_6.0002804` Fig.1, one deposition per pulse time |
| `Observation` | one sample measured continuously | `10.1002_pssa.201532305` Fig.4, in-situ SE trace |
| `ModelRun` | simulation output | `10.1039_d0cp03358h` Fig.10 |
| `ImportedLiteratureProfile` | re-plotted from a cited work | `10.1016_j.sse.2022.108584` Fig.4 `Arts 2019` |

Only `ExperimentalCase` may be split per point, and only when the assertions show
that a *non-coordinate* condition actually differs between points.
