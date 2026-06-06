import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional
import pandas as pd
from docling_core.types.doc import PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("docling-extract")

# ─────────────────────────────────────────
# Section extraction patterns
# ─────────────────────────────────────────
_ABSTRACT_HEADER = re.compile(
    r"^#{1,3}\s+abstract\b",
    re.IGNORECASE | re.MULTILINE
)
_INTRO_HEADER = re.compile(
    r"^#{1,3}\s+.*\bintroduction\b",
    re.IGNORECASE | re.MULTILINE
)
_CONCLUSION_HEADER = re.compile(
    r"^#{1,3}\s+[^\n]*(?:"
    r"conclusion"
    r"|conclusions"
    r"|summary"
    r"|summary\s*and\s*conclusions?"
    r"|summary\s*and\s*outlook"
    r"|outlook"
    r"|concluding\s*remarks?"
    r"|closing\s*remarks?"
    r")[^\n]*$",
    re.I | re.M,
)
_NEXT_HEADER = re.compile(r"^#{1,3}\s+", re.MULTILINE)

_ABSTRACT_STOP_HEADERS = [
    re.compile(r"^\s*#{0,3}\s*NOMENCLATURE\b", re.I | re.M),
    re.compile(r"^\s*#{0,3}\s*LIST OF SYMBOLS\b", re.I | re.M),
    re.compile(r"^\s*#{0,3}\s*ABBREVIATIONS\b", re.I | re.M),
    re.compile(r"^\s*#{0,3}\s*ACRONYMS\b", re.I | re.M),
]

_TABLE_CAPTION = re.compile(
    r"^\s*TABLE\s+[A-Z0-9IVXLC]+[\.:]?",
    re.I
)

_FIG_CAPTION = re.compile(
    r"^\s*(FIG\.?|FIGURE)\s*\d+[\.:]?",
    re.I
)

def _extract_abstract(md_text: str) -> Optional[str]:

    intro_match = _INTRO_HEADER.search(md_text)
    abst_match = _ABSTRACT_HEADER.search(md_text)

    if abst_match:

        start = abst_match.end()

        candidates = []

        if intro_match:
            candidates.append(intro_match.start())

        for pattern in _ABSTRACT_STOP_HEADERS:
            m = pattern.search(md_text, start)
            if m:
                candidates.append(m.start())

        end = min(candidates) if candidates else len(md_text)

        text = md_text[start:end].strip()

        return text if len(text) >= 100 else None

    # 헤더 없는 경우
    if not intro_match:
        return None

    pre_intro = md_text[:intro_match.start()]

    stop_positions = []

    for pattern in _ABSTRACT_STOP_HEADERS:
        m = pattern.search(pre_intro)
        if m:
            stop_positions.append(m.start())

    if stop_positions:
        pre_intro = pre_intro[:min(stop_positions)]

    paragraphs = []
    current = []

    for line in pre_intro.split("\n"):
        line = line.strip()

        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue

        if not line.startswith(("#", "<!--")) and len(line) >= 20:
            current.append(line)

    if current:
        paragraphs.append(" ".join(current))

    candidates = [p for p in paragraphs if len(p) >= 200]

    return "\n\n".join(candidates) if candidates else None


def _extract_conclusion(md_text: str) -> Optional[str]:

    match = _CONCLUSION_HEADER.search(md_text)

    if not match:
        return None

    remaining = md_text[match.end():]

    next_header = _NEXT_HEADER.search(remaining)

    text = (
        remaining[:next_header.start()].strip()
        if next_header
        else remaining.strip()
    )

    text = _clean_conclusion_text(text)

    return text if len(text) >= 50 else None
@dataclass
class CaptionRecord:
    kind: str                  # "figure" | "table"
    index: int                 # 1-based
    page_nos: list[int]        # provenance 기반 page list (없을 수도)
    caption: Optional[str]     # 캡션 텍스트 (없으면 None)
    self_ref: Optional[str]    # doc pointer (있으면 유용)
def _crop_formula(page_img,bbox,scale=1,pad=40):
    H=page_img.height
    left=max(0,int(bbox.l*scale)-pad)
    right=min(page_img.width,int(bbox.r*scale)+pad)
    top=max(0,int(H-bbox.t*scale)-pad)
    bottom=min(H,int(H-bbox.b*scale)+pad)
    return page_img.crop((left,top,right,bottom))
