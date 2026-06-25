"""Per-page text extraction with an automatic native-text/OCR fallback.

Most chemistry textbook PDFs have real, selectable text embedded by
whatever tool produced them (e.g. exported from LaTeX or InDesign).
Some are just scans of paper pages — a photo with no text layer at all.
PyMuPDF's `page.get_text()` returns an empty (or near-empty) string for
the second kind, which is the cheapest possible signal to tell them apart
without running OCR on every single page (OCR is ~50-100x slower).
"""

import io

import fitz
import pytesseract
from PIL import Image

# A page with real text rarely has fewer characters than this, even if
# it's mostly a figure with a short caption. Tuned empirically, not exact.
NATIVE_TEXT_MIN_CHARS = 30
OCR_DPI = 300
OCR_LANGUAGES = "eng+spa"


def page_has_native_text(page: fitz.Page) -> bool:
    return len(page.get_text().strip()) >= NATIVE_TEXT_MIN_CHARS


def extract_native_text(page: fitz.Page) -> str:
    return page.get_text().strip()


def extract_ocr_text(page: fitz.Page) -> str:
    pixmap = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return pytesseract.image_to_string(image, lang=OCR_LANGUAGES).strip()


def extract_page_text(page: fitz.Page) -> tuple[str, str]:
    """Returns (text, method) — method is 'native' or 'ocr'."""
    if page_has_native_text(page):
        return extract_native_text(page), "native"
    return extract_ocr_text(page), "ocr"
