"""Live-pipeline and comparison tests (spec §14 items 26, 27, 33, 34, 35; §2.3-2.8)."""
import json
import unittest

from canonical import live
from canonical import units as U
from canonical.schema import REPO, Status

OUTPUT = REPO / "02_extraction" / "output"


def all_experiments():
    out = []
    for p in sorted(OUTPUT.glob("*/resolved/experiments.json")):
        out.extend(json.loads(p.read_text()))
    return out


def all_series():
    out = []
    for p in sorted(OUTPUT.glob("*/resolved/series.json")):
        out.extend(json.loads(p.read_text()))
    return out


class TestLiveUnitConversion(unittest.TestCase):
    """§2.4 — values AND units are converted together."""

    def test_measurand_values_are_rescaled_not_just_relabelled(self):
        vals, unit, rec = live.normalize_measurand("growth_per_cycle", "Å/cycle", [10.0, 3.7])
        self.assertEqual(unit, "nm/cycle")
        self.assertAlmostEqual(vals[0], 1.0, places=12)
        self.assertAlmostEqual(vals[1], 0.37, places=12)
        self.assertTrue(rec["values_rescaled"])

    def test_per_cycle_is_preserved_not_degraded_to_length(self):
        _, unit, _ = live.normalize_measurand("growth_per_cycle", "Å/cycle", [10.0])
        self.assertEqual(unit, "nm/cycle")
        self.assertNotEqual(unit, "nm")

    def test_gpc_printed_as_a_bare_length_is_flagged_not_guessed(self):
        """growth_per_cycle labelled 'nm' is a dimension conflict. The missing
        '/cycle' must never be assumed."""
        vals, unit, rec = live.normalize_measurand("growth_per_cycle", "nm", [1.5])
        self.assertEqual(rec["status"], Status.INVALID)
        self.assertFalse(rec["values_rescaled"])
        self.assertEqual(vals, [1.5])
        self.assertIn("disagree", rec["reason"])

    def test_per_cycle_recovered_only_with_label_evidence(self):
        vals, unit, rec = live.normalize_measurand(
            "growth_per_cycle", "nm", [1.5], label="Thickness/cycles S/N (nm)")
        self.assertEqual(unit, "nm/cycle")
        self.assertEqual(rec["unit_recovered"], "nm/cycle")

    def test_unparseable_unit_leaves_values_untouched(self):
        vals, unit, rec = live.normalize_measurand("intensity", "a.u.", [5.0])
        self.assertEqual(rec["status"], Status.UNSUPPORTED)
        self.assertEqual(vals, [5.0])


class TestCoordinateUnits(unittest.TestCase):
    """§2.3 — coordinate numbers are never stored bare."""

    def test_coordinate_unit_is_resolved(self):
        raw, norm, dimless = live.coordinate_unit("spatial_coordinate", "um")
        self.assertEqual(norm, "µm")
        self.assertFalse(dimless)

    def test_cycle_number_gets_the_cycle_unit(self):
        _, norm, dimless = live.coordinate_unit("cycle_number", "")
        self.assertEqual(norm, "cycle")
        self.assertFalse(dimless)

    def test_unresolvable_coordinate_unit_is_reported_not_invented(self):
        _, norm, _ = live.coordinate_unit("Binding Energy", "")
        self.assertIsNone(norm)

    def test_live_experiments_record_coordinate_unit_status(self):
        exps = all_experiments()
        self.assertGreater(len(exps), 0, "run 06_to_kb.py --all --resolve-only first")
        for e in exps:
            if e.get("coordinate") is None:
                continue
            self.assertIn("coordinate_unit_status", e)
            if e["coordinate_unit_status"] == "unresolved":
                self.assertTrue(e.get("coordinate_unit_reason"))
            else:
                self.assertTrue(e.get("coordinate_unit_normalized"))


from canonical import entities as _ent_mod