def _safe_page_nos(item: Any) -> list[int]:
    """
    Docling item.prov: list[ProvenanceItem] 를 기대.
    ProvenanceItem에 page_no 등이 들어있을 수 있음.
    (버전에 따라 필드명이 다를 수 있어 최대한 방어적으로 처리)
    """
    page_nos: list[int] = []
    prov = getattr(item, "prov", None)
    if not prov:
        return page_nos
    for p in prov:
        # 흔한 케이스: p.page_no
        if hasattr(p, "page_no") and isinstance(p.page_no, int):
            page_nos.append(p.page_no)
            continue
        # 혹시 p.page / p.page_index 같은 이름일 수도 있어서 fallback
        for k in ("page", "page_index", "pageno"):
            v = getattr(p, k, None)
            if isinstance(v, int):
                page_nos.append(v)
                break
    # 중복 제거 + 정렬
    return sorted(set(page_nos))

def _caption_text_from_item(item, doc):
    caps = getattr(item, "captions", None)
    if not caps:
        return None
    cap = caps[0]
    # RefItem resolve
    if hasattr(cap, "cref"):
        ref = cap.cref
        for t in getattr(doc, "texts", []):
            if getattr(t, "self_ref", None) == ref:
                return getattr(t, "text", None)
    if hasattr(cap, "text"):
        return cap.text
    return None
CAPTION_PATTERN = re.compile(
    r"^(fig\.?|figure|table)\s*\d+",
    re.IGNORECASE
)

def _find_caption_from_layout(doc, pic):
    texts = getattr(doc, "texts", [])
    page_nos = _safe_page_nos(pic)
    pic_bbox = getattr(pic, "bbox", None)
    if not pic_bbox:
        return None
    best = None
    best_dist = 9999
    for t in texts:
        txt = getattr(t, "text", "").strip()
        if not txt.lower().startswith(("fig", "figure")):
            continue
        if not hasattr(t, "bbox"):
            continue
        dist = abs(t.bbox.y0 - pic_bbox.y1)
        if dist < best_dist and dist < 200:
            best = txt
            best_dist = dist
    return best

