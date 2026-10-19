"""P98: every pending entry (ontology/pending.csv) is decided by rule, never by hand:
  (a) used by the records of two or more papers (pilot/*.facts.csv columns and kb/*.figures.json);
  (b) Cremers 2019 defines it (CREMERS below: the section, written from knowledge of the review, confidence sure | check;
      only a 'sure' section accepts);
  (c) a species, structure or method named by a paper's experiment: a setting of an experimental run (pilot/experiments.csv, run
      ids <paper>:ent:..., never simrun or refs) or the method of an observation;
  (d) P109: a quantity that converts_to an accepted entry (target|rule|requires) is accepted with it: the transformation makes its records
      comparable with the target's;
else it stays pending. Writes ontology/pending_decisions.csv (id, kind, papers, rule applied, section, decision) and sets the
status column of pending.csv (accepted | pending) and its evidence column (P131b: paper key and element ids of the records that name the
entry, naming()). Run after a paper is added; then ontology/merge_pending.py, then ontology/export.py.

    python3 psed_v2/ontology/pending_decide.py                          # decide every pending.csv row
    python3 psed_v2/ontology/pending_decide.py --labels "b_film;k"      # P131b: first add a candidate row per free label other[<label>]

A free label (records of quantity other, label_as_printed equal up to case) becomes a candidate row by code (candidate()): id = the label
in snake case; unit = the most common unit; role model_parameter when a model record carries it, else condition; definition = the label
and the first record's statement verbatim; cq blank (no rule gives one). Its records count as
naming it by their printed label (usage()). A label whose records carry two dimensions (units.yaml) is two concepts: no row, reported."""
import csv, glob, json, pathlib, collections, re

HERE = pathlib.Path(__file__).resolve().parent
V2 = HERE.parent
CREMERS = {                                                                     # id: (Cremers 2019 section that defines it, confidence)
    "anodic_alumina_membrane": ("Sec. III, Table I (anodic aluminium oxide membranes as porous test structures)", "sure"),
    "pillarhall_1": ("Sec. III C and Table IV (lateral high-aspect-ratio structures, the PillarHall prototypes of Gao 2015)", "sure"),
    "molar_mass": ("Sec. V B (M in the Knudsen diffusion coefficient D_Kn = (d_h/3)(8RT/πM)^1/2)", "sure"),
    "molecule_diameter": ("Sec. II D (d in the mean free path λ = k_B T/(√2 π d² p))", "sure"),
    "surface_recombination": ("Sec. II E (recombination probability r of plasma radicals on the surface)", "sure"),
    "knudsen_diffusion_coefficient": ("Sec. V B (D_Kn of the diffusion-reaction models)", "sure"),
    "effective_diffusion_coefficient": ("Sec. V B (Bosanquet interpolation 1/D_eff = 1/D + 1/D_Kn)", "sure"),
    "gas_phase_diffusion_coefficient": ("Sec. V B (the molecular (bulk) diffusion coefficient D of the Bosanquet interpolation)", "sure"),
    "elam_monte_carlo": ("Sec. V A (Monte Carlo models; Elam 2003's random walk among them)", "check"),
    "reactant_number_density": ("Sec. V B writes the continuum equations in partial pressure, not number density", "check"),
    "pore_density": ("not defined; Sec. III names porous membranes by pore diameter and thickness", "check"),
    "hfo2": ("Table III lists Gordon 2003's HfO2 but defines no material", "check"),
}
PAPER_KEYS = {"10.1039_d0cp03358h": "yim20", "10.1021_acs.chemmater.2c01154": "mat22", "10.1116_6.0003182": "gre23", "10.1021_cm0303080": "ela03",
              "10.1002_cvde.200390005": "gor03", "10.1063_1.5028178": "yli18", "10.1116_1.4903941": "gao15", "10.1021_acs.jpcc.9b08176": "art19",
              "10.1039_d1cp04758b": "yim22", "10.1039_d3cp05639b": "hei24", "10.1116_6.0002993": "mat23", "10.1116_6.0002804": "zou23"}   # pilot/elements.PAPERS
