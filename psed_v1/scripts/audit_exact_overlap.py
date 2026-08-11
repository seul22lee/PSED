#!/usr/bin/env python3
"""
scripts/audit_exact_overlap.py — re-audit the exact_overlap candidates by hand-checked
deposited material, and write reports/exact_overlap_audit.json.

    python3 scripts/audit_exact_overlap.py

Why this exists: the automated triage in scripts/triage_candidates.py answers "does a
material name that the corpus also has appear in a deposition-ish sentence". That is not
the selection objective. A paper that deposits gold on TiO2 particles, or WSe2 on an SiO2
wafer, or LiNbO3 on a sapphire (Al2O3) substrate, matches on the SUPPORT, not on the
film. Selecting those would add no repeated evidence for the corpus material at all.

The DETERMINATIONS below are Claude-derived from reading the local Docling text of each
candidate; each carries the sentence it was read from, so it is auditable rather than
opaque. The script re-extracts that sentence from document.md at run time and flags any
determination whose evidence can no longer be found — so the audit cannot silently rot
against changed text. No API, no Docling rerun.

Categories:
  TRUE_DEPOSITION_EXACT_OVERLAP   the paper itself deposits a corpus material
  SUPPORT_OR_SUBSTRATE_OVERLAP    the shared name is substrate/support/template only
  COMPOSITE_DOPED_STACK_AMBIGUOUS the film is doped/ternary/stacked, not the pure material
  REVIEW_NO_OWN_DEPOSITION        a review/overview reporting no primary deposition of
                                  its own (not one of the three requested labels, but
                                  filing these under the others would misstate them)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paths as P                                              # noqa: E402

CANDIDATES = P.REPO / "corpus" / "acquisition" / "candidates"
TRIAGE = P.REPORTS / "candidate_corpus_expansion.json"
OUT = P.REPORTS / "exact_overlap_audit.json"

TRUE = "TRUE_DEPOSITION_EXACT_OVERLAP"
SUPPORT = "SUPPORT_OR_SUBSTRATE_OVERLAP"
COMPOSITE = "COMPOSITE_DOPED_STACK_AMBIGUOUS"
REVIEW = "REVIEW_NO_OWN_DEPOSITION"

#: candidate_id -> verdict, deposited film(s), substrate/support(s), true corpus overlap,
#: and a distinctive phrase that must still be present in the local document.md
DETERMINATIONS = {
    "10.1039_c7ra13417g": (TRUE, ["Y2O3"], [], ["Y2O3"],
        "atomic layer deposition (ALD) process for yttrium oxide"),
    "10.1039_d0ra09876k": (TRUE, ["Y2O3"], [], ["Y2O3"],
        "Atomic layer deposition of dielectric Y"),
    "10.1039_d0ra01602k": (TRUE, ["SiO2"], [], ["SiO2"],
        "SiO2 thin"),
    "10.1149_2.067203jes": (TRUE, ["SiO2", "Al2O3"], ["Si(100)"], ["SiO2", "Al2O3"],
        "used to deposit SiO2 films in the temperature range"),
    "10.1038_am.2016.182": (TRUE, ["Pt"], ["textile fiber"], ["Pt"],
        "atomic layer deposi"),
    "10.1039_c7ta03257a": (TRUE, ["Pt"], ["silica template"], ["Pt"],
        "After ALD of Pt in the silica material"),
    "10.1039_c5ta00205b": (TRUE, ["Pt"], ["porous anodic oxide (TiO2)"], ["Pt"],
        "the ALD procedure is applied to porous anodic oxide substrates"),
    "10.1039_c3ta01665j": (TRUE, ["Pt"], ["TiO2 (Aeroxide P-25 particles)"], ["Pt"],
        "used as the substrate for the deposition"),
    "10.1039_c4nr05049e": (TRUE, ["TiO2"], ["porous titania film"], ["TiO2"],
        "during ALD of TiO2 in a porous titania film"),
    "10.1039_c3ra42928h": (TRUE, ["TiO2"], ["carbon nanotubes (sacrificial)"], ["TiO2"],
        "photoactive TiO2 nanoparticle chains"),
    "10.1021_acs.langmuir.6b03119": (TRUE, ["Al2O3"], ["TiO2 nanotube layers"], ["Al2O3"],
        "deposition of Al2O3 (as a model secondary material)"),
    "10.1063_1.2338776": (TRUE, ["Al2O3"], ["polymer (PEN)"], ["Al2O3"],
        "moisture permeation barriers"),

    "10.1039_d0nr01092h": (SUPPORT, ["Au"], ["TiO2"], [],
        "approach for depositing gold nanoparticles"),
    "10.1088_2053-1583_3_1_014004": (SUPPORT, ["WSe2"], ["SiO2"], [],
        "self-limited layer synthesis"),
    "10.1039_c3tc30271g": (SUPPORT, ["LiNbO3"], ["Al2O3 (sapphire)", "Si(100)"], [],
        "epitaxially oriented on substrates of Al2O3"),

    "10.1039_c4tc02707h": (COMPOSITE, ["B-doped ZnO", "Al-doped ZnO"], [], ["ZnO"],
        "B-doped ZnO using triisopropyl borate"),
    "10.1039_d1ra00507c": (COMPOSITE, ["Ru-doped Fe2O3"], [], ["Fe2O3"],
        "ruthenium-doped iron oxide"),
    "10.1039_c3ra47469k": (COMPOSITE, ["EuxTiyOz (TiO2 - Eu2O3 range)"], [], ["TiO2"],
        "control of the stoichiometry from pure TiO2 to pure Eu2O3"),
    "10.1039_d1dt03543f": (COMPOSITE, ["aluminium ruthenate", "platinum ruthenate"], [],
        ["RuO2"], "one for aluminum ruthenate"),

    "10.1116_1.4728205": (REVIEW, ["Al2O3 (topic of the review)"], [], [],
        "Status and prospects of Al"),
    "10.1557_mrs.2011.239": (REVIEW, ["various (process-technology overview)"], [], [],
        "Advanced process technologies"),
}


def clean(t):
    t = (t or "").replace("/uniFB01", "fi").replace("/uniFB02", "fl").replace("/uniFB00", "ff")
    return re.sub(r"/uni[0-9A-F]{4}", "", t)


def sentence_for(cid, phrase):
    """Re-extract the supporting sentence from the local text, so the stored verdict is
    checkable. Returns (sentence, found)."""
    md = CANDIDATES / cid / "document.md"
    if not md.exists():
        return None, False
    txt = clean(md.read_text(errors="ignore"))
    i = txt.find(phrase)
    if i < 0:
        return None, False
    s = max(txt.rfind(".", 0, i), txt.rfind("\n", 0, i)) + 1
    e = txt.find(".", i + len(phrase))
    return re.sub(r"\s+", " ", txt[s:(e + 1 if e > 0 else i + 240)]).strip()[:300], True


def main():
    triage = json.loads(TRIAGE.read_text())
    by_id = {r["candidate_id"]: r for r in triage["candidates"]}
    flagged = [r["candidate_id"] for r in triage["candidates"] if r["exact_overlap"]]
    missing = [c for c in flagged if c not in DETERMINATIONS]
    extra = [c for c in DETERMINATIONS if c not in flagged]

    rows, unverified = [], []
    for cid in flagged:
        verdict, film, sub, overlap, phrase = DETERMINATIONS.get(
            cid, (None, [], [], [], ""))
        sent, ok = sentence_for(cid, phrase) if phrase else (None, False)
        if not ok:
            unverified.append(cid)
        t = by_id[cid]
        rows.append({
            "candidate_id": cid,
            "title": t.get("title"),
            "verdict": verdict,
            "triage_exact_overlap": t.get("exact_overlap"),
            "deposited_material": film,
            "substrate_support_material": sub,
            "true_corpus_overlap": overlap,
            "supporting_sentence": sent,
            "evidence_phrase": phrase,
            "evidence_verified_in_local_text": ok,
            "source_paths": t.get("source_paths"),
            "extraction_value": t.get("extraction_value"),
            "study_type": t.get("study_type"),
        })

    true_rows = [r for r in rows if r["verdict"] == TRUE]
    mat = Counter(m for r in true_rows for m in r["true_corpus_overlap"])
    out = {
        "note": ("Re-audit of the triage exact_overlap set by DEPOSITED material. "
                 "Determinations are Claude-derived from local Docling text; each stores "
                 "the sentence it was read from and is re-verified against document.md "
                 "at build time. No API, no Docling rerun."),
        "triage_exact_overlap_count": len(flagged),
        "corrected_true_deposition_count": len(true_rows),
        "verdict_counts": dict(Counter(r["verdict"] for r in rows)),
        "true_overlap_material_counts": dict(mat),
        "current_corpus_material_counts": {
            m: triage["current_material_counts"].get(m, 0) for m in mat},
        "unverified_evidence": unverified,
        "determinations_missing_for": missing,
        "determinations_not_in_flagged_set": extra,
        "candidates": rows,
    }
    OUT.write_text(json.dumps(out, indent=1))
    print("wrote %s" % OUT)
    print("  triage exact_overlap        : %d" % len(flagged))
    print("  TRUE deposition overlap     : %d" % len(true_rows))
    for k, v in sorted(out["verdict_counts"].items()):
        print("    %-32s %d" % (k, v))
    if unverified:
        print("  *** evidence phrase NOT found for: %s" % unverified)
    if missing:
        print("  *** no determination for: %s" % missing)
    return 1 if (unverified or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
