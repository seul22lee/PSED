#!/usr/bin/env python3
"""READ-ONLY. Correction #9 — can the missing pressures be recovered DETERMINISTICALLY
from local text, before any LLM call is proposed?

For the 13 papers with a pressure in document.md and an empty pressure.json, extract:
  * explicit pressure-unit expressions
  * symbolic forms p_A, p_A0, p_B, pA, pB
  * assertion status: direct | estimated | assumed | fitted
  * pressure vs EXPOSURE (a Pa*s / Torr*s product is not a pressure)
  * species and figure applicability
and report what a deterministic parser would and would not resolve.
"""
import json, re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "reports" / "condition_binding_diagnosis"
EX = REPO / "03_corpus" / "extracted"

PUNIT = r"(?:mTorr|Torr|mbar|hPa|kPa|MPa|Pa|atm|bar)"
NUM = r"[-+]?\d*\.?\d+(?:\s*[x×]\s*10\s*[-–]?\d+)?(?:[eE][-+]?\d+)?"
# exposure = pressure * time  -> NOT a pressure
EXPOSURE = re.compile(r"(" + NUM + r")\s*(" + PUNIT + r")\s*[·⋅*.]?\s*s\b|"
                      r"(" + NUM + r")\s*(" + PUNIT + r")\s*(?:s|sec|second)\b(?!\w)", re.I)
PLAIN = re.compile(r"(" + NUM + r")\s*(" + PUNIT + r")\b")
SYMBOL = re.compile(r"(𝑝|p)\s*[_ ]?\s*(A0|B0|A|B)\b\s*[=≈]\s*(" + NUM + r")\s*(" + PUNIT + r")",
                    re.I)
STATUS = [(re.compile(r"\b(?:we\s+)?estimat\w+", re.I), "estimated"),
          (re.compile(r"\bassum\w+", re.I), "assumed"),
          (re.compile(r"\bfitt?\w+", re.I), "fitted"),
          (re.compile(r"\btypical\w*|\bnominal\w*|\bca\.|\babout\b|approximately", re.I), "approximate")]
SPECIES = re.compile(r"\(?\s*(?:A|B)\s*=\s*([A-Za-z0-9()]+)\s*\)?")
FIGREF = re.compile(r"[Ff]ig(?:ure)?s?\.?\s*(\d+)")


def status_of(win):
    for rx, s in STATUS:
        if rx.search(win):
            return s
    return "direct"


MANIFEST = REPO / "03_corpus" / "extraction_manifest.json"


