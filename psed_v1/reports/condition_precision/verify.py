#!/usr/bin/env python3
"""READ-ONLY precision verification of sampled bound assertions.

Each criterion is re-derived FROM THE SOURCE TEXT, not read back off the assertion:
  1 value/unit   the number+unit must occur in the cited source at the cited locator
  2 quantity     re-typing the located span must yield the same quantity
  3 applicability the assertion's figure/panel/series must cover the entity
  4 scope        the bound scope must not exceed what the evidence source supports
  5 status       re-deriving direct/estimated/assumed/fitted from the span must agree
  6 species/role re-deriving the species from the span must agree
  7 duplication  the same (quantity,value,unit) must not arrive via >1 locator
"""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "02_extraction"))
sys.path.insert(0, str(REPO / "02_extraction" / "stages"))
sys.path.insert(0, str(REPO / "03_corpus" / "scripts"))
import importlib.util as _u
from canonical import conditions as C

_s = _u.spec_from_file_location("kb6", REPO / "03_corpus" / "scripts" / "06_to_kb.py")
kb6 = _u.module_from_spec(_s)
_s.loader.exec_module(kb6)

KB = REPO / "02_extraction" / "output"
EX = REPO / "03_corpus" / "extracted"
OUT = REPO / "reports" / "condition_precision"

# what scope each evidence source may legitimately support
MAX_SCOPE = {"series_label": "series", "caption": "figure", "body": "figure",
             "methods": "method", "table": "figure"}
ORDER = ["series", "panel", "figure", "method", "paper"]


SUFFIX = sys.argv[1] if len(sys.argv) > 1 else ""


def _num(v):
    try:
        return float(str(v).replace("e-", "e-"))
    except Exception:
        return None


_AXIS_CACHE = {}


def _series_axis(rec):
    """The panel's series_axis, which types a legend value. Omitting it made the
    verifier re-type every legend temperature as the generic `temperature`."""
    key = (rec["paper_id"], str(rec["fig_docling_index"]), str(rec["panel"] or ""))
    if key not in _AXIS_CACHE:
        axis = None
        fd = json.loads((EX / rec["paper_id"] / "figure_data.json").read_text())
        for f in fd.get("figures", []):
            if str(f.get("figure")) != str(rec["fig_docling_index"]):
                continue
            for pan in f.get("panels", []) or []:
                if str(pan.get("panel") or "") == str(rec["panel"] or ""):
                    axis = pan.get("series_axis")
        _AXIS_CACHE[key] = axis
    return _AXIS_CACHE[key]


def val_present(text, rec):
    v = _num(rec["value"])
    if v is None:
        return True
    for tok in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", re.sub(r"\s+", " ", text)):
        try:
            if abs(float(tok) - v) <= 1e-9 * max(1.0, abs(v)):
                return True
        except ValueError:
            pass
    return False


def source_text(rec):
    """The actual source text the locator names."""
    doi, loc = rec["paper_id"], (rec["evidence_locator"] or "")
    if rec["source_kind"] == "methods":
        return kb6._methods(doi), "methods section"
    if rec["source_kind"] == "series_label":
        return C.fold_math(rec["source_series"] or ""), "series label"
    fd = json.loads((EX / doi / "figure_data.json").read_text())
    cap = ""
    for f in fd.get("figures", []):
        if str(f.get("figure")) == str(rec["fig_docling_index"]):
            cap = f.get("caption") or ""
            break
    if rec["source_kind"] == "caption":
        cap = C.fold_math(cap)
        if "panel (" in loc:
            clauses, _pre = C.caption_panel_clauses(cap)
            return clauses.get((rec["panel"] or "").lower(), cap), "caption panel clause"
        clauses, pre = C.caption_panel_clauses(cap)
        if not clauses:
            return cap, "caption"
        # pressures_from_text reads the WHOLE caption; the preamble slice is used only
        # by from_caption/conditions_from_prose. Verify against whichever the parser saw.
        if rec["quantity"] in ("working_pressure", "base_pressure", "generic_pressure",
                               "precursor_partial_pressure", "co_reactant_partial_pressure",
                               "carrier_gas_partial_pressure", "bubbler_pressure",
                               "exposure"):
            return cap, "caption (full, pressure path)"
        if val_present(pre, rec):
            return pre, "caption preamble"
        return cap, "caption (full)"
    if rec["source_kind"] == "body":
        if "reference-scoped" in loc:
            return C.fold_math((EX / doi / "document.md").read_text(errors="replace")), "document body"
        return C.fold_math(kb6._figure_body(doi, rec["printed_figure_number"])), "figure body"
    return "", "unknown"


