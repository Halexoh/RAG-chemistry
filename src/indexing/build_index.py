"""Builds a single FAISS index across every book's chunks.

One index for the whole corpus (not one per book) because retrieval
should be able to surface the best chunk regardless of which book it
came from — the corrosion example in docs/03-embeddings.md needed both
books to answer well.

Chunks flagged as bibliography-like (reference_filter.is_bibliography_like)
are excluded from the index but never deleted from chunks.jsonl/
embeddings.npy — see reference_filter.py for why.

Embeddings were L2-normalized at embedding time, so IndexFlatIP (inner
product) gives exact cosine similarity with no extra normalization step
here, and no approximation: FlatIP does an exhaustive scan, which is
still fast enough at this corpus size (thousands, not millions, of
vectors).
"""

import json
from pathlib import Path

import faiss
import numpy as np

from src.indexing.reference_filter import is_bibliography_like
from src.indexing.structural_filter import is_structural_section

PROCESSED_DIR = Path("data/processed")
VECTORSTORE_DIR = Path("vectorstore")


def load_book(book_dir: Path) -> tuple[list[dict], np.ndarray]:
    with open(book_dir / "chunks.jsonl", encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    vectors = np.load(book_dir / "embeddings.npy")
    return chunks, vectors


def build_index() -> tuple[int, int]:
    kept_chunks: list[dict] = []
    kept_vectors: list[np.ndarray] = []
    n_excluded = 0

    for book_dir in sorted(PROCESSED_DIR.iterdir()):
        if not (book_dir / "chunks.jsonl").exists():
            continue
        chunks, vectors = load_book(book_dir)
        for chunk, vector in zip(chunks, vectors):
            if is_bibliography_like(chunk["text"]) or is_structural_section(chunk["chapter"]):
                n_excluded += 1
                continue
            kept_chunks.append(chunk)
            kept_vectors.append(vector)

    matrix = np.vstack(kept_vectors).astype("float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    VECTORSTORE_DIR.mkdir(exist_ok=True)
    faiss.write_index(index, str(VECTORSTORE_DIR / "index.faiss"))
    with open(VECTORSTORE_DIR / "metadata.jsonl", "w", encoding="utf-8") as f:
        for chunk in kept_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return index.ntotal, n_excluded


def main():
    n_indexed, n_excluded = build_index()
    print(f"Indexed {n_indexed} chunks, excluded {n_excluded} bibliography-like chunks")


if __name__ == "__main__":
    main()
