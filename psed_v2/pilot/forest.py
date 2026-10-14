#!/usr/bin/env python3
"""The forest: the three paper trees (<paper_id>.facts.csv with parent/links) read together.

    python3 psed_v2/pilot/forest.py          # Cases 9 and 10 rebuilt from the forest only, against the hand-made CSVs

Used by report.py for the quantity picker and scatter of the Facts tab. The rules, all local to a tree:
- leaves(q): every fact of quantity q with a numeric value (or a range) in any paper; cited when its type is cited or a
  cited work (:refs:N) is among its ancestors; scope = the nearest run, group, process or cited work above it.
- context(leaf): the nearest-scope settings. Walk up the parent chain; at each ancestor take the ancestor itself and its
  children; the first fact with a value seen for a quantity is that quantity's context. When two siblings at the same
  level carry the same quantity (e.g. three design heights under process), that quantity is "ambiguous" at that level
  and is not taken from farther up; one exact value beside censored bounds (17000 Torr-s beside ">1e4") wins.
- flags(leaves): for the quantity's leaves across all papers, the majority value of every qualifier key (absent counts)
  and the majority unit; a leaf is flagged with each key, or "unit", where it differs from the majority.
No unit conversion and no merging: values are as printed, so a scatter mixes units unless the flag says otherwise.

__main__ rebuilds Case 9 (sticking values) and Case 10 (coated EAR against exposure) from the forest alone and compares them
with the hand-made sticking_reported.csv and exposure_ear.csv, row by row for the three pilot papers: the points the forest
gives, the CSV numbers it matches (same paper, within 2% or inside a stated range), and each point only one side has, with
the reason (REASONS, written by hand after reading both sides).
"""
import collections, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from elements import PAPERS  # noqa: E402
from facts import num  # noqa: E402

SCOPES = ("run", "group", "process", "cited", "paper")


def quals(s):
    return dict(p.split("=", 1) for p in s.split(";") if "=" in p)


def value_of(row):
    """(value, low, high): a single value, or a range with value = its midpoint (geometric when both are positive)."""
    v, lo, hi = num(row["value"]), num(row["value_min"]), num(row["value_max"])
    if v is None and lo is not None and hi is not None:
        v = (lo * hi) ** 0.5 if lo > 0 and hi > 0 else (lo + hi) / 2
    elif v is None:
        v = lo if lo is not None else hi
    return v, lo, hi


