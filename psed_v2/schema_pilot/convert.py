#!/usr/bin/env python3
"""Turns the draft tables of each pilot paper (<paper>/draft/*.csv, six tables as first filled) into the simplified schema:
paper, sample, condition, series, value (no link table; links become series rows). Uses the fixed lists of lists.py.

    python3 psed_v2/schema_pilot/convert.py

- sample keeps identity only; temperature and cycles become condition rows; groups and model runs are sample rows
  (kind = group with members; kind = model_run for simulations);
- a multi-id or "*" sample reference in series or value becomes a group; "*" stays only in condition (paper-wide rows);
- qualifiers are key=value from lists.QUALIFIERS; anything else goes to note; methods map to lists.METHODS;
- quantities outside lists.QUANTITIES become "other" with label_as_printed;
- links: a link already covered by a series of the same figure and panel sets that series' link status; an uncovered
  link becomes a series row of its kind without points;
- points: from cases/points.json (as drafted) and, where empty, from v1_points.json (v1 points accepted in v1_points_check.csv).
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L

PAPERS = {"10.1039_d0cp03358h": "yim20", "10.1021_acs.chemmater.2c01154": "mat22", "10.1116_6.0003182": "gre23"}
COLS = {
    "paper": ["paper_id", "year", "topic"],
    "sample": ["sample_id", "paper_id", "kind", "label_as_printed", "parent_sample", "members", "material", "precursor", "coreactant",
               "process_mode", "reactor", "structure_class", "structure_dims", "width_kind", "note", "evidence"],
    "condition": ["condition_id", "sample_id", "kind", "quantity", "label_as_printed", "qualifiers", "value", "unit", "data_kind",
                  "applies_when", "note", "evidence"],
    "series": ["series_id", "sample_id", "kind", "figure", "panel", "method", "x_id", "x_qualifiers", "x_label", "y_id", "y_qualifiers",
               "y_label", "z_id", "z_label", "data_kind", "link_status", "points_source", "points", "reused_from", "note", "evidence"],
    "value": ["value_id", "sample_id", "from_series", "quantity", "label_as_printed", "qualifiers", "value", "value_min", "value_max",
              "censor", "unit", "data_kind", "method", "relation", "regime", "cited_ref", "note", "evidence"],
}
MEAS_Q = {"spot_size", "reflectometer_magnification", "afm_scan_area", "measurement_instrument", "probe_resolution", "eds_voltage",
          "xrd_scan", "raman_laser", "xps_pass_energy", "scan_step", "electrode", "magnification", "eds_take_off"}
PREP_Q = {"degas_temperature", "pressing_pressure", "pressing_time", "substrate", "substrate_preparation", "pillar_layout"}


def rd(p):
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def split_q(raw, extra=""):
    """quantity string 'base{k=v,...} (new)' plus a qualifier column -> base id, label, qualifiers, note."""
    inner = re.search(r"\{(.*?)\}", raw)
    base = re.sub(r"\{.*?\}", "", raw).replace("(new)", "").strip()
    base = L.ALIASES.get(base, base)
    parts = [p.strip() for p in re.split(r"[;,]", (inner.group(1) if inner else "") + ";" + (extra or "")) if p.strip()]
    good, note = [], []
    for p in parts:
        if "=" in p and not L.qualifiers_ok(p.replace(" ", "")):
            good.append(p.replace(" ", ""))
        else:
            note.append(p)
    label = raw.replace("(new)", "").strip() if base == "other" else ""
    if base not in L.QUANTITIES:
        label, base = raw.replace("(new)", "").strip(), "other"
        good = []
    return base, label, ";".join(dict.fromkeys(good)), "; ".join(note)


def ranges(v):
    v = (v or "").strip()
    m = re.match(r"^([<>])\s*(dl|[\d.eE+-]+)", v)
    if m:
        return ("", "", "", m.group(1) + ("dl" if m.group(2) == "dl" else "")) if m.group(2) == "dl" else ("", "", "", m.group(1))
    m = re.match(r"^([\d.]+(?:[eE][+-]?\d+)?)\s*(?:-|to|–)\s*([\d.]+(?:[eE][+-]?\d+)?)$", v)
    if m:
        return "", m.group(1), m.group(2), ""
    return v, "", "", ""


# values that summarize several runs and carry no sample in the draft: the group they describe (ALL = every run;
# T<lo>-<hi>,R<lo>-<hi> = the mat22 grid cells uT<T>R<ratio×100> in those ranges)
VALUE_GROUP = {
    **{f"yim20:v{n}": "ALL" for n in (157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 172, 173, 174, 175, 176, 179, 180)},
    "mat22:v210": "T150-150,R0-94", "mat22:v222": "T0-999,R0-94", "mat22:v223": "T150-999,R0-94", "mat22:v224": "T0-999,R0-94",
    "mat22:v225": "T0-999,R0-94", "mat22:v227": "T0-999,R80-80", "mat22:v230": "T0-999,R94-94", "mat22:v231": "T100-250,R50-80",
    "mat22:v232": "T100-250,R50-80", "mat22:v233": "T350-450,R20-20", "mat22:v234": "T350-450,R20-20", "mat22:v237": "T0-999,R94-94",
    "mat22:v240": "T100-250,R50-80", "mat22:v241": "T0-999,R0-94", "mat22:v242": "T100-100,R0-94", "mat22:v243": "T150-150,R0-94",
    "mat22:v244": "T100-100,R0-94", "mat22:v245": "T300-999,R0-94", "mat22:v262": "T0-999,R0-94", "mat22:v264": "T0-999,R0-94",
    "gre23:v014": "gre23:120", "gre23:v015": "gre23:160",
}


def convert(pid, key):
    D = HERE / pid / "draft"
    T = {t: rd(D / f"{t}.csv") for t in ("paper", "sample", "condition", "series", "value", "link")}
    samples = {}
    for s in T["sample"]:
        par = s["parent_sample"]
        kind = "reference" if re.search(r"bare|reference|uncoated", s["label_as_printed"] + s.get("evidence", ""), re.I) and not s["cycles"] else \
            ("channel" if par and re.search(r"channel", s["structure_class"] + s.get("evidence", ""), re.I) else "piece" if par else "run")
        samples[s["sample_id"]] = {**{c: s.get(c, "") for c in COLS["sample"]}, "kind": kind, "members": "", "note": ""}
    cond = []
    for s in T["sample"]:
        if s["temperature_C"]:
            cond.append(dict(sample_id=s["sample_id"], kind="process", quantity="deposition_temperature", qualifiers="kind=set_point",
                             value=s["temperature_C"], unit="°C", data_kind="stated", evidence=s["evidence"]))
        if s["cycles"]:
            cond.append(dict(sample_id=s["sample_id"], kind="process", quantity="cycle_number", value=s["cycles"], unit="", data_kind="stated", evidence=s["evidence"]))
    groups = {}

    def group_of(ids, why):
        ids = [i for i in ids if i]
        if ids == ["*"]:
            ids = [k for k, v in samples.items() if v["kind"] == "run"]
        mem = ";".join(sorted(dict.fromkeys(ids)))
        if mem not in groups:
            gid = f"{key}:G{len(groups) + 1}"
            groups[mem] = gid
            samples[gid] = {**{c: "" for c in COLS["sample"]}, "sample_id": gid, "paper_id": pid, "kind": "group", "label_as_printed": "u",
                            "members": mem, "note": why, "evidence": why}
        return groups[mem]

    def sample_ref(raw, why):
        raw = (raw or "").strip()
        if not raw:
            return ""
        if raw == "*" or ";" in raw:
            return group_of(raw.split(";"), why)
        m = re.match(r"^(\S+) \(all (\S+) samples\)$", raw)         # "key:grid (all uT*R* samples)": a group by pattern
        if m:
            import fnmatch
            gid = m.group(1)
            if gid not in samples:
                mem = sorted(k for k, v in samples.items() if v["kind"] != "group" and fnmatch.fnmatch(k.split(":", 1)[1], m.group(2)))
                samples[gid] = {**{c: "" for c in COLS["sample"]}, "sample_id": gid, "paper_id": pid, "kind": "group", "label_as_printed": "u",
                                "members": ";".join(mem), "note": f"all samples {m.group(2)}", "evidence": why}
            return gid
        if raw not in samples and raw.startswith(key + ":"):          # a group id used in the draft without a sample row
            samples[raw] = {**{c: "" for c in COLS["sample"]}, "sample_id": raw, "paper_id": pid, "kind": "group", "label_as_printed": "u",
                            "members": "", "note": "group named in the draft; members in the evidence", "evidence": why}
        return raw

    # ---- conditions
    for c in T["condition"]:
        base, label, qual, note = split_q(c["quantity"], "")
        stp = (c.get("step") or "").strip()
        step = {"A": "reactant_A", "B": "reactant_B", "purge": "", "plasma": "plasma", "none": ""}.get(stp, stp)
        if step and "step=" not in qual and step in L.QUALIFIERS["step"]:
            qual = ";".join(filter(None, [qual, f"step={step}"]))
        raw = re.sub(r"\{.*", "", c["quantity"]).replace("(new)", "").strip()
        kind = "measurement" if raw in MEAS_Q or re.search(r"magnification|spot|scan|laser|pass energy|kV|electrode|detector|instrument", c["quantity"] + c.get("evidence", ""), re.I) and base == "other" \
            else "substrate_prep" if raw in PREP_Q else "process"
        sid = c["sample_id"] if c["sample_id"] == "*" else sample_ref(c["sample_id"], c["evidence"])
        cond.append(dict(sample_id=sid, kind=kind, quantity=base, label_as_printed=label, qualifiers=qual, value=c["value"], unit=c["unit"],
                         data_kind=c["data_kind"] if c["data_kind"] in L.DATA_KINDS_CONDITION else "stated", note=note, evidence=c["evidence"]))
    # ---- series
    series = []
    v1 = {}
    vp = HERE / "v1_points.json"                              # accepted v1 points (v1_points_check.csv), stored here so the conversion is reproducible
    if vp.exists():
        v1 = {k: v for k, v in json.loads(vp.read_text(encoding="utf-8"))["series"].items() if k.startswith(key + ":")}
    for s in T["series"]:
        dk = s["data_kind"]
        sid = s["sample_ids"].strip()
        if dk in ("simulation", "schematic") and (not sid or sid == "*"):
            sid = f"{key}:model_F{s['figure']}"
            if sid not in samples:
                samples[sid] = {**{c: "" for c in COLS["sample"]}, "sample_id": sid, "paper_id": pid, "kind": "model_run", "label_as_printed": "u",
                                "note": "model or sketch of Fig. " + s["figure"], "evidence": f"Fig. {s['figure']}"}
        else:
            sid = sample_ref(sid, s["evidence"] or f"Fig. {s['figure']}")
        xb, xl, xq, xn = split_q(s["x_id"], f"by={s['x_by']}" if s["x_by"] in L.QUALIFIERS["by"] else "")
        yb, yl, yq, yn = split_q(s["y_id"], f"reference={s['y_reference']}" if s["y_reference"] in L.QUALIFIERS["reference"] else "")
        meth = L.method_id(s["method"])
        txt = (s["method"] + " " + s["evidence"]).lower()
        kind = "map" if "map" in txt else "spectrum" if meth in ("xps", "raman", "xrd") else "image" if not s["x_id"] and not s["y_id"] else "plot"
        pts, src = s.get("points", ""), ("cases/points.json" if s.get("points") else "")
        v1note = ""
        if not pts and s["series_id"] in v1:
            pts, src, v1note = json.dumps(v1[s["series_id"]]["points"]), "v1 (checked against the figure)", "v1 check: " + v1[s["series_id"]]["note"]
        series.append(dict(series_id=s["series_id"], sample_id=sid, kind=kind, figure=s["figure"], panel=s["panel"], method=meth, x_id=xb, x_qualifiers=xq,
                           x_label=xl, y_id=yb, y_qualifiers=yq, y_label=yl, data_kind=dk if dk in L.DATA_KINDS_SERIES else "measured", link_status="",
                           points_source=src, points=pts, reused_from=s.get("reused_from", ""),
                           note="; ".join(filter(None, [s["method"] if meth != s["method"] else "", xn, yn, v1note, "" if s["x_by"] in L.QUALIFIERS["by"] or not s["x_by"] else f"x measured from: {s['x_by']}",
                                                       "" if s["y_reference"] in L.QUALIFIERS["reference"] or not s["y_reference"] else f"y reference: {s['y_reference']}"])),
                           evidence=s["evidence"]))
    # ---- links into series
    def members(sid):
        m = samples.get(sid, {}).get("members", "")
        return set(m.split(";")) if m else {sid}
    FM = {}
    for r in csv.DictReader((HERE.parent / "cases" / "figures.csv").open(encoding="utf-8")):
        if r["paper_id"] == pid and r["method"]:
            FM.setdefault((r["figure"], r["panel"][:1]), r["method"]); FM.setdefault((r["figure"], ""), r["method"])
    n_new = 0
    for l in T["link"]:
        fig = re.sub(r"^(Fig\.|Table)\s*", "", l["figure"]).strip()
        istable = l["figure"].startswith("Table")
        sid = sample_ref(l["sample_id"], l["evidence"])
        cov = [s for s in series if s["figure"] == fig and (not l["panel"] or s["panel"].startswith(l["panel"][:1])) and (sid in members(s["sample_id"]) or s["sample_id"] == sid)]
        if cov and not istable:
            for s in cov:
                s["link_status"] = "stated" if l["stated_or_inferred"] == "stated" or s["link_status"] == "stated" else "inferred"
            continue
        n_new += 1
        kind = "table" if istable else l["kind"] if l["kind"] in L.SERIES_KINDS else "image"
        series.append(dict(series_id=f"{key}:L{n_new}", sample_id=sid, kind=kind, figure=("Table " + fig) if istable else fig, panel=l["panel"],
                           method="tabulated" if istable else L.method_id(FM.get((fig, l["panel"][:1])) or FM.get((fig, "")) or l["evidence"]),
                           x_id="", x_qualifiers="", x_label="", y_id="", y_qualifiers="", y_label="", data_kind="measured", link_status=l["stated_or_inferred"],
                           points_source="", points="", reused_from="", note="from the draft link table", evidence=l["evidence"]))
    # ---- values
    vals = []
    ser_sample = {s["series_id"]: s["sample_id"] for s in series}
    for v in T["value"]:
        base, label, qual, note = split_q(v["quantity"], v.get("qualifiers", ""))
        val, vmin, vmax, cen = ranges(v["value"])
        dk = v["data_kind"] if v["data_kind"] in L.DATA_KINDS_VALUE else "measured"
        sid = v["sample_id"].strip()
        if not sid and v["from_series"]:
            sid = ser_sample.get(v["from_series"], "")
        if not sid and dk in ("chosen input", "assumed") and re.search(r"Fig\.\s*(\d+)", v["evidence"]):
            f = re.search(r"Fig\.\s*(\d+)", v["evidence"]).group(1)
            sid = f"{key}:model_F{f}" if f"{key}:model_F{f}" in samples else ""
        if not sid and dk in ("chosen input", "assumed"):
            sid = f"{key}:model"
            samples.setdefault(sid, {**{c: "" for c in COLS["sample"]}, "sample_id": sid, "paper_id": pid, "kind": "model_run", "label_as_printed": "u",
                                     "note": "the paper's model, inputs stated in the text", "evidence": "text"})
        spec = VALUE_GROUP.get(v["value_id"])
        if not sid and spec:
            if spec == "ALL":
                sid = group_of(["*"], "all runs of the paper")
            elif spec.startswith("T"):
                (t0, t1), (r0, r1) = [tuple(map(int, p_[1:].split("-"))) for p_ in spec.split(",")]
                mem = [k for k in samples if re.match(rf"{key}:uT(\d+)R(\d+)$", k) and t0 <= int(re.match(rf"{key}:uT(\d+)R(\d+)$", k).group(1)) <= t1
                       and r0 <= int(re.match(rf"{key}:uT(\d+)R(\d+)$", k).group(2)) <= r1]
                sid = group_of(mem, f"grid cells with T {t0}-{t1} °C and H2 ratio {r0 / 100:.2f}-{r1 / 100:.2f}")
            else:
                sid = spec
        sid = sample_ref(sid, v["evidence"]) if sid else ""
        cited = ""
        if dk == "literature":
            m = re.search(r"(ref\.?\s*\d+|[A-Z][a-z]+ (?:et al\.? )?\(?(?:19|20)\d\d\)?)", (v.get("qualifiers", "") + " " + v["evidence"] + " " + v.get("relation", "")))
            cited = m.group(1) if m else "see evidence"
        vals.append(dict(value_id=v["value_id"], sample_id=sid, from_series=v["from_series"], quantity=base, label_as_printed=label, qualifiers=qual,
                         value=val, value_min=vmin, value_max=vmax, censor=cen, unit=v["unit"], data_kind=dk, method=L.method_id(v["method"]),
                         relation=v["relation"], regime=v["regime"], cited_ref=cited,
                         note="; ".join(filter(None, [note, v["method"] if v["method"] and L.method_id(v["method"]) != v["method"] else ""])), evidence=v["evidence"]))
    # ---- ids, dedupe, write
    def dedupe(rows, keys):
        seen, out = set(), []
        for r in rows:
            k = tuple(r.get(c, "") for c in keys)
            if k not in seen:
                seen.add(k); out.append(r)
        return out
    cond = dedupe(cond, [c for c in COLS["condition"] if c != "condition_id"])
    for i, c in enumerate(cond, 1):
        c["condition_id"] = f"{key}:c{i:03d}"
    series = dedupe(series, [c for c in COLS["series"] if c not in ("series_id",)])
    vals = dedupe(vals, [c for c in COLS["value"] if c != "value_id"])
    for t, rows in (("paper", T["paper"]), ("sample", list(samples.values())), ("condition", cond), ("series", series), ("value", vals)):
        with (HERE / pid / f"{t}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS[t], extrasaction="ignore"); w.writeheader()
            w.writerows([{c: r.get(c, "") for c in COLS[t]} for r in rows])
    return {t: len(rd(HERE / pid / f"{t}.csv")) for t in COLS}, {t: len(T[t]) for t in T}


if __name__ == "__main__":
    for pid, key in PAPERS.items():
        after, before = convert(pid, key)
        print(pid, "before", before, "after", after)
