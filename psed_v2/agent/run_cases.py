#!/usr/bin/env python3
"""Run the three Sec. 3.3.1 queries through the agent and report on the logs.

    python3 -m psed_v2.agent.run_cases [--cases case1 case2 case3] [--repeat 3] [--plan] [--yes]   # runs -> agent/runs/<case>_<ts>.json
    python3 -m psed_v2.agent.run_cases --report [LOG ...]                                           # -> agent/runs/REPORT.md

Before any call it prints the planned conversations, the most model requests they can make and an estimated cost, and asks y/n
(--yes skips the question, --plan stops after the plan). The report reads only the logs: per case and run, the tool calls in order,
the key results, the final answer, the deviations from the expected path, every number of the answer checked against the text the
model received from the tools (exact, rounded, or not found), the stability of the tool path and the numbers across runs, and the
counts the figure will show (samples, papers, images, values, curves) straight from the logged tool results.
"""
import argparse, collections, json, math, re
from pathlib import Path

from . import agent as A

CASES = {
    "case1": "Are there SEM images showing how far a coating reaches into a high-aspect-ratio structure?",
    "case2": "With TMA/H₂O at 300 °C in 500 nm channels, how does penetration change with cycle number?",
    "case3": "What sticking coefficient should the twin use for TMA at 300 °C?",
}
EST_REQUESTS = 7                   # requests of a typical conversation (plan estimate)
EST_INPUT = 30_000                 # input tokens per request, mostly cache reads after the first (plan estimate)
EST_OUTPUT = 3_000                  # output tokens per request, thinking included (plan estimate)


# ------------------------------------------------------------------------------------------------------------ expected paths
def _calls(turn):
    return [s for s in turn["steps"] if s["type"] == "tool_result"]


def _terms(calls):
    return [str(c["input"].get("term", "")).lower() for c in calls if c["name"] == "resolve"]


def _filters(c):
    return {f.get("concept"): f for f in c["input"].get("filters", [])}


def _vals(f):
    v = (f or {}).get("value", [])
    return [str(x).lower() for x in (v if isinstance(v, list) else [v])]


def expected_case1(calls):
    fs = [_filters(c) for c in calls if c["name"] == "find_samples"]
    meth = {v for f in fs for v in _vals(f.get("method"))}
    struct = {v for f in fs for v in _vals(f.get("structure"))}
    imgs = [c for c in calls if c["name"] == "get_records" and "images" in (c["input"].get("include") or ["images"])]
    return [("resolve SEM", any("sem" in t for t in _terms(calls))),
            ("resolve high aspect ratio", any("aspect" in t or "har" in t.split() for t in _terms(calls))),
            ("find_samples method filter has sem, sem_eds", {"sem", "sem_eds"} <= meth),
            ("find_samples method filter has tem, tem_eds, epma", {"tem", "tem_eds", "epma"} <= meth),
            ("find_samples structure filter has har_feature (or its subclasses)", bool(struct & {"har_feature", "lateral_channel", "trench", "via_hole"})),
            ("find_samples structure filter has porous_body", "porous_body" in struct),
            ("get_records with images", bool(imgs))]


def expected_case2(calls):
    fs = [_filters(c) for c in calls if c["name"] == "find_samples"]
    vary = {v for c in calls if c["name"] == "find_samples" for v in (c["input"].get("vary") or [])}
    gr = [c["input"] for c in calls if c["name"] == "get_records"]
    cl = [c["input"] for c in calls if c["name"] == "claims"]
    has = lambda concept, want: any(want in _vals(f.get(concept)) for f in fs)
    num = lambda concept, want: any(str(want) in _vals(f.get(concept)) or str(float(want)) in _vals(f.get(concept)) for f in fs)
    return [("find_samples reactant_A = tma", has("reactant_A", "tma")), ("find_samples reactant_B = h2o", has("reactant_B", "h2o")),
            ("find_samples deposition_temperature = 300", num("deposition_temperature", 300)),
            ("find_samples structure lateral_channel", any(_vals(f.get("structure")) for f in fs)),
            ("find_samples feature_width = 500", num("feature_width", 500)),
            ("cycle_number left free (vary)", "cycle_number" in vary),
            ("get_records penetration_depth with level=50%", any(g.get("quantity") == "penetration_depth" and
                                                                (g.get("qualifiers") or {}).get("level") == "50%" for g in gr)),
            ("compare", any(c["name"] == "compare" for c in calls)),
            ("claims on cycle_number", any("cycle_number" in json.dumps(x) for x in cl))]


def expected_case3(calls):
    gr = [c["input"] for c in calls if c["name"] == "get_records"]
    return [("resolve sticking coefficient", any("stick" in t for t in _terms(calls))),
            ("get_records initial_sticking_coefficient", any(g.get("quantity") == "initial_sticking_coefficient" for g in gr)),
            ("get_records species = tma", any((g.get("qualifiers") or {}).get("species") == "tma" for g in gr)),
            ("trace_citation", any(c["name"] == "trace_citation" for c in calls))]