EXPERIMENT_RUN = "ent"                                                          # run id <paper>:ent:...; simrun = model run, refs = cited work


def naming(rows):
    """{id: {paper key: [(record type, element ids)]}}: the records that name each row's id (any column but the text columns; P131b: an
    other[...] record whose printed label is the row's label or one of its aliases) and the imported figure values (element fig<n><panel>)."""
    ids = {r["id"] for r in rows}
    by_label = {a: r["id"] for r in rows if r.get("label") and r["id"] in FREE for a in [r["label"]] + (r.get("aliases") or "").split("|") if a}
    use = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in sorted(glob.glob(str(V2 / "pilot" / "*.facts.csv"))):
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            k = r["fact_id"].split(":")[0]
            els = [e for e in r["evidence"].split(";") if e]
            for col, v in r.items():
                if v and col not in ("statement", "evidence", "definition_note"):
                    for tok in v.replace(";", " ").replace(",", " ").replace("{", " ").replace("}", " ").replace("=", " ").split():
                        if tok in ids:
                            use[tok][k].append((r["type"], els))
            if r["quantity"] == "other" and r["label_as_printed"] in by_label:
                use[by_label[r["label_as_printed"]]][k].append((r["type"], els))
    for p in sorted(glob.glob(str(V2 / "kb" / "*.figures.json"))):
        d = json.load(open(p, encoding="utf-8"))
        for part in ("inventory", "curves", "values", "sets", "derived"):
            for x in d.get(part) or []:
                s = json.dumps(x)
                for i in ids:
                    if f'"{i}"' in s:
                        use[i][d["key"]].append(("figure", [f"fig{x.get('figure', '')}{x.get('panel', '')}"]))
    return use


def usage():
    """{id: {paper: {record types that name it}}} over the facts tables and the imported figures."""
    rows = list(csv.DictReader((HERE / "pending.csv").open(newline="", encoding="utf-8")))
    return {i: {k: {t for t, _ in v} for k, v in u.items()} for i, u in naming(rows).items()}


def evidence(uses):
    """The evidence column: '<key> <element ids>' per paper, at most 12 element ids each."""
    out = []
    for k, v in sorted(uses.items()):
        els = sorted({e for _, es in v for e in es})
        out.append(f"{k} {' '.join(els[:12])}" + (f" (+{len(els) - 12})" if len(els) > 12 else ""))
    return "; ".join(out)


def experimental():
    """{id: {paper}}: the pending species and structures set on an experimental run, and the methods of any observation."""
    ids = {r["id"]: r["kind"] for r in csv.DictReader((HERE / "pending.csv").open(newline="", encoding="utf-8"))}
    out = collections.defaultdict(set)
    for r in csv.DictReader((V2 / "pilot" / "experiments.csv").open(newline="", encoding="utf-8")):
        if r["run"].split(":")[1] != EXPERIMENT_RUN:
            continue
        for col, v in r.items():
            if col.startswith("setting:") and v:
                for tok in (col + " " + v).replace("[", " ").replace("]", " ").replace(";", " ").replace("=", " ").replace(",", " ").split():
                    if ids.get(tok) in ("species", "structure"):
                        out[tok].add(r["paper"])
    for p in glob.glob(str(V2 / "pilot" / "*.facts.csv")):
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            if r["type"] == "observation" and ids.get(r["method"]) == "method":
                out[r["method"]].add(r["fact_id"].split(":")[0])
    return out


FREE = set()                                                                    # ids of candidate rows made from a free label (candidate())


