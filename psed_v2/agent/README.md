# KB question-answering agent (Sec. 3.3.1)

An LLM agent that answers questions by calling deterministic tools over the compiled KB, step by step, and logs every
call. The Sec. 3.3.1 figure is rebuilt from these logs: every box (plan, resolve, retrieve, analyze, answer) is a logged
call or the final answer.

```
psed_v2/agent/
  tools.py          the six tools (no model call) + unit_tree for the UI; --check runs the expected paths and the known KB issues
  agent.py          Conversation: the provider layer (DeepSeek / Anthropic), the tool loop, streaming, logging; CLI for one question or a chat
  run_cases.py      the three preset queries, 3 runs each; --report writes runs/REPORT.md from the logs
  app.py            FastAPI app; static/index.html is the page (no build step)
  runs/             one JSON log per conversation: <case>_<timestamp>.json (chat_<timestamp>.json for free questions); field origin:
                    run_cases (the batch runs the report reads), app (the web app), cli
```

## Run

Conda env `psed310` (it has `anthropic` and `openai`; `fastapi` was added for the app). The agent code lives on branch
`kb-agent`, checked out as its own worktree (`git worktree add ../psed-agent kb-agent`); run from that worktree's root.
`psed_v2/.env` (not in git) is read from the worktree, else from the main checkout; it sets `PSED_MODEL` and the keys.
Crops are read from the main checkout's `psed_v2/ingest/final/` when the worktree has none.

```
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.tools --check            # no key needed
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.run_cases --plan         # planned calls and cost, no call
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.run_cases                # 3 cases x 3 runs (asks y/n first)
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.run_cases --report       # -> runs/REPORT.md
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.agent "question"         # one question
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.agent --interactive      # follow-ups in one conversation
~/miniconda3/envs/psed310/bin/python -m psed_v2.agent.app [--port 8770]       # http://127.0.0.1:8765/ by default
```

`python -m psed_v2.agent.tools --call find_samples '{"filters": [...]}'` prints one tool's full result.

## Model and loop

`PSED_MODEL=provider:model` (env or `.env`; `--model` overrides) picks the provider:

