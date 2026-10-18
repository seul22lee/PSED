"""P102/P103 calibration of the evaluation tool, no model call: (1) the kind check (eval/kind_phrases.yaml) on 30 synthetic sentences
(15 correct, 15 wrong, several citing two ids) built on records of the probe battery, precision and recall of the mismatch flag;
(2) the number check on the battery-only test: every battery line that carries numbers, cited by its own id as the given text, in
its own notation (set A) and with exponents rewritten as superscripts (set B); the match rate under the current parser (v6) and,
with --old PATH (a copy of the previous ask.py), under the previous one (v5). Writes the markdown given as --out."""
import argparse, collections, importlib.util, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ask, check, lists as L, query as Q, tools   # noqa: E402

SUPER = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
WORDING = {                                                                     # one wording per kind, taken from the phrase table's intent
    "measured": "was measured by XPS",
    "stated": "is stated in the paper",
    "read_from_figure": "was read from Fig. 3",
    "computed_by_authors": "was computed by the authors",
    "computed_by_kb": "was computed by this knowledge base",
    "simulated": "is a simulated value",
    "model_input": "is a model input",
    "cited": "is cited from another work",
    "assumed": "was assumed",
}
WRONG_FOR = {"measured": "computed_by_kb", "stated": "read_from_figure", "read_from_figure": "measured", "computed_by_authors": "computed_by_kb",
             "computed_by_kb": "computed_by_authors", "simulated": "measured", "model_input": "measured", "cited": "measured", "assumed": "measured"}


def battery_outputs():
    probes, _ = check.tool_probes()
    out = []
    for name, args in probes:
        lines, e = tools.run_tool(name, args)
        joined = []
        for i, t in lines:
            if t.startswith("… ") and joined:
                joined[-1] = (joined[-1][0], joined[-1][1] + " " + t[2:])
            else:
                joined.append((i, t))
        out.append((name, args, joined))
    return out


def records_by_kind():
    """{kind: [(id, text)]} of the facts with a stored kind and a statement, one per paper first."""
    by = collections.defaultdict(list)
    for k, T in Q.TREES.items():
        for f in T.rows:
            if "#" in f["fact_id"] and f.get("data_kind") and f["type"] in Q.RESULT_TYPES + ("cited",) and f["statement"]:
                by[f["data_kind"]].append((f["fact_id"], f["statement"]))
    return by


def synthetic():
    """30 sentences: for each kind with records, a correct and a wrong single-id sentence; then two-id sentences (one right, one wrong)
    until 30; returns [(answer text, given, {id: expected mismatch?})]."""
    by = records_by_kind()
    kinds = [k for k in WORDING if by.get(k)]
    out = []
    for k in kinds:
        i, t = by[k][0]
        out.append((f"The value {WORDING[k]} [{i}].", {i: t}, {i: False}))
        out.append((f"The value {WORDING[WRONG_FOR[k]]} [{i}].", {i: t}, {i: True}))
    j = 1
    while len(out) < 30:
        k1, k2 = kinds[j % len(kinds)], kinds[(j + 1) % len(kinds)]
        i1, t1 = by[k1][min(j, len(by[k1]) - 1)]; i2, t2 = by[k2][min(j, len(by[k2]) - 1)]
        out.append((f"The first value {WORDING[k1]} [{i1}], while the second {WORDING[WRONG_FOR[k2]]} [{i2}].", {i1: t1, i2: t2}, {i1: False, i2: True}))
        j += 1
    return out[:30]


