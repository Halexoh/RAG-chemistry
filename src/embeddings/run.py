"""Embeds every book's chunks.jsonl into a sibling embeddings.npy.

Row i of embeddings.npy is the vector for line i of chunks.jsonl — that
positional correspondence is the only thing tying a vector back to its
text and citation metadata, so the two files must always be regenerated
together (chunking changes => re-embed).
"""

import json
from pathlib import Path

import numpy as np

from src.embeddings.embedder import embed_passages

PROCESSED_DIR = Path("data/processed")


def load_chunks(book_dir: Path) -> list[dict]:
    with open(book_dir / "chunks.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def embed_book(book_dir: Path) -> tuple[Path, int]:
    chunks = load_chunks(book_dir)
    vectors = embed_passages([c["text"] for c in chunks])

    out_path = book_dir / "embeddings.npy"
    np.save(out_path, vectors)
    return out_path, len(chunks)


def main():
    for book_dir in sorted(PROCESSED_DIR.iterdir()):
        if book_dir.is_dir() and (book_dir / "chunks.jsonl").exists():
            out_path, n_chunks = embed_book(book_dir)
            print(f"{book_dir.name}: {n_chunks} chunks embedded -> {out_path}")


if __name__ == "__main__":
    main()
