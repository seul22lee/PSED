#!/usr/bin/env python3
"""Three ways to answer one question about the three pilot papers, side by side, with a number check (and a fourth arm, the
knowledge base dumped into the prompt, selectable with --arms).

    python3 psed_v2/pilot/ask.py "question" [--model vendor:model] [--arms model,text,kb,dump]  # -> pilot/runs/asks.jsonl
    python3 psed_v2/pilot/ask.py --questions FILE --out RUNS.jsonl [--model vendor:model] [--arms model,text,kb]
                                 [--max-cost 20] [--max-calls 200]                            # -> RUNS.jsonl, RUNS.summary.csv

Arms (one model, its default settings, the same for every arm; the arms of a question run in parallel; default model, text, kb):
  model  Model only: the question, no documents, no tools.
  text   Paper text: every element of the three papers as "[id] text" in the system prompt (a table is one piece,
         <paper>:tabN, holding its caption and its markdown; figure panels have no text and are left out).
  kb     Knowledge base: five tools over query.py (tools.py: concept, search, values, detail, source); each returns plain text, one line per value or row,
         starting with its id in square brackets (format only; the tool layer computes nothing). At most 10 executed tool calls, about 2,000 tokens each, no line over 300 characters;
         a call whose normalized arguments equal an earlier call's gets one line, 'identical to call N' (P69); an error or an identical call costs nothing
         toward the 10, and two walls end a question's calls: 20 calls in all, 5 calls that returned an error (P75).
  dump   KB dump: the whole knowledge base serialized once (dump.py: the L0 map, every activity, entity and cited work with its settings and
         results, the comparison sets, the claims, the caveats once by id) in the system prompt, no tools (P71).
The models cite by writing ids in square brackets; nothing vendor-specific changes what a model sees (providers.py).
Number check: every number of the answer, sentence by sentence: matches (in a text cited in that sentence), elsewhere (in another
text the model was given), not seen (in no text it was given), uncited (the sentence cites no id); and unknown ids.
Kind check (P72): for every citation, the kind its sentence states (measured, read from a figure, computed by the authors, computed
from other values, assumed, taken from another work) against the record's kind; --kind-check RUNS.jsonl reruns it on stored answers.
LLM API calls are allowed only in this file, providers.py and serve.py. Runs with conda env psed310 (the vendor SDKs).
"""
import argparse, concurrent.futures as cf, csv, datetime, json, re, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(HERE))
import concept as CN  # noqa: E402
import dump as DU  # noqa: E402
import elements as E  # noqa: E402
import lists as L  # noqa: E402
import providers as P  # noqa: E402
import query as Q  # noqa: E402
import run_metrics as RM  # noqa: E402
from tools import TOOLS, KIND_MARK, run_tool, open_target, short_name  # noqa: E402

RUNS = HERE / "runs"
ARMS = ["model", "text", "kb", "dump"]
DEFAULT_ARMS = ["model", "text", "kb"]
ARM_NAMES = {"model": "Model only", "text": "Paper text", "kb": "Knowledge base", "dump": "KB dump"}
TOOL_CAP = 10           # executed calls per question (P44); an error or an identical call costs nothing toward it (P75)
TOTAL_WALL = 20         # every call of a question, executed or not (P75)
ERROR_WALL = 5          # calls of a question that returned an error (P75)

# ---------------------------------------------------------------------------------------------------------------- prompts (fixed)
SHARED = """You answer questions from atomic layer deposition (ALD) researchers about three papers:
{papers}
Answer in English. Start with a direct answer in one or two sentences, then give the evidence.
For every number, give its unit and the conditions it was obtained under (material, process, temperature, structure or substrate, how it was measured), and say whether it was measured, read from a figure, computed by the authors, computed from other values, assumed, or taken from another work.
If the answer depends on conditions, say so and organize the answer by those conditions.
Keep the answer under 400 words, tables included. Give the values that answer the question, not every related value; put each number's conditions and kind in a table rather than repeating them in sentences. State the assumptions that change the answer, and say briefly what your sources do not cover. If the question cannot be answered from what you have, say so and why."""

