#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
from pathlib import Path


def extract_two_column_text(pdf_path: str | Path) -> str:
    """
    두 컬럼으로 된 논문 PDF를
    [PAGE별 / LEFT 먼저 / RIGHT 나중] 순서로 텍스트를 뽑아서
    하나의 큰 문자열로 반환.
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    all_pages_text = []

    for page_idx, page in enumerate(doc):
        blocks = page.get_text("blocks")

        left_blocks = []
        right_blocks = []

        page_rect = page.rect
        mid_x = (page_rect.x0 + page_rect.x1) / 2.0

        for b in blocks:
            # block 형식이 (x0, y0, x1, y1, text, ...) 로 온다고 가정하고 앞 5개만 사용
            if len(b) < 5:
                continue
            x0, y0, x1, y1, text = b[:5]
            if not text or not str(text).strip():
                continue

            cx = (x0 + x1) / 2.0  # 블록 중심 x

            if cx < mid_x:
                left_blocks.append((y0, text))
            else:
                right_blocks.append((y0, text))

        # y 기준 정렬
        left_blocks.sort(key=lambda t: t[0])
        right_blocks.sort(key=lambda t: t[0])

        left_text = "\n".join(t for _, t in left_blocks)
        right_text = "\n".join(t for _, t in right_blocks)

        page_text = (
            f"===== PAGE {page_idx + 1} =====\n"
            f"----- LEFT COLUMN -----\n{left_text}\n\n"
            f"----- RIGHT COLUMN -----\n{right_text}\n"
        )
        all_pages_text.append(page_text)

    doc.close()
    return "\n\n".join(all_pages_text)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Dump two-column PDF text to txt (for debugging order)."
    )
    parser.add_argument("pdf", type=str, help="PDF file path")
    parser.add_argument("-o", "--out", type=str, default="pdf_text_dump.txt",
                        help="output txt file (default: pdf_text_dump.txt)")

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    out_path = Path(args.out)

    text = extract_two_column_text(pdf_path)
    out_path.write_text(text, encoding="utf-8")

    print(f"Saved text dump to {out_path.resolve()}")


if __name__ == "__main__":
    main()
