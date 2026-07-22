# Input-scope benchmark

Settles the open question — build the KB from **abstract / abstract+conclusion /
whole manuscript?** — with data instead of intuition, and **without human ground
truth**.

## Design (why it's trustworthy)

- **One variable.** A single self-contained, ontology-grounded, *text-only*
  extraction ([bench_extract.py](bench_extract.py)) runs on each scope. The only
  thing that changes between runs is how much of the paper the model sees.
- **Silver standard = full text.** No hand-labelling: the full-manuscript
  extraction is the reference, and each narrower scope is scored by how much it
  **recovers** (recall) and how much it **invents** (spurious rate — a
  hallucination proxy). [bench_score.py](bench_score.py)
- **Split by field class** — `profile` (material/process/apparatus/precursors),
  `quantitative` (text-stated quantity+value), `claims`. This is what makes the
  result actionable: it tests the hypothesis that *scope should be per-stage*
  (profile survives on abstract+conclusion; quantitative needs full text).

Note: this deliberately targets **text-stated** facts. Figure-digitised
per-experiment data (stage 06) needs the manuscript body regardless, so it isn't
part of the scope question.

## Run it (you run the LLM step)

```bash
cd 0706_pipeline/benchmark
python3 slice_scopes.py          # already run: builds slices/ (pure file ops)
python3 bench_extract.py         # dry-run: writes prompts/, prints cost (~<$0.03)
python3 bench_extract.py --run   # <-- YOU run this: 8 Gemini calls, needs GOOGLE_API_KEY in .env
python3 bench_score.py           # reads out/, prints table + writes report.json
```

`--run` uses the same client/keys/model as `0604_kg` (`gemini-2.5-flash`,
`dotenv` → `GOOGLE_API_KEY`), temperature 0, JSON mode. It **skips** any
`out/<paper>__<scope>.json` that already exists, so it's resumable.

## Corpus & caveats

- 3 papers × 3 scopes = 9 jobs; **8** actually run — `yim2020` has no parsed
  abstract (`abstract_found=false`), so its abstract-scope is excluded rather
  than faked. Abstract-scope therefore averages over 2 papers.
- 3 papers is small — read the result as a **direction**, not a precise number.
  The harness scales to the full corpus unchanged once more papers are extracted.

## How to read the output

`bench_score.py` prints per-paper and aggregate **recall vs full**, by field
class, plus spurious rate. The decision rule:

| Pattern | Action |
|---|---|
| profile recall high, quant recall low | confirm **per-stage** scope: profile/claims → `abstract+conclusion`; quantitative/equations → `full` |
| both high on a narrower scope | that scope is enough — save tokens |
| high spurious rate on a scope | that scope invents facts — avoid it |

The numbers then set `INPUT_SCOPE` in [../config.py](../config.py), and we port
the extraction stages with the answer baked in.
