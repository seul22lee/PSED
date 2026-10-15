"""Stage 2 helpers, shared by the per-paper <paper_id>.facts.py scripts and by check.py.

A <paper_id>.facts.py reads the paper itself (element texts from elements.py --text, figure crops) and states each fact:

    F(K, "s3.p2;fig9c.cap", "observation", "film thickness at the channel entrance is about 50 nm after 500 cycles",
      quantity="film_thickness", qualifiers="position=entrance", value="50", unit="nm", data_kind="measured",
      method="reflectometry", mentions="sample 8;H 500 nm")
    NK("s0.p1", "citation line")                 # an element with no knowledge, with the reason
    write(K, PID)                                # <pid>.facts.csv, <pid>.coverage.csv, <pid>.points.json

<pid>.facts.csv columns (one row per piece of knowledge; a fact stated in several elements is one row citing all of them):
  fact_id      <key>:<first evidence id>#<n>, stable while the element's facts keep their order
  type         lists.TYPES: setting | observation | derived | model | definition | claim | cited
  evidence     element ids, ";"-separated (the first one names the fact)
  statement    one line, own words
  quantity     an id of lists.QUANTITIES, or "other" with label_as_printed; blank for a claim without one
  qualifiers   k=v;k=v from lists.QUALIFIERS
  label_as_printed  the quantity's label or symbol as printed, when quantity is other (else optional)
  value, value_min, value_max, censor, unit   as printed in the element (no unit conversion in stage 2)
  value_text   a categorical value (pillar layout v2a, a substrate, a crystallinity class, a reactor name, an LHAR type) when the
               value is a name, not a number; the statement then names the setting without repeating the value
  points_ref   the name of a digitized curve in <pid>.points.json (only from points.json or accepted v1 points)
  data_kind    lists.DATA_KINDS (required with a value or points)
  method       a short id from lists.METHODS
  mentions     sample, series, condition, figure and reference labels written in the element, as printed, ";"-separated
  inputs       fact_ids this fact is computed or fitted from, when the element says so
  parent       (stage 3) one id: the row without which this fact would not exist; blank only for the paper row
  links        (stage 3) ids of a second home, ";"-separated: a claim's supporting facts, the same data shown twice

Stage 3 makes each paper one tree inside its facts file. Tree rows have ids without "#" and are added with N():
  <key>                    type=paper, the root
  <key>:process            type=process, conditions shared by every run
  <key>:grp:<name>         type=group, a set of runs the paper names (a series, a reproducibility set, the simulations)
  <key>:run<n>, :sim:<k>   type=run, a deposition, a specimen or a simulation; qualifiers run=<kind>;how=stated|inferred;<key>=<v>
  <key>:refs:<n>           type=cited, a cited work (reference number n)
Tree rows do not count as facts and do not enter coverage.csv. A group row's first link is its purpose: the fact (the
paper's own sentence, a claim, observation, setting or model) that says what the group was made to test; purpose(gid, fid)
sets it.
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lists as L  # noqa: E402
import elements  # noqa: E402

FIELDS = ["fact_id", "type", "evidence", "statement", "quantity", "qualifiers", "label_as_printed", "value", "value_min",
          "value_max", "censor", "unit", "value_text", "points_ref", "data_kind", "method", "mentions", "inputs", "parent", "links"]
COV_FIELDS = ["element_id", "kind", "status", "fact_ids", "reason", "n_numbers", "n_numbers_reached"]

_facts, _nk, _count, _points = [], {}, {}, {}


def F(key, evidence, type_, statement, **kw):
    """Add one fact; returns its fact_id (use it in inputs= of later facts)."""
    ev = [e.strip() for e in evidence.split(";") if e.strip()]
    n = _count[ev[0]] = _count.get(ev[0], 0) + 1
    fid = f"{key}:{ev[0]}#{n}"
    row = {k: "" for k in FIELDS}
    row.update(fact_id=fid, type=type_, evidence=";".join(ev), statement=statement)
    for k, v in kw.items():
        if k not in FIELDS:
            raise KeyError(k)
        row[k] = ";".join(v) if isinstance(v, (list, tuple)) else str(v)
    _facts.append(row)
    return fid


def N(fid, type_, statement, parent, evidence="", **kw):
    """Add a tree row (paper, process, group, run or cited work); returns its id."""
    row = {k: "" for k in FIELDS}
    row.update(fact_id=fid, type=type_, statement=statement, parent=parent, evidence=evidence)
    for k, v in kw.items():
        if k not in FIELDS:
            raise KeyError(k)
        row[k] = ";".join(v) if isinstance(v, (list, tuple)) else str(v)
    _facts.append(row)
    return fid


def purpose(gid, fid):
    """Make fact fid the purpose of group row gid (its first link); the row and the fact must already exist."""
    row = next(r for r in _facts if r["fact_id"] == gid)
    assert any(r["fact_id"] == fid for r in _facts), fid
    rest = [l for l in row["links"].split(";") if l and l != fid]
    row["links"] = ";".join([fid] + rest)
    return fid


def facts():
    """The rows added so far (for a paper script's stage-3 pass)."""
    return _facts


def NK(element_ids, reason):
    """Elements that hold no knowledge, with the reason; element_ids may be ';'-separated."""
    for e in element_ids.split(";"):
        if e.strip():
            _nk[e.strip()] = reason


def P(pid, name, points, source, x_label="", y_label="", note=""):
    """Keep a digitized curve for <pid>.points.json under its name; returns the points_ref (the name)."""
    if name in _points:
        raise KeyError(f"points {name} given twice")
    _points[name] = dict(source=source, x_label_as_printed=x_label, y_label_as_printed=y_label, note=note, points=points)
    return name


def cases_points(pid, figure, panel, series):
    """The points of one series of points.json (first match on paper, figure, panel and series label)."""
    for s in json.loads((HERE / "points.json").read_text(encoding="utf-8"))["series"]:
        if s["paper"] == pid and str(s["figure"]) == str(figure) and s["panel"] == panel and s["series"] == series:
            return s
    raise KeyError((figure, panel, series))


def v1_points(series_id):
    """Points of an accepted v1 curve (v1_points.json, accepted in v1_points_check.csv)."""
    ok = {r["pilot_series_id"] for r in csv.DictReader((HERE / "v1_points_check.csv").open(encoding="utf-8"))
          if r["decision"] == "accept"}
    if series_id not in ok:
        raise KeyError(f"{series_id} is not an accepted v1 curve")
    return json.loads((HERE / "v1_points.json").read_text(encoding="utf-8"))["series"][series_id]


def num(x):
    try:
        return float(str(x).replace("−", "-").replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def nums_of(text):
    out = set()
    for t in re.findall(r"[-−]?\d+(?:[.,]\d+)?(?:[eE][-−+]?\d+)?", text or ""):
        v = num(t.replace(",", ".") if re.fullmatch(r"[-−]?\d+,\d{1,2}", t) else t)
        if v is not None:
            out.add(round(abs(v), 9))
    return out


def reached(element_text, facts):
    """Numbers of an element (elements.numbers) and how many appear in a fact citing it (value, range, statement,
    mentions or label)."""
    have = set()
    for f in facts:
        for k in ("value", "value_min", "value_max", "statement", "mentions", "label_as_printed", "qualifiers"):
            have |= nums_of(f[k])
    ns = elements.numbers(element_text)
    hit = 0
    for t in ns:
        t2 = re.sub(r"\s*[×x]\s*10\^?\{?([-−]?\d+)\}?", r"e\1", t)
        v = num(t2) if num(t2) is not None else num(t2.replace(",", "."))
        if v is not None and round(abs(v), 9) in have:
            hit += 1
    return len(ns), hit


def write(key, pid):
    """<pid>.facts.csv, <pid>.coverage.csv and <pid>.points.json; elements without facts and without an NK reason are 'missed'."""
    with (HERE / f"{pid}.facts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(_facts)
    (HERE / f"{pid}.points.json").write_text(json.dumps(_points, ensure_ascii=False, indent=0), encoding="utf-8")
    els = elements.load(pid)
    texts = elements.texts(pid)
    by_el = {}
    for r in _facts:
        if "#" not in r["fact_id"]:
            continue                                          # tree rows are not facts
        for e in r["evidence"].split(";"):
            by_el.setdefault(e, []).append(r)
    rows = []
    for e in els:
        eid = e["element_id"]
        fs = by_el.get(eid, [])
        nn, nr = reached(texts.get(eid, ""), fs) if e["kind"] != "panel" else ("", "")
        status = "covered" if fs else ("no knowledge" if eid in _nk else "missed")
        rows.append(dict(element_id=eid, kind=e["kind"], status=status, fact_ids=";".join(r["fact_id"] for r in fs),
                         reason=_nk.get(eid, "") if not fs else "", n_numbers=nn, n_numbers_reached=nr))
    with (HERE / f"{pid}.coverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COV_FIELDS); w.writeheader(); w.writerows(rows)
    import collections
    fs = [r for r in _facts if "#" in r["fact_id"]]
    print(pid, len(fs), "facts", dict(collections.Counter(r["type"] for r in fs)), "| tree rows", len(_facts) - len(fs),
          dict(collections.Counter(r["status"] for r in rows)))
