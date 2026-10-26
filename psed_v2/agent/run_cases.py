#!/usr/bin/env python3
"""Run the three Sec. 3.3.1 queries through the agent and report on the logs.

    python3 -m psed_v2.agent.run_cases [--cases case1 case2 case3] [--repeat 3] [--model P:M] [--plan] [--yes]  # -> agent/runs/<case>_<ts>.json
    python3 -m psed_v2.agent.run_cases --report [LOG ...]       # -> agent/runs/REPORT.md (default: the logs of origin run_cases)

Before any call it prints the planned conversations, the most model requests they can make and an estimated cost, and asks y/n
(--yes skips the question, --plan stops after the plan). The report reads the logs; per case and run: the tool calls in order,
the case's listing (case 1: samples with method and structure, papers, images, images not tied to one sample; case 2: samples
with every matched condition, whether pulse and purge times were filtered; case 3: the values by how they were obtained, the
filled species, the citation traces), the deviations from the expected path, the final answer, every number of the answer checked
against the text the model received from the tools (exact, rounded, or not found) and the counts the figure shows. Each run's
sets are compared with the expected path run deterministically now (the tools on its expected arguments); per case, what differs
between runs.
"""
import argparse, collections, json, math, re
from pathlib import Path

from . import agent as A
from . import tools as T

CASES = {
    "case1": "Are there SEM images showing how far a coating reaches into a high-aspect-ratio structure?",
    "case2": "With TMA/H\u2082O at 300 \u00b0C in 500 nm channels, how does penetration change with cycle number?",
    "case3": "What sticking coefficient should the twin use for TMA at 300 \u00b0C?",
}
EST_REQUESTS = 7                   # requests of a typical conversation (plan estimate)
EST_INPUT = 30_000                 # input tokens per request (plan estimate), 85 % assumed served from the prompt cache
EST_OUTPUT = 3_000                 # output tokens per request, thinking included (plan estimate)

# the directive's expected arguments, run on the tools for the reference of each case (no counts pinned)
REF_METHODS = ["sem", "sem_eds", "tem", "tem_eds", "epma"]
REF_CASE1 = [{"concept": "method", "value": REF_METHODS}, {"concept": "structure", "value": ["har_feature", "porous_body"]}]
REF_CASE2 = [{"concept": "reactant_A", "value": "tma"}, {"concept": "reactant_B", "value": "h2o"},
             {"concept": "deposition_temperature", "value": 300, "unit": "°C"}, {"concept": "structure", "value": "lateral_channel"},
             {"concept": "feature_width", "value": 500, "unit": "nm"}]


# ------------------------------------------------------------------------------------------------------------ expected paths
def _calls(turn):
    return [s for s in turn["steps"] if s["type"] == "tool_result"]


def _ok(calls, name):
    return [c for c in calls if c["name"] == name and not (c.get("result") or {}).get("error")]


def _terms(calls):
    return [str(c["input"].get("term", "")).lower() for c in calls if c["name"] == "resolve"]


def _filters(c):
    return {f.get("concept"): f for f in c["input"].get("filters", []) if isinstance(f, dict)}


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


# ------------------------------------------------------------------------------------------------------------ listings
def _v(s):
    """The value part of an evidence string 'value [fact_id] (where from)'."""
    if isinstance(s, list):
        return " | ".join(_v(x) for x in s)
    return str(s).split(" [")[0] if s else ""


def _cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def _matched(sample, concept):
    return next((ev for k, ev in sample.get("matched", {}).items() if k.startswith(concept)), "")


def figure_counts(calls):
    """Counts the figure shows, from the logged tool results (not from the answer)."""
    samples, papers, images, values, curves = set(), set(), set(), set(), set()
    for c in _ok(calls, "find_samples"):
        for s in c["result"].get("samples", []):
            samples.add(s["id"])
            papers.add(s["paper"])
    for c in _ok(calls, "get_records"):
        r = c["result"]
        values |= {v["fact_id"] for v in r.get("values", [])}
        images |= {i["image_id"] for i in r.get("images", [])}
        curves |= {x["curve_id"] for x in r.get("curves", [])}
    return {"samples": len(samples), "papers": len(papers), "images": len(images), "values": len(values), "curves": len(curves)}


