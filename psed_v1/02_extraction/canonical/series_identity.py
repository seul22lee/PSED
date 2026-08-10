"""
canonical/series_identity.py — measured / calculated / fitted, resolved PER SERIES.

The provenance gate reads `source` at figure or panel level. That is right for a
wholly simulated figure and wrong for the common conformality figure, where one
panel holds measured circles AND a calculated line:

    "The measured (circles) and calculated (line) thickness profiles of a
     1000cycle deposition process of TiO2 from TiCl4 and H2O."

Both series inherited `measured`, so the calculated line was typed
`experimental_profile` and minted its own ExperimentalCase, DepositionRun and
Sample -- the paper appeared to contain twice as many depositions as it
describes.

Two independent signals are used, and a weak one is never allowed to decide
alone:

  * the caption declares a contrast ("measured ... and calculated ...", "circles
    represent the numerical solution and lines the approximate model");
  * the series label names its own kind ("Measured", "Fitting result",
    "Gordon model", "Numerical").

When the caption declares a contrast the label is trusted to resolve which side
of it a series sits on. When there is no contrast the label alone may still type
a series as calculated, because a label like "Fitting result" is self-describing
-- but it can never type a series as *measured*, since an unlabelled curve in a
measured figure is already measured by inheritance.
"""
from __future__ import annotations

import re

MEASURED = re.compile(
    r"\b(measured|measurement|experimental(?:ly)?|observed|exp\.?|data)\b", re.I)
#: 'fitting' is spelled out: \bfit(?:ted)?\b does not match it, which is exactly
#: how "Fitting result" reached the experiment surface in 10.1063_1.5028178.
FITTED = re.compile(
    r"\b(fit|fits|fitted|fitting|regression|least[- ]squares|best[- ]fit|"
    r"guide to the eye)\b", re.I)
CALCULATED = re.compile(
    r"\b(calculated|calculation|computed|model(?:led|ed|ling|ing)?|simulat\w+|"
    r"theor\w+|predicted|prediction|analytic\w*|approximation|approximate|"
    r"numerical|knudsen|bosanquet|gordon)\b", re.I)

#: a caption that explicitly contrasts the two kinds inside one panel
_CONTRAST = re.compile(
    r"measured[^.]{0,60}\band\b[^.]{0,60}(?:calculated|fitted|modell?ed|simulated)"
    r"|(?:calculated|fitted|modell?ed|simulated)[^.]{0,60}\band\b[^.]{0,60}measured"
    r"|circles?[^.]{0,80}\band\b[^.]{0,80}lines?"
    r"|lines?[^.]{0,80}\band\b[^.]{0,80}circles?",
    re.I)


def caption_declares_contrast(caption):
    if not caption:
        return None
    m = _CONTRAST.search(caption)
    return " ".join(m.group(0).split())[:200] if m else None


def series_source_kind(label, caption, figure_source_flag=None):
    """-> (kind, confidence, evidence)

    kind in {measured, fitted, calculated, unknown}. `unknown` means the series
    carries no evidence of its own and must keep whatever the figure/panel flag
    says -- it is not an error and never blocks classification.
    """
    label = (label or "").strip()
    contrast = caption_declares_contrast(caption)

    lab_fit = FITTED.search(label)
    lab_calc = CALCULATED.search(label)
    lab_meas = MEASURED.search(label)

    # a label may not be BOTH; "measured" wins only if nothing modelled is named
    if lab_fit and not lab_meas:
        return ("fitted", "corroborated" if contrast else "label_explicit",
                "series label %r names a fit%s" %
                (label, "; caption contrasts measured with calculated: %r" % contrast
                 if contrast else ""))
    if lab_calc and not lab_meas:
        return ("calculated", "corroborated" if contrast else "label_explicit",
                "series label %r names a calculation%s" %
                (label, "; caption contrast: %r" % contrast if contrast else ""))
    if lab_meas and not (lab_fit or lab_calc):
        # only meaningful when something in the panel is NOT measured
        if contrast:
            return ("measured", "corroborated",
                    "series label %r against caption contrast %r" % (label, contrast))
        return ("measured", "label_explicit", "series label %r" % label)
    return ("unknown", None, None)


def resolve_panel(series_labels, caption, figure_source_flag=None):
    """Resolve every series of one panel together.

    Returns {label: {"kind", "confidence", "evidence", "fit_of"}}.

    `fit_of` links a fitted or calculated curve to the measured curve it
    describes, so the fit is preserved and attached instead of minting a second
    physical run. It is set only when the panel contains exactly one measured
    series -- with two measured curves there is no evidence which one the fit
    belongs to, and an arbitrary choice would be a fabricated link.
    """
    out = {}
    for lab in series_labels:
        k, c, ev = series_source_kind(lab, caption, figure_source_flag)
        out[lab] = {"kind": k, "confidence": c, "evidence": ev, "fit_of": None}

    measured = [l for l, v in out.items() if v["kind"] == "measured"]
    # a figure flagged measured, holding one calculated/fitted curve and one
    # unlabelled curve: the unlabelled one is the measured data
    if not measured and figure_source_flag == "measured":
        unknown = [l for l, v in out.items() if v["kind"] == "unknown"]
        modelled = [l for l, v in out.items() if v["kind"] in ("fitted", "calculated")]
        if len(unknown) == 1 and modelled:
            out[unknown[0]].update(
                kind="measured", confidence="by_elimination",
                evidence="the only series in a measured panel that is not "
                         "labelled as a fit or calculation")
            measured = unknown

    if len(measured) == 1:
        for lab, v in out.items():
            if v["kind"] in ("fitted", "calculated") and lab != measured[0]:
                v["fit_of"] = measured[0]
    return out
