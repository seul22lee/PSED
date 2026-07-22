"""
similarity.py  —  experiment similarity metrics (condition/configuration first)

Researcher's design: similarity is multi-dimensional and coverage-aware. This module
implements CONDITION (configuration) similarity carefully, because experiments record
heterogeneous, partly-missing information:

  · score only attributes BOTH experiments have (Gower-style); never reward both-missing
  · merge equivalent quantities via ontology families (temperature≈deposition_temperature,
    pulse_time≈plasma_exposure_time) so different papers' vocab still compares
  · numeric distances in LOG space, normalized by the corpus spread (robust p10–p90)
  · categorical = exact match; reactant sets = Jaccard
  · report COVERAGE (shared weight) and SHRINK low-coverage scores toward a neutral
    prior, so one coincidental match can't read as "identical"
  · score CONFIGURATION only — exclude model-fit parameters (reaction_probability,
    site_density, molecular_mass, precursor_molecular_diameter …)

Returns a per-attribute PROFILE and a composite condition score. Curve/derived metrics
are layered on later; the composite will fold them in the same coverage-aware way.
"""
import json, glob, math, os
from collections import defaultdict
from statistics import median

_HERE = os.path.dirname(os.path.abspath(__file__))          # …/0706_pipeline
_REPO = os.path.dirname(_HERE)
ROOT_GLOB = os.path.join(_HERE, "output", "*", "resolved", "experiments.json")

# ---- configuration attribute taxonomy (what counts as "setup") + weights --------
CATEG = {"material": 3.0, "process_type": 1.2, "structure": 0.8}      # exact-match
SETS  = {"precursors": 2.0, "coreactants": 1.5}                        # Jaccard
# numeric slots (quantity -> canonical slot merges equivalent quantities); weights
SLOT = {"temperature": "temperature", "deposition_temperature": "temperature",
        "pulse_time": "exposure_time", "plasma_exposure_time": "exposure_time",
        "exposure": "dose", "purge_time": "purge_time",
        "feature_height": "feature_height", "feature_width": "feature_width",
        "aspect_ratio": "aspect_ratio", "cycle_number": "cycle_number",
        "pore_diameter": "pore_diameter", "partial_pressure": "pressure"}
NUMW = {"temperature": 2.0, "exposure_time": 1.6, "dose": 1.4, "pressure": 1.0,
        "purge_time": 0.7, "feature_height": 1.2, "feature_width": 0.9,
        "aspect_ratio": 1.2, "cycle_number": 0.8, "pore_diameter": 0.9}
PRIOR, PRIOR_W = 0.5, 1.5          # shrinkage: neutral prior + its pseudo-weight


def load():
    E = []
    for f in sorted(glob.glob(ROOT_GLOB)):
        pid = f.split("/output/")[1].split("/")[0]
        for i, e in enumerate(json.load(open(f))):
            e["_pid"], e["_id"] = pid, f"{pid}:{i}"; E.append(e)
    return E


def config(e):
    """Extract the configuration vector: categoricals, reactant sets, numeric slots."""
    c = {"material": e.get("material"), "process_type": e.get("process_type"),
         "structure": e.get("structure"),
         "precursors": frozenset(e.get("precursors") or []),
         "coreactants": frozenset(e.get("coreactants") or [])}
    num = {}
    for ctrl in e.get("controlled") or []:
        q, v = ctrl.get("quantity"), ctrl.get("value")
        if q in SLOT and isinstance(v, (int, float)) and v > 0 and SLOT[q] not in num:
            num[SLOT[q]] = float(v)
    c["num"] = num
    return c


