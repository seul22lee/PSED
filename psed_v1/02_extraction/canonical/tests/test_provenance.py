"""Provenance, immutability and determinism tests (spec §14 items 28-31, 36-37)."""
import json
import unittest
from pathlib import Path

from canonical import validate as V
from canonical import sources as S
from canonical.schema import REPO, Status

OUTPUT = REPO / "papers"          # papers/<doi>/{resolved,canonical}/


def any_canonical_doc():
    for p in sorted(OUTPUT.glob("*/canonical/curves.json")):
        doc = json.loads(p.read_text())
        if doc.get("curves"):
            return doc
    return None


class TestRawImmutability(unittest.TestCase):
    """28 — raw source data must be unchanged after transformation."""

    def test_28_raw_points_match_the_source_slice(self):
        doc = any_canonical_doc()
        self.assertIsNotNone(doc, "build_canonical.py has not been run")
        rep = V.Report()
        V.validate_raw_unchanged(doc["doi"], doc["curves"], rep)
        muts = [f for f in rep.failures if f["check"].startswith("raw.")]
        self.assertEqual(muts, [], "raw points diverged from source: %s" % muts[:3])

    def test_28b_canonical_values_are_separate_arrays(self):
        doc = any_canonical_doc()
        for c in doc["curves"]:
            for axis, i in (("x", 0), ("y", 1)):
                can = (c.get("canonical") or {}).get(axis)
                if not can:
                    continue
                raw_vals = [p[i] for p in c["raw"]["points"]]
                self.assertIsNot(can["values"], raw_vals)
                self.assertEqual(len(can["values"]), len(raw_vals))

    def test_figure_data_json_is_never_written_by_the_canonical_layer(self):
        import canonical.build_canonical as B
        import canonical.audit as A
        for mod in (B, A, S):
            src = Path(mod.__file__).read_text()
            for bad in ("figure_data.json\").write_text", "figure_data'].write_text",
                        'paths["figure_data"].write_text'):
                self.assertNotIn(bad, src,
                                 "%s writes to figure_data.json" % mod.__name__)


class TestProvenanceRequired(unittest.TestCase):
    """29, 31 — locator + checksum retained; missing provenance fails validation."""

    def test_29_source_locator_and_checksum_are_retained(self):
        doc = any_canonical_doc()
        for c in doc["curves"]:
            src = c["source"]
            self.assertTrue(src.get("source_file"))
            self.assertTrue(src.get("json_pointer", "").startswith("/figures/"))
            self.assertTrue(str(src.get("source_checksum", "")).startswith("sha256:"))

    def test_31_missing_provenance_fails_validation(self):
        doc = any_canonical_doc()
        good = next(c for c in doc["curves"]
                    if (c.get("canonical") or {}).get("x") or (c.get("canonical") or {}).get("y"))
        rep = V.Report()
        V.validate_curve(json.loads(json.dumps(good)), rep)
        self.assertEqual(rep.failures, [], "a well-formed curve must validate")

        # strip the transformation records -> canonical value with no execution
        broken = json.loads(json.dumps(good))
        broken["transformations"] = []
        rep2 = V.Report()
        V.validate_curve(broken, rep2)
        self.assertTrue(any(f["check"] == "provenance.execution" for f in rep2.failures))

        # strip the source checksum -> locator failure
        broken2 = json.loads(json.dumps(good))
        broken2["source"]["source_checksum"] = None
        rep3 = V.Report()
        V.validate_curve(broken2, rep3)
        self.assertTrue(any(f["check"] == "provenance.locator" for f in rep3.failures))

    def test_31b_unresolved_status_without_a_reason_fails(self):
        doc = any_canonical_doc()
        c = json.loads(json.dumps(doc["curves"][0]))
        for t in c["transformations"]:
            t["status"] = Status.MISSING_CONTEXT
            t["unresolved_reason"] = None
        rep = V.Report()
        V.validate_curve(c, rep)
        self.assertTrue(any(f["check"] == "provenance.reason" for f in rep.failures))

    def test_every_context_binding_carries_scope_and_source(self):
        for p in sorted(OUTPUT.glob("*/canonical/curves.json")):
            for c in json.loads(p.read_text())["curves"]:
                for t in c.get("transformations") or []:
                    for q, b in (t.get("context") or {}).items():
                        if b.get("status") == "resolved":
                            self.assertTrue(b.get("scope"), "%s missing scope" % q)
                            self.assertTrue(b.get("source_file"), "%s missing source" % q)


class TestRecoveryMerge(unittest.TestCase):
    """36 — selective recovery adds metadata without replacing digitized points."""

    def test_36_recovery_files_carry_no_points(self):
        found = 0
        for p in sorted((REPO / "papers").glob("*/extracted/recovery/figure_semantics_v1.json")):
            found += 1
            doc = json.loads(p.read_text())
            self.assertFalse(doc.get("points"))
            for panel in doc.get("panels", []):
                self.assertNotIn("points", panel)
                self.assertNotIn("series", panel)
                for axis in ("x", "y"):
                    self.assertNotIn("points", panel.get(axis) or {})
                self.assertFalse((panel.get("recovery") or {}).get("points_replaced", False))
        self.assertGreater(found, 0, "no recovery files were produced")

    def test_36b_point_counts_are_unchanged_by_recovery(self):
        """Every canonical curve must have exactly as many points as the source."""
        for p in sorted(OUTPUT.glob("*/canonical/curves.json")):
            doc = json.loads(p.read_text())
            fd = json.loads((REPO / "papers" / doc["doi"] / "extracted" / "figure_data.json").read_text())
            for c in doc["curves"]:
                node = V._resolve_pointer(fd, c["source"]["json_pointer"])
                self.assertIsNotNone(node)
                src_pts = [q for q in (node.get("points") or [])
                           if isinstance(q, (list, tuple)) and len(q) == 2]
                self.assertEqual(len(src_pts), len(c["raw"]["points"]))


class TestDeterminism(unittest.TestCase):
    """37 — ids and content are stable across repeated builds."""

    def test_37_curve_ids_are_deterministic_and_unique(self):
        import canonical.build_canonical as B
        seen = set()
        for doi in S.papers():
            if not S.paper_paths(doi)["figure_data"].exists():
                continue
            for c in S.iter_curves(doi):
                cid = B.curve_id(c)
                self.assertEqual(cid, B.curve_id(c))          # stable
                self.assertNotIn(cid, seen, "duplicate curve id %s" % cid)
                seen.add(cid)
        self.assertGreater(len(seen), 0)

    def test_37b_rebuilding_a_paper_reproduces_the_same_document(self):
        import canonical.build_canonical as B
        doc = any_canonical_doc()
        rebuilt = {"curves": [B.build_curve(c) for c in S.iter_curves(doc["doi"])]}
        self.assertEqual(json.dumps(rebuilt["curves"], sort_keys=True),
                         json.dumps(doc["curves"], sort_keys=True))

    def test_37c_series_ids_are_deterministic(self):
        from canonical import live
        a = live.series_id("doi", "F3", "a", 2)
        self.assertEqual(a, live.series_id("doi", "F3", "a", 2))
        self.assertEqual(live.point_experiment_id(a, 7), a + "-P007")


if __name__ == "__main__":
    unittest.main()
