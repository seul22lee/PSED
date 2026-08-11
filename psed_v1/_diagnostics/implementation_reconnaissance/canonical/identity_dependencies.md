# Canonical layer's dependencies on upstream identity

## Direct

| canonical field | upstream source | coupling strength |
|---|---|---|
| `source.linked_experiment_ids` | resolved `experiment_id` | **the only direct dependency**; a list of opaque strings |
| `source.paper_id` / `doi` | paper directory name | strong, unchanged by any identity work |
| `source.figure`, `figure_index`, `panel`, `series`, `series_index`, `json_pointer` | `figure_data.json` | strong — but these are extraction provenance, frozen |
| `curve_id` | the four fields above | derived; does not read resolved identity |
| `source.data_source` | `panel_source` from figure extraction | strong; the B2-protected path |

## Indirect — via `sources.build_context_pool`

`build_curve` calls `S.build_context_pool(doi, fig, panel, series, c.get("experiment"))`,
which supplies the context quantities used for contextual unit conversion. It reads the
resolved experiment record. A change to which experiment a curve is linked to would change
the context pool and therefore possibly a `contextually_convertible` conversion.

## The join in the core KG

`build_core_kg.py:106-132` builds three indexes and one string-parsing join:

```python
curve_by_entity[eid.split("__case")[0]].append(c)         # L112  parses the case suffix
...
parts = str(source_series_id).split("|")                  # L123  parses entity_key
if len(parts) >= 5:
    k = (parts[0], parts[1], parts[3])                    # paper, docling index, panel
    c = curve_by_slice.get(k + (_lab(parts[4]),))         # + series label
```

`source_series_id` is `entity_key` verbatim (`to_kb.py:1334`). **`build_core_kg.py` is the
one place in the repository that parses `entity_key` positionally**, and it depends on
fields 1, 2, 4 and 5 of the six.

Fallbacks when the parse or the lookup fails: the same slice with `<single>`/`primary`
normalised to `""` (`_lab`, L98-103), then the panel when it holds exactly one curve, then
`curve_by_entity`. When all fail, `ResultSeries.source` is `"unknown"` — never `"measured"`.