def run_sets(calls):
    """The sets a run reached: samples, images, values, cited fact ids traced."""
    return {"samples": {s["id"] for c in _ok(calls, "find_samples") for s in c["result"].get("samples", [])},
            "images": {i["image_id"] for c in _ok(calls, "get_records") for i in c["result"].get("images", [])},
            "values": {v["fact_id"] for c in _ok(calls, "get_records") for v in c["result"].get("values", [])},
            "traced": {c["input"].get("fact_id") for c in calls if c["name"] == "trace_citation"}}


def reference(case):
    """The expected path run on the tools now: the sets a run following the directive's arguments reaches."""
    if case == "case1":
        r = T.find_samples(REF_CASE1)
        ids = [s["id"] for s in r["samples"]]
        g = T.get_records(ids, include=["images"])
        return {"samples": set(ids), "papers": {s["paper"] for s in r["samples"]}, "images": {i["image_id"] for i in g["images"]},
                "not_tied": {i["image_id"] for i in g["images"] if i["binding"] == "ambiguous"}}
    if case == "case2":
        r = T.find_samples(REF_CASE2, vary=["cycle_number"])
        return {"samples": {s["id"] for s in r["samples"]}, "papers": {s["paper"] for s in r["samples"]}}
    if case == "case3":
        g = T.get_records(None, "initial_sticking_coefficient", {"species": "tma"})
        return {"own": {v["fact_id"] for v in g["values"] if v["group"] == "own"}, "values": {v["fact_id"] for v in g["values"]}}
    return {}


def vs_reference(name, got, ref):
    miss, extra = sorted(ref - got), sorted(got - ref)
    s = f"- {name}: {len(got)} in the run, {len(ref)} in the reference"
    s += "; same set" if not miss and not extra else ""
    s += f"; not reached: {', '.join(miss)}" if miss else ""
    s += f"; beyond the reference: {', '.join(extra)}" if extra else ""
    return s


def listing_case1(calls, ref):
    out = []
    for c in _ok(calls, "find_samples"):
        r = c["result"]
        out += [f"find_samples call #{c['call']}: filters {'; '.join(r['filters'])}; {r['counts']['matched']} samples in "
                f"{r['counts']['papers_matched']} papers ({r['counts']['scanned']} scanned)", "",
                "| sample id | paper | label | method (measurement) | structure |", "|---|---|---|---|---|"]
        for s in r["samples"]:
            out.append(f"| {s['id']} | {s['paper']} | {_cell(s['label'])} | {_cell(_v(_matched(s, 'method')))} | "
                       f"{_cell(_v(_matched(s, 'structure')))} |")
        out += ["", f"Papers: {', '.join(sorted({s['paper'] for s in r['samples']}))}", ""]
    imgs = {i["image_id"]: i for c in _ok(calls, "get_records") for i in c["result"].get("images", [])}
    if imgs:
        out += [f"Images ({len(imgs)}):", "", "| image | paper | method | sample | tied to one sample |", "|---|---|---|---|---|"]
        for i in imgs.values():
            who = i.get("sample_id") or ", ".join(x.get("sample_id") or x["unit_id"] for x in i.get("candidates", []))
            meth = ", ".join(i["method"]) or ("not recorded; candidates measured by " + ", ".join(i.get("candidate_methods", [])))
            out.append(f"| {i['image_id']} | {i['paper']} | {_cell(meth)} | {_cell(who)} | {'yes' if i['binding'] == 'bound' else 'no'} |")
        nt = [i for i in imgs.values() if i["binding"] != "bound"]
        out += ["", f"Images not tied to one sample ({len(nt)}): " + "; ".join(f"{i['image_id']} ({i.get('note', '')})" for i in nt), ""]
    sets = run_sets(calls)
    out += ["Against the expected path:", vs_reference("samples", sets["samples"], ref["samples"]),
            vs_reference("papers", {s["paper"] for c in _ok(calls, "find_samples") for s in c["result"]["samples"]}, ref["papers"]),
            vs_reference("images", sets["images"], ref["images"]),
            vs_reference("images not tied to one sample", {k for k, i in imgs.items() if i["binding"] != "bound"}, ref["not_tied"]), ""]
    return out