EXPECTED = {"case1": expected_case1, "case2": expected_case2, "case3": expected_case3}
EXPECTED_VALUES = {"case3": [("Ylilammi 2018 0.00572", 0.00572), ("Yim 2020 4e-3", 0.004)]}


# ------------------------------------------------------------------------------------------------------------ numbers
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺−", "0123456789--" + "-")
NUM = re.compile(r"(?<![\w.^])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:\s*(?:×|x|\*)\s*10\^(-?\d+)|[eE]([-+]?\d+)|\^(-?\d+))?(?![\w])")


def numbers(text):
    """(value, precision, as written) of every number in a text; '4 × 10⁻³', '4e-3', '1,109' are one number each."""
    t = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+", lambda m: "^" + m.group().translate(SUP), str(text))
    t = re.sub(r"\^\{\s*([-−]?\d+)\s*\}", r"^\1", t).replace("−", "-").replace("\\times", "×")
    out = []
    for m in NUM.finditer(t):
        mant, e1, e2, power = m.group(1).replace(",", ""), m.group(2), m.group(3), m.group(4)
        if power is not None:                                                      # 10^-3 standing alone
            out.append((float(mant) ** int(power), 0.0, m.group(0)))
            continue
        exp = int(e1 or e2 or 0)
        dec = len(mant.split(".")[1]) if "." in mant else 0
        out.append((float(mant) * 10 ** exp, 0.5 * 10 ** (exp - dec), m.group(0)))
    return out


def check_numbers(answer, sent_texts):
    """Every number of the answer (citations in [...] removed) against the numbers of the text the model received."""
    pool = [v for s in sent_texts for v, _, _ in numbers(s)]
    rows = []
    for v, prec, raw in numbers(re.sub(r"\[[^\]]*\]", " ", answer)):
        if any(math.isclose(v, p, rel_tol=1e-9, abs_tol=1e-15) for p in pool):
            how = "exact"
        elif any(abs(v - p) <= prec * (1 + 1e-9) for p in pool):
            how = "rounded"
        else:
            how = "not found"
        rows.append({"number": raw.strip(), "value": v, "found": how})
    return rows


# ------------------------------------------------------------------------------------------------------------ the report
def figure_counts(calls):
    """Counts the figure shows, from the logged tool results (not from the answer)."""
    samples, papers, images, values, curves = set(), set(), set(), set(), set()
    for c in calls:
        r = c.get("result") or {}
        if c["name"] == "find_samples":
            for s in r.get("samples", []):
                samples.add(s["id"])
                papers.add(s["paper"])
        if c["name"] == "get_records":
            values |= {v["fact_id"] for v in r.get("values", [])}
            images |= {i["image_id"] for i in r.get("images", [])}
            curves |= {x["curve_id"] for x in r.get("curves", [])}
            papers |= {v["paper"] for v in r.get("values", [])}
    return {"samples": len(samples), "papers": len(papers), "images": len(images), "values": len(values), "curves": len(curves)}


def key_result(c):
    r = c.get("result") or {}
    if r.get("error"):
        return f"ERROR {r['error']}"
    n = c["name"]
    if n == "resolve":
        return ", ".join(m["id"] for m in r.get("matches", [])[:6])
    if n == "find_samples":
        k = r["counts"]
        return f"{k['matched']} samples in {k['papers_matched']} papers ({k['scanned']} scanned, {k['undecided']} undecided)"
    if n == "get_records":
        k = r["counts"]
        return (f"{k['values']} values ({', '.join(f'{a} {b}' for a, b in k['by_data_kind'].items())}), "
                f"{k.get('curves', 0)} curves, {k.get('images', 0)} images, {k['excluded']} excluded, {k['rejected']} rejected")
    if n == "compare":
        k = r["counts"]
        return f"{k['same']} same, {k['different']} different, {k['partly_recorded']} partly recorded, {k['comparison_sets']} comparison sets"
    if n == "claims":
        return f"{r['n_claims']} claims ({', '.join(c['fact_id'] for c in r['claims'][:5])})"
    if n == "trace_citation":
        return r.get("outcome", "")
    return ""


