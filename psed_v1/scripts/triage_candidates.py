#!/usr/bin/env python3
"""
scripts/triage_candidates.py — document-level triage of the candidate pool.

    python3 scripts/triage_candidates.py

Reads the candidate Docling output written by scripts/parse_candidates.py and the
LIVE corpus, and writes reports/candidate_corpus_expansion.json — one record per
candidate. Rendering is a separate step: corpus_status.py reads this JSON, so the
HTML is never the source of the analysis.

Everything here is deterministic and local: no LLM, no network. Materials come from
the ontology vocabulary plus a formula pattern; study type, process, geometry and
expected data types come from keyword evidence in the title, abstract and the
figure/table captions Docling already extracted. Every classification stores the
sentence it came from, so a wrong call is auditable rather than opaque.

These are TRIAGE estimates, not Scout or figure-extraction results.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                          # noqa: E402
from pipeline.scout.scout import abstract_of               # noqa: E402  (no API at import)

CANDIDATES = P.REPO / "corpus" / "acquisition" / "candidates"
OUT = P.REPORTS / "candidate_corpus_expansion.json"

ONTO = json.loads(P.ONTOLOGY_JSON.read_text())
ONTO_MATERIALS = [m["id"] for m in ONTO["individuals"]["materials"]]
ONTO_PRECURSORS = [p["id"] for p in ONTO["individuals"]["precursors"]]
ONTO_COREACTANTS = [c["id"] for c in ONTO["individuals"]["coreactants"]]

#: a stoichiometric inorganic formula: Al2O3, MoS2, HfO2, ZnO, TiN, MoOx, Bi2Te3
_FORMULA = re.compile(r"\b((?:[A-Z][a-z]?\d{0,2}){2,4}[xy]?)\b")
_ELEMENT = re.compile(r"[A-Z][a-z]?")
#: words that mark a formula as the DEPOSITED film rather than an incidental mention
_DEPOSIT_CUE = re.compile(
    r"\b(deposit|deposition|grown|growth|film|films|coating|coated|layer|layers|"
    r"ALD of|atomic layer deposition of|thin[- ]film)\b", re.I)

PROCESS_CUES = [
    ("plasma_ALD", r"\b(plasma[- ]enhanced|PEALD|plasma ALD|remote plasma|O2 plasma|"
                   r"N2 plasma|H2 plasma)\b"),
    ("spatial_ALD", r"\b(spatial ALD|spatial atomic layer)\b"),
    ("ALE", r"\b(atomic layer etch|ALE\b)"),
    ("thermal_ALD", r"\b(thermal ALD|thermal atomic layer deposition)\b"),
    ("ALD", r"\b(atomic layer deposition|\bALD\b)"),
    ("CVD", r"\b(chemical vapou?r deposition|\bCVD\b)"),
]
STUDY_CUES = [
    ("review", r"\b(this review|we review|review article|overview of the literature|"
               r"in this review)\b"),
    ("simulation", r"\b(monte carlo|simulation|simulated|computational model|"
                   r"density functional|DFT|first[- ]principles|finite element|"
                   r"reaction[- ]diffusion model)\b"),
    ("experimental", r"\b(we deposit|were deposited|was deposited|measured|"
                     r"experiments? were|samples were|we grew|were grown|"
                     r"characteri[sz]ed)\b"),
]
GEOMETRY_CUES = [
    ("HAR/trench/via", r"\b(high[- ]aspect[- ]ratio|aspect ratio|trench|via|"
                       r"lateral high aspect|LHAR|deep hole|nanoscale hole)\b"),
    ("porous", r"\b(porous|mesoporous|aerogel|anodic alumina|AAO|membrane)\b"),
    ("particles", r"\b(nanoparticle|particles|powder|fluidi[sz]ed)\b"),
    ("nanostructure", r"\b(nanowire|nanotube|nanorod|nanostructure|CNT|fiber|fibre)\b"),
    ("reactor", r"\b(reactor|cross[- ]flow|showerhead|viscous flow)\b"),
    ("planar", r"\b(planar|flat substrate|Si\(100\)|silicon wafer|blanket)\b"),
]
#: quantitative data signals, matched against captions + abstract
DATA_CUES = [
    ("growth_per_cycle", r"\b(growth per cycle|GPC|growth rate|A/cycle|Å/cycle|nm/cycle)\b"),
    ("thickness_vs_cycles", r"\b(thickness (?:vs\.?|versus|as a function of) .{0,20}cycles|"
                            r"number of (?:ALD )?cycles)\b"),
    ("saturation_dose", r"\b(saturat|dose|exposure time|pulse (?:time|length)|precursor dose)\b"),
    ("purge_dependence", r"\b(purge (?:time|dependence))\b"),
    ("temperature_window", r"\b(ALD window|temperature window|(?:vs\.?|versus|as a function of) "
                           r".{0,20}temperature|deposition temperature)\b"),
    ("conformality_profile", r"\b(conformal|step coverage|penetration depth|penetration profile|"
                             r"thickness profile|coverage profile)\b"),
    ("composition", r"\b(XPS|composition|stoichiometr|atomic (?:%|percent)|RBS|EDS|impurit)\b"),
    ("density", r"\b(density|XRR|x-ray reflectivit)\b"),
    ("roughness", r"\b(roughness|RMS|AFM)\b"),
    ("resistivity", r"\b(resistivit|conductivit|sheet resistance)\b"),
    ("optical", r"\b(refractive index|optical|absorbance|transmittance|ellipsometr|band gap)\b"),
    ("crystallinity", r"\b(XRD|diffraction|crystallin|grain size)\b"),
    ("pressure_exposure", r"\b(partial pressure|chamber pressure|exposure \(|Torr|mbar)\b"),
    ("plasma_conditions", r"\b(plasma (?:power|time|exposure)|RF power)\b"),
]
#: data types that indicate real deposition-process quantitation, not just characterisation
CORE_DATA = {"growth_per_cycle", "thickness_vs_cycles", "saturation_dose",
             "purge_dependence", "temperature_window", "conformality_profile"}


#: element symbols that plausibly head a deposited inorganic film
_FILM_CATIONS = set("""Li Be B Na Mg Al Si K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge
Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Sb Te Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu
Hf Ta W Re Os Ir Pt Au Bi Pb Th U""".split())
_ANIONS = set("O N S Se Te C F P As".split())
#: ligand/organic fragments and halides that mark a PRECURSOR, never a deposited film
_PRECURSOR_MARK = re.compile(
    r"(Cp|Me|Et|iPr|tBu|OiPr|thd|acac|amd|NMe|NEt|TDMA|TEMA|DEZ|TMA|Cl\d|Br\d|I\d|"
    r"\(|\)|=)", re.I)
_HALIDE = re.compile(r"(Cl|Br|F|I)\d*$")
_ACRONYM = re.compile(r"^[A-Z]{2,6}$")


_LIG = {"/uniFB00": "ff", "/uniFB01": "fi", "/uniFB02": "fl", "/uniFB03": "ffi",
        "/uniFB04": "ffl", "/uni00A0": " ", "/C14": "°", "/C0": "-"}


def clean_text(t):
    """Docling emits unresolved glyphs as /uniFBxx escapes; they otherwise ride through
    into titles and evidence strings and make them unreadable."""
    for k, v in _LIG.items():
        t = (t or "").replace(k, v)
    return re.sub(r"/uni[0-9A-F]{4}", "", t or "").strip()


def doc_title(md):
    """Docling keeps the title as the first markdown heading far more reliably than
    'longest line on page 1', which lands on author or affiliation blocks."""
    for ln in (md or "").splitlines()[:80]:
        t = ln.strip()
        if t.startswith("#"):
            t = t.lstrip("#").strip()
            t = clean_text(t)
            if 20 < len(t) < 260 and not re.match(
                    r"(abstract|introduction|contents|journal of|rsc |acs )", t, re.I):
                return t
    for ln in (md or "").splitlines()[:40]:
        t = ln.strip()
        if 30 < len(t) < 260 and not t.startswith("<!--") and "@" not in t \
                and not re.search(r"\b(university|department|institute|laborator)\b", t, re.I):
            return clean_text(t)
    return None


def is_film_formula(f):
    """Would this token be a deposited inorganic film? Rejects precursors, ligand
    fragments and bare acronyms, which is what stopped TiCl4, OiPr, CAS and HDMP from
    being reported as deposited materials."""
    if f in ONTO_MATERIALS:
        return True
    if len(f) < 2 or len(f) > 12:
        return False
    if _ACRONYM.match(f) or _PRECURSOR_MARK.search(f) or _HALIDE.search(f):
        return False
    if f in ONTO_PRECURSORS:
        return False
    els = _ELEMENT.findall(f)
    if not els or "".join(re.findall(r"[A-Za-z]", f)) != "".join(els):
        return False
    if els[0] not in _FILM_CATIONS:
        return False
    return len(els) == 1 or any(e in _ANIONS or e in _FILM_CATIONS for e in els[1:])


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text or "") if s.strip()]


def find_cue(text, cues):
    """First matching (label, evidence sentence) from an ordered cue list."""
    for label, pat in cues:
        m = re.search(pat, text or "", re.I)
        if m:
            for s in sentences(text):
                if re.search(pat, s, re.I):
                    return label, s[:240]
            return label, (text[max(0, m.start() - 60):m.start() + 120]).strip()[:240]
    return None, None


def anion_class(formula):
    f = formula
    if re.search(r"O\d?[xy]?$", f) or "O" in f and not re.search(r"[SNC]", f):
        return "oxide"
    for suf, cls in (("N", "nitride"), ("S", "sulfide"), ("Se", "selenide"),
                     ("Te", "telluride"), ("C", "carbide"), ("F", "fluoride")):
        if f.endswith(suf):
            return cls
    if re.fullmatch(r"[A-Z][a-z]?", f):
        return "metal"
    return "other"


def family_key(formula):
    """Cation element + anion class. MoO3 and MoOx share a family; Al2O3 and AlN do not."""
    els = _ELEMENT.findall(formula)
    cation = els[0] if els else formula
    return "%s-%s" % (cation, anion_class(formula))


def detect_materials(title, abstract, body):
    """Deposited material(s), with the sentence that supports each.

    A formula counts only when it is in the title, or appears in a sentence that also
    talks about depositing/growing a film. That is what stops a precursor chemistry or
    a substrate mentioned in the introduction becoming the 'deposited material'.
    """
    found = {}
    hay_title = title or ""
    for sent in sentences(abstract) + [hay_title]:
        deposit_ctx = (sent is hay_title) or bool(_DEPOSIT_CUE.search(sent))
        cands = set(_FORMULA.findall(sent))
        cands |= {m for m in ONTO_MATERIALS if re.search(r"\b%s\b" % re.escape(m), sent)}
        for f in cands:
            if not is_film_formula(f):
                continue
            if not (deposit_ctx or f in ONTO_MATERIALS):
                continue
            score = (3 if sent is hay_title else 0) + (2 if f in ONTO_MATERIALS else 0) + 1
            if f not in found or score > found[f][0]:
                found[f] = (score, sent[:240])
    ranked = sorted(found.items(), key=lambda kv: -kv[1][0])
    return [{"material": m, "score": s, "evidence": ev} for m, (s, ev) in ranked[:4]]


def corpus_material_counts():
    """{material: n_papers} from the LIVE corpus resolved layer."""
    c = Counter()
    for pid in sorted(P.papers()):
        f = P.resolved_json(pid, "experiments")
        if not f.exists():
            continue
        mats = {e.get("material") for e in json.loads(f.read_text()) if e.get("material")}
        for m in mats:
            c[m] += 1
    return c


def corpus_series_counts():
    c = Counter()
    for pid in sorted(P.papers()):
        f = P.resolved_json(pid, "experiments")
        r = P.resolved_json(pid, "results")
        if not (f.exists() and r.exists()):
            continue
        mats = {e.get("material") for e in json.loads(f.read_text()) if e.get("material")}
        n = len(json.loads(r.read_text()).get("results") or [])
        for m in mats:
            c[m] += n // max(len(mats), 1)
    return c


def triage_one(d, cmats):
    meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
    md_path = d / "document.md"
    if not md_path.exists():
        # Same field set as a successful record: a consumer of the JSON or the HTML
        # must not have to special-case the failures, and a candidate that could not be
        # read still has to appear in the table rather than silently vanish.
        return {"candidate_id": d.name, "doi": meta.get("doi"),
                "title": meta.get("title_from_pdf") or d.name, "source_paths": [],
                "pdf": meta.get("pdf"),
                "status": "no_docling_text", "error": meta.get("error"),
                "materials": [], "material_evidence": [], "precursors": [],
                "coreactants": [], "process_type": "unclear", "process_evidence": None,
                "study_type": "unclear", "study_evidence": None,
                "geometry_context": "unclear", "geometry_evidence": None,
                "exact_overlap": [], "family_overlap": {}, "new_materials": [],
                "current_material_counts": {}, "expected_data_types": [],
                "core_data_types": [], "extraction_value": "LOW", "experimental": False,
                "abstract_summary": "", "n_figures": None, "n_tables": None,
                "md_chars": 0,
                "priority_rank": None, "priority_reason": "no readable text",
                "uncertainty": "Docling produced no readable document.md for this PDF"}
    md = md_path.read_text(errors="ignore")
    struct = json.loads((d / "structure.json").read_text()) if (d / "structure.json").exists() else {}
    caps = " \n".join([f.get("caption") or "" for f in struct.get("figures") or []] +
                      [t.get("caption") or "" for t in struct.get("tables") or []])
    abstract = abstract_of(md)
    title = doc_title(md) or meta.get("title_from_pdf") or d.name
    head = "%s\n%s" % (title, abstract)

    mats = detect_materials(title, abstract, md)
    mat_ids = [m["material"] for m in mats]
    exact = [m for m in mat_ids if m in cmats]
    fams = {}
    for m in mat_ids:
        if m in exact:
            continue
        fk = family_key(m)
        rel = sorted({cm for cm in cmats if family_key(cm) == fk and cm != m})
        if rel:
            fams[m] = rel
    new = [m for m in mat_ids if m not in exact and m not in fams]

    proc, proc_ev = find_cue(head, PROCESS_CUES)
    # Weight of evidence, not first-match: ordering the cue list put "simulation" ahead
    # of "experimental", so one incidental mention of a model relabelled a measurement
    # paper. Count hits for each kind instead and let a mixed paper say so.
    hits, evs = {}, {}
    for label, pat in STUDY_CUES:
        found = [sn for sn in sentences(head) if re.search(pat, sn, re.I)]
        if found:
            hits[label] = len(found)
            evs[label] = found[0][:240]
    if re.search(r"\breview\b", title or "", re.I):
        hits["review"] = hits.get("review", 0) + 3
        evs.setdefault("review", title)
    if hits.get("review", 0) >= max(hits.values() or [0]):
        study = "review" if hits.get("review") else None
    elif hits.get("experimental") and hits.get("simulation"):
        study = "mixed"
    elif hits.get("experimental"):
        study = "experimental"
    elif hits.get("simulation"):
        study = "simulation"
    else:
        study = None
    study_ev = evs.get(study) or evs.get("experimental") or evs.get("simulation")
    geo, geo_ev = find_cue(head + " " + caps, GEOMETRY_CUES)

    hay = "%s\n%s" % (head, caps)
    dtypes = [lab for lab, pat in DATA_CUES if re.search(pat, hay, re.I)]
    core = [t for t in dtypes if t in CORE_DATA]
    experimental = study in ("experimental", "mixed") or (study is None and bool(core))
    if study is None and core:
        # No explicit "we deposited/measured" phrasing, but the figure captions carry
        # process measurements. Say that rather than "unclear", and mark it inferred so
        # the label is never mistaken for a stated claim.
        study, study_ev = "experimental_inferred", "figure captions report: %s" % ", ".join(core[:4])

    if experimental and len(core) >= 3:
        value = "HIGH"
    elif experimental and (core or len(dtypes) >= 4):
        value = "MEDIUM"
    elif study in ("review", "simulation") and not core:
        value = "LOW"
    elif dtypes:
        value = "MEDIUM" if core else "LOW"
    else:
        value = "LOW"

    return {
        "candidate_id": d.name, "doi": meta.get("doi"), "title": title,
        "source_paths": [str(md_path.relative_to(P.REPO)),
                         str((d / "structure.json").relative_to(P.REPO))],
        "pdf": meta.get("pdf"), "status": "ok",
        "materials": mat_ids, "material_evidence": mats,
        "precursors": [p for p in ONTO_PRECURSORS if re.search(r"\b%s\b" % re.escape(p), head)],
        "coreactants": [c for c in ONTO_COREACTANTS
                        if re.search(r"\b%s\b" % re.escape(c.replace("_", " ")), head, re.I)],
        "process_type": proc or "unclear", "process_evidence": proc_ev,
        "study_type": study or "unclear", "study_evidence": study_ev,
        "geometry_context": geo or "unclear", "geometry_evidence": geo_ev,
        "exact_overlap": exact, "family_overlap": fams, "new_materials": new,
        "current_material_counts": {m: cmats.get(m, 0) for m in exact},
        "expected_data_types": dtypes, "core_data_types": core,
        "extraction_value": value, "experimental": experimental,
        "abstract_summary": (clean_text(abstract)[:600] + ("…" if len(abstract) > 600 else "")) if abstract else "",
        "n_figures": struct.get("n_figures"), "n_tables": struct.get("n_tables"),
        "md_chars": len(md),
        "uncertainty": ("deposited material not established from title/abstract"
                        if not mat_ids else
                        "study type unclear" if study is None else ""),
    }


def score(r, cmats):
    """Explainable priority. Repeated comparable evidence for materials PSED already
    has is the objective, so exact overlap and core process data dominate; sparse
    materials get a deliberate boost because a second paper helps more than a fifth."""
    if r.get("status") != "ok":
        return -1, ["no readable text"]
    s, why = 0, []
    if r["exact_overlap"]:
        s += 40
        why.append("exact overlap: %s" % ", ".join(r["exact_overlap"]))
        n = min(cmats.get(m, 0) for m in r["exact_overlap"])
        if n <= 2:
            s += 12
            why.append("reinforces a sparse material (%d current paper(s))" % n)
    elif r["family_overlap"]:
        s += 15
        why.append("family overlap: %s" % ", ".join("%s~%s" % (k, "/".join(v))
                                                    for k, v in r["family_overlap"].items()))
    else:
        s += 2
        why.append("new material" if r["materials"] else "material unresolved")
    if r["experimental"]:
        s += 20
        why.append("experimental")
    if r["study_type"] == "review":
        s -= 25
        why.append("review")
    if r["study_type"] == "simulation":
        s -= 12
        why.append("simulation-only")
    s += 6 * len(r["core_data_types"])
    if r["core_data_types"]:
        why.append("core data: %s" % ", ".join(r["core_data_types"]))
    s += 1 * len(r["expected_data_types"])
    if r["geometry_context"] in ("HAR/trench/via", "porous"):
        s += 8
        why.append("HAR/porous geometry")
    if not r["materials"]:
        s -= 15
        why.append("deposited material unclear")
    if r["extraction_value"] == "HIGH":
        s += 8
    return s, why


def main():
    cmats = corpus_material_counts()
    cser = corpus_series_counts()
    dirs = sorted(d for d in CANDIDATES.iterdir() if d.is_dir()) if CANDIDATES.exists() else []
    recs = [triage_one(d, cmats) for d in dirs]
    for r in recs:
        sc, why = score(r, cmats)
        r["priority_score"] = sc
        r["priority_reason"] = "; ".join(why)
    recs.sort(key=lambda r: (-r["priority_score"], r["candidate_id"]))
    for i, r in enumerate(recs, 1):
        r["priority_rank"] = i

    # material coverage / expansion opportunity
    cov = {}
    for m, n in cmats.items():
        cov[m] = {"material": m, "current_papers": n, "current_series": cser.get(m, 0),
                  "candidate_papers": 0, "high_value_candidates": 0, "candidate_ids": []}
    for r in recs:
        for m in r["exact_overlap"]:
            cov.setdefault(m, {"material": m, "current_papers": cmats.get(m, 0),
                               "current_series": cser.get(m, 0), "candidate_papers": 0,
                               "high_value_candidates": 0, "candidate_ids": []})
            cov[m]["candidate_papers"] += 1
            cov[m]["candidate_ids"].append(r["candidate_id"])
            if r["extraction_value"] == "HIGH":
                cov[m]["high_value_candidates"] += 1
    coverage = sorted(cov.values(),
                      key=lambda c: (-c["high_value_candidates"], -c["candidate_papers"],
                                     c["current_papers"], c["material"]))

    # ---- role-corrected overlap ------------------------------------------------
    # The triage's exact_overlap answers "a corpus material name appears in a
    # deposition-ish sentence", which conflates the deposited film with substrate,
    # support, template, electrode and cited material. reports/exact_overlap_audit.json
    # re-read each flagged candidate and recorded what is actually DEPOSITED; where a
    # verdict exists it overrides, and the original triage value is kept as provenance.
    audit_path = P.REPORTS / "exact_overlap_audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {"candidates": []}
    ver = {a["candidate_id"]: a for a in audit.get("candidates", [])}
    for r in recs:
        a = ver.get(r["candidate_id"])
        r["triage_exact_overlap"] = list(r.get("exact_overlap") or [])
        if a:
            r["deposited_material"] = a["deposited_material"]
            r["substrate_support_material"] = a["substrate_support_material"]
            r["material_role_verdict"] = a["verdict"]
            r["material_role_verified"] = True
            r["strict_deposition_overlap"] = a["true_corpus_overlap"]
            r["role_evidence"] = a["supporting_sentence"]
        else:
            r["deposited_material"] = None
            r["substrate_support_material"] = []
            r["material_role_verdict"] = "UNVERIFIED"
            r["material_role_verified"] = False
            # not asserted: a name match alone is not evidence of deposition
            r["strict_deposition_overlap"] = []
            r["role_evidence"] = None

    strict = [r for r in recs if r["strict_deposition_overlap"]]
    out = {
        "generated_from": "local Docling text only (no LLM, no network)",
        "overlap_semantics": ("exact_overlap is the ORIGINAL name-match triage and is "
                              "retained only as provenance. The selection metric is "
                              "strict_deposition_overlap, which counts a candidate only "
                              "where reports/exact_overlap_audit.json verified that the "
                              "paper DEPOSITS the corpus material. Candidates with no "
                              "verdict carry an empty strict overlap and "
                              "material_role_verdict=UNVERIFIED -- absence of a verdict is "
                              "not evidence of overlap."),
        "strict_deposition_overlap_candidates": len(strict),
        "strict_overlap_material_counts": dict(Counter(
            m for r in strict for m in r["strict_deposition_overlap"])),
        "material_role_verdicts": dict(Counter(r["material_role_verdict"] for r in recs)),
        "disclaimer": ("Candidate material/study classifications are document-level "
                       "triage derived from local Docling text and are NOT yet "
                       "Scout/figure-extraction results."),
        "live_corpus_papers": len(P.papers()),
        "candidate_count": len(recs),
        "exact_overlap_candidates": sum(1 for r in recs if r["exact_overlap"]),
        "experimental_exact_overlap": sum(1 for r in recs if r["exact_overlap"] and r["experimental"]),
        "high_value_exact_overlap": sum(1 for r in recs if r["exact_overlap"]
                                        and r["extraction_value"] == "HIGH"),
        "no_text_candidates": sum(1 for r in recs if r.get("status") != "ok"),
        "current_material_counts": dict(cmats),
        "material_coverage": coverage,
        "candidates": recs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print("wrote %s" % OUT)
    print("  candidates=%d  exact-overlap=%d  experimental-exact=%d  high-value-exact=%d"
          % (out["candidate_count"], out["exact_overlap_candidates"],
             out["experimental_exact_overlap"], out["high_value_exact_overlap"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