ARM_PROMPT = {
    "model": "You have no documents and no tools. Answer from your own knowledge. For each statement, say whether you know it from these papers specifically or from general knowledge, and how confident you are. Do not write source ids.",
    "text": "The full text of the three papers follows, split into pieces. Each piece starts with its id in square brackets. Base your answer on them. After every sentence that uses a piece, write the piece's id in square brackets, for example [yim20:s7.p5]. Cite only ids that appear below.",
    "kb": "You have tools that query a structured knowledge base built from the three papers. Use them. Every result line starts with its id in square brackets. After every sentence that uses a result, write the result's id in square brackets. Cite only ids the tools returned. Do not state a number from the papers that you did not obtain from a tool.",
    "dump": "The whole structured knowledge base built from the three papers follows, serialized once: its map, then per paper every activity, specimen, model run and cited work with its settings and results, the comparison sets, the claims and the caveats. Every record carries its id in square brackets; a value's kind is a mark explained in the legend at the end, unmarked values are measured or stated by the paper. Base your answer on it. After every sentence that uses a record, write the record's id in square brackets. Cite only ids that appear below.",
}


def paper_lines():
    """One line per paper: authors (first author et al.), year, title, journal, DOI, from corpus/manifest.csv."""
    man = {r["paper_id"]: r for r in csv.DictReader((V2 / "corpus/manifest.csv").open(encoding="utf-8"))}
    out = []
    for k, pid in Q.KEY.items():
        r = man[pid]
        first = r["authors"].split(";")[0].strip().split()[-1]
        out.append(f"- {first} et al. ({r['year']}). {r['title']}. {r['journal']}. DOI {r['doi']}.")
    return "\n".join(out)


_PIECES = {}


def pieces():
    """[(id, text)] of the three papers in elements.py order: abstract groups, headings, paragraphs, equations, captions, tables
    (one piece per table: caption and markdown, id <paper>:tabN or <paper>:tabuK); panels left out (no text)."""
    if _PIECES:
        return _PIECES["list"]
    out = []
    for k, pid in Q.KEY.items():
        rows, tx = E.build(pid)
        st = json.loads((V2 / f"ingest/final/{pid}/structure.json").read_text(encoding="utf-8"))
        tables = {str(c["number"]): c for c in st["captions"] if c["kind"] == "table" and c.get("number")}
        untabs = [c for c in st["captions"] if c["kind"] == "table" and not c.get("number") and c.get("table")]
        seen = set()
        for r in rows:
            eid, kind = r["element_id"], r["kind"]
            if kind == "panel":
                continue
            m = re.match(r"tab([0-9IVXLC]+)\.cap$", eid)
            if m:
                c = tables[m.group(1)]
                out.append((f"{k}:tab{m.group(1)}", (c.get("caption") or "").strip() + "\n" + (c.get("table") or "").strip()))
                continue
            if kind == "table_cell":
                m = re.match(r"(tabu\d+)\.", eid)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    out.append((f"{k}:{m.group(1)}", (untabs[int(m.group(1)[4:]) - 1].get("table") or "").strip()))
                continue
            out.append((f"{k}:{eid}", tx[eid].strip()))
    _PIECES["list"] = out
    return out


_DUMP = {}


def dump_text():
    """The knowledge base serialized once (dump.serialize, P71), built on first use."""
    if "text" not in _DUMP:
        _DUMP["text"] = DU.serialize()[0]
    return _DUMP["text"]


def system_prompt(arm):
    """SHARED with the paper lines; for the Knowledge base arm also the L0 map generated from the data and the descend protocol (P70;
    concept.l0_map, concept.DESCEND); then the arm's own text (and, for Paper text, the pieces; for KB dump, the serialization)."""
    s = SHARED.format(papers=paper_lines())
    if arm == "kb":
        s += "\n\n" + CN.l0_map() + "\n\n" + CN.DESCEND
    s += "\n\n" + ARM_PROMPT[arm]
    if arm == "dump":
        s += "\n\n" + dump_text()
    if arm == "text":
        parts, cur = [], None
        for pid_, text in pieces():
            k = pid_.split(":")[0]
            if k != cur:
                parts.append(f"\n=== {short_name(k)} ({k}) ===")
                cur = k
            parts.append(f"[{pid_}] {text}")
        s += "\n\n" + "\n\n".join(parts)
    return s


