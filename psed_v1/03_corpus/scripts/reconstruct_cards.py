#!/usr/bin/env python3
"""One-off: rebuild extracted/{sd}/card.json from the process conditions already
methods-filled into output/{pid}/resolved/experiments.json in a prior session, so the
now-cached card survives the retirement of the methods-fill LLM model — deterministic,
no LLM. After this, `06_to_kb.py --resolve-only` re-grounds against the ontology for free.
"""
import json, sys
from pathlib import Path

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
    main()
