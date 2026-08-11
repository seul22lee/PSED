"""psed_v1 must stand alone.

The acceptance test for this refactor: a developer copies `psed_v1/` into a
clean repository, installs the declared dependencies, and runs the pipeline with
no historical PSED directory present. These tests fail if anything under
psed_v1 imports, reads, or resolves a path into a pre-psed_v1 tree.
"""
from __future__ import annotations
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))

import ast
import importlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: every pre-psed_v1 implementation tree
HISTORICAL = re.compile(
    r"(?<![\w.])(old/|0226_kb|0529_kg|0604_kg|0706_pipeline|0706_ontology|"
    r"0709_corpus|0722_|PSED_MPC)")

#: numbered top-level directories the refactor removed
OLD_LAYOUT = re.compile(r"(?<![\w.])(00_paper|01_ontology|02_extraction|"
                        r"03_corpus|04_twin_mpc|05_orchestration)(?![\w])")

SKIP_DIRS = {"__pycache__", "papers", "extract-line-chart-data", ".git"}
#: prose that DESCRIBES history is allowed; only reports/ and docs/ may do it
PROSE_ONLY = ("reports", "docs")


#: the guard tests must NAME the things they forbid, so they exempt themselves
#: guard tests must NAME what they forbid, so they exempt themselves
SELF_EXEMPT = {"test_standalone.py", "validate_layout.py",
               "test_vocab_port.py"}


def source_files(exts=(".py",)):
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or set(p.parts) & SKIP_DIRS:
            continue
        if p.suffix not in exts:
            continue
        rel = p.relative_to(ROOT)
        if rel.parts and rel.parts[0] in PROSE_ONLY:
            continue
        if p.name in SELF_EXEMPT:
            continue
        yield rel, p


class NoHistoricalDependency(unittest.TestCase):

    def test_no_runtime_reference_to_historical_trees(self):
        hits = []
        for rel, p in source_files():
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if HISTORICAL.search(line):
                    hits.append("%s:%d %s" % (rel, i, line.strip()[:100]))
        self.assertEqual(hits, [], "psed_v1 still references historical trees")

    def test_no_reference_to_the_old_numbered_layout(self):
        hits = []
        for rel, p in source_files():
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if OLD_LAYOUT.search(line):
                    hits.append("%s:%d %s" % (rel, i, line.strip()[:100]))
        self.assertEqual(hits, [], "psed_v1 still references the numbered layout")

    def test_no_sys_path_escapes(self):
        """No module may reach outside psed_v1 by mutating sys.path."""
        bad = []
        for rel, p in source_files():
            for i, line in enumerate(p.read_text().splitlines(), 1):
                st = line.strip()
                if "sys.path" not in line or st.startswith(("#", '"', "'", "*")):
                    continue
                if '".."' in line or "'..'" in line or "parent.parent.parent" in line:
                    bad.append("%s:%d %s" % (rel, i, line.strip()[:100]))
        self.assertEqual(bad, [])

    def test_no_subprocess_into_historical_scripts(self):
        bad = []
        for rel, p in source_files():
            txt = p.read_text()
            if "subprocess" not in txt:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if HISTORICAL.search(line) or OLD_LAYOUT.search(line):
                    bad.append("%s:%d" % (rel, i))
        self.assertEqual(bad, [])

    def test_every_active_module_imports(self):
        """Import failure is the real standalone test: a module reaching into a
        deleted tree raises here."""
        mods = []
        for rel, _p in source_files():
            if rel.parts[0] in ("tests", "scripts"):
                continue
            if rel.name == "__init__.py":
                continue
            mods.append(".".join(rel.with_suffix("").parts))
        self.assertGreater(len(mods), 20, "module discovery found almost nothing")
        failed = []
        for m in mods:
            try:
                importlib.import_module(m)
            except Exception as e:                       # noqa: BLE001
                failed.append("%s -> %s: %s" % (m, type(e).__name__, str(e)[:90]))
        self.assertEqual(failed, [])

    def test_declared_dependencies_exist(self):
        self.assertTrue((ROOT / "requirements.txt").exists(),
                        "a standalone project must declare its dependencies")


