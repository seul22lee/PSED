#!/usr/bin/env python3
"""Tests for the Docling -> figure provenance -> scout -> figure extraction handoff.

The invariants this locks down, each of which was a real defect:

  1. an uncaptioned PictureItem is never silently dropped — every crop carries an
     explicit disposition;
  2. a caption is recovered from document.md only on positional evidence, never from
     a body reference such as "Figure 1b shows the mass changes…";
  3. machine identity (docling index) and printed identity (figure number) stay
     separate, and one printed figure may own several crops;
  4. a crop belonging to a split printed figure is never given a panel expectation
     derived from the whole printed caption — that pressure is what fabricated a
     second panel for 10.1116/6.0002436 FIG. 1;
  5. an empty scout selection invalidates stale downstream artifacts instead of
     leaving an older, incompatible run's output in place.

No LLM and no network: caption recovery is deterministic, and the extraction test
drives the empty-drill path, which makes no vision call.

    python3 tests/regression/test_figure_provenance.py
"""
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import _project                                     # noqa: E402
import json                                         # noqa: E402
import shutil                                       # noqa: E402
import tempfile                                     # noqa: E402
from pathlib import Path                            # noqa: E402

import paths as P                                   # noqa: E402
from pipeline.figures import inventory as inv       # noqa: E402

FAIL = []


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


def check(name, got, want):
    ok(name, got == want, f"got {got!r}, want {want!r}")


CNMA = "10.1002_cnma.201700148"
MOOX = "10.1116_6.0002436"

print("1) caption parsing rejects body references, keeps real captions")
md = ("\nFigure 1b shows the mass changes observed through in situ QCM.\n\n"
      "Figure 2. a) Thicknesses of annealed BN films as a function of ALD cycles.\n\n"
      "FIG. 1. Saturation curves for ozone and the Mo precursor.\n\n"
      "Figure 7 ． Scheme of the ALD set-up made of glassware.\n\n"
      "Figure 3 is discussed below.\n")
caps = inv.parse_captions(md)
nums = [c["printed_figure"] for c in caps]
ok("body reference 'Figure 1b shows …' rejected",
   not any("shows" in c["text"] for c in caps), nums)
ok("'Figure 2.' caption kept", "2" in nums, nums)
ok("'FIG. 1.' caption kept", "1" in nums, nums)
ok("fullwidth 'Figure 7 ．' caption kept", "7" in nums, nums)
ok("'Figure 3 is discussed' rejected", nums.count("3") == 0, nums)

print("2) every PictureItem receives an explicit disposition")
VALID = {inv.DRILL, inv.SKIP_WITH_REASON, inv.MANUAL_REVIEW,
         inv.MERGED_INTO_PRINTED_FIGURE, inv.OFFERED}
for pid in (CNMA, MOOX):
    o = inv.build(pid)
    bad = [c["candidate_id"] for c in o["candidates"] if c["disposition"] not in VALID]
    ok(f"{pid}: no crop without a disposition", not bad, bad)
    check(f"{pid}: one entry per PictureItem", len(o["candidates"]), o["n_pictures"])
    ok(f"{pid}: marker alignment exact", o["marker_alignment"] == "exact")

print("3) CNMA — the two lost plots are recovered from document.md")
o = inv.build(CNMA)
by = {c["docling_index"]: c for c in o["candidates"]}
check("P3 printed figure", by[3]["printed_figure"], "2")
check("P3 caption source", by[3]["caption_source"], "document_md")
ok("P3 caption is the thickness-vs-cycles caption",
   "Thicknesses" in inv.caption_for(by[3]), inv.caption_for(by[3])[:60])
check("P4 printed figure", by[4]["printed_figure"], "3")
check("P4 caption source", by[4]["caption_source"], "document_md")
ok("P4 caption is the FTIR/XPS caption", "FTIR" in inv.caption_for(by[4]))
ok("P3 offered to scout", by[3]["disposition"] in (inv.OFFERED, inv.DRILL))
ok("P4 offered to scout", by[4]["disposition"] in (inv.OFFERED, inv.DRILL))
ok("the HAL logo (P0) is never bound to a caption", by[0]["caption_source"] == "none")

