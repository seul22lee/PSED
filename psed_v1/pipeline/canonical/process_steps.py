#!/usr/bin/env python3
"""ALD process-step semantics: a timing quantity plus the step it belongs to.

`pulse_time = 2 s` is not an experimental condition. An ALD cycle is a sequence --
precursor exposure, purge, reactant exposure, purge -- and the same number means a
different experiment in each position. Collapsing all four to `pulse_time`/`purge_time`
made a 2 s TMA dose and a 2 s O2 plasma indistinguishable, and made the two purges of one
cycle unrepresentable at all.

Two layers are kept apart:

    quantity       what was measured        exposure_time / purge_time
    step_context   where in the cycle       precursor_exposure / precursor_purge /
                                            reactant_exposure / reactant_purge

and activation is a property of an EXPOSURE, never of a species and never of a purge:
plasma is not a chemical, and a purge after a plasma step is not itself plasma-active.
"""
import re

# --- the four positions of a binary ALD cycle --------------------------------------
PRECURSOR_EXPOSURE = "precursor_exposure"
PRECURSOR_PURGE = "precursor_purge"
REACTANT_EXPOSURE = "reactant_exposure"
REACTANT_PURGE = "reactant_purge"
STEP_CONTEXTS = (PRECURSOR_EXPOSURE, PRECURSOR_PURGE, REACTANT_EXPOSURE, REACTANT_PURGE)

EXPOSURE_STEPS = (PRECURSOR_EXPOSURE, REACTANT_EXPOSURE)
PURGE_STEPS = (PRECURSOR_PURGE, REACTANT_PURGE)

#: the step each purge follows, which is what makes the two purges distinguishable
FOLLOWS = {PRECURSOR_PURGE: PRECURSOR_EXPOSURE, REACTANT_PURGE: REACTANT_EXPOSURE}

#: canonical timing quantities. The quantity says WHAT was timed; step_context says WHERE.
#: PULSE and EXPOSURE are deliberately DIFFERENT quantities: a pulse time is how long the
#: valve delivers reactant, an exposure time is how long the surface is held in contact
#: with it (a static soak, an extended hold, a plasma exposure). Many reactors make them
#: equal; papers that use stop-flow or hold steps state them separately, and collapsing
#: the two rewrote "0.4 s TMA pulse" as an exposure statement the source never made.
#:
#: DOSE is a third, deliberately UNRESOLVED family. "Dose time" is used in the
#: literature for the valve pulse in some papers and for the whole exposure (including
#: static holds) in others, so the word alone resolves to neither: a dose-worded timing
#: keeps its own kind, and only source wording beyond the word "dose" may place it in
#: the pulse or exposure family. Inventing that equivalence is exactly the collapse the
#: pulse/exposure split exists to prevent.
PULSE_TIME = "pulse_time"
EXPOSURE_TIME = "exposure_time"
DOSE_TIME = "dose_time"
PURGE_TIME = "purge_time"

#: The two SIDES of a half-cycle a timing can describe. A pulse and an exposure both time
#: the reactant-contact side of a step -- they are different measurements of the SAME
#: position in the recipe -- while a purge times the evacuation side. Side identity is
#: what "is this step already stated?" questions need; the fine-grained quantity is what
#: the scientific record keeps.
EXPOSURE_SIDE = "exposure_side"
PURGE_SIDE = "purge_side"

# --- activation is a property of an exposure, not of a species ---------------------
ACTIVATION_NONE = "none"
ACTIVATION_PLASMA = "plasma"
PLASMA_REMOTE = "remote"
PLASMA_DIRECT = "direct"

#: Words that name the ROLE a step plays. Deliberately role words only: a species name is
#: never evidence of a position, because the same chemical can be either reagent.
_PRECURSOR_WORDS = r"precursor|dose|dosing|metal[- ]organic|\bmo\b"
_REACTANT_WORDS = r"reactant|co[- ]?reactant|oxidant|plasma|counter[- ]?reactant|" \
                  r"\bo2\b|\bo₂\b|oxygen|ozone|\bo3\b|water|\bh2o\b|ammonia|\bnh3\b"
_PURGE_WORDS = r"purge|purging|pump[- ]?down|evacuat"
_PLASMA_WORDS = r"plasma"
_REMOTE_WORDS = r"remote|downstream"
_DIRECT_WORDS = r"direct|capacitively|\bccp\b"


