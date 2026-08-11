"""
process_id.py  (M4 / §4.1 — process identification, grounded + cited)
---------------------------------------------------------------------
The Argonne characterization task (their Paper 1, Table V/VI): given a target
material and an installed reactor channel set, name a viable ALD process
(precursor + coreactant + cycle). Their LLM agents fail on the long tail because
they rely on model memory. We ground it in the extracted literature and return
CITATIONS.

`identify(material, channels)` queries the KB for precursor→material→coreactant
combinations actually reported for that material, keeps those compatible with the
installed channels, ranks by literature support, and returns a resolved Recipe +
Argonne-format JSON + the papers it came from. Falls back to the ontology
(metal-matched precursors) only when the KB is silent.
"""
import json
from collections import defaultdict

from pipeline.resolve import kb_service as ks
from pipeline.resolve import recipe as recipe_mod

_ONTO = ks.ONTO
_PRECURSORS = _ONTO["individuals"].get("precursors", [])


def _kb_processes(material):
    """(precursor, coreactant) combos reported for `material`, with support + papers."""
    combos = defaultdict(lambda: {"n": 0, "papers": set(), "exp_ids": []})
    for e in ks._load():
        if e.get("material") != material or not e.get("analysis_ready"):
            continue
        prec = next((r.get("species") for r in e.get("reactants") or [] if r.get("role") == "precursor"), None)
        core = next((r.get("species") for r in e.get("reactants") or [] if r.get("role") == "coreactant"), None)
        if not prec:
            continue
        key = (prec, core)
        combos[key]["n"] += 1
        combos[key]["papers"].add(e["_pid"])
        combos[key]["exp_ids"].append(e.get("exp_id"))
    return combos


def _ontology_fallback(material):
    """Precursors for `material` from the ontology when the KB has no process.
    Prefer an explicit `deposits` annotation (chemistry-grounded); else fall back to
    matching the material's metal element in the precursor's names."""
    import re
    metal = re.match(r"([A-Z][a-z]?)", material or "")
    metal = metal.group(1) if metal else None
    out = []
    for p in _PRECURSORS:
        dep = p.get("deposits") or []
        if material in (dep if isinstance(dep, list) else [dep]):
            out.append(p["id"]); continue
        names = [p.get("id"), p.get("formula"), p.get("full_name")] + (p.get("aka") or [])
        if metal and any(metal in str(n) for n in names if n):
            out.append(p["id"])
    return out


# coreactant inference by material class, when the KB has no reported coreactant.
# Ordered preference; the first one present in the installed channels is used.
def _coreactant_candidates(material):
    m = material or ""
    if re.search(r"O(\d|x|$)", m) or m.endswith("O"):          # oxide
        return ["H2O", "O3", "O2", "O2_plasma"]
    if re.search(r"N(\d|x|$)", m) or m.endswith("N"):          # nitride
        return ["NH3", "N2H4", "N2_plasma", "H2"]
    if re.search(r"S(\d|$)", m):                                # sulfide
        return ["H2S"]
    if re.search(r"Se", m):                                     # selenide
        return ["H2Se"]
    return ["H2", "Si2H6", "O2", "H2O"]                         # metals / reducers (best-effort)


import re  # noqa: E402  (used by helpers above)


# channel-name → ontology-id aliases (papers write TDMAHf where the ontology says TDMAH)
_CHAN_ALIAS = {"tdmahf": "TDMAH", "water": "H2O", "tdmat": "TDMAT", "tema-hf": "TEMAHf",
               "ticl4": "TiCl4", "hfcl4": "HfCl4", "zrcl4": "ZrCl4"}


def _canon_channels(channels):
    out = []
    for ch in channels:
        out.append(_CHAN_ALIAS.get(str(ch).strip().lower(), ch))
    return out


def identify(material, channels, top=5):
    """Return ranked candidate processes to deposit `material` on a reactor with the
    given `channels` (1-indexed species list). Each candidate: recipe, channel map,
    compatibility, literature support, citations, Argonne JSON. When the KB has no
    reported coreactant, one is inferred by material class (oxide→H2O/O3, nitride→NH3…)
    among the installed channels."""
    channels = _canon_channels(channels)
    inst = {recipe_mod._norm(c) for c in channels}
    combos = _kb_processes(material)
    cands = []
    for (prec, core), sup in combos.items():
        rec = recipe_mod.Recipe(
            material=material,
            reactants=[recipe_mod.Reactant("A", "precursor", prec)]
            + ([recipe_mod.Reactant("B", "coreactant", core)] if core else []),
            cycle_sequence="AB" if core else "A", provenance="kb")
        cmap, ok = recipe_mod.resolve_channels(rec, channels)
        cands.append({"precursor": prec, "coreactant": core, "compatible": ok,
                      "channels": cmap, "support": sup["n"], "papers": sorted(sup["papers"]),
                      "exp_ids": sup["exp_ids"][:4], "source": "kb",
                      "recipe": rec, "argonne": recipe_mod.to_process(rec)})
    if not any(c["compatible"] for c in cands):      # KB silent/incompatible → ontology fallback
        core = next((cc for cc in _coreactant_candidates(material)
                     if recipe_mod._norm(cc) in inst), None)   # infer coreactant among channels
        for prec in _ontology_fallback(material):
            rec = recipe_mod.Recipe(
                material=material,
                reactants=[recipe_mod.Reactant("A", "precursor", prec)]
                + ([recipe_mod.Reactant("B", "coreactant", core)] if core else []),
                cycle_sequence="AB" if core else "A", provenance="ontology")
            cmap, ok = recipe_mod.resolve_channels(rec, channels)
            cands.append({"precursor": prec, "coreactant": core, "compatible": ok,
                          "channels": cmap, "support": 0, "papers": [], "exp_ids": [],
                          "source": "ontology", "recipe": rec, "argonne": recipe_mod.to_process(rec)})
    # rank: channel-compatible first, then by literature support
    cands.sort(key=lambda c: (c["compatible"], c["support"]), reverse=True)
    return cands[:top]


if __name__ == "__main__":
    # a reactor with TMA, water, DEZ, TiCl4 installed (1-indexed)
    channels = ["TMA", "water", "DEZ", "TiCl4", "TDMAHf"]
    print(f"reactor channels: {channels}\n")
    for material in ("Al2O3", "TiO2", "ZnO", "HfO2"):
        cands = identify(material, channels)
        print(f"== {material} ==")
        if not cands:
            print("  (no KB process; no metal-matched precursor)\n")
            continue
        for c in cands[:3]:
            tag = "✓ installable" if c["compatible"] else "✗ missing channel"
            cite = f"[{', '.join(c['papers'])}]" if c["papers"] else "(ontology only)"
            print(f"  {c['precursor']:6}+{str(c['coreactant']):5}  {tag}  "
                  f"support n={c['support']} {cite}  -> {json.dumps(c['argonne'])}")
        print()