class TestGranularityInLivePipeline(unittest.TestCase):
    """26, 27 — condition sweeps become series; profiles stay profiles."""

    def test_26_condition_curves_became_experiment_series(self):
        """CONTRACT CHANGE. An earlier version of this test asserted that a sweep
        produced one Experiment per digitised point. The Stage-0 audit showed that
        is wrong: point count is digitisation density, not a count of depositions.
        A sweep is now an ExperimentalSeries holding observations.

        SECOND CONTRACT CHANGE. Requiring an explicit sample list left 146 of 151
        corroborated sweeps minting nothing, so a measured sweep on a
        process-setting axis with documentary corroboration may now mint one case
        per plotted setting. The guarantee the test protects is unchanged: a case
        count is never the digitised point count."""
        series = all_series()
        self.assertGreater(len(series), 0, "no ExperimentSeries were created")
        for s in series:
            self.assertTrue(s.get("series_varies"))
            self.assertGreater(s.get("n_observations", 0), 1)
            self.assertIn(s.get("case_count_status"),
                          ("enumerated_in_source",
                           "enumerated_in_source_and_plotted",
                           "process_setting_axis_corroborated",
                           "unresolved_settings"))
            if s["case_count_status"] == "unresolved_settings":
                self.assertEqual(s["supported_case_count"], 0)
                self.assertTrue(s.get("case_count_reason"))
                # The lower bound is the structural constant 2 (a sweep varies its
                # axis, so at least two settings were prepared). It is deliberately
                # independent of n_observations; on a 2-point sweep the two numbers
                # coincide, which is a coincidence and not a density-derived count.
                self.assertEqual(s.get("case_count_lower_bound"), 2)

    def test_26b_sweep_observations_are_not_experiments(self):
        """The observations of a sweep stay observations. None of them may appear
        as an Experiment, and the swept values remain queryable on the entity."""
        import json as _j
        series = {s["series_id"]: s for s in all_series()}
        self.assertTrue(series)
        for p in sorted(OUTPUT.glob("*/resolved/entities.json")):
            for ent in _j.loads(p.read_text()):
                if ent.get("experimental_series_id") in series:
                    self.assertGreater(ent["n_observations"], 0)
                    # the swept setting value of every observation is preserved
                    self.assertTrue(all("x_raw" in o for o in ent["observations"]))
                    if ent["experimental_case_status"] == "unresolved_settings":
                        self.assertEqual(ent["experimental_case_count"], 0)
        cases = all_experiments()
        for c in cases:
            self.assertNotEqual(c.get("granularity"), "single_point_of_a_sweep")

    def test_27_spatial_profiles_remain_single_profile_experiments(self):
        profs = [e for e in all_experiments()
                 if e.get("coordinate") == "spatial_coordinate" and len(e.get("points") or []) > 2]
        self.assertGreater(len(profs), 0)
        for e in profs:
            self.assertEqual(e["granularity"], "profile")
            self.assertEqual(e.get("measurement_class"), "ExperimentalProfile")
            self.assertEqual(e.get("varies"), ["spatial_coordinate"])

    def test_granularity_is_not_a_function_of_point_count(self):
        """No experimental case may exist whose count was derived from how densely
        its curve happened to be digitised."""
        import json as _j
        for p in sorted(OUTPUT.glob("*/resolved/entities.json")):
            for ent in _j.loads(p.read_text()):
                if ent["experimental_case_count"] > 1:
                    self.assertIn(ent["experimental_case_status"],
                                  ("enumerated_in_source",
                                   "enumerated_in_source_and_plotted",
                                   "process_setting_axis_corroborated"),
                                  ent["entity_id"])
                    # The count is a number of SETTINGS. An earlier version
                    # asserted count != n_observations as a proxy for "not
                    # density-derived". That proxy is now wrong: a saturation
                    # curve measured at 7 ozone exposures has 7 settings AND 7
                    # points, and they coincide because every plotted point IS a
                    # deposition. The real invariant is stated directly instead --
                    # the count equals the DISTINCT settings, on an axis that is
                    # a process setting, from named evidence.
                    _distinct = len({o["x_raw"] for o in ent["observations"]})
                    self.assertLessEqual(ent["experimental_case_count"], _distinct,
                                         ent["entity_id"])
                    self.assertEqual(
                        _ent_mod.setting_axis_kind(ent.get("coordinate")),
                        "process_setting", ent["entity_id"])
                    self.assertTrue(ent["experimental_case_reason"],
                                    ent["entity_id"])