def candidate(label, rows):
    """P131b: a pending.csv row for the free label other[<label>] (equal up to case), or (None, why) when it cannot be one concept."""
    import export
    recs = []
    for p in sorted(glob.glob(str(V2 / "pilot" / "*.facts.csv"))):
        recs += [r for r in csv.DictReader(open(p, newline="", encoding="utf-8")) if r["quantity"] == "other" and r["label_as_printed"].lower() == label.lower()]
    if not recs:
        return None, "no other[...] record carries it"
    dims = {r["unit"]: export.unit_dimension(r["unit"]) for r in recs}
    if len({d or f"unit {u!r} not in units.yaml" for u, d in dims.items()}) > 1:
        return None, "two concepts: " + "; ".join(f"{r['fact_id']} {r['label_as_printed']!r} [{r['unit']}] {dims[r['unit']] or 'no dimension'}" for r in recs)
    unit = collections.Counter(r["unit"] for r in recs).most_common(1)[0][0]
    role = "model_parameter" if any(r["type"] == "model" for r in recs) else "condition"
    papers = sorted({r["fact_id"].split(":")[0] for r in recs})
    pids = {v: k for k, v in PAPER_KEYS.items()}
    printed = list(dict.fromkeys(r["label_as_printed"] for r in recs))
    return dict(id=re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_"), kind="quantity", unit=unit, role=role, **{"class": ""},
                definition=f"{printed[0]}: the free label of {len(recs)} records in {len(papers)} papers; first record ({recs[0]['fact_id']}): {recs[0]['statement']}",
                citation="; ".join(f"{r['fact_id']} ({r['evidence']})" for r in recs), cq="", paper=";".join(pids[k] for k in papers),
                records=f"{len(recs)} records", status="pending", label=printed[0], aliases="|".join(printed), converts_to=""), ""


ONTOLOGY_IDS = set(re.findall(r"(?m)^  - id: (\S+)", (HERE / "ontology.yaml").read_text(encoding="utf-8")))


def decide(labels=()):
    rows = list(csv.DictReader((HERE / "pending.csv").open(newline="", encoding="utf-8")))
    for r in rows:
        r.setdefault("evidence", "")
    FREE.update(r["id"] for r in rows if r["definition"].startswith(f"{r['label']}: the free label of "))
    stopped = []
    for lab in labels:
        row, why = candidate(lab, rows)
        if row is None:
            stopped.append((lab, why)); continue
        if any(r["id"] == row["id"] for r in rows) or row["id"] in ONTOLOGY_IDS:
            stopped.append((lab, f"id {row['id']} exists")); continue
        rows.append(dict(row, evidence="")); FREE.add(row["id"])
    uses = naming(rows)
    use = {i: {k: {t for t, _ in v} for k, v in u.items()} for i, u in uses.items()}
    exp_use = experimental()
    out = []
    for r in rows:
        u = use.get(r["id"], {})
        papers = sorted(u)
        sec, conf = CREMERS.get(r["id"], ("", ""))
        exp = bool(exp_use.get(r["id"]))
        target = (r.get("converts_to") or "").split("|")[0]
        if len(papers) >= 2:
            rule, dec = "a", "accepted"
        elif sec and conf == "sure":
            rule, dec = "b", "accepted"
        elif exp:
            rule, dec = "c", "accepted"
        elif target and (target in ONTOLOGY_IDS or any(x["id"] == target and x["status"] == "accepted" for x in rows)):
            rule, dec = "d", "accepted"
        else:
            rule, dec = "none", "pending"
        r["status"] = dec
        r["evidence"] = evidence(uses.get(r["id"], {}))
        out.append(dict(id=r["id"], kind=r["kind"], papers=" ".join(papers), rule=rule, section=sec, confidence=conf, decision=dec,
                        note="" if dec == "accepted" else ("a model-only record" if u and r["kind"] in ("species", "structure") else "one paper, no Cremers definition" if u else "no record names it")))
    with (HERE / "pending_decisions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "kind", "papers", "rule", "section", "confidence", "decision", "note"], lineterminator="\n"); w.writeheader(); w.writerows(out)
    with (HERE / "pending.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    c = collections.Counter((o["rule"], o["decision"]) for o in out)
    print(f"{len(out)} pending entries: " + ", ".join(f"rule {k[0]} -> {k[1]}: {n}" for k, n in sorted(c.items())))
    for lab, why in stopped:
        print(f"STOPPED {lab!r}: {why}")
    return out, stopped


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    decide([x for x in sys.argv[sys.argv.index("--labels") + 1].split(";") if x] if "--labels" in sys.argv else ())
