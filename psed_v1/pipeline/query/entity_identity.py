#!/usr/bin/env python3
"""Entity identity: condition cases, physical realizations, observing acts.

The audit established what these entities actually are, and the names are misleading in
one important way: an `ExperimentalCase` is a **condition-defined case**, not a physical
experiment. One case can have several physical realizations, and its conditions are
nominal -- they describe the design point, not something measured on any particular chip.
A UI that calls it "Experiment" asserts a physical identity the data does not carry.

Three repairs live here.

`MeasurementAct` makes the model's own `represents_same_measurement_as` operational. That
field already records that Fig 9a, 9b and 9c are one observing act rendered three ways,
but the entities were still minted per curve, so the knowledge sat in a sideband while the
structure disagreed with it. Grouping is by transitive closure and only ever follows that
explicit link -- never "same figure", never "same conditions", because neither is evidence
about an observing act. Existing Measurement ids are preserved; an act is a grouping over
them, not a replacement for them.

`persisted_run_id` exists because a reader that guessed the field name produced a run with
a null identity, and a null identity that groups things asserts a shared run nobody
recorded. Run membership is read from explicit links only.

`cases_for_result_series` closes the first-case collapse. A sweep curve legitimately
belongs to every case it traverses, and returning `case_ids[0]` silently discards the
rest. Callers that genuinely need one case must say so and handle the alternative.
"""
import json
from collections import defaultdict
from pathlib import Path

# --- condition scope: where a condition's evidence actually comes from -------------
DIRECT_SAMPLE_EVIDENCE = "DIRECT_SAMPLE_EVIDENCE"
CASE_CONTEXT = "CASE_CONTEXT"
RUN_CONTEXT = "RUN_CONTEXT"
MEASUREMENT_SETTING = "MEASUREMENT_SETTING"

#: what a Case->Run link means. Never "this case was grown in this run": a case may hold
#: several realizations and only some of them may have a known run.
RUNS_OBSERVED_AMONG_CASE_REALIZATIONS = "RUNS_OBSERVED_AMONG_CASE_REALIZATIONS"

MULTI_CASE = "MULTI_CASE"
NO_CASE = "NO_CASE"

#: A run record whose identifier cannot be resolved. It is never given a synthetic id and
#: never becomes a bucket: a null identity that groups things asserts a shared run that
#: nobody recorded.
INVALID_RUN_RECORD = "INVALID_RUN_RECORD"

#: Field names a persisted DepositionRun may carry, in authority order. The live schema
#: uses `run_id`; a reader that only knew `deposition_run_id`/`id` silently produced a
#: null-identified run and swept run-less samples into it.
_RUN_ID_FIELDS = ("run_id", "deposition_run_id", "id")

#: how a canonical physical specimen was established
SPECIMEN_FROM_TRACEABLE_ID = "TRACEABLE_SPECIMEN_ID"
SPECIMEN_UNRESOLVED = "PHYSICAL_IDENTITY_UNRESOLVED"
RUN_LINK_VIA_CANONICAL_PHYSICAL_IDENTITY = "RUN_LINK_VIA_CANONICAL_PHYSICAL_IDENTITY"

#: Field names that denote a PERSISTENT PHYSICAL specimen identifier. Deliberately narrow:
#: a bare "sample code" is a paper-local analysis label, not a specimen identity, and
#: treating it as one would manufacture physical identity out of table row numbers.
_SPECIMEN_ID_FIELDS = ("traceable_sample_code", "traceable_specimen_id",
                       "unique_sample_code", "unique_specimen_code",
                       "physical_specimen_id", "specimen_id", "chip_id", "wafer_id")


def persisted_run_id(record):
    """The identifier of a persisted DepositionRun record, or None.

    One reader, so a schema field name lives in exactly one place.
    """
    for f in _RUN_ID_FIELDS:
        v = record.get(f)
        if v not in (None, "", "None", "null"):
            return str(v)
    return None


