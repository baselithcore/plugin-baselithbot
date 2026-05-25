from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from agent_jira.config import EASYOCR_LANGUAGES, EASYOCR_USE_GPU

from .utils import normalize_text, warn_missing_dependency

if TYPE_CHECKING:  # pragma: no cover
    pass


def run_pdf_ocr(path: Path) -> Optional[str]:
    """Esegue OCR su PDF scannerizzati utilizzando EasyOCR."""
    return _run_pdf_ocr_easyocr(path)


def run_image_ocr(path: Path) -> Optional[str]:
    """Esegue OCR su immagini supportate utilizzando EasyOCR."""
    return _run_image_ocr_easyocr(path)


def run_image_bytes_ocr(image_bytes: bytes, label: str = "Immagine") -> Optional[str]:
    """Esegue OCR su immagine fornita come bytes utilizzando EasyOCR."""
    return _run_image_bytes_ocr_easyocr(image_bytes, label)


# ─── EasyOCR ──────────────────────────────────────────────────────────────────

_easyocr_reader = None  # singleton lazy-init
_easyocr_lock = threading.Lock()


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    with _easyocr_lock:
        # Double-check dopo aver acquisito il lock
        if _easyocr_reader is not None:
            return _easyocr_reader
        try:
            import easyocr  # type: ignore[import]
        except ImportError:
            warn_missing_dependency("easyocr", "OCR (EasyOCR)")
            return None
        try:
            print(
                f"[ocr] Inizializzazione EasyOCR (lingue: {EASYOCR_LANGUAGES}, GPU: {EASYOCR_USE_GPU})...",
                file=sys.stderr,
            )
            _easyocr_reader = easyocr.Reader(EASYOCR_LANGUAGES, gpu=EASYOCR_USE_GPU)
            return _easyocr_reader
        except Exception as exc:
            print(f"[ocr] ⚠️ Impossibile inizializzare EasyOCR: {exc}", file=sys.stderr)
            return None


def _easyocr_results_to_text(results: list) -> str:
    """Converte i risultati EasyOCR (lista di tuple) in testo plain."""
    lines = []
    for item in results:
        # EasyOCR restituisce (bbox, text, confidence)
        text = item[1] if len(item) >= 2 else ""
        confidence = item[2] if len(item) >= 3 else 1.0
        if confidence >= 0.3 and text.strip():
            lines.append(text.strip())
    return " ".join(lines)


def _run_pdf_ocr_easyocr(path: Path) -> Optional[str]:
    reader = _get_easyocr_reader()
    if reader is None:
        return None

    # Usa pymupdf per convertire le pagine in immagini numpy
    try:
        import fitz  # pymupdf
    except ImportError:
        warn_missing_dependency("pymupdf", "conversione PDF per EasyOCR")
        return None

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        print(f"[ocr] ⚠️ EasyOCR: impossibile aprire PDF {path}: {exc}", file=sys.stderr)
        return None

    text_parts: List[str] = []
    try:
        for page_index, page in enumerate(doc, start=1):
            # Render a 300 DPI (4.17x scale da 72 DPI base) per migliore qualità OCR
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")
            pix = None  # libera memoria

            try:
                import io

                import numpy as np
                from PIL import Image as PILImage

                img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
                img_array = np.array(img)
                results = reader.readtext(img_array)
            except Exception as exc:
                print(
                    f"[ocr] ⚠️ EasyOCR: errore su pagina {page_index} di {path}: {exc}",
                    file=sys.stderr,
                )
                continue

            snippet = normalize_text(_easyocr_results_to_text(results))
            if snippet:
                text_parts.append(f"[Pagina {page_index}]\n{snippet}")
    finally:
        doc.close()

    combined = "\n\n".join(text_parts)
    if not combined.strip():
        print(f"[ocr] ⚠️ EasyOCR non ha prodotto testo per {path}", file=sys.stderr)
        return None
    return combined


def _run_image_ocr_easyocr(path: Path) -> Optional[str]:
    reader = _get_easyocr_reader()
    if reader is None:
        return None
    try:
        results = reader.readtext(str(path))
    except Exception as exc:
        print(f"[ocr] ⚠️ EasyOCR: errore su immagine {path}: {exc}", file=sys.stderr)
        return None
    snippet = normalize_text(_easyocr_results_to_text(results))
    if not snippet:
        print(f"[ocr] ⚠️ EasyOCR non ha prodotto testo per {path}", file=sys.stderr)
        return None
    return f"[Immagine 1]\n{snippet}"


def _run_image_bytes_ocr_easyocr(image_bytes: bytes, label: str) -> Optional[str]:
    reader = _get_easyocr_reader()
    if reader is None:
        return None
    try:
        import io

        import numpy as np
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)
        results = reader.readtext(img_array)
    except Exception as exc:
        print(
            f"[ocr] ⚠️ EasyOCR: errore su immagine bytes ({label}): {exc}",
            file=sys.stderr,
        )
        return None
    snippet = normalize_text(_easyocr_results_to_text(results))
    return snippet or None


__all__ = ["run_pdf_ocr", "run_image_ocr", "run_image_bytes_ocr"]