class SinglePathContract(unittest.TestCase):
    """One path API; one per-paper root."""

    def setUp(self):
        import paths
        self.P = paths

    def test_paths_module_is_the_only_root_definition(self):
        offenders = []
        # a PER-PAPER path: <something> / <paper var> / "<bucket>". Report and
        # fixture directories that merely contain the word "canonical" are not.
        pat = re.compile(r'/\s*(?:doi|sd|pid|paper|p|f|d)\s*/\s*'
                         r'"(extracted|resolved|canonical|review\.json)"'
                         r'|/\s*"papers"\s*/')
        for rel, p in source_files():
            if rel.name == "paths.py":
                continue
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if pat.search(line) and "P." not in line and not line.strip().startswith("#"):
                    offenders.append("%s:%d %s" % (rel, i, line.strip()[:90]))
        self.assertEqual(offenders, [],
                         "these build per-paper paths without the paths API")

    def test_every_artifact_resolves_under_one_paper_root(self):
        d = "10.1063_1.5028178"
        P = self.P
        for fn in (P.paper_dir, P.extracted_dir, P.resolved_dir, P.canonical_dir,
                   P.figures_dir, P.recovery_dir, P.document_md, P.structure_json,
                   P.scout_json, P.card_json, P.figure_data_json, P.records_json,
                   P.geometry_json, P.pressure_json, P.curves_json, P.review_path):
            got = fn(d)
            self.assertTrue(str(got).startswith(str(P.PAPERS / d)),
                            "%s -> %s escapes papers/%s" % (fn.__name__, got, d))

    def test_no_second_active_paper_output_root(self):
        for stale in ("02_extraction/output", "03_corpus/extracted",
                      "0709_corpus", "0706_pipeline"):
            self.assertFalse((ROOT / stale).exists(),
                             "a second per-paper tree still exists: %s" % stale)

    def test_docling_writes_into_the_paper_folder(self):
        src = (ROOT / "pipeline" / "parse" / "docling_parse.py").read_text()
        self.assertIn("P.extracted_dir", src,
                      "the parse stage must write via the paths API")
        self.assertNotIn('ROOT / "extracted"', src)

    def test_stages_read_the_same_paper_folder(self):
        for stage in ("pipeline/scout/scout.py",
                      "pipeline/figures/figure_extract.py",
                      "pipeline/resolve/to_kb.py",
                      "pipeline/canonical/build_canonical.py"):
            src = (ROOT / stage).read_text()
            self.assertIn("P.", src, "%s does not use the paths API" % stage)


class ScoutRole(unittest.TestCase):
    """Scout selects coverage; it does not mint physical experiment identity."""

    def setUp(self):
        self.src = (ROOT / "pipeline" / "scout" / "scout.py").read_text()

    def test_prompt_has_no_figure_equals_experiment_assumption(self):
        banned = [
            r"different figures are\s*\n?\s*different experiments",
            r"[Ss]ame-type figures are\s*\n?\s*separate experiments",
            r"each figure is (?:a|one) (?:separate|distinct) experiment",
        ]
        for pat in banned:
            self.assertIsNone(re.search(pat, self.src),
                              "Scout still asserts figure == experiment: %s" % pat)

    def test_prompt_states_identity_is_resolved_downstream(self):
        self.assertIn("resolved", self.src)
        self.assertRegex(self.src, r"identity is resolved\s*\n?\s*downstream|"
                                   r"resolved\s*\n?\s*downstream")

    def test_coverage_rule_is_retained(self):
        self.assertIn("CRITICAL COVERAGE RULE", self.src)
        self.assertIn("never drop a data plot", self.src)


if __name__ == "__main__":
    unittest.main(verbosity=1)