class Forest:
    def __init__(self):
        self.papers = {}
        for pid, key in PAPERS.items():
            rows = list(csv.DictReader((HERE / f"{pid}.facts.csv").open(encoding="utf-8")))
            kids = collections.defaultdict(list)
            for r in rows:
                if r.get("parent"):
                    kids[r["parent"]].append(r)
            self.papers[key] = dict(pid=pid, rows=rows, byid={r["fact_id"]: r for r in rows}, kids=kids)

    def ancestors(self, key, fid):
        P, out, i = self.papers[key], [], self.papers[key]["byid"][fid].get("parent", "")
        while i and i in P["byid"] and i not in out:
            out.append(i); i = P["byid"][i].get("parent", "")
        return out

    def cited(self, key, fid):
        P = self.papers[key]
        return P["byid"][fid]["type"] == "cited" or any(":refs:" in a for a in self.ancestors(key, fid))

    def scope(self, key, fid):
        P = self.papers[key]
        return next((a for a in self.ancestors(key, fid) if P["byid"][a]["type"] in SCOPES), "")

    def context(self, key, fid):
        """quantity -> row (nearest scope first) or "ambiguous"."""
        P, ctx = self.papers[key], {}
        for a in self.ancestors(key, fid):
            seen = collections.Counter()
            cands = [P["byid"][a]] + P["kids"].get(a, [])
            for c in cands:
                if "#" in c["fact_id"] and c["fact_id"] != fid and c["quantity"] and c["quantity"] != "other" and value_of(c)[0] is not None:
                    seen[c["quantity"]] += 1
            exact = collections.Counter(c["quantity"] for c in cands if c["quantity"] in seen and not c["censor"]
                                        and "#" in c["fact_id"] and c["fact_id"] != fid and value_of(c)[0] is not None)
            for c in cands:
                q = c["quantity"]
                if q in seen and q not in ctx:
                    if seen[q] == 1:
                        ctx[q] = c
                    elif exact[q] == 1:                       # one exact value beside bounds: the value wins
                        ctx[q] = next(x for x in cands if x["quantity"] == q and not x["censor"] and "#" in x["fact_id"] and x["fact_id"] != fid)
                    else:
                        ctx[q] = "ambiguous"
        return ctx

    def leaves(self, quantities):
        qs = {quantities} if isinstance(quantities, str) else set(quantities)
        out = []
        for key, P in self.papers.items():
            for r in P["rows"]:
                if "#" in r["fact_id"] and r["quantity"] in qs:
                    v, lo, hi = value_of(r)
                    if v is None:
                        continue
                    out.append(dict(key=key, fid=r["fact_id"], row=r, value=v, low=lo, high=hi, unit=r["unit"], censor=r["censor"],
                                    quals=quals(r["qualifiers"]), cited=self.cited(key, r["fact_id"]), scope=self.scope(key, r["fact_id"]),
                                    ctx=self.context(key, r["fact_id"])))
        return out

    @staticmethod
    def flags(leaves):
        """fid -> the qualifier keys (or "unit") where the leaf differs from the majority of these leaves."""
        keys = {k for l in leaves for k in l["quals"]}
        maj = {k: collections.Counter(l["quals"].get(k, "") for l in leaves).most_common(1)[0][0] for k in keys}
        unit = collections.Counter(l["unit"] for l in leaves).most_common(1)[0][0] if leaves else ""
        out = {}
        for l in leaves:
            f = [k for k in sorted(keys) if l["quals"].get(k, "") != maj[k]] + (["unit"] if l["unit"] != unit else [])
            if f:
                out[l["fid"]] = f
        return out

    def quantities(self):
        """quantity -> number of leaves (numeric, any paper), without "other"."""
        c = collections.Counter()
        for P in self.papers.values():
            for r in P["rows"]:
                if "#" in r["fact_id"] and r["quantity"] and r["quantity"] != "other" and value_of(r)[0] is not None:
                    c[r["quantity"]] += 1
        return dict(c)

    def page_fields(self):
        """Per paper key: fid -> dict(ctx, cited, scope, flag) for every numeric leaf, as report.py embeds them."""
        out = {k: {} for k in self.papers}
        for q in self.quantities():
            ls = self.leaves(q)
            fl = self.flags(ls)
            for l in ls:
                ctx = {q2: ("ambiguous" if r == "ambiguous" else [r["censor"] + r["value"] + (f"{r['value_min']}–{r['value_max']}" if r["value_min"] else "") + (" " + r["unit"] if r["unit"] else ""),
                                                                  value_of(r)[0], r["fact_id"], value_of(r)[1], value_of(r)[2]]) for q2, r in l["ctx"].items()}
                out[l["key"]][l["fid"]] = dict(ctx=ctx, cited=l["cited"], scope=l["scope"], flag=fl.get(l["fid"], []))
        return out


NUM = r"(?<![\w.^-])(\d+(?:\.\d+)?(?:e-?\d+)?)(?: ?(?:x|×) ?10\^?(-?\d+))?"    # the number rule Case 9 applies to the CSV value text
KEY = {pid: k for pid, k in PAPERS.items()}
TORR = 133.322
REASONS = {
    # Case 9, forest only
    "yim20:fig10.cap#14": "a simulation input (chosen input, Fig. 10 caption); the CSV lists reported fits and literature only",
    "yim20:s18.p3#6": "Table 2 footnote d, Vandalon et al. (2017) c_H2O at 100 °C; the CSV's literature row stops at the table body",
    "yim20:s18.p3#7": "Table 2 footnote d, Vandalon et al. (2017) c_TMA; the CSV's literature row stops at the table body",
    # Case 9, CSV only
    "yim20 0.0001 (Arts)": "not a Table 2 value as parsed: Arts' c_TMA is (0.5-2) × 10^-3 and c_H2O (0.8-2) × 10^-4; the stray '10^-4' cell of the split row (tab2.r6c6) was likely read as a value",
    "yim20:tab2.r5c7#1": "in the CSV as 'c_H2O (0.8-2)e-4 (Arts)' but the CSV's regex and the match see 'Arts' only in the c_TMA segment; see the CSV item line",
    "yim20 slope row": "16 front slopes and 5 x~50% values: inputs of the slope method, not sticking values (Case 9 skips this row too); all 16 are front_slope leaves of the forest, see 'derivable'",
    # Case 10
    "gre23:s6.p4#1": "a cited work (Gayle et al., ref. 9, silica aerogel): the CSV holds the corpus papers' own records only; both numbers are censored bounds",
    "gre23 per-run rows": "the CSV writes one record per run (120 and 120/160 °C, T 120 and 140); in the tree the aspect ratio (s6.p8#7) and the exposure (s6.p8#11) sit under process, the temperatures under each run, so the forest has one point with no T",
    "gre23 reading=lower": "'fully coated, a lower bound' is the Fig. 6 line-scan observation (fig6d#1, fig6f#1: Zn flat across the thickness), a fact without a value; the forest point carries no reading",
    "gre23 160 °C excluded": "the CSV leaves out the 160 °C run (metallic Zn, a claim of the paper); the forest point is run-less, so nothing to exclude",
    "gre23 sat density 9.8 nm-2, mass 123.5 amu": "hand-computed from the stated GPC with an assumed bulk density, and the DEZ molar mass from outside the paper; neither is a leaf, so the forest cannot normalize the exposure as Case 10 does",
}


