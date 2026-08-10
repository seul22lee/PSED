"""Regression tests for the granularity / axis-semantics / identity repair.

Every test names a concrete failure from the review. The unit tests pin the
LOGIC (so they hold for papers not yet in the corpus); the corpus tests pin the
regenerated output.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.schema import REPO                    # noqa: E402
from canonical import axis_roles as AR               # noqa: E402
from canonical import granularity as G               # noqa: E402

sys.path.insert(0, str(REPO / "02_extraction" / "stages"))
import lib                                           # noqa: E402

PAPERS = REPO / "papers"


def canon(s):
    if not s:
        return None
    return lib.resolve_axis_label(s) or lib.canon_quantity(s)


def results(paper):
    f = PAPERS / paper / "resolved" / "results.json"
    return json.loads(f.read_text())["results"] if f.exists() else []


def row(paper, suffix):
    for r in results(paper):
        if r["result_id"].endswith(suffix):
            return r
    raise AssertionError("no result %r in %s" % (suffix, paper))


# ===================================================================== axes
class AxisSemantics(unittest.TestCase):
    """"Do not allow a lexical match to override obvious dimensional evidence.\""""

    def test_reciprocal_space_Q_is_not_site_density(self):
        r = AR.resolve_axis("Q (1/Å)", None, "1/Å", caption="GIWAXS", canon=canon)
        self.assertEqual(r["canonical_quantity"], "scattering_vector_q")
        self.assertEqual(r["axis_role"], "measurement_coordinate")

    def test_impedance_is_not_a_spatial_coordinate(self):
        for lab, want in (("Z' (ohms)", "impedance_real"),
                          ("-Z'' (ohms)", "impedance_imaginary")):
            r = AR.resolve_axis(lab, None, None, caption="Nyquist", canon=canon)
            self.assertEqual(r["canonical_quantity"], want, lab)
            self.assertEqual(r["axis_role"], "measurement_coordinate", lab)

    def test_storage_time_is_not_an_ald_pulse(self):
        r = AR.resolve_axis("storage time (h)", None, "h", canon=canon)
        self.assertEqual(r["canonical_quantity"], "storage_time")
        self.assertEqual(r["axis_role"], "progression_coordinate")

    def test_conductivity_is_not_resistivity(self):
        r = AR.resolve_axis("log σ (S/cm)", None, "S/cm", canon=canon)
        self.assertEqual(r["canonical_quantity"], "ionic_conductivity")

    def test_arrhenius_abscissa_is_a_transform(self):
        r = AR.resolve_axis("1000/T (1/K)", None, "1/K", canon=canon)
        self.assertEqual(r["canonical_quantity"], "inverse_temperature")
        self.assertEqual(r["axis_role"], "derived_representation")

    def test_duration_and_integrated_dose_are_different(self):
        t = AR.resolve_axis("At-H exposure time (min)", None, "min", canon=canon)
        d = AR.resolve_axis("Integrated precursor exposure (torr-s)", None,
                            "torr-s", canon=canon)
        self.assertEqual(t["canonical_quantity"], "exposure_time")
        self.assertEqual(d["unit_dimension"], "dose")
        self.assertNotEqual(t["canonical_quantity"], d["canonical_quantity"])

    def test_sputter_axis_is_a_measurement_coordinate(self):
        r = AR.resolve_axis("Sputter time (min)", None, "min", canon=canon)
        self.assertEqual(r["axis_role"], "measurement_coordinate")

    def test_atomic_concentration_is_an_output(self):
        r = AR.resolve_axis("Atomic concentration (%)", None, "%", canon=canon)
        self.assertEqual(r["axis_role"], "output")

    def test_element_prefix_does_not_become_feature_width(self):
        """'W thickness (nm)' is tungsten thickness, not feature WIDTH."""
        r = AR.resolve_axis("W thickness (nm)", None, "nm", canon=canon)
        self.assertEqual(r["canonical_quantity"], "film_thickness")

    def test_dimensional_guard_rejects_and_says_so(self):
        r = AR.resolve_axis("z (ohms)", None, "ohms", canon=canon)
        self.assertNotEqual(r["canonical_quantity"], "spatial_coordinate")
        self.assertTrue(r["rejected_lexical_match"] or r["canonical_quantity"])

    def test_raw_semantics_are_always_preserved(self):
        r = AR.resolve_axis("Q (1/Å)", "site_density", "1/Å", canon=canon)
        self.assertEqual(r["raw_label"], "Q (1/Å)")
        self.assertEqual(r["raw_quantity"], "site_density")