- `deepseek:deepseek-flash` (in use): the openai SDK on DeepSeek's OpenAI-compatible API (`https://api.deepseek.com`,
  `DEEPSEEK_API_KEY`); tool schemas sent in the OpenAI `tools` format; thinking on, effort `high` (the model's default);
  each turn's `reasoning_content` is passed back in every later request, as the API requires when tools are present.
  Verified on 2026-10-25: `GET /models` lists `deepseek-flash` (DeepSeek-V4.1-Flash), and a tool-call request returned a
  function call. Cost estimates use the peak rates ($0.30 / $0.006 cached / $1.20 per million input / cached / output).
- `anthropic:claude-sonnet-5-5`: the anthropic SDK, adaptive thinking (summarized), effort `medium`, prompt caching, the
  server-side refusal fallback (`fallbacks: "default"`; a turn served by another model is logged as `fallback_ran`).

Both stream, and the loop is the same: the model calls tools, reads the results, calls again, then answers. At most 15
tool calls per question; past the cap each call returns an error asking for the answer. The log records the provider,
the model, and each request's token usage (input, cached input, output, reasoning) with a cost estimate. Key values are
never logged; errors are scrubbed of them. Batch mode (the presets) never asks a clarifying question and states its
reading; interactive mode (free questions in the app, `--interactive`) may ask one.

The system prompt carries the rules: every number from a tool result with its fact_id in brackets; only the 13 papers;
a cited value is reported as cited, never as evidence; "not recorded" when the KB has none; no guessed causes; report
the tools' flags (conflicts, exclusions, undecided samples); plain names, not internal terms.

## Tools

| tool | what it returns |
|---|---|
| `resolve(term, kind)` | ontology concepts: exact / partial / in a definition / printed so in the KB; methods of the same class; a structure class's subclasses and structures; a quantity's unit, dimension, printed labels, qualifiers in the KB, other concepts of its category, structure classes that carry it as a slot |
| `find_samples(filters, vary, include_models, papers)` | specimens and run films (model runs on request) matching every filter; per sample the matched conditions as `value [fact_id] (where from)`, the `vary` values, conflicts; counts (scanned, matched, per paper, failures by filter and reason); undecided samples |
| `get_records(sample_ids, quantity, qualifiers, include, normalize, methods, papers)` | values (fact_id, value, unit, data_kind, statement, the sample's key conditions), curves (points, axes, figure-derived plateau and 50% crossing), images (id, method, description, crop path); with no ids, every record of the quantity in the KB, own / cited / model in that order; excluded and rejected values with the reason |
| `compare(sample_ids)` | every condition: same, different (per sample), recorded for some only; conflicts; the KB comparison sets and figure series holding these samples |
| `claims(cause, effect, papers, relation)` | claim facts with cause, relation, effect, stance, statement, and the linked records resolved to samples and the conditions that differ among them |
| `trace_citation(fact_id)` | for a cited value: the cited paper if it is one of the 13 (first author and year in the citing text), its own values, value match and the conditions side by side |

The model receives `tools.model_view(result)`: curve points summarized (count and ranges) and statements cut to 200
characters. The log keeps the full result (`result`) and the exact text sent (`sent`); the number check uses `sent`.

General rules in the tools (no logic keyed on a paper, element or value):

- Inheritance: per (quantity, qualifiers) the nearest level holding the key wins; a level holding several values of a key
  passes none down ("several values at recipe (not inherited)").
- Conflict: two conditions of one quantity at different levels whose qualifiers agree except a missing species / step /
  gas / element, with different values: the nearer is preferred and both are reported.
- A filter value against a recorded range is not a match ("recorded as a range"); such samples are listed as undecided.
- A value whose unit's dimension differs from its quantity's (or flagged `dimension_mismatch` by compile) is rejected.
- A species of kind material on a value excludes it from a species query (as compile's P207 rule: "material is not a
  molecule"); an atom species (O radicals) is kept as a reactant.
- An own value without a species takes its run's reactant A when a species is asked for (`species_filled`); cited and
  model values are not filled.

## The known KB issues

| issue | how the tools handle it |
|---|---|
| Yim 2020 samples 15, 16: own N₂ purge 1 s / 10 s plus the recipe's 4 s | conflict: the run's value preferred, both reported (find_samples `conflicts`, compare, unit tree) |
| ela03 sticking coefficients with species al2o3 / sio2 | excluded from a species query, listed with "species … is a material, not a molecule" |
| yli18 Table I `c` without species | filled from the run's reactant A, marked `species_filled` |
| gao15 s6.p22#2 `penetration_depth level=50%` = 130, no unit | rejected: unit dimensionless vs length |
| gao15 Fig. 3 specimens with the recipe range 110–300 °C | not matched to 300 °C; listed as undecided ("recorded as a range") |

## Recipe fill: two sources

`RECIPE_SOURCE` (env `PSED_AGENT_RECIPE_SOURCE`) picks where a run's reactants, carrier gas, process mode and material
come from: `compiled` (default, user: `kb/compiled/<pid>.recipe_fields.csv`, compile's importer with its quote check and
the user's history.csv recipe decisions) or `records` (an option: every `0rf` line merged in file order, the line
compile.log names last). They differ on 32 fields; `tools --check` lists them. Examples: yli18 runs `process_mode` thermal
(records) vs null (the user's P182 decision); yli18 simulations `carrier_gas` null vs n2 (the user's decision); gao15
Fig. 3 runs reactant A / B tma / h2o (records) vs null (quote not found). The log records the source used.

## UI

Left: the conversation (the answer streams; each number cited with a fact_id links to its record; an id in no tool
result is marked red). Middle: one card per step, LLM and KB marked, each expandable to the full JSON. Right: the
evidence of the selected step or number: values table, curves per figure panel (raw and, when the tool normalized them,
normalized, with the references used), images (the crop when present on this machine, else id and description), the
unit tree of a sample (conditions by level, used / shadowed / conflict marked; from `tools.unit_tree`, logged as a UI
tool call), claims and citation traces. Buttons: the three presets, new conversation, open a saved log (read-only),
export the log (JSON) and the evidence shown (CSV). The page computes no value; it shows logged tool results.

Crops are not in git: `kb/pilot/<pid>.elements.csv` gives the path under `psed_v2/ingest/final/<pid>/`. An image's
description is the figure stage's panel description from `kb/<pid>.figures.json`, not the paper's caption.

## Validation (run_cases.py --report)

Reads the logs of origin `run_cases`. Per case and run: the tool calls in order with a key result each, the plan, the
case listing (case 1: every sample with paper, method and structure, the papers, every image with method and sample,
the images not tied to one sample; case 2: every sample with each condition it matched, whether pulse_time and
purge_time were filtered; case 3: the values sorted by how they were obtained, the filled species, the citation traces),
the deviations from the expected path, the final answer, every number of the answer against the text the tools sent
(exact / rounded / not found), and the counts the figure shows. Each run's sets are compared with "the reference": the
expected path run on the tools at report time (the directive's arguments; no counts pinned). Per case: the differences
between runs (tool path, samples, images, values, traced citations, numbers, cited fact ids, figure counts).