def listing_case2(calls, ref):
    out = []
    for c in _ok(calls, "find_samples"):
        r, fs = c["result"], _filters(c)
        out += [f"find_samples call #{c['call']}: filters {'; '.join(r['filters'])}; free {', '.join(r['vary']) or 'none'}; "
                f"{r['counts']['matched']} samples in {r['counts']['papers_matched']} papers",
                f"pulse_time filtered: {'yes (' + json.dumps(fs['pulse_time'], ensure_ascii=False) + ')' if 'pulse_time' in fs else 'no'}; "
                f"purge_time filtered: {'yes (' + json.dumps(fs['purge_time'], ensure_ascii=False) + ')' if 'purge_time' in fs else 'no'}", ""]
        keys = list(r["samples"][0]["matched"]) if r["samples"] else []
        out += ["| sample id | paper | label | " + " | ".join(_cell(k) for k in keys) + " | free | conflicts |",
                "|" + "---|" * (len(keys) + 5)]
        for s in r["samples"]:
            out.append(f"| {s['id']} | {s['paper']} | {_cell(s['label'])} | " + " | ".join(_cell(s["matched"].get(k, "")) for k in keys)
                       + f" | {_cell(json.dumps(s.get('vary', {}), ensure_ascii=False))} | {_cell('; '.join(s.get('conflicts', [])))} |")
        out.append("")
        und = r.get("undecided", [])
        if und:
            out += [f"Undecided ({r['counts']['undecided']}, first {min(len(und), 8)} listed): " +
                    "; ".join(f"{u['id']} ({'; '.join(f'{k}: {v}' for k, v in u['open'].items())})" for u in und[:8]), ""]
    sets = run_sets(calls)
    out += ["Against the expected path:", vs_reference("samples", sets["samples"], ref["samples"]),
            vs_reference("papers", {s["paper"] for c in _ok(calls, "find_samples") for s in c["result"]["samples"]}, ref["papers"]), ""]
    return out


def listing_case3(calls, ref):
    out = []
    order = {"measured": 0, "stated": 1, "read_from_figure": 2, "computed_by_authors": 3, "computed_by_kb": 4, "cited": 5, "model_input": 6, "simulated": 7}
    for c in _ok(calls, "get_records"):
        r = c["result"]
        if r.get("quantity") != "initial_sticking_coefficient":
            continue
        vals = sorted(r["values"], key=lambda v: (order.get(v["data_kind"], 9), v["paper"], v["fact_id"]))
        out += [f"get_records call #{c['call']}: {json.dumps(c['input'], ensure_ascii=False)}; {r['counts']['values']} values "
                f"({', '.join(f'{k} {n}' for k, n in r['counts']['by_data_kind'].items())}), {r['counts']['excluded']} excluded", "",
                "| how obtained | fact id | paper | value | species | filled species | temperature |", "|---|---|---|---|---|---|---|"]
        for v in vals:
            val = v.get("value") if v.get("value") is not None else f"{v.get('value_min', '')}–{v.get('value_max', '')}"
            out.append(f"| {v['data_kind']} | {v['fact_id']} | {v['paper']} | {val} | {_cell(v['qualifiers'])} | "
                       f"{_cell(v.get('species_filled', ''))} | {_cell(_v(v.get('key_conditions', {}).get('deposition_temperature', '')))} |")
        why = collections.Counter(x["reason"] for x in r.get("excluded", []))
        out += ["", "Excluded: " + "; ".join(f"{k} ({n})" for k, n in why.most_common()), ""]
        mat = [x["fact_id"] for x in r.get("excluded", []) if "material" in x["reason"]]
        if mat:
            out += [f"Excluded for a film species: {', '.join(mat)}", ""]
    for c in calls:
        if c["name"] != "trace_citation":
            continue
        t = c.get("result") or {}
        if t.get("error"):
            out.append(f"- trace_citation #{c['call']} {c['input'].get('fact_id')}: ERROR {t['error']}")
            continue
        cv = t["cited"]
        val = cv.get("value") if cv.get("value") is not None else f"{cv.get('value_min', '')}–{cv.get('value_max', '')}"
        line = f"trace_citation #{c['call']} {cv['fact_id']} (cited {val}, {cv['qualifiers']}): {t['outcome']}"
        if t.get("cited_paper"):
            line += f"; cited paper {', '.join(p['paper'] for p in t['cited_paper'])}"
            for o in t["own_values"]:
                line += (f"; own {o['fact_id']} = {o.get('value')} ({o['data_kind']}"
                         f"{', species filled: ' + o['species_filled'] if o.get('species_filled') else ''}): {o['value_comparison']}")
        out.append("- " + line)
    sets = run_sets(calls)
    out += ["", "Against the expected path:", vs_reference("values of TMA (all kinds)", sets["values"], ref["values"]),
            vs_reference("own values of TMA", sets["values"] & ref["values"] & ref["own"], ref["own"]), ""]
    return out