def verify(rec, ent_index):
    txt, kind = source_text(rec)
    ev = (rec["raw_evidence"] or "").strip()
    res = {"assertion_uid": rec["assertion_uid"], "source_text_kind": kind}

    # --- 1 value and unit present in the source ---------------------------
    flat = re.sub(r"\s+", " ", txt)
    ev_flat = re.sub(r"\s+", " ", ev)
    span_found = ev_flat[:40] in flat if len(ev_flat) >= 6 else False
    val = _num(rec["value"])
    unit = (rec["unit"] or "").strip()
    val_in_src = False
    if val is not None:
        for tok in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", flat):
            try:
                if abs(float(tok) - val) <= 1e-9 * max(1.0, abs(val)):
                    val_in_src = True
                    break
            except ValueError:
                pass
    def _unit_present(u):
        if not u or u in ("cycle",):
            return True                     # synthesized by definition
        base = u.split("/")[0].replace("*s", "")   # Å/cycle -> Å ; mTorr*s -> mTorr
        loose = re.escape(base).replace(r"\°", r"\s*°\s*")
        return re.search(loose, flat, re.I) is not None or \
            re.search(r"\s*".join(map(re.escape, base)), flat, re.I) is not None

    unit_in_src = _unit_present(unit)
    res["c1_value_unit"] = "pass" if (val_in_src and unit_in_src) else "FAIL"
    res["c1_detail"] = "" if res["c1_value_unit"] == "pass" else \
        "value_in_source=%s unit_in_source=%s" % (val_in_src, unit_in_src)
    res["evidence_span_relocated"] = span_found

    # --- 2 quantity re-typed from the located span ------------------------
    redo = C.conditions_from_prose(txt, rec["bound_at_scope"], rec["source_kind"], "verify")
    redo += C.pressures_from_text(txt, rec["bound_at_scope"], rec["source_kind"], "verify")
    if rec["source_kind"] == "series_label":
        redo += C.from_series_label(rec["source_series"], _series_axis(rec))
    same_val = [a for a in redo if _num(a["value"]) is not None and val is not None
                and abs(_num(a["value"]) - val) <= 1e-9 * max(1.0, abs(val))]
    qs = {a["quantity"] for a in same_val}
    res["c2_quantity"] = ("pass" if rec["quantity"] in qs
                          else ("unverifiable" if not same_val else "FAIL"))
    res["c2_detail"] = "" if res["c2_quantity"] == "pass" else "re-typed as %s" % sorted(qs)

    # --- 3 applicability to the entity ------------------------------------
    ok3 = True
    why3 = []
    if rec["reference_work"]:
        if rec["reference_work"] not in (rec["source_series"] or ""):
            ok3 = False
            why3.append("reference %r not in series label %r"
                        % (rec["reference_work"], rec["source_series"]))
    if rec["source_kind"] == "series_label" and rec["bound_at_scope"] != "series":
        ok3 = False
        why3.append("series-label evidence bound at %s" % rec["bound_at_scope"])
    res["c3_applicability"] = "pass" if ok3 else "FAIL"
    res["c3_detail"] = "; ".join(why3)

    # --- 4 scope not broader than the source supports ---------------------
    allowed = MAX_SCOPE.get(rec["source_kind"], "paper")
    ok4 = ORDER.index(rec["bound_at_scope"]) <= ORDER.index(allowed)
    if rec["source_kind"] == "caption" and kind == "caption panel clause":
        ok4 = rec["bound_at_scope"] in ("panel", "series")
    res["c4_scope"] = "pass" if ok4 else "FAIL"
    res["c4_detail"] = "" if ok4 else "%s evidence bound at %s (max %s)" % (
        rec["source_kind"], rec["bound_at_scope"], allowed)

    # --- 5 status re-derived ----------------------------------------------
    st = None
    if same_val:
        sts = {a["assertion_status"] for a in same_val}
        st = rec["assertion_status"] if rec["assertion_status"] in sts else sorted(sts)[0]
    res["c5_status"] = ("pass" if st == rec["assertion_status"]
                        else ("unverifiable" if st is None else "FAIL"))
    res["c5_detail"] = "" if res["c5_status"] == "pass" else "re-derived %r vs stored %r" % (
        st, rec["assertion_status"])

    # --- 6 species / reactant role ----------------------------------------
    sps = {a.get("species") for a in same_val if a["quantity"] == rec["quantity"]}
    if rec["species"] is None:
        real = {x for x in sps if x}
        res["c6_species"] = "pass" if not real else "under_attributed"
        res["c6_detail"] = "" if not real else "source supports %s, none stored" % sorted(real)
    else:
        res["c6_species"] = ("pass" if rec["species"] in sps
                             else ("unverifiable" if not sps else "FAIL"))
        res["c6_detail"] = "" if res["c6_species"] == "pass" else \
            "source supports %s vs stored %r" % (sorted(x for x in sps if x), rec["species"])

    # --- 7 duplication across evidence paths ------------------------------
    key = (rec["quantity"], str(rec["value"]), str(rec["unit"]), str(rec["species"]))
    dups = ent_index.get((rec["entity_id"], key), [])
    res["c7_duplication"] = "pass" if len(dups) <= 1 else "FAIL"
    res["c7_detail"] = "" if len(dups) <= 1 else "%d bindings: locators %s" % (
        len(dups), sorted({d for d in dups})[:3])

    fails = [k for k in ("c1_value_unit", "c2_quantity", "c3_applicability", "c4_scope",
                         "c5_status", "c6_species", "c7_duplication")
             if res[k] == "FAIL"]
    res["under_attributed"] = res["c6_species"] == "under_attributed"
    res["verdict"] = "correct" if not fails else "error"
    res["error_criteria"] = ";".join(fails)
    res.update({k: rec[k] for k in ("paper_id", "entity_id", "classification",
                                    "printed_figure_number", "panel", "source_series",
                                    "quantity", "value", "unit", "species",
                                    "assertion_status", "source_kind", "bound_at_scope",
                                    "family", "raw_evidence", "evidence_locator")})
    return res


