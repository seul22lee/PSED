"""Transformation-rule tests (spec §14 items 9-11, 15-23, 30, 32, 38)."""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import unittest

from pipeline.canonical import rules as R
from pipeline.canonical import units as U
from pipeline.canonical.schema import ContextBinding, NORMALIZATION_DEFINITIONS, COMPARISON_GROUPS


def ctx(quantity, value, unit, scope="curve"):
    return {quantity: ContextBinding.make(quantity, value, unit, scope,
                                          "fixture", "synthetic", "test", 1.0)}


class TestRegistrySync(unittest.TestCase):
    def test_38_registry_and_implementations_stay_synchronised(self):
        errors = R.validate_registry()
        self.assertEqual(errors, [], "registry errors:\n  " + "\n  ".join(errors))

    def test_every_rule_has_version_and_type(self):
        for rid, rule in R.REGISTRY.items():
            self.assertTrue(rule.version, "%s has no version" % rid)
            self.assertTrue(rule.type, "%s has no type" % rid)

    def test_invertible_rules_expose_an_inverse(self):
        for rid, rule in R.REGISTRY.items():
            if rule.invertible:
                self.assertTrue(rule.impl.has_inverse,
                                "%s claims invertible but has no inverse" % rid)

    def test_rules_referencing_normalizations_use_declared_ones(self):
        for rid, rule in R.REGISTRY.items():
            if rule.normalization_definition:
                self.assertIn(rule.normalization_definition, NORMALIZATION_DEFINITIONS)
                self.assertIn(rule.comparison_group, COMPARISON_GROUPS)


class TestDenormalizeDistance(unittest.TestCase):
    def test_09_x_over_L_plus_L_gives_distance(self):
        rule = R.denormalization_rule_for("x_over_channel_length")
        out = rule.apply([0.0, 0.45, 1.0], ctx=ctx("feature_length", 100.0, "µm"),
                         from_unit="1", to_unit="µm", allow_empty_as_dimensionless=True)
        self.assertAlmostEqual(out[1], 45.0, places=9)

    def test_10_x_over_H_plus_H_gives_distance(self):
        rule = R.denormalization_rule_for("x_over_feature_height")
        # H given in nm; rule output is µm -> unit conversion must happen inside
        out = rule.apply([0.5, 2.0], ctx=ctx("feature_height", 2000.0, "nm"),
                         from_unit="1", to_unit="µm", allow_empty_as_dimensionless=True)
        self.assertAlmostEqual(out[0], 1.0, places=9)
        self.assertAlmostEqual(out[1], 4.0, places=9)

    def test_11_x_over_Dh_plus_hydraulic_diameter_gives_distance(self):
        rule = R.denormalization_rule_for("x_over_hydraulic_diameter")
        out = rule.apply([2.0], ctx=ctx("hydraulic_diameter", 5.0, "µm"),
                         from_unit="1", to_unit="µm", allow_empty_as_dimensionless=True)
        self.assertAlmostEqual(out[0], 10.0, places=9)

    def test_zero_denominator_is_rejected(self):
        rule = R.denormalization_rule_for("x_over_feature_height")
        with self.assertRaises(R.TransformationError):
            rule.apply([1.0], ctx=ctx("feature_height", 0.0, "nm"),
                       from_unit="1", to_unit="µm", allow_empty_as_dimensionless=True)

    def test_12_missing_denominator_raises_missing_context(self):
        rule = R.denormalization_rule_for("x_over_feature_height")
        self.assertEqual(rule.missing_context({}), ["feature_height"])
        with self.assertRaises(R.MissingContext):
            rule.apply([1.0], ctx={}, from_unit="1", to_unit="µm",
                       allow_empty_as_dimensionless=True)


class TestCycleBased(unittest.TestCase):
    def test_15_gpc_plus_cycles_gives_thickness(self):
        rule = R.get("thickness_from_gpc_and_cycles")
        out = rule.apply([0.1], ctx=ctx("cycle_number", 500.0, "cycle"),
                         from_unit="nm/cycle", to_unit="nm")
        self.assertAlmostEqual(out[0], 50.0, places=9)

    def test_16_thickness_plus_cycles_gives_gpc(self):
        rule = R.get("gpc_from_thickness_and_cycles")
        out = rule.apply([50.0], ctx=ctx("cycle_number", 500.0, "cycle"),
                         from_unit="nm", to_unit="nm/cycle")
        self.assertAlmostEqual(out[0], 0.1, places=12)

    def test_16b_steady_growth_assumption_is_recorded(self):
        rule = R.get("gpc_from_thickness_and_cycles")
        self.assertTrue(any("steady" in a for a in rule.assumptions),
                        "the linear-growth assumption must be declared on the rule")

    def test_17_nucleation_delay_aware_conversion(self):
        rule = R.get("gpc_from_thickness_and_cycles")
        c = ctx("cycle_number", 500.0, "cycle")
        c.update(ctx("nucleation_delay", 100.0, "cycle"))
        out = rule.apply([40.0], ctx=c, from_unit="nm", to_unit="nm/cycle")
        self.assertAlmostEqual(out[0], 0.1, places=12)      # 40 / (500-100)

    def test_18_invalid_effective_cycle_count_fails(self):
        rule = R.get("gpc_from_thickness_and_cycles")
        c = ctx("cycle_number", 100.0, "cycle")
        c.update(ctx("nucleation_delay", 100.0, "cycle"))
        with self.assertRaises(R.TransformationError):
            rule.apply([40.0], ctx=c, from_unit="nm", to_unit="nm/cycle")
        with self.assertRaises(R.TransformationError):
            rule.apply([40.0], ctx=ctx("cycle_number", 0.0, "cycle"),
                       from_unit="nm", to_unit="nm/cycle")


