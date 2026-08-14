"""
canonical/units.py — dimension-aware unit model for the comparison layer.

Design points that matter scientifically (all of them are tested):

  * `cycle` is a BASE DIMENSION, not a dimensionless scalar. nm, nm/cycle, a
    dimensionless fraction and a cycle count are therefore mutually
    non-interchangeable. This is what stops "Å/cycle" from degrading to "nm".
  * `unknown` (an unparseable unit string such as "a.u." or "cps") is a distinct
    outcome from `dimensionless`. An empty unit string is NOT automatically
    dimensionless — callers must supply semantic evidence before treating it so.
  * Temperature is AFFINE (°C <-> K has an offset). Offset units are refused as
    ratio units, so "25 °C / 5 °C" can never be computed.

Python 3.8 compatible (this repo runs 3.8).
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

# --- base dimensions ------------------------------------------------------
# order is fixed; a dimension is a tuple of integer exponents.
BASE = ("length", "mass", "time", "temperature", "amount", "current", "cycle", "angle")


def dim(**kw) -> Tuple[int, ...]:
    return tuple(int(kw.get(b, 0)) for b in BASE)


DIMENSIONLESS = dim()
LENGTH = dim(length=1)
TIME = dim(time=1)
TEMPERATURE = dim(temperature=1)
PRESSURE = dim(mass=1, length=-1, time=-2)
CYCLE = dim(cycle=1)
LENGTH_PER_CYCLE = dim(length=1, cycle=-1)
EXPOSURE = dim(mass=1, length=-1, time=-1)          # Pa*s
ANGLE = dim(angle=1)

DIM_NAME = {
    DIMENSIONLESS: "dimensionless",
    LENGTH: "length",
    TIME: "time",
    TEMPERATURE: "temperature",
    PRESSURE: "pressure",
    CYCLE: "cycle",
    LENGTH_PER_CYCLE: "length_per_cycle",
    EXPOSURE: "exposure",
    ANGLE: "angle",
}


class Unit(object):
    """factor/offset convert TO the SI-ish reference of the dimension:
        si_value = value * factor + offset
    `offset_unit` marks affine units, which may not be used as ratio units.

    `exp10` is set when the unit is EXACTLY a power of ten times the reference
    (all metric prefixes). Converting between two such units then uses a single
    exact multiplier 10**(from.exp10 - to.exp10) instead of a divide-through-SI,
    which would turn 1 µm into 999.9999999999999 nm."""

    __slots__ = ("symbol", "dimension", "factor", "offset", "offset_unit", "exp10")

    def __init__(self, symbol, dimension, factor=1.0, offset=0.0, offset_unit=False,
                 exp10=None):
        self.symbol = symbol
        self.dimension = dimension
        self.factor = float(factor)
        self.offset = float(offset)
        self.offset_unit = bool(offset_unit)
        self.exp10 = exp10

    def __repr__(self):
        return "Unit(%r, %s)" % (self.symbol, DIM_NAME.get(self.dimension, self.dimension))


class UnknownUnit(Exception):
    """Raised when a unit string cannot be parsed. Deliberately NOT the same as
    dimensionless — see module docstring."""


class IncompatibleDimensions(Exception):
    pass


class OffsetUnitMisuse(Exception):
    pass


def _u(symbol, dimension, factor=1.0, offset=0.0, offset_unit=False, exp10=None):
    return Unit(symbol, dimension, factor, offset, offset_unit, exp10)


# --- registry -------------------------------------------------------------
# key: normalised unit token (see `_norm`) -> Unit. Canonical display symbol
# lives on the Unit itself, so "um"/"μm"/"µm" all resolve to the same "µm".
_REG = {}


def _register(unit, *aliases):
    for a in (unit.symbol,) + aliases:
        _REG[_norm(a)] = unit
    return unit


def _norm(s):
    """Normalise a unit token for lookup: lowercase, strip whitespace/dots,
    unify the three micro signs and the two angstrom code points."""
    if s is None:
        return None
    t = str(s).strip()
    t = t.replace("µ", "μ").replace("·", ".")     # MICRO SIGN -> greek mu
    t = t.replace("Å", "å")                             # ANGSTROM SIGN -> a-ring
    t = t.lower()
    t = t.replace(" ", "")
    t = re.sub(r"^\((.*)\)$", r"\1", t)
    return t


# length (SI reference: metre)
M = _register(_u("m", LENGTH, 1.0, exp10=0), "metre", "meter", "metres", "meters")
_register(_u("mm", LENGTH, 1e-3, exp10=-3), "millim", "millimetre", "millimeter")
_register(_u("cm", LENGTH, 1e-2, exp10=-2), "centim", "centimetre", "centimeter")
_register(_u("µm", LENGTH, 1e-6, exp10=-6), "um", "μm", "micron", "microns", "microm",
          "micrometre", "micrometer")
_register(_u("nm", LENGTH, 1e-9, exp10=-9), "nanom", "nanometre", "nanometer")
_register(_u("Å", LENGTH, 1e-10, exp10=-10), "å", "a", "ang", "angstrom", "angstroms", "aa")
_register(_u("pm", LENGTH, 1e-12, exp10=-12), "picom", "picometre")

# time (SI reference: second)
_register(_u("s", TIME, 1.0, exp10=0), "sec", "secs", "second", "seconds")
_register(_u("ms", TIME, 1e-3, exp10=-3), "milli-s", "millisecond", "milliseconds", "msec")
_register(_u("min", TIME, 60.0), "mins", "minute", "minutes")
_register(_u("h", TIME, 3600.0), "hr", "hrs", "hour", "hours")

# pressure (SI reference: pascal)
_register(_u("Pa", PRESSURE, 1.0, exp10=0), "pa", "pascal", "pascals")
_register(_u("kPa", PRESSURE, 1e3, exp10=3), "kpa")
_register(_u("hPa", PRESSURE, 1e2, exp10=2), "hpa")
_register(_u("bar", PRESSURE, 1e5, exp10=5))
_register(_u("mbar", PRESSURE, 1e2, exp10=2), "millibar")
_register(_u("Torr", PRESSURE, 133.32236842105263), "torr")
_register(_u("mTorr", PRESSURE, 0.13332236842105263), "mtorr", "millitorr")
_register(_u("atm", PRESSURE, 101325.0), "atmosphere")

# temperature (SI reference: kelvin) — AFFINE
_register(_u("K", TEMPERATURE, 1.0, exp10=0), "k", "kelvin"),
_register(_u("°C", TEMPERATURE, 1.0, 273.15, offset_unit=True),
          "c", "degc", "deg_c", "degreecelsius", "celsius", "oc", "℃")

# cycle count — its OWN dimension
_register(_u("cycle", CYCLE, 1.0, exp10=0), "cycles", "cyc", "cycle_number", "ald_cycles")

# growth per cycle (reference: metre/cycle)
_register(_u("nm/cycle", LENGTH_PER_CYCLE, 1e-9, exp10=-9), "nm/cyc", "nmpercycle", "nm/c")
_register(_u("Å/cycle", LENGTH_PER_CYCLE, 1e-10, exp10=-10), "å/cycle", "å/cyc", "a/cycle",
          "a/cyc", "angstrom/cycle", "å/cycles")
_register(_u("pm/cycle", LENGTH_PER_CYCLE, 1e-12, exp10=-12), "pm/cyc")

# exposure (reference: Pa*s)
_register(_u("Pa.s", EXPOSURE, 1.0, exp10=0), "pas", "pa*s", "pa-s", "pa.s", "pa·s", "pasec")
_register(_u("Torr.s", EXPOSURE, 133.32236842105263), "torr-s", "torrs", "torr*s",
          "torr.s", "torr·s")

# dimensionless / scale
_register(_u("1", DIMENSIONLESS, 1.0, exp10=0), "-", "dimensionless", "unitless", "ratio",
          "fraction", "num", "none")
_register(_u("%", DIMENSIONLESS, 0.01, exp10=-2), "percent", "pct", "at%", "atomic%")

# angle
_register(_u("deg", ANGLE, 1.0), "degree", "degrees", "°", "o")
_register(_u("rad", ANGLE, 57.29577951308232), "radian", "radians")

# Units that LOOK dimensionless but carry no comparable scale. Parsing these
# must fail loudly rather than silently become "1".
ARBITRARY = {"a.u.", "au", "arb.u.", "arb.units", "arb.unit", "arbitraryunits",
             "cps", "counts", "counts/s", "cnt", "arbitraryunit", "a.u", "arb.u"}


def parse(symbol, allow_empty_as_dimensionless=False):
    """Resolve a unit string to a Unit.

    An EMPTY unit is only dimensionless when the caller passes
    allow_empty_as_dimensionless=True — i.e. when semantic evidence (a resolved
    normalization definition, or an ontology-dimensionless quantity kind) says so.
    Otherwise it raises UnknownUnit, because "" in this corpus is overwhelmingly
    'the extractor did not record a unit', not 'this quantity is a pure ratio'."""
    n = _norm(symbol)
    if n is None or n == "":
        if allow_empty_as_dimensionless:
            return _REG["1"]
        raise UnknownUnit("empty unit string (no semantic evidence that it is dimensionless)")
    if n in ARBITRARY:
        raise UnknownUnit("arbitrary/uncalibrated unit: %r" % symbol)
    u = _REG.get(n)
    if u is None:
        raise UnknownUnit("unrecognised unit: %r" % symbol)
    return u


def try_parse(symbol, allow_empty_as_dimensionless=False):
    """parse() but returns None instead of raising."""
    try:
        return parse(symbol, allow_empty_as_dimensionless)
    except UnknownUnit:
        return None


def dimension_of(symbol, allow_empty_as_dimensionless=False):
    return parse(symbol, allow_empty_as_dimensionless).dimension


def dimension_name(symbol, allow_empty_as_dimensionless=False):
    d = dimension_of(symbol, allow_empty_as_dimensionless)
    return DIM_NAME.get(d, str(d))


def same_dimension(a, b, allow_empty_as_dimensionless=False):
    try:
        return (dimension_of(a, allow_empty_as_dimensionless)
                == dimension_of(b, allow_empty_as_dimensionless))
    except UnknownUnit:
        return False


def _exact_scale(fu, tu):
    """Single exact multiplier for two power-of-ten units of the same dimension.

    Going through the SI reference costs two roundings, so 1 µm -> nm came out as
    999.9999999999999. 10**(exp_from - exp_to) is one exactly-representable
    multiplication for every metric prefix pair in range."""
    if fu.offset or tu.offset or fu.exp10 is None or tu.exp10 is None:
        return None
    d = fu.exp10 - tu.exp10
    if abs(d) > 300:
        return None
    return float(10 ** d) if d >= 0 else 1.0 / float(10 ** -d)


def convert(value, from_symbol, to_symbol, allow_empty_as_dimensionless=False):
    """Convert a scalar between units of the SAME dimension.

    Raises IncompatibleDimensions across dimensions — including cycle vs
    dimensionless and nm vs nm/cycle, which is the whole point of the cycle
    base dimension."""
    if value is None:
        raise ValueError("convert() requires a numeric value; got None "
                         "(the historical bug was calling the converter with value=None)")
    fu = parse(from_symbol, allow_empty_as_dimensionless)
    tu = parse(to_symbol, allow_empty_as_dimensionless)
    if fu.dimension != tu.dimension:
        raise IncompatibleDimensions(
            "cannot convert %s (%s) -> %s (%s)"
            % (fu.symbol, DIM_NAME.get(fu.dimension, fu.dimension),
               tu.symbol, DIM_NAME.get(tu.dimension, tu.dimension)))
    if fu is tu:
        return float(value)      # identity: no float round-trip, no drift
    scale = _exact_scale(fu, tu)
    if scale is not None:
        return float(value) * scale
    si = float(value) * fu.factor + fu.offset
    return (si - tu.offset) / tu.factor


def convert_series(values, from_symbol, to_symbol, allow_empty_as_dimensionless=False):
    """Vector form of convert(). Non-numeric entries are preserved as None so a
    single bad digitized point cannot silently drop the rest of the curve."""
    fu = parse(from_symbol, allow_empty_as_dimensionless)
    tu = parse(to_symbol, allow_empty_as_dimensionless)
    if fu.dimension != tu.dimension:
        raise IncompatibleDimensions(
            "cannot convert %s -> %s" % (fu.symbol, tu.symbol))
    identity = fu is tu
    scale = None if identity else _exact_scale(fu, tu)
    out = []
    for v in values:
        try:
            if identity:
                out.append(float(v))
            elif scale is not None:
                out.append(float(v) * scale)
            else:
                si = float(v) * fu.factor + fu.offset
                out.append((si - tu.offset) / tu.factor)
        except (TypeError, ValueError):
            out.append(None)
    return out


def is_ratio_safe(symbol, allow_empty_as_dimensionless=False):
    """False for affine units: a temperature in °C may not be used as the
    numerator/denominator of a ratio."""
    return not parse(symbol, allow_empty_as_dimensionless).offset_unit


def require_ratio_safe(symbol, role, allow_empty_as_dimensionless=False):
    if not is_ratio_safe(symbol, allow_empty_as_dimensionless):
        raise OffsetUnitMisuse(
            "offset unit %r cannot be used as a %s of a ratio" % (symbol, role))


def canonical_symbol(symbol, allow_empty_as_dimensionless=False):
    """Display form for a unit token ('um' -> 'µm', 'torr' -> 'Torr')."""
    return parse(symbol, allow_empty_as_dimensionless).symbol


def base_symbol(symbol, allow_empty_as_dimensionless=False):
    """The unit a NORMALISED value is expressed in ('°C' -> 'K', 'mbar' -> 'Pa').

    A caller that reports value*factor+offset is holding a number in this unit, and
    labelling it with the original symbol is how 80 °C gets shown as "80 K" or a range
    box asks for °C while filtering kelvin. Returns None when the dimension has no
    unit-scale-1 member in the registry.
    """
    d = dimension_of(symbol, allow_empty_as_dimensionless)
    cands = {u.symbol for u in _REG.values()
             if u.dimension == d and u.factor == 1.0 and u.offset == 0.0}
    return sorted(cands, key=lambda x: (len(x), x))[0] if cands else None


# --- QUDT bridge ----------------------------------------------------------
# The ontology stores QUDT unit IRIs on quantity kinds. Map the trailing token
# back to a registry symbol so ontology-declared canonical units resolve here.
QUDT_TOKEN = {
    "NanoM": "nm", "MicroM": "µm", "MilliM": "mm", "CentiM": "cm", "M": "m",
    "ANGSTROM": "Å", "SEC": "s", "MilliSEC": "ms", "MIN": "min", "HR": "h",
    "DEG_C": "°C", "K": "K", "PA": "Pa", "KiloPA": "kPa", "BAR": "bar",
    "MilliBAR": "mbar", "TORR": "Torr", "ATM": "atm", "PERCENT": "%",
    "UNITLESS": "1", "NUM": "1", "DEG": "deg", "RAD": "rad",
}


def from_qudt(iri_or_token):
    """'http://qudt.org/vocab/unit/NanoM' -> 'nm'. Returns None if unmapped.

    Only an actual IRI is split on '/'. The ontology also stores plain unit
    strings such as 'nm/cycle'; splitting those on '/' would reduce them to
    'cycle' and silently turn a growth-per-cycle quantity into a cycle count."""
    if not iri_or_token:
        return None
    s = str(iri_or_token)
    if "://" in s or "#" in s:
        tok = s.rstrip("/").split("/")[-1].split("#")[-1]
    else:
        tok = s
        u = try_parse(tok)
        if u is not None:
            return u.symbol
    sym = QUDT_TOKEN.get(tok)
    if sym:
        return sym
    u = try_parse(tok)
    return u.symbol if u else None
