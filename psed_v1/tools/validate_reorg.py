#!/usr/bin/env python3
"""Validate the paper-folder reorganization and the figure-anchored ids.

Checks exactly what was asked:
  1. every paper has exactly one review folder
  2. every experiment is assigned to the correct paper
  3. figure/panel provenance is preserved in the experiment id
  4. no records are lost
  5. no broken references or stale paths remain

Read-only apart from tools/reorg_validation.json.
"""
import json
import re
import subprocess
import sys
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAPERS = REPO / "papers"
sys.path.insert(0, str(REPO))
import paper_layout as L                                    # noqa: E402

#: paths that no longer exist and must not be referenced by code
STALE = [
    r'03_corpus\s*/\s*extracted', r'"03_corpus"\s*/\s*"extracted"',
    r'02_extraction/output/10\.', r'"output"\s*/\s*(sd|pid|doi|paper)\b',
    r'\(ROOT / "output"\)\.glob\("\*/(resolved|canonical)',
]
#: corpus-level artifacts that legitimately stay in 02_extraction/output/
CORPUS_OK = ("knowledge_graph_onto", "recipes.json", "recipe_accounting",
             "_accuracy", "_archive")

ID_RE = re.compile(r"^(?P<doi>.+?)__(?P<slug>Fig[0-9A-Za-z.]+|FigIdx\w+|NoFig)"
                   r"(?:__(?:exp|case)\d+)*$")