class TestThicknessNormalizations(unittest.TestCase):
    def test_19_t_over_t0_normalization(self):
        rule = R.get("normalize_thickness_by_entrance")
        out = rule.apply([20.0, 10.0], ctx=ctx("reference_thickness", 20.0, "nm"),
                         from_unit="nm", to_unit="1")
        self.assertAlmostEqual(out[0], 1.0, places=12)
        self.assertAlmostEqual(out[1], 0.5, places=12)

    def test_20_t_over_tmax_normalization_is_self_contained(self):
        rule = R.get("normalize_thickness_by_max")
        self.assertTrue(rule.self_contained)
        out = rule.apply([5.0, 20.0, 10.0], from_unit="nm", to_unit="1")
        self.assertAlmostEqual(out[1], 1.0, places=12)
        self.assertAlmostEqual(out[0], 0.25, places=12)

    def test_21_bottom_to_top_step_coverage(self):
        rule = R.get("step_coverage_from_bottom_top")
        out = rule.apply([8.0], ctx=ctx("reference_thickness", 10.0, "nm"),
                         from_unit="nm", to_unit="1")
        self.assertAlmostEqual(out[0], 0.8, places=12)

    def test_22_local_to_planar_gpc_ratio(self):
        rule = R.get("local_to_planar_gpc_ratio")
        out = rule.apply([0.08], ctx=ctx("growth_per_cycle", 0.1, "nm/cycle"),
                         from_unit="nm/cycle", to_unit="1")
        self.assertAlmostEqual(out[0], 0.8, places=12)

    def test_normalizations_stay_distinct(self):
        """t(x)/t(0), t/tmax, t/t_planar, bottom/top and GPC ratios must be five
        different definitions in five different comparison groups."""
        ids = ["t_over_t_entrance", "t_over_t_max", "t_over_t_planar",
               "t_bottom_over_t_top", "gpc_local_over_gpc_planar"]
        groups = {NORMALIZATION_DEFINITIONS[i]["comparison_group"] for i in ids}
        self.assertEqual(len(groups), len(ids))


class TestExposure(unittest.TestCase):
    def test_23_exposure_from_pressure_and_pulse_time(self):
        rule = R.get("exposure_from_pressure_and_time")
        out = rule.apply([2.0], ctx=ctx("pulse_time", 5.0, "s"),
                         from_unit="Pa", to_unit="Pa.s")
        self.assertAlmostEqual(out[0], 10.0, places=12)

    def test_exposure_records_non_independence(self):
        rule = R.get("exposure_from_pressure_and_time")
        self.assertTrue(any("independent" in a for a in rule.assumptions))


class TestRoundTripAndDomain(unittest.TestCase):
    def test_30_transformation_round_trip(self):
        rule = R.denormalization_rule_for("x_over_feature_height")
        vals = [0.0, 0.25, 0.5, 1.0]
        err = rule.roundtrip_error(vals, ctx=ctx("feature_height", 1500.0, "nm"),
                                   from_unit="1", to_unit="µm",
                                   allow_empty_as_dimensionless=True)
        self.assertIsNotNone(err)
        self.assertLess(err, 1e-9)

    def test_unit_rule_round_trip(self):
        rule = R.unit_conversion_rule_for("Å/cycle")
        err = rule.roundtrip_error([1.0, 3.7], from_unit="Å/cycle", to_unit="nm/cycle")
        self.assertLess(err, 1e-12)

    def test_domain_violations_are_flagged_not_clamped(self):
        rule = R.get("denormalize_thickness_by_max")     # valid domain 0..1
        bad = rule.check_domain([0.5, 1.4])
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["bound"], "max")
        self.assertAlmostEqual(bad[0]["value"], 1.4)     # value untouched


class TestIdentity(unittest.TestCase):
    def test_32_already_canonical_identity_mapping(self):
        rule = R.get("identity_canonical_mapping")
        vals = [1.0, 2.5, 3.0]
        out = rule.apply(list(vals), from_unit="nm", to_unit="nm")
        self.assertEqual(out, vals)
        self.assertIsNot(out, vals)      # a copy, not the same list object


if __name__ == "__main__":
    unittest.main()