def _has(pat, text):
    return bool(re.search(pat, text or "", re.I))


def classify_step(label, *, role_hint=None, species=None):
    """(step_context, evidence) for a timing label such as a figure axis.

    `role_hint` is a persisted role for the series/axis when the pipeline already knows
    one; it outranks the wording. Species is accepted for provenance ONLY -- it never
    decides the position, because naming a chemical does not say which half-cycle it is.
    """
    txt = label or ""
    purge = _has(_PURGE_WORDS, txt)
    ev = []
    role = None
    if role_hint in ("precursor", "reactant", "coreactant"):
        role = "precursor" if role_hint == "precursor" else "reactant"
        ev.append("persisted role %r on the series/axis" % role_hint)
    elif _has(_PRECURSOR_WORDS, txt):
        role = "precursor"
        ev.append("label names the precursor half-cycle")
    elif _has(_REACTANT_WORDS, txt):
        role = "reactant"
        ev.append("label names the reactant half-cycle")
    if role is None:
        return None, ["no role evidence in %r" % txt]
    if purge:
        ev.append("label names a purge")
        return (PRECURSOR_PURGE if role == "precursor" else REACTANT_PURGE), ev
    ev.append("label names an exposure")
    return (PRECURSOR_EXPOSURE if role == "precursor" else REACTANT_EXPOSURE), ev


def classify_activation(label, step_context=None):
    """(activation, plasma_type, evidence) for an exposure.

    A purge is never reported as plasma-active: the plasma is off while the chamber is
    being purged. What a purge carries instead is which step it follows, and that step's
    activation -- expressed through `preceding_activation`, never as its own.
    """
    txt = label or ""
    if step_context in PURGE_STEPS:
        return ACTIVATION_NONE, None, ["a purge is not an activated exposure"]
    if not _has(_PLASMA_WORDS, txt):
        return ACTIVATION_NONE, None, ["no activation named in %r" % txt]
    ptype = (PLASMA_REMOTE if _has(_REMOTE_WORDS, txt)
             else PLASMA_DIRECT if _has(_DIRECT_WORDS, txt) else None)
    ev = ["label names a plasma"]
    if ptype:
        ev.append("plasma type %r stated in the label" % ptype)
    return ACTIVATION_PLASMA, ptype, ev


#: What a source's word for a timed thing MEANS. "pulse" names the valve-delivery
#: duration; "exposure", "soak", "hold" and "dwell" name a contact/hold duration; a
#: plasma time is a plasma exposure duration (its plasma-ness lives in `activation`,
#: never in the quantity name). "dose"/"dosing" resolve to NEITHER family: the
#: literature uses the word both ways, so a dose keeps its own unresolved kind. The
#: families are never folded into one quantity: which family a number belongs to is
#: part of what the source said, and rewriting a stated pulse as an exposure -- or a
#: dose as either -- is a different physical claim. WHERE the timing sits in the cycle
#: remains step_context's job; the shared position is expressed by `timing_side`, never
#: by renaming the quantity. (A reactor RESIDENCE time is not a cycle-step timing at
#: all and is deliberately absent from this table.)
_TIMING_ALIAS = {"pulse_time": PULSE_TIME, "pulse_length": PULSE_TIME,
                 "pulse_duration": PULSE_TIME,
                 "dose_time": DOSE_TIME, "dosing_time": DOSE_TIME,
                 "exposure_time": EXPOSURE_TIME, "soak_time": EXPOSURE_TIME,
                 "hold_time": EXPOSURE_TIME, "dwell_time": EXPOSURE_TIME,
                 "plasma_time": EXPOSURE_TIME,
                 "plasma_exposure_time": EXPOSURE_TIME,
                 "purge_time": PURGE_TIME, "purging_time": PURGE_TIME}

#: which side of a half-cycle each canonical timing quantity describes. A dose, whatever
#: family it turns out to be, times the reactant-contact side.
_TIMING_SIDE = {PULSE_TIME: EXPOSURE_SIDE, EXPOSURE_TIME: EXPOSURE_SIDE,
                DOSE_TIME: EXPOSURE_SIDE, PURGE_TIME: PURGE_SIDE}

