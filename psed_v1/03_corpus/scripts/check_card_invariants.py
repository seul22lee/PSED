#!/usr/bin/env python3
"""Corpus-level invariant: a non-degenerate temperature WINDOW must never be promoted
to the paper-level scalar `temperature_C` via the scout path.

  python3 scripts/check_card_invariants.py        # exit 1 on violation

Two levels, because the card schema has no per-field provenance:

  HARD (exact, provenance-free) — replay base_card(scout) for every paper and assert the
      SCOUT path contributes no scalar when the window is non-degenerate. This tests the
      code path directly rather than inferring intent from the merged result, so it is
      exact and cannot false-positive. This is the invariant that actually encodes
      "no endpoint promoted from the scout/window path".

  ADVISORY (heuristic) — on the FINAL merged card, report any paper whose temperature_C
      equals an endpoint of its non-degenerate window. After the fix such a value can
      only have come from the independent methods/table extraction, which is LEGITIMATE
      (a paper may state a window AND a specific growth temperature that happens to sit
      at an endpoint). It is therefore reported, never failed.

  LIMITATION: with the current schema we cannot prove the source of a merged scalar.
      An explicit per-field provenance/status (e.g. {"temperature_C": "varied_across_samples"}
      or {"temperature_C": {"source": "methods"}}) would let the advisory check become
      exact. Documented, not implemented.
"""
import importlib.util as u
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACTED = HERE.parents[2] / "papers"   # papers/<doi>/extracted/

spec = u.spec_from_file_location("kb6", HERE / "06_to_kb.py")
kb6 = u.module_from_spec(spec)
spec.loader.exec_module(kb6)


def _is_window(w):
    return (isinstance(w, (list, tuple)) and len(w) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in w)
            and float(w[0]) != float(w[1]))


def main():
    hard_violations, advisories, checked = [], [], 0
    for d in sorted(p for p in (d / "extracted" for d in EXTRACTED.iterdir() if d.is_dir()) if p.is_dir()):
        sp, cp = d / "scout.json", d / "card.json"
        if not sp.exists():
            continue
        scout = json.loads(sp.read_text())
        window = scout.get("temperature_window_C")
        if not _is_window(window):
            continue
        checked += 1

        # HARD: the scout path itself must yield no scalar for a real window
        scout_scalar = kb6.base_card(scout).get("temperature_C")
        if scout_scalar is not None:
            hard_violations.append((d.parent.name, window, scout_scalar))

        # ADVISORY: merged card sits on an endpoint (legitimate only if independently stated)
        if cp.exists():
            t = json.loads(cp.read_text()).get("temperature_C")
            if t is not None and float(t) in (float(window[0]), float(window[1])):
                advisories.append((d.parent.name, window, t))

    print(f"papers with a non-degenerate temperature window: {checked}")

    print("\nHARD — scout path must not promote an endpoint:")
    if hard_violations:
        for name, w, v in hard_violations:
            print(f"  VIOLATION {name}: window {w} -> scout scalar {v}")
    else:
        print("  PASS — no window endpoint promoted from the scout path")

    print("\nADVISORY — merged temperature_C equals a window endpoint:")
    if advisories:
        for name, w, v in advisories:
            print(f"  REVIEW {name}: window {w}, temperature_C={v} "
                  f"(legitimate only if the methods/tables state it independently)")
    else:
        print("  none")

    if hard_violations:
        print(f"\nFAILED: {len(hard_violations)} hard violation(s)")
        return 1
    print("\nINVARIANT HOLDS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
