# Regression (Directive 6′, step 4)

## Not run: the A10 and B11 question files are held out

The A10 and B11 question files and their run records are not in this repository (HANDOFF: "the A10_v2 records live outside this
directive's reading scope"); Directive 6′ says held-out materials stay out of this session, so the kb arm could not be rerun and no
per-question table against the last figures (A10: 98 executed / 18 refused / 134,246 tokens; B11: 97 / 27, errors 7) exists for this
state. The table below is what the directive asks for, with the columns left for the run that gets the question files.

| run | executed (last) | refused (last) | tokens (last) | executed (now) | refused (now) | tokens (now) | verdicts per question |
|---|---|---|---|---|---|---|---|
| A10 kb arm | 98 | 18 | 134,246 | not run | not run | not run | not run |
| B11 kb arm | 97 | 27 (errors 7) | | not run | not run | not run | not run |

## What was run on the 3-paper KB instead (no model call)

- pilot/questions.py: 26 of 26 questions answered through query.py (questions.csv regenerated, every status answered).
- The probe battery of check.py (P68): 153 probe calls; 77,068 tokens over the battery against 74,462 at ask-v4 (+3.5 %); max 1,811 tokens per output.
  The 21 figure sets add 21 values(set=) probes; every output stays within the 2,000-token budget.
- check.py: every section OK; the P86 cross-check found 40 stated counterparts for 43 derived scalars, 1 outside tolerance (kb/problems.txt).
- The hand-read curves against the imported ones (kb/figures_agreement.py): 101 hand curves, 59 matched, mean share within 2 % 0.43.

## The import, 12 papers

{'curves': 208, 'read': 92, 'sim': 116, 'cells': 64, 'peaks': 33, 'sets': 42, 'derived': 65} (curves: read from a figure 92, simulated 116); the 3-paper KB holds 79 curves (yim20 58: 28 read, 30 simulated; mat22 8; gre23 13), 64 cells, 25 peaks, 21 sets, 43 derived scalars.
