"""P129: the kb-vs-text comparison as one self-contained HTML page (inline CSS, a few lines of inline JS, no external URL), from the
same inputs and joins as compare_runs.py (P126–P128), no model call:

    python3 psed_v2/pilot/report_html.py RUN.jsonl [RUN.jsonl ...] [--verdicts verdicts.csv] [--papers 58] [--context-limit 900000] --out report.html

Sections: 1 header (files, model, arms, preamble hash per arm, questions, date); 2 cost and time per (file, arm), the cost per answer as
billed (the records' cost, compare_runs section 2) beside the cost without the cache discount (every input token at the full input price
of prices.csv, ask.cost_of with cache_read 0), and kb ÷ text within a file; 3 a projection to --papers papers (rules in its footnote);
4 the verdict sections 5b and 5c of compare_runs.report, rendered; 5 one card per question: the bottom line (first paragraph) of each
answer above kb | text columns with verdict badge and note, process numbers and the answer from its markdown, every cited id coloured by
whether both arms, kb only or text only cited its anchor (P127), repeats stacked; 6 a filter bar over the cards.
Measured paper count and per-paper index size: the records do not carry them, so they come from verify/d10/prompt_size.txt (P120)."""
import argparse, collections, csv, datetime, html, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_runs as CR  # noqa: E402
import ask  # noqa: E402  (price and cost_of only: prices.csv, peak and off-peak)

PROMPT_SIZE = HERE.parent / "verify" / "d10" / "prompt_size.txt"
VCOLOR = {"right": "#2e7d32", "slips": "#b8860b", "material": "#d9631e", "fabricated": "#c62828", "empty": "#757575"}


def measured_index():
    """(measured paper count, paper-index tokens per paper) from the P120 line of verify/d10/prompt_size.txt."""
    m = re.search(r"after P120: kb prompt [\d,]+ tokens at (\d+) papers \(map \d+, paper index (\d+)\)", PROMPT_SIZE.read_text(encoding="utf-8"))
    return int(m.group(1)), int(m.group(2)) / int(m.group(1))


def when(r):
    return datetime.datetime.fromisoformat(r["time"]) if r.get("time") else None


def nocache_cost(r):
    """The record's cost with every input token at the full input price (the record's peak or off-peak tier), output unchanged."""
    return ask.cost_of(r["model"], dict(r["usage"], cache_read=0), when(r))


def answered(rs):
    return [r for r in rs if (r.get("answer") or "").strip() and not r.get("error")]


# ------------------------------------------------------------------------------------------------------------- markdown, minimal
def inline(s, colour=None):
    """Escape, **bold**, and every bracketed group of ids wrapped id by id in a span coloured by colour(anchor)."""
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    def ids(m):
        parts = re.split(r"([;,]\s*)", m.group(1))
        if not all(re.fullmatch(r"[a-z0-9]+:\S+", p) for p in parts[::2]):
            return m.group(0)
        return "[" + "".join(p if k % 2 else f'<span class="cite {colour(p.split("#", 1)[0]) if colour else ""}">{p}</span>' for k, p in enumerate(parts)) + "]"
    return re.sub(r"\[([^\[\]]+)\]", ids, s)


def md(text, colour=None, h=3):
    """Headings, paragraphs, bold, bullet lists and pipe tables; anything else stays text. h: the level of a '#' heading."""
    lines, out, para, i = (text or "").splitlines(), [], [], 0
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para), colour) + "</p>"); para.clear()
    cells = lambda ln: [c.strip() for c in ln.strip().strip("|").split("|")]
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            flush(); i += 1; continue
        m = re.match(r"(#{1,6})\s+(.*)", ln)
        if m:
            flush(); k = min(6, h + len(m.group(1)) - 1); out.append(f"<h{k}>{inline(m.group(2), colour)}</h{k}>"); i += 1; continue
        if ln.lstrip().startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\s*\|?[\s:|-]*-[\s:|-]*", lines[i + 1]):
            flush(); head = cells(ln); i += 2; body = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                body.append(cells(lines[i])); i += 1
            out.append("<table><tr>" + "".join(f"<th>{inline(c, colour)}</th>" for c in head) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c, colour)}</td>" for c in row) + "</tr>" for row in body) + "</table>"); continue
        if re.match(r"\s*[-*]\s+", ln):
            flush(); items = []
            while i < len(lines) and re.match(r"\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"\s*[-*]\s+", "", lines[i], count=1)); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x, colour)}</li>" for x in items) + "</ul>"); continue
        para.append(ln.strip()); i += 1
    flush()
    return "\n".join(out)