# ---------------------------------------------------------------------------------------------------------------- number check
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
ABBR = ["et al.", "e.g.", "i.e.", "Figs.", "Fig.", "Eqs.", "Eq.", "refs.", "ref.", "Ref.", "vs.", "approx.", "ca.", "cf.", "No.", "resp.", "Ref.", "Refs."]
MARK = re.compile(r"\[([^\[\]\n]+)\]")
ID = re.compile(r"^[A-Za-z0-9_]+:\S+$")
SCI = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*[×x·*]\s*10\s*\^\s*\(?\s*([-+]?\d+)\s*\)?|(?<![\w.^])10\s*\^\s*\(?\s*([-+]?\d+)\s*\)?|(?<![\w.])(\d+(?:\.\d+)?)[eE]([-+]?\d+)(?![\w])")
PLAIN = re.compile(r"(?<![\w.^\u0300-\u036f])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")
SKIP = re.compile(r"\b(?:Fig(?:ure)?s?\.?|Tables?|Eq(?:uation)?s?\.?|[Rr]efs?\.?|[Rr]eferences?|[Ss]amples?|Series|columns?|rows?|sections?|Sec\.)\s*\(?\d+[a-z]?", re.I)


def normalize(t):
    t = t.translate(SUP)
    t = re.sub(r"\\(?:times)", "×", t)
    t = re.sub(r"\\(?:cdot)", "·", t)
    t = re.sub(r"\\(?:text|mathrm|mathit)\s*", "", t)
    t = t.replace("$", "").replace("{", "").replace("}", "").replace("\\,", "").replace("−", "-").replace("–", " – ")
    t = re.sub(r"(?<=\d)[\u2009\u202f\u00a0](?=\d{3}\b)", "", t)                     # 17 000 with a thin space
    return t


def nums(t, skip=False):
    """[(value, half of the last digit's unit, text)] of a text: a × 10^b, 10^b, aEb, then plain numbers; digits attached to a letter
    (formulas, units, labels like PD50) are not numbers; with skip, numbers that follow Fig., Table, Eq., ref., sample or Series and
    years are left out."""
    t = normalize(t)
    out = []

    def sci(m):
        if m.group(3) is not None:
            e = int(m.group(3)); out.append((10.0 ** e, 0.0, m.group(0)))
        else:
            a, e = (m.group(1), m.group(2)) if m.group(1) is not None else (m.group(4), m.group(5))
            d = len(a.split(".")[1]) if "." in a else 0
            out.append((float(a) * 10.0 ** int(e), 0.5 * 10.0 ** (int(e) - d), m.group(0)))
        return " "
    t = SCI.sub(sci, t)
    if skip:
        t = SKIP.sub(" ", t)
    t = re.sub(r"(?<=[A-Za-zµÅΩ\u0300-\u036f_])\^?-?\d+(?:\.\d+)?", " ", t)
    for m in PLAIN.finditer(t):
        ip, fp = m.group(1).replace(",", ""), m.group(2)
        v = float(ip + ("." + fp if fp else ""))
        if skip and not fp and "," not in m.group(1) and len(ip) == 4 and 1900 <= v <= 2100 and not re.match(r"\s*[A-Za-zµÅΩ°%]", t[m.end():]):
            continue                                                              # a year
        out.append((v, 0.5 * 10.0 ** (-len(fp) if fp else 0), m.group(0)))
    return out


def sentences(text):
    """[(sentence text without markers, [cited ids])]: lines, then sentences; markers right after a sentence's end belong to it."""
    out = []
    for line in text.splitlines():
        s = line
        for i, a in enumerate(ABBR):
            s = s.replace(a, f"\x00{i}\x00")
        parts = re.split(r"(?<=[.!?])((?:\s*\[[^\[\]\n]+\])*)\s+(?=[A-Z(*\"“#-])", s)
        segs = [parts[0]]
        for j in range(1, len(parts), 2):
            segs[-1] += parts[j] or ""
            segs.append(parts[j + 1])
        for seg in segs:
            seg = re.sub("\x00(\\d+)\x00", lambda m: ABBR[int(m.group(1))], seg)
            ids = []
            for m in MARK.finditer(seg):
                toks = [x.strip().rstrip(".,;") for x in re.split(r"[,;]\s*|\s+", m.group(1)) if x.strip()]
                if toks and all(ID.match(x) for x in toks):
                    ids += toks
            clean = MARK.sub(lambda m: " " if all(ID.match(x.strip().rstrip(".,;")) for x in re.split(r"[,;]\s*|\s+", m.group(1)) if x.strip()) else m.group(0), seg)
            if clean.strip() or ids:
                out.append((clean, ids))
    return out


