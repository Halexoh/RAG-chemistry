"""Extracts text from every book/document in data/raw/ into data/processed/<slug>/pages.jsonl.

Two source layouts are recognized, distinguished by directory name, not by
content sniffing — content-shape heuristics (e.g. "flat folder with many
PDFs") turned out unable to tell a real multi-chapter book apart from a
folder of unrelated standalone documents (a personal archive's topical
folders, full of independent vendor data sheets, papers, theses), since
both look identical on disk: many loose PDFs, no further nesting.

  - A folder named "[Author_Year]_Title" is a BOOK: every PDF directly
    inside it is one chapter (number from the filename, or a recognized
    structural section, or — for un-numbered articles in an edited
    volume — its own filename as the title). Or, if it holds exactly one
    PDF, that PDF's own embedded table of contents resolves the chapters.
  - Anything else is a CATEGORY: every loose PDF directly inside becomes
    its own standalone, single-document "book" (its own real title, not
    the category's name — citing a vendor data sheet as "chapter 3 of
    Additives" would be misleading), and every subdirectory is walked
    the same way, one level deeper into the category path.

This means adding a new complete book later means naming its folder with
the bracket convention; anything else uploaded loose is treated as its
own independent document. See docs/01-extraccion.md.

Each output line is one page record, carrying everything the later
chunking/citation stages need: book, chapter, page, and (new) the
category path it was found under — empty for a book living directly in
data/raw/, e.g. "Corrosion y Proteccion/Materias Primas/Aditivos" for a
data sheet found three levels deep in a personal archive.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from src.extraction.chapters import (
    chapter_from_filename,
    chapter_map_from_toc,
    dedupe_versioned_chapters,
    drop_exact_duplicate_files,
    structural_label_from_filename,
)
from src.extraction.pdf_text import extract_page_text

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

BOOK_FOLDER_PATTERN = re.compile(r"^\[.+\]_.+")
BRACKET_TITLE_PATTERN = re.compile(r"^\[(.+)_(\d{4})\]_(.+)$")


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def is_book_folder(folder: Path) -> bool:
    return bool(BOOK_FOLDER_PATTERN.match(folder.name))


def book_title_from_bracket_folder(folder_name: str) -> str:
    match = BRACKET_TITLE_PATTERN.match(folder_name)
    if not match:
        return folder_name
    author, year, title = match.groups()
    return f"{title.replace('_', ' ')} ({author}, {year})"


def clean_category_segment(name: str) -> str:
    name = re.sub(r"^\d+[_\s]*", "", name)  # strip a leading sort-order number
    return name.replace("_", " ").strip()


@dataclass
class BookSource:
    title: str
    pdf_files: list[Path]
    category: str


@dataclass
class StandaloneSource:
    title: str
    pdf_path: Path
    category: str


def discover_sources(folder: Path, category: str = "") -> list[BookSource | StandaloneSource]:
    sources: list[BookSource | StandaloneSource] = []
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and entry.suffix.lower() == ".pdf":
            sources.append(StandaloneSource(title=entry.stem, pdf_path=entry, category=category))
        elif entry.is_dir():
            if is_book_folder(entry):
                pdf_files = sorted(entry.glob("*.pdf"))
                title = book_title_from_bracket_folder(entry.name)
                sources.append(BookSource(title=title, pdf_files=pdf_files, category=category))
            else:
                child_category = "/".join(
                    p for p in [category, clean_category_segment(entry.name)] if p
                )
                sources.extend(discover_sources(entry, child_category))
    return sources


def extract_multi_file_book(book_title: str, pdf_files: list[Path], category: str = "") -> list[dict]:
    pdf_files = drop_exact_duplicate_files(pdf_files)
    numbered: dict[str, list[Path]] = {}
    other: list[tuple[Path, str]] = []

    for pdf_path in pdf_files:
        chapter = chapter_from_filename(pdf_path.name)
        if chapter is not None:
            numbered.setdefault(chapter, []).append(pdf_path)
        else:
            label = structural_label_from_filename(pdf_path.name) or pdf_path.stem
            other.append((pdf_path, label))

    deduped_names = dedupe_versioned_chapters({ch: [p.name for p in paths] for ch, paths in numbered.items()})
    chapter_files = [
        (pdf_path, chapter)
        for chapter, paths in numbered.items()
        for pdf_path in paths
        if pdf_path.name in deduped_names[chapter]
    ]

    records = []
    for pdf_path, chapter in sorted(chapter_files + other, key=lambda item: item[0].name):
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text, method = extract_page_text(page)
            records.append(
                {
                    "book": book_title,
                    "chapter": chapter,
                    "page": i + 1,
                    "category": category,
                    "source_file": pdf_path.name,
                    "text": text,
                    "extraction_method": method,
                }
            )
        doc.close()
    return records


def extract_single_file_book(book_title: str, pdf_path: Path, category: str = "") -> list[dict]:
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
                "category": category,
                "source_file": pdf_path.name,
                "text": text,
                "extraction_method": method,
            }
        )
    doc.close()
    return records


def extract_source(source: BookSource | StandaloneSource) -> tuple[Path, int]:
    if isinstance(source, BookSource):
        if len(source.pdf_files) > 1:
            records = extract_multi_file_book(source.title, source.pdf_files, source.category)
        else:
            records = extract_single_file_book(source.title, source.pdf_files[0], source.category)
    else:
        records = extract_single_file_book(source.title, source.pdf_path, source.category)

    out_dir = PROCESSED_DIR / slugify(source.title)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pages.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return out_path, len(records)


def main():
    for source in discover_sources(RAW_DIR):
        out_path, n_pages = extract_source(source)
        category_note = f" [{source.category}]" if source.category else ""
        print(f"{source.title}{category_note}: {n_pages} pages -> {out_path}")


if __name__ == "__main__":
    main()
