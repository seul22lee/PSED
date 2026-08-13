> **SCOPE CORRECTED.** This profile was taken over a nine-paper set that included
> `cremers2019`, a review paper since **removed from the pilot entirely** as out of
> scope. The measurements below are unchanged and were not retaken, but the conclusion
> has changed materially and is restated here.
>
> | set | seconds |
> |---|---|
> | **Active set, 8 experimental papers** | **58.5** |
> | removed review paper alone | 399.7 |
> | nine-paper set as profiled | 458.2 |
>
> **The dominant bottleneck belonged almost entirely to the removed paper.** `body_near`
> was 97.8 % of the nine-paper run because its cost grows super-linearly in document
> length and that review's `document.md` is 261 KB — 3.6× the largest active paper
> (72 KB). At active-set sizes the whole run is 58.5 s.
>
> **There is therefore no pressing performance problem in the active set, and the
> proposed `body_near` optimization is not currently justified on runtime grounds.** It
> remains correct and cheap (a cache on a pure function, mirroring `printed_caption`'s
> existing `_cap_cache`), so it is worth doing if document sizes grow or the corpus
> expands — but it is no longer urgent. Sections B2–B6 below still describe real
> inefficiencies in the active set; all are small in absolute terms at current scale.

# Performance profile — pilot resolver, as it stands

Measurement only. No semantic rule, expected count or resolver behaviour was changed.
Stages were timed by wrapping existing functions from `code/profile_pilot.py`, so no
semantic module was edited. The profiled run produced output **byte-identical** to the
preceding clean run (`md5` of all `papers/*/semantic/*.json` unchanged at
`4018c7dd124b1f71047928a3607ba766`), which is the evidence that profiling did not
perturb behaviour.

Python 3.8, single process, cProfile active.

## 1. Total runtime

| | seconds |
|---|---|
| **Total, nine papers (profiled)** | **458.2** |
| Same run unprofiled, measured earlier by process elapsed time | 758 |

The unprofiled figure is *higher* than the profiled one. That earlier measurement was
taken while two `run_pilot.py` processes were briefly competing for CPU, so 458 s is the
figure to trust and 758 s should be read as contended, not as a cProfile speed-up.

## 2. Runtime per paper

| paper | seconds | share | len(document.md) |
|---|---|---|---|
| `cremers2019` | 399.7 | 87.2% | 261,549 |
| `10.1039_d0cp03358h` | 34.5 | 7.5% | 72,351 |
| `10.1149_2.067203jes` | 7.6 | 1.6% | 60,988 |
| `10.1039_d0ra09876k` | 5.1 | 1.1% | 51,678 |
| `10.1039_d0ra01602k` | 3.6 | 0.8% | 40,411 |
| `10.1038_am.2016.182` | 3.4 | 0.7% | 46,100 |
| `10.1039_c5ta00205b` | 1.8 | 0.4% | 41,362 |
| `10.1021_acs.langmuir.6b03119` | 1.6 | 0.3% | 44,671 |
| `10.1039_c7ta03257a` | 0.7 | 0.1% | 46,082 |

**One paper is 87% of the run.** `cremers2019` is a 44-page review whose
`document.md` is 261 KB — 3.6× the next largest. Runtime tracks document length far
more strongly than it tracks the number of semantic objects produced (that paper yields
exactly **1** ExperimentalCase).

## 3. Major stages inside the semantic build

Inclusive time: a wrapped function that calls another counts the callee in both.

