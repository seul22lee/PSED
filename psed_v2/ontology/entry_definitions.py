#!/usr/bin/env python3
"""P131b-12c: the user's names, definitions and categories for the five entries made from free labels (Directive 12c; content copied
verbatim from the directive, categories as the user chose them in the chat: p_d and b_film surface_kinetics, wall_temperature
deposition_run, base_pressure ald_reactor, wavelength_range measurement). Sets name, definition, definition_source (paper | user) and
category; removes definition_status and category_status. A definition_source: paper entry quotes its element: the quote must occur in the
element text (elements.texts(), LaTeX wrapper removed: $, \\text{..}, _{..}) or the script stops before writing; the element id and the quote
go into evidence. base_pressure's evidence and citation are rebuilt from the records keyed to it (12c: ela03:s3.p26#3 is other[evacuated below]).

    python3 psed_v2/ontology/entry_definitions.py
"""
import csv, glob, re, sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "kb" / "pilot"))
sys.path.insert(0, str(HERE))
import elements      # noqa: E402
from alias_audit import set_field  # noqa: E402

PID = {v: k for k, v in elements.PAPERS.items()}
ENTRIES = {
    "b_film": dict(name="metal atoms per film formula unit", definition="b_film is the number of metal atoms in the formula unit of the deposited film",
                   source="paper", category="surface_kinetics", quotes=[("yli18", "s5.p18", "b_film is the number of metal atoms in the formula unit of the deposited film")]),
    "p_d": dict(name="desorption probability (per unit time)", definition="desorption probability, P_d", source="paper", category="surface_kinetics",
                quotes=[("yim22", "fig4.cap", "desorption probability, P_d")], extra=("yli18", "P_d", "desorption")),
    "wall_temperature": dict(name="reactor wall temperature", source="user", category="deposition_run",
                             definition="temperature at which the reactor or chamber walls are held during deposition, as distinct from the substrate or table temperature"),
    "base_pressure": dict(name="reactor base pressure", source="user", category="ald_reactor",
                          definition="lowest pressure the pumped reactor reaches with no gas flowing (ultimate vacuum), stated before deposition"),
    "wavelength_range": dict(name="measurement wavelength range", source="user", category="measurement",
                             definition="wavelength interval covered by an optical measurement (reflectometry, transmittance)"),
}


def delatex(t):
    t = re.sub(r"\\text\{([^}]*)\}", r"\1", t)
    t = re.sub(r"_\{([^}]*)\}", r"_\1", t)
    return " ".join(t.replace("$", "").split())


def scalar(text, eid, field, value):
    """Set a one-line scalar field (set_field writes flow lists; a scalar is dumped as its own mapping line)."""
    line = yaml.safe_dump({field: value}, allow_unicode=True, width=100000).strip()
    marker = "__SCALAR__"
    text = set_field(text, eid, field, [marker])
    return text.replace(f"    {field}: [{marker}]", "    " + line, 1)


def drop(text, eid, field):
    head, rest = text.split("\nentries:\n", 1)
    body, tail = rest.split("\nfamilies:", 1)
    blocks = re.split(r"(?m)^(?=  - id: )", body)
    i = next(k for k, b in enumerate(blocks) if re.match(rf"  - id: {re.escape(eid)}\n", b))
    blocks[i] = re.sub(rf"(?m)^    {field}:.*\n", "", blocks[i])
    return head + "\nentries:\n" + "".join(blocks) + "\nfamilies:" + tail


def main():
    texts = {}
    tx = lambda key: texts.setdefault(key, elements.texts(PID[key]))
    text = (HERE / "ontology.yaml").read_text(encoding="utf-8")
    onto = yaml.safe_load(text)
    by = {e["id"]: e for e in onto["entries"]}
    plan = {}
    for eid, d in ENTRIES.items():
        ev = [x for x in by[eid].get("evidence", []) if not x.startswith("quote ")]
        for key, el, q in d.get("quotes", []):
            src = tx(key).get(el, "")
            if q not in delatex(src):
                print(f"STOPPED {eid}: {q!r} is not in {key} {el}"); return 1
            ev.append(f"quote {key} {el}: {q}")
        if d.get("extra"):                                                      # p_d: a sentence of yli18 with P_d and 'desorption', verbatim
            key, sym, word = d["extra"]
            for el, t in tx(key).items():
                for sent in re.split(r"(?<=[.;])\s+", t):
                    if sym in sent and word in sent.lower():
                        ev.append(f"quote {key} {el}: {' '.join(sent.split())}")
        plan[eid] = ev
    recs = []                                                                   # base_pressure: the records keyed to it now
    for p in sorted(glob.glob(str(V2 / "kb" / "pilot" / "10.*.facts.csv"))):
        recs += [r for r in csv.DictReader(open(p, newline="", encoding="utf-8")) if r["quantity"] == "base_pressure"]
    byp = {}
    for r in recs:
        byp.setdefault(r["fact_id"].split(":")[0], set()).update(x for x in r["evidence"].split(";") if x)
    plan["base_pressure"] = [f"{k} {' '.join(sorted(v))}" for k, v in sorted(byp.items())] + [x for x in plan["base_pressure"] if x.startswith("alias ")]
    for eid, d in ENTRIES.items():
        text = scalar(text, eid, "name", d["name"])
        text = scalar(text, eid, "category", d["category"])
        text = scalar(text, eid, "definition", d["definition"])
        text = drop(text, eid, "definition_status")
        text = drop(text, eid, "category_status")
        text = drop(text, eid, "definition_source")
        text = scalar(text, eid, "definition_source", d["source"])
        text = set_field(text, eid, "evidence", plan[eid])
        if eid == "base_pressure":
            text = scalar(text, eid, "citation", "; ".join(f"{r['fact_id']} ({r['evidence']})" for r in recs))
        print(f"{eid}: name {d['name']!r}, category {d['category']}, source {d['source']}; evidence {plan[eid]}")
    yaml.safe_load(text)
    (HERE / "ontology.yaml").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