def main():
    fail = collections.defaultdict(list)
    info = {}

    # ---- 1. one folder per paper ----------------------------------------
    folders = sorted(p.name for p in PAPERS.iterdir() if p.is_dir())
    info["paper_folders"] = len(folders)
    dupes = [k for k, v in collections.Counter(
        L.paper_id(f) for f in folders).items() if v > 1]
    if dupes:
        fail["duplicate_folders"] = dupes
    for f in folders:
        if L.paper_id(f) != f:
            fail["folder_name_not_deterministic"].append(f)
        if not (PAPERS / f / "extracted").exists():
            fail["folder_without_extraction"].append(f)
    # the old trees must be gone
    for old in (REPO / "03_corpus" / "extracted",):
        if old.exists():
            fail["old_tree_still_present"].append(str(old.relative_to(REPO)))
    leftover = [d.name for d in (REPO / "02_extraction" / "output").iterdir()
                if d.is_dir() and not d.name.startswith("_")] \
        if (REPO / "02_extraction" / "output").exists() else []
    if leftover:
        fail["per_paper_dirs_left_in_output"] = leftover

    # ---- 4. no records lost (checked before 2/3 so counts are known) -----
    tot_raw = tot_res = tot_pts_raw = tot_pts_res = 0
    for p in folders:
        fd = PAPERS / p / "extracted" / "figure_data.json"
        rf = PAPERS / p / "resolved" / "results.json"
        if fd.exists():
            d = json.loads(fd.read_text())
            n = sum(len(s.get("points") or [])
                    for f in (d.get("figures") or [])
                    for pan in (f.get("panels") or [])
                    for s in (pan.get("series") or []))
            c = sum(len(pan.get("series") or [])
                    for f in (d.get("figures") or [])
                    for pan in (f.get("panels") or []))
            tot_raw += c
            tot_pts_raw += n
        if rf.exists():
            res = json.loads(rf.read_text())
            tot_res += len(res["results"])
            tot_pts_res += sum(r["n_points"] or 0 for r in res["results"])
    info["raw_series"] = tot_raw
    info["result_records"] = tot_res
    info["raw_points"] = tot_pts_raw
    info["result_points"] = tot_pts_res
    if tot_pts_raw != tot_pts_res:
        fail["points_lost"] = [tot_pts_raw, tot_pts_res]

    # ---- 2 + 3. ids: right paper, real figure/panel provenance ----------
    seen_ids = collections.Counter()
    no_fig, no_panel = [], []
    for p in folders:
        rf = PAPERS / p / "resolved" / "results.json"
        if not rf.exists():
            continue
        for r in json.loads(rf.read_text())["results"]:
            rid = r["result_id"]
            seen_ids[rid] += 1
            m = ID_RE.match(rid)
            if not m:
                fail["id_not_parseable"].append(rid)
                continue
            # 2. the id's paper part must BE this folder
            if m.group("doi") != p:
                fail["experiment_in_wrong_paper"].append((p, rid))
            if r["paper_id"] != p:
                fail["paper_id_field_mismatch"].append((p, rid, r["paper_id"]))
            # 3. the figure/panel in the id must match the record's provenance
            slug = m.group("slug")
            fn = str(r["printed_figure_number"] or "").strip()
            pan = str(r["panel"] or "").strip().lower()
            if fn:
                want = "Fig%s" % re.sub(r"[^A-Za-z0-9.]", "", fn)
                if re.fullmatch(r"[a-z]", pan):
                    want += pan
                if slug != want:
                    fail["id_figure_panel_mismatch"].append((rid, want))
            else:
                no_fig.append(rid)
                if not slug.startswith(("FigIdx", "NoFig")):
                    fail["invented_figure"].append(rid)
            # a panel may never be invented
            _pm = re.fullmatch(r"Fig[0-9.]+([a-z])", slug)
            if _pm and not re.fullmatch(r"[a-z]", pan):
                fail["invented_panel"].append((rid, r["panel"]))
            if not pan:
                no_panel.append(rid)
    dup = [k for k, v in seen_ids.items() if v > 1]
    if dup:
        fail["duplicate_experiment_ids"] = dup[:10]
    info["experiment_ids"] = len(seen_ids)
    info["ids_without_printed_figure"] = len(no_fig)
    info["records_without_panel"] = len(no_panel)
    info["examples_without_figure"] = no_fig[:10]

    # ---- cross-file reference integrity ---------------------------------
    for p in folders:
        rd = PAPERS / p / "resolved"
        if not (rd / "entities.json").exists():
            continue
        ents = json.loads((rd / "entities.json").read_text())
        ids = {e["entity_id"] for e in ents}
        for e in ents:
            if e.get("fit_of_entity") and e["fit_of_entity"] not in ids:
                fail["dangling_fit_link"].append((p, e["entity_id"]))
        for f, key in (("experiments.json", "entity_id"),
                       ("series.json", "entity_id")):
            fp = rd / f
            if not fp.exists():
                continue
            for row in json.loads(fp.read_text()):
                if row.get(key) and row[key] not in ids:
                    fail["dangling_%s_ref" % f.split(".")[0]].append(
                        (p, row.get(key)))

    # ---- 5. no stale paths in code --------------------------------------
    py = [f for f in subprocess.check_output(
        ["git", "ls-files", "*.py"], cwd=str(REPO)).decode().split()
        if "third_party" not in f and "extract-line-chart" not in f]
    py += [str(p.relative_to(REPO)) for p in REPO.rglob("*.py")
           if "third_party" not in p.parts and "extract-line-chart" not in str(p)
           and str(p.relative_to(REPO)) not in py]
    for rel in sorted(set(py)):
        f = REPO / rel
        if not f.exists() or rel.startswith("tools/") or rel == "paper_layout.py":
            continue
        txt = f.read_text()
        for pat in STALE:
            for m in re.finditer(pat, txt):
                line = txt[:m.start()].count("\n") + 1
                ctx = txt.splitlines()[line - 1]
                if any(k in ctx for k in CORPUS_OK) or ctx.strip().startswith("#"):
                    continue
                fail["stale_path_reference"].append("%s:%d %s" % (rel, line,
                                                                  ctx.strip()[:90]))

    # ---- ids must never be STRING-PARSED to recover the paper ------------
    # This is how the reorganization actually broke something: the twin derived
    # the paper with `exp_id.split("-")[0]`, which had already been silently
    # truncating hyphenated DOIs and collapsed entirely once ids became
    # figure-anchored. The paper is a field; parsing the id is the bug.
    for rel in sorted(set(py)):
        f = REPO / rel
        if not f.exists() or rel.startswith("tools/"):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            st = line.strip()
            if st.startswith('#') or st.startswith('"') or st.startswith("'") or '`' in st:
                continue      # prose describing the defect, not code doing it
            if re.search(r'(exp_id|entity_id|result_id)[^)\n]{0,30}'
                         r'\.(split|rsplit|partition)\(', line):
                fail["experiment_id_is_string_parsed"].append(
                    "%s:%d %s" % (rel, i, line.strip()[:90]))

    # ---- every experiment record must carry its paper as a field ---------
    for p in folders:
        xf = PAPERS / p / "resolved" / "experiments.json"
        if not xf.exists():
            continue
        for row in json.loads(xf.read_text()):
            if (row.get("paper_id") or row.get("doi")) != p:
                fail["experiment_missing_paper_field"].append((p, row.get("exp_id")))

    # ---- review manifests ------------------------------------------------
    missing = [p for p in folders
               if (PAPERS / p / "resolved").exists()
               and not (PAPERS / p / "review.json").exists()]
    if missing:
        fail["missing_review_manifest"] = missing

    out = {"info": info, "failures": {k: v[:12] for k, v in fail.items()},
           "failure_counts": {k: len(v) for k, v in fail.items()}}
    (REPO / "tools" / "reorg_validation.json").write_text(json.dumps(out, indent=1))

    print("paper folders: %d   experiment ids: %d" % (info["paper_folders"],
                                                      info["experiment_ids"]))
    print("raw series %d -> result records %d ; points %d -> %d"
          % (tot_raw, tot_res, tot_pts_raw, tot_pts_res))
    print()
    CHECKS = ["duplicate_folders", "folder_name_not_deterministic",
              "folder_without_extraction", "old_tree_still_present",
              "per_paper_dirs_left_in_output", "points_lost",
              "id_not_parseable", "experiment_in_wrong_paper",
              "paper_id_field_mismatch", "id_figure_panel_mismatch",
              "invented_figure", "invented_panel", "duplicate_experiment_ids",
              "dangling_fit_link", "dangling_experiments_ref",
              "dangling_series_ref", "stale_path_reference",
              "experiment_id_is_string_parsed", "experiment_missing_paper_field",
              "missing_review_manifest"]
    for k in CHECKS:
        n = len(fail.get(k, []))
        print("  %-34s %s" % (k, "PASS" if n == 0 else "FAIL (%d)" % n))
        for x in fail.get(k, [])[:3]:
            print("        %s" % (x,))
    print()
    print("  records with no printed figure number : %d %s"
          % (len(no_fig), no_fig[:4]))
    print("  records with no panel in the source   : %d" % len(no_panel))
    return 1 if any(fail.get(k) for k in CHECKS) else 0


if __name__ == "__main__":
    sys.exit(main())