| stage | calls | inclusive s | % of total |
|---|---|---|---|
| `pilot_semantics.build` | 9 | 457.916 | 99.9% |
| `pilot_semantics.discover_links` | 9 | 13.475 | 2.9% |
| `pilot_supplements.build` | 9 | 1.446 | 0.3% |
| `pilot_roles.material_roles` | 226 | 0.643 | 0.1% |
| `pilot_semantics._sentences` | 34 | 0.621 | 0.1% |
| `pilot_semantics.series_definitions_from_text` | 9 | 0.526 | 0.1% |
| `pilot_semantics._norm` | 2391 | 0.291 | 0.1% |
| `pilot_semantics._paper_default_values` | 119 | 0.240 | 0.1% |
| `pilot_cases._cond_key` | 585 | 0.197 | 0.0% |
| `pilot_cases.resolve_cases` | 9 | 0.170 | 0.0% |
| `pilot_evidence.series_refs` | 11398 | 0.138 | 0.0% |
| `pilot_semantics.produced_material_chain` | 9 | 0.135 | 0.0% |
| `pilot_semantics.representation_groups` | 9 | 0.134 | 0.0% |
| `pilot_evidence.panel_clauses` | 559 | 0.130 | 0.0% |
| `pilot_evidence.techniques` | 546 | 0.119 | 0.0% |
| `pilot_semantics.Paper` | 9 | 0.106 | 0.0% |
| `pilot_semantics.text_cases` | 9 | 0.078 | 0.0% |
| `pilot_semantics._case` | 175 | 0.071 | 0.0% |
| `pilot_semantics.instrument_setting_map` | 10 | 0.055 | 0.0% |
| `pilot_cases.unresolved_pairs` | 9 | 0.054 | 0.0% |
| `pilot_semantics._shared_process_conditions` | 120 | 0.051 | 0.0% |
| `pilot_cases.resolve_conditions` | 609 | 0.048 | 0.0% |

`build` is 457.9 s, but every *named* sub-stage together accounts for roughly 17 s.
The missing ~440 s is inline code inside `build` — which section 4 locates exactly.

## 4. cProfile — top functions by cumulative time

| function | ncalls | tottime | cumtime |
|---|---|---|---|
| `run_pilot.py:186(main)` | 1 | 0.007 | 458.204 |
| `profile_pilot.py:172(timed_build)` | 9 | 0.000 | 457.916 |
| `profile_pilot.py:56(wrapper)` | 20706 | 0.144 | 457.916 |
| `pilot_semantics.py:225(build)` | 9 | 0.097 | 457.902 |
| `pilot_semantics.py:214(body_near)` | 400 | 447.950 | 448.073 |
| `pilot_semantics.py:1731(discover_links)` | 9 | 0.004 | 13.475 |
| `__init__.py:183(dumps)` | 164 | 0.003 | 3.778 |
| `encoder.py:182(encode)` | 164 | 0.357 | 3.775 |
| `encoder.py:413(_iterencode)` | 265774 | 0.703 | 3.412 |
| `encoder.py:277(_iterencode_list)` | 387834 | 1.060 | 2.653 |
| `encoder.py:333(_iterencode_dict)` | 446522 | 1.233 | 1.997 |
| `pilot_supplements.py:212(build)` | 9 | 0.006 | 1.446 |
| `pilot_supplements.py:186(render_page)` | 12 | 0.002 | 1.383 |
| `pilot_semantics.py:1905(deposition_runs)` | 9 | 0.017 | 1.219 |
| `pilot_evidence.py:158(linkage_evidence)` | 11824 | 0.066 | 0.988 |
| `pilot_evidence.py:148(_hits)` | 35472 | 0.590 | 0.922 |
| `re.py:289(_compile)` | 42480 | 0.131 | 0.685 |
| `pilot_roles.py:225(material_roles)` | 226 | 0.203 | 0.642 |
| `pilot_semantics.py:66(_sentences)` | 34 | 0.109 | 0.621 |
| `pilot_semantics.py:2000(series_definitions_from_text)` | 9 | 0.523 | 0.526 |
| `__init__.py:10245(save)` | 7 | 0.000 | 0.472 |
| `__init__.py:9990(_writeIMG)` | 7 | 0.000 | 0.471 |
| `~:0(<built-in method pymupdf._mupdf.fz_save_pixmap_as_png>)` | 7 | 0.471 | 0.471 |
| `mupdf.py:47072(fz_save_pixmap_as_png)` | 7 | 0.000 | 0.471 |
| `sre_compile.py:759(compile)` | 170 | 0.002 | 0.471 |
| `re.py:250(compile)` | 4091 | 0.011 | 0.461 |
| `~:0(<method 'search' of 're.Pattern' objects>)` | 79206 | 0.409 | 0.409 |
| `utils.py:894(get_text)` | 88 | 0.004 | 0.378 |
| `~:0(<method 'finditer' of 're.Pattern' objects>)` | 242424 | 0.356 | 0.356 |
| `re.py:198(search)` | 24780 | 0.101 | 0.348 |

## 5. Per-paper object counts