def traceable_specimen_id(sample):
    """A persistent physical specimen identifier for this sample record, or None.

    Only fields that mean a specimen count. `source_sample_code` deliberately does not:
    it is the paper's analysis label, and several of them may denote one specimen -- which
    is precisely the distinction this function exists to keep.
    """
    for f in _SPECIMEN_ID_FIELDS:
        v = sample.get(f)
        if v not in (None, "", "None", "null"):
            # conservative normalisation: whitespace only, never case or punctuation,
            # because those can carry identity in a specimen code
            return " ".join(str(v).split())
    return None


def canonical_specimens(samples, paper_id):
    """Group Sample records by traceable specimen identity, scoped to the paper.

    A specimen code is only known to be unique within its source, so the identity key is
    (paper, code) unless the code is documented as global. Records without such a code are
    each their own unresolved specimen -- never one shared "unknown" bucket, which would
    assert that every unidentified sample is the same piece of silicon.
    """
    groups, unresolved = {}, []
    for s in samples:
        sid = s.get("sample_id")
        tid = traceable_specimen_id(s)
        if tid:
            key = "SPECIMEN::%s::%s" % (paper_id, tid)
            g = groups.setdefault(key, {"canonical_specimen_id": key, "paper_id": paper_id,
                                        "traceable_specimen_id": tid, "sample_ids": [],
                                        "source_aliases": [],
                                        "basis": SPECIMEN_FROM_TRACEABLE_ID})
            g["sample_ids"].append(sid)
            if s.get("source_sample_code") is not None:
                g["source_aliases"].append(str(s["source_sample_code"]))
        else:
            unresolved.append({"sample_id": sid, "paper_id": paper_id,
                               "source_sample_code": s.get("source_sample_code"),
                               "status": SPECIMEN_UNRESOLVED,
                               "basis": "no persistent specimen identifier on the record"})
    for g in groups.values():
        g["sample_ids"] = sorted(g["sample_ids"])
        g["source_aliases"] = sorted(set(g["source_aliases"]))
        g["n_aliases"] = len(g["source_aliases"])
    return groups, unresolved


def specimen_run_conflicts(group, samples_by_id):
    """Explicit run ids disagreeing among aliases of one specimen. Never resolved here."""
    runs = {samples_by_id[s].get("produced_by_run")
            for s in group["sample_ids"] if s in samples_by_id}
    runs = {r for r in runs if r}
    return sorted(runs) if len(runs) > 1 else []


def _unwrap(d, k):
    return d.get(k, d) if isinstance(d, dict) else d


def load_paper(base, pid):
    """Every semantic collection for one paper, unwrapped."""
    out = {}
    for name in ("experimental_cases", "samples", "deposition_runs", "measurements",
                 "simulation_runs", "result_series", "representations"):
        p = Path(base) / "papers" / pid / "semantic" / ("%s.json" % name)
        out[name] = _unwrap(json.loads(p.read_text()), name) if p.exists() else []
    return out


