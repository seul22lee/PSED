#!/usr/bin/env python3
"""The axis record trust boundary, and the regeneration harness that mirrors it.

Two things are pinned here, both about PROVENANCE rather than physics.

`_axis_canon` is the axis-only gate in to_kb: extraction transcribes what an axis printed,
so a record may hold nothing but "j". Canonicalising that on the way in turns a one-letter
transcription into a strong claim -- collision_flux, a molecular impingement flux -- before
the resolver has seen the label, the unit or the sibling evidence, and the resolver then
cannot tell a real reading from a guess. A bare symbol is therefore passed through
untouched; anything naming a quantity outright is canonicalised as before.

The regeneration harness replays that same step over the frozen snapshots, so it has to
reconstruct each record's raw axis quantity. Keying that reconstruction on the axis LABEL
collapsed records -- "Temperature (deg C)" is a deposition temperature on one figure and a
measurement temperature on another -- and moved 20 case fingerprints in a paper the repair
never touched. The key is record identity, and within a panel a curve read against its own
axis keeps its own semantics, exactly as production's `_axis_labels` does.

Run:  python3 tests/test_axis_record_canon.py
"""
import importlib.util
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W))

from ontology import vocab as lib                                  # noqa: E402
from pipeline.resolve.to_kb import _axis_canon                     # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "regen", W / "_diagnostics" / "axis_dimension_audit" / "regenerate_axis_semantics.py")
regen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(regen)

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def main():
    print("=== A. bare ontology symbols are preserved, not promoted ===")
    for sym in ("j", "E", "C", "q"):
        got = _axis_canon(sym)
        ok("A: _axis_canon(%-3r) keeps the raw symbol" % sym, got == sym, got)
        # each of these DOES canonicalise through the global lookup -- that is the point
        ok("A: %-3r would otherwise canonicalise to %-22r"
           % (sym, lib.canon_quantity(sym)), lib.canon_quantity(sym) is not None)

    print("=== B. strong semantics canonicalise normally ===")
    for raw, want in (("current_density", "current_density"),
                      ("Current density", "current_density"),
                      ("film_thickness", "film_thickness"),
                      ("intensity", "intensity"),
                      ("thickness_per_cycle", "thickness_per_cycle")):
        got = _axis_canon(raw)
        ok("B: _axis_canon(%-22r) -> %s" % (raw, want), got == want, got)

    print("=== C. benign inputs are untouched ===")
    ok("C: None survives", _axis_canon(None) is None)
    ok("C: empty string survives", _axis_canon("") == "")
    ok("C: junk that names no quantity is returned verbatim",
       _axis_canon("some_unknown_token") == "some_unknown_token")
    ok("C: junk is not promoted to any quantity",
       lib.canon_quantity("some_unknown_token") is None)

    print("=== D. the harness keys on record identity, never on label text ===")
    fig = {"printed_figure": "3", "panels": [{"panel": "a",
           "x": {"label_raw": "Temperature (°C)", "quantity": "deposition_temperature"},
           "y": {"label_raw": "GPC (Å)", "quantity": "growth_per_cycle"}, "series": []}]}
    fig2 = {"printed_figure": "9", "panels": [{"panel": "a",
            "x": {"label_raw": "Temperature (°C)", "quantity": "temperature"},
            "y": {"label_raw": "GPC (Å)", "quantity": "growth_per_cycle"}, "series": []}]}
    idx = regen.build_index({"figures": [fig, fig2]})
    ok("D: one repeated label, two figures, two distinct quantities",
       idx.get(("3", "a", "x")) == "deposition_temperature"
       and idx.get(("9", "a", "x")) == "temperature", idx)
    ok("D: nothing is keyed by the label itself",
       not any("Temperature" in str(k) for k in idx), sorted(idx)[:3])

    print("=== E. a series that owns its own axis keeps its own semantics ===")
    # same figure, same panel, same axis direction -- two curves, one reading against a
    # secondary y axis. A (figure, panel, axis) key alone would collapse these.
    panel = {"panel": "a",
             "x": {"label_raw": "Temperature (°C)", "quantity": "deposition_temperature"},
             "y": {"label_raw": "GPC (Å)", "quantity": "growth_per_cycle"},
             "series": [{"label": "GPC", "points": [[1, 2]]},
                        {"label": "Theta", "points": [[1, 2]],
                         "y": {"label_raw": "Θ_c (°)", "quantity": "critical_angle"}}]}
    idx = regen.build_index({"figures": [{"printed_figure": "5", "panels": [panel]}]})
    ok("E: the panel axis is still recorded",
       idx.get(("5", "a", "y")) == "growth_per_cycle", idx)
    ok("E: the series-owned axis gets its own entry",
       idx.get(("5", "a", "theta", "y")) == "critical_angle", idx)
    ok("E: the sharing series gets NO private entry",
       ("5", "a", "gpc", "y") not in idx, sorted(idx))
    ok("E: a pure (figure, panel, axis) key would have collapsed them",
       idx[("5", "a", "y")] != idx[("5", "a", "theta", "y")])

    print("=== F. a genuinely shared panel axis stays shared ===")
    shared = {"panel": "b",
              "x": {"label_raw": "Cycles", "quantity": "cycle_number"},
              "y": {"label_raw": "Thickness (nm)", "quantity": "film_thickness"},
              "series": [{"label": "A", "points": [[1, 2]]},
                         {"label": "B", "points": [[1, 2]]}]}
    idx = regen.build_index({"figures": [{"printed_figure": "6", "panels": [shared]}]})
    ok("F: no per-series entries are invented",
       not [k for k in idx if len(k) == 4], sorted(idx))
    ok("F: the shared axis resolves once",
       idx.get(("6", "b", "y")) == "film_thickness", idx)

    print("=== G. genericity ===")
    # EXECUTABLE code only: the docstring deliberately quotes the motivating labels,
    # which is documentation, not dispatch.
    import io
    import re
    import tokenize
    src = (W / "_diagnostics" / "axis_dimension_audit"
           / "regenerate_axis_semantics.py").read_text()
    code = "".join("" if t.type in (tokenize.COMMENT, tokenize.STRING) else t.string
                   for t in tokenize.generate_tokens(io.StringIO(src).readline))
    ok("G: the harness names no DOI", not re.search(r"10\.\d{4}[_/]", code))
    for lit in ("Ag/AgCl", "Temperature", "collision_flux", "current_density"):
        ok("G: no %-18r in executable harness code" % lit, lit not in code)
    ok("G: the docstring may still explain the defect", "Temperature" in src)

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