def _hit(v, half, pool):
    return any(abs(abs(v) - abs(c)) <= max(half, 1e-12 * abs(v)) * (1 + 1e-9) or abs(v) == abs(c) for c, _, _ in pool)


def number_check(text, arm, given):
    """Per number: matches (in the text of an id cited in its sentence, allowing for rounding of the last digit), elsewhere (not
    there, but in the text of another id the model was given), not seen (in no text the model was given: a value it computed or
    invented), uncited (its sentence cites no id); and the cited ids not given to the model."""
    rows, unknown, cited = [], [], []
    everything = [n for t in given.values() for n in nums(t)]
    for sent, ids in sentences(text):
        known = [i for i in ids if i in given]
        unknown += [i for i in ids if i not in given and i not in unknown]
        cited += [i for i in known if i not in cited]
        pool = [n for i in known for n in nums(given[i])]
        for v, half, raw in nums(sent, skip=True):
            st = "uncited" if not ids else "matches" if _hit(v, half, pool) else "elsewhere" if _hit(v, half, everything) else "not seen"
            rows.append(dict(number=raw.strip(), value=v, status=st, sentence=sent.strip()[:300], ids=ids))
    c = {k: sum(r["status"] == k for r in rows) for k in ("matches", "elsewhere", "not seen", "uncited")}
    return dict(numbers=len(rows), match=c["matches"], elsewhere=c["elsewhere"], not_seen=c["not seen"], uncited=c["uncited"],
                unknown_ids=len(unknown), unknown=unknown, cited=cited, per_number=rows)


# ---------------------------------------------------------------------------------------------------------------- kind check (P72)
# How an answer may word a kind: the ontology's phrase table and the SHARED prompt's kind words (measured, read from a figure,
# computed by the authors, computed from other values, assumed, taken from another work), with the wordings a model derives from
# them; 'computed here' is the wording of runs stored before P57. Measured and stated are one class (lists.UNMARKED, P57).
STATED_KIND = [
    ("computed_by_authors", r"(computed|calculated|fitted|fit|derived|estimated|obtained|determined) by (the )?(paper'?s? |study'?s? )?authors|authors'? (own )?(computed|calculated|fit|calculation|estimate|derived|reported)|paper'?s? (own )?(calculation|fit|estimate)"),
    ("computed_by_kb", r"computed (from other values|by (this|the) knowledge[- ]base|here)|knowledge[- ]base[- ](computed|derived|calculated)|\bkb[- ](computed|derived|calculated)|computed by (the )?kb\b|derived (here|from other values|by (this|the) knowledge base)|calculated (here|from other values)"),
    ("read_from_figure", r"read (off|from) (a |the )?(figure|fig\.?|plot|graph|curve|panel|image)|from (a |the )?figure"),
    ("assumed", r"\bassumed\b|\bassumption\b"),
    ("cited", r"taken from another work|from (another|other|a different) work|\bcited\b|literature value|from (the )?literature"),
    ("model_input", r"model input|simulation input|model parameter|input to the model"),
    ("stated", r"\bstated\b|\breported\b|\bquoted\b"),
    ("measured", r"\bmeasured\b"),
]
RECORD_KIND = {p: k for k, p in L.PHRASES.items()}
RECORD_KIND["computed here"] = "computed_by_kb"
MARK_KIND = {m: k for k, m in KIND_MARK.items()}


def _fold(ks):
    return {"measured" if k in L.UNMARKED else k for k in ks}


