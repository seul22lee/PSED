"""Axis-semantics and granularity tests (spec §14 items 24-27, 33; §2.6)."""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import unittest

from pipeline.canonical import axis_semantics as AX
from pipeline.canonical.schema import Status, COMPARISON_GROUPS


def texts(*pairs):
    """(source, text) -> the 4-tuple shape the resolver consumes."""
    return [(src, "fixture.json", "synthetic", txt) for src, txt in pairs]


class TestNormalizationDetection(unittest.TestCase):
    def test_x_over_H_detected_from_axis_label(self):
        s = AX.resolve_x_axis("spatial_coordinate", "", "x̃ = x/H",
                              texts(("axis_label", "x̃ = x/H")))
        self.assertEqual(s["status"], "resolved")
        self.assertEqual(s["normalization_definition"], "x_over_feature_height")
        self.assertEqual(s["comparison_group"],
                         "normalized_spatial_position_by_feature_height")

    def test_x_over_L_detected_and_kept_distinct_from_x_over_H(self):
        s = AX.resolve_x_axis("spatial_coordinate", "", "x/L",
                              texts(("axis_label", "x/L")))
        self.assertEqual(s["normalization_definition"], "x_over_channel_length")
        self.assertNotEqual(s["comparison_group"],
                            "normalized_spatial_position_by_feature_height")

    def test_x_over_Dh_detected(self):
        s = AX.resolve_x_axis("spatial_coordinate", "", "x/D_h",
                              texts(("axis_label", "x/D_h")))
        self.assertEqual(s["normalization_definition"], "x_over_hydraulic_diameter")

    def test_no_evidence_leaves_denominator_unresolved(self):
        s = AX.resolve_x_axis("spatial_coordinate", "", None,
                              texts(("figure_caption", "Normalized profile for ALD.")))
        self.assertEqual(s["status"], Status.MISSING_CONTEXT)
        self.assertIsNone(s["normalization_definition"])
        self.assertIn("no normalization expression", s["unresolved_reason"])

    def test_conflicting_definitions_in_one_source_are_ambiguous(self):
        cap = "(c) Type 1 normalized profile (x/H) and (d) Type 2 normalized profile (x/L)"
        s = AX.resolve_x_axis("spatial_coordinate", "", None,
                              texts(("figure_caption", cap)))
        self.assertEqual(s["status"], Status.AMBIGUOUS)
        self.assertIsNone(s["normalization_definition"])

    def test_evidence_confidence_decays_with_source_distance(self):
        near = AX.resolve_x_axis("spatial_coordinate", "", "x/H",
                                 texts(("axis_label", "x/H")))
        far = AX.resolve_x_axis("spatial_coordinate", "", None,
                                texts(("document_text", "the normalized distance x/H")))
        self.assertGreater(near["evidence"][0]["confidence"],
                           far["evidence"][0]["confidence"])


class TestThicknessNormalizationSemantics(unittest.TestCase):
    def test_t_over_t0_detected(self):
        s = AX.resolve_y_axis("normalized_thickness", "", "t(x)/t(0)",
                              texts(("axis_label", "t(x)/t(0)")))
        self.assertEqual(s["normalization_definition"], "t_over_t_entrance")
        self.assertEqual(s["comparison_group"], "entrance_normalized_thickness")

    def test_t_over_tmax_detected_and_distinct(self):
        s = AX.resolve_y_axis("normalized_thickness", "", "t/tmax",
                              texts(("axis_label", "t/tmax")))
        self.assertEqual(s["normalization_definition"], "t_over_t_max")
        self.assertEqual(s["comparison_group"], "maximum_normalized_thickness")

    def test_bottom_over_top_step_coverage_detected(self):
        s = AX.resolve_y_axis("step_coverage", "%", "t_bottom/t_top",
                              texts(("axis_label", "t_bottom/t_top")))
        self.assertEqual(s["normalization_definition"], "t_bottom_over_t_top")

    def test_generic_normalized_thickness_is_not_assigned_a_definition(self):
        """'normalized thickness' with no denominator evidence must NOT collapse
        into any of the specific normalization groups."""
        s = AX.resolve_y_axis("normalized_thickness", "", "Normalized thickness",
                              texts(("axis_label", "Normalized thickness")))
        self.assertEqual(s["status"], Status.MISSING_CONTEXT)
        self.assertIsNone(s["comparison_group"])

    def test_33_all_normalized_thickness_groups_stay_separate(self):
        defs = {"t_over_t_entrance": "entrance_normalized_thickness",
                "t_over_t_max": "maximum_normalized_thickness",
                "t_over_t_planar": "planar_normalized_thickness",
                "t_bottom_over_t_top": "step_coverage_bottom_to_top",
                "gpc_local_over_gpc_planar": "local_to_planar_growth_ratio"}
        self.assertEqual(len(set(defs.values())), 5)
        for g in defs.values():
            self.assertIn(g, COMPARISON_GROUPS)


