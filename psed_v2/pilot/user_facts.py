#!/usr/bin/env python3
"""The user's facts, in the facts schema with author user: claims the user makes across papers (the perspective paper's case
studies, one sentence each with links into several papers) and, later, bridges between two papers' definitions.

    python3 psed_v2/pilot/user_facts.py      # writes user.facts.csv

A user claim's quantity and x= qualifier name the forest preset that shows it (y against x); its links are the facts it rests on.
Cases 9 and 10 take the forest's leaves at writing time (forest.py), so the links are reproducible from the trees.
"""
import csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from facts import FIELDS  # noqa: E402
from forest import Forest  # noqa: E402


def row(fid, type_, statement, **kw):
    r = {k: "" for k in FIELDS}
    r.update(fact_id=fid, type=type_, statement=statement, author="user")
    for k, v in kw.items():
        if k not in FIELDS:
            raise KeyError(k)
        r[k] = ";".join(v) if isinstance(v, (list, tuple)) else str(v)
    return r


F = Forest()
c9 = F.leaves({"lumped_sticking_coefficient", "initial_sticking_coefficient"})
c10 = [l for l in F.leaves({"aspect_ratio", "coated_aspect_ratio", "equivalent_aspect_ratio"}) if l["ctx"].get("exposure") not in (None, "ambiguous")]
ROWS = [
    row("user:case9", "claim", "lumped sticking coefficients of TMA fitted in the pilot papers and the works they cite lie between 1e-3 and 2e-2 "
        "over 100-300 °C, a factor of about 4 like with like; the 0.1 of Dendooven et al. and the 0.012 simulation input are chosen "
        "values, not fits; the fitted c_H2O of 3e-4 sits an order of magnitude below c_TMA",
        quantity="lumped_sticking_coefficient", qualifiers="x=deposition_temperature", label_as_printed="Case 9: c vs T", stance="asserted", cause="deposition_temperature", effect="lumped_sticking_coefficient",
        links=[l["fid"] for l in c9], mentions="Case 9"),
    row("user:case10", "claim", "of the aspect ratios the pilot papers report with the exposure that reached them, the compacts of Greenberg "
        "et al. (7800 at 17 000 Torr s) and the aerogel they cite both lie at or above the exposure Gordon's square law asks; the "
        "10 000 channels of Yim et al. come without an exposure and cannot be placed",
        quantity="aspect_ratio", qualifiers="x=exposure", label_as_printed="Case 10: AR vs exposure", stance="asserted", cause="exposure", effect="aspect_ratio",
        links=[l["fid"] for l in c10] + [l["ctx"]["exposure"]["fact_id"] for l in c10], mentions="Case 10"),
]

if __name__ == "__main__":
    with (HERE / "user.facts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(ROWS)
    print("user.facts.csv:", len(ROWS), "rows;", {r["fact_id"]: len(r["links"].split(";")) for r in ROWS}, "links")
