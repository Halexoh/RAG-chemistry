"""Searches the FAISS index built by build_index.py."""

import json
from pathlib import Path

import faiss

from src.embeddings.embedder import embed_query

VECTORSTORE_DIR = Path("vectorstore")


def load_index() -> tuple[faiss.Index, list[dict]]:
    index = faiss.read_index(str(VECTORSTORE_DIR / "index.faiss"))
    with open(VECTORSTORE_DIR / "metadata.jsonl", encoding="utf-8") as f:
        metadata = [json.loads(line) for line in f]
    return index, metadata


def search(
    query: str,
    k: int = 5,
    index: faiss.Index | None = None,
    metadata: list[dict] | None = None,
) -> list[dict]:
    if index is None or metadata is None:
        index, metadata = load_index()

    query_vector = embed_query(query).reshape(1, -1).astype("float32")
    scores, indices = index.search(query_vector, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        result = dict(metadata[idx])
        result["score"] = float(score)
        results.append(result)
    return results