# ============================================================== granularity
class GranularityLogic(unittest.TestCase):
    """"axis_role == condition -> each point is one experiment" is gone."""

    def test_a_recipe_axis_alone_never_splits(self):
        k, ev, review = G.classify("process_condition", "measured",
                                   caption="Growth versus pulse time.",
                                   methods="", body="")
        self.assertEqual(k, "unresolved")
        self.assertTrue(review)

    def test_in_situ_beats_a_recipe_axis(self):
        k, ev, _ = G.classify(
            "process_condition", "measured",
            caption="Film growth (obtained by in-situ SE) versus different "
                    "deposition parameters.",
            methods="films were deposited with various settings", body="")
        self.assertEqual(k, "continuous_or_longitudinal_run")

    def test_separate_executions_do_split(self):
        k, ev, _ = G.classify(
            "process_condition", "measured",
            caption="Growth per cycle as a function of ozone exposure.",
            methods="Films were deposited with different ozone exposures.",
            body="")
        self.assertEqual(k, "independent_process_sweep")

    def test_measurement_and_spatial_axes_never_split(self):
        for role, want in (("measurement_coordinate", "measurement_scan"),
                           ("spatial_coordinate", "spatial_profile"),
                           ("derived_representation", "measurement_scan")):
            k, _, _ = G.classify(role, "measured", caption="", methods="", body="")
            self.assertEqual(k, want, role)

    def test_cycling_of_one_cell_is_longitudinal(self):
        k, _, _ = G.classify("progression_coordinate", "measured",
                             caption="Coulombic efficiency versus cycling number "
                                     "of the same cell.", methods="", body="")
        self.assertEqual(k, "continuous_or_longitudinal_run")

    def test_films_grown_for_different_cycle_counts_do_split(self):
        k, _, _ = G.classify("progression_coordinate", "measured",
                             caption="Thickness versus number of ALD cycles.",
                             methods="Films were grown for different numbers of "
                                     "cycles.", body="")
        self.assertEqual(k, "independent_process_sweep")

    def test_models_are_never_physical(self):
        for sk in ("calculated", "fitted", "simulated"):
            k, _, _ = G.classify("process_condition", sk, caption="", methods="",
                                 body="")
            self.assertEqual(k, "model_or_simulation", sk)

    def test_channels_of_one_measurement_share_an_event(self):
        k, _, _ = G.classify("measurement_coordinate", "measured", caption="XPS",
                             methods="", body="",
                             panel_labels=["O", "C", "W", "F"])
        self.assertEqual(k, "multi_output_measurement")

    def test_single_run_evidence_is_caption_scoped(self):
        """'in-situ QCM was used' in the METHODS must not make every figure of
        the paper one monitored run."""
        k, _, _ = G.classify(
            "process_condition", "measured",
            caption="Growth per cycle as a function of ozone exposure.",
            methods="Growth was monitored in-situ by QCM. Films were deposited "
                    "with different exposures.", body="")
        self.assertEqual(k, "independent_process_sweep")


