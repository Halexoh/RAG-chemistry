"""Extracts text from every book in data/raw/ into data/processed/<book>/pages.jsonl.

Convention: each subfolder of data/raw/ is one book. A book is either:
  - split into one PDF per chapter (multiple files), or
  - a single PDF for the whole book, in which case chapters are derived
    from its embedded table of contents.

Each output line is one page record, carrying everything the later
chunking/citation stages need: which book, which chapter, which page.
"""

import json
import re
from pathlib import Path

import fitz

from src.extraction.chapters import chapter_from_filename, chapter_map_from_toc, structural_label_from_filename
from src.extraction.pdf_text import extract_page_text

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def extract_multi_file_book(book_title: str, pdf_files: list[Path]) -> list[dict]:
    records = []
    for pdf_path in pdf_files:
        # In order: a numbered chapter, a recognized structural section, or
        # — if neither matches — the filename's own title is the chapter
        # (e.g. one article in an edited volume with no chapter numbers).
        chapter = (
            chapter_from_filename(pdf_path.name)
            or structural_label_from_filename(pdf_path.name)
            or pdf_path.stem
        )
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text, method = extract_page_text(page)
            records.append(
                {
                    "book": book_title,
                    "chapter": chapter,
                    "page": i + 1,
                    "source_file": pdf_path.name,
                    "text": text,
                    "extraction_method": method,
                }
            )
        doc.close()
    return records


def extract_single_file_book(book_title: str, pdf_path: Path) -> list[dict]:
    records = []
    doc = fitz.open(pdf_path)
    page_to_chapter = chapter_map_from_toc(doc)
    for i, page in enumerate(doc):
        text, method = extract_page_text(page)
        records.append(
            {
                "book": book_title,
                "chapter": page_to_chapter.get(i, "Unknown"),
                "page": i + 1,
                "source_file": pdf_path.name,
                "text": text,
                "extraction_method": method,
            }
        )
    doc.close()
    return records


def extract_book(book_dir: Path) -> tuple[Path, int]:
    pdf_files = sorted(book_dir.glob("*.pdf"))
    book_title = book_dir.name

    if len(pdf_files) > 1:
        records = extract_multi_file_book(book_title, pdf_files)
    else:
        records = extract_single_file_book(book_title, pdf_files[0])

    out_dir = PROCESSED_DIR / slugify(book_title)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pages.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return out_path, len(records)


def main():
    for book_dir in sorted(RAW_DIR.iterdir()):
        if not book_dir.is_dir():
            continue
        out_path, n_pages = extract_book(book_dir)
        print(f"{book_dir.name}: {n_pages} pages -> {out_path}")


if __name__ == "__main__":
    main()
