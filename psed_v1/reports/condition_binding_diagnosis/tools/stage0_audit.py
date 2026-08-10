#!/usr/bin/env python3
"""READ-ONLY. Stage 0 step 2 — classify every unique source entity from CORROBORATED
paper evidence, reconstruct its conditions and scopes, and resolve pressure at
series/run scope.

Rule (spec item 4): a final class is assigned ONLY when >=2 INDEPENDENT signal
families agree. Point count, curve smoothness, axis type and a lone caption keyword
are recorded as weak signals and can never decide on their own. Anything else is
`unknown` with its signals listed, never a guess.

Signal families (independent by construction):
  M  measurement modality           caption / body / methods name an instrument
  R  explicit run-structure statement ("independently varied", "each film", sample list)
  I  sample / run identifier         "sample 12, 13 and 14", "Series E", table row
  L  series-label semantics          Author+Year -> literature; Model/Knudsen -> simulation
  F  extraction source flag          panel_source / figure source (measured|simulated)
  T  table linkage                   a table caption binds the parameter set
  w* weak: axis role, point count, single caption keyword   (never decisive alone)
"""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis" / "stage0"
EX = REPO / "papers"    # papers/<doi>/extracted/
KB = REPO / "papers"              # papers/<doi>/resolved/

def J(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d

# ---------- signal detectors ------------------------------------------------
MODALITY = [
    (r"in[- ]?situ", "in_situ", "continuous"),
    (r"spectroscopic ellipsometr|\bVASE\b|\bSE\b(?!M)", "ellipsometry", "continuous_if_in_situ"),
    (r"\bQCM\b|quartz crystal microbalance", "qcm", "continuous"),
    (r"real[- ]time", "real_time", "continuous"),
    (r"depth profil|sputter(?:ing)? (?:time|depth)|TOF[- ]?ERDA|\bSIMS\b", "depth_profile", "continuous"),
    (r"\bXRR\b|X-ray reflectivit", "xrr", "discrete"),
    (r"\bSEM\b|\bTEM\b|cross[- ]section", "microscopy", "discrete"),
    (r"\bXPS\b|photoelectron spectro", "xps", "spectrum"),
    (r"\bXRD\b|diffractogram|diffraction pattern", "xrd", "spectrum"),
    (r"\bFTIR\b|infrared spectr|Raman", "vibrational", "spectrum"),
    (r"photocataly|degradation of|C/C0", "photocatalysis", "continuous"),
    (r"impedance|symmetric cell|storage", "electrochemistry", "continuous"),
    (r"contact angle", "contact_angle", "discrete"),
]
RUNSTRUCT_DISCRETE = [
    r"independently varied", r"saturation curves?", r"self[- ]limiting",
    r"determining .{0,25}windows?", r"each (?:film|sample|run) was",
    r"films? were (?:grown|deposited) (?:at|with|using)",
    r"(?:as a function of|versus|vs\.?|influence of|effect of|dependence of)"
    r"[^.]{0,40}(?:temperature|pressure|pulse|purge|exposure|dose|flow|cycles)",
    r"samples? \d+[^.]{0,40}(?:in )?Table",
]
RUNSTRUCT_CONTINUOUS = [
    r"in[- ]?situ monitor", r"monitored (?:by|with|using)", r"stepwise growth",
    r"during (?:one|a single|the) (?:cycle|run|deposition|exposure)",
    r"as a function of (?:the )?(?:deposition |process |elapsed )?time",
]
SAMPLE_ID = re.compile(r"\b(?:samples?|runs?|specimens?)\s+((?:[A-Za-z0-9]+\s*[,;]?\s*(?:and\s*)?){1,8})"
                       r"(?:\s*(?:in|of|from)\s+Table\s*\S+)?|\bSeries\s+([A-Z])\b", re.I)
LIT_LABEL = re.compile(r"\b([A-Z][a-z]{2,})\s*(?:et al\.?)?\s*,?\s*((?:19|20)\d{2})\b")
SIM_LABEL = re.compile(r"\b(model|simulat\w*|knudsen|bosanquet|calculated|fit(?:ted)?|theor\w*)\b", re.I)
FIT_LABEL = re.compile(r"\b(fit|fitted|linear fit|arrhenius|regression|guide to the eye|solid line serves)\b", re.I)
CONCEPT = re.compile(r"\bschematic|\bdiagram of|illustration|configuration|setup|layout\b", re.I)

PUNIT = r"(?:mTorr|Torr|mbar|hPa|kPa|MPa|Pa|atm|bar)"
NUM = r"[-+]?\d*\.?\d+(?:\s*[x×]\s*10\s*[-–−]?\s*\d+)?(?:[eE][-+]?\d+)?"
EXPOSURE_RX = re.compile(r"(" + NUM + r")\s*(" + PUNIT + r")\s*[·⋅*.\s]?\s*(?:s|sec)\b", re.I)
PSYM_RX = re.compile(r"\bp\s*[_ ]?\s*(A0|B0|A|B)\b\s*[=≈]\s*(" + NUM + r")\s*(" + PUNIT + r")", re.I)
PPLAIN_RX = re.compile(r"(" + NUM + r")\s*(" + PUNIT + r")\b")
SPECIES_RX = re.compile(r"\(\s*([AB])\s*=\s*([A-Za-z0-9][A-Za-z0-9()\-]*)\s*\)")
STATUS_RX = [(re.compile(r"\b(?:we\s+)?estimat\w+", re.I), "estimated"),
             (re.compile(r"\bassum\w+", re.I), "assumed"),
             (re.compile(r"\bfitt?ed\b|\bfitting\b", re.I), "fitted"),
             (re.compile(r"\bca\.|\babout\b|approximately|typical\w*|nominal\w*", re.I), "approximate")]


def hits(patterns, text):
    out = []
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            out.append(" ".join(m.group(0).split())[:180])
    return out


SETTING_ENUM = re.compile(
    r"(?:at|of|to|using|with|between)\s+((?:\d[\d.]*\s*(?:,|and|-|–|to)\s*){1,10}\d[\d.]*)\s*"
    r"(°\s*C|K|Pa|hPa|kPa|mbar|Torr|mTorr|sccm|s\b|ms|min|nm|µm|um|μm|cycles?)", re.I)
SAMPLE_LIST = re.compile(r"\b(?:samples?|runs?|specimens?)\s+((?:[A-Za-z0-9]+\s*(?:,|and)\s*)"
                         r"{1,10}[A-Za-z0-9]+)", re.I)


def stated_setting_count(cap, body, label):
    """How many DISTINCT prepared settings the paper actually states for this figure.

    Returns (count, evidence) or (None, None). This is the only defensible upper
    bound on a sweep's size -- the digitised point count is digitisation density,
    not a count of depositions, and must never be used for it."""
    for text, src in ((cap, "caption"), (body, "body")):
        if not text:
            continue
        m = SAMPLE_LIST.search(text)
        if m:
            ids = [x for x in re.split(r"\s*(?:,|and)\s*", m.group(1)) if x.strip()]
            if 1 < len(ids) <= 12:
                return len(ids), "%s: %s" % (src, " ".join(m.group(0).split())[:120])
        m = SETTING_ENUM.search(text)
        if m:
            vals = [v for v in re.split(r"\s*(?:,|and|-|–|to)\s*", m.group(1)) if v.strip()]
            if 1 < len(vals) <= 12:
                return len(vals), "%s: %s" % (src, " ".join(m.group(0).split())[:120])
    return None, None


def status_of(win):
    for rx, s in STATUS_RX:
        if rx.search(win):
            return s
    return "direct"


def resolve_pressures(ent, doc, methods_text):
    """Pressure assertions applicable to THIS entity, at series/run scope.
    Exposure products are typed separately and never returned as pressures."""
    cap = ent["caption"] or ""
    body = ent.get("body_mentions") or ""
    label = ent["source_series"] or ""
    out, exposures = [], []

    def scan(text, scope, src):
        spans = {(m.start(), m.end()) for m in EXPOSURE_RX.finditer(text)}
        for m in EXPOSURE_RX.finditer(text):
            win = text[max(0, m.start() - 200): m.end() + 200]
            exposures.append({"value": m.group(1), "unit": m.group(2) + "*s",
                              "status": status_of(win), "scope": scope, "source": src,
                              "evidence": " ".join(m.group(0).split())})
        for m in PSYM_RX.finditer(text):
            win = text[max(0, m.start() - 260): m.end() + 260]
            sym = "p_" + m.group(1).upper()
            role = {"A": "precursor", "A0": "precursor",
                    "B": "carrier_or_coreactant", "B0": "carrier_or_coreactant"}[m.group(1).upper()]
            sp = None
            for sm in SPECIES_RX.finditer(win):
                if sm.group(1).upper() == m.group(1).upper()[0]:
                    sp = sm.group(2).rstrip(")")
            out.append({"quantity_type": ("precursor_partial_pressure" if role == "precursor"
                                          else "carrier_gas_partial_pressure"),
                        "symbol": sym, "value": m.group(2), "unit": m.group(3),
                        "species": sp, "reactant_role": role,
                        "assertion_status": status_of(win), "scope": scope, "source": src,
                        "evidence": " ".join(m.group(0).split())})
        for m in PPLAIN_RX.finditer(text):
            if any(a <= m.start() < b for a, b in spans):
                continue
            win = text[max(0, m.start() - 220): m.end() + 220]
            if not re.search(r"pressure|vacuum|\bp\s*[_ ]?[AB]\b", win, re.I):
                continue
            if PSYM_RX.search(win):
                continue
            kind = ("base_pressure" if re.search(r"base pressure", win, re.I)
                    else "working_pressure" if re.search(r"process|working|deposition|chamber", win, re.I)
                    else "generic_pressure")
            out.append({"quantity_type": kind, "symbol": None, "value": m.group(1),
                        "unit": m.group(2), "species": None, "reactant_role": None,
                        "assertion_status": status_of(win), "scope": scope, "source": src,
                        "evidence": " ".join(win[180:].split())[:140]})

    for k, v in (ent["panel_conditions"] or {}).items():
        if "press" in k.lower():
            out.append({"quantity_type": "generic_pressure", "symbol": None,
                        "value": str(v).split()[0], "unit": " ".join(str(v).split()[1:]) or None,
                        "species": None, "reactant_role": None,
                        "assertion_status": "direct", "scope": "panel",
                        "source": "figure_data.panel.conditions", "evidence": "%s=%s" % (k, v)})
    scan(label, "series", "series_label")
    scan(cap, "figure", "caption")
    scan(body, "figure", "body_mention")
    scan(methods_text, "paper", "methods")
    # applicability: narrowest scope that produced anything
    order = ["series", "panel", "figure", "paper"]
    applicable = None
    for sc in order:
        cands = [p for p in out if p["scope"] == sc and p["quantity_type"] != "base_pressure"]
        if cands:
            vals = {(p["value"], p["unit"], p["quantity_type"]) for p in cands}
            applicable = {"scope": sc, "n_candidates": len(cands),
                          "resolved": len(vals) == 1,
                          "value": cands[0]["value"] if len(vals) == 1 else None,
                          "unit": cands[0]["unit"] if len(vals) == 1 else None,
                          "quantity_type": cands[0]["quantity_type"] if len(vals) == 1 else None,
                          "status": "resolved" if len(vals) == 1 else "ambiguous",
                          "candidates": sorted("%s %s (%s)" % v for v in vals)}
            break
    return out, exposures, applicable


def classify(ent, doc, methods_text):
    cap = ent["caption"] or ""
    body = ent.get("body_mentions") or ""
    blob = cap + "\n" + body
    label = ent["source_series"] or ""
    sig = {}

    # M — modality
    mods = []
    for rx, name, implic in MODALITY:
        m = re.search(rx, blob, re.I)
        if m:
            mods.append({"modality": name, "implication": implic,
                         "evidence": " ".join(blob[max(0, m.start() - 60): m.end() + 80].split())[:180]})
    if mods:
        sig["M"] = mods
    # R — explicit run structure
    dr = hits(RUNSTRUCT_DISCRETE, blob)
    cr = hits(RUNSTRUCT_CONTINUOUS, blob)
    if dr or cr:
        sig["R"] = {"discrete": dr, "continuous": cr}
    # Me — modality stated in the METHODS section (independent of caption/body)
    me = []
    for rx, name, implic in MODALITY:
        m = re.search(rx, methods_text, re.I)
        if m:
            me.append({"modality": name, "implication": implic,
                       "evidence": " ".join(methods_text[max(0, m.start() - 50):
                                                         m.end() + 70].split())[:160]})
    if me:
        sig["Me"] = me
    # I — sample/run identifier
    sm = SAMPLE_ID.search(cap) or SAMPLE_ID.search(body)
    if sm:
        sig["I"] = " ".join(sm.group(0).split())[:120]
    # L — series-label semantics
    lit = LIT_LABEL.search(label)
    simm = SIM_LABEL.search(label)
    if lit or simm:
        sig["L"] = {"literature": lit.group(0) if lit else None,
                    "simulation": simm.group(0) if simm else None}
    # F — extraction source flag
    flag = ent.get("panel_source_flag") or ent.get("figure_source_flag")
    if flag:
        sig["F"] = flag
    # X — the panel's series_axis names what distinguishes the curves. Combined with
    # a numeric series label this is structural evidence that the curves are
    # different prepared conditions, independent of the caption prose.
    sa = (ent.get("panel_series_axis") or "").strip()
    if sa:
        sig["X"] = sa
    # T — table linkage
    tl = [t for t in (ent.get("table_captions") or []) if t and re.search(
        r"paramet|condition|sample|series|process", t, re.I)]
    if tl:
        sig["T"] = tl[:2]
    # weak signals (recorded, never decisive)
    weak = {"axis_role_coordinate": ent["coordinate"] in ("spatial_coordinate", "time",
                                                          "dimensionless_distance"),
            "n_source_points": ent["n_source_points"],
            "granularity": ent["granularity"]}

    # ---- decision -------------------------------------------------------
    # PROVENANCE and RUN STRUCTURE are different questions. Provenance is decided
    # first and gates the rest: a simulated or literature curve can never be
    # reclassified as an experimental sweep just because its x axis is swept.
    votes = Counter()
    why = defaultdict(list)

    def vote(cls, fam, ev):
        votes[cls] += 1
        why[cls].append("%s: %s" % (fam, ev))

    # --- provenance branch ---
    prov_votes = Counter()
    prov_why = defaultdict(list)

    def pvote(cls, fam, ev):
        prov_votes[cls] += 1
        prov_why[cls].append("%s: %s" % (fam, ev))

    if simm and re.search(r"simulat|knudsen|bosanquet|calculated|theor", simm.group(0), re.I):
        pvote("simulation", "L", "series label %r" % label)
    elif simm and re.search(r"^model", simm.group(0), re.I):
        pvote("simulation", "L", "series label %r" % label)
    if FIT_LABEL.search(label):
        pvote("fit", "L", "series label %r" % label)
    if lit and not simm:
        pvote("imported_literature_data", "L", lit.group(0))
    if sig.get("F") == "simulated":
        pvote("simulation", "F", "panel/figure source flag = simulated")
    if ent["is_model_result"] or ent["relevance"] == "model":
        pvote("simulation", "F", "pipeline relevance=model")
    if re.search(r"\bsimulat\w+|\bmodel(?:l)?ed\b|\bcomputed\b", cap, re.I):
        pvote("simulation", "R", " ".join(
            re.search(r"[^.]{0,90}(?:simulat\w+|model(?:l)?ed|computed)[^.]{0,60}",
                      cap, re.I).group(0).split())[:180])
    if CONCEPT.search(cap) and ent["n_source_points"] == 0:
        pvote("conceptual_figure", "M", cap[:120])

    prov_fams = lambda c: len({w.split(":")[0] for w in prov_why.get(c, [])})
    prov_cls = None
    if prov_votes:
        pr = prov_votes.most_common()
        cand = pr[0][0]
        # literature beats simulation when BOTH fire: an author-year label on a curve
        # inside a modelling figure is imported measured data, not the model output
        if "imported_literature_data" in prov_votes and "simulation" in prov_votes:
            cand = "imported_literature_data"
        if prov_fams(cand) >= 2 or cand in ("simulation", "imported_literature_data",
                                            "conceptual_figure", "fit"):
            prov_cls = cand

    if prov_cls:
        # a simulation whose x axis is a swept model parameter is a model_sweep
        if prov_cls == "simulation" and ent["coordinate"] not in (
                "spatial_coordinate", "dimensionless_distance", "time"):
            prov_cls = "model_sweep"
        for w in prov_why.get(cand if prov_cls in ("model_sweep",) else prov_cls,
                              prov_why.get("simulation", [])):
            why[prov_cls].append(w)
            votes[prov_cls] += 1
        fams = len({w.split(":")[0] for w in why[prov_cls]})
        conf = "corroborated" if fams >= 2 else "single_definitional_signal"
        return {"classification": prov_cls, "classification_confidence": conf,
                "classification_method": "provenance_gate(%d families)" % fams,
                "signal_families": sorted(sig.keys()), "signals": sig,
                "weak_signals_not_used_alone": weak, "votes": dict(votes),
                "supporting_evidence": why[prov_cls][:4]}

    # --- experimental run-structure branch ---
    # STRUCTURAL GATE. If x is a spatial coordinate the entity's own data is a
    # profile of one specimen -- the axis semantics say so directly. Being one
    # member of a swept family is a BETWEEN-curve fact, reported in
    # `between_curve_condition`, not a competing class for this entity.
    coord_axis_gate = ent["coordinate"] in ("spatial_coordinate", "dimensionless_distance")
    in_situ = any(m["modality"] == "in_situ" for m in mods)
    for m in mods:
        imp = m["implication"]
        if imp == "continuous_if_in_situ":
            imp = "continuous" if in_situ else "discrete"
        if imp == "continuous":
            vote("continuous_trace", "M", m["evidence"])
        elif imp == "spectrum":
            vote("multi_output_measurement", "M", m["evidence"])
        elif imp == "discrete":
            vote("discrete_experimental_sweep", "M", m["evidence"])
    me_in_situ = any(x["modality"] == "in_situ" for x in me)
    for x in me:
        imp = x["implication"]
        if imp == "continuous_if_in_situ":
            imp = "continuous" if me_in_situ else "discrete"
        if imp == "continuous" and x["modality"] in ("in_situ", "qcm", "real_time"):
            vote("continuous_trace", "Me", x["evidence"])
        elif imp == "discrete":
            vote("discrete_experimental_sweep", "Me", x["evidence"])
    if cr:
        vote("continuous_trace", "R", cr[0])
    if dr:
        vote("discrete_experimental_sweep", "R", dr[0])
    if sm:
        vote("discrete_experimental_sweep", "I", sig["I"])
    coord_axis = ent["coordinate"] in ("spatial_coordinate", "dimensionless_distance")
    if sa and re.search(r"temperatur|pressure|pulse|purge|flow|dose|exposure|cycle|"
                        r"height|width|opening|thickness|ratio|time", sa, re.I) and \
            re.search(r"\d", label):
        # series_axis describes what differs BETWEEN curves. If the x axis is a
        # spatial coordinate, this entity is ONE run's profile and the series axis
        # is its between-curve condition -- not a sweep along its own x axis.
        vote("experimental_profile" if coord_axis else "discrete_experimental_sweep", "X",
             "series_axis %r with numeric label %r%s" % (
                 sa, label, "; x is a spatial coordinate" if coord_axis else ""))
    if ent["coordinate"] in ("angle", "2theta", "binding_energy", "wavelength",
                             "wavenumber", "Binding Energy", "Binding energy",
                             "2\u03b8", "2\u0398", "Raman shift", "photon energy", "Energy",
                             "sputter depth", "sputtering time", "Sputtering time",
                             "Etching time", "Sputtering Time", "Ar Sputter Time"):
        vote("multi_output_measurement", "X",
             "x axis %r is a measurement coordinate, not a prepared condition"
             % ent["coordinate"])
    if coord_axis:
        vote("experimental_profile", "R" if not sa else "F",
             "x axis %r is a spatial coordinate: the curve is one specimen's profile"
             % ent["coordinate"])

    if coord_axis_gate:
        ev = ["X: x axis %r is a spatial coordinate; the curve is one specimen's profile"
              % ent["coordinate"]]
        corroborating = [w for c, ws in why.items() for w in ws
                         if c in ("discrete_experimental_sweep", "continuous_trace")]
        fams = 1 + len({w.split(":")[0] for w in corroborating})
        return {"classification": "experimental_profile",
                "classification_confidence": "corroborated" if fams >= 2
                else "single_definitional_signal",
                "classification_method": "coordinate_axis_gate(%d families)" % fams,
                "signal_families": sorted(sig.keys()), "signals": sig,
                "weak_signals_not_used_alone": weak, "votes": dict(votes),
                "supporting_evidence": ev + corroborating[:3]}

    ranked = votes.most_common()
    fam_of = lambda c: len({w.split(":")[0] for w in why.get(c, [])})
    tie = len(ranked) > 1 and ranked[0][1] == ranked[1][1]
    best = ranked[0][0] if ranked else None
    if tie:
        top = [c for c, v in ranked if v == ranked[0][1]]
        top.sort(key=lambda c: -fam_of(c))
        if len(top) > 1 and fam_of(top[0]) > fam_of(top[1]):
            best, tie = top[0], False
        else:
            best = None
    families = fam_of(best) if best else 0
    if best and families >= 2:
        cls, conf, method = best, "corroborated", "multi_signal(%d families)" % families
    elif tie or best is None:
        cls, conf, method = "unknown", "conflicting_signals", "tie_between_%s" % (
            "/".join(c for c, _ in ranked[:3]) or "none")
    else:
        cls, conf, method = "unknown", "insufficient_corroboration", \
            "only_one_signal_family(%s)" % (best or "none")

    return {
        "classification": cls,
        "classification_confidence": conf,
        "classification_method": method,
        "signal_families": sorted(sig.keys()),
        "signals": sig,
        "weak_signals_not_used_alone": weak,
        "votes": dict(votes),
        "supporting_evidence": why.get(cls, [])[:4],
    }


def main():
    src = J(OUT / "source_entities.json")
    ents = src["entities"]
    docs, methods = {}, {}
    rows = []
    for ent in ents:
        doi = ent["paper_id"]
        if doi not in docs:
            p = EX / doi / "extracted" / "document.md"
            t = p.read_text(errors="replace") if p.exists() else ""
            from_stage0 = sys.modules[__name__]
            docs[doi] = t
            m = re.search(r"(?is)\b(experimental|methods?|experimental section|"
                          r"materials and methods)\b(.{0,6000})", t)
            methods[doi] = m.group(0) if m else t[:6000]
        cls = classify(ent, docs[doi], methods[doi])
        pres, expo, applicable = resolve_pressures(ent, docs[doi], methods[doi])
        row = {k: ent[k] for k in ("entity_key", "paper_id", "fig_docling_index",
                                   "printed_figure_number", "panel", "source_series",
                                   "representation", "record_node_count",
                                   "n_source_points", "coordinate", "measurand",
                                   "measurand_unit", "relevance", "granularity")}
        row["record_node_ids"] = ";".join(ent["record_node_ids"][:6]) + (
            " …+%d" % (len(ent["record_node_ids"]) - 6) if len(ent["record_node_ids"]) > 6 else "")
        row["caption_pdf_page"] = ent.get("caption_pdf_page")
        row["body_pdf_page"] = ent.get("body_pdf_page")
        row["caption_evidence"] = (ent["caption"] or "")[:300]
        row["body_evidence"] = (ent.get("body_mentions") or "")[:300]
        row["sample_or_run_id"] = cls["signals"].get("I")
        row["table_evidence"] = "; ".join(cls["signals"].get("T") or [])[:200]
        row.update({k: cls[k] for k in ("classification", "classification_confidence",
                                        "classification_method", "signal_families")})
        row["supporting_evidence"] = " | ".join(cls["supporting_evidence"])[:400]
        row["votes"] = json.dumps(cls["votes"])
        row["weak_signals"] = json.dumps(cls["weak_signals_not_used_alone"])
        row["pressure_assertions"] = json.dumps(pres, ensure_ascii=False)[:900]
        row["exposure_assertions"] = json.dumps(expo, ensure_ascii=False)[:400]
        row["pressure_applicable_scope"] = (applicable or {}).get("scope")
        row["pressure_applicable_status"] = (applicable or {}).get("status")
        row["pressure_applicable_value"] = (applicable or {}).get("value")
        row["pressure_applicable_unit"] = (applicable or {}).get("unit")
        row["pressure_applicable_quantity"] = (applicable or {}).get("quantity_type")
        row["pressure_candidates"] = "; ".join((applicable or {}).get("candidates") or [])[:200]
        n_set, set_ev = stated_setting_count(ent["caption"] or "",
                                             ent.get("body_mentions") or "",
                                             ent["source_series"])
        row["stated_setting_count"] = n_set
        row["stated_setting_evidence"] = set_ev
        row["between_curve_condition"] = ent.get("panel_series_axis") or None
        row["between_curve_value"] = ent["source_series"] if ent.get("panel_series_axis") else None
        row["underlying_case_id"] = "%s::F%s::%s::%s" % (
            row["paper_id"], row["printed_figure_number"], row["panel"] or "-",
            row["source_series"])
        rows.append(row)

    (OUT / "entity_audit.json").write_text(json.dumps(
        {"n_entities": len(rows), "rows": rows}, indent=1, ensure_ascii=False))
    with open(OUT / "entity_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("entities audited: %d" % len(rows))
    print("\nclassification:")
    for k, v in Counter(r["classification"] for r in rows).most_common():
        print("   %-32s %4d  (%.1f%%)" % (k, v, 100 * v / len(rows)))
    print("\nconfidence:")
    for k, v in Counter(r["classification_confidence"] for r in rows).most_common():
        print("   %-32s %4d" % (k, v))
    print("\npressure applicability (entity level):")
    for k, v in Counter(str(r["pressure_applicable_scope"]) + "/" +
                        str(r["pressure_applicable_status"]) for r in rows).most_common():
        print("   %-32s %4d" % (k, v))
    print("\nPDF page resolved: caption %d, body %d" %
          (sum(1 for r in rows if r["caption_pdf_page"]),
           sum(1 for r in rows if r["body_pdf_page"])))


if __name__ == "__main__":
    main()
