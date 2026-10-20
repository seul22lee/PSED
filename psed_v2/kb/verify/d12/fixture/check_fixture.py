"""P127/P128 check on the fixture: recompute, from the .jsonl files and verdicts.csv alone, per (file, run, question) the anchor and paper
overlap counts, per (file, run) the kb × text verdict grid and the two 'right & not right' lines, per file the preamble label (by arm when
several) and the within-file kb / text cost ratio, and compare with fixture_report.md."""
import collections, csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent / "fixture_report.md"
V = ["right", "slips", "material", "fabricated", "empty", "not graded"]
recs = [dict(json.loads(l), _file=f) for f in ("fix_a.jsonl", "fix_b.jsonl") for l in (HERE / f).open(encoding="utf-8") if l.strip()]
qno = {}
for r in recs:
    qno.setdefault(r["question"], len(qno) + 1)
verd = {(v["run_file"], v["arm"], int(v["run"]), int(v["question_no"])): v["verdict"] for v in csv.DictReader((HERE / "verdicts.csv").open(encoding="utf-8"))}
md = REPORT.read_text(encoding="utf-8")
err, n_cells, n_grids = [], 0, 0
sec5 = md.split("## 5. Per question", 1)[1].split("## 5b.", 1)[0].strip().splitlines()
head = [c.strip() for c in sec5[0].strip("|").split("|")]
rows = {int(c[0]): c for c in ([x.strip() for x in l.strip("|").split("|")] for l in sec5[2:])}
by = {(r["_file"], r["arm"], r["run"], qno[r["question"]]): r for r in recs}
pairs = sorted({(f, run) for (f, a, run, n) in by if a == "kb" and any(k[0] == f and k[1] == "text" for k in by)})
for f, run in pairs:
    col = head.index(f"{f} run {run} · anchors both / kb only / text only · papers both / kb only / text only")
    for q, n in qno.items():
        kb, tx = by.get((f, "kb", run, n)), by.get((f, "text", run, n))
        got = rows[n][col]
        if kb is None or tx is None:
            want = "—"
        else:
            a, b = ({i.split("#")[0] for i in r["cited"]} for r in (kb, tx))
            pa, pb = ({i.split(":")[0] for i in s} for s in (a, b))
            want = f"{len(a & b)} / {len(a - b)} / {len(b - a)} · {len(pa & pb)} / {len(pa - pb)} / {len(pb - pa)}"
        n_cells += 1
        if got != want:
            err.append(f"{f} run {run} q{n}: {got} != {want}")
sec5c = md.split("## 5c. Per-question verdict agreement", 1)[1].split("## 6.", 1)[0]
for f, run in pairs:
    block = sec5c.split(f"{f} run {run} (rows kb, columns text)", 1)[1].split("(rows kb, columns text)", 1)[0]
    grid = collections.Counter(); kbr, txr = [], []
    for q, n in qno.items():
        if (f, "kb", run, n) not in by and (f, "text", run, n) not in by:
            continue
        vk, vt = (verd.get((f, a, run, n), "not graded") if (f, a, run, n) in by else "not graded" for a in ("kb", "text"))
        grid[(vk, vt)] += 1
        kbr += [n] if vk == "right" and vt not in ("right", "not graded") else []
        txr += [n] if vt == "right" and vk not in ("right", "not graded") else []
    lines = [l for l in block.splitlines() if l.startswith("| ") and not l.startswith("| kb")][:6]
    got = {(l.strip("|").split("|")[0].strip(), V[j]): int(c) for l in lines for j, c in enumerate(l.strip("|").split("|")[1:])}
    if got != {(a, b): grid[(a, b)] for a in V for b in V}:
        err.append(f"{f} run {run}: grid {got} != {dict(grid)}")
    want = f"kb right & text not right: {len(kbr)} questions (nos {', '.join(map(str, kbr)) or '—'}); text right & kb not right: {len(txr)} (nos {', '.join(map(str, txr)) or '—'})"
    if want not in block:
        err.append(f"{f} run {run}: line missing: {want}")
    n_grids += 1
sec1 = md.split("## 1. Runs", 1)[1].split("## 2.", 1)[0]
for f in ("fix_a.jsonl", "fix_b.jsonl"):
    hs = {}
    for r in recs:
        if r["_file"] == f:
            hs.setdefault(r["arm"], set()).add(r["preamble_sha256"])
    allh = set().union(*hs.values())
    want = next(iter(allh)) if len(allh) == 1 else " · ".join(f"{a} " + "/".join(h[:4] + "…" for h in sorted(v)) for a, v in sorted(hs.items()))
    if not any(l.startswith(f"| {f} |") and f"| {want} |" in l for l in sec1.splitlines()):
        err.append(f"section 1: preamble of {f} should read {want!r}")
sec6 = md.split("## 6. Summary", 1)[1]
for f in ("fix_a.jsonl", "fix_b.jsonl"):
    per = {}
    for a in ("kb", "text"):
        rs = [r for r in recs if r["_file"] == f and r["arm"] == a]
        ans = [r for r in rs if r["answer"].strip() and not r["error"]]
        per[a] = sum(r["cost"] for r in rs) / len(ans)
    if f"In {f}, kb costs {per['kb'] / per['text']:.1f}× text per answer" not in sec6:
        err.append(f"section 6: the within-file cost clause of {f} is missing")
if "cheapest" in sec6:
    err.append("section 6: a cross-file cost comparison is still there")
if re.search(r"Fixture question", md) is None:
    err.append("questions missing from the report")
print(f"== P127 fixture: {len(recs)} records, {len(qno)} questions, {len(pairs)} (file, run) pairs with kb and text; {n_cells} anchor/paper count cells, {n_grids} verdict grids, 2 preamble labels and 2 cost clauses recomputed from the jsonl and verdicts.csv")
print("== P127 fixture: " + ("OK" if not err else "FAILED\n" + "\n".join(err)))
sys.exit(1 if err else 0)