print("4) machine identity stays separate from printed identity")
o = inv.build(MOOX)
by = {c["docling_index"]: c for c in o["candidates"]}
ok("P16 and P17 are different crops of ONE printed figure",
   by[16]["printed_figure"] == by[17]["printed_figure"] == "1")
ok("their candidate ids differ", by[16]["candidate_id"] != by[17]["candidate_id"])
ok("they share a printed group", by[16]["printed_group_id"] == by[17]["printed_group_id"])
ok("each knows its siblings", 17 in by[16]["siblings"] and 16 in by[17]["siblings"])
ok("printed number is never used as the routing id",
   by[16]["candidate_id"] == "P16" and by[17]["candidate_id"] == "P17")
ok("P16 (Mo-pulse crop) reaches the scout",
   by[16]["disposition"] in (inv.OFFERED, inv.DRILL), by[16]["disposition"])

print("5) label-strip siblings are merged, not sent for a second vision call")
merged = [c for c in o["candidates"] if c["disposition"] == inv.MERGED_INTO_PRINTED_FIGURE]
ok("at least one fragment sibling merged", merged, [c["candidate_id"] for c in merged])
ok("merged crops are the tiny ones",
   all((c.get("crop") or {}).get("klass") in ("fragment", "banner_or_logo")
       or "duplicate" in c["disposition_reason"] for c in merged))

print("6) a split crop gets NO panel expectation from the printed caption")
fx = _project.load("figures")
ok("split crops are flagged in the crop index",
   fx.caption_fig_index(MOOX)["16"]["siblings"], "P16 must know it is split")
cap = ("FIG. 1. Saturation curves for ozone (a) and the Mo precursor (b), "
       "showing panels (a) and (b).")
ok("the caption alone would demand 2 panels", fx._caption_panel_count(cap) == 2)
# the guard: a split crop must not inherit that count (see extract_paper)
src = _project.path("pipeline", "figures", "figure_extract.py").read_text()
ok("extract_paper zeroes the expectation for split crops",
   'if g.get("split")' in src and "expected = 0" in src)
ok("the split prompt forbids inventing panels",
   "do NOT invent a panel" in src and "ONE CROP of printed figure" in src)

print("7) an empty scout selection invalidates stale downstream artifacts")
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    ex = root / "10.0000_x" / "extracted"
    ex.mkdir(parents=True)
    (ex / "document.md").write_text("nothing here\n")
    (ex / "structure.json").write_text(json.dumps(
        {"n_figures": 0, "n_tables": 0, "figures": [], "tables": [], "sections": []}))
    (ex / "scout.json").write_text(json.dumps({"drill": [], "go_deeper": False}))
    # a stale artifact from an older, incompatible run
    (ex / "figure_data.json").write_text(json.dumps(
        {"doi": "10.0000_x", "figures": [{"figure": "9"}], "_tokens": {"in": 6777, "out": 15}}))
    (ex / "records.json").write_text(json.dumps([{"doi": "10.0000_x", "points": [[1, 2]]}]))
    orig = P.PAPERS
    P.PAPERS = root
    fx.EXTRACTED = root
    try:
        res, recs, ti, to = fx.extract_paper("10.0000_x", client=None)
        check("no vision results", res, [])
        check("no records returned", recs, [])
        fd = json.loads((ex / "figure_data.json").read_text())
        check("stale figures[] invalidated", fd["figures"], [])
        check("stale token counts invalidated", fd["_tokens"], {"in": 0, "out": 0})
        check("stale records.json invalidated", json.loads((ex / "records.json").read_text()), [])
        ok("output records the upstream scout it came from", "_upstream_scout" in fd)
    finally:
        P.PAPERS = orig

print("8) a successful run stamps its upstream scout fingerprint")
fd = P.figure_data_json(MOOX)
if fd.exists():
    obj = json.loads(fd.read_text())
    ok("figure_data records _upstream_scout", obj.get("_upstream_scout"))
    import hashlib
    want = hashlib.sha256(P.scout_json(MOOX).read_bytes()).hexdigest()[:16]
    ok("fingerprint matches the current scout.json", obj.get("_upstream_scout") == want,
       f"{obj.get('_upstream_scout')} vs {want}")