class TestScopedContext(unittest.TestCase):
    """34, 35 — conflicting paper-level values are not broadcast."""

    def test_34_conflicting_paper_geometry_is_marked_ambiguous(self):
        ctrl = [
            {"quantity": "feature_height", "value": 100.0, "unit": "nm",
             "source": "geometry", "origin": {"level": "paper", "from": "geometry"}},
            {"quantity": "feature_height", "value": 500.0, "unit": "nm",
             "source": "geometry", "origin": {"level": "paper", "from": "geometry"}},
        ]
        out, conflicts = live.mark_ambiguous_context(ctrl)
        self.assertEqual(len(conflicts), 1)
        for c in out:
            self.assertEqual(c["context_status"], Status.AMBIGUOUS)
        v, u, sc = live.narrowest_scope_value(out, "feature_height")
        self.assertIsNone(v, "an ambiguous value must not be handed out")

    def test_35_narrower_scope_wins_over_paper_scope(self):
        ctrl = [
            {"quantity": "feature_height", "value": 2000.0, "unit": "nm",
             "source": "geometry", "origin": {"level": "paper", "from": "geometry"}},
            {"quantity": "feature_height", "value": 500.0, "unit": "nm",
             "source": "series", "origin": {"level": "experiment", "from": "series_label"}},
        ]
        out, conflicts = live.mark_ambiguous_context(ctrl)
        self.assertEqual(conflicts, [], "different scopes are not a conflict")
        v, u, sc = live.narrowest_scope_value(out, "feature_height")
        self.assertEqual(v, 500.0)
        self.assertEqual(sc, "curve")

    def test_live_experiments_carry_scope_on_every_controlled_value(self):
        for e in all_experiments()[:400]:
            for c in e.get("controlled") or []:
                self.assertIn("scope", c)
                self.assertIn(c["scope"], live.SCOPE_ORDER)


class TestNoMinMaxFallback(unittest.TestCase):
    """33 — comparison must never fall back to per-curve min-max rescaling."""

    def test_33_similarity_refuses_incomparable_curves(self):
        import sys
        sys.path.insert(0, str(REPO / "02_extraction"))
        import similarity as sim
        self.assertIsNone(sim.canonize({"exp_id": "does-not-exist"}))
        self.assertIsNone(sim.curve_similarity({"exp_id": "nope-a"}, {"exp_id": "nope-b"}))

    def test_33b_no_minmax_rescaling_remains_in_the_comparison_path(self):
        src = (REPO / "02_extraction" / "similarity.py").read_text()
        canonize = src[src.index("def canonize("):]
        self.assertNotIn("(hi - lo)", canonize,
                         "min-max rescaling is still present in canonize()")

    def test_33c_different_normalizations_are_not_merged(self):
        """x/H and x/L curves must not share a comparison group."""
        import sys
        sys.path.insert(0, str(REPO / "02_extraction"))
        import similarity as sim
        idx = sim._canonical_index()
        by_group = {}
        for c in idx.values():
            nd = ((c.get("canonical") or {}).get("x") or {}).get("normalization_definition")
            grp = ((c.get("canonical") or {}).get("x") or {}).get("comparison_group")
            if nd:
                by_group.setdefault(nd, set()).add(grp)
        for nd, groups in by_group.items():
            self.assertEqual(len(groups), 1, "%s spread across %s" % (nd, groups))
        # distinct definitions must map to distinct groups
        allg = [next(iter(g)) for g in by_group.values()]
        self.assertEqual(len(allg), len(set(allg)))


if __name__ == "__main__":
    unittest.main()
