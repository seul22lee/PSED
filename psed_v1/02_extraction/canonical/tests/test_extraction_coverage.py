"""Tests that FAIL on the diagnosed experiment-extraction defects.

The existing suites verify transformation fidelity — units, provenance, IDs, KG
visibility — and every one of them passed while a multi-material paper was
collapsed to one chemistry and 146 corroborated sweeps minted zero cases. They
could not catch either, because none of them ties an output back to its input.

These do. Each test names the defect it guards.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.schema import REPO                      # noqa: E402
from canonical import chemistry_scope as cschem        # noqa: E402
from canonical import series_identity as csid          # noqa: E402
from canonical import entities as cent                 # noqa: E402

KB = REPO / "papers"              # papers/<doi>/resolved/
EXTRACTED = REPO / "papers"       # papers/<doi>/extracted/
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def papers():
    return sorted(p.name for p in KB.iterdir()
                  if (p / "resolved" / "results.json").exists())


def load(paper, name):
    f = KB / paper / "resolved" / (name + ".json")
    return json.loads(f.read_text()) if f.exists() else None


def raw_series(paper):
    """Every series drawn in figure_data.json, the true extraction input."""
    f = EXTRACTED / paper / "extracted" / "figure_data.json"
    if not f.exists():
        return []
    d = json.loads(f.read_text())
    out = []
    for fig in d.get("figures", []) or []:
        for pan in fig.get("panels", []) or []:
            for s in pan.get("series", []) or []:
                out.append((str(fig.get("figure")), str(pan.get("panel") or ""),
                            str(s.get("label") or "").strip(),
                            len(s.get("points") or [])))
    return out


class RawSeriesCoverage(unittest.TestCase):
    """Defect R1: the result was split across three files and consumers read one."""

    def test_every_raw_series_has_a_result_record(self):
        for p in papers():
            raw = raw_series(p)
            if not raw:
                continue
            res = load(p, "results")
            self.assertEqual(
                len(raw), res["result_records"],
                "%s: %d raw series but %d result records — a series was "
                "orphaned or duplicated" % (p, len(raw), res["result_records"]))

    def test_no_orphaned_source_series(self):
        """Every figure keeps exactly as many result records as it has curves.

        Counted per FIGURE rather than per panel: a docling panel key like
        'b(i)' is normalised to a bare letter downstream, so a per-panel join
        would report a naming difference as a lost curve.
        """
        for p in papers():
            raw = Counter(f for f, _pan, _lab, _n in raw_series(p))
            if not raw:
                continue
            got = Counter(str(r["fig_docling_index"])
                          for r in load(p, "results")["results"])
            self.assertEqual(dict(raw), dict(got),
                             "%s: per-figure series counts differ — a curve was "
                             "orphaned or duplicated" % p)

    def test_no_points_are_lost_corpus_wide(self):
        for p in papers():
            raw = sum(n for _f, _pan, _lab, n in raw_series(p))
            if not raw:
                continue
            got = sum(r["n_points"] or 0 for r in load(p, "results")["results"])
            self.assertEqual(raw, got, "%s: %d raw points, %d kept" % (p, raw, got))

    def test_results_view_is_self_sufficient(self):
        """A consumer must not need entities/experiments/series to see a curve."""
        need = {"result_id", "paper_id", "printed_figure_number", "panel",
                "source_series_label", "points", "source_kind", "result_kind",
                "granularity", "material", "precursors", "coreactants",
                "provenance", "experimental_case_count"}
        for p in papers():
            rows = load(p, "results")["results"]
            for r in rows[:5]:
                self.assertTrue(need.issubset(r.keys()),
                                "%s: results row missing %s" %
                                (p, need - set(r.keys())))

    def test_every_class_is_reported_somewhere(self):
        """No entity class may fall out of the summary unreported."""
        for p in papers():
            res = load(p, "results")
            rows, summ = res["results"], res["summary"]
            self.assertEqual(summ["source_figure_series"], len(rows), p)
            # the summary keys now fold the granularity vocabulary in, so the
            # partition is over the granularity kinds plus the provenance ones
            counted = sum(Counter(r["result_kind"] for r in rows).values())
            self.assertEqual(counted, len(rows),
                             "%s: %d rows but %d accounted for in the summary"
                             % (p, len(rows), counted))


class Traceability(unittest.TestCase):
    """Defect R1: source series -> resolved entity must be a bijection."""

    def test_result_ids_are_unique(self):
        for p in papers():
            ids = [r["result_id"] for r in load(p, "results")["results"]]
            self.assertEqual(len(ids), len(set(ids)), "%s: duplicate result_id" % p)

    def test_entities_and_results_agree(self):
        for p in papers():
            ents = load(p, "entities") or []
            res = load(p, "results")["results"]
            self.assertEqual(len(ents), len(res), p)
            self.assertEqual({e["entity_id"] for e in ents},
                             {r["result_id"] for r in res}, p)

    def test_no_unexplained_many_to_one_merge(self):
        """Curves may share an experimental identity only as multi-output."""
        for p in papers():
            rows = load(p, "results")["results"]
            shared = [r for r in rows
                      if r["is_current_paper_experiment"]
                      and (r["experimental_case_count"] or 0) == 0
                      and r["result_kind"] not in (
                          "discrete_experimental_sweep",
                          "independent_process_sweep",
                          "fit_or_calculated_representation")]
            for r in shared:
                self.assertIn(
                    r["result_kind"], ("multi_output_measurement", "unresolved",
                                       "measurement_scan", "spatial_profile",
                                       "continuous_or_longitudinal_run"),
                    "%s/%s: an experimental curve with no case and no "
                    "shared-identity evidence" % (p, r["result_id"]))


class SweepGranularity(unittest.TestCase):
    """Defect R2: corroborated sweeps minted zero cases."""

    def test_genuine_sweeps_now_produce_cases(self):
        n = sum(1 for p in papers() for r in load(p, "results")["results"]
                if r["result_kind"] in ("discrete_experimental_sweep",
                                        "independent_process_sweep")
                and (r["experimental_case_count"] or 0) > 0)
        self.assertGreater(n, 40,
                           "sweeps with supported per-setting cases collapsed "
                           "back to the sample-list-only rule")

    def test_unresolved_sweeps_state_why(self):
        for p in papers():
            for r in load(p, "results")["results"]:
                if r["experimental_case_status"] == "unresolved_settings":
                    self.assertTrue(r["experimental_case_reason"],
                                    "%s/%s: unresolved with no reason"
                                    % (p, r["result_id"]))

    def test_within_run_axes_never_become_cases(self):
        """A growth curve versus cycles is ONE run, not one run per cycle.

        CONTRACT CHANGE: "films grown for different cycle counts" IS a sweep, so
        the axis alone no longer decides. The guarantee is now conditional on
        granularity: a curve the evidence calls a continuous run may never be
        split, whatever its axis.
        """
        for p in papers():
            for r in load(p, "results")["results"]:
                if cent.setting_axis_kind(r["coordinate"]) != "within_run":
                    continue
                if r.get("granularity_kind") == "independent_process_sweep":
                    self.assertTrue(r.get("granularity_evidence"),
                                    "%s/%s split without evidence"
                                    % (p, r["result_id"]))
                    continue
                self.assertLessEqual(
                    r["experimental_case_count"] or 0, 1,
                    "%s/%s: %d cases on within-run axis %r — digitisation "
                    "density became experiments" %
                    (p, r["result_id"], r["experimental_case_count"],
                     r["coordinate"]))

    def test_measurement_coordinates_never_become_cases(self):
        for p in papers():
            for r in load(p, "results")["results"]:
                if cent.setting_axis_kind(r["coordinate"]) != "measurement_coordinate":
                    continue
                self.assertLessEqual(
                    r["experimental_case_count"] or 0, 1,
                    "%s/%s: spectrum/profile coordinate %r expanded into %d cases"
                    % (p, r["result_id"], r["coordinate"],
                       r["experimental_case_count"]))

    def test_setting_axis_classification(self):
        self.assertEqual(cent.setting_axis_kind("deposition_temperature"),
                         "process_setting")
        self.assertEqual(cent.setting_axis_kind("cycle_number"), "within_run")
        self.assertEqual(cent.setting_axis_kind("Sputtering time"),
                         "measurement_coordinate")
        self.assertEqual(cent.setting_axis_kind("spatial_coordinate"),
                         "measurement_coordinate")
        self.assertEqual(cent.setting_axis_kind("Binding energy"),
                         "measurement_coordinate")
        # an axis nobody classified must NOT default into case minting
        self.assertEqual(cent.setting_axis_kind("frobnication index"), "unknown")

    def test_enumeration_must_match_the_plotted_values(self):
        """The rejected prose rule matched an unrelated sentence; the values now
        have to be the ones the curve actually plots."""
        n, ev = cent.enumerated_settings("grown at 180 and 200 C", [250, 300])
        self.assertIsNone(n, ev)
        n, ev = cent.enumerated_settings("grown at 250 and 300 C", [250, 300])
        self.assertEqual(n, 2)

    def test_dense_process_axis_stays_unresolved(self):
        n, method, why = cent.sweep_setting_cases(
            "discrete_experimental_sweep", "deposition_temperature",
            list(range(100, 400, 5)), 60, "", "", ["independently varied"], False)
        self.assertIsNone(n)
        self.assertIn("resampled line", why)


class ProcessSettingAxis(unittest.TestCase):
    """10.1021_acs.jpcc.9b08176: a figure whose x axis is plasma exposure time
    held eight separate depositions and produced ZERO signals, so the whole
    paper contributed no experiments. The two structural gates covered a curve
    measured across one specimen; nothing covered a curve measured across
    settings."""

    def test_a_process_setting_axis_is_classified(self):
        """CONTRACT CHANGE. The bespoke process-setting gate was replaced by
        canonical/granularity.py, which decides the same question from the axis
        ROLE plus run-structure evidence. What must hold is that a
        process-condition axis still reaches a decision, by either route."""
        n = sum(1 for p in papers() for r in load(p, "results")["results"]
                if (r["classification_method"] or "").startswith(
                    ("process_setting_axis_gate", "granularity("))
                and r.get("x_axis_role") == "process_condition")
        self.assertGreater(n, 50, "process-condition axes stopped being resolved")

    def test_continuous_monitoring_is_not_a_sweep(self):
        """An in-situ / QCM / real-time curve is one run being watched, even
        when its x axis is named 'exposure'."""
        for p in papers():
            for r in load(p, "results")["results"]:
                if not (r["classification_method"] or "").startswith(
                        "process_setting_axis_gate"):
                    continue
                cap = (r["caption"] or "").lower()
                for kw in ("in-situ", "in situ", "qcm", "real-time",
                           "quartz crystal", "impedance"):
                    self.assertNotIn(
                        kw, cap,
                        "%s/%s: a continuously monitored curve was typed as a "
                        "sweep" % (p, r["result_id"]))

    def test_gate_needs_a_run_structure_statement(self):
        """The `measured` flag is on nearly every experimental figure, so it may
        not corroborate an axis name on its own."""
        for p in papers():
            for r in load(p, "results")["results"]:
                if not (r["classification_method"] or "").startswith(
                        "process_setting_axis_gate"):
                    continue
                ev = [e for e in (r["classification_evidence"] or [])
                      if not e.startswith("X:") and not e.startswith("F:")]
                self.assertTrue(
                    ev, "%s/%s: gate fired on the axis name plus the measured "
                        "flag alone" % (p, r["result_id"]))

    def test_jpcc_yields_its_eight_depositions(self):
        """Ground truth read from the PDF: SiO2 at 3.8/12/38/120 s, TiO2 at
        12/120 s, Al2O3 at 120 s, HfO2 at 120 s."""
        res = load("10.1021_acs.jpcc.9b08176", "results")
        rows = res["results"]
        self.assertEqual(len(rows), 15)
        self.assertEqual(res["summary"]["physical_experimental_cases"], 8)
        by_mat = {r["material"]: r for r in rows
                  if r["result_kind"] in ("discrete_experimental_sweep",
                                          "independent_process_sweep")}
        self.assertEqual(by_mat["SiO2"]["experimental_case_count"], 4)
        self.assertEqual(by_mat["TiO2"]["experimental_case_count"], 2)
        self.assertEqual(by_mat["Al2O3"]["experimental_case_count"], 1)
        self.assertEqual(by_mat["HfO2"]["experimental_case_count"], 1)
        # Figure 1 is pure modelling and stays out of the experiment count
        self.assertEqual(res["summary"]["model_curves"], 9)

    def test_jpcc_chemistry_from_the_methods_sentence(self):
        """"...for the growth of SiO2, TiO2, Al2O3, and HfO2, respectively" —
        the element-hint table left SiO2 and HfO2 with no precursor at all."""
        want = {"SiO2": "BDEAS", "TiO2": "TDMAT",
                "Al2O3": "TMA", "HfO2": "TDMACpH"}
        for r in load("10.1021_acs.jpcc.9b08176", "results")["results"]:
            if r["material"] in want and r["result_kind"] == \
                    "discrete_experimental_sweep":
                self.assertEqual(r["precursors"], [want[r["material"]]],
                                 r["material"])
                self.assertEqual(r["coreactants"], ["O2_plasma"])

    def test_replotted_figures_do_not_double_count(self):
        """jpcc Fig. 3 re-plots Fig. 2's depositions "as presented in Figure 2".
        Counting both would report 14 depositions for a paper that ran 8."""
        rows = load("10.1021_acs.jpcc.9b08176", "results")["results"]
        derived = [r for r in rows
                   if r["result_kind"] == "derived_representation"
                   or r.get("classification") == "derived_representation"]
        self.assertEqual(len(derived), 2)
        for r in derived:
            self.assertEqual(r["experimental_case_count"], 0)
            self.assertTrue(r["points"], "a re-plot lost its points")

    def test_methods_mapping_requires_equal_lists(self):
        got = cschem.methods_chemistry_mapping(
            "The precursors used were A (AA), B (BB) for the growth of "
            "SiO2, TiO2, Al2O3, respectively.", ["SiO2", "TiO2", "Al2O3"])
        self.assertEqual(got, {}, "an unequal pairing must not be aligned")


class MeasuredVersusFit(unittest.TestCase):
    """Defect R3: a calculated line inherited `measured` from its figure."""

    def test_fits_are_not_experiments(self):
        for p in papers():
            for r in load(p, "results")["results"]:
                if r["result_kind"] != "fit_or_calculated_representation":
                    continue
                self.assertEqual(
                    r["experimental_case_count"] or 0, 0,
                    "%s/%s: a fit minted %d experimental case(s)"
                    % (p, r["result_id"], r["experimental_case_count"]))
                self.assertFalse(
                    r["is_current_paper_experiment"],
                    "%s/%s: a fit is flagged as a current-paper experiment"
                    % (p, r["result_id"]))

    def test_no_deposition_run_is_minted_by_a_fit(self):
        """A DepositionRun/Sample exists only where a case does."""
        for p in papers():
            exps = load(p, "experiments") or []
            fits = {r["result_id"] for r in load(p, "results")["results"]
                    if r["result_kind"] == "fit_or_calculated_representation"}
            for e in exps:
                self.assertNotIn(
                    e.get("source_entity_id"), fits,
                    "%s: experiments.json contains a fit" % p)

    def test_calculated_label_beats_the_figure_flag(self):
        got = csid.resolve_panel(
            ["Measured", "Fitting result"],
            "The measured (circles) and calculated (line) thickness profiles of a "
            "1000cycle deposition process of TiO2 from TiCl4 and H2O.",
            "measured")
        self.assertEqual(got["Fitting result"]["kind"], "fitted")
        self.assertEqual(got["Measured"]["kind"], "measured")
        self.assertEqual(got["Fitting result"]["fit_of"], "Measured")
        self.assertIsNone(got["Measured"]["fit_of"])

    def test_fitting_spelling_is_caught(self):
        """`\\bfit(?:ted)?\\b` never matched 'Fitting result' — the exact hole
        through which two fits reached the experiment surface."""
        self.assertTrue(cent.FIT_LABEL.search("Fitting result"))
        self.assertTrue(csid.FITTED.search("Fitting result"))

    def test_fit_links_to_its_measurement(self):
        for p in papers():
            rows = {r["result_id"]: r for r in load(p, "results")["results"]}
            for r in rows.values():
                tgt = r.get("fit_of_entity")
                if not tgt:
                    continue
                self.assertIn(tgt, rows, "%s: fit points at a missing entity" % p)
                self.assertNotEqual(tgt, r["result_id"])


class ChemistryPrecedence(unittest.TestCase):
    """Defect R4: material = scout.materials[0]."""

    def test_no_first_item_fallback(self):
        """On a multi-material paper, a material may only come from evidence."""
        allowed = {"series_legend", "panel_caption_clause", "figure_caption",
                   "figure_scout_note", "figure_body", "paper_single_material"}
        for p in papers():
            for r in load(p, "results")["results"]:
                if not r["multi_material_paper"] or r["material"] is None:
                    continue
                self.assertIn(
                    r["material_scope_level"], allowed,
                    "%s/%s: material %r assigned at level %r"
                    % (p, r["result_id"], r["material"], r["material_scope_level"]))
                self.assertNotEqual(r["material_scope_level"],
                                    "paper_single_material",
                                    "%s: single-material rung used on a "
                                    "multi-material paper" % p)

    def test_resolver_refuses_rather_than_guessing(self):
        got = cschem.resolve_material(
            series_label="Fitting result", caption="Thickness profiles.",
            drill_why=None, body=None, materials=["Al2O3", "TiO2"])
        self.assertIsNone(got["material"])
        self.assertEqual(sorted(got["candidates"]), ["Al2O3", "TiO2"])
        self.assertIn("NOT assigned by list order", got["ambiguity_reason"])

    def test_caption_material_outranks_paper_default(self):
        got = cschem.resolve_material(
            series_label="Measured",
            caption="The measured (circles) and calculated (line) thickness "
                    "profiles of a 1000cycle deposition process of TiO2 from "
                    "TiCl4 and H2O.",
            drill_why=None, body=None, materials=["Al2O3", "TiO2"])
        self.assertEqual(got["material"], "TiO2")
        self.assertEqual(got["scope_level"], "figure_caption")

    def test_caption_chemistry_is_parsed(self):
        got = cschem.caption_chemistry(
            "thickness profiles of a 1000cycle deposition process of TiO2 from "
            "TiCl4 and H2O.", ["Al2O3", "TiO2"])
        self.assertEqual(got["material"], "TiO2")
        self.assertEqual(got["precursor"], "TiCl4")
        self.assertEqual(got["coreactant"], "H2O")

    def test_panel_clause_outranks_figure_caption(self):
        cap = ("Raman spectra of (a) WSx (150 C) and (b) TiSx (100 C) films "
               "grown using different H2 flow ratios, a TiS2 mode.")
        got = cschem.resolve_material(
            series_label="0.80", caption=cap, drill_why=None, body=None,
            materials=["MoS2", "TiS2", "WS2"],
            panel_clause="(a) WSx (150 C)")
        self.assertEqual(got["material"], "WS2")
        self.assertEqual(got["scope_level"], "panel_caption_clause")

    def test_panel_figure_does_not_inherit_another_panels_material(self):
        cap = "Raman spectra of (a) WSx and (b) TiSx films."
        got = cschem.resolve_material(
            series_label="0.80", caption=cap, drill_why=None, body=None,
            materials=["MoS2", "TiS2", "WS2"], panel_clause="(a) something",
            panel_assigns_materials=True)
        self.assertIsNone(got["material"])

    def test_material_precursor_consistency(self):
        for p in papers():
            for r in load(p, "results")["results"]:
                self.assertIsNot(
                    r["chemistry_consistent"], False,
                    "%s/%s: %s" % (p, r["result_id"], r["chemistry_inconsistency"]))

    def test_consistency_check_accepts_named_precursors(self):
        self.assertTrue(cschem.consistent("Er2O3", "tris_dmamb_erbium", "H2O")[0])
        self.assertTrue(cschem.consistent("Fe2O3", "tert-butylferrocene", "O3")[0])
        self.assertTrue(cschem.consistent("Al2O3", "TMA", "H2O")[0])
        self.assertFalse(cschem.consistent("TiO2", "TMA", "H2O")[0])

    def test_unresolved_material_records_its_candidates(self):
        for p in papers():
            for r in load(p, "results")["results"]:
                if r["material"] is None and r["multi_material_paper"]:
                    self.assertTrue(
                        r["material_candidates"] or r["material_ambiguity_reason"],
                        "%s/%s: material dropped with no explanation"
                        % (p, r["result_id"]))


class Ylilammi19Series(unittest.TestCase):
    """The permanent per-series fixture for 10.1063_1.5028178."""

    @classmethod
    def setUpClass(cls):
        cls.fx = json.loads(
            (FIXTURES / "10.1063_1.5028178_series.json").read_text())
        cls.rows = load("10.1063_1.5028178", "results")["results"]
        cls.by = {(str(r["fig_docling_index"]), r["source_series_label"]): r
                  for r in cls.rows}

    def test_all_19_source_curves_are_preserved(self):
        self.assertEqual(len(self.rows), 19)
        self.assertEqual(self.fx["source_series_total"], 19)

    def test_every_series_matches_its_expectation(self):
        for exp in self.fx["series"]:
            key = (exp["fig_docling_index"], exp["series_label"])
            got = self.by.get(key)
            self.assertIsNotNone(got, "missing series %s" % (key,))
            for field in ("classification", "granularity",
                          "experimental_case_count", "is_current_paper_experiment",
                          "material", "precursors", "coreactants",
                          "source_kind", "fit_of_series_label",
                          "material_scope_level", "n_points"):
                self.assertEqual(got[field], exp[field],
                                 "%s %s: %s" % (key, field, got[field]))

    def test_fig7_measured_profile(self):
        r = self.by[("15", "Measured")]
        self.assertEqual(r["material"], "TiO2")
        self.assertEqual(r["precursors"], ["TiCl4"])
        self.assertEqual(r["coreactants"], ["H2O"])
        self.assertEqual(r["result_kind"], "spatial_profile")
        self.assertEqual(r["experimental_case_count"], 1)

    def test_fig7_cycle_count(self):
        ents = load("10.1063_1.5028178", "entities")
        e = next(x for x in ents
                 if x["fig_docling_index"] == "15" and x["source_series"] == "Measured")
        cyc = [b for b in e["bound_conditions"] if b["quantity"] == "cycle_number"]
        self.assertEqual([b["value"] for b in cyc], ["1000"])

    def test_fig7_fit_adds_no_run(self):
        r = self.by[("15", "Fitting result")]
        self.assertEqual(r["result_kind"], "fit_or_calculated_representation")
        self.assertEqual(r["experimental_case_count"], 0)
        self.assertFalse(r["is_current_paper_experiment"])
        self.assertEqual(r["material"], "TiO2")       # same chemistry context
        self.assertEqual(r["fit_of_series_label"], "Measured")

    def test_fig6_is_the_same_shape_with_its_own_chemistry(self):
        m = self.by[("14", "Measured")]
        f = self.by[("14", "Fitting result")]
        self.assertEqual(m["material"], "Al2O3")
        self.assertEqual(m["precursors"], ["TMA"])
        self.assertEqual(m["experimental_case_count"], 1)
        self.assertEqual(f["experimental_case_count"], 0)
        self.assertEqual(f["fit_of_series_label"], "Measured")

    def test_model_curves_are_preserved_and_not_experiments(self):
        model = [r for r in self.rows
                 if r["result_kind"] in ("simulation", "model_curve",
                                         "model_or_simulation")]
        self.assertEqual(len(model), 15)
        for r in model:
            self.assertEqual(r["experimental_case_count"], 0)
            self.assertTrue(r["points"], "a model curve lost its points")

    def test_case_count_is_derived_not_hard_coded(self):
        """The physical experiment count FOLLOWS from the 19 decisions."""
        derived = sum(e["experimental_case_count"] or 0 for e in self.fx["series"])
        live = sum(r["experimental_case_count"] or 0 for r in self.rows)
        self.assertEqual(live, derived)

    def test_no_points_were_lost(self):
        raw = {(f, l): n for f, _p, l, n in raw_series("10.1063_1.5028178")}
        for r in self.rows:
            key = (str(r["fig_docling_index"]), r["source_series_label"])
            self.assertEqual(r["n_points"], raw[key],
                             "%s lost points" % (key,))


if __name__ == "__main__":
    unittest.main(verbosity=1)