# =================================================================== corpus
class ReportedFailures(unittest.TestCase):
    """The concrete cases named in the review, on the regenerated corpus."""

    # --- 10.1002_admi.202000318 ------------------------------------------
    def test_admi_fig1_sweeps_mint_cases(self):
        for suffix, n in (("Fig1a", 7), ("Fig1d", 5)):
            r = row("10.1002_admi.202000318", suffix)
            self.assertEqual(r["result_kind"], "independent_process_sweep", suffix)
            self.assertEqual(r["experimental_case_count"], n, suffix)

    def test_admi_giwaxs_Q_is_not_a_condition(self):
        r = row("10.1002_admi.202000318", "Fig6a__exp01")
        self.assertEqual(r["coordinate"], "scattering_vector_q")
        self.assertEqual(r["result_kind"], "measurement_scan")
        self.assertLessEqual(r["experimental_case_count"], 1)

    def test_admi_xrr_model_curves_are_not_experiments(self):
        model = [r for r in results("10.1002_admi.202000318")
                 if str(r["printed_figure_number"]) == "4"
                 and r["result_kind"] in ("model_or_simulation", "simulation",
                                          "model_curve")]
        self.assertGreaterEqual(len(model), 2)
        for r in model:
            self.assertEqual(r["experimental_case_count"], 0, r["result_id"])

    # --- 10.1002_celc.201600139 ------------------------------------------
    def test_celc_sequential_traces_are_not_split(self):
        for r in results("10.1002_celc.201600139"):
            if r["coordinate"] in ("cycle_number", "cycling_number",
                                   "storage_time"):
                self.assertLessEqual(r["experimental_case_count"], 1,
                                     r["result_id"])
                self.assertEqual(r["result_kind"],
                                 "continuous_or_longitudinal_run", r["result_id"])

    def test_celc_nyquist_is_a_spectrum_not_a_profile(self):
        for suffix in ("Fig2a__exp01", "Fig3a__exp01"):
            r = row("10.1002_celc.201600139", suffix)
            self.assertEqual(r["coordinate"], "impedance_real", suffix)
            self.assertEqual(r["result_kind"], "measurement_scan", suffix)

    def test_celc_semantics(self):
        self.assertEqual(row("10.1002_celc.201600139", "Fig3b__exp01")["coordinate"],
                         "storage_time")
        self.assertEqual(row("10.1002_celc.201600139", "Fig1c")["measurand"],
                         "ionic_conductivity")
        self.assertEqual(row("10.1002_celc.201600139", "Fig1c")["coordinate"],
                         "inverse_temperature")

    # --- 10.1002_pssa.201532305 ------------------------------------------
    def test_pssa_fig4_is_in_situ_progression(self):
        for r in results("10.1002_pssa.201532305"):
            if str(r["printed_figure_number"]) == "4":
                self.assertEqual(r["result_kind"],
                                 "continuous_or_longitudinal_run", r["result_id"])
                self.assertEqual(r["experimental_case_count"], 1, r["result_id"])

    def test_pssa_at_h_exposure_is_a_duration_not_a_dose(self):
        r = row("10.1002_pssa.201532305", "Fig4a__exp01")
        self.assertEqual(r["coordinate"], "exposure_time")

    def test_pssa_pressure_sweeps_mint_cases(self):
        r = row("10.1002_pssa.201532305", "Fig9a")
        self.assertEqual(r["result_kind"], "independent_process_sweep")
        self.assertGreaterEqual(r["experimental_case_count"], 2)

    def test_pssa_fig10_is_one_growth_run(self):
        r = row("10.1002_pssa.201532305", "Fig10a")
        self.assertEqual(r["result_kind"], "continuous_or_longitudinal_run")
        self.assertEqual(r["experimental_case_count"], 1)

    def test_pssa_fig11_ald_window_mints_cases(self):
        for suffix in ("Fig11a", "Fig11c"):
            r = row("10.1002_pssa.201532305", suffix)
            self.assertEqual(r["result_kind"], "independent_process_sweep", suffix)
            self.assertGreater(r["experimental_case_count"], 1, suffix)

    def test_pssa_xps_channels_share_one_sample(self):
        """Fig 5 and Fig 12: several elemental curves from ONE film."""
        for fig in ("5", "12"):
            rows = [r for r in results("10.1002_pssa.201532305")
                    if str(r["printed_figure_number"]) == fig]
            self.assertGreater(len(rows), 1, fig)
            self.assertEqual(sum(r["experimental_case_count"] or 0 for r in rows),
                             1, "figure %s minted more than one physical case" % fig)
            self.assertEqual(len({r["physical_case_id"] for r in rows}), 1, fig)

    def test_pssa_fig7_is_a_temporal_trace(self):
        r = row("10.1002_pssa.201532305", "Fig7a")
        self.assertEqual(r["result_kind"], "continuous_or_longitudinal_run")

    # --- provenance / ids -------------------------------------------------
    def test_ids_use_the_printed_figure_number(self):
        """Printed Fig 9 must not be given an id anchored on docling index 12."""
        for r in results("10.1002_pssa.201532305"):
            fn = str(r["printed_figure_number"] or "")
            if fn:
                self.assertTrue(r["figure_slug"].startswith("Fig%s" % fn),
                                "%s has slug %s" % (r["result_id"], r["figure_slug"]))

    def test_no_id_collisions_corpus_wide(self):
        seen = {}
        for d in sorted(p for p in PAPERS.iterdir() if p.is_dir()):
            for r in results(d.name):
                self.assertNotIn(r["result_id"], seen,
                                 "%s collides with %s" %
                                 (r["result_id"], seen.get(r["result_id"])))
                seen[r["result_id"]] = d.name

    def test_recovery_index_namespaces_do_not_cross(self):
        from canonical import sources as S
        idx = S.recovery_index("10.1002_pssa.201532305")
        self.assertIn("by_docling", idx)
        self.assertIn("by_printed", idx)


