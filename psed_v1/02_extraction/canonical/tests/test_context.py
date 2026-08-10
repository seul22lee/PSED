"""Context-resolver tests (spec §14 items 13, 14, 34, 35; §7; §2.7)."""
import unittest

from canonical.context import ContextPool
from canonical.schema import Status


def pool_with(*entries):
    p = ContextPool()
    for quantity, value, unit, scope in entries:
        p.add(quantity, value, unit, scope, "fixture.json",
              "synthetic/%s" % scope, evidence="test", confidence=1.0)
    return p


class TestScopePriority(unittest.TestCase):
    def test_35_narrower_curve_scope_overrides_paper_scope(self):
        p = pool_with(("feature_height", 2000.0, "nm", "paper"),
                      ("feature_height", 500.0, "nm", "curve"))
        r = p.resolve("feature_height")
        self.assertTrue(r.resolved)
        self.assertEqual(r.binding["value"], 500.0)
        self.assertEqual(r.binding["scope"], "curve")
        self.assertIn("paper", r.binding["overrode_scopes"])

    def test_scope_order_is_narrowest_first(self):
        p = pool_with(("cycle_number", 1.0, "cycle", "paper"),
                      ("cycle_number", 2.0, "cycle", "method"),
                      ("cycle_number", 3.0, "cycle", "experiment"),
                      ("cycle_number", 4.0, "cycle", "figure"),
                      ("cycle_number", 5.0, "cycle", "panel"),
                      ("cycle_number", 6.0, "cycle", "curve"))
        self.assertEqual(p.resolve("cycle_number").binding["value"], 6.0)


class TestAmbiguity(unittest.TestCase):
    def test_13_conflicting_candidates_at_one_scope_are_ambiguous(self):
        p = pool_with(("feature_height", 100.0, "nm", "paper"),
                      ("feature_height", 500.0, "nm", "paper"),
                      ("feature_height", 2000.0, "nm", "paper"))
        r = p.resolve("feature_height")
        self.assertEqual(r.status, Status.AMBIGUOUS)
        self.assertIsNone(r.binding)
        self.assertEqual(len(r.candidates), 3)
        self.assertIn("3 distinct", r.reason)

    def test_34_conflicting_paper_level_geometry_is_not_broadcast(self):
        """The real corpus case (10.1039_d0cp03358h: 100/500/2000 nm). No value
        may be handed to the rule layer."""
        p = pool_with(("feature_height", 100.0, "nm", "paper"),
                      ("feature_height", 500.0, "nm", "paper"),
                      ("feature_height", 2000.0, "nm", "paper"))
        ctx, res, status, reason = p.resolve_all(["feature_height"])
        self.assertEqual(ctx, {})
        self.assertEqual(status, Status.AMBIGUOUS)
        self.assertIn("feature_height", res)

    def test_ambiguity_is_not_resolved_by_list_order(self):
        a = pool_with(("feature_height", 100.0, "nm", "paper"),
                      ("feature_height", 2000.0, "nm", "paper"))
        b = pool_with(("feature_height", 2000.0, "nm", "paper"),
                      ("feature_height", 100.0, "nm", "paper"))
        self.assertEqual(a.resolve("feature_height").status, Status.AMBIGUOUS)
        self.assertEqual(b.resolve("feature_height").status, Status.AMBIGUOUS)


class TestEquivalence(unittest.TestCase):
    def test_14_equivalent_candidates_in_different_units_resolve(self):
        p = pool_with(("feature_height", 2000.0, "nm", "paper"),
                      ("feature_height", 2.0, "µm", "paper"))
        r = p.resolve("feature_height", target_unit="nm")
        self.assertTrue(r.resolved)
        self.assertAlmostEqual(r.binding["value"], 2000.0, places=9)
        # all provenance retained
        self.assertEqual(len(r.binding["equivalent_sources"]), 2)

    def test_equivalent_candidates_do_not_hide_a_third_conflicting_one(self):
        p = pool_with(("feature_height", 2000.0, "nm", "paper"),
                      ("feature_height", 2.0, "µm", "paper"),
                      ("feature_height", 500.0, "nm", "paper"))
        self.assertEqual(p.resolve("feature_height", target_unit="nm").status,
                         Status.AMBIGUOUS)


class TestMissing(unittest.TestCase):
    def test_12_absent_quantity_is_missing_context(self):
        r = pool_with(("cycle_number", 500.0, "cycle", "paper")).resolve("feature_height")
        self.assertEqual(r.status, Status.MISSING_CONTEXT)
        self.assertIn("no value for feature_height", r.reason)

    def test_resolution_records_scope_and_provenance(self):
        p = pool_with(("feature_height", 500.0, "nm", "panel"))
        d = p.resolve("feature_height").to_dict()
        for key in ("quantity", "value", "unit", "scope", "source_file",
                    "source_location", "evidence", "confidence"):
            self.assertIn(key, d)
        self.assertEqual(d["scope"], "panel")


if __name__ == "__main__":
    unittest.main()
