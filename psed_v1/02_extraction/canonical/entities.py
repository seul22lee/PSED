"""
canonical/entities.py — resolve what a digitised curve ACTUALLY IS.

This is the Stage-0 audit classifier promoted to live code. It answers one question
per source entity (one drawn curve), from corroborated documentary evidence:

    is this a physically distinct experimental case, a single monitored run, a
    profile of one specimen, several channels of one measurement, a simulation, a
    model sweep, a fit, re-plotted literature data, a derived representation —
    or is the evidence insufficient to say?

Hard rules, enforced here rather than left to callers:
  * a PlotSeries is never an Experiment;
  * a digitised point is an Observation by default, and is promoted to an
    ExperimentalCase ONLY on independent evidence of separately performed settings;
  * point count, curve smoothness and axis type are recorded as weak signals and
    can never decide a class on their own;
  * `unknown` is a real outcome and is preserved, never forced into a class.

Signal families (independent by construction):
  M  caption/body measurement modality      Me methods-section modality
  R  explicit run-structure statement       I  sample / run identifier
  L  series-label semantics                 F  extraction source flag
  T  table linkage                          X  axis / series-axis structure
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

# ---------------------------------------------------------------- signal tables
MODALITY = [
    (r"in[- ]?situ", "in_situ", "continuous"),
    (r"spectroscopic ellipsometr|\bVASE\b|\bSE\b(?!M)", "ellipsometry", "continuous_if_in_situ"),
    (r"\bQCM\b|quartz crystal microbalance", "qcm", "continuous"),
    (r"real[- ]time", "real_time", "continuous"),
    (r"depth profil|sputter(?:ing)? (?:time|depth)|TOF[- ]?ERDA|\bSIMS\b", "depth_profile", "continuous"),
    (r"\bXRR\b|X-ray reflectivit", "xrr", "discrete"),
    (r"\bSEM\b|\bTEM\b|cross[- ]section", "microscopy", "discrete"),
    (r"\bXPS\b|photoelectron spectro", "xps", "spectrum"),
    (r"\bXRD\b|diffractogram|diffraction pattern", "xrd", "spectrum"),
    (r"\bFTIR\b|infrared spectr|Raman", "vibrational", "spectrum"),
    (r"photocataly|degradation of|C/C0", "photocatalysis", "continuous"),
    (r"impedance|symmetric cell|storage", "electrochemistry", "continuous"),
    (r"contact angle", "contact_angle", "discrete"),
]
RUNSTRUCT_DISCRETE = [
    r"independently varied", r"saturation curves?", r"self[- ]limiting",
    r"determining .{0,25}windows?", r"each (?:film|sample|run) was",
    r"films? were (?:grown|deposited) (?:at|with|using)",
    r"(?:as a function of|versus|vs\.?|influence of|effect of|dependence of)"
    r"[^.]{0,40}(?:temperature|pressure|pulse|purge|exposure|dose|flow|cycles)",
    r"samples? \d+[^.]{0,40}(?:in )?Table",
    # "Plasma exposure times ranging from 3.8 up to 120 s were used" — a methods
    # sentence stating that a parameter took several values ACROSS depositions.
    # This is the run-structure statement the contract admits as evidence that
    # settings were independently varied.
    r"(?:times?|temperatures?|pressures?|flows?|exposures?|doses?)\s+"
    r"ranging from[^;]{0,70}?(?:were used|were applied|were studied|were varied)",
    r"(?:varying|varied)\s+(?:the\s+)?[a-z ]{0,25}"
    r"(?:time|temperature|pressure|flow|exposure|dose)[^;]{0,40}?"
    r"(?:from|between)\s*\d",
]
RUNSTRUCT_CONTINUOUS = [
    r"in[- ]?situ monitor", r"monitored (?:by|with|using)", r"stepwise growth",
    r"during (?:one|a single|the) (?:cycle|run|deposition|exposure)",
    r"as a function of (?:the )?(?:deposition |process |elapsed )?time",
]
SAMPLE_ID = re.compile(
    r"\b(?:samples?|runs?|specimens?)\s+((?:[A-Za-z0-9]+\s*[,;]?\s*(?:and\s*)?){1,8})"
    r"(?:\s*(?:in|of|from)\s+Table\s*\S+)?|\bSeries\s+([A-Z])\b", re.I)
# an enumerated list of prepared samples is the ONLY reliable count of settings
SAMPLE_LIST = re.compile(r"\b(?:samples?|runs?|specimens?)\s+"
                         r"((?:[A-Za-z0-9]+\s*(?:,|and)\s*){1,10}[A-Za-z0-9]+)", re.I)
LIT_LABEL = re.compile(r"\b([A-Z][a-z]{2,})\s*(?:et al\.?)?\s*,?\s*((?:19|20)\d{2})\b")
SIM_LABEL = re.compile(r"\b(model|simulat\w*|knudsen|bosanquet|calculated|fit(?:ted)?|theor\w*)\b", re.I)
FIT_LABEL = re.compile(r"\b(fit|fits|fitted|fitting|linear fit|arrhenius|regression|"
                       r"least[- ]squares|best[- ]fit|guide to the eye|"
                       r"solid line serves)\b", re.I)
#: "…as presented in Figure 2, plotted against…" — the caption says outright that
#: this curve shows data already counted elsewhere. Without it the same eight
#: depositions are counted once in the figure that reports them and again in the
#: figure that re-plots them.
REPLOT = re.compile(
    r"(?:as (?:presented|shown|reported|given)|same data|replotted|re-plotted|"
    r"data from|taken from)\s+(?:in\s+)?(?:Fig(?:ure)?\.?\s*\d+)", re.I)
CONCEPT = re.compile(r"\bschematic|\bdiagram of|illustration|configuration|setup|layout\b", re.I)
# series axes that name a CHANNEL of one measurement rather than a prepared condition
CHANNEL_AXIS = re.compile(r"element|component|peak|orbital|species|channel|signal|"
                          r"quantity|parameter|termination|phase", re.I)
MEASUREMENT_COORD = {
    "angle", "2theta", "binding_energy", "wavelength", "wavenumber", "Binding Energy",
    "Binding energy", "2θ", "2Θ", "2-theta", "Raman shift", "photon energy", "Energy",
    "sputter depth", "sputtering time", "Sputtering time", "Etching time",
    "Sputtering Time", "Ar Sputter Time", "binding energy", "wavelength (nm)",
}
COORDINATE_AXIS = {"spatial_coordinate", "dimensionless_distance"}

CLASSES = ("continuous_trace", "discrete_experimental_sweep", "experimental_profile",
           "multi_output_measurement", "simulation", "model_sweep",
           "imported_literature_data", "fit", "derived_representation",
           "conceptual_figure", "unknown")


def _hits(patterns, text):
    out = []
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            out.append(" ".join(m.group(0).split())[:180])
    return out


# --------------------------------------------------------- setting-axis kinds
#: A quantity that an experimenter SETS before a deposition. Only these can make
#: the points of a sweep separate experiments.
PROCESS_SETTING_AXIS = re.compile(
    r"deposition_temperature|growth_temperature|substrate_temperature|"
    r"^temperature$|hot[- ]?wire[ _]temperature|source[ _]temperature|"
    r"pulse_time|purge_time|dose_time|exposure|residence|"
    r"flow_rate|flow ratio|partial_pressure|working_pressure|"
    r"^pressure$|applied power|plasma power|rf power|"
    r"aspect_ratio|feature_height|channel height|duty cycle", re.I)

#: A quantity that advances WITHIN one run. Its points are stages of a single
#: experiment, never separate experiments -- expanding them is exactly the
#: digitisation-density error the contract forbids.
WITHIN_RUN_AXIS = re.compile(
    r"cycle_number|number of cycles|^cycles?$|^time$|deposition_time|"
    r"process_time|elapsed|sputter\w*[ _]time|etch\w*[ _]time|heating[ _]time|"
    r"measurement number|^position|spatial_coordinate|dimensionless_distance|"
    r"depth|thickness", re.I)


def setting_axis_kind(coordinate):
    """process_setting | within_run | measurement_coordinate | unknown.

    An allow-list, deliberately: an axis nobody has classified stays `unknown`
    and its sweep stays unresolved, rather than defaulting into case minting.
    """
    c = (coordinate or "").strip()
    if not c:
        return "unknown"
    if c in MEASUREMENT_COORD or c in COORDINATE_AXIS:
        return "measurement_coordinate"
    if WITHIN_RUN_AXIS.search(c):
        return "within_run"
    if PROCESS_SETTING_AXIS.search(c):
        return "process_setting"
    if re.search(r"\[eV\]|energy|angle|θ|Θ|wavelength|wavenumber|shift", c, re.I):
        return "measurement_coordinate"
    return "unknown"


#: "at 200, 250 and 300 °C" -- an enumeration of settings in prose. On its own
#: this matched unrelated sentences during the audit, so it counts ONLY when the
#: values it lists coincide with the values the curve actually plots.
#: Only ',' and 'and' join an ENUMERATION. 'to', '-' and '–' make a RANGE, and a
#: range states the span a parameter covered, never the settings that were run:
#: "at 1-10 Torr" was read as the two settings {1, 10} and, because a 16-point
#: growth curve happened to pass through x=1 and x=10, turned a single run into
#: two experiments.
_ENUM_SETTINGS = re.compile(
    r"(?:at|of|for|using|with)\s+((?:\d+(?:\.\d+)?\s*(?:,|and)\s*){1,10}"
    r"\d+(?:\.\d+)?)\s*(°?\s*C\b|K\b|s\b|ms\b|min\b|sccm|Torr|mTorr|mbar|Pa\b|W\b|%)",
    re.I)


def enumerated_settings(text, observed_x):
    """Settings the prose enumerates AND that ACCOUNT FOR the plotted curve.

    Intersecting the curve is not enough — any two numbers in a paper will
    intersect a dense curve somewhere. The enumeration must explain the whole
    series: as many values as the curve has distinct x positions, each matching
    one. That correspondence is what separates a real setting list from a
    coincidence.
    """
    if not text or not observed_x:
        return (None, None)
    obs = []
    for x in observed_x:
        try:
            obs.append(float(x))
        except (TypeError, ValueError):
            pass
    obs = sorted(set(obs))
    if not obs or len(obs) > 12:
        return (None, None)
    for m in _ENUM_SETTINGS.finditer(text):
        vals = sorted(set(float(v) for v in re.findall(r"\d+(?:\.\d+)?", m.group(1))))
        if len(vals) < 2 or len(vals) != len(obs):
            continue
        tol = 0.02 * max(abs(v) for v in obs + vals)
        if all(abs(v - o) <= max(tol, 1e-9) for v, o in zip(vals, obs)):
            return (len(vals),
                    "prose enumerates %s, which accounts for every plotted "
                    "setting: %r" % (vals, " ".join(m.group(0).split())[:140]))
    return (None, None)


#: more separately grown films than this, and a paper enumerates them; beyond it
#: a dense point set is far more likely a digitised line than a run per marker
MAX_UNENUMERATED_SETTINGS = 12


def sweep_setting_cases(classification, coordinate, observed_x, n_points,
                        caption, body, run_structure_hits, table_linked,
                        series_source_kind=None):
    """How many separately performed settings a MEASURED discrete sweep holds.

    Returns (count, method, evidence) or (None, None, reason).

    The previous rule required an explicit sample list, which almost no paper
    provides, so 146 of 151 corroborated sweeps minted zero cases and vanished
    from every experiment surface. This admits three further kinds of evidence
    and still refuses whenever the points could be a resampled line:

      * an enumeration in prose that matches the plotted values;
      * a process-setting x axis plus documentary corroboration that the
        parameter was independently varied;
      * a conditions table linked to the figure.

    It never counts points on a within-run or measurement axis, and never counts
    a fitted, calculated or simulated curve.
    """
    if classification != "discrete_experimental_sweep":
        return (None, None, "not a discrete sweep")
    if series_source_kind in ("fitted", "calculated", "simulated"):
        return (None, None,
                "series is %s; a modelled curve has no separately performed "
                "settings" % series_source_kind)

    axis = setting_axis_kind(coordinate)
    distinct = sorted({x for x in (observed_x or []) if x is not None})

    # The axis is checked FIRST, before any enumeration. A list of settings in
    # the prose cannot make the points of a growth curve or a spectrum into
    # separate experiments no matter how well the numbers line up.
    if axis == "within_run":
        return (None, None,
                "x axis %r advances within one run; its points are stages of a "
                "single experiment, not separate experiments" % coordinate)
    if axis == "measurement_coordinate":
        return (None, None,
                "x axis %r is a measurement coordinate; its points are "
                "observations of one specimen" % coordinate)
    if axis == "unknown":
        return (None, None,
                "x axis %r is not a recognised process setting; the sweep stays "
                "unresolved rather than assuming its points are runs" % coordinate)

    n_enum, enum_ev = enumerated_settings(caption, distinct)
    if not n_enum:
        n_enum, enum_ev = enumerated_settings(body, distinct)
    if n_enum:
        return (n_enum, "enumerated_in_source_and_plotted", enum_ev)

    corroboration = list(run_structure_hits or [])
    if table_linked:
        corroboration.append("conditions table linked to this figure")
    if not corroboration:
        return (None, None,
                "process-setting axis %r but no statement that the parameter was "
                "independently varied; a single signal may not decide" % coordinate)

    if len(distinct) < 2:
        return (None, None, "fewer than two distinct settings plotted")
    if len(distinct) > MAX_UNENUMERATED_SETTINGS:
        return (None, None,
                "%d distinct x values on a process axis exceeds the %d beyond "
                "which markers cannot be told from a resampled line; the paper "
                "does not enumerate them, so the count stays unresolved"
                % (len(distinct), MAX_UNENUMERATED_SETTINGS))
    return (len(distinct), "process_setting_axis_corroborated",
            "x axis %r is a process setting; %d distinct values plotted; %s"
            % (coordinate, len(distinct), "; ".join(corroboration)[:220]))


def supported_setting_count(caption, body):
    """How many separately prepared settings the paper ENUMERATES.

    Only an explicit sample/run list counts. Loose numeric enumerations in prose are
    rejected: during the audit they matched unrelated values (an "at 180 and 200 °C"
    sentence was picked up for an ozone-exposure figure). Returns (count, evidence)
    or (None, None) -> the setting count is UNRESOLVED and no cases may be minted."""
    for text, src in ((caption, "caption"), (body, "body")):
        if not text:
            continue
        m = SAMPLE_LIST.search(text)
        if m:
            ids = [x.strip() for x in re.split(r"\s*(?:,|and)\s*", m.group(1)) if x.strip()]
            if 1 < len(ids) <= 12:
                return len(ids), "%s: %s" % (src, " ".join(m.group(0).split())[:140])
    return None, None


def classify(ent, methods_text=""):
    """ent: dict with caption, body_mentions, source_series, panel_series_axis,
    coordinate, granularity, relevance, is_model_result, panel_source_flag,
    figure_source_flag, representation, n_source_points, table_captions.

    Returns a dict: classification, confidence, method, signals, evidence, votes."""
    cap = ent.get("caption") or ""
    body = ent.get("body_mentions") or ""
    blob = cap + "\n" + body
    label = ent.get("source_series") or ""
    sig = {}

    mods = []
    for rx, name, implic in MODALITY:
        m = re.search(rx, blob, re.I)
        if m:
            mods.append({"modality": name, "implication": implic,
                         "evidence": " ".join(blob[max(0, m.start() - 60):
                                                   m.end() + 80].split())[:180]})
    if mods:
        sig["M"] = mods
    me = []
    for rx, name, implic in MODALITY:
        m = re.search(rx, methods_text or "", re.I)
        if m:
            me.append({"modality": name, "implication": implic,
                       "evidence": " ".join((methods_text or "")[max(0, m.start() - 50):
                                                                 m.end() + 70].split())[:160]})
    if me:
        sig["Me"] = me
    dr = _hits(RUNSTRUCT_DISCRETE, blob)
    cr = _hits(RUNSTRUCT_CONTINUOUS, blob)
    if dr or cr:
        sig["R"] = {"discrete": dr, "continuous": cr}
    sm = SAMPLE_ID.search(cap) or SAMPLE_ID.search(body)
    if sm:
        sig["I"] = " ".join(sm.group(0).split())[:120]
    lit = LIT_LABEL.search(label)
    simm = SIM_LABEL.search(label)
    if lit or simm:
        sig["L"] = {"literature": lit.group(0) if lit else None,
                    "simulation": simm.group(0) if simm else None}
    flag = ent.get("panel_source_flag") or ent.get("figure_source_flag")
    if flag:
        sig["F"] = flag
    tl = [t for t in (ent.get("table_captions") or [])
          if t and re.search(r"paramet|condition|sample|series|process", t, re.I)]
    if tl:
        sig["T"] = tl[:2]
    sa = (ent.get("panel_series_axis") or "").strip()
    if sa:
        sig["X"] = sa
    weak = {"n_source_points": ent.get("n_source_points"),
            "granularity": ent.get("granularity"),
            "note": "weak signals are recorded but never decide a class"}

    why = defaultdict(list)
    votes = Counter()

    def vote(cls, fam, ev):
        votes[cls] += 1
        why[cls].append("%s: %s" % (fam, ev))

    # ---------- 1. PROVENANCE gate ----------
    pv, pw = Counter(), defaultdict(list)

    def pvote(cls, fam, ev):
        pv[cls] += 1
        pw[cls].append("%s: %s" % (fam, ev))

    # SERIES-level source identity outranks the figure/panel flag. A measured
    # figure may hold a calculated line; inheriting "measured" for it is what
    # promoted a fit to an ExperimentalCase with its own DepositionRun.
    ssk = ent.get("series_source_kind")
    if ssk == "fitted":
        pvote("fit", "S", "series resolved as a fit against the caption's "
                          "measured/calculated contrast")
    elif ssk == "calculated":
        pvote("simulation", "S", "series resolved as calculated against the "
                                 "caption's measured/calculated contrast")

    is_fit_label = bool(FIT_LABEL.search(label)) or ssk == "fitted"
    if is_fit_label:
        pvote("fit", "L", "series label %r is a fit/guide, not a simulation" % label)
    elif simm:
        pvote("simulation", "L", "series label %r" % label)
    if lit and not simm:
        pvote("imported_literature_data", "L", lit.group(0))
    if not is_fit_label:
        # a series the caption identifies as MEASURED is not made simulated by
        # the figure-level flag of a mixed figure
        if sig.get("F") == "simulated" and ssk != "measured":
            pvote("simulation", "F", "panel/figure source flag = simulated")
        if ent.get("is_model_result") or ent.get("relevance") == "model":
            pvote("simulation", "F", "pipeline relevance=model")
    msim = re.search(r"[^.]{0,90}(?:simulat\w+|model(?:l)?ed|computed)[^.]{0,60}", cap, re.I)
    # A caption that MENTIONS modelling does not make every curve under it
    # modelled -- "the measured (circles) and calculated (line) profiles" is one
    # caption describing two different kinds of series.
    if msim and ssk not in ("measured", "fitted"):
        pvote("simulation", "R", " ".join(msim.group(0).split())[:180])
    rep = REPLOT.search(cap)
    if rep and not lit:
        pvote("derived_representation", "R",
              "caption re-plots data presented elsewhere: %r"
              % " ".join(rep.group(0).split())[:120])
        # The cross-reference is only evidence if it points at a figure this
        # paper actually has. Resolving it is a second, independent check --
        # a caption may cite a figure of a DIFFERENT paper, and that is
        # imported literature, not a re-plot of our own data.
        _tgt = re.search(r"(\d+)\s*$", rep.group(0))
        _figs = {str(x) for x in (ent.get("paper_figure_numbers") or [])}
        if _tgt and _figs and _tgt.group(1) in _figs \
                and _tgt.group(1) != str(ent.get("figure_number") or ""):
            pvote("derived_representation", "X",
                  "the referenced Figure %s is a figure of this paper and is not "
                  "this one" % _tgt.group(1))
    if CONCEPT.search(cap) and not ent.get("n_source_points"):
        pvote("conceptual_figure", "M", cap[:120])

    if pv:
        cand = pv.most_common(1)[0][0]
        # an author-year label inside a modelling figure is imported MEASURED data
        if "imported_literature_data" in pv and "simulation" in pv:
            cand = "imported_literature_data"
        fams = len({w.split(":")[0] for w in pw[cand]})
        cls = cand
        if cls == "simulation" and ent.get("coordinate") not in COORDINATE_AXIS | {"time"}:
            cls = "model_sweep"
        return _result(cls, fams, "provenance_gate", sig, weak, pv, pw[cand],
                       ent, lit, sa, cap, body)

    # ---------- 2. GRANULARITY, resolved from axis semantics ----------
    # canonical/granularity.py answers "does variation along this curve mean
    # separate physical executions?" from the axis ROLE plus the modality and the
    # paper's run-structure statements. When it reaches a decision, that decision
    # IS the class -- the old `condition axis -> one experiment per point` rule
    # is gone. `unresolved` falls through to the gates and votes below.
    _gran = ent.get("granularity_kind")
    _GRAN_CLASS = {
        "independent_process_sweep": "discrete_experimental_sweep",
        "continuous_or_longitudinal_run": "continuous_trace",
        "measurement_scan": "multi_output_measurement",
        "spatial_profile": "experimental_profile",
        "multi_output_measurement": "multi_output_measurement",
    }
    if _gran in _GRAN_CLASS:
        ev = ["G: granularity resolved as %r from the x-axis role %r"
              % (_gran, ent.get("x_axis_role"))]
        gev = ent.get("granularity_evidence")
        if gev:
            ev.append("G: %s" % gev)
        fams = 2 if gev else 1
        if mods:
            fams += 1
        return _result(_GRAN_CLASS[_gran], fams, "granularity(%s)" % _gran, sig,
                       weak, Counter({_GRAN_CLASS[_gran]: 1}), ev,
                       ent, lit, sa, cap, body)

    # ---------- 3. STRUCTURAL gates on the x axis ----------
    # A MEASUREMENT coordinate (binding energy, 2-theta, wavelength, sputter depth)
    # means this curve is one specimen scanned across that coordinate. What differs
    # BETWEEN curves (an H2 ratio, a temperature) is a between-curve condition and is
    # recorded as such -- it does not make the curve itself a sweep along its own x.
    # The gate only fires when a spectroscopy / depth-profile MODALITY corroborates
    # it. On its own an axis name is a single signal, and letting it decide would
    # promote Stage-0 unknowns on one signal and override genuine sweeps. Without
    # corroboration the axis still votes below, as any other signal does.
    if ent.get("coordinate") in MEASUREMENT_COORD:
        corr = [m["evidence"] for m in mods
                if m["implication"] in ("spectrum", "continuous")
                and m["modality"] in ("xps", "xrd", "vibrational", "depth_profile")]
        if corr:
            ev = ["X: x axis %r is a measurement coordinate; this curve is one "
                  "specimen's scan" % ent.get("coordinate")]
            return _result("multi_output_measurement", 2, "measurement_axis_gate", sig,
                           weak, Counter({"multi_output_measurement": 1}), ev + corr[:2],
                           ent, lit, sa, cap, body)

    if ent.get("coordinate") in COORDINATE_AXIS:
        corr = _hits(RUNSTRUCT_DISCRETE + RUNSTRUCT_CONTINUOUS, blob)
        fams = 1 + (1 if corr else 0) + (1 if mods else 0)
        ev = ["X: x axis %r is a spatial coordinate; this curve is one specimen's "
              "profile" % ent.get("coordinate")]
        # The series' OWN source identity is an independent family: a label
        # reading "experimental profile" under a panel flagged `measured`
        # corroborates the profile from two directions, which is what
        # distinguishes it from the simulated panel beside it.
        if ssk == "measured":
            fams += 1
            ev.append("S: series resolved as measured in its own right (%s)"
                      % (sig.get("F") or "series label"))
        return _result("experimental_profile", fams, "coordinate_axis_gate", sig, weak,
                       Counter({"experimental_profile": 1}), ev + corr[:2],
                       ent, lit, sa, cap, body)

    # A PROCESS-SETTING x axis is the third structural case, and it was missing.
    # The two gates above cover a curve measured ACROSS one specimen; this covers
    # a curve measured ACROSS SETTINGS, where every point is a different
    # deposition. Without it a figure plotting penetration depth against plasma
    # exposure time produced no signal at all -- 10.1021_acs.jpcc.9b08176 Fig. 2
    # holds eight separate depositions and classified as `unknown` with zero
    # votes, so the paper contributed no experiments whatever.
    #
    # It fires only for a MEASURED series: the identical axis under a model curve
    # is a parameter sweep, which the provenance gate has already caught above.
    # Corroboration is required, exactly as for the measurement-axis gate -- an
    # axis name alone is one signal and may not decide a class.
    # One point on a process-setting axis is still one run at one setting -- the
    # Al2O3 and HfO2 depositions of jpcc.9b08176 appear as a single point each,
    # and requiring two would have dropped two real depositions. The degenerate
    # case is handled downstream: a one-observation sweep yields exactly one case
    # and no series.
    in_situ_hint = any(m["modality"] == "in_situ" for m in mods) or \
        any(x["modality"] == "in_situ" for x in me)
    # A CONTINUOUSLY MONITORED curve is excluded first. In-situ SE, QCM, real-time
    # and electrochemical storage measurements record one run as it proceeds, so
    # their x axis is elapsed time WITHIN that run even when it is named
    # "exposure": 10.1002_pssa.201532305 Fig. 4 is "Film growth (obtained by
    # in-situ SE) versus different deposition parameters", one monitored exposure
    # per curve, and calling it a sweep would turn one run into several.
    _continuous = ([m["evidence"] for m in mods
                    if m["implication"] == "continuous"
                    or (m["implication"] == "continuous_if_in_situ" and in_situ_hint)]
                   + _hits(RUNSTRUCT_CONTINUOUS, blob))
    if setting_axis_kind(ent.get("coordinate")) == "process_setting" \
            and ssk != "calculated" and (ent.get("n_source_points") or 0) >= 1 \
            and not _continuous:
        # A real run-structure STATEMENT is required. The `measured` flag is
        # nearly universal on experimental figures, so letting it corroborate
        # would leave the axis name deciding the class on its own.
        corr = _hits(RUNSTRUCT_DISCRETE, blob) + _hits(RUNSTRUCT_DISCRETE,
                                                       methods_text or "")
        if corr and sig.get("F") == "measured":
            corr.append("F: figure/panel source flag = measured")
        if corr:
            ev = ["X: x axis %r is a process setting; each point is a separately "
                  "prepared run, not a point on one specimen"
                  % ent.get("coordinate")]
            return _result("discrete_experimental_sweep", 1 + len(set(corr[:2])),
                           "process_setting_axis_gate", sig, weak,
                           Counter({"discrete_experimental_sweep": 1}),
                           ev + corr[:2], ent, lit, sa, cap, body)

    # ---------- 3. run structure ----------
    in_situ = any(m["modality"] == "in_situ" for m in mods)
    for m in mods:
        imp = m["implication"]
        if imp == "continuous_if_in_situ":
            imp = "continuous" if in_situ else "discrete"
        if imp == "continuous":
            vote("continuous_trace", "M", m["evidence"])
        elif imp == "spectrum":
            vote("multi_output_measurement", "M", m["evidence"])
        elif imp == "discrete":
            vote("discrete_experimental_sweep", "M", m["evidence"])
    me_in_situ = any(x["modality"] == "in_situ" for x in me)
    for x in me:
        imp = x["implication"]
        if imp == "continuous_if_in_situ":
            imp = "continuous" if me_in_situ else "discrete"
        if imp == "continuous" and x["modality"] in ("in_situ", "qcm", "real_time"):
            vote("continuous_trace", "Me", x["evidence"])
        elif imp == "discrete":
            vote("discrete_experimental_sweep", "Me", x["evidence"])
    if cr:
        vote("continuous_trace", "R", cr[0])
    if dr:
        vote("discrete_experimental_sweep", "R", dr[0])
    if sm:
        vote("discrete_experimental_sweep", "I", sig["I"])
    if ent.get("coordinate") in MEASUREMENT_COORD:
        vote("multi_output_measurement", "X",
             "x axis %r is a measurement coordinate, not a prepared condition"
             % ent.get("coordinate"))
    if sa and CHANNEL_AXIS.search(sa):
        vote("multi_output_measurement", "X",
             "series axis %r names a channel of one measurement" % sa)
    elif sa and re.search(r"temperatur|pressure|pulse|purge|flow|dose|exposure|cycle|"
                          r"height|width|opening|thickness|ratio|time", sa, re.I) \
            and re.search(r"\d", label):
        vote("discrete_experimental_sweep", "X",
             "series axis %r with numeric label %r" % (sa, label))

    ranked = votes.most_common()
    fam_of = lambda c: len({w.split(":")[0] for w in why.get(c, [])})
    tie = len(ranked) > 1 and ranked[0][1] == ranked[1][1]
    best = ranked[0][0] if ranked else None
    if tie:
        top = sorted([c for c, v in ranked if v == ranked[0][1]], key=lambda c: -fam_of(c))
        if len(top) > 1 and fam_of(top[0]) > fam_of(top[1]):
            best, tie = top[0], False
        else:
            best = None
    fams = fam_of(best) if best else 0
    if best and fams >= 2:
        return _result(best, fams, "multi_signal", sig, weak, votes, why[best],
                       ent, lit, sa, cap, body)
    reason = ("conflicting signals: " + "/".join(c for c, _ in ranked[:3])) if tie or best is None \
        else ("only one signal family (%s)" % best)
    return _result("unknown", fams, "unresolved", sig, weak, votes,
                   ["unresolved: " + reason], ent, lit, sa, cap, body,
                   unresolved_reason=reason)


def _result(cls, fams, method, sig, weak, votes, evidence, ent, lit, sa, cap, body,
            unresolved_reason=None):
    n_set, set_ev = supported_setting_count(cap, body)
    return {
        "classification": cls,
        "confidence": ("corroborated" if fams >= 2
                       else "single_definitional_signal" if cls != "unknown"
                       else "unresolved"),
        "method": "%s(%d families)" % (method, fams),
        "signal_families": sorted(sig.keys()),
        "signals": sig,
        "weak_signals_not_used_alone": weak,
        "votes": dict(votes),
        "evidence": list(evidence)[:4],
        "unresolved_reason": unresolved_reason,
        # provenance for imported literature (contract: keep BOTH papers)
        "originally_reported_in": lit.group(0) if (lit and cls == "imported_literature_data") else None,
        # setting enumeration — the ONLY basis for minting cases from a sweep
        "supported_setting_count": n_set,
        "supported_setting_evidence": set_ev,
        "between_curve_condition": sa or None,
        "between_curve_value": ent.get("source_series") if sa else None,
    }


# ------------------------------------------------------------------ entity model
#: how many current-paper EXPERIMENTAL CASES a class yields, and what its samples are
CLASS_MODEL = {
    "continuous_trace":            {"case": 1, "measurement": "ContinuousTrace",
                                    "samples_are": "observations", "is_experiment": True},
    "experimental_profile":        {"case": 1, "measurement": "ExperimentalProfile",
                                    "samples_are": "observations", "is_experiment": True},
    "multi_output_measurement":    {"case": 1, "measurement": "MultiOutputMeasurement",
                                    "samples_are": "observations", "is_experiment": True},
    "discrete_experimental_sweep": {"case": "from_evidence", "measurement": "Measurement",
                                    "samples_are": "observations", "is_experiment": True},
    "simulation":                  {"case": 0, "measurement": None,
                                    "samples_are": "simulated_observations", "is_experiment": False},
    "model_sweep":                 {"case": 0, "measurement": None,
                                    "samples_are": "model_predictions", "is_experiment": False},
    "imported_literature_data":    {"case": 0, "measurement": None,
                                    "samples_are": "imported_observations", "is_experiment": False},
    "fit":                         {"case": 0, "measurement": None,
                                    "samples_are": "fitted_values", "is_experiment": False},
    "derived_representation":      {"case": 0, "measurement": None,
                                    "samples_are": "derived_values", "is_experiment": False},
    "conceptual_figure":           {"case": 0, "measurement": None,
                                    "samples_are": "none", "is_experiment": False},
    "unknown":                     {"case": 0, "measurement": None,
                                    "samples_are": "unresolved", "is_experiment": False},
}

ENTITY_CLASS = {
    "continuous_trace": "ContinuousTrace",
    "experimental_profile": "ExperimentalProfile",
    "multi_output_measurement": "MultiOutputMeasurement",
    "discrete_experimental_sweep": "ExperimentSeries",
    "simulation": "SimulationRun",
    "model_sweep": "ModelSweep",
    "imported_literature_data": "ImportedLiteratureObservation",
    "fit": "Fit",
    "derived_representation": "DerivedRepresentation",
    "conceptual_figure": "DerivedRepresentation",
    "unknown": "UnresolvedSourceEntity",
}


def is_current_paper_experiment(cls):
    return CLASS_MODEL.get(cls, {}).get("is_experiment", False)
