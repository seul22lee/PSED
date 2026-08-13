#!/usr/bin/env python3
"""Profile the pilot resolver exactly as it stands.

Measurement only. Nothing here changes resolver behaviour: stages are timed by WRAPPING
the existing functions from outside, so no semantic module is edited and the wrapped
callables return exactly what they returned before.

Produces `logs/profile_raw.json` with:
  * total wall time of the nine-paper run
  * wall time per paper
  * inclusive wall time and call count per major stage
  * cProfile stats (top functions by cumulative time)
  * per-paper object counts

Run once:  python3 code/profile_pilot.py
"""
import cProfile
import io
import json
import pstats
import sys
import time
from collections import defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))

import pilot_cases as PC          # noqa: E402
import pilot_design as D          # noqa: E402
import pilot_evidence as PE       # noqa: E402
import pilot_ranges as PRG        # noqa: E402
import pilot_roles as R           # noqa: E402
import pilot_sample_table as PT   # noqa: E402
import pilot_semantics as S       # noqa: E402
import pilot_supplements as SUP   # noqa: E402
import run_pilot                  # noqa: E402

PAPERS = json.loads((W / "pilot_papers.json").read_text())["papers"]

#: stage -> [calls, inclusive seconds]. Inclusive: a wrapped function that calls another
#: wrapped function counts the callee's time in both, which is what "stage" means here.
STAGE = defaultdict(lambda: [0, 0.0])
CURRENT = {"pid": None}
#: per-paper counters that only the resolver knows: candidates minted, entities read
PER_PAPER = defaultdict(lambda: defaultdict(int))


def wrap(mod, name, label=None):
    """Time every call to mod.name without altering what it returns."""
    fn = getattr(mod, name, None)
    if fn is None or getattr(fn, "_profiled", False):
        return
    label = label or "%s.%s" % (mod.__name__, name)

    def wrapper(*a, **k):
        t0 = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            rec = STAGE[label]
            rec[0] += 1
            rec[1] += time.perf_counter() - t0
            if CURRENT["pid"]:
                PER_PAPER[CURRENT["pid"]]["stage::" + label] += 1

    wrapper._profiled = True
    wrapper.__name__ = getattr(fn, "__name__", name)
    setattr(mod, name, wrapper)


#: The stages worth naming. Chosen because each is a distinct phase of the build, not
#: because of what the profile turned out to say.
STAGES = [
    (S, "Paper"),                       # every JSON/markdown read for one paper
    (S, "build"),
    (S, "discover_links"),
    (S, "nominal_identity_links"),
    (S, "tabulated_case_links"),
    (S, "build_value_joins"),
    (S, "value_join_specimens"),
    (S, "series_design_factors"),
    (S, "series_definitions_from_text"),
    (S, "text_cases"),
    (S, "representation_groups"),
    (S, "produced_material_chain"),
    (S, "instrument_setting_map"),
    (S, "_case"),
    (S, "_cand"),
    (S, "_paper_default_values"),
    (S, "local_synthesis_evidence"),
    (S, "_shared_process_conditions"),
    (S, "_sentences"),
    (S, "_norm"),
    (PC, "resolve_cases"),
    (PC, "entity_conditions"),
    (PC, "resolve_conditions"),
    (PC, "compatibility"),
    (PC, "_cond_key"),
    (PC, "unresolved_pairs"),
    (PC, "chemistry_conditions"),
    (D, "design_from_sweep"),
    (D, "signatures_identify_same_design"),
    (D, "decompose_recipe"),
    (D, "nominal_key"),
    (R, "material_roles"),
    (R, "condition_role"),
    (R, "geometry_in_scope"),
    (R, "is_species_property"),
    (PE, "panel_clauses"),
    (PE, "sample_codes"),
    (PE, "series_refs"),
    (PE, "techniques"),
    (PRG, "repair_all"),
    (PRG, "quantities_from_text"),
    (SUP, "build"),
    (SUP, "image_supported_cases"),
    (PT, "column_map"),
]


def install():
    for mod, name in STAGES:
        wrap(mod, name)
    # Paper.printed_caption / body_near are methods: wrap on the class
    for meth in ("printed_caption", "caption", "body_near", "_j"):
        fn = getattr(S.Paper, meth, None)
        if fn is None or getattr(fn, "_profiled", False):
            continue

        def mk(fn=fn, meth=meth):
            def wrapper(self, *a, **k):
                t0 = time.perf_counter()
                try:
                    return fn(self, *a, **k)
                finally:
                    rec = STAGE["Paper.%s" % meth]
                    rec[0] += 1
                    rec[1] += time.perf_counter() - t0
            wrapper._profiled = True
            return wrapper
        setattr(S.Paper, meth, mk())


def counts_on_disk(pid):
    d = W / "papers" / pid / "semantic"

    def n(name):
        f = d / ("%s.json" % name)
        return len(json.loads(f.read_text())) if f.exists() else 0
    return {
        "experimental_designs": n("experimental_designs"),
        "design_branches": n("design_branches"),
        "experimental_cases": n("experimental_cases"),
        "link_decisions": n("links"),
        "evidence_records": n("evidence"),
        "measurements": n("measurements"),
        "result_series": n("result_series"),
        "representations": n("representations"),
        "samples": n("samples"),
        "simulation_runs": n("simulation_runs"),
        "unresolved": n("unresolved"),
    }


def main():
    install()

    per_paper = {}
    real_build = S.build

    def timed_build(pid):
        CURRENT["pid"] = pid
        t0 = time.perf_counter()
        try:
            o = real_build(pid)
        finally:
            per_paper[pid] = time.perf_counter() - t0
            CURRENT["pid"] = None
        return o

    S.build = timed_build
    run_pilot.S = S

    prof = cProfile.Profile()
    t_start = time.perf_counter()
    prof.enable()
    try:
        run_pilot.main()
    finally:
        prof.disable()
    total = time.perf_counter() - t_start

    buf = io.StringIO()
    st = pstats.Stats(prof, stream=buf).sort_stats("cumulative")
    st.print_stats(60)
    cum_text = buf.getvalue()

    rows = []
    for fn, (cc, nc, tt, ct, _cal) in st.stats.items():
        rows.append({"function": "%s:%d(%s)" % (Path(fn[0]).name, fn[1], fn[2]),
                     "ncalls": nc, "tottime": round(tt, 4),
                     "cumtime": round(ct, 4)})
    rows.sort(key=lambda r: -r["cumtime"])

    out = {
        "total_wall_seconds": round(total, 2),
        "per_paper_seconds": {k: round(v, 2) for k, v in per_paper.items()},
        "stages": sorted(({"stage": k, "calls": v[0], "inclusive_seconds": round(v[1], 3)}
                          for k, v in STAGE.items()),
                         key=lambda r: -r["inclusive_seconds"]),
        "cprofile_top": rows[:60],
        "per_paper_counts": {pid: dict(counts_on_disk(pid),
                                       source_entities=PER_PAPER[pid].get(
                                           "stage::pilot_cases.entity_conditions", 0),
                                       candidates=PER_PAPER[pid].get(
                                           "stage::pilot_semantics._cand", 0))
                             for pid in PAPERS},
    }
    (W / "logs").mkdir(exist_ok=True)
    (W / "logs" / "profile_raw.json").write_text(json.dumps(out, indent=1))
    (W / "logs" / "profile_cumulative.txt").write_text(cum_text)
    print("total %.1fs" % total)
    for pid, sec in sorted(per_paper.items(), key=lambda kv: -kv[1]):
        print("  %-30s %6.1fs" % (pid[:30], sec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