def report(paths):
    logs = []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        d["_path"] = Path(p).name
        logs.append(d)
    by_case = collections.defaultdict(list)
    for d in logs:
        by_case[d.get("case") or "chat"].append(d)
    out = ["# Agent runs: Sec. 3.3.1 cases", "",
           "Written by `run_cases.py --report` from the logs in `agent/runs/`. Numbers are checked against the text the model "
           "received from the tools (`sent`); 'rounded' = equal at the precision the answer prints; 'not found' = in no tool result.", ""]
    for case, ds in sorted(by_case.items()):
        out += [f"## {case}: {ds[0]['turns'][0]['user'] if ds[0]['turns'] else ''}", ""]
        paths_seen, numsets, citesets = [], [], []
        for d in sorted(ds, key=lambda x: x["_path"]):
            if not d["turns"]:
                continue
            t = d["turns"][0]
            calls = _calls(t)
            seq = [c["name"] for c in calls]
            paths_seen.append(tuple(seq))
            ans = t["final_answer"]
            nums = check_numbers(ans, [c["sent"] for c in calls])
            numsets.append(tuple(sorted({round(n["value"], 12) for n in nums})))
            citesets.append(tuple(sorted(set(re.findall(r"[a-z]+\d\d:[^\s\],;]+", ans)))))
            out += [f"### {d['_path']}", "",
                    f"model {d['model']} (effort {d['effort']}), {t['requests']} requests, {t['tool_calls']} tool calls, stop {t['stop']}, "
                    f"cap reached {t['cap_reached']}, estimated ${d.get('cost_usd_estimate', 0):.4f}, recipe source {d.get('recipe_source')}", ""]
            plan = next((s["text"] for s in t["steps"] if s["type"] == "assistant" and s["text"]), "")
            if plan and plan != ans:
                out += [f"Plan (first assistant text): {plan.strip()}", ""]
            out += ["| # | tool | arguments | key result |", "|---|---|---|---|"]
            for i, c in enumerate(calls, 1):
                out.append(f"| {i} | {c['name']} | `{json.dumps(c['input'], ensure_ascii=False)}` | {key_result(c)} |")
            exp = EXPECTED.get(case)
            if exp:
                dev = [name for name, ok in exp(calls) if not ok]
                out += ["", "Deviations from the expected path: " + ("; ".join(dev) if dev else "none")]
            for name, v in EXPECTED_VALUES.get(case, []):
                hit = any(math.isclose(n["value"], v, rel_tol=1e-9) for n in nums)
                out.append(f"Expected value {name}: {'in the answer' if hit else 'NOT in the answer'}")
            bad = [n["number"] for n in nums if n["found"] == "not found"]
            rnd = [n["number"] for n in nums if n["found"] == "rounded"]
            out += [f"Numbers in the answer: {len(nums)}; not found in any tool result: {', '.join(bad) or 'none'}; "
                    f"rounded: {', '.join(rnd) or 'none'}",
                    f"Figure counts (from the logged tool results): {json.dumps(figure_counts(calls))}", "", "Final answer:", "",
                    *["> " + line for line in ans.strip().splitlines()], ""]
        n = len(paths_seen)
        out += [f"### Stability across {n} runs", "",
                f"- tool path identical: {len(set(paths_seen)) == 1}" + ("" if len(set(paths_seen)) == 1 else
                                                                          "; paths: " + " | ".join(" > ".join(p) for p in paths_seen)),
                f"- numbers in the answer identical: {len(set(numsets)) == 1}",
                f"- cited fact ids identical: {len(set(citesets)) == 1}", ""]
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="*")
    ap.add_argument("--cases", nargs="+", default=list(CASES), choices=list(CASES))
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--model", default=A.MODEL)
    ap.add_argument("--effort", default=A.EFFORT)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        paths = a.logs or sorted(str(p) for p in A.RUNS.glob("case*_*.json"))
        text = report(paths)
        (A.RUNS / "REPORT.md").write_text(text + "\n", encoding="utf-8")
        print(text)
        print(f"\n-> {A.RUNS / 'REPORT.md'}")
        return
    n = len(a.cases) * a.repeat
    worst = n * (A.MAX_TOOL_CALLS + A.EXTRA_REQUESTS + 1)
    p = A.PRICE
    est = n * EST_REQUESTS * (EST_INPUT * (0.85 * p["cache_read"] + 0.15 * p["cache_write"]) + EST_OUTPUT * p["output"]) / 1e6
    print(f"plan: {n} conversations ({', '.join(a.cases)} x {a.repeat}), model {a.model}, effort {a.effort}, recipe source {A.T.RECIPE_SOURCE}")
    print(f"      model requests: about {n * EST_REQUESTS} expected, at most {worst} (cap {A.MAX_TOOL_CALLS} tool calls per question)")
    print(f"      estimated cost: about ${est:.2f} (typical); the logs record the actual usage")
    if a.plan:
        return
    if not a.yes and input("run? [y/N] ").strip().lower() != "y":
        return
    for r in range(a.repeat):
        for case in a.cases:
            conv = A.Conversation(case=case, mode="batch", model=a.model, effort=a.effort)
            print(f"\n=== {case} run {r + 1}: {CASES[case]}")
            conv.ask(CASES[case], lambda kind, d: print(f"  [{d['call']}] {d['name']} {d['sent_chars']} chars", flush=True)
                     if kind == "tool_result" else None)
            t = conv.log["turns"][0]
            print(f"  -> {t['tool_calls']} tool calls, stop {t['stop']}, ${conv.log['cost_usd_estimate']:.4f}, {conv.path.name}")


if __name__ == "__main__":
    main()
