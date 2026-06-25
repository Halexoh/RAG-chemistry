"""Turns chunk text into vectors using a local multilingual embedding model.

Model: intfloat/multilingual-e5-base. Chosen because the source chunks are
in English but questions may come in Spanish or English — a multilingual
embedding model places both languages' text for the same chemistry concept
close together in vector space. That's what lets a Spanish query retrieve
an English passage straight from the source PDFs without any translation
step in the pipeline.

E5 models require an explicit prefix on every input string: "query: ..."
for things you search with, "passage: ..." for things you search over.
This isn't a stylistic choice — the model was trained with this
convention, and embeddings end up in noticeably worse positions in vector
space if it's left off.

Embeddings are L2-normalized on output, so cosine similarity between two
vectors reduces to a plain dot product — what FAISS's inner-product index
computes directly (used in the indexing phase).

Forced onto CPU (not Apple Silicon's MPS/GPU backend): found during
evaluation that this model's MPS tensor copies (`MTLCommandBuffer
waitUntilCompleted`) can stall indefinitely when Ollama's own GPU usage
is happening concurrently under memory pressure — two processes
contending for the same Metal command queue on a 16 GB machine. CPU
inference is slower per call but small batches (a handful of chunks,
one query) make that difference negligible, and it removes the GPU
contention with Ollama entirely.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-base"

_model: SentenceTransformer | None = None  # lazy singleton: loading is the expensive part


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model


def add_passage_prefix(texts: list[str]) -> list[str]:
    return [f"passage: {t}" for t in texts]


def add_query_prefix(text: str) -> str:
    return f"query: {text}"


def embed_passages(texts: list[str], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
    model = get_model()
    prefixed = add_passage_prefix(texts)
    return model.encode(
        prefixed,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )


def embed_query(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(add_query_prefix(text), normalize_embeddings=True)