#: kinds whose FAMILY is genuinely unresolved: they name a contact-side timing without
#: saying whether it is the valve pulse or the surface exposure
_FAMILY_UNRESOLVED_KINDS = frozenset({DOSE_TIME})


def timing_family_resolved(quantity):
    """The resolved pulse/exposure/purge family of a timing quantity, or None.

    A dose-kind quantity has a KIND but no resolved FAMILY -- the source's word does not
    say which physical duration it is -- so it answers None here while still answering
    `timing_kind` and `timing_side`.
    """
    kind = timing_kind(quantity)
    if kind in _FAMILY_UNRESOLVED_KINDS:
        return None
    return kind


#: Role prefixes a source may put in front of a timing quantity. They name the half-cycle
#: rather than a different measurement, so the KIND of timing survives stripping them.
_ROLE_PREFIXES = ("precursor_", "coreactant_", "reactant_", "purge_gas_", "carrier_gas_")


def timing_kind(quantity):
    """PULSE_TIME / EXPOSURE_TIME / PURGE_TIME for a timing quantity, role prefix and all.

    `precursor_pulse_time` and `pulse_time` are the same KIND of measurement written at
    two levels of qualification; a check that only understood the bare form let a broad
    "TMA pulse time" land on a case that already stated its precursor pulse explicitly.
    Use this when the pulse/exposure distinction matters; use `timing_side` to ask "is
    this position of the cycle already recorded?", which a pulse and an exposure both
    answer for the same step.
    """
    q = str(quantity or "").strip().lower()
    direct = _TIMING_ALIAS.get(q)
    if direct:
        return direct
    for pref in _ROLE_PREFIXES:
        if q.startswith(pref):
            return _TIMING_ALIAS.get(q[len(pref):])
    return None


def timing_side(quantity):
    """EXPOSURE_SIDE / PURGE_SIDE for a timing quantity, or None.

    A pulse time and an exposure time are different measurements of the SAME position in
    the cycle, so slot-occupancy questions ("does this case already state a timing for
    the TMA step?") compare sides, never fine kinds.
    """
    return _TIMING_SIDE.get(timing_kind(quantity))


def step_side(step_context):
    """EXPOSURE_SIDE / PURGE_SIDE for a step context, or None."""
    if step_context in EXPOSURE_STEPS:
        return EXPOSURE_SIDE
    if step_context in PURGE_STEPS:
        return PURGE_SIDE
    return None


def timing_role(quantity, step_context=None, species_role=None):
    """'precursor' / 'coreactant' for a timing quantity, from any recorded evidence.

    The role can be written three ways: as a prefix on the quantity itself
    (`precursor_pulse_time`), as the step the record resolved (`precursor_exposure`), or
    as a persisted reactant role. Any one of them names the half-cycle; none is invented.
    """
    q = str(quantity or "").strip().lower()
    for pref in ("precursor_",):
        if q.startswith(pref):
            return "precursor"
    for pref in ("coreactant_", "reactant_"):
        if q.startswith(pref):
            return "coreactant"
    if step_context in (PRECURSOR_EXPOSURE, PRECURSOR_PURGE):
        return "precursor"
    if step_context in (REACTANT_EXPOSURE, REACTANT_PURGE):
        return "coreactant"
    if species_role in ("precursor", "coreactant"):
        return species_role
    if species_role == "reactant":
        return "coreactant"
    return None


def specialize_timing_quantity(quantity, step_context=None, species_role=None):
    """The role-qualified spelling of a timing quantity, KIND preserved.

    `pulse_time` with precursor-step evidence becomes `precursor_pulse_time` -- the same
    measurement, now saying whose half-cycle it times. The kind is never rewritten: a
    pulse stays a pulse and an exposure stays an exposure, because which family the
    source used is part of what it asserted. With no role evidence the quantity is
    returned unchanged, and a non-timing quantity is always returned unchanged.
    """
    kind = timing_kind(quantity)
    if not kind:
        return quantity
    role = timing_role(quantity, step_context, species_role)
    if not role:
        return kind
    return "%s_%s" % (role, kind)


def timing_slot(quantity, step_context=None, species=None, species_role=None):
    """The physical slot a timing condition occupies: (side, role or '', species or '').

    Two records land in one slot exactly when they time the same position of the same
    reagent's half-cycle -- however they spell the quantity. A record that does not name
    a role occupies the role-less slot; matching it to a qualified sibling is a separate,
    explicit act (`fold` logic), never a property of the key.
    """
    side = timing_side(quantity)
    if not side:
        return None
    role = timing_role(quantity, step_context, species_role) or ""
    return (side, role, str(species or ""))


