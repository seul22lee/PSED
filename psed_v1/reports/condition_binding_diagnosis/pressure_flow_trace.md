# Pressure flow trace

```
document.md / caption / table
   │  03_corpus/scripts/10_pressure.py            [LLM, one call/paper]
   │    PRESSURE_SCHEMA → typed observations
   │    FACT_CONTEXTS = ("process_condition","apparatus_setting")     L38
   │       ⇒ context "model_definition" and "measured_response" can NEVER
   │         become a controlled condition, by design
   ▼
pressure.json
   │  10_pressure.py :: pressure_facts(sd, reactants)
   ▼
06_to_kb.py :: press_ctrl → controlled
   │  _dedup_pressures(base_ctrl + panel_ctrl + series_ctrl + press_ctrl)
   ▼
resolved/experiments.json → recipe.py → kb_service / kb_bridge / build_kg
```

## Corpus-wide measurement (all 31 papers)

| | papers |
|---|--:|
| `pressure.json` empty | **18 / 31** |
| pressure present in `document.md` **but** `pressure.json` empty | **13 / 31** |
| `pressure.json` non-empty but **no usable pressure on any experiment** | **3 / 31** |
| **papers ending with zero usable pressure on any record** | **16 / 31 (52 %)** |

Random-sample estimate of records that lose an available pressure:
**26.7 % (32/120), 95 % CI [19.6 %, 35.2 %]**.

## Root cause 1 — the extractor is a pilot and did not run everywhere

`03_corpus/scripts/10_pressure.py` docstring, lines 12-18:

> "This is a PILOT tool. It does **NOT** run the whole corpus … only papers that
> have a `pressure.json` are affected, so wiring it in leaves the rest of the
> corpus untouched."

13 papers have a pressure in their text and an **empty** `pressure.json`, including
both case-study papers. Category **M** (relevant extractor not executed).

## Root cause 2 — model-input pressures are filtered out by design

`10_pressure.py:38` `FACT_CONTEXTS = ("process_condition", "apparatus_setting")`.
SSE Fig. 6's `pA = 325 mTorr` is an **estimated model input** → context
`model_definition` → excluded even if extracted. D0CP Fig. 10's `pA0 = 65 Pa` and
`pB = 300 Pa` are simulation-run inputs → same exclusion. The schema has no
representation for "assumed model input", so these cannot be stored at all.
Category **N**.

## Root cause 3 — dedup discards the NARROWER-scope pressure

`03_corpus/scripts/06_to_kb.py::_dedup_pressures` keeps the value whose
`source == "pressure_extraction"` (paper scope) and drops any other pressure whose
value matches within 1 %:

```python
if (c.get("source") != "pressure_extraction" and q in _PRESSURE_Q
        and isinstance(v, (int, float)) and _matches_ext(v)):
    continue                      # ← the caption/panel-scope value is dropped
```

Verified on `10.1002_pssa.201532305` Fig. 4: the caption states
*"Standard parameter values: 0.01 mbar of pressure, 325 °C …"*.

* `records.json` → `controlled = {"pressure": "0.01 mbar", "temperature": "325 °C"}` ✓
* `_num_cond("pressure","0.01 mbar")` → `generic_pressure = 1.0 Pa`, source `caption` ✓
* `_dedup_pressures` drops it because paper-scope extraction also has `1.0 Pa`
* the surviving paper-scope `generic_pressure` has **3 distinct values** (1, 100, 1000 Pa)
  → flagged `context_status = ambiguous`
* **net result: the record has no usable pressure, although the caption states it unambiguously.**

Temperature from the same caption survives (no dedup rule applies to it), which is
why `temperature 325 °C scope=figure` is present and pressure is not.
Category **I**, compounded by **J**.

## Per-assertion results for the two case studies

| paper | assertion | document.md | caption | figure_data | pressure.json | resolved | recipe/KB/KG |
|---|---|---|---|---|---|---|---|
| D0CP | working pressure ≈ 3 hPa | ✅ | – | – | ❌ empty | ❌ | ❌ |
| D0CP | Fig.10 `pA0 = 65 Pa` (TMA) | ✅ | ✅ | ❌ not in `conditions{}` | ❌ empty | ❌ | ❌ |
| D0CP | Fig.10 `pB = 300 Pa` (N2) | ✅ | ✅ | ❌ | ❌ empty | ❌ | ❌ |
| SSE | Fig.6 `pA = 325 mTorr` (est.) | ✅ | – | – | ❌ empty | ❌ | ❌ |
| SSE | Fig.6 `pA = 160 mTorr` (est.) | ✅ | – | – | ❌ empty | ❌ | ❌ |
| SSE | Fig.4 `750 mTorr·s` H2O dose | ✅ | – | – | n/a (**exposure**, not pressure) | ❌ | ❌ |

`750 mTorr·s` is an **exposure** (Pa·s dimension), not a pressure. The unit model
already separates these (`canonical/units.py` `EXPOSURE` dimension); nothing in the
extraction path routes it there.
