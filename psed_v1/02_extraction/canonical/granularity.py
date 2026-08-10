"""
canonical/granularity.py — does the variation along a curve mean separate
physical executions?

This replaces the rule the review rejected:

    axis_role == condition  ->  each point is one experiment

which is wrong in both directions. It split in-situ traces whose x axis merely
*names* a recipe quantity (film thickness versus at-H exposure time is one run
being watched, not 25 depositions), and it failed to split genuine sweeps whose
axis the ontology happened to type differently.

Granularity is decided from the axis ROLE (canonical/axis_roles.py) plus the
measurement modality, the run-structure statements in the caption/methods, and
the series' own source kind. It is a separate question from what the axis means,
and it has its own vocabulary:

    independent_process_sweep      split: each setting is a separate execution
    continuous_or_longitudinal_run one run/sample observed over time or cycles
    measurement_scan               one specimen scanned across an instrument axis
    spatial_profile                one specimen measured across position
    multi_output_measurement       several channels of ONE measurement event
    model_or_simulation            never a physical experiment
    unresolved                     evidence insufficient; do NOT split

`unresolved` is a real answer. Nothing here splits by default.
"""
from __future__ import annotations

import re

KINDS = ("independent_process_sweep", "continuous_or_longitudinal_run",
         "measurement_scan", "spatial_profile", "multi_output_measurement",
         "model_or_simulation", "unresolved")

#: the paper stating that settings were realised as SEPARATE executions. A
#: process-condition axis alone is not enough: the same axis appears on in-situ
#: traces where one run is swept continuously.
SEPARATE_EXECUTION_STRONG = [
    r"films? (?:were|was) (?:grown|deposited|prepared|synthesi[sz]ed)\s*(?:at|with|using|for)",
    r"samples? (?:were|was) (?:grown|deposited|prepared)",
    r"each (?:film|sample|run|deposition) was",
    r"(?:separate|individual|different)\s+(?:runs?|depositions?|samples?|films?|experiments?)",
    r"independently varied",
    r"saturation curves?", r"self[- ]limiting", r"determining .{0,25}windows?",
    r"ALD window",
    r"(?:times?|temperatures?|pressures?|flows?|exposures?|doses?|powers?)\s+"
    r"ranging from[^;]{0,70}?(?:were used|were applied|were studied|were varied)",
    r"(?:varying|varied)\s+(?:the\s+)?[a-z ]{0,25}"
    r"(?:time|temperature|pressure|flow|exposure|dose|power)[^;]{0,40}?"
    r"(?:from|between)\s*\d",
    r"different\s+(?:numbers? of\s+)?cycles?",
    r"grown\s+(?:for|with)\s+(?:different|various)\s+",
]

#: WEAK evidence: it describes what the figure PLOTS, not how it was executed.
#: "Film growth versus different deposition parameters" is the caption of an
#: in-situ figure whose panels each sweep one parameter -- it says nothing about
#: whether the x axis within a panel is several runs or one monitored run.
SEPARATE_EXECUTION_WEAK = [
    r"(?:as a function of|versus|vs\.?|influence of|effect of|dependence of)"
    r"[^.]{0,40}(?:temperature|pressure|pulse|purge|exposure|dose|flow|power|parameter)",
    r"different\s+(?:deposition\s+)?parameters?",
]
SEPARATE_EXECUTION = SEPARATE_EXECUTION_STRONG + SEPARATE_EXECUTION_WEAK

#: the paper stating that ONE run/sample was followed. Beats a process-condition
#: axis: "film thickness versus at-H exposure time, monitored in situ" is one
#: deposition, however recipe-like the axis name looks.
SINGLE_RUN = [
    r"in[- ]?situ", r"real[- ]?time", r"\bQCM\b", r"quartz crystal",
    r"monitored (?:by|with|using|during)", r"during (?:one|a single|the) "
    r"(?:cycle|run|deposition|exposure|experiment)",
    r"stepwise growth", r"continuously", r"as the .{0,20}proceed",
    r"of the (?:same|one) (?:sample|film|cell|specimen)",
    r"same (?:sample|film|cell|specimen)",
    r"cycling (?:of|performance|stability)",
    # "storage" alone is far too loose -- it matched an unrelated sentence near
    # a saturation-curve figure and turned separate depositions into one run
    r"storage\s+(?:time|test|period|stability)", r"stored for",
    r"ageing\s+(?:time|test)", r"aging\s+(?:time|test)",
]

#: series labels that name a CHANNEL of one measurement rather than a specimen
CHANNEL_LABEL = re.compile(
    r"^\s*(?:[A-Z][a-z]?\s*\d?[spdf]?(?:\s*\d/\d)?|"
    r"O|C|N|H|F|Si|Al|Ti|Zr|Hf|W|Mo|Ru|Sn|Zn|Fe|Er|Y|Ba|Li|S|Cl|Pt|Ir)\s*"
    r"(?:1s|2s|2p|3d|4f|3p|K|L|M)?\s*$")
CHANNEL_WORD = re.compile(
    r"element|component|peak|orbital|species|channel|signal|core level|"
    r"atomic|composition|phase|contribution", re.I)


def _hit(patterns, text):
    for p in patterns:
        m = re.search(p, text or "", re.I)
        if m:
            return " ".join(m.group(0).split())[:160]
    return None