print("8b) scout input is IDEMPOTENT — a reconciled inventory still offers its crops")
sc = _project.load("scout")
before_n = len(sc.build_scout_input(MOOX)[2])
inv_now = json.loads((P.extracted_dir(MOOX) / "figure_inventory.json").read_text())
ok("the on-disk inventory has already been reconciled by a scout run",
   inv_now.get("scout_reconciled") and
   not any(c["disposition"] == inv.OFFERED for c in inv_now["candidates"]))
ok("crops are still offered on a second run", before_n > 0,
   f"{before_n} crops offered from a reconciled inventory")
ok("eligibility is evidence-based, not disposition-based",
   all(inv.is_offerable(c) == (bool(c.get("image"))
                               and c.get("caption_source") in ("docling", "document_md", "sibling")
                               and c["disposition"] != inv.MERGED_INTO_PRINTED_FIGURE)
       for c in inv_now["candidates"]))

print("10) caption grammar — house styles that omit the delimiter still parse")
for text, want in (
        ("Fig. 5 Dependence of Er2O3 film thicknesses on the number of ALD cycles.", "5"),
        ("Fig. 5 (a) Growth rate for Y2O3 films as function of water purge time.", "5"),
        ("Fig. 2 a Typical XPS data on the substrate surface; b Iron concentration.", "2"),
        ("FIG. 20. Thickness profiles of a hole structure with EAR of 50:1.", "20"),
        ("Figure 8 In fluence of total pressure and substrate temperature.", "8")):
    got = inv.parse_captions("\n" + text + "\n")
    ok(f"caption parsed: {text[:44]}…", [c["printed_figure"] for c in got] == [want], got)
for text in ("Fig. 5 for films grown on Si(100), the thicknesses were proportional to N.",
             "Fig. 5(a) shows that a higher growth rate was achieved at 10 and 30 s.",
             "Figure 1b shows the mass changes observed through in situ QCM.",
             "Figure 3 is discussed below in the context of nucleation."):
    ok(f"body reference rejected: {text[:44]}…", not inv.parse_captions("\n" + text + "\n"),
       inv.parse_captions("\n" + text + "\n"))

print("11) structural association modes, on synthetic documents")


def synth(md, captions):
    """A throwaway paper: `captions` is the docling-bound caption per crop ('' = none)."""
    td = tempfile.mkdtemp()
    d = Path(td) / "10.0000_synth" / "extracted"
    d.mkdir(parents=True)
    (d / "document.md").write_text(md)
    (d / "structure.json").write_text(json.dumps({
        "n_figures": len(captions), "n_tables": 0, "tables": [], "sections": [],
        "figures": [{"index": i, "caption": c, "image": ""} for i, c in enumerate(captions)]}))
    orig = P.PAPERS
    P.PAPERS = Path(td)
    try:
        return {c["docling_index"]: c for c in inv.build("10.0000_synth")["candidates"]}
    finally:
        P.PAPERS = orig


M = "<!-- image -->"
CAP1 = "Fig. 1 Growth rate of the film versus deposition temperature."
CAP2 = "Fig. 2 Thickness of the film versus the number of ALD cycles."

# caption bound to the FIRST crop of a run — the trailing sibling loses it (5 of the 11)
r = synth(f"intro\n\n{CAP1}\n\n{M}\n\n{M}\n\nbody\n", [CAP1, ""])
check("trailing sibling inherits the printed figure", r[1]["printed_figure"], "1")
check("and records how", r[1]["association_method"], "shared_printed_figure")
check("the docling-bound crop keeps its own provenance", r[0]["association_method"], "docling_bound")
ok("original docling caption is never overwritten", r[0]["caption_original"] == CAP1)

# caption bound to the LAST crop, printed between its siblings (10.1116/6.0002436 FIG. 1)
r = synth(f"intro\n\n{M}\n\n{M}\n\n{CAP1}\n\n{M}\n\nbody\n", ["", "", CAP1])
check("leading siblings inherit across their own caption", r[0]["printed_figure"], "1")
check("and the middle crop too", r[1]["printed_figure"], "1")

# a crop whose OWN caption follows it must not inherit the neighbour's (d3dt01824e P8)
r = synth(f"{CAP1}\n\n{M}\n\n" + "x" * 900 + f"\n\n{M}\n\n{CAP2}\n\nbody\n", [CAP1, ""])
check("crop with its own following caption binds to it", r[1]["printed_figure"], "2")
check("by positional adjacency", r[1]["association_method"], "positional_adjacent")