def csv_items(row):
    """Case 9's CSV value cell as items (low, high, source, species): "0.1 (Dendooven 2009)", "(0.5-2)e-3 and 1e-4 (Arts 2019)",
    "c_H2O (0.8-2)e-4 (Arts)"; a fit row is one item with no source."""
    import re
    out = []
    text = row["value"] if row["data_kind"] == "literature" else re.sub(r"\([^)]*\)", "", row["value"])   # a fit row's notes carry no source
    for seg in re.split(r"[;,]", text):
        src = re.findall(r"\(([A-Z][a-z]+)[^)]*\)", seg)
        src = src[-1] if src and row["data_kind"] == "literature" else ""
        sp = "H2O" if "c_H2O" in seg else "TMA" if "c_TMA" in seg else ""
        t = re.sub(r"\([A-Z][^)]*\)", "", seg)
        for m in re.finditer(r"\(([\d.]+)-([\d.]+)\)e(-?\d+)", t):
            out.append((float(m.group(1)) * 10 ** int(m.group(3)), float(m.group(2)) * 10 ** int(m.group(3)), src, sp))
        t = re.sub(r"\([\d.]+-[\d.]+\)e-?\d+", "", t)
        for v in re.findall(NUM, re.sub(r"\([^)]*\)", "", t)):
            val = float(v[0]) * (10 ** int(v[1]) if v[1] else 1)
            if 1e-9 < val <= 1:
                out.append((val, val, src, sp))
    return out


def author(F, key, scope):
    """The first author named in a cited work's facts ("Dendooven et al. ...")."""
    import re
    for c in F.papers[key]["kids"].get(scope, []):
        m = re.match(r"(?:follow-up )?([A-Z][a-z]+) et al", c["statement"])
        if m:
            return m.group(1)
    return ""


def close(leaf, lo, hi):
    if leaf["low"] is not None and leaf["high"] is not None:
        if lo != hi:
            return abs(leaf["low"] - lo) <= 0.02 * lo and abs(leaf["high"] - hi) <= 0.02 * hi
        return leaf["low"] * 0.98 <= lo <= leaf["high"] * 1.02
    return lo == hi and abs(leaf["value"] - lo) <= 0.02 * abs(lo)


