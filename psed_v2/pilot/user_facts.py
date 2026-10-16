#!/usr/bin/env python3
"""The user's facts, in the facts schema with author user: claims the user makes across papers (the perspective paper's case
studies, one sentence each with links into several papers), the user's own definitions, and bridges between two definitions
(type bridge: links = the two definition facts, statement = the transform in words, value_text = the factor that turns a value of
the second definition into the first as a quotient of quantity ids, evidence = the justifying element, paper-qualified).

    python3 psed_v2/pilot/user_facts.py      # writes user.facts.csv

A user claim's quantity and x= qualifier name the forest preset that shows it (y against x); its links are the facts it rests on.
Cases 9 and 10 take the forest's leaves at writing time (forest.py), so the links are reproducible from the trees.
Assumed facts (type setting, data_kind assumed): constants and model values a derived quantity needs that no paper states as a
setting (a molar mass, a bulk density, Avogadro's and Boltzmann's constants, a model input standing in for a pressure, the number of
compacts per run, a molecular diameter taken from an analogue); links name the paper fact or entities they stand in for, and
every derived value computed from one says so (questions.derive). An assumed fact serves only the papers its links name; a
constant without links (N_A, k_B) serves all.
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
    row("user:assume_M_ZnO", "setting", "molar mass of ZnO, 81.38 g/mol (standard atomic weights), an assumed input to derived quantities of gre23",
        quantity="other", qualifiers="species=ZnO", label_as_printed="molar mass", value="81.38", unit="g/mol", data_kind="assumed", links=["gre23:abs.g1#3"]),
    row("user:assume_M_MoS2", "setting", "molar mass of MoS2, 160.07 g/mol (standard atomic weights), an assumed input to derived quantities of mat22",
        quantity="other", qualifiers="species=MoS2", label_as_printed="molar mass", value="160.07", unit="g/mol", data_kind="assumed", links=["mat22:abs.g1#3"]),
    row("user:assume_rho_ZnO", "setting", "the density of gre23's ZnO coating is taken as that of bulk zincite, 5.61 g/cm3; the paper gives no coating density",
        quantity="film_density", qualifiers="species=ZnO", value="5.61", unit="g/cm3", data_kind="assumed", links=["gre23:abs.g1#3"]),
    row("user:assume_M_Al2O3", "setting", "molar mass of Al2O3, 101.96 g/mol (standard atomic weights), an assumed input to derived quantities of yim20",
        quantity="other", qualifiers="species=Al2O3", label_as_printed="molar mass", value="101.96", unit="g/mol", data_kind="assumed", links=["yim20:s6.p1#13"]),
    row("user:assume_rho_Al2O3", "setting", "the density of yim20's Al2O3 films is taken as 3.1 g/cm3, the value its model uses (from its ref. 51); no film density is measured",
        quantity="film_density", qualifiers="species=Al2O3", value="3.1", unit="g/cm3", data_kind="assumed", links=["yim20:fig10.cap#16"]),
    row("user:assume_N_A", "setting", "Avogadro constant 6.02214076e23 per mole", quantity="other", label_as_printed="Avogadro constant", value="6.02214076e23",
        unit="1/mol", data_kind="assumed"),
    row("user:assume_k_B", "setting", "Boltzmann constant 1.380649e-23 J/K", quantity="other", label_as_printed="Boltzmann constant", value="1.380649e-23",
        unit="J/K", data_kind="assumed"),
    row("user:assume_p_TMA", "setting", "the TMA partial pressure during a pulse in yim20 is taken as the Fig. 10 model input, 65 Pa; the paper states no measured value",
        quantity="partial_pressure", qualifiers="species=TMA;step=reactant_A", value="65", unit="Pa", data_kind="assumed", links=["yim20:fig10.cap#3"]),
    row("user:assume_npc_per_run", "setting", "two NPCs per ALD run in gre23, the pair weighed together, assumed for the mass balance",
        quantity="other", label_as_printed="NPCs per run", value="2", data_kind="assumed", links=["gre23:ent:120:pair", "gre23:ent:160:pair", "gre23:ent:120_160:pair"]),
    row("user:assume_d_DEZ", "setting", "the molecular diameter of DEZ is taken as that of TMA, 591 pm (yim20's model input from its ref. 33), for a mean free path in gre23",
        quantity="other", qualifiers="species=DEZ", label_as_printed="molecular diameter", value="0.591", unit="nm", data_kind="assumed", links=["yim20:fig10.cap#7", "gre23:abs.g1#3"]),
    row("user:def_xd", "definition", "dimensionless depth of a pore: the depth over the pore diameter d, the rule Cremers 2019 applies to pores",
        quantity="dimensionless_distance", qualifiers="by=d", mentions="Cremers 2019"),
    row("user:bridge_xH_xd", "bridge", "x~ by H (a channel's height, yim20) and x~ by d (a pore's diameter) measure the same depth: "
        "x~_H = x~_d * d / H, so a pore value times d over H compares with a channel value", quantity="dimensionless_distance",
        links=["yim20:s3.p3#2", "user:def_xd"], value_text="feature_width/feature_height", evidence="yim20:s3.p3", mentions="x~"),
]

if __name__ == "__main__":
    with (HERE / "user.facts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(ROWS)
    print("user.facts.csv:", len(ROWS), "rows;", {r["fact_id"]: len(r["links"].split(";")) for r in ROWS}, "links")
