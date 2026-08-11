# Semantic fields available at identity time

`entity_key` is built at `to_kb.py:901-903`; `experiment_id` at L1236. This lists what the
resolver already holds at each of those points.

## Available at `entity_key` construction (L901)

From `ctx` (`_entity_context`, L530-594) and `e{}`:

| field | source | populated | used in identity |
|---|---|---|---|
| `caption` (full) | `figure_data.json` | yes | no |
| `body_mentions` | `document.md` near the figure | yes | no |
| `source_series` (legend label) | record `series_name` | yes | **yes** |
| `representation` | `_representation(caption, panel)` | 1044/1044 | **yes** (no effect — see representation_identity.md) |
| `panel_conditions` | vision panel `conditions` | partial | no |
| `panel_series_labels` | all labels in the panel | yes | no |
| `panel_source_flag` / `figure_source_flag` | measured/simulated | yes | no |
| `coordinate`, `granularity`, `x_axis_role` | axis resolution | yes | no |
| `fig_docling_index`, `figure_number`, `panel`, `panel_key` | provenance | yes | **yes (4 of 6 key fields)** |
| `material`, `material_scope_level`, `material_evidence`, `material_candidates` | `cschem.resolve_material` ladder | 1044/1044 | no |
| `precursors`, `coreactants`, `reactants`, `carrier_gas`, `process_type`, `cycle_sequence` | card + propagation | yes | no |
| `geometry_class`, `structure` | paper `geometry.json` | yes | no |

## Available before case minting (L1037), additionally

| field | value/shape | populated | used in identity |
|---|---|---|---|
| `classification` + `confidence` + `method` | 11-way | 1044/1044 | gates minting, not identity |
| `signal_families` | letters, e.g. `["F","M","I","X"]` | 1044/1044 | no |
| `signals` (the matched TEXT per family) | dict | **computed, not persisted** | no |
| `supported_setting_count` / `_evidence` | from `SAMPLE_LIST` | **computed, not persisted** | no |
| `bound_conditions` | 2601 corpus-wide, with quantity/value/unit/scope/source_kind/species/raw_evidence/locator | 1044/1044 | no |
| `ambiguous_conditions` | list | partial | no |
| `granularity_kind` + evidence | 5-way | 1044/1044 | gates sweep expansion |
| `between_curve_condition` / `between_curve_value` | from the series axis | partial | no |
| `series_source_kind` / `fit_of_series_label` | measured/calculated/fit | 1044/1044 | no |
| `observations` | full x/y raw + canonical | 1044/1044 | no |

## The signal `I` — sample/run/series identifiers

`entities.py:69-73`:

```python
SAMPLE_ID = re.compile(
    r"\b(?:samples?|runs?|specimens?)\s+((?:[A-Za-z0-9]+\s*[,;]?\s*(?:and\s*)?){1,8})"
    r"(?:\s*(?:in|of|from)\s+Table\s*\S+)?|\bSeries\s+([A-Z])\b", re.I)
SAMPLE_LIST = re.compile(r"\b(?:samples?|runs?|specimens?)\s+"
                         r"((?:[A-Za-z0-9]+\s*(?:,|and)\s*){1,10}[A-Za-z0-9]+)", re.I)
```

Applied at `entities.py:331` to the caption and the body; the match becomes `sig["I"]`.

Measured: **268 entities across 24 papers carry family `I`.** On Yim's figure captions the
regex returns `sample 11 surface`, `Samples 4, 5, and 6`, `sample 8 in Table 1`,
`Sample 7, 8, and 9`, `sample 12, 13, and 14 in Table 1 Series E`.

`to_kb.py:976` persists `cls["signal_families"]` (the letters only). `cls["signals"]`,
`cls["votes"]`, `cls["supported_setting_count"]` and `cls["supported_setting_evidence"]`
are not written to any output. Corpus check: none of those four keys appears on any of the
1044 entities.

## Signal family census (entities carrying each)

```
F 1042   source flag                 X  802   axis/coordinate
Me 715   methods modality            M  679   figure modality
R  374   run structure               T  304   table caption
I  268   sample/run/Series id        L   44   literature/simulation label
```