def record_kinds(i, text):
    """The kinds of a cited id: a fact's stored kind (the data); for an entity, a set or an element the kind phrases and marks in
    the text the model was given for it."""
    k = i.split(":")[0]
    if k in Q.TREES and i in Q.TREES[k].byid and "#" in i and Q.TREES[k].byid[i].get("data_kind"):
        return {Q.TREES[k].byid[i]["data_kind"]}
    out = set()
    for m in re.finditer(r"(?<!set )kinds?: ([^·\)\]]+)", text or ""):
        out |= {RECORD_KIND[p.strip().rstrip(":")] for p in m.group(1).split(";") if p.strip().rstrip(":") in RECORD_KIND}
    out |= {MARK_KIND[m.group(1)] for m in re.finditer(r"\((k\d+)\)", text or "") if m.group(1) in MARK_KIND}
    return out


def kind_check(text, given):
    """Post-hoc, beside the number check (P72): for every cited id, the kinds the sentence (or table row) around the citation states,
    matched against the phrase table, against the record's kind; a mismatch when the sentence states a kind and none of its kinds is
    the record's (measured and stated one class). Returns dict(mismatches, checked, per_id)."""
    rows, checked = [], 0
    for sent, ids in sentences(text):
        low = sent.lower()
        stated = {k for k, rx in STATED_KIND if re.search(rx, low)}
        if not stated or not ids:
            continue
        for i in dict.fromkeys(ids):
            rk = record_kinds(i, given.get(i, ""))
            if not rk:
                continue
            checked += 1
            if not (_fold(stated) & _fold(rk)):
                rows.append(dict(id=i, stated=sorted(stated), record=sorted(rk), sentence=sent.strip()[:300]))
    return dict(mismatches=len(rows), checked=checked, per_id=rows)


def kind_recheck(path, arm=None):
    """The kind check on the stored answers of a run file, from each record's cited texts (no model call); prints per record."""
    out = []
    for line in Path(path).open(encoding="utf-8"):
        r = json.loads(line)
        if arm and r["arm"] != arm:
            continue
        kc = kind_check(r["answer"], {i: v["text"] for i, v in r.get("cited", {}).items()})
        out.append(kc)
        print(f"{len(out):3d} {ARM_NAMES.get(r['arm'], r['arm']):15s} {kc['checked']} citations with a stated kind · {kc['mismatches']} mismatches")
        for x in kc["per_id"]:
            print(f"      {x['id']}: stated {', '.join(x['stated'])} · record {', '.join(x['record'])} · {x['sentence'][:120]}")
    return out


def words(text):
    """The answer's word count: id markers, table rules and lone punctuation are not words (P37)."""
    t = MARK.sub(" ", text or "").replace("|", " ")
    return len(re.findall(r"\S*[^\W_]\S*", t))


def check_line(nc, n_words=None):
    return (("" if n_words is None else f"{n_words} words · ") + f"{nc['numbers']} numbers · {nc['match']} match · {nc['elsewhere']} elsewhere · {nc['not_seen']} not seen · "
            f"{nc['uncited']} uncited · {nc['unknown_ids']} unknown ids")


def process_line(p):
    """The process metrics of a Knowledge base answer after its check line (P69): '' for an arm without tool calls."""
    if not p["calls"]:
        return ""
    return (f" · {p['calls']} calls ({p['refused']} refused, {p['duplicates']} duplicates) · tool output {p['tool_output_tokens']:,} tokens · "
            f"re-delivered {100 * p['redelivered_share']:.0f} % · {p['cited']} of {p['delivered']} delivered ids cited ({100 * p['utilization']:.0f} %)")


# ---------------------------------------------------------------------------------------------------------------- prices, records
def price(model):
    """The model's row of prices.csv (P73): input_per_mtok (a cache miss), cache_hit_per_mtok, output_per_mtok, their offpeak_
    counterparts and offpeak_utc ('16:30-00:30', the vendor's documented window), per million tokens; None without a row."""
    vendor, name = model.split(":", 1)
    f = HERE / "prices.csv"
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if r.get("vendor") == vendor and r.get("model") == name and r.get("input_per_mtok") and r.get("output_per_mtok"):
                return r
    return None


def offpeak(p, when):
    """Whether a time falls in the row's off-peak window (UTC, as the vendor documents it; a window may cross midnight)."""
    w = (p.get("offpeak_utc") or "").strip()
    if not w or when is None:
        return False
    a, b = (datetime.time(*map(int, x.split(":"))) for x in w.split("-"))
    t = when.astimezone(datetime.timezone.utc).time()
    return (a <= t < b) if a < b else (t >= a or t < b)


