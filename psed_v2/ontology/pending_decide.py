"""P98: every pending entry (ontology/pending.csv) is decided by rule, never by hand:
  (a) used by the records of two or more papers (pilot/*.facts.csv columns and kb/*.figures.json);
  (b) Cremers 2019 defines it (CREMERS below: the section, written from knowledge of the review, confidence sure | check;
      only a 'sure' section accepts);
  (c) a species, structure or method named by a paper's experiment: a setting of an experimental run (pilot/experiments.csv, run
      ids <paper>:ent:..., never simrun or refs) or the method of an observation;
  (d) P109: a quantity that converts_to an accepted entry (target|rule|requires) is accepted with it: the transformation makes its records
      comparable with the target's;
else it stays pending. Writes ontology/pending_decisions.csv (id, kind, papers, rule applied, section, decision) and sets the
status column of pending.csv (accepted | pending). Run after a paper is added; then ontology/export.py."""
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
EXPERIMENT_RUN = "ent"                                                          # run id <paper>:ent:...; simrun = model run, refs = cited work


def usage():
    """{id: {paper: {record types that name it}}} over the facts tables and the imported figures."""
    ids = [r["id"] for r in csv.DictReader((HERE / "pending.csv").open(newline="", encoding="utf-8"))]
    use = collections.defaultdict(lambda: collections.defaultdict(set))
    for p in glob.glob(str(V2 / "pilot" / "*.facts.csv")):
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            k = r["fact_id"].split(":")[0]
            for col, v in r.items():
                if v and col not in ("statement", "evidence", "definition_note"):
                    for tok in v.replace(";", " ").replace(",", " ").replace("{", " ").replace("}", " ").replace("=", " ").split():
                        if tok in ids:
                            use[tok][k].add(r["type"])
    for p in glob.glob(str(V2 / "kb" / "*.figures.json")):
        d = json.load(open(p, encoding="utf-8"))
        s = json.dumps(d)
        for i in ids:
            if f'"{i}"' in s:
                use[i][d["key"]].add("figure")
    return use


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


ONTOLOGY_IDS = set(re.findall(r"(?m)^  - id: (\S+)", (HERE / "ontology.yaml").read_text(encoding="utf-8")))


def decide():
    rows = list(csv.DictReader((HERE / "pending.csv").open(newline="", encoding="utf-8")))
    use = usage()
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
        out.append(dict(id=r["id"], kind=r["kind"], papers=" ".join(papers), rule=rule, section=sec, confidence=conf, decision=dec,
                        note="" if dec == "accepted" else ("a model-only record" if u and r["kind"] in ("species", "structure") else "one paper, no Cremers definition" if u else "no record names it")))
    with (HERE / "pending_decisions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "kind", "papers", "rule", "section", "confidence", "decision", "note"], lineterminator="\n"); w.writeheader(); w.writerows(out)
    with (HERE / "pending.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    c = collections.Counter((o["rule"], o["decision"]) for o in out)
    print(f"{len(out)} pending entries: " + ", ".join(f"rule {k[0]} -> {k[1]}: {n}" for k, n in sorted(c.items())))
    return out


if __name__ == "__main__":
    decide()