def looks_like_channels(labels):
    """Do these series look like channels of one measurement (XPS elements,
    orbitals, phases) rather than separate specimens?"""
    labs = [str(x or "").strip() for x in labels if str(x or "").strip()]
    if len(labs) < 2:
        return False
    return sum(1 for x in labs if CHANNEL_LABEL.match(x)) >= max(2, len(labs) - 1)


def classify(x_role, source_kind, caption, methods, body,
             panel_labels=(), series_label="", n_points=0, measurand_role=None):
    """-> (kind, evidence, needs_review_reason)

    `x_role` comes from axis_roles.resolve_axis; `source_kind` is the series'
    measured/calculated/fitted/simulated identity.
    """
    # SCOPE MATTERS. "in-situ QCM was used" in the methods does not make every
    # figure of the paper a single monitored run -- it says what instrument
    # exists. Single-run evidence is therefore read from the FIGURE's own
    # caption and its surrounding discussion; separate-execution evidence may
    # come from the methods too, because that is where a paper states how its
    # films were grown.
    # Narrower still: the CAPTION is authored about this figure, while the body
    # window around a figure reference is wide and picks up neighbouring
    # sentences. An "in-situ" three paragraphs away turned a three-point
    # pressure sweep into one monitored run.
    figure_text = str(caption or "")
    everything = " ".join(str(x or "") for x in (caption, body, methods))

    # 0. anything modelled is out of the physical count entirely
    if source_kind in ("calculated", "fitted", "simulated", "model"):
        return ("model_or_simulation",
                "series source kind is %r" % source_kind, None)

    # 1. several channels of ONE measurement event
    if looks_like_channels(panel_labels) and x_role in (
            "measurement_coordinate", "spatial_coordinate",
            "progression_coordinate"):
        return ("multi_output_measurement",
                "panel series %s name channels of one measurement, not separate "
                "specimens" % list(panel_labels)[:5], None)

    # 2. instrument coordinate -> one specimen scanned
    if x_role == "measurement_coordinate":
        return ("measurement_scan",
                "x is an instrument coordinate; its points are one specimen's "
                "scan", None)
    if x_role == "spatial_coordinate":
        return ("spatial_profile",
                "x is a position within one specimen", None)
    if x_role == "derived_representation":
        return ("measurement_scan",
                "x is a transformed measurement axis (e.g. an Arrhenius "
                "abscissa); its points are measurements of one specimen", None)

    # 3. progression within one run/sample
    if x_role == "progression_coordinate":
        sep = _hit(SEPARATE_EXECUTION, everything)
        one = _hit(SINGLE_RUN, figure_text)
        if one and not sep:
            return ("continuous_or_longitudinal_run",
                    "x advances within one run/sample: %r" % one, None)
        if sep and not one:
            # "films grown for different cycle counts" IS a sweep
            return ("independent_process_sweep",
                    "x is a progression axis but the paper describes separately "
                    "executed runs: %r" % sep, None)
        if one and sep:
            return ("continuous_or_longitudinal_run",
                    "both single-run and separate-run wording present (%r / %r); "
                    "the conservative reading is one run, since splitting a trace "
                    "fabricates experiments while merging only under-counts"
                    % (one, sep), "conflicting run-structure evidence")
        return ("continuous_or_longitudinal_run",
                "x advances within a run and nothing states separate executions",
                None)

    # 4. a recipe variable -> a sweep ONLY with evidence of separate executions
    if x_role in ("process_condition",):
        one = _hit(SINGLE_RUN, figure_text)
        strong = _hit(SEPARATE_EXECUTION_STRONG, everything)
        weak = _hit(SEPARATE_EXECUTION_WEAK, everything)
        if one:
            # A monitored run beats a phrase about what the figure plots.
            # Splitting a trace FABRICATES experiments; declining to split only
            # under-counts, so the tie goes to the conservative reading.
            return ("continuous_or_longitudinal_run",
                    "the axis names a recipe quantity but the paper monitors ONE "
                    "run across it: %r%s" % (
                        one, "; separate-run wording %r is about what the figure "
                        "plots, not how it was executed" % (strong or weak)
                        if (strong or weak) else ""),
                    "single-run and separate-run wording both present"
                    if strong else None)
        if strong:
            return ("independent_process_sweep",
                    "each x value is a separately executed run: %r" % strong, None)
        if weak:
            return ("unresolved",
                    "the caption says the figure plots against %r but never states "
                    "that the settings were separately executed" % weak,
                    "only weak separate-execution evidence")
        return ("unresolved",
                "x is a recipe quantity but nothing states whether the settings "
                "were separately executed or swept within one run",
                "no separate-execution evidence")

    # 5. a measurement setting on one specimen
    if x_role == "measurement_condition":
        return ("measurement_scan",
                "x is a setting of the MEASUREMENT, not of the process", None)

    return ("unresolved", "x-axis role could not be resolved (%r)" % x_role,
            "unresolved axis role")


#: how many physical cases a granularity kind yields for ONE result series
CASE_MODEL = {
    "independent_process_sweep": "per_setting",
    "continuous_or_longitudinal_run": 1,
    "measurement_scan": 1,
    "spatial_profile": 1,
    "multi_output_measurement": "shared",
    "model_or_simulation": 0,
    "unresolved": 0,
}
