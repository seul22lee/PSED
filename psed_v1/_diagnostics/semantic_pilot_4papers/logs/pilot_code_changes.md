# Pilot implementation change log

Two production modules were COPIED into `code/`. One copy was modified; the other is an
unmodified reference. Everything else is new pilot code. **No production file was edited.**

## Copied production modules

| original | pilot copy | changed? | functions changed | why | narrower change possible? | tests |
|---|---|---|---|---|---|---|
| `pipeline/figures/inventory.py` | `code/pilot_inventory.py` | **no — kept as an unmodified reference** | — | The caption-grammar defect it contains (`_PANEL_HEAD` rejecting `( a )`) is the cause of the `am.2016.182` Figure 4 loss. Rather than fork a 594-line production module for one regex, the pilot implements its own caption/panel parser in `code/pilot_evidence.py`, which the semantic layer actually uses. The copy is retained so the defect can be diffed against the pilot's parser. | Yes, and it was taken: the narrower change is a new 40-line parser, not a forked module. | invariant 16; `am: printed Figure 4 evidence is present` |
| `pipeline/canonical/entities.py` | `code/pilot_entities.py` | **no — unmodified reference** | — | Read to reuse its `SAMPLE_ID` / `SAMPLE_LIST` intent and to confirm which entity classes are non-experimental (`CLASS_MODEL`, `ENTITY_CLASS`), which the pilot preserves verbatim as `SIMULATION_CLASSES` / `NON_EXPERIMENTAL`. | n/a | invariants 12, 13, 14 |

## New pilot modules

| module | responsibility | semantic requirement served | tests |
|---|---|---|---|
| `code/pilot_evidence.py` | generic source-text evidence: explicit same/different/repeat statements, specimen codes, series references, techniques, **panel-clause splitting that accepts `( a )`, `(a-c)` and `(panels a-c)`**, representation type | §6, §7, §5.4, §12A | invariants 5, 7, 8; am Figure 4 anchors |
| `code/pilot_roles.py` | the two role vocabularies: condition role (CASE_DEFINING / MEASUREMENT_SETTING / MODEL_PARAMETER / DERIVED) driven by the ontology's own `recipe_role` plus a generic instrument lexicon; material role (DEPOSITED / SUBSTRATE / SUPPORT / TEMPLATE / STACK_COMPONENT); figure-scope geometry | §9, §10, §11 | invariant 4; jes stack anchors; yim Series B |
| `code/pilot_cases.py` | sweep normalisation (each case carries its own varied value), condition compatibility, the evidence-gated union-find resolver, unresolved-pair reporting, chemistry identity from the series legend | §6, §8 | invariants 3, 7, 8; am precursor-blocked merges |
| `code/pilot_sample_table.py` | recovers the per-specimen parameter table from the PDF's reading order (Docling's export of it is transposed and unusable) | §5.5, §5.6, §16 | yim Series A / sample 8 / sample 12 anchors |
| `code/pilot_supplements.py` | finds caption panels that describe a measurement and have no extracted entity; classifies the cause (`caption_not_associated` vs `panel_absent_from_crop`); renders the PDF page locally as evidence | §12, §14, §15A, §15C | am Figure 4; cta Fig 8(b) |
| `code/pilot_semantics.py` | builds the eleven semantic objects per paper and wires the relations | §5, §22–§26 | all |
| `code/run_pilot.py` | runner + old-vs-pilot comparison + invariant computation | §27, §44 | — |
| `code/build_report.py` | the self-contained HTML review report | §28–§38 | — |
| `pilot_papers.json` | the work list, in configuration rather than code | §41 | invariant 16 |

## Decisions taken to keep the change minimal

- **The pilot is a post-resolve layer.** It reads the existing `resolved/` and `extracted/`
  artifacts and adds semantics on top. `to_kb.py` (2019 lines) was neither copied nor
  forked, so the entire extraction and resolution chain is untouched and every source
  identity survives by construction.
- **The resolver's own sweep-granularity verdict is reused verbatim.** How many settings a
  digitised curve represents is an extraction-quality question PSED already answers
  (`experimental_case_status` / `experimental_case_count`, guarded by
  `MAX_UNENUMERATED_SETTINGS`). The pilot adds only what was missing: WHICH value each
  case carries.
- **No production identity was renamed.** `entity_id`, `exp_id`, `curve_id`,
  `json_pointer`, `physical_case_id` are all carried through unchanged as source
  provenance; the pilot's scientific ids (`CASE-…`, `M::…`, `S::…`, `RUN::…`) are new and
  separate, per §19.
- **`entity_key` was NOT reused as scientific identity**, per §19.

## What would need porting back, if anything

Ranked by how much of the pilot's result depends on it — this is an observation, not a
recommendation, and the porting decision is outside this task:

1. the caption/panel grammar accepting `( a )` (one regex; recovers a whole printed figure);
2. the curve→entity source-slice fallback join (no ResultSeries would be lost);
3. the condition role axis (nothing else separates a deposition setting from an instrument one);
4. per-case sweep values (`case00` → `deposition_temperature = 100 °C`);
5. the specimen-table reader (the only source of specimen identity in papers that tabulate).
