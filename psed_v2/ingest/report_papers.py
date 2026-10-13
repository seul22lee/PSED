#!/usr/bin/env python3
"""ingest/reports/papers.html: the ingest output paper by paper, for review by eye (reads the repo, writes the report only).
    ~/miniconda3/envs/psed310/bin/python psed_v2/ingest/report_papers.py            all papers
    ONLY=<paper_id>[,<paper_id>] ... report_papers.py                               a subset (same file)

Reads corpus/manifest.csv, corpus/openalex_abstracts.json, ingest/final/<pid>/ (document.md, structure.json, figures/),
ingest/marker/<pid>/ (bands.json, band crops, structure.json for n_pages), corpus/raw/<pid>.pdf (equation crops),
ingest/answers/*.json (answer-set tags) and ingest/ERRORS.md (known errors per paper). Per paper: metadata, abstract
(source, recall against OpenAlex), figures with captions, tables (Marker's table, crop, check), equations (crop, both
LaTeX rendered by KaTeX), the body text with every flag at its sentence and every repair marked, band repairs and
the known errors. Markdown and LaTeX are rendered in the browser (marked and KaTeX from cdnjs; without network the
raw text is shown). Images embedded as JPEG, max width 900 px; above 100 MB one HTML per paper plus an index.
"""
import base64, collections, csv, datetime, html, io, json, os, re, sys

from PIL import Image
import pypdfium2 as pdfium

ING = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ING)
OUT_DIR = f"{ING}/reports"
MAXW = 900
QUALITY = 80
LIMIT = 100 * 1024 * 1024