def bottom_line(text, colour=None):
    """The first paragraph of an answer (the first block that is not a heading or a table), inline."""
    for b in re.split(r"\n\s*\n", (text or "").strip()):
        b = b.strip()
        if b and not b.startswith(("#", "|")):
            return inline(" ".join(re.sub(r"^\s*[-*]\s+", "", x) for x in b.splitlines()), colour)
    return "<em>no answer</em>"


def table(header, rows, cls=""):
    return (f'<table class="{cls}"><tr>' + "".join(f"<th>{html.escape(str(c))}</th>" for c in header) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in rows) + "</table>")


def money(x):
    return "—" if x is None else f"${x:.4f}"


# ------------------------------------------------------------------------------------------------------------------- the page
def report(paths, verdicts=None, papers=58, context_limit=900_000):
    recs = [r for p in paths for r in CR.load(p)]
    qno = CR.question_numbers(recs)
    groups = collections.OrderedDict()
    for r in recs:
        groups.setdefault((r["_file"], r["arm"]), []).append(r)
    verd = {}
    if verdicts:
        for v in csv.DictReader(Path(verdicts).open(encoding="utf-8")):
            verd[(v["run_file"], v["arm"], int(v.get("run") or 1), int(v["question_no"]))] = (v["verdict"], v.get("note") or "")
    files = list(dict.fromkeys(r["_file"] for r in recs))
    both = [f for f in files if (f, "kb") in groups and (f, "text") in groups]
    out = []
    # 1 header
    pre = collections.defaultdict(set)
    for r in recs:
        pre[r["arm"]].add(str(r.get("preamble_sha256", "—")))
    out += ["<h1>kb vs text comparison</h1>", "<dl class=\"head\">",
            f"<dt>files</dt><dd>{html.escape(', '.join(files))}</dd>",
            f"<dt>model</dt><dd>{html.escape(', '.join(sorted({r['model'] for r in recs})))}</dd>",
            f"<dt>arms</dt><dd>{html.escape(', '.join(CR.ARM_NAMES.get(a, a) for a in dict.fromkeys(r['arm'] for r in recs)))}</dd>",
            "<dt>preamble</dt><dd>" + " · ".join(f"{html.escape(a)} {html.escape('/'.join(sorted(v)))}" for a, v in sorted(pre.items())) + "</dd>",
            f"<dt>questions</dt><dd>{len(qno)}</dd>",
            f"<dt>generated</dt><dd>{datetime.date.today().isoformat()}</dd></dl>"]
    # 2 cost and time
    st = {}
    for (f, a), rs in groups.items():
        ans = answered(rs); inp = sum(r["usage"].get("input", 0) for r in rs); cr = sum(r["usage"].get("cache_read", 0) for r in rs)
        nocache = [nocache_cost(r) for r in rs]
        st[(f, a)] = dict(answers=len(ans), calls=CR.mean([CR.proc(r)["calls"] for r in rs]), input=inp, share=cr / inp if inp else 0.0,
                          output=sum(r["usage"].get("output", 0) for r in rs), billed=sum(r.get("cost") or 0 for r in rs) / len(ans) if ans else None,
                          nocache=sum(nocache) / len(ans) if ans and None not in nocache else None, seconds=CR.mean([r.get("seconds", 0) for r in rs]))
    def ratio(f, a, k):
        if a != "kb" or f not in both or not st[(f, "text")][k] or st[(f, "kb")][k] is None:
            return ""
        return f"{st[(f, 'kb')][k] / st[(f, 'text')][k]:.2f}×"
    rows = [[f, CR.ARM_NAMES.get(a, a), v["answers"], f"{v['calls']:.1f}", f"{v['input']:,} ({100 * v['share']:.0f} % cached)", f"{v['output']:,}",
             money(v["billed"]), money(v["nocache"]), f"{v['seconds']:.1f}", ratio(f, a, "billed"), ratio(f, a, "nocache")] for (f, a), v in st.items()]
    out += ["<h2>2. Cost and time per (file, arm)</h2>",
            table(["file", "arm", "answers", "tool calls / question", "input tokens (cache-read share)", "output tokens", "cost / answer as billed",
                   "cost / answer without cache discount", "s / answer (measured)", "kb ÷ text, billed", "kb ÷ text, without discount"], rows, "num sec2")]
    # 3 projection
    m_papers, per_paper = measured_index()
    rows = []
    for f in both:
        for a in ("kb", "text"):
            rs = groups[(f, a)]; ans = answered(rs)
            if not ans:
                continue
            billed = nocache = 0.0; prompt = []
            for r in rs:
                u = dict(r["usage"]); n_calls = max(r.get("model_calls") or 1, 1); share = u.get("cache_read", 0) / u["input"] if u.get("input") else 0.0
                if a == "text":
                    u["input"] = round(u["input"] * papers / m_papers); u["cache_read"] = round(u.get("cache_read", 0) * papers / m_papers)
                    prompt.append(u["input"] / n_calls)
                else:
                    extra = round((papers - m_papers) * per_paper) * n_calls          # the per-paper index, re-sent with every model call
                    u["input"] += extra; u["cache_read"] = u.get("cache_read", 0) + round(extra * share)
                    prompt.append(u["input"] / n_calls)
                billed += ask.cost_of(r["model"], u, when(r)) or 0; nocache += ask.cost_of(r["model"], dict(u, cache_read=0), when(r)) or 0
            top = max(prompt, default=0)
            rows.append([f, CR.ARM_NAMES.get(a, a), m_papers, papers, f"{CR.mean(prompt):,.0f}", money(billed / len(ans)), money(nocache / len(ans)),
                         "exceeds context limit" if a == "text" and top > context_limit else ""])
    out += [f"<h2>3. Projection to {papers} papers</h2>",
            table(["file", "arm", "measured papers", "projected papers", "projected input tokens / model call (mean)", "projection: cost / answer as billed",
                   "projection: cost / answer without cache discount", "note"], rows, "num"),
            f"<p class=\"foot\">Projection, not a measurement. Text arm: the prompt grows linearly with the paper count (each record's input and "
            f"cache-read tokens × {papers} / {m_papers}), output tokens unchanged; marked when the largest projected prompt of a call exceeds "
            f"{context_limit:,} tokens. Knowledge-base arm: only the per-paper index in the preamble grows, by {per_paper:.0f} tokens per paper "
            f"({m_papers} papers measured, {PROMPT_SIZE.relative_to(HERE.parent)}), re-sent with every model call of the record and read from the "
            f"cache in the record's measured cache-read share; tool output and output tokens unchanged. Prices: prices.csv in each record's tier. "
            f"Time is not projected.</p>"]
    # 4 verdicts, from compare_runs
    out.append("<h2>4. Verdicts</h2>")
    if verd:
        mdtext = CR.report(paths, verdicts)
        part = mdtext.split("## 5b.", 1)[1].split("## 6.", 1)[0]
        part = re.sub(r"^ Verdicts per \(run, arm\)\n", "<h3>Verdicts per (file, arm)</h3>\n", part)
        part = part.replace("## 5c. Per-question verdict agreement", "<h3>Per-question verdict agreement</h3>")
        out.append('<div class="verdicts">' + "\n".join(x if x.startswith("<h3>") else md(x) for x in re.split(r"(<h3>.*?</h3>)", part)) + "</div>")
    else:
        out.append("<p>No verdicts file given.</p>")
    # 5–6 cards with the filter bar
    out += ["<h2>5. Per question</h2>", '<p class="legend">Cited ids: <span class="cite both">cited by both arms</span><span class="cite kbonly">kb only</span>'
            '<span class="cite textonly">text only</span> (the anchor, the id before \'#\')</p>', '<div class="bar">' + "".join(f'<button data-f="{k}"{" class=on" if k == "all" else ""}>{t}</button>' for k, t in
            [("all", "all"), ("bothright", "both right"), ("kbnot", "kb not right"), ("textnot", "text not right"), ("disagree", "disagree")]) + "</div>"]
    for q, n in qno.items():
        flags, body = set(), []
        for f in files:
            if (f, "kb") not in groups and (f, "text") not in groups:
                continue
            runs = sorted({r.get("run", 1) for a in ("kb", "text") for r in groups.get((f, a), []) if r["question"].strip() == q})
            if not runs:
                continue
            pick = lambda a, run: next((r for r in groups.get((f, a), []) if r.get("run", 1) == run and r["question"].strip() == q), None)
            cols = {"kb": [], "text": []}; lines = []; tops = []
            for run in runs:
                rk, rt = pick("kb", run), pick("text", run)
                ak, at = (CR.anchors(r) if r else set() for r in (rk, rt))
                colour = lambda x: "both" if x in ak and x in at else ("kbonly" if x in ak else "textonly")
                vs = {a: verd.get((f, a, run, n), ("", ""))[0] for a in ("kb", "text")}
                if all(vs.values()):
                    flags |= {"bothright"} if vs["kb"] == vs["text"] == "right" else set()
                    flags |= {"kbnot"} if vs["kb"] != "right" else set()
                    flags |= {"textnot"} if vs["text"] != "right" else set()
                    flags |= {"disagree"} if vs["kb"] != vs["text"] else set()
                for a, r in (("kb", rk), ("text", rt)):
                    if r is None:
                        cols[a].append('<div class="run"><em>no record</em></div>'); continue
                    v, note = verd.get((f, a, run, n), ("", ""))
                    p = CR.proc(r)
                    tops.append(f'<div class="bl"><b>{CR.ARM_NAMES[a]}{" · run " + str(run) if len(runs) > 1 else ""}:</b> {bottom_line(r.get("answer"), colour)}</div>')
                    badge = f'<span class="badge" style="background:{VCOLOR[v]}">{v}</span>' if v in VCOLOR else '<span class="badge none">not graded</span>'
                    cols[a].append(f'<div class="run"><div class="meta">{"run " + str(run) + " · " if len(runs) > 1 else ""}{badge} {html.escape(note)}</div>'
                                   f'<div class="meta">{p["calls"]} calls · {p["tool_tokens_delivered"]:,} delivered tokens · {money(r.get("cost"))} · {r.get("seconds", 0)} s</div>'
                                   + (md(r.get("answer"), colour, 4) if (r.get("answer") or "").strip() else f'<p><em>{html.escape(r.get("error") or "empty answer")}</em></p>') + "</div>")
                if rk and rt:
                    pk, pt = ({i.split(":", 1)[0] for i in s} for s in (ak, at))
                    lines.append(f'<div class="ov">{"run " + str(run) + ": " if len(runs) > 1 else ""}anchors both / kb only / text only · papers both / kb only / text only: '
                                 f'{CR.overlap(ak, at)} · {CR.overlap(pk, pt)}</div>')
            body.append(f'<div class="file">{html.escape(f)}</div><div class="tops">{"".join(tops)}</div><div class="cols"><div class="col"><h4>Knowledge base</h4>{"".join(cols["kb"])}</div>'
                        f'<div class="col"><h4>Paper text</h4>{"".join(cols["text"])}</div></div>' + "".join(lines))
        out.append(f'<section class="card" data-flags="{" ".join(sorted(flags))}"><h3>{n}. {html.escape(q)}</h3>{"".join(body)}</section>')
    return PAGE.replace("{BODY}", "\n".join(out))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>kb vs text comparison</title>