| paper | s | source entities | candidates | designs | branches | cases | link decisions | evidence | measurements | result series | representations |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `10.1038_am.2016.182` | 3.4 | 16 | 39 | 3 | 19 | 25 | 20 | 88 | 19 | 16 | 0 |
| `10.1149_2.067203jes` | 7.6 | 38 | 80 | 9 | 48 | 57 | 59 | 164 | 41 | 38 | 14 |
| `10.1039_c7ta03257a` | 0.7 | 4 | 2 | 0 | 0 | 2 | 0 | 15 | 5 | 4 | 2 |
| `10.1039_d0cp03358h` | 34.5 | 70 | 36 | 6 | 18 | 11 | 137 | 374 | 44 | 70 | 53 |
| `cremers2019` | 399.7 | 93 | 1 | 0 | 0 | 1 | 0 | 50 | 9 | 93 | 25 |
| `10.1039_d0ra09876k` | 5.1 | 34 | 47 | 3 | 20 | 47 | 2 | 120 | 33 | 34 | 0 |
| `10.1039_c5ta00205b` | 1.8 | 21 | 7 | 0 | 0 | 5 | 0 | 26 | 21 | 21 | 0 |
| `10.1021_acs.langmuir.6b03119` | 1.6 | 12 | 13 | 0 | 0 | 7 | 0 | 28 | 13 | 12 | 2 |
| `10.1039_d0ra01602k` | 3.6 | 36 | 20 | 0 | 0 | 20 | 0 | 58 | 37 | 36 | 0 |

## 6. Suspected bottlenecks

### B1 — `Paper.body_near` re-scans the whole document with a lazy unanchored regex
**97.8 % of total runtime. 400 calls, 447.95 s `tottime`, 1.12 s per call.**
`tottime` — the cost is inside this function's own regex engine work, not in callees.

```python
# pilot_semantics.py:214
def body_near(self, printed):
    out = []
    for m in re.finditer(r"[^.]*?\bFig(?:ure)?\.?\s*%s\b[^.]*\." % re.escape(str(printed)),
                         self.md, re.I):
        out.append(_norm(m.group(0)))
    return " ".join(out)[:4000]
```

Three things compound:

1. **Leading `[^.]*?` is lazy and unanchored.** At every start position that is not
   inside a match, the engine expands the lazy quantifier one character at a time
   looking for `Fig`, fails, advances one position, and repeats. Work per start
   position grows with the distance to the next period, so total work grows with the
   product of document length and sentence length.
2. **The whole `document.md` is scanned on every call**, not the region near the figure.
3. **There is no cache.** `printed_caption` has `self._cap_cache`; `body_near` has
   none, so the same (paper, figure) pair is recomputed on every entity that mentions
   it. It is called from two places — the per-entity loop (`:447`) and
   `discover_links` (`:1782`).

Measured scaling on the worst document, same regex, increasing prefix length:

| document prefix | chars | seconds | vs previous |
|---|---|---|---|
| 12.5 % | 32,693 | 0.053 | — |
| 25 % | 65,387 | 0.133 | 2.5× for 2× input |
| 50 % | 130,774 | 1.239 | 9.3× for 2× input |
| 100 % | 261,549 | 4.189 | 3.4× for 2× input |

4× the input (65 k → 261 k) costs 31× the time. **Empirically ~O(N^2.5)** in document
length; the regex's worst case is quadratic and the observed exponent exceeds that
because longer documents also contain longer sentences.

Arithmetic check: 261 KB document × 4.09 s/call × ~98 calls ≈ 400 s, which is exactly
`cremers2019`'s measured 399.7 s. The bottleneck fully explains the paper, and the
paper fully explains the run.

### B2 — `discover_links` pairwise scope comparison
**13.48 s, 2.9 % of total, 9 calls.** The second-largest cost and the largest one that
is genuinely about semantics.
`pilot_evidence.linkage_evidence` is called **11,824** times and `_hits` **35,472**
times (3 per call). Call volume grows as scopes × candidates: for one paper that is
**O(S × C)** and, where candidate pairs are compared, **O(C²)**. `d0cp03358h` — 70
entities, 137 link decisions — spends 34.5 s, most of it here; it is the only paper
where link discovery, not document scanning, dominates.