# ----------------------------------------------------------------------------------------------------------- images
def _to_jpeg_uri(img):
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if img.width > MAXW:
        img = img.resize((MAXW, max(1, round(img.height * MAXW / img.width))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def img_uri(path):
    try:
        with Image.open(path) as im:
            im.load()
            return _to_jpeg_uri(im)
    except Exception as e:
        print(f"image not embedded: {path}: {e!r}", file=sys.stderr)
        return None


_pdfs = {}


def pdf_crop_uri(pid, page, bbox, pad=6, scale=2.0):
    """bbox in Marker's top-left PDF points on page `page` (1-based)."""
    if pid not in _pdfs:
        _pdfs[pid] = pdfium.PdfDocument(f"{ROOT}/corpus/raw/{pid}.pdf")
    doc = _pdfs[pid]
    if page < 1 or page > len(doc):
        return None
    pg = doc[page - 1]
    W, H = pg.get_size()
    x0, y0, x1, y1 = bbox
    crop = (max(0, x0 - pad), max(0, H - y1 - pad), max(0, W - x1 - pad), max(0, y0 - pad))
    if crop[0] + crop[2] >= W or crop[1] + crop[3] >= H:
        return None
    try:
        im = pg.render(scale=scale, crop=crop).to_pil()
    except Exception:
        return None
    return _to_jpeg_uri(im)


def img_tag(uri, cls="", alt=""):
    if not uri:
        return '<span class="noimg">no image</span>'
    return f'<img class="{cls}" src="{uri}" alt="{html.escape(alt)}" loading="lazy">'


# ----------------------------------------------------------------------------------------------------------- text
E = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def md_inline(s):
    """Minimal inline markdown for ERRORS.md cells: code, bold, italic-free."""
    s = E(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


WORD = re.compile(r"[A-Za-z]{3,}")


def _wre(w):
    return re.compile(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])")


def locate_sentence(chunk, sentence):
    """(start, end) of `sentence` (normalised text) inside the raw markdown chunk, by its words in order."""
    ws = WORD.findall(sentence)
    if not ws:
        return None
    starts = [m.start() for m in _wre(ws[0]).finditer(chunk)]
    if not starts:
        return None

    def score(s):
        pos, n = s, 0
        for w in ws[1:6]:
            m = _wre(w).search(chunk, pos, min(len(chunk), pos + 400))
            if m:
                n += 1
                pos = m.end()
        return n

    s = max(starts, key=score)
    pos = s
    end = s + len(ws[0])
    lim = min(len(chunk), s + len(sentence) * 3 + 200)
    for w in ws:
        m = _wre(w).search(chunk, pos, lim)
        if m:
            pos = m.end()
            end = m.end()
    m = re.match(r"(?:</su[bp]>)?[)\].,;:]{0,3}", chunk[end:])
    end += m.end()
    m = re.match(r"[^.!?\n]{0,60}?[.!?](?=\s|$|<)", chunk[end:])   # the rest of the sentence (short tokens, "1b).")
    if m:
        end += m.end()
    return s, end


def balance_end(chunk, s, e):
    """Extend e so that every tag opened inside chunk[s:e] is closed inside it."""
    for _ in range(4):
        seg = chunk[s:e]
        opens = len(re.findall(r"<(su[bp]|b|i)>", seg))
        closes = len(re.findall(r"</(su[bp]|b|i)>", seg))
        if opens <= closes:
            break
        m = re.compile(r"</(su[bp]|b|i)>").search(chunk, e)
        if not m:
            break
        e = m.end()
    return e


MATH_RE = re.compile(r"\$\$[\s\S]+?\$\$|\$(?!\s)[^$\n]{1,400}?(?<!\s)\$")


def snap_math(chunk, s, e):
    """Move s/e outside any inline or display math span they fall into (the page protects math before markdown)."""
    for m in MATH_RE.finditer(chunk):
        if m.start() < s < m.end():
            s = m.start()
        if m.start() < e < m.end():
            e = m.end()
    return s, e


def lead_len(chunk):
    m = re.match(r"\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s*)?", chunk)
    return m.end()


def is_block_special(chunk):
    c = chunk.lstrip()
    return c.startswith("|") or c.startswith("$$") or c.startswith("![") or c.startswith("<")


def annotate_markdown(md, flags, repairs, ans_flags, pid):
    """Insert flag badges / marks and repair marks into the markdown. Returns (md, notes[]) with notes for the side panel."""
    chunks = re.split(r"(\n\s*\n)", md)          # keep separators at odd indices
    texts = chunks[0::2]
    seps = chunks[1::2]
    marks = collections.defaultdict(list)        # raw chunk index -> [(start, end, id, cls)]
    tails = collections.defaultdict(list)        # raw chunk index -> [badge html]
    notes = []
    for i, f in enumerate(flags):
        fid = f"f{i + 1}"
        key = f"{pid}|{f['page']}|{f['kind'][:6]}|{f.get('number')}"
        ans = ans_flags.get(key)
        kind = f["kind"]
        if kind == "not checkable":
            notes.append({"id": fid, "label": ("output side, " if f.get("side") == "output" else "") + "not checkable: " + (f.get("reason") or ""), "f": f, "ans": ans, "nc": True})
            continue
        if kind.startswith("letters"):
            label = "letters differ: " + ", ".join(f.get("layer_words") or []) + " → " + ", ".join(f.get("output_words") or [])
        elif kind.startswith("line not"):
            label = "line not found"
        elif "text layer missing" in kind:
            label = f"missing in output: {f.get('number')}"
        else:
            label = f"absent in layer: {f.get('number')}"
        notes.append({"id": fid, "label": label, "f": f, "ans": ans})
        badge = f'<a class="fb" id="{pid}-{fid}" data-f="{fid}" title="{E(label)}">⚑{i + 1}</a>'
        if kind.startswith("line not"):
            ci = f.get("after_paragraph", 0)
            tails[ci].append(badge + f'<span class="fbl">dropped line after this paragraph: “{E(f.get("layer_line", ""))}”</span>')
            continue
        ci = f.get("paragraph")
        if ci is None or ci >= len(texts):
            tails[0].append(badge)
            continue
        loc = locate_sentence(texts[ci], f.get("output_sentence", "")) if f.get("output_sentence") else None
        if loc:
            s0, e0 = snap_math(texts[ci], loc[0], balance_end(texts[ci], loc[0], loc[1]))
            marks[ci].append((s0, e0, fid, "flag", badge))
        else:
            marks[ci].append((snap_math(texts[ci], lead_len(texts[ci]), lead_len(texts[ci]))[0], None, fid, "flag", badge))
    rnotes = []
    for j, r in enumerate(repairs):
        rid = f"r{j + 1}"
        if r["kind"].startswith("number replaced"):
            label = f'R1 number replaced: {r["from"]} → {r["to"]}'
            badge = f'<a class="fb rep" id="{pid}-{rid}" data-f="{rid}" title="{E(label)}">R1</a>'
            # the chunk with the best overlap with the sentence that holds `to`
            sw = set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", r.get("sentence", "")))
            best, bi = -1, None
            for ci, t in enumerate(texts):
                if r["to"] not in t:
                    continue
                tw = set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", t))
                sc = len(sw & tw)
                if sc > best:
                    best, bi = sc, ci
            if bi is None:
                tails[0].append(badge)
            else:
                p = texts[bi].find(r["to"])
                s0, e0 = snap_math(texts[bi], p, balance_end(texts[bi], p, p + len(r["to"])))
                marks[bi].append((s0, e0, rid, "rep", badge))
            rnotes.append({"id": rid, "label": label, "r": r})
        else:
            label = "R2 dropped line restored from the text layer"
            rnotes.append({"id": rid, "label": label, "r": r})
    # R2 blocks: every chunk carrying the marker
    r2 = [n for n in rnotes if n["label"].startswith("R2")]
    k = 0
    for ci, t in enumerate(texts):
        if "[restored from the text layer]" in t:
            ids = []
            # one block may hold several restored lines (one repair each)
            nlines = t.count("\n") + 1
            for _ in range(nlines):
                if k < len(r2):
                    ids.append(r2[k]["id"])
                    k += 1
            if not ids:
                ids = ["r?"]
            badge = "".join(f'<a class="fb rep" id="{pid}-{x}" data-f="{x}" title="R2 dropped line restored">R2</a>' for x in ids)
            marks[ci].append((0, len(t), ids[0], "rep", badge))
    # apply
    for ci in list(marks):
        t = texts[ci]
        spans = sorted(marks[ci], key=lambda s: (s[0], -(s[1] or s[0])))
        out, pos = [], 0
        pieces = []
        last_end = -1
        for s, e, fid, cls, badge in spans:
            if pieces and e is not None and (pieces[-1][0], pieces[-1][1]) == (s, e):   # the same sentence: one mark, several badges
                pieces[-1] = (s, e, pieces[-1][2] + " " + fid, cls, pieces[-1][4] + badge)
            elif e is None or s < last_end:        # badge only (no span, or overlapping a previous span)
                pieces.append((s, s, fid, cls, badge))
            else:
                pieces.append((s, e, fid, cls, badge))
                last_end = e
        pieces.sort(key=lambda p: p[0])
        for s, e, fid, cls, badge in pieces:
            s = max(s, pos)
            out.append(t[pos:s])
            if e > s:
                out.append(badge + f'<mark class="{cls}" data-f="{fid}">' + t[s:e] + "</mark>")
                pos = e
            else:
                out.append(badge)
                pos = s
        out.append(t[pos:])
        texts[ci] = "".join(out)
    for ci, tl in tails.items():
        if ci >= len(texts):
            ci = len(texts) - 1
        if is_block_special(texts[ci]):
            texts[ci] = texts[ci] + "\n\n" + "<p class=\"fbline\">" + " ".join(tl) + "</p>"
        else:
            texts[ci] = texts[ci] + " " + " ".join(tl)
    res = []
    for i, t in enumerate(texts):
        res.append(t)
        if i < len(seps):
            res.append(seps[i])
    return "".join(res), notes, rnotes


# ----------------------------------------------------------------------------------------------------------- ERRORS.md
def parse_errors_md(path):
    """[(section, header_cells, [row_cells])] of every markdown table in ERRORS.md."""
    lines = open(path).read().split("\n")
    sec = ""
    tables = []
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("## "):
            sec = l[3:].strip()
        if l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*-", lines[i + 1]):
            header = [c.strip() for c in l.strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tables.append((sec, header, rows))
            i = j
            continue
        i += 1
    return tables


def pid_tokens(pid):
    toks = {pid}
    if "_" in pid:
        suf = pid.split("_", 1)[1]
        toks.add(suf)
        if suf.startswith("acs."):
            toks.add(suf[4:])
    return toks


def errors_for(tables, pid):
    toks = pid_tokens(pid)
    out = []
    for sec, header, rows in tables:
        hit = [r for r in rows if any(t in " ".join(r) for t in toks)]
        if hit:
            out.append((sec, header, hit))
    return out


# ----------------------------------------------------------------------------------------------------------- build
def words4(s):
    return set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", s or ""))


def build_paper(pid, man, oa, ans, err_tables):
    fin = f"{ING}/final/{pid}"
    st = json.load(open(f"{fin}/structure.json"))
    md = open(f"{fin}/document.md").read()
    ms = json.load(open(f"{ING}/marker/{pid}/structure.json"))
    bands = json.load(open(f"{ING}/marker/{pid}/bands.json"))
    row = man.get(pid, {})
    parts = []
    counts = {}

    # 1 metadata
    fields = [("paper_id", pid), ("doi", row.get("doi")), ("title", row.get("title")), ("authors", row.get("authors")),
              ("year", row.get("year")), ("journal", row.get("journal")), ("type", row.get("type")),
              ("in_scope", row.get("in_scope")), ("pdf_status", row.get("pdf_status")), ("pdf_source", row.get("pdf_source")),
              ("materials", row.get("materials")), ("processes", row.get("processes")), ("marker run", row.get("marker")),
              ("pages", ms.get("n_pages")), ("sources", ", ".join(f"{k}: {v}" for k, v in (st.get("sources") or {}).items()))]
    parts.append('<section data-sec="meta"><h2>1. Metadata (manifest)</h2><table class="kv">' +
                 "".join(f"<tr><th>{E(k)}</th><td>{E(v)}</td></tr>" for k, v in fields) + "</table></section>")

    # 2 abstract
    oa_abs = (oa.get(pid) or {}).get("abstract") or ""
    ours = st.get("abstract") or ""
    ow = words4(oa_abs)
    rec = f"{100 * len(ow & words4(ours)) / len(ow):.0f} % ({len(ow & words4(ours))} of {len(ow)} words of 4+ letters)" if ow else "no OpenAlex abstract"
    parts.append('<section data-sec="abstract"><h2>2. Abstract</h2>'
                 f'<p class="small">source: <b>{E(st.get("abstract_source"))}</b> · recall of the OpenAlex abstract: {E(rec)}</p>'
                 f'<div class="mdblock"><textarea class="mdsrc" hidden>{E(ours)}</textarea><div class="mdout"></div></div>'
                 + (f'<details><summary>OpenAlex abstract ({len(oa_abs)} characters)</summary><p>{E(oa_abs)}</p></details>' if oa_abs else "")
                 + "</section>")

    # 3 figures
    caps = st.get("captions") or []
    figs = [c for c in caps if c["kind"] == "figure" and c.get("number")]
    unnum = [c for c in caps if c["kind"] == "figure" and not c.get("number")]
    tabs = [c for c in caps if c["kind"] == "table"]
    counts["figures"] = len(figs)
    counts["unnumbered"] = len(unnum)
    h = [f'<section data-sec="figures"><h2>3. Figures ({len(figs)} numbered, {len(unnum)} unnumbered pictures)</h2>']
    for c in figs:
        imgs = "".join(img_tag(img_uri(f"{fin}/{p}"), "fig", p) for p in (c.get("images") or []))
        h.append(f'<div class="item" data-flag="0"><div class="ihead"><b>Figure {E(c["number"])}</b> · page {E(c.get("page"))} · {", ".join(E(os.path.basename(p)) for p in (c.get("images") or []))}</div>'
                 f'<div class="imgs">{imgs}</div><p class="cap">{E(c.get("caption"))}</p></div>')
    if unnum:
        h.append(f'<h3>Unnumbered pictures ({len(unnum)})</h3>')
        for c in unnum:
            imgs = "".join(img_tag(img_uri(f"{fin}/{p}"), "fig small", p) for p in (c.get("images") or []))
            h.append(f'<div class="item" data-flag="1"><div class="ihead">page {E(c.get("page"))} · {", ".join(E(os.path.basename(p)) for p in (c.get("images") or []))}</div>'
                     f'<div class="imgs">{imgs}</div>' + (f'<p class="cap">{E(c.get("caption"))}</p>' if c.get("caption") else "") + "</div>")
    referenced = {os.path.basename(p) for c in caps for p in (c.get("images") or [])} | {os.path.basename(c.get("crop") or "") for c in tabs}
    referenced |= {os.path.basename(f.get("crop") or "") for f in st.get("body_flags") or []}
    stray = sorted(f for f in os.listdir(f"{fin}/figures") if f not in referenced and not f.startswith("body_p") and not f.startswith("table_"))
    if stray:
        h.append(f'<h3>Images in figures/ bound to no entry ({len(stray)})</h3>')
        for f in stray:
            h.append(f'<div class="item" data-flag="1"><div class="ihead">{E(f)}</div><div class="imgs">{img_tag(img_uri(f"{fin}/figures/{f}"), "fig small", f)}</div></div>')
    counts["stray"] = len(stray)
    h.append("</section>")
    parts.append("".join(h))

    # 4 tables
    counts["tables"] = len(tabs)
    counts["tables_flag"] = sum(1 for t in tabs if t.get("check") == "flag")
    counts["tables_nc"] = sum(1 for t in tabs if t.get("check") == "not checkable")
    h = [f'<section data-sec="tables"><h2>4. Tables ({len(tabs)}; flagged {counts["tables_flag"]}, not checkable {counts["tables_nc"]})</h2>']
    seen = collections.Counter()
    for t in tabs:
        k = (str(t.get("page")), t.get("number"))
        ordinal = seen[k]
        seen[k] += 1
        a = ans["tables"].get((pid, str(t.get("page")), t.get("number"), ordinal))
        chk = t.get("check") or "?"
        cls = {"ok": "ok", "flag": "flag", "not checkable": "nc"}.get(chk, "nc")
        reasons = "; ".join(t.get("check_reasons") or [])
        detail = t.get("check_detail") or {}
        label = f"Table {t['number']}" if t.get("number") else "Unnumbered table"
        anstag = (f'<span class="ans">answer set: <b>{E(a["verdict"])}</b>' + (f' — {E(a["error_type"])}' if a.get("error_type") else "") +
                  f' <i>({E(a["judged_by"])}, {E(a["judged_on"])}, {E(a["date"])})</i></span>') if a else '<span class="ans none">answer set: no judgement</span>'
        h.append(f'<div class="item" data-flag="{0 if chk == "ok" else 1}"><div class="ihead"><b>{E(label)}</b> · page {E(t.get("page"))} · '
                 f'<span class="chk {cls}">{E(chk)}</span> {E(reasons)} {anstag}</div>'
                 f'<p class="cap">{E(t.get("caption"))}</p>'
                 f'<div class="two"><div class="mdblock"><textarea class="mdsrc" hidden>{E(t.get("table") or "")}</textarea><div class="mdout"></div>'
                 f'<details><summary>raw markdown</summary><pre>{E(t.get("table") or "")}</pre></details>'
                 + (f'<details><summary>check detail</summary><pre>{E(json.dumps(detail, ensure_ascii=False, indent=1))}</pre></details>' if detail else "")
                 + f'</div><div>{img_tag(img_uri(fin + "/" + t["crop"]) if t.get("crop") else None, "crop", t.get("crop") or "")}</div></div></div>')
    h.append("</section>")
    parts.append("".join(h))

    # 5 equations
    eqs = st.get("equations") or []
    counts["equations"] = len(eqs)
    counts["eq_notagree"] = sum(1 for e in eqs if e.get("status") != "agree")
    h = [f'<section data-sec="equations"><h2>5. Equations ({len(eqs)}; not agree {counts["eq_notagree"]})</h2>']
    for e in eqs:
        stt = e.get("status") or "?"
        cls = {"agree": "ok", "differ": "flag"}.get(stt, "nc")
        a = ans["equations"].get((pid, str(e.get("page")), str(e.get("number"))))
        anstag = (f'<span class="ans">answer set: <b>{E(a["verdict"])}</b>' + (f' — {E(a["note"])}' if a.get("note") and a["note"] != "page" else "") +
                  (f' [status then: {E(a["status"])}]' if a.get("status") != stt else "") +
                  f' <i>({E(a["judged_by"])}, {E(a["judged_on"])}, {E(a["date"])})</i></span>') if a else ""
        crop = pdf_crop_uri(pid, int(e["page"]), e["bbox"]) if e.get("bbox") else None
        d, m = e.get("docling"), e.get("marker")
        h.append(f'<div class="item" data-flag="{0 if stt == "agree" else 1}"><div class="ihead"><b>Eq. {E(e.get("number") or "—")}</b> · page {E(e.get("page"))} · '
                 f'<span class="chk {cls}">{E(stt)}</span> {anstag}</div>'
                 f'<div class="eqrow"><div class="eqcrop">{img_tag(crop, "crop", "crop")}</div>'
                 f'<div class="eqtool"><div class="tl">Docling</div>' + (f'<div class="ktx" data-tex="{E(d)}"></div><pre>{E(d)}</pre>' if d else '<span class="noimg">none</span>') +
                 f'</div><div class="eqtool"><div class="tl">Marker</div>' + (f'<div class="ktx" data-tex="{E(m)}"></div><pre>{E(m)}</pre>' if m else '<span class="noimg">none</span>') +
                 "</div></div></div>")
    h.append("</section>")
    parts.append("".join(h))

    # 6 body text
    flags = st.get("body_flags") or []
    repairs = st.get("body_repairs") or []
    bc = st.get("body_check") or {}
    cnt = bc.get("counts") or {}
    counts["body_flags"] = sum(1 for f in flags if f["kind"] != "not checkable")
    counts["body_nc_flags"] = sum(1 for f in flags if f["kind"] == "not checkable")
    counts["body_repairs"] = len(repairs)
    counts["body_repairs_undone"] = len(st.get("body_repairs_undone") or [])
    counts["body_lines"] = cnt.get("lines", 0)
    counts["body_checked"] = cnt.get("checked", 0)
    amd, notes, rnotes = annotate_markdown(md, flags, repairs, ans["body_flags"], pid)
    cov = f'{100 * cnt.get("checked", 0) / cnt["lines"]:.0f} %' if cnt.get("lines") else "n/a"
    ln = bc.get("line_numbers") or {}
    h = [f'<section data-sec="body"><h2>6. Body text (document.md; {counts["body_flags"]} body flags, {counts["body_nc_flags"]} not-checkable flags, {len(repairs)} rule repairs, {counts["body_repairs_undone"]} undone; '
         f'{cnt.get("checked", 0)} of {cnt.get("lines", 0)} body lines checked = {cov})</h2>']
    h.append('<details class="small"><summary>body_check counts and not-checkable reasons</summary><pre>' + E(json.dumps(bc, ensure_ascii=False, indent=1)) + "</pre></details>")
    if ln.get("removed"):
        h.append(f'<p class="small">margin line numbers removed: {ln["removed"]} on {ln.get("pages")} pages ({ln.get("kept_real")} real numbers kept)</p>')
    h.append('<div class="bodywrap"><div class="doc mdblock"><div class="tools"><label><input type="checkbox" class="rawtoggle"> show raw markdown</label></div>'
             f'<textarea class="mdsrc" hidden>{E(amd)}</textarea><div class="mdout"></div><pre class="raw" hidden>{E(md)}</pre></div>')
    h.append('<div class="notes"><h3>Flags and repairs</h3>')
    if not notes and not rnotes:
        h.append('<p class="small">none</p>')
    for n in notes:
        f = n["f"]
        a = n["ans"]
        crop = img_uri(f"{fin}/{f['crop']}") if f.get("crop") else None
        anstag = (f'<div class="ans">answer set: <b>{E(a["verdict"])}</b>' +
                  (f' — {E(a.get("error_type"))}; cause: {E(a.get("cause"))}' if a["verdict"] == "real error" else f' — {E(a.get("measurement_cause"))}' + (f'; fixable: {E(a.get("fixable"))}' if a.get("fixable") not in (None, "") else "")) +
                  f' <i>({E(a["judged_by"])}, {E(a["judged_on"])}, {E(a["date"])})</i></div>') if a else '<div class="ans none">answer set: no judgement</div>'
        h.append(f'<div class="note{" nc" if n.get("nc") else ""}" data-f="{n["id"]}" data-flag="1"><div class="nh"><a class="fb{" nc" if n.get("nc") else ""}" href="#{pid}-{n["id"]}">{"NC" if n.get("nc") else "⚑" + n["id"][1:]}</a> <b>{E(n["label"])}</b> · page {E(f.get("page"))}' + (f' · {E(f.get("lines"))} line(s), block {E(f.get("block"))}' if n.get("nc") else "") + '</div>'
                 f'<div class="small">text-layer line: “{E(f.get("layer_line"))}”' + (f'<br>context: “{E(f.get("layer_context"))}”' if f.get("layer_context") else "") +
                 f'<br>numbers in the layer line: {E(", ".join(f.get("layer_numbers") or []) or "—")}; in the output sentence: {E(", ".join(f.get("output_numbers") or []) or "—")}' +
                 (f'<br>output sentence: “{E(f.get("output_sentence"))}”' if f.get("output_sentence") else "") +
                 (f'<br>block: {E(f.get("block"))}, {E(f.get("words"))} words, undecoded: {E(f.get("undecoded"))}' if f.get("block") else "") +
                 f'</div>{img_tag(crop, "crop", "line crop")}{anstag}</div>')
    for u in st.get("body_repairs_undone") or []:
        h.append(f'<div class="note rep" data-f="undone" data-flag="1"><div class="nh"><a class="fb rep">R?</a> <b>repair undone by the recheck</b> · page {E(u.get("page"))}</div>'
                 f'<div class="small">{E(u.get("kind"))}' + (f'<br>from “{E(u["from"])}” to “{E(u["to"])}”' if u.get("from") else f'<br>line: “{E(u.get("to"))}”') +
                 f'<br>remaining flag: {E(u["remaining_flag"]["kind"])} {E(u["remaining_flag"].get("number"))}</div></div>')
    for n in rnotes:
        r = n["r"]
        h.append(f'<div class="note rep" data-f="{n["id"]}" data-flag="1"><div class="nh"><a class="fb rep" href="#{pid}-{n["id"]}">{E(n["id"][:1].upper() + ("1" if n["id"] in [x["id"] for x in rnotes if x["label"].startswith("R1")] else "2"))}</a> <b>{E(n["label"])}</b> · page {E(r.get("page"))}</div>'
                 f'<div class="small">{E(r.get("kind"))}' + (f'<br>from “{E(r["from"])}” to “{E(r["to"])}”' if r.get("from") else f'<br>restored: “{E(r.get("to"))}”') +
                 (f'<br>sentence: “{E(r["sentence"])}”' if r.get("sentence") else "") + "</div></div>")
    h.append("</div></div></section>")
    parts.append("".join(h))

    # 7 bands and known errors
    counts["bands"] = len(bands)
    counts["bands_applied"] = sum(1 for b in bands if b.get("applied"))
    h = [f'<section data-sec="bands"><h2>7. Band repairs ({len(bands)}, applied {counts["bands_applied"]}) and known errors</h2>']
    for b in bands:
        png = f"{ING}/marker/{pid}/{b.get('png')}" if b.get("png") else None
        crop = img_uri(png) if png and os.path.exists(png) else None
        h.append(f'<div class="item" data-flag="1"><div class="ihead"><b>{E(b.get("trigger"))}</b> {E(b.get("label"))} · page {E(b.get("page"))} · block {E(b.get("block"))} · '
                 f'applied: {E(b.get("applied"))} · in document.md: {E(b.get("in_markdown", "?"))}</div>'
                 f'<div class="two"><div><p class="small">OCR text: “{E(b.get("text"))}”</p>' + (f'<p class="small">note: {E(b["note"])}</p>' if b.get("note") else "") +
                 f'</div><div>{img_tag(crop, "crop", "band") if crop else "<span class=noimg>no crop stored" + (" (record rebuilt from the band_ocr mark)" if b.get("note") else "") + "</span>"}</div></div></div>')
    errs = errors_for(err_tables, pid)
    counts["errors"] = sum(len(r) for _, _, r in errs)
    h.append(f'<h3>Known errors of this paper in ERRORS.md ({counts["errors"]} rows)</h3>')
    for sec, header, rows in errs:
        h.append(f'<p class="small"><b>{E(sec)}</b></p><table class="err"><tr>' + "".join(f"<th>{md_inline(c)}</th>" for c in header) + "</tr>" +
                 "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>")
    if not errs:
        h.append('<p class="small">no row names this paper</p>')
    h.append("</section>")
    parts.append("".join(h))
    return "".join(parts), counts, row


CSS = """
:root{--bg:#fff;--fg:#1c1c1c;--mut:#666;--line:#ddd;--flag:#c8201b;--ok:#2a7a2a;--nc:#777;--ans:#6a2fa8;--rep:#b36b00}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,Segoe UI,Roboto,sans-serif;color:var(--fg);background:var(--bg)}
header{position:sticky;top:0;background:#fafafa;border-bottom:1px solid var(--line);padding:8px 16px;z-index:5;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
header h1{font-size:16px;margin:0 8px 0 0}main{padding:12px 16px 60px}select{max-width:60vw}
table{border-collapse:collapse}#index td,#index th,table.err td,table.err th,table.kv td,table.kv th{border:1px solid var(--line);padding:3px 6px;vertical-align:top;font-size:13px}
#index th{background:#f3f3f3;position:sticky;top:46px;cursor:pointer}#index tr:hover td{background:#f7f3ff}#index td.num{text-align:right}#index tr{cursor:pointer}
table.kv th{text-align:left;background:#f7f7f7;white-space:nowrap}
section{border-top:2px solid var(--line);margin-top:18px;padding-top:6px}h2{font-size:15px;margin:6px 0}h3{font-size:14px;margin:12px 0 4px;color:var(--mut)}
.item{border:1px solid var(--line);border-radius:4px;padding:6px 8px;margin:8px 0;background:#fff}.ihead{font-size:13px;margin-bottom:4px}.cap{margin:4px 0;font-size:13px}
.imgs img{max-width:100%;height:auto;display:block;margin:4px 0}img.small{max-width:300px}img.crop{max-width:100%;height:auto;border:1px solid var(--line)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.eqrow{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}.eqtool .tl{font-size:12px;color:var(--mut)}
pre{white-space:pre-wrap;word-break:break-word;font-size:12px;background:#f7f7f7;padding:4px 6px;margin:4px 0;border-radius:3px}
.chk{padding:0 6px;border-radius:3px;color:#fff;font-size:12px}.chk.ok{background:var(--ok)}.chk.flag{background:var(--flag)}.chk.nc{background:var(--nc)}
.ans{display:inline-block;border:1px dashed var(--ans);color:var(--ans);padding:0 6px;border-radius:3px;font-size:12px;margin:2px 0;background:#faf6ff}.ans.none{opacity:.6}
.small{font-size:12px;color:var(--mut)}.noimg{color:var(--mut);font-style:italic;font-size:12px}
.mdout table{border-collapse:collapse;margin:6px 0}.mdout td,.mdout th{border:1px solid var(--line);padding:2px 6px;font-size:13px}
.mdout img{max-width:100%}.mdout h1,.mdout h2,.mdout h3{font-size:14px;margin:12px 0 4px;color:var(--fg);border:0}
.bodywrap{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:16px}.notes{position:sticky;top:50px;align-self:start;max-height:calc(100vh - 60px);overflow:auto;border-left:1px solid var(--line);padding-left:10px}
.note{border:1px solid var(--line);border-left:4px solid var(--flag);padding:4px 6px;margin:6px 0;font-size:13px}.note.rep{border-left-color:var(--rep)}.note.nc{border-left-color:var(--nc)}a.fb.nc{background:var(--nc)}.note.hl{background:#fff3e0}
.note .ans{display:block}.note img.crop{margin:4px 0}
a.fb{display:inline-block;background:var(--flag);color:#fff;font-size:11px;padding:0 4px;border-radius:3px;text-decoration:none;cursor:pointer;margin:0 2px;vertical-align:middle}
a.fb.rep{background:var(--rep)}mark.flag{background:#ffd9d6}mark.rep{background:#ffe6bf}mark.hl{outline:2px solid var(--flag)}.fbline{font-size:12px;color:var(--flag)}.fbl{color:var(--flag);font-size:12px}
.hid{display:none!important}.dim{display:none!important}.katex-display{margin:4px 0}.ktx{overflow-x:auto}.tools{font-size:12px;color:var(--mut)}
#status{font-size:12px;color:var(--mut)}label{font-size:13px}.filters label{margin-right:8px}
@media (max-width:900px){.bodywrap{grid-template-columns:1fr}.notes{position:static;max-height:none}.eqrow,.two{grid-template-columns:1fr}}
"""

JS = r"""
const MATH=[];function protect(md){MATH.length=0;return md.replace(/\$\$[\s\S]+?\$\$|\$(?!\s)[^$\n]{1,400}?(?<!\s)\$/g,(m)=>{MATH.push(m);return ""+(MATH.length-1)+"";});}
function restore(h){return h.replace(/(\d+)/g,(_,i)=>{const m=MATH[+i];const disp=m.startsWith("$$");const tex=disp?m.slice(2,-2):m.slice(1,-1);return '<span class="ktx'+(disp?' disp':'')+'" data-tex="'+tex.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;")+'"></span>';});}
function renderMd(src){if(!window.marked)return "<pre>"+src.replace(/[&<]/g,c=>({"&":"&amp;","<":"&lt;"}[c]))+"</pre>";try{return restore(marked.parse(protect(src),{gfm:true,breaks:false,mangle:false,headerIds:false}));}catch(e){return "<pre>"+src.replace(/[&<]/g,c=>({"&":"&amp;","<":"&lt;"}[c]))+"</pre>";}}
function fixTex(t){return (/(^|[^\\])&|\\\\/.test(t)&&!/\\begin\{/.test(t))?"\\begin{aligned}"+t+"\\end{aligned}":t;}
function renderKatex(root){if(!window.katex)return;root.querySelectorAll(".ktx").forEach(el=>{if(el.dataset.done)return;el.dataset.done=1;try{katex.render(fixTex(el.dataset.tex),el,{throwOnError:false,displayMode:el.classList.contains("disp")||el.parentElement.classList.contains("eqtool"),strict:"ignore"});}catch(e){el.textContent=el.dataset.tex;}});}
function show(i){const tpl=document.getElementById("tpl-"+i);const main=document.getElementById("paper");main.innerHTML="";if(!tpl)return;main.appendChild(tpl.content.cloneNode(true));
 document.getElementById("sel").value=i;document.getElementById("index").classList.add("hid");document.getElementById("paper").classList.remove("hid");
 main.querySelectorAll(".mdblock").forEach(b=>{const ta=b.querySelector(".mdsrc");const out=b.querySelector(".mdout");out.innerHTML=renderMd(ta.value);});
 renderKatex(main);
 main.querySelectorAll(".rawtoggle").forEach(cb=>cb.addEventListener("change",()=>{const d=cb.closest(".doc");d.querySelector(".raw").hidden=!cb.checked;d.querySelector(".mdout").hidden=cb.checked;}));
 main.querySelectorAll("a.fb[data-f]").forEach(a=>{a.addEventListener("mouseenter",()=>hl(a.dataset.f,true));a.addEventListener("mouseleave",()=>hl(a.dataset.f,false));a.addEventListener("click",ev=>{ev.preventDefault();const n=main.querySelector('.note[data-f="'+a.dataset.f+'"]');if(n)n.scrollIntoView({block:"center"});});});
 main.querySelectorAll(".note[data-f]").forEach(n=>{n.addEventListener("mouseenter",()=>hl(n.dataset.f,true));n.addEventListener("mouseleave",()=>hl(n.dataset.f,false));n.querySelector("a.fb").addEventListener("click",ev=>{ev.preventDefault();const b=main.querySelector('a.fb[data-f="'+n.dataset.f+'"]');if(b)b.scrollIntoView({block:"center"});});});
 applyFilters();location.hash="p"+i;window.scrollTo(0,0);}
function hl(f,on){document.querySelectorAll('.note[data-f="'+f+'"],mark[data-f~="'+f+'"]').forEach(e=>e.classList.toggle("hl",on));}
function showIndex(){document.getElementById("index").classList.remove("hid");document.getElementById("paper").classList.add("hid");document.getElementById("sel").value="";location.hash="";}
function applyFilters(){const fo=document.getElementById("flagonly").checked;const types={};document.querySelectorAll(".filters input[data-sec]").forEach(c=>types[c.dataset.sec]=c.checked);
 const main=document.getElementById("paper");main.querySelectorAll("section[data-sec]").forEach(s=>s.classList.toggle("hid",!types[s.dataset.sec]));
 main.querySelectorAll(".item[data-flag], .note[data-flag]").forEach(it=>it.classList.toggle("dim",fo&&it.dataset.flag==="0"));
 main.querySelectorAll(".doc .mdout").forEach(doc=>{Array.from(doc.children).forEach(ch=>{const has=ch.querySelector("a.fb,mark")||ch.matches("mark,a.fb");ch.classList.toggle("dim",fo&&!has);});});}
function sortIndex(col){const tb=document.querySelector("#index tbody");const rows=Array.from(tb.rows);const dir=(tb.dataset.col==col&&tb.dataset.dir=="1")?-1:1;tb.dataset.col=col;tb.dataset.dir=dir;
 rows.sort((a,b)=>{const x=a.cells[col].dataset.v??a.cells[col].textContent,y=b.cells[col].dataset.v??b.cells[col].textContent;const nx=parseFloat(x),ny=parseFloat(y);if(!isNaN(nx)&&!isNaN(ny))return dir*(nx-ny);return dir*x.localeCompare(y);});rows.forEach(r=>tb.appendChild(r));}
document.addEventListener("DOMContentLoaded",()=>{document.getElementById("sel").addEventListener("change",e=>{if(e.target.value==="")showIndex();else show(+e.target.value);});
 document.querySelectorAll(".filters input").forEach(c=>c.addEventListener("change",applyFilters));
 document.querySelectorAll("#index tbody tr").forEach(r=>r.addEventListener("click",()=>show(+r.dataset.i)));
 document.querySelectorAll("#index th").forEach((th,i)=>th.addEventListener("click",()=>sortIndex(i)));
 document.getElementById("status").textContent=(window.marked?"marked ":"marked missing (raw text shown) ")+(window.katex?"· KaTeX":"· KaTeX missing (LaTeX shown raw)");
 const m=location.hash.match(/^#p(\d+)$/);if(m)show(+m[1]);});
"""

HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11/katex.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11/katex.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<style>{css}</style></head><body>"""


def main():
    man = {r["paper_id"]: r for r in csv.DictReader(open(f"{ROOT}/corpus/manifest.csv")) if r.get("paper_id")}
    pids = sorted(p for p in man if os.path.isdir(f"{ING}/final/{p}"))
    if os.environ.get("ONLY"):
        pids = [p for p in pids if p in os.environ["ONLY"].split(",")]
    oa = json.load(open(f"{ROOT}/corpus/openalex_abstracts.json"))["papers"]
    A = {"tables": {}, "equations": {}, "body_flags": {}}
    for t in json.load(open(f"{ING}/answers/tables.json"))["items"]:
        A["tables"][(t["paper_id"], str(t["page"]), t["table"], t["ordinal"])] = t
    for e in json.load(open(f"{ING}/answers/equations.json"))["items"]:
        A["equations"][(e["paper_id"], str(e["page"]), str(e["number"]))] = e
    for f in json.load(open(f"{ING}/answers/body_flags.json"))["items"]:
        A["body_flags"][f["flag_key"]] = f
    err_tables = parse_errors_md(f"{ING}/ERRORS.md")

    papers = []
    for i, pid in enumerate(pids):
        body, counts, row = build_paper(pid, man, oa, A, err_tables)
        papers.append((pid, body, counts, row))
        print(f"{i + 1:2d}/{len(pids)} {pid} {len(body) / 1e6:.1f} MB", file=sys.stderr, flush=True)

    tot = collections.Counter()
    for _, _, c, _ in papers:
        for k, v in c.items():
            tot[k] += v
    cols = ["#", "paper_id", "title", "year", "journal", "figures", "unnumbered", "tables", "equations", "tables flagged", "eq. not agree", "body flags", "not-checkable flags", "band repairs (applied)", "body repairs", "body check coverage"]
    idx = ['<div id="index"><table><thead><tr>' + "".join(f"<th>{E(c)}</th>" for c in cols) + "</tr></thead><tbody>"]
    for i, (pid, _, c, row) in enumerate(papers):
        cov = 100 * c["body_checked"] / c["body_lines"] if c["body_lines"] else 0
        cells = [i + 1, pid, row.get("title"), row.get("year"), row.get("journal"), c["figures"], c["unnumbered"], c["tables"], c["equations"],
                 c["tables_flag"], c["eq_notagree"], c["body_flags"], c["body_nc_flags"], f'{c["bands_applied"]} / {c["bands"]}', c["body_repairs"], f"{cov:.0f} %"]
        idx.append(f'<tr data-i="{i}">' + "".join(f'<td class="{"num" if isinstance(v, (int, float)) or (isinstance(v, str) and v[:1].isdigit() and j > 4) else ""}" data-v="{E(v)}">{E(v)}</td>' for j, v in enumerate(cells)) + "</tr>")
    idx.append("</tbody></table></div>")
    summary = (f'{len(papers)} papers · figures {tot["figures"]} (+{tot["unnumbered"]} unnumbered) · tables {tot["tables"]} ({tot["tables_flag"]} flagged, {tot["tables_nc"]} not checkable) · '
               f'equations {tot["equations"]} ({tot["eq_notagree"]} not agree) · body flags {tot["body_flags"]} (+{tot["body_nc_flags"]} not checkable) · band repairs {tot["bands_applied"]} applied of {tot["bands"]} · body repairs {tot["body_repairs"]} · '
               f'body lines checked {tot["body_checked"]} of {tot["body_lines"]}')
    sel = '<select id="sel"><option value="">— index —</option>' + "".join(f'<option value="{i}">{E(p)} — {E((r.get("title") or "")[:70])}</option>' for i, (p, _, _, r) in enumerate(papers)) + "</select>"
    filters = ('<span class="filters"><label><input type="checkbox" id="flagonly"> flagged items only</label> | types: ' +
               " ".join(f'<label><input type="checkbox" data-sec="{s}" checked> {n}</label>' for s, n in
                        [("meta", "metadata"), ("abstract", "abstract"), ("figures", "figures"), ("tables", "tables"), ("equations", "equations"), ("body", "body text"), ("bands", "bands + known errors")]) + "</span>")
    head = HEAD.format(title="Ingest output by paper", css=CSS)
    header = (f'<header><h1>Ingest output by paper</h1>{sel}{filters}<span id="status"></span><span class="small">{E(summary)} · built {datetime.date.today().isoformat()} from ingest/final, marker, docling, answers, ERRORS.md · '
              '<span class="ans">answer set</span> = Claude Code\'s page judgements, not pipeline output</span></header>')
    tpls = []
    for i, (pid, body, c, row) in enumerate(papers):
        tpls.append(f'<template id="tpl-{i}"><h2 class="ptitle"><a href="#" onclick="showIndex();return false">← index</a> · {E(pid)} — {E(row.get("title"))}</h2>{body}</template>')
    single = head + header + '<main>' + "".join(idx) + '<div id="paper" class="hid"></div></main>' + "".join(tpls) + f"<script>{JS}</script></body></html>"
    size = len(single.encode())
    print(f"single file would be {size / 1e6:.1f} MB", file=sys.stderr)
    if size <= LIMIT:
        with open(f"{OUT_DIR}/papers.html", "w") as fh:
            fh.write(single)
        print(f"wrote {OUT_DIR}/papers.html {size / 1e6:.1f} MB")
    else:
        os.makedirs(f"{OUT_DIR}/papers", exist_ok=True)
        for i, (pid, body, c, row) in enumerate(papers):
            page = (head + f'<header><h1><a href="../papers.html">← index</a> · {E(pid)}</h1>{filters}<span id="status"></span></header><main><div id="index" class="hid"></div><div id="paper"></div></main>'
                    f'<template id="tpl-0"><h2 class="ptitle">{E(pid)} — {E(row.get("title"))}</h2>{body}</template><script>{JS}\ndocument.addEventListener("DOMContentLoaded",()=>show(0));</script></body></html>')
            with open(f"{OUT_DIR}/papers/{pid}.html", "w") as fh:
                fh.write(page)
        idx2 = "".join(idx).replace('<tr data-i="', '<tr onclick="location.href=\'papers/\'+this.dataset.pid+\'.html\'" data-i="')
        for i, (pid, _, _, _) in enumerate(papers):
            idx2 = idx2.replace(f'data-i="{i}">', f'data-i="{i}" data-pid="{E(pid)}">', 1)
        with open(f"{OUT_DIR}/papers.html", "w") as fh:
            fh.write(head + header.replace(sel, "") + "<main>" + idx2 + "</main></body></html>")
        print(f"wrote {OUT_DIR}/papers.html (index) and {len(papers)} files in {OUT_DIR}/papers/ ({size / 1e6:.1f} MB in all)")
    print(json.dumps(dict(tot)))


if __name__ == "__main__":
    main()
