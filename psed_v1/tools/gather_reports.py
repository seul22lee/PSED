#!/usr/bin/env python3
"""Refresh reports/ — one flat copy of every .html and .md under psed_v1.

The mirror existed but was assembled by hand, so it drifted the moment anything
was regenerated: after the experiment-extraction repair the copies still showed
the pre-repair dashboards. This makes the gather reproducible, and it is the
step that must follow any dashboard or report rebuild.

Originals stay where they are; the copies here are flattened
(`02_extraction/kg_viewer.html` -> `02_extraction__kg_viewer.html`) and indexed
in reports/index.md.

Usage:  python3 tools/gather_reports.py [--check]
        --check reports what is stale and exits non-zero, copying nothing.
"""
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"

#: report SUBDIRECTORIES keep their own structure and are never flattened --
#: they are working directories with scripts and data next to the prose
KEEP_NESTED = {"canonical", "condition_binding_diagnosis", "condition_completeness",
               "condition_precision", "entity_model",
               "experiment_extraction_regression"}
SKIP_DIRS = {"reports", "tools", "output", "figures", "raw", "recovery",
             "__pycache__", ".git", "node_modules", "third_party", "data"}


def sources():
    out = []
    for p in sorted(REPO.rglob("*")):
        if p.suffix not in (".html", ".md") or not p.is_file():
            continue
        rel = p.relative_to(REPO)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        out.append(rel)
    return out


def flat_name(rel):
    return "__".join(rel.parts)


def main():
    check = "--check" in sys.argv
    REPORTS.mkdir(exist_ok=True)
    src = sources()
    stale, new = [], []
    for rel in src:
        dst = REPORTS / flat_name(rel)
        if not dst.exists():
            new.append(rel)
        elif not filecmp.cmp(REPO / rel, dst, shallow=False):
            stale.append(rel)
        if not check:
            shutil.copy2(REPO / rel, dst)

    # index
    groups = {}
    for rel in src:
        groups.setdefault(rel.parts[0] if len(rel.parts) > 1 else ".", []).append(rel)
    lines = ["# psed_v1 — gathered reports & docs", "",
             "Copies of every .html and .md under psed_v1, in one place. Originals "
             "stay in their folders; links point to the copies here.", "",
             "Regenerate with `python3 tools/gather_reports.py` (use `--check` to "
             "detect drift without copying). Run it after rebuilding any dashboard.",
             ""]
    for g in sorted(groups):
        lines.append("## %s" % g)
        lines.append("")
        for rel in groups[g]:
            lines.append("- [%s](%s)" % (rel.as_posix(), flat_name(rel)))
        lines.append("")
    lines.append("## working report directories")
    lines.append("")
    lines.append("Kept nested, with their generating scripts and data alongside:")
    lines.append("")
    for d in sorted(KEEP_NESTED):
        if (REPORTS / d).exists():
            n = len(list((REPORTS / d).rglob("*")))
            lines.append("- [%s/](%s/) — %d files" % (d, d, n))
    lines.append("")
    if not check:
        (REPORTS / "index.md").write_text("\n".join(lines) + "\n")

    print("%s %d source file(s): %d new, %d stale"
          % ("would refresh" if check else "refreshed", len(src), len(new), len(stale)))
    for rel in (new + stale)[:25]:
        print("   %s" % rel.as_posix())
    if check and (new or stale):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
