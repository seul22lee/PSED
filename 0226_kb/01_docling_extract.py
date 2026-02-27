import json
import logging
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


@dataclass
class CaptionRecord:
    kind: str                  # "figure" | "table"
    index: int                 # 1-based
    page_nos: list[int]        # provenance 기반 page list (없을 수도)
    caption: Optional[str]     # 캡션 텍스트 (없으면 None)
    self_ref: Optional[str]    # doc pointer (있으면 유용)


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


def _caption_text_from_item(item: Any) -> Optional[str]:
    """
    PictureItem/TableItem에는 caption: Optional[Union[TextItem, RefItem]] 가 있을 수 있음. :contentReference[oaicite:1]{index=1}
    TextItem이면 .text, RefItem이면 간단히 str() fallback.
    """
    cap = getattr(item, "caption", None)
    if cap is None:
        return None
    if hasattr(cap, "text"):
        return cap.text
    return str(cap)


def extract_one_pdf(pdf_path: Path, out_root: Path) -> None:
    pdf_stem = pdf_path.stem
    out_dir = out_root / pdf_stem
    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # (선택) 그림/페이지 이미지까지 보존하려면 pipeline 옵션을 켜면 됨. :contentReference[oaicite:2]{index=2}
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = False  # 지금은 텍스트/테이블/캡션만이면 False로 가볍게

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    log.info(f"Converting: {pdf_path}")
    conv_res = converter.convert(pdf_path)
    doc = conv_res.document

    # 1) full text: markdown / json
    md_path = out_dir / "document.md"
    json_path = out_dir / "document.json"

    # save_as_markdown / save_as_json API는 공식 예시에서 사용 :contentReference[oaicite:3]{index=3}
    doc.save_as_markdown(md_path)
    doc.save_as_json(json_path)

    # 2) tables export (csv/html + index json)
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
                "caption": _caption_text_from_item(table),
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

        caption = _caption_text_from_item(pic)
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

    log.info(f"Done: {pdf_stem} (tables={len(tables_meta)}, figures={len(fig_records)})")


def main():
    pdf_dir = Path("pdf")
    out_root = Path("extracted")
    out_root.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError("No PDF files found in ./pdf")

    for pdf_path in pdf_files:
        extract_one_pdf(pdf_path, out_root)


if __name__ == "__main__":
    main()