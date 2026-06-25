"""Turns each book's data/processed/<book>/pages.jsonl into chunks.jsonl.

Pages are grouped by chapter (relying on extraction/run.py having written
each chapter's pages contiguously) and each chapter is chunked
independently, so no chunk ever spans two chapters.
"""

import json
from itertools import groupby
from pathlib import Path

from src.chunking.chunker import chunk_pages

PROCESSED_DIR = Path("data/processed")


def load_pages(book_dir: Path) -> list[dict]:
    with open(book_dir / "pages.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def chunk_book(book_dir: Path) -> tuple[Path, int]:
    pages = load_pages(book_dir)

    all_chunks = []
    for _chapter, chapter_pages in groupby(pages, key=lambda p: p["chapter"]):
        all_chunks.extend(chunk_pages(list(chapter_pages)))

    out_path = book_dir / "chunks.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return out_path, len(all_chunks)


def main():
    for book_dir in sorted(PROCESSED_DIR.iterdir()):
        if book_dir.is_dir() and (book_dir / "pages.jsonl").exists():
            out_path, n_chunks = chunk_book(book_dir)
            print(f"{book_dir.name}: {n_chunks} chunks -> {out_path}")


if __name__ == "__main__":
    main()
