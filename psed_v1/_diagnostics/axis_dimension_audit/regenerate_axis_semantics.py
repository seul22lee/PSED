#!/usr/bin/env python3
"""Re-run ONLY the production axis-resolution step over the frozen active-8 snapshots.

The pilot consumes a frozen `resolved/entities.json` per paper rather than re-running
production (which needs an LLM for the methods card). To see an axis-resolver change in
the pilot's output, that one step has to be replayed over the snapshot.

The step is replayed exactly as `to_kb.to_experiments()` performs it: the record's raw
axis quantity is prepared through `_axis_canon` and handed to `axis_roles.resolve_axis`
together with the record's own label and unit.

Provenance is the whole difficulty. An earlier version of this script rebuilt the raw
quantities with a lookup keyed on the axis LABEL, and labels repeat: "Temperature (deg C)"
is a deposition temperature on one figure and a measurement temperature on another, and
"E vs. Ag/AgCl / V" appears on four panels carrying two different raw quantities. Keying
on the label collapsed those records onto one reading and moved 20 case fingerprints in a
paper the repair does not even touch. The key is therefore the record's own identity --
printed figure, panel, axis -- never its text.

Reads the frozen baseline from git so the result depends only on (baseline, resolver) and
re-running cannot accumulate drift.

    python3 _diagnostics/axis_dimension_audit/regenerate_axis_semantics.py [--check]
"""
import json
import subprocess
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[2]           # psed_v1/
sys.path.insert(0, str(W))

from ontology import vocab as lib                                  # noqa: E402
from pipeline.canonical import axis_roles as caxis                 # noqa: E402
from pipeline.resolve.to_kb import _axis_canon                     # noqa: E402

PILOT = W / "_diagnostics" / "semantic_pilot_9papers"
BASELINE = "4c65b52"
REL = "psed_v1/_diagnostics/semantic_pilot_9papers/papers/%s/resolved/entities.json"


def _canon(label):
    return lib.resolve_axis_label(label) or lib.canon_quantity(label)


def raw_axis_index(pid):
    """(printed_figure, panel, axis) -> raw quantity, as extraction wrote it.

    Keyed on record identity. Two panels may print the same label and mean different
    quantities; that is exactly what this index must not lose.
    """
    idx, fd = {}, PILOT / "papers" / pid / "extracted" / "figure_data.json"
    if not fd.exists():
        return idx
    for fig in json.loads(fd.read_text()).get("figures") or []:
        for pan in fig.get("panels") or []:
            for axis in ("x", "y"):
                a = pan.get(axis) or {}
                if a.get("label_raw"):
                    idx[(str(fig.get("printed_figure")), str(pan.get("panel")), axis)] = \
                        a.get("quantity")
    return idx


def frozen_entities(pid):
    r = subprocess.run(["git", "show", "%s:%s" % (BASELINE, REL % pid)],
                       capture_output=True, text=True, cwd=str(W.parent))
    return json.loads(r.stdout) if r.returncode == 0 else None


def regenerate(pid, check=False):
    base = frozen_entities(pid)
    if base is None:
        return 0, []
    idx = raw_axis_index(pid)
    changed = []
    for e in base:
        key0 = (str(e.get("printed_figure_number")), str(e.get("panel") or ""))
        for field, target in (("x_semantics", "coordinate"), ("y_semantics", "measurand")):
            sem = e.get(field)
            if not isinstance(sem, dict):
                continue
            axis = field[0]
            # record identity first; the snapshot's own raw_quantity is the fallback, and
            # it is already post-canonicalisation, so it is only used when extraction has
            # no record for this axis at all
            raw = idx.get(key0 + (axis,), sem.get("raw_quantity"))
            res = caxis.resolve_axis(raw_label=sem.get("raw_label"),
                                     raw_quantity=_axis_canon(raw),
                                     unit=sem.get("unit"), caption="", context="",
                                     other_axis_label=None, canon=_canon)
            new, old = res.get("canonical_quantity"), sem.get("canonical_quantity")
            e[field] = dict(sem, canonical_quantity=new,
                            semantic_status=res.get("semantic_status"),
                            axis_role=res.get("axis_role"), evidence=res.get("evidence"))
            if new == old:
                continue
            changed.append((e["entity_id"], axis, sem.get("raw_label"), old, new))
            fallback = new or raw
            if target == "coordinate":
                if e.get("coordinate") == old:
                    e["coordinate"] = fallback
            else:
                md = e.get("measurand")
                if isinstance(md, dict) and md.get("quantity") == old:
                    e["measurand"] = dict(md, quantity=fallback)
                elif isinstance(md, str) and md == old:
                    e["measurand"] = fallback
    if not check:
        (PILOT / "papers" / pid / "resolved" / "entities.json").write_text(
            json.dumps(base, indent=1))
    return len(changed), changed


def main():
    check = "--check" in sys.argv
    papers = json.loads((PILOT / "pilot_papers.json").read_text())["papers"]
    total = 0
    for pid in papers:
        n, ch = regenerate(pid, check)
        total += n
        if n:
            print("  %-32s %d axes re-resolved" % (pid[:32], n))
            for eid, ax, lab, old, new in ch:
                print("      %-34s %s %-26r %-22r -> %r"
                      % (eid[-34:], ax, str(lab)[:26], old, new))
    print("  total: %d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