# structurally unambiguous but far away — distance is evidence, not a gate (cremers, s11671)
r = synth(f"intro\n\n{CAP2}\n\n" + "y" * 1800 + f"\n\n{M}\n\nbody\n", [""])
check("distant but unambiguous caption is found", r[0]["printed_figure"], "2")
check("and is labelled as a structural search", r[0]["association_method"],
      "structural_local_search")

# an intervening DIFFERENT caption blocks inheritance
r = synth(f"{CAP1}\n\n{M}\n\n{CAP2}\n\n" + "z" * 900 + f"\n\n{M}\n\nbody\n", [CAP1, ""])
ok("intervening caption prevents the wrong figure being inherited",
   r[1]["printed_figure"] != "1", r[1]["printed_figure"])

# two equally plausible captions -> refuse, do not guess
pad = "q" * 700
r = synth(f"{CAP1}\n\n{pad}\n\n{M}\n\n{pad}\n\n{CAP2}\n\nbody\n", [""])
check("ambiguous neighbours leave the crop unresolved", r[0]["association_method"], "unresolved")
check("and it keeps no printed figure", r[0]["printed_figure"], None)

print("12) incomplete caption coverage withholds inheritance")
# the document cites Figure 2 but no caption for it exists anywhere -> an uncaptioned
# crop may BE Figure 2, so it must not inherit Figure 1 (10.1186/s11671-015-0872-9)
r = synth(f"We show this in Figure 2 below.\n\n{CAP1}\n\n{M}\n\n{M}\n\nbody\n", [CAP1, ""])
check("no inheritance when a cited figure has no caption",
      r[1]["association_method"], "unresolved")
r = synth(f"We show this in Figure 1 below.\n\n{CAP1}\n\n{M}\n\n{M}\n\nbody\n", [CAP1, ""])
check("inheritance allowed when coverage is complete",
      r[1]["association_method"], "shared_printed_figure")

print("13) a captioned fragment never becomes a vision call")
found = []
for pid in P.papers():
    if not P.structure_json(pid).exists():
        continue
    for c in inv.build(pid)["candidates"]:
        if (c.get("crop") or {}).get("klass") in ("fragment", "banner_or_logo") \
                and c["caption_source"] != "docling" and inv.is_offerable(c):
            found.append((pid, c["candidate_id"]))
ok("no fragment or banner is offered to scout on caption evidence alone", not found, found[:4])

print("14) the 11 audited crops are associated and offered")
EXPECT = {("10.1002_pssa.201532305", 11): "8", ("10.1007_s11671-010-9676-0", 4): "2",
          ("10.1007_s11671-010-9676-0", 5): "2", ("10.1021_acs.jpcc.9b08176", 8): "2",
          ("10.1039_d3dt01824e", 8): "5", ("10.1039_d3ra05217f", 9): "5",
          ("10.1116_1.4892385", 9): "2", ("10.1116_1.4938104", 11): "5",
          ("10.1116_1.4938104", 20): "10", ("cremers2019", 26): "9", ("cremers2019", 37): "20"}
_seen = {}
for (pid, idx), want in sorted(EXPECT.items()):
    if pid not in _seen:
        _seen[pid] = {c["docling_index"]: c for c in inv.build(pid)["candidates"]}
    c = _seen[pid][idx]
    ok(f"{pid} P{idx} -> printed Figure {want}, offered",
       c["printed_figure"] == want and inv.is_offerable(c),
       f"got Figure {c['printed_figure']} / {c['disposition']}")
    ok(f"{pid} P{idx} records its association evidence",
       c["association_method"] in ("positional_adjacent", "shared_printed_figure",
                                   "structural_local_search"), c["association_method"])

print("16) canonical panel key — one normalisation for provenance AND panel_source")
for label, want in (("a", "a"), ("(a)", "a"), ("a (With bottom)", "a"),
                    ("a - Without bottom", "a"), ("b (description)", "b"),
                    ("b (C 1s)", "b"), ("A", "a"), ("(c) O 1s", "c"),
                    ("", ""), ("left", ""), ("ab", "")):
    check(f"panel {label!r}", fx._clean_panel(label), want)