def cost_of(model, usage, when=None):
    """The cost of a record (P73): the input tokens not read from the cache at the miss price, the cache_read tokens at the hit
    price, the output tokens at the output price; off-peak prices when the record's time (aware, or naive local) is in the window."""
    p = price(model)
    if p is None:
        return None
    if when is not None and when.tzinfo is None:
        when = when.astimezone()
    pre = "offpeak_" if offpeak(p, when) else ""
    rate = lambda col: float(p.get(pre + col) or p.get(col) or 0)
    hit = float(p.get(pre + "cache_hit_per_mtok") or p.get("cache_hit_per_mtok") or rate("input_per_mtok"))
    cr = min(usage.get("cache_read", 0) or 0, usage["input"])
    return ((usage["input"] - cr) * rate("input_per_mtok") + cr * hit + usage["output"] * rate("output_per_mtok")) / 1e6


def recost(path):
    """The cost of every record of a run file recomputed from its token counts and time with the current prices.csv (no model
    call); prints the stored and the recomputed totals and returns the recomputed costs."""
    out, stored = [], 0.0
    for line in Path(path).open(encoding="utf-8"):
        r = json.loads(line)
        out.append(cost_of(r["model"], r["usage"], datetime.datetime.fromisoformat(r["time"])))
        stored += r.get("cost") or 0
    print(f"{len(out)} records · stored ${stored:.4f} · recomputed ${sum(c or 0 for c in out):.4f}")
    return out


_LOCK = threading.Lock()


def append(path, rec):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


# ---------------------------------------------------------------------------------------------------------------- arms
def answer_call(c, tool_calls, given, seen_calls):
    """One tool call answered and recorded (P38): a call whose normalized arguments equal an earlier call's (case, key order,
    whitespace: run_metrics.normalized) gets one line 'identical to call N' (P69); else run_tool. Call accounting (P75): only an
    executed call (no error) counts toward TOOL_CAP; an error (unresolved name, bad argument, nothing matches) or an identical call
    costs nothing toward it; two walls end a question's calls, TOTAL_WALL calls in all and ERROR_WALL error calls, and a refusal
    names the wall it hit (record error 'wall:total' or 'wall:errors'; the cap's refusal is 'cap', its message unchanged). Returns
    the result for the model; the record (name, arguments, results, error, chars, tokens, the full output) goes on tool_calls."""
    key = RM.normalized(c["name"], c["arguments"])
    n = RM.process(tool_calls)
    if n["calls"] >= TOTAL_WALL:
        msg = (f"error: the wall of {TOTAL_WALL} calls in this question is reached ({n['executed']} executed, {n['errors']} errors, "
               f"{n['identical']} identical); answer from what you have")
        rec, err = dict(results=0, error="wall:total", chars=0, output=msg), True
    elif key in seen_calls:
        msg = f"{RM.DUPLICATE}{seen_calls[key]}"
        rec, err = dict(results=0, error=msg, chars=len(msg), output=msg), False
    elif n["errors"] >= ERROR_WALL:
        msg = f"error: the wall of {ERROR_WALL} calls that returned an error is reached in this question; answer from what you have"
        rec, err = dict(results=0, error="wall:errors", chars=0, output=msg), True
    elif n["executed"] >= TOOL_CAP:
        msg = f"error: the limit of {TOOL_CAP} tool calls is reached"
        rec, err = dict(results=0, error="cap", chars=0, output=msg), True
    else:
        seen_calls[key] = len(tool_calls) + 1
        lines, e = run_tool(c["name"], c["arguments"])
        for i, ln in lines:                                           # an id's text: every returned line that starts with it or names it
            if i == "more":
                continue
            for j in dict.fromkeys([i] + MARK.findall(ln)):
                given[j] = (given.get(j, "") + "\n" + ln).strip()
        msg = e or "\n".join(ln if i == "more" else f"[{i}] {ln}" for i, ln in lines) or "no results"
        rec, err = dict(results=sum(i != "more" for i, _ in lines), error=e, chars=len(msg), output=msg), bool(e)
    tool_calls.append(dict(name=c["name"], arguments=c["arguments"], tokens=None, **rec))     # the full text the model received (P38)
    return dict(id=c["id"], name=c["name"], content=msg, error=err)


