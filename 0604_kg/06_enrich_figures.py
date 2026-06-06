import re,json
from pathlib import Path
from config import OUTPUT_DIR,STEP

def load_json(p):
    with open(p,"r",encoding="utf-8") as f:return json.load(f)

def save_json(obj,p):
    with open(p,"w",encoding="utf-8") as f:json.dump(obj,f,indent=2,ensure_ascii=False)

def get_figure_no(fig):
    cap=fig.get("caption") or ""
    m=re.search(r"\bfig(?:ure)?\.?\s*(\d+)",cap,re.I)
    return int(m.group(1)) if m else None

def resolve_ref(doc,ref):
    m=re.match(r"#/(\w+)/(\d+)",ref)
    if not m:return None,None,None
    kind=m.group(1)
    idx=int(m.group(2))
    return kind,doc[kind][idx],idx

def build_units(doc):
    units=[]
    eq_idx=0

    for child in doc["body"]["children"]:
        ref=child.get("$ref")
        if not ref:continue

        kind,obj,idx=resolve_ref(doc,ref)
        if not kind:continue

        if kind=="texts":
            label=obj.get("label","")
            text=(obj.get("text") or "").strip()

            if label=="formula":
                eq_idx+=1
                units.append({
                    "type":"formula",
                    "equation_index":eq_idx,
                    "text":f"[EQUATION_{eq_idx:04d}]"
                })

            elif text:
                units.append({
                    "type":label,
                    "text":text
                })

        elif kind=="pictures":
            units.append({
                "type":"figure",
                "figure_index":idx,
                "text":f"[FIGURE_{idx:03d}]"
            })

        elif kind=="tables":
            units.append({
                "type":"table",
                "table_index":idx,
                "text":f"[TABLE_{idx:03d}]"
            })

    return units

# def is_caption_text(text):
#     return bool(re.match(r"^\s*(fig(?:ure)?|table)\.?\s*\d+",text,re.I))

def is_caption_text(u: dict) -> bool:
    return u.get("type") == "caption"

# def collect_context(units,i,window=5):
#     start=max(0,i-window)
#     end=min(len(units),i+window+1)

#     chunks=[]

#     for u in units[start:end]:
#         if u["type"]=="page_header":continue
#         if u["type"]=="page_footer":continue

#         txt=u.get("text","").strip()
#         if not txt:continue

#         chunks.append(txt)

#     return "\n".join(chunks)

SKIP_TYPES = {"page_header", "page_footer", "caption"}
BREAK_TYPES = {"section_header", "figure", "table"}  # 문단 경계

def collect_paragraph(units, i):
    """hit unit(i)을 포함하는 연속 text 블록만 반환 (figure/section_header/table에서 끊김)"""
    # 앞쪽: BREAK_TYPES 만나면 중단, SKIP_TYPES는 건너뜀
    start = i
    for j in range(i - 1, -1, -1):
        t = units[j]["type"]
        if t in BREAK_TYPES:
            break
        if t not in SKIP_TYPES:
            start = j

    # 뒤쪽: BREAK_TYPES 만나면 중단
    end = i
    for j in range(i + 1, len(units)):
        t = units[j]["type"]
        if t in BREAK_TYPES:
            break
        if t not in SKIP_TYPES:
            end = j

    chunks = []
    for u in units[start:end + 1]:
        if u["type"] in SKIP_TYPES | BREAK_TYPES | {"figure"}:
            continue
        txt = u.get("text", "").strip()
        if txt and len(txt) > 3:
            chunks.append(txt)
    return "\n".join(chunks)