LISTINGS = {"case1": listing_case1, "case2": listing_case2, "case3": listing_case3}


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


# ------------------------------------------------------------------------------------------------------------ the report
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
           "received from the tools (`sent`); 'rounded' = equal at the precision the answer prints; 'not found' = in no tool result. "
           "'The reference' is the expected path run on the tools at report time (the directive's arguments).", ""]
    for case, ds in sorted(by_case.items()):
        ref = reference(case)
        out += [f"## {case}: {ds[0]['turns'][0]['user'] if ds[0]['turns'] else ''}", ""]
        runs = []
        for d in sorted(ds, key=lambda x: x["_path"]):
            if not d["turns"]:
                continue
            t = d["turns"][0]
            calls = _calls(t)
            ans = t["final_answer"]
            nums = check_numbers(ans, [c["sent"] for c in calls])
            u = d.get("usage_total", {})
            runs.append({"name": d["_path"], "path": [c["name"] for c in calls], "nums": nums, "sets": run_sets(calls),
                         "cites": set(re.findall(r"[a-z]+\d\d:[^\s\],;]+", ans)), "counts": figure_counts(calls)})
            cost = f"${d['cost_usd_estimate']:.4f}" if d.get("price_per_mtok") else "no price"
            out += [f"### {d['_path']}", "",
                    f"{d.get('provider', 'anthropic')}:{d['model']} (effort {d['effort']}), {t['requests']} requests, {t['tool_calls']} tool calls, "
                    f"stop {t['stop']}, cap reached {t['cap_reached']}; tokens: input {u.get('input_tokens', 0)}, cached input "
                    f"{u.get('cache_read_input_tokens', 0)}, output {u.get('output_tokens', 0)} (reasoning {u.get('reasoning_tokens', 0)}); "
                    f"estimated {cost}; recipe source {d.get('recipe_source')}", ""]
            plan = next((s["text"] for s in t["steps"] if s["type"] == "assistant" and s["text"]), "")
            if plan and plan != ans:
                out += [f"Plan (first assistant text): {plan.strip()}", ""]
            out += ["| # | tool | arguments | key result |", "|---|---|---|---|"]
            for c in calls:
                out.append(f"| {c['call']} | {c['name']} | `{_cell(json.dumps(c['input'], ensure_ascii=False))}` | {_cell(key_result(c))} |")
            out.append("")
            if case in LISTINGS:
                out += LISTINGS[case](calls, ref)
            exp = EXPECTED.get(case)
            if exp:
                dev = [name for name, ok in exp(calls) if not ok]
                out += ["Deviations from the expected path: " + ("; ".join(dev) if dev else "none")]
            for name, v in EXPECTED_VALUES.get(case, []):
                hit = any(math.isclose(n["value"], v, rel_tol=1e-9) for n in nums)
                out.append(f"Expected value {name}: {'in the answer' if hit else 'NOT in the answer'}")
            bad = [n["number"] for n in nums if n["found"] == "not found"]
            rnd = [n["number"] for n in nums if n["found"] == "rounded"]
            out += [f"Number check: {len(nums)} numbers in the answer; exact {sum(n['found'] == 'exact' for n in nums)}; "
                    f"rounded {len(rnd)}{': ' + ', '.join(rnd) if rnd else ''}; not found in any tool result {len(bad)}"
                    f"{': ' + ', '.join(bad) if bad else ''}",
                    f"Figure counts (from the logged tool results): {json.dumps(figure_counts(calls))}", "", "Final answer:", "",
                    *["> " + line for line in ans.strip().splitlines()], ""]
        out += [f"### Differences between the {len(runs)} runs", ""]
        if runs:
            paths_ = {tuple(r["path"]) for r in runs}
            out.append(f"- tool path identical: {len(paths_) == 1}")
            for r in runs:
                out.append(f"  - {r['name']}: {' > '.join(r['path'])}")
            for key in ("samples", "images", "values", "traced"):
                allv = set().union(*(r["sets"][key] for r in runs))
                common = set.intersection(*(r["sets"][key] for r in runs))
                if allv:
                    out.append(f"- {key}: {len(common)} in every run" + ("" if allv == common else "; only in some runs: " +
                               "; ".join(f"{r['name']}: {', '.join(sorted(r['sets'][key] - common)) or '-'}" for r in runs)))
            numsets = [{round(n["value"], 12) for n in r["nums"]} for r in runs]
            common = set.intersection(*numsets)
            out.append(f"- numbers in the answer: {len(common)} in every run" + ("" if all(s == common for s in numsets) else
                       "; only in some runs: " + "; ".join(f"{r['name']}: {', '.join(f'{x:g}' for x in sorted(s - common)) or '-'}"
                                                           for r, s in zip(runs, numsets))))
            cites = [r["cites"] for r in runs]
            cc = set.intersection(*cites)
            out.append(f"- cited fact ids: {len(cc)} in every run" + ("" if all(c == cc for c in cites) else "; only in some runs: " +
                       "; ".join(f"{r['name']}: {', '.join(sorted(c - cc)) or '-'}" for r, c in zip(runs, cites))))
            out.append("- figure counts: " + "; ".join(f"{r['name']}: {json.dumps(r['counts'])}" for r in runs))
        out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="*")
    ap.add_argument("--cases", nargs="+", default=list(CASES), choices=list(CASES))
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--model", help="provider:model (default PSED_MODEL)")
    ap.add_argument("--effort")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        paths = a.logs or sorted(str(p) for p in A.RUNS.glob("case*_*.json")
                                 if json.loads(p.read_text(encoding="utf-8")).get("origin") == "run_cases")
        text = report(paths)
        (A.RUNS / "REPORT.md").write_text(text + "\n", encoding="utf-8")
        print(text)
        print(f"\n-> {A.RUNS / 'REPORT.md'}")
        return
    A.load_env()
    provider, model = A.resolve_model(a.model)
    n = len(a.cases) * a.repeat
    worst = n * (A.MAX_TOOL_CALLS + A.EXTRA_REQUESTS + 1)
    p = A.PRICES.get(model)
    print(f"plan: {n} conversations ({', '.join(a.cases)} x {a.repeat}), {provider}:{model}, effort {a.effort or A.EFFORT[provider]}, "
          f"recipe source {T.RECIPE_SOURCE}")
    print(f"      model requests: about {n * EST_REQUESTS} expected, at most {worst} (cap {A.MAX_TOOL_CALLS} tool calls per question)")
    if p:
        est = n * EST_REQUESTS * (EST_INPUT * (0.85 * p["cache_read"] + 0.15 * p["input"]) + EST_OUTPUT * p["output"]) / 1e6
        print(f"      estimated cost: about ${est:.2f} (typical); the logs record the actual usage")
    else:
        print("      estimated cost: no price for this model in agent.PRICES; the logs record the token usage")
    if a.plan:
        return
    if not a.yes and input("run? [y/N] ").strip().lower() != "y":
        return
    for r in range(a.repeat):
        for case in a.cases:
            conv = A.Conversation(case=case, mode="batch", model=a.model, effort=a.effort, origin="run_cases")
            print(f"\n=== {case} run {r + 1}: {CASES[case]}")
            conv.ask(CASES[case], lambda kind, d: print(f"  [{d['call']}] {d['name']} {d['sent_chars']} chars", flush=True)
                     if kind == "tool_result" else print(f"  {d['message']}", flush=True) if kind == "error" else None)
            t = conv.log["turns"][0]
            print(f"  -> {t['tool_calls']} tool calls, stop {t['stop']}, ${conv.log['cost_usd_estimate']:.4f}, {conv.path.name}")


if __name__ == "__main__":
    main()