<style>
:root { --bg: #fff; --fg: #1d1d1f; --muted: #666; --line: #ddd; --card: #fafafa; --both: #d7f0d9; --kb: #d6e6fb; --text: #fde3cc; }
@media (prefers-color-scheme: dark) { :root { --bg: #161618; --fg: #e8e8ea; --muted: #a0a0a6; --line: #3a3a3e; --card: #1f1f22; --both: #1f4a26; --kb: #1c3557; --text: #5a3415; } }
body { background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 1400px; padding: 16px; }
h1 { font-size: 1.5em; } h2 { margin-top: 2em; border-bottom: 1px solid var(--line); }
table { border-collapse: collapse; margin: .5em 0; font-size: .9em; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 3px 7px; text-align: left; vertical-align: top; }
table.num td { text-align: right; } table.num td:first-child, table.num td:nth-child(2) { text-align: left; }
dl.head { display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; } dt { color: var(--muted); } dd { margin: 0; }
.foot { color: var(--muted); font-size: .88em; max-width: 70em; }
.bar { position: sticky; top: 0; background: var(--bg); padding: 8px 0; z-index: 1; }
.bar button { border: 1px solid var(--line); background: var(--card); color: var(--fg); border-radius: 14px; padding: 3px 12px; margin-right: 4px; cursor: pointer; }
.bar button.on { background: var(--fg); color: var(--bg); }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 16px; margin: 14px 0; }
.file { color: var(--muted); font-size: .85em; margin-top: 8px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; } @media (max-width: 800px) { .cols { grid-template-columns: 1fr; } }
.col { min-width: 0; } .col h4 { margin: 6px 0; } .run { border-top: 1px dashed var(--line); padding-top: 6px; margin-top: 6px; }
.meta { color: var(--muted); font-size: .88em; } .tops { margin: 4px 0 8px; } .bl { margin: 2px 0; }
.badge { color: #fff; border-radius: 4px; padding: 0 6px; font-size: .85em; } .badge.none { color: var(--muted); border: 1px solid var(--line); }
.cite { border-radius: 3px; padding: 0 2px; } .cite.both { background: var(--both); } .cite.kbonly { background: var(--kb); } .cite.textonly { background: var(--text); }
.ov { font-size: .88em; margin: 6px 0; } .legend span { margin-right: 10px; }
</style></head><body>
{BODY}
<script>
document.querySelectorAll('.bar button').forEach(b => b.onclick = () => {
  document.querySelectorAll('.bar button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.card').forEach(c => {
    c.style.display = b.dataset.f === 'all' || c.dataset.flags.split(' ').includes(b.dataset.f) ? '' : 'none';
  });
});
</script>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="+"); ap.add_argument("--verdicts"); ap.add_argument("--papers", type=int, default=58)
    ap.add_argument("--context-limit", type=int, default=900_000); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).write_text(report(a.runs, a.verdicts, a.papers, a.context_limit), encoding="utf-8")
    print(f"report {a.out}")


if __name__ == "__main__":
    main()