class TestAxisClassification(unittest.TestCase):
    def test_24_coordinate_axis_classification(self):
        s = AX.resolve_x_axis("spatial_coordinate", "µm", "Distance (µm)", texts())
        self.assertEqual(s["axis_role"], "coordinate")
        self.assertEqual(s["comparison_group"], "spatial_position")

    def test_25_condition_axis_classification(self):
        """CONTRACT CHANGE. `cycle_number` moved from `condition` to
        `coordinate`: whether its points are separate runs is decided by
        canonical/granularity.py from run-structure evidence, not by the axis
        table. The recipe quantities are unchanged."""
        for q in ("deposition_temperature", "pulse_time", "exposure"):
            s = AX.resolve_x_axis(q, "s", None, texts())
            self.assertEqual(s["axis_role"], "condition",
                             "%s should be a condition axis" % q)
        s = AX.resolve_x_axis("cycle_number", "s", None, texts())
        self.assertEqual(s["axis_role"], "coordinate")

    def test_unknown_quantity_is_unsupported_not_guessed(self):
        s = AX.resolve_x_axis("Binding Energy of the 2p peak", "eV", None, texts())
        self.assertEqual(s["status"], Status.UNSUPPORTED)
        self.assertIsNone(s["comparison_group"])


class TestGranularity(unittest.TestCase):
    def test_27_coordinate_profile_stays_one_experiment(self):
        s = AX.resolve_x_axis("spatial_coordinate", "µm", None, texts())
        rep, why = AX.resolve_granularity(s, 30)
        self.assertEqual(rep, "profile")
        self.assertIn("coordinate", why)

    def test_26_condition_curve_becomes_a_series(self):
        s = AX.resolve_x_axis("deposition_temperature", "°C", None, texts())
        rep, why = AX.resolve_granularity(s, 5)
        self.assertEqual(rep, "series")
        self.assertIn("each point is one experiment", why)

    def test_granularity_is_not_decided_by_point_count(self):
        """The historical bug: len(points) > 1 -> 'profile'. A 5-point
        temperature sweep must NOT be a profile."""
        cond = AX.resolve_x_axis("deposition_temperature", "°C", None, texts())
        coord = AX.resolve_x_axis("spatial_coordinate", "µm", None, texts())
        self.assertNotEqual(AX.resolve_granularity(cond, 5)[0],
                            AX.resolve_granularity(coord, 5)[0])

    def test_single_point_is_single(self):
        s = AX.resolve_x_axis("spatial_coordinate", "µm", None, texts())
        self.assertEqual(AX.resolve_granularity(s, 1)[0], "single")

    def test_output_vs_output_curve_is_a_correlation(self):
        s = AX.resolve_x_axis("film_thickness", "nm", None, texts())
        rep, why = AX.resolve_granularity(s, 10)
        self.assertEqual(rep, "correlation")


if __name__ == "__main__":
    unittest.main()
