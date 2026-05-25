"""PDF parser. Native via pdfplumber; fallback PaddleOCR for scanned pages."""

import uuid
from pathlib import Path
from typing import Any

from ...schemas.state import Chunk

# OCR confidence below this → flag chunk as low quality
_OCR_MIN_CONF = 0.60


def parse(path: Path) -> list[Chunk]:
    import pdfplumber

    chunks: list[Chunk] = []
    scanned_pages: list[int] = []

    with pdfplumber.open(path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                chunks.extend(_chunks_from_native(page, page_idx, text))
            else:
                scanned_pages.append(page_idx)

    if scanned_pages:
        chunks.extend(_run_ocr(path, scanned_pages))

    return chunks


def _chunks_from_native(page: Any, page_idx: int, text: str) -> list[Chunk]:
    bbox = (0.0, 0.0, float(page.width), float(page.height))
    return [
        Chunk(
            id=f"c-{uuid.uuid4().hex[:8]}",
            text=text,
            page=page_idx,
            line_start=1,
            line_end=text.count("\n") + 1,
            bbox=bbox,
            token_count=len(text.split()),
        )
    ]


def _run_ocr(path: Path, page_indices: list[int]) -> list[Chunk]:
    from paddleocr import PaddleOCR
    from pdf2image import convert_from_path

    ocr = PaddleOCR(use_angle_cls=True, lang="latin", show_log=False)
    images = convert_from_path(str(path), dpi=200)
    chunks: list[Chunk] = []

    for page_idx in page_indices:
        img = images[page_idx - 1]
        result = ocr.ocr(_pil_to_array(img), cls=True)
        if not result or not result[0]:
            continue
        for line_idx, line in enumerate(result[0], start=1):
            box, (text, conf) = line
            if conf < _OCR_MIN_CONF:
                continue
            x0, y0 = box[0]
            x1, y1 = box[2]
            chunks.append(
                Chunk(
                    id=f"c-{uuid.uuid4().hex[:8]}",
                    text=text,
                    page=page_idx,
                    line_start=line_idx,
                    line_end=line_idx,
                    bbox=(float(x0), float(y0), float(x1), float(y1)),
                    token_count=len(text.split()),
                )
            )
    return chunks


def _pil_to_array(img: Any) -> Any:
    import numpy as np

    return np.array(img)