# ============================================================== invariants
class CorpusInvariants(unittest.TestCase):

    def papers(self):
        return sorted(p.name for p in PAPERS.iterdir()
                      if (p / "resolved" / "results.json").exists())

    def test_nothing_that_is_one_run_is_exploded(self):
        never = {"continuous_or_longitudinal_run", "measurement_scan",
                 "spatial_profile", "multi_output_measurement",
                 "model_or_simulation"}
        for p in self.papers():
            for r in results(p):
                if r["result_kind"] in never:
                    self.assertLessEqual(r["experimental_case_count"] or 0, 1,
                                         "%s/%s" % (p, r["result_id"]))

    def test_every_minted_sweep_case_has_evidence(self):
        for p in self.papers():
            for r in results(p):
                if r["result_kind"] == "independent_process_sweep" and \
                        (r["experimental_case_count"] or 0) > 0:
                    self.assertTrue(r.get("granularity_evidence")
                                    or r.get("experimental_case_reason"),
                                    "%s/%s" % (p, r["result_id"]))

    def test_unresolved_is_never_split(self):
        """Unresolved means "do not SPLIT", not "do not count".

        A one-point series at a single setting is one execution and may carry
        one case; what unresolved evidence may never do is fan a curve out into
        several physical experiments.
        """
        for p in self.papers():
            for r in results(p):
                if r.get("granularity_kind") in (None, "unresolved"):
                    self.assertLessEqual(
                        r["experimental_case_count"] or 0, 1,
                        "%s/%s split on unresolved evidence" % (p, r["result_id"]))

    def test_manifest_groups_by_real_figure(self):
        for p in self.papers():
            man = PAPERS / p / "review.json"
            if not man.exists():
                continue
            m = json.loads(man.read_text())
            self.assertNotIn("?", [g["figure_slug"] for g in m["by_figure"]], p)
            if len(results(p)) > 2:
                figs = {str(r["printed_figure_number"]) for r in results(p)
                        if r["printed_figure_number"]}
                if len(figs) > 1:
                    self.assertGreater(len(m["by_figure"]), 1,
                                       "%s put every record under one group" % p)

    def test_summary_counts_are_auditable(self):
        for p in self.papers():
            s = json.loads((PAPERS / p / "resolved" / "results.json").read_text())["summary"]
            self.assertEqual(s["physical_process_runs"],
                             len(s["physical_case_ids"]), p)
            self.assertEqual(s["measurement_events"],
                             len(s["measurement_event_ids"]), p)
            self.assertEqual(s["unresolved_granularity"],
                             len(s["unresolved_granularity_ids"]), p)


if __name__ == "__main__":
    unittest.main(verbosity=1)
