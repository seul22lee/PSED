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

def is_caption_text(text):
    return bool(re.match(r"^\s*(fig(?:ure)?|table)\.?\s*\d+",text,re.I))

def collect_context(units,idx,window=5):
    out=[]
    start=max(0,idx-window)
    end=min(len(units),idx+window+1)

    for j in range(start,end):
        if j==idx:
            out.append(units[j].get("text",""))
            continue

        if units[j].get("type")=="figure":
            continue

        txt=units[j].get("text","").strip()
        if not txt:
            continue

        out.append(txt)

    return "\n".join(out)

def find_contexts(units,fig_no):
    fig_ctx=[]
    sub_ctx={}

    fig_pat=re.compile(rf"\bfig(?:ure)?\.?\s*{fig_no}\b",re.I)

    for i,u in enumerate(units):

        # if u["type"]=="figure":
        #     continue

        txt=u.get("text","")

        # if is_caption_text(txt):
        #     continue

        if fig_pat.search(txt):
            print("MATCHED")
            print(txt[:300])

            ctx=collect_context(units,i,window=8)

            print("CTX>>>")
            print(repr(ctx[:500] if ctx else ctx))

            ctx=collect_context(units,i)

            if ctx not in fig_ctx:
                fig_ctx.append(ctx)

            for s in "abcdefghijklmnopqrstuvwxyz":
                if re.search(rf"\bfig(?:ure)?\.?\s*{fig_no}\s*\(\s*{s}\s*\)",ctx,re.I):
                    sub_ctx.setdefault(s,[]).append(ctx)

    return fig_ctx,sub_ctx

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

    for plot_file in plot_files:
        m=re.search(r"figure-(\d+)\.json",plot_file.name)
        if not m:continue

        idx=int(m.group(1))
        fig=fig_map.get(idx)

        if not fig:continue

        fig_no=get_figure_no(fig)
        if fig_no is None:continue

        print("="*80)
        print("FIG:",fig_no)

        hits=0
        for u in units:
            txt=u.get("text","")
            if str(fig_no) in txt:
                print(txt[:300])
                hits+=1

        print("HITS:",hits)

        fig_ctx,sub_ctx=find_contexts(units,fig_no)

        print("FIG_CTX_LEN",len(fig_ctx))

        for i,x in enumerate(fig_ctx[:5]):
            print("="*80)
            print(i)
            print(x[:1000])

        pdata=load_json(plot_file)

        if isinstance(pdata,list):
            if not pdata:
                print(f"[SKIP] empty plot data: {plot_file}")
                continue
            pdata=pdata[0]

        meta=pdata.get("metadata",{})

        enriched={
            "figure_id":f"figure-{idx:03d}",
            "figure_index":idx,
            "figure_no":fig_no,
            "title":meta.get("title",""),
            "caption":fig.get("caption"),
            "page_nos":fig.get("page_nos",[]),
            "image_path":fig.get("image_path"),
            "plot_data_path":str(plot_file),
            "series":[d.get("series","") for d in pdata.get("data",[])],
            "figure_contexts":fig_ctx,
            "subfigure_contexts":sub_ctx
        }

        save_json(enriched,out_dir/f"figure-{idx:03d}.json")
        print("[PROCESS]",idx,plot_file.name)

def main():
    for paper_dir in OUTPUT_DIR.iterdir():
        if paper_dir.is_dir():
            process_paper(paper_dir)

if __name__=="__main__":
    main()