### B3 — repeated `_paper_default_values(P)` construction
**119 calls, 0.24 s.** Small in absolute terms, but it is called *inside* loops at
`:743`, `:794`, `:796` and `:833` and rebuilds the same paper-level dict every time by
re-walking `_shared_process_conditions` and every entity's `bound_conditions`
(`_shared_process_conditions`: 120 calls). **O(entities) per call, O(entities²) per
paper.** Currently masked by B1.

### B4 — linear `next(...)` lookups inside loops
Nine sites scan a whole list per iteration:
`:942` measurements, `:1092` samples, `:1096`/`:1101` cases, `:1455` samples,
`:1963` study series. Each is **O(objects)** inside a loop over objects → **O(N²)**.
Too small to appear in this profile (the back-reference pass is well under a second at
current sizes), but it scales with corpus size, not document size.

### B5 — repeated JSON serialisation
**`json.dumps` 3.78 s cumulative over 164 calls** (`_iterencode_dict` 446,522 calls).
This is report/output writing, not resolving — 0.8 % of the run, and inherent to
emitting the artifacts.

### B6 — PDF page rendering inside supplement detection
`pilot_supplements.build` 1.45 s, of which `render_page` 1.38 s and
`fz_save_pixmap_as_png` 0.47 s over 7 calls. **Filesystem and PDF I/O**, executed while
classifying missing panels. Bounded (7 renders) but it is I/O in a semantic path.

### Explicitly checked and NOT found

- **Repeated JSON reads of paper inputs** — `Paper._j` runs once per file per paper;
  `Paper` construction totals 0.106 s across all nine. Inputs are read once.
- **Repeated markdown parsing** — `_norm` is 2,391 calls / 0.291 s; `_sentences` 34
  calls / 0.621 s. Not a hotspot.
- **Caption re-derivation** — `printed_caption` is already cached via `_cap_cache`.
- **O(N³)** — no three-level nesting was observed in the profile.

## 7. Which optimizations would be behaviour-preserving

Ranked by measured benefit. Each is a statement about what *would* preserve behaviour;
none has been applied.

| # | change | expected saving | why behaviour is preserved | risk |
|---|---|---|---|---|
| 1 | **Memoize `body_near` per (paper, printed figure)**, exactly as `printed_caption` already memoizes | ~440 s → ~10 s; **≈96 % of total runtime** | pure function of `self.md` and `printed`, both immutable for a `Paper`; identical string returned | very low |
| 2 | **Anchor the scan**: find `Fig N` occurrences first (`finditer` on the literal), then expand to sentence bounds around each hit | turns O(N^2.5) into O(N + hits×sentence) | same sentences selected, provided expansion uses the same `[^.]` boundary and the same 4,000-char cap | low — needs a regression diff of the returned string on all nine |
| 3 | **Hoist `_paper_default_values(P)` to one call per paper** | ~0.2 s now; removes an O(entities²) term | the dict is a pure function of the paper and is already recomputed identically at each site | very low |
| 4 | **Index the `next(...)` lookups** into dicts built once per paper (`{measurement_id: m}`, `{case_id: c}`, `{sample_id: s}`) | negligible now; removes five O(N²) terms | dict lookup returns the same object as the linear scan; ids are unique (asserted by invariant S8) | very low |
| 5 | **Precompute the scope→candidate index in `discover_links`** so `linkage_evidence` is called once per (scope, pattern) rather than per candidate pair | up to ~10 s on link-heavy papers | evidence records are keyed by scope, not by pair; the same set is produced | medium — this is semantic code and must be diffed against `links.json` |
| 6 | Cache `render_page` output by (pdf, page) | ~1 s | rendering is deterministic | very low |

**Order matters:** item 1 alone removes ~96 % of the runtime and is a two-line cache
on a pure function. Items 2 and 5 touch matching logic and should only follow a
byte-for-byte diff of `papers/*/semantic/*.json` — the same `md5` check used to verify
this profiling run.

## 8. Method and reproduction

```
python3 code/profile_pilot.py     # one run: wall clock, per-paper, per-stage, cProfile
```
Raw output: `logs/profile_raw.json`, `logs/profile_cumulative.txt`.
Integrity check used here:
```
find papers -path '*/semantic/*.json' | sort | xargs md5sum | md5sum
```
Identical before and after profiling.