def extract_one_pdf(pdf_path: Path, out_root: Path) -> None:
    pdf_stem = pdf_path.stem
    out_dir = out_root / pdf_stem / "01_docling"
    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    formulas_dir = out_dir / "formulas"
    for d in [out_dir, tables_dir, figures_dir, formulas_dir]:
        d.mkdir(parents=True, exist_ok=True)
    # (선택) 그림/페이지 이미지까지 보존하려면 pipeline 옵션을 켜면 됨. :contentReference[oaicite:2]{index=2}
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = False  # 지금은 텍스트/테이블/캡션만이면 False로 가볍게
    pipeline_options.images_scale = 4
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    log.info(f"Converting: {pdf_path}")
    conv_res = converter.convert(pdf_path)
    doc = conv_res.document
    import inspect
    print(inspect.signature(conv_res.pages[0].get_image))

    # =============================
    # DEBUG: caption 구조 확인
    # =============================
    print("\n===== DEBUG CAPTION STRUCTURE =====")
    print("Total pictures:", len(getattr(doc, "pictures", [])))
    for i, pic in enumerate(doc.pictures):
        print(f"\nPicture {i+1}")
        print("caption field:", pic.captions)
    print("\nDoc captions count:", len(getattr(doc, "captions", [])))
    print("===================================\n")
    # 1) full text: markdown / json
    md_path = out_dir / "document.md"
    json_path = out_dir / "document.json"
    # save_as_markdown / save_as_json API는 공식 예시에서 사용 :contentReference[oaicite:3]{index=3}
    doc.save_as_markdown(md_path)
    doc.save_as_json(json_path)
    # 2) sections.json — abstract + conclusion
    md_text    = md_path.read_text(encoding="utf-8")
    abstract   = _extract_abstract(md_text)
    conclusion = _extract_conclusion(md_text)
    sections   = {
        "abstract":         abstract,
        "conclusion":       conclusion,
        "abstract_found":   abstract   is not None,
        "conclusion_found": conclusion is not None,
    }
    with (out_dir / "sections.json").open("w", encoding="utf-8") as fp:
        json.dump(sections, fp, ensure_ascii=False, indent=2)
    log.info(f"Sections: abstract={sections['abstract_found']}, conclusion={sections['conclusion_found']}")
    # 3) tables export (csv/html + index json)
    tables_meta: list[dict[str, Any]] = []
    for t_idx, table in enumerate(getattr(doc, "tables", []), start=1):
        df: pd.DataFrame = table.export_to_dataframe(doc=doc)  # 공식 예시 :contentReference[oaicite:4]{index=4}
        csv_path = tables_dir / f"table-{t_idx:03d}.csv"
        html_path = tables_dir / f"table-{t_idx:03d}.html"
        df.to_csv(csv_path, index=False)
        with html_path.open("w", encoding="utf-8") as fp:
            fp.write(table.export_to_html(doc=doc))
        tables_meta.append(
            {
                "table_index": t_idx,
                "rows": int(df.shape[0]),
                "cols": int(df.shape[1]),
                "page_nos": _safe_page_nos(table),
                "caption": _caption_text_from_item(table,doc),
                "self_ref": getattr(table, "self_ref", None),
                "csv_path": str(csv_path),
                "html_path": str(html_path),
            }
        )
    with (tables_dir / "tables.json").open("w", encoding="utf-8") as fp:
        json.dump(tables_meta, fp, ensure_ascii=False, indent=2)
    # 3) figure captions + PNG export
    fig_records = []
    for p_idx, pic in enumerate(getattr(doc, "pictures", []), start=1):
        caption = _caption_text_from_item(pic, doc)
        if caption is None:
            caption = _find_caption_from_layout(doc, pic)
        page_nos = _safe_page_nos(pic)
        image = None
        try:
            image = pic.get_image(doc)  # Pillow Image 반환
        except Exception:
            pass
        image_path = None
        if image:
            image_path = figures_dir / f"figure-{p_idx:03d}.png"
            image.save(image_path)
        fig_records.append(
            {
                "figure_index": p_idx,
                "page_nos": page_nos,
                "caption": caption,
                "self_ref": getattr(pic, "self_ref", None),
                "image_path": str(image_path) if image_path else None,
            }
        )
    with (figures_dir / "figures.json").open("w", encoding="utf-8") as fp:
        json.dump(fig_records, fp, ensure_ascii=False, indent=2)
    def _formula_no(t):
        m=re.search(r"\((\d+)\)\s*$",getattr(t,"orig",""))
        return int(m.group(1)) if m else 10**9

    formula_records=[];eq_idx=1
    formula_items=[t for t in getattr(doc,"texts",[]) if getattr(t,"label",None)=="formula" and getattr(t,"prov",None)]
    formula_items.sort(key=_formula_no)

    for text_item in formula_items:
        p=text_item.prov[0];page_no=p.page_no;bbox=p.bbox
        try:
            EQ_SCALE=4
            page_img=conv_res.pages[page_no-1].get_image(scale=EQ_SCALE)
            crop=_crop_formula(page_img,bbox,scale=EQ_SCALE)
            image_path=formulas_dir/f"equation-{eq_idx:04d}.png";crop.save(image_path)
            formula_records.append({"equation_index":eq_idx,"equation_no":_formula_no(text_item),"page_no":page_no,"bbox":{"l":bbox.l,"t":bbox.t,"r":bbox.r,"b":bbox.b},"orig":getattr(text_item,"orig",""),"self_ref":getattr(text_item,"self_ref",None),"image_path":str(image_path)})
            eq_idx+=1
        except Exception as e:
            print(f"[EQ ERROR] page={page_no}: {e}")
    with (formulas_dir / "formulas.json").open("w", encoding="utf-8") as fp:
        json.dump(formula_records, fp, ensure_ascii=False, indent=2)
    log.info(
        f"Done: {pdf_stem} "
        f"(tables={len(tables_meta)}, figures={len(fig_records)}, formulas={len(formula_records)})"
    )

def _clean_conclusion_text(text: str) -> str:
    lines = text.splitlines()

    cleaned = []
    inside_table = False

    for line in lines:
        stripped = line.strip()

        # markdown table row
        if "|" in stripped:
            inside_table = True
            continue

        # table 종료
        if inside_table:
            if stripped == "":
                inside_table = False
            continue

        # TABLE I ...
        if _TABLE_CAPTION.match(stripped):
            continue

        # FIG. 1 ...
        if _FIG_CAPTION.match(stripped):
            continue

        cleaned.append(line)

    text = "\n".join(cleaned)

    # 빈줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
def main():
    from config import PDF_DIR, OUTPUT_DIR
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {PDF_DIR}")
    for pdf_path in pdf_files:
        extract_one_pdf(pdf_path, OUTPUT_DIR)
if __name__ == "__main__":
    main()