print("17) panel provenance is resolved, never defaulted to measured")
SIM = {"panel_source": {"a": "simulated", "b": "simulated"}, "source": "simulated"}
for label in ("a", "a (With bottom)", "a - Without bottom", "b (description)"):
    check(f"descriptive label {label!r} keeps simulated",
          fx.panel_source_for(SIM, label), "simulated")
check("unknown panel of an all-simulated figure",
      fx.panel_source_for(SIM, "z (x)"), "simulated")
check("no evidence anywhere -> unresolved, not measured",
      fx.panel_source_for({"panel_source": {}, "source": "both"}, "a"), "unresolved")
check("mixed panels + unknown label -> unresolved",
      fx.panel_source_for({"panel_source": {"a": "measured", "b": "simulated"},
                           "source": "both"}, "q"), "unresolved")
ok("'measured' is never a silent fallback in the resolver",
   'or "measured"' not in _project.path("pipeline", "figures", "figure_extract.py").read_text())

print("18) simulated panels stay simulated through flattening")
_fr = {"figure": "37", "caption": "FIG. 20. Thickness profiles.", "source": "simulated",
       "panel_source": {"a": "simulated", "b": "simulated"},
       "panels": [{"panel": "a (With bottom)", "x": {"quantity": "aspect_ratio"},
                   "y": {"quantity": "normalized_thickness"}, "series_axis": "s0",
                   "series": [{"label": "1", "points": [[1, 1], [2, 0.5]]}]},
                  {"panel": "b - Without bottom", "x": {"quantity": "aspect_ratio"},
                   "y": {"quantity": "normalized_thickness"}, "series_axis": "s0",
                   "series": [{"label": "0.1", "points": [[1, 1], [2, 0.4]]}]}]}
_recs = fx.flatten_records("10.0000_x", {"materials": ["Al2O3"]}, [_fr])
check("both descriptive panels flattened", len(_recs), 2)
ok("no simulated curve became measured",
   all(r["source"] == "simulated" for r in _recs), [r["source"] for r in _recs])
check("canonical panel recorded in provenance",
      sorted(r["provenance"]["panel"] for r in _recs), ["a", "b"])

print("19) corpus anchor — a known supported x-y figure stays selected")
# 10.1063/1.5028178 FIG. 2 (crop P10): reactant pressure vs position, four pulse-time
# series. A single scout sample dropped it once; this asserts it survives. It is an
# assertion about the CORPUS, never a routing rule.
for pid, idx, pf, min_series in [("10.1063_1.5028178", 10, "2", 4)]:
    c = {x["docling_index"]: x for x in inv.load(pid)["candidates"]}[idx]
    ok(f"{pid} P{idx} is offered", inv.is_offerable(c), c["disposition"])
    check(f"{pid} P{idx} printed figure", c["printed_figure"], pf)
    _r = [x for x in json.loads(P.records_json(pid).read_text())
          if str(x["provenance"].get("fig_docling_index")) == str(idx)]
    ok(f"{pid} P{idx} yields >= {min_series} series", len(_r) >= min_series, len(_r))
    ok(f"{pid} P{idx} series carry points", all(len(x.get("points") or []) for x in _r))

print("20) scout unions independent samples rather than trusting one")
check("two figures from separate samples are both kept",
      len(sc.union_drill([{"where": "F1", "type": "t", "measurand": "m"}],
                         [{"where": "F9", "type": "t", "measurand": "m"}])), 2)
check("a figure already covered is not duplicated",
      len(sc.union_drill([{"where": "F9a", "type": "t", "measurand": "m"}],
                         [{"where": "F9", "type": "t", "measurand": "m"}])), 1)
ok("scout takes more than one sample", sc.SCOUT_SAMPLES >= 2, sc.SCOUT_SAMPLES)

print("15) the scout input is built from the inventory, not a caption filter")
scout_src = _project.path("pipeline", "scout", "scout.py").read_text()
ok("the silent caption filter is gone",
   'for f in struct["figures"] if f["caption"]' not in scout_src)
ok("scout consumes the inventory", "_inventory.load(sd)" in scout_src)
ok("scout tags crops by docling index", 'f"[F{c[\'docling_index\']}]"' in scout_src
   or "[F{c['docling_index']}]" in scout_src)

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    _sys.exit(1)
print("ALL TESTS PASSED")