def normalize_math(t):
    """docling emits MATHEMATICAL ITALIC letters for symbols, so the literal text is
    'we estimate \U0001D45D \U0001D434 = 325 mTorr', not 'p_A = 325 mTorr'.
    Any deterministic symbol parser MUST fold these to ASCII first."""
    out = []
    for ch in t:
        o = ord(ch)
        if 0x1D400 <= o <= 0x1D7FF:                      # Mathematical Alphanumeric Symbols
            for base, start in ((0x41, 0x1D434), (0x61, 0x1D44E),   # italic upper / lower
                                (0x41, 0x1D400), (0x61, 0x1D41A),   # bold upper / lower
                                (0x41, 0x1D468), (0x61, 0x1D482)):  # bold-italic
                if start <= o < start + 26:
                    out.append(chr(base + o - start))
                    break
            else:
                out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def main():
    keep = set((json.loads(MANIFEST.read_text()).get("papers") or {}).keys())
    targets = []
    for d in sorted((EX).iterdir()):
        if not d.is_dir() or d.name not in keep:
            continue          # cremers2019 is a stale non-manifest leftover
        pj = d / "pressure.json"
        doc = d / "document.md"
        if not doc.exists():
            continue
        empty = (not pj.exists()) or not (json.loads(pj.read_text()).get("pressures") or [])
        txt = normalize_math(doc.read_text(errors="replace"))
        if empty and PLAIN.search(txt):
            targets.append((d.name, txt))

    report, totals = [], Counter()
    for doi, txt in targets:
        found = []
        # symbolic first (most specific)
        for m in SYMBOL.finditer(txt):
            win = txt[max(0, m.start() - 220): m.end() + 220]
            sp = SPECIES.search(win)
            fg = FIGREF.search(win)
            found.append({"kind": "symbolic", "symbol": "p_%s" % m.group(2).upper(),
                          "value": m.group(3), "unit": m.group(4),
                          "status": status_of(win), "species": sp.group(1) if sp else None,
                          "figure_hint": fg.group(1) if fg else None,
                          "evidence": " ".join(m.group(0).split())})
        # exposure products must NOT be counted as pressures
        exps = []
        for m in EXPOSURE.finditer(txt):
            win = txt[max(0, m.start() - 160): m.end() + 160]
            fg = FIGREF.search(win)
            exps.append({"kind": "exposure", "value": (m.group(1) or m.group(3)),
                         "unit": (m.group(2) or m.group(4)) + "*s",
                         "status": status_of(win),
                         "figure_hint": fg.group(1) if fg else None,
                         "evidence": " ".join(m.group(0).split())})
        exp_spans = {(m.start(), m.end()) for m in EXPOSURE.finditer(txt)}
        for m in PLAIN.finditer(txt):
            if any(a <= m.start() < b for a, b in exp_spans):
                continue                       # part of an exposure product
            win = txt[max(0, m.start() - 220): m.end() + 220]
            if not re.search(r"pressure|\bp\s*[_ ]?[AB]\b|vacuum|base|chamber|process|working",
                             win, re.I):
                continue                       # a bare unit with no pressure context
            fg = FIGREF.search(win)
            kind = "base" if re.search(r"base pressure", win, re.I) else "process"
            found.append({"kind": kind, "symbol": None, "value": m.group(1),
                          "unit": m.group(2), "status": status_of(win),
                          "species": None, "figure_hint": fg.group(1) if fg else None,
                          "evidence": " ".join(win[max(0, m.start() - (m.start() - 60)):].split())[:150]})
        resolvable = [f for f in found if f["value"] and f["unit"]]
        ambiguous = [f for f in found
                     if f["kind"] == "process" and not f["figure_hint"] and f["status"] == "direct"]
        report.append({
            "paper_id": doi,
            "n_pressure_mentions": len(found),
            "n_exposure_mentions_correctly_separated": len(exps),
            "deterministically_resolvable": len(resolvable),
            "symbolic_forms": [f for f in found if f["kind"] == "symbolic"],
            "needs_disambiguation": len(ambiguous),
            "by_status": dict(Counter(f["status"] for f in found)),
            "by_kind": dict(Counter(f["kind"] for f in found)),
            "sample_mentions": found[:6],
            "exposures": exps[:4],
        })
        totals["papers"] += 1
        totals["mentions"] += len(found)
        totals["resolvable"] += len(resolvable)
        totals["exposures"] += len(exps)
        totals["ambiguous"] += len(ambiguous)
        totals["symbolic"] += sum(1 for f in found if f["kind"] == "symbolic")

    (OUT / "pressure_recovery_feasibility.json").write_text(json.dumps(
        {"papers_examined": len(targets), "totals": dict(totals),
         "conclusion": ("deterministic parsing resolves value+unit for %d/%d mentions; "
                        "%d mentions remain ambiguous (no figure anchor, no status cue) "
                        "and are the only candidates for LLM review"
                        % (totals["resolvable"], totals["mentions"], totals["ambiguous"])),
         "papers": report}, indent=1, ensure_ascii=False))
    print("papers with text pressure + empty pressure.json: %d" % len(targets))
    print("  total pressure mentions found deterministically : %d" % totals["mentions"])
    print("  value+unit resolvable deterministically         : %d" % totals["resolvable"])
    print("  symbolic p_A / p_A0 / p_B forms                 : %d" % totals["symbolic"])
    print("  exposure products correctly separated out       : %d" % totals["exposures"])
    print("  residual ambiguous (candidates for LLM)         : %d" % totals["ambiguous"])
    print()
    for r in report:
        print("  %-34s mentions=%-3d resolvable=%-3d symbolic=%-2d exposure=%-2d ambiguous=%-2d %s"
              % (r["paper_id"], r["n_pressure_mentions"], r["deterministically_resolvable"],
                 len(r["symbolic_forms"]), r["n_exposure_mentions_correctly_separated"],
                 r["needs_disambiguation"], r["by_status"]))


if __name__ == "__main__":
    main()
