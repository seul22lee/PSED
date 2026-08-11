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

print("9) the scout input is built from the inventory, not a caption filter")
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
