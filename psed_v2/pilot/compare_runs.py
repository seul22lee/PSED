"""P126: the kb-vs-text comparison report from run files (ask.py --questions ... --out RUN.jsonl), no model call, nothing read but the
paths given:

    python3 psed_v2/pilot/compare_runs.py RUN.jsonl [RUN.jsonl ...] [--verdicts verdicts.csv] [--out report.md]

Sections (each a table generated from the records): 1 runs; 2 cost and process per (run, arm); 3 number and kind checks with the
P74/P75 process columns; 4 stability (P115) where a file holds repeats; 5 the per-question table (and the verdict counts with the
Wilson 95 % interval when --verdicts is given: columns question_no, run_file, arm, run, verdict right | slips | material | fabricated |
empty, note; joined on file, arm, run and the question's order of first appearance); 6 one closing paragraph computed from the numbers.
Answer bodies are never copied; the question text is truncated to 60 characters."""
import argparse, collections, csv, json, math, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_metrics as RM  # noqa: E402

ARM_NAMES = {"model": "Model only", "text": "Paper text", "kb": "Knowledge base", "dump": "KB dump"}
VERDICTS = ["right", "slips", "material", "fabricated", "empty"]


def load(path):
    recs = []
    for line in Path(path).open(encoding="utf-8"):
        if line.strip():
            r = json.loads(line); r["_file"] = Path(path).name; recs.append(r)
    return recs


def nc(r):
    """The number check of a record with the current keys (older records had mismatch / not_in_source)."""
    n = r.get("number_check") or {}
    return dict(numbers=n.get("numbers", 0), match=n.get("match", 0), elsewhere=n.get("elsewhere", n.get("mismatch", 0)), not_seen=n.get("not_seen", n.get("not_in_source", 0)),
                derived=n.get("derived", 0), uncited=n.get("uncited", 0), unknown=n.get("unknown_ids", 0))


def kc(r):
    k = r.get("kind_check") or {}
    return k.get("mismatches", 0)


def proc(r):
    return RM.process(r.get("tool_calls") or [], list((r.get("cited") or {}).keys()))


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


def fmt(x, d=1):
    return "" if x is None else (f"{x:,.{d}f}" if isinstance(x, float) else f"{x:,}")


def table(header, rows):
    return "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n" + "\n".join("| " + " | ".join(str(c) for c in row) + " |" for row in rows) + "\n"


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def question_numbers(recs):
    """{question text: number} in order of first appearance over every file."""
    out = {}
    for r in recs:
        q = r["question"].strip()
        if q not in out:
            out[q] = len(out) + 1
    return out