def run_arm(arm, question, model):
    t0 = time.time()
    usage = dict(input=0, output=0, cache_read=0, cache_write=0, reasoning=0)
    calls, retries, tool_calls, given, text, error, seen_calls = 0, 0, [], {}, "", "", {}
    try:
        s = P.session(model, system_prompt(arm), TOOLS if arm == "kb" else None)
        if arm == "text":
            given = dict(pieces())
        elif arm == "dump":
            given = DU.given(dump_text())
        t = s.send(question); calls += 1; retries += t.retries
        for k in usage:
            usage[k] += t.usage.get(k, 0)
        while t.calls and arm == "kb":
            results = [answer_call(c, tool_calls, given, seen_calls) for c in t.calls]
            batch_ = tool_calls[-len(t.calls):]
            prev = t.usage
            t = s.send(results=results); calls += 1; retries += t.retries
            for k in usage:
                usage[k] += t.usage.get(k, 0)
            # each result's tokens: the growth of the input over the previous call (less what that call returned and is re-sent),
            # shared among this turn's results by their length; the vendor's own counts, no tokenizer of ours
            grow = t.usage.get("input", 0) - prev.get("input", 0) - (prev.get("output", 0) - prev.get("reasoning", 0))
            tot = sum(x["chars"] for x in batch_) or 1
            for x in batch_:
                x["tokens"] = round(max(grow, 0) * x["chars"] / tot) if grow > 0 else round(x["chars"] / 4)
            if calls > TOTAL_WALL + 10:
                break
        text = t.text
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    t_start = datetime.datetime.fromtimestamp(t0).astimezone()
    nc = number_check(text, arm, given)
    proc = RM.process(tool_calls, nc["cited"])                               # P69: calls, refused, duplicates, tool output tokens, delivered and cited ids, shares
    kc = kind_check(text, given)                                              # P72: the stated kind of every citation against the record's
    return dict(time=datetime.datetime.now().isoformat(timespec="seconds"), question=question, arm=arm, model=model, answer=text,
                cited={i: dict(text=given[i], open=open_target(i)) for i in nc["cited"]}, unknown_ids=nc["unknown"], tool_calls=tool_calls,
                number_check={k: v for k, v in nc.items() if k not in ("cited", "unknown")}, kind_check=kc, process=proc, words=words(text),
                check_line=check_line(nc, words(text)) + f" · {kc['mismatches']} kind mismatches" + process_line(proc), usage=usage, model_calls=calls, retries=retries,
                cost=cost_of(model, usage, t_start), seconds=round(time.time() - t0, 1), error=error)


def ask(question, model=None, arms=None, out=None):
    """The arms of one question in parallel; each record appended to out (default runs/asks.jsonl)."""
    model = model or P.default_model()
    arms = arms or DEFAULT_ARMS
    with cf.ThreadPoolExecutor(len(arms)) as ex:
        recs = list(ex.map(lambda a: run_arm(a, question, model), arms))
    for r in recs:
        append(out or RUNS / "asks.jsonl", r)
    return recs


def last_records(question, model, path=None):
    """The last record of each arm for this question and model, from runs/asks.jsonl."""
    path = Path(path or RUNS / "asks.jsonl")
    last = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r["question"].strip() == question.strip() and r["model"] == model:
                last[r["arm"]] = r
    return [last[a] for a in ARMS if a in last]


SUMMARY = ["question", "arm", "model", "numbers", "match", "elsewhere", "not_seen", "uncited", "unknown_ids", "kind_mismatches", "tool_calls", "executed", "refused",
           "duplicates", "errors", "identical", "wall_hit", "tool_output_tokens", "redelivered_share", "delivered", "cited", "utilization", "words", "input_tokens",
           "output_tokens", "cache_read_tokens", "cost", "seconds", "error"]