def find_contexts(units, fig_no):
    fig_ctx = []
    sub_ctx = {}
    fig_pat = re.compile(
        rf"\bfig(?:ure)?\.?\s*{fig_no}(?![0-9])",
        re.I
    )

    for i, u in enumerate(units):
        if u["type"] == "figure":
            continue
        txt = u.get("text", "")

        if is_caption_text(u):
            continue

        if fig_pat.search(txt):
            ctx = txt.strip()
            if ctx and ctx not in fig_ctx:
                fig_ctx.append(ctx)

            # 패턴 1: Fig. 9 (panels a-c) → a, b, c 전부
            for m in re.finditer(
                rf"\bfig(?:ure)?\.?\s*{fig_no}\s*\(panels\s+([a-z])-([a-z])\)",
                ctx, re.I
            ):
                start_s = m.group(1).lower()
                end_s   = m.group(2).lower()
                for s in [chr(c) for c in range(ord(start_s), ord(end_s) + 1)]:
                    sub_ctx.setdefault(s, []).append(ctx)

            # 패턴 2: Fig. 9 (a) 또는 Fig. 9a
            for m in re.finditer(
                rf"\bfig(?:ure)?\.?\s*{fig_no}\s*(?:\(\s*([a-z])\s*\)|([a-z])\b)",
                ctx, re.I
            ):
                s = (m.group(1) or m.group(2)).lower()
                sub_ctx.setdefault(s, []).append(ctx)

    return fig_ctx, sub_ctx

def process_paper(paper_dir):
    doc_json=paper_dir/STEP["01"]/"document.json"
    figs_json=paper_dir/STEP["01"]/"figures"/"figures.json"
    plot_dir=paper_dir/STEP["03"]
    out_dir=paper_dir/STEP["06"]

    if not doc_json.exists() or not figs_json.exists() or not plot_dir.exists():
        return

    out_dir.mkdir(parents=True,exist_ok=True)

    doc=load_json(doc_json)
    units=build_units(doc)

    figures=load_json(figs_json)
    fig_map={f["figure_index"]:f for f in figures}

    plot_files=sorted(plot_dir.glob("figure-*.json"))

    # 이 부분을 교체
    PANEL_LETTERS = "abcdefghijklmnopqrstuvwxyz"

    for plot_file in plot_files:
        m=re.search(r"figure-(\d+)\.json",plot_file.name)
        if not m:continue

        idx=int(m.group(1))
        fig=fig_map.get(idx)

        if not fig:continue

        fig_no=get_figure_no(fig)
        if fig_no is None:continue

        fig_ctx,sub_ctx=find_contexts(units,fig_no)

        pdata=load_json(plot_file)

        # list → 패널별 분리, dict → 단일 패널로 통일
        if isinstance(pdata,dict):
            pdata=[pdata]
        if not pdata:
            continue

        for panel_i,panel in enumerate(pdata):
            panel_letter=PANEL_LETTERS[panel_i]
            meta=panel.get("metadata",{})

            # 패널이 1개면 letter 없이, 여러 개면 letter 붙임
            if len(pdata)==1:
                figure_id=f"figure-{idx:03d}"
                out_name=f"figure-{idx:03d}.json"
            else:
                figure_id=f"figure-{idx:03d}{panel_letter}"
                out_name=f"figure-{idx:03d}{panel_letter}.json"

            enriched={
                "figure_id":figure_id,
                "figure_index":idx,
                "panel":panel_letter if len(pdata)>1 else None,
                "figure_no":fig_no,
                "title":meta.get("title",""),
                "caption":fig.get("caption"),
                "page_nos":fig.get("page_nos",[]),
                "image_path":fig.get("image_path"),
                "plot_data_path":str(plot_file),
                "series":[d.get("series","") for d in panel.get("data",[])],
                "figure_contexts":fig_ctx,
                "subfigure_contexts":sub_ctx.get(panel_letter,[]) if len(pdata)>1 else sub_ctx,
            }

            save_json(enriched,out_dir/out_name)
            print("[PROCESS]",figure_id,plot_file.name)

def main():
    for paper_dir in OUTPUT_DIR.iterdir():
        if paper_dir.is_dir():
            process_paper(paper_dir)

if __name__=="__main__":
    main()