def canonical_timing_quantity(quantity):
    """The canonical kind for an UNPREFIXED timed-step quantity, or None.

    Note: `pulse_time` now canonicalises to PULSE_TIME, not EXPOSURE_TIME -- the two are
    different quantities (delivery vs contact duration) and are related only through
    `timing_side`.
    """
    return _TIMING_ALIAS.get(str(quantity or "").strip().lower())


def timing_quantity(step_context):
    """The generic contact/purge quantity for a step, when nothing finer is known.

    Position lives in step_context, not here. When the SOURCE named the timing family
    (pulse vs exposure), keep that family and use `specialize_timing_quantity` instead:
    this fallback answers only "a step of this side was timed", and EXPOSURE_TIME here
    means contact duration in the broadest sense.
    """
    if step_context in PURGE_STEPS:
        return PURGE_TIME
    if step_context in EXPOSURE_STEPS:
        return EXPOSURE_TIME
    return None


def sequence_corroboration(labels, evidence_text=None):
    """Evidence, BESIDES print order, that these panels run as one recipe sequence.

    Print order on its own is not evidence: panels can be laid out by importance, by
    material, or in any order an author likes, and inferring "this purge follows that
    dose" from adjacency alone would manufacture a half-cycle assignment the source never
    made. Two things do count -- the figure's own text describing a dose/purge sequence,
    and a printed run that actually ALTERNATES exposure and purge, which is the recipe's
    own shape and not something an arbitrary layout produces.
    """
    if evidence_text and _has(_PURGE_WORDS, evidence_text) and (
            _has(_PRECURSOR_WORDS, evidence_text) or _has(_REACTANT_WORDS, evidence_text)):
        return "the figure's own text describes the dose/purge sequence"
    kinds = []
    for lab in labels:
        if _has(_PURGE_WORDS, lab or ""):
            kinds.append("purge")
        elif classify_step(lab)[0] in EXPOSURE_STEPS:
            kinds.append("exposure")
    if (len(kinds) >= 4 and kinds[0] == "exposure"
            and all(kinds[i] != kinds[i + 1] for i in range(len(kinds) - 1))):
        return "the printed panels alternate exposure and purge"
    return None


def resolve_panel_sequence(labels, *, role_hints=None, species=None, evidence_text=None):
    """Resolve a figure's timing panels together, so a bare label gets its position.

    A panel labelled only "Purge time" says nothing about which half-cycle it purges. The
    figure does: it is the purge that follows the dose panel beside it. Panels are read in
    printed order and an unqualified purge takes the role of the exposure most recently
    established, which is the sequence the recipe itself runs in. A purge with no
    preceding exposure stays unresolved rather than guessing.
    """
    role_hints = role_hints or {}
    species = species or {}
    corroboration = sequence_corroboration(labels, evidence_text)
    out, last_exposure = [], None
    for i, lab in enumerate(labels):
        hint = role_hints.get(i) or role_hints.get(lab)
        step, _ = classify_step(lab, role_hint=hint)
        if (step is None and _has(_PURGE_WORDS, lab or "") and last_exposure
                and corroboration):
            # a bare purge belongs to the exposure it follows -- but only where something
            # beyond the layout says these panels are a sequence at all
            hint = ("precursor" if last_exposure["step_context"] == PRECURSOR_EXPOSURE
                    else "reactant")
        rec = describe_step(lab, role_hint=hint, species=species.get(i),
                            preceding=last_exposure)
        if rec["step_context"] in PURGE_STEPS and last_exposure:
            rec["evidence"] = rec["evidence"] + [
                "printed after the %s panel in the same figure"
                % last_exposure["step_context"]]
            if corroboration:
                rec["evidence"] = rec["evidence"] + [corroboration]
                rec["sequence_corroboration"] = corroboration
        if rec["step_context"] in EXPOSURE_STEPS:
            last_exposure = rec
        out.append(rec)
    return out