def logscale(E):
    """Robust per-slot log spread (p90–p10) for normalizing numeric distance."""
    vals = defaultdict(list)
    for e in E:
        for slot, v in config(e)["num"].items():
            vals[slot].append(math.log10(v))
    sc = {}
    for slot, xs in vals.items():
        xs.sort()
        if len(xs) >= 3:
            lo, hi = xs[len(xs) // 10], xs[-max(1, len(xs) // 10)]
            sc[slot] = max(hi - lo, 0.3)
        else:
            sc[slot] = 1.0
    return sc


def condition_similarity(a, b, SC):
    """Coverage-aware weighted similarity + per-attribute profile. Returns dict."""
    ca, cb = config(a), config(b)
    parts, wsum, wsim = [], 0.0, 0.0
    def add(name, w, s):
        nonlocal wsum, wsim
        parts.append((name, round(s, 3), w)); wsum += w; wsim += w * s
    for k, w in CATEG.items():
        if ca[k] and cb[k]:
            add(k, w, 1.0 if ca[k] == cb[k] else 0.0)
    for k, w in SETS.items():
        A, B = ca[k], cb[k]
        if A or B:
            if A and B:
                add(k, w, len(A & B) / len(A | B))
            # one-sided missing: skip (no shared info)
    for slot, va in ca["num"].items():
        vb = cb["num"].get(slot)
        if vb is not None:
            d = abs(math.log10(va) - math.log10(vb)) / SC.get(slot, 1.0)
            add(slot, NUMW.get(slot, 1.0), max(0.0, 1.0 - d))
    if wsum == 0:
        return {"score": None, "coverage": 0, "n_shared": 0, "parts": []}
    raw = wsim / wsum
    adj = (wsum * raw + PRIOR_W * PRIOR) / (wsum + PRIOR_W)      # shrink low-coverage
    return {"score": round(adj, 3), "raw": round(raw, 3), "coverage": round(wsum, 1),
            "n_shared": len(parts), "parts": sorted(parts, key=lambda p: -p[2])}


# =============================================================================
# CURVE similarity — agreement of the actual data in the canonical basis
# =============================================================================
import re
ONTO = json.load(open(os.path.join(_REPO, "01_ontology", "ald_ontology.json")))
_QR = ONTO.get("quantity_relations", {})
FAM = {f: s["canonical"] for f, s in (_QR.get("families") or {}).items()}
TRANS = _QR.get("transforms", [])
LENFAC = {"nm": 1, "µm": 1e3, "μm": 1e3, "um": 1e3, "mm": 1e6, "cm": 1e7, "m": 1e9, "å": .1}
def _tobase(v, u): f = LENFAC.get(u); return v * f if f else v


def _axis_unit(label):
    m = re.search(r"[\(\[]\s*([^)\]]{1,6})\s*[\)\]]\s*$", str(label or ""))
    return m.group(1).strip() if m else None


def _plan(e, q, fam, srcunit):
    """Bring quantity q to its family canonical; returns transform op + bridge value/unit."""
    canon = FAM.get(fam)
    if not (q and fam and canon): return {"op": "norm", "canon": q}
    if q == canon: return {"op": "none", "canon": canon}
    t = next((t for t in TRANS if t["from"] == q and t["to"] == canon), None)
    if t:
        c = next((c for c in e.get("controlled") or [] if c.get("quantity") == t["bridge"]), None)
        bv = c.get("value") if c and isinstance(c.get("value"), (int, float)) else None
        if bv: return {"op": t["op"], "val": bv, "vunit": c.get("unit"), "sunit": srcunit, "canon": canon}
    return {"op": "norm", "canon": canon}


def _apply(v, p):
    if p["op"] == "divide": return _tobase(v, p.get("sunit")) / _tobase(p["val"], p.get("vunit"))
    if p["op"] == "multiply": return v * p["val"]
    return v


def canonize(e):
    """Return the curve as (xs, ys) in canonical basis; per-curve 0–1 fallback when a
    bridge is missing (so shape is still comparable)."""
    pts = sorted([p for p in (e.get("points") or []) if p and p[0] is not None and p[1] is not None])
    if len(pts) < 3: return None
    xun = _axis_unit(e.get("x_label")) or next((c.get("unit") for c in e.get("controlled") or []
                                                 if c.get("quantity") == e.get("coordinate")), None)
    yun = (e.get("measurand") or {}).get("unit")
    pxp = _plan(e, e.get("coordinate"), e.get("coordinate_family"), xun)
    pyp = _plan(e, (e.get("measurand") or {}).get("quantity"), e.get("measurand_family"), yun)
    xs = [_apply(p[0], pxp) for p in pts]; ys = [_apply(p[1], pyp) for p in pts]
    if pxp["op"] == "norm":
        lo, hi = min(xs), max(xs); xs = [(x - lo) / ((hi - lo) or 1) for x in xs]
    if pyp["op"] == "norm":
        lo, hi = min(ys), max(ys); ys = [(y - lo) / ((hi - lo) or 1) for y in ys]
    return xs, ys


def _interp(xs, ys, xq):
    if xq <= xs[0]: return ys[0]
    if xq >= xs[-1]: return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= xq:
            t = (xq - xs[i - 1]) / ((xs[i] - xs[i - 1]) or 1)
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


def curve_metrics(xa, ya, xb, yb, N=40):
    """Plain-points curve agreement on the OVERLAPPING x-range: nRMSE, R², overlap
    fraction, curve_sim = exp(-3·nRMSE). Reference curve is A (R² is of B against A).
    Used both for experiment-vs-experiment and for TWIN-vs-measured validation."""
    if not xa or not xb or len(xa) < 2 or len(xb) < 2:
        return None
    x0, x1 = max(min(xa), min(xb)), min(max(xa), max(xb))
    span = max(max(xa), max(xb)) - min(min(xa), min(xb))       # union span for overlap frac
    if x1 <= x0 or span <= 0:
        return {"curve_sim": None, "overlap": 0.0}
    grid = [x0 + (x1 - x0) * i / (N - 1) for i in range(N)]
    fa = [_interp(xa, ya, g) for g in grid]; fb = [_interp(xb, yb, g) for g in grid]
    allv = fa + fb; yr = (max(allv) - min(allv)) or 1
    rmse = math.sqrt(sum((p - q) ** 2 for p, q in zip(fa, fb)) / N)
    nrmse = rmse / yr
    my = sum(fa) / N; sstot = sum((p - my) ** 2 for p in fa) or 1
    ssres = sum((p - q) ** 2 for p, q in zip(fa, fb))
    r2 = 1 - ssres / sstot
    return {"curve_sim": round(math.exp(-3 * nrmse), 3), "nrmse": round(nrmse, 3),
            "r2": round(r2, 3), "overlap": round((x1 - x0) / span, 2)}


def curve_similarity(a, b):
    """Same comparability class only. Resample on the OVERLAPPING x-range -> nRMSE, R²."""
    if a.get("comparability_key") != b.get("comparability_key"): return None
    ca, cb = canonize(a), canonize(b)
    if not ca or not cb: return None
    (xa, ya), (xb, yb) = ca, cb
    return curve_metrics(xa, ya, xb, yb)


# ---- derived scalars (canonical basis) --------------------------------------
def derived(e):
    c = canonize(e)
    if not c: return None
    xs, ys = c
    ymax = max(ys) or 1
    half = 0.5 * ymax; pd50 = None
    for (x0, y0), (x1, y1) in zip(list(zip(xs, ys)), list(zip(xs, ys))[1:]):
        if (y0 - half) * (y1 - half) <= 0 and y1 != y0:
            pd50 = x0 + (half - y0) * (x1 - x0) / (y1 - y0); break
    return {"pd50": pd50, "plateau": ymax, "front": ys[0]}


def _reldelta_sim(a, b):
    if a is None or b is None: return None
    m = (abs(a) + abs(b)) / 2 or 1
    return max(0.0, 1 - abs(a - b) / m)


def derived_similarity(a, b):
    da, db = derived(a), derived(b)
    if not da or not db: return None
    out = {}
    for k in ("pd50", "plateau", "front"):
        s = _reldelta_sim(da[k], db[k])
        if s is not None: out[k] = round(s, 3)
    return out or None


# =============================================================================
# COMPOSITE — coverage-aware blend of condition + curve + derived
# =============================================================================
COMPW = {"condition": 0.45, "curve": 0.35, "derived": 0.20}
def composite(a, b, SC):
    cond = condition_similarity(a, b, SC)
    cur = curve_similarity(a, b)
    der = derived_similarity(a, b)
    comps = {}
    if cond["score"] is not None: comps["condition"] = cond["score"]
    if cur and cur.get("curve_sim") is not None: comps["curve"] = cur["curve_sim"]
    if der: comps["derived"] = round(sum(der.values()) / len(der), 3)
    if not comps: return None
    wsum = sum(COMPW[k] for k in comps)
    score = round(sum(COMPW[k] * v for k, v in comps.items()) / wsum, 3)
    # condition×outcome 2×2 (outcome = curve agreement)
    quad = None
    if "condition" in comps and "curve" in comps:
        hc, ho = comps["condition"] >= 0.7, comps["curve"] >= 0.7
        quad = ("reproducible" if hc and ho else "inconsistency⚠" if hc and not ho
                else "insensitivity" if not hc and ho else "trend")
    return {"composite": score, "components": comps, "quadrant": quad,
            "condition": cond, "curve": cur, "derived": der}


def cluster(items, SC, thr=0.75):
    """Agglomerative (average-linkage) grouping by composite similarity >= thr."""
    groups = [[i] for i in range(len(items))]
    def gsim(g1, g2):
        ss = [composite(items[i], items[j], SC) for i in g1 for j in g2]
        ss = [s["composite"] for s in ss if s]
        return sum(ss) / len(ss) if ss else 0
    merged = True
    while merged and len(groups) > 1:
        merged = False; best = (thr, None, None)
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                s = gsim(groups[i], groups[j])
                if s > best[0]: best = (s, i, j)
        if best[1] is not None:
            i, j = best[1], best[2]; groups[i] += groups[j]; groups.pop(j); merged = True
    return groups


def demo():
    E = load()
    ER = [e for e in E if e.get("analysis_ready")]
    SC = logscale(ER)
    print(f"corpus: {len(ER)} analysis-ready experiments · numeric log-scales: "
          + ", ".join(f"{k}={v:.2f}" for k, v in sorted(SC.items())) + "\n" + "=" * 78)

    # 1) a fully-worked pair (show the careful per-attribute profile + coverage)
    exp = [e for e in ER if e["_pid"] == "yim2020" and e.get("granularity") == "profile"]
    a, b = exp[0], exp[3]
    r = condition_similarity(a, b, SC)
    print(f"\n1) PAIR PROFILE  A='{a['series_name']}'  B='{b['series_name']}'  ({a['_pid']})")
    print(f"   composite condition-sim = {r['score']}  (raw {r['raw']}, coverage {r['coverage']}, {r['n_shared']} shared attrs)")
    for name, s, w in r["parts"]:
        print(f"      {name:20} sim={s:<5}  weight={w}")

    # 2) coverage caution: a low-overlap pair vs a high-overlap pair, same raw
    print("\n2) WHY COVERAGE MATTERS — shrinkage keeps thin evidence honest")
    import itertools
    pairs = [(x, y) for x, y in itertools.combinations(ER, 2)]
    scored = [(condition_similarity(x, y, SC), x, y) for x, y in pairs]
    scored = [(r, x, y) for r, x, y in scored if r["score"] is not None]
    thin = min(scored, key=lambda t: t[0]["coverage"])
    thick = max(scored, key=lambda t: t[0]["coverage"])
    for tag, (r, x, y) in [("thin ", thin), ("thick", thick)]:
        print(f"   {tag}: raw={r['raw']} -> shrunk={r['score']}  coverage={r['coverage']} ({r['n_shared']} attrs)  "
              f"{x['_pid']}/{x['series_name'][:14]!r} vs {y['_pid']}/{y['series_name'][:14]!r}")

    # 3) reproducibility cohort: most-similar setups across DIFFERENT papers
    print("\n3) CROSS-PAPER LOOK-ALIKES (same config, different paper) — reproducibility candidates")
    cross = [(r, x, y) for r, x, y in scored if x["_pid"] != y["_pid"] and r["coverage"] >= 4]
    for r, x, y in sorted(cross, key=lambda t: -t[0]["score"])[:6]:
        print(f"   sim={r['score']} cov={r['coverage']}  {x['_pid']}:'{x['series_name'][:16]}'  ~  {y['_pid']}:'{y['series_name'][:16]}'")

    # 4) COMPOSITE + curve agreement + 2×2 — on the big film-amount conformality cohort
    coh = [e for e in ER if e.get("comparability_key") == "position ~ film_amount"
           and e.get("points")][:8]
    print(f"\n4) COMPOSITE on a comparability cohort (position ~ film_amount, n={len(coh)})")
    print(f"   {'A':22}{'B':22}{'comp':>6}{'cond':>6}{'curve':>6}{'R²':>6}  quadrant")
    import itertools as it
    for a, b in list(it.combinations(coh, 2))[:8]:
        r = composite(a, b, SC)
        if not r: continue
        cu = r["curve"] or {}
        print(f"   {a['series_name'][:20]:22}{b['series_name'][:20]:22}"
              f"{r['composite']:>6}{r['components'].get('condition','-'):>6}"
              f"{str(r['components'].get('curve','-')):>6}{str(cu.get('r2','-')):>6}  {r['quadrant'] or ''}")

    # 5) DERIVED scalar comparison (PD50 etc. in canonical basis)
    print("\n5) DERIVED SCALARS (canonical) for the cohort — PD50 / plateau / front")
    for e in coh[:5]:
        d = derived(e)
        pd = f"{d['pd50']:.2f}" if d and d['pd50'] is not None else "—"
        print(f"   {e['_pid']:12} {e['series_name'][:20]:22} PD50={pd:>6}  plateau={d['plateau']:.2f}  front={d['front']:.2f}")

    # 6) CLUSTERING into cohorts
    print("\n6) CLUSTERS (composite ≥ 0.75, average-linkage)")
    groups = cluster(coh, SC, 0.75)
    for gi, g in enumerate(sorted(groups, key=len, reverse=True)):
        names = [coh[i]["series_name"][:16] for i in g]
        print(f"   cluster {gi+1} (n={len(g)}): {', '.join(names)}")


if __name__ == "__main__":
    demo()
