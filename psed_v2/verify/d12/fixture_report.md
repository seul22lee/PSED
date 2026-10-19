# Run comparison (P126)

Files: fix_a.jsonl, fix_b.jsonl · 18 records · 3 questions

## 1. Runs

| file | arms | model | max_tokens/max_calls | preamble | repeats | git head |
|---|---|---|---|---|---|---|
| fix_a.jsonl | kb, text | fixture:none | 40000/10 | kb 50e4… · text 1d62… | 2 | fixture |
| fix_b.jsonl | kb, model, text | fixture:none | 40000/10 | fixture | 1 | fixture |

## 2. Cost and process per (run, arm)

| file | arm | answers | empty/failed | tool calls / question (mean, min–max) | tool output tokens / question (vendor) | delivered tokens / question (chars/4) | input tokens (cache-read share) | output tokens | cost | cost / answer | s / answer | cost ratio vs cheapest |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fix_a.jsonl | Knowledge base | 6 | 0 | 1.8 (0–4) | 183 | 92 | 17,000 (32 % cached) | 600 | $0.0170 | $0.0028 | 1.0 | 2.83× |
| fix_a.jsonl | Paper text | 6 | 0 | 0.0 (0–0) | 0 | 0 | 17,000 (32 % cached) | 600 | $0.0085 | $0.0014 | 1.0 | 1.42× |
| fix_b.jsonl | Knowledge base | 2 | 0 | 1.0 (1–1) | 100 | 50 | 4,000 (25 % cached) | 200 | $0.0040 | $0.0020 | 1.0 | 2.00× |
| fix_b.jsonl | Paper text | 2 | 0 | 0.0 (0–0) | 0 | 0 | 4,000 (25 % cached) | 200 | $0.0020 | $0.0010 | 1.0 | 1.00× |
| fix_b.jsonl | Model only | 0 | 2 | 0.0 (0–0) | 0 | 0 | 2,000 (0 % cached) | 200 | $0.0020 |  | 1.0 |  |

## 3. Number and kind checks per (run, arm)

| file | arm | numbers | match | elsewhere | not seen | derived | uncited | kind mismatches | unknown ids | executed | refused | errors | malformed | wall hits | re-delivered | utilization |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fix_a.jsonl | Knowledge base | 11 | 55 % | 0 | 5 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 0 | none | 0 % | 83 % |
| fix_a.jsonl | Paper text | 11 | 45 % | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | none | 0 % | 0 % |
| fix_b.jsonl | Knowledge base | 2 | 0 % | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | none | 0 % | 100 % |
| fix_b.jsonl | Paper text | 2 | 0 % | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | none | 0 % | 0 % |
| fix_b.jsonl | Model only | 0 | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | none | 0 % | 0 % |

## 4. Stability per (run, arm) (P115, files with repeats)

| file | arm | questions | numbers | papers | first sentence | stability |
|---|---|---|---|---|---|---|
| fix_a.jsonl | Knowledge base | 3 | 0.33 | 0.33 | 1.00 | 0.56 |
| fix_a.jsonl | Paper text | 3 | 0.56 | 0.83 | 1.00 | 0.80 |

## 5. Per question

| no | question | fix_a.jsonl · Knowledge base | fix_a.jsonl · Paper text | fix_b.jsonl · Knowledge base | fix_b.jsonl · Paper text | fix_b.jsonl · Model only | fix_a.jsonl run 1 · anchors both / kb only / text only · papers both / kb only / text only | fix_a.jsonl run 2 · anchors both / kb only / text only · papers both / kb only / text only | fix_b.jsonl run 1 · anchors both / kb only / text only · papers both / kb only / text only |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Fixture question one: how thick is the made-up widget layer? | 4 calls · 200 tok · match 75 % · not seen 1 · uncited 0 · verdict right<br>2 calls · 100 tok · match 50 % · not seen 1 · uncited 0 · verdict slips | 0 calls · 0 tok · match 67 % · not seen 1 · uncited 0 · verdict right<br>0 calls · 0 tok · match 50 % · not seen 1 · uncited 0 · verdict material | 1 calls · 50 tok · match 0 % · not seen 1 · uncited 0 · verdict right | 0 calls · 0 tok · match 0 % · not seen 1 · uncited 0 · verdict right | 0 calls · 0 tok · no numbers · verdict empty | 2 / 1 / 1 · 1 / 1 / 0 | 1 / 1 / 1 · 1 / 0 / 1 | 1 / 0 / 0 · 1 / 0 / 0 |
| 2 | Fixture question two: which invented gadget grows faster? | 2 calls · 100 tok · match 50 % · not seen 1 · uncited 0 · verdict right<br>1 calls · 50 tok · match 0 % · not seen 1 · uncited 0 · verdict right | 0 calls · 0 tok · match 50 % · not seen 1 · uncited 0 · verdict slips<br>0 calls · 0 tok · match 0 % · not seen 1 · uncited 0 · verdict fabricated | 1 calls · 50 tok · match 0 % · not seen 1 · uncited 0 · verdict material | 0 calls · 0 tok · match 0 % · not seen 1 · uncited 0 · verdict right | 0 calls · 0 tok · no numbers · verdict empty | 1 / 1 / 1 · 1 / 1 / 0 | 1 / 0 / 0 · 1 / 0 / 0 | 0 / 1 / 1 · 0 / 1 / 1 |
| 3 | Fixture question three: what limits the pretend coating dept | 0 calls · 0 tok · no numbers · verdict empty<br>2 calls · 100 tok · match 50 % · not seen 1 · uncited 0 · verdict right | 0 calls · 0 tok · match 50 % · not seen 1 · uncited 0 · verdict right<br>0 calls · 0 tok · match 0 % · not seen 1 · uncited 0 | — | — | — | 0 / 0 / 2 · 0 / 0 / 1 | 1 / 1 / 0 · 1 / 1 / 0 | — |