def summary_row(r):
    """One summary.csv row of a record: the number check, the kind check (recomputed when the record predates P72), the process
    metrics (recomputed from the record's tool calls and cited ids: run_metrics.metrics_of, P74), words, tokens, cost."""
    nc, p = r["number_check"], RM.metrics_of(r)
    kc = r.get("kind_check") or kind_check(r["answer"], {i: v["text"] for i, v in r.get("cited", {}).items()})
    return dict(question=r["question"], arm=r["arm"], model=r["model"], numbers=nc["numbers"], match=nc["match"], elsewhere=nc["elsewhere"],
                not_seen=nc["not_seen"], uncited=nc["uncited"], unknown_ids=nc["unknown_ids"], kind_mismatches=kc["mismatches"], tool_calls=p["calls"],
                executed=p["executed"], refused=p["refused"], duplicates=p["duplicates"], errors=p["errors"], identical=p["identical"], wall_hit=p["wall_hit"],
                tool_output_tokens=p["tool_output_tokens"], redelivered_share=p["redelivered_share"],
                delivered=p["delivered"], cited=p["cited"], utilization=p["utilization"], words=r.get("words", 0), input_tokens=r["usage"]["input"],
                output_tokens=r["usage"]["output"], cache_read_tokens=r["usage"]["cache_read"], cost="" if r["cost"] is None else round(r["cost"], 4),
                seconds=r["seconds"], error=r["error"])


def batch(qfile, out, model, arms, max_cost, max_calls):
    qs = [l.strip() for l in Path(qfile).read_text(encoding="utf-8").splitlines() if l.strip()]
    out = Path(out)
    rows, spent, calls = [], 0.0, 0
    priced = price(model) is not None
    for n, q in enumerate(qs, 1):
        if (priced and spent >= max_cost) or (not priced and calls >= max_calls):
            print(f"stopped before question {n}: {'cost' if priced else 'model calls'} limit reached"); break
        for r in ask(q, model, arms, out):
            rows.append(summary_row(r)); spent += r["cost"] or 0; calls += r["model_calls"]
            print(f"{n:3d} {ARM_NAMES[r['arm']]:15s} {r['check_line']}{' · ERROR ' + r['error'][:80] if r['error'] else ''}")
    summ = out.with_suffix(".summary.csv")
    with summ.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY); w.writeheader(); w.writerows(rows)
    print("totals per arm:")
    for a in arms:
        rs = [r for r in rows if r["arm"] == a]
        tot = {k: sum(r[k] for r in rs) for k in ("numbers", "match", "elsewhere", "not_seen", "uncited", "unknown_ids", "kind_mismatches", "tool_calls", "executed", "refused", "duplicates", "errors", "identical", "tool_output_tokens", "delivered", "cited", "words", "input_tokens", "output_tokens")}
        cost = sum(r["cost"] for r in rs if r["cost"] != "") if priced else "cost not set"
        print(f"  {ARM_NAMES[a]:15s} {tot} cost {cost} · failed: {sum(1 for r in rs if r['error'])}")
    print(f"records {out}; summary {summ}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--questions"); ap.add_argument("--out"); ap.add_argument("--model"); ap.add_argument("--arms", default="model,text,kb")
    ap.add_argument("--max-cost", type=float, default=20.0); ap.add_argument("--max-calls", type=int, default=200)
    ap.add_argument("--kind-check", metavar="RUNS.jsonl", help="the kind check (P72) on the stored answers of a run file; no model call")
    ap.add_argument("--recost", metavar="RUNS.jsonl", help="the cost of a run file's records recomputed from their token counts with prices.csv (P73); no model call")
    a = ap.parse_args()
    model, arms = a.model or P.default_model(), a.arms.split(",")
    if a.kind_check:
        kind_recheck(a.kind_check)
    elif a.recost:
        recost(a.recost)
    elif a.questions:
        batch(a.questions, a.out or str(RUNS / "batch.jsonl"), model, arms, a.max_cost, a.max_calls)
    elif a.question:
        for r in ask(a.question, model, arms):
            print(f"== {ARM_NAMES[r['arm']]} ({r['model']}) · {r['check_line']} · {r['usage']['input']} in / {r['usage']['output']} out tokens · "
                  f"{'cost not set' if r['cost'] is None else '$%.3f' % r['cost']} · {r['seconds']} s")
            print(r["error"] or r["answer"]); print()
    else:
        ap.print_help()