# --- MeasurementAct ----------------------------------------------------------------
def measurement_acts(measurements):
    """Group Measurement records into canonical observing acts.

    Only `represents_same_measurement_as` groups anything, and it is closed transitively:
    if A points at B and B at C, all three are one act. The act's id is the smallest
    member id, so the grouping is deterministic under any input ordering rather than
    depending on which record happened to be read first.

    Returns (act_id -> sorted member ids, member id -> act_id).
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            # attach the larger id under the smaller so the root is the minimum member
            lo, hi = (ra, rb) if ra < rb else (rb, ra)
            parent[hi] = lo

    for m in measurements:
        mid = m.get("measurement_id")
        if not mid:
            continue
        find(mid)
        same = m.get("represents_same_measurement_as")
        if same:
            find(same)
            union(mid, same)

    groups = defaultdict(list)
    for mid in parent:
        groups[find(mid)].append(mid)
    acts = {("ACT::%s" % root): sorted(members) for root, members in groups.items()}
    of = {m: a for a, ms in acts.items() for m in ms}
    return acts, of


def act_evidence(measurements, members):
    """Why these Measurement records are one act, quoted from the records themselves."""
    by = {m["measurement_id"]: m for m in measurements if m.get("measurement_id")}
    ev = []
    for mid in members:
        same = (by.get(mid) or {}).get("represents_same_measurement_as")
        if same:
            ev.append("%s declares represents_same_measurement_as -> %s" % (mid, same))
    return ev or ["single-member act: no same-measurement relation is recorded"]


# --- ResultSeries -> Cases ---------------------------------------------------------
def producer_case_index(measurements, simulation_runs):
    """producer id -> the full set of cases it is linked to."""
    idx = {}
    for m in measurements:
        idx[m["measurement_id"]] = sorted(set(m.get("measures_case") or []))
    for s in simulation_runs:
        sid = s.get("simulation_run_id") or s.get("id")
        if sid:
            idx[sid] = sorted(set(s.get("realises_case_ids")
                                  or s.get("measures_case") or []))
    return idx


def cases_for_result_series(series, producer_cases):
    """Every ExperimentalCase a ResultSeries belongs to. Never truncated.

    A sweep curve traverses the cases it plots, so the answer is a set. Returning one of
    them would be a different, smaller claim.
    """
    return sorted(set(producer_cases.get(series.get("produced_by"), ())))


def single_case_for_series(series, producer_cases):
    """(case_id, status). A case id ONLY when there is exactly one.

    The point is that a caller cannot accidentally receive an arbitrary member of a set.
    """
    cs = cases_for_result_series(series, producer_cases)
    if len(cs) == 1:
        return cs[0], "SINGLE_CASE"
    return None, (MULTI_CASE if cs else NO_CASE)


# --- physical realization ----------------------------------------------------------
def realizations(case, samples_by_id, sample_runs):
    """The known physical realizations of a condition case.

    A case with no samples is not a broken case; it is a case whose physical realization
    was never extracted, which is a different and honest statement.
    """
    ids = case.get("sample_ids") or []
    known = [samples_by_id[s] for s in ids if s in samples_by_id]
    return {
        "case_id": case.get("case_id"),
        "n_samples_linked": len(ids),
        "n_samples_resolved": len(known),
        "samples": [{
            "sample_id": s.get("sample_id"),
            "source_sample_code": s.get("source_sample_code"),
            "table_series": s.get("table_series"),
            "also_in_series": s.get("also_in_series") or [],
            "produced_by_run": s.get("produced_by_run"),
            "run_status": "KNOWN" if s.get("produced_by_run") else "RUN_UNRESOLVED",
            "source_references": s.get("source_references") or [],
        } for s in known],
        "physical_identity_status": ("RESOLVED" if known else "UNRESOLVED"),
        "runs_observed": sorted({s["produced_by_run"] for s in known
                                 if s.get("produced_by_run")}),
        "run_link_semantics": RUNS_OBSERVED_AMONG_CASE_REALIZATIONS,
    }


def run_members(run_record, samples):
    """Samples explicitly belonging to a run. Membership is never inferred.

    A sample whose `produced_by_run` is null is unresolved, not a member of anything; the
    run record's own declared members are honoured, and everything else must point back.
    """
    rid = persisted_run_id(run_record)
    if not rid:
        return None, []
    declared = set(run_record.get("sample_ids") or [])
    pointing = {s["sample_id"] for s in samples
                if s.get("produced_by_run") == rid and s.get("sample_id")}
    return rid, sorted(declared | pointing)


def case_run_links(case, samples_by_id):
    """Runs reachable from a case, each scoped to the sample that actually carries it.

    The hazard this replaces: a case exposing one sample's run as though every
    realization in the case had been grown in it.
    """
    out = []
    for sid in (case.get("sample_ids") or []):
        s = samples_by_id.get(sid)
        if s and s.get("produced_by_run"):
            out.append({"run_id": s["produced_by_run"], "via_sample": sid,
                        "scope": "SAMPLE", "semantics": RUNS_OBSERVED_AMONG_CASE_REALIZATIONS})
    return out


def inherited_conditions(case):
    """Case conditions offered as context for a realization, never as sample evidence."""
    return [{**c, "condition_scope": CASE_CONTEXT,
             "provenance_note": "nominal condition of the condition case; not measured on "
                                "any particular physical realization"}
            for c in (case.get("case_defining_conditions") or [])]
