#!/usr/bin/env python3
"""READ-ONLY. Correction #6 — a pressure counts as LOST for a record only when the
assertion demonstrably APPLIES to that record.

Applicability test, strictest first:
  1. the record's own panel `conditions{}` names a pressure           -> applies (panel scope)
  2. the record's figure CAPTION states a pressure                    -> applies (figure scope)
  3. the paper's METHODS states a single process/working pressure and
     the record is an experimental record of that paper               -> applies (paper scope)
  4. pressure.json has an entry whose context is process_condition AND
     it is the ONLY such value in the paper                           -> applies (paper scope)
Anything else (base pressure, several conflicting paper values with no narrower
evidence, a model-definition symbol, a measured-response y-axis) does NOT apply and
is NOT counted as a loss.
"""
import json, re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
KB = REPO / "papers"              # papers/<doi>/resolved/
EX = REPO / "papers"    # papers/<doi>/extracted/
PRESSURE_Q = {"generic_pressure", "working_pressure", "total_pressure", "partial_pressure",
              "chamber_total_pressure", "precursor_partial_pressure",
              "co_reactant_partial_pressure", "reactant_A_partial_pressure",
              "reactant_B_partial_pressure", "carrier_gas_partial_pressure"}
PUNIT = r"(?:mTorr|Torr|mbar|hPa|kPa|MPa|Pa|atm|bar)"
CAP_P = re.compile(r"\d[\d.]*\s*" + PUNIT + r"\b")
METH_P = re.compile(r"(?:process|working|deposition|chamber|total)\s+pressure[^.]{0,60}?"
                    r"(\d[\d.]*)\s*(" + PUNIT + r")", re.I)


def J(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def main():
    audit = J(OUT / "random_sample_audit.json")
    cache, fdcache, doccache = {}, {}, {}
    stats = Counter()
    for a in audit["rows"]:
        doi = a["paper_id"]
        if doi not in cache:
            cache[doi] = {e["exp_id"]: e for e in (J(KB / doi / "resolved" / "experiments.json", []) or [])}
            fdcache[doi] = J(EX / doi / "extracted" / "figure_data.json", {}) or {}
            doccache[doi] = Path(EX / doi / "extracted" / "document.md").read_text(errors="replace") \
                if (EX / doi / "extracted" / "document.md").exists() else ""
        exp = cache[doi].get(a["record_id"], {})
        prov = exp.get("provenance") or {}
        fi, pan = str(prov.get("fig_docling_index") or ""), str(prov.get("panel") or "")

        applies, scope, ev = False, None, None
        # 1. panel conditions
        for f in fdcache[doi].get("figures", []):
            if str(f.get("figure")) != fi:
                continue
            for p in f.get("panels", []) or []:
                if str(p.get("panel") or "") == pan:
                    for k, v in (p.get("conditions") or {}).items():
                        if "press" in k.lower():
                            applies, scope, ev = True, "panel", "%s=%s" % (k, v)
            # 2. caption
            if not applies:
                m = CAP_P.search(f.get("caption") or "")
                if m:
                    applies, scope, ev = True, "figure", m.group(0)
        # 3. methods, only for experimental records
        if not applies and exp.get("relevance") == "experimental":
            m = METH_P.search(doccache[doi])
            if m:
                applies, scope, ev = True, "paper_methods", " ".join(m.group(0).split())[:120]
        # 4. single unambiguous process_condition pressure in pressure.json
        if not applies:
            pj = (J(EX / doi / "extracted" / "pressure.json", {}) or {}).get("pressures") or []
            proc = [x for x in pj if x.get("context") == "process_condition"
                    and x.get("value") is not None]
            vals = {round(float(x["value"]), 9) for x in proc}
            if len(vals) == 1:
                applies, scope, ev = True, "paper_pressure_json", proc[0].get("evidence_text")

        ctrl = exp.get("controlled") or []
        usable = [c for c in ctrl if c.get("quantity") in PRESSURE_Q
                  and c.get("context_status") != "ambiguous"]
        a["pressure_applies_to_record"] = applies
        a["pressure_applicability_scope"] = scope
        a["pressure_applicability_evidence"] = ev
        a["pressure_present_and_usable"] = bool(usable)
        a["pressure_applicable_and_lost"] = bool(applies and not usable)
        stats["applies" if applies else "does_not_apply"] += 1
        if applies:
            stats["applies_and_lost" if not usable else "applies_and_bound"] += 1
    (OUT / "random_sample_audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False))
    n = len(audit["rows"])
    print("pressure applicability over the %d sampled records:" % n)
    for k, v in stats.most_common():
        print("   %-22s %3d  (%.1f%%)" % (k, v, 100 * v / n))
    print("\nPREVIOUS (over-counted) metric counted any record in a paper whose "
          "pressure.json was non-empty OR whose caption mentioned a pressure,\n"
          "regardless of whether that pressure applied to the record.")


if __name__ == "__main__":
    main()
