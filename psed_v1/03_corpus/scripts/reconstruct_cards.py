#!/usr/bin/env python3
"""DEPRECATED — DO NOT RUN. Retained for history only; exits non-zero if invoked.

Original purpose (one-off): rebuild extracted/{sd}/card.json from process conditions
already methods-filled into output/{pid}/resolved/experiments.json, so cached cards would
survive the retirement of the gemini-2.5-flash methods-fill model.

Why it is retired:
  1. ALREADY BROKEN — PAIRS maps to SHORT pids ("admi.202000318"), but output dirs have
     used the full DOI ("10.1002_admi.202000318") since the pid unification. Every path
     it builds is missing, so it raises on the first paper.
  2. OBSOLETE — the methods-fill model works again (MODEL = gemini-flash-latest).
  3. PROVENANCE INVERSION — it derives the CARD from the KB. The card is the upstream
     source of paper-level conditions; rebuilding it from downstream experiments echoes
     whatever the KB already holds straight back into the card. Pre-fix that meant a
     collapsed temperature-window endpoint (source="methods") would be copied back into
     a card as a scalar. It never read `temperature_window_C` itself, so it did not
     perform the range->scalar coercion — but it would re-seed the result of one.

Supported rebuild path instead:
    python3 scripts/06_to_kb.py <doi> [<doi> ...]   # rebuild card.json (LLM) + resolve
    python3 scripts/06_to_kb.py --resolve-only <doi> ...   # re-ground only, no LLM
"""
import json, sys
from pathlib import Path

_DEPRECATED_MSG = """\
reconstruct_cards.py is DEPRECATED and will not run.

It rebuilds cards FROM the knowledge base, which inverts provenance (the card is the
source of paper-level conditions, not a derivative of them) and would re-seed any value
already collapsed in the KB. Its hardcoded short pids are also stale — the corpus has
used full-DOI ids since the pid unification, so all of its paths are missing.

Use the supported path:
    python3 scripts/06_to_kb.py <doi> [<doi> ...]          # rebuild card.json + resolve
    python3 scripts/06_to_kb.py --resolve-only <doi> ...   # re-ground only (no LLM)
"""

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"
OUT = ROOT.parent / "02_extraction" / "output"

# doi-dir  ->  short output pid
PAIRS = {
    "10.1002_admi.202000318": "admi.202000318",
    "10.1016_j.mee.2018.01.027": "j.mee.2018.01.027",
    "10.1039_c5tc03561a": "c5tc03561a",
    "10.1039_d3ra05217f": "d3ra05217f",
    "10.1116_6.0002804": "6.0002804",
    "10.3762_bjnano.5.25": "bjnano.5.25",
}
Q2CARD = {"temperature": "temperature_C", "total_pressure": "pressure_Pa",
          "cycle_number": "ncycles", "purge_time": "purge_time_s"}


def main():
    for sd, pid in PAIRS.items():
        scout = json.loads((EXTRACTED / sd / "scout.json").read_text())
        exps = json.loads((OUT / pid / "resolved" / "experiments.json").read_text())
        e0 = exps[0] if exps else {}
        card = {"precursors": scout.get("precursors") or [],
                "coreactants": scout.get("coreactants") or [],
                "process_type": e0.get("process_type") or scout.get("process_type") or "unknown",
                "temperature_C": None, "pressure_Pa": None, "pulse_time_s": None,
                "purge_time_s": None, "ncycles": None,
                "carrier_gas": (e0.get("carrier_gas") or {}).get("species") if e0.get("carrier_gas") else None}
        pulse = {}
        for c in e0.get("controlled", []):
            if c.get("source") != "methods":
                continue
            q = c["quantity"]
            if q in Q2CARD:
                card[Q2CARD[q]] = c["value"]
            elif q == "pulse_time":
                pulse["precursor" if c.get("of_reactant") == "A" else "coreactant"] = c["value"]
        if pulse:
            card["pulse_time_s"] = pulse
        (EXTRACTED / sd / "card.json").write_text(json.dumps(card, indent=1))
        print(f"[reconstruct] {pid:20} card={ {k:v for k,v in card.items() if v not in (None,[],{})} }")


if __name__ == "__main__":
    sys.stderr.write(_DEPRECATED_MSG)
    sys.exit(2)