def case9(F):
    print("== Case 9, sticking values: the forest against sticking_reported.csv")
    ls = F.leaves({"lumped_sticking_coefficient", "initial_sticking_coefficient"})
    for l in ls:
        T = l["ctx"].get("deposition_temperature")
        T = "T ambiguous" if T == "ambiguous" else (f"T {T['value'] or T['value_min'] + '–' + T['value_max']} {T['unit']}" if T else "no T in scope")
        print(f"   forest {l['key']} {l['fid'].split(':')[1]:14s} {l['quals'].get('species', '?'):4s} {l['row']['censor']}{l['row']['value'] or l['row']['value_min'] + '–' + l['row']['value_max']:>12s}"
              f"  {l['row']['data_kind']:13s} {'cited ' + l['scope'].split(':')[-1] + ' ' + author(F, l['key'], l['scope']) if l['cited'] else 'own, ' + l['scope'].split(':')[-1]:24s} {T}")
    der = [l for l in F.leaves("front_slope") if l["quals"].get("reference") == "entrance"]
    print(f"   derivable by the case's transform c = 13.9·slope²: {len(der)} front slopes dθ/dx~ (Table 1), c from {min(13.9 * l['value'] ** 2 for l in der):.1e} to {max(13.9 * l['value'] ** 2 for l in der):.1e}")
    rows = [r for r in csv.DictReader((HERE / "sticking_reported.csv").open(encoding="utf-8")) if r["paper_id"] in KEY]
    n_items, matched, csv_only, used = 0, 0, [], set()
    for r in rows:
        k = KEY[r["paper_id"]]
        if r["quantity"].startswith("slope") or r["quantity"] == "none":
            csv_only.append((f"{k} slope row", REASONS[f"{k} slope row"])); continue
        for lo, hi, src, sp in csv_items(r):
            n_items += 1
            lab = f"{k} {lo:g}" + (f"–{hi:g}" if hi != lo else "") + (f" ({src})" if src else "") + (f" {sp}" if sp else "")
            hits = [l for l in ls if l["key"] == k and close(l, lo, hi) and (author(F, k, l["scope"]) == src if src else not l["cited"])
                    and (not sp or l["quals"].get("species") == sp)]
            if hits:
                matched += 1; used.update(l["fid"] for l in hits)
                print(f"   CSV item    {lab}: " + ", ".join(l["fid"].split(":")[1] + " (" + l["quals"].get("species", "") + (", inside its range" if lo == hi and l["low"] is not None and l["low"] != l["high"] else "") + ")" for l in hits))
            else:
                csv_only.append((lab, REASONS.get(lab, "no forest leaf with this value under that cited work")))
    f_only = [(l["fid"], REASONS.get(l["fid"], "no CSV item with this value")) for l in ls if l["fid"] not in used]
    print(f"   forest {len(ls)} leaves ({sum(not l['cited'] for l in ls)} own, {sum(l['cited'] for l in ls)} cited) + {len(der)} derivable; "
          f"CSV {len(rows)} rows for the pilot papers ({n_items} values); matched {matched} CSV values")
    for lab, why in csv_only:
        print(f"   CSV only    {lab}: {why}")
    for fid, why in f_only:
        print(f"   forest only {fid}: {why}")


def case10(F):
    print("== Case 10, coated EAR against exposure: the forest against exposure_ear.csv")
    pts = []
    for l in F.leaves({"aspect_ratio", "coated_aspect_ratio", "equivalent_aspect_ratio"}):
        e = l["ctx"].get("exposure")
        if not e or e == "ambiguous":
            continue
        ev, _, _ = value_of(e)
        pa = ev * TORR if "Torr" in e["unit"] else ev
        T = l["ctx"].get("deposition_temperature")
        pts.append(dict(l=l, e=e, pa=pa, T=None if T in (None, "ambiguous") else T["value"]))
        print(f"   forest {l['key']} {l['fid'].split(':')[1]:10s} {l['row']['quantity']} {l['row']['censor']}{l['value']:g}  exposure {e['censor']}{e['value']} {e['unit']} ({e['fact_id'].split(':')[1]}; = {e['censor']}{pa:.3g} Pa s)"
              f"  {'cited ' + l['scope'].split(':')[-1] if l['cited'] else 'own, ' + l['scope'].split(':')[-1]}  T {pts[-1]['T'] or 'none in scope'}")
    skipped = [l for l in F.leaves({"aspect_ratio", "coated_aspect_ratio", "equivalent_aspect_ratio"}) if not l["ctx"].get("exposure") or l["ctx"].get("exposure") == "ambiguous"]
    print(f"   {len(skipped)} aspect-ratio leaves without an exposure in scope ({', '.join(l['key'] + ' ' + l['fid'].split(':')[1] for l in skipped)})")
    rows = [r for r in csv.DictReader((HERE / "exposure_ear.csv").open(encoding="utf-8")) if r["paper_id"] in KEY]
    matched, used = 0, set()
    for r in rows:
        k = KEY[r["paper_id"]]
        hits = [p for p in pts if p["l"]["key"] == k and abs(p["l"]["value"] - float(r["ear"])) <= 0.02 * float(r["ear"]) and abs(p["pa"] - float(r["exposure_pa_s"])) <= 0.02 * float(r["exposure_pa_s"])]
        if hits:
            matched += 1; used.update(p["l"]["fid"] for p in hits)
        print(f"   CSV {k} T {r['T_C']} EAR {r['ear']} exposure {r['exposure_pa_s']} Pa s, reading {r['reading']}: {'matched ' + ', '.join(p['l']['fid'].split(':')[1] for p in hits) if hits else 'no forest point'}")
    print(f"   forest {len(pts)} points ({sum(not p['l']['cited'] for p in pts)} own, {sum(p['l']['cited'] for p in pts)} cited); CSV {len(rows)} records for the pilot papers; matched {matched} records")
    for key in ("gre23 per-run rows", "gre23 reading=lower", "gre23 160 °C excluded", "gre23 sat density 9.8 nm-2, mass 123.5 amu"):
        print(f"   CSV only    {key}: {REASONS[key]}")
    for p in pts:
        if p["l"]["fid"] not in used:
            print(f"   forest only {p['l']['fid']}: {REASONS.get(p['l']['fid'], 'no CSV record with this pair')}")


