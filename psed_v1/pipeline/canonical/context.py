"""
canonical/context.py — scoped context resolution.

The resolver walks scopes NARROWEST FIRST:

    point -> curve -> series -> panel -> figure -> experiment -> method -> paper

and returns the first scope that yields a usable value. Within a scope:

  * candidate values are converted to a common unit before comparison;
  * numerically equivalent candidates collapse to one value, keeping ALL
    provenance;
  * genuinely conflicting candidates return AMBIGUOUS — never a pick, never
    list order.

A paper-scope quantity with several distinct candidates (the 3 conflicting
feature_height values in 10.1039_d0cp03358h) therefore cannot be broadcast onto
every experiment: it resolves to ambiguous unless a narrower scope answers first.
"""
from __future__ import annotations

from . import units as U
from .schema import ContextBinding, SCOPE_ORDER, Status, scope_rank

REL_TOL = 1e-6


class Resolution(object):
    """Outcome of resolving one contextual quantity."""

    def __init__(self, quantity, status, binding=None, candidates=None, reason=None):
        self.quantity = quantity
        self.status = status
        self.binding = binding
        self.candidates = candidates or []
        self.reason = reason

    @property
    def resolved(self):
        return self.status == "resolved"

    def to_dict(self):
        d = {"quantity": self.quantity, "status": self.status}
        if self.binding is not None:
            d.update({k: self.binding.get(k) for k in
                      ("value", "unit", "scope", "source_file", "source_location",
                       "evidence", "confidence")})
            d["origin"] = self.binding.get("origin")
        if self.candidates:
            d["candidates"] = self.candidates
        if self.reason:
            d["unresolved_reason"] = self.reason
        return d


class ContextPool(object):
    """All contextual quantities visible to one curve, tagged by scope."""

    def __init__(self):
        self._by_scope = {s: {} for s in SCOPE_ORDER}

    def add(self, quantity, value, unit, scope, source_file, source_location,
            evidence=None, confidence=1.0, origin=None):
        if quantity is None or value is None:
            return
        if scope not in self._by_scope:
            self._by_scope[scope] = {}
        self._by_scope[scope].setdefault(quantity, []).append(
            ContextBinding.make(quantity, value, unit, scope, source_file,
                                source_location, evidence, confidence, origin))

    def scopes_with(self, quantity):
        return [s for s in SCOPE_ORDER if self._by_scope.get(s, {}).get(quantity)]

    def all_bindings(self, quantity):
        out = []
        for s in SCOPE_ORDER:
            out.extend(self._by_scope.get(s, {}).get(quantity, []))
        return out

    def quantities(self):
        qs = set()
        for s in SCOPE_ORDER:
            qs.update(self._by_scope.get(s, {}).keys())
        return sorted(qs)

    # --- resolution -------------------------------------------------------
    def resolve(self, quantity, target_unit=None):
        """Resolve one contextual quantity. Narrowest scope wins outright: a
        curve-level value overrides a conflicting paper-level one WITHOUT being
        flagged ambiguous, because the narrower scope is genuinely more specific."""
        scopes = self.scopes_with(quantity)
        if not scopes:
            return Resolution(quantity, Status.MISSING_CONTEXT, reason=(
                "no value for %s in any scope (%s)" % (quantity, "/".join(SCOPE_ORDER))))
        scope = scopes[0]                      # SCOPE_ORDER is narrowest-first
        cands = self._by_scope[scope][quantity]
        return self._collapse(quantity, scope, cands, target_unit, scopes)

    def _collapse(self, quantity, scope, cands, target_unit, all_scopes):
        ref_unit = target_unit or cands[0].get("unit")
        norm = []
        unparseable = []
        for c in cands:
            v, u = c.get("value"), c.get("unit")
            try:
                nv = U.convert(float(v), u, ref_unit) if (u and ref_unit) else float(v)
            except Exception:
                unparseable.append(c)
                continue
            norm.append((nv, c))
        if not norm:
            return Resolution(quantity, Status.MISSING_CONTEXT,
                              candidates=[dict(c) for c in cands],
                              reason="no candidate for %s had a convertible unit" % quantity)
        base = norm[0][0]
        equivalent = all(abs(nv - base) <= REL_TOL * max(abs(nv), abs(base), 1e-12)
                         for nv, _ in norm)
        if not equivalent:
            distinct = sorted({round(nv, 12) for nv, _ in norm})
            return Resolution(
                quantity, Status.AMBIGUOUS,
                candidates=[dict(c) for c in cands],
                reason=("%d distinct %s candidates at %s scope (%s %s); "
                        "no narrower scope disambiguates them"
                        % (len(distinct), quantity, scope,
                           ", ".join("%g" % d for d in distinct), ref_unit or "")))
        # equivalent: resolve to one value, retain every provenance record
        winner = ContextBinding(dict(norm[0][1]))
        winner["value"] = base
        winner["unit"] = ref_unit
        if len(norm) > 1:
            winner["equivalent_sources"] = [dict(c) for _, c in norm]
        if unparseable:
            winner["unparseable_sources"] = [dict(c) for c in unparseable]
        winner["scopes_present"] = all_scopes
        if len(all_scopes) > 1:
            winner["overrode_scopes"] = all_scopes[1:]
        return Resolution(quantity, "resolved", binding=winner)

    def resolve_all(self, quantities, target_units=None):
        """Resolve several quantities. Returns (ctx, resolutions, status, reason)
        where ctx is the {quantity: binding} map the rule layer consumes."""
        target_units = target_units or {}
        ctx, res = {}, {}
        status, reason = None, None
        for q in quantities:
            r = self.resolve(q, target_units.get(q))
            res[q] = r.to_dict()
            if r.resolved:
                ctx[q] = r.binding
            elif status is None or r.status == Status.AMBIGUOUS:
                status, reason = r.status, r.reason
        return ctx, res, status, reason