def report(paths, verdicts=None):
    recs = [r for p in paths for r in load(p)]
    qno = question_numbers(recs)
    groups = collections.OrderedDict()
    for r in recs:
        groups.setdefault((r["_file"], r["arm"]), []).append(r)
    out = ["# Run comparison (P126)", "", f"Files: {', '.join(Path(p).name for p in paths)} · {len(recs)} records · {len(qno)} questions", ""]
    # 1 runs
    rows = []
    for p in paths:
        rs = load(p)
        rows.append([Path(p).name, ", ".join(sorted({r["arm"] for r in rs})), ", ".join(sorted({r["model"] for r in rs})),
                     ", ".join(sorted({f"{r.get('max_tokens', '—')}/{r.get('max_calls', '—')}" for r in rs})), ", ".join(sorted({str(r.get("preamble_sha256", "—")) for r in rs})),
                     max((r.get("run", 1) for r in rs), default=1), ", ".join(sorted({str(r.get("git_head", "unknown")) for r in rs}))])
    out += ["## 1. Runs", "", table(["file", "arms", "model", "max_tokens/max_calls", "preamble", "repeats", "git head"], rows)]
    # 2 cost and process
    stats = {}
    for key, rs in groups.items():
        ps = [proc(r) for r in rs]
        ans = [r for r in rs if (r.get("answer") or "").strip() and not r.get("error")]
        cost = sum(r.get("cost") or 0 for r in rs)
        inp = sum(r["usage"].get("input", 0) for r in rs); cr = sum(r["usage"].get("cache_read", 0) for r in rs)
        stats[key] = dict(answers=len(ans), failed=len(rs) - len(ans), calls=[p["calls"] for p in ps], tokens=[p["tool_output_tokens"] for p in ps], delivered=[p["tool_tokens_delivered"] for p in ps],
                          input=inp, cache_share=(cr / inp if inp else 0.0), output=sum(r["usage"].get("output", 0) for r in rs), cost=cost, per_answer=(cost / len(ans) if ans else None),
                          seconds=mean([r.get("seconds", 0) for r in rs]), procs=ps)
    cheapest = min((v["per_answer"] for v in stats.values() if v["per_answer"]), default=None)
    rows = []
    for (f, a), v in stats.items():
        rows.append([f, ARM_NAMES.get(a, a), v["answers"], v["failed"], f"{mean(v['calls']):.1f} ({min(v['calls'], default=0)}–{max(v['calls'], default=0)})", fmt(mean(v["tokens"]), 0), fmt(mean(v["delivered"]), 0),
                     f"{v['input']:,} ({100 * v['cache_share']:.0f} % cached)", f"{v['output']:,}", f"${v['cost']:.4f}", "" if v["per_answer"] is None else f"${v['per_answer']:.4f}", f"{v['seconds']:.1f}",
                     "" if v["per_answer"] is None or not cheapest else f"{v['per_answer'] / cheapest:.2f}×"])
    out += ["## 2. Cost and process per (run, arm)", "", table(["file", "arm", "answers", "empty/failed", "tool calls / question (mean, min–max)", "tool output tokens / question (vendor)", "delivered tokens / question (chars/4)",
                                                               "input tokens (cache-read share)", "output tokens", "cost", "cost / answer", "s / answer", "cost ratio vs cheapest"], rows)]
    # 3 checks
    rows = []
    for (f, a), rs in groups.items():
        n = [nc(r) for r in rs]; ps = stats[(f, a)]["procs"]
        tot = {k: sum(x[k] for x in n) for k in n[0]} if n else {}
        walls = collections.Counter(p["wall_hit"] for p in ps)
        rows.append([f, ARM_NAMES.get(a, a), tot.get("numbers", 0), f"{100 * tot.get('match', 0) / tot['numbers']:.0f} %" if tot.get("numbers") else "—", tot.get("elsewhere", 0), tot.get("not_seen", 0), tot.get("derived", 0),
                     tot.get("uncited", 0), sum(kc(r) for r in rs), tot.get("unknown", 0), sum(p["executed"] for p in ps), sum(p["refused"] for p in ps), sum(p["errors"] for p in ps), sum(p["malformed"] for p in ps),
                     ", ".join(f"{k} {v}" for k, v in sorted(walls.items()) if k != "none") or "none", f"{100 * mean([p['redelivered_share'] for p in ps]):.0f} %", f"{100 * mean([p['utilization'] for p in ps]):.0f} %"])
    out += ["## 3. Number and kind checks per (run, arm)", "", table(["file", "arm", "numbers", "match", "elsewhere", "not seen", "derived", "uncited", "kind mismatches", "unknown ids", "executed", "refused", "errors", "malformed",
                                                                    "wall hits", "re-delivered", "utilization"], rows)]
    # 4 stability
    rows = []
    for p in paths:
        rs = load(p)
        st = RM.stability(rs)
        by_arm = collections.defaultdict(list)
        for (q, a), v in st.items():
            if v["runs"] > 1:
                by_arm[a].append(v)
        for a, vs in by_arm.items():
            rows.append([Path(p).name, ARM_NAMES.get(a, a), len(vs), f"{mean([v['numbers'] for v in vs]):.2f}", f"{mean([v['papers'] for v in vs]):.2f}", f"{mean([v['first_sentence'] for v in vs]):.2f}", f"{mean([v['stability'] for v in vs]):.2f}"])
    out += ["## 4. Stability per (run, arm) (P115, files with repeats)", "", table(["file", "arm", "questions", "numbers", "papers", "first sentence", "stability"], rows) if rows else "No file holds repeated runs.\n"]
    # 5 per question
    verd = {}
    if verdicts:
        for v in csv.DictReader(Path(verdicts).open(encoding="utf-8")):
            verd[(v["run_file"], v["arm"], int(v.get("run") or 1), int(v["question_no"]))] = v["verdict"]
    cols = list(groups)
    rows = []
    for q, n in qno.items():
        row = [n, q[:60]]
        for key in cols:
            rs = [r for r in groups[key] if r["question"].strip() == q]
            if not rs:
                row.append("—"); continue
            cell = []
            for r in rs:
                p = proc(r); x = nc(r)
                cell.append(f"{p['calls']} calls · {p['tool_tokens_delivered']:,} tok · match {100 * x['match'] / x['numbers']:.0f} % · not seen {x['not_seen']} · uncited {x['uncited']}" if x["numbers"] else f"{p['calls']} calls · {p['tool_tokens_delivered']:,} tok · no numbers")
                vd = verd.get((key[0], key[1], r.get("run", 1), n))
                if vd:
                    cell[-1] += f" · verdict {vd}"
            row.append("<br>".join(cell))
        rows.append(row)
    out += ["## 5. Per question", "", table(["no", "question", *[f"{f} · {ARM_NAMES.get(a, a)}" for f, a in cols]], rows)]
    counts = {}
    if verd:
        rows = []
        for key in cols:
            c = collections.Counter(verd.get((key[0], key[1], r.get("run", 1), qno[r["question"].strip()]), "—") for r in groups[key])
            n = sum(v for k, v in c.items() if k != "—"); lo, hi = wilson(c.get("right", 0), n)
            counts[key] = (c, n, lo, hi)
            rows.append([key[0], ARM_NAMES.get(key[1], key[1]), *[c.get(v, 0) for v in VERDICTS], c.get("—", 0), f"{100 * c.get('right', 0) / n:.0f} % [{100 * lo:.0f}–{100 * hi:.0f}]" if n else "—"])
        out += ["## 5b. Verdicts per (run, arm)", "", table(["file", "arm", *VERDICTS, "not graded", "right share (Wilson 95 %)"], rows)]
    # 6 closing paragraph, computed
    sent = []
    priced = {k: v["per_answer"] for k, v in stats.items() if v["per_answer"]}
    if len(priced) >= 2:
        lo_k = min(priced, key=priced.get); hi_k = max(priced, key=priced.get)
        sent.append(f"Per answer, {ARM_NAMES.get(lo_k[1], lo_k[1])} ({lo_k[0]}) is the cheapest at ${priced[lo_k]:.4f}; {ARM_NAMES.get(hi_k[1], hi_k[1])} ({hi_k[0]}) costs {priced[hi_k] / priced[lo_k]:.2f}× as much at ${priced[hi_k]:.4f}.")
    bad = {k: sum(nc(r)["not_seen"] + nc(r)["uncited"] for r in rs) for k, rs in groups.items()}
    if len(bad) >= 2:
        b = min(bad, key=bad.get)
        sent.append(f"{ARM_NAMES.get(b[1], b[1])} ({b[0]}) has the fewest not-seen and uncited numbers ({bad[b]}); " + "; ".join(f"{ARM_NAMES.get(k[1], k[1])} ({k[0]}) {v}" for k, v in bad.items() if k != b) + ".")
    for key, (c, n, lo, hi) in counts.items():
        sent.append(f"{ARM_NAMES.get(key[1], key[1])} ({key[0]}): {c.get('right', 0)} of {n} graded answers right ({100 * lo:.0f}–{100 * hi:.0f} % Wilson 95 %), {c.get('slips', 0)} slips, {c.get('material', 0)} material, {c.get('fabricated', 0)} fabricated, {c.get('empty', 0)} empty.")
    out += ["## 6. Summary", "", " ".join(sent) if sent else "One (run, arm) only: nothing to compare.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="+"); ap.add_argument("--verdicts"); ap.add_argument("--out")
    a = ap.parse_args()
    md = report(a.runs, a.verdicts)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8"); print(f"report {a.out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