## 5b. Verdicts per (run, arm)

| file | arm | right | slips | material | fabricated | empty | not graded | right share (Wilson 95 %) |
|---|---|---|---|---|---|---|---|---|
| fix_a.jsonl | Knowledge base | 4 | 1 | 0 | 0 | 1 | 0 | 67 % [30–90] |
| fix_a.jsonl | Paper text | 2 | 1 | 1 | 1 | 0 | 1 | 40 % [12–77] |
| fix_b.jsonl | Knowledge base | 1 | 0 | 1 | 0 | 0 | 0 | 50 % [9–91] |
| fix_b.jsonl | Paper text | 2 | 0 | 0 | 0 | 0 | 0 | 100 % [34–100] |
| fix_b.jsonl | Model only | 0 | 0 | 0 | 0 | 2 | 0 | 0 % [0–66] |

## 5c. Per-question verdict agreement

fix_a.jsonl run 1 (rows kb, columns text)

| kb \ text | right | slips | material | fabricated | empty | not graded |
|---|---|---|---|---|---|---|
| right | 1 | 1 | 0 | 0 | 0 | 0 |
| slips | 0 | 0 | 0 | 0 | 0 | 0 |
| material | 0 | 0 | 0 | 0 | 0 | 0 |
| fabricated | 0 | 0 | 0 | 0 | 0 | 0 |
| empty | 1 | 0 | 0 | 0 | 0 | 0 |
| not graded | 0 | 0 | 0 | 0 | 0 | 0 |

kb right & text not right: 1 questions (nos 2); text right & kb not right: 1 (nos 3)

fix_a.jsonl run 2 (rows kb, columns text)

| kb \ text | right | slips | material | fabricated | empty | not graded |
|---|---|---|---|---|---|---|
| right | 0 | 0 | 0 | 1 | 0 | 1 |
| slips | 0 | 0 | 1 | 0 | 0 | 0 |
| material | 0 | 0 | 0 | 0 | 0 | 0 |
| fabricated | 0 | 0 | 0 | 0 | 0 | 0 |
| empty | 0 | 0 | 0 | 0 | 0 | 0 |
| not graded | 0 | 0 | 0 | 0 | 0 | 0 |

kb right & text not right: 1 questions (nos 2); text right & kb not right: 0 (nos —)

fix_b.jsonl run 1 (rows kb, columns text)

| kb \ text | right | slips | material | fabricated | empty | not graded |
|---|---|---|---|---|---|---|
| right | 1 | 0 | 0 | 0 | 0 | 0 |
| slips | 0 | 0 | 0 | 0 | 0 | 0 |
| material | 1 | 0 | 0 | 0 | 0 | 0 |
| fabricated | 0 | 0 | 0 | 0 | 0 | 0 |
| empty | 0 | 0 | 0 | 0 | 0 | 0 |
| not graded | 0 | 0 | 0 | 0 | 0 | 0 |

kb right & text not right: 0 questions (nos —); text right & kb not right: 1 (nos 2)

## 6. Summary

In fix_a.jsonl, kb costs 2.0× text per answer. In fix_b.jsonl, kb costs 2.0× text per answer. Model only (fix_b.jsonl) has the fewest not-seen and uncited numbers (0); Knowledge base (fix_a.jsonl) 5; Paper text (fix_a.jsonl) 6; Knowledge base (fix_b.jsonl) 2; Paper text (fix_b.jsonl) 2. Knowledge base (fix_a.jsonl): 4 of 6 graded answers right (30–90 % Wilson 95 %), 1 slips, 0 material, 0 fabricated, 1 empty. Paper text (fix_a.jsonl): 2 of 5 graded answers right (12–77 % Wilson 95 %), 1 slips, 1 material, 1 fabricated, 0 empty. Knowledge base (fix_b.jsonl): 1 of 2 graded answers right (9–91 % Wilson 95 %), 0 slips, 1 material, 0 fabricated, 0 empty. Paper text (fix_b.jsonl): 2 of 2 graded answers right (34–100 % Wilson 95 %), 0 slips, 0 material, 0 fabricated, 0 empty. Model only (fix_b.jsonl): 0 of 2 graded answers right (0–66 % Wilson 95 %), 0 slips, 0 material, 0 fabricated, 2 empty.