def kind_calibration(outs):
    rows = synthetic()
    tp = fp = fn = tn = 0
    detail = []
    for text, given, expect in rows:
        kc = ask.kind_check(text, given)
        flagged = {r["id"] for r in kc["per_id"]}
        for i, exp in expect.items():
            got = i in flagged
            tp += got and exp; fp += got and not exp; fn += exp and not got; tn += (not got) and (not exp)
            detail.append((text[:110], i, "wrong" if exp else "right", "flagged" if got else "passed"))
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    n_batt, n_checked, n_mis = 0, 0, 0
    mis = collections.Counter()
    for name, args, lines in outs:                                               # the battery's value lines, each cited by its id alone: the table must read the tools' kind phrase as the record's kind
        for i, t in lines:
            if i in ("between", "concept") or ":" not in str(i) or "kind" not in t or t.startswith("claim"):
                continue
            own = ask.MARK.sub(" ", t.split(" · statement: ")[0])                  # other ids and the paper's own wording out
            kc = ask.kind_check(f"{own} [{i}]", {i: t})
            n_batt += 1; n_checked += kc["checked"]; n_mis += kc["mismatches"]
            for r in kc["per_id"]:
                mis[(", ".join(r["stated"]), ", ".join(r["record"]))] += 1
    return dict(battery_by_pair=mis, n=len(rows), ids=tp + fp + fn + tn, tp=tp, fp=fp, fn=fn, tn=tn, precision=prec, recall=rec, detail=detail, battery_lines=n_batt, battery_checked=n_checked, battery_mismatches=n_mis)


def load_old(path):
    spec = importlib.util.spec_from_file_location("ask_old", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def superscript(t):
    t = re.sub(r"(\d)e(-?\d+)\b", lambda m: f"{m.group(1)}×10^{m.group(2)}", t)
    return re.sub(r"\^(-?\d+)", lambda m: m.group(1).translate(SUPER), t)


def number_test(outs, old=None):
    sets = {"A (as printed)": [], "B (exponents as superscripts)": []}
    for name, args, lines in outs:
        for i, t in lines:
            if ":" not in str(i) or i in ("between", "concept") or not ask.nums(t, skip=True):
                continue
            sets["A (as printed)"].append((f"{t} [{i}]", {i: t}))
            if re.search(r"\^-?\d|\de-?\d", t):
                sets["B (exponents as superscripts)"].append((f"{superscript(t)} [{i}]", {i: t}))
    res = {}
    for label, rows in sets.items():
        for ver, mod in (("v6", ask),) + ((("v5", old),) if old else ()):
            n = m = d = 0
            for text, given in rows:
                nc = mod.number_check(text, "kb", given)
                n += nc["numbers"]; m += nc["match"]; d += nc.get("derived", 0)
            res[(label, ver)] = (len(rows), n, m, d)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", help="path to the previous ask.py (v5) for the before/after of the number check")
    ap.add_argument("--out", default=str(HERE.parent / "verify" / "d8" / "kind_check_calibration.md"))
    a = ap.parse_args()
    outs = battery_outputs()
    kc = kind_calibration(outs)
    nt = number_test(outs, load_old(a.old) if a.old else None)
    md = ["# Kind-check and number-check calibration (P102, P103)", "",
          f"Kind check: {kc['n']} synthetic sentences, {kc['ids']} cited ids ({kc['tp'] + kc['fn']} wrong kinds, {kc['fp'] + kc['tn']} right); "
          f"mismatch flag: TP {kc['tp']}, FP {kc['fp']}, FN {kc['fn']}, TN {kc['tn']}; precision {kc['precision']:.2f}, recall {kc['recall']:.2f}.",
          f"Battery value lines carrying a kind phrase, each cited by its own id (other ids and the paper's statement removed): {kc['battery_lines']} lines, {kc['battery_checked']} citations checked, {kc['battery_mismatches']} mismatches"
          + (" (stated -> record: " + "; ".join(f"{a} -> {b}: {n}" for (a, b), n in kc["battery_by_pair"].most_common()) + ")" if kc["battery_mismatches"] else "") + ".", "",
          "| sentence | id | kind | result |", "|---|---|---|---|"] + [f"| {t} | {i} | {k} | {r} |" for t, i, k, r in kc["detail"]] + ["",
          "Number check, battery-only test (every battery line with numbers, cited by its own id as the given text):", "",
          "| set | parser | lines | numbers | match | derived | match rate |", "|---|---|---|---|---|---|---|"]
    for (label, ver), (ln, n, m, d) in sorted(nt.items()):
        md.append(f"| {label} | {ver} | {ln} | {n} | {m} | {d} | {100 * m / n if n else 0:.1f} % |")
    Path(a.out).write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:4])); print("\n".join(md[-(len(nt) + 2):]))


if __name__ == "__main__":
    main()