def main():
    man = json.loads((OUT / ("precision_sample_manifest%s.json" % SUFFIX)).read_text())
    ent_index = defaultdict(list)
    for ef in sorted(KB.glob("*/resolved/entities.json")):
        for e in json.loads(ef.read_text()):
            for b in e.get("bound_conditions") or []:
                k = (b["quantity"], str(b["value"]), str(b["unit"]), str(b.get("species")))
                ent_index[(e["entity_id"], k)].append(b.get("evidence_locator"))
    rows = [verify(r, ent_index) for r in man["records"]]
    (OUT / ("precision_audit%s.json" % SUFFIX)).write_text(json.dumps(
        {"n": len(rows), "seed": man["random_seed"], "rows": rows}, indent=1, ensure_ascii=False))
    with open(OUT / ("precision_audit%s.csv" % SUFFIX), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n = len(rows)
    print("verified %d sampled bound assertions" % n)
    print("  verdict:", dict(Counter(r["verdict"] for r in rows)))
    for c in ("c1_value_unit", "c2_quantity", "c3_applicability", "c4_scope",
              "c5_status", "c6_species", "c7_duplication"):
        cc = Counter(r[c] for r in rows)
        print("  %-18s pass %3d  FAIL %3d  unverifiable %3d"
              % (c, cc["pass"], cc["FAIL"], cc["unverifiable"]))
    errs = [r for r in rows if r["verdict"] == "error"]
    print("\nerror criteria:", Counter(c for r in errs for c in r["error_criteria"].split(";") if c))
    print("errors by family:", Counter(r["family"] for r in errs))
    print("errors by source:", Counter(r["source_kind"] for r in errs))


if __name__ == "__main__":
    main()