#: which timing KIND a label's own wording names. Pulse words name the delivery
#: duration; exposure/soak/hold/dwell words -- and a plasma time, which is a plasma
#: exposure duration -- name the exposure; dose words name the unresolved dose kind,
#: because the literature uses "dose" for both physical durations. The step position
#: never overrides what the source wrote, and precedence runs from the more specific
#: wording: a "plasma dose" is a dose whose activation is plasma, not thereby a pulse.
_PULSE_FAMILY_WORDS = r"pulse"
_DOSE_FAMILY_WORDS = r"dos(?:e|ing)"
_EXPOSURE_FAMILY_WORDS = r"exposure|soak|hold|dwell|plasma"


def timing_family_from_label(label):
    """PULSE_TIME / EXPOSURE_TIME / DOSE_TIME / PURGE_TIME named by the wording, or None.

    Returns the KIND the label names, which for a dose-worded label is the unresolved
    dose kind: the word alone does not place it in the pulse or exposure family, and
    `timing_family_resolved` reports that unresolvedness to consumers that need the
    physical family rather than the spelling.
    """
    txt = label or ""
    if _has(_PURGE_WORDS, txt):
        return PURGE_TIME
    if _has(_PULSE_FAMILY_WORDS, txt):
        return PULSE_TIME
    if _has(_DOSE_FAMILY_WORDS, txt):
        return DOSE_TIME
    if _has(_EXPOSURE_FAMILY_WORDS, txt):
        return EXPOSURE_TIME
    return None


def describe_step(label, *, role_hint=None, species=None, preceding=None):
    """The structured record for one timed ALD step.

    A purge carries `follows` and, when the step it follows was activated, that step's
    species and activation as PRECEDING context -- so "the purge after the O2 plasma" is
    representable without ever claiming the purge was itself plasma-active.

    The quantity keeps the FAMILY the label wrote: a panel that says "Dose time" times a
    pulse, one that says "Plasma time" times an exposure. Only a label that names no
    family falls back to the step's generic contact/purge quantity.
    """
    step, ev = classify_step(label, role_hint=role_hint, species=species)
    if step is None:
        return {"step_context": None, "quantity": None, "activation": None,
                "evidence": ev, "source_label": label}
    act, ptype, aev = classify_activation(label, step)
    fam = timing_family_from_label(label)
    q = fam if fam and _TIMING_SIDE.get(fam) == step_side(step) else timing_quantity(step)
    rec = {"step_context": step, "quantity": q,
           "species": species, "activation": act, "plasma_type": ptype,
           "source_label": label, "evidence": ev + aev}
    if step in PURGE_STEPS:
        rec["follows"] = FOLLOWS[step]
        if preceding:
            rec["preceding_species"] = preceding.get("species")
            rec["preceding_activation"] = preceding.get("activation")
            rec["evidence"] = rec["evidence"] + [
                "follows the %s step" % FOLLOWS[step]]
    return rec


#: Delivery channels are sometimes named by fusing the activation onto the chemical --
#: "O2_plasma", "N2_plasma". That is a channel identifier, not a species: the chemical is
#: O2 and the plasma is how it was delivered. Splitting them keeps a plasma-activated O2
#: step comparable with a thermal O2 step as the same reagent under different activation.
_ACTIVATION_SUFFIX = {"_plasma": ACTIVATION_PLASMA, "-plasma": ACTIVATION_PLASMA,
                      " plasma": ACTIVATION_PLASMA}


def split_activated_species(token):
    """('O2_plasma') -> ('O2', 'plasma'). ('H2O') -> ('H2O', None)."""
    t = (token or "").strip()
    low = t.lower()
    for suf, act in _ACTIVATION_SUFFIX.items():
        if low.endswith(suf) and len(t) > len(suf):
            return t[: -len(suf)].rstrip("_- "), act
    return (t or None), None


def condition_key(quantity, step_context=None, species=None, activation=None):
    """The identity of a timed condition.

    Two conditions are the same only when the quantity, the position in the cycle, the
    reagent AND the activation all agree. Without the position, a 2 s precursor dose and a
    2 s plasma exposure compare equal, which is how a saturation curve for one reagent
    silently became evidence about the other. Without the activation, a 2 s thermal O2
    exposure and a 2 s O2 PLASMA exposure compare equal, which is a different process
    reported as the same one -- the plasma is the whole point of the experiment.
    """
    return "%s@%s@%s@%s" % (quantity or "", step_context or "", species or "",
                            activation or "")