def fig9(F):
    """Fig. 9 of yim20 rebuilt from the tree: for each Fig. 9a (Series C) and 9d (Series D) curve with points, H, N, S_IIb, PD50
    and x~50 inherited from the curve's run (its children in the tree), then S/N and S/S_IIb against x/H, and the x~ where
    S/S_IIb crosses 0.5 (linear interpolation on the first descending crossing), against Table 1's x~50."""
    import json
    P = F.papers["yim20"]
    pts = json.loads((HERE / f"{P['pid']}.points.json").read_text(encoding="utf-8"))
    out = {}
    for series, panel, cfids in (("C", "a", ("fig9a#2", "fig9a#3", "fig9a#4")), ("D", "d", ("fig9d#2", "fig9d#3", "fig9d#4"))):
        rows = []
        for cf in cfids:
            f = P["byid"]["yim20:" + cf]
            run = f["parent"]
            kids = P["kids"][run]
            get = lambda q, **ql: next((k for k in kids if k["quantity"] == q and all(quals(k["qualifiers"]).get(a) == b for a, b in ql.items())), None)
            H, N, SIIb, PD = get("feature_height"), get("cycle_number"), get("film_thickness", position="plateau"), get("penetration_depth", level="50%")
            xt = next((k for k in P["kids"].get(PD["fact_id"], []) if k["quantity"] == "dimensionless_distance"), None) if PD else None
            r = dict(fid=f["fact_id"], label=f["mentions"].split(";")[0], run=run.split(":")[1], H=num(H["value"]), N=num(N["value"]), SIIb=num(SIIb["value"]),
                     PD50=num(PD["value"]), xt50_tab=num(xt["value"]) if xt else None,
                     used=[x["fact_id"] for x in (H, N, SIIb, PD, xt) if x], raw=None, sn=None, norm=None, xt50=None)
            r["xt_pd50"] = r["PD50"] / (r["H"] / 1000)
            if f["points_ref"]:
                raw = pts[f["points_ref"]]["points"]
                h = r["H"] / 1000
                r["raw"] = raw
                r["sn"] = [[x / h, s / r["N"]] for x, s in raw]
                r["norm"] = [[x / h, s / r["SIIb"]] for x, s in raw]
                for (x0, y0), (x1, y1) in zip(r["norm"], r["norm"][1:]):
                    if y0 >= 0.5 > y1:
                        r["xt50"] = x0 + (y0 - 0.5) / (y0 - y1) * (x1 - x0); break
            rows.append(r)
        out[series] = dict(panel=panel, curves=rows)
    return out


if __name__ == "__main__":
    F = Forest()
    print("leaves per quantity:", dict(sorted(F.quantities().items(), key=lambda x: -x[1])))
    case9(F)
    case10(F)
    print("== Fig. 9 from the tree (yim20): x~50 computed from the Fig. 9a/9d points against Table 1")
    for series, d in fig9(F).items():
        for r in d["curves"]:
            c = f"computed {r['xt50']:.0f}" if r["xt50"] else "no points"
            dev = f" ({(r['xt50'] - r['xt50_tab']) / r['xt50_tab'] * 100:+.0f}%)" if r["xt50"] else ""
            print(f"   Series {series} {r['label']:12s} {r['run']:6s} H {r['H']:g} nm, N {r['N']:g}, S_IIb {r['SIIb']:g} nm, PD50 {r['PD50']:g} µm: Table 1 x~50 {r['xt50_tab']:g} (PD50/H {r['xt_pd50']:.0f}); {c}{dev}"
                  + (f"; {len(r['raw'])} points" if r["raw"] else ""))
